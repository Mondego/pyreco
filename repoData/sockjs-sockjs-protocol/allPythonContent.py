__FILENAME__ = http-quirks
#!/usr/bin/env python

# Http quirks
# ===========
#
# During the work on SockJS few interesting aspects of Http were
# identified. Following tests try to trigger that. If the tests end
# with success - you can be more confident that your web server will
# survive clients that are violating some aspects of http.
#
# This tests aren't really a part of SockJS test suite, it's more
# about verification http quirks.
import unittest2 as unittest
import uuid
import urlparse
import httplib_fork as httplib
import os

test_top_url = os.environ.get('SOCKJS_URL', 'http://localhost:8081')
base_url = test_top_url + '/echo'

def POST_empty(url):
    u = urlparse.urlparse(url)
    if u.scheme == 'http':
        conn = httplib.HTTPConnection(u.netloc)
    elif u.scheme == 'https':
        conn = httplib.HTTPSConnection(u.netloc)
    else:
        assert False, "Unsupported scheme " + u.scheme
    path = u.path + ('?' + u.query if u.query else '')
    conn.request('POST', path)
    res = conn.getresponse()
    headers = dict( (k.lower(), v) for k, v in res.getheaders() )
    body = res.read()
    conn.close()
    return res.status, body, headers

class HttpQuirks(unittest.TestCase):
    def test_emptyContentLengthForPost(self):
        # Doing POST without Content-Length shouldn't break the
        # server (it does break misultin)
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        status, body, _ = POST_empty(trans_url + '/xhr')
        self.assertEqual(body, 'o\n')
        self.assertEqual(status, 200)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = httplib_fork
"""HTTP/1.1 client library

<intro stuff goes here>
<other stuff, too>

HTTPConnection goes through a number of "states", which define when a client
may legally make another request or fetch the response for a particular
request. This diagram details these state transitions:

    (null)
      |
      | HTTPConnection()
      v
    Idle
      |
      | putrequest()
      v
    Request-started
      |
      | ( putheader() )*  endheaders()
      v
    Request-sent
      |
      | response = getresponse()
      v
    Unread-response   [Response-headers-read]
      |\____________________
      |                     |
      | response.read()     | putrequest()
      v                     v
    Idle                  Req-started-unread-response
                     ______/|
                   /        |
   response.read() |        | ( putheader() )*  endheaders()
                   v        v
       Request-started    Req-sent-unread-response
                            |
                            | response.read()
                            v
                          Request-sent

This diagram presents the following rules:
  -- a second request may not be started until {response-headers-read}
  -- a response [object] cannot be retrieved until {request-sent}
  -- there is no differentiation between an unread response body and a
     partially read response body

Note: this enforcement is applied by the HTTPConnection class. The
      HTTPResponse class does not enforce this state machine, which
      implies sophisticated clients may accelerate the request/response
      pipeline. Caution should be taken, though: accelerating the states
      beyond the above pattern may imply knowledge of the server's
      connection-close behavior for certain requests. For example, it
      is impossible to tell whether the server will close the connection
      UNTIL the response headers have been read; this means that further
      requests cannot be placed into the pipeline until it is known that
      the server will NOT be closing the connection.

Logical State                  __state            __response
-------------                  -------            ----------
Idle                           _CS_IDLE           None
Request-started                _CS_REQ_STARTED    None
Request-sent                   _CS_REQ_SENT       None
Unread-response                _CS_IDLE           <response_class>
Req-started-unread-response    _CS_REQ_STARTED    <response_class>
Req-sent-unread-response       _CS_REQ_SENT       <response_class>
"""

from array import array
import os
import socket
from sys import py3kwarning
from urlparse import urlsplit
import warnings
with warnings.catch_warnings():
    if py3kwarning:
        warnings.filterwarnings("ignore", ".*mimetools has been removed",
                                DeprecationWarning)
    import mimetools

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

__all__ = ["HTTP", "HTTPResponse", "HTTPConnection",
           "HTTPException", "NotConnected", "UnknownProtocol",
           "UnknownTransferEncoding", "UnimplementedFileMode",
           "IncompleteRead", "InvalidURL", "ImproperConnectionState",
           "CannotSendRequest", "CannotSendHeader", "ResponseNotReady",
           "BadStatusLine", "error", "responses"]

HTTP_PORT = 80
HTTPS_PORT = 443

_UNKNOWN = 'UNKNOWN'

# connection states
_CS_IDLE = 'Idle'
_CS_REQ_STARTED = 'Request-started'
_CS_REQ_SENT = 'Request-sent'

# status codes
# informational
CONTINUE = 100
SWITCHING_PROTOCOLS = 101
PROCESSING = 102

# successful
OK = 200
CREATED = 201
ACCEPTED = 202
NON_AUTHORITATIVE_INFORMATION = 203
NO_CONTENT = 204
RESET_CONTENT = 205
PARTIAL_CONTENT = 206
MULTI_STATUS = 207
IM_USED = 226

# redirection
MULTIPLE_CHOICES = 300
MOVED_PERMANENTLY = 301
FOUND = 302
SEE_OTHER = 303
NOT_MODIFIED = 304
USE_PROXY = 305
TEMPORARY_REDIRECT = 307

# client error
BAD_REQUEST = 400
UNAUTHORIZED = 401
PAYMENT_REQUIRED = 402
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
NOT_ACCEPTABLE = 406
PROXY_AUTHENTICATION_REQUIRED = 407
REQUEST_TIMEOUT = 408
CONFLICT = 409
GONE = 410
LENGTH_REQUIRED = 411
PRECONDITION_FAILED = 412
REQUEST_ENTITY_TOO_LARGE = 413
REQUEST_URI_TOO_LONG = 414
UNSUPPORTED_MEDIA_TYPE = 415
REQUESTED_RANGE_NOT_SATISFIABLE = 416
EXPECTATION_FAILED = 417
UNPROCESSABLE_ENTITY = 422
LOCKED = 423
FAILED_DEPENDENCY = 424
UPGRADE_REQUIRED = 426

# server error
INTERNAL_SERVER_ERROR = 500
NOT_IMPLEMENTED = 501
BAD_GATEWAY = 502
SERVICE_UNAVAILABLE = 503
GATEWAY_TIMEOUT = 504
HTTP_VERSION_NOT_SUPPORTED = 505
INSUFFICIENT_STORAGE = 507
NOT_EXTENDED = 510

# Mapping status codes to official W3C names
responses = {
    100: 'Continue',
    101: 'Switching Protocols',

    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',

    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: '(Unused)',
    307: 'Temporary Redirect',

    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',

    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
}

# maximal amount of data to read at one time in _safe_read
MAXAMOUNT = 1048576

# maximal line length when calling readline().
_MAXLINE = 65536

class HTTPMessage(mimetools.Message):

    def addheader(self, key, value):
        """Add header for field key handling repeats."""
        prev = self.dict.get(key)
        if prev is None:
            self.dict[key] = value
        else:
            combined = ", ".join((prev, value))
            self.dict[key] = combined

    def addcontinue(self, key, more):
        """Add more field data from a continuation line."""
        prev = self.dict[key]
        self.dict[key] = prev + "\n " + more

    def readheaders(self):
        """Read header lines.

        Read header lines up to the entirely blank line that terminates them.
        The (normally blank) line that ends the headers is skipped, but not
        included in the returned list.  If a non-header line ends the headers,
        (which is an error), an attempt is made to backspace over it; it is
        never included in the returned list.

        The variable self.status is set to the empty string if all went well,
        otherwise it is an error message.  The variable self.headers is a
        completely uninterpreted list of lines contained in the header (so
        printing them will reproduce the header exactly as it appears in the
        file).

        If multiple header fields with the same name occur, they are combined
        according to the rules in RFC 2616 sec 4.2:

        Appending each subsequent field-value to the first, each separated
        by a comma. The order in which header fields with the same field-name
        are received is significant to the interpretation of the combined
        field value.
        """
        # XXX The implementation overrides the readheaders() method of
        # rfc822.Message.  The base class design isn't amenable to
        # customized behavior here so the method here is a copy of the
        # base class code with a few small changes.

        self.dict = {}
        self.unixfrom = ''
        self.headers = hlist = []
        self.status = ''
        headerseen = ""
        firstline = 1
        startofline = unread = tell = None
        if hasattr(self.fp, 'unread'):
            unread = self.fp.unread
        elif self.seekable:
            tell = self.fp.tell
        while True:
            if tell:
                try:
                    startofline = tell()
                except IOError:
                    startofline = tell = None
                    self.seekable = 0
            line = self.fp.readline(_MAXLINE + 1)
            if len(line) > _MAXLINE:
                raise LineTooLong("header line")
            if not line:
                self.status = 'EOF in headers'
                break
            # Skip unix From name time lines
            if firstline and line.startswith('From '):
                self.unixfrom = self.unixfrom + line
                continue
            firstline = 0
            if headerseen and line[0] in ' \t':
                # XXX Not sure if continuation lines are handled properly
                # for http and/or for repeating headers
                # It's a continuation line.
                hlist.append(line)
                self.addcontinue(headerseen, line.strip())
                continue
            elif self.iscomment(line):
                # It's a comment.  Ignore it.
                continue
            elif self.islast(line):
                # Note! No pushback here!  The delimiter line gets eaten.
                break
            headerseen = self.isheader(line)
            if headerseen:
                # It's a legal header line, save it.
                hlist.append(line)
                self.addheader(headerseen, line[len(headerseen)+1:].strip())
                continue
            else:
                # It's not a header line; throw it back and stop here.
                if not self.dict:
                    self.status = 'No headers'
                else:
                    self.status = 'Non-header line where header expected'
                # Try to undo the read.
                if unread:
                    unread(line)
                elif tell:
                    self.fp.seek(startofline)
                else:
                    self.status = self.status + '; bad seek'
                break

class HTTPResponse:

    # strict: If true, raise BadStatusLine if the status line can't be
    # parsed as a valid HTTP/1.0 or 1.1 status line.  By default it is
    # false because it prevents clients from talking to HTTP/0.9
    # servers.  Note that a response with a sufficiently corrupted
    # status line will look like an HTTP/0.9 response.

    # See RFC 2616 sec 19.6 and RFC 1945 sec 6 for details.

    def __init__(self, sock, debuglevel=0, strict=0, method=None, buffering=False):
        if buffering:
            # The caller won't be using any sock.recv() calls, so buffering
            # is fine and recommended for performance.
            self.fp = sock.makefile('rb')
        else:
            # The buffer size is specified as zero, because the headers of
            # the response are read with readline().  If the reads were
            # buffered the readline() calls could consume some of the
            # response, which make be read via a recv() on the underlying
            # socket.
            self.fp = sock.makefile('rb', 0)
        self.debuglevel = debuglevel
        self.strict = strict
        self._method = method

        self.msg = None

        # from the Status-Line of the response
        self.version = _UNKNOWN # HTTP-Version
        self.status = _UNKNOWN  # Status-Code
        self.reason = _UNKNOWN  # Reason-Phrase

        self.chunked = _UNKNOWN         # is "chunked" being used?
        self.chunk_left = _UNKNOWN      # bytes left to read in current chunk
        self.length = _UNKNOWN          # number of bytes left in response
        self.will_close = _UNKNOWN      # conn will close at end of response

    def _read_status(self):
        # Initialize with Simple-Response defaults
        line = self.fp.readline()
        if self.debuglevel > 0:
            print "reply:", repr(line)
        if not line:
            # Presumably, the server closed the connection before
            # sending a valid response.
            raise BadStatusLine(line)
        try:
            [version, status, reason] = line.split(None, 2)
        except ValueError:
            try:
                [version, status] = line.split(None, 1)
                reason = ""
            except ValueError:
                # empty version will cause next test to fail and status
                # will be treated as 0.9 response.
                version = ""
        if not version.startswith('HTTP/'):
            if self.strict:
                self.close()
                raise BadStatusLine(line)
            else:
                # assume it's a Simple-Response from an 0.9 server
                self.fp = LineAndFileWrapper(line, self.fp)
                return "HTTP/0.9", 200, ""

        # The status code is a three-digit number
        try:
            status = int(status)
            if status < 100 or status > 999:
                raise BadStatusLine(line)
        except ValueError:
            raise BadStatusLine(line)
        return version, status, reason

    def begin(self):
        if self.msg is not None:
            # we've already started reading the response
            return

        # read until we get a non-100 response
        while True:
            version, status, reason = self._read_status()
            if status != CONTINUE:
                break
            # skip the header from the 100 response
            while True:
                skip = self.fp.readline(_MAXLINE + 1)
                if len(skip) > _MAXLINE:
                    raise LineTooLong("header line")
                skip = skip.strip()
                if not skip:
                    break
                if self.debuglevel > 0:
                    print "header:", skip

        self.status = status
        self.reason = reason.strip()
        if version == 'HTTP/1.0':
            self.version = 10
        elif version.startswith('HTTP/1.'):
            self.version = 11   # use HTTP/1.1 code for HTTP/1.x where x>=1
        elif version == 'HTTP/0.9':
            self.version = 9
        else:
            raise UnknownProtocol(version)

        if self.version == 9:
            self.length = None
            self.chunked = 0
            self.will_close = 1
            self.msg = HTTPMessage(StringIO())
            return

        self.msg = HTTPMessage(self.fp, 0)
        if self.debuglevel > 0:
            for hdr in self.msg.headers:
                print "header:", hdr,

        # don't let the msg keep an fp
        self.msg.fp = None

        # are we using the chunked-style of transfer encoding?
        tr_enc = self.msg.getheader('transfer-encoding')
        if tr_enc and tr_enc.lower() == "chunked":
            self.chunked = 1
            self.chunk_left = None
        else:
            self.chunked = 0

        # will the connection close at the end of the response?
        self.will_close = self._check_close()

        # do we have a Content-Length?
        # NOTE: RFC 2616, S4.4, #3 says we ignore this if tr_enc is "chunked"
        length = self.msg.getheader('content-length')
        if length and not self.chunked:
            try:
                self.length = int(length)
            except ValueError:
                self.length = None
            else:
                if self.length < 0:  # ignore nonsensical negative lengths
                    self.length = None
        else:
            self.length = None

        # does the body have a fixed length? (of zero)
        if (status == NO_CONTENT or status == NOT_MODIFIED or
            100 <= status < 200 or      # 1xx codes
            self._method == 'HEAD'):
            self.length = 0

        # if the connection remains open, and we aren't using chunked, and
        # a content-length was not provided, then assume that the connection
        # WILL close.
        if not self.will_close and \
           not self.chunked and \
           self.length is None:
            self.will_close = 1

    def _check_close(self):
        conn = self.msg.getheader('connection')
        if self.version == 11:
            # An HTTP/1.1 proxy is assumed to stay open unless
            # explicitly closed.
            conn = self.msg.getheader('connection')
            if conn and "close" in conn.lower():
                return True
            return False

        # Some HTTP/1.0 implementations have support for persistent
        # connections, using rules different than HTTP/1.1.

        # For older HTTP, Keep-Alive indicates persistent connection.
        if self.msg.getheader('keep-alive'):
            return False

        # At least Akamai returns a "Connection: Keep-Alive" header,
        # which was supposed to be sent by the client.
        if conn and "keep-alive" in conn.lower():
            return False

        # Proxy-Connection is a netscape hack.
        pconn = self.msg.getheader('proxy-connection')
        if pconn and "keep-alive" in pconn.lower():
            return False

        # otherwise, assume it will close
        return True

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None

    def isclosed(self):
        # NOTE: it is possible that we will not ever call self.close(). This
        #       case occurs when will_close is TRUE, length is None, and we
        #       read up to the last byte, but NOT past it.
        #
        # IMPLIES: if will_close is FALSE, then self.close() will ALWAYS be
        #          called, meaning self.isclosed() is meaningful.
        return self.fp is None

    # XXX It would be nice to have readline and __iter__ for this, too.

    def read(self, amt=None):
        if self.fp is None:
            return ''

        if self._method == 'HEAD':
            self.close()
            return ''

        if self.chunked:
            return self._read_chunked(amt)

        if amt is None:
            # unbounded read
            if self.length is None:
                s = self.fp.read()
            else:
                s = self._safe_read(self.length)
                self.length = 0
            self.close()        # we read everything
            return s

        if self.length is not None:
            if amt > self.length:
                # clip the read to the "end of response"
                amt = self.length

        # we do not use _safe_read() here because this may be a .will_close
        # connection, and the user is reading more bytes than will be provided
        # (for example, reading in 1k chunks)
        s = self.fp.read(amt)
        if self.length is not None:
            self.length -= len(s)
            if not self.length:
                self.close()
        return s

    def _read_chunked(self, amt):
        assert self.chunked != _UNKNOWN
        chunk_left = self.chunk_left
        value = []
        while True:
            if chunk_left is None:
                line = self.fp.readline(_MAXLINE + 1)
                if len(line) > _MAXLINE:
                    raise LineTooLong("chunk size")
                i = line.find(';')
                if i >= 0:
                    line = line[:i] # strip chunk-extensions
                try:
                    chunk_left = int(line, 16)
                except ValueError:
                    # close the connection as protocol synchronisation is
                    # probably lost
                    self.close()
                    raise IncompleteRead(''.join(value))
                if chunk_left == 0:
                    break
            if amt is None:
                value.append(self._safe_read(chunk_left))
            elif amt < chunk_left:
                value.append(self._safe_read(amt))
                self.chunk_left = chunk_left - amt
                return ''.join(value)
            elif amt == chunk_left:
                value.append(self._safe_read(amt))
                self._safe_read(2)  # toss the CRLF at the end of the chunk
                self.chunk_left = None
                return ''.join(value)
            else:
                value.append(self._safe_read(chunk_left))
                amt -= chunk_left

            # we read the whole chunk, get another
            self._safe_read(2)      # toss the CRLF at the end of the chunk
            chunk_left = None
            return ''.join(value)

        # read and discard trailer up to the CRLF terminator
        ### note: we shouldn't have any trailers!
        while True:
            line = self.fp.readline(_MAXLINE + 1)
            if len(line) > _MAXLINE:
                raise LineTooLong("trailer line")
            if not line:
                # a vanishingly small number of sites EOF without
                # sending the trailer
                break
            if line == '\r\n':
                break

        # we read everything; close the "file"
        self.close()

        return ''.join(value)

    def _safe_read(self, amt):
        """Read the number of bytes requested, compensating for partial reads.

        Normally, we have a blocking socket, but a read() can be interrupted
        by a signal (resulting in a partial read).

        Note that we cannot distinguish between EOF and an interrupt when zero
        bytes have been read. IncompleteRead() will be raised in this
        situation.

        This function should be used when <amt> bytes "should" be present for
        reading. If the bytes are truly not available (due to EOF), then the
        IncompleteRead exception can be used to detect the problem.
        """
        # NOTE(gps): As of svn r74426 socket._fileobject.read(x) will never
        # return less than x bytes unless EOF is encountered.  It now handles
        # signal interruptions (socket.error EINTR) internally.  This code
        # never caught that exception anyways.  It seems largely pointless.
        # self.fp.read(amt) will work fine.
        s = []
        while amt > 0:
            chunk = self.fp.read(min(amt, MAXAMOUNT))
            if not chunk:
                raise IncompleteRead(''.join(s), amt)
            s.append(chunk)
            amt -= len(chunk)
        return ''.join(s)

    def fileno(self):
        return self.fp.fileno()

    def getheader(self, name, default=None):
        if self.msg is None:
            raise ResponseNotReady()
        return self.msg.getheader(name, default)

    def getheaders(self):
        """Return list of (header, value) tuples."""
        if self.msg is None:
            raise ResponseNotReady()
        return self.msg.items()


class HTTPConnection:

    _http_vsn = 11
    _http_vsn_str = 'HTTP/1.1'

    response_class = HTTPResponse
    default_port = HTTP_PORT
    auto_open = 1
    debuglevel = 0
    strict = 0

    def __init__(self, host, port=None, strict=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        self.timeout = timeout
        self.source_address = source_address
        self.sock = None
        self._buffer = []
        self.__response = None
        self.__state = _CS_IDLE
        self._method = None
        self._tunnel_host = None
        self._tunnel_port = None
        self._tunnel_headers = {}

        self._set_hostport(host, port)
        if strict is not None:
            self.strict = strict

    def set_tunnel(self, host, port=None, headers=None):
        """ Sets up the host and the port for the HTTP CONNECT Tunnelling.

        The headers argument should be a mapping of extra HTTP headers
        to send with the CONNECT request.
        """
        self._tunnel_host = host
        self._tunnel_port = port
        if headers:
            self._tunnel_headers = headers
        else:
            self._tunnel_headers.clear()

    def _set_hostport(self, host, port):
        if port is None:
            i = host.rfind(':')
            j = host.rfind(']')         # ipv6 addresses have [...]
            if i > j:
                try:
                    port = int(host[i+1:])
                except ValueError:
                    raise InvalidURL("nonnumeric port: '%s'" % host[i+1:])
                host = host[:i]
            else:
                port = self.default_port
            if host and host[0] == '[' and host[-1] == ']':
                host = host[1:-1]
        self.host = host
        self.port = port

    def set_debuglevel(self, level):
        self.debuglevel = level

    def _tunnel(self):
        self._set_hostport(self._tunnel_host, self._tunnel_port)
        self.send("CONNECT %s:%d HTTP/1.0\r\n" % (self.host, self.port))
        for header, value in self._tunnel_headers.iteritems():
            self.send("%s: %s\r\n" % (header, value))
        self.send("\r\n")
        response = self.response_class(self.sock, strict = self.strict,
                                       method = self._method)
        (version, code, message) = response._read_status()

        if code != 200:
            self.close()
            raise socket.error("Tunnel connection failed: %d %s" % (code,
                                                                    message.strip()))
        while True:
            line = response.fp.readline(_MAXLINE + 1)
            if len(line) > _MAXLINE:
                raise LineTooLong("header line")
            if line == '\r\n': break


    def connect(self):
        """Connect to the host and port specified in __init__."""
        self.sock = socket.create_connection((self.host,self.port),
                                             self.timeout)

        if self._tunnel_host:
            self._tunnel()

    def close(self):
        """Close the connection to the HTTP server."""
        if self.sock:
            self.sock.close()   # close it manually... there may be other refs
            self.sock = None
        if self.__response:
            self.__response.close()
            self.__response = None
        self.__state = _CS_IDLE

    def send(self, data):
        """Send `data' to the server."""
        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise NotConnected()

        if self.debuglevel > 0:
            print "send:", repr(data)
        blocksize = 8192
        if hasattr(data,'read') and not isinstance(data, array):
            if self.debuglevel > 0: print "sendIng a read()able"
            datablock = data.read(blocksize)
            while datablock:
                self.sock.sendall(datablock)
                datablock = data.read(blocksize)
        else:
            self.sock.sendall(data)

    def _output(self, s):
        """Add a line of output to the current request buffer.

        Assumes that the line does *not* end with \\r\\n.
        """
        self._buffer.append(s)

    def _send_output(self, message_body=None):
        """Send the currently buffered request and clear the buffer.

        Appends an extra \\r\\n to the buffer.
        A message_body may be specified, to be appended to the request.
        """
        self._buffer.extend(("", ""))
        msg = "\r\n".join(self._buffer)
        del self._buffer[:]
        # If msg and message_body are sent in a single send() call,
        # it will avoid performance problems caused by the interaction
        # between delayed ack and the Nagle algorithm.
        if isinstance(message_body, str):
            msg += message_body
            message_body = None
        self.send(msg)
        if message_body is not None:
            #message_body was not a string (i.e. it is a file) and
            #we must run the risk of Nagle
            self.send(message_body)

    def putrequest(self, method, url, skip_host=0, skip_accept_encoding=0):
        """Send a request to the server.

        `method' specifies an HTTP request method, e.g. 'GET'.
        `url' specifies the object being requested, e.g. '/index.html'.
        `skip_host' if True does not add automatically a 'Host:' header
        `skip_accept_encoding' if True does not add automatically an
           'Accept-Encoding:' header
        """

        # if a prior response has been completed, then forget about it.
        if self.__response and self.__response.isclosed():
            self.__response = None


        # in certain cases, we cannot issue another request on this connection.
        # this occurs when:
        #   1) we are in the process of sending a request.   (_CS_REQ_STARTED)
        #   2) a response to a previous request has signalled that it is going
        #      to close the connection upon completion.
        #   3) the headers for the previous response have not been read, thus
        #      we cannot determine whether point (2) is true.   (_CS_REQ_SENT)
        #
        # if there is no prior response, then we can request at will.
        #
        # if point (2) is true, then we will have passed the socket to the
        # response (effectively meaning, "there is no prior response"), and
        # will open a new one when a new request is made.
        #
        # Note: if a prior response exists, then we *can* start a new request.
        #       We are not allowed to begin fetching the response to this new
        #       request, however, until that prior response is complete.
        #
        if self.__state == _CS_IDLE:
            self.__state = _CS_REQ_STARTED
        else:
            raise CannotSendRequest()

        # Save the method we use, we need it later in the response phase
        self._method = method
        if not url:
            url = '/'
        hdr = '%s %s %s' % (method, url, self._http_vsn_str)

        self._output(hdr)

        if self._http_vsn == 11:
            # Issue some standard headers for better HTTP/1.1 compliance

            if not skip_host:
                # this header is issued *only* for HTTP/1.1
                # connections. more specifically, this means it is
                # only issued when the client uses the new
                # HTTPConnection() class. backwards-compat clients
                # will be using HTTP/1.0 and those clients may be
                # issuing this header themselves. we should NOT issue
                # it twice; some web servers (such as Apache) barf
                # when they see two Host: headers

                # If we need a non-standard port,include it in the
                # header.  If the request is going through a proxy,
                # but the host of the actual URL, not the host of the
                # proxy.

                netloc = ''
                if url.startswith('http'):
                    nil, netloc, nil, nil, nil = urlsplit(url)

                if netloc:
                    try:
                        netloc_enc = netloc.encode("ascii")
                    except UnicodeEncodeError:
                        netloc_enc = netloc.encode("idna")
                    self.putheader('Host', netloc_enc)
                else:
                    try:
                        host_enc = self.host.encode("ascii")
                    except UnicodeEncodeError:
                        host_enc = self.host.encode("idna")
                    # Wrap the IPv6 Host Header with [] (RFC 2732)
                    if host_enc.find(':') >= 0:
                        host_enc = "[" + host_enc + "]"
                    if self.port == self.default_port:
                        self.putheader('Host', host_enc)
                    else:
                        self.putheader('Host', "%s:%s" % (host_enc, self.port))

            # note: we are assuming that clients will not attempt to set these
            #       headers since *this* library must deal with the
            #       consequences. this also means that when the supporting
            #       libraries are updated to recognize other forms, then this
            #       code should be changed (removed or updated).

            # we only want a Content-Encoding of "identity" since we don't
            # support encodings such as x-gzip or x-deflate.
            if not skip_accept_encoding:
                self.putheader('Accept-Encoding', 'identity')

            # we can accept "chunked" Transfer-Encodings, but no others
            # NOTE: no TE header implies *only* "chunked"
            #self.putheader('TE', 'chunked')

            # if TE is supplied in the header, then it must appear in a
            # Connection header.
            #self.putheader('Connection', 'TE')

        else:
            # For HTTP/1.0, the server will assume "not chunked"
            pass

    def putheader(self, header, *values):
        """Send a request header line to the server.

        For example: h.putheader('Accept', 'text/html')
        """
        if self.__state != _CS_REQ_STARTED:
            raise CannotSendHeader()

        hdr = '%s: %s' % (header, '\r\n\t'.join([str(v) for v in values]))
        self._output(hdr)

    def endheaders(self, message_body=None):
        """Indicate that the last header line has been sent to the server.

        This method sends the request to the server.  The optional
        message_body argument can be used to pass message body
        associated with the request.  The message body will be sent in
        the same packet as the message headers if possible.  The
        message_body should be a string.
        """
        if self.__state == _CS_REQ_STARTED:
            self.__state = _CS_REQ_SENT
        else:
            raise CannotSendHeader()
        self._send_output(message_body)

    def request(self, method, url, body=None, headers={}):
        """Send a complete request to the server."""
        self._send_request(method, url, body, headers)

    def _set_content_length(self, body):
        # Set the content-length based on the body.
        thelen = None
        try:
            thelen = str(len(body))
        except TypeError, te:
            # If this is a file-like object, try to
            # fstat its file descriptor
            try:
                thelen = str(os.fstat(body.fileno()).st_size)
            except (AttributeError, OSError):
                # Don't send a length if this failed
                if self.debuglevel > 0: print "Cannot stat!!"

        if thelen is not None:
            self.putheader('Content-Length', thelen)

    def _send_request(self, method, url, body, headers):
        # Honor explicitly requested Host: and Accept-Encoding: headers.
        header_names = dict.fromkeys([k.lower() for k in headers])
        skips = {}
        if 'host' in header_names:
            skips['skip_host'] = 1
        if 'accept-encoding' in header_names:
            skips['skip_accept_encoding'] = 1

        self.putrequest(method, url, **skips)

        if body and ('content-length' not in header_names):
            self._set_content_length(body)
        for hdr, value in headers.iteritems():
            self.putheader(hdr, value)
        self.endheaders(body)

    def getresponse(self, buffering=False):
        "Get the response from the server."

        # if a prior response has been completed, then forget about it.
        if self.__response and self.__response.isclosed():
            self.__response = None

        #
        # if a prior response exists, then it must be completed (otherwise, we
        # cannot read this response's header to determine the connection-close
        # behavior)
        #
        # note: if a prior response existed, but was connection-close, then the
        # socket and response were made independent of this HTTPConnection
        # object since a new request requires that we open a whole new
        # connection
        #
        # this means the prior response had one of two states:
        #   1) will_close: this connection was reset and the prior socket and
        #                  response operate independently
        #   2) persistent: the response was retained and we await its
        #                  isclosed() status to become true.
        #
        if self.__state != _CS_REQ_SENT or self.__response:
            raise ResponseNotReady()

        args = (self.sock,)
        kwds = {"strict":self.strict, "method":self._method}
        if self.debuglevel > 0:
            args += (self.debuglevel,)
        if buffering:
            #only add this keyword if non-default, for compatibility with
            #other response_classes.
            kwds["buffering"] = True;
        response = self.response_class(*args, **kwds)

        response.begin()
        assert response.will_close != _UNKNOWN
        self.__state = _CS_IDLE

        if response.will_close:
            # this effectively passes the connection to the response
            self.close()
        else:
            # remember this, so we can tell when it is complete
            self.__response = response

        return response


class HTTP:
    "Compatibility class with httplib.py from 1.5."

    _http_vsn = 10
    _http_vsn_str = 'HTTP/1.0'

    debuglevel = 0

    _connection_class = HTTPConnection

    def __init__(self, host='', port=None, strict=None):
        "Provide a default host, since the superclass requires one."

        # some joker passed 0 explicitly, meaning default port
        if port == 0:
            port = None

        # Note that we may pass an empty string as the host; this will throw
        # an error when we attempt to connect. Presumably, the client code
        # will call connect before then, with a proper host.
        self._setup(self._connection_class(host, port, strict))

    def _setup(self, conn):
        self._conn = conn

        # set up delegation to flesh out interface
        self.send = conn.send
        self.putrequest = conn.putrequest
        self.putheader = conn.putheader
        self.endheaders = conn.endheaders
        self.set_debuglevel = conn.set_debuglevel

        conn._http_vsn = self._http_vsn
        conn._http_vsn_str = self._http_vsn_str

        self.file = None

    def connect(self, host=None, port=None):
        "Accept arguments to set the host/port, since the superclass doesn't."

        if host is not None:
            self._conn._set_hostport(host, port)
        self._conn.connect()

    def getfile(self):
        "Provide a getfile, since the superclass' does not use this concept."
        return self.file

    def getreply(self, buffering=False):
        """Compat definition since superclass does not define it.

        Returns a tuple consisting of:
        - server status code (e.g. '200' if all goes well)
        - server "reason" corresponding to status code
        - any RFC822 headers in the response from the server
        """
        try:
            if not buffering:
                response = self._conn.getresponse()
            else:
                #only add this keyword if non-default for compatibility
                #with other connection classes
                response = self._conn.getresponse(buffering)
        except BadStatusLine, e:
            ### hmm. if getresponse() ever closes the socket on a bad request,
            ### then we are going to have problems with self.sock

            ### should we keep this behavior? do people use it?
            # keep the socket open (as a file), and return it
            self.file = self._conn.sock.makefile('rb', 0)

            # close our socket -- we want to restart after any protocol error
            self.close()

            self.headers = None
            return -1, e.line, None

        self.headers = response.msg
        self.file = response.fp
        return response.status, response.reason, response.msg

    def close(self):
        self._conn.close()

        # note that self.file == response.fp, which gets closed by the
        # superclass. just clear the object ref here.
        ### hmm. messy. if status==-1, then self.file is owned by us.
        ### well... we aren't explicitly closing, but losing this ref will
        ### do it
        self.file = None

try:
    import ssl
except ImportError:
    pass
else:
    class HTTPSConnection(HTTPConnection):
        "This class allows communication via SSL."

        default_port = HTTPS_PORT

        def __init__(self, host, port=None, key_file=None, cert_file=None,
                     strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                     source_address=None):
            HTTPConnection.__init__(self, host, port, strict, timeout,
                                    source_address)
            self.key_file = key_file
            self.cert_file = cert_file

        def connect(self):
            "Connect to a host on a given (SSL) port."

            sock = socket.create_connection((self.host, self.port),
                                            self.timeout, self.source_address)
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file)

    __all__.append("HTTPSConnection")

    class HTTPS(HTTP):
        """Compatibility with 1.5 httplib interface

        Python 1.5.2 did not have an HTTPS class, but it defined an
        interface for sending http requests that is also useful for
        https.
        """

        _connection_class = HTTPSConnection

        def __init__(self, host='', port=None, key_file=None, cert_file=None,
                     strict=None):
            # provide a default host, pass the X509 cert info

            # urf. compensate for bad input.
            if port == 0:
                port = None
            self._setup(self._connection_class(host, port, key_file,
                                               cert_file, strict))

            # we never actually use these for anything, but we keep them
            # here for compatibility with post-1.5.2 CVS.
            self.key_file = key_file
            self.cert_file = cert_file


    def FakeSocket (sock, sslobj):
        warnings.warn("FakeSocket is deprecated, and won't be in 3.x.  " +
                      "Use the result of ssl.wrap_socket() directly instead.",
                      DeprecationWarning, stacklevel=2)
        return sslobj


class HTTPException(Exception):
    # Subclasses that define an __init__ must call Exception.__init__
    # or define self.args.  Otherwise, str() will fail.
    pass

class NotConnected(HTTPException):
    pass

class InvalidURL(HTTPException):
    pass

class UnknownProtocol(HTTPException):
    def __init__(self, version):
        self.args = version,
        self.version = version

class UnknownTransferEncoding(HTTPException):
    pass

class UnimplementedFileMode(HTTPException):
    pass

class IncompleteRead(HTTPException):
    def __init__(self, partial, expected=None):
        self.args = partial,
        self.partial = partial
        self.expected = expected
    def __repr__(self):
        if self.expected is not None:
            e = ', %i more expected' % self.expected
        else:
            e = ''
        return 'IncompleteRead(%i bytes read%s)' % (len(self.partial), e)
    def __str__(self):
        return repr(self)

class ImproperConnectionState(HTTPException):
    pass

class CannotSendRequest(ImproperConnectionState):
    pass

class CannotSendHeader(ImproperConnectionState):
    pass

class ResponseNotReady(ImproperConnectionState):
    pass

class BadStatusLine(HTTPException):
    def __init__(self, line):
        if not line:
            line = repr(line)
        self.args = line,
        self.line = line

class LineTooLong(HTTPException):
    def __init__(self, line_type):
        HTTPException.__init__(self, "got more than %d bytes when reading %s"
                                     % (_MAXLINE, line_type))

# for backwards compatibility
error = HTTPException

