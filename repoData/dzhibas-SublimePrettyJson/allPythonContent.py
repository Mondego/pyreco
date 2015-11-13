__FILENAME__ = PrettyJson
import sublime
import sublime_plugin
import decimal
import sys
import re

try:
    # python 3 / Sublime Text 3
    from . import simplejson as json
    from .simplejson import OrderedDict
except (ValueError):
    # python 2 / Sublime Text 2
    import simplejson as json
    from simplejson import OrderedDict

jq_exits = False
jq_version = None

import subprocess

try:
    # checking if ./jq tool is available so we can use it
    s = subprocess.Popen(["jq", "--version"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = s.communicate()
    jq_version = err.decode("utf-8").replace("jq version ", "").strip()
    jq_exits = True
except OSError:
    jq_exits = False


s = sublime.load_settings("Pretty JSON.sublime-settings")


class PrettyJsonCommand(sublime_plugin.TextCommand):
    json_error_matcher = re.compile(r"line (\d+) column (\d+) \(char (\d+)\)")

    """ Pretty Print JSON """
    def run(self, edit):
        self.view.erase_regions('json_errors')
        for region in self.view.sel():

            selected_entire_file = False

            # If no selection, use the entire file as the selection
            if region.empty() and s.get("use_entire_file_if_no_selection", True):
                selection = sublime.Region(0, self.view.size())
                selected_entire_file = True
            else:
                selection = region

            try:
                obj = json.loads(self.view.substr(selection),
                                 object_pairs_hook=OrderedDict,
                                 parse_float=decimal.Decimal)

                self.view.replace(edit, selection, json.dumps(obj,
                                  indent=s.get("indent", 2),
                                  ensure_ascii=s.get("ensure_ascii", False),
                                  sort_keys=s.get("sort_keys", False),
                                  separators=(',', ': '),
                                  use_decimal=True))

                if selected_entire_file:
                    self.change_syntax()

            except Exception:
                exc = sys.exc_info()[1]
                sublime.status_message(str(exc))
                self.highlight_error(str(exc))

    def highlight_error(self, message):
        m = self.json_error_matcher.search(message)
        if m:
            line = int(m.group(1)) - 1
            regions = [self.view.full_line(self.view.text_point(line, 0)), ]
            self.view.add_regions('json_errors', regions, 'invalid', 'dot', sublime.DRAW_OUTLINED)
            self.view.set_status('json_errors', message)

    def change_syntax(self):
        """ Changes syntax to JSON if its in plain text """
        if "Plain text" in self.view.settings().get('syntax'):
            self.view.set_syntax_file("Packages/JavaScript/JSON.tmLanguage")


class UnPrettyJsonCommand(PrettyJsonCommand):
    """
    Compress/minify JSON
    it makes json as one-liner
    """
    def run(self, edit):
        """ overwriting base class run function to remove intent """
        self.view.erase_regions('json_errors')
        for region in self.view.sel():

            selected_entire_file = False

            # If no selection, use the entire file as the selection
            if region.empty() and s.get("use_entire_file_if_no_selection", True):
                selection = sublime.Region(0, self.view.size())
                selected_entire_file = True
            else:
                selection = region

            try:
                obj = json.loads(self.view.substr(selection),
                                 object_pairs_hook=OrderedDict,
                                 parse_float=decimal.Decimal)

                self.view.replace(edit, selection, json.dumps(obj,
                                  ensure_ascii=s.get("ensure_ascii", False),
                                  sort_keys=s.get("sort_keys", False),
                                  separators=(',', ':'),
                                  use_decimal=True))

                if selected_entire_file:
                    self.change_syntax()

            except Exception:
                exc = sys.exc_info()[1]
                self.highlight_error(str(exc))
                sublime.status_message(str(exc))


class JqPrettyJson(sublime_plugin.WindowCommand):
    """
    Allows work with ./jq
    """
    def run(self):
        if jq_exits:
            self.window.show_input_panel("Enter ./jq filter expression", ".", on_done=self.done, on_change=None, on_cancel=None)
        else:
            sublime.status_message("./jq tool is not available on your system. http://stedolan.github.io/jq")

    def get_content(self):
        """
        returns content of active view or selected region
        """
        view = self.window.active_view()
        selection = ""
        for region in view.sel():
            # If no selection, use the entire file as the selection
            if region.empty():
                selection = sublime.Region(0, view.size())
            else:
                selection = region
        return view.substr(selection)

    def done(self, query):
        try:
            p = subprocess.Popen(["jq", query], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            raw_json = self.get_content()
            out, err = p.communicate(bytes(raw_json, "utf-8"))
            output = out.decode("UTF-8").strip()

            if output:
                view = self.window.new_file()
                view.run_command("jq_pretty_json_out", {"jq_output": output})
                view.set_syntax_file("Packages/JavaScript/JSON.tmLanguage")

        except OSError:
            exc = sys.exc_info()[1]
            sublime.status_message(str(exc))


class JqPrettyJsonOut(sublime_plugin.TextCommand):
    def run(self, edit, jq_output=''):
        self.view.insert(edit, 0, jq_output)


def plugin_loaded():
    global s
    s = sublime.load_settings("Pretty JSON.sublime-settings")
########NEW FILE########
__FILENAME__ = compat
"""Python 3 compatibility shims
"""
import sys
if sys.version_info[0] < 3:
    PY3 = False
    def b(s):
        return s
    def u(s):
        return unicode(s, 'unicode_escape')
    import cStringIO as StringIO
    StringIO = BytesIO = StringIO.StringIO
    text_type = unicode
    binary_type = str
    string_types = (basestring,)
    integer_types = (int, long)
    unichr = unichr
    reload_module = reload
    def fromhex(s):
        return s.decode('hex')

else:
    PY3 = True
    from imp import reload as reload_module
    import codecs
    def b(s):
        return codecs.latin_1_encode(s)[0]
    def u(s):
        return s
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
    text_type = str
    binary_type = bytes
    string_types = (str,)
    integer_types = (int,)

    def unichr(s):
        return u(chr(s))

    def fromhex(s):
        return bytes.fromhex(s)

long_type = integer_types[-1]

########NEW FILE########
__FILENAME__ = decoder
"""Implementation of JSONDecoder
"""
from __future__ import absolute_import
import re
import sys
import struct
from .compat import fromhex, b, u, text_type, binary_type, PY3, unichr
from .scanner import make_scanner
def _import_c_scanstring():
    try:
        from ._speedups import scanstring
        return scanstring
    except ImportError:
        return None
c_scanstring = _import_c_scanstring()

__all__ = ['JSONDecoder']

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    _BYTES = fromhex('7FF80000000000007FF0000000000000')
    # The struct module in Python 2.4 would get frexp() out of range here
    # when an endian is specified in the format string. Fixed in Python 2.5+
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


class JSONDecodeError(ValueError):
    """Subclass of ValueError with the following additional properties:

    msg: The unformatted error message
    doc: The JSON document being parsed
    pos: The start index of doc where parsing failed
    end: The end index of doc where parsing failed (may be None)
    lineno: The line corresponding to pos
    colno: The column corresponding to pos
    endlineno: The line corresponding to end (may be None)
    endcolno: The column corresponding to end (may be None)

    """
    def __init__(self, msg, doc, pos, end=None):
        ValueError.__init__(self, errmsg(msg, doc, pos, end=end))
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.end = end
        self.lineno, self.colno = linecol(doc, pos)
        if end is not None:
            self.endlineno, self.endcolno = linecol(doc, end)
        else:
            self.endlineno, self.endcolno = None, None


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    # Note that this function is called from _speedups
    lineno, colno = linecol(doc, pos)
    if end is None:
        #fmt = '{0}: line {1} column {2} (char {3})'
        #return fmt.format(msg, lineno, colno, pos)
        fmt = '%s: line %d column %d (char %d)'
        return fmt % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    #fmt = '{0}: line {1} column {2} - line {3} column {4} (char {5} - {6})'
    #return fmt.format(msg, lineno, colno, endlineno, endcolno, pos, end)
    fmt = '%s: line %d column %d - line %d column %d (char %d - %d)'
    return fmt % (msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}

STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u('"'), '\\': u('\u005c'), '/': u('/'),
    'b': u('\b'), 'f': u('\f'), 'n': u('\n'), 'r': u('\r'), 't': u('\t'),
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True,
        _b=BACKSLASH, _m=STRINGCHUNK.match, _join=u('').join,
        _PY3=PY3, _maxunicode=sys.maxunicode):
    """Scan the string s for a JSON string. End is the index of the
    character in s after the quote that started the JSON string.
    Unescapes all valid JSON string escape sequences and raises ValueError
    on attempt to decode an invalid string. If strict is False then literal
    control characters are allowed in the string.

    Returns a tuple of the decoded string and the index of the character in s
    after the end quote."""
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        end = chunk.end()
        content, terminator = chunk.groups()
        # Content is contains zero or more unescaped string characters
        if content:
            if not _PY3 and not isinstance(content, text_type):
                content = text_type(content, encoding)
            _append(content)
        # Terminator is the end of string, a literal control character,
        # or a backslash denoting that an escape sequence follows
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                msg = "Invalid control character %r at" % (terminator,)
                #msg = "Invalid control character {0!r} at".format(terminator)
                raise JSONDecodeError(msg, s, end)
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        # If not a unicode escape sequence, must be in the lookup table
        if esc != 'u':
            try:
                char = _b[esc]
            except KeyError:
                msg = "Invalid \\escape: " + repr(esc)
                raise JSONDecodeError(msg, s, end)
            end += 1
        else:
            # Unicode escape sequence
            esc = s[end + 1:end + 5]
            next_end = end + 5
            if len(esc) != 4:
                msg = "Invalid \\uXXXX escape"
                raise JSONDecodeError(msg, s, end)
            try:
                uni = int(esc, 16)
            except ValueError:
                msg = "Invalid \\uXXXX escape"
                raise JSONDecodeError(msg, s, end)
            # Check for surrogate pair on UCS-4 systems
            if _maxunicode > 65535:
                unimask = uni & 0xfc00
                if unimask == 0xd800:
                    msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                    if not s[end + 5:end + 7] == '\\u':
                        raise JSONDecodeError(msg, s, end)
                    esc2 = s[end + 7:end + 11]
                    if len(esc2) != 4:
                        raise JSONDecodeError(msg, s, end)
                    try:
                        uni2 = int(esc2, 16)
                    except ValueError:
                        raise JSONDecodeError(msg, s, end)
                    if uni2 & 0xfc00 != 0xdc00:
                        msg = "Unpaired high surrogate"
                        raise JSONDecodeError(msg, s, end)
                    uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                    next_end += 6
                elif unimask == 0xdc00:
                    msg = "Unpaired low surrogate"
                    raise JSONDecodeError(msg, s, end)
            char = unichr(uni)
            end = next_end
        # Append the unescaped character
        _append(char)
    return _join(chunks), end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'

def JSONObject(state, encoding, strict, scan_once, object_hook,
        object_pairs_hook, memo=None,
        _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    (s, end) = state
    # Backwards compatibility
    if memo is None:
        memo = {}
    memo_get = memo.setdefault
    pairs = []
    # Use a slice to prevent IndexError from being raised, the following
    # check will raise a more specific ValueError if the string is empty
    nextchar = s[end:end + 1]
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end:end + 1]
        # Trivial empty object
        if nextchar == '}':
            if object_pairs_hook is not None:
                result = object_pairs_hook(pairs)
                return result, end + 1
            pairs = {}
            if object_hook is not None:
                pairs = object_hook(pairs)
            return pairs, end + 1
        elif nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes",
                s, end)
    end += 1
    while True:
        key, end = scanstring(s, end, encoding, strict)
        key = memo_get(key, key)

        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            end = _w(s, end).end()
            if s[end:end + 1] != ':':
                raise JSONDecodeError("Expecting ':' delimiter", s, end)

        end += 1

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise JSONDecodeError("Expecting object", s, end)
        pairs.append((key, value))

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ''
        end += 1

        if nextchar == '}':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting ',' delimiter", s, end - 1)

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end += 1
                nextchar = s[end]
                if nextchar in _ws:
                    end = _w(s, end + 1).end()
                    nextchar = s[end]
        except IndexError:
            nextchar = ''

        end += 1
        if nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes",
                s, end - 1)

    if object_pairs_hook is not None:
        result = object_pairs_hook(pairs)
        return result, end
    pairs = dict(pairs)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end

