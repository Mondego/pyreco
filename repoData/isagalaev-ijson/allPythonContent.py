__FILENAME__ = python
'''
Pure-python parsing backend.
'''
from __future__ import unicode_literals
from decimal import Decimal
import re
from codecs import unicode_escape_decode, getreader

from ijson import common
from ijson.compat import chr


BUFSIZE = 16 * 1024
NONWS = re.compile(r'\S')
LEXTERM = re.compile(r'[^a-z0-9\.+-]')


class UnexpectedSymbol(common.JSONError):
    def __init__(self, symbol, reader):
        super(UnexpectedSymbol, self).__init__('Unexpected symbol "%s" at %d' % (symbol[0], reader.pos - len(symbol)))

class Lexer(object):
    '''
    JSON lexer. Supports iterator interface.
    '''
    def __init__(self, f, buf_size=BUFSIZE):
        self.f = getreader('utf-8')(f)
        self.buf_size = buf_size

    def __iter__(self):
        self.buffer = ''
        self.pos = 0
        return self

    def __next__(self):
        while True:
            match = NONWS.search(self.buffer, self.pos)
            if match:
                self.pos = match.start()
                char = self.buffer[self.pos]
                if 'a' <= char <= 'z' or '0' <= char <= '9' or char == '-':
                    return self.lexem()
                elif char == '"':
                    return self.stringlexem()
                else:
                    self.pos += 1
                    return char
            self.buffer = self.f.read(self.buf_size)
            self.pos = 0
            if not len(self.buffer):
                raise StopIteration
    next = __next__

    def lexem(self):
        current = self.pos
        while True:
            match = LEXTERM.search(self.buffer, current)
            if match:
                current = match.start()
                break
            else:
                current = len(self.buffer)
                self.buffer += self.f.read(self.buf_size)
                if len(self.buffer) == current:
                    break
        result = self.buffer[self.pos:current]
        self.pos = current
        if self.pos > self.buf_size:
            self.buffer = self.buffer[self.pos:]
            self.pos = 0
        return result

    def stringlexem(self):
        start = self.pos + 1
        while True:
            try:
                end = self.buffer.index('"', start)
                escpos = end - 1
                while self.buffer[escpos] == '\\':
                    escpos -= 1
                if (end - escpos) % 2 == 0:
                    start = end + 1
                else:
                    result = self.buffer[self.pos:end + 1]
                    self.pos = end + 1
                    return result
            except ValueError:
                old_len = len(self.buffer)
                self.buffer += self.f.read(self.buf_size)
                if len(self.buffer) == old_len:
                    raise common.IncompleteJSONError()

def unescape(s):
    start = 0
    while start < len(s):
        pos = s.find('\\', start)
        if pos == -1:
            yield s[start:]
            break
        yield s[start:pos]
        pos += 1
        esc = s[pos]
        if esc == 'b':
            yield '\b'
        elif esc == 'f':
            yield '\f'
        elif esc == 'n':
            yield '\n'
        elif esc == 'r':
            yield '\r'
        elif esc == 't':
            yield '\t'
        elif esc == 'u':
            yield chr(int(s[pos + 1:pos + 5], 16))
            pos += 4
        else:
            yield esc
        start = pos + 1

def parse_value(lexer, symbol=None):
    try:
        if symbol is None:
            symbol = next(lexer)
        if symbol == 'null':
            yield ('null', None)
        elif symbol == 'true':
            yield ('boolean', True)
        elif symbol == 'false':
            yield ('boolean', False)
        elif symbol == '[':
            for event in parse_array(lexer):
                yield event
        elif symbol == '{':
            for event in parse_object(lexer):
                yield event
        elif symbol[0] == '"':
            yield ('string', ''.join(unescape(symbol[1:-1])))
        else:
            try:
                number = Decimal(symbol) if '.' in symbol else int(symbol)
                yield ('number', number)
            except ValueError:
                raise UnexpectedSymbol(symbol, lexer)
    except StopIteration:
        raise common.IncompleteJSONError()

def parse_array(lexer):
    yield ('start_array', None)
    symbol = next(lexer)
    if symbol != ']':
        while True:
            for event in parse_value(lexer, symbol):
                yield event
            symbol = next(lexer)
            if symbol == ']':
                break
            if symbol != ',':
                raise UnexpectedSymbol(symbol, lexer)
            symbol = next(lexer)
    yield ('end_array', None)

