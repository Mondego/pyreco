__FILENAME__ = proxy
#!/usr/bin/env python

"""
A simple HTTP proxy as a demonstration.
"""


import sys
try: # run from dist without installation
    sys.path.insert(0, "..")
    from src import Client, Server, header_dict, run, client, schedule
except ImportError:
    from nbhttp import Client, Server, header_dict, run, client, schedule

# TODO: CONNECT support
# TODO: remove headers nominated by Connection
# TODO: add Via

class ProxyClient(Client):
    read_timeout = 10
    connect_timeout = 15

def proxy_handler(method, uri, req_hdrs, s_res_start, req_pause):
    # can modify method, uri, req_hdrs here
    def c_res_start(version, status, phrase, res_hdrs, res_pause):
        # can modify status, phrase, res_hdrs here
        res_body, res_done = s_res_start(status, phrase, res_hdrs, res_pause)
        # can modify res_body here
        return res_body, res_done
    c = ProxyClient(c_res_start)
    req_body, req_done = c.req_start(method, uri, req_hdrs, req_pause)
    # can modify req_body here
    return req_body, req_done 


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1])
    server = Server('', port, proxy_handler)
    run()
########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python

"""
Non-Blocking HTTP Client

This library allow implementation of an HTTP/1.1 client that is
"non-blocking," "asynchronous" and "event-driven" -- i.e., it achieves very
high performance and concurrency, so long as the application code does not
block (e.g., upon network, disk or database access). Blocking on one response
will block the entire client.

Instantiate a Client with the following parameter:
  - res_start (callable)
  
Call req_start on the Client instance to begin a request. It takes the
following arguments:
  - method (string)
  - uri (string)
  - req_hdrs (list of (name, value) tuples)
  - req_body_pause (callable)
and returns:
  - req_body (callable)
  - req_done (callable)
    
Call req_body to send part of the request body. It takes the following 
argument:
  - chunk (string)

Call req_done when the request is complete, whether or not it contains a 
body. It takes the following argument:
  - err (error dictionary, or None for no error)

req_body_pause is called when the client needs you to temporarily stop sending
the request body, or restart. It must take the following argument:
  - paused (boolean; True means pause, False means unpause)
    
res_start is called to start the response, and must take the following 
arguments:
  - status_code (string)
  - status_phrase (string)
  - res_hdrs (list of (name, value) tuples)
  - res_body_pause
It must return:
  - res_body (callable)
  - res_done (callable)
    
res_body is called when part of the response body is available. It must accept
the following parameter:
  - chunk (string)
  
res_done is called when the response is finished, and must accept the 
following argument:
  - err (error dictionary, or None if no error)
    
See the error module for the complete list of valid error dictionaries.

Where possible, errors in the response will be indicated with the appropriate
5xx HTTP status code (i.e., by calling res_start, res_body and res_done with
an error dictionary). However, if a response has already been started, the
connection will be dropped (for example, when the response chunking or
indicated length are incorrect). In these cases, res_done will still be called
with the appropriate error dictionary.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2010 Mark Nottingham

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
"""

import errno
import os
from urlparse import urlsplit, urlunsplit

import push_tcp
from http_common import HttpMessageHandler, \
    CLOSE, COUNTED, NOBODY, \
    WAITING, \
    idempotent_methods, no_body_status, hop_by_hop_hdrs, \
    dummy, get_hdr
from error import ERR_URL, ERR_CONNECT, \
    ERR_READ_TIMEOUT, ERR_HTTP_VERSION

req_remove_hdrs = hop_by_hop_hdrs + ['host']

# TODO: proxy support
# TODO: next-hop version cache for Expect/Continue, etc.