def JSONArray(state, scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    (s, end) = state
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    _append = values.append
    while True:
        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise JSONDecodeError("Expecting object", s, end)
        _append(value)
        nextchar = s[end:end + 1]
        if nextchar in _ws:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting ',' delimiter", s, end)

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True,
            object_pairs_hook=None):
        """
        *encoding* determines the encoding used to interpret any
        :class:`str` objects decoded by this instance (``'utf-8'`` by
        default).  It has no effect when decoding :class:`unicode` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as :class:`unicode`.

        *object_hook*, if specified, will be called with the result of every
        JSON object decoded and its return value will be used in place of the
        given :class:`dict`.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        *object_pairs_hook* is an optional function that will be called with
        the result of any object literal decode with an ordered list of pairs.
        The return value of *object_pairs_hook* will be used instead of the
        :class:`dict`.  This feature can be used to implement custom decoders
        that rely on the order that the key and value pairs are decoded (for
        example, :func:`collections.OrderedDict` will remember the order of
        insertion). If *object_hook* is also defined, the *object_pairs_hook*
        takes priority.

        *parse_float*, if specified, will be called with the string of every
        JSON float to be decoded.  By default, this is equivalent to
        ``float(num_str)``. This can be used to use another datatype or parser
        for JSON floats (e.g. :class:`decimal.Decimal`).

        *parse_int*, if specified, will be called with the string of every
        JSON int to be decoded.  By default, this is equivalent to
        ``int(num_str)``.  This can be used to use another datatype or parser
        for JSON integers (e.g. :class:`float`).

        *parse_constant*, if specified, will be called with one of the
        following strings: ``'-Infinity'``, ``'Infinity'``, ``'NaN'``.  This
        can be used to raise an exception if invalid JSON numbers are
        encountered.

        *strict* controls the parser's behavior when it encounters an
        invalid control character in a string. The default setting of
        ``True`` means that unescaped control characters are parse errors, if
        ``False`` then control characters will be allowed in strings.

        """
        if encoding is None:
            encoding = DEFAULT_ENCODING
        self.encoding = encoding
        self.object_hook = object_hook
        self.object_pairs_hook = object_pairs_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.memo = {}
        self.scan_once = make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match, _PY3=PY3):
        """Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)

        """
        if _PY3 and isinstance(s, binary_type):
            s = s.decode(self.encoding)
        obj, end = self.raw_decode(s)
        end = _w(s, end).end()
        if end != len(s):
            raise JSONDecodeError("Extra data", s, end, len(s))
        return obj

    def raw_decode(self, s, idx=0, _w=WHITESPACE.match, _PY3=PY3):
        """Decode a JSON document from ``s`` (a ``str`` or ``unicode``
        beginning with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.
        Optionally, ``idx`` can be used to specify an offset in ``s`` where
        the JSON document begins.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        if _PY3 and not isinstance(s, text_type):
            raise TypeError("Input string must be text, not bytes")
        try:
            obj, end = self.scan_once(s, idx=_w(s, idx).end())
        except StopIteration:
            raise JSONDecodeError("No JSON object could be decoded", s, idx)
        return obj, end

########NEW FILE########
__FILENAME__ = encoder
"""Implementation of JSONEncoder
"""
from __future__ import absolute_import
import re
from operator import itemgetter
from decimal import Decimal
from .compat import u, unichr, binary_type, string_types, integer_types, PY3
def _import_speedups():
    try:
        from . import _speedups
        return _speedups.encode_basestring_ascii, _speedups.make_encoder
    except ImportError:
        return None, None
c_encode_basestring_ascii, c_make_encoder = _import_speedups()

from .decoder import PosInf

#ESCAPE = re.compile(ur'[\x00-\x1f\\"\b\f\n\r\t\u2028\u2029]')
# This is required because u() will mangle the string and ur'' isn't valid
# python3 syntax
ESCAPE = re.compile(u'[\\x00-\\x1f\\\\"\\b\\f\\n\\r\\t\u2028\u2029]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    #ESCAPE_DCT.setdefault(chr(i), '\\u{0:04x}'.format(i))
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))
for i in [0x2028, 0x2029]:
    ESCAPE_DCT.setdefault(unichr(i), '\\u%04x' % (i,))

FLOAT_REPR = repr

def encode_basestring(s, _PY3=PY3, _q=u('"')):
    """Return a JSON representation of a Python string

    """
    if _PY3:
        if isinstance(s, binary_type):
            s = s.decode('utf-8')
    else:
        if isinstance(s, str) and HAS_UTF8.search(s) is not None:
            s = s.decode('utf-8')
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return _q + ESCAPE.sub(replace, s) + _q


def py_encode_basestring_ascii(s, _PY3=PY3):
    """Return an ASCII-only JSON representation of a Python string

    """
    if _PY3:
        if isinstance(s, binary_type):
            s = s.decode('utf-8')
    else:
        if isinstance(s, str) and HAS_UTF8.search(s) is not None:
            s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                #return '\\u{0:04x}'.format(n)
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                #return '\\u{0:04x}\\u{1:04x}'.format(s1, s2)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


encode_basestring_ascii = (
    c_encode_basestring_ascii or py_encode_basestring_ascii)

class JSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict, namedtuple  | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None,
            use_decimal=True, namedtuple_as_object=True,
            tuple_as_array=True, bigint_as_string=False,
            item_sort_key=None):
        """Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is false, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is true, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is true, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is true, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is true, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a string, then JSON array elements and object members
        will be pretty-printed with a newline followed by that string repeated
        for each level of nesting. ``None`` (the default) selects the most compact
        representation without any newlines. For backwards compatibility with
        versions of simplejson earlier than 2.1.0, an integer is also accepted
        and is converted to a string with that many spaces.

        If specified, separators should be a (item_separator, key_separator)
        tuple.  The default is (', ', ': ').  To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.

        If use_decimal is true (not the default), ``decimal.Decimal`` will
        be supported directly by the encoder. For the inverse, decode JSON
        with ``parse_float=decimal.Decimal``.

        If namedtuple_as_object is true (the default), objects with
        ``_asdict()`` methods will be encoded as JSON objects.

        If tuple_as_array is true (the default), tuple (and subclasses) will
        be encoded as JSON arrays.

        If bigint_as_string is true (not the default), ints 2**53 and higher
        or lower than -2**53 will be encoded as strings. This is to avoid the
        rounding that happens in Javascript otherwise.

        If specified, item_sort_key is a callable used to sort the items in
        each dictionary. This is useful if you want to sort items other than
        in alphabetical order by key.
        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.use_decimal = use_decimal
        self.namedtuple_as_object = namedtuple_as_object
        self.tuple_as_array = tuple_as_array
        self.bigint_as_string = bigint_as_string
        self.item_sort_key = item_sort_key
        if indent is not None and not isinstance(indent, string_types):
            indent = indent * ' '
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        elif indent is not None:
            self.item_separator = ','
        if default is not None:
            self.default = default
        self.encoding = encoding

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)

        """
        raise TypeError(repr(o) + " is not JSON serializable")

    def encode(self, o):
        """Return a JSON string representation of a Python data structure.

        >>> from simplejson import JSONEncoder
        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, binary_type):
            _encoding = self.encoding
            if (_encoding is not None and not (_encoding == 'utf-8')):
                o = o.decode(_encoding)
        if isinstance(o, string_types):
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = self.iterencode(o, _one_shot=True)
        if not isinstance(chunks, (list, tuple)):
            chunks = list(chunks)
        if self.ensure_ascii:
            return ''.join(chunks)
        else:
            return u''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring
        if self.encoding != 'utf-8':
            def _encoder(o, _orig_encoder=_encoder, _encoding=self.encoding):
                if isinstance(o, binary_type):
                    o = o.decode(_encoding)
                return _orig_encoder(o)

        def floatstr(o, allow_nan=self.allow_nan,
                _repr=FLOAT_REPR, _inf=PosInf, _neginf=-PosInf):
            # Check for specials. Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on
            # the internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text


        key_memo = {}
        if (_one_shot and c_make_encoder is not None
                and self.indent is None):
            _iterencode = c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan, key_memo, self.use_decimal,
                self.namedtuple_as_object, self.tuple_as_array,
                self.bigint_as_string, self.item_sort_key,
                self.encoding,
                Decimal)
        else:
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot, self.use_decimal,
                self.namedtuple_as_object, self.tuple_as_array,
                self.bigint_as_string, self.item_sort_key,
                self.encoding,
                Decimal=Decimal)
        try:
            return _iterencode(o, 0)
        finally:
            key_memo.clear()


