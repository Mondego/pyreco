__FILENAME__ = compat
# #!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

import sys
import types

PY3 = sys.version_info[0] == 3
if PY3:  # pragma: no cover
    text_type = str
    byte_type = bytes
    import io
    StringIO = io.BytesIO
    basestring = (str, bytes)

    class BaseClass(object):
        def __repr__(self):
            return self.__str__()
else:  # pragma: no cover
    text_type = unicode
    byte_type = str
    import StringIO
    StringIO = StringIO.StringIO
    basestring = basestring


class BaseClass(object):
    def __repr__(self):
        ret = self.__str__()
        if PY3:  # pragma: no cover
            return ret
        else:
            return ret.encode('utf-8')


try:  # pragma: no cover
    from urllib.parse import urlsplit, urlunsplit, parse_qs, quote, quote_plus, unquote
    unquote_utf8 = unquote
except ImportError:  # pragma: no cover
    from urlparse import urlsplit, urlunsplit, parse_qs, unquote
    from urllib import quote, quote_plus
    def unquote_utf8(qs):
        if isinstance(qs, text_type):
            qs = qs.encode('utf-8')
        s = unquote(qs)
        if isinstance(s, byte_type):
            return s.decode("utf-8")
        else:
            return s


try:  # pragma: no cover
    from http.server import BaseHTTPRequestHandler
except ImportError:  # pragma: no cover
    from BaseHTTPServer import BaseHTTPRequestHandler


ClassTypes = (type,)
if not PY3:  # pragma: no cover
    ClassTypes = (type, types.ClassType)


__all__ = [
    'PY3',
    'StringIO',
    'text_type',
    'byte_type',
    'BaseClass',
    'BaseHTTPRequestHandler',
    'quote',
    'quote_plus',
    'urlunsplit',
    'urlsplit',
    'parse_qs',
    'ClassTypes',
]

########NEW FILE########
__FILENAME__ = core
# #!/usr/bin/env python
# -*- coding: utf-8 -*-
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

import re
import codecs
import inspect
import socket
import functools
import itertools
import warnings
import logging
import traceback
import json
import contextlib


from .compat import (
    PY3,
    StringIO,
    text_type,
    BaseClass,
    BaseHTTPRequestHandler,
    quote,
    quote_plus,
    urlunsplit,
    urlsplit,
    parse_qs,
    unquote,
    unquote_utf8,
    ClassTypes,
    basestring
)
from .http import (
    STATUSES,
    HttpBaseClass,
    parse_requestline,
    last_requestline,
)

from .utils import (
    utf8,
    decode_utf8,
)

from .errors import HTTPrettyError

from datetime import datetime
from datetime import timedelta
from errno import EAGAIN

old_socket = socket.socket
old_create_connection = socket.create_connection
old_gethostbyname = socket.gethostbyname
old_gethostname = socket.gethostname
old_getaddrinfo = socket.getaddrinfo
old_socksocket = None
old_ssl_wrap_socket = None
old_sslwrap_simple = None
old_sslsocket = None

if PY3:  # pragma: no cover
    basestring = (bytes, str)
try:  # pragma: no cover
    import socks
    old_socksocket = socks.socksocket
except ImportError:
    socks = None

try:  # pragma: no cover
    import ssl
    old_ssl_wrap_socket = ssl.wrap_socket
    if not PY3:
        old_sslwrap_simple = ssl.sslwrap_simple
    old_sslsocket = ssl.SSLSocket
except ImportError:  # pragma: no cover
    ssl = None


POTENTIAL_HTTP_PORTS = set([80, 443])
DEFAULT_HTTP_PORTS = tuple(POTENTIAL_HTTP_PORTS)


class HTTPrettyRequest(BaseHTTPRequestHandler, BaseClass):
    """Represents a HTTP request. It takes a valid multi-line, `\r\n`
    separated string with HTTP headers and parse them out using the
    internal `parse_request` method.

    It also replaces the `rfile` and `wfile` attributes with StringIO
    instances so that we garantee that it won't make any I/O, neighter
    for writing nor reading.

    It has some convenience attributes:

    `headers` -> a mimetype object that can be cast into a dictionary,
    contains all the request headers

    `method` -> the HTTP method used in this request

    `querystring` -> a dictionary containing lists with the
    attributes. Please notice that if you need a single value from a
    query string you will need to get it manually like:

    ```python
    >>> request.querystring
    {'name': ['Gabriel Falcao']}
    >>> print request.querystring['name'][0]
    ```

    `parsed_body` -> a dictionary containing parsed request body or
    None if HTTPrettyRequest doesn't know how to parse it.  It
    currently supports parsing body data that was sent under the
    `content-type` headers values: 'application/json' or
    'application/x-www-form-urlencoded'
    """
    def __init__(self, headers, body=''):
        # first of all, lets make sure that if headers or body are
        # unicode strings, it must be converted into a utf-8 encoded
        # byte string
        self.raw_headers = utf8(headers.strip())
        self.body = utf8(body)

        # Now let's concatenate the headers with the body, and create
        # `rfile` based on it
        self.rfile = StringIO(b'\r\n\r\n'.join([self.raw_headers, self.body]))
        self.wfile = StringIO()  # Creating `wfile` as an empty
                                 # StringIO, just to avoid any real
                                 # I/O calls

        # parsing the request line preemptively
        self.raw_requestline = self.rfile.readline()

        # initiating the error attributes with None
        self.error_code = None
        self.error_message = None

        # Parse the request based on the attributes above
        self.parse_request()

        # making the HTTP method string available as the command
        self.method = self.command

        # Now 2 convenient attributes for the HTTPretty API:

        # `querystring` holds a dictionary with the parsed query string
        try:
            self.path = self.path.encode('iso-8859-1')
        except UnicodeDecodeError:
            pass
        self.path = decode_utf8(self.path)

        qstring = self.path.split("?", 1)[-1]
        self.querystring = self.parse_querystring(qstring)

        # And the body will be attempted to be parsed as
        # `application/json` or `application/x-www-form-urlencoded`
        self.parsed_body = self.parse_request_body(self.body)

    def __str__(self):
        return '<HTTPrettyRequest("{0}", total_headers={1}, body_length={2})>'.format(
            self.headers.get('content-type', ''),
            len(self.headers),
            len(self.body),
        )

    def parse_querystring(self, qs):
        expanded = unquote_utf8(qs)
        parsed = parse_qs(expanded)
        result = {}
        for k in parsed:
            result[k] = list(map(decode_utf8, parsed[k]))

        return result

    def parse_request_body(self, body):
        """ Attempt to parse the post based on the content-type passed. Return the regular body if not """

        PARSING_FUNCTIONS = {
            'application/json': json.loads,
            'text/json': json.loads,
            'application/x-www-form-urlencoded': self.parse_querystring,
        }
        FALLBACK_FUNCTION = lambda x: x

        content_type = self.headers.get('content-type', '')

        do_parse = PARSING_FUNCTIONS.get(content_type, FALLBACK_FUNCTION)
        try:
            body = decode_utf8(body)
            return do_parse(body)
        except:
            return body


class EmptyRequestHeaders(dict):
    pass


class HTTPrettyRequestEmpty(object):
    body = ''
    headers = EmptyRequestHeaders()


class FakeSockFile(StringIO):
    pass


class FakeSSLSocket(object):
    def __init__(self, sock, *args, **kw):
        self._httpretty_sock = sock

    def __getattr__(self, attr):
        return getattr(self._httpretty_sock, attr)


class fakesock(object):
    class socket(object):
        _entry = None
        debuglevel = 0
        _sent_data = []

        def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM,
                     protocol=0):
            self.setsockopt(family, type, protocol)
            self.truesock = old_socket(family, type, protocol)
            self._closed = True
            self.fd = FakeSockFile()
            self.timeout = socket._GLOBAL_DEFAULT_TIMEOUT
            self._sock = self
            self.is_http = False
            self._bufsize = 16

        def getpeercert(self, *a, **kw):
            now = datetime.now()
            shift = now + timedelta(days=30 * 12)
            return {
                'notAfter': shift.strftime('%b %d %H:%M:%S GMT'),
                'subjectAltName': (
                    ('DNS', '*%s' % self._host),
                    ('DNS', self._host),
                    ('DNS', '*'),
                ),
                'subject': (
                    (
                        ('organizationName', '*.%s' % self._host),
                    ),
                    (
                        ('organizationalUnitName',
                         'Domain Control Validated'),
                    ),
                    (
                        ('commonName', '*.%s' % self._host),
                    ),
                ),
            }

        def ssl(self, sock, *args, **kw):
            return sock

        def setsockopt(self, family, type, protocol):
            self.family = family
            self.protocol = protocol
            self.type = type

        def connect(self, address):
            self._address = (self._host, self._port) = address
            self._closed = False
            self.is_http = self._port in POTENTIAL_HTTP_PORTS

            if not self.is_http:
                self.truesock.connect(self._address)

        def close(self):
            if not (self.is_http and self._closed):
                self.truesock.close()
            self._closed = True

        def makefile(self, mode='r', bufsize=-1):
            """Returns this fake socket's own StringIO buffer.

            If there is an entry associated with the socket, the file
            descriptor gets filled in with the entry data before being
            returned.
            """
            self._mode = mode
            self._bufsize = bufsize

            if self._entry:
                self._entry.fill_filekind(self.fd)

            return self.fd

        def real_sendall(self, data, *args, **kw):
            """Sends data to the remote server. This method is called
            when HTTPretty identifies that someone is trying to send
            non-http data.

            The received bytes are written in this socket's StringIO
            buffer so that HTTPretty can return it accordingly when
            necessary.
            """
            if self.is_http:  # no need to connect if `self.is_http` is
                              # False because self.connect already did
                              # that
                self.truesock.connect(self._address)

            self.truesock.settimeout(0)
            self.truesock.sendall(data, *args, **kw)

            should_continue = True
            while should_continue:
                try:
                    received = self.truesock.recv(self._bufsize)
                    self.fd.write(received)
                    should_continue = len(received) > 0

                except socket.error as e:
                    if e.errno == EAGAIN:
                        continue
                    break

            self.fd.seek(0)

        def sendall(self, data, *args, **kw):
            self._sent_data.append(data)

            try:
                requestline, _ = data.split(b'\r\n', 1)
                method, path, version = parse_requestline(decode_utf8(requestline))
                is_parsing_headers = True
            except ValueError:
                is_parsing_headers = False

                if not self._entry:
                    # If the previous request wasn't mocked, don't mock the subsequent sending of data
                    return self.real_sendall(data, *args, **kw)

            self.fd.seek(0)

            if not is_parsing_headers:
                if len(self._sent_data) > 1:
                    headers = utf8(last_requestline(self._sent_data))
                    meta = self._entry.request.headers
                    body = utf8(self._sent_data[-1])
                    if meta.get('transfer-encoding', '') == 'chunked':
                        if not body.isdigit() and body != b'\r\n' and body != b'0\r\n\r\n':
                            self._entry.request.body += body
                    else:
                        self._entry.request.body += body

                    httpretty.historify_request(headers, body, False)
                    return

            # path might come with
            s = urlsplit(path)
            POTENTIAL_HTTP_PORTS.add(int(s.port or 80))
            headers, body = list(map(utf8, data.split(b'\r\n\r\n', 1)))

            request = httpretty.historify_request(headers, body)

            info = URIInfo(hostname=self._host, port=self._port,
                           path=s.path,
                           query=s.query,
                           last_request=request)

            matcher, entries = httpretty.match_uriinfo(info)

            if not entries:
                self._entry = None
                self.real_sendall(data)
                return

            self._entry = matcher.get_next_entry(method, info, request)

        def debug(self, func, *a, **kw):
            if self.is_http:
                frame = inspect.stack()[0][0]
                lines = list(map(utf8, traceback.format_stack(frame)))

                message = [
                    "HTTPretty intercepted and unexpected socket method call.",
                    ("Please open an issue at "
                     "'https://github.com/gabrielfalcao/HTTPretty/issues'"),
                    "And paste the following traceback:\n",
                    "".join(decode_utf8(lines)),
                ]
                raise RuntimeError("\n".join(message))
            return func(*a, **kw)

        def settimeout(self, new_timeout):
            self.timeout = new_timeout

        def send(self, *args, **kwargs):
            return self.debug(self.truesock.send, *args, **kwargs)

        def sendto(self, *args, **kwargs):
            return self.debug(self.truesock.sendto, *args, **kwargs)

        def recvfrom_into(self, *args, **kwargs):
            return self.debug(self.truesock.recvfrom_into, *args, **kwargs)

        def recv_into(self, *args, **kwargs):
            return self.debug(self.truesock.recv_into, *args, **kwargs)

        def recvfrom(self, *args, **kwargs):
            return self.debug(self.truesock.recvfrom, *args, **kwargs)

        def recv(self, *args, **kwargs):
            return self.debug(self.truesock.recv, *args, **kwargs)

        def __getattr__(self, name):
            return getattr(self.truesock, name)


def fake_wrap_socket(s, *args, **kw):
    return s


def create_fake_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    s = fakesock.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
        s.settimeout(timeout)
    if source_address:
        s.bind(source_address)
    s.connect(address)
    return s


def fake_gethostbyname(host):
    return '127.0.0.1'


def fake_gethostname():
    return 'localhost'


def fake_getaddrinfo(
        host, port, family=None, socktype=None, proto=None, flags=None):
    return [(2, 1, 6, '', (host, port))]