class Client(HttpMessageHandler):
    "An asynchronous HTTP client."
    connect_timeout = None
    read_timeout = None
    retry_limit = 2

    def __init__(self, res_start_cb):
        HttpMessageHandler.__init__(self)
        self.res_start_cb = res_start_cb
        self.res_body_cb = None
        self.res_done_cb = None
        self.method = None
        self.uri = None
        self.req_hdrs = []
        self._host = None
        self._port = None
        self._tcp_conn = None
        self._conn_reusable = False
        self._req_body_pause_cb = None
        self._retries = 0
        self._read_timeout_ev = None
        self._output_buffer = []

    def __getstate__(self):
        props = ['method', 'uri', 'req_hdrs', 
            'input_header_length', 'input_transfer_length']
        return dict([(k, v) for (k, v) in self.__dict__.items() 
                     if k in props])

    def req_start(self, method, uri, req_hdrs, req_body_pause):
        """
        Start a request to uri using method, where 
        req_hdrs is a list of (field_name, field_value) for
        the request headers.
        
        Returns a (req_body, req_done) tuple.
        """
        self._req_body_pause_cb = req_body_pause
        req_hdrs = [i for i in req_hdrs \
            if not i[0].lower() in req_remove_hdrs]
        (scheme, authority, path, query, fragment) = urlsplit(uri)
        if scheme.lower() != 'http':
            self._handle_error(ERR_URL, "Only HTTP URLs are supported")
            return dummy, dummy
        if "@" in authority:
            userinfo, authority = authority.split("@", 1)
        if ":" in authority:
            self._host, port = authority.rsplit(":", 1)
            try:
                self._port = int(port)
            except ValueError:
                self._handle_error(ERR_URL, "Non-integer port in URL")
                return dummy, dummy
        else:
            self._host, self._port = authority, 80
        if path == "":
            path = "/"
        uri = urlunsplit(('', '', path, query, ''))
        self.method, self.uri, self.req_hdrs = method, uri, req_hdrs
        self.req_hdrs.append(("Host", authority))
        self.req_hdrs.append(("Connection", "keep-alive"))
        try:
            body_len = int(get_hdr(req_hdrs, "content-length").pop(0))
            delimit = COUNTED
        except (IndexError, ValueError):
            body_len = None
            delimit = NOBODY
        self._output_start("%s %s HTTP/1.1" % (self.method, self.uri),
            self.req_hdrs, delimit
        )
        _idle_pool.attach(self._host, self._port, self._handle_connect,
            self._handle_connect_error, self.connect_timeout
        )
        return self.req_body, self.req_done
    # TODO: if we sent Expect: 100-continue, don't wait forever 
    # (i.e., schedule something)

    def req_body(self, chunk):
        "Send part of the request body. May be called zero to many times."
        # FIXME: self._handle_error(ERR_LEN_REQ)
        self._output_body(chunk)
        
    def req_done(self, err=None):
        """
        Signal the end of the request, whether or not there was a body. MUST
        be called exactly once for each request.
        
         If err is not None, it is an error dictionary (see the error module)
        indicating that an HTTP-specific (i.e., non-application) error
        occurred while satisfying the request; this is useful for debugging.
        """
        self._output_end(err)            

    def res_body_pause(self, paused):
        "Temporarily stop / restart sending the response body."
        if self._tcp_conn and self._tcp_conn.tcp_connected:
            self._tcp_conn.pause(paused)
        
    # Methods called by push_tcp

    def _handle_connect(self, tcp_conn):
        "The connection has succeeded."
        self._tcp_conn = tcp_conn
        self._output("") # kick the output buffer
        if self.read_timeout:
            self._read_timeout_ev = push_tcp.schedule(
                self.read_timeout, self._handle_error, 
                ERR_READ_TIMEOUT, 'connect'
            )
        return self._handle_input, self._conn_closed, self._req_body_pause

    def _handle_connect_error(self, err):
        "The connection has failed."
        if err[0] == errno.EINVAL: # weirdness.
            err = (errno.ECONNREFUSED, os.strerror(errno.ECONNREFUSED))
        self._handle_error(ERR_CONNECT, err[1])

    def _conn_closed(self):
        "The server closed the connection."
        if self.read_timeout:
            self._read_timeout_ev.delete()
        if self._input_buffer:
            self._handle_input("")
        if self._input_delimit == CLOSE:
            self._input_end()
        elif self._input_state == WAITING:
            if self.method in idempotent_methods:
                if self._retries < self.retry_limit:
                    self._retry()
                else:
                    self._handle_error(ERR_CONNECT, 
                        "Tried to connect %s times." % (self._retries + 1)
                    )
            else:
                self._handle_error(ERR_CONNECT, 
                    "Can't retry %s method" % self.method
                )
        else:
            self._input_error(ERR_CONNECT, 
                "Server dropped connection before the response was received."
            )

    def _retry(self):
        "Retry the request."
        if self._read_timeout_ev:
            self._read_timeout_ev.delete()
        self._retries += 1
        _idle_pool.attach(self._host, self._port, self._handle_connect,
            self._handle_connect_error, self.connect_timeout
        )

    def _req_body_pause(self, paused):
        "The client needs the application to pause/unpause the request body."
        if self._req_body_pause_cb:
            self._req_body_pause_cb(paused)

    # Methods called by common.HttpMessageHandler

    def _input_start(self, top_line, hdr_tuples, conn_tokens, 
        transfer_codes, content_length):
        """
        Take the top set of headers from the input stream, parse them
        and queue the request to be processed by the application.
        """
        if self.read_timeout:
            self._read_timeout_ev.delete()
        try: 
            res_version, status_txt = top_line.split(None, 1)
            res_version = float(res_version.rsplit('/', 1)[1])
            # TODO: check that the protocol is HTTP
        except (ValueError, IndexError):
            self._handle_error(ERR_HTTP_VERSION, top_line)
            raise ValueError
        try:
            res_code, res_phrase = status_txt.split(None, 1)
        except ValueError:
            res_code = status_txt.rstrip()
            res_phrase = ""
        if 'close' not in conn_tokens:
            if (res_version == 1.0 and 'keep-alive' in conn_tokens) or \
                res_version > 1.0:
                self._conn_reusable = True
        if self.read_timeout:
            self._read_timeout_ev = push_tcp.schedule(
                 self.read_timeout, self._input_error, 
                 ERR_READ_TIMEOUT, 'start'
            )
        self.res_body_cb, self.res_done_cb = self.res_start_cb(
            res_version, res_code, res_phrase, 
            hdr_tuples, self.res_body_pause
        )
        allows_body = (res_code not in no_body_status) \
            or (self.method == "HEAD")
        return allows_body 

    def _input_body(self, chunk):
        "Process a response body chunk from the wire."
        if self.read_timeout:
            self._read_timeout_ev.delete()
        self.res_body_cb(chunk)
        if self.read_timeout:
            self._read_timeout_ev = push_tcp.schedule(self.read_timeout,
                self._input_error, ERR_READ_TIMEOUT, 'body'
            )

    def _input_end(self):
        "Indicate that the response body is complete."
        if self.read_timeout:
            self._read_timeout_ev.delete()
        if self._tcp_conn:
            if self._tcp_conn.tcp_connected and self._conn_reusable:
                # Note that we don't reset read_cb; if more bytes come in
                # before the next request, we'll still get them.
                _idle_pool.release(self._tcp_conn)
            else:
                self._tcp_conn.close()
                self._tcp_conn = None
        self.res_done_cb(None)

    def _input_error(self, err, detail=None):
        "Indicate a parsing problem with the response body."
        if self.read_timeout:
            self._read_timeout_ev.delete()
        if self._tcp_conn:
            self._tcp_conn.close()
            self._tcp_conn = None
        err['detail'] = detail
        self.res_done_cb(err)

    def _output(self, chunk):
        self._output_buffer.append(chunk)
        if self._tcp_conn and self._tcp_conn.tcp_connected:
            self._tcp_conn.write("".join(self._output_buffer))
            self._output_buffer = []

    # misc

    def _handle_error(self, err, detail=None):
        """
        Handle a problem with the request by generating an appropriate
        response.
        """
        assert self._input_state == WAITING
        if self._read_timeout_ev:
            self._read_timeout_ev.delete()
        if self._tcp_conn:
            self._tcp_conn.close()
            self._tcp_conn = None
        if detail:
            err['detail'] = detail
        status_code, status_phrase = err.get('status', 
            ('504', 'Gateway Timeout')
        )
        hdrs = [
            ('Content-Type', 'text/plain'),
            ('Connection', 'close'),
        ]
        body = err['desc']
        if err.has_key('detail'):
            body += " (%s)" % err['detail']
        res_body_cb, res_done_cb = self.res_start_cb(
              "1.1", status_code, status_phrase, hdrs, dummy)
        res_body_cb(str(body))
        push_tcp.schedule(0, res_done_cb, err)