def parse_object(lexer):
    yield ('start_map', None)
    symbol = next(lexer)
    if symbol != '}':
        while True:
            if symbol[0] != '"':
                raise UnexpectedSymbol(symbol, lexer)
            yield ('map_key', symbol[1:-1])
            symbol = next(lexer)
            if symbol != ':':
                raise UnexpectedSymbol(symbol, lexer)
            for event in parse_value(lexer):
                yield event
            symbol = next(lexer)
            if symbol == '}':
                break
            if symbol != ',':
                raise UnexpectedSymbol(symbol, lexer)
            symbol = next(lexer)
    yield ('end_map', None)

def basic_parse(file=None, buf_size=BUFSIZE):
    '''
    Iterator yielding unprefixed events.

    Parameters:

    - file: a readable file-like object with JSON input
    '''
    lexer = iter(Lexer(file, buf_size))
    for value in parse_value(lexer):
        yield value
    try:
        next(lexer)
    except StopIteration:
        pass
    else:
        raise common.JSONError('Additional data')

def parse(file):
    '''
    Backend-specific wrapper for ijson.common.parse.
    '''
    return common.parse(basic_parse(file))

def items(file, prefix):
    '''
    Backend-specific wrapper for ijson.common.items.
    '''
    return common.items(parse(file), prefix)

########NEW FILE########
__FILENAME__ = yajl
'''
Wrapper for YAJL C library version 1.x.
'''

from ctypes import Structure, c_uint, c_ubyte, c_int, c_long, c_double, \
                   c_void_p, c_char_p, CFUNCTYPE, POINTER, byref, string_at, cast , \
                   cdll, util, c_char
from decimal import Decimal

from ijson import common, backends
from ijson.compat import b2s


yajl = backends.find_yajl(1)

yajl.yajl_alloc.restype = POINTER(c_char)
yajl.yajl_get_error.restype = POINTER(c_char)

C_EMPTY = CFUNCTYPE(c_int, c_void_p)
C_INT = CFUNCTYPE(c_int, c_void_p, c_int)
C_LONG = CFUNCTYPE(c_int, c_void_p, c_long)
C_DOUBLE = CFUNCTYPE(c_int, c_void_p, c_double)
C_STR = CFUNCTYPE(c_int, c_void_p, POINTER(c_ubyte), c_uint)


def number(value):
    '''
    Helper function casting a string that represents any Javascript number
    into appropriate Python value: either int or Decimal.
    '''
    try:
        return int(value)
    except ValueError:
        return Decimal(value)

_callback_data = [
    # Mapping of JSON parser events to callback C types and value converters.
    # Used to define the Callbacks structure and actual callback functions
    # inside the parse function.
    ('null', C_EMPTY, lambda: None),
    ('boolean', C_INT, lambda v: bool(v)),
    # "integer" and "double" aren't actually yielded by yajl since "number"
    # takes precedence if defined
    ('integer', C_LONG, lambda v, l: int(string_at(v, l))),
    ('double', C_DOUBLE, lambda v, l: float(string_at(v, l))),
    ('number', C_STR, lambda v, l: number(b2s(string_at(v, l)))),
    ('string', C_STR, lambda v, l: string_at(v, l).decode('utf-8')),
    ('start_map', C_EMPTY, lambda: None),
    ('map_key', C_STR, lambda v, l: b2s(string_at(v, l))),
    ('end_map', C_EMPTY, lambda: None),
    ('start_array', C_EMPTY, lambda: None),
    ('end_array', C_EMPTY, lambda: None),
]

class Callbacks(Structure):
    _fields_ = [(name, type) for name, type, func in _callback_data]

class Config(Structure):
    _fields_ = [
        ("allowComments", c_uint),
        ("checkUTF8", c_uint)
    ]

YAJL_OK = 0
YAJL_CANCELLED = 1
YAJL_INSUFFICIENT_DATA = 2
YAJL_ERROR = 3