class Entry(BaseClass):
    def __init__(self, method, uri, body,
                 adding_headers=None,
                 forcing_headers=None,
                 status=200,
                 streaming=False,
                 **headers):

        self.method = method
        self.uri = uri
        self.info = None
        self.request = None

        self.body_is_callable = False
        if hasattr(body, "__call__"):
            self.callable_body = body
            self.body = None
            self.body_is_callable = True
        elif isinstance(body, text_type):
            self.body = utf8(body)
        else:
            self.body = body

        self.streaming = streaming
        if not streaming and not self.body_is_callable:
            self.body_length = len(self.body or '')
        else:
            self.body_length = 0

        self.adding_headers = adding_headers or {}
        self.forcing_headers = forcing_headers or {}
        self.status = int(status)

        for k, v in headers.items():
            name = "-".join(k.split("_")).title()
            self.adding_headers[name] = v

        self.validate()

    def validate(self):
        content_length_keys = 'Content-Length', 'content-length'
        for key in content_length_keys:
            got = self.adding_headers.get(
                key, self.forcing_headers.get(key, None))

            if got is None:
                continue

            try:
                igot = int(got)
            except ValueError:
                warnings.warn(
                    'HTTPretty got to register the Content-Length header ' \
                    'with "%r" which is not a number' % got,
                )

            if igot > self.body_length:
                raise HTTPrettyError(
                    'HTTPretty got inconsistent parameters. The header ' \
                    'Content-Length you registered expects size "%d" but ' \
                    'the body you registered for that has actually length ' \
                    '"%d".' % (
                        igot, self.body_length,
                    )
                )

    def __str__(self):
        return r'<Entry %s %s getting %d>' % (
            self.method, self.uri, self.status)

    def normalize_headers(self, headers):
        new = {}
        for k in headers:
            new_k = '-'.join([s.lower() for s in k.split('-')])
            new[new_k] = headers[k]

        return new

    def fill_filekind(self, fk):
        now = datetime.utcnow()

        headers = {
            'status': self.status,
            'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'server': 'Python/HTTPretty',
            'connection': 'close',
        }

        if self.forcing_headers:
            headers = self.forcing_headers

        if self.adding_headers:
            headers.update(self.normalize_headers(self.adding_headers))

        headers = self.normalize_headers(headers)
        status = headers.get('status', self.status)
        if self.body_is_callable:
            status, headers, self.body = self.callable_body(self.request, self.info.full_url(), headers)
            headers.update({
                'content-length': len(self.body)
            })

        string_list = [
            'HTTP/1.1 %d %s' % (status, STATUSES[status]),
        ]

        if 'date' in headers:
            string_list.append('date: %s' % headers.pop('date'))

        if not self.forcing_headers:
            content_type = headers.pop('content-type',
                                       'text/plain; charset=utf-8')

            content_length = headers.pop('content-length', self.body_length)

            string_list.append('content-type: %s' % content_type)
            if not self.streaming:
                string_list.append('content-length: %s' % content_length)

            string_list.append('server: %s' % headers.pop('server'))

        for k, v in headers.items():
            string_list.append(
                '{0}: {1}'.format(k, v),
            )

        for item in string_list:
            fk.write(utf8(item) + b'\n')

        fk.write(b'\r\n')

        if self.streaming:
            self.body, body = itertools.tee(self.body)
            for chunk in body:
                fk.write(utf8(chunk))
        else:
            fk.write(utf8(self.body))

        fk.seek(0)


def url_fix(s, charset='utf-8'):
    scheme, netloc, path, querystring, fragment = urlsplit(s)
    path = quote(path, b'/%')
    querystring = quote_plus(querystring, b':&=')
    return urlunsplit((scheme, netloc, path, querystring, fragment))


class URIInfo(BaseClass):
    def __init__(self,
                 username='',
                 password='',
                 hostname='',
                 port=80,
                 path='/',
                 query='',
                 fragment='',
                 scheme='',
                 last_request=None):

        self.username = username or ''
        self.password = password or ''
        self.hostname = hostname or ''

        if port:
            port = int(port)

        elif scheme == 'https':
            port = 443

        self.port = port or 80
        self.path = path or ''
        self.query = query or ''
        self.scheme = scheme or (self.port == 443 and "https" or "http")
        self.fragment = fragment or ''
        self.last_request = last_request

    def __str__(self):
        attrs = (
            'username',
            'password',
            'hostname',
            'port',
            'path',
        )
        fmt = ", ".join(['%s="%s"' % (k, getattr(self, k, '')) for k in attrs])
        return r'<httpretty.URIInfo(%s)>' % fmt

    def __hash__(self):
        return hash(text_type(self))

    def __eq__(self, other):
        self_tuple = (
            self.port,
            decode_utf8(self.hostname.lower()),
            url_fix(decode_utf8(self.path)),
        )
        other_tuple = (
            other.port,
            decode_utf8(other.hostname.lower()),
            url_fix(decode_utf8(other.path)),
        )
        return self_tuple == other_tuple

    def full_url(self, use_querystring=True):
        credentials = ""
        if self.password:
            credentials = "{0}:{1}@".format(
                self.username, self.password)

        query = ""
        if use_querystring and self.query:
            query = "?{0}".format(decode_utf8(self.query))

        result = "{scheme}://{credentials}{domain}{path}{query}".format(
            scheme=self.scheme,
            credentials=credentials,
            domain=self.get_full_domain(),
            path=decode_utf8(self.path),
            query=query
        )
        return result

    def get_full_domain(self):
        hostname = decode_utf8(self.hostname)
        if self.port not in DEFAULT_HTTP_PORTS:
            return ":".join([hostname, str(self.port)])

        return hostname

    @classmethod
    def from_uri(cls, uri, entry):
        result = urlsplit(uri)
        POTENTIAL_HTTP_PORTS.add(int(result.port or 80))
        return cls(result.username,
                   result.password,
                   result.hostname,
                   result.port,
                   result.path,
                   result.query,
                   result.fragment,
                   result.scheme,
                   entry)


class URIMatcher(object):
    regex = None
    info = None

    def __init__(self, uri, entries, match_querystring=False):
        self._match_querystring = match_querystring
        if type(uri).__name__ == 'SRE_Pattern':
            self.regex = uri
        else:
            self.info = URIInfo.from_uri(uri, entries)

        self.entries = entries

        #hash of current_entry pointers, per method.
        self.current_entries = {}

    def matches(self, info):
        if self.info:
            return self.info == info
        else:
            return self.regex.search(info.full_url(
                use_querystring=self._match_querystring))

    def __str__(self):
        wrap = 'URLMatcher({0})'
        if self.info:
            return wrap.format(text_type(self.info))
        else:
            return wrap.format(self.regex.pattern)

    def get_next_entry(self, method, info, request):
        """Cycle through available responses, but only once.
        Any subsequent requests will receive the last response"""

        if method not in self.current_entries:
            self.current_entries[method] = 0

        #restrict selection to entries that match the requested method
        entries_for_method = [e for e in self.entries if e.method == method]

        if self.current_entries[method] >= len(entries_for_method):
            self.current_entries[method] = -1

        if not self.entries or not entries_for_method:
            raise ValueError('I have no entries for method %s: %s'
                             % (method, self))

        entry = entries_for_method[self.current_entries[method]]
        if self.current_entries[method] != -1:
            self.current_entries[method] += 1

        # Attach more info to the entry
        # So the callback can be more clever about what to do
        # This does also fix the case where the callback
        # would be handed a compiled regex as uri instead of the
        # real uri
        entry.info = info
        entry.request = request
        return entry

    def __hash__(self):
        return hash(text_type(self))

    def __eq__(self, other):
        return text_type(self) == text_type(other)


class httpretty(HttpBaseClass):
    """The URI registration class"""
    _entries = {}
    latest_requests = []

    last_request = HTTPrettyRequestEmpty()
    _is_enabled = False

    @classmethod
    def match_uriinfo(cls, info):
        for matcher, value in cls._entries.items():
            if matcher.matches(info):
                return (matcher, info)

        return (None, [])

    @classmethod
    @contextlib.contextmanager
    def record(cls, filename, indentation=4, encoding='utf-8'):
        try:
            import urllib3
        except ImportError:
            raise RuntimeError('HTTPretty requires urllib3 installed for recording actual requests.')


        http = urllib3.PoolManager()

        cls.enable()
        calls = []
        def record_request(request, uri, headers):
            cls.disable()

            response = http.request(request.method, uri)
            calls.append({
                'request': {
                    'uri': uri,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'body': decode_utf8(request.body),
                    'querystring': request.querystring
                },
                'response': {
                    'status': response.status,
                    'body': decode_utf8(response.data),
                    'headers': dict(response.headers)
                }
            })
            cls.enable()
            return response.status, response.headers, response.data

        for method in cls.METHODS:
            cls.register_uri(method, re.compile(r'.*', re.M), body=record_request)

        yield
        cls.disable()
        with codecs.open(filename, 'w', encoding) as f:
            f.write(json.dumps(calls, indent=indentation))

    @classmethod
    @contextlib.contextmanager
    def playback(cls, origin):
        cls.enable()

        data = json.loads(open(origin).read())
        for item in data:
            uri = item['request']['uri']
            method = item['request']['method']
            cls.register_uri(method, uri, body=item['response']['body'], forcing_headers=item['response']['headers'])

        yield
        cls.disable()

    @classmethod
    def reset(cls):
        global POTENTIAL_HTTP_PORTS
        POTENTIAL_HTTP_PORTS = set([80, 443])
        cls._entries.clear()
        cls.latest_requests = []
        cls.last_request = HTTPrettyRequestEmpty()

    @classmethod
    def historify_request(cls, headers, body='', append=True):
        request = HTTPrettyRequest(headers, body)
        cls.last_request = request
        if append or not cls.latest_requests:
            cls.latest_requests.append(request)
        else:
            cls.latest_requests[-1] = request
        return request

    @classmethod
    def register_uri(cls, method, uri, body='HTTPretty :)',
                     adding_headers=None,
                     forcing_headers=None,
                     status=200,
                     responses=None, match_querystring=False,
                     **headers):

        uri_is_string = isinstance(uri, basestring)

        if uri_is_string and re.search(r'^\w+://[^/]+[.]\w{2,}$', uri):
            uri += '/'

        if isinstance(responses, list) and len(responses) > 0:
            for response in responses:
                response.uri = uri
                response.method = method
            entries_for_this_uri = responses
        else:
            headers[str('body')] = body
            headers[str('adding_headers')] = adding_headers
            headers[str('forcing_headers')] = forcing_headers
            headers[str('status')] = status

            entries_for_this_uri = [
                cls.Response(method=method, uri=uri, **headers),
            ]

        matcher = URIMatcher(uri, entries_for_this_uri,
                             match_querystring)
        if matcher in cls._entries:
            matcher.entries.extend(cls._entries[matcher])
            del cls._entries[matcher]

        cls._entries[matcher] = entries_for_this_uri

    def __str__(self):
        return '<HTTPretty with %d URI entries>' % len(self._entries)

    @classmethod
    def Response(cls, body, method=None, uri=None, adding_headers=None, forcing_headers=None,
                 status=200, streaming=False, **headers):

        headers[str('body')] = body
        headers[str('adding_headers')] = adding_headers
        headers[str('forcing_headers')] = forcing_headers
        headers[str('status')] = int(status)
        headers[str('streaming')] = streaming
        return Entry(method, uri, **headers)

    @classmethod
    def disable(cls):
        cls._is_enabled = False
        socket.socket = old_socket
        socket.SocketType = old_socket
        socket._socketobject = old_socket

        socket.create_connection = old_create_connection
        socket.gethostname = old_gethostname
        socket.gethostbyname = old_gethostbyname
        socket.getaddrinfo = old_getaddrinfo

        socket.__dict__['socket'] = old_socket
        socket.__dict__['_socketobject'] = old_socket
        socket.__dict__['SocketType'] = old_socket

        socket.__dict__['create_connection'] = old_create_connection
        socket.__dict__['gethostname'] = old_gethostname
        socket.__dict__['gethostbyname'] = old_gethostbyname
        socket.__dict__['getaddrinfo'] = old_getaddrinfo

        if socks:
            socks.socksocket = old_socksocket
            socks.__dict__['socksocket'] = old_socksocket

        if ssl:
            ssl.wrap_socket = old_ssl_wrap_socket
            ssl.SSLSocket = old_sslsocket
            ssl.__dict__['wrap_socket'] = old_ssl_wrap_socket
            ssl.__dict__['SSLSocket'] = old_sslsocket

            if not PY3:
                ssl.sslwrap_simple = old_sslwrap_simple
                ssl.__dict__['sslwrap_simple'] = old_sslwrap_simple

    @classmethod
    def is_enabled(cls):
        return cls._is_enabled

    @classmethod
    def enable(cls):
        cls._is_enabled = True
        socket.socket = fakesock.socket
        socket._socketobject = fakesock.socket
        socket.SocketType = fakesock.socket

        socket.create_connection = create_fake_connection
        socket.gethostname = fake_gethostname
        socket.gethostbyname = fake_gethostbyname
        socket.getaddrinfo = fake_getaddrinfo

        socket.__dict__['socket'] = fakesock.socket
        socket.__dict__['_socketobject'] = fakesock.socket
        socket.__dict__['SocketType'] = fakesock.socket

        socket.__dict__['create_connection'] = create_fake_connection
        socket.__dict__['gethostname'] = fake_gethostname
        socket.__dict__['gethostbyname'] = fake_gethostbyname
        socket.__dict__['getaddrinfo'] = fake_getaddrinfo

        if socks:
            socks.socksocket = fakesock.socket
            socks.__dict__['socksocket'] = fakesock.socket

        if ssl:
            ssl.wrap_socket = fake_wrap_socket
            ssl.SSLSocket = FakeSSLSocket

            ssl.__dict__['wrap_socket'] = fake_wrap_socket
            ssl.__dict__['SSLSocket'] = FakeSSLSocket

            if not PY3:
                ssl.sslwrap_simple = fake_wrap_socket
                ssl.__dict__['sslwrap_simple'] = fake_wrap_socket


