__FILENAME__ = ascii_with_complaints
"""
'ascii' codec, plus warnings. Suitable for use as the default encoding in
`site.py`.
Copyright Allen Short, 2010.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


Based on ASCII codec from Python 2.7, made available under the Python license
(http://docs.python.org/license.html):

 Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010
Python Software Foundation; All Rights Reserved

 Python 'ascii' Codec


Written by Marc-Andre Lemburg (mal@lemburg.com).

(c) Copyright CNRI, All Rights Reserved. NO WARRANTY.

"""
import codecs, warnings

def encode(input, errors='strict'):
    warnings.warn("Implicit conversion of unicode to str", UnicodeWarning, 2)
    return codecs.ascii_encode(input, errors)


def decode(input, errors='strict'):
    warnings.warn("Implicit conversion of str to unicode", UnicodeWarning, 2)
    return codecs.ascii_decode(input, errors)



class Codec(codecs.Codec):

    def encode(self, input,errors='strict'):
        return encode(input,errors)
    def decode(self, input,errors='strict'):
        return decode(input,errors)


class IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, input, final=False):
        return encode(input, self.errors)[0]

class IncrementalDecoder(codecs.IncrementalDecoder):
    def decode(self, input, final=False):
        return decode(input, self.errors)[0]

class StreamWriter(Codec,codecs.StreamWriter):
    pass

class StreamReader(Codec,codecs.StreamReader):
    pass


### encodings module API

def getregentry():
    return codecs.CodecInfo(
        name='ascii_with_complaints',
        encode=encode,
        decode=decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamwriter=StreamWriter,
        streamreader=StreamReader,
    )

def search_function(encoding):
    if encoding == 'ascii_with_complaints':
        return getregentry()

codecs.register(search_function)

########NEW FILE########
__FILENAME__ = framework
#!/usr/bin/env python

"""
Framework for testing clients and servers, moving one of them into 
a separate thread.
"""

import os
import sys
import threading
import unittest

import thor
from thor.http.common import HttpMessageHandler

test_host = "127.0.0.1"
test_port = 8001


class ClientServerTestCase(unittest.TestCase):
    
    def setUp(self):
        self.loop = thor.loop.make()
        self.timeout_hit = False

    def tearDown(self):
        if self.loop.running:
            sys.stdout.write("WARNING: loop still running at end of test.")
            self.loop.stop()

    def move_to_thread(self, target, args=None):
        t = threading.Thread(target=target, args=args or [])
        t.setDaemon(True)
        t.start()
            
    def go(self, server_sides, client_sides, timeout=5):
        """
        Start the server(s), handling connections with server_side (handler),
        and then run the client(s), calling client_side (client).
        
        One of the handlers MUST stop the loop before the timeout, which
        is considered failure.
        """

        for server_side in server_sides:
            offset = 0
            if hasattr(server_side, "port_offset"):
                offset = server_side.port_offset
            self.create_server(test_host, test_port + offset, server_side)
        
        for client_side in client_sides:
            self.create_client(test_host, test_port, client_side)
            
        def do_timeout():
            self.loop.stop()
            self.timeout_hit = True
        self.loop.schedule(timeout, do_timeout)
        self.loop.run()
        self.assertEqual(self.timeout_hit, False)

    def create_server(self, host, port, server_side):
        raise NotImplementedError
        
    def create_client(self, host, port, client_side):
        raise NotImplementedError
        

class DummyHttpParser(HttpMessageHandler):
    def __init__(self, *args, **kw):
        HttpMessageHandler.__init__(self, *args, **kw)
        self.test_top_line = None
        self.test_hdrs = None
        self.test_body = ""
        self.test_trailers = None
        self.test_err = None
        self.test_states = []
    
    def input_start(self, top_line, hdr_tuples, conn_tokens, 
                     transfer_codes, content_length):
        self.test_states.append("START")
        self.test_top_line = top_line
        self.test_hdrs = hdr_tuples
        return bool
        
    def input_body(self, chunk):
        self.test_states.append("BODY")
        self.test_body += chunk

    def input_end(self, trailers):
        self.test_states.append("END")
        self.test_trailers = trailers

    def input_error(self, err):
        self.test_states.append("ERROR")
        self.test_err = err
        return False # never recover.
        
    def check(self, asserter, expected):
        """
        Check the parsed message against expected attributes and 
        assert using asserter as necessary.
        """
        aE = asserter.assertEqual
        aE(expected.get('top_line', self.test_top_line), self.test_top_line)
        aE(expected.get('hdrs', self.test_hdrs), self.test_hdrs)
        aE(expected.get('body', self.test_body), self.test_body)
        aE(expected.get('trailers', self.test_trailers), self.test_trailers)
        aE(expected.get('error', self.test_err), self.test_err)
        aE(expected.get('states', self.test_states), self.test_states)


def make_fifo(filename):
    try:
        os.unlink(filename)
    except OSError:
        pass # wasn't there
    try:
        os.mkfifo(filename)
    except OSError, e:
        print "Failed to create FIFO: %s" % e
    else:
        r = os.open(filename, os.O_RDONLY|os.O_NONBLOCK)
        w = os.open(filename, os.O_WRONLY|os.O_NONBLOCK)
        return r, w

########NEW FILE########
__FILENAME__ = sitecustomize
#!/usr/bin/env python

import ascii_with_complaints
import sys

sys.setdefaultencoding('ascii_with_complaints')
########NEW FILE########
__FILENAME__ = test_events
#!/usr/bin/env python

import sys
import unittest

from thor.events import EventEmitter, on

class TestEventEmitter(unittest.TestCase):
    def setUp(self):
        class Thing(EventEmitter):
            def __init__(self):
                EventEmitter.__init__(self)
                self.foo_count = 0
                self.bar_count = 0
                self.rem1_count = 0
                self.rem2_count = 0
                self.on('foo', self.handle_foo)
                self.once('bar', self.handle_bar)
                self.on('baz', self.handle_baz)
                self.on('rem1', self.handle_rem1)
                self.on('rem1', self.handle_rem1a)
                self.on('rem2', self.handle_rem2)
                self.on('rem2', self.handle_rem2a)
            
            def handle_foo(self):
                self.foo_count += 1
            
            def handle_bar(self):
                self.bar_count += 1
            
            def handle_baz(self):
                raise Exception, "Baz wasn't removed."
                
            def handle_rem1(self):
                self.rem1_count += 1
                self.removeListeners()
                self.emit('foo')
                
            def handle_rem1a(self):
                self.rem1_count += 1
                
            def handle_rem2(self):
                self.rem2_count += 1
                self.removeListener('rem2', self.handle_rem2a)
            
            def handle_rem2a(self):
                self.rem2_count += 1
                
        self.t = Thing()

    def test_basic(self):
        self.assertEquals(self.t.foo_count, 0)
        self.t.emit('foo')
        self.assertEquals(self.t.foo_count, 1)
        self.t.emit('foo')
        self.assertEquals(self.t.foo_count, 2)

    def test_once(self):
        self.assertEquals(self.t.bar_count, 0)
        self.t.emit('bar')
        self.assertEquals(self.t.bar_count, 1)
        self.t.emit('bar')
        self.assertEquals(self.t.bar_count, 1)

    def test_removeListener(self):
        self.t.removeListener('foo', self.t.handle_foo)
        self.t.emit('foo')
        self.assertEquals(self.t.foo_count, 0)

    def test_removeListeners_named(self):
        self.t.removeListeners('baz')
        self.t.emit('baz')

    def test_removeListeners_named_multiple(self):
        self.t.removeListeners('baz', 'foo')
        self.t.emit('baz')
        self.t.emit('foo')
        self.assertEquals(self.t.foo_count, 0)
        
    def test_removeListeners_all(self):
        self.t.emit('foo')
        self.t.removeListeners()
        self.t.emit('foo')
        self.assertEquals(self.t.foo_count, 1)
        self.t.emit('baz')

    def test_sink(self):
        class TestSink(object):
            def __init__(self):
                self.bam_count = 0
            def bam(self):
                self.bam_count += 1
        s = TestSink()
        self.t.sink(s)
        self.assertEquals(s.bam_count, 0)
        self.t.emit('bam')
        self.assertEquals(s.bam_count, 1)
        self.assertEquals(self.t.foo_count, 0)
        self.t.emit('foo')
        self.assertEquals(self.t.foo_count, 1)
        
    def test_on_named(self):
        self.t.boom_count = 0
        @on(self.t, 'boom')
        def do():
            self.t.boom_count += 1
        self.assertEquals(self.t.boom_count, 0)
        self.t.emit('boom')
        self.assertEquals(self.t.boom_count, 1)

    def test_on_default(self):
        self.t.boom_count = 0
        @on(self.t)
        def boom():
            self.t.boom_count += 1
        self.assertEquals(self.t.boom_count, 0)
        self.t.emit('boom')
        self.assertEquals(self.t.boom_count, 1)


    def test_removeListeners_recursion(self):
        """
        All event listeners are called for a given
        event, even if one of the previous listeners
        calls removeListeners().
        """
        self.assertEquals(self.t.rem1_count, 0)
        self.t.emit('rem1')
        self.assertEquals(self.t.foo_count, 0)
        self.assertEquals(self.t.rem1_count, 2)
        
    def test_removeListener_recursion(self):
        """
        Removing a later listener specifically for 
        a given event causes it not to be run.
        """
        self.assertEquals(self.t.rem2_count, 0)
        self.t.emit('rem2')
        self.assertEquals(self.t.rem2_count, 1)
            
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_http_client
#!/usr/bin/env python

import SocketServer
import sys
import time
import unittest

import framework
from framework import test_host, test_port

import thor
from thor.events import on
from thor.http import HttpClient

thor.loop.debug = True
        
class LittleServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True


