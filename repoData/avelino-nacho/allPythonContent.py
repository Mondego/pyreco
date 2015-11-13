__FILENAME__ = main
#!/usr/bin/env python3
import logging
import sys

assert sys.version >= '3.3', 'Please use Python 3.3 or higher.'

from nacho.routing import Router
from nacho.http import HttpServer
from nacho.multithreading import Superviser
from nacho.app import Application, StaticFile


class Home(Application):
    def get(self, request_args=None):
        data = {'title': 'Nacho Application Server'}
        self.render('home.html', **data)


def urls():
    router = Router()
    router.add_handler('/static/',
                       StaticFile('/Users/avelino/projects/nacho/example/'))
    router.add_handler('/(.*)', Home())
    return HttpServer(router, debug=True, keep_alive=75)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    superviser = Superviser()
    superviser.start(urls)
########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python3
import cgi
import os
import tulip
import tulip.http
import email.message
from urllib.parse import urlparse
from tulip.http.errors import HttpErrorException

from nacho.renderers.quik import QuikWorker


class Application(object):

    template_dirs = ['html']
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options', 'trace']

    def __init__(self, write_headers=True):
        self.response = None
        self.write_headers = write_headers
        self.renderer = QuikWorker(self.template_dirs)

    def initialize(self, server, message, payload, prev_response=None):
        self.server = server
        self.request = message
        self.payload = payload
        self.prev_response = prev_response
        if self.write_headers:
            self.response = self._write_headers()

    def __call__(self, request_args=None):
        if self.request.method.lower() in self.http_method_names:
            handler = getattr(self, self.request.method.lower(), None)
            if handler:
                return handler()
        self.response.write(b'nacho: base handler')
        return self.response

    @property
    def query(self):
        parsed = urlparse(self.request.path)
        querydict = cgi.parse_qs(parsed.query)
        for key, value in querydict.items():
            if isinstance(value, list) and len(value) < 2:
                querydict[key] = value[0] if value else None
        return querydict

    def _write_headers(self):
        headers = email.message.Message()
        response = tulip.http.Response(
            self.server.transport, 200, close=True)
        response.add_header('Transfer-Encoding', 'chunked')

        # content encoding
        accept_encoding = headers.get('accept-encoding', '').lower()
        if 'deflate' in accept_encoding:
            response.add_header('Content-Encoding', 'deflate')
            response.add_compression_filter('deflate')
        elif 'gzip' in accept_encoding:
            response.add_header('Content-Encoding', 'gzip')
            response.add_compression_filter('gzip')

        response.add_chunking_filter(1025)

        response.add_header('Content-type', 'text/html')
        response.send_headers()
        return response

    def render(self, template_name, **kwargs):
        self.response.write(self.renderer.render(template_name, **kwargs))


class StaticFile(Application):
    def __init__(self, staticroot):
        super(StaticFile, self).__init__(write_headers=False)
        self.staticroot = staticroot

    def __call__(self, request_args=None):
        path = self.staticroot
        if not os.path.exists(path):
            print('no file', repr(path))
            path = None
        else:
            isdir = os.path.isdir(path)

        if not path:
            raise HttpErrorException(404, message="Path not found")

        headers = email.message.Message()
        response = tulip.http.Response(
            self.server.transport, 200, close=True)
        response.add_header('Transfer-Encoding', 'chunked')

        if isdir:
            response.add_header('Content-type', 'text/html')
            response.send_headers()

            response.write(b'<ul>\r\n')
            for name in sorted(os.listdir(path)):
                if name.isprintable() and not name.startswith('.'):
                    try:
                        bname = name.encode('ascii')
                    except UnicodeError:
                        pass
                    else:
                        if os.path.isdir(os.path.join(path, name)):
                            response.write(b'<li><a href="' + bname +
                                           b'/">' + bname + b'/</a></li>\r\n')
                        else:
                            response.write(b'<li><a href="' + bname +
                                           b'">' + bname + b'</a></li>\r\n')
            response.write(b'</ul>')
        else:
            response.add_header('Content-type', 'text/plain')
            response.send_headers()

            try:
                with open(path, 'rb') as fp:
                    chunk = fp.read(8196)
                    while chunk:
                        response.write(chunk)
                        chunk = fp.read(8196)
            except OSError:
                response.write(b'Cannot open')
        return response