def httprettified(test):
    "A decorator tests that use HTTPretty"
    def decorate_class(klass):
        for attr in dir(klass):
            if not attr.startswith('test_'):
                continue

            attr_value = getattr(klass, attr)
            if not hasattr(attr_value, "__call__"):
                continue

            setattr(klass, attr, decorate_callable(attr_value))
        return klass

    def decorate_callable(test):
        @functools.wraps(test)
        def wrapper(*args, **kw):
            httpretty.reset()
            httpretty.enable()
            try:
                return test(*args, **kw)
            finally:
                httpretty.disable()
        return wrapper

    if isinstance(test, ClassTypes):
        return decorate_class(test)
    return decorate_callable(test)

########NEW FILE########
__FILENAME__ = errors
# #!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals


class HTTPrettyError(Exception):
    pass

########NEW FILE########
__FILENAME__ = http
# #!/usr/bin/env python
# -*- coding: utf-8 -*-
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

import re
from .compat import BaseClass
from .utils import decode_utf8


STATUSES = {
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi-Status",
    208: "Already Reported",
    226: "IM Used",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    306: "Switch Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request a Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request-URI Too Long",
    415: "Unsupported Media Type",
    416: "Requested Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a teapot",
    420: "Enhance Your Calm",
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    424: "Method Failure",
    425: "Unordered Collection",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    431: "Request Header Fields Too Large",
    444: "No Response",
    449: "Retry With",
    450: "Blocked by Windows Parental Controls",
    451: "Unavailable For Legal Reasons",
    451: "Redirect",
    494: "Request Header Too Large",
    495: "Cert Error",
    496: "No Cert",
    497: "HTTP to HTTPS",
    499: "Client Closed Request",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    506: "Variant Also Negotiates",
    507: "Insufficient Storage",
    508: "Loop Detected",
    509: "Bandwidth Limit Exceeded",
    510: "Not Extended",
    511: "Network Authentication Required",
    598: "Network read timeout error",
    599: "Network connect timeout error",
}


class HttpBaseClass(BaseClass):
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    DELETE = 'DELETE'
    HEAD = 'HEAD'
    PATCH = 'PATCH'
    OPTIONS = 'OPTIONS'
    CONNECT = 'CONNECT'
    METHODS = (GET, PUT, POST, DELETE, HEAD, PATCH, OPTIONS, CONNECT)


def parse_requestline(s):
    """
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5

    >>> parse_requestline('GET / HTTP/1.0')
    ('GET', '/', '1.0')
    >>> parse_requestline('post /testurl htTP/1.1')
    ('POST', '/testurl', '1.1')
    >>> parse_requestline('Im not a RequestLine')
    Traceback (most recent call last):
        ...
    ValueError: Not a Request-Line
    """
    methods = '|'.join(HttpBaseClass.METHODS)
    m = re.match(r'(' + methods + ')\s+(.*)\s+HTTP/(1.[0|1])', s, re.I)
    if m:
        return m.group(1).upper(), m.group(2), m.group(3)
    else:
        raise ValueError('Not a Request-Line')


def last_requestline(sent_data):
    """
    Find the last line in sent_data that can be parsed with parse_requestline
    """
    for line in reversed(sent_data):
        try:
            parse_requestline(decode_utf8(line))
        except ValueError:
            pass
        else:
            return line

########NEW FILE########
__FILENAME__ = utils
# #!/usr/bin/env python
# -*- coding: utf-8 -*-
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

from .compat import (
    byte_type, text_type
)


def utf8(s):
    if isinstance(s, text_type):
        s = s.encode('utf-8')

    return byte_type(s)


def decode_utf8(s):
    if isinstance(s, byte_type):
        s = s.decode("utf-8")

    return text_type(s)

########NEW FILE########
__FILENAME__ = base
# #!/usr/bin/env python
# -*- coding: utf-8 -*-

# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals
import os
import threading
import traceback
import tornado.ioloop
import tornado.web
from functools import wraps
from sure import scenario
import json
from os.path import abspath, dirname, join
from httpretty.core import POTENTIAL_HTTP_PORTS


LOCAL_FILE = lambda *path: join(abspath(dirname(__file__)), *path)
FIXTURE_FILE = lambda name: LOCAL_FILE('fixtures', name)


class JSONEchoHandler(tornado.web.RequestHandler):
    def get(self, matched):
        payload = dict([(x, self.get_argument(x)) for x in self.request.arguments])
        self.write(json.dumps({matched or 'index': payload}, indent=4))

    def post(self, matched):
        payload = dict(self.request.arguments)
        self.write(json.dumps({matched or 'index': payload}, indent=4))


class JSONEchoServer(threading.Thread):
    def __init__(self, lock, port=8888, *args, **kw):
        self.lock = lock
        self.port = int(port)
        self._stop = threading.Event()
        super(JSONEchoServer, self).__init__(*args, **kw)
        self.daemon = True

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def setup_application(self):
        return tornado.web.Application([
            (r"/(.*)", JSONEchoHandler),
        ])

    def run(self):
        application = self.setup_application()
        application.listen(self.port)
        self.lock.release()
        tornado.ioloop.IOLoop.instance().start()



def use_tornado_server(callback):
    lock = threading.Lock()
    lock.acquire()

    @wraps(callback)
    def func(*args, **kw):
        server = JSONEchoServer(lock, os.getenv('TEST_PORT', 8888))
        server.start()
        try:
            lock.acquire()
            callback(*args, **kw)
        finally:
            lock.release()
            server.stop()
            if 8888 in POTENTIAL_HTTP_PORTS:
                POTENTIAL_HTTP_PORTS.remove(8888)
    return func

########NEW FILE########
__FILENAME__ = testserver
# #!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

import os
import sys

try:
    import io
    StringIO = io.StringIO
except ImportError:
    import StringIO
    StringIO = StringIO.StringIO

import time
import socket
from tornado.web import Application
from tornado.web import RequestHandler
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from multiprocessing import Process

PY3 = sys.version_info[0] == 3
if PY3:
    text_type = str
    byte_type = bytes
else:
    text_type = unicode
    byte_type = str


def utf8(s):
    if isinstance(s, text_type):
        s = s.encode('utf-8')

    return byte_type(s)

true_socket = socket.socket

PY3 = sys.version_info[0] == 3

if not PY3:
    bytes = lambda s, *args: str(s)


class BubblesHandler(RequestHandler):
    def get(self):
        self.write(". o O 0 O o . o O 0 O o . o O 0 O o . o O 0 O o . o O 0 O o .")


class ComeHandler(RequestHandler):
    def get(self):
        self.write("<- HELLO WORLD ->")


class TornadoServer(object):
    is_running = False

    def __init__(self, port):
        self.port = int(port)
        self.process = None

    @classmethod
    def get_handlers(cls):
        return Application([
            (r"/go-for-bubbles/?", BubblesHandler),
            (r"/come-again/?", ComeHandler),
        ])

    def start(self):
        def go(app, port, data={}):
            from httpretty import HTTPretty
            HTTPretty.disable()
            http = HTTPServer(app)
            http.listen(int(port))
            IOLoop.instance().start()

        app = self.get_handlers()

        data = {}
        args = (app, self.port, data)
        self.process = Process(target=go, args=args)
        self.process.start()
        time.sleep(0.4)

    def stop(self):
        try:
            os.kill(self.process.pid, 9)
        except OSError:
            self.process.terminate()
        finally:
            self.is_running = False


class TCPServer(object):
    def __init__(self, port):
        self.port = int(port)

    def start(self):
        def go(port):
            from httpretty import HTTPretty
            HTTPretty.disable()
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('localhost', port))
            s.listen(True)
            conn, addr = s.accept()

            while True:
                data = conn.recv(1024)
                conn.send(b"RECEIVED: " + bytes(data))

            conn.close()

        args = [self.port]
        self.process = Process(target=go, args=args)
        self.process.start()
        time.sleep(0.4)

    def stop(self):
        try:
            os.kill(self.process.pid, 9)
        except OSError:
            self.process.terminate()
        finally:
            self.is_running = False


class TCPClient(object):
    def __init__(self, port):
        self.port = int(port)
        self.sock = true_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('localhost', self.port))

    def send(self, what):
        data = bytes(what, 'utf-8')
        self.sock.sendall(data)
        return self.sock.recv(len(data) + 11)

    def close(self):
        try:
            self.sock.close()
        except socket.error:
            pass  # already closed

    def __del__(self):
        self.close()

########NEW FILE########
__FILENAME__ = test_bypass
# #!/usr/bin/env python
# -*- coding: utf-8 -*-

# <httpretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

from .testserver import TornadoServer, TCPServer, TCPClient
from sure import expect, that_with_context

import httpretty
from httpretty import core


def start_http_server(context):
    context.server = TornadoServer(9999)
    context.server.start()
    httpretty.enable()


def stop_http_server(context):
    context.server.stop()
    httpretty.enable()


def start_tcp_server(context):
    context.server = TCPServer(8888)
    context.server.start()
    context.client = TCPClient(8888)
    httpretty.enable()


def stop_tcp_server(context):
    context.server.stop()
    context.client.close()
    httpretty.enable()


@httpretty.activate
@that_with_context(start_http_server, stop_http_server)
def test_httpretty_bypasses_when_disabled(context):
    "httpretty should bypass all requests by disabling it"

    httpretty.register_uri(
        httpretty.GET, "http://localhost:9999/go-for-bubbles/",
        body="glub glub")

    httpretty.disable()

    fd = urllib2.urlopen('http://localhost:9999/go-for-bubbles/')
    got1 = fd.read()
    fd.close()

    expect(got1).to.equal(
        b'. o O 0 O o . o O 0 O o . o O 0 O o . o O 0 O o . o O 0 O o .')

    fd = urllib2.urlopen('http://localhost:9999/come-again/')
    got2 = fd.read()
    fd.close()

    expect(got2).to.equal(b'<- HELLO WORLD ->')

    httpretty.enable()

    fd = urllib2.urlopen('http://localhost:9999/go-for-bubbles/')
    got3 = fd.read()
    fd.close()

    expect(got3).to.equal(b'glub glub')
    core.POTENTIAL_HTTP_PORTS.remove(9999)

@httpretty.activate
@that_with_context(start_http_server, stop_http_server)
def test_httpretty_bypasses_a_unregistered_request(context):
    "httpretty should bypass a unregistered request by disabling it"

    httpretty.register_uri(
        httpretty.GET, "http://localhost:9999/go-for-bubbles/",
        body="glub glub")

    fd = urllib2.urlopen('http://localhost:9999/go-for-bubbles/')
    got1 = fd.read()
    fd.close()

    expect(got1).to.equal(b'glub glub')

    fd = urllib2.urlopen('http://localhost:9999/come-again/')
    got2 = fd.read()
    fd.close()

    expect(got2).to.equal(b'<- HELLO WORLD ->')
    core.POTENTIAL_HTTP_PORTS.remove(9999)


@httpretty.activate
@that_with_context(start_tcp_server, stop_tcp_server)
def test_using_httpretty_with_other_tcp_protocols(context):
    "httpretty should work even when testing code that also use other TCP-based protocols"

    httpretty.register_uri(
        httpretty.GET, "http://falcao.it/foo/",
        body="BAR")

    fd = urllib2.urlopen('http://falcao.it/foo/')
    got1 = fd.read()
    fd.close()

    expect(got1).to.equal(b'BAR')

    expect(context.client.send("foobar")).to.equal(b"RECEIVED: foobar")

########NEW FILE########
__FILENAME__ = test_debug
# #!/usr/bin/env python
# -*- coding: utf-8 -*-

# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals
import socket
from sure import scenario, expect
from httpretty import httprettified


def create_socket(context):
    context.sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
    )
    context.sock.is_http = True


@httprettified
@scenario(create_socket)
def test_httpretty_debugs_socket_send(context):
    "HTTPretty should debug socket.send"

    expect(context.sock.send).when.called.to.throw(
        RuntimeError,
        "HTTPretty intercepted and unexpected socket method call."
    )


@httprettified
@scenario(create_socket)
def test_httpretty_debugs_socket_sendto(context):
    "HTTPretty should debug socket.sendto"

    expect(context.sock.sendto).when.called.to.throw(
        RuntimeError,
        "HTTPretty intercepted and unexpected socket method call."
    )


@httprettified
@scenario(create_socket)
def test_httpretty_debugs_socket_recv(context):
    "HTTPretty should debug socket.recv"

    expect(context.sock.recv).when.called.to.throw(
        RuntimeError,
        "HTTPretty intercepted and unexpected socket method call."
    )


@httprettified
@scenario(create_socket)
def test_httpretty_debugs_socket_recvfrom(context):
    "HTTPretty should debug socket.recvfrom"

    expect(context.sock.recvfrom).when.called.to.throw(
        RuntimeError,
        "HTTPretty intercepted and unexpected socket method call."
    )


@httprettified
@scenario(create_socket)
def test_httpretty_debugs_socket_recv_into(context):
    "HTTPretty should debug socket.recv_into"

    expect(context.sock.recv_into).when.called.to.throw(
        RuntimeError,
        "HTTPretty intercepted and unexpected socket method call."
    )


@httprettified
@scenario(create_socket)
def test_httpretty_debugs_socket_recvfrom_into(context):
    "HTTPretty should debug socket.recvfrom_into"

    expect(context.sock.recvfrom_into).when.called.to.throw(
        RuntimeError,
        "HTTPretty intercepted and unexpected socket method call."
    )

########NEW FILE########
__FILENAME__ = test_decorator
# coding: utf-8
from unittest import TestCase
from sure import expect
from httpretty import httprettified, HTTPretty

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2


@httprettified
def test_decor():
    HTTPretty.register_uri(
        HTTPretty.GET, "http://localhost/",
        body="glub glub")

    fd = urllib2.urlopen('http://localhost/')
    got1 = fd.read()
    fd.close()

    expect(got1).to.equal(b'glub glub')