class TestHttpClient(framework.ClientServerTestCase):

    def create_server(self, test_host, test_port, server_side):
        class LittleRequestHandler(SocketServer.BaseRequestHandler):
            handle = server_side
        server = LittleServer(
            (framework.test_host, framework.test_port), 
            LittleRequestHandler
        )
        self.move_to_thread(target=server.serve_forever)

        @on(self.loop)
        def stop():
            server.shutdown()
            server.server_close()

    def create_client(self, host, port, client_side):
        client = HttpClient(loop=self.loop)
        client.connect_timeout = 1
        client_side(client)

    def check_exchange(self, exchange, expected):
        """
        Given an exchange, check that the status, phrase and body are as
        expected, and verify that it actually happened.
        """
        exchange.test_happened = False
        
        @on(exchange)
        def error(err_msg):
            exchange.test_happened = True
            self.assertEqual(err_msg, expected.get('error', err_msg))

        @on(exchange)
        def response_start(status, phrase, headers):
            self.assertEqual(
                exchange.res_version, 
                expected.get('version', exchange.res_version)
            )
            self.assertEqual(status, expected.get('status', status))
            self.assertEqual(phrase, expected.get('phrase', phrase))

        exchange.tmp_res_body = ""
        @on(exchange)
        def response_body(chunk):
            exchange.tmp_res_body += chunk

        @on(exchange)
        def response_done(trailers):
            exchange.test_happened = True
            self.assertEqual(
                exchange.tmp_res_body, 
                expected.get('body', exchange.tmp_res_body)
            )
            
        @on(self.loop)
        def stop():
            self.assertTrue(exchange.test_happened, expected)



    def test_basic(self):
        def client_side(client):
            exchange = client.exchange()
            self.check_exchange(exchange, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })
            
            @on(exchange)
            def response_done(trailers):
                self.loop.stop()

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange.request_start(
                "GET", req_uri, []
            )
            exchange.request_done([])
                
        def server_side(conn):
            conn.request.send("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 5
Connection: close

12345""")
            conn.request.close()
        self.go([server_side], [client_side])


    def test_chunked_response(self):
        def client_side(client):
            exchange = client.exchange()
            self.check_exchange(exchange, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })
            @on(exchange)
            def response_done(trailers):
                self.loop.stop()

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange.request_start(
                "GET", req_uri, []
            )
            exchange.request_done([])
                
        def server_side(conn):
            conn.request.send("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

5\r
12345\r
0\r
\r
""")
            conn.request.close()
        self.go([server_side], [client_side])


    def test_chunked_request(self):
        req_body = "54321"
        def client_side(client):
            exchange = client.exchange()
            self.check_exchange(exchange, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })
            @on(exchange)
            def response_done(trailers):
                self.loop.stop()

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange.request_start(
                "POST", req_uri, []
            )
            exchange.request_body(req_body)
            exchange.request_body(req_body)
            exchange.request_done([])
                
        def server_side(conn):
            conn.request.send("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

5\r
12345\r
0\r
\r
""")
            # TODO: check server-side recv
            conn.request.close()
        self.go([server_side], [client_side])


    def test_multiconn(self):
        self.test_req_count = 0
        def check_done(trailers):
            self.test_req_count += 1
            if self.test_req_count == 2:
                self.loop.stop()
        
        def client_side(client):
            exchange1 = client.exchange()
            self.check_exchange(exchange1, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })

            exchange1.on('response_done', check_done)
            exchange2 = client.exchange()
            self.check_exchange(exchange2, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })
            exchange2.on('response_done', check_done)

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange1.request_start(
                "GET", req_uri, []
            )
            exchange2.request_start(
                "GET", req_uri, []
            )
            exchange1.request_done([])
            exchange2.request_done([])                
                
        def server_side(conn):
            conn.request.send("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 5
Connection: close

12345""")
            time.sleep(1)
            conn.request.close()
        self.go([server_side], [client_side])

        
    def test_conn_refuse_err(self):
        def client_side(client):
            exchange = client.exchange()
            @on(exchange)
            def error(err_msg):
                self.assertEqual(
                    err_msg.__class__, thor.http.error.ConnectError
                )
                self.loop.stop()

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange.request_start(
                "GET", req_uri, []
            )
            exchange.request_done([])
        self.go([], [client_side])


    # FIXME: works because dns is currently blocking
    def test_conn_noname_err(self):
        client = HttpClient(loop=self.loop)
        exchange = client.exchange()
        @on(exchange)
        def error(err_msg):
            self.assertEqual(
                err_msg.__class__, thor.http.error.ConnectError
            )
            self.loop.stop()

        req_uri = "http://foo.bar/"
        exchange.request_start(
            "GET", req_uri, []
        )
        exchange.request_done([])

        
    def test_url_err(self):
        client = HttpClient(loop=self.loop)
        exchange = client.exchange()
        @on(exchange)
        def error(err_msg):
            self.assertEqual(
                err_msg.__class__, thor.http.error.UrlError
            )
            self.loop.stop()

        req_uri = "foo://%s:%s/" % (test_host, test_port)
        exchange.request_start(
            "GET", req_uri, []
        )
        exchange.request_done([])


    def test_url_port_err(self):
        client = HttpClient(loop=self.loop)
        exchange = client.exchange()
        @on(exchange)
        def error(err_msg):
            self.assertEqual(
                err_msg.__class__, thor.http.error.UrlError
            )
            self.loop.stop()

        req_uri = "http://%s:ABC123/" % (test_host)
        exchange.request_start(
            "GET", req_uri, []
        )
        exchange.request_done([])


    def test_http_version_err(self):
        def client_side(client):
            exchange = client.exchange()
            @on(exchange)
            def error(err_msg):
                self.assertEqual(
                    err_msg.__class__, thor.http.error.HttpVersionError
                )
                self.loop.stop()

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange.request_start(
                "GET", req_uri, []
            )
            exchange.request_done([])
                
        def server_side(conn):
            conn.request.send("""\
HTTP/2.5 200 OK
Content-Type: text/plain
Content-Length: 5
Connection: close

12345""")
            conn.request.close()
        self.go([server_side], [client_side])


    def test_http_protoname_err(self):
        def client_side(client):
            exchange = client.exchange()
            @on(exchange)
            def error(err_msg):
                self.assertEqual(
                    err_msg.__class__, thor.http.error.HttpVersionError
                )
                self.loop.stop()

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange.request_start(
                "GET", req_uri, []
            )
            exchange.request_done([])
                
        def server_side(conn):
            conn.request.send("""\
ICY/1.1 200 OK
Content-Type: text/plain
Content-Length: 5
Connection: close

12345""")
            conn.request.close()
        self.go([server_side], [client_side])

    def test_close_in_body(self):
        def client_side(client):
            exchange = client.exchange()
            self.check_exchange(exchange, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
            })
            
            @on(exchange)
            def error(err_msg):
                self.assertEqual(
                    err_msg.__class__, 
                    thor.http.error.ConnectError
                )
                self.loop.stop()

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange.request_start(
                "GET", req_uri, []
            )
            exchange.request_done([])
                
        def server_side(conn):
            conn.request.send("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 15
Connection: close

12345""")
            conn.request.close()
        self.go([server_side], [client_side])
        

    def test_conn_reuse(self):
        self.conn_checked = False
        def client_side(client):
            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange1 = client.exchange()
            self.check_exchange(exchange1, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })

            @on(exchange1)
            def response_start(*args):
                self.conn_id = id(exchange1.tcp_conn)

            @on(exchange1)
            def response_done(trailers):
                exchange2 = client.exchange()
                self.check_exchange(exchange2, {
                    'version': "1.1",
                    'status': "404",
                    'phrase': 'Not Found',
                    'body': "54321"
                })
                def start2():
                    exchange2.request_start("GET", req_uri, [])
                    exchange2.request_done([])
                self.loop.schedule(1, start2)

                @on(exchange2)
                def response_start(*args):
                    self.assertEqual(self.conn_id, id(exchange2.tcp_conn))
                    self.conn_checked = True

                @on(exchange2)
                def response_done(trailers):
                    self.loop.stop()

            exchange1.request_start("GET", req_uri, [])
            exchange1.request_done([])
                
        def server_side(conn):
            conn.request.sendall("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 5

12345""")
            time.sleep(2)
            conn.request.sendall("""\
HTTP/1.1 404 Not Found
Content-Type: text/plain
Content-Length: 5
Connection: close

54321""")
            conn.request.close()
        self.go([server_side], [client_side])
        self.assertTrue(self.conn_checked)


    def test_conn_succeed_then_err(self):
        self.conn_checked = False
        def client_side(client):
            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange1 = client.exchange()
            self.check_exchange(exchange1, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })
            exchange2 = client.exchange()

            @on(exchange1)
            def response_start(*args):
                self.conn_id = id(exchange1.tcp_conn)

            @on(exchange1)
            def response_done(trailers):
                def start2():
                    exchange2.request_start("GET", req_uri, [])
                    exchange2.request_done([])
                self.loop.schedule(1, start2)

            @on(exchange2)
            def error(err_msg):
                self.conn_checked = True
                self.assertEqual(
                    err_msg.__class__, thor.http.error.HttpVersionError
                )
                self.loop.stop()

            exchange1.request_start("GET", req_uri, [])
            exchange1.request_done([])
                
        def server_side(conn):
            conn.request.sendall("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 5

12345""")
            time.sleep(2)
            conn.request.sendall("""\
HTTP/9.1 404 Not Found
Content-Type: text/plain
Content-Length: 5
Connection: close

54321""")
            conn.request.close()
        self.go([server_side], [client_side])
        self.assertTrue(self.conn_checked)


    def test_HEAD(self):
        def client_side(client):
            exchange = client.exchange()
            self.check_exchange(exchange, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': ""
            })
            @on(exchange)
            def response_done(trailers):
                self.loop.stop()

            req_uri = "http://%s:%s/" % (test_host, test_port)
            exchange.request_start(
                "HEAD", req_uri, []
            )
            exchange.request_done([])
                
        def server_side(conn):
            conn.request.send("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 5
Connection: close

""")
            time.sleep(1)
            conn.request.close()
        self.go([server_side], [client_side])
        

    def test_req_retry(self):
        def client_side(client):
            exchange = client.exchange()
            self.check_exchange(exchange, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })
            @on(exchange)
            def response_done(trailers):
                self.loop.stop()

            req_uri = "http://%s:%s" % (test_host, test_port)
            exchange.request_start(
                "OPTIONS", req_uri, []
            )
            exchange.request_done([])
                
        self.conn_num = 0
        def server_side(conn):
            self.conn_num += 1
            if self.conn_num > 1:
                conn.request.send("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 5
Connection: close

12345""")
            conn.request.close()
        self.go([server_side], [client_side])   


    def test_req_retry_fail(self):
        def client_side(client):
            exchange = client.exchange()
            self.check_exchange(exchange, {
                'version': "1.1",
                'status': "200",
                'phrase': 'OK',
                'body': "12345"
            })
            
            @on(exchange)
            def error(err_msg):
                self.assertEqual(
                    err_msg.__class__, thor.http.error.ConnectError
                )
                self.loop.stop()
                
            req_uri = "http://%s:%s" % (test_host, test_port)
            exchange.request_start(
                "OPTIONS", req_uri, []
            )
            exchange.request_done([])
                
        self.conn_num = 0
        def server_side(conn):
            self.conn_num += 1
            if self.conn_num > 3:
                conn.request.send("""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 5
Connection: close

12345""")
            conn.request.close()
        self.go([server_side], [client_side])   


# TODO:
#    def test_req_body(self):
#    def test_req_body_dont_retry(self):
#    def test_req_body_close_on_err(self):
#    def test_pipeline(self):
#    def test_malformed_hdr(self):
#    def test_unexpected_res(self):
#    def test_pause(self):
#    def test_options_star(self):
#    def test_idle_timeout(self):
#    def test_idle_timeout_reuse(self):
#    def test_alternate_tcp_client(self):

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_http_parser
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest

from framework import DummyHttpParser

import thor.http.error as error


class TestHttpParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = DummyHttpParser()

    def checkSingleMsg(self, inputs, body, expected_err=None, close=False):
        """
        Check a single HTTP message. 
        """
        assert type(inputs) == type([])
        for chunk in inputs:
            self.parser.handle_input(chunk % {
                'body': body, 
                'body_len': len(body)
            })
        states = self.parser.test_states

        if not expected_err:
            self.assertTrue(states.count('START') == 1, states)
            self.assertTrue(states.index('START') < states.index('BODY'))
            if close:
                self.assertEqual(self.parser._input_delimit, "close")
            else:
                self.assertTrue(states.index('END') < states[-1])
            self.assertEqual(body, self.parser.test_body)
        else:
            self.assertTrue("ERROR" in states, states)
            self.assertEqual(self.parser.test_err.__class__, expected_err)

    def checkMultiMsg(self, inputs, body, count):
        """
        Check pipelined messages. Assumes the same body for each (for now).
        """
        for chunk in inputs:
            self.parser.handle_input(chunk % {
                'body': body, 
                'body_len': len(body)
            })
        states = self.parser.test_states
        self.parser.check(self, {'states': ['START', 'BODY', 'END'] * count})

    def test_hdrs(self):
        body = "12345678901234567890"
        self.checkSingleMsg(["""\
http/1.1 200 OK
Content-Type: text/plain
Foo: bar
Content-Length: %(body_len)s
Foo: baz, bam

%(body)s"""], body)
        self.parser.check(self, {
            'hdrs': [
                ('Content-Type', " text/plain"),
                ('Foo', " bar"),
                ('Content-Length', " %s" % len(body)),
                ('Foo', " baz, bam"),
            ]
        })

    def test_hdrs_nocolon(self):
        body = "12345678901234567890"
        self.checkSingleMsg(["""\
http/1.1 200 OK
Content-Type: text/plain
Foo bar
Content-Length: %(body_len)s

%(body)s"""], body)
        # FIXME: error?

    def test_hdr_case(self):
        body = "12345678901234567890"
        self.checkSingleMsg(["""\
http/1.1 200 OK
Content-Type: text/plain
content-LENGTH: %(body_len)s

%(body)s"""], body)

    def test_hdrs_whitespace_before_colon(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length : %(body_len)s

%(body)s"""], body, error.HeaderSpaceError)

    def test_hdrs_fold(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Foo: bar
     baz
Content-Length: %(body_len)s

%(body)s"""], body)
        foo_val = [v for k,v in self.parser.test_hdrs if k == 'Foo'][-1]
        self.assertEqual(foo_val, u" bar baz")
        headers = [k for k,v in self.parser.test_hdrs]
        self.assertEqual(headers, ['Content-Type', 'Foo', 'Content-Length'])

    def test_hdrs_noname(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
: bar
Content-Length: %(body_len)s

%(body)s"""], body)
        headers = [k for k,v in self.parser.test_hdrs]
        self.assertEqual(headers, ['Content-Type', '', 'Content-Length'])
        

    def test_hdrs_utf8(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg([u"""\
HTTP/1.1 200 OK
Content-Type: text/plain
Foo: ედუარდ შევარდნაძე
Content-Length: %(body_len)s

%(body)s""".encode('utf-8')], body)
        foo_val = [v for k,v in self.parser.test_hdrs if k == 'Foo'][-1]
        self.assertEqual(foo_val.decode('utf-8'), u" ედუარდ შევარდნაძე")

    def test_hdrs_null(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg([u"""\
HTTP/1.1 200 OK
Content-Type: text/plain
Foo: \0
Content-Length: %(body_len)s

%(body)s""".encode('utf-8')], body)
        foo_val = [v for k,v in self.parser.test_hdrs if k == 'Foo'][-1]
        self.assertEqual(foo_val, " \0")


    def test_cl_delimit_11(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: %(body_len)s

%(body)s"""], body)

    def test_cl_delimit_10(self):
        body = "abcdefghijklmnopqrstuvwxyz"
        self.checkSingleMsg(["""\
HTTP/1.0 200 OK
Content-Type: text/plain
Content-Length: %(body_len)s

%(body)s"""], body)

    def test_close_delimit(self):
        body = "abcdefghijklmnopqrstuvwxyz"
        self.checkSingleMsg(["""\
HTTP/1.0 200 OK
Content-Type: text/plain

%(body)s"""], body, close=True)

    def test_extra_line(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg(["""\
            
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: %(body_len)s

%(body)s"""], body)

    def test_extra_lines(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg(["""\

    

HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: %(body_len)s

%(body)s"""], body)

    def test_telnet_client(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg(list("""\

        

HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: %(body_len)s

%(body)s""" % {'body': body, 'body_len': len(body)}), body)


    def test_naughty_first_header(self):
        body = "lorum ipsum whatever goes after that."
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
    Content-Type: text/plain
Content-Length: %(body_len)s

%(body)s"""], body, error.TopLineSpaceError)

    def test_cl_header_case(self):
        body = "12345678901234567890"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
content-LENGTH: %(body_len)s

%(body)s"""], body)

    def test_chunk_delimit(self):
        body = "aaabbbcccdddeeefffggghhhiii"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

%(body_len)x\r
%(body)s\r
0\r
\r
"""], body)

    def test_chunk_exact(self):
        body = "aaabbbcccdddeeefffggghhhiii"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

""", """\
%(body_len)x\r
%(body)s\r
""", """\
0\r
\r
"""], body)

    def test_chunk_exact_offset(self):
        body = "aaabbbcccdddeeefffggghhhiii"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

""", """\
%(body_len)x\r
%(body)s""", """\r
0\r
\r
"""], body)
    def test_chunk_more(self):
        body = "1234567890"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

""", """\
%(body_len)x\r
%(body)s\r
%(body_len)x\r
%(body)s\r
0\r
\r
""" % {'body': body, 'body_len': len(body)}], body * 2)


    def test_transfer_case(self):
        body = "aaabbbcccdddeeefffggghhhiii"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: cHuNkEd

%(body_len)x\r
%(body)s\r
0\r
\r
"""], body)

    def test_big_chunk(self):
        body = "aaabbbcccdddeeefffggghhhiii" * 1000000
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

%(body_len)x\r
%(body)s\r
0\r
\r
"""], body)

    def test_small_chunks(self):
        num_chunks = 50000
        body = "a" * num_chunks
        inputs = ["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

"""]
        for i in range(num_chunks):
            inputs.append("""\
1\r
a\r
""")
        inputs.append("""\
0\r
\r
""")
        self.checkSingleMsg(inputs, body)

    def test_split_chunk(self):
        body = "abcdefg123456"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

%(body_len)x\r
abcdefg""",
"""\
123456\r
0\r
\r
"""], body)

    def test_split_chunk_length(self):
        body = "do re mi so fa la ti do"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

%(body_len)x""",
"""\
\r
%(body)s\r
0\r
\r
"""], body)

    def test_chunk_bad_syntax(self):
        body = "abc123def456ghi789"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