class _HttpConnectionPool:
    "A pool of idle TCP connections for use by the client."
    _conns = {}

    def attach(self, host, port, handle_connect, 
        handle_connect_error, connect_timeout):
        "Find an idle connection for (host, port), or create a new one."
        while True:
            try:
                tcp_conn = self._conns[(host, port)].pop()
            except (IndexError, KeyError):
                push_tcp.create_client(host, port, 
                    handle_connect, handle_connect_error, connect_timeout
                )
                break        
            if tcp_conn.tcp_connected:
                tcp_conn.read_cb, tcp_conn.close_cb, tcp_conn.pause_cb = \
                    handle_connect(tcp_conn)
                break
        
    def release(self, tcp_conn):
        "Add an idle connection back to the pool."
        if tcp_conn.tcp_connected:
            def idle_close():
                "Remove the connection from the pool when it closes."
                try:
                    self._conns[
                        (tcp_conn.host, tcp_conn.port)
                    ].remove(tcp_conn)
                except ValueError:
                    pass
            tcp_conn.close_cb = idle_close
            if not self._conns.has_key((tcp_conn.host, tcp_conn.port)):
                self._conns[(tcp_conn.host, tcp_conn.port)] = [tcp_conn]
            else:
                self._conns[(tcp_conn.host, tcp_conn.port)].append(tcp_conn)

_idle_pool = _HttpConnectionPool()


def test_client(request_uri, out, err):
    "A simple demonstration of a client."

    def printer(version, status, phrase, headers, res_pause):
        "Print the response headers."
        print "HTTP/%s" % version, status, phrase
        print "\n".join(["%s:%s" % header for header in headers])
        print
        def body(chunk):
            out(chunk)
        def done(err_msg):
            if err_msg:
                err("\n*** ERROR: %s (%s)\n" % 
                    (err_msg['desc'], err_msg['detail'])
                )
            push_tcp.stop()
        return body, done
    c = Client(printer)
    req_body_write, req_done = c.req_start("GET", request_uri, [], dummy)
    req_done(None)
    push_tcp.run()
            
if __name__ == "__main__":
    import sys
    test_client(sys.argv[1], sys.stdout.write, sys.stderr.write)

########NEW FILE########
__FILENAME__ = error
#!/usr/bin/env python

"""
errors
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2010 Mark Nottingham

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
"""

# General parsing errors

ERR_CHUNK = {
    'desc': "Chunked encoding error",
}
ERR_EXTRA_DATA = {
    'desc': "Extra data received",
}

ERR_BODY_FORBIDDEN = {
    'desc': "This message does not allow a body",
}

ERR_HTTP_VERSION = {
    'desc': "Unrecognised HTTP version",  # FIXME: more specific status
}

ERR_READ_TIMEOUT = {
    'desc': "Read timeout", 
}

ERR_TRANSFER_CODE = {
    'desc': "Unknown request transfer coding",
    'status': ("501", "Not Implemented"),
}

ERR_WHITESPACE_HDR = {
    'desc': "Whitespace between request-line and first header",
    'status': ("400", "Bad Request"),
}

ERR_TOO_MANY_MSGS = {
    'desc': "Too many messages to parse",
    'status': ("400", "Bad Request"),
}

# client-specific errors

ERR_URL = {
    'desc': "Unsupported or invalid URI",
    'status': ("400", "Bad Request"),
}
ERR_LEN_REQ = {
    'desc': "Content-Length required",
    'status': ("411", "Length Required"),
}

ERR_CONNECT = {
    'desc': "Connection closed",
    'status': ("504", "Gateway Timeout"),
}

# server-specific errors

ERR_HOST_REQ = {
    'desc': "Host header required",
}

########NEW FILE########
__FILENAME__ = http_common
#!/usr/bin/env python

"""
shared HTTP infrastructure

This module contains utility functions for nbhttp and a base class
for the parsing portions of the client and server.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2010 Mark Nottingham

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
"""

import re
lws = re.compile("\r?\n[ \t]+", re.M)
hdr_end = re.compile(r"\r?\n\r?\n", re.M)
linesep = "\r\n" 

# conn_modes
CLOSE, COUNTED, CHUNKED, NOBODY = 'close', 'counted', 'chunked', 'nobody'

# states
WAITING, HEADERS_DONE = 1, 2

idempotent_methods = ['GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS', 'TRACE']
safe_methods = ['GET', 'HEAD', 'OPTIONS', 'TRACE']
no_body_status = ['100', '101', '204', '304']
hop_by_hop_hdrs = ['connection', 'keep-alive', 'proxy-authenticate', 
                   'proxy-authorization', 'te', 'trailers', 
                   'transfer-encoding', 'upgrade', 'proxy-connection']


from error import ERR_EXTRA_DATA, ERR_CHUNK, ERR_BODY_FORBIDDEN, \
    ERR_TOO_MANY_MSGS

def dummy(*args, **kw):
    "Dummy method that does nothing; useful to ignore a callback."
    pass

def header_dict(header_tuple, strip=None):
    """
    Given a header tuple, return a dictionary keyed upon the lower-cased
    header names.
    
    If strip is defined, each header listed (by lower-cased name) will not be
    returned in the dictionary.
    """ 
    # TODO: return a list of values; currently destructive.
    if strip == None:
        strip = []
    return dict([(n.strip().lower(), v.strip()) for (n, v) in header_tuple])

def get_hdr(hdr_tuples, name):
    """
    Given a list of (name, value) header tuples and a header name (lowercase),
    return a list of all values for that header.

    This includes header lines with multiple values separated by a comma; 
    such headers will be split into separate values. As a result, it is NOT
    safe to use this on headers whose values may include a comma (e.g.,
    Set-Cookie, or any value with a quoted string).
    """
    # TODO: support quoted strings
    return [v.strip() for v in sum(
               [l.split(',') for l in 
                    [i[1] for i in hdr_tuples if i[0].lower() == name]
                ]
            , [])]