@httprettified
class ClassDecorator(TestCase):

    def test_decorated(self):
        HTTPretty.register_uri(
            HTTPretty.GET, "http://localhost/",
            body="glub glub")

        fd = urllib2.urlopen('http://localhost/')
        got1 = fd.read()
        fd.close()

        expect(got1).to.equal(b'glub glub')

    def test_decorated2(self):
        HTTPretty.register_uri(
            HTTPretty.GET, "http://localhost/",
            body="buble buble")

        fd = urllib2.urlopen('http://localhost/')
        got1 = fd.read()
        fd.close()

        expect(got1).to.equal(b'buble buble')
########NEW FILE########
__FILENAME__ = test_httplib2
# #!/usr/bin/env python
# -*- coding: utf-8 -*-

# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

import re
import httplib2
from sure import expect, within, microseconds
from httpretty import HTTPretty, httprettified
from httpretty.core import decode_utf8


@httprettified
@within(two=microseconds)
def test_httpretty_should_mock_a_simple_get_with_httplib2_read(now):
    "HTTPretty should mock a simple GET with httplib2.context.http"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/",
                           body="Find the best daily deals")

    _, got = httplib2.Http().request('http://yipit.com', 'GET')
    expect(got).to.equal(b'Find the best daily deals')

    expect(HTTPretty.last_request.method).to.equal('GET')
    expect(HTTPretty.last_request.path).to.equal('/')


@httprettified
@within(two=microseconds)
def test_httpretty_provides_easy_access_to_querystrings(now):
    "HTTPretty should provide an easy access to the querystring"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/",
                           body="Find the best daily deals")

    httplib2.Http().request('http://yipit.com?foo=bar&foo=baz&chuck=norris', 'GET')
    expect(HTTPretty.last_request.querystring).to.equal({
        'foo': ['bar', 'baz'],
        'chuck': ['norris'],
    })



@httprettified
@within(two=microseconds)
def test_httpretty_should_mock_headers_httplib2(now):
    "HTTPretty should mock basic headers with httplib2"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/",
                           body="this is supposed to be the response",
                           status=201)

    headers, _ = httplib2.Http().request('http://github.com', 'GET')
    expect(headers['status']).to.equal('201')
    expect(dict(headers)).to.equal({
        'content-type': 'text/plain; charset=utf-8',
        'connection': 'close',
        'content-length': '35',
        'status': '201',
        'server': 'Python/HTTPretty',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_adding_and_overwritting_httplib2(now):
    "HTTPretty should allow adding and overwritting headers with httplib2"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/foo",
                           body="this is supposed to be the response",
                           adding_headers={
                               'Server': 'Apache',
                               'Content-Length': '27',
                               'Content-Type': 'application/json',
                           })

    headers, _ = httplib2.Http().request('http://github.com/foo', 'GET')

    expect(dict(headers)).to.equal({
        'content-type': 'application/json',
        'content-location': 'http://github.com/foo',
        'connection': 'close',
        'content-length': '27',
        'status': '200',
        'server': 'Apache',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_forcing_headers_httplib2(now):
    "HTTPretty should allow forcing headers with httplib2"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/foo",
                           body="this is supposed to be the response",
                           forcing_headers={
                               'Content-Type': 'application/xml',
                           })

    headers, _ = httplib2.Http().request('http://github.com/foo', 'GET')

    expect(dict(headers)).to.equal({
        'content-location': 'http://github.com/foo',  # httplib2 FORCES
                                                   # content-location
                                                   # even if the
                                                   # server does not
                                                   # provide it
        'content-type': 'application/xml',
        'status': '200',  # httplib2 also ALWAYS put status on headers
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_adding_and_overwritting_by_kwargs_u2(now):
    "HTTPretty should allow adding and overwritting headers by keyword args " \
        "with httplib2"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/foo",
                           body="this is supposed to be the response",
                           server='Apache',
                           content_length='27',
                           content_type='application/json')

    headers, _ = httplib2.Http().request('http://github.com/foo', 'GET')

    expect(dict(headers)).to.equal({
        'content-type': 'application/json',
        'content-location': 'http://github.com/foo',  # httplib2 FORCES
                                                   # content-location
                                                   # even if the
                                                   # server does not
                                                   # provide it
        'connection': 'close',
        'content-length': '27',
        'status': '200',
        'server': 'Apache',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_rotating_responses_with_httplib2(now):
    "HTTPretty should support rotating responses with httplib2"

    HTTPretty.register_uri(
        HTTPretty.GET, "https://api.yahoo.com/test",
        responses=[
            HTTPretty.Response(body="first response", status=201),
            HTTPretty.Response(body='second and last response', status=202),
        ])

    headers1, body1 = httplib2.Http().request(
        'https://api.yahoo.com/test', 'GET')

    expect(headers1['status']).to.equal('201')
    expect(body1).to.equal(b'first response')

    headers2, body2 = httplib2.Http().request(
        'https://api.yahoo.com/test', 'GET')

    expect(headers2['status']).to.equal('202')
    expect(body2).to.equal(b'second and last response')

    headers3, body3 = httplib2.Http().request(
        'https://api.yahoo.com/test', 'GET')

    expect(headers3['status']).to.equal('202')
    expect(body3).to.equal(b'second and last response')


@httprettified
@within(two=microseconds)
def test_can_inspect_last_request(now):
    "HTTPretty.last_request is a mimetools.Message request from last match"

    HTTPretty.register_uri(HTTPretty.POST, "http://api.github.com/",
                           body='{"repositories": ["HTTPretty", "lettuce"]}')

    headers, body = httplib2.Http().request(
        'http://api.github.com', 'POST',
        body='{"username": "gabrielfalcao"}',
        headers={
            'content-type': 'text/json',
        },
    )

    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.body).to.equal(
        b'{"username": "gabrielfalcao"}',
    )
    expect(HTTPretty.last_request.headers['content-type']).to.equal(
        'text/json',
    )
    expect(body).to.equal(b'{"repositories": ["HTTPretty", "lettuce"]}')


@httprettified
@within(two=microseconds)
def test_can_inspect_last_request_with_ssl(now):
    "HTTPretty.last_request is recorded even when mocking 'https' (SSL)"

    HTTPretty.register_uri(HTTPretty.POST, "https://secure.github.com/",
                           body='{"repositories": ["HTTPretty", "lettuce"]}')

    headers, body = httplib2.Http().request(
        'https://secure.github.com', 'POST',
        body='{"username": "gabrielfalcao"}',
        headers={
            'content-type': 'text/json',
        },
    )

    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.body).to.equal(
        b'{"username": "gabrielfalcao"}',
    )
    expect(HTTPretty.last_request.headers['content-type']).to.equal(
        'text/json',
    )
    expect(body).to.equal(b'{"repositories": ["HTTPretty", "lettuce"]}')


@httprettified
@within(two=microseconds)
def test_httpretty_ignores_querystrings_from_registered_uri(now):
    "Registering URIs with query string cause them to be ignored"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/?id=123",
                           body="Find the best daily deals")

    _, got = httplib2.Http().request('http://yipit.com/?id=123', 'GET')

    expect(got).to.equal(b'Find the best daily deals')
    expect(HTTPretty.last_request.method).to.equal('GET')
    expect(HTTPretty.last_request.path).to.equal('/?id=123')


@httprettified
@within(two=microseconds)
def test_callback_response(now):
    ("HTTPretty should all a callback function to be set as the body with"
      " httplib2")

    def request_callback(request, uri, headers):
        return [200,headers,"The {0} response from {1}".format(decode_utf8(request.method), uri)]

    HTTPretty.register_uri(
        HTTPretty.GET, "https://api.yahoo.com/test",
        body=request_callback)

    headers1, body1 = httplib2.Http().request(
        'https://api.yahoo.com/test', 'GET')

    expect(body1).to.equal(b"The GET response from https://api.yahoo.com/test")

    HTTPretty.register_uri(
        HTTPretty.POST, "https://api.yahoo.com/test_post",
        body=request_callback)

    headers2, body2 = httplib2.Http().request(
        'https://api.yahoo.com/test_post', 'POST')

    expect(body2).to.equal(b"The POST response from https://api.yahoo.com/test_post")


@httprettified
def test_httpretty_should_allow_registering_regexes():
    "HTTPretty should allow registering regexes with httplib2"

    HTTPretty.register_uri(
        HTTPretty.GET,
        re.compile("https://api.yipit.com/v1/deal;brand=(?P<brand_name>\w+)"),
        body="Found brand",
    )

    response, body = httplib2.Http().request('https://api.yipit.com/v1/deal;brand=gap', 'GET')
    expect(body).to.equal(b'Found brand')
    expect(HTTPretty.last_request.method).to.equal('GET')
    expect(HTTPretty.last_request.path).to.equal('/v1/deal;brand=gap')

########NEW FILE########
__FILENAME__ = test_requests
# #!/usr/bin/env python
# -*- coding: utf-8 -*-

# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import os
import re
import json
import requests
from sure import within, microseconds, expect
from tornado import version as tornado_version
from httpretty import HTTPretty, httprettified
from httpretty.compat import text_type
from httpretty.core import decode_utf8

from .base import FIXTURE_FILE, use_tornado_server
from tornado import version as tornado_version

try:
    xrange = xrange
except NameError:
    xrange = range

try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator

PORT = int(os.getenv('TEST_PORT') or 8888)
server_url = lambda path: "http://localhost:{0}/{1}".format(PORT, path.lstrip('/'))


@httprettified
@within(two=microseconds)
def test_httpretty_should_mock_a_simple_get_with_requests_read(now):
    "HTTPretty should mock a simple GET with requests.get"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/",
                           body="Find the best daily deals")

    response = requests.get('http://yipit.com')
    expect(response.text).to.equal('Find the best daily deals')
    expect(HTTPretty.last_request.method).to.equal('GET')
    expect(HTTPretty.last_request.path).to.equal('/')


@httprettified
@within(two=microseconds)
def test_httpretty_provides_easy_access_to_querystrings(now):
    "HTTPretty should provide an easy access to the querystring"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/",
                           body="Find the best daily deals")

    requests.get('http://yipit.com/?foo=bar&foo=baz&chuck=norris')
    expect(HTTPretty.last_request.querystring).to.equal({
        'foo': ['bar', 'baz'],
        'chuck': ['norris'],
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_mock_headers_requests(now):
    "HTTPretty should mock basic headers with requests"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/",
                           body="this is supposed to be the response",
                           status=201)

    response = requests.get('http://github.com')
    expect(response.status_code).to.equal(201)

    expect(dict(response.headers)).to.equal({
        'content-type': 'text/plain; charset=utf-8',
        'connection': 'close',
        'content-length': '35',
        'status': '201',
        'server': 'Python/HTTPretty',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_adding_and_overwritting_requests(now):
    "HTTPretty should allow adding and overwritting headers with requests"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/foo",
                           body="this is supposed to be the response",
                           adding_headers={
                               'Server': 'Apache',
                               'Content-Length': '27',
                               'Content-Type': 'application/json',
                           })

    response = requests.get('http://github.com/foo')

    expect(dict(response.headers)).to.equal({
        'content-type': 'application/json',
        'connection': 'close',
        'content-length': '27',
        'status': '200',
        'server': 'Apache',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_forcing_headers_requests(now):
    "HTTPretty should allow forcing headers with requests"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/foo",
                           body="<root><baz /</root>",
                           forcing_headers={
                               'Content-Type': 'application/xml',
                               'Content-Length': '19',
                           })

    response = requests.get('http://github.com/foo')

    expect(dict(response.headers)).to.equal({
        'content-type': 'application/xml',
        'content-length': '19',
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_adding_and_overwritting_by_kwargs_u2(now):
    "HTTPretty should allow adding and overwritting headers by keyword args " \
        "with requests"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/foo",
                           body="this is supposed to be the response",
                           server='Apache',
                           content_length='27',
                           content_type='application/json')

    response = requests.get('http://github.com/foo')

    expect(dict(response.headers)).to.equal({
        'content-type': 'application/json',
        'connection': 'close',
        'content-length': '27',
        'status': '200',
        'server': 'Apache',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_rotating_responses_with_requests(now):
    "HTTPretty should support rotating responses with requests"

    HTTPretty.register_uri(
        HTTPretty.GET, "https://api.yahoo.com/test",
        responses=[
            HTTPretty.Response(body=b"first response", status=201),
            HTTPretty.Response(body=b'second and last response', status=202),
        ])

    response1 = requests.get(
        'https://api.yahoo.com/test')

    expect(response1.status_code).to.equal(201)
    expect(response1.text).to.equal('first response')

    response2 = requests.get(
        'https://api.yahoo.com/test')

    expect(response2.status_code).to.equal(202)
    expect(response2.text).to.equal('second and last response')

    response3 = requests.get(
        'https://api.yahoo.com/test')

    expect(response3.status_code).to.equal(202)
    expect(response3.text).to.equal('second and last response')


@httprettified
@within(two=microseconds)
def test_can_inspect_last_request(now):
    "HTTPretty.last_request is a mimetools.Message request from last match"

    HTTPretty.register_uri(HTTPretty.POST, "http://api.github.com/",
                           body='{"repositories": ["HTTPretty", "lettuce"]}')

    response = requests.post(
        'http://api.github.com',
        '{"username": "gabrielfalcao"}',
        headers={
            'content-type': 'text/json',
        },
    )

    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.body).to.equal(
        b'{"username": "gabrielfalcao"}',
    )
    expect(HTTPretty.last_request.headers['content-type']).to.equal(
        'text/json',
    )
    expect(response.json()).to.equal({"repositories": ["HTTPretty", "lettuce"]})


@httprettified
@within(two=microseconds)
def test_can_inspect_last_request_with_ssl(now):
    "HTTPretty.last_request is recorded even when mocking 'https' (SSL)"

    HTTPretty.register_uri(HTTPretty.POST, "https://secure.github.com/",
                           body='{"repositories": ["HTTPretty", "lettuce"]}')

    response = requests.post(
        'https://secure.github.com',
        '{"username": "gabrielfalcao"}',
        headers={
            'content-type': 'text/json',
        },
    )

    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.body).to.equal(
        b'{"username": "gabrielfalcao"}',
    )
    expect(HTTPretty.last_request.headers['content-type']).to.equal(
        'text/json',
    )
    expect(response.json()).to.equal({"repositories": ["HTTPretty", "lettuce"]})


@httprettified
@within(two=microseconds)
def test_httpretty_ignores_querystrings_from_registered_uri(now):
    "HTTPretty should ignore querystrings from the registered uri (requests library)"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/?id=123",
                           body=b"Find the best daily deals")

    response = requests.get('http://yipit.com/', params={'id': 123})
    expect(response.text).to.equal('Find the best daily deals')
    expect(HTTPretty.last_request.method).to.equal('GET')
    expect(HTTPretty.last_request.path).to.equal('/?id=123')


@httprettified
@within(five=microseconds)
def test_streaming_responses(now):
    """
    Mock a streaming HTTP response, like those returned by the Twitter streaming
    API.
    """
    from contextlib import contextmanager

    @contextmanager
    def in_time(time, message):
        """
        A context manager that uses signals to force a time limit in tests
        (unlike the `@within` decorator, which only complains afterward), or
        raise an AssertionError.
        """
        import signal

        def handler(signum, frame):
            raise AssertionError(message)
        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(signal.ITIMER_REAL, time)
        yield
        signal.setitimer(signal.ITIMER_REAL, 0)

    #XXX this obviously isn't a fully functional twitter streaming client!
    twitter_response_lines = [
        b'{"text":"If \\"for the boobs\\" requests to follow me one more time I\'m calling the police. http://t.co/a0mDEAD8"}\r\n',
        b'\r\n',
        b'{"text":"RT @onedirection: Thanks for all your #FollowMe1D requests Directioners! We\u2019ll be following 10 people throughout the day starting NOW. G ..."}\r\n'
    ]

    TWITTER_STREAMING_URL = "https://stream.twitter.com/1/statuses/filter.json"

    HTTPretty.register_uri(HTTPretty.POST, TWITTER_STREAMING_URL,
                           body=(l for l in twitter_response_lines),
                           streaming=True)

    # taken from the requests docs
    # Http://docs.python-requests.org/en/latest/user/advanced/#streaming-requests
    response = requests.post(TWITTER_STREAMING_URL, data={'track': 'requests'},
                             auth=('username', 'password'), stream=True)

    #test iterating by line
    line_iter = response.iter_lines()
    with in_time(0.01, 'Iterating by line is taking forever!'):
        for i in xrange(len(twitter_response_lines)):
            expect(next(line_iter).strip()).to.equal(
                twitter_response_lines[i].strip())

    #test iterating by line after a second request
    response = requests.post(TWITTER_STREAMING_URL, data={'track': 'requests'},
                            auth=('username', 'password'), stream=True)

    line_iter = response.iter_lines()
    with in_time(0.01, 'Iterating by line is taking forever the second time '
                       'around!'):
        for i in xrange(len(twitter_response_lines)):
            expect(next(line_iter).strip()).to.equal(
                twitter_response_lines[i].strip())

    #test iterating by char
    response = requests.post(TWITTER_STREAMING_URL, data={'track': 'requests'},
                            auth=('username', 'password'), stream=True)

    twitter_expected_response_body = b''.join(twitter_response_lines)
    with in_time(0.02, 'Iterating by char is taking forever!'):
        twitter_body = b''.join(c for c in response.iter_content(chunk_size=1))

    expect(twitter_body).to.equal(twitter_expected_response_body)

    #test iterating by chunks larger than the stream

    response = requests.post(TWITTER_STREAMING_URL, data={'track': 'requests'},
                             auth=('username', 'password'), stream=True)

    with in_time(0.02, 'Iterating by large chunks is taking forever!'):
        twitter_body = b''.join(c for c in
                                response.iter_content(chunk_size=1024))

    expect(twitter_body).to.equal(twitter_expected_response_body)


@httprettified
def test_multiline():
    url = 'http://httpbin.org/post'
    data = b'content=Im\r\na multiline\r\n\r\nsentence\r\n'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Accept': 'text/plain',
    }
    HTTPretty.register_uri(
        HTTPretty.POST,
        url,
    )
    response = requests.post(url, data=data, headers=headers)

    expect(response.status_code).to.equal(200)
    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.path).to.equal('/post')
    expect(HTTPretty.last_request.body).to.equal(data)
    expect(HTTPretty.last_request.headers['content-length']).to.equal('37')
    expect(HTTPretty.last_request.headers['content-type']).to.equal('application/x-www-form-urlencoded; charset=utf-8')
    expect(len(HTTPretty.latest_requests)).to.equal(1)


@httprettified
def test_octet_stream():
    url = 'http://httpbin.org/post'
    data = b"\xf5\x00\x00\x00"  # utf-8 with invalid start byte
    headers = {
        'Content-Type': 'application/octet-stream',
    }
    HTTPretty.register_uri(
        HTTPretty.POST,
        url,
    )
    response = requests.post(url, data=data, headers=headers)

    expect(response.status_code).to.equal(200)
    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.path).to.equal('/post')
    expect(HTTPretty.last_request.body).to.equal(data)
    expect(HTTPretty.last_request.headers['content-length']).to.equal('4')
    expect(HTTPretty.last_request.headers['content-type']).to.equal('application/octet-stream')
    expect(len(HTTPretty.latest_requests)).to.equal(1)