class JSONEncoderForHTML(JSONEncoder):
    """An encoder that produces JSON safe to embed in HTML.

    To embed JSON content in, say, a script tag on a web page, the
    characters &, < and > should be escaped. They cannot be escaped
    with the usual entities (e.g. &amp;) because they are not expanded
    within <script> tags.
    """

    def encode(self, o):
        # Override JSONEncoder.encode because it has hacks for
        # performance that make things more complicated.
        chunks = self.iterencode(o, True)
        if self.ensure_ascii:
            return ''.join(chunks)
        else:
            return u''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        chunks = super(JSONEncoderForHTML, self).iterencode(o, _one_shot)
        for chunk in chunks:
            chunk = chunk.replace('&', '\\u0026')
            chunk = chunk.replace('<', '\\u003c')
            chunk = chunk.replace('>', '\\u003e')
            yield chunk


def _make_iterencode(markers, _default, _encoder, _indent, _floatstr,
        _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
        _use_decimal, _namedtuple_as_object, _tuple_as_array,
        _bigint_as_string, _item_sort_key, _encoding,
        ## HACK: hand-optimized bytecode; turn globals into locals
        _PY3=PY3,
        ValueError=ValueError,
        string_types=string_types,
        Decimal=Decimal,
        dict=dict,
        float=float,
        id=id,
        integer_types=integer_types,
        isinstance=isinstance,
        list=list,
        str=str,
        tuple=tuple,
    ):
    if _item_sort_key and not callable(_item_sort_key):
        raise TypeError("item_sort_key must be None or callable")
    elif _sort_keys and not _item_sort_key:
        _item_sort_key = itemgetter(0)

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (_indent * _current_indent_level)
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if (isinstance(value, string_types) or
                (_PY3 and isinstance(value, binary_type))):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, integer_types):
                yield ((buf + str(value))
                       if (not _bigint_as_string or
                           (-1 << 53) < value < (1 << 53))
                           else (buf + '"' + str(value) + '"'))
            elif isinstance(value, float):
                yield buf + _floatstr(value)
            elif _use_decimal and isinstance(value, Decimal):
                yield buf + str(value)
            else:
                yield buf
                if isinstance(value, list):
                    chunks = _iterencode_list(value, _current_indent_level)
                else:
                    _asdict = _namedtuple_as_object and getattr(value, '_asdict', None)
                    if _asdict and callable(_asdict):
                        chunks = _iterencode_dict(_asdict(),
                                                  _current_indent_level)
                    elif _tuple_as_array and isinstance(value, tuple):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance(value, dict):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (_indent * _current_indent_level)
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _stringify_key(key):
        if isinstance(key, string_types): # pragma: no cover
            pass
        elif isinstance(key, binary_type):
            key = key.decode(_encoding)
        elif isinstance(key, float):
            key = _floatstr(key)
        elif key is True:
            key = 'true'
        elif key is False:
            key = 'false'
        elif key is None:
            key = 'null'
        elif isinstance(key, integer_types):
            key = str(key)
        elif _use_decimal and isinstance(key, Decimal):
            key = str(key)
        elif _skipkeys:
            key = None
        else:
            raise TypeError("key " + repr(key) + " is not a string")
        return key

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (_indent * _current_indent_level)
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _PY3:
            iteritems = dct.items()
        else:
            iteritems = dct.iteritems()
        if _item_sort_key:
            items = []
            for k, v in dct.items():
                if not isinstance(k, string_types):
                    k = _stringify_key(k)
                    if k is None:
                        continue
                items.append((k, v))
            items.sort(key=_item_sort_key)
        else:
            items = iteritems
        for key, value in items:
            if not (_item_sort_key or isinstance(key, string_types)):
                key = _stringify_key(key)
                if key is None:
                    # _skipkeys must be True
                    continue
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if (isinstance(value, string_types) or
                (_PY3 and isinstance(value, binary_type))):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, integer_types):
                yield (str(value)
                       if (not _bigint_as_string or
                           (-1 << 53) < value < (1 << 53))
                           else ('"' + str(value) + '"'))
            elif isinstance(value, float):
                yield _floatstr(value)
            elif _use_decimal and isinstance(value, Decimal):
                yield str(value)
            else:
                if isinstance(value, list):
                    chunks = _iterencode_list(value, _current_indent_level)
                else:
                    _asdict = _namedtuple_as_object and getattr(value, '_asdict', None)
                    if _asdict and callable(_asdict):
                        chunks = _iterencode_dict(_asdict(),
                                                  _current_indent_level)
                    elif _tuple_as_array and isinstance(value, tuple):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance(value, dict):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (_indent * _current_indent_level)
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if (isinstance(o, string_types) or
            (_PY3 and isinstance(o, binary_type))):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, integer_types):
            yield (str(o)
                   if (not _bigint_as_string or
                       (-1 << 53) < o < (1 << 53))
                       else ('"' + str(o) + '"'))
        elif isinstance(o, float):
            yield _floatstr(o)
        elif isinstance(o, list):
            for chunk in _iterencode_list(o, _current_indent_level):
                yield chunk
        else:
            _asdict = _namedtuple_as_object and getattr(o, '_asdict', None)
            if _asdict and callable(_asdict):
                for chunk in _iterencode_dict(_asdict(), _current_indent_level):
                    yield chunk
            elif (_tuple_as_array and isinstance(o, tuple)):
                for chunk in _iterencode_list(o, _current_indent_level):
                    yield chunk
            elif isinstance(o, dict):
                for chunk in _iterencode_dict(o, _current_indent_level):
                    yield chunk
            elif _use_decimal and isinstance(o, Decimal):
                yield str(o)
            else:
                if markers is not None:
                    markerid = id(o)
                    if markerid in markers:
                        raise ValueError("Circular reference detected")
                    markers[markerid] = o
                o = _default(o)
                for chunk in _iterencode(o, _current_indent_level):
                    yield chunk
                if markers is not None:
                    del markers[markerid]

    return _iterencode