ZZZZ\r
%(body)s\r
0\r
\r
"""], body, error.ChunkError)

    def test_chunk_nonfinal(self):
        body = "abc123def456ghi789"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked, foo

%(body)s"""], body, close=True)

    def test_cl_dup(self):
        body = "abc123def456ghi789"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: %(body_len)s
Content-Length: %(body_len)s

%(body)s"""], body)

    def test_cl_conflict(self):
        body = "abc123def456ghi789"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 2
Content-Length: %(body_len)s

%(body)s"""], body, error.DuplicateCLError)

    def test_cl_bad_syntax(self):
        body = "abc123def456ghi789"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 2abc

%(body)s"""], body, error.MalformedCLError)

    def test_chunk_ext(self):
        body = "abc123def456ghi789"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

%(body_len)x; myext=foobarbaz\r
%(body)s\r
0\r
\r
"""], body)

    def test_trailers(self):
        body = "abc123def456ghi789"
        self.checkSingleMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

%(body_len)x\r
%(body)s\r
0\r
Foo: bar
Baz: 1
\r
"""], body)
        self.assertEqual(self.parser.test_trailers, 
            [('Foo', ' bar'), ('Baz', ' 1')]
        )

    def test_pipeline_chunked(self):
        body = "abc123def456ghi789"
        self.checkMultiMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

%(body_len)x\r
%(body)s\r
0\r
\r
HTTP/1.1 404 Not Found
Content-Type: text/plain
Transfer-Encoding: chunked

%(body_len)x\r
%(body)s\r
0\r
\r
"""], body, 2)

    def test_pipeline_cl(self):
        body = "abc123def456ghi789"
        self.checkMultiMsg(["""\
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: %(body_len)s

%(body)sHTTP/1.1 404 Not Found
Content-Type: text/plain
Content-Length: %(body_len)s

%(body)s"""], body, 2)

# TODO:
#    def test_nobody_delimit(self):
#    def test_pipeline_nobody(self):
#    def test_chunked_then_length(self):
#    def test_length_then_chunked(self):
#    def test_inspectable(self):

            
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_http_server
##!/usr/bin/env python

import socket
import sys
import time
import unittest

import framework

import thor
from thor.events import on
from thor.http import HttpServer

class TestHttpServer(framework.ClientServerTestCase):
            
    def create_server(self, test_host, test_port, server_side):
        server = HttpServer(test_host, test_port, loop=self.loop)
        server_side(server)
        @on(self.loop)
        def stop():
            server.shutdown()

    def create_client(self, test_host, test_port, client_side):
        def run_client(client_side1):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((test_host, test_port))
            client_side1(client)
            client.close()
        self.move_to_thread(target=run_client, args=(client_side,))

    def check_exchange(self, exchange, expected):
        """
        Given an exchange, check that the status, phrase and body are as
        expected, and verify that it actually happened.
        """
        exchange.test_happened = False
        
        @on(exchange)
        def error(err_msg):
            exchange.test_happened = True
            self.assertEqual(err_msg, expected.get('error', err_msg))
            self.loop.stop()

        @on(exchange)
        def request_start(method, uri, headers):
            self.assertEqual(method, expected.get('method', method))
            self.assertEqual(uri, expected.get('phrase', uri))

        exchange.tmp_req_body = ""
        @on(exchange)
        def request_body(chunk):
            exchange.tmp_req_body += chunk

        @on(exchange)
        def request_done(trailers):
            exchange.test_happened = True
            self.assertEqual(
                trailers, 
                expected.get('req_trailers', trailers)
            )
            self.assertEqual(
                exchange.tmp_req_body, 
                expected.get('body', exchange.tmp_req_body)
            )
            self.loop.stop()
            
        @on(self.loop)
        def stop():
            self.assertTrue(exchange.test_happened)


    def test_basic(self):
        def server_side(server):
            def check(exchange):
                self.check_exchange(exchange, {
                    'method': 'GET',
                    'uri': '/'                    
                })
            server.on('exchange', check)
            
        def client_side(client_conn):
            client_conn.sendall("""\
GET / HTTP/1.1
Host: %s:%s

""" % (framework.test_host, framework.test_port))
            time.sleep(1)
            client_conn.close()
        self.go([server_side], [client_side])


    def test_extraline(self):
        def server_side(server):
            def check(exchange):
                self.check_exchange(exchange, {
                    'method': 'GET',
                    'uri': '/'
                })
            server.on('exchange', check)
            
        def client_side(client_conn):
            client_conn.sendall("""\
            
GET / HTTP/1.1
Host: %s:%s

""" % (framework.test_host, framework.test_port))
            time.sleep(1)
            client_conn.close()
        self.go([server_side], [client_side])


    def test_post(self):
        def server_side(server):
            def check(exchange):
                self.check_exchange(exchange, {
                    'method': 'POST',
                    'uri': '/foo'                    
                })
            server.on('exchange', check)
            
        def client_side(client_conn):
            client_conn.sendall("""\
POST / HTTP/1.1
Host: %s:%s
Content-Type: text/plain
Content-Length: 5

12345""" % (framework.test_host, framework.test_port))
            time.sleep(1)
            client_conn.close()
        self.go([server_side], [client_side])
        

    def test_post_extra_crlf(self):
        def server_side(server):
            def check(exchange):
                self.check_exchange(exchange, {
                    'method': 'POST',
                    'uri': '/foo'                    
                })
            server.on('exchange', check)
            
        def client_side(client_conn):
            client_conn.sendall("""\
POST / HTTP/1.1
Host: %s:%s
Content-Type: text/plain
Content-Length: 5

12345
""" % (framework.test_host, framework.test_port))
            time.sleep(1)
            client_conn.close()
        self.go([server_side], [client_side])        


#    def test_pipeline(self):
#        def server_side(server):
#            server.ex_count = 0
#            def check(exchange):
#                self.check_exchange(exchange, {
#                    'method': 'GET',
#                    'uri': '/'
#                })
#                server.ex_count += 1
#            server.on('exchange', check)
#            @on(self.loop)
#            def stop():
#                self.assertEqual(server.ex_count, 2)
#            
#        def client_side(client_conn):
#            client_conn.sendall("""\
#GET / HTTP/1.1
#Host: %s:%s
#
#GET / HTTP/1.1
#Host: %s:%s
#
#""" % (
#    framework.test_host, framework.test_port,
#    framework.test_host, framework.test_port
#))
#            time.sleep(1)
#            client_conn.close()
#        self.go([server_side], [client_side])



#    def test_conn_close(self):
#    def test_req_nobody(self):
#    def test_res_nobody(self):
#    def test_bad_http_version(self):
#    def test_pause(self):
#    def test_extra_crlf_after_post(self):
#    def test_absolute_uri(self): # ignore host header
#    def test_host_header(self):#
#    def test_unknown_transfercode(self): # should be 501
#    def test_shutdown(self):
#    def test_alternate_tcp_server(self):


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_http_utils
#!/usr/bin/env python

import sys
import unittest

from thor.http.common import header_names, header_dict, get_header

hdrs = [
    ('A', 'a1'),
    ('B', 'b1'),
    ('a', 'a2'),
    ('C', 'c1'),
    ('b', 'b2'),
    ('A', 'a3, a4'),
    ('D', '"d1, d1"'),
]


class TestHttpUtils(unittest.TestCase):
    def test_header_names(self):
        hdrs_n = header_names(hdrs)
        self.assertEqual(hdrs_n, set(['a', 'b', 'c', 'd']))
    
    def test_header_dict(self):
        hdrs_d = header_dict(hdrs)
        self.assertEqual(hdrs_d['a'], ['a1', 'a2', 'a3', 'a4'])
        self.assertEqual(hdrs_d['b'], ['b1', 'b2'])
        self.assertEqual(hdrs_d['c'], ['c1'])

    def test_header_dict_omit(self):
        hdrs_d = header_dict(hdrs, 'b')
        self.assertEqual(hdrs_d['a'], ['a1', 'a2', 'a3', 'a4'])
        self.assertTrue('b' not in hdrs_d.keys())
        self.assertTrue('B' not in hdrs_d.keys())
        self.assertEqual(hdrs_d['c'], ['c1'])
        
    def test_get_header(self):
        self.assertEqual(get_header(hdrs, 'a'), ['a1', 'a2', 'a3', 'a4'])
        self.assertEqual(get_header(hdrs, 'b'), ['b1', 'b2'])
        self.assertEqual(get_header(hdrs, 'c'), ['c1'])

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_loop
#!/usr/bin/env python

import errno
import os
import socket
import sys
import tempfile
import time as systime
import unittest

from framework import make_fifo

import thor.loop


class IOStopper(thor.loop.EventSource):
    def __init__(self, testcase, loop):
        thor.loop.EventSource.__init__(self, loop)
        self.testcase = testcase
        self.r_fd, self.w_fd = make_fifo('tmp_fifo')
        self.on('writable', self.write)
        self.register_fd(self.w_fd, 'writable')
    
    def write(self):
        self.testcase.assertTrue(self._loop.running)
        self._loop.stop()
        os.close(self.r_fd)
        os.close(self.w_fd)
        os.unlink('tmp_fifo')


class TestLoop(unittest.TestCase):
    
    def setUp(self):
        self.loop = thor.loop.make()
        self.i = 0

    def increment_counter(self):
        self.i += 1

    def test_start_event(self):
        self.loop.on('start', self.increment_counter)
        self.loop.schedule(1, self.loop.stop)
        self.loop.run()
        self.assertEqual(self.i, 1)

    def test_stop_event(self):
        self.loop.on('stop', self.increment_counter)
        self.loop.schedule(1, self.loop.stop)
        self.loop.run()
        self.assertEqual(self.i, 1)

    def test_run(self):
        def check_running():
            self.assertTrue(self.loop.running)
        self.loop.schedule(0, check_running)
        self.loop.schedule(1, self.loop.stop)
        self.loop.run()

    def test_scheduled_stop(self):
        self.loop.schedule(1, self.loop.stop)
        self.loop.run()
        self.assertFalse(self.loop.running)

    def test_io_stop(self):
        r = IOStopper(self, self.loop)
        self.loop.run()
        self.assertFalse(self.loop.running)
    
    def test_run_stop_run(self):
        def check_running():
            self.assertTrue(self.loop.running)
        self.loop.schedule(0, check_running)
        self.loop.schedule(1, self.loop.stop)
        self.loop.run()
        self.assertFalse(self.loop.running)
        self.loop.schedule(0, check_running)
        self.loop.schedule(1, self.loop.stop)
        self.loop.run()
            
    def test_schedule(self):
        run_time = 3 # how long to run for
        def check_time(start_time):
            now = systime.time()
            self.assertTrue(
                now - run_time - start_time <= self.loop.precision,
                "now: %s run_time: %s start_time: %s precision: %s" % (
                    now, run_time, start_time, self.loop.precision
                )
            )
            self.loop.stop()
        self.loop.schedule(run_time, check_time, systime.time())
        self.loop.run()
        
    def test_schedule_delete(self):
        def not_good():
            assert Exception, "this event should not have happened."
        e = self.loop.schedule(2, not_good)
        self.loop.schedule(1, e.delete)
        self.loop.schedule(3, self.loop.stop)
        self.loop.run()
        
    def test_time(self):
        run_time = 2
        def check_time():
            self.assertTrue(
                abs(systime.time() - self.loop.time()) <= self.loop.precision
            )
            self.loop.stop()
        self.loop.schedule(run_time, check_time)
        self.loop.run()


class TestEventSource(unittest.TestCase):

    def setUp(self):
        self.loop = thor.loop.make()
        self.es = thor.loop.EventSource(self.loop)
        self.events_seen = []
        self.r_fd, self.w_fd = make_fifo('tmp_fifo')

    def tearDown(self):
        os.close(self.r_fd)
        os.close(self.w_fd)
        os.unlink('tmp_fifo')

    def test_EventSource_register(self):
        self.es.register_fd(self.r_fd)
        self.assertTrue(self.r_fd in self.loop._fd_targets.keys())
    
    def test_EventSource_unregister(self):
        self.es.register_fd(self.r_fd)
        self.assertTrue(self.r_fd in self.loop._fd_targets.keys())
        self.es.unregister_fd()
        self.assertFalse(self.r_fd in self.loop._fd_targets.keys())
        
    def test_EventSource_event_del(self):
        self.es.register_fd(self.r_fd, 'readable')
        self.es.on('readable', self.readable_check)
        self.es.event_del('readable')
        os.write(self.w_fd, 'foo')
        self.loop._run_fd_events()
        self.assertFalse('readable' in self.events_seen)
        
    def test_EventSource_readable(self):
        self.es.register_fd(self.r_fd, 'readable')
        self.es.on('readable', self.readable_check)
        os.write(self.w_fd, "foo")
        self.loop._run_fd_events()
        self.assertTrue('readable' in self.events_seen)

    def test_EventSource_not_readable(self):
        self.es.register_fd(self.r_fd, 'readable')
        self.es.on('readable', self.readable_check)
        self.loop._run_fd_events()
        self.assertFalse('readable' in self.events_seen)

    def readable_check(self, check="foo"):
        data = os.read(self.r_fd, 5)
        self.assertEquals(data, check)
        self.events_seen.append('readable')

#    def test_EventSource_close(self):
#        self.es.register_fd(self.fd, 'close')
#        self.es.on('close', self.close_check)
#        self.fd.close()
#        self.loop._run_fd_events()
#        self.assertTrue('close' in self.events_seen)
#
#    def close_check(self):
#        self.events_seen.append('close')        

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_tcp_client
#!/usr/bin/env python

import errno
import socket
import SocketServer
import sys
import threading
import unittest

from thor import loop
from thor.tcp import TcpClient

test_host = "127.0.0.1"
test_port = 9002

class LittleRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        # Echo the back to the client
        data = self.request.recv(1024)
        self.request.send(data)
        
class LittleServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True