class HttpMessageHandler:
    """
    This is a base class for something that has to parse and/or serialise 
    HTTP messages, request or response.

    For parsing, it expects you to override _input_start, _input_body and
    _input_end, and call _handle_input when you get bytes from the network.

    For serialising, it expects you to override _output.
    """

    def __init__(self):
        self.input_header_length = 0
        self.input_transfer_length = 0
        self._input_buffer = ""
        self._input_state = WAITING
        self._input_delimit = None
        self._input_body_left = 0
        self._output_state = WAITING
        self._output_delimit = None

    # input-related methods

    def _input_start(self, top_line, hdr_tuples, conn_tokens, 
                     transfer_codes, content_length):
        """
        Take the top set of headers from the input stream, parse them
        and queue the request to be processed by the application.
        
        Returns boolean allows_body to indicate whether the message allows a 
        body.
        """
        raise NotImplementedError

    def _input_body(self, chunk):
        "Process a body chunk from the wire."
        raise NotImplementedError

    def _input_end(self):
        "Indicate that the response body is complete."
        raise NotImplementedError
    
    def _input_error(self, err, detail=None):
        "Indicate a parsing problem with the body."
        raise NotImplementedError
    
    def _handle_input(self, instr):
        """
        Given a chunk of input, figure out what state we're in and handle it,
        making the appropriate calls.
        """
        if self._input_buffer != "":
            # will need to move to a list if writev comes around
            instr = self._input_buffer + instr 
            self._input_buffer = ""
        if self._input_state == WAITING:
            if hdr_end.search(instr): # found one
                rest = self._parse_headers(instr)
                try:
                    self._handle_input(rest)
                except RuntimeError:
                    self._input_error(ERR_TOO_MANY_MSGS)
            else: # partial headers; store it and wait for more
                self._input_buffer = instr
        elif self._input_state == HEADERS_DONE:
            try:
                input_parse = getattr(self, '_handle_%s' %
                                      self._input_delimit)
            except AttributeError:
                raise Exception, "Unknown input delimiter %s" % \
                                 self._input_delimit
            input_parse(instr)
        else:
            raise Exception, "Unknown state %s" % self._input_state

    def _handle_nobody(self, instr):
        "Handle input that shouldn't have a body."
        if instr:
            # FIXME: will not work with pipelining
            self._input_error(ERR_BODY_FORBIDDEN, instr) 
        else:
            self._input_end()
        self._input_state = WAITING
#       self._handle_input(instr)

    def _handle_close(self, instr):
        "Handle input where the body is delimited by the connection closing."
        self.input_transfer_length += len(instr)
        self._input_body(instr)

    def _handle_chunked(self, instr):
        "Handle input where the body is delimited by chunked encoding."
        while instr:
            if self._input_body_left < 0: # new chunk
                instr = self._handle_chunk_new(instr)
            elif self._input_body_left > 0: 
                # we're in the middle of reading a chunk
                instr = self._handle_chunk_body(instr)
            elif self._input_body_left == 0: # body is done
                instr = self._handle_chunk_done(instr)

    def _handle_chunk_new(self, instr):
        try:
            # they really need to use CRLF
            chunk_size, rest = instr.split(linesep, 1)
        except ValueError:
            # got a CRLF without anything behind it.. wait a bit
            if len(instr) > 256:
                # OK, this is absurd...
                self._input_error(ERR_CHUNK, instr)
            else:
                self._input_buffer += instr
            return
        if chunk_size.strip() == "": # ignore bare lines
            self._handle_chunked(rest) # FIXME: recursion
            return
        if ";" in chunk_size: # ignore chunk extensions
            chunk_size = chunk_size.split(";", 1)[0]
        try:
            self._input_body_left = int(chunk_size, 16)
        except ValueError:
            self._input_error(ERR_CHUNK, chunk_size)
            return # blow up if we can't process a chunk.
        self.input_transfer_length += len(instr) - len(rest)        
        return rest

    def _handle_chunk_body(self, instr):
        if self._input_body_left < len(instr): # got more than the chunk
            this_chunk = self._input_body_left
            self._input_body(instr[:this_chunk])
            self.input_transfer_length += this_chunk
            self._input_body_left = -1
            return instr[this_chunk+2:] # +2 consumes the CRLF
        elif self._input_body_left == len(instr): 
            # got the whole chunk exactly
            self._input_body(instr)
            self.input_transfer_length += self._input_body_left
            self._input_body_left = -1
        else: 
            # got partial chunk
            self._input_body(instr)
            self.input_transfer_length += len(instr)
            self._input_body_left -= len(instr)

    def _handle_chunk_done(self, instr):
        if len(instr) >= 2 and instr[:2] == linesep:
            self._input_state = WAITING
            self._input_end()
#                self._handle_input(instr[2:]) # pipelining
        elif hdr_end.search(instr): # trailers
            self._input_state = WAITING
            self._input_end()
            trailers, rest = hdr_end.split(instr, 1) # TODO: process trailers
#                self._handle_input(rest) # pipelining
        else: # don't have full headers yet
            self._input_buffer = instr

    def _handle_counted(self, instr):
        "Handle input where the body is delimited by the Content-Length."
        assert self._input_body_left >= 0, \
            "message counting problem (%s)" % self._input_body_left
        # process body
        if self._input_body_left <= len(instr): # got it all (and more?)
            self.input_transfer_length += self._input_body_left
            self._input_body(instr[:self._input_body_left])
            self._input_state = WAITING
            if instr[self._input_body_left:]:
                # This will catch extra input that isn't on packet boundaries.
                self._input_error(ERR_EXTRA_DATA,
                                  instr[self._input_body_left:])
            else:
                self._input_end()
        else: # got some of it
            self._input_body(instr)
            self.input_transfer_length += len(instr)
            self._input_body_left -= len(instr)

    def _parse_headers(self, instr):
        """
        Given a string that we knows contains a header block (possibly more), 
        parse the headers out and return the rest. Calls self._input_start
        to kick off processing.
        """
        top, rest = hdr_end.split(instr, 1)
        self.input_header_length = len(top)
        hdr_lines = lws.sub(" ", top).splitlines()   # Fold LWS
        try:
            top_line = hdr_lines.pop(0)
        except IndexError: # empty
            return ""
        hdr_tuples = []
        conn_tokens = []
        transfer_codes = []
        content_length = None
        for line in hdr_lines:
            try:
                fn, fv = line.split(":", 1)
                hdr_tuples.append((fn, fv))
            except ValueError:
                continue # TODO: flesh out bad header handling
            f_name = fn.strip().lower()
            f_val = fv.strip()

            # parse connection-related headers
            if f_name == "connection":
                conn_tokens += [v.strip().lower() for v in f_val.split(',')]
            elif f_name == "transfer-encoding": # FIXME: parameters
                transfer_codes += [v.strip().lower() for \
                                   v in f_val.split(',')]
            elif f_name == "content-length":
                if content_length != None:
                    continue # ignore any C-L past the first. 
                try:
                    content_length = int(f_val)
                except ValueError:
                    continue

        # FIXME: WSP between name and colon; request = 400, response = discard
        # TODO: remove *and* ignore conn tokens if the message was 1.0 

        # ignore content-length if transfer-encoding is present
        if transfer_codes != [] and content_length != None:
            content_length = None 

        try:
            allows_body = self._input_start(top_line, hdr_tuples, 
                        conn_tokens, transfer_codes, content_length)
        except ValueError: # parsing error of some kind; abort.
            return ""
                                
        self._input_state = HEADERS_DONE
        if not allows_body:
            self._input_delimit = NOBODY
        elif len(transfer_codes) > 0:
            if 'chunked' in transfer_codes:
                self._input_delimit = CHUNKED
                self._input_body_left = -1 # flag that we don't know
            else:
                self._input_delimit = CLOSE
        elif content_length != None:
            self._input_delimit = COUNTED
            self._input_body_left = content_length
        else: 
            self._input_delimit = CLOSE
        return rest

    ### output-related methods

    def _output(self, out):
        raise NotImplementedError

    def _handle_error(self, err):
        raise NotImplementedError

    def _output_start(self, top_line, hdr_tuples, delimit):
        """
        Start ouputting a HTTP message.
        """
        self._output_delimit = delimit
        # TODO: strip whitespace?
        out = linesep.join(
                [top_line] +
                ["%s: %s" % (k, v) for k, v in hdr_tuples] +
                ["", ""]
        )
        self._output(out)
        self._output_state = HEADERS_DONE

    def _output_body(self, chunk):
        """
        Output a part of a HTTP message.
        """
        if not chunk:
            return
        if self._output_delimit == CHUNKED:
            chunk = "%s\r\n%s\r\n" % (hex(len(chunk))[2:], chunk)
        self._output(chunk)
        #FIXME: body counting