def basic_parse(f, allow_comments=False, check_utf8=False, buf_size=64 * 1024):
    '''
    Iterator yielding unprefixed events.

    Parameters:

    - f: a readable file-like object with JSON input
    - allow_comments: tells parser to allow comments in JSON input
    - check_utf8: if True, parser will cause an error if input is invalid utf-8
    - buf_size: a size of an input buffer
    '''
    events = []

    def callback(event, func_type, func):
        def c_callback(context, *args):
            events.append((event, func(*args)))
            return 1
        return func_type(c_callback)

    callbacks = Callbacks(*[callback(*data) for data in _callback_data])
    config = Config(allow_comments, check_utf8)
    handle = yajl.yajl_alloc(byref(callbacks), byref(config), None, None)
    try:
        while True:
            buffer = f.read(buf_size)
            if buffer:
                result = yajl.yajl_parse(handle, buffer, len(buffer))
            else:
                result = yajl.yajl_parse_complete(handle)
            if result == YAJL_ERROR:
                perror = yajl.yajl_get_error(handle, 1, buffer, len(buffer))
                error = cast(perror, c_char_p).value
                yajl.yajl_free_error(handle, perror)
                raise common.JSONError(error)
            if not buffer and not events:
                if result == YAJL_INSUFFICIENT_DATA:
                    raise common.IncompleteJSONError()
                break

            for event in events:
                yield event
            events = []
    finally:
        yajl.yajl_free(handle)

def parse(file, **kwargs):
    '''
    Backend-specific wrapper for ijson.common.parse.
    '''
    return common.parse(basic_parse(file, **kwargs))

def items(file, prefix):
    '''
    Backend-specific wrapper for ijson.common.items.
    '''
    return common.items(parse(file), prefix)

########NEW FILE########
__FILENAME__ = yajl2
'''
Wrapper for YAJL C library version 2.x.
'''

from ctypes import Structure, c_uint, c_ubyte, c_int, c_long, c_double, \
                   c_void_p, c_char_p, CFUNCTYPE, POINTER, byref, string_at, cast , \
                   cdll, util, c_char
from decimal import Decimal

from ijson import common, backends
from ijson.compat import b2s


yajl = backends.find_yajl(2)

yajl.yajl_alloc.restype = POINTER(c_char)
yajl.yajl_get_error.restype = POINTER(c_char)

C_EMPTY = CFUNCTYPE(c_int, c_void_p)
C_INT = CFUNCTYPE(c_int, c_void_p, c_int)
C_LONG = CFUNCTYPE(c_int, c_void_p, c_long)
C_DOUBLE = CFUNCTYPE(c_int, c_void_p, c_double)
C_STR = CFUNCTYPE(c_int, c_void_p, POINTER(c_ubyte), c_uint)


def number(value):
    '''
    Helper function casting a string that represents any Javascript number
    into appropriate Python value: either int or Decimal.
    '''
    try:
        return int(value)
    except ValueError:
        return Decimal(value)

_callback_data = [
    # Mapping of JSON parser events to callback C types and value converters.
    # Used to define the Callbacks structure and actual callback functions
    # inside the parse function.
    ('null', C_EMPTY, lambda: None),
    ('boolean', C_INT, lambda v: bool(v)),
    # "integer" and "double" aren't actually yielded by yajl since "number"
    # takes precedence if defined
    ('integer', C_LONG, lambda v, l: int(string_at(v, l))),
    ('double', C_DOUBLE, lambda v, l: float(string_at(v, l))),
    ('number', C_STR, lambda v, l: number(b2s(string_at(v, l)))),
    ('string', C_STR, lambda v, l: string_at(v, l).decode('utf-8')),
    ('start_map', C_EMPTY, lambda: None),
    ('map_key', C_STR, lambda v, l: b2s(string_at(v, l))),
    ('end_map', C_EMPTY, lambda: None),
    ('start_array', C_EMPTY, lambda: None),
    ('end_array', C_EMPTY, lambda: None),
]

class Callbacks(Structure):
    _fields_ = [(name, type) for name, type, func in _callback_data]

YAJL_OK = 0
YAJL_CANCELLED = 1
YAJL_INSUFFICIENT_DATA = 2
YAJL_ERROR = 3

# constants defined in yajl_parse.h
YAJL_ALLOW_COMMENTS = 1
YAJL_MULTIPLE_VALUES = 8