# TODO: update with framework
class TestTcpClientConnect(unittest.TestCase):

    def setUp(self):
        self.loop = loop.make()
        self.connect_count = 0
        self.error_count = 0
        self.last_error_type = None
        self.last_error = None
        self.timeout_hit = False
        self.conn = None
        def check_connect(conn):
            self.conn = conn
            self.assertTrue(conn.tcp_connected)
            self.connect_count += 1
            conn.write("test")
            conn.close()
            self.loop.schedule(1, self.loop.stop)
        def check_error(err_type, err_id, err_str):
            self.error_count += 1
            self.last_error_type = err_type
            self.last_error = err_id
            self.loop.schedule(1, self.loop.stop)
        def timeout():
            self.loop.stop()
            self.timeout_hit = True
        self.timeout = timeout
        self.client = TcpClient(self.loop)
        self.client.on('connect', check_connect)
        self.client.on('connect_error', check_error)

    def test_connect(self):
        self.server = LittleServer(
            (test_host, test_port), 
            LittleRequestHandler
        )
        t = threading.Thread(target=self.server.serve_forever)
        t.setDaemon(True)
        t.start()
        self.client.connect(test_host, test_port)
        self.loop.schedule(2, self.timeout)
        self.loop.run()
        self.assertFalse(self.conn.tcp_connected)
        self.assertEqual(self.connect_count, 1)
        self.assertEqual(self.error_count, 0)
        self.assertEqual(self.timeout_hit, False)
        self.server.shutdown()
        self.server.socket.close()
        
    def test_connect_refused(self):
        self.client.connect(test_host, test_port + 1)
        self.loop.schedule(3, self.timeout)
        self.loop.run()
        self.assertEqual(self.connect_count, 0)
        self.assertEqual(self.error_count, 1)
        self.assertEqual(self.last_error_type, socket.error)
        self.assertEqual(self.last_error, errno.ECONNREFUSED)
        self.assertEqual(self.timeout_hit, False)
        
    def test_connect_noname(self):
        self.client.connect('does.not.exist', test_port)
        self.loop.schedule(3, self.timeout)
        self.loop.run()
        self.assertEqual(self.connect_count, 0)
        self.assertEqual(self.error_count, 1)
        self.assertEqual(self.last_error_type, socket.gaierror)
        self.assertEqual(self.last_error, socket.EAI_NONAME)
        self.assertEqual(self.timeout_hit, False)

    def test_connect_timeout(self):
        self.client.connect('128.66.0.1', test_port, 1)
        self.loop.schedule(3, self.timeout)
        self.loop.run()
        self.assertEqual(self.connect_count, 0)
        self.assertEqual(self.error_count, 1)
        self.assertEqual(self.last_error_type, socket.error)
        self.assertEqual(self.last_error, errno.ETIMEDOUT)
        self.assertEqual(self.timeout_hit, False)

# TODO:
#   def test_pause(self):

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tcp_server
#!/usr/bin/env python

import socket
import sys
import time
import unittest

import framework

import thor
from thor.events import on

class TestTcpServer(framework.ClientServerTestCase):

    def create_server(self, host, port, server_side):
        server = thor.TcpServer(host, port, loop=self.loop)
        server.conn_count = 0
        def run_server(conn):
            server.conn_count += 1
            server_side(conn)
        server.on('connect', run_server)
        @on(self.loop)
        def stop():
            self.assertTrue(server.conn_count > 0)
            server.shutdown()
                    
    def create_client(self, host, port, client_side):
        def run_client(client_side1):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((host, port))
            client_side1(client)
            client.close()
        self.move_to_thread(target=run_client, args=(client_side,))
        self.loop.schedule(1, self.loop.stop)

    def test_basic(self):
        def server_side(server_conn):
            self.server_recv = 0
            def check_data(chunk):
                self.assertEqual(chunk, "foo!")
                self.server_recv += 1
            server_conn.on('data', check_data)
            server_conn.pause(False)
            server_conn.write("bar!")
            
        def client_side(client_conn):
            sent = client_conn.send('foo!')

        self.go([server_side], [client_side])
        self.assertTrue(self.server_recv > 0, self.server_recv)
 
# TODO:
#   def test_pause(self):
#   def test_shutdown(self):

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_udp
#!/usr/bin/env python

import errno
import socket
import sys
import threading
import unittest


from thor import loop
from thor.udp import UdpEndpoint

test_host = "127.0.0.1"
test_port = 9002


class TestUdpEndpoint(unittest.TestCase):

    def setUp(self):
        self.loop = loop.make()
        self.ep1 = UdpEndpoint(self.loop)
        self.ep1.bind(test_host, test_port)
        self.ep1.on('datagram', self.input)
        self.ep1.pause(False)
        self.ep2 = UdpEndpoint()
        self.loop.schedule(5, self.timeout)
        self.timeout_hit = False
        self.datagrams = []

    def tearDown(self):
        self.ep1.shutdown()
        
    def timeout(self):
        self.timeout_hit = True
        self.loop.stop()

    def input(self, data, host, port):
        self.datagrams.append((data, host, port))

    def output(self, msg):
        self.ep2.send(msg, test_host, test_port)
        
    def test_basic(self):
        self.loop.schedule(1, self.output, 'foo!')
        self.loop.schedule(2, self.output, 'bar!')
        
        def check():
            self.assertEqual(self.datagrams[0][0], 'foo!')
            self.assertEqual(self.datagrams[1][0], 'bar!')
            self.loop.stop()
        self.loop.schedule(3, check)
        self.loop.run()
        
    def test_bigdata(self):
        self.loop.schedule(1, self.output, 'a' * 100)
        self.loop.schedule(2, self.output, 'b' * 1000)
        self.loop.schedule(3, self.output, 'c' * self.ep1.max_dgram)
        
        def check():
            self.assertEqual(self.datagrams[0][0], 'a' * 100)
            self.assertEqual(self.datagrams[1][0], 'b' * 1000)
            # we only check the first 1000 characters because, well, 
            # it's lossy.
            self.assertEqual(self.datagrams[2][0][:1000], 'c' * 1000)
            self.loop.stop()
        self.loop.schedule(4, check)
        self.loop.run()

#   def test_pause(self):


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = events
#!/usr/bin/env python

"""
Event utilities, including:

* EventEmitter - in the style of Node.JS.
* on - a decorator for making functions and methods listen to events.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2005-2013 Mark Nottingham

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

from collections import defaultdict


class EventEmitter(object):
    """
    An event emitter, in the style of Node.JS.
    """

    def __init__(self):
        self.__events = defaultdict(list)
        self.__sink = None

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["_EventEmitter__events"]
        return state

    def on(self, event, listener):
        """
        Call listener when event is emitted.
        """
        self.__events[event].append(listener)
        self.emit('newListener', event, listener)

    def once(self, event, listener):
        """
        Call listener the first time event is emitted.
        """
        def mycall(*args):
            listener(*args)
            self.removeListener(event, mycall)
        self.on(event, mycall)

    def removeListener(self, event, listener):
        """
        Remove a specific listener from an event.

        If called for a specific listener by a previous listener
        for the same event, that listener will not be fired.
        """
        self.__events.get(event, [listener]).remove(listener)

    def removeListeners(self, *events):
        """
        Remove all listeners from an event; if no event
        is specified, remove all listeners for all events.

        If called from an event listener, other listeners
        for that event will still be fired.
        """
        if events:
            for event in events:
                self.__events[event] = []
        else:
            self.__events = defaultdict(list)

    def listeners(self, event):
        """
        Return a list of listeners for an event.
        """
        return self.__events.get(event, [])

    def events(self):
        """
        Return a list of events being listened for.
        """
        return self.__events.keys()

    def emit(self, event, *args):
        """
        Emit the event (with any given args) to
        its listeners.
        """
        events = self.__events.get(event, [])
        if len(events):
            for e in events:
                e(*args)
        else:
            sink_event = getattr(self.__sink, event, None)
            if sink_event:
                sink_event(*args)

    def sink(self, sink):
        """
        If no listeners are found for an event, call
        the method that shares the event's name (if present)
        on the event sink.
        """
        self.__sink = sink

    # TODO: event bubbling


def on(obj, event=None):
    """
    Decorator to call a function when an object emits
    the specified event.
    """
    def wrap(funk):
        obj.on(event or funk.__name__, funk)
        return funk
    return wrap

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python

"""
Thor HTTP Client

This library allow implementation of an HTTP/1.1 client that is
"non-blocking," "asynchronous" and "event-driven" -- i.e., it achieves very
high performance and concurrency, so long as the application code does not
block (e.g., upon network, disk or database access). Blocking on one response
will block the entire client.

"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2005-2013 Mark Nottingham

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

from collections import defaultdict
from urlparse import urlsplit, urlunsplit

import thor
from thor.events import EventEmitter, on
from thor.tcp import TcpClient
from thor.tls import TlsClient

from thor.http.common import HttpMessageHandler, \
    CLOSE, COUNTED, CHUNKED, NOBODY, \
    WAITING, ERROR, \
    idempotent_methods, no_body_status, hop_by_hop_hdrs, \
    header_names
from thor.http.error import UrlError, ConnectError, \
    ReadTimeoutError, HttpVersionError

req_rm_hdrs = hop_by_hop_hdrs + ['host']

# TODO: next-hop version cache for Expect/Continue, etc.

class HttpClient(object):
    "An asynchronous HTTP client."

    tcp_client_class = TcpClient
    tls_client_class = TlsClient

    def __init__(self, loop=None):
        self.loop = loop or thor.loop._loop
        self.idle_timeout = 60 # in seconds
        self.connect_timeout = None
        self.read_timeout = None
        self.retry_limit = 2
        self.retry_delay = 0.5 # in sec
        self.max_server_conn = 4
        self.proxy_tls = False
        self.proxy_host = None
        self.proxy_port = None
        self._idle_conns = defaultdict(list)
        self._conn_counts = defaultdict(int)
        self.loop.on('stop', self._close_conns)

    def exchange(self):
        return HttpClientExchange(self)

    def _attach_conn(self, origin, handle_connect,
               handle_connect_error, connect_timeout):
        "Find an idle connection for origin, or create a new one."
        if self.proxy_host and self.proxy_port:
            # TODO: full form of request-target
            import sys
            host, port = self.proxy_host, self.proxy_port
            if self.proxy_tls:
                scheme = 'https'
            else:
                scheme = 'http'
            origin = (scheme, host, port)
        else:
            scheme, host, port = origin
        while True:
            try:
                tcp_conn = self._idle_conns[origin].pop()
            except IndexError:
                self._new_conn(
                    origin,
                    handle_connect,
                    handle_connect_error,
                    connect_timeout
                )
                break
            if tcp_conn.tcp_connected:
                if hasattr(tcp_conn, "_idler"):
                    tcp_conn._idler.delete()
                handle_connect(tcp_conn)
                break

    def _release_conn(self, tcp_conn, scheme):
        "Add an idle connection back to the pool."
        tcp_conn.removeListeners('data', 'pause', 'close')
        tcp_conn.on('close', tcp_conn.handle_close)
        tcp_conn.pause(True)
        origin = (scheme, tcp_conn.host, tcp_conn.port)
        if tcp_conn.tcp_connected:
            def idle_close():
                "Remove the connection from the pool when it closes."
                if hasattr(tcp_conn, "_idler"):
                    tcp_conn._idler.delete()                    
                self._dead_conn(origin)
                try:
                    self._idle_conns[origin].remove(tcp_conn)
                except (KeyError, ValueError):
                    pass
            tcp_conn.on('close', idle_close)
            if self.idle_timeout > 0:
                tcp_conn._idler = self.loop.schedule(
                    self.idle_timeout, tcp_conn.close
                )
            else:
                tcp_conn.close()
                self._dead_conn(origin)
            self._idle_conns[origin].append(tcp_conn)
        else:
            self._dead_conn(origin)

    def _new_conn(self, origin, handle_connect, handle_error, timeout):
        "Create a new connection."
        (scheme, host, port) = origin
        if scheme == 'http':
            tcp_client = self.tcp_client_class(self.loop)
        elif scheme == 'https':
            tcp_client = self.tls_client_class(self.loop)
        else:
            raise ValueError, 'unknown scheme %s' % scheme
        tcp_client.on('connect', handle_connect)
        tcp_client.on('connect_error', handle_error)
        self._conn_counts[origin] += 1
        tcp_client.connect(host, port, timeout)

    def _dead_conn(self, origin):
        "Notify the client that a connect to origin is dead."
        self._conn_counts[origin] -= 1

    def _close_conns(self):
        "Close all idle HTTP connections."
        for conn_list in self._idle_conns.values():
            for conn in conn_list:
                try:
                    conn.close()
                except:
                    pass
        self._idle_conns.clear()
        # TODO: probably need to close in-progress conns too.