#        self._output_body_sent += len(chunk)
#        assert self._output_body_sent <= self._output_content_length, \
#            "Too many body bytes sent"

    def _output_end(self, err):
        """
        Finish outputting a HTTP message.
        """
        if err:
            self.output_body_cb, self.output_done_cb = dummy, dummy
            self._tcp_conn.close()
            self._tcp_conn = None
        elif self._output_delimit == NOBODY:
            pass # didn't have a body at all.
        elif self._output_delimit == CHUNKED:
            self._output("0\r\n\r\n")
        elif self._output_delimit == COUNTED:
            pass # TODO: double-check the length
        elif self._output_delimit == CLOSE:
            self._tcp_conn.close() # FIXME: abstract out?
        else:
            raise AssertionError, "Unknown request delimiter %s" % \
                                  self._output_delimit
        self._output_state = WAITING

########NEW FILE########
__FILENAME__ = push_tcp
#!/usr/bin/env python

"""
push-based asynchronous TCP

This is a generic library for building event-based / asynchronous
TCP servers and clients. 

By default, it uses the asyncore library included with Python. 
However, if the pyevent library 
<http://www.monkey.org/~dugsong/pyevent/> is available, it will 
use that, offering higher concurrency and, perhaps, performance.

It uses a push model; i.e., the network connection pushes data to
you (using a callback), and you push data to the network connection
(using a direct method invocation). 

*** Building Clients

To connect to a server, use create_client;
> host = 'www.example.com'
> port = '80'
> push_tcp.create_client(host, port, conn_handler, error_handler)

conn_handler will be called with the tcp_conn as the argument 
when the connection is made. See "Working with Connections" 
below for details.

error_handler will be called if the connection can't be made for some reason.

> def error_handler(host, port, reason):
>   print "can't connect to %s:%s: %s" % (host, port, reason)

*** Building Servers

To start listening, use create_server;

> server = push_tcp.create_server(host, port, conn_handler)

conn_handler is called every time a new client connects; see
"Working with Connections" below for details.

The server object itself keeps track of all of the open connections, and
can be used to do things like idle connection management, etc.

*** Working with Connections

Every time a new connection is established -- whether as a client
or as a server -- the conn_handler given is called with tcp_conn
as its argument;

> def conn_handler(tcp_conn):
>   print "connected to %s:%s" % tcp_conn.host, tcp_conn.port
>   return read_cb, close_cb, pause_cb

It must return a (read_cb, close_cb, pause_cb) tuple.

read_cb will be called every time incoming data is available from
the connection;

> def read_cb(data):
>   print "got some data:", data

When you want to write to the connection, just write to it:

> tcp_conn.write(data)

If you want to close the connection from your side, just call close:

> tcp_conn.close()

Note that this will flush any data already written.

If the other side closes the connection, close_cb will be called;

> def close_cb():
>   print "oops, they don't like us any more..."

If you write too much data to the connection and the buffers fill up, 
pause_cb will be called with True to tell you to stop sending data 
temporarily;

> def pause_cb(paused):
>   if paused:
>       # stop sending data
>   else:
>       # it's OK to start again

Note that this is advisory; if you ignore it, the data will still be
buffered, but the buffer will grow.

Likewise, if you want to pause the connection because your buffers 
are full, call pause;

> tcp_conn.pause(True)

but don't forget to tell it when it's OK to send data again;

> tcp_conn.pause(False)

*** Timed Events

It's often useful to schedule an event to be run some time in the future;

> push_tcp.schedule(10, cb, "foo")

This example will schedule the function 'cb' to be called with the argument
"foo" ten seconds in the future.

*** Running the loop

In all cases (clients, servers, and timed events), you'll need to start
the event loop before anything actually happens;

> push_tcp.run()

To stop it, just stop it;

> push_tcp.stop()
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2010 Mark Nottingham

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
"""

import asyncore
import bisect
import errno
import os
import sys
import socket
import time

try:
    import event      # http://www.monkey.org/~dugsong/pyevent/
except ImportError:
    event = None