@httprettified
def test_multipart():
    url = 'http://httpbin.org/post'
    data = b'--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="content"\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 68\r\n\r\nAction: comment\nText: Comment with attach\nAttachment: x1.txt, x2.txt\r\n--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="attachment_2"; filename="x.txt"\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\nbye\n\r\n--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="attachment_1"; filename="x.txt"\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\nbye\n\r\n--xXXxXXyYYzzz--\r\n'
    headers = {'Content-Length': '495', 'Content-Type': 'multipart/form-data; boundary=xXXxXXyYYzzz', 'Accept': 'text/plain'}
    HTTPretty.register_uri(
        HTTPretty.POST,
        url,
    )
    response = requests.post(url, data=data, headers=headers)
    expect(response.status_code).to.equal(200)
    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.path).to.equal('/post')
    expect(HTTPretty.last_request.body).to.equal(data)
    expect(HTTPretty.last_request.headers['content-length']).to.equal('495')
    expect(HTTPretty.last_request.headers['content-type']).to.equal('multipart/form-data; boundary=xXXxXXyYYzzz')
    expect(len(HTTPretty.latest_requests)).to.equal(1)


@httprettified
@within(two=microseconds)
def test_callback_response(now):
    ("HTTPretty should call a callback function and set its return value as the body of the response"
     " requests")

    def request_callback(request, uri, headers):
        return [200, headers,"The {0} response from {1}".format(decode_utf8(request.method), uri)]

    HTTPretty.register_uri(
        HTTPretty.GET, "https://api.yahoo.com/test",
        body=request_callback)

    response = requests.get('https://api.yahoo.com/test')

    expect(response.text).to.equal("The GET response from https://api.yahoo.com/test")

    HTTPretty.register_uri(
        HTTPretty.POST, "https://api.yahoo.com/test_post",
        body=request_callback)

    response = requests.post(
        "https://api.yahoo.com/test_post",
        {"username": "gabrielfalcao"}
    )

    expect(response.text).to.equal("The POST response from https://api.yahoo.com/test_post")

@httprettified
@within(two=microseconds)
def test_callback_body_remains_callable_for_any_subsequent_requests(now):
    ("HTTPretty should call a callback function more than one"
     " requests")

    def request_callback(request, uri, headers):
        return [200, headers,"The {0} response from {1}".format(decode_utf8(request.method), uri)]

    HTTPretty.register_uri(
        HTTPretty.GET, "https://api.yahoo.com/test",
        body=request_callback)

    response = requests.get('https://api.yahoo.com/test')
    expect(response.text).to.equal("The GET response from https://api.yahoo.com/test")

    response = requests.get('https://api.yahoo.com/test')
    expect(response.text).to.equal("The GET response from https://api.yahoo.com/test")

@httprettified
@within(two=microseconds)
def test_callback_setting_headers_and_status_response(now):
    ("HTTPretty should call a callback function and uses it retur tuple as status code, headers and body"
     " requests")

    def request_callback(request, uri, headers):
        headers.update({'a':'b'})
        return [418,headers,"The {0} response from {1}".format(decode_utf8(request.method), uri)]

    HTTPretty.register_uri(
        HTTPretty.GET, "https://api.yahoo.com/test",
        body=request_callback)

    response = requests.get('https://api.yahoo.com/test')
    expect(response.text).to.equal("The GET response from https://api.yahoo.com/test")
    expect(response.headers).to.have.key('a').being.equal("b")
    expect(response.status_code).to.equal(418)

    HTTPretty.register_uri(
        HTTPretty.POST, "https://api.yahoo.com/test_post",
        body=request_callback)

    response = requests.post(
        "https://api.yahoo.com/test_post",
        {"username": "gabrielfalcao"}
    )

    expect(response.text).to.equal("The POST response from https://api.yahoo.com/test_post")
    expect(response.headers).to.have.key('a').being.equal("b")
    expect(response.status_code).to.equal(418)

@httprettified
def test_httpretty_should_allow_registering_regexes_and_give_a_proper_match_to_the_callback():
    "HTTPretty should allow registering regexes with requests and giva a proper match to the callback"

    HTTPretty.register_uri(
        HTTPretty.GET,
        re.compile("https://api.yipit.com/v1/deal;brand=(?P<brand_name>\w+)"),
        body=lambda method,uri,headers: [200,headers,uri]
    )

    response = requests.get('https://api.yipit.com/v1/deal;brand=gap?first_name=chuck&last_name=norris')

    expect(response.text).to.equal('https://api.yipit.com/v1/deal;brand=gap?first_name=chuck&last_name=norris')
    expect(HTTPretty.last_request.method).to.equal('GET')
    expect(HTTPretty.last_request.path).to.equal('/v1/deal;brand=gap?first_name=chuck&last_name=norris')

@httprettified
def test_httpretty_should_allow_registering_regexes():
    "HTTPretty should allow registering regexes with requests"

    HTTPretty.register_uri(
        HTTPretty.GET,
        re.compile("https://api.yipit.com/v1/deal;brand=(?P<brand_name>\w+)"),
        body="Found brand",
    )

    response = requests.get('https://api.yipit.com/v1/deal;brand=gap?first_name=chuck&last_name=norris'
                            )
    expect(response.text).to.equal('Found brand')
    expect(HTTPretty.last_request.method).to.equal('GET')
    expect(HTTPretty.last_request.path).to.equal('/v1/deal;brand=gap?first_name=chuck&last_name=norris')


@httprettified
def test_httpretty_provides_easy_access_to_querystrings_with_regexes():
    "HTTPretty should match regexes even if they have a different querystring"

    HTTPretty.register_uri(
        HTTPretty.GET,
        re.compile("https://api.yipit.com/v1/(?P<endpoint>\w+)/$"),
        body="Find the best daily deals"
    )

    response = requests.get('https://api.yipit.com/v1/deals/?foo=bar&foo=baz&chuck=norris')
    expect(response.text).to.equal("Find the best daily deals")
    expect(HTTPretty.last_request.querystring).to.equal({
        'foo': ['bar', 'baz'],
        'chuck': ['norris'],
    })


@httprettified
def test_httpretty_allows_to_chose_if_querystring_should_be_matched():
    "HTTPretty should provide a way to not match regexes that have a different querystring"

    HTTPretty.register_uri(
        HTTPretty.GET,
        re.compile("https://example.org/(?P<endpoint>\w+)/$"),
        body="Nudge, nudge, wink, wink. Know what I mean?",
        match_querystring=True
    )

    response = requests.get('https://example.org/what/')
    expect(response.text).to.equal('Nudge, nudge, wink, wink. Know what I mean?')
    try:
        requests.get('https://example.org/what/?flying=coconuts')
        raised = False
    except requests.ConnectionError:
        raised = True

    assert raised is True


@httprettified
def test_httpretty_should_allow_multiple_methods_for_the_same_uri():
    "HTTPretty should allow registering multiple methods for the same uri"

    url = 'http://test.com/test'
    methods = ['GET', 'POST', 'PUT', 'OPTIONS']
    for method in methods:
        HTTPretty.register_uri(
            getattr(HTTPretty, method),
            url,
            method
        )

    for method in methods:
        request_action = getattr(requests, method.lower())
        expect(request_action(url).text).to.equal(method)


@httprettified
def test_httpretty_should_allow_registering_regexes_with_streaming_responses():
    "HTTPretty should allow registering regexes with streaming responses"
    import os
    os.environ['DEBUG'] = 'true'

    def my_callback(request, url, headers):
        request.body.should.equal(b'hithere')
        return 200, headers, "Received"

    HTTPretty.register_uri(
        HTTPretty.POST,
        re.compile("https://api.yipit.com/v1/deal;brand=(?P<brand_name>\w+)"),
        body=my_callback,
    )

    def gen():
        yield b'hi'
        yield b'there'

    response = requests.post(
        'https://api.yipit.com/v1/deal;brand=gap?first_name=chuck&last_name=norris',
        data=gen(),
    )
    expect(response.content).to.equal(b"Received")
    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.path).to.equal('/v1/deal;brand=gap?first_name=chuck&last_name=norris')