def basic_parse(f, allow_comments=False, buf_size=64 * 1024,
                multiple_values=False):
    '''
    Iterator yielding unprefixed events.

    Parameters:

    - f: a readable file-like object with JSON input
    - allow_comments: tells parser to allow comments in JSON input
    - buf_size: a size of an input buffer
    - multiple_values: allows the parser to parse multiple JSON objects
    '''
    events = []

    def callback(event, func_type, func):
        def c_callback(context, *args):
            events.append((event, func(*args)))
            return 1
        return func_type(c_callback)

    callbacks = Callbacks(*[callback(*data) for data in _callback_data])
    handle = yajl.yajl_alloc(byref(callbacks), None, None)
    if allow_comments:
        yajl.yajl_config(handle, YAJL_ALLOW_COMMENTS, 1)
    if multiple_values:
        yajl.yajl_config(handle, YAJL_MULTIPLE_VALUES, 1)
    try:
        while True:
            buffer = f.read(buf_size)
            if buffer:
                result = yajl.yajl_parse(handle, buffer, len(buffer))
            else:
                result = yajl.yajl_complete_parse(handle)
            if result == YAJL_ERROR:
                perror = yajl.yajl_get_error(handle, 1, buffer, len(buffer))
                error = cast(perror, c_char_p).value
                yajl.yajl_free_error(handle, perror)
                raise common.JSONError(error)
            if not buffer and not events:
                if result == YAJL_INSUFFICIENT_DATA:
                    raise common.IncompleteJSONError()
                break

            for event in events:
                yield event
            events = []
    finally:
        yajl.yajl_free(handle)

def parse(file, **kwargs):
    '''
    Backend-specific wrapper for ijson.common.parse.
    '''
    return common.parse(basic_parse(file, **kwargs))

def items(file, prefix):
    '''
    Backend-specific wrapper for ijson.common.items.
    '''
    return common.items(parse(file), prefix)

########NEW FILE########
__FILENAME__ = common
'''
Backend independent higher level interfaces, common exceptions.
'''

class JSONError(Exception):
    '''
    Base exception for all parsing errors.
    '''
    pass

class IncompleteJSONError(JSONError):
    '''
    Raised when the parser expects data and it's not available. May be
    caused by malformed syntax or a broken source stream.
    '''
    def __init__(self):
        super(IncompleteJSONError, self).__init__('Incomplete or empty JSON data')

def parse(basic_events):
    '''
    An iterator returning parsing events with the information about their location
    with the JSON object tree. Events are tuples ``(prefix, type, value)``.

    Available types and values are:

    ('null', None)
    ('boolean', <True or False>)
    ('number', <int or Decimal>)
    ('string', <unicode>)
    ('map_key', <str>)
    ('start_map', None)
    ('end_map', None)
    ('start_array', None)
    ('end_array', None)

    Prefixes represent the path to the nested elements from the root of the JSON
    document. For example, given this document::

        {
          "array": [1, 2],
          "map": {
            "key": "value"
          }
        }

    the parser would yield events:

      ('', 'start_map', None)
      ('', 'map_key', 'array')
      ('array', 'start_array', None)
      ('array.item', 'number', 1)
      ('array.item', 'number', 2)
      ('array', 'end_array', None)
      ('', 'map_key', 'map')
      ('map', 'start_map', None)
      ('map', 'map_key', 'key')
      ('map.key', 'string', u'value')
      ('map', 'end_map', None)
      ('', 'end_map', None)

    '''
    path = []
    for event, value in basic_events:
        if event == 'map_key':
            prefix = '.'.join(path[:-1])
            path[-1] = value
        elif event == 'start_map':
            prefix = '.'.join(path)
            path.append(None)
        elif event == 'end_map':
            path.pop()
            prefix = '.'.join(path)
        elif event == 'start_array':
            prefix = '.'.join(path)
            path.append('item')
        elif event == 'end_array':
            path.pop()
            prefix = '.'.join(path)
        else: # any scalar value
            prefix = '.'.join(path)

        yield prefix, event, value


class ObjectBuilder(object):
    '''
    Incrementally builds an object from JSON parser events. Events are passed
    into the `event` function that accepts two parameters: event type and
    value. The object being built is available at any time from the `value`
    attribute.

    Example::

        from StringIO import StringIO
        from ijson.parse import basic_parse
        from ijson.utils import ObjectBuilder

        builder = ObjectBuilder()
        f = StringIO('{"key": "value"})
        for event, value in basic_parse(f):
            builder.event(event, value)
        print builder.value

    '''
    def __init__(self):
        def initial_set(value):
            self.value = value
        self.containers = [initial_set]

    def event(self, event, value):
        if event == 'map_key':
            self.key = value
        elif event == 'start_map':
            map = {}
            self.containers[-1](map)
            def setter(value):
                map[self.key] = value
            self.containers.append(setter)
        elif event == 'start_array':
            array = []
            self.containers[-1](array)
            self.containers.append(array.append)
        elif event == 'end_array' or event == 'end_map':
            self.containers.pop()
        else:
            self.containers[-1](value)