class LineAndFileWrapper:
    """A limited file-like object for HTTP/0.9 responses."""

    # The status-line parsing code calls readline(), which normally
    # get the HTTP status line.  For a 0.9 response, however, this is
    # actually the first line of the body!  Clients need to get a
    # readable file object that contains that line.

    def __init__(self, line, file):
        self._line = line
        self._file = file
        self._line_consumed = 0
        self._line_offset = 0
        self._line_left = len(line)

    def __getattr__(self, attr):
        return getattr(self._file, attr)

    def _done(self):
        # called when the last byte is read from the line.  After the
        # call, all read methods are delegated to the underlying file
        # object.
        self._line_consumed = 1
        self.read = self._file.read
        self.readline = self._file.readline
        self.readlines = self._file.readlines

    def read(self, amt=None):
        if self._line_consumed:
            return self._file.read(amt)
        assert self._line_left
        if amt is None or amt > self._line_left:
            s = self._line[self._line_offset:]
            self._done()
            if amt is None:
                return s + self._file.read()
            else:
                return s + self._file.read(amt - len(s))
        else:
            assert amt <= self._line_left
            i = self._line_offset
            j = i + amt
            s = self._line[i:j]
            self._line_offset = j
            self._line_left -= amt
            if self._line_left == 0:
                self._done()
            return s

    def readline(self):
        if self._line_consumed:
            return self._file.readline()
        assert self._line_left
        s = self._line[self._line_offset:]
        self._done()
        return s

    def readlines(self, size=None):
        if self._line_consumed:
            return self._file.readlines(size)
        assert self._line_left
        L = [self._line[self._line_offset:]]
        self._done()
        if size is None:
            return L + self._file.readlines()
        else:
            return L + self._file.readlines(size)

########NEW FILE########
__FILENAME__ = sockjs-protocol-0.1
#!/usr/bin/env python
"""
[**SockJS-protocol**](https://github.com/sockjs/sockjs-protocol) is an
effort to define a protocol between in-browser
[SockJS-client](https://github.com/sockjs/sockjs-client) and its
server-side counterparts, like
[SockJS-node](https://github.com/sockjs/sockjs-client). This should
help others to write alternative server implementations.


This protocol definition is also a runnable test suite, do run it
against your server implementation. Supporting all the tests doesn't
guarantee that SockJS client will work flawlessly, end-to-end tests
using real browsers are always required.
"""
import os
import time
import re
import unittest2 as unittest
from utils_02 import GET, GET_async, POST, POST_async, OPTIONS
from utils_02 import WebSocket8Client
import uuid


# Base URL
# ========

"""
The SockJS server provides one or more SockJS services. The services
are usually exposed with a simple url prefixes, like:
`http://localhost:8000/echo` or
`http://localhost:8000/broadcast`. We'll call this kind of url a
`base_url`. There is nothing wrong with base url being more complex,
like `http://localhost:8000/a/b/c/d/echo`. Base url should
never end with a slash.

Base url is the url that needs to be supplied to the SockJS client.

All paths under base url are controlled by SockJS server and are
defined by SockJS protocol.

SockJS protocol can be using either http or https.

To run this tests server pointed by `base_url` needs to support
following services:

 - `echo` - responds with identical data as received
 - `disabled_websocket_echo` - identical to `echo`, but with websockets disabled
 - `close` - server immediately closes the session

This tests should not be run more often than once in five seconds -
many tests operate on the same (named) sessions and they need to have
enough time to timeout.
"""
test_top_url = os.environ.get('SOCKJS_URL', 'http://localhost:8081')
base_url = test_top_url + '/echo'
close_base_url = test_top_url + '/close'
wsoff_base_url = test_top_url + '/disabled_websocket_echo'


# Static URLs
# ===========

class Test(unittest.TestCase):
    # We are going to test several `404/not found` pages. We don't
    # define a body or a content type.
    def verify404(self, r, cookie=False):
        self.assertEqual(r.status, 404)
        if cookie is False:
            self.verify_no_cookie(r)
        elif cookie is True:
            self.verify_cookie(r)

    # In some cases `405/method not allowed` is more appropriate.
    def verify405(self, r):
        self.assertEqual(r.status, 405)
        self.assertFalse(r['content-type'])
        self.assertFalse(r.body)
        self.verify_no_cookie(r)

    # Multiple transport protocols need to support OPTIONS method. All
    # responses to OPTIONS requests must be cacheable and contain
    # appropriate headers.
    def verify_options(self, url, allowed_methods):
        for origin in [None, 'test']:
            h = {}
            if origin:
                h['Origin'] = origin
            r = OPTIONS(url, headers=h)
            self.assertEqual(r.status, 204)
            self.assertTrue(re.search('public', r['Cache-Control']))
            self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                            "max-age must be large, one year (31536000) is best")
            self.assertTrue(r['Expires'])
            self.assertTrue(int(r['access-control-max-age']) > 1000000)
            self.assertEqual(r['Allow'], allowed_methods)
            self.assertFalse(r.body)
            self.verify_cors(r, origin)
            self.verify_cookie(r)

    # All transports except WebSockets need sticky session support
    # from the load balancer. Some load balancers enable that only
    # when they see `JSESSIONID` cookie. For all the session urls we
    # must set this cookie.
    def verify_cookie(self, r):
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=dummy')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    def verify_no_cookie(self, r):
        self.assertFalse(r['Set-Cookie'])

    # Most of the XHR/Ajax based transports do work CORS if proper
    # headers are set.
    def verify_cors(self, r, origin=None):
        self.assertEqual(r['access-control-allow-origin'], origin or '*')
        # In order to get cookies (`JSESSIONID` mostly) flying, we
        # need to set `allow-credentials` header to true.
        self.assertEqual(r['access-control-allow-credentials'], 'true')

    # Sometimes, due to transports limitations we need to request
    # private data using GET method. In such case it's very important
    # to disallow any caching.
    def verify_not_cached(self, r, origin=None):
        self.assertEqual(r['Cache-Control'],
                         'no-store, no-cache, must-revalidate, max-age=0')
        self.assertFalse(r['Expires'])
        self.assertFalse(r['ETag'])
        self.assertFalse(r['Last-Modified'])


# Greeting url: `/`
# ----------------
class BaseUrlGreeting(Test):
    # The most important part of the url scheme, is without doubt, the
    # top url. Make sure the greeting is valid.
    def test_greeting(self):
        for url in [base_url, base_url + '/']:
            r = GET(url)
            self.assertEqual(r.status, 200)
            self.assertEqual(r['content-type'], 'text/plain; charset=UTF-8')
            self.assertEqual(r.body, 'Welcome to SockJS!\n')
            self.verify_no_cookie(r)

    # Other simple requests should return 404.
    def test_notFound(self):
        for suffix in ['/a', '/a.html', '//', '///', '/a/a', '/a/a/', '/a',
                       '/a/']:
            self.verify404(GET(base_url + suffix))


# IFrame page: `/iframe*.html`
# ----------------------------
class IframePage(Test):
    """
    Some transports don't support cross domain communication
    (CORS). In order to support them we need to do a cross-domain
    trick: on remote (server) domain we serve an simple html page,
    that loads back SockJS client javascript and is able to
    communicate with the server within the same domain.
    """
    iframe_body = re.compile('''
^<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function\(\){SockJS.bootstrap_iframe\(\);};
  </script>
  <script src="(?P<sockjs_url>[^"]*)"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>$
'''.strip())

    # SockJS server must provide this html page.
    def test_simpleUrl(self):
        self.verify(base_url + '/iframe.html')

    # To properly utilize caching, the same content must be served
    # for request which try to version the iframe. The server may want
    # to give slightly different answer for every SockJS client
    # revision.
    def test_versionedUrl(self):
        for suffix in ['/iframe-a.html', '/iframe-.html', '/iframe-0.1.2.html',
                       '/iframe-0.1.2abc-dirty.2144.html']:
            self.verify(base_url + suffix)

    # In some circumstances (`devel` set to true) client library
    # wants to skip caching altogether. That is achieved by
    # supplying a random query string.
    def test_queriedUrl(self):
        for suffix in ['/iframe-a.html?t=1234', '/iframe-0.1.2.html?t=123414',
                       '/iframe-0.1.2abc-dirty.2144.html?t=qweqweq123']:
            self.verify(base_url + suffix)

    # Malformed urls must give 404 answer.
    def test_invalidUrl(self):
        for suffix in ['/iframe.htm', '/iframe', '/IFRAME.HTML', '/IFRAME',
                       '/iframe.HTML', '/iframe.xml', '/iframe-/.html']:
            r = GET(base_url + suffix)
            self.verify404(r)

    # The '/iframe.html' page and its variants must give `200/ok` and be
    # served with 'text/html' content type.
    def verify(self, url):
        r = GET(url)
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'], 'text/html; charset=UTF-8')
        # The iframe page must be strongly cacheable, supply
        # Cache-Control, Expires and Etag headers and avoid
        # Last-Modified header.
        self.assertTrue(re.search('public', r['Cache-Control']))
        self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                        "max-age must be large, one year (31536000) is best")
        self.assertTrue(r['Expires'])
        self.assertTrue(r['ETag'])
        self.assertFalse(r['last-modified'])

        # Body must be exactly as specified, with the exception of
        # `sockjs_url`, which should be configurable.
        match = self.iframe_body.match(r.body.strip())
        self.assertTrue(match)
        # `Sockjs_url` must be a valid url and should utilize caching.
        sockjs_url = match.group('sockjs_url')
        self.assertTrue(sockjs_url.startswith('/') or
                        sockjs_url.startswith('http'))
        self.verify_no_cookie(r)
        return r


    # The iframe page must be strongly cacheable. ETag headers must
    # not change too often. Server must support 'if-none-match'
    # requests.
    def test_cacheability(self):
        r1 = GET(base_url + '/iframe.html')
        r2 = GET(base_url + '/iframe.html')
        self.assertEqual(r1['etag'], r2['etag'])
        self.assertTrue(r1['etag']) # Let's make sure ETag isn't None.

        r = GET(base_url + '/iframe.html', headers={'If-None-Match': r1['etag']})
        self.assertEqual(r.status, 304)
        self.assertFalse(r['content-type'])
        self.assertFalse(r.body)

# Chunking test: `/chunking_test`
# -------------------------------
#
# Warning: this functionality is going to be removed.
class ChunkingTest(Test):
    # This feature is used in order to check if the client and
    # intermediate proxies support http chunking.
    #
    # The chunking test requires the server to send six http chunks
    # containing a `h` byte delayed by varying timeouts.
    #
    # First, the server must send a 'h' frame.
    #
    # Then, the server must send 2048 bytes of `%20` character
    # (space), as a prelude, followed by a 'h' character.
    #
    # That should be followed by a series of `h` frames with following
    # delays between them:
    #
    #  * 5 ms
    #  * 25 ms
    #  * 125 ms
    #  * 625 ms
    #  * 3125 ms
    #
    # At that point the server should close the request. The client
    # will break the connection as soon as it detects that chunking is
    # indeed working.
    def test_basic(self):
        t0 = time.time()
        r = POST_async(base_url + '/chunking_test')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'],
                         'application/javascript; charset=UTF-8')
        self.verify_no_cookie(r)
        self.verify_cors(r)

        # In first chunk the server must send a 'h' frame:
        self.assertEqual(r.read(), 'h\n')
        # As second chunk the server must send 2KiB prelude.
        self.assertEqual(r.read(), ' ' * 2048 + 'h\n')
        # Later the server must send a `h` byte.
        self.assertEqual(r.read(), 'h\n')
        # In third chunk the server must send a `h` byte.
        self.assertEqual(r.read(), 'h\n')

        # At least 30 ms must have passed since the request.
        t1 = time.time()
        self.assertGreater((t1-t0) * 1000., 30.)
        r.close()

    # Chunking test must support CORS.
    def test_options(self):
        self.verify_options(base_url + '/chunking_test', 'OPTIONS, POST')


# Session URLs
# ============

# Top session URL: `/<server>/<session>`
# --------------------------------------
#
# The session between the client and the server is always initialized
# by the client. The client chooses `server_id`, which should be a
# three digit number: 000 to 999. It can be supplied by user or
# randomly generated. The main reason for this parameter is to make it
# easier to configure load balancer - and enable sticky sessions based
# on first part of the url.
#
# Second parameter `session_id` must be a random string, unique for
# every session.
#
# It is undefined what happens when two clients share the same
# `session_id`. It is a client responsibility to choose identifier
# with enough entropy.
#
# Neither server nor client API's can expose `session_id` to the
# application. This field must be protected from the app.
class SessionURLs(Test):

    # The server must accept any value in `server` and `session` fields.
    def test_anyValue(self):
        self.verify('/a/a')
        for session_part in ['/_/_', '/1/1', '/abcdefgh_i-j%20/abcdefg_i-j%20']:
            self.verify(session_part)

    # To test session URLs we're going to use `xhr-polling` transport
    # facilitites.
    def verify(self, session_part):
        r = POST(base_url + session_part + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

    # But not an empty string, anything containing dots or paths with
    # less or more parts.
    def test_invalidPaths(self):
        for suffix in ['//', '/a./a', '/a/a.', '/./.' ,'/', '///']:
            self.verify404(GET(base_url + suffix + '/xhr'))
            self.verify404(POST(base_url + suffix + '/xhr'))

    # A session is identified by only `session_id`. `server_id` is a
    # parameter for load balancer and must be ignored by the server.
    def test_ignoringServerId(self):
        ''' See Protocol.test_simpleSession for explanation. '''
        session_id = str(uuid.uuid4())
        r = POST(base_url + '/000/' + session_id + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '["a"]'
        r = POST(base_url + '/000/' + session_id + '/xhr_send', body=payload)
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)

        r = POST(base_url + '/999/' + session_id + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)

# Protocol and framing
# --------------------
#
# SockJS tries to stay API-compatible with WebSockets, but not on the
# network layer. For technical reasons SockJS must introduce custom
# framing and simple custom protocol.
#
# ### Framing accepted by the client
#
# SockJS client accepts following frames:
#
# * `o` - Open frame. Every time a new session is established, the
#   server must immediately send the open frame. This is required, as
#   some protocols (mostly polling) can't distinguish between a
#   properly established connection and a broken one - we must
#   convince the client that it is indeed a valid url and it can be
#   expecting further messages in the future on that url.
#
# * `h` - Heartbeat frame. Most loadbalancers have arbitrary timeouts
#   on connections. In order to keep connections from breaking, the
#   server must send a heartbeat frame every now and then. The typical
#   delay is 25 seconds and should be configurable.
#
# * `a` - Array of json-encoded messages. For example: `a["message"]`.
#
# * `c` - Close frame. This frame is send to the browser every time
#   the client asks for data on closed connection. This may happen
#   multiple times. Close frame contains a code and a string explaining
#   a reason of closure, like: `c[3000,"Go away!"]`.
#
# ### Framing accepted by the server
#
# SockJS server does not have any framing defined. All incoming data
# is treated as incoming messages, either single json-encoded messages
# or an array of json-encoded messages, depending on transport.
#
# ### Tests
#
# To explain the protocol we'll use `xhr-polling` transport
# facilities.
class Protocol(Test):
    # When server receives a request with unknown `session_id` it must
    # recognize that as request for a new session. When server opens a
    # new sesion it must immediately send an frame containing a letter
    # `o`.
    def test_simpleSession(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        "New line is a frame delimiter specific for xhr-polling"
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        # After a session was established the server needs to accept
        # requests for sending messages.
        "Xhr-polling accepts messages as a list of JSON-encoded strings."
        payload = '["a"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)

        '''We're using an echo service - we'll receive our message
        back. The message is encoded as an array 'a'.'''
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)

        # Sending messages to not existing sessions is invalid.
        payload = '["a"]'
        r = POST(base_url + '/000/bad_session/xhr_send', body=payload)
        self.verify404(r, cookie=True)

        # The session must time out after 5 seconds of not having a
        # receiving connection. The server must send a heartbeat frame
        # every 25 seconds. The heartbeat frame contains a single `h`
        # character. This delays may be configurable.
        pass
        # The server must not allow two receiving connections to wait
        # on a single session. In such case the server must send a
        # close frame to the new connection.
        r1 = POST_async(trans_url + '/xhr', load=False)
        r2 = POST(trans_url + '/xhr')
        r1.close()
        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')
        self.assertEqual(r2.status, 200)

    # The server may terminate the connection, passing error code and
    # message.
    def test_closeSession(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')
        self.assertEqual(r.status, 200)

        # Until the timeout occurs, the server must constantly serve
        # the close message.
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')
        self.assertEqual(r.status, 200)


# WebSocket protocols: `/*/*/websocket`
# -------------------------------------
import websocket

# The most important feature of SockJS is to support native WebSocket
# protocol. A decent SockJS server should support at least the
# following variants:
#
#   - hixie-75 (Chrome 4, Safari 5.0.0)
#   - hixie-76/hybi-00 (Chrome 6, Safari 5.0.1)
#   - hybi-07 (Firefox 6)
#   - hybi-10 (Firefox 7, Chrome 14)
#
class WebsocketHttpErrors(Test):
    # User should be able to disable websocket transport
    # altogether. This is useful when load balancer doesn't
    # support websocket protocol and we need to be able to reject
    # the transport immediately. This is achieved by returning 404
    # response on websocket transport url. This particular 404 page
    # must be small (less than 1KiB).
    def test_disabledTransport(self):
        r = GET(wsoff_base_url + '/0/0/websocket')
        self.verify404(r)
        if r.body:
            self.assertLess(len(r.body), 1025)

    # Normal requests to websocket should not succeed.
    def test_httpMethod(self):
        r = GET(base_url + '/0/0/websocket')
        self.assertEqual(r.status, 400)
        self.assertEqual(r.body, 'Can "Upgrade" only to "WebSocket".')

    # Server should be able to reject connections if origin is
    # invalid.
    def test_verifyOrigin(self):
        '''
        r = GET(base_url + '/0/0/websocket', {'Upgrade': 'WebSocket',
                                              'Origin': 'VeryWrongOrigin'})
        self.assertEqual(r.status, 400)
        self.assertEqual(r.body, 'Unverified origin.')
        '''
        pass

    # Some proxies and load balancers can rewrite 'Connection' header,
    # in such case we must refuse connection.
    def test_invalidConnectionHeader(self):
        r = GET(base_url + '/0/0/websocket', headers={'Upgrade': 'WebSocket',
                                                      'Connection': 'close'})
        self.assertEqual(r.status, 400)
        self.assertEqual(r.body, '"Connection" must be "Upgrade".')

    # WebSocket should only accept GET
    def test_invalidMethod(self):
        for h in [{'Upgrade': 'WebSocket', 'Connection': 'Upgrade'},
                  {}]:
            r = POST(base_url + '/0/0/websocket', headers=h)
            self.assertEqual(r.status, 405)
            self.assertFalse(r.body)


# Support WebSocket Hixie-76 protocol
class WebsocketHixie76(Test):
    def test_transport(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    def test_close(self):
        ws_url = 'ws:' + close_base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')
        ws.close()

    # Empty frames must be ignored by the server side.
    def test_empty_frame(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'"a"')
        self.assertEqual(ws.recv(), u'a["a"]')
        ''' TODO: should ws connection be automatically closed after
        sending a close frame?'''
        ws.close()

    # For WebSockets, as opposed to other transports, it is valid to
    # reuse `session_id`. The lifetime of SockJS WebSocket session is
    # defined by a lifetime of underlying WebSocket connection. It is
    # correct to have two separate sessions sharing the same
    # `session_id` at the same time.
    def test_reuseSessionId(self):
        on_close = lambda(ws): self.assertFalse(True)

        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws1 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws1.recv(), u'o')

        ws2 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws2.recv(), u'o')

        ws1.send(u'"a"')
        self.assertEqual(ws1.recv(), u'a["a"]')

        ws2.send(u'"b"')
        self.assertEqual(ws2.recv(), u'a["b"]')

        ws1.close()
        ws2.close()

        # It is correct to reuse the same `session_id` after closing a
        # previous connection.
        ws1 = websocket.create_connection(ws_url)
        self.assertEqual(ws1.recv(), u'o')
        ws1.send(u'"a"')
        self.assertEqual(ws1.recv(), u'a["a"]')
        ws1.close()

    # Verify WebSocket headers sanity. Due to HAProxy design the
    # websocket server must support writing response headers *before*
    # receiving -76 nonce. In other words, the websocket code must
    # work like that:
    #
    # * Receive request headers.
    # * Write response headers.
    # * Receive request nonce.
    # * Write response nonce.
    def test_headersSanity(self):
        url = base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])
        h = {'Upgrade': 'WebSocket',
             'Connection': 'Upgrade',
             'Origin': origin,
             'Sec-WebSocket-Key1': '4 @1  46546xW%0l 1 5',
             'Sec-WebSocket-Key2': '12998 5 Y3 1  .P00'
            }

        r = GET_async(http_url, headers=h)
        self.assertEqual(r.status, 101)
        self.assertEqual(r['sec-websocket-location'], ws_url)
        self.assertEqual(r['connection'].lower(), 'upgrade')
        self.assertEqual(r['upgrade'].lower(), 'websocket')
        self.assertEqual(r['sec-websocket-origin'], origin)
        self.assertFalse(r['content-length'])
        r.close()

    # When user sends broken data - broken JSON for example, the
    # server must terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'"a')
        with self.assertRaises(websocket.ConnectionClosedException):
            # Raises on error, returns None on valid closure.
            if ws.recv() is None:
                raise websocket.ConnectionClosedException()


# The server must support Hybi-10 protocol
class WebsocketHybi10(Test):
    def test_transport(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)

        self.assertEqual(ws.recv(), 'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'"a"')
        self.assertEqual(ws.recv(), 'a["a"]')
        ''' TODO: should ws connection be automatically closed after
        sending a close frame?'''
        ws.close()

    def test_close(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')
        ws.close()

    # Verify WebSocket headers sanity. Server must support both
    # Hybi-07 and Hybi-10.
    def test_headersSanity(self):
        for version in ['7', '8', '13']:
            url = base_url.split(':',1)[1] + \
                '/000/' + str(uuid.uuid4()) + '/websocket'
            ws_url = 'ws:' + url
            http_url = 'http:' + url
            origin = '/'.join(http_url.split('/')[:3])
            h = {'Upgrade': 'websocket',
                 'Connection': 'Upgrade',
                 'Sec-WebSocket-Version': version,
                 'Sec-WebSocket-Origin': 'http://asd',
                 'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
                 }

            r = GET_async(http_url, headers=h)
            self.assertEqual(r.status, 101)
            self.assertEqual(r['sec-websocket-accept'], 'HSmrc0sMlYUkAGmm5OPpG2HaGWk=')
            self.assertEqual(r['connection'].lower(), 'upgrade')
            self.assertEqual(r['upgrade'].lower(), 'websocket')
            self.assertFalse(r['content-length'])
            r.close()

    # When user sends broken data - broken JSON for example, the
    # server must terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'"a')
        self.assertRaises(WebSocket8Client.ConnectionClosedException, ws.recv)

    # As a fun part, Firefox 6.0.2 supports Websockets protocol '7'. But,
    # it doesn't send a normal 'Connection: Upgrade' header. Instead it
    # sends: 'Connection: keep-alive, Upgrade'. Brilliant.
    def test_firefox_602_connection_header(self):
        url = base_url.split(':',1)[1] + \
            '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])
        h = {'Upgrade': 'websocket',
             'Connection': 'keep-alive, Upgrade',
             'Sec-WebSocket-Version': '7',
             'Sec-WebSocket-Origin': 'http://asd',
             'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
             }
        r = GET_async(http_url, headers=h)
        self.assertEqual(r.status, 101)


# XhrPolling: `/*/*/xhr`, `/*/*/xhr_send`
# ---------------------------------------
#
# The server must support xhr-polling.
class XhrPolling(Test):
    # The transport must support CORS requests, and answer correctly
    # to OPTIONS requests.
    def test_options(self):
        for suffix in ['/xhr', '/xhr_send']:
            self.verify_options(base_url + '/abc/abc' + suffix,
                                'OPTIONS, POST')

    # Test the transport itself.
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'],
                         'application/javascript; charset=UTF-8')
        self.verify_cookie(r)
        self.verify_cors(r)

        # Xhr transports receive json-encoded array of messages.
        r = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)
        # The content type of `xhr_send` must be set to `text/plain`,
        # even though the response code is `204`. This is due to
        # Firefox/Firebug behaviour - it assumes that the content type
        # is xml and shouts about it.
        self.assertEqual(r['content-type'], 'text/plain')
        self.verify_cookie(r)
        self.verify_cors(r)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["x"]\n')
        self.assertEqual(r.status, 200)

    # Publishing messages to a non-existing session must result in
    # a 404 error.
    def test_invalid_session(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr_send', body='["x"]')
        self.verify404(r, cookie=None)

    # The server must behave when invalid json data is send or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')

        r = POST(url + '/xhr_send', body='["x')
        self.assertEqual(r.body.strip(), "Broken JSON encoding.")
        self.assertEqual(r.status, 500)

        r = POST(url + '/xhr_send', body='')
        self.assertEqual(r.body.strip(), "Payload expected.")
        self.assertEqual(r.status, 500)

        r = POST(url + '/xhr_send', body='["a"]')
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)

    # The server must accept messages send with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')

        ctypes = ['text/plain', 'T', 'application/json', 'application/xml', '']
        for ct in ctypes:
            r = POST(url + '/xhr_send', body='["a"]', headers={'Content-Type': ct})
            self.assertFalse(r.body)
            self.assertEqual(r.status, 204)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["a","a","a","a","a"]\n')
        self.assertEqual(r.status, 200)

    # JSESSIONID cookie must be set by default.
    def test_jsessionid(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.verify_cookie(r)

        # And must be echoed back if it's already set.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr', headers={'Cookie': 'JSESSIONID=abcdef'})
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=abcdef')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')


# XhrStreaming: `/*/*/xhr_streaming`
# ----------------------------------
class XhrStreaming(Test):
    def test_options(self):
        self.verify_options(base_url + '/abc/abc/xhr_streaming',
                            'OPTIONS, POST')

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'application/javascript; charset=UTF-8')
        self.verify_cookie(r)
        self.verify_cors(r)

        # The transport must first send 2KiB of `h` bytes as prelude.
        self.assertEqual(r.read(), 'h' *  2048 + '\n')

        self.assertEqual(r.read(), 'o\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(), 'a["x"]\n')
        r.close()


# EventSource: `/*/*/eventsource`
# -------------------------------
#
# For details of this protocol framing read the spec:
#
# * [http://dev.w3.org/html5/eventsource/](http://dev.w3.org/html5/eventsource/)
#
# Beware leading spaces.
class EventSource(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'text/event-stream; charset=UTF-8')
        # As EventSource is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        # The transport must first send a new line prelude, due to a
        # bug in Opera.
        self.assertEqual(r.read(), '\r\n')

        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(), 'data: a["x"]\r\n\r\n')

        # This protocol doesn't allow binary data and we need to
        # specially treat leading space, new lines and things like
        # \x00. But, now the protocol json-encodes everything, so
        # there is no way to trigger this case.
        r1 = POST(url + '/xhr_send', body=r'["  \u0000\n\r "]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         'data: a["  \\u0000\\n\\r "]\r\n\r\n')

        r.close()


# HtmlFile: `/*/*/htmlfile`
# -------------------------
#
# Htmlfile transport is based on research done by Michael Carter. It
# requires a famous `document.domain` trick. Read on:
#
# * [http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do](http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do)
# * [http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/](http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/)
#
class HtmlFile(Test):
    head = r'''
<!doctype html>
<html><head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head><body><h2>Don't panic!</h2>
  <script>
    document.domain = document.domain;
    var c = parent.%s;
    c.start();
    function p(d) {c.message(d);};
    window.onload = function() {c.stop();};
  </script>
'''.strip()

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'text/html; charset=UTF-8')
        # As HtmlFile is requested using GET we must be very careful
        # not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        d = r.read()
        self.assertEqual(d.strip(), self.head % ('callback',))
        self.assertGreater(len(d), 1024)
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         '<script>\np("a[\\"x\\"]");\n</script>\r\n')
        r.close()

    def test_no_callback(self):
        r = GET(base_url + '/a/a/htmlfile')
        self.assertEqual(r.status, 500)
        self.assertEqual(r.body.strip(), '"callback" parameter required')

# JsonpPolling: `/*/*/jsonp`, `/*/*/jsonp_send`
# ---------------------------------------------
class JsonPolling(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'application/javascript; charset=UTF-8')
        # As JsonPolling is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        # Konqueror does weird things on 204. As a workaround we need
        # to respond with something - let it be the string `ok`.
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.assertFalse(r['Content-Type'])
        self.verify_cookie(r)

        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'callback("a[\\"x\\"]");\r\n')


    def test_no_callback(self):
        r = GET(base_url + '/a/a/jsonp')
        self.assertEqual(r.status, 500)
        self.assertEqual(r.body.strip(), '"callback" parameter required')

    # The server must behave when invalid json data is send or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body.strip(), "Broken JSON encoding.")
        self.assertEqual(r.status, 500)

        for data in ['', 'd=', 'p=p']:
            r = POST(url + '/jsonp_send', body=data,
                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            self.assertEqual(r.body.strip(), "Payload expected.")
            self.assertEqual(r.status, 500)

        r = POST(url + '/jsonp_send', body='d=%5B%22b%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"b\\"]");\r\n')

    # The server must accept messages sent with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22abc%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        r = POST(url + '/jsonp_send', body='["%61bc"]',
                 headers={'Content-Type': 'text/plain'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"abc\\",\\"%61bc\\"]");\r\n')


# Protocol Quirks
# ===============
#
# Over the time there were various implementation quirks
# found. Following tests go through the quirks and verify that the
# server behaves itself.
#
# This is less about defining the protocol and more about sanity checking
# implementations.
class ProtocolQuirks(Test):
    def test_closeSession_another_connection(self):
        # When server is closing session, it should unlink current
        # request. That means, if a new request appears, it should
        # receive an application close message rather than "Another
        # connection still open" message.
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')
        self.assertEqual(r1.read(), 'c[3000,"Go away!"]\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[3000,"Go away!"]\n')

        ''' TODO: should request be automatically closed after close?
        self.assertEqual(r1.read(), None)
        self.assertEqual(r2.read(), None)
        '''

# Footnote
# ========

# Make this script runnable.
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = sockjs-protocol-0.2.1
#!/usr/bin/env python
"""
[**SockJS-protocol**](https://github.com/sockjs/sockjs-protocol) is an
effort to define a protocol between in-browser
[SockJS-client](https://github.com/sockjs/sockjs-client) and its
server-side counterparts, like
[SockJS-node](https://github.com/sockjs/sockjs-client). This should
help others to write alternative server implementations.


This protocol definition is also a runnable test suite, do run it
against your server implementation. Supporting all the tests doesn't
guarantee that SockJS client will work flawlessly, end-to-end tests
using real browsers are always required.
"""
import os
import time
import json
import re
import unittest2 as unittest
from utils_02 import GET, GET_async, POST, POST_async, OPTIONS
from utils_02 import WebSocket8Client
from utils_02 import RawHttpConnection
import uuid


# Base URL
# ========

"""
The SockJS server provides one or more SockJS services. The services
are usually exposed with a simple url prefixes, like:
`http://localhost:8000/echo` or
`http://localhost:8000/broadcast`. We'll call this kind of url a
`base_url`. There is nothing wrong with base url being more complex,
like `http://localhost:8000/a/b/c/d/echo`. Base url should
never end with a slash.

Base url is the url that needs to be supplied to the SockJS client.

All paths under base url are controlled by SockJS server and are
defined by SockJS protocol.

SockJS protocol can be using either http or https.

To run this tests server pointed by `base_url` needs to support
following services:

 - `echo` - responds with identical data as received
 - `disabled_websocket_echo` - identical to `echo`, but with websockets disabled
 - `close` - server immediately closes the session

This tests should not be run more often than once in five seconds -
many tests operate on the same (named) sessions and they need to have
enough time to timeout.
"""
test_top_url = os.environ.get('SOCKJS_URL', 'http://localhost:8081')
base_url = test_top_url + '/echo'
close_base_url = test_top_url + '/close'
wsoff_base_url = test_top_url + '/disabled_websocket_echo'


# Static URLs
# ===========

class Test(unittest.TestCase):
    # We are going to test several `404/not found` pages. We don't
    # define a body or a content type.
    def verify404(self, r, cookie=False):
        self.assertEqual(r.status, 404)
        if cookie is False:
            self.verify_no_cookie(r)
        elif cookie is True:
            self.verify_cookie(r)

    # In some cases `405/method not allowed` is more appropriate.
    def verify405(self, r):
        self.assertEqual(r.status, 405)
        self.assertFalse(r['content-type'])
        self.assertTrue(r['allow'])
        self.assertFalse(r.body)

    # Multiple transport protocols need to support OPTIONS method. All
    # responses to OPTIONS requests must be cacheable and contain
    # appropriate headers.
    def verify_options(self, url, allowed_methods):
        for origin in [None, 'test']:
            h = {}
            if origin:
                h['Origin'] = origin
            r = OPTIONS(url, headers=h)
            self.assertEqual(r.status, 204)
            self.assertTrue(re.search('public', r['Cache-Control']))
            self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                            "max-age must be large, one year (31536000) is best")
            self.assertTrue(r['Expires'])
            self.assertTrue(int(r['access-control-max-age']) > 1000000)
            self.assertEqual(r['Access-Control-Allow-Methods'], allowed_methods)
            self.assertFalse(r.body)
            self.verify_cors(r, origin)
            self.verify_cookie(r)

    # All transports except WebSockets need sticky session support
    # from the load balancer. Some load balancers enable that only
    # when they see `JSESSIONID` cookie. For all the session urls we
    # must set this cookie.
    def verify_cookie(self, r):
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=dummy')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    def verify_no_cookie(self, r):
        self.assertFalse(r['Set-Cookie'])

    # Most of the XHR/Ajax based transports do work CORS if proper
    # headers are set.
    def verify_cors(self, r, origin=None):
        self.assertEqual(r['access-control-allow-origin'], origin or '*')
        # In order to get cookies (`JSESSIONID` mostly) flying, we
        # need to set `allow-credentials` header to true.
        self.assertEqual(r['access-control-allow-credentials'], 'true')

    # Sometimes, due to transports limitations we need to request
    # private data using GET method. In such case it's very important
    # to disallow any caching.
    def verify_not_cached(self, r, origin=None):
        self.assertEqual(r['Cache-Control'],
                         'no-store, no-cache, must-revalidate, max-age=0')
        self.assertFalse(r['Expires'])
        self.assertFalse(r['Last-Modified'])


# Greeting url: `/`
# ----------------
class BaseUrlGreeting(Test):
    # The most important part of the url scheme, is without doubt, the
    # top url. Make sure the greeting is valid.
    def test_greeting(self):
        for url in [base_url, base_url + '/']:
            r = GET(url)
            self.assertEqual(r.status, 200)
            self.assertEqual(r['content-type'], 'text/plain; charset=UTF-8')
            self.assertEqual(r.body, 'Welcome to SockJS!\n')
            self.verify_no_cookie(r)

    # Other simple requests should return 404.
    def test_notFound(self):
        for suffix in ['/a', '/a.html', '//', '///', '/a/a', '/a/a/', '/a',
                       '/a/']:
            self.verify404(GET(base_url + suffix))