@httprettified
def test_httpretty_should_allow_multiple_responses_with_multiple_methods():
    "HTTPretty should allow multiple responses when binding multiple methods to the same uri"

    url = 'http://test.com/list'

    #add get responses
    HTTPretty.register_uri(HTTPretty.GET, url,
                           responses=[HTTPretty.Response(body='a'),
                                      HTTPretty.Response(body='b')
                           ]
    )

    #add post responses
    HTTPretty.register_uri(HTTPretty.POST, url,
                           responses=[HTTPretty.Response(body='c'),
                                      HTTPretty.Response(body='d')
                           ]
    )

    expect(requests.get(url).text).to.equal('a')
    expect(requests.post(url).text).to.equal('c')

    expect(requests.get(url).text).to.equal('b')
    expect(requests.get(url).text).to.equal('b')
    expect(requests.get(url).text).to.equal('b')

    expect(requests.post(url).text).to.equal('d')
    expect(requests.post(url).text).to.equal('d')
    expect(requests.post(url).text).to.equal('d')


@httprettified
def test_httpretty_should_normalize_url_patching():
    "HTTPretty should normalize all url patching"

    HTTPretty.register_uri(
        HTTPretty.GET,
        "http://yipit.com/foo(bar)",
        body="Find the best daily deals")

    response = requests.get('http://yipit.com/foo%28bar%29')
    expect(response.text).to.equal('Find the best daily deals')


@httprettified
def test_lack_of_trailing_slash():
    ("HTTPretty should automatically append a slash to given urls")
    url = 'http://www.youtube.com'
    HTTPretty.register_uri(HTTPretty.GET, url, body='')
    response = requests.get(url)
    response.status_code.should.equal(200)


@httprettified
def test_unicode_querystrings():
    ("Querystrings should accept unicode characters")
    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/login",
                           body="Find the best daily deals")
    requests.get('http://yipit.com/login?user=Gabriel+Falcão')
    expect(HTTPretty.last_request.querystring['user'][0]).should.be.equal('Gabriel Falcão')


@use_tornado_server
def test_recording_calls():
    ("HTTPretty should be able to record calls")
    # Given a destination path:
    destination = FIXTURE_FILE("recording-.json")

    # When I record some calls
    with HTTPretty.record(destination):
        requests.get(server_url("/foobar?name=Gabriel&age=25"))
        requests.post(server_url("/foobar"), data=json.dumps({'test': '123'}))

    # Then the destination path should exist
    os.path.exists(destination).should.be.true

    # And the contents should be json
    raw = open(destination).read()
    json.loads.when.called_with(raw).should_not.throw(ValueError)

    # And the contents should be expected
    data = json.loads(raw)
    data.should.be.a(list)
    data.should.have.length_of(2)

    # And the responses should have the expected keys
    response = data[0]
    response.should.have.key("request").being.length_of(5)
    response.should.have.key("response").being.length_of(3)

    response['request'].should.have.key("method").being.equal("GET")
    response['request'].should.have.key("headers").being.a(dict)
    response['request'].should.have.key("querystring").being.equal({
        "age": [
            "25"
        ],
        "name": [
            "Gabriel"
        ]
    })
    response['response'].should.have.key("status").being.equal(200)
    response['response'].should.have.key("body").being.an(text_type)
    response['response'].should.have.key("headers").being.a(dict)
    response['response']["headers"].should.have.key("server").being.equal("TornadoServer/" + tornado_version)


def test_playing_calls():
    ("HTTPretty should be able to record calls")
    # Given a destination path:
    destination = FIXTURE_FILE("playback-1.json")

    # When I playback some previously recorded calls
    with HTTPretty.playback(destination):
        # And make the expected requests
        response1 = requests.get(server_url("/foobar?name=Gabriel&age=25"))
        response2 = requests.post(server_url("/foobar"), data=json.dumps({'test': '123'}))

    # Then the responses should be the expected
    response1.json().should.equal({"foobar": {"age": "25", "name": "Gabriel"}})
    response2.json().should.equal({"foobar": {}})


@httprettified
def test_py26_callback_response():
    ("HTTPretty should call a callback function *once* and set its return value"
    " as the body of the response requests")

    from mock import Mock

    def _request_callback(request, uri, headers):
        return [200, headers,"The {0} response from {1}".format(decode_utf8(request.method), uri)]

    request_callback = Mock()
    request_callback.side_effect = _request_callback

    HTTPretty.register_uri(
        HTTPretty.POST, "https://api.yahoo.com/test_post",
        body=request_callback)

    response = requests.post(
        "https://api.yahoo.com/test_post",
        {"username": "gabrielfalcao"}
    )
    os.environ['STOP'] = 'true'
    expect(request_callback.call_count).equal(1)


import json


def hello():
    return json.dumps({
        'href': 'http://foobar.com'
    })

########NEW FILE########
__FILENAME__ = test_urllib2
# #!/usr/bin/env python
# -*- coding: utf-8 -*-

# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals

try:
    from urllib.request import urlopen
    import urllib.request as urllib2
except ImportError:
    import urllib2
    urlopen = urllib2.urlopen

from sure import *
from httpretty import HTTPretty, httprettified
from httpretty.core import decode_utf8


@httprettified
@within(two=microseconds)
def test_httpretty_should_mock_a_simple_get_with_urllib2_read():
    "HTTPretty should mock a simple GET with urllib2.read()"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/",
                           body="Find the best daily deals")

    fd = urlopen('http://yipit.com')
    got = fd.read()
    fd.close()

    expect(got).to.equal(b'Find the best daily deals')