class _TcpConnection(asyncore.dispatcher):
    "Base class for a TCP connection."
    write_bufsize = 16
    read_bufsize = 1024 * 16
    def __init__(self, sock, host, port):
        self.socket = sock
        self.host = host
        self.port = port
        self.read_cb = None
        self.close_cb = None
        self._close_cb_called = False
        self.pause_cb = None  
        self.tcp_connected = True # we assume a connected socket
        self._paused = False # TODO: should be paused by default
        self._closing = False
        self._write_buffer = []
        if event:
            self._revent = event.read(sock, self.handle_read)
            self._wevent = event.write(sock, self.handle_write)
        else: # asyncore
            asyncore.dispatcher.__init__(self, sock)

    def __repr__(self):
        status = [self.__class__.__module__+"."+self.__class__.__name__]
        if self.tcp_connected:
            status.append('connected')
        status.append('%s:%s' % (self.host, self.port))
        if event:
            status.append('event-based')
        if self._paused:
            status.append('paused')
        if self._closing:
            status.append('closing')
        if self._close_cb_called:
            status.append('close cb called')
        if self._write_buffer:
            status.append('%s write buffered' % len(self._write_buffer))
        return "<%s at %#x>" % (", ".join(status), id(self))

    def handle_connect(self): # asyncore
        pass
        
    def handle_read(self):
        """
        The connection has data read for reading; call read_cb
        if appropriate.
        """
        try:
            data = self.socket.recv(self.read_bufsize)
        except socket.error, why:
            if why[0] in [errno.EBADF, errno.ECONNRESET, errno.ESHUTDOWN, 
                          errno.ECONNABORTED, errno.ECONNREFUSED, 
                          errno.ENOTCONN, errno.EPIPE]:
                self.conn_closed()
                return
            else:
                raise
        if data == "":
            self.conn_closed()
        else:
            self.read_cb(data)
            if event:
                if self.read_cb and self.tcp_connected and not self._paused:
                    return self._revent
        
    def handle_write(self):
        "The connection is ready for writing; write any buffered data."
        if len(self._write_buffer) > 0:
            data = "".join(self._write_buffer)
            try:
                sent = self.socket.send(data)
            except socket.error, why:
                if why[0] == errno.EWOULDBLOCK:
                    return
                elif why[0] in [errno.EBADF, errno.ECONNRESET, 
                                errno.ESHUTDOWN, errno.ECONNABORTED,
                                errno.ECONNREFUSED, errno.ENOTCONN, 
                                errno.EPIPE]:
                    self.conn_closed()
                    return
                else:
                    raise
            if sent < len(data):
                self._write_buffer = [data[sent:]]
            else:
                self._write_buffer = []
        if self.pause_cb and len(self._write_buffer) < self.write_bufsize:
            self.pause_cb(False)
        if self._closing:
            self.close()
        if event:
            if self.tcp_connected \
            and (len(self._write_buffer) > 0 or self._closing):
                return self._wevent

    def conn_closed(self):
        """
        The connection has been closed by the other side. Do local cleanup
        and then call close_cb.
        """
        self.tcp_connected = False
        if self._close_cb_called:
            return
        elif self.close_cb:
            self._close_cb_called = True
            self.close_cb()
        else:
            # uncomfortable race condition here, so we try again.
            # not great, but ok for now. 
            schedule(1, self.conn_closed)
    handle_close = conn_closed # for asyncore

    def write(self, data):
        "Write data to the connection."
#        assert not self._paused
        self._write_buffer.append(data)
        if self.pause_cb and len(self._write_buffer) > self.write_bufsize:
            self.pause_cb(True)
        if event:
            if not self._wevent.pending():
                self._wevent.add()

    def pause(self, paused):
        """
        Temporarily stop/start reading from the connection and pushing
        it to the app.
        """
        if event:
            if paused:
                if self._revent.pending():
                    self._revent.delete()
            else:
                if not self._revent.pending():
                    self._revent.add()
        self._paused = paused

    def close(self):
        "Flush buffered data (if any) and close the connection."
        self.pause(True)
        if len(self._write_buffer) > 0:
            self._closing = True
        else:
            self.tcp_connected = False
            if event:
                if self._revent.pending():
                    self._revent.delete()
                if self._wevent.pending():
                    self._wevent.delete()
                self.socket.close()
            else:
                asyncore.dispatcher.close(self)

    def readable(self):
        "asyncore-specific readable method"
        return self.read_cb and self.tcp_connected and not self._paused
    
    def writable(self):
        "asyncore-specific writable method"
        return self.tcp_connected and \
            (len(self._write_buffer) > 0 or self._closing)

    def handle_error(self):
        """
        asyncore-specific misc error method.
        """
        raise


def create_server(host, port, conn_handler):
    """Listen to host:port and send connections to conn_handler."""
    sock = server_listen(host, port)
    attach_server(host, port, sock, conn_handler)

def server_listen(host, port):
    "Return a socket listening to host:port."
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(socket.SOMAXCONN)
    return sock
    
class attach_server(asyncore.dispatcher):
    "Attach a server to a listening socket."
    def __init__(self, host, port, sock, conn_handler):
        self.host = host
        self.port = port
        self.conn_handler = conn_handler
        if event:
            event.event(self.handle_accept, handle=sock,
                        evtype=event.EV_READ|event.EV_PERSIST).add()
        else: # asyncore
            asyncore.dispatcher.__init__(self, sock=sock)
            self.accepting = True

    def handle_accept(self, *args):
        try:
            if event:
                conn, addr = args[1].accept()
            else: # asyncore
                conn, addr = self.accept()
        except TypeError: 
            # sometimes accept() returns None if we have 
            # multiple processes listening
            return
        tcp_conn = _TcpConnection(conn, self.host, self.port)
        tcp_conn.read_cb, tcp_conn.close_cb, tcp_conn.pause_cb = \
            self.conn_handler(tcp_conn)

    def handle_error(self):
        stop() # FIXME: handle unscheduled errors more gracefully
        raise