########NEW FILE########
__FILENAME__ = http
#!/usr/bin/env python3
import logging

import tulip
from tulip.http import ServerHttpProtocol
from tulip.http.errors import HttpErrorException

class HttpServer(ServerHttpProtocol):
    def __init__(self, router, *args, **kwargs):
        super(HttpServer, self).__init__(*args, **kwargs)
        self.router = router

    @tulip.coroutine
    def handle_request(self, message, payload):
        response = None
        logging.debug('method = {!r}; path = {!r}; version = {!r}'.format(
            message.method, message.path, message.version))

        handlers, args = self.router.get_handler(message.path)
        if handlers:
            for handler in handlers:
                logging.debug("handler: %s", handler)
                handler.initialize(self, message, payload, prev_response=response)
                result = handler(request_args=args)
                response = handler.response
            if not response:
                raise HttpErrorException(404, message="No Handler found")
        else:
            raise HttpErrorException(404)

        response.write_eof()
        if response.keep_alive():
            self.keep_alive(True)

########NEW FILE########
__FILENAME__ = multithreading
#!/usr/bin/env python3
import os
import socket
import signal
import time
import tulip
import argparse
import tulip.http
from tulip.http import websocket
try:
    import ssl
except ImportError:  # pragma: no cover
    ssl = None


ARGS = argparse.ArgumentParser(description="Run simple http server.")
ARGS.add_argument(
    '--host', action="store", dest='host',
    default='127.0.0.1', help='Host name')
ARGS.add_argument(
    '--port', action="store", dest='port',
    default=7000, type=int, help='Port number')
ARGS.add_argument(
    '--iocp', action="store_true", dest='iocp', help='Windows IOCP event loop')
ARGS.add_argument(
    '--ssl', action="store_true", dest='ssl', help='Run ssl mode.')
ARGS.add_argument(
    '--sslcert', action="store", dest='certfile', help='SSL cert file.')
ARGS.add_argument(
    '--sslkey', action="store", dest='keyfile', help='SSL key file.')
ARGS.add_argument(
    '--workers', action="store", dest='workers',
    default=1, type=int, help='Number of workers.')
ARGS.add_argument(
    '--staticroot', action="store", dest='staticroot',
    default='./static/', type=str, help='Static root.')


class ChildProcess:

    def __init__(self, up_read, down_write, args, sock, protocol_factory, ssl):
        self.up_read = up_read
        self.down_write = down_write
        self.args = args
        self.sock = sock
        self.protocol_factory = protocol_factory
        self.ssl = ssl

    def start(self):
        # start server
        self.loop = loop = tulip.new_event_loop()
        tulip.set_event_loop(loop)

        def stop():
            self.loop.stop()
            os._exit(0)
        loop.add_signal_handler(signal.SIGINT, stop)

        f = loop.start_serving(
            self.protocol_factory, sock=self.sock, ssl=self.ssl)
        x = loop.run_until_complete(f)[0]
        print('Starting srv worker process {} on {}'.format(
            os.getpid(), x.getsockname()))

        # heartbeat
        self.heartbeat()

        tulip.get_event_loop().run_forever()
        os._exit(0)

    @tulip.task
    def heartbeat(self):
        # setup pipes
        read_transport, read_proto = yield from self.loop.connect_read_pipe(
            tulip.StreamProtocol, os.fdopen(self.up_read, 'rb'))
        write_transport, _ = yield from self.loop.connect_write_pipe(
            tulip.StreamProtocol, os.fdopen(self.down_write, 'wb'))

        reader = read_proto.set_parser(websocket.WebSocketParser())
        writer = websocket.WebSocketWriter(write_transport)

        while True:
            msg = yield from reader.read()
            if msg is None:
                print('Superviser is dead, {} stopping...'.format(os.getpid()))
                self.loop.stop()
                break
            elif msg.tp == websocket.MSG_PING:
                writer.pong()
            elif msg.tp == websocket.MSG_CLOSE:
                break

        read_transport.close()
        write_transport.close()