class HttpClientExchange(HttpMessageHandler, EventEmitter):

    def __init__(self, client):
        HttpMessageHandler.__init__(self)
        EventEmitter.__init__(self)
        self.client = client
        self.method = None
        self.uri = None
        self.req_hdrs = None
        self.req_target = None
        self.scheme = None
        self.authority = None
        self.res_version = None
        self.tcp_conn = None
        self.origin = None
        self._conn_reusable = False
        self._req_body = False
        self._req_started = False
        self._retries = 0
        self._read_timeout_ev = None
        self._output_buffer = []

    def __repr__(self):
        status = [self.__class__.__module__ + "." + self.__class__.__name__]
        status.append('%s {%s}' % (self.method or "-", self.uri or "-"))
        if self.tcp_conn:
            status.append(
              self.tcp_conn.tcp_connected and 'connected' or 'disconnected')
        return "<%s at %#x>" % (", ".join(status), id(self))

    def request_start(self, method, uri, req_hdrs):
        """
        Start a request to uri using method, where
        req_hdrs is a list of (field_name, field_value) for
        the request headers.
        """
        self.method = method
        self.uri = uri
        self.req_hdrs = req_hdrs
        try:
            self.origin = self._parse_uri(self.uri)
        except (TypeError, ValueError):
            return 
        self.client._attach_conn(self.origin, self._handle_connect,
            self._handle_connect_error, self.client.connect_timeout
        )
    # TODO: if we sent Expect: 100-continue, don't wait forever
    # (i.e., schedule something)

    def _parse_uri(self, uri):
        """
        Given a URI, parse out the host, port, authority and request target. 
        Returns None if there is an error, otherwise the origin.
        """
        (scheme, authority, path, query, fragment) = urlsplit(uri)
        scheme = scheme.lower()
        if scheme == 'http':
            default_port = 80
        elif scheme == 'https':
            default_port = 443
        else:
            self.input_error(UrlError("Unsupported URL scheme '%s'" % scheme))
            raise ValueError
        if "@" in authority:
            userinfo, authority = authority.split("@", 1)
        if ":" in authority:
            host, port = authority.rsplit(":", 1)
            try:
                port = int(port)
            except ValueError:
                self.input_error(UrlError("Non-integer port in URL"))
                raise
        else:
            host, port = authority, default_port
        if path == "":
            path = "/"
        self.scheme = scheme
        self.authority = authority
        self.req_target = urlunsplit(('', '', path, query, ''))
        return scheme, host, port

    def _req_start(self):
        """
        Actually queue the request headers for sending.
        """
        self._req_started = True
        req_hdrs = [
            i for i in self.req_hdrs if not i[0].lower() in req_rm_hdrs
        ]
        req_hdrs.append(("Host", self.authority))
        if self.client.idle_timeout > 0:
            req_hdrs.append(("Connection", "keep-alive"))
        else:
            req_hdrs.append(("Connection", "close"))
        if "content-length" in header_names(req_hdrs):
            delimit = COUNTED
        elif self._req_body:
            req_hdrs.append(("Transfer-Encoding", "chunked"))
            delimit = CHUNKED
        else:
            delimit = NOBODY
        self.output_start("%s %s HTTP/1.1" % (self.method, self.req_target),
            req_hdrs, delimit
        )


    def request_body(self, chunk):
        "Send part of the request body. May be called zero to many times."
        if not self._req_started:
            self._req_body = True
            self._req_start()
        self.output_body(chunk)

    def request_done(self, trailers):
        """
        Signal the end of the request, whether or not there was a body. MUST
        be called exactly once for each request.
        """
        if not self._req_started:
            self._req_start()
        self.output_end(trailers)

    def res_body_pause(self, paused):
        "Temporarily stop / restart sending the response body."
        if self.tcp_conn and self.tcp_conn.tcp_connected:
            self.tcp_conn.pause(paused)

    # Methods called by tcp

    def _handle_connect(self, tcp_conn):
        "The connection has succeeded."
        self.tcp_conn = tcp_conn
        self._set_read_timeout('connect')
        tcp_conn.on('data', self.handle_input)
        tcp_conn.on('close', self._conn_closed)
        tcp_conn.on('pause', self._req_body_pause)
        # FIXME: should this be done AFTER _req_start?
        self.output("") # kick the output buffer
        self.tcp_conn.pause(False)

    def _handle_connect_error(self, err_type, err_id, err_str):
        "The connection has failed."
        self.input_error(ConnectError(err_str))

    def _conn_closed(self):
        "The server closed the connection."
        self._clear_read_timeout()
        if self._input_buffer:
            self.handle_input("")
        if self._input_delimit == CLOSE:
            self.input_end([])
        elif self._input_state == WAITING: # TODO: needs to be tighter
            if self.method in idempotent_methods:
                if self._retries < self.client.retry_limit:
                    self.client.loop.schedule(
                        self.client.retry_delay, self._retry
                    )
                else:
                    self.input_error(
                        ConnectError(
                            "Tried to connect %s times." % (self._retries + 1)
                        )
                    )
            else:
                self.input_error(
                    ConnectError("Can't retry %s method" % self.method)
                )
        else:
            self.input_error(ConnectError(
                "Server dropped connection before the response was complete."
            ))

    def _retry(self):
        "Retry the request."
        self._clear_read_timeout()
        self._retries += 1
        try:
            origin = self._parse_uri(self.uri)
        except (TypeError, ValueError):
            return 
        self.client._attach_conn(origin, self._handle_connect,
            self._handle_connect_error, self.client.connect_timeout
        )

    def _req_body_pause(self, paused):
        "The client needs the application to pause/unpause the request body."
        self.emit('pause', paused)

    # Methods called by common.HttpMessageHandler

    def input_start(self, top_line, hdr_tuples, conn_tokens,
        transfer_codes, content_length):
        """
        Take the top set of headers from the input stream, parse them
        and queue the request to be processed by the application.
        """
        self._clear_read_timeout()
        try:
            proto_version, status_txt = top_line.split(None, 1)
            proto, self.res_version = proto_version.rsplit('/', 1)
        except (ValueError, IndexError):
            self.input_error(HttpVersionError(top_line))
            raise ValueError
        if proto != "HTTP" or self.res_version not in ["1.0", "1.1"]:
            self.input_error(HttpVersionError(proto_version))
            raise ValueError
        try:
            res_code, res_phrase = status_txt.split(None, 1)
        except ValueError:
            res_code = status_txt.rstrip()
            res_phrase = ""
        if 'close' not in conn_tokens:
            if (
              self.res_version == "1.0" and 'keep-alive' in conn_tokens) or \
              self.res_version in ["1.1"]:
                self._conn_reusable = True
        self._set_read_timeout('start')
        self.emit('response_start',
                  res_code,
                  res_phrase,
                  hdr_tuples
        )
        allows_body = (res_code not in no_body_status) \
            and (self.method != "HEAD")
        return allows_body

    def input_body(self, chunk):
        "Process a response body chunk from the wire."
        self._clear_read_timeout()
        self.emit('response_body', chunk)
        self._set_read_timeout('body')

    def input_end(self, trailers):
        "Indicate that the response body is complete."
        self._clear_read_timeout()
        if self.tcp_conn.tcp_connected and self._conn_reusable:
            self.client._release_conn(self.tcp_conn, self.scheme)
        else:
            if self.tcp_conn:
              self.tcp_conn.close()
            self._dead_conn()
        self.tcp_conn = None
        self.emit('response_done', trailers)

    def input_error(self, err):
        "Indicate an error state."
        if self.inspecting: # we want to get the rest of the response.
            self._conn_reusable = False
        else:
            self._input_state = ERROR
            self._clear_read_timeout()
            if err.client_recoverable and \
              self.tcp_conn and self.tcp_conn.tcp_connected:
                self.client._release_conn(self.tcp_conn, self.scheme)
            else:
                self._dead_conn()
                if self.tcp_conn:
                    self.tcp_conn.close()
            self.tcp_conn = None
        self.emit('error', err)
        
    def _dead_conn(self):
        "Inform the client that the connection is dead."
        self.client._dead_conn(self.origin)

    def output(self, chunk):
        self._output_buffer.append(chunk)
        if self.tcp_conn and self.tcp_conn.tcp_connected:
            self.tcp_conn.write("".join(self._output_buffer))
            self._output_buffer = []

    # misc

    def _set_read_timeout(self, kind):
        "Set the read timeout."
        if self.client.read_timeout:
            self._read_timeout_ev = self.client.loop.schedule(
                self.client.read_timeout, self.input_error,
                ReadTimeoutError(kind)
            )

    def _clear_read_timeout(self):
        "Clear the read timeout."
        if self._read_timeout_ev:
            self._read_timeout_ev.delete()


def test_client(request_uri, out, err):
    "A simple demonstration of a client."
    from thor.loop import stop, run

    c = HttpClient()
    c.connect_timeout = 5
    x = c.exchange()

    @on(x)
    def response_start(status, phrase, headers):
        "Print the response headers."
        print "HTTP/%s %s %s" % (x.res_version, status, phrase)
        print "\n".join(["%s:%s" % header for header in headers])
        print

    @on(x)
    def error(err_msg):
        if err_msg:
            err("*** ERROR: %s (%s)\n" %
                (err_msg.desc, err_msg.detail)
            )
        stop()

    x.on('response_body', out)

    @on(x)
    def response_done(trailers):
        stop()

    x.request_start("GET", request_uri, [])
    x.request_done([])
    run()


if __name__ == "__main__":
    import sys
    test_client(sys.argv[1], sys.stdout.write, sys.stderr.write)

########NEW FILE########
__FILENAME__ = common
#!/usr/bin/env python

"""
Thor shared HTTP infrastructure

This module contains utility functions and a base class
for the parsing portions of the HTTP client and server.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2005-2013 Mark Nottingham

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

from collections import defaultdict
import re

from thor.http import error

lws = re.compile("\r?\n[ \t]+", re.M)
hdr_end = re.compile(r"\r?\n\r?\n", re.M)
linesep = "\r\n"

# conn_modes
CLOSE, COUNTED, CHUNKED, NOBODY = 'close', 'counted', 'chunked', 'nobody'

# states
WAITING, HEADERS_DONE, ERROR = 1, 2, 3

idempotent_methods = ['GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS', 'TRACE']
safe_methods = ['GET', 'HEAD', 'OPTIONS', 'TRACE']
no_body_status = ['100', '101', '204', '304']
hop_by_hop_hdrs = ['connection', 'keep-alive', 'proxy-authenticate',
                   'proxy-authorization', 'te', 'trailers',
                   'transfer-encoding', 'upgrade', 'proxy-connection']


def dummy(*args, **kw):
    "Dummy method that does nothing; useful to ignore a callback."
    pass

def header_names(hdr_tuples):
    """
    Given a list of header tuples, return the set of the header names seen.
    """
    return set([n.lower() for n, v in hdr_tuples])

def header_dict(hdr_tuples, omit=None):
    """
    Given a list of header tuples, return a dictionary keyed upon the
    lower-cased header names.

    If omit is defined, each header listed (by lower-cased name) will not be
    returned in the dictionary.
    """
    out = defaultdict(list)
    for (n, v) in hdr_tuples:
        n = n.lower()
        if n in (omit or []):
            continue
        out[n].extend([i.strip() for i in v.split(',')])
    return out

def get_header(hdr_tuples, name):
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
            , [])
    ]


class HttpMessageHandler:
    """
    This is a base class for something that has to parse and/or serialise
    HTTP messages, request or response.

    For parsing, it expects you to override input_start, input_body and
    input_end, and call handle_input when you get bytes from the network.

    For serialising, it expects you to override _output.
    """

    inspecting = False # if True, don't fail on errors, but preserve them.

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

    def input_start(self, top_line, hdr_tuples, conn_tokens,
                     transfer_codes, content_length):
        """
        Take the top set of headers from the input stream, parse them
        and queue the request to be processed by the application.

        Returns boolean allows_body to indicate whether the message allows a
        body.

        Can raise ValueError to indicate that there's a problem and parsing
        cannot continue.
        """
        raise NotImplementedError

    def input_body(self, chunk):
        "Process a body chunk from the wire."
        raise NotImplementedError

    def input_end(self, trailers):
        """
        Indicate that the response body is complete. Optionally can contain
        trailers.
        """
        raise NotImplementedError

    def input_error(self, err):
        "Indicate an unrecoverable parsing problem with the input stream."
        raise NotImplementedError

    def handle_input(self, instr):
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
                    self.handle_input(rest)
                except RuntimeError:
                    self.input_error(error.TooManyMsgsError)
                    # we can't recover from this, so we bail.
            else: # partial headers; store it and wait for more
                self._input_buffer = instr
        elif self._input_state == HEADERS_DONE:
            try:
                handler = getattr(self, '_handle_%s' % self._input_delimit)
            except AttributeError:
                raise Exception, "Unknown input delimiter %s" % \
                                 self._input_delimit
            handler(instr)
        elif self._input_state == ERROR:
            pass # I'm silently ignoring input that I don't understand.
        else:
            raise Exception, "Unknown state %s" % self._input_state

    def _handle_nobody(self, instr):
        "Handle input that shouldn't have a body."
        self.input_end([])
        self._input_state = WAITING
        self.handle_input(instr)

    def _handle_close(self, instr):
        "Handle input where the body is delimited by the connection closing."
        self.input_transfer_length += len(instr)
        self.input_body(instr)

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
            # don't have the whole chunk_size yet... wait a bit
            if len(instr) > 512:
                # OK, this is absurd...
                self.input_error(error.ChunkError(instr))
                # TODO: need testing around this; catching the right thing?
            else:
                self._input_buffer += instr
            return
        # TODO: do we need to ignore blank lines?
        if ";" in chunk_size: # ignore chunk extensions
            chunk_size = chunk_size.split(";", 1)[0]
        try:
            self._input_body_left = int(chunk_size, 16)
        except ValueError:
            self.input_error(error.ChunkError(chunk_size))
            return
        self.input_transfer_length += len(instr) - len(rest)
        return rest

    def _handle_chunk_body(self, instr):
        got = len(instr)
        if self._input_body_left + 2 < got: # got more than the chunk
            this_chunk = self._input_body_left
            self.input_body(instr[:this_chunk])
            self.input_transfer_length += this_chunk + 2
            self._input_body_left = -1
            return instr[this_chunk + 2:] # +2 consumes the trailing CRLF
        elif self._input_body_left + 2 == got:
            # got the whole chunk exactly (including CRLF)
            self.input_body(instr[:-2])
            self.input_transfer_length += self._input_body_left + 2
            self._input_body_left = -1
        elif self._input_body_left == got: # corner case
            self._input_buffer += instr  
        else: # got partial chunk
            self.input_body(instr)
            self.input_transfer_length += got
            self._input_body_left -= got

    def _handle_chunk_done(self, instr):
        if len(instr) >= 2 and instr[:2] == linesep:
            self._input_state = WAITING
            self.input_end([])
            self.handle_input(instr[2:]) # 2 consumes the CRLF
        elif hdr_end.search(instr): # trailers
            self._input_state = WAITING
            trailer_block, rest = hdr_end.split(instr, 1)
            trailers = self._parse_fields(trailer_block.splitlines())
            if trailers == None: # found a problem
                self._input_state = ERROR # TODO: need an explicit error 
                return
            else:
                self.input_end(trailers)
                self.handle_input(rest)
        else: # don't have full trailers yet
            self._input_buffer = instr

    def _handle_counted(self, instr):
        "Handle input where the body is delimited by the Content-Length."
        if self._input_body_left <= len(instr): # got it all (and more?)
            self.input_transfer_length += self._input_body_left
            self.input_body(instr[:self._input_body_left])
            self.input_end([])
            self._input_state = WAITING
            if instr[self._input_body_left:]:
                self.handle_input(instr[self._input_body_left:])
        else: # got some of it
            self.input_body(instr)
            self.input_transfer_length += len(instr)
            self._input_body_left -= len(instr)

    def _parse_fields(self, header_lines, gather_conn_info=False):
        """
        Given a list of raw header lines (without the top line,
        and without the trailing CRLFCRLF), return its header tuples.
        """

        hdr_tuples = []
        conn_tokens = []
        transfer_codes = []
        content_length = None

        for line in header_lines:
            if line[:1] in [" ", "\t"]: # Fold LWS
                if len(hdr_tuples):
                    hdr_tuples[-1] = (
                        hdr_tuples[-1][0], 
                        "%s %s" % (hdr_tuples[-1][1], line.lstrip())
                    )
                    continue
                else: # top header starts with whitespace
                    self.input_error(error.TopLineSpaceError(line))
                    if not self.inspecting:
                        return
            try:
                fn, fv = line.split(":", 1)
            except ValueError:
                if self.inspecting:
                    hdr_tuples.append(line)
                else:
                    continue # TODO: error on unparseable field?
            # TODO: a zero-length name isn't valid
            if fn[-1:] in [" ", "\t"]:
                self.input_error(error.HeaderSpaceError(fn))
                if not self.inspecting:
                    return
            hdr_tuples.append((fn, fv))

            if gather_conn_info:
                f_name = fn.strip().lower()
                f_val = fv.strip()

                # parse connection-related headers
                if f_name == "connection":
                    conn_tokens += [
                        v.strip().lower() for v in f_val.split(',')
                    ]
                elif f_name == "transfer-encoding": # TODO: parameters? no...
                    transfer_codes += [v.strip().lower() for \
                                       v in f_val.split(',')]
                elif f_name == "content-length":
                    if content_length != None:
                        try:
                            if int(f_val) == content_length:
                                # we have a duplicate, non-conflicting c-l.
                                continue
                        except ValueError:
                            pass
                        self.input_error(error.DuplicateCLError())
                        if not self.inspecting:
                            return
                    try:
                        content_length = int(f_val)
                        assert content_length >= 0
                    except (ValueError, AssertionError):
                        self.input_error(error.MalformedCLError(f_val))
                        if not self.inspecting:
                            return
            
        # yes, this is a horrible hack.     
        if gather_conn_info:
            return hdr_tuples, conn_tokens, transfer_codes, content_length
        else:
            return hdr_tuples

    def _parse_headers(self, instr):
        """
        Given a string that we knows starts with a header block (possibly
        more), parse the headers out and return the rest. Calls
        self.input_start to kick off processing.
        """
        top, rest = hdr_end.split(instr, 1)
        self.input_header_length = len(top)
        header_lines = top.splitlines()

        # chop off the top line
        while True: # TODO: limit?
            try:
                top_line = header_lines.pop(0)
                if top_line.strip() != "":
                    break
            except IndexError: # empty
                return rest
        
        try:
            hdr_tuples, conn_tokens, transfer_codes, content_length \
            = self._parse_fields(header_lines, True)
        except TypeError: # returned None because there was an error
            if not self.inspecting:
                return "" # throw away the rest
            
        # ignore content-length if transfer-encoding is present
        if transfer_codes != [] and content_length != None:
            content_length = None

        try:
            allows_body = self.input_start(top_line, hdr_tuples,
                        conn_tokens, transfer_codes, content_length)
        except ValueError: # parsing error of some kind; abort.
            if not self.inspecting:
                return "" # throw away the rest
            allows_body = True

        self._input_state = HEADERS_DONE
        if not allows_body:
            self._input_delimit = NOBODY
        elif len(transfer_codes) > 0:
            if transfer_codes[-1] == 'chunked':
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

    def output(self, out):
        raise NotImplementedError

    def output_start(self, top_line, hdr_tuples, delimit):
        """
        Start ouputting a HTTP message.
        """
        self._output_delimit = delimit
        out = linesep.join(
                [top_line] +
                ["%s: %s" % (k.strip(), v) for k, v in hdr_tuples] +
                ["", ""]
        )
        self.output(out)
        self._output_state = HEADERS_DONE

    def output_body(self, chunk):
        """
        Output a part of a HTTP message.
        """
        if not chunk or self._output_delimit == None:
            return
        if self._output_delimit == CHUNKED:
            chunk = "%s\r\n%s\r\n" % (hex(len(chunk))[2:], chunk)
        self.output(chunk)
        # TODO: body counting
#        self._output_body_sent += len(chunk)
#        assert self._output_body_sent <= self._output_content_length, \
#            "Too many body bytes sent"

    def output_end(self, trailers):
        """
        Finish outputting a HTTP message, including trailers if appropriate.
        """
        if self._output_delimit == NOBODY:
            pass # didn't have a body at all.
        elif self._output_delimit == CHUNKED:
            self.output("0\r\n%s\r\n" % "\r\n".join([
                "%s: %s" % (k.strip(), v) for k, v in trailers
            ]))
        elif self._output_delimit == COUNTED:
            pass # TODO: double-check the length
        elif self._output_delimit == CLOSE:
            # FIXME: abstract out
            self.tcp_conn.close() # pylint: disable=E1101 
        elif self._output_delimit == None:
            pass # encountered an error before we found a delmiter
        else:
            raise AssertionError, "Unknown request delimiter %s" % \
                                  self._output_delimit
        self._output_state = WAITING

########NEW FILE########
__FILENAME__ = error
#!/usr/bin/env python

"""
Thor HTTP Errors
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