class create_client(asyncore.dispatcher):
    "An asynchronous TCP client."
    def __init__(self, host, port, conn_handler, 
        connect_error_handler, connect_timeout=None):
        self.host = host
        self.port = port
        self.conn_handler = conn_handler
        self.connect_error_handler = connect_error_handler
        self._timeout_ev = None
        self._error_sent = False
        # TODO: socket.getaddrinfo(); needs to be non-blocking.
        if event:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(0)
            event.write(sock, self.handle_connect, sock).add()
            try:
                # FIXME: check for DNS errors, etc.
                err = sock.connect_ex((host, port))
            except socket.error, why:
                self.handle_conn_error()
                return
            except socket.gaierror, why:
                self.handle_conn_error()
                return
            if err != errno.EINPROGRESS: # FIXME: others?
                self.handle_conn_error((err, os.strerror(err)))
                return
        else: # asyncore
            asyncore.dispatcher.__init__(self)
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.connect((host, port)) 
                # exceptions should be caught by handle_error
            except socket.error, why:
                self.handle_conn_error()
                return
            except socket.gaierror, why:
                self.handle_conn_error()
                return
        if connect_timeout:
            self._timeout_ev = schedule(connect_timeout,
                            self.connect_error_handler, 
                            (errno.ETIMEDOUT, os.strerror(errno.ETIMEDOUT))
            )

    def handle_connect(self, sock=None):
        if self._timeout_ev:
            self._timeout_ev.delete()
        if self._error_sent:
            return
        if sock is None: # asyncore
            sock = self.socket
        tcp_conn = _TcpConnection(sock, self.host, self.port)
        tcp_conn.read_cb, tcp_conn.close_cb, tcp_conn.pause_cb = \
            self.conn_handler(tcp_conn)

    def handle_read(self): # asyncore
        pass

    def handle_write(self): # asyncore
        pass

    def handle_conn_error(self, ex_value=None):
        if ex_value is None:
            ex_type, ex_value = sys.exc_info()[:2]
        else:
            ex_type = socket.error
        if ex_type in [socket.error, socket.gaierror]:
            if ex_value[0] == errno.ECONNREFUSED:
                return # OS will retry
            if self._timeout_ev:
                self._timeout_ev.delete()
            if self._error_sent:
                return
            elif self.connect_error_handler:
                self._error_sent = True
                self.connect_error_handler(ex_value)
        else:
            if self._timeout_ev:
                self._timeout_ev.delete()
            raise
    
    def handle_error(self):
        stop() # FIXME: handle unscheduled errors more gracefully
        raise


# adapted from Medusa
class _AsyncoreLoop:
    "Asyncore main loop + event scheduling."
    def __init__(self):
        self.events = []
        self.num_channels = 0
        self.max_channels = 0
        self.timeout = 1
        self.granularity = 1
        self.socket_map = asyncore.socket_map
        self._now = None
        self._running = False

    def run(self):
        "Start the loop."
        last_event_check = 0
        self._running = True
        while (self.socket_map or self.events) and self._running:
            self._now = time.time()
            if (self._now - last_event_check) >= self.granularity:
                last_event_check = self._now
                for event in self.events:
                    when, what = event
                    if self._now >= when:
                        try:
                            self.events.remove(event)
                        except ValueError: 
                            # a previous event may have removed this one.
                            continue
                        what()
                    else:
                        break
            # sample the number of channels
            n = len(self.socket_map)
            self.num_channels = n
            if n > self.max_channels:
                self.max_channels = n
            asyncore.poll(self.timeout) # TODO: use poll2 when available
            
    def stop(self):
        "Stop the loop."
        self.socket_map.clear()
        self.events = []
        self._now = None
        self._running = False
            
    def time(self):
        "Return the current time (to avoid a system call)."
        return self._now or time.time()

    def schedule(self, delta, callback, *args):
        "Schedule callable callback to be run in delta seconds with *args."
        def cb():
            if callback:
                callback(*args)
        new_event = (self.time() + delta, cb)
        events = self.events
        bisect.insort(events, new_event)
        class event_holder:
            def __init__(self):
                self._deleted = False
            def delete(self):
                if not self._deleted:
                    try:
                        events.remove(new_event)
                        self._deleted = True
                    except ValueError: # already gone
                        pass
        return event_holder()

_event_running = False
def _event_run(*args):
    _event_running = True
    event.dispatch(*args)

def _event_stop(*args):
    _event_running = False
    event.abort(*args)

if event:
    schedule = event.timeout
    run = _event_run
    stop =  _event_stop
    now = time.time
    running = _event_running
else:
    _loop = _AsyncoreLoop()
    schedule = _loop.schedule
    run = _loop.run
    stop = _loop.stop
    now = _loop.time
    running = _loop._running

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python

"""
Non-Blocking HTTP Server

This library allow implementation of an HTTP/1.1 server that is
"non-blocking," "asynchronous" and "event-driven" -- i.e., it achieves very
high performance and concurrency, so long as the application code does not
block (e.g., upon network, disk or database access). Blocking on one request
will block the entire server.

Instantiate a Server with the following parameters:
  - host (string)
  - port (int)
  - req_start (callable)
  
req_start is called when a request starts. It must take the following
arguments:
  - method (string)
  - uri (string)
  - req_hdrs (list of (name, value) tuples)
  - res_start (callable)
  - req_body_pause (callable)
and return:
  - req_body (callable)
  - req_done (callable)
    
req_body is called when part of the request body is available. It must take
the following argument:
  - chunk (string)

req_done is called when the request is complete, whether or not it contains a 
body. It must take the following argument:
  - err (error dictionary, or None for no error)

Call req_body_pause when you want the server to temporarily stop sending the 
request body, or restart. You must provide the following argument:
  - paused (boolean; True means pause, False means unpause)
    
Call res_start when you want to start the response, and provide the following 
arguments:
  - status_code (string)
  - status_phrase (string)
  - res_hdrs (list of (name, value) tuples)
  - res_body_pause
It returns:
  - res_body (callable)
  - res_done (callable)
    
Call res_body to send part of the response body to the client. Provide the 
following parameter:
  - chunk (string)
  
Call res_done when the response is finished, and provide the 
following argument if appropriate:
  - err (error dictionary, or None for no error)
    
See the error module for the complete list of valid error dictionaries.

Where possible, errors in the request will be responded to with the
appropriate 4xx HTTP status code. However, if a response has already been
started, the connection will be dropped (for example, when the request
chunking or indicated length are incorrect).
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2010 Mark Nottingham

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
"""

import os
import sys
import logging

import push_tcp
from http_common import HttpMessageHandler, \
    CLOSE, COUNTED, CHUNKED, \
    WAITING, \
    hop_by_hop_hdrs, \
    dummy, get_hdr

from error import ERR_HTTP_VERSION, ERR_HOST_REQ, \
    ERR_WHITESPACE_HDR, ERR_TRANSFER_CODE

logging.basicConfig()
log = logging.getLogger('server')
log.setLevel(logging.WARNING)

# FIXME: assure that the connection isn't closed before reading the entire 
#        req body
# TODO: filter out 100 responses to HTTP/1.0 clients that didn't ask for it.