# IFrame page: `/iframe*.html`
# ----------------------------
class IframePage(Test):
    """
    Some transports don't support cross domain communication
    (CORS). In order to support them we need to do a cross-domain
    trick: on remote (server) domain we serve an simple html page,
    that loads back SockJS client javascript and is able to
    communicate with the server within the same domain.
    """
    iframe_body = re.compile('''
^<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function\(\){SockJS.bootstrap_iframe\(\);};
  </script>
  <script src="(?P<sockjs_url>[^"]*)"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>$
'''.strip())

    # SockJS server must provide this html page.
    def test_simpleUrl(self):
        self.verify(base_url + '/iframe.html')

    # To properly utilize caching, the same content must be served
    # for request which try to version the iframe. The server may want
    # to give slightly different answer for every SockJS client
    # revision.
    def test_versionedUrl(self):
        for suffix in ['/iframe-a.html', '/iframe-.html', '/iframe-0.1.2.html',
                       '/iframe-0.1.2abc-dirty.2144.html']:
            self.verify(base_url + suffix)

    # In some circumstances (`devel` set to true) client library
    # wants to skip caching altogether. That is achieved by
    # supplying a random query string.
    def test_queriedUrl(self):
        for suffix in ['/iframe-a.html?t=1234', '/iframe-0.1.2.html?t=123414',
                       '/iframe-0.1.2abc-dirty.2144.html?t=qweqweq123']:
            self.verify(base_url + suffix)

    # Malformed urls must give 404 answer.
    def test_invalidUrl(self):
        for suffix in ['/iframe.htm', '/iframe', '/IFRAME.HTML', '/IFRAME',
                       '/iframe.HTML', '/iframe.xml', '/iframe-/.html']:
            r = GET(base_url + suffix)
            self.verify404(r)

    # The '/iframe.html' page and its variants must give `200/ok` and be
    # served with 'text/html' content type.
    def verify(self, url):
        r = GET(url)
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'], 'text/html; charset=UTF-8')
        # The iframe page must be strongly cacheable, supply
        # Cache-Control, Expires and Etag headers and avoid
        # Last-Modified header.
        self.assertTrue(re.search('public', r['Cache-Control']))
        self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                        "max-age must be large, one year (31536000) is best")
        self.assertTrue(r['Expires'])
        self.assertTrue(r['ETag'])
        self.assertFalse(r['last-modified'])

        # Body must be exactly as specified, with the exception of
        # `sockjs_url`, which should be configurable.
        match = self.iframe_body.match(r.body.strip())
        self.assertTrue(match)
        # `Sockjs_url` must be a valid url and should utilize caching.
        sockjs_url = match.group('sockjs_url')
        self.assertTrue(sockjs_url.startswith('/') or
                        sockjs_url.startswith('http'))
        self.verify_no_cookie(r)
        return r


    # The iframe page must be strongly cacheable. ETag headers must
    # not change too often. Server must support 'if-none-match'
    # requests.
    def test_cacheability(self):
        r1 = GET(base_url + '/iframe.html')
        r2 = GET(base_url + '/iframe.html')
        self.assertEqual(r1['etag'], r2['etag'])
        self.assertTrue(r1['etag']) # Let's make sure ETag isn't None.

        r = GET(base_url + '/iframe.html', headers={'If-None-Match': r1['etag']})
        self.assertEqual(r.status, 304)
        self.assertFalse(r['content-type'])
        self.assertFalse(r.body)

# Info test: `/info`
# ------------------
#
# Warning: this is a replacement of `/chunking_test` functionality
# from SockJS 0.1.
class InfoTest(Test):
    # This url is called before the client starts the session. It's
    # used to check server capabilities (websocket support, cookies
    # requiremet) and to get the value of "origin" setting (currently
    # not used).
    #
    # But more importantly, the call to this url is used to measure
    # the roundtrip time between the client and the server. So, please,
    # do respond to this url in a timely fashin.
    def test_basic(self):
        r = GET(base_url + '/info')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'],
                         'application/json; charset=UTF-8')
        self.verify_no_cookie(r)
        self.verify_not_cached(r)
        self.verify_cors(r)

        data = json.loads(r.body)
        # Are websockets enabled on the server?
        self.assertEqual(data['websocket'], True)
        # Do transports need to support cookies (ie: for load
        # balancing purposes. Test server must have `cookie_needed`
        # option enabled.
        self.assertEqual(data['cookie_needed'], True)
        # List of allowed origins. Currently ignored.
        self.assertEqual(data['origins'], ['*:*'])
        # Source of entropy for random number generator.
        self.assertTrue(type(data['entropy']) in [int, long])

    # As browsers don't have a good entropy source, the server must
    # help with tht. Info url must supply a good, unpredictable random
    # number from the range 0..2^32 to feed the browser.
    def test_entropy(self):
        r1 = GET(base_url + '/info')
        data1 = json.loads(r1.body)
        r2 = GET(base_url + '/info')
        data2 = json.loads(r2.body)
        self.assertTrue(type(data1['entropy']) in [int, long])
        self.assertTrue(type(data2['entropy']) in [int, long])
        self.assertNotEqual(data1['entropy'], data2['entropy'])

    # Info url must support CORS.
    def test_options(self):
        self.verify_options(base_url + '/info', 'OPTIONS, GET')

    # The 'disabled_websocket_echo' service should have websockets
    # disabled.
    def test_disabled_websocket(self):
        r = GET(wsoff_base_url + '/info')
        self.assertEqual(r.status, 200)
        data = json.loads(r.body)
        self.assertEqual(data['websocket'], False)

# Session URLs
# ============