class HttpError(Exception):
    desc = "Unknown Error"
    server_status = None # status this produces when it occurs in a server
    server_recoverable = False # whether a server can recover the connection
    client_recoverable = False # whether a client can recover the connection

    def __init__(self, detail=None):
        Exception.__init__(self)
        self.detail = detail

    def __repr__(self):
        status = [self.__class__.__module__ + "." + self.__class__.__name__]
        if self.detail:
            status.append(self.detail)
        return "<%s at %#x>" % (", ".join(status), id(self))

# General parsing errors

class ChunkError(HttpError):
    desc = "Chunked encoding error"

class DuplicateCLError(HttpError):
    desc = "Duplicate Content-Length header"
    server_status = ("400", "Bad Request")

class MalformedCLError(HttpError):
    desc = "Malformed Content-Length header"
    server_status = ("400", "Bad Request")

class BodyForbiddenError(HttpError):
    desc = "This message does not allow a body",

class HttpVersionError(HttpError):
    desc = "Unrecognised HTTP version"
    server_status = ("505", "HTTP Version Not Supported")

class ReadTimeoutError(HttpError):
    desc = "Read Timeout"

class TransferCodeError(HttpError):
    desc = "Unknown request transfer coding"
    server_status = ("501", "Not Implemented")

class HeaderSpaceError(HttpError):
    desc = "Whitespace at the end of a header field-name"
    server_status = ("400", "Bad Request")
    
class TopLineSpaceError(HttpError):
    desc = "Whitespace after top line, before first header"
    server_status = ("400", "Bad Request")

class TooManyMsgsError(HttpError):
    desc = "Too many messages to parse"
    server_status = ("400", "Bad Request")

# client-specific errors

class UrlError(HttpError):
    desc = "Unsupported or invalid URI"
    server_status = ("400", "Bad Request")
    client_recoverable = True

class LengthRequiredError(HttpError):
    desc = "Content-Length required"
    server_status = ("411", "Length Required")
    client_recoverable = True

class ConnectError(HttpError):
    desc = "Connection error"
    server_status = ("504", "Gateway Timeout")

# server-specific errors

class HostRequiredError(HttpError):
    desc = "Host header required"
    server_recoverable = True

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python