########NEW FILE########
__FILENAME__ = ordered_dict
"""Drop-in replacement for collections.OrderedDict by Raymond Hettinger

http://code.activestate.com/recipes/576693/

"""
from UserDict import DictMixin

# Modified from original to support Python 2.4, see
# http://code.google.com/p/simplejson/issues/detail?id=53
try:
    all
except NameError:
    def all(seq):
        for elem in seq:
            if not elem:
                return False
        return True

class OrderedDict(dict, DictMixin):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        # Modified from original to support Python 2.4, see
        # http://code.google.com/p/simplejson/issues/detail?id=53
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and \
                   all(p==q for p, q in  zip(self.items(), other.items()))
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = scanner
"""JSON token scanner
"""
import re
def _import_c_make_scanner():
    try:
        from simplejson._speedups import make_scanner
        return make_scanner
    except ImportError:
        return None
c_make_scanner = _import_c_make_scanner()

__all__ = ['make_scanner']

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))

def py_make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = NUMBER_RE.match
    encoding = context.encoding
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook
    object_pairs_hook = context.object_pairs_hook
    memo = context.memo

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return parse_string(string, idx + 1, encoding, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), encoding, strict,
                _scan_once, object_hook, object_pairs_hook, memo)
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration

    def scan_once(string, idx):
        try:
            return _scan_once(string, idx)
        finally:
            memo.clear()

    return scan_once