class Worker:

    _started = False

    def __init__(self, loop, args, sock, protocol_factory, ssl):
        self.loop = loop
        self.args = args
        self.sock = sock
        self.protocol_factory = protocol_factory
        self.ssl = ssl
        self.start()

    def start(self):
        assert not self._started
        self._started = True

        up_read, up_write = os.pipe()
        down_read, down_write = os.pipe()
        args, sock = self.args, self.sock

        pid = os.fork()
        if pid:
            # parent
            os.close(up_read)
            os.close(down_write)
            self.connect(pid, up_write, down_read)
        else:
            # child
            os.close(up_write)
            os.close(down_read)

            # cleanup after fork
            tulip.set_event_loop(None)

            # setup process
            process = ChildProcess(up_read, down_write, args, sock, 
                                   self.protocol_factory, self.ssl)
            process.start()

    @tulip.task
    def heartbeat(self, writer):
        while True:
            yield from tulip.sleep(15)

            if (time.monotonic() - self.ping) < 30:
                writer.ping()
            else:
                print('Restart unresponsive worker process: {}'.format(
                    self.pid))
                self.kill()
                self.start()
                return

    @tulip.task
    def chat(self, reader):
        while True:
            msg = yield from reader.read()
            if msg is None:
                print('Restart unresponsive worker process: {}'.format(
                    self.pid))
                self.kill()
                self.start()
                return
            elif msg.tp == websocket.MSG_PONG:
                self.ping = time.monotonic()

    @tulip.task
    def connect(self, pid, up_write, down_read):
        # setup pipes
        read_transport, proto = yield from self.loop.connect_read_pipe(
            tulip.StreamProtocol, os.fdopen(down_read, 'rb'))
        write_transport, _ = yield from self.loop.connect_write_pipe(
            tulip.StreamProtocol, os.fdopen(up_write, 'wb'))

        # websocket protocol
        reader = proto.set_parser(websocket.WebSocketParser())
        writer = websocket.WebSocketWriter(write_transport)

        # store info
        self.pid = pid
        self.ping = time.monotonic()
        self.rtransport = read_transport
        self.wtransport = write_transport
        self.chat_task = self.chat(reader)
        self.heartbeat_task = self.heartbeat(writer)

    def kill(self):
        self._started = False
        self.chat_task.cancel()
        self.heartbeat_task.cancel()
        self.rtransport.close()
        self.wtransport.close()
        os.kill(self.pid, signal.SIGTERM)


class Superviser:

    def __init__(self):
        self.loop = tulip.get_event_loop()
        args = ARGS.parse_args()
        if ':' in args.host:
            args.host, port = args.host.split(':', 1)
            args.port = int(port)

        if args.iocp:
            from tulip import windows_events
            sys.argv.remove('--iocp')
            logging.info('using iocp')
            el = windows_events.ProactorEventLoop()
            tulip.set_event_loop(el)

        if args.ssl:
            here = os.path.join(os.path.dirname(__file__), 'tests')

            if args.certfile:
                certfile = args.certfile or os.path.join(here, 'sample.crt')
                keyfile = args.keyfile or os.path.join(here, 'sample.key')
            else:
                certfile = os.path.join(here, 'sample.crt')
                keyfile = os.path.join(here, 'sample.key')

            sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            sslcontext.load_cert_chain(certfile, keyfile)
        else:
            sslcontext = None
        self.ssl = sslcontext

        self.args = args
        self.workers = []

    def start(self, protocol_factory):
        # bind socket
        sock = self.sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.args.host, self.args.port))
        sock.listen(1024)
        sock.setblocking(False)

        # start processes
        for idx in range(self.args.workers):
            self.workers.append(Worker(self.loop, self.args, sock, protocol_factory, self.ssl))

        self.loop.add_signal_handler(signal.SIGINT, lambda: self.loop.stop())
        self.loop.run_forever()

########NEW FILE########
__FILENAME__ = jinja2
#!/usr/bin/env python3
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


class Jinja2Worker(object):

    def __init__(self, template_dirs=['html']):
        self.template_dirs = template_dirs

    def render(self, template_name, *args, **kwargs):
        env = Environment(loader=FileSystemLoader(self.template_dirs))
        try:
            template = env.get_template(template_name)
        except TemplateNotFound:
            raise TemplateNotFound(template_name)

        return template.render(kwargs).encode('utf-8')