class Server:
    "An asynchronous HTTP server."
    def __init__(self, host, port, request_handler):
        self.request_handler = request_handler
        push_tcp.create_server(host, port, self.handle_connection)
        
    def handle_connection(self, tcp_conn):
        "Process a new push_tcp connection, tcp_conn."
        conn = HttpServerConnection(self.request_handler, tcp_conn)
        return conn._handle_input, conn._conn_closed, conn._res_body_pause


class HttpServerConnection(HttpMessageHandler):
    "A handler for an HTTP server connection."
    def __init__(self, request_handler, tcp_conn):
        HttpMessageHandler.__init__(self)
        self.request_handler = request_handler
        self._tcp_conn = tcp_conn
        self.req_body_cb = None
        self.req_done_cb = None
        self.method = None
        self.req_version = None
        self.connection_hdr = []
        self._res_body_pause_cb = None

    def res_start(self, status_code, status_phrase, res_hdrs, res_body_pause):
        "Start a response. Must only be called once per response."
        self._res_body_pause_cb = res_body_pause
        res_hdrs = [i for i in res_hdrs \
                    if not i[0].lower() in hop_by_hop_hdrs ]

        try:
            body_len = int(get_hdr(res_hdrs, "content-length").pop(0))
        except (IndexError, ValueError):
            body_len = None
        if body_len is not None:
            delimit = COUNTED
            res_hdrs.append(("Connection", "keep-alive"))
        elif 2.0 > self.req_version >= 1.1:
            delimit = CHUNKED
            res_hdrs.append(("Transfer-Encoding", "chunked"))
        else:
            delimit = CLOSE
            res_hdrs.append(("Connection", "close"))

        self._output_start("HTTP/1.1 %s %s" % (status_code, status_phrase),
            res_hdrs, delimit
        )
        return self.res_body, self.res_done

    def res_body(self, chunk):
        "Send part of the response body. May be called zero to many times."
        self._output_body(chunk)

    def res_done(self, err=None):
        """
        Signal the end of the response, whether or not there was a body. MUST
        be called exactly once for each response.
        
        If err is not None, it is an error dictionary (see the error module)
        indicating that an HTTP-specific (i.e., non-application) error occured
        in the generation of the response; this is useful for debugging.
        """
        self._output_end(err)

    def req_body_pause(self, paused):
        """
        Indicate that the server should pause (True) or unpause (False) the
        request.
        """
        if self._tcp_conn and self._tcp_conn.tcp_connected:
            self._tcp_conn.pause(paused)

    # Methods called by push_tcp

    def _res_body_pause(self, paused):
        "Pause/unpause sending the response body."
        if self._res_body_pause_cb:
            self._res_body_pause_cb(paused)

    def _conn_closed(self):
        "The server connection has closed."
        if self._output_state != WAITING:
            pass # FIXME: any cleanup necessary?
#        self.pause()
#        self._queue = []
#        self.tcp_conn.handler = None
#        self.tcp_conn = None

    # Methods called by common.HttpRequestHandler

    def _output(self, chunk):
        self._tcp_conn.write(chunk)

    def _input_start(self, top_line, hdr_tuples, conn_tokens, 
        transfer_codes, content_length):
        """
        Take the top set of headers from the input stream, parse them
        and queue the request to be processed by the application.
        """
        assert self._input_state == WAITING, "pipelining not supported" 
        # FIXME: pipelining
        try: 
            method, _req_line = top_line.split(None, 1)
            uri, req_version = _req_line.rsplit(None, 1)
            self.req_version = float(req_version.rsplit('/', 1)[1])
        except (ValueError, IndexError):
            self._handle_error(ERR_HTTP_VERSION, top_line) 
            # FIXME: more fine-grained
            raise ValueError
        if self.req_version == 1.1 \
        and 'host' not in [t[0].lower() for t in hdr_tuples]:
            self._handle_error(ERR_HOST_REQ)
            raise ValueError
        if hdr_tuples[:1][:1][:1] in [" ", "\t"]:
            self._handle_error(ERR_WHITESPACE_HDR)
        for code in transfer_codes: 
            # we only support 'identity' and chunked' codes
            if code not in ['identity', 'chunked']: 
                # FIXME: SHOULD also close connection
                self._handle_error(ERR_TRANSFER_CODE)
                raise ValueError
        # FIXME: MUST 400 request messages with whitespace between 
        #        name and colon
        self.method = method
        self.connection_hdr = conn_tokens

        log.info("%s server req_start %s %s %s" % (
            id(self), method, uri, self.req_version)
        )
        self.req_body_cb, self.req_done_cb = self.request_handler(
                method, uri, hdr_tuples, self.res_start, self.req_body_pause)
        allows_body = (content_length) or (transfer_codes != [])
        return allows_body

    def _input_body(self, chunk):
        "Process a request body chunk from the wire."
        self.req_body_cb(chunk)
    
    def _input_end(self):
        "Indicate that the request body is complete."
        self.req_done_cb(None)

    def _input_error(self, err, detail=None):
        "Indicate a parsing problem with the request body."
        err['detail'] = detail
        if self._tcp_conn:
            self._tcp_conn.close()
            self._tcp_conn = None
        self.req_done_cb(err)

    def _handle_error(self, err, detail=None):
        """
        Handle a problem with the request by generating an appropriate
        response.
        """
#   self._queue.append(ErrorHandler(status_code, status_phrase, body, self))
        assert self._output_state == WAITING
        if detail:
            err['detail'] = detail
        status_code, status_phrase = err.get('status', ('400', 'Bad Request'))
        hdrs = [
            ('Content-Type', 'text/plain'),
        ]
        body = err['desc']
        if err.has_key('detail'):
            body += " (%s)" % err['detail']
        self.res_start(status_code, status_phrase, hdrs, dummy)
        self.res_body(body)
        self.res_done()

    
def test_handler(method, uri, hdrs, res_start, req_pause):
    """
    An extremely simple (and limited) server request_handler.
    """
    code = "200"
    phrase = "OK"
    res_hdrs = [('Content-Type', 'text/plain')]
    res_body, res_done = res_start(code, phrase, res_hdrs, dummy)
    res_body('foo!')
    res_done(None)
    return dummy, dummy
    
if __name__ == "__main__":
    sys.stderr.write("PID: %s\n" % os.getpid())
    h, p = '127.0.0.1', int(sys.argv[1])
    server = Server(h, p, test_handler)
    push_tcp.run()

########NEW FILE########