make_scanner = c_make_scanner or py_make_scanner

########NEW FILE########
__FILENAME__ = tool
r"""Command-line tool to validate and pretty-print JSON

Usage::

    $ echo '{"json":"obj"}' | python -m simplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -m simplejson.tool
    Expecting property name: line 1 column 2 (char 2)

"""
import sys
import simplejson as json

def main():
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'rb')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'rb')
        outfile = open(sys.argv[2], 'wb')
    else:
        raise SystemExit(sys.argv[0] + " [infile [outfile]]")
    try:
        obj = json.load(infile,
                        object_pairs_hook=json.OrderedDict,
                        use_decimal=True)
    except ValueError:
        raise SystemExit(sys.exc_info()[1])
    json.dump(obj, outfile, sort_keys=True, indent='    ', use_decimal=True)
    outfile.write('\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tests
import sys
import os

# parent folder holds libraries which needs to be included
sys.path.append(os.path.realpath('..'))

import simplejson as json
from simplejson import OrderedDict

import decimal
import unittest


class TestIssues(unittest.TestCase):

    def setUp(self):
        pass

    def test_ascii_issue_10(self):
        tmp_str = '{"tempstr":"\u2022"}'
        expected_output = '''{
  "tempstr": "\\u2022"
}'''
        obj = json.loads(tmp_str, object_pairs_hook=OrderedDict, parse_float=decimal.Decimal)
        tmp_str = json.dumps(obj, indent=2, ensure_ascii=True, sort_keys=False,
                    separators=(',', ': '),
                    use_decimal=True)
        self.assertEqual(tmp_str, expected_output)

    # issue 15
    def test_float_issue_15(self):
        tmp_str = '{"real":0.99}'
        expected_output = """{
  "real": 0.99
}"""
        obj = json.loads(tmp_str, object_pairs_hook=OrderedDict, parse_float=decimal.Decimal)
        tmp_str = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False,
                    separators=(',', ': '),
                    use_decimal=True)
        self.assertEqual(tmp_str, expected_output)

    # issue 16
    def test_float_issue_16_1(self):
        tmp_str = '{ "float": 1.0 }'
        obj = json.loads(tmp_str, object_pairs_hook=OrderedDict, parse_float=decimal.Decimal)
        self.assertEqual(obj['float'], 1.0)
        tmp_str = json.dumps(obj, indent=0, ensure_ascii=False, sort_keys=False,
                    separators=(',', ': '),
                    use_decimal=True)
        self.assertEqual(tmp_str.split('\n')[1], '"float": 1.0')

    # issue 16
    def test_float_issue_16_2(self):
        tmp_str = '{"test1":0.99, "test2":"1.99", "test3":1.00000000001, "test4":1.99, "test5":1, "test6":4.589999999999999999, "test7":1.0}'
        expected_output = """{
  "test1": 0.99,
  "test2": "1.99",
  "test3": 1.00000000001,
  "test4": 1.99,
  "test5": 1,
  "test6": 4.589999999999999999,
  "test7": 1.0
}"""
        obj = json.loads(tmp_str, object_pairs_hook=OrderedDict, parse_float=decimal.Decimal)
        tmp_str = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False,
                    separators=(',', ': '),
                    use_decimal=True)
        self.assertEqual(tmp_str, expected_output)

    def test_compress_feature(self):
        tmp_str = """{
  "real": 0.99
}"""
        expected_output = '{"real":0.99}'
        obj = json.loads(tmp_str, object_pairs_hook=OrderedDict, parse_float=decimal.Decimal)
        tmp_str = json.dumps(obj, ensure_ascii=False, sort_keys=False,
                    separators=(',', ':'),
                    use_decimal=True)
        self.assertEqual(tmp_str, expected_output)



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