########NEW FILE########
__FILENAME__ = quik
#!/usr/bin/env python3
from quik import FileLoader


class QuikWorker(object):

    def __init__(self, template_dirs=['html']):
        self.template_dirs = template_dirs

    def render(self, template_name, *args, **kwargs):
        loader = FileLoader(self.template_dirs[0])
        template = loader.load_template(template_name)
        return template.render(kwargs, loader=loader).encode('utf-8')

########NEW FILE########
__FILENAME__ = routing
import re
import collections

class Router(object):
    def __init__(self, handlers=None):
        self.handlers = handlers or []

    def add_handler(self, url_regex, handlers):
        self.handlers.append(
            (re.compile(url_regex), 
             handlers if isinstance(handlers, collections.Iterable) 
             else [handlers]))

    def get_handler(self, url):
        for matcher, handler in self.handlers:
            match = matcher.match(url)
            if match:
                return handler, match.groups()
        return None, None

########NEW FILE########
__FILENAME__ = http_server_test
#!/usr/bin/env python3
import unittest
import unittest.mock
import re

import tulip
from tulip.http import server, errors
from tulip.test_utils import run_briefly
from nacho.http import HttpServer
from nacho.routing import Router


class MockHttpServer(HttpServer):
    """Wrap server class with mocking support
    """
    def handle_error(self, *args, **kwargs):
        if self.transport.__class__.__name__ == 'Mock':
            self.transport.reset_mock()
        super(HttpServer, self).handle_error(*args, **kwargs)


class HttpServerTest(unittest.TestCase):
    def setUp(self):
        self.loop = tulip.new_event_loop()
        tulip.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_handle_request(self):
        transport = unittest.mock.Mock()
        srv = MockHttpServer(Router())
        srv.connection_made(transport)
        rline = unittest.mock.Mock()
        rline.version = (1, 1)
        message = unittest.mock.Mock()
        srv.handle_request(rline, message)
        srv.stream.feed_data(
            b'GET / HTTP/1.0\r\n'
            b'Host: example.com\r\n\r\n')
        self.loop.run_until_complete(srv._request_handler)

        content = b''.join([c[1][0] for c in list(transport.write.mock_calls)])
        self.assertTrue(content.startswith(b'HTTP/1.1 404 Not Found\r\n'))

    def _base_handler_test(self, urlregx, handler, testcontent, url=b'/',
                           expected_code=200):
        transport = unittest.mock.Mock()
        router = Router()
        router.add_handler(
            urlregx, handler)
        srv = MockHttpServer(router)
        srv.connection_made(transport)
        rline = unittest.mock.Mock()
        rline.version = (1, 1)
        message = unittest.mock.Mock()
        srv.handle_request(rline, message)
        srv.stream.feed_data(b'GET ')
        srv.stream.feed_data(url)
        srv.stream.feed_data(b' HTTP/1.0\r\n'
            b'Host: example.com\r\n\r\n')
        self.loop.run_until_complete(srv._request_handler)

        header = transport.write.mock_calls[0][1][0].decode('utf-8')
        code = int(re.match("^HTTP/1.1 (\d+) ", header).groups()[0])
        self.assertEquals(code, expected_code, )
        headers = re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", header)
        content = b''.join([c[1][0] for c in list(transport.write.mock_calls)[2:-2]])
        self.assertEqual(content, testcontent)
        transport = None