@httprettified
@within(two=microseconds)
def test_httpretty_provides_easy_access_to_querystrings(now):
    "HTTPretty should provide an easy access to the querystring"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/",
                           body="Find the best daily deals")

    fd = urllib2.urlopen('http://yipit.com/?foo=bar&foo=baz&chuck=norris')
    fd.read()
    fd.close()

    expect(HTTPretty.last_request.querystring).to.equal({
        'foo': ['bar', 'baz'],
        'chuck': ['norris'],
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_mock_headers_urllib2(now):
    "HTTPretty should mock basic headers with urllib2"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/",
                           body="this is supposed to be the response",
                           status=201)

    request = urlopen('http://github.com')

    headers = dict(request.headers)
    request.close()

    expect(request.code).to.equal(201)
    expect(headers).to.equal({
        'content-type': 'text/plain; charset=utf-8',
        'connection': 'close',
        'content-length': '35',
        'status': '201',
        'server': 'Python/HTTPretty',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_adding_and_overwritting_urllib2(now):
    "HTTPretty should allow adding and overwritting headers with urllib2"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/",
                           body="this is supposed to be the response",
                           adding_headers={
                               'Server': 'Apache',
                               'Content-Length': '27',
                               'Content-Type': 'application/json',
                           })

    request = urlopen('http://github.com')
    headers = dict(request.headers)
    request.close()

    expect(request.code).to.equal(200)
    expect(headers).to.equal({
        'content-type': 'application/json',
        'connection': 'close',
        'content-length': '27',
        'status': '200',
        'server': 'Apache',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_forcing_headers_urllib2():
    "HTTPretty should allow forcing headers with urllib2"

    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/",
                           body="this is supposed to be the response",
                           forcing_headers={
                               'Content-Type': 'application/xml',
                           })

    request = urlopen('http://github.com')
    headers = dict(request.headers)
    request.close()

    expect(headers).to.equal({
        'content-type': 'application/xml',
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_allow_adding_and_overwritting_by_kwargs_u2(now):
    "HTTPretty should allow adding and overwritting headers by " \
    "keyword args with urllib2"

    body = "this is supposed to be the response, indeed"
    HTTPretty.register_uri(HTTPretty.GET, "http://github.com/",
                           body=body,
                           server='Apache',
                           content_length=len(body),
                           content_type='application/json')

    request = urlopen('http://github.com')
    headers = dict(request.headers)
    request.close()

    expect(request.code).to.equal(200)
    expect(headers).to.equal({
        'content-type': 'application/json',
        'connection': 'close',
        'content-length': str(len(body)),
        'status': '200',
        'server': 'Apache',
        'date': now.strftime('%a, %d %b %Y %H:%M:%S GMT'),
    })


@httprettified
@within(two=microseconds)
def test_httpretty_should_support_a_list_of_successive_responses_urllib2(now):
    "HTTPretty should support adding a list of successive " \
    "responses with urllib2"

    HTTPretty.register_uri(
        HTTPretty.GET, "https://api.yahoo.com/test",
        responses=[
            HTTPretty.Response(body="first response", status=201),
            HTTPretty.Response(body='second and last response', status=202),
        ])

    request1 = urlopen('https://api.yahoo.com/test')
    body1 = request1.read()
    request1.close()

    expect(request1.code).to.equal(201)
    expect(body1).to.equal(b'first response')

    request2 = urlopen('https://api.yahoo.com/test')
    body2 = request2.read()
    request2.close()
    expect(request2.code).to.equal(202)
    expect(body2).to.equal(b'second and last response')

    request3 = urlopen('https://api.yahoo.com/test')
    body3 = request3.read()
    request3.close()
    expect(request3.code).to.equal(202)
    expect(body3).to.equal(b'second and last response')


@httprettified
@within(two=microseconds)
def test_can_inspect_last_request(now):
    "HTTPretty.last_request is a mimetools.Message request from last match"

    HTTPretty.register_uri(HTTPretty.POST, "http://api.github.com/",
                           body='{"repositories": ["HTTPretty", "lettuce"]}')

    request = urllib2.Request(
        'http://api.github.com',
        b'{"username": "gabrielfalcao"}',
        {
            'content-type': 'text/json',
        },
    )
    fd = urlopen(request)
    got = fd.read()
    fd.close()

    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.body).to.equal(
        b'{"username": "gabrielfalcao"}',
    )
    expect(HTTPretty.last_request.headers['content-type']).to.equal(
        'text/json',
    )
    expect(got).to.equal(b'{"repositories": ["HTTPretty", "lettuce"]}')


@httprettified
@within(two=microseconds)
def test_can_inspect_last_request_with_ssl(now):
    "HTTPretty.last_request is recorded even when mocking 'https' (SSL)"

    HTTPretty.register_uri(HTTPretty.POST, "https://secure.github.com/",
                           body='{"repositories": ["HTTPretty", "lettuce"]}')

    request = urllib2.Request(
        'https://secure.github.com',
        b'{"username": "gabrielfalcao"}',
        {
            'content-type': 'text/json',
        },
    )
    fd = urlopen(request)
    got = fd.read()
    fd.close()

    expect(HTTPretty.last_request.method).to.equal('POST')
    expect(HTTPretty.last_request.body).to.equal(
        b'{"username": "gabrielfalcao"}',
    )
    expect(HTTPretty.last_request.headers['content-type']).to.equal(
        'text/json',
    )
    expect(got).to.equal(b'{"repositories": ["HTTPretty", "lettuce"]}')


@httprettified
@within(two=microseconds)
def test_httpretty_ignores_querystrings_from_registered_uri():
    "HTTPretty should mock a simple GET with urllib2.read()"

    HTTPretty.register_uri(HTTPretty.GET, "http://yipit.com/?id=123",
                           body="Find the best daily deals")

    fd = urlopen('http://yipit.com/?id=123')
    got = fd.read()
    fd.close()

    expect(got).to.equal(b'Find the best daily deals')
    expect(HTTPretty.last_request.method).to.equal('GET')
    expect(HTTPretty.last_request.path).to.equal('/?id=123')


@httprettified
@within(two=microseconds)
def test_callback_response(now):
    ("HTTPretty should all a callback function to be set as the body with"
      " urllib2")

    def request_callback(request, uri, headers):
        return [200, headers, "The {0} response from {1}".format(decode_utf8(request.method), uri)]

    HTTPretty.register_uri(
        HTTPretty.GET, "https://api.yahoo.com/test",
        body=request_callback)

    fd = urllib2.urlopen('https://api.yahoo.com/test')
    got = fd.read()
    fd.close()

    expect(got).to.equal(b"The GET response from https://api.yahoo.com/test")

    HTTPretty.register_uri(
        HTTPretty.POST, "https://api.yahoo.com/test_post",
        body=request_callback)

    request = urllib2.Request(
        "https://api.yahoo.com/test_post",
        b'{"username": "gabrielfalcao"}',
        {
            'content-type': 'text/json',
        },
    )
    fd = urllib2.urlopen(request)
    got = fd.read()
    fd.close()

    expect(got).to.equal(b"The POST response from https://api.yahoo.com/test_post")


@httprettified
def test_httpretty_should_allow_registering_regexes():
    "HTTPretty should allow registering regexes with urllib2"

    HTTPretty.register_uri(
        HTTPretty.GET,
        re.compile("https://api.yipit.com/v1/deal;brand=(?P<brand_name>\w+)"),
        body="Found brand",
    )

    request = urllib2.Request(
        "https://api.yipit.com/v1/deal;brand=GAP",
    )
    fd = urllib2.urlopen(request)
    got = fd.read()
    fd.close()

    expect(got).to.equal(b"Found brand")

########NEW FILE########
__FILENAME__ = test_core
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import errno
from datetime import datetime

from mock import Mock, patch, call
from sure import expect

from httpretty.compat import StringIO
from httpretty.core import HTTPrettyRequest, FakeSSLSocket, fakesock, httpretty


class SocketErrorStub(Exception):
    def __init__(self, errno):
        self.errno = errno


def test_request_stubs_internals():
    ("HTTPrettyRequest is a BaseHTTPRequestHandler that replaces "
     "real socket file descriptors with in-memory ones")

    # Given a valid HTTP request header string
    headers = "\r\n".join([
        'POST /somewhere/?name=foo&age=bar HTTP/1.1',
        'accept-encoding: identity',
        'host: github.com',
        'content-type: application/json',
        'connection: close',
        'user-agent: Python-urllib/2.7',
    ])

    # When I create a HTTPrettyRequest with an empty body
    request = HTTPrettyRequest(headers, body='')

    # Then it should have parsed the headers
    dict(request.headers).should.equal({
        'accept-encoding': 'identity',
        'connection': 'close',
        'content-type': 'application/json',
        'host': 'github.com',
        'user-agent': 'Python-urllib/2.7'
    })

    # And the `rfile` should be a StringIO
    type_as_str = StringIO.__module__ + '.' + StringIO.__name__

    request.should.have.property('rfile').being.a(type_as_str)

    # And the `wfile` should be a StringIO
    request.should.have.property('wfile').being.a(type_as_str)

    # And the `method` should be available
    request.should.have.property('method').being.equal('POST')



def test_request_parse_querystring():
    ("HTTPrettyRequest#parse_querystring should parse unicode data")

    # Given a request string containing a unicode encoded querystring

    headers = "\r\n".join([
        'POST /create?name=Gabriel+Falcão HTTP/1.1',
        'Content-Type: multipart/form-data',
    ])

    # When I create a HTTPrettyRequest with an empty body
    request = HTTPrettyRequest(headers, body='')

    # Then it should have a parsed querystring
    request.querystring.should.equal({'name': ['Gabriel Falcão']})


def test_request_parse_body_when_it_is_application_json():
    ("HTTPrettyRequest#parse_request_body recognizes the "
     "content-type `application/json` and parses it")

    # Given a request string containing a unicode encoded querystring
    headers = "\r\n".join([
        'POST /create HTTP/1.1',
        'Content-Type: application/json',
    ])
    # And a valid json body
    body = json.dumps({'name': 'Gabriel Falcão'})

    # When I create a HTTPrettyRequest with that data
    request = HTTPrettyRequest(headers, body)

    # Then it should have a parsed body
    request.parsed_body.should.equal({'name': 'Gabriel Falcão'})


def test_request_parse_body_when_it_is_text_json():
    ("HTTPrettyRequest#parse_request_body recognizes the "
     "content-type `text/json` and parses it")

    # Given a request string containing a unicode encoded querystring
    headers = "\r\n".join([
        'POST /create HTTP/1.1',
        'Content-Type: text/json',
    ])
    # And a valid json body
    body = json.dumps({'name': 'Gabriel Falcão'})

    # When I create a HTTPrettyRequest with that data
    request = HTTPrettyRequest(headers, body)

    # Then it should have a parsed body
    request.parsed_body.should.equal({'name': 'Gabriel Falcão'})


def test_request_parse_body_when_it_is_urlencoded():
    ("HTTPrettyRequest#parse_request_body recognizes the "
     "content-type `application/x-www-form-urlencoded` and parses it")

    # Given a request string containing a unicode encoded querystring
    headers = "\r\n".join([
        'POST /create HTTP/1.1',
        'Content-Type: application/x-www-form-urlencoded',
    ])
    # And a valid urlencoded body
    body = "name=Gabriel+Falcão&age=25&projects=httpretty&projects=sure&projects=lettuce"

    # When I create a HTTPrettyRequest with that data
    request = HTTPrettyRequest(headers, body)

    # Then it should have a parsed body
    request.parsed_body.should.equal({
        'name': ['Gabriel Falcão'],
        'age': ["25"],
        'projects': ["httpretty", "sure", "lettuce"]
    })


def test_request_parse_body_when_unrecognized():
    ("HTTPrettyRequest#parse_request_body returns the value as "
     "is if the Content-Type is not recognized")

    # Given a request string containing a unicode encoded querystring
    headers = "\r\n".join([
        'POST /create HTTP/1.1',
        'Content-Type: whatever',
    ])
    # And a valid urlencoded body
    body = "foobar:\nlalala"

    # When I create a HTTPrettyRequest with that data
    request = HTTPrettyRequest(headers, body)

    # Then it should have a parsed body
    request.parsed_body.should.equal("foobar:\nlalala")


def test_request_string_representation():
    ("HTTPrettyRequest should have a debug-friendly "
     "string representation")

    # Given a request string containing a unicode encoded querystring
    headers = "\r\n".join([
        'POST /create HTTP/1.1',
        'Content-Type: JPEG-baby',
    ])
    # And a valid urlencoded body
    body = "foobar:\nlalala"

    # When I create a HTTPrettyRequest with that data
    request = HTTPrettyRequest(headers, body)

    # Then its string representation should show the headers and the body
    str(request).should.equal('<HTTPrettyRequest("JPEG-baby", total_headers=1, body_length=14)>')


def test_fake_ssl_socket_proxies_its_ow_socket():
    ("FakeSSLSocket is a simpel wrapper around its own socket, "
     "which was designed to be a HTTPretty fake socket")

    # Given a sentinel mock object
    socket = Mock()

    # And a FakeSSLSocket wrapping it
    ssl = FakeSSLSocket(socket)

    # When I make a method call
    ssl.send("FOO")

    # Then it should bypass any method calls to its own socket
    socket.send.assert_called_once_with("FOO")


@patch('httpretty.core.datetime')
def test_fakesock_socket_getpeercert(dt):
    ("fakesock.socket#getpeercert should return a hardcoded fake certificate")
    # Background:
    dt.now.return_value = datetime(2013, 10, 4, 4, 20, 0)

    # Given a fake socket instance
    socket = fakesock.socket()

    # And that it's bound to some host and port
    socket.connect(('somewhere.com', 80))

    # When I retrieve the peer certificate
    certificate = socket.getpeercert()

    # Then it should return a hardcoded value
    certificate.should.equal({
        u'notAfter': 'Sep 29 04:20:00 GMT',
        u'subject': (
            ((u'organizationName', u'*.somewhere.com'),),
            ((u'organizationalUnitName', u'Domain Control Validated'),),
            ((u'commonName', u'*.somewhere.com'),)),
        u'subjectAltName': (
            (u'DNS', u'*somewhere.com'),
            (u'DNS', u'somewhere.com'),
            (u'DNS', u'*')
        )
    })


def test_fakesock_socket_ssl():
    ("fakesock.socket#ssl should take a socket instance and return itself")
    # Given a fake socket instance
    socket = fakesock.socket()

    # And a stubbed socket sentinel
    sentinel = Mock()

    # When I call `ssl` on that mock
    result = socket.ssl(sentinel)

    # Then it should have returned its first argument
    result.should.equal(sentinel)



@patch('httpretty.core.old_socket')
@patch('httpretty.core.POTENTIAL_HTTP_PORTS')
def test_fakesock_socket_connect_fallback(POTENTIAL_HTTP_PORTS, old_socket):
    ("fakesock.socket#connect should open a real connection if the "
     "given port is not a potential http port")
    # Background: the potential http ports are 80 and 443
    POTENTIAL_HTTP_PORTS.__contains__.side_effect = lambda other: int(other) in (80, 443)

    # Given a fake socket instance
    socket = fakesock.socket()

    # When it is connected to a remote server in a port that isn't 80 nor 443
    socket.connect(('somewhere.com', 42))

    # Then it should have open a real connection in the background
    old_socket.return_value.connect.assert_called_once_with(('somewhere.com', 42))

    # And _closed is set to False
    socket._closed.should.be.false


@patch('httpretty.core.old_socket')
def test_fakesock_socket_close(old_socket):
    ("fakesock.socket#close should close the actual socket in case "
     "it's not http and _closed is False")
    # Given a fake socket instance that is synthetically open
    socket = fakesock.socket()
    socket._closed = False

    # When I close it
    socket.close()

    # Then its real socket should have been closed
    old_socket.return_value.close.assert_called_once_with()

    # And _closed is set to True
    socket._closed.should.be.true


@patch('httpretty.core.old_socket')
def test_fakesock_socket_makefile(old_socket):
    ("fakesock.socket#makefile should set the mode, "
     "bufsize and return its mocked file descriptor")

    # Given a fake socket that has a mocked Entry associated with it
    socket = fakesock.socket()
    socket._entry = Mock()

    # When I call makefile()
    fd = socket.makefile(mode='rw', bufsize=512)

    # Then it should have returned the socket's own filedescriptor
    expect(fd).to.equal(socket.fd)
    # And the mode should have been set in the socket instance
    socket._mode.should.equal('rw')
    # And the bufsize should have been set in the socket instance
    socket._bufsize.should.equal(512)

    # And the entry should have been filled with that filedescriptor
    socket._entry.fill_filekind.assert_called_once_with(fd)


@patch('httpretty.core.old_socket')
def test_fakesock_socket_real_sendall(old_socket):
    ("fakesock.socket#real_sendall sends data and buffers "
     "the response in the file descriptor")
    # Background: the real socket will stop returning bytes after the
    # first call
    real_socket = old_socket.return_value
    real_socket.recv.side_effect = [b'response from server', b""]

    # Given a fake socket
    socket = fakesock.socket()

    # When I call real_sendall with data, some args and kwargs
    socket.real_sendall(b"SOMEDATA", b'some extra args...', foo=b'bar')

    # Then it should have called sendall in the real socket
    real_socket.sendall.assert_called_once_with(b"SOMEDATA", b'some extra args...', foo=b'bar')

    # And the timeout was set to 0
    real_socket.settimeout.assert_called_once_with(0)

    # And recv was called with the bufsize
    real_socket.recv.assert_has_calls([
        call(16),
        call(16),
    ])

    # And the buffer should contain the data from the server
    socket.fd.getvalue().should.equal(b"response from server")

    # And connect was never called
    real_socket.connect.called.should.be.false


@patch('httpretty.core.old_socket')
@patch('httpretty.core.socket')
def test_fakesock_socket_real_sendall_continue_eagain(socket, old_socket):
    ("fakesock.socket#real_sendall should continue if the socket error was EAGAIN")
    socket.error = SocketErrorStub
    # Background: the real socket will stop returning bytes after the
    # first call
    real_socket = old_socket.return_value
    real_socket.recv.side_effect = [SocketErrorStub(errno.EAGAIN), b'after error', b""]

    # Given a fake socket
    socket = fakesock.socket()


    # When I call real_sendall with data, some args and kwargs
    socket.real_sendall(b"SOMEDATA", b'some extra args...', foo=b'bar')

    # Then it should have called sendall in the real socket
    real_socket.sendall.assert_called_once_with(b"SOMEDATA", b'some extra args...', foo=b'bar')

    # And the timeout was set to 0
    real_socket.settimeout.assert_called_once_with(0)

    # And recv was called with the bufsize
    real_socket.recv.assert_has_calls([
        call(16),
        call(16),
    ])

    # And the buffer should contain the data from the server
    socket.fd.getvalue().should.equal(b"after error")

    # And connect was never called
    real_socket.connect.called.should.be.false


@patch('httpretty.core.old_socket')
@patch('httpretty.core.socket')
def test_fakesock_socket_real_sendall_socket_error(socket, old_socket):
    ("fakesock.socket#real_sendall should continue if the socket error was EAGAIN")
    socket.error = SocketErrorStub
    # Background: the real socket will stop returning bytes after the
    # first call
    real_socket = old_socket.return_value
    real_socket.recv.side_effect = [SocketErrorStub(42), b'after error', ""]

    # Given a fake socket
    socket = fakesock.socket()

    # When I call real_sendall with data, some args and kwargs
    socket.real_sendall(b"SOMEDATA", b'some extra args...', foo=b'bar')

    # Then it should have called sendall in the real socket
    real_socket.sendall.assert_called_once_with(b"SOMEDATA", b'some extra args...', foo=b'bar')

    # And the timeout was set to 0
    real_socket.settimeout.assert_called_once_with(0)

    # And recv was called with the bufsize
    real_socket.recv.assert_called_once_with(16)

    # And the buffer should contain the data from the server
    socket.fd.getvalue().should.equal(b"")

    # And connect was never called
    real_socket.connect.called.should.be.false


@patch('httpretty.core.old_socket')
@patch('httpretty.core.POTENTIAL_HTTP_PORTS')
def test_fakesock_socket_real_sendall_when_http(POTENTIAL_HTTP_PORTS, old_socket):
    ("fakesock.socket#real_sendall should connect before sending data")
    # Background: the real socket will stop returning bytes after the
    # first call
    real_socket = old_socket.return_value
    real_socket.recv.side_effect = [b'response from foobar :)', b""]

    # And the potential http port is 4000
    POTENTIAL_HTTP_PORTS.__contains__.side_effect = lambda other: int(other) == 4000

    # Given a fake socket
    socket = fakesock.socket()

    # When I call connect to a server in a port that is considered HTTP
    socket.connect(('foobar.com', 4000))

    # And send some data
    socket.real_sendall(b"SOMEDATA")

    # Then connect should have been called
    real_socket.connect.assert_called_once_with(('foobar.com', 4000))

    # And the timeout was set to 0
    real_socket.settimeout.assert_called_once_with(0)

    # And recv was called with the bufsize
    real_socket.recv.assert_has_calls([
        call(16),
        call(16),
    ])

    # And the buffer should contain the data from the server
    socket.fd.getvalue().should.equal(b"response from foobar :)")


@patch('httpretty.core.old_socket')
@patch('httpretty.core.httpretty')
@patch('httpretty.core.POTENTIAL_HTTP_PORTS')
def test_fakesock_socket_sendall_with_valid_requestline(POTENTIAL_HTTP_PORTS, httpretty, old_socket):
    ("fakesock.socket#sendall should create an entry if it's given a valid request line")
    matcher = Mock()
    info = Mock()
    httpretty.match_uriinfo.return_value = (matcher, info)
    httpretty.register_uri(httpretty.GET, 'http://foo.com/foobar')

    # Background:
    # using a subclass of socket that mocks out real_sendall
    class MySocket(fakesock.socket):
        def real_sendall(self, data, *args, **kw):
            raise AssertionError('should never call this...')

    # Given an instance of that socket
    socket = MySocket()

    # And that is is considered http
    socket.connect(('foo.com', 80))

    # When I try to send data
    socket.sendall(b"GET /foobar HTTP/1.1\r\nContent-Type: application/json\r\n\r\n")


@patch('httpretty.core.old_socket')
@patch('httpretty.core.httpretty')
@patch('httpretty.core.POTENTIAL_HTTP_PORTS')
def test_fakesock_socket_sendall_with_valid_requestline(POTENTIAL_HTTP_PORTS, httpretty, old_socket):
    ("fakesock.socket#sendall should create an entry if it's given a valid request line")
    matcher = Mock()
    info = Mock()
    httpretty.match_uriinfo.return_value = (matcher, info)
    httpretty.register_uri(httpretty.GET, 'http://foo.com/foobar')

    # Background:
    # using a subclass of socket that mocks out real_sendall
    class MySocket(fakesock.socket):
        def real_sendall(self, data, *args, **kw):
            raise AssertionError('should never call this...')

    # Given an instance of that socket
    socket = MySocket()

    # And that is is considered http
    socket.connect(('foo.com', 80))

    # When I try to send data
    socket.sendall(b"GET /foobar HTTP/1.1\r\nContent-Type: application/json\r\n\r\n")


@patch('httpretty.core.old_socket')
@patch('httpretty.core.POTENTIAL_HTTP_PORTS')
def test_fakesock_socket_sendall_with_body_data_no_entry(POTENTIAL_HTTP_PORTS, old_socket):
    ("fakesock.socket#sendall should call real_sendall when not parsing headers and there is no entry")
    # Background:
    # Using a subclass of socket that mocks out real_sendall
    class MySocket(fakesock.socket):
        def real_sendall(self, data):
            data.should.equal(b'BLABLABLABLA')
            return 'cool'

    # Given an instance of that socket
    socket = MySocket()
    socket._entry = None

    # And that is is considered http
    socket.connect(('foo.com', 80))

    # When I try to send data
    result = socket.sendall(b"BLABLABLABLA")

    # Then the result should be the return value from real_sendall
    result.should.equal('cool')


@patch('httpretty.core.old_socket')
@patch('httpretty.core.POTENTIAL_HTTP_PORTS')
def test_fakesock_socket_sendall_with_body_data_with_entry(POTENTIAL_HTTP_PORTS, old_socket):
    ("fakesock.socket#sendall should call real_sendall when not ")
    # Background:
    # Using a subclass of socket that mocks out real_sendall
    class MySocket(fakesock.socket):
        def real_sendall(self, data):
            raise AssertionError('should have never been called')
    # Using a mocked entry
    entry = Mock()
    entry.request.headers = {}
    entry.request.body = b''

    # Given an instance of that socket
    socket = MySocket()
    socket._entry = entry


    # And that is is considered http
    socket.connect(('foo.com', 80))

    # When I try to send data
    socket.sendall(b"BLABLABLABLA")

    # Then the entry should have that body
    entry.request.body.should.equal(b'BLABLABLABLA')


@patch('httpretty.core.old_socket')
@patch('httpretty.core.POTENTIAL_HTTP_PORTS')
def test_fakesock_socket_sendall_with_body_data_with_chunked_entry(POTENTIAL_HTTP_PORTS, old_socket):
    ("fakesock.socket#sendall should call real_sendall when not ")
    # Background:
    # Using a subclass of socket that mocks out real_sendall
    class MySocket(fakesock.socket):
        def real_sendall(self, data):
            raise AssertionError('should have never been called')
    # Using a mocked entry
    entry = Mock()
    entry.request.headers = {
        'transfer-encoding': 'chunked',
    }
    entry.request.body = b''

    # Given an instance of that socket
    socket = MySocket()
    socket._entry = entry

    # And that is is considered http
    socket.connect(('foo.com', 80))

    # When I try to send data
    socket.sendall(b"BLABLABLABLA")

    # Then the entry should have that body
    httpretty.last_request.body.should.equal(b'BLABLABLABLA')

########NEW FILE########
__FILENAME__ = test_http
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from httpretty.http import parse_requestline


def test_parse_request_line_connect():
    ("parse_requestline should parse the CONNECT method appropriately")

    # Given a valid request line string that has the CONNECT method
    line = "CONNECT / HTTP/1.1"

    # When I parse it
    result = parse_requestline(line)

    # Then it should return a tuple
    result.should.equal(("CONNECT", "/", "1.1"))

########NEW FILE########
__FILENAME__ = test_httpretty
# #!/usr/bin/env python
# -*- coding: utf-8 -*-

# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2013>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
from __future__ import unicode_literals
import json
from sure import expect
from httpretty import HTTPretty, HTTPrettyError, core
from httpretty.core import URIInfo, BaseClass, Entry, FakeSockFile, HTTPrettyRequest
from httpretty.http import STATUSES

try:
    from mock import MagicMock
except ImportError:
    from unittest.mock import MagicMock

TEST_HEADER = """
GET /test/test.html HTTP/1.1
Host: www.host1.com:80
Content-Type: %(content_type)s
"""


def test_httpretty_should_raise_proper_exception_on_inconsistent_length():
    "HTTPretty should raise proper exception on inconsistent Content-Length / "\
       "registered response body"
    expect(HTTPretty.register_uri).when.called_with(
      HTTPretty.GET,
        "http://github.com/gabrielfalcao",
        body="that's me!",
        adding_headers={
            'Content-Length': '999'
        }
    ).to.throw(
        HTTPrettyError,
        'HTTPretty got inconsistent parameters. The header Content-Length you registered expects size "999" '
        'but the body you registered for that has actually length "10".'
    )


def test_httpretty_should_raise_on_socket_send_when_uri_registered():
    """HTTPretty should raise a RuntimeError when the fakesocket is used in
    an invalid usage.
    """
    import socket
    HTTPretty.enable()

    HTTPretty.register_uri(HTTPretty.GET,
                           'http://127.0.0.1:5000')
    expect(core.POTENTIAL_HTTP_PORTS).to.be.equal(set([80, 443, 5000]))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 5000))
    expect(sock.send).when.called_with(b'whatever').to.throw(RuntimeError)
    sock.close()

    # restore the previous value
    core.POTENTIAL_HTTP_PORTS.remove(5000)
    HTTPretty.reset()
    HTTPretty.disable()


def test_httpretty_should_not_raise_on_socket_send_when_uri_not_registered():
    """HTTPretty should not raise a RuntimeError when the fakesocket is used in
    an invalid usage.
    """
    import socket
    HTTPretty.enable()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    sock.setblocking(0)
    expect(sock.sendto).when.called_with(b'whatever',
                                         ('127.0.0.1', 53)
                                         ).should_not.throw(RuntimeError)

    sock.close()
    HTTPretty.reset()
    HTTPretty.disable()


def test_does_not_have_last_request_by_default():
    'HTTPretty.last_request is a dummy object by default'
    HTTPretty.reset()

    expect(HTTPretty.last_request.headers).to.be.empty
    expect(HTTPretty.last_request.body).to.be.empty


def test_status_codes():
    "HTTPretty supports N status codes"

    expect(STATUSES).to.equal({
        100: "Continue",
        101: "Switching Protocols",
        102: "Processing",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        207: "Multi-Status",
        208: "Already Reported",
        226: "IM Used",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        306: "Switch Proxy",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request a Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Request Entity Too Large",
        414: "Request-URI Too Long",
        415: "Unsupported Media Type",
        416: "Requested Range Not Satisfiable",
        417: "Expectation Failed",
        418: "I'm a teapot",
        420: "Enhance Your Calm",
        422: "Unprocessable Entity",
        423: "Locked",
        424: "Failed Dependency",
        424: "Method Failure",
        425: "Unordered Collection",
        426: "Upgrade Required",
        428: "Precondition Required",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        444: "No Response",
        449: "Retry With",
        450: "Blocked by Windows Parental Controls",
        451: "Unavailable For Legal Reasons",
        451: "Redirect",
        494: "Request Header Too Large",
        495: "Cert Error",
        496: "No Cert",
        497: "HTTP to HTTPS",
        499: "Client Closed Request",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
        506: "Variant Also Negotiates",
        507: "Insufficient Storage",
        508: "Loop Detected",
        509: "Bandwidth Limit Exceeded",
        510: "Not Extended",
        511: "Network Authentication Required",
        598: "Network read timeout error",
        599: "Network connect timeout error",
    })

def test_uri_info_full_url():
    uri_info = URIInfo(
        username='johhny',
        password='password',
        hostname=b'google.com',
        port=80,
        path=b'/',
        query=b'foo=bar&baz=test',
        fragment='',
        scheme='',
    )

    expect(uri_info.full_url()).to.equal(
        "http://johhny:password@google.com/?foo=bar&baz=test"
    )

    expect(uri_info.full_url(use_querystring=False)).to.equal(
        "http://johhny:password@google.com/"
    )

def test_uri_info_eq_ignores_case():
    """Test that URIInfo.__eq__ method ignores case for
    hostname matching.
    """
    uri_info_uppercase = URIInfo(
        username='johhny',
        password='password',
        hostname=b'GOOGLE.COM',
        port=80,
        path=b'/',
        query=b'foo=bar&baz=test',
        fragment='',
        scheme='',
    )
    uri_info_lowercase = URIInfo(
        username='johhny',
        password='password',
        hostname=b'google.com',
        port=80,
        path=b'/',
        query=b'foo=bar&baz=test',
        fragment='',
        scheme='',
    )
    expect(uri_info_uppercase).to.equal(uri_info_lowercase)

def test_global_boolean_enabled():
    expect(HTTPretty.is_enabled()).to.be.falsy
    HTTPretty.enable()
    expect(HTTPretty.is_enabled()).to.be.truthy
    HTTPretty.disable()
    expect(HTTPretty.is_enabled()).to.be.falsy


def test_py3kobject_implements_valid__repr__based_on__str__():
    class MyObject(BaseClass):
        def __str__(self):
            return 'hi'

    myobj = MyObject()
    expect(repr(myobj)).to.be.equal('hi')


def test_Entry_class_normalizes_headers():
    entry = Entry(HTTPretty.GET, 'http://example.com', 'example',
                  host='example.com', cache_control='no-cache', x_forward_for='proxy')

    expect(entry.adding_headers).to.equal({
       'Host':'example.com',
       'Cache-Control':'no-cache',
       'X-Forward-For':'proxy'
    })


def test_Entry_class_counts_multibyte_characters_in_bytes():
    entry = Entry(HTTPretty.GET, 'http://example.com', 'こんにちは')
    buf = FakeSockFile()
    entry.fill_filekind(buf)
    response = buf.getvalue()
    expect(b'content-length: 15\n').to.be.within(response)


def test_fake_socket_passes_through_setblocking():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.setblocking).called_with(0).should_not.throw(AttributeError)
    s.truesock.setblocking.assert_called_with(0)

def test_fake_socket_passes_through_fileno():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.fileno).called_with().should_not.throw(AttributeError)
    s.truesock.fileno.assert_called_with()