# Top session URL: `/<server>/<session>`
# --------------------------------------
#
# The session between the client and the server is always initialized
# by the client. The client chooses `server_id`, which should be a
# three digit number: 000 to 999. It can be supplied by user or
# randomly generated. The main reason for this parameter is to make it
# easier to configure load balancer - and enable sticky sessions based
# on first part of the url.
#
# Second parameter `session_id` must be a random string, unique for
# every session.
#
# It is undefined what happens when two clients share the same
# `session_id`. It is a client responsibility to choose identifier
# with enough entropy.
#
# Neither server nor client API's can expose `session_id` to the
# application. This field must be protected from the app.
class SessionURLs(Test):

    # The server must accept any value in `server` and `session` fields.
    def test_anyValue(self):
        self.verify('/a/a')
        for session_part in ['/_/_', '/1/1', '/abcdefgh_i-j%20/abcdefg_i-j%20']:
            self.verify(session_part)

    # To test session URLs we're going to use `xhr-polling` transport
    # facilitites.
    def verify(self, session_part):
        r = POST(base_url + session_part + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

    # But not an empty string, anything containing dots or paths with
    # less or more parts.
    def test_invalidPaths(self):
        for suffix in ['//', '/a./a', '/a/a.', '/./.' ,'/', '///']:
            self.verify404(GET(base_url + suffix + '/xhr'))
            self.verify404(POST(base_url + suffix + '/xhr'))

    # A session is identified by only `session_id`. `server_id` is a
    # parameter for load balancer and must be ignored by the server.
    def test_ignoringServerId(self):
        ''' See Protocol.test_simpleSession for explanation. '''
        session_id = str(uuid.uuid4())
        r = POST(base_url + '/000/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        payload = '["a"]'
        r = POST(base_url + '/000/' + session_id + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        r = POST(base_url + '/999/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

# Protocol and framing
# --------------------
#
# SockJS tries to stay API-compatible with WebSockets, but not on the
# network layer. For technical reasons SockJS must introduce custom
# framing and simple custom protocol.
#
# ### Framing accepted by the client
#
# SockJS client accepts following frames:
#
# * `o` - Open frame. Every time a new session is established, the
#   server must immediately send the open frame. This is required, as
#   some protocols (mostly polling) can't distinguish between a
#   properly established connection and a broken one - we must
#   convince the client that it is indeed a valid url and it can be
#   expecting further messages in the future on that url.
#
# * `h` - Heartbeat frame. Most loadbalancers have arbitrary timeouts
#   on connections. In order to keep connections from breaking, the
#   server must send a heartbeat frame every now and then. The typical
#   delay is 25 seconds and should be configurable.
#
# * `a` - Array of json-encoded messages. For example: `a["message"]`.
#
# * `c` - Close frame. This frame is send to the browser every time
#   the client asks for data on closed connection. This may happen
#   multiple times. Close frame contains a code and a string explaining
#   a reason of closure, like: `c[3000,"Go away!"]`.
#
# ### Framing accepted by the server
#
# SockJS server does not have any framing defined. All incoming data
# is treated as incoming messages, either single json-encoded messages
# or an array of json-encoded messages, depending on transport.
#
# ### Tests
#
# To explain the protocol we'll use `xhr-polling` transport
# facilities.
class Protocol(Test):
    # When server receives a request with unknown `session_id` it must
    # recognize that as request for a new session. When server opens a
    # new sesion it must immediately send a frame containing letter `o`.
    def test_simpleSession(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        "New line is a frame delimiter specific for xhr-polling"
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        # After a session was established the server needs to accept
        # requests for sending messages.
        "Xhr-polling accepts messages as a list of JSON-encoded strings."
        payload = '["a"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        '''We're using an echo service - we'll receive our message
        back. The message is encoded as an array 'a'.'''
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

        # Sending messages to not existing sessions is invalid.
        payload = '["a"]'
        r = POST(base_url + '/000/bad_session/xhr_send', body=payload)
        self.verify404(r, cookie=True)

        # The session must time out after 5 seconds of not having a
        # receiving connection. The server must send a heartbeat frame
        # every 25 seconds. The heartbeat frame contains a single `h`
        # character. This delay may be configurable.
        pass
        # The server must not allow two receiving connections to wait
        # on a single session. In such case the server must send a
        # close frame to the new connection.
        r1 = POST_async(trans_url + '/xhr', load=False)
        r2 = POST(trans_url + '/xhr')
        r1.close()
        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')
        self.assertEqual(r2.status, 200)

    # The server may terminate the connection, passing error code and
    # message.
    def test_closeSession(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')

        # Until the timeout occurs, the server must constantly serve
        # the close message.
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')


# WebSocket protocols: `/*/*/websocket`
# -------------------------------------
import websocket

# The most important feature of SockJS is to support native WebSocket
# protocol. A decent SockJS server should support at least the
# following variants:
#
#   - hixie-75 (Chrome 4, Safari 5.0.0)
#   - hixie-76/hybi-00 (Chrome 6, Safari 5.0.1)
#   - hybi-07 (Firefox 6)
#   - hybi-10 (Firefox 7, Chrome 14)
#
class WebsocketHttpErrors(Test):
    # Normal requests to websocket should not succeed.
    def test_httpMethod(self):
        r = GET(base_url + '/0/0/websocket')
        self.assertEqual(r.status, 400)
        self.assertTrue('Can "Upgrade" only to "WebSocket".' in r.body)

    # Server should be able to reject connections if origin is
    # invalid.
    def test_verifyOrigin(self):
        '''
        r = GET(base_url + '/0/0/websocket', {'Upgrade': 'WebSocket',
                                              'Origin': 'VeryWrongOrigin'})
        self.assertEqual(r.status, 400)
        self.assertEqual(r.body, 'Unverified origin.')
        '''
        pass

    # Some proxies and load balancers can rewrite 'Connection' header,
    # in such case we must refuse connection.
    def test_invalidConnectionHeader(self):
        r = GET(base_url + '/0/0/websocket', headers={'Upgrade': 'WebSocket',
                                                      'Connection': 'close'})
        self.assertEqual(r.status, 400)
        self.assertTrue('"Connection" must be "Upgrade".', r.body)

    # WebSocket should only accept GET
    def test_invalidMethod(self):
        for h in [{'Upgrade': 'WebSocket', 'Connection': 'Upgrade'},
                  {}]:
            r = POST(base_url + '/0/0/websocket', headers=h)
            self.verify405(r)


# Support WebSocket Hixie-76 protocol
class WebsocketHixie76(Test):
    def test_transport(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    def test_close(self):
        ws_url = 'ws:' + close_base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')

        # The connection should be closed after the close frame.
        with self.assertRaises(websocket.ConnectionClosedException):
            if ws.recv() is None:
                raise websocket.ConnectionClosedException
        ws.close()

    # Empty frames must be ignored by the server side.
    def test_empty_frame(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'"a"')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    # For WebSockets, as opposed to other transports, it is valid to
    # reuse `session_id`. The lifetime of SockJS WebSocket session is
    # defined by a lifetime of underlying WebSocket connection. It is
    # correct to have two separate sessions sharing the same
    # `session_id` at the same time.
    def test_reuseSessionId(self):
        on_close = lambda(ws): self.assertFalse(True)

        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws1 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws1.recv(), u'o')

        ws2 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws2.recv(), u'o')

        ws1.send(u'"a"')
        self.assertEqual(ws1.recv(), u'a["a"]')

        ws2.send(u'"b"')
        self.assertEqual(ws2.recv(), u'a["b"]')

        ws1.close()
        ws2.close()

        # It is correct to reuse the same `session_id` after closing a
        # previous connection.
        ws1 = websocket.create_connection(ws_url)
        self.assertEqual(ws1.recv(), u'o')
        ws1.send(u'"a"')
        self.assertEqual(ws1.recv(), u'a["a"]')
        ws1.close()

    # Verify WebSocket headers sanity. Due to HAProxy design the
    # websocket server must support writing response headers *before*
    # receiving -76 nonce. In other words, the websocket code must
    # work like that:
    #
    # * Receive request headers.
    # * Write response headers.
    # * Receive request nonce.
    # * Write response nonce.
    def test_haproxy(self):
        url = base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])

        c = RawHttpConnection(http_url)
        r = c.request('GET', http_url, http='1.1', headers={
                'Connection':'Upgrade',
                'Upgrade':'WebSocket',
                'Origin': origin,
                'Sec-WebSocket-Key1': '4 @1  46546xW%0l 1 5',
                'Sec-WebSocket-Key2': '12998 5 Y3 1  .P00'
                })
        # First check response headers
        self.assertEqual(r.status, 101)
        self.assertEqual(r.headers['connection'].lower(), 'upgrade')
        self.assertEqual(r.headers['upgrade'].lower(), 'websocket')
        self.assertEqual(r.headers['sec-websocket-location'], ws_url)
        self.assertEqual(r.headers['sec-websocket-origin'], origin)
        self.assertFalse('Content-Length' in r.headers)
        # Later send token
        c.send('aaaaaaaa')
        self.assertEqual(c.read(), '\xca4\x00\xd8\xa5\x08G\x97,\xd5qZ\xba\xbfC{')

    # When user sends broken data - broken JSON for example, the
    # server must terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'"a')
        with self.assertRaises(websocket.ConnectionClosedException):
            if ws.recv() is None:
                raise websocket.ConnectionClosedException
        ws.close()


# The server must support Hybi-10 protocol
class WebsocketHybi10(Test):
    def test_transport(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)

        self.assertEqual(ws.recv(), 'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'"a"')
        self.assertEqual(ws.recv(), 'a["a"]')
        ws.close()

    def test_close(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # Verify WebSocket headers sanity. Server must support both
    # Hybi-07 and Hybi-10.
    def test_headersSanity(self):
        for version in ['7', '8', '13']:
            url = base_url.split(':',1)[1] + \
                '/000/' + str(uuid.uuid4()) + '/websocket'
            ws_url = 'ws:' + url
            http_url = 'http:' + url
            origin = '/'.join(http_url.split('/')[:3])
            h = {'Upgrade': 'websocket',
                 'Connection': 'Upgrade',
                 'Sec-WebSocket-Version': version,
                 'Sec-WebSocket-Origin': 'http://asd',
                 'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
                 }

            r = GET_async(http_url, headers=h)
            self.assertEqual(r.status, 101)
            self.assertEqual(r['sec-websocket-accept'], 'HSmrc0sMlYUkAGmm5OPpG2HaGWk=')
            self.assertEqual(r['connection'].lower(), 'upgrade')
            self.assertEqual(r['upgrade'].lower(), 'websocket')
            self.assertFalse(r['content-length'])
            r.close()

    # When user sends broken data - broken JSON for example, the
    # server must terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'"a')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # As a fun part, Firefox 6.0.2 supports Websockets protocol '7'. But,
    # it doesn't send a normal 'Connection: Upgrade' header. Instead it
    # sends: 'Connection: keep-alive, Upgrade'. Brilliant.
    def test_firefox_602_connection_header(self):
        url = base_url.split(':',1)[1] + \
            '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])
        h = {'Upgrade': 'websocket',
             'Connection': 'keep-alive, Upgrade',
             'Sec-WebSocket-Version': '7',
             'Sec-WebSocket-Origin': 'http://asd',
             'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
             }
        r = GET_async(http_url, headers=h)
        self.assertEqual(r.status, 101)


# XhrPolling: `/*/*/xhr`, `/*/*/xhr_send`
# ---------------------------------------
#
# The server must support xhr-polling.
class XhrPolling(Test):
    # The transport must support CORS requests, and answer correctly
    # to OPTIONS requests.
    def test_options(self):
        for suffix in ['/xhr', '/xhr_send']:
            self.verify_options(base_url + '/abc/abc' + suffix,
                                'OPTIONS, POST')

    # Test the transport itself.
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['content-type'],
                         'application/javascript; charset=UTF-8')
        self.verify_cookie(r)
        self.verify_cors(r)

        # Xhr transports receive json-encoded array of messages.
        r = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)
        # The content type of `xhr_send` must be set to `text/plain`,
        # even though the response code is `204`. This is due to
        # Firefox/Firebug behaviour - it assumes that the content type
        # is xml and shouts about it.
        self.assertEqual(r['content-type'], 'text/plain; charset=UTF-8')
        self.verify_cookie(r)
        self.verify_cors(r)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["x"]\n')

    # Publishing messages to a non-existing session must result in
    # a 404 error.
    def test_invalid_session(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr_send', body='["x"]')
        self.verify404(r, cookie=None)

    # The server must behave when invalid json data is send or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(url + '/xhr_send', body='["x')
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        r = POST(url + '/xhr_send', body='')
        self.assertEqual(r.status, 500)
        self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/xhr_send', body='["a"]')
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)

    # The server must accept messages send with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')

        ctypes = ['text/plain', 'T', 'application/json', 'application/xml', '',
                  'application/json; charset=utf-8', 'text/xml; charset=utf-8',
                  'text/xml']
        for ct in ctypes:
            r = POST(url + '/xhr_send', body='["a"]', headers={'Content-Type': ct})
            self.assertEqual(r.status, 204)
            self.assertFalse(r.body)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a[' + (',').join(['"a"']*len(ctypes)) +']\n')

    # JSESSIONID cookie must be set by default.
    def test_jsessionid(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.verify_cookie(r)

        # And must be echoed back if it's already set.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr', headers={'Cookie': 'JSESSIONID=abcdef'})
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=abcdef')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')


# XhrStreaming: `/*/*/xhr_streaming`
# ----------------------------------
class XhrStreaming(Test):
    def test_options(self):
        self.verify_options(base_url + '/abc/abc/xhr_streaming',
                            'OPTIONS, POST')

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'application/javascript; charset=UTF-8')
        self.verify_cookie(r)
        self.verify_cors(r)

        # The transport must first send 2KiB of `h` bytes as prelude.
        self.assertEqual(r.read(), 'h' *  2048 + '\n')

        self.assertEqual(r.read(), 'o\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r1.status, 204)
        self.assertFalse(r1.body)

        self.assertEqual(r.read(), 'a["x"]\n')
        r.close()

    def test_response_limit(self):
        # Single streaming request will buffer all data until
        # closed. In order to remove (garbage collect) old messages
        # from the browser memory we should close the connection every
        # now and then. By default we should close a streaming request
        # every 128KiB messages was send. The test server should have
        # this limit decreased to 4096B.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'o\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 128) + '"'
        for i in range(31):
            r1 = POST(url + '/xhr_send', body='[' + msg + ']')
            self.assertEqual(r1.status, 204)
            self.assertEqual(r.read(), 'a[' + msg + ']\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# EventSource: `/*/*/eventsource`
# -------------------------------
#
# For details of this protocol framing read the spec:
#
# * [http://dev.w3.org/html5/eventsource/](http://dev.w3.org/html5/eventsource/)
#
# Beware leading spaces.
class EventSource(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'text/event-stream; charset=UTF-8')
        # As EventSource is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        # The transport must first send a new line prelude, due to a
        # bug in Opera.
        self.assertEqual(r.read(), '\r\n')

        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(), 'data: a["x"]\r\n\r\n')

        # This protocol doesn't allow binary data and we need to
        # specially treat leading space, new lines and things like
        # \x00. But, now the protocol json-encodes everything, so
        # there is no way to trigger this case.
        r1 = POST(url + '/xhr_send', body=r'["  \u0000\n\r "]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         'data: a["  \\u0000\\n\\r "]\r\n\r\n')

        r.close()

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        # Although EventSource transport is better, and in theory may
        # not need this mechanism, there are some bugs in the browsers
        # that actually prevent the automatic GC. See:
        #  * https://bugs.webkit.org/show_bug.cgi?id=61863
        #  * http://code.google.com/p/chromium/issues/detail?id=68160
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 4096) + '"'
        r1 = POST(url + '/xhr_send', body='[' + msg + ']')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(), 'data: a[' + msg + ']\r\n\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# HtmlFile: `/*/*/htmlfile`
# -------------------------
#
# Htmlfile transport is based on research done by Michael Carter. It
# requires a famous `document.domain` trick. Read on:
#
# * [http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do](http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do)
# * [http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/](http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/)
#
class HtmlFile(Test):
    head = r'''
<!doctype html>
<html><head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head><body><h2>Don't panic!</h2>
  <script>
    document.domain = document.domain;
    var c = parent.%s;
    c.start();
    function p(d) {c.message(d);};
    window.onload = function() {c.stop();};
  </script>
'''.strip()

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'text/html; charset=UTF-8')
        # As HtmlFile is requested using GET we must be very careful
        # not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        d = r.read()
        self.assertEqual(d.strip(), self.head % ('callback',))
        self.assertGreater(len(d), 1024)
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         '<script>\np("a[\\"x\\"]");\n</script>\r\n')
        r.close()

    def test_no_callback(self):
        r = GET(base_url + '/a/a/htmlfile')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=callback')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = ('x' * 4096)
        r1 = POST(url + '/xhr_send', body='["' + msg + '"]')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(),
                         '<script>\np("a[\\"' + msg + '\\"]");\n</script>\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())

# JsonpPolling: `/*/*/jsonp`, `/*/*/jsonp_send`
# ---------------------------------------------
class JsonPolling(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'application/javascript; charset=UTF-8')
        # As JsonPolling is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        # Konqueror does weird things on 204. As a workaround we need
        # to respond with something - let it be the string `ok`.
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'], 'text/plain; charset=UTF-8')
        self.verify_cookie(r)

        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'callback("a[\\"x\\"]");\r\n')


    def test_no_callback(self):
        r = GET(base_url + '/a/a/jsonp')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    # The server must behave when invalid json data is send or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        for data in ['', 'd=', 'p=p']:
            r = POST(url + '/jsonp_send', body=data,
                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            self.assertEqual(r.status, 500)
            self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/jsonp_send', body='d=%5B%22b%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"b\\"]");\r\n')

    # The server must accept messages sent with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22abc%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        r = POST(url + '/jsonp_send', body='["%61bc"]',
                 headers={'Content-Type': 'text/plain'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"abc\\",\\"%61bc\\"]");\r\n')

    def test_close(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("c[3000,\\"Go away!\\"]");\r\n')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("c[3000,\\"Go away!\\"]");\r\n')

# Raw WebSocket url: `/websocket`
# -------------------------------
#
# SockJS protocol defines a bit of higher level framing. This is okay
# when the browser using SockJS-client establishes the connection, but
# it's not really appropriate when the connection is being established
# from another program. Although SockJS focuses on server-browser
# communication, it should be straightforward to connect to SockJS
# from command line or some any programming language.
#
# In order to make writing command-line clients easier, we define this
# `/websocket` entry point. This entry point is special and doesn't
# use any additional custom framing, no open frame, no
# heartbeats. Only raw WebSocket protocol.
class RawWebsocket(Test):
    def test_transport(self):
        ws = WebSocket8Client(base_url + '/websocket')
        ws.send(u'Hello world!\uffff')
        self.assertEqual(ws.recv(), u'Hello world!\uffff')
        ws.close()

    def test_close(self):
        ws = WebSocket8Client(close_base_url + '/websocket')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()



# JSON Unicode Encoding
# =====================
#
# SockJS takes the responsibility of encoding Unicode strings for the
# user.  The idea is that SockJS should properly deliver any valid
# string from the browser to the server and back. This is actually
# quite hard, as browsers do some magical character
# translations. Additionally there are some valid characters from
# JavaScript point of view that are not valid Unicode, called
# surrogates (JavaScript uses UCS-2, which is not really Unicode).
#
# Dealing with unicode surrogates (0xD800-0xDFFF) is quite special. If
# possible we should make sure that server does escape decode
# them. This makes sense for SockJS servers that support UCS-2
# (SockJS-node), but can't really work for servers supporting unicode
# properly (Python).
#
# The browser must escape quite a list of chars, this is due to
# browser mangling outgoing chars on transports like XHR.
escapable_by_client = re.compile(u"[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u2000-\u20ff\ufeff\ufff0-\uffff\x00-\x1f\ufffe\uffff\u0300-\u0333\u033d-\u0346\u034a-\u034c\u0350-\u0352\u0357-\u0358\u035c-\u0362\u0374\u037e\u0387\u0591-\u05af\u05c4\u0610-\u0617\u0653-\u0654\u0657-\u065b\u065d-\u065e\u06df-\u06e2\u06eb-\u06ec\u0730\u0732-\u0733\u0735-\u0736\u073a\u073d\u073f-\u0741\u0743\u0745\u0747\u07eb-\u07f1\u0951\u0958-\u095f\u09dc-\u09dd\u09df\u0a33\u0a36\u0a59-\u0a5b\u0a5e\u0b5c-\u0b5d\u0e38-\u0e39\u0f43\u0f4d\u0f52\u0f57\u0f5c\u0f69\u0f72-\u0f76\u0f78\u0f80-\u0f83\u0f93\u0f9d\u0fa2\u0fa7\u0fac\u0fb9\u1939-\u193a\u1a17\u1b6b\u1cda-\u1cdb\u1dc0-\u1dcf\u1dfc\u1dfe\u1f71\u1f73\u1f75\u1f77\u1f79\u1f7b\u1f7d\u1fbb\u1fbe\u1fc9\u1fcb\u1fd3\u1fdb\u1fe3\u1feb\u1fee-\u1fef\u1ff9\u1ffb\u1ffd\u2000-\u2001\u20d0-\u20d1\u20d4-\u20d7\u20e7-\u20e9\u2126\u212a-\u212b\u2329-\u232a\u2adc\u302b-\u302c\uaab2-\uaab3\uf900-\ufa0d\ufa10\ufa12\ufa15-\ufa1e\ufa20\ufa22\ufa25-\ufa26\ufa2a-\ufa2d\ufa30-\ufa6d\ufa70-\ufad9\ufb1d\ufb1f\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufb4e]")
#
# The server is able to send much more chars verbatim. But, it can't
# send Unicode surrogates over Websockets, also various \u2xxxx chars
# get mangled. Additionally, if the server is capable of handling
# UCS-2 (ie: 16 bit character size), it should be able to deal with
# Unicode surrogates 0xD800-0xDFFF:
# http://en.wikipedia.org/wiki/Mapping_of_Unicode_characters#Surrogates
escapable_by_server = re.compile(u"[\x00-\x1f\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufff0-\uffff]")

client_killer_string_esc = '"' + ''.join([
        r'\u%04x' % (i) for i in range(65536)
            if escapable_by_client.match(unichr(i))]) + '"'
server_killer_string_esc = '"' + ''.join([
        r'\u%04x'% (i) for i in range(255, 65536)
            if escapable_by_server.match(unichr(i))]) + '"'

class JSONEncoding(Test):
    def test_xhr_server_encodes(self):
        # Make sure that server encodes at least all the characters
        # it's supposed to encode.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '["' + json.loads(server_killer_string_esc) + '"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we send previously, aka - escaped.
        self.assertEqual(recv, server_killer_string_esc)

    def test_xhr_server_decodes(self):
        # Make sure that server decodes the chars we're customly
        # encoding.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '[' + client_killer_string_esc + ']' # Sending escaped
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we send previously. We don't
        # really need to know what exactly got escaped and what not.
        a = json.loads(recv)
        b = json.loads(client_killer_string_esc)
        self.assertEqual(a, b)


# Handling close
# ==============
#
# Dealing with session closure is quite complicated part of the
# protocol. The exact details here don't matter that much to the
# client side, but it's good to have a common behaviour on the server
# side.
#
# This is less about defining the protocol and more about sanity
# checking implementations.
class HandlingClose(Test):
    # When server is closing session, it should unlink current
    # request. That means, if a new request appears, it should receive
    # an application close message rather than "Another connection
    # still open" message.
    def test_close_frame(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')
        self.assertEqual(r1.read(), 'c[3000,"Go away!"]\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[3000,"Go away!"]\n')

        # HTTP streaming requests should be automatically closed after
        # close.
        self.assertEqual(r1.read(), None)
        self.assertEqual(r2.read(), None)

    def test_close_request(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')

        # HTTP streaming requests should be automatically closed after
        # getting the close frame.
        self.assertEqual(r2.read(), None)

    # When a polling request is closed by a network error - not by
    # server, the session should be automatically closed. When there
    # is a network error - we're in an undefined state. Some messages
    # may have been lost, there is not much we can do about it.
    def test_abort_xhr_streaming(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')
        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        # Can't do second polling request now.
        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')
        self.assertEqual(r2.read(), None)

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST_async(url + '/xhr_streaming')
        r3.read() # prelude
        self.assertTrue(r3.read() in ['o\n', 'c[1002,"Connection interrupted"]\n'])
        r3.close()

    # The same for polling transports
    def test_abort_xhr_polling(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST(url + '/xhr')
        self.assertEqual(r1.body, 'o\n')

        r1 = POST_async(url + '/xhr', load=False)

        # Can't do second polling request now.
        r2 = POST(url + '/xhr')
        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST(url + '/xhr')
        self.assertTrue(r3.body in ['o\n', 'c[1002,"Connection interrupted"]\n'])

# Http 1.0 and 1.1 chunking
# =========================
#
# There seem to be a lot of confusion about http/1.0 and http/1.1
# content-length and transfer-encoding:chunking headers. Although
# following tests don't really test anything sockjs specific, it's
# good to make sure that the server is behaving about this.
#
# It is not the intention of this test to verify all possible urls -
# merely to check the sanity of http server implementation.  It is
# assumed that the implementator is able to apply presented behaviour
# to other urls served by the sockjs server.
class Http10(Test):
    # We're going to test a greeting url. No dynamic content, just the
    # simplest possible response.
    def test_synchronous(self):
        c = RawHttpConnection(base_url)
        # In theory 'connection:Keep-Alive' isn't a valid http/1.0
        # header, but in this header may in practice be issued by a
        # http/1.0 client:
        # http://www.freesoft.org/CIE/RFC/2068/248.htm
        r = c.request('GET', base_url, http='1.0',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # In practice the exact http version on the response doesn't
        # really matter. Many serves always respond 1.1.
        self.assertTrue(r.http in ['1.0', '1.1'])
        # Transfer-encoding is not allowed in http/1.0.
        self.assertFalse(r.headers.get('transfer-encoding'))

        # There are two ways to give valid response. Use
        # Content-Length (and maybe connection:Keep-Alive) or
        # Connection: close.
        if not r.headers.get('content-length'):
            self.assertEqual(r.headers['connection'].lower(), 'close')
            self.assertEqual(c.read(), 'Welcome to SockJS!\n')
            self.assertTrue(c.closed())
        else:
            self.assertEqual(int(r.headers['content-length']), 19)
            self.assertEqual(c.read(19), 'Welcome to SockJS!\n')
            connection = r.headers.get('connection', '').lower()
            if connection in ['close', '']:
                # Connection-close behaviour is default in http 1.0
                self.assertTrue(c.closed())
            else:
                self.assertEqual(connection, 'keep-alive')
                # We should be able to issue another request on the same connection
                r = c.request('GET', base_url, http='1.0',
                              headers={'Connection':'Keep-Alive'})
                self.assertEqual(r.status, 200)

    def test_streaming(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        c = RawHttpConnection(url)
        # In theory 'connection:Keep-Alive' isn't a valid http/1.0
        # header, but in this header may in practice be issued by a
        # http/1.0 client:
        # http://www.freesoft.org/CIE/RFC/2068/248.htm
        r = c.request('POST', url + '/xhr_streaming', http='1.0',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # Transfer-encoding is not allowed in http/1.0.
        self.assertFalse(r.headers.get('transfer-encoding'))
        # Content-length is not allowed - we don't know it yet.
        self.assertFalse(r.headers.get('content-length'))

        # `Connection` should be not set or be `close`. On the other
        # hand, if it is set to `Keep-Alive`, it won't really hurt, as
        # we are confident that neither `Content-Length` nor
        # `Transfer-Encoding` are set.

        # This is a the same logic as HandlingClose.test_close_frame
        self.assertEqual(c.read(2048+1)[0], 'h') # prelude
        self.assertEqual(c.read(2), 'o\n')
        self.assertEqual(c.read(19), 'c[3000,"Go away!"]\n')
        self.assertTrue(c.closed())


class Http11(Test):
    def test_synchronous(self):
        c = RawHttpConnection(base_url)
        r = c.request('GET', base_url, http='1.1',
                      headers={'Connection':'Keep-Alive'})
        # Keepalive is default in http 1.1
        self.assertTrue(r.http, '1.1')
        self.assertTrue(r.headers.get('connection', '').lower() in ['keep-alive', ''],
                         "Your server doesn't support connection:Keep-Alive")
        # Server should use 'Content-Length' or 'Transfer-Encoding'
        if r.headers.get('content-length'):
            self.assertEqual(int(r.headers['content-length']), 19)
            self.assertEqual(c.read(19), 'Welcome to SockJS!\n')
            self.assertFalse(r.headers.get('transfer-encoding'))
        else:
            self.assertEqual(r.headers['transfer-encoding'].lower(), 'chunked')
            self.assertEqual(c.read_chunk(), 'Welcome to SockJS!\n')
            self.assertEqual(c.read_chunk(), '')
        # We should be able to issue another request on the same connection
        r = c.request('GET', base_url, http='1.1',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)

    def test_streaming(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        c = RawHttpConnection(url)
        r = c.request('POST', url + '/xhr_streaming', http='1.1',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # Transfer-encoding is required in http/1.1.
        self.assertTrue(r.headers['transfer-encoding'].lower(), 'chunked')
        # Content-length is not allowed.
        self.assertFalse(r.headers.get('content-length'))
        # Connection header can be anything, so don't bother verifying it.

        # This is the same logic as HandlingClose.test_close_frame
        self.assertEqual(c.read_chunk()[0], 'h') # prelude
        self.assertEqual(c.read_chunk(), 'o\n')
        self.assertEqual(c.read_chunk(), 'c[3000,"Go away!"]\n')
        self.assertEqual(c.read_chunk(), '')


# Footnote
# ========

# Make this script runnable.
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = sockjs-protocol-0.2
#!/usr/bin/env python
"""
[**SockJS-protocol**](https://github.com/sockjs/sockjs-protocol) is an
effort to define a protocol between in-browser
[SockJS-client](https://github.com/sockjs/sockjs-client) and its
server-side counterparts, like
[SockJS-node](https://github.com/sockjs/sockjs-client). This should
help others to write alternative server implementations.


This protocol definition is also a runnable test suite, do run it
against your server implementation. Supporting all the tests doesn't
guarantee that SockJS client will work flawlessly, end-to-end tests
using real browsers are always required.
"""
import os
import time
import json
import re
import unittest2 as unittest
from utils_02 import GET, GET_async, POST, POST_async, OPTIONS
from utils_02 import WebSocket8Client
import uuid


# Base URL
# ========

"""
The SockJS server provides one or more SockJS services. The services
are usually exposed with a simple url prefixes, like:
`http://localhost:8000/echo` or
`http://localhost:8000/broadcast`. We'll call this kind of url a
`base_url`. There is nothing wrong with base url being more complex,
like `http://localhost:8000/a/b/c/d/echo`. Base url should
never end with a slash.

Base url is the url that needs to be supplied to the SockJS client.

All paths under base url are controlled by SockJS server and are
defined by SockJS protocol.

SockJS protocol can be using either http or https.

To run this tests server pointed by `base_url` needs to support
following services:

 - `echo` - responds with identical data as received
 - `disabled_websocket_echo` - identical to `echo`, but with websockets disabled
 - `close` - server immediately closes the session

This tests should not be run more often than once in five seconds -
many tests operate on the same (named) sessions and they need to have
enough time to timeout.
"""
test_top_url = os.environ.get('SOCKJS_URL', 'http://localhost:8081')
base_url = test_top_url + '/echo'
close_base_url = test_top_url + '/close'
wsoff_base_url = test_top_url + '/disabled_websocket_echo'


# Static URLs
# ===========

class Test(unittest.TestCase):
    # We are going to test several `404/not found` pages. We don't
    # define a body or a content type.
    def verify404(self, r, cookie=False):
        self.assertEqual(r.status, 404)
        if cookie is False:
            self.verify_no_cookie(r)
        elif cookie is True:
            self.verify_cookie(r)

    # In some cases `405/method not allowed` is more appropriate.
    def verify405(self, r):
        self.assertEqual(r.status, 405)
        self.assertFalse(r['content-type'])
        self.assertTrue(r['allow'])
        self.assertFalse(r.body)

    # Multiple transport protocols need to support OPTIONS method. All
    # responses to OPTIONS requests must be cacheable and contain
    # appropriate headers.
    def verify_options(self, url, allowed_methods):
        for origin in [None, 'test']:
            h = {}
            if origin:
                h['Origin'] = origin
            r = OPTIONS(url, headers=h)
            self.assertEqual(r.status, 204)
            self.assertTrue(re.search('public', r['Cache-Control']))
            self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                            "max-age must be large, one year (31536000) is best")
            self.assertTrue(r['Expires'])
            self.assertTrue(int(r['access-control-max-age']) > 1000000)
            self.assertEqual(r['Access-Control-Allow-Methods'], allowed_methods)
            self.assertFalse(r.body)
            self.verify_cors(r, origin)
            self.verify_cookie(r)

    # All transports except WebSockets need sticky session support
    # from the load balancer. Some load balancers enable that only
    # when they see `JSESSIONID` cookie. For all the session urls we
    # must set this cookie.
    def verify_cookie(self, r):
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=dummy')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    def verify_no_cookie(self, r):
        self.assertFalse(r['Set-Cookie'])

    # Most of the XHR/Ajax based transports do work CORS if proper
    # headers are set.
    def verify_cors(self, r, origin=None):
        self.assertEqual(r['access-control-allow-origin'], origin or '*')
        # In order to get cookies (`JSESSIONID` mostly) flying, we
        # need to set `allow-credentials` header to true.
        self.assertEqual(r['access-control-allow-credentials'], 'true')

    # Sometimes, due to transports limitations we need to request
    # private data using GET method. In such case it's very important
    # to disallow any caching.
    def verify_not_cached(self, r, origin=None):
        self.assertEqual(r['Cache-Control'],
                         'no-store, no-cache, must-revalidate, max-age=0')
        self.assertFalse(r['Expires'])
        self.assertFalse(r['Last-Modified'])


# Greeting url: `/`
# ----------------
class BaseUrlGreeting(Test):
    # The most important part of the url scheme, is without doubt, the
    # top url. Make sure the greeting is valid.
    def test_greeting(self):
        for url in [base_url, base_url + '/']:
            r = GET(url)
            self.assertEqual(r.status, 200)
            self.assertEqual(r['content-type'], 'text/plain; charset=UTF-8')
            self.assertEqual(r.body, 'Welcome to SockJS!\n')
            self.verify_no_cookie(r)

    # Other simple requests should return 404.
    def test_notFound(self):
        for suffix in ['/a', '/a.html', '//', '///', '/a/a', '/a/a/', '/a',
                       '/a/']:
            self.verify404(GET(base_url + suffix))


# IFrame page: `/iframe*.html`
# ----------------------------
class IframePage(Test):
    """
    Some transports don't support cross domain communication
    (CORS). In order to support them we need to do a cross-domain
    trick: on remote (server) domain we serve an simple html page,
    that loads back SockJS client javascript and is able to
    communicate with the server within the same domain.
    """
    iframe_body = re.compile('''
^<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function\(\){SockJS.bootstrap_iframe\(\);};
  </script>
  <script src="(?P<sockjs_url>[^"]*)"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>$
'''.strip())

    # SockJS server must provide this html page.
    def test_simpleUrl(self):
        self.verify(base_url + '/iframe.html')

    # To properly utilize caching, the same content must be served
    # for request which try to version the iframe. The server may want
    # to give slightly different answer for every SockJS client
    # revision.
    def test_versionedUrl(self):
        for suffix in ['/iframe-a.html', '/iframe-.html', '/iframe-0.1.2.html',
                       '/iframe-0.1.2abc-dirty.2144.html']:
            self.verify(base_url + suffix)

    # In some circumstances (`devel` set to true) client library
    # wants to skip caching altogether. That is achieved by
    # supplying a random query string.
    def test_queriedUrl(self):
        for suffix in ['/iframe-a.html?t=1234', '/iframe-0.1.2.html?t=123414',
                       '/iframe-0.1.2abc-dirty.2144.html?t=qweqweq123']:
            self.verify(base_url + suffix)

    # Malformed urls must give 404 answer.
    def test_invalidUrl(self):
        for suffix in ['/iframe.htm', '/iframe', '/IFRAME.HTML', '/IFRAME',
                       '/iframe.HTML', '/iframe.xml', '/iframe-/.html']:
            r = GET(base_url + suffix)
            self.verify404(r)

    # The '/iframe.html' page and its variants must give `200/ok` and be
    # served with 'text/html' content type.
    def verify(self, url):
        r = GET(url)
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'], 'text/html; charset=UTF-8')
        # The iframe page must be strongly cacheable, supply
        # Cache-Control, Expires and Etag headers and avoid
        # Last-Modified header.
        self.assertTrue(re.search('public', r['Cache-Control']))
        self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                        "max-age must be large, one year (31536000) is best")
        self.assertTrue(r['Expires'])
        self.assertTrue(r['ETag'])
        self.assertFalse(r['last-modified'])

        # Body must be exactly as specified, with the exception of
        # `sockjs_url`, which should be configurable.
        match = self.iframe_body.match(r.body.strip())
        self.assertTrue(match)
        # `Sockjs_url` must be a valid url and should utilize caching.
        sockjs_url = match.group('sockjs_url')
        self.assertTrue(sockjs_url.startswith('/') or
                        sockjs_url.startswith('http'))
        self.verify_no_cookie(r)
        return r


    # The iframe page must be strongly cacheable. ETag headers must
    # not change too often. Server must support 'if-none-match'
    # requests.
    def test_cacheability(self):
        r1 = GET(base_url + '/iframe.html')
        r2 = GET(base_url + '/iframe.html')
        self.assertEqual(r1['etag'], r2['etag'])
        self.assertTrue(r1['etag']) # Let's make sure ETag isn't None.

        r = GET(base_url + '/iframe.html', headers={'If-None-Match': r1['etag']})
        self.assertEqual(r.status, 304)
        self.assertFalse(r['content-type'])
        self.assertFalse(r.body)

# Info test: `/info`
# ------------------
#
# Warning: this is a replacement of `/chunking_test` functionality
# from SockJS 0.1.
class InfoTest(Test):
    # This url is called before the client starts the session. It's
    # used to check server capabilities (websocket support, cookies
    # requiremet) and to get the value of "origin" setting (currently
    # not used).
    #
    # But more importantly, the call to this url is used to measure
    # the roundtrip time between the client and the server. So, please,
    # do respond to this url in a timely fashin.
    def test_basic(self):
        r = GET(base_url + '/info')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'],
                         'application/json; charset=UTF-8')
        self.verify_no_cookie(r)
        self.verify_not_cached(r)
        self.verify_cors(r)

        data = json.loads(r.body)
        # Are websockets enabled on the server?
        self.assertEqual(data['websocket'], True)
        # Do transports need to support cookies (ie: for load
        # balancing purposes. Test server must have `cookie_needed`
        # option enabled.
        self.assertEqual(data['cookie_needed'], True)
        # List of allowed origins. Currently ignored.
        self.assertEqual(data['origins'], ['*:*'])
        # Source of entropy for random number generator.
        self.assertTrue(type(data['entropy']) in [int, long])

    # As browsers don't have a good entropy source, the server must
    # help with tht. Info url must supply a good, unpredictable random
    # number from the range 0..2^32 to feed the browser.
    def test_entropy(self):
        r1 = GET(base_url + '/info')
        data1 = json.loads(r1.body)
        r2 = GET(base_url + '/info')
        data2 = json.loads(r2.body)
        self.assertTrue(type(data1['entropy']) in [int, long])
        self.assertTrue(type(data2['entropy']) in [int, long])
        self.assertNotEqual(data1['entropy'], data2['entropy'])

    # Info url must support CORS.
    def test_options(self):
        self.verify_options(base_url + '/info', 'OPTIONS, GET')

    # The 'disabled_websocket_echo' service should have websockets
    # disabled.
    def test_disabled_websocket(self):
        r = GET(wsoff_base_url + '/info')
        self.assertEqual(r.status, 200)
        data = json.loads(r.body)
        self.assertEqual(data['websocket'], False)

# Session URLs
# ============

# Top session URL: `/<server>/<session>`
# --------------------------------------
#
# The session between the client and the server is always initialized
# by the client. The client chooses `server_id`, which should be a
# three digit number: 000 to 999. It can be supplied by user or
# randomly generated. The main reason for this parameter is to make it
# easier to configure load balancer - and enable sticky sessions based
# on first part of the url.
#
# Second parameter `session_id` must be a random string, unique for
# every session.
#
# It is undefined what happens when two clients share the same
# `session_id`. It is a client responsibility to choose identifier
# with enough entropy.
#
# Neither server nor client API's can expose `session_id` to the
# application. This field must be protected from the app.
class SessionURLs(Test):

    # The server must accept any value in `server` and `session` fields.
    def test_anyValue(self):
        self.verify('/a/a')
        for session_part in ['/_/_', '/1/1', '/abcdefgh_i-j%20/abcdefg_i-j%20']:
            self.verify(session_part)

    # To test session URLs we're going to use `xhr-polling` transport
    # facilitites.
    def verify(self, session_part):
        r = POST(base_url + session_part + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

    # But not an empty string, anything containing dots or paths with
    # less or more parts.
    def test_invalidPaths(self):
        for suffix in ['//', '/a./a', '/a/a.', '/./.' ,'/', '///']:
            self.verify404(GET(base_url + suffix + '/xhr'))
            self.verify404(POST(base_url + suffix + '/xhr'))

    # A session is identified by only `session_id`. `server_id` is a
    # parameter for load balancer and must be ignored by the server.
    def test_ignoringServerId(self):
        ''' See Protocol.test_simpleSession for explanation. '''
        session_id = str(uuid.uuid4())
        r = POST(base_url + '/000/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        payload = '["a"]'
        r = POST(base_url + '/000/' + session_id + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        r = POST(base_url + '/999/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

# Protocol and framing
# --------------------
#
# SockJS tries to stay API-compatible with WebSockets, but not on the
# network layer. For technical reasons SockJS must introduce custom
# framing and simple custom protocol.
#
# ### Framing accepted by the client
#
# SockJS client accepts following frames:
#
# * `o` - Open frame. Every time a new session is established, the
#   server must immediately send the open frame. This is required, as
#   some protocols (mostly polling) can't distinguish between a
#   properly established connection and a broken one - we must
#   convince the client that it is indeed a valid url and it can be
#   expecting further messages in the future on that url.
#
# * `h` - Heartbeat frame. Most loadbalancers have arbitrary timeouts
#   on connections. In order to keep connections from breaking, the
#   server must send a heartbeat frame every now and then. The typical
#   delay is 25 seconds and should be configurable.
#
# * `a` - Array of json-encoded messages. For example: `a["message"]`.
#
# * `c` - Close frame. This frame is send to the browser every time
#   the client asks for data on closed connection. This may happen
#   multiple times. Close frame contains a code and a string explaining
#   a reason of closure, like: `c[3000,"Go away!"]`.
#
# ### Framing accepted by the server
#
# SockJS server does not have any framing defined. All incoming data
# is treated as incoming messages, either single json-encoded messages
# or an array of json-encoded messages, depending on transport.
#
# ### Tests
#
# To explain the protocol we'll use `xhr-polling` transport
# facilities.
class Protocol(Test):
    # When server receives a request with unknown `session_id` it must
    # recognize that as request for a new session. When server opens a
    # new sesion it must immediately send an frame containing a letter
    # `o`.
    def test_simpleSession(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        "New line is a frame delimiter specific for xhr-polling"
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        # After a session was established the server needs to accept
        # requests for sending messages.
        "Xhr-polling accepts messages as a list of JSON-encoded strings."
        payload = '["a"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        '''We're using an echo service - we'll receive our message
        back. The message is encoded as an array 'a'.'''
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

        # Sending messages to not existing sessions is invalid.
        payload = '["a"]'
        r = POST(base_url + '/000/bad_session/xhr_send', body=payload)
        self.verify404(r, cookie=True)

        # The session must time out after 5 seconds of not having a
        # receiving connection. The server must send a heartbeat frame
        # every 25 seconds. The heartbeat frame contains a single `h`
        # character. This delay may be configurable.
        pass
        # The server must not allow two receiving connections to wait
        # on a single session. In such case the server must send a
        # close frame to the new connection.
        r1 = POST_async(trans_url + '/xhr', load=False)
        r2 = POST(trans_url + '/xhr')
        r1.close()
        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')
        self.assertEqual(r2.status, 200)

    # The server may terminate the connection, passing error code and
    # message.
    def test_closeSession(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')

        # Until the timeout occurs, the server must constantly serve
        # the close message.
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')


# WebSocket protocols: `/*/*/websocket`
# -------------------------------------
import websocket

# The most important feature of SockJS is to support native WebSocket
# protocol. A decent SockJS server should support at least the
# following variants:
#
#   - hixie-75 (Chrome 4, Safari 5.0.0)
#   - hixie-76/hybi-00 (Chrome 6, Safari 5.0.1)
#   - hybi-07 (Firefox 6)
#   - hybi-10 (Firefox 7, Chrome 14)
#
class WebsocketHttpErrors(Test):
    # Normal requests to websocket should not succeed.
    def test_httpMethod(self):
        r = GET(base_url + '/0/0/websocket')
        self.assertEqual(r.status, 400)
        self.assertTrue('Can "Upgrade" only to "WebSocket".' in r.body)

    # Server should be able to reject connections if origin is
    # invalid.
    def test_verifyOrigin(self):
        '''
        r = GET(base_url + '/0/0/websocket', {'Upgrade': 'WebSocket',
                                              'Origin': 'VeryWrongOrigin'})
        self.assertEqual(r.status, 400)
        self.assertEqual(r.body, 'Unverified origin.')
        '''
        pass

    # Some proxies and load balancers can rewrite 'Connection' header,
    # in such case we must refuse connection.
    def test_invalidConnectionHeader(self):
        r = GET(base_url + '/0/0/websocket', headers={'Upgrade': 'WebSocket',
                                                      'Connection': 'close'})
        self.assertEqual(r.status, 400)
        self.assertTrue('"Connection" must be "Upgrade".', r.body)

    # WebSocket should only accept GET
    def test_invalidMethod(self):
        for h in [{'Upgrade': 'WebSocket', 'Connection': 'Upgrade'},
                  {}]:
            r = POST(base_url + '/0/0/websocket', headers=h)
            self.verify405(r)


# Support WebSocket Hixie-76 protocol
class WebsocketHixie76(Test):
    def test_transport(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    def test_close(self):
        ws_url = 'ws:' + close_base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')

        # The connection should be closed after the close frame.
        with self.assertRaises(websocket.ConnectionClosedException):
            ws.recv()
        ws.close()

    # Empty frames must be ignored by the server side.
    def test_empty_frame(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'"a"')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    # For WebSockets, as opposed to other transports, it is valid to
    # reuse `session_id`. The lifetime of SockJS WebSocket session is
    # defined by a lifetime of underlying WebSocket connection. It is
    # correct to have two separate sessions sharing the same
    # `session_id` at the same time.
    def test_reuseSessionId(self):
        on_close = lambda(ws): self.assertFalse(True)

        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws1 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws1.recv(), u'o')

        ws2 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws2.recv(), u'o')

        ws1.send(u'"a"')
        self.assertEqual(ws1.recv(), u'a["a"]')

        ws2.send(u'"b"')
        self.assertEqual(ws2.recv(), u'a["b"]')

        ws1.close()
        ws2.close()

        # It is correct to reuse the same `session_id` after closing a
        # previous connection.
        ws1 = websocket.create_connection(ws_url)
        self.assertEqual(ws1.recv(), u'o')
        ws1.send(u'"a"')
        self.assertEqual(ws1.recv(), u'a["a"]')
        ws1.close()

    # Verify WebSocket headers sanity. Due to HAProxy design the
    # websocket server must support writing response headers *before*
    # receiving -76 nonce. In other words, the websocket code must
    # work like that:
    #
    # * Receive request headers.
    # * Write response headers.
    # * Receive request nonce.
    # * Write response nonce.
    def test_headersSanity(self):
        url = base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])
        h = {'Upgrade': 'WebSocket',
             'Connection': 'Upgrade',
             'Origin': origin,
             'Sec-WebSocket-Key1': '4 @1  46546xW%0l 1 5',
             'Sec-WebSocket-Key2': '12998 5 Y3 1  .P00'
            }

        r = GET_async(http_url, headers=h)
        self.assertEqual(r.status, 101)
        self.assertEqual(r['sec-websocket-location'], ws_url)
        self.assertEqual(r['connection'].lower(), 'upgrade')
        self.assertEqual(r['upgrade'].lower(), 'websocket')
        self.assertEqual(r['sec-websocket-origin'], origin)
        self.assertFalse(r['content-length'])
        r.close()

    # When user sends broken data - broken JSON for example, the
    # server must terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'"a')
        with self.assertRaises(websocket.ConnectionClosedException):
            ws.recv()
        ws.close()


# The server must support Hybi-10 protocol
class WebsocketHybi10(Test):
    def test_transport(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)

        self.assertEqual(ws.recv(), 'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'"a"')
        self.assertEqual(ws.recv(), 'a["a"]')
        ws.close()

    def test_close(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # Verify WebSocket headers sanity. Server must support both
    # Hybi-07 and Hybi-10.
    def test_headersSanity(self):
        for version in ['7', '8', '13']:
            url = base_url.split(':',1)[1] + \
                '/000/' + str(uuid.uuid4()) + '/websocket'
            ws_url = 'ws:' + url
            http_url = 'http:' + url
            origin = '/'.join(http_url.split('/')[:3])
            h = {'Upgrade': 'websocket',
                 'Connection': 'Upgrade',
                 'Sec-WebSocket-Version': version,
                 'Sec-WebSocket-Origin': 'http://asd',
                 'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
                 }

            r = GET_async(http_url, headers=h)
            self.assertEqual(r.status, 101)
            self.assertEqual(r['sec-websocket-accept'], 'HSmrc0sMlYUkAGmm5OPpG2HaGWk=')
            self.assertEqual(r['connection'].lower(), 'upgrade')
            self.assertEqual(r['upgrade'].lower(), 'websocket')
            self.assertFalse(r['content-length'])
            r.close()

    # When user sends broken data - broken JSON for example, the
    # server must terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'"a')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # As a fun part, Firefox 6.0.2 supports Websockets protocol '7'. But,
    # it doesn't send a normal 'Connection: Upgrade' header. Instead it
    # sends: 'Connection: keep-alive, Upgrade'. Brilliant.
    def test_firefox_602_connection_header(self):
        url = base_url.split(':',1)[1] + \
            '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])
        h = {'Upgrade': 'websocket',
             'Connection': 'keep-alive, Upgrade',
             'Sec-WebSocket-Version': '7',
             'Sec-WebSocket-Origin': 'http://asd',
             'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
             }
        r = GET_async(http_url, headers=h)
        self.assertEqual(r.status, 101)


# XhrPolling: `/*/*/xhr`, `/*/*/xhr_send`
# ---------------------------------------
#
# The server must support xhr-polling.
class XhrPolling(Test):
    # The transport must support CORS requests, and answer correctly
    # to OPTIONS requests.
    def test_options(self):
        for suffix in ['/xhr', '/xhr_send']:
            self.verify_options(base_url + '/abc/abc' + suffix,
                                'OPTIONS, POST')

    # Test the transport itself.
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['content-type'],
                         'application/javascript; charset=UTF-8')
        self.verify_cookie(r)
        self.verify_cors(r)

        # Xhr transports receive json-encoded array of messages.
        r = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)
        # The content type of `xhr_send` must be set to `text/plain`,
        # even though the response code is `204`. This is due to
        # Firefox/Firebug behaviour - it assumes that the content type
        # is xml and shouts about it.
        self.assertEqual(r['content-type'], 'text/plain; charset=UTF-8')
        self.verify_cookie(r)
        self.verify_cors(r)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["x"]\n')

    # Publishing messages to a non-existing session must result in
    # a 404 error.
    def test_invalid_session(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr_send', body='["x"]')
        self.verify404(r, cookie=None)

    # The server must behave when invalid json data is send or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(url + '/xhr_send', body='["x')
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        r = POST(url + '/xhr_send', body='')
        self.assertEqual(r.status, 500)
        self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/xhr_send', body='["a"]')
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)

    # The server must accept messages send with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')

        ctypes = ['text/plain', 'T', 'application/json', 'application/xml', '',
                  'application/json; charset=utf-8', 'text/xml; charset=utf-8',
                  'text/xml']
        for ct in ctypes:
            r = POST(url + '/xhr_send', body='["a"]', headers={'Content-Type': ct})
            self.assertEqual(r.status, 204)
            self.assertFalse(r.body)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a[' + (',').join(['"a"']*len(ctypes)) +']\n')

    # JSESSIONID cookie must be set by default.
    def test_jsessionid(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.verify_cookie(r)

        # And must be echoed back if it's already set.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr', headers={'Cookie': 'JSESSIONID=abcdef'})
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=abcdef')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')


# XhrStreaming: `/*/*/xhr_streaming`
# ----------------------------------
class XhrStreaming(Test):
    def test_options(self):
        self.verify_options(base_url + '/abc/abc/xhr_streaming',
                            'OPTIONS, POST')

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'application/javascript; charset=UTF-8')
        self.verify_cookie(r)
        self.verify_cors(r)

        # The transport must first send 2KiB of `h` bytes as prelude.
        self.assertEqual(r.read(), 'h' *  2048 + '\n')

        self.assertEqual(r.read(), 'o\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r1.status, 204)
        self.assertFalse(r1.body)

        self.assertEqual(r.read(), 'a["x"]\n')
        r.close()

    def test_response_limit(self):
        # Single streaming request will buffer all data until
        # closed. In order to remove (garbage collect) old messages
        # from the browser memory we should close the connection every
        # now and then. By default we should close a streaming request
        # every 128KiB messages was send. The test server should have
        # this limit decreased to 4096B.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'o\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 128) + '"'
        for i in range(31):
            r1 = POST(url + '/xhr_send', body='[' + msg + ']')
            self.assertEqual(r1.status, 204)
            self.assertEqual(r.read(), 'a[' + msg + ']\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# EventSource: `/*/*/eventsource`
# -------------------------------
#
# For details of this protocol framing read the spec:
#
# * [http://dev.w3.org/html5/eventsource/](http://dev.w3.org/html5/eventsource/)
#
# Beware leading spaces.
class EventSource(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'text/event-stream; charset=UTF-8')
        # As EventSource is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        # The transport must first send a new line prelude, due to a
        # bug in Opera.
        self.assertEqual(r.read(), '\r\n')

        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(), 'data: a["x"]\r\n\r\n')

        # This protocol doesn't allow binary data and we need to
        # specially treat leading space, new lines and things like
        # \x00. But, now the protocol json-encodes everything, so
        # there is no way to trigger this case.
        r1 = POST(url + '/xhr_send', body=r'["  \u0000\n\r "]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         'data: a["  \\u0000\\n\\r "]\r\n\r\n')

        r.close()

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        # Although EventSource transport is better, and in theory may
        # not need this mechanism, there are some bugs in the browsers
        # that actually prevent the automatic GC.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 4096) + '"'
        r1 = POST(url + '/xhr_send', body='[' + msg + ']')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(), 'data: a[' + msg + ']\r\n\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# HtmlFile: `/*/*/htmlfile`
# -------------------------
#
# Htmlfile transport is based on research done by Michael Carter. It
# requires a famous `document.domain` trick. Read on:
#
# * [http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do](http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do)
# * [http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/](http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/)
#
class HtmlFile(Test):
    head = r'''
<!doctype html>
<html><head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head><body><h2>Don't panic!</h2>
  <script>
    document.domain = document.domain;
    var c = parent.%s;
    c.start();
    function p(d) {c.message(d);};
    window.onload = function() {c.stop();};
  </script>
'''.strip()

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'text/html; charset=UTF-8')
        # As HtmlFile is requested using GET we must be very careful
        # not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        d = r.read()
        self.assertEqual(d.strip(), self.head % ('callback',))
        self.assertGreater(len(d), 1024)
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         '<script>\np("a[\\"x\\"]");\n</script>\r\n')
        r.close()

    def test_no_callback(self):
        r = GET(base_url + '/a/a/htmlfile')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=callback')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = ('x' * 4096)
        r1 = POST(url + '/xhr_send', body='["' + msg + '"]')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(),
                         '<script>\np("a[\\"' + msg + '\\"]");\n</script>\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())

# JsonpPolling: `/*/*/jsonp`, `/*/*/jsonp_send`
# ---------------------------------------------
class JsonPolling(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'application/javascript; charset=UTF-8')
        # As JsonPolling is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)
        self.verify_cookie(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        # Konqueror does weird things on 204. As a workaround we need
        # to respond with something - let it be the string `ok`.
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'], 'text/plain; charset=UTF-8')
        self.verify_cookie(r)

        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'callback("a[\\"x\\"]");\r\n')


    def test_no_callback(self):
        r = GET(base_url + '/a/a/jsonp')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    # The server must behave when invalid json data is send or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        for data in ['', 'd=', 'p=p']:
            r = POST(url + '/jsonp_send', body=data,
                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            self.assertEqual(r.status, 500)
            self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/jsonp_send', body='d=%5B%22b%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"b\\"]");\r\n')

    # The server must accept messages sent with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22abc%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        r = POST(url + '/jsonp_send', body='["%61bc"]',
                 headers={'Content-Type': 'text/plain'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"abc\\",\\"%61bc\\"]");\r\n')


# Raw WebSocket url: `/websocket`
# -------------------------------
#
# SockJS protocol defines a bit of higher level framing. This is okay
# when the browser using SockJS-client establishes the connection, but
# it's not really appropriate when the connection is being esablished
# from another program. Although SockJS focuses on server-browser
# communication, it should be straightforward to connect to SockJS
# from command line or some any programming language.
#
# In order to make writing command-line clients easier, we define this
# `/websocket` entry point. This entry point is special and doesn't
# use any additional custom framing, no open frame, no
# heartbeats. Only raw WebSocket protocol.
class RawWebsocket(Test):
    def test_transport(self):
        ws = WebSocket8Client(base_url + '/websocket')
        ws.send(u'Hello world!\uffff')
        self.assertEqual(ws.recv(), u'Hello world!\uffff')
        ws.close()

    def test_close(self):
        ws = WebSocket8Client(close_base_url + '/websocket')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()



# JSON Unicode Encoding
# =====================
#
# SockJS takes the responsibility of encoding Unicode strings for the
# user.  The idea is that SockJS should properly deliver any valid
# string from the browser to the server and back. This is actually
# quite hard, as browsers do some magical character
# translations. Additionally there are some valid characters from
# JavaScript point of view that are not valid Unicode, called
# surrogates (JavaScript uses UCS-2, which is not really Unicode).
#
# Dealing with unicode surrogates (0xD800-0xDFFF) is quite special. If
# possible we should make sure that server does escape decode
# them. This makes sense for SockJS servers that support UCS-2
# (SockJS-node), but can't really work for servers supporting unicode
# properly (Python).
#
# The browser must escape quite a list of chars, this is due to
# browser mangling outgoing chars on transports like XHR.
escapable_by_client = re.compile(u"[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u2000-\u20ff\ufeff\ufff0-\uffff\x00-\x1f\ufffe\uffff\u0300-\u0333\u033d-\u0346\u034a-\u034c\u0350-\u0352\u0357-\u0358\u035c-\u0362\u0374\u037e\u0387\u0591-\u05af\u05c4\u0610-\u0617\u0653-\u0654\u0657-\u065b\u065d-\u065e\u06df-\u06e2\u06eb-\u06ec\u0730\u0732-\u0733\u0735-\u0736\u073a\u073d\u073f-\u0741\u0743\u0745\u0747\u07eb-\u07f1\u0951\u0958-\u095f\u09dc-\u09dd\u09df\u0a33\u0a36\u0a59-\u0a5b\u0a5e\u0b5c-\u0b5d\u0e38-\u0e39\u0f43\u0f4d\u0f52\u0f57\u0f5c\u0f69\u0f72-\u0f76\u0f78\u0f80-\u0f83\u0f93\u0f9d\u0fa2\u0fa7\u0fac\u0fb9\u1939-\u193a\u1a17\u1b6b\u1cda-\u1cdb\u1dc0-\u1dcf\u1dfc\u1dfe\u1f71\u1f73\u1f75\u1f77\u1f79\u1f7b\u1f7d\u1fbb\u1fbe\u1fc9\u1fcb\u1fd3\u1fdb\u1fe3\u1feb\u1fee-\u1fef\u1ff9\u1ffb\u1ffd\u2000-\u2001\u20d0-\u20d1\u20d4-\u20d7\u20e7-\u20e9\u2126\u212a-\u212b\u2329-\u232a\u2adc\u302b-\u302c\uaab2-\uaab3\uf900-\ufa0d\ufa10\ufa12\ufa15-\ufa1e\ufa20\ufa22\ufa25-\ufa26\ufa2a-\ufa2d\ufa30-\ufa6d\ufa70-\ufad9\ufb1d\ufb1f\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufb4e]")
#
# The server is able to send much more chars verbatim. But, it can't
# send Unicode surrogates over Websockets, also various \u2xxxx chars
# get mangled. Additionally, if the server is capable of handling
# UCS-2 (ie: 16 bit character size), it should be able to deal with
# Unicode surrogates 0xD800-0xDFFF:
# http://en.wikipedia.org/wiki/Mapping_of_Unicode_characters#Surrogates
escapable_by_server = re.compile(u"[\x00-\x1f\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufff0-\uffff]")

client_killer_string_esc = '"' + ''.join([
        r'\u%04x' % (i) for i in range(65536)
            if escapable_by_client.match(unichr(i))]) + '"'
server_killer_string_esc = '"' + ''.join([
        r'\u%04x'% (i) for i in range(255, 65536)
            if escapable_by_server.match(unichr(i))]) + '"'

class JSONEncoding(Test):
    def test_xhr_server_encodes(self):
        # Make sure that server encodes at least all the characters
        # it's supposed to encode.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '["' + json.loads(server_killer_string_esc) + '"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we send previously, aka - escaped.
        self.assertEqual(recv, server_killer_string_esc)

    def test_xhr_server_decodes(self):
        # Make sure that server decodes the chars we're customly
        # encoding.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '[' + client_killer_string_esc + ']' # Sending escaped
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we send previously. We don't
        # really need to know what exactly got escaped and what not.
        a = json.loads(recv)
        b = json.loads(client_killer_string_esc)
        self.assertEqual(a, b)


# Handling close
# ==============
#
# Dealing with session closure is quite complicated part of the
# protocol. The exact details here don't matter that much to the
# client side, but it's good to have a common behaviour on the server
# side.
#
# This is less about defining the protocol and more about sanity
# checking implementations.
class HandlingClose(Test):
    # When server is closing session, it should unlink current
    # request. That means, if a new request appears, it should receive
    # an application close message rather than "Another connection
    # still open" message.
    def test_close_frame(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')
        self.assertEqual(r1.read(), 'c[3000,"Go away!"]\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[3000,"Go away!"]\n')

        # HTTP streaming requests should be automatically closed after
        # close.
        self.assertEqual(r1.read(), None)
        self.assertEqual(r2.read(), None)

    def test_close_request(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')

        # HTTP streaming requests should be automatically closed after
        # getting the close frame.
        self.assertEqual(r2.read(), None)

    # When a polling request is closed by a network error - not by
    # server, the session should be automatically closed. When there
    # is a network error - we're in an undefined state. Some messages
    # may have been lost, there is not much we can do about it.
    def test_abort_xhr_streaming(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')
        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        # Can't do second polling request now.
        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')
        self.assertEqual(r2.read(), None)

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST_async(url + '/xhr_streaming')
        r3.read() # prelude
        self.assertTrue(r3.read() in ['o\n', 'c[1002,"Connection interrupted"]\n'])
        r3.close()

    # The same for polling transports
    def test_abort_xhr_polling(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST(url + '/xhr')
        self.assertEqual(r1.body, 'o\n')

        r1 = POST_async(url + '/xhr', load=False)

        # Can't do second polling request now.
        r2 = POST(url + '/xhr')
        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST(url + '/xhr')
        self.assertTrue(r3.body in ['o\n', 'c[1002,"Connection interrupted"]\n'])

# Footnote
# ========

# Make this script runnable.
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = sockjs-protocol-0.3.3
#!/usr/bin/env python
"""
[**SockJS-protocol**](https://github.com/sockjs/sockjs-protocol) is an
effort to define a protocol between in-browser
[SockJS-client](https://github.com/sockjs/sockjs-client) and its
server-side counterparts, like
[SockJS-node](https://github.com/sockjs/sockjs-node). This should
help others to write alternative server implementations.


This protocol definition is also a runnable test suite, do run it
against your server implementation. Supporting all the tests doesn't
guarantee that SockJS client will work flawlessly, end-to-end tests
using real browsers are always required.
"""
import os
import time
import json
import re
import unittest2 as unittest
from utils_03 import GET, GET_async, POST, POST_async, OPTIONS, old_POST_async
from utils_03 import WebSocket8Client
from utils_03 import RawHttpConnection
import uuid


# Base URL
# ========

"""
The SockJS server provides one or more SockJS services. The services
are usually exposed with a simple url prefix, like:
`http://localhost:8000/echo` or
`http://localhost:8000/broadcast`. We'll call this kind of url a
`base_url`. There is nothing wrong with base url being more complex,
like `http://localhost:8000/a/b/c/d/echo`. Base url should
never end with a slash.

Base url is the url that needs to be supplied to the SockJS client.

All paths under base url are controlled by SockJS server and are
defined by SockJS protocol.

SockJS protocol can be using either http or https.

To run this tests server pointed by `base_url` needs to support
following services:

 - `echo` - responds with identical data as received
 - `disabled_websocket_echo` - identical to `echo`, but with websockets disabled
 - `cookie_needed_echo` - identical to `echo`, but with JSESSIONID cookies sent
 - `close` - server immediately closes the session

This tests should not be run more often than once in five seconds -
many tests operate on the same (named) sessions and they need to have
enough time to timeout.
"""
test_top_url = os.environ.get('SOCKJS_URL', 'http://localhost:8081')
base_url = test_top_url + '/echo'
close_base_url = test_top_url + '/close'
wsoff_base_url = test_top_url + '/disabled_websocket_echo'
cookie_base_url = test_top_url + '/cookie_needed_echo'


# Static URLs
# ===========

class Test(unittest.TestCase):
    # We are going to test several `404/not found` pages. We don't
    # define a body or a content type.
    def verify404(self, r):
        self.assertEqual(r.status, 404)

    # In some cases `405/method not allowed` is more appropriate.
    def verify405(self, r):
        self.assertEqual(r.status, 405)
        self.assertFalse(r['content-type'])
        self.assertTrue(r['allow'])
        self.assertFalse(r.body)

    # Compare the 'content-type' header ignoring spaces
    def verify_content_type(self, r, content_type):
        self.assertEqual(r['content-type'].replace(' ', ''), content_type)

    # Multiple transport protocols need to support OPTIONS method. All
    # responses to OPTIONS requests must be cacheable and contain
    # appropriate headers.
    def verify_options(self, url, allowed_methods):
        for origin in [None, 'test', 'null']:
            h = {}
            if origin:
                h['Origin'] = origin
            r = OPTIONS(url, headers=h)
            self.assertEqual(r.status, 204)
            self.assertTrue(re.search('public', r['Cache-Control']))
            self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                            "max-age must be large, one year (31536000) is best")
            self.assertTrue(r['Expires'])
            self.assertTrue(int(r['access-control-max-age']) > 1000000)
            self.assertEqual(r['Access-Control-Allow-Methods'], allowed_methods)
            self.assertFalse(r.body)
            self.verify_cors(r, origin)

    def verify_no_cookie(self, r):
        self.assertFalse(r['Set-Cookie'])

    # Most of the XHR/Ajax based transports do work CORS if proper
    # headers are set.
    def verify_cors(self, r, origin=None):
        if origin and origin != 'null':
            self.assertEqual(r['access-control-allow-origin'], origin)
        else:
            self.assertEqual(r['access-control-allow-origin'], '*')
        # In order to get cookies (`JSESSIONID` mostly) flying, we
        # need to set `allow-credentials` header to true.
        self.assertEqual(r['access-control-allow-credentials'], 'true')

    # Sometimes, due to transports limitations we need to request
    # private data using GET method. In such case it's very important
    # to disallow any caching.
    def verify_not_cached(self, r, origin=None):
        self.assertEqual(r['Cache-Control'],
                         'no-store, no-cache, must-revalidate, max-age=0')
        self.assertFalse(r['Expires'])
        self.assertFalse(r['Last-Modified'])


# Greeting url: `/`
# ----------------
class BaseUrlGreeting(Test):
    # The most important part of the url scheme, is without doubt, the
    # top url. Make sure the greeting is valid.
    def test_greeting(self):
        for url in [base_url, base_url + '/']:
            r = GET(url)
            self.assertEqual(r.status, 200)
            self.verify_content_type(r, 'text/plain;charset=UTF-8')
            self.assertEqual(r.body, 'Welcome to SockJS!\n')
            self.verify_no_cookie(r)

    # Other simple requests should return 404.
    def test_notFound(self):
        for suffix in ['/a', '/a.html', '//', '///', '/a/a', '/a/a/', '/a',
                       '/a/']:
            self.verify404(GET(base_url + suffix))


# IFrame page: `/iframe*.html`
# ----------------------------
class IframePage(Test):
    """
    Some transports don't support cross domain communication
    (CORS). In order to support them we need to do a cross-domain
    trick: on remote (server) domain we serve an simple html page,
    that loads back SockJS client javascript and is able to
    communicate with the server within the same domain.
    """
    iframe_body = re.compile('''
^<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function\(\){SockJS.bootstrap_iframe\(\);};
  </script>
  <script src="(?P<sockjs_url>[^"]*)"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>$
'''.strip())

    # SockJS server must provide this html page.
    def test_simpleUrl(self):
        self.verify(base_url + '/iframe.html')

    # To properly utilize caching, the same content must be served
    # for request which try to version the iframe. The server may want
    # to give slightly different answer for every SockJS client
    # revision.
    def test_versionedUrl(self):
        for suffix in ['/iframe-a.html', '/iframe-.html', '/iframe-0.1.2.html',
                       '/iframe-0.1.2abc-dirty.2144.html']:
            self.verify(base_url + suffix)

    # In some circumstances (`devel` set to true) client library
    # wants to skip caching altogether. That is achieved by
    # supplying a random query string.
    def test_queriedUrl(self):
        for suffix in ['/iframe-a.html?t=1234', '/iframe-0.1.2.html?t=123414',
                       '/iframe-0.1.2abc-dirty.2144.html?t=qweqweq123']:
            self.verify(base_url + suffix)

    # Malformed urls must give 404 answer.
    def test_invalidUrl(self):
        for suffix in ['/iframe.htm', '/iframe', '/IFRAME.HTML', '/IFRAME',
                       '/iframe.HTML', '/iframe.xml', '/iframe-/.html']:
            r = GET(base_url + suffix)
            self.verify404(r)

    # The '/iframe.html' page and its variants must give `200/ok` and be
    # served with 'text/html' content type.
    def verify(self, url):
        r = GET(url)
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'text/html;charset=UTF-8')
        # The iframe page must be strongly cacheable, supply
        # Cache-Control, Expires and Etag headers and avoid
        # Last-Modified header.
        self.assertTrue(re.search('public', r['Cache-Control']))
        self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                        "max-age must be large, one year (31536000) is best")
        self.assertTrue(r['Expires'])
        self.assertTrue(r['ETag'])
        self.assertFalse(r['last-modified'])

        # Body must be exactly as specified, with the exception of
        # `sockjs_url`, which should be configurable.
        match = self.iframe_body.match(r.body.strip())
        self.assertTrue(match)
        # `Sockjs_url` must be a valid url and should utilize caching.
        sockjs_url = match.group('sockjs_url')
        self.assertTrue(sockjs_url.startswith('/') or
                        sockjs_url.startswith('http'))
        self.verify_no_cookie(r)
        return r


    # The iframe page must be strongly cacheable. ETag headers must
    # not change too often. Server must support 'if-none-match'
    # requests.
    def test_cacheability(self):
        r1 = GET(base_url + '/iframe.html')
        r2 = GET(base_url + '/iframe.html')
        self.assertEqual(r1['etag'], r2['etag'])
        self.assertTrue(r1['etag']) # Let's make sure ETag isn't None.

        r = GET(base_url + '/iframe.html', headers={'If-None-Match': r1['etag']})
        self.assertEqual(r.status, 304)
        self.assertFalse(r['content-type'])
        self.assertFalse(r.body)

# Info test: `/info`
# ------------------
#
# Warning: this is a replacement of `/chunking_test` functionality
# from SockJS 0.1.
class InfoTest(Test):
    # This url is called before the client starts the session. It's
    # used to check server capabilities (websocket support, cookies
    # requiremet) and to get the value of "origin" setting (currently
    # not used).
    #
    # But more importantly, the call to this url is used to measure
    # the roundtrip time between the client and the server. So, please,
    # do respond to this url in a timely fashin.
    def test_basic(self):
        r = GET(base_url + '/info')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'application/json;charset=UTF-8')
        self.verify_no_cookie(r)
        self.verify_not_cached(r)
        self.verify_cors(r)

        data = json.loads(r.body)
        # Are websockets enabled on the server?
        self.assertEqual(data['websocket'], True)
        # Do transports need to support cookies (ie: for load
        # balancing purposes.
        self.assertTrue(data['cookie_needed'] in  [True, False])
        # List of allowed origins. Currently ignored.
        self.assertEqual(data['origins'], ['*:*'])
        # Source of entropy for random number generator.
        self.assertTrue(type(data['entropy']) in [int, long])

    # As browsers don't have a good entropy source, the server must
    # help with tht. Info url must supply a good, unpredictable random
    # number from the range <0; 2^32-1> to feed the browser.
    def test_entropy(self):
        r1 = GET(base_url + '/info')
        data1 = json.loads(r1.body)
        r2 = GET(base_url + '/info')
        data2 = json.loads(r2.body)
        self.assertTrue(type(data1['entropy']) in [int, long])
        self.assertTrue(type(data2['entropy']) in [int, long])
        self.assertNotEqual(data1['entropy'], data2['entropy'])

    # Info url must support CORS.
    def test_options(self):
        self.verify_options(base_url + '/info', 'OPTIONS, GET')

    # SockJS client may be hosted from file:// url. In practice that
    # means the 'Origin' headers sent by the browser will have a value
    # of a string "null". Unfortunately, just echoing back "null"
    # won't work - browser will understand that as a rejection. We
    # must respond with star "*" origin in such case.
    def test_options_null_origin(self):
            url = base_url + '/info'
            r = OPTIONS(url, headers={'Origin': 'null'})
            self.assertEqual(r.status, 204)
            self.assertFalse(r.body)
            self.assertEqual(r['access-control-allow-origin'], '*')

    # The 'disabled_websocket_echo' service should have websockets
    # disabled.
    def test_disabled_websocket(self):
        r = GET(wsoff_base_url + '/info')
        self.assertEqual(r.status, 200)
        data = json.loads(r.body)
        self.assertEqual(data['websocket'], False)


# Session URLs
# ============

# Top session URL: `/<server>/<session>`
# --------------------------------------
#
# The session between the client and the server is always initialized
# by the client. The client chooses `server_id`, which should be a
# three digit number: 000 to 999. It can be supplied by user or
# randomly generated. The main reason for this parameter is to make it
# easier to configure load balancer - and enable sticky sessions based
# on first part of the url.
#
# Second parameter `session_id` must be a random string, unique for
# every session.
#
# It is undefined what happens when two clients share the same
# `session_id`. It is a client responsibility to choose identifier
# with enough entropy.
#
# Neither server nor client API's can expose `session_id` to the
# application. This field must be protected from the app.
class SessionURLs(Test):

    # The server must accept any value in `server` and `session` fields.
    def test_anyValue(self):
        self.verify('/a/a')
        for session_part in ['/_/_', '/1/1', '/abcdefgh_i-j%20/abcdefg_i-j%20']:
            self.verify(session_part)

    # To test session URLs we're going to use `xhr-polling` transport
    # facilitites.
    def verify(self, session_part):
        r = POST(base_url + session_part + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

    # But not an empty string, anything containing dots or paths with
    # less or more parts.
    def test_invalidPaths(self):
        for suffix in ['//', '/a./a', '/a/a.', '/./.' ,'/', '///']:
            self.verify404(GET(base_url + suffix + '/xhr'))
            self.verify404(POST(base_url + suffix + '/xhr'))

    # A session is identified by only `session_id`. `server_id` is a
    # parameter for load balancer and must be ignored by the server.
    def test_ignoringServerId(self):
        ''' See Protocol.test_simpleSession for explanation. '''
        session_id = str(uuid.uuid4())
        r = POST(base_url + '/000/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        payload = '["a"]'
        r = POST(base_url + '/000/' + session_id + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        r = POST(base_url + '/999/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

# Protocol and framing
# --------------------
#
# SockJS tries to stay API-compatible with WebSockets, but not on the
# network layer. For technical reasons SockJS must introduce custom
# framing and simple custom protocol.
#
# ### Framing accepted by the client
#
# SockJS client accepts following frames:
#
# * `o` - Open frame. Every time a new session is established, the
#   server must immediately send the open frame. This is required, as
#   some protocols (mostly polling) can't distinguish between a
#   properly established connection and a broken one - we must
#   convince the client that it is indeed a valid url and it can be
#   expecting further messages in the future on that url.
#
# * `h` - Heartbeat frame. Most loadbalancers have arbitrary timeouts
#   on connections. In order to keep connections from breaking, the
#   server must send a heartbeat frame every now and then. The typical
#   delay is 25 seconds and should be configurable.
#
# * `a` - Array of json-encoded messages. For example: `a["message"]`.
#
# * `c` - Close frame. This frame is sent to the browser every time
#   the client asks for data on closed connection. This may happen
#   multiple times. Close frame contains a code and a string explaining
#   a reason of closure, like: `c[3000,"Go away!"]`.
#
# ### Framing accepted by the server
#
# SockJS server does not have any framing defined. All incoming data
# is treated as incoming messages, either single json-encoded messages
# or an array of json-encoded messages, depending on transport.
#
# ### Tests
#
# To explain the protocol we'll use `xhr-polling` transport
# facilities.
class Protocol(Test):
    # When server receives a request with unknown `session_id` it must
    # recognize that as request for a new session. When server opens a
    # new sesion it must immediately send an frame containing a letter
    # `o`.
    def test_simpleSession(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        "New line is a frame delimiter specific for xhr-polling"
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        # After a session was established the server needs to accept
        # requests for sending messages.
        "Xhr-polling accepts messages as a list of JSON-encoded strings."
        payload = '["a"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        '''We're using an echo service - we'll receive our message
        back. The message is encoded as an array 'a'.'''
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

        # Sending messages to not existing sessions is invalid.
        payload = '["a"]'
        r = POST(base_url + '/000/bad_session/xhr_send', body=payload)
        self.verify404(r)

        # The session must time out after 5 seconds of not having a
        # receiving connection. The server must send a heartbeat frame
        # every 25 seconds. The heartbeat frame contains a single `h`
        # character. This delay may be configurable.
        pass
        # The server must not allow two receiving connections to wait
        # on a single session. In such case the server must send a
        # close frame to the new connection.
        r1 = old_POST_async(trans_url + '/xhr', load=False)
        time.sleep(0.25)
        r2 = POST(trans_url + '/xhr')

        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')
        self.assertEqual(r2.status, 200)

        r1.close()

    # The server may terminate the connection, passing error code and
    # message.
    def test_closeSession(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')

        # Until the timeout occurs, the server must constantly serve
        # the close message.

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')


# WebSocket protocols: `/*/*/websocket`
# -------------------------------------
import websocket

# The most important feature of SockJS is to support native WebSocket
# protocol. A decent SockJS server should support at least the
# following variants:
#
#   - hixie-75 (Chrome 4, Safari 5.0.0)
#   - hixie-76/hybi-00 (Chrome 6, Safari 5.0.1)
#   - hybi-07 (Firefox 6)
#   - hybi-10 (Firefox 7, Chrome 14)
#
class WebsocketHttpErrors(Test):
    # Normal requests to websocket should not succeed.
    def test_httpMethod(self):
        r = GET(base_url + '/0/0/websocket')
        self.assertEqual(r.status, 400)
        self.assertTrue('Can "Upgrade" only to "WebSocket".' in r.body)

    # Some proxies and load balancers can rewrite 'Connection' header,
    # in such case we must refuse connection.
    def test_invalidConnectionHeader(self):
        r = GET(base_url + '/0/0/websocket', headers={'Upgrade': 'WebSocket',
                                                      'Connection': 'close'})
        self.assertEqual(r.status, 400)
        self.assertTrue('"Connection" must be "Upgrade".', r.body)

    # WebSocket should only accept GET
    def test_invalidMethod(self):
        for h in [{'Upgrade': 'WebSocket', 'Connection': 'Upgrade'},
                  {}]:
            r = POST(base_url + '/0/0/websocket', headers=h)
            self.verify405(r)


# Support WebSocket Hixie-76 protocol
class WebsocketHixie76(Test):
    def test_transport(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    def test_close(self):
        ws_url = 'ws:' + close_base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')

        # The connection should be closed after the close frame.
        with self.assertRaises(websocket.ConnectionClosedException):
            if ws.recv() is None:
                raise websocket.ConnectionClosedException
        ws.close()

    # Empty frames must be ignored by the server side.
    def test_empty_frame(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    # For WebSockets, as opposed to other transports, it is valid to
    # reuse `session_id`. The lifetime of SockJS WebSocket session is
    # defined by a lifetime of underlying WebSocket connection. It is
    # correct to have two separate sessions sharing the same
    # `session_id` at the same time.
    def test_reuseSessionId(self):
        on_close = lambda(ws): self.assertFalse(True)

        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws1 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws1.recv(), u'o')

        ws2 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws2.recv(), u'o')

        ws1.send(u'["a"]')
        self.assertEqual(ws1.recv(), u'a["a"]')

        ws2.send(u'["b"]')
        self.assertEqual(ws2.recv(), u'a["b"]')

        ws1.close()
        ws2.close()

        # It is correct to reuse the same `session_id` after closing a
        # previous connection.
        ws1 = websocket.create_connection(ws_url)
        self.assertEqual(ws1.recv(), u'o')
        ws1.send(u'["a"]')
        self.assertEqual(ws1.recv(), u'a["a"]')
        ws1.close()

    # Verify WebSocket headers sanity. Due to HAProxy design the
    # websocket server must support writing response headers *before*
    # receiving -76 nonce. In other words, the websocket code must
    # work like that:
    #
    # * Receive request headers.
    # * Write response headers.
    # * Receive request nonce.
    # * Write response nonce.
    def test_haproxy(self):
        url = base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])

        c = RawHttpConnection(http_url)
        r = c.request('GET', http_url, http='1.1', headers={
                'Connection':'Upgrade',
                'Upgrade':'WebSocket',
                'Origin': origin,
                'Sec-WebSocket-Key1': '4 @1  46546xW%0l 1 5',
                'Sec-WebSocket-Key2': '12998 5 Y3 1  .P00'
                })
        # First check response headers
        self.assertEqual(r.status, 101)
        self.assertEqual(r.headers['connection'].lower(), 'upgrade')
        self.assertEqual(r.headers['upgrade'].lower(), 'websocket')
        self.assertEqual(r.headers['sec-websocket-location'], ws_url)
        self.assertEqual(r.headers['sec-websocket-origin'], origin)
        self.assertFalse('Content-Length' in r.headers)
        # Later send token
        c.send('aaaaaaaa')
        self.assertEqual(c.read()[:16],
                         '\xca4\x00\xd8\xa5\x08G\x97,\xd5qZ\xba\xbfC{')

    # When user sends broken data - broken JSON for example, the
    # server must abruptly terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a')
        with self.assertRaises(websocket.ConnectionClosedException):
            if ws.recv() is None:
                raise websocket.ConnectionClosedException
        ws.close()


# The server must support Hybi-10 protocol
class WebsocketHybi10(Test):
    def test_transport(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)

        self.assertEqual(ws.recv(), 'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), 'a["a"]')
        ws.close()

    def test_close(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # Verify WebSocket headers sanity. Server must support both
    # Hybi-07 and Hybi-10.
    def test_headersSanity(self):
        for version in ['7', '8', '13']:
            url = base_url.split(':',1)[1] + \
                '/000/' + str(uuid.uuid4()) + '/websocket'
            ws_url = 'ws:' + url
            http_url = 'http:' + url
            origin = '/'.join(http_url.split('/')[:3])
            h = {'Upgrade': 'websocket',
                 'Connection': 'Upgrade',
                 'Sec-WebSocket-Version': version,
                 'Sec-WebSocket-Origin': 'http://asd',
                 'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
                 }

            r = GET_async(http_url, headers=h)
            self.assertEqual(r.status, 101)
            self.assertEqual(r['sec-websocket-accept'], 'HSmrc0sMlYUkAGmm5OPpG2HaGWk=')
            self.assertEqual(r['connection'].lower(), 'upgrade')
            self.assertEqual(r['upgrade'].lower(), 'websocket')
            self.assertFalse(r['content-length'])
            r.close()

    # When user sends broken data - broken JSON for example, the
    # server must abruptly terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # As a fun part, Firefox 6.0.2 supports Websockets protocol '7'. But,
    # it doesn't send a normal 'Connection: Upgrade' header. Instead it
    # sends: 'Connection: keep-alive, Upgrade'. Brilliant.
    def test_firefox_602_connection_header(self):
        url = base_url.split(':',1)[1] + \
            '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])
        h = {'Upgrade': 'websocket',
             'Connection': 'keep-alive, Upgrade',
             'Sec-WebSocket-Version': '7',
             'Sec-WebSocket-Origin': 'http://asd',
             'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
             }
        r = GET_async(http_url, headers=h)
        self.assertEqual(r.status, 101)


# XhrPolling: `/*/*/xhr`, `/*/*/xhr_send`
# ---------------------------------------
#
# The server must support xhr-polling.
class XhrPolling(Test):
    # The transport must support CORS requests, and answer correctly
    # to OPTIONS requests.
    def test_options(self):
        for suffix in ['/xhr', '/xhr_send']:
            self.verify_options(base_url + '/abc/abc' + suffix,
                                'OPTIONS, POST')

    # Test the transport itself.
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.verify_content_type(r, 'application/javascript;charset=UTF-8')
        self.verify_cors(r)
        # iOS 6 caches POSTs. Make sure we send no-cache header.
        self.verify_not_cached(r)

        # Xhr transports receive json-encoded array of messages.
        r = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)
        # The content type of `xhr_send` must be set to `text/plain`,
        # even though the response code is `204`. This is due to
        # Firefox/Firebug behaviour - it assumes that the content type
        # is xml and shouts about it.
        self.verify_content_type(r, 'text/plain;charset=UTF-8')
        self.verify_cors(r)
        # iOS 6 caches POSTs. Make sure we send no-cache header.
        self.verify_not_cached(r)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["x"]\n')

    # Publishing messages to a non-existing session must result in
    # a 404 error.
    def test_invalid_session(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr_send', body='["x"]')
        self.verify404(r)

    # The server must behave when invalid json data is sent or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(url + '/xhr_send', body='["x')
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        r = POST(url + '/xhr_send', body='')
        self.assertEqual(r.status, 500)
        self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/xhr_send', body='["a"]')
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)

    # The server must accept messages sent with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')

        ctypes = ['text/plain', 'T', 'application/json', 'application/xml', '',
                  'application/json; charset=utf-8', 'text/xml; charset=utf-8',
                  'text/xml']
        for ct in ctypes:
            r = POST(url + '/xhr_send', body='["a"]', headers={'Content-Type': ct})
            self.assertEqual(r.status, 204)
            self.assertFalse(r.body)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a[' + (',').join(['"a"']*len(ctypes)) +']\n')

    # When client sends a CORS request with
    # 'Access-Control-Request-Headers' header set, the server must
    # echo back this header as 'Access-Control-Allow-Headers'. This is
    # required in order to get CORS working. Browser will be unhappy
    # otherwise.
    def test_request_headers_cors(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr',
                 headers={'Access-Control-Request-Headers': 'a, b, c'})
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertEqual(r['Access-Control-Allow-Headers'], 'a, b, c')

        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr',
                 headers={'Access-Control-Request-Headers': ''})
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertFalse(r['Access-Control-Allow-Headers'])

        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertFalse(r['Access-Control-Allow-Headers'])


# XhrStreaming: `/*/*/xhr_streaming`
# ----------------------------------
class XhrStreaming(Test):
    def test_options(self):
        self.verify_options(base_url + '/abc/abc/xhr_streaming',
                            'OPTIONS, POST')

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'application/javascript;charset=UTF-8')
        self.verify_cors(r)
        # iOS 6 caches POSTs. Make sure we send no-cache header.
        self.verify_not_cached(r)

        # The transport must first send 2KiB of `h` bytes as prelude.
        self.assertEqual(r.read(), 'h' *  2048 + '\n')

        self.assertEqual(r.read(), 'o\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r1.status, 204)
        self.assertFalse(r1.body)

        self.assertEqual(r.read(), 'a["x"]\n')
        r.close()

    def test_response_limit(self):
        # Single streaming request will buffer all data until
        # closed. In order to remove (garbage collect) old messages
        # from the browser memory we should close the connection every
        # now and then. By default we should close a streaming request
        # every 128KiB messages was send. The test server should have
        # this limit decreased to 4096B.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'o\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 128) + '"'
        for i in range(31):
            r1 = POST(url + '/xhr_send', body='[' + msg + ']')
            self.assertEqual(r1.status, 204)
            self.assertEqual(r.read(), 'a[' + msg + ']\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# EventSource: `/*/*/eventsource`
# -------------------------------
#
# For details of this protocol framing read the spec:
#
# * [http://dev.w3.org/html5/eventsource/](http://dev.w3.org/html5/eventsource/)
#
# Beware leading spaces.
class EventSource(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'text/event-stream;charset=UTF-8')
        # As EventSource is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)

        # The transport must first send a new line prelude, due to a
        # bug in Opera.
        self.assertEqual(r.read(), '\r\n')

        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(), 'data: a["x"]\r\n\r\n')

        # This protocol doesn't allow binary data and we need to
        # specially treat leading space, new lines and things like
        # \x00. But, now the protocol json-encodes everything, so
        # there is no way to trigger this case.
        r1 = POST(url + '/xhr_send', body=r'["  \u0000\n\r "]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         'data: a["  \\u0000\\n\\r "]\r\n\r\n')

        r.close()

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        # Although EventSource transport is better, and in theory may
        # not need this mechanism, there are some bugs in the browsers
        # that actually prevent the automatic GC. See:
        #  * https://bugs.webkit.org/show_bug.cgi?id=61863
        #  * http://code.google.com/p/chromium/issues/detail?id=68160
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 4096) + '"'
        r1 = POST(url + '/xhr_send', body='[' + msg + ']')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(), 'data: a[' + msg + ']\r\n\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# HtmlFile: `/*/*/htmlfile`
# -------------------------
#
# Htmlfile transport is based on research done by Michael Carter. It
# requires a famous `document.domain` trick. Read on:
#
# * [http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do](http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do)
# * [http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/](http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/)
#
class HtmlFile(Test):
    head = r'''
<!doctype html>
<html><head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head><body><h2>Don't panic!</h2>
  <script>
    document.domain = document.domain;
    var c = parent.%s;
    c.start();
    function p(d) {c.message(d);};
    window.onload = function() {c.stop();};
  </script>
'''.strip()

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'text/html;charset=UTF-8')
        # As HtmlFile is requested using GET we must be very careful
        # not to allow it being cached.
        self.verify_not_cached(r)

        d = r.read()
        self.assertEqual(d.strip(), self.head % ('callback',))
        self.assertGreater(len(d), 1024)
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         '<script>\np("a[\\"x\\"]");\n</script>\r\n')
        r.close()

    def test_no_callback(self):
        r = GET(base_url + '/a/a/htmlfile')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=callback')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = ('x' * 4096)
        r1 = POST(url + '/xhr_send', body='["' + msg + '"]')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(),
                         '<script>\np("a[\\"' + msg + '\\"]");\n</script>\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())

# JsonpPolling: `/*/*/jsonp`, `/*/*/jsonp_send`
# ---------------------------------------------
class JsonPolling(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'application/javascript;charset=UTF-8')
        # As JsonPolling is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        # Konqueror does weird things on 204. As a workaround we need
        # to respond with something - let it be the string `ok`.
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'text/plain;charset=UTF-8')
        # iOS 6 caches POSTs. Make sure we send no-cache header.
        self.verify_not_cached(r)

        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'callback("a[\\"x\\"]");\r\n')


    def test_no_callback(self):
        r = GET(base_url + '/a/a/jsonp')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    # The server must behave when invalid json data is sent or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        for data in ['', 'd=', 'p=p']:
            r = POST(url + '/jsonp_send', body=data,
                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            self.assertEqual(r.status, 500)
            self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/jsonp_send', body='d=%5B%22b%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"b\\"]");\r\n')

    # The server must accept messages sent with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22abc%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        r = POST(url + '/jsonp_send', body='["%61bc"]',
                 headers={'Content-Type': 'text/plain'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"abc\\",\\"%61bc\\"]");\r\n')

    def test_close(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("c[3000,\\"Go away!\\"]");\r\n')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("c[3000,\\"Go away!\\"]");\r\n')

# JSESSIONID cookie
# -----------------
#
# All transports except WebSockets need sticky session support from
# the load balancer. Some load balancers enable that only when they
# see `JSESSIONID` cookie. User of a sockjs server must be able to
# opt-in for this functionality - and set this cookie for all the
# session urls.
#
class JsessionidCookie(Test):
    # Verify if info has cookie_needed set.
    def test_basic(self):
        r = GET(cookie_base_url + '/info')
        self.assertEqual(r.status, 200)
        self.verify_no_cookie(r)

        data = json.loads(r.body)
        self.assertEqual(data['cookie_needed'], True)

    # Helper to check cookie validity.
    def verify_cookie(self, r):
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=dummy')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    # JSESSIONID cookie must be set by default
    def test_xhr(self):
        # polling url must set cookies
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.verify_cookie(r)

        # Cookie must be echoed back if it's already set.
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr', headers={'Cookie': 'JSESSIONID=abcdef'})
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=abcdef')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    def test_xhr_streaming(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_eventsource(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_htmlfile(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_jsonp(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)


# Raw WebSocket url: `/websocket`
# -------------------------------
#
# SockJS protocol defines a bit of higher level framing. This is okay
# when the browser uses SockJS-client to establish the connection, but
# it's not really appropriate when the connection is being established
# from another program. Although SockJS focuses on server-browser
# communication, it should be straightforward to connect to SockJS
# from the command line or using any programming language.
#
# In order to make writing command-line clients easier, we define this
# `/websocket` entry point. This entry point is special and doesn't
# use any additional custom framing, no open frame, no
# heartbeats. Only raw WebSocket protocol.
class RawWebsocket(Test):
    def test_transport(self):
        ws = WebSocket8Client(base_url + '/websocket')
        ws.send(u'Hello world!\uffff')
        self.assertEqual(ws.recv(), u'Hello world!\uffff')
        ws.close()

    def test_close(self):
        ws = WebSocket8Client(close_base_url + '/websocket')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()



# JSON Unicode Encoding
# =====================
#
# SockJS takes the responsibility of encoding Unicode strings for the
# user.  The idea is that SockJS should properly deliver any valid
# string from the browser to the server and back. This is actually
# quite hard, as browsers do some magical character
# translations. Additionally there are some valid characters from
# JavaScript point of view that are not valid Unicode, called
# surrogates (JavaScript uses UCS-2, which is not really Unicode).
#
# Dealing with unicode surrogates (0xD800-0xDFFF) is quite special. If
# possible we should make sure that server does escape decode
# them. This makes sense for SockJS servers that support UCS-2
# (SockJS-node), but can't really work for servers supporting unicode
# properly (Python).
#
# The browser must escape quite a list of chars, this is due to
# browser mangling outgoing chars on transports like XHR.
escapable_by_client = re.compile(u"[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u2000-\u20ff\ufeff\ufff0-\uffff\x00-\x1f\ufffe\uffff\u0300-\u0333\u033d-\u0346\u034a-\u034c\u0350-\u0352\u0357-\u0358\u035c-\u0362\u0374\u037e\u0387\u0591-\u05af\u05c4\u0610-\u0617\u0653-\u0654\u0657-\u065b\u065d-\u065e\u06df-\u06e2\u06eb-\u06ec\u0730\u0732-\u0733\u0735-\u0736\u073a\u073d\u073f-\u0741\u0743\u0745\u0747\u07eb-\u07f1\u0951\u0958-\u095f\u09dc-\u09dd\u09df\u0a33\u0a36\u0a59-\u0a5b\u0a5e\u0b5c-\u0b5d\u0e38-\u0e39\u0f43\u0f4d\u0f52\u0f57\u0f5c\u0f69\u0f72-\u0f76\u0f78\u0f80-\u0f83\u0f93\u0f9d\u0fa2\u0fa7\u0fac\u0fb9\u1939-\u193a\u1a17\u1b6b\u1cda-\u1cdb\u1dc0-\u1dcf\u1dfc\u1dfe\u1f71\u1f73\u1f75\u1f77\u1f79\u1f7b\u1f7d\u1fbb\u1fbe\u1fc9\u1fcb\u1fd3\u1fdb\u1fe3\u1feb\u1fee-\u1fef\u1ff9\u1ffb\u1ffd\u2000-\u2001\u20d0-\u20d1\u20d4-\u20d7\u20e7-\u20e9\u2126\u212a-\u212b\u2329-\u232a\u2adc\u302b-\u302c\uaab2-\uaab3\uf900-\ufa0d\ufa10\ufa12\ufa15-\ufa1e\ufa20\ufa22\ufa25-\ufa26\ufa2a-\ufa2d\ufa30-\ufa6d\ufa70-\ufad9\ufb1d\ufb1f\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufb4e]")
#
# The server is able to send much more chars verbatim. But, it can't
# send Unicode surrogates over Websockets, also various \u2xxxx chars
# get mangled. Additionally, if the server is capable of handling
# UCS-2 (ie: 16 bit character size), it should be able to deal with
# Unicode surrogates 0xD800-0xDFFF:
# http://en.wikipedia.org/wiki/Mapping_of_Unicode_characters#Surrogates
escapable_by_server = re.compile(u"[\x00-\x1f\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufff0-\uffff]")

client_killer_string_esc = '"' + ''.join([
        r'\u%04x' % (i) for i in range(65536)
            if escapable_by_client.match(unichr(i))]) + '"'
server_killer_string_esc = '"' + ''.join([
        r'\u%04x'% (i) for i in range(255, 65536)
            if escapable_by_server.match(unichr(i))]) + '"'

class JSONEncoding(Test):
    def test_xhr_server_encodes(self):
        # Make sure that server encodes at least all the characters
        # it's supposed to encode.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '["' + json.loads(server_killer_string_esc) + '"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we sent previously, aka - escaped.
        self.assertEqual(recv, server_killer_string_esc)

    def test_xhr_server_decodes(self):
        # Make sure that server decodes the chars we're customly
        # encoding.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '[' + client_killer_string_esc + ']' # Sending escaped
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we sent previously. We don't
        # really need to know what exactly got escaped and what not.
        a = json.loads(recv)
        b = json.loads(client_killer_string_esc)
        self.assertEqual(a, b)


# Handling close
# ==============
#
# Dealing with session closure is quite complicated part of the
# protocol. The exact details here don't matter that much to the
# client side, but it's good to have a common behaviour on the server
# side.
#
# This is less about defining the protocol and more about sanity
# checking implementations.
class HandlingClose(Test):
    # When server is closing session, it should unlink current
    # request. That means, if a new request appears, it should receive
    # an application close message rather than "Another connection
    # still open" message.
    def test_close_frame(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')
        self.assertEqual(r1.read(), 'c[3000,"Go away!"]\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[3000,"Go away!"]\n')

        # HTTP streaming requests should be automatically closed after
        # close.
        self.assertFalse(r1.read())
        self.assertFalse(r2.read())

    def test_close_request(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')

        # HTTP streaming requests should be automatically closed after
        # getting the close frame.
        self.assertFalse(r2.read())

    # When a polling request is closed by a network error - not by
    # server, the session should be automatically closed. When there
    # is a network error - we're in an undefined state. Some messages
    # may have been lost, there is not much we can do about it.
    def test_abort_xhr_streaming(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')
        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        # Can't do second polling request now.
        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')
        self.assertFalse(r2.read())

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST_async(url + '/xhr_streaming')
        r3.read() # prelude
        self.assertTrue(r3.read() in ['o\n', 'c[1002,"Connection interrupted"]\n'])
        r3.close()

    # The same for polling transports
    def test_abort_xhr_polling(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST(url + '/xhr')
        self.assertEqual(r1.body, 'o\n')

        r1 = old_POST_async(url + '/xhr', load=False)
        time.sleep(0.25)

        # Can't do second polling request now.
        r2 = POST(url + '/xhr')
        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST(url + '/xhr')
        self.assertTrue(r3.body in ['o\n', 'c[1002,"Connection interrupted"]\n'])

# Http 1.0 and 1.1 chunking
# =========================
#
# There seem to be a lot of confusion about http/1.0 and http/1.1
# content-length and transfer-encoding:chunking headers. Although
# following tests don't really test anything sockjs specific, it's
# good to make sure that the server is behaving about this.
#
# It is not the intention of this test to verify all possible urls -
# merely to check the sanity of http server implementation.  It is
# assumed that the implementator is able to apply presented behaviour
# to other urls served by the sockjs server.
class Http10(Test):
    # We're going to test a greeting url. No dynamic content, just the
    # simplest possible response.
    def test_synchronous(self):
        c = RawHttpConnection(base_url)
        # In theory 'connection:Keep-Alive' isn't a valid http/1.0
        # header, but in this header may in practice be issued by a
        # http/1.0 client:
        # http://www.freesoft.org/CIE/RFC/2068/248.htm
        r = c.request('GET', base_url, http='1.0',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # In practice the exact http version on the response doesn't
        # really matter. Many serves always respond 1.1.
        self.assertTrue(r.http in ['1.0', '1.1'])
        # Transfer-encoding is not allowed in http/1.0.
        self.assertFalse(r.headers.get('transfer-encoding'))

        # There are two ways to give valid response. Use
        # Content-Length (and maybe connection:Keep-Alive) or
        # Connection: close.
        if not r.headers.get('content-length'):
            self.assertEqual(r.headers['connection'].lower(), 'close')
            self.assertEqual(c.read(), 'Welcome to SockJS!\n')
            self.assertTrue(c.closed())
        else:
            self.assertEqual(int(r.headers['content-length']), 19)
            self.assertEqual(c.read(19), 'Welcome to SockJS!\n')
            connection = r.headers.get('connection', '').lower()
            if connection in ['close', '']:
                # Connection-close behaviour is default in http 1.0
                self.assertTrue(c.closed())
            else:
                self.assertEqual(connection, 'keep-alive')
                # We should be able to issue another request on the same connection
                r = c.request('GET', base_url, http='1.0',
                              headers={'Connection':'Keep-Alive'})
                self.assertEqual(r.status, 200)

    def test_streaming(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        c = RawHttpConnection(url)
        # In theory 'connection:Keep-Alive' isn't a valid http/1.0
        # header, but in this header may in practice be issued by a
        # http/1.0 client:
        # http://www.freesoft.org/CIE/RFC/2068/248.htm
        r = c.request('POST', url + '/xhr_streaming', http='1.0',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # Transfer-encoding is not allowed in http/1.0.
        self.assertFalse(r.headers.get('transfer-encoding'))
        # Content-length is not allowed - we don't know it yet.
        self.assertFalse(r.headers.get('content-length'))

        # `Connection` should be not set or be `close`. On the other
        # hand, if it is set to `Keep-Alive`, it won't really hurt, as
        # we are confident that neither `Content-Length` nor
        # `Transfer-Encoding` are set.

        # This is a the same logic as HandlingClose.test_close_frame
        self.assertEqual(c.read(2048+1)[0], 'h') # prelude
        self.assertEqual(c.read(2), 'o\n')
        self.assertEqual(c.read(19), 'c[3000,"Go away!"]\n')
        self.assertTrue(c.closed())


class Http11(Test):
    def test_synchronous(self):
        c = RawHttpConnection(base_url)
        r = c.request('GET', base_url, http='1.1',
                      headers={'Connection':'Keep-Alive'})
        # Keepalive is default in http 1.1
        self.assertTrue(r.http, '1.1')
        self.assertTrue(r.headers.get('connection', '').lower() in ['keep-alive', ''],
                         "Your server doesn't support connection:Keep-Alive")
        # Server should use 'Content-Length' or 'Transfer-Encoding'
        if r.headers.get('content-length'):
            self.assertEqual(int(r.headers['content-length']), 19)
            self.assertEqual(c.read(19), 'Welcome to SockJS!\n')
            self.assertFalse(r.headers.get('transfer-encoding'))
        else:
            self.assertEqual(r.headers['transfer-encoding'].lower(), 'chunked')
            self.assertEqual(c.read_chunk(), 'Welcome to SockJS!\n')
            self.assertEqual(c.read_chunk(), '')
        # We should be able to issue another request on the same connection
        r = c.request('GET', base_url, http='1.1',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)

    def test_streaming(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        c = RawHttpConnection(url)
        r = c.request('POST', url + '/xhr_streaming', http='1.1',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # Transfer-encoding is required in http/1.1.
        self.assertTrue(r.headers['transfer-encoding'].lower(), 'chunked')
        # Content-length is not allowed.
        self.assertFalse(r.headers.get('content-length'))
        # Connection header can be anything, so don't bother verifying it.

        # This is a the same logic as HandlingClose.test_close_frame
        self.assertEqual(c.read_chunk()[0], 'h') # prelude
        self.assertEqual(c.read_chunk(), 'o\n')
        self.assertEqual(c.read_chunk(), 'c[3000,"Go away!"]\n')
        self.assertEqual(c.read_chunk(), '')


# Footnote
# ========

# Make this script runnable.
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = sockjs-protocol-0.3
#!/usr/bin/env python
"""
[**SockJS-protocol**](https://github.com/sockjs/sockjs-protocol) is an
effort to define a protocol between in-browser
[SockJS-client](https://github.com/sockjs/sockjs-client) and its
server-side counterparts, like
[SockJS-node](https://github.com/sockjs/sockjs-client). This should
help others to write alternative server implementations.


This protocol definition is also a runnable test suite, do run it
against your server implementation. Supporting all the tests doesn't
guarantee that SockJS client will work flawlessly, end-to-end tests
using real browsers are always required.
"""
import os
import time
import json
import re
import unittest2 as unittest
from utils_03 import GET, GET_async, POST, POST_async, OPTIONS, old_POST_async
from utils_03 import WebSocket8Client
from utils_03 import RawHttpConnection
import uuid


# Base URL
# ========

"""
The SockJS server provides one or more SockJS services. The services
are usually exposed with a simple url prefixes, like:
`http://localhost:8000/echo` or
`http://localhost:8000/broadcast`. We'll call this kind of url a
`base_url`. There is nothing wrong with base url being more complex,
like `http://localhost:8000/a/b/c/d/echo`. Base url should
never end with a slash.

Base url is the url that needs to be supplied to the SockJS client.

All paths under base url are controlled by SockJS server and are
defined by SockJS protocol.

SockJS protocol can be using either http or https.

To run this tests server pointed by `base_url` needs to support
following services:

 - `echo` - responds with identical data as received
 - `disabled_websocket_echo` - identical to `echo`, but with websockets disabled
 - `cookie_needed_echo` - identical to `echo`, but with JSESSIONID cookies sent
 - `close` - server immediately closes the session

This tests should not be run more often than once in five seconds -
many tests operate on the same (named) sessions and they need to have
enough time to timeout.
"""
test_top_url = os.environ.get('SOCKJS_URL', 'http://localhost:8081')
base_url = test_top_url + '/echo'
close_base_url = test_top_url + '/close'
wsoff_base_url = test_top_url + '/disabled_websocket_echo'
cookie_base_url = test_top_url + '/cookie_needed_echo'


# Static URLs
# ===========

class Test(unittest.TestCase):
    # We are going to test several `404/not found` pages. We don't
    # define a body or a content type.
    def verify404(self, r):
        self.assertEqual(r.status, 404)

    # In some cases `405/method not allowed` is more appropriate.
    def verify405(self, r):
        self.assertEqual(r.status, 405)
        self.assertFalse(r['content-type'])
        self.assertTrue(r['allow'])
        self.assertFalse(r.body)

    # Multiple transport protocols need to support OPTIONS method. All
    # responses to OPTIONS requests must be cacheable and contain
    # appropriate headers.
    def verify_options(self, url, allowed_methods):
        for origin in [None, 'test', 'null']:
            h = {}
            if origin:
                h['Origin'] = origin
            r = OPTIONS(url, headers=h)
            self.assertEqual(r.status, 204)
            self.assertTrue(re.search('public', r['Cache-Control']))
            self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                            "max-age must be large, one year (31536000) is best")
            self.assertTrue(r['Expires'])
            self.assertTrue(int(r['access-control-max-age']) > 1000000)
            self.assertEqual(r['Access-Control-Allow-Methods'], allowed_methods)
            self.assertFalse(r.body)
            self.verify_cors(r, origin)

    def verify_no_cookie(self, r):
        self.assertFalse(r['Set-Cookie'])

    # Most of the XHR/Ajax based transports do work CORS if proper
    # headers are set.
    def verify_cors(self, r, origin=None):
        if origin and origin != 'null':
            self.assertEqual(r['access-control-allow-origin'], origin)
        else:
            self.assertEqual(r['access-control-allow-origin'], '*')
        # In order to get cookies (`JSESSIONID` mostly) flying, we
        # need to set `allow-credentials` header to true.
        self.assertEqual(r['access-control-allow-credentials'], 'true')

    # Sometimes, due to transports limitations we need to request
    # private data using GET method. In such case it's very important
    # to disallow any caching.
    def verify_not_cached(self, r, origin=None):
        self.assertEqual(r['Cache-Control'],
                         'no-store, no-cache, must-revalidate, max-age=0')
        self.assertFalse(r['Expires'])
        self.assertFalse(r['Last-Modified'])


# Greeting url: `/`
# ----------------
class BaseUrlGreeting(Test):
    # The most important part of the url scheme, is without doubt, the
    # top url. Make sure the greeting is valid.
    def test_greeting(self):
        for url in [base_url, base_url + '/']:
            r = GET(url)
            self.assertEqual(r.status, 200)
            self.assertEqual(r['content-type'], 'text/plain; charset=UTF-8')
            self.assertEqual(r.body, 'Welcome to SockJS!\n')
            self.verify_no_cookie(r)

    # Other simple requests should return 404.
    def test_notFound(self):
        for suffix in ['/a', '/a.html', '//', '///', '/a/a', '/a/a/', '/a',
                       '/a/']:
            self.verify404(GET(base_url + suffix))


# IFrame page: `/iframe*.html`
# ----------------------------
class IframePage(Test):
    """
    Some transports don't support cross domain communication
    (CORS). In order to support them we need to do a cross-domain
    trick: on remote (server) domain we serve an simple html page,
    that loads back SockJS client javascript and is able to
    communicate with the server within the same domain.
    """
    iframe_body = re.compile('''
^<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function\(\){SockJS.bootstrap_iframe\(\);};
  </script>
  <script src="(?P<sockjs_url>[^"]*)"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>$