"""
Thor HTTP Server

This library allow implementation of an HTTP/1.1 server that is
"non-blocking," "asynchronous" and "event-driven" -- i.e., it achieves very
high performance and concurrency, so long as the application code does not
block (e.g., upon network, disk or database access). Blocking on one request
will block the entire server.

"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2005-2013 Mark Nottingham

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

from thor import schedule
from thor.events import EventEmitter, on
from thor.tcp import TcpServer

from thor.http.common import HttpMessageHandler, \
    CLOSE, COUNTED, CHUNKED, \
    ERROR, \
    hop_by_hop_hdrs, \
    get_header, header_names
from thor.http.error import HttpVersionError, HostRequiredError, \
    TransferCodeError


class HttpServer(EventEmitter):
    "An asynchronous HTTP server."

    tcp_server_class = TcpServer
    idle_timeout = 60 # in seconds

    def __init__(self, host, port, loop=None):
        EventEmitter.__init__(self)
        self.tcp_server = self.tcp_server_class(host, port, loop=loop)
        self.tcp_server.on('connect', self.handle_conn)
        schedule(0, self.emit, 'start')

    def handle_conn(self, tcp_conn):
        http_conn = HttpServerConnection(tcp_conn, self)
        tcp_conn.on('data', http_conn.handle_input)
        tcp_conn.on('close', http_conn.conn_closed)
        tcp_conn.on('pause', http_conn.res_body_pause)
        tcp_conn.pause(False)

    def shutdown(self):
        "Stop the server"
        # TODO: Finish outstanding requests w/ timeout?
        self.tcp_server.shutdown()
        self.emit('stop')


class HttpServerConnection(HttpMessageHandler, EventEmitter):
    "A handler for an HTTP server connection."
    def __init__(self, tcp_conn, server):
        HttpMessageHandler.__init__(self)
        EventEmitter.__init__(self)
        self.tcp_conn = tcp_conn
        self.server = server
        self.ex_queue = [] # queue of exchanges
        self.output_paused = False

    def req_body_pause(self, paused):
        """
        Indicate that the server should pause (True) or unpause (False) the
        request.
        """
        self.tcp_conn.pause(paused)

    # Methods called by tcp

    def res_body_pause(self, paused):
        "Pause/unpause sending the response body."
        self.output_paused = paused
        self.emit('pause', paused)
        if not paused:
            self.drain_exchange_queue()

    def conn_closed(self):
        "The server connection has closed."
#        for exchange in self.ex_queue:
#            exchange.pause() # FIXME - maybe a connclosed err?
        self.ex_queue = []
        self.tcp_conn = None

    # Methods called by common.HttpRequestHandler

    def output(self, data):
        self.tcp_conn.write(data)

    def input_start(self, top_line, hdr_tuples, conn_tokens,
        transfer_codes, content_length):
        """
        Take the top set of headers from the input stream, parse them
        and queue the request to be processed by the application.
        """
        try:
            method, _req_line = top_line.split(None, 1)
            uri, req_version = _req_line.rsplit(None, 1)
            req_version = req_version.rsplit('/', 1)[1]
        except (ValueError, IndexError):
            self.input_error(HttpVersionError(top_line))
            # TODO: more fine-grained
            raise ValueError
        if 'host' not in header_names(hdr_tuples):
            self.input_error(HostRequiredError())
            raise ValueError
        for code in transfer_codes:
            # we only support 'identity' and chunked' codes in requests
            if code not in ['identity', 'chunked']:
                self.input_error(TransferCodeError(code))
                raise ValueError
        exchange = HttpServerExchange(
            self, method, uri, hdr_tuples, req_version
        )
        self.ex_queue.append(exchange)
        self.server.emit('exchange', exchange)
        if not self.output_paused:
            # we only start new requests if we have some output buffer 
            # available. 
            exchange.request_start()
        allows_body = (content_length) or (transfer_codes != [])
        return allows_body

    def input_body(self, chunk):
        "Process a request body chunk from the wire."
        self.ex_queue[-1].emit('request_body', chunk)

    def input_end(self, trailers):
        "Indicate that the request body is complete."
        self.ex_queue[-1].emit('request_done', trailers)

    def input_error(self, err):
        """
        Indicate a parsing problem with the request body (which
        hasn't been queued as an exchange yet).
        """
        self._input_state = ERROR
        status_code, status_phrase = err.server_status or \
            (500, 'Internal Server Error')
        hdrs = [
            ('Content-Type', 'text/plain'),
        ]
        body = err.desc
        if err.detail:
            body += " (%s)" % err.detail
        ex = HttpServerExchange(self, "1.1") # FIXME
        ex.response_start(status_code, status_phrase, hdrs)
        ex.response_body(body)
        ex.response_done([])
        self.ex_queue.append(ex)

# FIXME: connection?

#        if self.tcp_conn and not err.server_recoverable:
#            self.tcp_conn.close()
#            self.tcp_conn = None

# TODO: if in mid-request, we need to send an error event and clean up.
#        self.ex_queue[-1].emit('error', err)

    def drain_exchange_queue(self):
        """
        Walk through the exchange queue and kick off unstarted requests
        until we run out of output buffer.
        """
        # TODO: probably have a separate metric for outstanding requests,
        # rather than just the write queue size.
        for exchange in self.ex_queue:
            if not exchange.started:
                exchange.request_start()


class HttpServerExchange(EventEmitter):
    """
    A request/response interaction on an HTTP server.
    """

    def __init__(self, http_conn, method, uri, req_hdrs, req_version):
        EventEmitter.__init__(self)
        self.http_conn = http_conn
        self.method = method
        self.uri = uri
        self.req_hdrs = req_hdrs
        self.req_version = req_version
        self.started = False

    def __repr__(self):
        status = [self.__class__.__module__ + "." + self.__class__.__name__]
        status.append('%s {%s}' % (self.method or "-", self.uri or "-"))
        return "<%s at %#x>" % (", ".join(status), id(self))

    def request_start(self):
        self.started = True
        self.emit('request_start', self.method, self.uri, self.req_hdrs)

    def response_start(self, status_code, status_phrase, res_hdrs):
        "Start a response. Must only be called once per response."
        res_hdrs = [i for i in res_hdrs \
                    if not i[0].lower() in hop_by_hop_hdrs ]

        try:
            body_len = int(get_header(res_hdrs, "content-length").pop(0))
        except (IndexError, ValueError):
            body_len = None
        if body_len is not None:
            delimit = COUNTED
            res_hdrs.append(("Connection", "keep-alive"))
        elif self.req_version == "1.1":
            delimit = CHUNKED
            res_hdrs.append(("Transfer-Encoding", "chunked"))
        else:
            delimit = CLOSE
            res_hdrs.append(("Connection", "close"))

        self.http_conn.output_start(
            "HTTP/1.1 %s %s" % (status_code, status_phrase),
            res_hdrs, delimit
        )

    def response_body(self, chunk):
        "Send part of the response body. May be called zero to many times."
        self.http_conn.output_body(chunk)

    def response_done(self, trailers):
        """
        Signal the end of the response, whether or not there was a body. MUST
        be called exactly once for each response.
        """
        self.http_conn.output_end(trailers)


def test_handler(x):
    @on(x, 'request_start')
    def go(*args):
        print "start: %s on %s" % (str(args[1]), id(x.http_conn))
        x.response_start(200, "OK", [])
        x.response_body('foo!')
        x.response_done([])

    @on(x, 'request_body')
    def body(chunk):
        print "body: %s" % chunk

    @on(x, 'request_done')
    def done(trailers):
        print "done: %s" % str(trailers)


if __name__ == "__main__":
    from thor.loop import run
    sys.stderr.write("PID: %s\n" % os.getpid())
    h, p = '127.0.0.1', int(sys.argv[1])
    demo_server = HttpServer(h, p)
    demo_server.on('exchange', test_handler)
    run()

########NEW FILE########
__FILENAME__ = loop
#!/usr/bin/env python

"""
Asynchronous event loops

This is a generic library for building asynchronous event loops, using
Python 2.6+'s built-in poll / epoll / kqueue support.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2005-2013 Mark Nottingham

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

import bisect
import select
import sys
import time as systime

from thor.events import EventEmitter

assert sys.version_info[0] == 2 and sys.version_info[1] >= 6, \
    "Please use Python 2.6 or greater"

__all__ = ['run', 'stop', 'schedule', 'time', 'running', 'debug']


class EventSource(EventEmitter):
    """
    Base class for objects that the loop will direct interesting
    events to.

    An instance should map to one thing with an interesting file
    descriptor, registered with register_fd.
    """
    def __init__(self, loop=None):
        EventEmitter.__init__(self)
        self._loop = loop or _loop
        self._interesting_events = set()
        self._fd = None

    def register_fd(self, fd, event=None):
        """
        Register myself with the loop using file descriptor fd.
        If event is specified, start emitting it.
        """
        self._fd = fd
        self._loop.register_fd(self._fd, [], self)
        self.event_add(event)

    def unregister_fd(self):
        "Unregister myself from the loop."
        if self._fd:
            self._loop.unregister_fd(self._fd)
            self._fd = None

    def event_add(self, event):
        "Start emitting the given event."
        if event and event not in self._interesting_events:
            self._interesting_events.add(event)
            self._loop.event_add(self._fd, event)

    def event_del(self, event):
        "Stop emitting the given event."
        if event in self._interesting_events:
            self._interesting_events.remove(event)
            self._loop.event_del(self._fd, event)


class LoopBase(EventEmitter):
    """
    Base class for async loops.
    """
    _event_types = {} # map of event types to names; override.

    def __init__(self, precision=None):
        EventEmitter.__init__(self)
        self.precision = precision or .5 # of running scheduled queue (secs)
        self.running = False # whether or not the loop is running (read-only)
        self.__sched_events = []
        self._fd_targets = {}
        self.__now = None
        self._eventlookup = dict(
            [(v,k) for (k,v) in self._event_types.items()]
        )
        self.__event_cache = {}

    def run(self):
        "Start the loop."
        self.running = True
        last_event_check = 0
        self.__now = systime.time()
        self.emit('start')
        while self.running:
            if debug:
                fd_start = systime.time()
            self._run_fd_events()
            self.__now = systime.time()
            if debug:
                delay = self.__now - fd_start
                if delay >= self.precision * 1.5:
                    sys.stderr.write(
                     "WARNING: long fd delay (%.2f)\n" % delay
                    )
            # find scheduled events
            if not self.running:
                break
            delay = self.__now - last_event_check
            if delay >= self.precision * 0.90:
                if debug:
                    if last_event_check and (delay >= self.precision * 4):
                        sys.stderr.write(
                          "WARNING: long loop delay (%.2f)\n" % delay
                        )
                    if len(self.__sched_events) > 5000:
                        sys.stderr.write(
                          "WARNING: %i events scheduled\n" % \
                            len(self.__sched_events))
                last_event_check = self.__now
                for event in self.__sched_events:
                    when, what = event
                    if self.__now >= when:
                        try:
                            self.__sched_events.remove(event)
                        except ValueError:
                            # a previous event may have removed this one.
                            continue
                        if debug:
                            ev_start = systime.time()
                        what()
                        if debug:
                            delay = systime.time() - ev_start
                            if delay > self.precision * 2:
                                sys.stderr.write(
                        "WARNING: long event delay (%.2f): %s\n" % \
                                (delay, repr(what)) 
                                )
                    else:
                        break

    def _run_fd_events(self):
        "Run loop-specific FD events."
        raise NotImplementedError

    def stop(self):
        "Stop the loop and unregister all fds."
        self.__sched_events = []
        self.__now = None
        self.running = False
        for fd in self._fd_targets.keys():
            self.unregister_fd(fd)
        self.emit('stop')

    def register_fd(self, fd, events, target):
        "emit events on target when they occur on fd."
        raise NotImplementedError

    def unregister_fd(self, fd):
        "Stop emitting events from fd."
        raise NotImplementedError

    def fd_count(self):
        "Return how many FDs are currently monitored by the loop."
        return len(self._fd_targets)

    def event_add(self, fd, event):
        "Start emitting event for fd."
        raise NotImplementedError

    def event_del(self, fd, event):
        "Stop emitting event for fd"
        raise NotImplementedError

    def _fd_event(self, event, fd):
        "An event has occured on an fd."
        if self._fd_targets.has_key(fd):
            self._fd_targets[fd].emit(event)
        # TODO: automatic unregister on 'close'?

    def time(self):
        "Return the current time (to avoid a system call)."
        return self.__now or systime.time()

    def schedule(self, delta, callback, *args):
        """
        Schedule callable callback to be run in delta seconds with *args.

        Returns an object which can be used to later remove the event, by
        calling its delete() method.
        """
        def cb():
            if callback:
                callback(*args)
        cb.__name__ = callback.__name__
        new_event = (self.time() + delta, cb)
        events = self.__sched_events
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

    def _eventmask(self, events):
        "Calculate the mask for a list of events."
        eventmask = 0
        for event in events:
            eventmask |= self._eventlookup.get(event, 0)
        return eventmask

    def _filter2events(self, evfilter):
        "Calculate the events implied by a given filter."
        if not self.__event_cache.has_key(evfilter):
            events = set()
            for et in self._event_types:
                if et & evfilter:
                    events.add(self._event_types[et])
            self.__event_cache[evfilter] = events
        return self.__event_cache[evfilter]


class PollLoop(LoopBase):
    """
    A poll()-based async loop.
    """

    def __init__(self, *args):
        # pylint: disable=E1101
        self._event_types = {
            select.POLLIN: 'readable',
            select.POLLOUT: 'writable',
            select.POLLERR: 'error',
            select.POLLHUP: 'close',
    #        select.POLLNVAL - TODO
        }
        LoopBase.__init__(self, *args)
        self._poll = select.poll()
        # pylint: enable=E1101

    def register_fd(self, fd, events, target):
        self._fd_targets[fd] = target
        self._poll.register(fd, self._eventmask(events))

    def unregister_fd(self, fd):
        self._poll.unregister(fd)
        del self._fd_targets[fd]

    def event_add(self, fd, event):
        eventmask = self._eventmask(self._fd_targets[fd]._interesting_events)
        self._poll.register(fd, eventmask)

    def event_del(self, fd, event):
        eventmask = self._eventmask(self._fd_targets[fd]._interesting_events)
        self._poll.register(fd, eventmask)

    def _run_fd_events(self):
        event_list = self._poll.poll(self.precision)
        for fileno, eventmask in event_list:
            for event in self._filter2events(eventmask):
                self._fd_event(event, fileno)


class EpollLoop(LoopBase):
    """
    An epoll()-based async loop.
    """

    def __init__(self, *args):
        # pylint: disable=E1101
        self._event_types = {
            select.EPOLLIN: 'readable',
            select.EPOLLOUT: 'writable',
            select.EPOLLHUP: 'close',
            select.EPOLLERR: 'error'
        }
        LoopBase.__init__(self, *args)
        self._epoll = select.epoll()
        # pylint: enable=E1101

    def register_fd(self, fd, events, target):
        eventmask = self._eventmask(events)
        if fd in self._fd_targets:
            self._epoll.modify(fd, eventmask)
        else:
            self._fd_targets[fd] = target
            self._epoll.register(fd, eventmask)

    def unregister_fd(self, fd):
        self._epoll.unregister(fd)
        del self._fd_targets[fd]

    def event_add(self, fd, event):
        eventmask = self._eventmask(self._fd_targets[fd]._interesting_events)
        self._epoll.modify(fd, eventmask)

    def event_del(self, fd, event):
        try:
            eventmask = self._eventmask(
                self._fd_targets[fd]._interesting_events
            )
        except KeyError:
            return # no longer interested
        self._epoll.modify(fd, eventmask)

    def _run_fd_events(self):
        event_list = self._epoll.poll(self.precision)
        for fileno, eventmask in event_list:
            for event in self._filter2events(eventmask):
                self._fd_event(event, fileno)


class KqueueLoop(LoopBase):
    """
    A kqueue()-based async loop.
    """
    def __init__(self, *args):
        self._event_types = {
            select.KQ_FILTER_READ: 'readable',
            select.KQ_FILTER_WRITE: 'writable'
        }
        LoopBase.__init__(self, *args)
        self.max_ev = 50 # maximum number of events to pull from the queue
        self._kq = select.kqueue()

    # TODO: override schedule() to use kqueue event scheduling.

    def register_fd(self, fd, events, target):
        self._fd_targets[fd] = target
        for event in events:
            self.event_add(fd, event)

    def unregister_fd(self, fd):
        try:
            obj = self._fd_targets[fd]
        except KeyError:
            return
        for event in list(obj._interesting_events):
            obj.event_del(event)
        del self._fd_targets[fd]

    def event_add(self, fd, event):
        eventmask = self._eventmask([event])
        if eventmask:
            ev = select.kevent(fd, eventmask,
                select.KQ_EV_ADD | select.KQ_EV_ENABLE
            )
            self._kq.control([ev], 0, 0)

    def event_del(self, fd, event):
        eventmask = self._eventmask([event])
        if eventmask:
            ev = select.kevent(fd, eventmask, select.KQ_EV_DELETE)
            self._kq.control([ev], 0, 0)

    def _run_fd_events(self):
        events = self._kq.control([], self.max_ev, self.precision)
        for e in events:
            event_types = self._filter2events(e.filter)
            for event_type in event_types:
                self._fd_event(event_type, int(e.ident))
            if e.flags & select.KQ_EV_EOF:
                self._fd_event('close', int(e.ident))
            if e.flags & select.KQ_EV_ERROR:
                pass
            # TODO: pull errors, etc. out of flags and fflags
            #   If the read direction of the socket has shutdown, then
    		#	the filter also sets EV_EOF in flags, and returns the
    		#	socket error (if any) in fflags.  It is possible for
    		#	EOF to be returned (indicating the connection is gone)
    		#	while there is still data pending in the socket
    		#	buffer.


def make(precision=None):
    """
    Create and return a named loop that is suitable for the current system. If
    _precision_ is given, it indicates how often scheduled events will be run.

    Returned loop instances have all of the methods and instance variables
    that *thor.loop* has.
    """
    if hasattr(select, 'epoll'):
        loop = EpollLoop(precision)
    elif hasattr(select, 'kqueue'):
        loop = KqueueLoop(precision)
    elif hasattr(select, 'poll'):
        loop = PollLoop(precision)
    else:
        # TODO: select()-based loop (I suppose)
        raise ImportError, "What is this thing, a Windows box?"
    return loop

_loop = make() # by default, just one big loop.
run = _loop.run
stop = _loop.stop
schedule = _loop.schedule
time = _loop.time
running = _loop.running
debug = False
########NEW FILE########
__FILENAME__ = tcp
#!/usr/bin/env python

"""
push-based asynchronous TCP

This is a generic library for building event-based / asynchronous
TCP servers and clients.

It uses a push model; i.e., the network connection pushes data to
you (using a 'data' event), and you push data to the network connection
(using the write method).
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2005-2013 Mark Nottingham

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
import sys
import socket

from thor.loop import EventSource, schedule


class TcpConnection(EventSource):
    """
    An asynchronous TCP connection.

    Emits:
     - data (chunk): incoming data
     - close (): the other party has closed the connection
     - pause (bool): whether the connection has been paused

    It will emit the 'data' even every time incoming data is
    available;

    > def process(data):
    >   print "got some data:", data
    > tcp_conn.on('data', process)

    When you want to write to the connection, just write to it:

    > tcp_conn.write(data)

    If you want to close the connection from your side, just call close:

    > tcp_conn.close()

    Note that this will flush any data already written.

    If the other side closes the connection, The 'close' event will be
    emitted;

    > def handle_close():
    >   print "oops, they don't like us any more..."
    > tcp_conn.on('close', handle_close)

    If you write too much data to the connection and the buffers fill up,
    pause_cb will be emitted with True to tell you to stop sending data
    temporarily;

    > def handle_pause(paused):
    >   if paused:
    >       # stop sending data
    >   else:
    >       # it's OK to start again
    > tcp_conn.on('pause', handle_pause)

    Note that this is advisory; if you ignore it, the data will still be
    buffered, but the buffer will grow.

    Likewise, if you want to pause the connection because your buffers
    are full, call pause;

    > tcp_conn.pause(True)

    but don't forget to tell it when it's OK to send data again;

    > tcp_conn.pause(False)

    NOTE that connections are paused to start with; if you want to start
    getting data from them, you'll need to pause(False).
    """

    # TODO: play with various buffer sizes
    write_bufsize = 16
    read_bufsize = 1024 * 16

    _block_errs = set([(socket.error, e) for e in [
        errno.EAGAIN, errno.EWOULDBLOCK, errno.ETIMEDOUT
    ]])
    _close_errs = set([(socket.error, e) for e in [
        errno.EBADF, errno.ECONNRESET, errno.ESHUTDOWN,
        errno.ECONNABORTED, errno.ECONNREFUSED,
        errno.ENOTCONN, errno.EPIPE
    ]])

    def __init__(self, sock, host, port, loop=None):
        EventSource.__init__(self, loop)
        self.socket = sock
        self.host = host
        self.port = port
        self.tcp_connected = True # we assume a connected socket
        self._input_paused = True # we start with input paused
        self._output_paused = False
        self._closing = False
        self._write_buffer = []

        self.register_fd(sock.fileno())
        self.on('readable', self.handle_read)
        self.on('writable', self.handle_write)
        self.on('close', self.handle_close)

    def __repr__(self):
        status = [self.__class__.__module__ + "." + self.__class__.__name__]
        status.append(self.tcp_connected and 'connected' or 'disconnected')
        status.append('%s:%s' % (self.host, self.port))
        if self._input_paused:
            status.append('input paused')
        if self._output_paused:
            status.append('output paused')
        if self._closing:
            status.append('closing')
        if self._write_buffer:
            status.append('%s write buffered' % len(self._write_buffer))
        return "<%s at %#x>" % (", ".join(status), id(self))

    def handle_read(self):
        "The connection has data read for reading"
        try:
            # TODO: look into recv_into (but see python issue7827)
            data = self.socket.recv(self.read_bufsize)
        except Exception, why:
            err = (type(why), why[0])
            if err in self._block_errs:
                return
            elif err in self._close_errs:
                self.emit('close')
                return
            else:
                raise
        if data == "":
            self.emit('close')
        else:
            self.emit('data', data)

    # TODO: try using buffer; see
    # http://itamarst.org/writings/pycon05/fast.html
    def handle_write(self):
        "The connection is ready for writing; write any buffered data."
        if len(self._write_buffer) > 0:
            data = "".join(self._write_buffer)
            try:
                sent = self.socket.send(data)
            except Exception, why:
                err = (type(why), why[0])
                if err in self._block_errs:
                    return
                elif err in self._close_errs:
                    self.emit('close')
                    return
                else:
                    raise
            if sent < len(data):
                self._write_buffer = [data[sent:]]
            else:
                self._write_buffer = []
        if self._output_paused and \
          len(self._write_buffer) < self.write_bufsize:
            self._output_paused = False
            self.emit('pause', False)
        if self._closing:
            self.close()
        if len(self._write_buffer) == 0:
            self.event_del('writable')

    def handle_close(self):
        """
        The connection has been closed by the other side.
        """
        self.tcp_connected = False
        # TODO: make sure removing close doesn't cause problems.
        self.removeListeners('readable', 'writable', 'close')
        self.unregister_fd()
        self.socket.close()

    def write(self, data):
        "Write data to the connection."
        self._write_buffer.append(data)
        if len(self._write_buffer) > self.write_bufsize:
            self._output_paused = True
            self.emit('pause', True)
        self.event_add('writable')

    def pause(self, paused):
        """
        Temporarily stop/start reading from the connection and pushing
        it to the app.
        """
        if paused:
            self.event_del('readable')
        else:
            self.event_add('readable')
        self._input_paused = paused

    def close(self):
        "Flush buffered data (if any) and close the connection."
        self.pause(True)
        if len(self._write_buffer) > 0:
            self._closing = True
        else:
            self.handle_close()

        # TODO: should loop stop automatically close all conns?

class TcpServer(EventSource):
    """
    An asynchronous TCP server.

    Emits:
      - connect (tcp_conn): upon connection

    To start listening:

    > s = TcpServer(host, port)
    > s.on('connect', conn_handler)

    conn_handler is called every time a new client connects.
    """
    def __init__(self, host, port, sock=None, loop=None):
        EventSource.__init__(self, loop)
        self.host = host
        self.port = port
        self.sock = sock or server_listen(host, port)
        self.on('readable', self.handle_accept)
        self.register_fd(self.sock.fileno(), 'readable')
        schedule(0, self.emit, 'start')

    def handle_accept(self):
        try:
            conn, addr = self.sock.accept()
        except (TypeError, IndexError):
            # sometimes accept() returns None if we have
            # multiple processes listening
            return
        conn.setblocking(False)
        tcp_conn = TcpConnection(conn, self.host, self.port, self._loop)
        self.emit('connect', tcp_conn)

    # TODO: should loop stop close listening sockets?

    def shutdown(self):
        "Stop accepting requests and close the listening socket."
        self.removeListeners('readable')
        self.sock.close()
        self.emit('stop')
        # TODO: emit close?


def server_listen(host, port, backlog=None):
    "Return a socket listening to host:port."
    # TODO: IPV6
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(backlog or socket.SOMAXCONN)
    return sock


class TcpClient(EventSource):
    """
    An asynchronous TCP client.

    Emits:
      - connect (tcp_conn): upon connection
      - connect_error (err_type, err_id, err_str): if there's a problem
        before getting a connection. err_type is socket.error or
        socket.gaierror; err_id is the specific error encountered, and
        err_str is its textual description.

    To connect to a server:

    > c = TcpClient()
    > c.on('connect', conn_handler)
    > c.on('connect_error', error_handler)
    > c.connect(host, port)

    conn_handler will be called with the tcp_conn as the argument
    when the connection is made.
    """
    def __init__(self, loop=None):
        EventSource.__init__(self, loop)
        self.host = None
        self.port = None
        self._timeout_ev = None
        self._error_sent = False
        # TODO: IPV6
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.on('error', self.handle_conn_error)
        self.register_fd(self.sock.fileno(), 'writable')
        self.event_add('error')


    def connect(self, host, port, connect_timeout=None):
        """
        Connect to host:port (with an optional connect timeout)
        and emit 'connect' when connected, or 'connect_error' in
        the case of an error.
        """
        self.host = host
        self.port = port
        self.on('writable', self.handle_connect)
        # TODO: use socket.getaddrinfo(); needs to be non-blocking.
        try:
            err = self.sock.connect_ex((host, port))
        except socket.gaierror, why:
            self.handle_conn_error(socket.gaierror, why)
            return
        except socket.error, why:
            self.handle_conn_error(socket.error, why)
            return
        if err != errno.EINPROGRESS:
            self.handle_conn_error(socket.error, [err, os.strerror(err)])
            return
        if connect_timeout:
            self._timeout_ev = self._loop.schedule(
                connect_timeout,
                self.handle_conn_error,
                socket.error,
                [errno.ETIMEDOUT, os.strerror(errno.ETIMEDOUT)],
                True
            )

    def handle_connect(self):
        self.unregister_fd()
        if self._timeout_ev:
            self._timeout_ev.delete()
        if self._error_sent:
            return
        err = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err:
            self.handle_conn_error(socket.error, [err, os.strerror(err)])
        else:
            tcp_conn = TcpConnection(
                self.sock, self.host, self.port, self._loop
            )
            self.emit('connect', tcp_conn)

    def handle_conn_error(self, err_type=None, why=None, close=False):
        """
        Handle a connect error.

        @err_type - e.g., socket.error; defaults to socket.error
        @why - tuple of [err_id, err_str]
        @close - whether the error means the socket should be closed
        """
        if self._timeout_ev:
            self._timeout_ev.delete()
        if self._error_sent:
            return
        if err_type is None:
            err_type = socket.error
            err_id = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            err_str = os.strerror(err_id)
        else:
            err_id = why[0]
            err_str = why[1]
        self._error_sent = True
        self.unregister_fd()
        self.emit('connect_error', err_type, err_id, err_str)
        if close:
            self.sock.close()


if __name__ == "__main__":
    # quick demo server
    from thor.loop import run, stop
    server = TcpServer('localhost', int(sys.argv[-1]))
    def handle_conn(conn):
        conn.pause(False)
        def echo(chunk):
            if chunk.strip().lower() in ['quit', 'stop']:
                stop()
            else:
                conn.write("-> %s" % chunk)
        conn.on('data', echo)
    server.on('connect', handle_conn)
    run()



########NEW FILE########
__FILENAME__ = tls
#!/usr/bin/env python


"""
push-based asynchronous SSL/TLS-over-TCP

This is a generic library for building event-based / asynchronous
SSL/TLS servers and clients.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2005-2013 Mark Nottingham

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
import socket
import ssl as sys_ssl

from thor.tcp import TcpServer, TcpClient, TcpConnection, server_listen

TcpConnection._block_errs.add((sys_ssl.SSLError, sys_ssl.SSL_ERROR_WANT_READ))
TcpConnection._block_errs.add(
                        (sys_ssl.SSLError, sys_ssl.SSL_ERROR_WANT_WRITE)
)
TcpConnection._close_errs.add((sys_ssl.SSLError, sys_ssl.SSL_ERROR_EOF))
TcpConnection._close_errs.add((sys_ssl.SSLError, sys_ssl.SSL_ERROR_SSL))

# TODO: TlsServer
# TODO: expose cipher info, peer info

class TlsClient(TcpClient):
    """
    An asynchronous SSL/TLS client.

    Emits:
      - connect (tcp_conn): upon connection
      - connect_error (err_type, err): if there's a problem before getting
        a connection. err_type is socket.error or socket.gaierror; err
        is the specific error encountered.

    To connect to a server:

    > c = TlsClient()
    > c.on('connect', conn_handler)
    > c.on('connect_error', error_handler)
    > c.connect(host, port)

    conn_handler will be called with the tcp_conn as the argument
    when the connection is made.
    """
    def __init__(self, loop=None):
        TcpClient.__init__(self, loop)
        # FIXME: CAs
        self.sock = sys_ssl.wrap_socket(
            self.sock, 
            cert_reqs=sys_ssl.CERT_NONE,
            do_handshake_on_connect=False
        )

    def handshake(self):
        try:
            self.sock.do_handshake()
            self.once('writable', self.handle_connect)
        except sys_ssl.SSLError, why:
            if why[0] == sys_ssl.SSL_ERROR_WANT_READ:
#                self.once('readable', self.handshake)
                self.once('writable', self.handshake) # Oh, Linux...
            elif why[0] == sys_ssl.SSL_ERROR_WANT_WRITE:
                self.once('writable', self.handshake)
            else:
                self.handle_conn_error(sys_ssl.SSLError, why)
        except socket.error, why:
            self.handle_conn_error(socket.error, why)

    # TODO: refactor into tcp.py
    def connect(self, host, port, connect_timeout=None):
        """
        Connect to host:port (with an optional connect timeout)
        and emit 'connect' when connected, or 'connect_error' in
        the case of an error.
        """
        self.host = host
        self.port = port
        self.once('writable', self.handshake)
        # TODO: use socket.getaddrinfo(); needs to be non-blocking.
        try:
            err = self.sock.connect_ex((host, port))
        except socket.gaierror, why:
            self.handle_conn_error(socket.gaierror, why)
            return
        except socket.error, why:
            self.handle_conn_error(socket.error, why)
            return
        if err != errno.EINPROGRESS:
            self.handle_conn_error(socket.error, [err, os.strerror(err)])
            return
        if connect_timeout:
            self._timeout_ev = self._loop.schedule(
                connect_timeout,
                self.handle_conn_error,
                socket.error,
                [errno.ETIMEDOUT, os.strerror(errno.ETIMEDOUT)],
                True
            )

def monkey_patch_ssl():
    """
    Oh, god, I feel dirty.
    
    See Python bug 11326.
    """
    if not hasattr(sys_ssl.SSLSocket, '_real_connect'):
        import _ssl
        def _real_connect(self, addr, return_errno):
            if self._sslobj:
                raise ValueError(
                    "attempt to connect already-connected SSLSocket!"
                )
            self._sslobj = _ssl.sslwrap(self._sock, False, self.keyfile,
                self.certfile, self.cert_reqs, self.ssl_version,
                self.ca_certs, self.ciphers)
            try:
                socket.socket.connect(self, addr)
                if self.do_handshake_on_connect:
                    self.do_handshake()
            except socket.error as e:
                if return_errno:
                    return e.errno
                else:
                    self._sslobj = None
                    raise e
            return 0
        def connect(self, addr):
            self._real_connect(addr, False)
        def connect_ex(self, addr):
            return self._real_connect(addr, True)
        sys_ssl.SSLSocket._real_connect = _real_connect
        sys_ssl.SSLSocket.connect = connect
        sys_ssl.SSLSocket.connect_ex = connect_ex
monkey_patch_ssl()


if __name__ == "__main__":
    import sys
    from thor import run
    test_host = sys.argv[1]

    def go(conn):
        conn.on('data', sys.stdout.write)
        conn.write("GET / HTTP/1.1\r\nHost: %s\r\n\r\n" % test_host)
        conn.pause(False)
        print conn.socket.cipher()

    c = TlsClient()
    c.on('connect', go)
    c.connect(test_host, 443)
    run()
########NEW FILE########
__FILENAME__ = udp
#!/usr/bin/env python

"""
push-based asynchronous UDP

This is a generic library for building event-based / asynchronous
UDP servers and clients.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2011-2013 Mark Nottingham

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
import socket

from thor.loop import EventSource




class UdpEndpoint(EventSource):
    """
    An asynchronous UDP endpoint.

    Emits:
      - datagram (data, address): upon recieving a datagram.

    To start:

    > s = UdpEndpoint(host, port)
    > s.on('datagram', datagram_handler)
    """
    recv_buffer = 8192
    _block_errs = set([
        errno.EAGAIN, errno.EWOULDBLOCK
    ])

    def __init__(self, loop=None):
        EventSource.__init__(self, loop)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.max_dgram = min((2**16 - 40), self.sock.getsockopt(
            socket.SOL_SOCKET, socket.SO_SNDBUF
        ))
        self.on('readable', self.handle_datagram)
        self.register_fd(self.sock.fileno())

    def bind(self, host, port):
        """
        Bind the socket bound to host:port. If called, must be before
        sending or receiving.

        Can raise socket.error if binding fails.
        """
        # TODO: IPV6
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))

    def shutdown(self):
        "Close the listening socket."
        self.removeListeners('readable')
        self.sock.close()
        # TODO: emit close?

    def pause(self, paused):
        "Control incoming datagram events."
        if paused:
            self.event_del('readable')
        else:
            self.event_add('readable')

    def send(self, datagram, host, port):
        "send datagram to host:port."
        try:
            self.sock.sendto(datagram, (host, port))
        except socket.error, why:
            if why[0] in self._block_errs:
                pass # we drop these on the floor. It's UDP, after all.
            else:
                raise

    def handle_datagram(self):
        "Handle an incoming datagram, emitting the 'datagram' event."
        # TODO: consider pre-allocating buffers.
        # TODO: is it best to loop here?
        while True:
            try:
                data, addr = self.sock.recvfrom(self.recv_buffer)
            except socket.error, why:
                if why[0] in self._block_errs:
                    break
                else:
                    raise
            self.emit('datagram', data, addr[0], addr[1])

########NEW FILE########