def test_fake_socket_passes_through_getsockopt():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.getsockopt).called_with(socket.SOL_SOCKET, 1).should_not.throw(AttributeError)
    s.truesock.getsockopt.assert_called_with(socket.SOL_SOCKET, 1)

def test_fake_socket_passes_through_bind():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.bind).called_with().should_not.throw(AttributeError)
    s.truesock.bind.assert_called_with()

def test_fake_socket_passes_through_connect_ex():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.connect_ex).called_with().should_not.throw(AttributeError)
    s.truesock.connect_ex.assert_called_with()

def test_fake_socket_passes_through_listen():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.listen).called_with().should_not.throw(AttributeError)
    s.truesock.listen.assert_called_with()

def test_fake_socket_passes_through_getpeername():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.getpeername).called_with().should_not.throw(AttributeError)
    s.truesock.getpeername.assert_called_with()

def test_fake_socket_passes_through_getsockname():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.getsockname).called_with().should_not.throw(AttributeError)
    s.truesock.getsockname.assert_called_with()

def test_fake_socket_passes_through_gettimeout():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.gettimeout).called_with().should_not.throw(AttributeError)
    s.truesock.gettimeout.assert_called_with()

def test_fake_socket_passes_through_shutdown():
    import socket
    HTTPretty.enable()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.truesock = MagicMock()
    expect(s.shutdown).called_with(socket.SHUT_RD).should_not.throw(AttributeError)
    s.truesock.shutdown.assert_called_with(socket.SHUT_RD)


def test_HTTPrettyRequest_json_body():
    """ A content-type of application/json should parse a valid json body """
    header = TEST_HEADER % {'content_type': 'application/json'}
    test_dict = {'hello': 'world'}
    request = HTTPrettyRequest(header, json.dumps(test_dict))
    expect(request.parsed_body).to.equal(test_dict)


def test_HTTPrettyRequest_invalid_json_body():
    """ A content-type of application/json with an invalid json body should return the content unaltered """
    header = TEST_HEADER % {'content_type': 'application/json'}
    invalid_json = u"{'hello', 'world','thisstringdoesntstops}"
    request = HTTPrettyRequest(header, invalid_json)
    expect(request.parsed_body).to.equal(invalid_json)


def test_HTTPrettyRequest_queryparam():
    """ A content-type of x-www-form-urlencoded with a valid queryparam body should return parsed content """
    header = TEST_HEADER % {'content_type': 'application/x-www-form-urlencoded'}
    valid_queryparam = u"hello=world&this=isavalidquerystring"
    valid_results = {'hello': ['world'], 'this': ['isavalidquerystring']}
    request = HTTPrettyRequest(header, valid_queryparam)
    expect(request.parsed_body).to.equal(valid_results)


def test_HTTPrettyRequest_arbitrarypost():
    """ A non-handled content type request's post body should return the content unaltered """
    header = TEST_HEADER % {'content_type': 'thisis/notarealcontenttype'}
    gibberish_body = "1234567890!@#$%^&*()"
    request = HTTPrettyRequest(header, gibberish_body)
    expect(request.parsed_body).to.equal(gibberish_body)

########NEW FILE########
__FILENAME__ = test_main
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from mock import patch
import httpretty


@patch('httpretty.httpretty')
def test_last_request(original):
    ("httpretty.last_request() should return httpretty.core.last_request")

    httpretty.last_request().should.equal(original.last_request)

########NEW FILE########