'''.strip())

    # SockJS server must provide this html page.
    def test_simpleUrl(self):
        self.verify(base_url + '/iframe.html')

    # To properly utilize caching, the same content must be served
    # for request which try to version the iframe. The server may want
    # to give slightly different answer for every SockJS client
    # revision.
    def test_versionedUrl(self):
        for suffix in ['/iframe-a.html', '/iframe-.html', '/iframe-0.1.2.html',
                       '/iframe-0.1.2abc-dirty.2144.html']:
            self.verify(base_url + suffix)

    # In some circumstances (`devel` set to true) client library
    # wants to skip caching altogether. That is achieved by
    # supplying a random query string.
    def test_queriedUrl(self):
        for suffix in ['/iframe-a.html?t=1234', '/iframe-0.1.2.html?t=123414',
                       '/iframe-0.1.2abc-dirty.2144.html?t=qweqweq123']:
            self.verify(base_url + suffix)

    # Malformed urls must give 404 answer.
    def test_invalidUrl(self):
        for suffix in ['/iframe.htm', '/iframe', '/IFRAME.HTML', '/IFRAME',
                       '/iframe.HTML', '/iframe.xml', '/iframe-/.html']:
            r = GET(base_url + suffix)
            self.verify404(r)

    # The '/iframe.html' page and its variants must give `200/ok` and be
    # served with 'text/html' content type.
    def verify(self, url):
        r = GET(url)
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'], 'text/html; charset=UTF-8')
        # The iframe page must be strongly cacheable, supply
        # Cache-Control, Expires and Etag headers and avoid
        # Last-Modified header.
        self.assertTrue(re.search('public', r['Cache-Control']))
        self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                        "max-age must be large, one year (31536000) is best")
        self.assertTrue(r['Expires'])
        self.assertTrue(r['ETag'])
        self.assertFalse(r['last-modified'])

        # Body must be exactly as specified, with the exception of
        # `sockjs_url`, which should be configurable.
        match = self.iframe_body.match(r.body.strip())
        self.assertTrue(match)
        # `Sockjs_url` must be a valid url and should utilize caching.
        sockjs_url = match.group('sockjs_url')
        self.assertTrue(sockjs_url.startswith('/') or
                        sockjs_url.startswith('http'))
        self.verify_no_cookie(r)
        return r


    # The iframe page must be strongly cacheable. ETag headers must
    # not change too often. Server must support 'if-none-match'
    # requests.
    def test_cacheability(self):
        r1 = GET(base_url + '/iframe.html')
        r2 = GET(base_url + '/iframe.html')
        self.assertEqual(r1['etag'], r2['etag'])
        self.assertTrue(r1['etag']) # Let's make sure ETag isn't None.

        r = GET(base_url + '/iframe.html', headers={'If-None-Match': r1['etag']})
        self.assertEqual(r.status, 304)
        self.assertFalse(r['content-type'])
        self.assertFalse(r.body)

# Info test: `/info`
# ------------------
#
# Warning: this is a replacement of `/chunking_test` functionality
# from SockJS 0.1.
class InfoTest(Test):
    # This url is called before the client starts the session. It's
    # used to check server capabilities (websocket support, cookies
    # requiremet) and to get the value of "origin" setting (currently
    # not used).
    #
    # But more importantly, the call to this url is used to measure
    # the roundtrip time between the client and the server. So, please,
    # do respond to this url in a timely fashin.
    def test_basic(self):
        r = GET(base_url + '/info')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['content-type'],
                         'application/json; charset=UTF-8')
        self.verify_no_cookie(r)
        self.verify_not_cached(r)
        self.verify_cors(r)

        data = json.loads(r.body)
        # Are websockets enabled on the server?
        self.assertEqual(data['websocket'], True)
        # Do transports need to support cookies (ie: for load
        # balancing purposes.
        self.assertTrue(data['cookie_needed'] in  [True, False])
        # List of allowed origins. Currently ignored.
        self.assertEqual(data['origins'], ['*:*'])
        # Source of entropy for random number generator.
        self.assertTrue(type(data['entropy']) in [int, long])

    # As browsers don't have a good entropy source, the server must
    # help with tht. Info url must supply a good, unpredictable random
    # number from the range <0; 2^32-1> to feed the browser.
    def test_entropy(self):
        r1 = GET(base_url + '/info')
        data1 = json.loads(r1.body)
        r2 = GET(base_url + '/info')
        data2 = json.loads(r2.body)
        self.assertTrue(type(data1['entropy']) in [int, long])
        self.assertTrue(type(data2['entropy']) in [int, long])
        self.assertNotEqual(data1['entropy'], data2['entropy'])

    # Info url must support CORS.
    def test_options(self):
        self.verify_options(base_url + '/info', 'OPTIONS, GET')

    # SockJS client may be hosted from file:// url. In practice that
    # means the 'Origin' headers sent by the browser will have a value
    # of a string "null". Unfortunately, just echoing back "null"
    # won't work - browser will understand that as a rejection. We
    # must respond with star "*" origin in such case.
    def test_options_null_origin(self):
            url = base_url + '/info'
            r = OPTIONS(url, headers={'Origin': 'null'})
            self.assertEqual(r.status, 204)
            self.assertFalse(r.body)
            self.assertEqual(r['access-control-allow-origin'], '*')

    # The 'disabled_websocket_echo' service should have websockets
    # disabled.
    def test_disabled_websocket(self):
        r = GET(wsoff_base_url + '/info')
        self.assertEqual(r.status, 200)
        data = json.loads(r.body)
        self.assertEqual(data['websocket'], False)


# Session URLs
# ============

# Top session URL: `/<server>/<session>`
# --------------------------------------
#
# The session between the client and the server is always initialized
# by the client. The client chooses `server_id`, which should be a
# three digit number: 000 to 999. It can be supplied by user or
# randomly generated. The main reason for this parameter is to make it
# easier to configure load balancer - and enable sticky sessions based
# on first part of the url.
#
# Second parameter `session_id` must be a random string, unique for
# every session.
#
# It is undefined what happens when two clients share the same
# `session_id`. It is a client responsibility to choose identifier
# with enough entropy.
#
# Neither server nor client API's can expose `session_id` to the
# application. This field must be protected from the app.
class SessionURLs(Test):

    # The server must accept any value in `server` and `session` fields.
    def test_anyValue(self):
        self.verify('/a/a')
        for session_part in ['/_/_', '/1/1', '/abcdefgh_i-j%20/abcdefg_i-j%20']:
            self.verify(session_part)

    # To test session URLs we're going to use `xhr-polling` transport
    # facilitites.
    def verify(self, session_part):
        r = POST(base_url + session_part + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

    # But not an empty string, anything containing dots or paths with
    # less or more parts.
    def test_invalidPaths(self):
        for suffix in ['//', '/a./a', '/a/a.', '/./.' ,'/', '///']:
            self.verify404(GET(base_url + suffix + '/xhr'))
            self.verify404(POST(base_url + suffix + '/xhr'))

    # A session is identified by only `session_id`. `server_id` is a
    # parameter for load balancer and must be ignored by the server.
    def test_ignoringServerId(self):
        ''' See Protocol.test_simpleSession for explanation. '''
        session_id = str(uuid.uuid4())
        r = POST(base_url + '/000/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        payload = '["a"]'
        r = POST(base_url + '/000/' + session_id + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        r = POST(base_url + '/999/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

# Protocol and framing
# --------------------
#
# SockJS tries to stay API-compatible with WebSockets, but not on the
# network layer. For technical reasons SockJS must introduce custom
# framing and simple custom protocol.
#
# ### Framing accepted by the client
#
# SockJS client accepts following frames:
#
# * `o` - Open frame. Every time a new session is established, the
#   server must immediately send the open frame. This is required, as
#   some protocols (mostly polling) can't distinguish between a
#   properly established connection and a broken one - we must
#   convince the client that it is indeed a valid url and it can be
#   expecting further messages in the future on that url.
#
# * `h` - Heartbeat frame. Most loadbalancers have arbitrary timeouts
#   on connections. In order to keep connections from breaking, the
#   server must send a heartbeat frame every now and then. The typical
#   delay is 25 seconds and should be configurable.
#
# * `a` - Array of json-encoded messages. For example: `a["message"]`.
#
# * `c` - Close frame. This frame is send to the browser every time
#   the client asks for data on closed connection. This may happen
#   multiple times. Close frame contains a code and a string explaining
#   a reason of closure, like: `c[3000,"Go away!"]`.
#
# ### Framing accepted by the server
#
# SockJS server does not have any framing defined. All incoming data
# is treated as incoming messages, either single json-encoded messages
# or an array of json-encoded messages, depending on transport.
#
# ### Tests
#
# To explain the protocol we'll use `xhr-polling` transport
# facilities.
class Protocol(Test):
    # When server receives a request with unknown `session_id` it must
    # recognize that as request for a new session. When server opens a
    # new sesion it must immediately send an frame containing a letter
    # `o`.
    def test_simpleSession(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        "New line is a frame delimiter specific for xhr-polling"
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        # After a session was established the server needs to accept
        # requests for sending messages.
        "Xhr-polling accepts messages as a list of JSON-encoded strings."
        payload = '["a"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        '''We're using an echo service - we'll receive our message
        back. The message is encoded as an array 'a'.'''
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

        # Sending messages to not existing sessions is invalid.
        payload = '["a"]'
        r = POST(base_url + '/000/bad_session/xhr_send', body=payload)
        self.verify404(r)

        # The session must time out after 5 seconds of not having a
        # receiving connection. The server must send a heartbeat frame
        # every 25 seconds. The heartbeat frame contains a single `h`
        # character. This delay may be configurable.
        pass
        # The server must not allow two receiving connections to wait
        # on a single session. In such case the server must send a
        # close frame to the new connection.
        r1 = old_POST_async(trans_url + '/xhr', load=False)
        r2 = POST(trans_url + '/xhr')

        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')
        self.assertEqual(r2.status, 200)

        r1.close()

    # The server may terminate the connection, passing error code and
    # message.
    def test_closeSession(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')

        # Until the timeout occurs, the server must constantly serve
        # the close message.
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')


# WebSocket protocols: `/*/*/websocket`
# -------------------------------------
import websocket

# The most important feature of SockJS is to support native WebSocket
# protocol. A decent SockJS server should support at least the
# following variants:
#
#   - hixie-75 (Chrome 4, Safari 5.0.0)
#   - hixie-76/hybi-00 (Chrome 6, Safari 5.0.1)
#   - hybi-07 (Firefox 6)
#   - hybi-10 (Firefox 7, Chrome 14)
#
class WebsocketHttpErrors(Test):
    # Normal requests to websocket should not succeed.
    def test_httpMethod(self):
        r = GET(base_url + '/0/0/websocket')
        self.assertEqual(r.status, 400)
        self.assertTrue('Can "Upgrade" only to "WebSocket".' in r.body)

    # Some proxies and load balancers can rewrite 'Connection' header,
    # in such case we must refuse connection.
    def test_invalidConnectionHeader(self):
        r = GET(base_url + '/0/0/websocket', headers={'Upgrade': 'WebSocket',
                                                      'Connection': 'close'})
        self.assertEqual(r.status, 400)
        self.assertTrue('"Connection" must be "Upgrade".', r.body)

    # WebSocket should only accept GET
    def test_invalidMethod(self):
        for h in [{'Upgrade': 'WebSocket', 'Connection': 'Upgrade'},
                  {}]:
            r = POST(base_url + '/0/0/websocket', headers=h)
            self.verify405(r)


# Support WebSocket Hixie-76 protocol
class WebsocketHixie76(Test):
    def test_transport(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    def test_close(self):
        ws_url = 'ws:' + close_base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')

        # The connection should be closed after the close frame.
        with self.assertRaises(websocket.ConnectionClosedException):
            if ws.recv() is None:
                raise websocket.ConnectionClosedException
        ws.close()

    # Empty frames must be ignored by the server side.
    def test_empty_frame(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    # For WebSockets, as opposed to other transports, it is valid to
    # reuse `session_id`. The lifetime of SockJS WebSocket session is
    # defined by a lifetime of underlying WebSocket connection. It is
    # correct to have two separate sessions sharing the same
    # `session_id` at the same time.
    def test_reuseSessionId(self):
        on_close = lambda(ws): self.assertFalse(True)

        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws1 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws1.recv(), u'o')

        ws2 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws2.recv(), u'o')

        ws1.send(u'"a"')
        self.assertEqual(ws1.recv(), u'a["a"]')

        ws2.send(u'"b"')
        self.assertEqual(ws2.recv(), u'a["b"]')

        ws1.close()
        ws2.close()

        # It is correct to reuse the same `session_id` after closing a
        # previous connection.
        ws1 = websocket.create_connection(ws_url)
        self.assertEqual(ws1.recv(), u'o')
        ws1.send(u'"a"')
        self.assertEqual(ws1.recv(), u'a["a"]')
        ws1.close()

    # Verify WebSocket headers sanity. Due to HAProxy design the
    # websocket server must support writing response headers *before*
    # receiving -76 nonce. In other words, the websocket code must
    # work like that:
    #
    # * Receive request headers.
    # * Write response headers.
    # * Receive request nonce.
    # * Write response nonce.
    def test_haproxy(self):
        url = base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])

        c = RawHttpConnection(http_url)
        r = c.request('GET', http_url, http='1.1', headers={
                'Connection':'Upgrade',
                'Upgrade':'WebSocket',
                'Origin': origin,
                'Sec-WebSocket-Key1': '4 @1  46546xW%0l 1 5',
                'Sec-WebSocket-Key2': '12998 5 Y3 1  .P00'
                })
        # First check response headers
        self.assertEqual(r.status, 101)
        self.assertEqual(r.headers['connection'].lower(), 'upgrade')
        self.assertEqual(r.headers['upgrade'].lower(), 'websocket')
        self.assertEqual(r.headers['sec-websocket-location'], ws_url)
        self.assertEqual(r.headers['sec-websocket-origin'], origin)
        self.assertFalse('Content-Length' in r.headers)
        # Later send token
        c.send('aaaaaaaa')
        self.assertEqual(c.read()[:16],
                         '\xca4\x00\xd8\xa5\x08G\x97,\xd5qZ\xba\xbfC{')

    # When user sends broken data - broken JSON for example, the
    # server must abruptly terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a')
        with self.assertRaises(websocket.ConnectionClosedException):
            if ws.recv() is None:
                raise websocket.ConnectionClosedException
        ws.close()


# The server must support Hybi-10 protocol
class WebsocketHybi10(Test):
    def test_transport(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)

        self.assertEqual(ws.recv(), 'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), 'a["a"]')
        ws.close()

    def test_close(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # Verify WebSocket headers sanity. Server must support both
    # Hybi-07 and Hybi-10.
    def test_headersSanity(self):
        for version in ['7', '8', '13']:
            url = base_url.split(':',1)[1] + \
                '/000/' + str(uuid.uuid4()) + '/websocket'
            ws_url = 'ws:' + url
            http_url = 'http:' + url
            origin = '/'.join(http_url.split('/')[:3])
            h = {'Upgrade': 'websocket',
                 'Connection': 'Upgrade',
                 'Sec-WebSocket-Version': version,
                 'Sec-WebSocket-Origin': 'http://asd',
                 'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
                 }

            r = GET_async(http_url, headers=h)
            self.assertEqual(r.status, 101)
            self.assertEqual(r['sec-websocket-accept'], 'HSmrc0sMlYUkAGmm5OPpG2HaGWk=')
            self.assertEqual(r['connection'].lower(), 'upgrade')
            self.assertEqual(r['upgrade'].lower(), 'websocket')
            self.assertFalse(r['content-length'])
            r.close()

    # When user sends broken data - broken JSON for example, the
    # server must abruptly terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # As a fun part, Firefox 6.0.2 supports Websockets protocol '7'. But,
    # it doesn't send a normal 'Connection: Upgrade' header. Instead it
    # sends: 'Connection: keep-alive, Upgrade'. Brilliant.
    def test_firefox_602_connection_header(self):
        url = base_url.split(':',1)[1] + \
            '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])
        h = {'Upgrade': 'websocket',
             'Connection': 'keep-alive, Upgrade',
             'Sec-WebSocket-Version': '7',
             'Sec-WebSocket-Origin': 'http://asd',
             'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
             }
        r = GET_async(http_url, headers=h)
        self.assertEqual(r.status, 101)


# XhrPolling: `/*/*/xhr`, `/*/*/xhr_send`
# ---------------------------------------
#
# The server must support xhr-polling.
class XhrPolling(Test):
    # The transport must support CORS requests, and answer correctly
    # to OPTIONS requests.
    def test_options(self):
        for suffix in ['/xhr', '/xhr_send']:
            self.verify_options(base_url + '/abc/abc' + suffix,
                                'OPTIONS, POST')

    # Test the transport itself.
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['content-type'],
                         'application/javascript; charset=UTF-8')
        self.verify_cors(r)

        # Xhr transports receive json-encoded array of messages.
        r = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)
        # The content type of `xhr_send` must be set to `text/plain`,
        # even though the response code is `204`. This is due to
        # Firefox/Firebug behaviour - it assumes that the content type
        # is xml and shouts about it.
        self.assertEqual(r['content-type'], 'text/plain; charset=UTF-8')
        self.verify_cors(r)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["x"]\n')

    # Publishing messages to a non-existing session must result in
    # a 404 error.
    def test_invalid_session(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr_send', body='["x"]')
        self.verify404(r)

    # The server must behave when invalid json data is send or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(url + '/xhr_send', body='["x')
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        r = POST(url + '/xhr_send', body='')
        self.assertEqual(r.status, 500)
        self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/xhr_send', body='["a"]')
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)

    # The server must accept messages send with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')

        ctypes = ['text/plain', 'T', 'application/json', 'application/xml', '',
                  'application/json; charset=utf-8', 'text/xml; charset=utf-8',
                  'text/xml']
        for ct in ctypes:
            r = POST(url + '/xhr_send', body='["a"]', headers={'Content-Type': ct})
            self.assertEqual(r.status, 204)
            self.assertFalse(r.body)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a[' + (',').join(['"a"']*len(ctypes)) +']\n')

    # When client sends a CORS request with
    # 'Access-Control-Request-Headers' header set, the server must
    # echo back this header as 'Access-Control-Allow-Headers'. This is
    # required in order to get CORS working. Browser will be unhappy
    # otherwise.
    def test_request_headers_cors(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr',
                 headers={'Access-Control-Request-Headers': 'a, b, c'})
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertEqual(r['Access-Control-Allow-Headers'], 'a, b, c')

        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr',
                 headers={'Access-Control-Request-Headers': ''})
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertFalse(r['Access-Control-Allow-Headers'])

        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertFalse(r['Access-Control-Allow-Headers'])


# XhrStreaming: `/*/*/xhr_streaming`
# ----------------------------------
class XhrStreaming(Test):
    def test_options(self):
        self.verify_options(base_url + '/abc/abc/xhr_streaming',
                            'OPTIONS, POST')

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'application/javascript; charset=UTF-8')
        self.verify_cors(r)

        # The transport must first send 2KiB of `h` bytes as prelude.
        self.assertEqual(r.read(), 'h' *  2048 + '\n')

        self.assertEqual(r.read(), 'o\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r1.status, 204)
        self.assertFalse(r1.body)

        self.assertEqual(r.read(), 'a["x"]\n')
        r.close()

    def test_response_limit(self):
        # Single streaming request will buffer all data until
        # closed. In order to remove (garbage collect) old messages
        # from the browser memory we should close the connection every
        # now and then. By default we should close a streaming request
        # every 128KiB messages was send. The test server should have
        # this limit decreased to 4096B.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'o\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 128) + '"'
        for i in range(31):
            r1 = POST(url + '/xhr_send', body='[' + msg + ']')
            self.assertEqual(r1.status, 204)
            self.assertEqual(r.read(), 'a[' + msg + ']\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# EventSource: `/*/*/eventsource`
# -------------------------------
#
# For details of this protocol framing read the spec:
#
# * [http://dev.w3.org/html5/eventsource/](http://dev.w3.org/html5/eventsource/)
#
# Beware leading spaces.
class EventSource(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'text/event-stream; charset=UTF-8')
        # As EventSource is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)

        # The transport must first send a new line prelude, due to a
        # bug in Opera.
        self.assertEqual(r.read(), '\r\n')

        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(), 'data: a["x"]\r\n\r\n')

        # This protocol doesn't allow binary data and we need to
        # specially treat leading space, new lines and things like
        # \x00. But, now the protocol json-encodes everything, so
        # there is no way to trigger this case.
        r1 = POST(url + '/xhr_send', body=r'["  \u0000\n\r "]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         'data: a["  \\u0000\\n\\r "]\r\n\r\n')

        r.close()

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        # Although EventSource transport is better, and in theory may
        # not need this mechanism, there are some bugs in the browsers
        # that actually prevent the automatic GC. See:
        #  * https://bugs.webkit.org/show_bug.cgi?id=61863
        #  * http://code.google.com/p/chromium/issues/detail?id=68160
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 4096) + '"'
        r1 = POST(url + '/xhr_send', body='[' + msg + ']')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(), 'data: a[' + msg + ']\r\n\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# HtmlFile: `/*/*/htmlfile`
# -------------------------
#
# Htmlfile transport is based on research done by Michael Carter. It
# requires a famous `document.domain` trick. Read on:
#
# * [http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do](http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do)
# * [http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/](http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/)
#
class HtmlFile(Test):
    head = r'''