def items(prefixed_events, prefix):
    '''
    An iterator returning native Python objects constructed from the events
    under a given prefix.
    '''
    prefixed_events = iter(prefixed_events)
    try:
        while True:
            current, event, value = next(prefixed_events)
            if current == prefix:
                if event in ('start_map', 'start_array'):
                    builder = ObjectBuilder()
                    end_event = event.replace('start', 'end')
                    while (current, event) != (prefix, end_event):
                        builder.event(event, value)
                        current, event, value = next(prefixed_events)
                    yield builder.value
                else:
                    yield value
    except StopIteration:
        pass

########NEW FILE########
__FILENAME__ = compat
'''
Python2/Python3 compatibility utilities.
'''

import sys


IS_PY2 = sys.version_info[0] < 3


if IS_PY2:
    b2s = lambda s: s
    chr = unichr
else:
    def b2s(b):
        return b.decode('utf-8')
    chr = chr

########NEW FILE########
__FILENAME__ = utils
# -*- coding:utf-8 -*-
from functools import wraps


def coroutine(func):
    '''
    Wraps a generator which intended to be used as a pure coroutine by
    .send()ing it values. The only thing that the wrapper does is calling
    .next() for the first time which is required by Python generator protocol.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        g = func(*args, **kwargs)
        next(g)
        return g
    return wrapper

@coroutine
def foreach(coroutine_func):
    '''
    Dispatches each JSON array item to a handler coroutine. A coroutine is
    created anew for each item by calling `coroutine_func` callable. The
    resulting coroutine should accept value in the form of tuple of values
    generated by rich JSON parser: (prefix, event, value).

    First event received by foreach should be a "start_array" event.
    '''
    g = None
    base, event, value = yield
    if event != 'start_array':
        raise Exception('foreach requires "start_array" as the first event, got %s' % repr((base, event, value)))
    START_EVENTS = set(['start_map', 'start_array', 'null', 'boolean', 'number', 'string'])
    itemprefix = base + '.item' if base else 'item'
    while True:
        prefix, event, value = yield
        if prefix == itemprefix and event in START_EVENTS:
            g = coroutine_func()
        if (prefix, event) != (base, 'end_array'):
            g.send((prefix, event, value))

@coroutine
def dispatcher(targets):
    '''
    Dispatches JSON parser events into several handlers depending on event
    prefixes.

    Accepts a list of tuples (base_prefix, coroutine). A coroutine then
    receives all the events with prefixes starting with its base_prefix.
    '''
    while True:
        prefix, event, value = yield
        for base, target in targets:
            if prefix.startswith(base):
                target.send((prefix, event, value))
                break

########NEW FILE########
__FILENAME__ = tests
# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import unittest
from io import BytesIO
from decimal import Decimal
import threading
from importlib import import_module

from ijson import common
from ijson.backends.python import basic_parse
from ijson.compat import IS_PY2


JSON = b'''
{
  "docs": [
    {
      "string": "\\u0441\\u0442\\u0440\\u043e\\u043a\\u0430 - \xd1\x82\xd0\xb5\xd1\x81\xd1\x82",
      "null": null,
      "boolean": false,
      "integer": 0,
      "double": 0.5,
      "exponent": 1.0e+2,
      "long": 10000000000
    },
    {
      "meta": [[1], {}]
    },
    {
      "meta": {"key": "value"}
    },
    {
      "meta": null
    }
  ]
}
'''
SCALAR_JSON = b'0'
EMPTY_JSON = b''
INVALID_JSON = b'{"key": "value",}'
INCOMPLETE_JSON = b'"test'
STRINGS_JSON = br'''
{
    "str1": "",
    "str2": "\"",
    "str3": "\\",
    "str4": "\\\\"
}
'''

class Parse(object):
    '''
    Base class for parsing tests that is used to create test cases for each
    available backends.
    '''
    def test_basic_parse(self):
        events = list(self.backend.basic_parse(BytesIO(JSON)))
        reference = [
            ('start_map', None),
                ('map_key', 'docs'),
                ('start_array', None),
                    ('start_map', None),
                        ('map_key', 'string'),
                        ('string', 'строка - тест'),
                        ('map_key', 'null'),
                        ('null', None),
                        ('map_key', 'boolean'),
                        ('boolean', False),
                        ('map_key', 'integer'),
                        ('number', 0),
                        ('map_key', 'double'),
                        ('number', Decimal('0.5')),
                        ('map_key', 'exponent'),
                        ('number', Decimal('100')),
                        ('map_key', 'long'),
                        ('number', 10000000000),
                    ('end_map', None),
                    ('start_map', None),
                        ('map_key', 'meta'),
                        ('start_array', None),
                            ('start_array', None),
                                ('number', 1),
                            ('end_array', None),
                            ('start_map', None),
                            ('end_map', None),
                        ('end_array', None),
                    ('end_map', None),
                    ('start_map', None),
                        ('map_key', 'meta'),
                        ('start_map', None),
                            ('map_key', 'key'),
                            ('string', 'value'),
                        ('end_map', None),
                    ('end_map', None),
                    ('start_map', None),
                        ('map_key', 'meta'),
                        ('null', None),
                    ('end_map', None),
                ('end_array', None),
            ('end_map', None),
        ]
        for e, r in zip(events, reference):
            self.assertEqual(e, r)

    def test_basic_parse_threaded(self):
        thread = threading.Thread(target=self.test_basic_parse)
        thread.start()
        thread.join()

    def test_scalar(self):
        events = list(self.backend.basic_parse(BytesIO(SCALAR_JSON)))
        self.assertEqual(events, [('number', 0)])

    def test_strings(self):
        events = list(self.backend.basic_parse(BytesIO(STRINGS_JSON)))
        strings = [value for event, value in events if event == 'string']
        self.assertEqual(strings, ['', '"', '\\', '\\\\'])

    def test_empty(self):
        self.assertRaises(
            common.IncompleteJSONError,
            lambda: list(self.backend.basic_parse(BytesIO(EMPTY_JSON))),
        )

    def test_incomplete(self):
        self.assertRaises(
            common.IncompleteJSONError,
            lambda: list(self.backend.basic_parse(BytesIO(INCOMPLETE_JSON))),
        )

    def test_invalid(self):
        self.assertRaises(
            common.JSONError,
            lambda: list(self.backend.basic_parse(BytesIO(INVALID_JSON))),
        )

    def test_utf8_split(self):
        buf_size = JSON.index(b'\xd1') + 1
        try:
            events = list(self.backend.basic_parse(BytesIO(JSON), buf_size=buf_size))
        except UnicodeDecodeError:
            self.fail('UnicodeDecodeError raised')

    def test_lazy(self):
        # shouldn't fail since iterator is not exhausted
        self.backend.basic_parse(BytesIO(INVALID_JSON))
        self.assertTrue(True)

# Generating real TestCase classes for each importable backend
for name in ['python', 'yajl', 'yajl2']:
    try:
        classname = '%sParse' % name.capitalize()
        if IS_PY2:
            classname = classname.encode('ascii')
        locals()[classname] = type(
            classname,
            (unittest.TestCase, Parse),
            {'backend': import_module('ijson.backends.%s' % name)},
        )
    except ImportError:
        pass

class Common(unittest.TestCase):
    '''
    Backend independent tests. They all use basic_parse imported explicitly from
    the python backend to generate parsing events.
    '''
    def test_object_builder(self):
        builder = common.ObjectBuilder()
        for event, value in basic_parse(BytesIO(JSON)):
            builder.event(event, value)
        self.assertEqual(builder.value, {
            'docs': [
                {
                   'string': 'строка - тест',
                   'null': None,
                   'boolean': False,
                   'integer': 0,
                   'double': Decimal('0.5'),
                   'exponent': Decimal('100'),
                   'long': 10000000000,
                },
                {
                    'meta': [[1], {}],
                },
                {
                    'meta': {'key': 'value'},
                },
                {
                    'meta': None,
                },
            ],
        })

    def test_scalar_builder(self):
        builder = common.ObjectBuilder()
        for event, value in basic_parse(BytesIO(SCALAR_JSON)):
            builder.event(event, value)
        self.assertEqual(builder.value, 0)

    def test_parse(self):
        events = common.parse(basic_parse(BytesIO(JSON)))
        events = [value
            for prefix, event, value in events
            if prefix == 'docs.item.meta.item.item'
        ]
        self.assertEqual(events, [1])

    def test_items(self):
        events = basic_parse(BytesIO(JSON))
        meta = list(common.items(common.parse(events), 'docs.item.meta'))
        self.assertEqual(meta, [
            [[1], {}],
            {'key': 'value'},
            None,
        ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