class HttpServerProtocolTests(unittest.TestCase):

    def setUp(self):
        self.loop = tulip.new_event_loop()
        tulip.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_http_status_exception(self):
        exc = errors.HttpErrorException(500, message='Internal error')
        self.assertEqual(exc.code, 500)
        self.assertEqual(exc.message, 'Internal error')

    def test_handle_request(self):
        transport = unittest.mock.Mock()

        srv = server.ServerHttpProtocol()
        srv.connection_made(transport)

        rline = unittest.mock.Mock()
        rline.version = (1, 1)
        message = unittest.mock.Mock()
        srv.handle_request(rline, message)

        content = b''.join([c[1][0] for c in list(transport.write.mock_calls)])
        self.assertTrue(content.startswith(b'HTTP/1.1 404 Not Found\r\n'))

    def test_connection_made(self):
        srv = server.ServerHttpProtocol()
        self.assertIsNone(srv._request_handler)

        srv.connection_made(unittest.mock.Mock())
        self.assertIsNotNone(srv._request_handler)

    def test_data_received(self):
        srv = server.ServerHttpProtocol()
        srv.connection_made(unittest.mock.Mock())

        srv.data_received(b'123')
        self.assertEqual(b'123', bytes(srv.stream._buffer))

        srv.data_received(b'456')
        self.assertEqual(b'123456', bytes(srv.stream._buffer))

    def test_eof_received(self):
        srv = server.ServerHttpProtocol()
        srv.connection_made(unittest.mock.Mock())
        srv.eof_received()
        self.assertTrue(srv.stream._eof)

    def test_connection_lost(self):
        srv = server.ServerHttpProtocol()
        srv.connection_made(unittest.mock.Mock())
        srv.data_received(b'123')

        keep_alive_handle = srv._keep_alive_handle = unittest.mock.Mock()

        handle = srv._request_handler
        srv.connection_lost(None)

        self.assertIsNone(srv._request_handler)
        self.assertTrue(handle.cancelled())

        self.assertIsNone(srv._keep_alive_handle)
        self.assertTrue(keep_alive_handle.cancel.called)

        srv.connection_lost(None)
        self.assertIsNone(srv._request_handler)
        self.assertIsNone(srv._keep_alive_handle)

    def test_srv_keep_alive(self):
        srv = server.ServerHttpProtocol()
        self.assertFalse(srv._keep_alive)

        srv.keep_alive(True)
        self.assertTrue(srv._keep_alive)

        srv.keep_alive(False)
        self.assertFalse(srv._keep_alive)

    def test_handle_error(self):
        transport = unittest.mock.Mock()
        srv = server.ServerHttpProtocol()
        srv.connection_made(transport)
        srv.keep_alive(True)

        srv.handle_error(404, headers=(('X-Server', 'Tulip'),))
        content = b''.join([c[1][0] for c in list(transport.write.mock_calls)])
        self.assertIn(b'HTTP/1.1 404 Not Found', content)
        self.assertIn(b'X-SERVER: Tulip', content)
        self.assertFalse(srv._keep_alive)

    @unittest.mock.patch('tulip.http.server.traceback')
    def test_handle_error_traceback_exc(self, m_trace):
        transport = unittest.mock.Mock()
        log = unittest.mock.Mock()
        srv = server.ServerHttpProtocol(debug=True, log=log)
        srv.connection_made(transport)

        m_trace.format_exc.side_effect = ValueError

        srv.handle_error(500, exc=object())
        content = b''.join([c[1][0] for c in list(transport.write.mock_calls)])
        self.assertTrue(
            content.startswith(b'HTTP/1.1 500 Internal Server Error'))
        self.assertTrue(log.exception.called)

    def test_handle_error_debug(self):
        transport = unittest.mock.Mock()
        srv = server.ServerHttpProtocol()
        srv.debug = True
        srv.connection_made(transport)

        try:
            raise ValueError()
        except Exception as exc:
            srv.handle_error(999, exc=exc)

        content = b''.join([c[1][0] for c in list(transport.write.mock_calls)])

        self.assertIn(b'HTTP/1.1 500 Internal', content)
        self.assertIn(b'Traceback (most recent call last):', content)

    def test_handle_error_500(self):
        log = unittest.mock.Mock()
        transport = unittest.mock.Mock()

        srv = server.ServerHttpProtocol(log=log)
        srv.connection_made(transport)

        srv.handle_error(500)
        self.assertTrue(log.exception.called)

    def test_handle(self):
        transport = unittest.mock.Mock()
        srv = server.ServerHttpProtocol()
        srv.connection_made(transport)

        handle = srv.handle_request = unittest.mock.Mock()

        srv.stream.feed_data(
            b'GET / HTTP/1.0\r\n'
            b'Host: example.com\r\n\r\n')

        self.loop.run_until_complete(srv._request_handler)
        self.assertTrue(handle.called)
        self.assertTrue(transport.close.called)

    def test_handle_coro(self):
        transport = unittest.mock.Mock()
        srv = server.ServerHttpProtocol()

        called = False

        @tulip.coroutine
        def coro(message, payload):
            nonlocal called
            called = True
            srv.eof_received()

        srv.handle_request = coro
        srv.connection_made(transport)

        srv.stream.feed_data(
            b'GET / HTTP/1.0\r\n'
            b'Host: example.com\r\n\r\n')
        self.loop.run_until_complete(srv._request_handler)
        self.assertTrue(called)

    def test_handle_cancel(self):
        log = unittest.mock.Mock()
        transport = unittest.mock.Mock()

        srv = server.ServerHttpProtocol(log=log, debug=True)
        srv.connection_made(transport)

        srv.handle_request = unittest.mock.Mock()

        @tulip.task
        def cancel():
            srv._request_handler.cancel()

        self.loop.run_until_complete(
            tulip.wait([srv._request_handler, cancel()]))
        self.assertTrue(log.debug.called)

    def test_handle_cancelled(self):
        log = unittest.mock.Mock()
        transport = unittest.mock.Mock()

        srv = server.ServerHttpProtocol(log=log, debug=True)
        srv.connection_made(transport)

        srv.handle_request = unittest.mock.Mock()
        run_briefly(self.loop)  # start request_handler task

        srv.stream.feed_data(
            b'GET / HTTP/1.0\r\n'
            b'Host: example.com\r\n\r\n')

        r_handler = srv._request_handler
        srv._request_handler = None  # emulate srv.connection_lost()

        self.assertIsNone(self.loop.run_until_complete(r_handler))

    def test_handle_400(self):
        transport = unittest.mock.Mock()
        srv = server.ServerHttpProtocol()
        srv.connection_made(transport)
        srv.handle_error = unittest.mock.Mock()
        srv.keep_alive(True)
        srv.stream.feed_data(b'GET / HT/asd\r\n\r\n')

        self.loop.run_until_complete(srv._request_handler)
        self.assertTrue(srv.handle_error.called)
        self.assertTrue(400, srv.handle_error.call_args[0][0])
        self.assertTrue(transport.close.called)

    def test_handle_500(self):
        transport = unittest.mock.Mock()
        srv = server.ServerHttpProtocol()
        srv.connection_made(transport)

        handle = srv.handle_request = unittest.mock.Mock()
        handle.side_effect = ValueError
        srv.handle_error = unittest.mock.Mock()

        srv.stream.feed_data(
            b'GET / HTTP/1.0\r\n'
            b'Host: example.com\r\n\r\n')
        self.loop.run_until_complete(srv._request_handler)

        self.assertTrue(srv.handle_error.called)
        self.assertTrue(500, srv.handle_error.call_args[0][0])

    def test_handle_error_no_handle_task(self):
        transport = unittest.mock.Mock()
        srv = server.ServerHttpProtocol()
        srv.keep_alive(True)
        srv.connection_made(transport)
        srv.connection_lost(None)

        srv.handle_error(300)
        self.assertFalse(srv._keep_alive)

    def test_keep_alive(self):
        srv = server.ServerHttpProtocol(keep_alive=0.1)
        transport = unittest.mock.Mock()
        closed = False

        def close():
            nonlocal closed
            closed = True
            srv.connection_lost(None)
            self.loop.stop()

        transport.close = close

        srv.connection_made(transport)

        handle = srv.handle_request = unittest.mock.Mock()

        srv.stream.feed_data(
            b'GET / HTTP/1.1\r\n'
            b'CONNECTION: keep-alive\r\n'
            b'HOST: example.com\r\n\r\n')

        self.loop.run_forever()
        self.assertTrue(handle.called)
        self.assertTrue(closed)

    def test_keep_alive_close_existing(self):
        transport = unittest.mock.Mock()
        srv = server.ServerHttpProtocol(keep_alive=15)
        srv.connection_made(transport)

        self.assertIsNone(srv._keep_alive_handle)
        keep_alive_handle = srv._keep_alive_handle = unittest.mock.Mock()
        srv.handle_request = unittest.mock.Mock()

        srv.stream.feed_data(
            b'GET / HTTP/1.0\r\n'
            b'HOST: example.com\r\n\r\n')

        self.loop.run_until_complete(srv._request_handler)
        self.assertTrue(keep_alive_handle.cancel.called)
        self.assertIsNone(srv._keep_alive_handle)
        self.assertTrue(transport.close.called)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import unittest
from http_server_test import *

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