<!doctype html>
<html><head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head><body><h2>Don't panic!</h2>
  <script>
    document.domain = document.domain;
    var c = parent.%s;
    c.start();
    function p(d) {c.message(d);};
    window.onload = function() {c.stop();};
  </script>
'''.strip()

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'text/html; charset=UTF-8')
        # As HtmlFile is requested using GET we must be very careful
        # not to allow it being cached.
        self.verify_not_cached(r)

        d = r.read()
        self.assertEqual(d.strip(), self.head % ('callback',))
        self.assertGreater(len(d), 1024)
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         '<script>\np("a[\\"x\\"]");\n</script>\r\n')
        r.close()

    def test_no_callback(self):
        r = GET(base_url + '/a/a/htmlfile')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=callback')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = ('x' * 4096)
        r1 = POST(url + '/xhr_send', body='["' + msg + '"]')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(),
                         '<script>\np("a[\\"' + msg + '\\"]");\n</script>\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())

# JsonpPolling: `/*/*/jsonp`, `/*/*/jsonp_send`
# ---------------------------------------------
class JsonPolling(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'],
                         'application/javascript; charset=UTF-8')
        # As JsonPolling is requested using GET we must be very
        # carefull not to allow it being cached.
        self.verify_not_cached(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        # Konqueror does weird things on 204. As a workaround we need
        # to respond with something - let it be the string `ok`.
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.assertEqual(r['Content-Type'], 'text/plain; charset=UTF-8')

        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'callback("a[\\"x\\"]");\r\n')


    def test_no_callback(self):
        r = GET(base_url + '/a/a/jsonp')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    # The server must behave when invalid json data is send or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        for data in ['', 'd=', 'p=p']:
            r = POST(url + '/jsonp_send', body=data,
                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            self.assertEqual(r.status, 500)
            self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/jsonp_send', body='d=%5B%22b%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"b\\"]");\r\n')

    # The server must accept messages sent with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22abc%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        r = POST(url + '/jsonp_send', body='["%61bc"]',
                 headers={'Content-Type': 'text/plain'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"abc\\",\\"%61bc\\"]");\r\n')

    def test_close(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("c[3000,\\"Go away!\\"]");\r\n')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("c[3000,\\"Go away!\\"]");\r\n')

# JSESSIONID cookie
# -----------------
#
# All transports except WebSockets need sticky session support from
# the load balancer. Some load balancers enable that only when they
# see `JSESSIONID` cookie. User of a sockjs server must be able to
# opt-in for this functionality - and set this cookie for all the
# session urls.
#
class JsessionidCookie(Test):
    # Verify if info has cookie_needed set.
    def test_basic(self):
        r = GET(cookie_base_url + '/info')
        self.assertEqual(r.status, 200)
        self.verify_no_cookie(r)

        data = json.loads(r.body)
        self.assertEqual(data['cookie_needed'], True)

    # Helper to check cookie validity.
    def verify_cookie(self, r):
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=dummy')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    # JSESSIONID cookie must be set by default
    def test_xhr(self):
        # polling url must set cookies
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.verify_cookie(r)

        # Cookie must be echoed back if it's already set.
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr', headers={'Cookie': 'JSESSIONID=abcdef'})
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=abcdef')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    def test_xhr_streaming(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_eventsource(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_htmlfile(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_jsonp(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)


# Raw WebSocket url: `/websocket`
# -------------------------------
#
# SockJS protocol defines a bit of higher level framing. This is okay
# when the browser using SockJS-client establishes the connection, but
# it's not really appropriate when the connection is being esablished
# from another program. Although SockJS focuses on server-browser
# communication, it should be straightforward to connect to SockJS
# from command line or some any programming language.
#
# In order to make writing command-line clients easier, we define this
# `/websocket` entry point. This entry point is special and doesn't
# use any additional custom framing, no open frame, no
# heartbeats. Only raw WebSocket protocol.
class RawWebsocket(Test):
    def test_transport(self):
        ws = WebSocket8Client(base_url + '/websocket')
        ws.send(u'Hello world!\uffff')
        self.assertEqual(ws.recv(), u'Hello world!\uffff')
        ws.close()

    def test_close(self):
        ws = WebSocket8Client(close_base_url + '/websocket')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()



# JSON Unicode Encoding
# =====================
#
# SockJS takes the responsibility of encoding Unicode strings for the
# user.  The idea is that SockJS should properly deliver any valid
# string from the browser to the server and back. This is actually
# quite hard, as browsers do some magical character
# translations. Additionally there are some valid characters from
# JavaScript point of view that are not valid Unicode, called
# surrogates (JavaScript uses UCS-2, which is not really Unicode).
#
# Dealing with unicode surrogates (0xD800-0xDFFF) is quite special. If
# possible we should make sure that server does escape decode
# them. This makes sense for SockJS servers that support UCS-2
# (SockJS-node), but can't really work for servers supporting unicode
# properly (Python).
#
# The browser must escape quite a list of chars, this is due to
# browser mangling outgoing chars on transports like XHR.
escapable_by_client = re.compile(u"[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u2000-\u20ff\ufeff\ufff0-\uffff\x00-\x1f\ufffe\uffff\u0300-\u0333\u033d-\u0346\u034a-\u034c\u0350-\u0352\u0357-\u0358\u035c-\u0362\u0374\u037e\u0387\u0591-\u05af\u05c4\u0610-\u0617\u0653-\u0654\u0657-\u065b\u065d-\u065e\u06df-\u06e2\u06eb-\u06ec\u0730\u0732-\u0733\u0735-\u0736\u073a\u073d\u073f-\u0741\u0743\u0745\u0747\u07eb-\u07f1\u0951\u0958-\u095f\u09dc-\u09dd\u09df\u0a33\u0a36\u0a59-\u0a5b\u0a5e\u0b5c-\u0b5d\u0e38-\u0e39\u0f43\u0f4d\u0f52\u0f57\u0f5c\u0f69\u0f72-\u0f76\u0f78\u0f80-\u0f83\u0f93\u0f9d\u0fa2\u0fa7\u0fac\u0fb9\u1939-\u193a\u1a17\u1b6b\u1cda-\u1cdb\u1dc0-\u1dcf\u1dfc\u1dfe\u1f71\u1f73\u1f75\u1f77\u1f79\u1f7b\u1f7d\u1fbb\u1fbe\u1fc9\u1fcb\u1fd3\u1fdb\u1fe3\u1feb\u1fee-\u1fef\u1ff9\u1ffb\u1ffd\u2000-\u2001\u20d0-\u20d1\u20d4-\u20d7\u20e7-\u20e9\u2126\u212a-\u212b\u2329-\u232a\u2adc\u302b-\u302c\uaab2-\uaab3\uf900-\ufa0d\ufa10\ufa12\ufa15-\ufa1e\ufa20\ufa22\ufa25-\ufa26\ufa2a-\ufa2d\ufa30-\ufa6d\ufa70-\ufad9\ufb1d\ufb1f\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufb4e]")
#
# The server is able to send much more chars verbatim. But, it can't
# send Unicode surrogates over Websockets, also various \u2xxxx chars
# get mangled. Additionally, if the server is capable of handling
# UCS-2 (ie: 16 bit character size), it should be able to deal with
# Unicode surrogates 0xD800-0xDFFF:
# http://en.wikipedia.org/wiki/Mapping_of_Unicode_characters#Surrogates
escapable_by_server = re.compile(u"[\x00-\x1f\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufff0-\uffff]")

client_killer_string_esc = '"' + ''.join([
        r'\u%04x' % (i) for i in range(65536)
            if escapable_by_client.match(unichr(i))]) + '"'
server_killer_string_esc = '"' + ''.join([
        r'\u%04x'% (i) for i in range(255, 65536)
            if escapable_by_server.match(unichr(i))]) + '"'

class JSONEncoding(Test):
    def test_xhr_server_encodes(self):
        # Make sure that server encodes at least all the characters
        # it's supposed to encode.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '["' + json.loads(server_killer_string_esc) + '"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we send previously, aka - escaped.
        self.assertEqual(recv, server_killer_string_esc)

    def test_xhr_server_decodes(self):
        # Make sure that server decodes the chars we're customly
        # encoding.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '[' + client_killer_string_esc + ']' # Sending escaped
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we send previously. We don't
        # really need to know what exactly got escaped and what not.
        a = json.loads(recv)
        b = json.loads(client_killer_string_esc)
        self.assertEqual(a, b)


# Handling close
# ==============
#
# Dealing with session closure is quite complicated part of the
# protocol. The exact details here don't matter that much to the
# client side, but it's good to have a common behaviour on the server
# side.
#
# This is less about defining the protocol and more about sanity
# checking implementations.
class HandlingClose(Test):
    # When server is closing session, it should unlink current
    # request. That means, if a new request appears, it should receive
    # an application close message rather than "Another connection
    # still open" message.
    def test_close_frame(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')
        self.assertEqual(r1.read(), 'c[3000,"Go away!"]\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[3000,"Go away!"]\n')

        # HTTP streaming requests should be automatically closed after
        # close.
        self.assertFalse(r1.read())
        self.assertFalse(r2.read())

    def test_close_request(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')

        # HTTP streaming requests should be automatically closed after
        # getting the close frame.
        self.assertFalse(r2.read())

    # When a polling request is closed by a network error - not by
    # server, the session should be automatically closed. When there
    # is a network error - we're in an undefined state. Some messages
    # may have been lost, there is not much we can do about it.
    def test_abort_xhr_streaming(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')
        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        # Can't do second polling request now.
        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')
        self.assertFalse(r2.read())

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST_async(url + '/xhr_streaming')
        r3.read() # prelude
        self.assertTrue(r3.read() in ['o\n', 'c[1002,"Connection interrupted"]\n'])
        r3.close()

    # The same for polling transports
    def test_abort_xhr_polling(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST(url + '/xhr')
        self.assertEqual(r1.body, 'o\n')

        r1 = old_POST_async(url + '/xhr', load=False)

        # Can't do second polling request now.
        r2 = POST(url + '/xhr')
        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST(url + '/xhr')
        self.assertTrue(r3.body in ['o\n', 'c[1002,"Connection interrupted"]\n'])

# Http 1.0 and 1.1 chunking
# =========================
#
# There seem to be a lot of confusion about http/1.0 and http/1.1
# content-length and transfer-encoding:chunking headers. Although
# following tests don't really test anything sockjs specific, it's
# good to make sure that the server is behaving about this.
#
# It is not the intention of this test to verify all possible urls -
# merely to check the sanity of http server implementation.  It is
# assumed that the implementator is able to apply presented behaviour
# to other urls served by the sockjs server.
class Http10(Test):
    # We're going to test a greeting url. No dynamic content, just the
    # simplest possible response.
    def test_synchronous(self):
        c = RawHttpConnection(base_url)
        # In theory 'connection:Keep-Alive' isn't a valid http/1.0
        # header, but in this header may in practice be issued by a
        # http/1.0 client:
        # http://www.freesoft.org/CIE/RFC/2068/248.htm
        r = c.request('GET', base_url, http='1.0',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # In practice the exact http version on the response doesn't
        # really matter. Many serves always respond 1.1.
        self.assertTrue(r.http in ['1.0', '1.1'])
        # Transfer-encoding is not allowed in http/1.0.
        self.assertFalse(r.headers.get('transfer-encoding'))

        # There are two ways to give valid response. Use
        # Content-Length (and maybe connection:Keep-Alive) or
        # Connection: close.
        if not r.headers.get('content-length'):
            self.assertEqual(r.headers['connection'].lower(), 'close')
            self.assertEqual(c.read(), 'Welcome to SockJS!\n')
            self.assertTrue(c.closed())
        else:
            self.assertEqual(int(r.headers['content-length']), 19)
            self.assertEqual(c.read(19), 'Welcome to SockJS!\n')
            connection = r.headers.get('connection', '').lower()
            if connection in ['close', '']:
                # Connection-close behaviour is default in http 1.0
                self.assertTrue(c.closed())
            else:
                self.assertEqual(connection, 'keep-alive')
                # We should be able to issue another request on the same connection
                r = c.request('GET', base_url, http='1.0',
                              headers={'Connection':'Keep-Alive'})
                self.assertEqual(r.status, 200)

    def test_streaming(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        c = RawHttpConnection(url)
        # In theory 'connection:Keep-Alive' isn't a valid http/1.0
        # header, but in this header may in practice be issued by a
        # http/1.0 client:
        # http://www.freesoft.org/CIE/RFC/2068/248.htm
        r = c.request('POST', url + '/xhr_streaming', http='1.0',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # Transfer-encoding is not allowed in http/1.0.
        self.assertFalse(r.headers.get('transfer-encoding'))
        # Content-length is not allowed - we don't know it yet.
        self.assertFalse(r.headers.get('content-length'))

        # `Connection` should be not set or be `close`. On the other
        # hand, if it is set to `Keep-Alive`, it won't really hurt, as
        # we are confident that neither `Content-Length` nor
        # `Transfer-Encoding` are set.

        # This is a the same logic as HandlingClose.test_close_frame
        self.assertEqual(c.read(2048+1)[0], 'h') # prelude
        self.assertEqual(c.read(2), 'o\n')
        self.assertEqual(c.read(19), 'c[3000,"Go away!"]\n')
        self.assertTrue(c.closed())


class Http11(Test):
    def test_synchronous(self):
        c = RawHttpConnection(base_url)
        r = c.request('GET', base_url, http='1.1',
                      headers={'Connection':'Keep-Alive'})
        # Keepalive is default in http 1.1
        self.assertTrue(r.http, '1.1')
        self.assertTrue(r.headers.get('connection', '').lower() in ['keep-alive', ''],
                         "Your server doesn't support connection:Keep-Alive")
        # Server should use 'Content-Length' or 'Transfer-Encoding'
        if r.headers.get('content-length'):
            self.assertEqual(int(r.headers['content-length']), 19)
            self.assertEqual(c.read(19), 'Welcome to SockJS!\n')
            self.assertFalse(r.headers.get('transfer-encoding'))
        else:
            self.assertEqual(r.headers['transfer-encoding'].lower(), 'chunked')
            self.assertEqual(c.read_chunk(), 'Welcome to SockJS!\n')
            self.assertEqual(c.read_chunk(), '')
        # We should be able to issue another request on the same connection
        r = c.request('GET', base_url, http='1.1',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)

    def test_streaming(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        c = RawHttpConnection(url)
        r = c.request('POST', url + '/xhr_streaming', http='1.1',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # Transfer-encoding is required in http/1.1.
        self.assertTrue(r.headers['transfer-encoding'].lower(), 'chunked')
        # Content-length is not allowed.
        self.assertFalse(r.headers.get('content-length'))
        # Connection header can be anything, so don't bother verifying it.

        # This is a the same logic as HandlingClose.test_close_frame
        self.assertEqual(c.read_chunk()[0], 'h') # prelude
        self.assertEqual(c.read_chunk(), 'o\n')
        self.assertEqual(c.read_chunk(), 'c[3000,"Go away!"]\n')
        self.assertEqual(c.read_chunk(), '')


# Footnote
# ========

# Make this script runnable.
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = sockjs-protocol-dev
#!/usr/bin/env python
"""
[**SockJS-protocol**](https://github.com/sockjs/sockjs-protocol) is an
effort to define a protocol between in-browser
[SockJS-client](https://github.com/sockjs/sockjs-client) and its
server-side counterparts, like
[SockJS-node](https://github.com/sockjs/sockjs-node). This should
help others to write alternative server implementations.


This protocol definition is also a runnable test suite, do run it
against your server implementation. Supporting all the tests doesn't
guarantee that SockJS client will work flawlessly, end-to-end tests
using real browsers are always required.
"""
import os
import random
import time
import json
import re
import unittest2 as unittest
from utils_03 import GET, GET_async, POST, POST_async, OPTIONS, old_POST_async
from utils_03 import WebSocket8Client
from utils_03 import RawHttpConnection
import uuid


# Base URL
# ========

"""
The SockJS server provides one or more SockJS services. The services
are usually exposed with a simple url prefix, like:
`http://localhost:8000/echo` or
`http://localhost:8000/broadcast`. We'll call this kind of url a
`base_url`. There is nothing wrong with base url being more complex,
like `http://localhost:8000/a/b/c/d/echo`. Base url should
never end with a slash.

Base url is the url that needs to be supplied to the SockJS client.

All paths under base url are controlled by SockJS server and are
defined by SockJS protocol.

SockJS protocol can be using either http or https.

To run this tests server pointed by `base_url` needs to support
following services:

 - `echo` - responds with identical data as received
 - `disabled_websocket_echo` - identical to `echo`, but with websockets disabled
 - `cookie_needed_echo` - identical to `echo`, but with JSESSIONID cookies sent
 - `close` - server immediately closes the session

This tests should not be run more often than once in five seconds -
many tests operate on the same (named) sessions and they need to have
enough time to timeout.
"""
test_top_url = os.environ.get('SOCKJS_URL', 'http://localhost:8081')
base_url = test_top_url + '/echo'
close_base_url = test_top_url + '/close'
wsoff_base_url = test_top_url + '/disabled_websocket_echo'
cookie_base_url = test_top_url + '/cookie_needed_echo'


# Static URLs
# ===========

class Test(unittest.TestCase):
    # We are going to test several `404/not found` pages. We don't
    # define a body or a content type.
    def verify404(self, r):
        self.assertEqual(r.status, 404)

    # In some cases `405/method not allowed` is more appropriate.
    def verify405(self, r):
        self.assertEqual(r.status, 405)
        self.assertFalse(r['content-type'])
        self.assertTrue(r['allow'])
        self.assertFalse(r.body)

    # Compare the 'content-type' header ignoring spaces
    def verify_content_type(self, r, content_type):
        self.assertEqual(r['content-type'].replace(' ', ''), content_type)

    # Multiple transport protocols need to support OPTIONS method. All
    # responses to OPTIONS requests must be cacheable and contain
    # appropriate headers.
    def verify_options(self, url, allowed_methods):
        for origin in [None, 'test', 'null']:
            h = {}
            if origin:
                h['Origin'] = origin
            r = OPTIONS(url, headers=h)
            self.assertEqual(r.status, 204)
            self.assertTrue(re.search('public', r['Cache-Control']))
            self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                            "max-age must be large, one year (31536000) is best")
            self.assertTrue(r['Expires'])
            self.assertTrue(int(r['access-control-max-age']) > 1000000)
            self.assertEqual(r['Access-Control-Allow-Methods'], allowed_methods)
            self.assertFalse(r.body)
            self.verify_cors(r, origin)

    def verify_no_cookie(self, r):
        self.assertFalse(r['Set-Cookie'])

    # Most of the XHR/Ajax based transports do work CORS if proper
    # headers are set.
    def verify_cors(self, r, origin=None):
        if origin and origin != 'null':
            self.assertEqual(r['access-control-allow-origin'], origin)
        else:
            self.assertEqual(r['access-control-allow-origin'], '*')
        # In order to get cookies (`JSESSIONID` mostly) flying, we
        # need to set `allow-credentials` header to true.
        self.assertEqual(r['access-control-allow-credentials'], 'true')

    # Sometimes, due to transports limitations we need to request
    # private data using GET method. In such case it's very important
    # to disallow any caching.
    def verify_not_cached(self, r, origin=None):
        self.assertEqual(r['Cache-Control'],
                         'no-store, no-cache, must-revalidate, max-age=0')
        self.assertFalse(r['Expires'])
        self.assertFalse(r['Last-Modified'])


# Greeting url: `/`
# ----------------
class BaseUrlGreeting(Test):
    # The most important part of the url scheme, is without doubt, the
    # top url. Make sure the greeting is valid.
    def test_greeting(self):
        for url in [base_url, base_url + '/']:
            r = GET(url)
            self.assertEqual(r.status, 200)
            self.verify_content_type(r, 'text/plain;charset=UTF-8')
            self.assertEqual(r.body, 'Welcome to SockJS!\n')
            self.verify_no_cookie(r)

    # Other simple requests should return 404.
    def test_notFound(self):
        for suffix in ['/a', '/a.html', '//', '///', '/a/a', '/a/a/', '/a',
                       '/a/']:
            self.verify404(GET(base_url + suffix))


# IFrame page: `/iframe*.html`
# ----------------------------
class IframePage(Test):
    """
    Some transports don't support cross domain communication
    (CORS). In order to support them we need to do a cross-domain
    trick: on remote (server) domain we serve an simple html page,
    that loads back SockJS client javascript and is able to
    communicate with the server within the same domain.
    """
    iframe_body = re.compile('''
^<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function\(\){SockJS.bootstrap_iframe\(\);};
  </script>
  <script src="(?P<sockjs_url>[^"]*)"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>$
'''.strip())

    # SockJS server must provide this html page.
    def test_simpleUrl(self):
        self.verify(base_url + '/iframe.html')

    # To properly utilize caching, the same content must be served
    # for request which try to version the iframe. The server may want
    # to give slightly different answer for every SockJS client
    # revision.
    def test_versionedUrl(self):
        for suffix in ['/iframe-a.html', '/iframe-.html', '/iframe-0.1.2.html',
                       '/iframe-0.1.2abc-dirty.2144.html']:
            self.verify(base_url + suffix)

    # In some circumstances (`devel` set to true) client library
    # wants to skip caching altogether. That is achieved by
    # supplying a random query string.
    def test_queriedUrl(self):
        for suffix in ['/iframe-a.html?t=1234', '/iframe-0.1.2.html?t=123414',
                       '/iframe-0.1.2abc-dirty.2144.html?t=qweqweq123']:
            self.verify(base_url + suffix)

    # Malformed urls must give 404 answer.
    def test_invalidUrl(self):
        for suffix in ['/iframe.htm', '/iframe', '/IFRAME.HTML', '/IFRAME',
                       '/iframe.HTML', '/iframe.xml', '/iframe-/.html']:
            r = GET(base_url + suffix)
            self.verify404(r)

    # The '/iframe.html' page and its variants must give `200/ok` and be
    # served with 'text/html' content type.
    def verify(self, url):
        r = GET(url)
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'text/html;charset=UTF-8')
        # The iframe page must be strongly cacheable, supply
        # Cache-Control, Expires and Etag headers and avoid
        # Last-Modified header.
        self.assertTrue(re.search('public', r['Cache-Control']))
        self.assertTrue(re.search('max-age=[1-9][0-9]{6}', r['Cache-Control']),
                        "max-age must be large, one year (31536000) is best")
        self.assertTrue(r['Expires'])
        self.assertTrue(r['ETag'])
        self.assertFalse(r['last-modified'])

        # Body must be exactly as specified, with the exception of
        # `sockjs_url`, which should be configurable.
        match = self.iframe_body.match(r.body.strip())
        self.assertTrue(match)
        # `Sockjs_url` must be a valid url and should utilize caching.
        sockjs_url = match.group('sockjs_url')
        self.assertTrue(sockjs_url.startswith('/') or
                        sockjs_url.startswith('http'))
        self.verify_no_cookie(r)
        return r


    # The iframe page must be strongly cacheable. ETag headers must
    # not change too often. Server must support 'if-none-match'
    # requests.
    def test_cacheability(self):
        r1 = GET(base_url + '/iframe.html')
        r2 = GET(base_url + '/iframe.html')
        self.assertEqual(r1['etag'], r2['etag'])
        self.assertTrue(r1['etag']) # Let's make sure ETag isn't None.

        r = GET(base_url + '/iframe.html', headers={'If-None-Match': r1['etag']})
        self.assertEqual(r.status, 304)
        self.assertFalse(r['content-type'])
        self.assertFalse(r.body)

# Info test: `/info`
# ------------------
#
# Warning: this is a replacement of `/chunking_test` functionality
# from SockJS 0.1.
class InfoTest(Test):
    # This url is called before the client starts the session. It's
    # used to check server capabilities (websocket support, cookies
    # requiremet) and to get the value of "origin" setting (currently
    # not used).
    #
    # But more importantly, the call to this url is used to measure
    # the roundtrip time between the client and the server. So, please,
    # do respond to this url in a timely fashion.
    def test_basic(self):
        r = GET(base_url + '/info')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'application/json;charset=UTF-8')
        self.verify_no_cookie(r)
        self.verify_not_cached(r)
        self.verify_cors(r)

        data = json.loads(r.body)
        # Are websockets enabled on the server?
        self.assertEqual(data['websocket'], True)
        # Do transports need to support cookies (ie: for load
        # balancing purposes.
        self.assertTrue(data['cookie_needed'] in  [True, False])
        # List of allowed origins. Currently ignored.
        self.assertEqual(data['origins'], ['*:*'])
        # Source of entropy for random number generator.
        self.assertTrue(type(data['entropy']) in [int, long])

    # As browsers don't have a good entropy source, the server must
    # help with tht. Info url must supply a good, unpredictable random
    # number from the range <0; 2^32-1> to feed the browser.
    def test_entropy(self):
        r1 = GET(base_url + '/info')
        data1 = json.loads(r1.body)
        r2 = GET(base_url + '/info')
        data2 = json.loads(r2.body)
        self.assertTrue(type(data1['entropy']) in [int, long])
        self.assertTrue(type(data2['entropy']) in [int, long])
        self.assertNotEqual(data1['entropy'], data2['entropy'])

    # Info url must support CORS.
    def test_options(self):
        self.verify_options(base_url + '/info', 'OPTIONS, GET')

    # SockJS client may be hosted from file:// url. In practice that
    # means the 'Origin' headers sent by the browser will have a value
    # of a string "null". Unfortunately, just echoing back "null"
    # won't work - browser will understand that as a rejection. We
    # must respond with star "*" origin in such case.
    def test_options_null_origin(self):
            url = base_url + '/info'
            r = OPTIONS(url, headers={'Origin': 'null'})
            self.assertEqual(r.status, 204)
            self.assertFalse(r.body)
            self.assertEqual(r['access-control-allow-origin'], '*')

    # The 'disabled_websocket_echo' service should have websockets
    # disabled.
    def test_disabled_websocket(self):
        r = GET(wsoff_base_url + '/info')
        self.assertEqual(r.status, 200)
        data = json.loads(r.body)
        self.assertEqual(data['websocket'], False)


# Session URLs
# ============

# Top session URL: `/<server>/<session>`
# --------------------------------------
#
# The session between the client and the server is always initialized
# by the client. The client chooses `server_id`, which should be a
# three digit number: 000 to 999. It can be supplied by user or
# randomly generated. The main reason for this parameter is to make it
# easier to configure load balancer - and enable sticky sessions based
# on first part of the url.
#
# Second parameter `session_id` must be a random string, unique for
# every session.
#
# It is undefined what happens when two clients share the same
# `session_id`. It is a client responsibility to choose identifier
# with enough entropy.
#
# Neither server nor client API's can expose `session_id` to the
# application. This field must be protected from the app.
class SessionURLs(Test):

    # The server must accept any value in `server` and `session` fields.
    def test_anyValue(self):
        # add some randomness, so that test could be rerun immediately.
        r = '%s' % random.randint(0, 1024)
        self.verify('/a/a' + r)
        for session_part in ['/_/_' + r, '/1/' + r, '/abcdefgh_i-j%20/abcdefg_i-j%20'+ r]:
            self.verify(session_part)

    # To test session URLs we're going to use `xhr-polling` transport
    # facilitites.
    def verify(self, session_part):
        r = POST(base_url + session_part + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

    # But not an empty string, anything containing dots or paths with
    # less or more parts.
    def test_invalidPaths(self):
        for suffix in ['//', '/a./a', '/a/a.', '/./.' ,'/', '///']:
            self.verify404(GET(base_url + suffix + '/xhr'))
            self.verify404(POST(base_url + suffix + '/xhr'))

    # A session is identified by only `session_id`. `server_id` is a
    # parameter for load balancer and must be ignored by the server.
    def test_ignoringServerId(self):
        ''' See Protocol.test_simpleSession for explanation. '''
        session_id = str(uuid.uuid4())
        r = POST(base_url + '/000/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        payload = '["a"]'
        r = POST(base_url + '/000/' + session_id + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        r = POST(base_url + '/999/' + session_id + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

# Protocol and framing
# --------------------
#
# SockJS tries to stay API-compatible with WebSockets, but not on the
# network layer. For technical reasons SockJS must introduce custom
# framing and simple custom protocol.
#
# ### Framing accepted by the client
#
# SockJS client accepts following frames:
#
# * `o` - Open frame. Every time a new session is established, the
#   server must immediately send the open frame. This is required, as
#   some protocols (mostly polling) can't distinguish between a
#   properly established connection and a broken one - we must
#   convince the client that it is indeed a valid url and it can be
#   expecting further messages in the future on that url.
#
# * `h` - Heartbeat frame. Most loadbalancers have arbitrary timeouts
#   on connections. In order to keep connections from breaking, the
#   server must send a heartbeat frame every now and then. The typical
#   delay is 25 seconds and should be configurable.
#
# * `a` - Array of json-encoded messages. For example: `a["message"]`.
#
# * `c` - Close frame. This frame is sent to the browser every time
#   the client asks for data on closed connection. This may happen
#   multiple times. Close frame contains a code and a string explaining
#   a reason of closure, like: `c[3000,"Go away!"]`.
#
# ### Framing accepted by the server
#
# SockJS server does not have any framing defined. All incoming data
# is treated as incoming messages, either single json-encoded messages
# or an array of json-encoded messages, depending on transport.
#
# ### Tests
#
# To explain the protocol we'll use `xhr-polling` transport
# facilities.
class Protocol(Test):
    # When server receives a request with unknown `session_id` it must
    # recognize that as request for a new session. When server opens a
    # new sesion it must immediately send an frame containing a letter
    # `o`.
    def test_simpleSession(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        "New line is a frame delimiter specific for xhr-polling"
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        # After a session was established the server needs to accept
        # requests for sending messages.
        "Xhr-polling accepts messages as a list of JSON-encoded strings."
        payload = '["a"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)

        '''We're using an echo service - we'll receive our message
        back. The message is encoded as an array 'a'.'''
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["a"]\n')

        # Sending messages to not existing sessions is invalid.
        payload = '["a"]'
        r = POST(base_url + '/000/bad_session/xhr_send', body=payload)
        self.verify404(r)

        # The session must time out after 5 seconds of not having a
        # receiving connection. The server must send a heartbeat frame
        # every 25 seconds. The heartbeat frame contains a single `h`
        # character. This delay may be configurable.
        pass
        # The server must not allow two receiving connections to wait
        # on a single session. In such case the server must send a
        # close frame to the new connection.
        r1 = old_POST_async(trans_url + '/xhr', load=False)
        time.sleep(0.25)
        r2 = POST(trans_url + '/xhr')

        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')
        self.assertEqual(r2.status, 200)

        r1.close()

    # The server may terminate the connection, passing error code and
    # message.
    def test_closeSession(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')

        # Until the timeout occurs, the server must constantly serve
        # the close message.

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'c[3000,"Go away!"]\n')


# WebSocket protocols: `/*/*/websocket`
# -------------------------------------
import websocket

# The most important feature of SockJS is to support native WebSocket
# protocol. A decent SockJS server should support at least the
# following variants:
#
#   - hixie-75 (Chrome 4, Safari 5.0.0)
#   - hixie-76/hybi-00 (Chrome 6, Safari 5.0.1)
#   - hybi-07 (Firefox 6)
#   - hybi-10 (Firefox 7, Chrome 14)
#
class WebsocketHttpErrors(Test):
    # Normal requests to websocket should not succeed.
    def test_httpMethod(self):
        r = GET(base_url + '/0/0/websocket')
        self.assertEqual(r.status, 400)
        self.assertTrue('Can "Upgrade" only to "WebSocket".' in r.body)

    # Some proxies and load balancers can rewrite 'Connection' header,
    # in such case we must refuse connection.
    def test_invalidConnectionHeader(self):
        r = GET(base_url + '/0/0/websocket', headers={'Upgrade': 'WebSocket',
                                                      'Connection': 'close'})
        self.assertEqual(r.status, 400)
        self.assertTrue('"Connection" must be "Upgrade".', r.body)

    # WebSocket should only accept GET
    def test_invalidMethod(self):
        for h in [{'Upgrade': 'WebSocket', 'Connection': 'Upgrade'},
                  {}]:
            r = POST(base_url + '/0/0/websocket', headers=h)
            self.verify405(r)


# Support WebSocket Hixie-76 protocol
class WebsocketHixie76(Test):
    def test_transport(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    def test_close(self):
        ws_url = 'ws:' + close_base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')

        # The connection should be closed after the close frame.
        with self.assertRaises(websocket.ConnectionClosedException):
            if ws.recv() is None:
                raise websocket.ConnectionClosedException
        ws.close()

    # Empty frames must be ignored by the server side.
    def test_empty_frame(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        # Server must ignore empty messages.
        ws.send(u'')
        # Server must also ignore frames with no messages.
        ws.send(u'[]')

        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), u'a["a"]')
        ws.close()

    # For WebSockets, as opposed to other transports, it is valid to
    # reuse `session_id`. The lifetime of SockJS WebSocket session is
    # defined by a lifetime of underlying WebSocket connection. It is
    # correct to have two separate sessions sharing the same
    # `session_id` at the same time.
    def test_reuseSessionId(self):
        on_close = lambda(ws): self.assertFalse(True)

        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws1 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws1.recv(), u'o')

        ws2 = websocket.create_connection(ws_url, on_close=on_close)
        self.assertEqual(ws2.recv(), u'o')

        ws1.send(u'["a"]')
        self.assertEqual(ws1.recv(), u'a["a"]')

        ws2.send(u'["b"]')
        self.assertEqual(ws2.recv(), u'a["b"]')

        ws1.close()
        ws2.close()

        # It is correct to reuse the same `session_id` after closing a
        # previous connection.
        ws1 = websocket.create_connection(ws_url)
        self.assertEqual(ws1.recv(), u'o')
        ws1.send(u'["a"]')
        self.assertEqual(ws1.recv(), u'a["a"]')
        ws1.close()

    # Verify WebSocket headers sanity. Due to HAProxy design the
    # websocket server must support writing response headers *before*
    # receiving -76 nonce. In other words, the websocket code must
    # work like that:
    #
    # * Receive request headers.
    # * Write response headers.
    # * Receive request nonce.
    # * Write response nonce.
    def test_haproxy(self):
        url = base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])

        c = RawHttpConnection(http_url)
        r = c.request('GET', http_url, http='1.1', headers={
                'Connection':'Upgrade',
                'Upgrade':'WebSocket',
                'Origin': origin,
                'Sec-WebSocket-Key1': '4 @1  46546xW%0l 1 5',
                'Sec-WebSocket-Key2': '12998 5 Y3 1  .P00'
                })
        # First check response headers
        self.assertEqual(r.status, 101)
        self.assertEqual(r.headers['connection'].lower(), 'upgrade')
        self.assertEqual(r.headers['upgrade'].lower(), 'websocket')
        self.assertEqual(r.headers['sec-websocket-location'], ws_url)
        self.assertEqual(r.headers['sec-websocket-origin'], origin)
        self.assertFalse('Content-Length' in r.headers)
        # Later send token
        c.send('aaaaaaaa')
        self.assertEqual(c.read()[:16],
                         '\xca4\x00\xd8\xa5\x08G\x97,\xd5qZ\xba\xbfC{')

    # When user sends broken data - broken JSON for example, the
    # server must abruptly terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = websocket.create_connection(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a')
        with self.assertRaises(websocket.ConnectionClosedException):
            if ws.recv() is None:
                raise websocket.ConnectionClosedException
        ws.close()


# The server must support Hybi-10 protocol
class WebsocketHybi10(Test):
    def test_transport(self):
        trans_url = base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)

        self.assertEqual(ws.recv(), 'o')
        # Server must ignore empty messages.
        ws.send(u'')
        ws.send(u'["a"]')
        self.assertEqual(ws.recv(), 'a["a"]')
        ws.close()

    def test_close(self):
        trans_url = close_base_url + '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(trans_url)
        self.assertEqual(ws.recv(), u'o')
        self.assertEqual(ws.recv(), u'c[3000,"Go away!"]')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # Verify WebSocket headers sanity. Server must support both
    # Hybi-07 and Hybi-10.
    def test_headersSanity(self):
        for version in ['7', '8', '13']:
            url = base_url.split(':',1)[1] + \
                '/000/' + str(uuid.uuid4()) + '/websocket'
            ws_url = 'ws:' + url
            http_url = 'http:' + url
            origin = '/'.join(http_url.split('/')[:3])
            h = {'Upgrade': 'websocket',
                 'Connection': 'Upgrade',
                 'Sec-WebSocket-Version': version,
                 'Sec-WebSocket-Origin': 'http://asd',
                 'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
                 }

            r = GET_async(http_url, headers=h)
            self.assertEqual(r.status, 101)
            self.assertEqual(r['sec-websocket-accept'], 'HSmrc0sMlYUkAGmm5OPpG2HaGWk=')
            self.assertEqual(r['connection'].lower(), 'upgrade')
            self.assertEqual(r['upgrade'].lower(), 'websocket')
            self.assertFalse(r['content-length'])
            r.close()

    # When user sends broken data - broken JSON for example, the
    # server must abruptly terminate the ws connection.
    def test_broken_json(self):
        ws_url = 'ws:' + base_url.split(':',1)[1] + \
                 '/000/' + str(uuid.uuid4()) + '/websocket'
        ws = WebSocket8Client(ws_url)
        self.assertEqual(ws.recv(), u'o')
        ws.send(u'["a')
        with self.assertRaises(ws.ConnectionClosedException):
            ws.recv()
        ws.close()

    # As a fun part, Firefox 6.0.2 supports Websockets protocol '7'. But,
    # it doesn't send a normal 'Connection: Upgrade' header. Instead it
    # sends: 'Connection: keep-alive, Upgrade'. Brilliant.
    def test_firefox_602_connection_header(self):
        url = base_url.split(':',1)[1] + \
            '/000/' + str(uuid.uuid4()) + '/websocket'
        ws_url = 'ws:' + url
        http_url = 'http:' + url
        origin = '/'.join(http_url.split('/')[:3])
        h = {'Upgrade': 'websocket',
             'Connection': 'keep-alive, Upgrade',
             'Sec-WebSocket-Version': '7',
             'Sec-WebSocket-Origin': 'http://asd',
             'Sec-WebSocket-Key': 'x3JJHMbDL1EzLkh9GBhXDw==',
             }
        r = GET_async(http_url, headers=h)
        self.assertEqual(r.status, 101)


# XhrPolling: `/*/*/xhr`, `/*/*/xhr_send`
# ---------------------------------------
#
# The server must support xhr-polling.
class XhrPolling(Test):
    # The transport must support CORS requests, and answer correctly
    # to OPTIONS requests.
    def test_options(self):
        for suffix in ['/xhr', '/xhr_send']:
            self.verify_options(base_url + '/abc/abc' + suffix,
                                'OPTIONS, POST')

    # Test the transport itself.
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.verify_content_type(r, 'application/javascript;charset=UTF-8')
        self.verify_cors(r)
        # iOS 6 caches POSTs. Make sure we send no-cache header.
        self.verify_not_cached(r)

        # Xhr transports receive json-encoded array of messages.
        r = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r.status, 204)
        self.assertFalse(r.body)
        # The content type of `xhr_send` must be set to `text/plain`,
        # even though the response code is `204`. This is due to
        # Firefox/Firebug behaviour - it assumes that the content type
        # is xml and shouts about it.
        self.verify_content_type(r, 'text/plain;charset=UTF-8')
        self.verify_cors(r)
        # iOS 6 caches POSTs. Make sure we send no-cache header.
        self.verify_not_cached(r)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a["x"]\n')

    # Publishing messages to a non-existing session must result in
    # a 404 error.
    def test_invalid_session(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr_send', body='["x"]')
        self.verify404(r)

    # The server must behave when invalid json data is sent or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        r = POST(url + '/xhr_send', body='["x')
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        r = POST(url + '/xhr_send', body='')
        self.assertEqual(r.status, 500)
        self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/xhr_send', body='["a"]')
        self.assertFalse(r.body)
        self.assertEqual(r.status, 204)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)

    # The server must accept messages sent with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'o\n')

        ctypes = ['text/plain', 'T', 'application/json', 'application/xml', '',
                  'application/json; charset=utf-8', 'text/xml; charset=utf-8',
                  'text/xml']
        for ct in ctypes:
            r = POST(url + '/xhr_send', body='["a"]', headers={'Content-Type': ct})
            self.assertEqual(r.status, 204)
            self.assertFalse(r.body)

        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'a[' + (',').join(['"a"']*len(ctypes)) +']\n')

    # When client sends a CORS request with
    # 'Access-Control-Request-Headers' header set, the server must
    # echo back this header as 'Access-Control-Allow-Headers'. This is
    # required in order to get CORS working. Browser will be unhappy
    # otherwise.
    def test_request_headers_cors(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr',
                 headers={'Access-Control-Request-Headers': 'a, b, c'})
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertEqual(r['Access-Control-Allow-Headers'], 'a, b, c')

        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr',
                 headers={'Access-Control-Request-Headers': ''})
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertFalse(r['Access-Control-Allow-Headers'])

        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.verify_cors(r)
        self.assertFalse(r['Access-Control-Allow-Headers'])

    # The client must be able to send frames containint no messages to
    # the server.  This is used as a heartbeat mechanism - client may
    # voluntairly send frames with no messages once in a while.
    def test_sending_empty_frame(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')

        # Sending empty frames with no data must allowed.
        r = POST(url + '/xhr_send', body='[]')
        self.assertEqual(r.status, 204)

        r = POST(url + '/xhr_send', body='["a"]')
        self.assertEqual(r.status, 204)

        r = POST(url + '/xhr')
        self.assertEqual(r.body, 'a["a"]\n')
        self.assertEqual(r.status, 200)


# XhrStreaming: `/*/*/xhr_streaming`
# ----------------------------------
class XhrStreaming(Test):
    def test_options(self):
        self.verify_options(base_url + '/abc/abc/xhr_streaming',
                            'OPTIONS, POST')

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'application/javascript;charset=UTF-8')
        self.verify_cors(r)
        # iOS 6 caches POSTs. Make sure we send no-cache header.
        self.verify_not_cached(r)

        # The transport must first send 2KiB of `h` bytes as prelude.
        self.assertEqual(r.read(), 'h' *  2048 + '\n')

        self.assertEqual(r.read(), 'o\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertEqual(r1.status, 204)
        self.assertFalse(r1.body)

        self.assertEqual(r.read(), 'a["x"]\n')
        r.close()

    def test_response_limit(self):
        # Single streaming request will buffer all data until
        # closed. In order to remove (garbage collect) old messages
        # from the browser memory we should close the connection every
        # now and then. By default we should close a streaming request
        # every 128KiB messages was send. The test server should have
        # this limit decreased to 4096B.
        url = base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'o\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 128) + '"'
        for i in range(31):
            r1 = POST(url + '/xhr_send', body='[' + msg + ']')
            self.assertEqual(r1.status, 204)
            self.assertEqual(r.read(), 'a[' + msg + ']\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# EventSource: `/*/*/eventsource`
# -------------------------------
#
# For details of this protocol framing read the spec:
#
# * [http://dev.w3.org/html5/eventsource/](http://dev.w3.org/html5/eventsource/)
#
# Beware leading spaces.
class EventSource(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'text/event-stream;charset=UTF-8')
        # As EventSource is requested using GET we must be very
        # careful not to allow it being cached.
        self.verify_not_cached(r)

        # The transport must first send a new line prelude, due to a
        # bug in Opera.
        self.assertEqual(r.read(), '\r\n')

        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(), 'data: a["x"]\r\n\r\n')

        # This protocol doesn't allow binary data and we need to
        # specially treat leading space, new lines and things like
        # \x00. But, now the protocol json-encodes everything, so
        # there is no way to trigger this case.
        r1 = POST(url + '/xhr_send', body=r'["  \u0000\n\r "]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         'data: a["  \\u0000\\n\\r "]\r\n\r\n')

        r.close()

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        # Although EventSource transport is better, and in theory may
        # not need this mechanism, there are some bugs in the browsers
        # that actually prevent the automatic GC. See:
        #  * https://bugs.webkit.org/show_bug.cgi?id=61863
        #  * http://code.google.com/p/chromium/issues/detail?id=68160
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(), 'data: o\r\n\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = '"' + ('x' * 4096) + '"'
        r1 = POST(url + '/xhr_send', body='[' + msg + ']')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(), 'data: a[' + msg + ']\r\n\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())


# HtmlFile: `/*/*/htmlfile`
# -------------------------
#
# Htmlfile transport is based on research done by Michael Carter. It
# requires a famous `document.domain` trick. Read on:
#
# * [http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do](http://stackoverflow.com/questions/1481251/what-does-document-domain-document-domain-do)
# * [http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/](http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/)
#
class HtmlFile(Test):
    head = r'''
<!doctype html>
<html><head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head><body><h2>Don't panic!</h2>
  <script>
    document.domain = document.domain;
    var c = parent.%s;
    c.start();
    function p(d) {c.message(d);};
    window.onload = function() {c.stop();};
  </script>
'''.strip()

    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'text/html;charset=UTF-8')
        # As HtmlFile is requested using GET we must be very careful
        # not to allow it being cached.
        self.verify_not_cached(r)

        d = r.read()
        self.assertEqual(d.strip(), self.head % ('callback',))
        self.assertGreater(len(d), 1024)
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        r1 = POST(url + '/xhr_send', body='["x"]')
        self.assertFalse(r1.body)
        self.assertEqual(r1.status, 204)

        self.assertEqual(r.read(),
                         '<script>\np("a[\\"x\\"]");\n</script>\r\n')
        r.close()

    def test_no_callback(self):
        r = GET(base_url + '/a/a/htmlfile')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    # Supplying invalid characters to callback parameter is invalid
    # and must result in a 500 errors. Invalid characters are any
    # matching the following regexp: `[^a-zA-Z0-9-_.]`
    def test_invalid_callback(self):
        for callback in ['%20', '*', 'abc(', 'abc%28']:
            r = GET(base_url + '/a/a/htmlfile?c=' + callback)
            self.assertEqual(r.status, 500)
            self.assertTrue('invalid "callback" parameter' in r.body)

    def test_response_limit(self):
        # Single streaming request should be closed after enough data
        # was delivered (by default 128KiB, but 4KiB for test server).
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=callback')
        self.assertEqual(r.status, 200)
        self.assertTrue(r.read()) # prelude
        self.assertEqual(r.read(),
                         '<script>\np("o");\n</script>\r\n')

        # Test server should gc streaming session after 4096 bytes
        # were sent (including framing).
        msg = ('x' * 4096)
        r1 = POST(url + '/xhr_send', body='["' + msg + '"]')
        self.assertEqual(r1.status, 204)
        self.assertEqual(r.read(),
                         '<script>\np("a[\\"' + msg + '\\"]");\n</script>\r\n')

        # The connection should be closed after enough data was
        # delivered.
        self.assertFalse(r.read())

# JsonpPolling: `/*/*/jsonp`, `/*/*/jsonp_send`
# ---------------------------------------------
class JsonPolling(Test):
    def test_transport(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'application/javascript;charset=UTF-8')
        # As JsonPolling is requested using GET we must be very
        # careful not to allow it being cached.
        self.verify_not_cached(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        # Konqueror does weird things on 204. As a workaround we need
        # to respond with something - let it be the string `ok`.
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.verify_content_type(r, 'text/plain;charset=UTF-8')
        # iOS 6 caches POSTs. Make sure we send no-cache header.
        self.verify_not_cached(r)

        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'callback("a[\\"x\\"]");\r\n')


    def test_no_callback(self):
        r = GET(base_url + '/a/a/jsonp')
        self.assertEqual(r.status, 500)
        self.assertTrue('"callback" parameter required' in r.body)

    # Supplying invalid characters to callback parameter is invalid
    # and must result in a 500 errors. Invalid characters are any
    # matching the following regexp: `[^a-zA-Z0-9-_.]`
    def test_invalid_callback(self):
        for callback in ['%20', '*', 'abc(', 'abc%28']:
            r = GET(base_url + '/a/a/jsonp?c=' + callback)
            self.assertEqual(r.status, 500)
            self.assertTrue('invalid "callback" parameter' in r.body)

    # The server must behave when invalid json data is sent or when no
    # json data is sent at all.
    def test_invalid_json(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.status, 500)
        self.assertTrue("Broken JSON encoding." in r.body)

        for data in ['', 'd=', 'p=p']:
            r = POST(url + '/jsonp_send', body=data,
                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
            self.assertEqual(r.status, 500)
            self.assertTrue("Payload expected." in r.body)

        r = POST(url + '/jsonp_send', body='d=%5B%22b%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"b\\"]");\r\n')

    # The server must accept messages sent with different content
    # types.
    def test_content_types(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22abc%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        r = POST(url + '/jsonp_send', body='["%61bc"]',
                 headers={'Content-Type': 'text/plain'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"abc\\",\\"%61bc\\"]");\r\n')

    def test_close(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("c[3000,\\"Go away!\\"]");\r\n')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("c[3000,\\"Go away!\\"]");\r\n')

    def test_sending_empty_frame(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.body, 'x("o");\r\n')

        # Sending frames containing no messages must be allowed.
        r = POST(url + '/jsonp_send', body='d=%5B%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')

        r = GET(url + '/jsonp?c=x')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'x("a[\\"x\\"]");\r\n')


# JSESSIONID cookie
# -----------------
#
# All transports except WebSockets need sticky session support from
# the load balancer. Some load balancers enable that only when they
# see `JSESSIONID` cookie. User of a sockjs server must be able to
# opt-in for this functionality - and set this cookie for all the
# session urls.
#
# Detailed explanation of this functionality is available [in this
# thread on SockJS mailing
# list](https://groups.google.com/group/sockjs/msg/ef0c508bb774a9ac).
#
class JsessionidCookie(Test):
    # Verify if info has cookie_needed set.
    def test_basic(self):
        r = GET(cookie_base_url + '/info')
        self.assertEqual(r.status, 200)
        self.verify_no_cookie(r)

        data = json.loads(r.body)
        self.assertEqual(data['cookie_needed'], True)

    # Helper to check cookie validity.
    def verify_cookie(self, r):
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=dummy')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    # JSESSIONID cookie must be set by default
    def test_xhr(self):
        # polling url must set cookies
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr')
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.verify_cookie(r)

        # Cookie must be echoed back if it's already set.
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST(url + '/xhr', headers={'Cookie': 'JSESSIONID=abcdef'})
        self.assertEqual(r.status, 200)
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r['Set-Cookie'].split(';')[0].strip(),
                         'JSESSIONID=abcdef')
        self.assertEqual(r['Set-Cookie'].split(';')[1].lower().strip(),
                         'path=/')

    def test_xhr_streaming(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = POST_async(url + '/xhr_streaming')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_eventsource(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/eventsource')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_htmlfile(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET_async(url + '/htmlfile?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

    def test_jsonp(self):
        url = cookie_base_url + '/000/' + str(uuid.uuid4())
        r = GET(url + '/jsonp?c=%63allback')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)

        self.assertEqual(r.body, 'callback("o");\r\n')

        r = POST(url + '/jsonp_send', body='d=%5B%22x%22%5D',
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(r.body, 'ok')
        self.assertEqual(r.status, 200)
        self.verify_cookie(r)


# Raw WebSocket url: `/websocket`
# -------------------------------
#
# SockJS protocol defines a bit of higher level framing. This is okay
# when the browser uses SockJS-client to establish the connection, but
# it's not really appropriate when the connection is being established
# from another program. Although SockJS focuses on server-browser
# communication, it should be straightforward to connect to SockJS
# from the command line or using any programming language.
#
# In order to make writing command-line clients easier, we define this
# `/websocket` entry point. This entry point is special and doesn't
# use any additional custom framing, no open frame, no
# heartbeats. Only raw WebSocket protocol.
class RawWebsocket(Test):
    def test_transport(self):
        ws = WebSocket8Client(base_url + '/websocket')
        ws.send(u'Hello world!\uffff')
        self.assertEqual(ws.recv(), u'Hello world!\uffff')
        ws.close()

    def test_close(self):
        ws = WebSocket8Client(close_base_url + '/websocket')
        with self.assertRaises(ws.ConnectionClosedException) as ce:
            ws.recv()
        self.assertEqual(ce.exception.reason, "Go away!")
        ws.close()



# JSON Unicode Encoding
# =====================
#
# SockJS takes the responsibility of encoding Unicode strings for the
# user.  The idea is that SockJS should properly deliver any valid
# string from the browser to the server and back. This is actually
# quite hard, as browsers do some magical character
# translations. Additionally there are some valid characters from
# JavaScript point of view that are not valid Unicode, called
# surrogates (JavaScript uses UCS-2, which is not really Unicode).
#
# Dealing with unicode surrogates (0xD800-0xDFFF) is quite special. If
# possible we should make sure that server does escape decode
# them. This makes sense for SockJS servers that support UCS-2
# (SockJS-node), but can't really work for servers supporting unicode
# properly (Python).
#
# The browser must escape quite a list of chars, this is due to
# browser mangling outgoing chars on transports like XHR.
escapable_by_client = re.compile(u"[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u2000-\u20ff\ufeff\ufff0-\uffff\x00-\x1f\ufffe\uffff\u0300-\u0333\u033d-\u0346\u034a-\u034c\u0350-\u0352\u0357-\u0358\u035c-\u0362\u0374\u037e\u0387\u0591-\u05af\u05c4\u0610-\u0617\u0653-\u0654\u0657-\u065b\u065d-\u065e\u06df-\u06e2\u06eb-\u06ec\u0730\u0732-\u0733\u0735-\u0736\u073a\u073d\u073f-\u0741\u0743\u0745\u0747\u07eb-\u07f1\u0951\u0958-\u095f\u09dc-\u09dd\u09df\u0a33\u0a36\u0a59-\u0a5b\u0a5e\u0b5c-\u0b5d\u0e38-\u0e39\u0f43\u0f4d\u0f52\u0f57\u0f5c\u0f69\u0f72-\u0f76\u0f78\u0f80-\u0f83\u0f93\u0f9d\u0fa2\u0fa7\u0fac\u0fb9\u1939-\u193a\u1a17\u1b6b\u1cda-\u1cdb\u1dc0-\u1dcf\u1dfc\u1dfe\u1f71\u1f73\u1f75\u1f77\u1f79\u1f7b\u1f7d\u1fbb\u1fbe\u1fc9\u1fcb\u1fd3\u1fdb\u1fe3\u1feb\u1fee-\u1fef\u1ff9\u1ffb\u1ffd\u2000-\u2001\u20d0-\u20d1\u20d4-\u20d7\u20e7-\u20e9\u2126\u212a-\u212b\u2329-\u232a\u2adc\u302b-\u302c\uaab2-\uaab3\uf900-\ufa0d\ufa10\ufa12\ufa15-\ufa1e\ufa20\ufa22\ufa25-\ufa26\ufa2a-\ufa2d\ufa30-\ufa6d\ufa70-\ufad9\ufb1d\ufb1f\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufb4e]")
#
# The server is able to send much more chars verbatim. But, it can't
# send Unicode surrogates over Websockets, also various \u2xxxx chars
# get mangled. Additionally, if the server is capable of handling
# UCS-2 (ie: 16 bit character size), it should be able to deal with
# Unicode surrogates 0xD800-0xDFFF:
# http://en.wikipedia.org/wiki/Mapping_of_Unicode_characters#Surrogates
escapable_by_server = re.compile(u"[\x00-\x1f\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufff0-\uffff]")

client_killer_string_esc = '"' + ''.join([
        r'\u%04x' % (i) for i in range(65536)
            if escapable_by_client.match(unichr(i))]) + '"'
server_killer_string_esc = '"' + ''.join([
        r'\u%04x'% (i) for i in range(255, 65536)
            if escapable_by_server.match(unichr(i))]) + '"'

class JSONEncoding(Test):
    def test_xhr_server_encodes(self):
        # Make sure that server encodes at least all the characters
        # it's supposed to encode.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '["' + json.loads(server_killer_string_esc) + '"]'
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we sent previously, aka - escaped.
        self.assertEqual(recv, server_killer_string_esc)

    def test_xhr_server_decodes(self):
        # Make sure that server decodes the chars we're customly
        # encoding.
        trans_url = base_url + '/000/' + str(uuid.uuid4())
        r = POST(trans_url + '/xhr')
        self.assertEqual(r.body, 'o\n')
        self.assertEqual(r.status, 200)

        payload = '[' + client_killer_string_esc + ']' # Sending escaped
        r = POST(trans_url + '/xhr_send', body=payload)
        self.assertEqual(r.status, 204)

        r = POST(trans_url + '/xhr')
        self.assertEqual(r.status, 200)
        # skip framing, quotes and parenthesis
        recv = r.body.strip()[2:-1]

        # Received string is indeed what we sent previously. We don't
        # really need to know what exactly got escaped and what not.
        a = json.loads(recv)
        b = json.loads(client_killer_string_esc)
        self.assertEqual(a, b)


# Handling close
# ==============
#
# Dealing with session closure is quite complicated part of the
# protocol. The exact details here don't matter that much to the
# client side, but it's good to have a common behaviour on the server
# side.
#
# This is less about defining the protocol and more about sanity
# checking implementations.
class HandlingClose(Test):
    # When server is closing session, it should unlink current
    # request. That means, if a new request appears, it should receive
    # an application close message rather than "Another connection
    # still open" message.
    def test_close_frame(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')
        self.assertEqual(r1.read(), 'c[3000,"Go away!"]\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[3000,"Go away!"]\n')

        # HTTP streaming requests should be automatically closed after
        # close.
        self.assertFalse(r1.read())
        self.assertFalse(r2.read())

    def test_close_request(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')

        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')

        # HTTP streaming requests should be automatically closed after
        # getting the close frame.
        self.assertFalse(r2.read())

    # When a polling request is closed by a network error - not by
    # server, the session should be automatically closed. When there
    # is a network error - we're in an undefined state. Some messages
    # may have been lost, there is not much we can do about it.
    def test_abort_xhr_streaming(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST_async(url + '/xhr_streaming')
        r1.read() # prelude
        self.assertEqual(r1.read(), 'o\n')

        # Can't do second polling request now.
        r2 = POST_async(url + '/xhr_streaming')
        r2.read() # prelude
        self.assertEqual(r2.read(), 'c[2010,"Another connection still open"]\n')
        self.assertFalse(r2.read())

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST_async(url + '/xhr_streaming')
        r3.read() # prelude
        self.assertTrue(r3.read() in ['o\n', 'c[1002,"Connection interrupted"]\n'])
        r3.close()

    # The same for polling transports
    def test_abort_xhr_polling(self):
        url = base_url + '/000/' + str(uuid.uuid4())
        r1 = POST(url + '/xhr')
        self.assertEqual(r1.body, 'o\n')

        r1 = old_POST_async(url + '/xhr', load=False)
        time.sleep(0.25)

        # Can't do second polling request now.
        r2 = POST(url + '/xhr')
        self.assertEqual(r2.body, 'c[2010,"Another connection still open"]\n')

        r1.close()

        # Polling request now, after we aborted previous one, should
        # trigger a connection closure. Implementations may close
        # the session and forget the state related. Alternatively
        # they may return a 1002 close message.
        r3 = POST(url + '/xhr')
        self.assertTrue(r3.body in ['o\n', 'c[1002,"Connection interrupted"]\n'])

# Http 1.0 and 1.1 chunking
# =========================
#
# There seem to be a lot of confusion about http/1.0 and http/1.1
# content-length and transfer-encoding:chunking headers. Although
# following tests don't really test anything sockjs specific, it's
# good to make sure that the server is behaving about this.
#
# It is not the intention of this test to verify all possible urls -
# merely to check the sanity of http server implementation.  It is
# assumed that the implementator is able to apply presented behaviour
# to other urls served by the sockjs server.
class Http10(Test):
    # We're going to test a greeting url. No dynamic content, just the
    # simplest possible response.
    def test_synchronous(self):
        c = RawHttpConnection(base_url)
        # In theory 'connection:Keep-Alive' isn't a valid http/1.0
        # header, but in this header may in practice be issued by a
        # http/1.0 client:
        # http://www.freesoft.org/CIE/RFC/2068/248.htm
        r = c.request('GET', base_url, http='1.0',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # In practice the exact http version on the response doesn't
        # really matter. Many serves always respond 1.1.
        self.assertTrue(r.http in ['1.0', '1.1'])
        # Transfer-encoding is not allowed in http/1.0.
        self.assertFalse(r.headers.get('transfer-encoding'))

        # There are two ways to give valid response. Use
        # Content-Length (and maybe connection:Keep-Alive) or
        # Connection: close.
        if not r.headers.get('content-length'):
            self.assertEqual(r.headers['connection'].lower(), 'close')
            self.assertEqual(c.read(), 'Welcome to SockJS!\n')
            self.assertTrue(c.closed())
        else:
            self.assertEqual(int(r.headers['content-length']), 19)
            self.assertEqual(c.read(19), 'Welcome to SockJS!\n')
            connection = r.headers.get('connection', '').lower()
            if connection in ['close', '']:
                # Connection-close behaviour is default in http 1.0
                print 'XXX'
                self.assertTrue(c.closed())
            else:
                self.assertEqual(connection, 'keep-alive')
                # We should be able to issue another request on the same connection
                r = c.request('GET', base_url, http='1.0',
                              headers={'Connection':'Keep-Alive'})
                self.assertEqual(r.status, 200)

    def test_streaming(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        c = RawHttpConnection(url)
        # In theory 'connection:Keep-Alive' isn't a valid http/1.0
        # header, but in this header may in practice be issued by a
        # http/1.0 client:
        # http://www.freesoft.org/CIE/RFC/2068/248.htm
        r = c.request('POST', url + '/xhr_streaming', http='1.0',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # Transfer-encoding is not allowed in http/1.0.
        self.assertFalse(r.headers.get('transfer-encoding'))
        # Content-length is not allowed - we don't know it yet.
        self.assertFalse(r.headers.get('content-length'))

        # `Connection` should be not set or be `close`. On the other
        # hand, if it is set to `Keep-Alive`, it won't really hurt, as
        # we are confident that neither `Content-Length` nor
        # `Transfer-Encoding` are set.

        # This is a the same logic as HandlingClose.test_close_frame
        self.assertEqual(c.read(2048+1)[0], 'h') # prelude
        self.assertEqual(c.read(2), 'o\n')
        self.assertEqual(c.read(19), 'c[3000,"Go away!"]\n')
        self.assertTrue(c.closed())


class Http11(Test):
    def test_synchronous(self):
        c = RawHttpConnection(base_url)
        r = c.request('GET', base_url, http='1.1',
                      headers={'Connection':'Keep-Alive'})
        # Keepalive is default in http 1.1
        self.assertTrue(r.http, '1.1')
        self.assertTrue(r.headers.get('connection', '').lower() in ['keep-alive', ''],
                         "Your server doesn't support connection:Keep-Alive")
        # Server should use 'Content-Length' or 'Transfer-Encoding'
        if r.headers.get('content-length'):
            self.assertEqual(int(r.headers['content-length']), 19)
            self.assertEqual(c.read(19), 'Welcome to SockJS!\n')
            self.assertFalse(r.headers.get('transfer-encoding'))
        else:
            self.assertEqual(r.headers['transfer-encoding'].lower(), 'chunked')
            self.assertEqual(c.read_chunk(), 'Welcome to SockJS!\n')
            self.assertEqual(c.read_chunk(), '')
        # We should be able to issue another request on the same connection
        r = c.request('GET', base_url, http='1.1',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)

    def test_streaming(self):
        url = close_base_url + '/000/' + str(uuid.uuid4())
        c = RawHttpConnection(url)
        r = c.request('POST', url + '/xhr_streaming', http='1.1',
                      headers={'Connection':'Keep-Alive'})
        self.assertEqual(r.status, 200)
        # Transfer-encoding is required in http/1.1.
        self.assertTrue(r.headers['transfer-encoding'].lower(), 'chunked')
        # Content-length is not allowed.
        self.assertFalse(r.headers.get('content-length'))
        # Connection header can be anything, so don't bother verifying it.

        # This is a the same logic as HandlingClose.test_close_frame
        self.assertEqual(c.read_chunk()[0], 'h') # prelude
        self.assertEqual(c.read_chunk(), 'o\n')
        self.assertEqual(c.read_chunk(), 'c[3000,"Go away!"]\n')
        self.assertEqual(c.read_chunk(), '')


# Footnote
# ========

# Make this script runnable.
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils_02
import urlparse
import httplib_fork as httplib
from ws4py.client.threadedclient import WebSocketClient
import Queue
import socket
import re


class HttpResponse:
    def __init__(self, method, url,
                 headers={}, body=None, async=False, load=True):
        headers = headers.copy()
        u = urlparse.urlparse(url)
        kwargs = {'timeout': 1.0}
        if u.scheme == 'http':
            conn = httplib.HTTPConnection(u.netloc, **kwargs)
        elif u.scheme == 'https':
            conn = httplib.HTTPSConnection(u.netloc, **kwargs)
        else:
            assert False, "Unsupported scheme " + u.scheme
        assert u.fragment == ''
        path = u.path + ('?' + u.query if u.query else '')
        self.conn = conn
        if not body:
            if method is 'POST':
                # The spec says: "Applications SHOULD use this field
                # to indicate the transfer-length of the message-body,
                # unless this is prohibited by the rules in section
                # 4.4."
                # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13
                # While httplib sets it only if there is body.
                headers['Content-Length'] = 0
            conn.request(method, path, headers=headers)
        else:
            if isinstance(body, unicode):
                body = body.encode('utf-8')
            conn.request(method, path, headers=headers, body=body)

        if load:
            if not async:
                self._load()
            else:
                self._async_load()

    def _get_status(self):
        return self.res.status
    status = property(_get_status)

    def __getitem__(self, key):
        return self.headers.get(key.lower())

    def _load(self):
        self.res = self.conn.getresponse()
        self.headers = dict( (k.lower(), v) for k, v in self.res.getheaders() )
        self.body = self.res.read()
        self.close()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _async_load(self):
        self.res = self.conn.getresponse()
        self.headers = dict( (k.lower(), v) for k, v in self.res.getheaders() )

    def read(self):
        data =  self.res.read(10240)
        if data:
            return data
        else:
            self.close()
            return None

def GET(url, **kwargs):
    return HttpResponse('GET', url, **kwargs)

def GET_async(url, **kwargs):
    return HttpResponse('GET', url, async=True, **kwargs)

def POST(url, **kwargs):
    return HttpResponse('POST', url, **kwargs)

def POST_async(url, **kwargs):
    return HttpResponse('POST', url, async=True, **kwargs)

def OPTIONS(url, **kwargs):
    return HttpResponse('OPTIONS', url, **kwargs)


class WebSocket8Client(object):
    class ConnectionClosedException(Exception): pass

    def __init__(self, url):
        queue = Queue.Queue()
        self.queue = queue
        class IntWebSocketClient(WebSocketClient):
            def received_message(self, m):
                queue.put(unicode(str(m), 'utf-8'))
            def read_from_connection(self, amount):
                r = super(IntWebSocketClient, self).read_from_connection(amount)
                if not r:
                    queue.put(Ellipsis)
                return r
        self.client = IntWebSocketClient(url)
        self.client.connect()

    def close(self):
        if self.client:
            self.client.running = False
            self.client.close()
            self.client._th.join()
            self.client = None

    def send(self, data):
        self.client.send(data)

    def recv(self):
        try:
            r = self.queue.get(timeout=1.0)
            if r is Ellipsis:
                raise self.ConnectionClosedException()
            return r
        except:
            self.close()
            raise

def recvline(s):
    b = []
    c = None
    while c != '\n':
        c = s.recv(1)
        b.append( c )
    return ''.join(b)


class CaseInsensitiveDict(object):
    def __init__(self, *args, **kwargs):
        self.lower = {}
        self.d = dict(*args, **kwargs)
        for k in self.d:
            self[k] = self.d[k]

    def __getitem__(self, key, *args, **kwargs):
        pkey = self.lower.setdefault(key.lower(), key)
        return self.d.__getitem__(pkey, *args, **kwargs)

    def __setitem__(self, key, *args, **kwargs):
        pkey = self.lower.setdefault(key.lower(), key)
        return self.d.__setitem__(pkey, *args, **kwargs)

    def items(self):
        for k in self.lower.values():
            yield (k, self[k])

    def __repr__(self): return repr(self.d)
    def __str__(self): return str(self.d)

    def get(self, key, *args, **kwargs):
        pkey = self.lower.setdefault(key.lower(), key)
        return self.d.get(pkey, *args, **kwargs)

    def __contains__(self, key):
        pkey = self.lower.setdefault(key.lower(), key)
        return pkey in self.d

class Response(object):
    def __repr__(self):
        return '<Response HTTP/%s %s %r %r>' % (
            self.http, self.status, self.description, self.headers)

    def __str__(self): return repr(self)

class RawHttpConnection(object):
    def __init__(self, url):
        u = urlparse.urlparse(url)
        self.s = socket.create_connection((u.hostname, u.port), timeout=1)

    def request(self, method, url, headers={}, body=None, timeout=1, http="1.1"):
        headers = CaseInsensitiveDict(headers)
        if method == 'POST':
            body = body or ''
        u = urlparse.urlparse(url)
        headers['Host'] = u.hostname + ':' + str(u.port) if u.port else u.hostname
        if body is not None:
            headers['Content-Length'] = str(len(body))

        req = ["%s %s HTTP/%s" % (method, u.path, http)]
        for k, v in headers.items():
            req.append( "%s: %s" % (k, v) )
        req.append('')
        req.append('')
        self.s.sendall('\r\n'.join(req))

        if body:
            self.s.sendall(body)

        head = recvline(self.s)
        r = re.match(r'HTTP/(?P<version>\S+) (?P<status>\S+) (?P<description>.*)', head)

        resp = Response()
        resp.http = r.group('version')
        resp.status = int(r.group('status'))
        resp.description = r.group('description').rstrip('\r\n')

        resp.headers = CaseInsensitiveDict()
        while True:
            header = recvline(self.s)
            if header in ['\n', '\r\n']:
                break
            k, _, v = header.partition(':')
            resp.headers[k] = v.lstrip().rstrip('\r\n')

        return resp

    def read(self, size=None):
        if size is None:
            # A single packet by default
            return self.s.recv(999999)
        data = []
        while size > 0:
            c = self.s.recv(size)
            if not c:
                raise Exception('Socket closed!')
            size -= len(c)
            data.append( c )
        return ''.join(data)

    def closed(self):
        # To check if socket is being closed, we need to recv and see
        # if the response is empty.
        t = self.s.settimeout(0.1)
        r = self.s.recv(1) == ''
        if not r:
            raise Exception('Socket not closed!')
        self.s.settimeout(t)
        return r

    def read_chunk(self):
        line = recvline(self.s).rstrip('\r\n')
        bytes = int(line, 16) + 2 # Additional \r\n
        return self.read(bytes)[:-2]

    def send(self, data):
        self.s.sendall(data)

########NEW FILE########
__FILENAME__ = utils_03
import urlparse
import httplib_fork as httplib
from ws4py.client.threadedclient import WebSocketClient
import Queue
import socket
import re

class HttpResponse:
    def __init__(self, method, url,
                 headers={}, body=None, async=False, load=True):
        headers = headers.copy()
        u = urlparse.urlparse(url)
        kwargs = {'timeout': 1.0}
        if u.scheme == 'http':
            conn = httplib.HTTPConnection(u.netloc, **kwargs)
        elif u.scheme == 'https':
            conn = httplib.HTTPSConnection(u.netloc, **kwargs)
        else:
            assert False, "Unsupported scheme " + u.scheme
        assert u.fragment == ''
        path = u.path + ('?' + u.query if u.query else '')
        self.conn = conn
        if not body:
            if method is 'POST':
                # The spec says: "Applications SHOULD use this field
                # to indicate the transfer-length of the message-body,
                # unless this is prohibited by the rules in section
                # 4.4."
                # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13
                # While httplib sets it only if there is body.
                headers['Content-Length'] = 0
            conn.request(method, path, headers=headers)
        else:
            if isinstance(body, unicode):
                body = body.encode('utf-8')
            conn.request(method, path, headers=headers, body=body)

        if load:
            if not async:
                self._load()
            else:
                self._async_load()

    def _get_status(self):
        return self.res.status
    status = property(_get_status)

    def __getitem__(self, key):
        return self.headers.get(key.lower())

    def _load(self):
        # That works for Content-Length responses.
        self.res = self.conn.getresponse()
        self.headers = dict( (k.lower(), v) for k, v in self.res.getheaders() )
        self.body = self.res.read()
        self.close()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _async_load(self):
        # That works for Transfer-Encoding: Chunked
        self.res = self.conn.getresponse()
        self.headers = dict( (k.lower(), v) for k, v in self.res.getheaders() )

    def read(self):
        data =  self.res.read(10240)
        if data:
            return data
        else:
            self.close()
            return None

def old_POST_async(url, **kwargs):
    return HttpResponse('POST', url, async=True, **kwargs)


class WebSocket8Client(object):
    class ConnectionClosedException(Exception): pass

    def __init__(self, url):
        queue = Queue.Queue()
        self.queue = queue
        class IntWebSocketClient(WebSocketClient):
            def received_message(self, m):
                queue.put(unicode(str(m), 'utf-8'))
            def read_from_connection(self, amount):
                r = super(IntWebSocketClient, self).read_from_connection(amount)
                if self.stream.closing:
                    queue.put((self.stream.closing.code, self.stream.closing.reason[2:]))
                elif not r:
                    queue.put((1000, ""))
                return r
        self.client = IntWebSocketClient(url)
        self.client.connect()

    def close(self):
        if self.client:
            self.client.running = False
            self.client.close()
            self.client._th.join()
            self.client = None

    def send(self, data):
        self.client.send(data)

    def recv(self):
        try:
            r = self.queue.get(timeout=1.0)
            if isinstance(r, tuple):
                ce = self.ConnectionClosedException()
                (ce.code, ce.reason) = r
                raise ce
            return r
        except:
            self.close()
            raise

def recvline(s):
    b = []
    c = None
    while c != '\n':
        c = s.recv(1)
        b.append( c )
    return ''.join(b)


class CaseInsensitiveDict(object):
    def __init__(self, *args, **kwargs):
        self.lower = {}
        self.d = dict(*args, **kwargs)
        for k in self.d:
            self[k] = self.d[k]

    def __getitem__(self, key, *args, **kwargs):
        pkey = self.lower.setdefault(key.lower(), key)
        return self.d.__getitem__(pkey, *args, **kwargs)

    def __setitem__(self, key, *args, **kwargs):
        pkey = self.lower.setdefault(key.lower(), key)
        return self.d.__setitem__(pkey, *args, **kwargs)

    def items(self):
        for k in self.lower.values():
            yield (k, self[k])

    def __repr__(self): return repr(self.d)
    def __str__(self): return str(self.d)

    def get(self, key, *args, **kwargs):
        pkey = self.lower.setdefault(key.lower(), key)
        return self.d.get(pkey, *args, **kwargs)

    def __contains__(self, key):
        pkey = self.lower.setdefault(key.lower(), key)
        return pkey in self.d

class Response(object):
    def __repr__(self):
        return '<Response HTTP/%s %s %r %r>' % (
            self.http, self.status, self.description, self.headers)

    def __str__(self): return repr(self)

    def __getitem__(self, key):
        return self.headers.get(key)

    def get(self, key, default):
        return self.headers.get(key, default)


class RawHttpConnection(object):
    def __init__(self, url):
        u = urlparse.urlparse(url)
        self.s = socket.create_connection((u.hostname, u.port), timeout=1)

    def request(self, method, url, headers={}, body=None, timeout=1, http="1.1"):
        headers = CaseInsensitiveDict(headers)
        if method == 'POST':
            body = (body or '').encode('utf-8')
        u = urlparse.urlparse(url)
        headers['Host'] = u.hostname + ':' + str(u.port) if u.port else u.hostname
        if body is not None:
            headers['Content-Length'] = str(len(body))

        rel_url = url[ url.find(u.path): ]

        req = ["%s %s HTTP/%s" % (method, rel_url, http)]
        for k, v in headers.items():
            req.append( "%s: %s" % (k, v) )
        req.append('')
        req.append('')
        self.send('\r\n'.join(req))

        if body:
            self.send(body)

        head = recvline(self.s)
        r = re.match(r'HTTP/(?P<version>\S+) (?P<status>\S+) (?P<description>.*)', head)

        resp = Response()
        resp.http = r.group('version')
        resp.status = int(r.group('status'))
        resp.description = r.group('description').rstrip('\r\n')

        resp.headers = CaseInsensitiveDict()
        while True:
            header = recvline(self.s)
            if header in ['\n', '\r\n']:
                break
            k, _, v = header.partition(':')
            resp.headers[k] = v.lstrip().rstrip('\r\n')

        return resp

    def read(self, size=None):
        if size is None:
            # A single packet by default
            return self.s.recv(999999)
        data = []
        while size > 0:
            c = self.s.recv(size)
            if not c:
                raise Exception('Socket closed!')
            size -= len(c)
            data.append( c )
        return ''.join(data)

    def read_till_eof(self):
        data = []
        while True:
            c = self.s.recv(999999)
            if not c:
                break
            data.append( c )
        return ''.join(data)

    def closed(self):
        # To check if socket is being closed, we need to recv and see
        # if the response is empty. If it is not - we're in trouble -
        # abort.
        t = self.s.settimeout(0.1)
        r = self.s.recv(1) == ''
        if not r:
            raise Exception('Socket not closed!')
        self.s.settimeout(t)
        return r

    def read_chunk(self):
        line = recvline(self.s).rstrip('\r\n')
        bytes = int(line, 16) + 2 # Additional \r\n
        return self.read(bytes)[:-2]

    def send(self, data):
        self.s.sendall(data)

    def close(self):
        self.s.close()


def SynchronousHttpRequest(method, url, **kwargs):
    c = RawHttpConnection(url)
    r = c.request(method, url, **kwargs)
    if r.get('Transfer-Encoding', '').lower() == 'chunked':
        chunks = []
        while True:
            chunk = c.read_chunk()
            if len(chunk) == 0:
                break
            chunks.append( chunk )
        r.body = ''.join(chunks)
    elif r.get('Content-Length', ''):
        cl = int(r['Content-Length'])
        r.body = c.read(cl)
    elif 'close' in [k.strip() for k in r.get('Connection', '').lower().split(',')]:
        r.body = c.read_till_eof()
    else:
        # Whitelist statuses that may not need a response
        if r.status in [101, 304, 204]:
            r.body = ''
        else:
            raise Exception(str(r.status) + ' '+str(r.headers) + " No Transfer-Encoding:chunked nor Content-Length nor Connection:Close!")
    c.close()
    return r

def GET(url, **kwargs):
    return SynchronousHttpRequest('GET', url, **kwargs)

def POST(url, **kwargs):
    return SynchronousHttpRequest('POST', url, **kwargs)

def OPTIONS(url, **kwargs):
    return SynchronousHttpRequest('OPTIONS', url, **kwargs)

def AsynchronousHttpRequest(method, url, **kwargs):
    c = RawHttpConnection(url)
    r = c.request(method, url, **kwargs)
    if r.get('Transfer-Encoding', '').lower() == 'chunked':
        def read():
            return c.read_chunk()
        r.read = read
    elif r.get('Content-Length', ''):
        cl = int(r['Content-Length'])
        def read():
            return c.read(cl)
        r.read = read
    elif ('close' in [k.strip() for k in r.get('Connection', '').lower().split(',')]
          or r.status == 101):
        def read():
            return c.read()
        r.read = read
    else:
        raise Exception(str(r.status) + ' '+str(r.headers) + " No Transfer-Encoding:chunked nor Content-Length nor Connection:Close!")
    def close():
        c.close()
    r.close = close
    return r

def GET_async(url, **kwargs):
    return AsynchronousHttpRequest('GET', url, **kwargs)

def POST_async(url, **kwargs):
    return AsynchronousHttpRequest('POST', url, **kwargs)

########NEW FILE########
