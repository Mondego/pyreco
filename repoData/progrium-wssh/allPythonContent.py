__FILENAME__ = client
import sys

import gevent
from gevent.event import Event

from ws4py.exc import HandshakeError
from ws4py.client.geventclient import WebSocketClient

from . import common

# Handles the WebSocket once it has been upgraded by the HTTP layer.
class StdioPipedWebSocketClient(WebSocketClient):

    def __init__(self, scheme, host, port, path, opts):
        url = "{0}://{1}:{2}{3}".format(scheme, host, port, path)
        WebSocketClient.__init__(self, url)

        self.path = path
        self.shutdown_cond = Event()
        self.opts = opts
        self.iohelper = common.StdioPipedWebSocketHelper(self.shutdown_cond, opts)

    def received_message(self, m):
        self.iohelper.received_message(self, m)

    def opened(self):
        if self.opts.verbosity >= 1:
            peername, peerport = self.sock.getpeername()
            print >> sys.stderr, "[%s] %d open for path '%s'" % (peername, peerport, self.path)
        self.iohelper.opened(self)

    def closed(self, code, reason):
        self.shutdown_cond.set()

    def connect_and_wait(self):
        self.connect()
        self.shutdown_cond.wait()

def connect(args, scheme, host, port, path):
    if path == None:
        path = '/'
    client = StdioPipedWebSocketClient(scheme, host, port, path, args)
    try:
        client.connect_and_wait()
    except (IOError, HandshakeError), e:
        print >> sys.stderr, e

########NEW FILE########
__FILENAME__ = common
import sys
import os
import fcntl

import string

import gevent
from gevent.socket import wait_read

from ws4py.websocket import WebSocket

# Common stdio piping behaviour for the WebSocket handler.  Unfortunately due
# to ws4py OO failures, it's not possible to just share a common WebSocket
# class for this (WebSocketClient extends WebSocket, rather than simply
# delegating to one as WebSocketServer can).
class StdioPipedWebSocketHelper:
    def __init__(self, shutdown_cond, opts):
        self.shutdown_cond = shutdown_cond
        self.opts = opts
        if self.opts.text_mode == 'auto':
            # This represents all printable, ASCII characters.  Only these
            # characters can pass through as a WebSocket text frame.
            self.textset = set(c for c in string.printable if ord(c) < 128)

    def received_message(self, websocket, m):
        if self.opts.verbosity >= 3:
            mode_msg = 'binary' if m.is_binary else 'text'
            print >> sys.stderr, "[received payload of length %d as %s]" % (len(m.data), mode_msg)
        sys.stdout.write(m.data)
        if self.opts.new_lines:
          sys.stdout.write("\n")
        sys.stdout.flush()

    def should_send_binary_frame(self, buf):
        if self.opts.text_mode == 'auto':
            return not set(buf).issubset(self.textset)
        elif self.opts.text_mode == 'text':
            return False
        else:
            return True

    def opened(self, websocket):
        def connect_stdin():
            fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NONBLOCK)
            while True:
                wait_read(sys.stdin.fileno())
                buf = sys.stdin.read(4096)
                if len(buf) == 0:
                    break
                binary=self.should_send_binary_frame(buf)
                if self.opts.verbosity >= 3:
                    mode_msg = 'binary' if binary else 'text'
                    print >> sys.stderr, "[sending payload of length %d as %s]" % (len(buf), mode_msg)
                websocket.send(buf, binary)

            if self.opts.verbosity >= 2:
                print >> sys.stderr, '[EOF on stdin, shutting down input]'

            # If -q was passed, shutdown the program after EOF and the
            # specified delay.  Otherwise, keep the socket open even with no
            # more input flowing (consistent with netcat's behaviour).
            if self.opts.quit_on_eof is not None:
                if self.opts.quit_on_eof > 0:
                    gevent.sleep(self.opts.quit_on_eof)
                self.shutdown_cond.set()

        # XXX: We wait for the socket to open before reading stdin so that we
        # support behaviour like: echo foo | wssh -l ...
        gevent.spawn(connect_stdin)

########NEW FILE########
__FILENAME__ = server
import sys

import gevent
from gevent.event import Event

from ws4py.server.geventserver import UpgradableWSGIHandler
from ws4py.server.wsgi.middleware import WebSocketUpgradeMiddleware
from ws4py.websocket import WebSocket

from . import common

# Handles the WebSocket once it has been upgraded by the HTTP layer.
class StdioPipedWebSocket(WebSocket):
    def my_setup(self, helper, opts):
        self.iohelper = helper
        self.opts = opts

    def received_message(self, m):
        self.iohelper.received_message(self, m)

    def opened(self):
        if self.opts.verbosity >= 1:
            peername, peerport = self.sock.getpeername()
            print >> sys.stderr, "connect from [%s] %d" % (peername, peerport)
        self.iohelper.opened(self)

    def closed(self, code, reason):
        pass

# Simple HTTP server implementing only one endpoint which upgrades to the
# stdin/stdout connected WebSocket.
class SimpleWebSocketServer(gevent.pywsgi.WSGIServer):
    handler_class = UpgradableWSGIHandler

    def __init__(self, host, port, path, opts):
        gevent.pywsgi.WSGIServer.__init__(self, (host, port), log=None)

        self.host = host
        self.port = port
        self.path = path
        self.application = self

        self.shutdown_cond = Event()
        self.opts = opts
        self.iohelper = common.StdioPipedWebSocketHelper(self.shutdown_cond, opts)

        self.ws_upgrade = WebSocketUpgradeMiddleware(app=self.ws_handler,
                websocket_class=StdioPipedWebSocket)

    def __call__(self, environ, start_response):
        request_path = environ['PATH_INFO']
        if self.path and request_path != self.path:
            if self.opts.verbosity >= 2:
                print "refusing to serve request for path '%s'" % request_path
            start_response('400 Not Found', [])
            return ['']
        else:
            # Hand-off the WebSocket upgrade negotiation to ws4py...
            return self.ws_upgrade(environ, start_response)

    def ws_handler(self, websocket):
        # Stop accepting new connections after we receive our first one (a la
        # netcat).
        self.stop_accepting()

        # Pass custom arguments over to our WebSocket instance.  The design of
        # gevent's pywsgi layer leaves a lot to be desired in terms of proper
        # dependency injection patterns...
        websocket.my_setup(self.iohelper, self.opts)

        # Transfer control to the websocket_class.
        g = gevent.spawn(websocket.run)
        g.join()

        # WebSocket connection terminated, exit program.
        self.shutdown_cond.set()

    def handle_one_websocket(self):
        self.start()
        if self.opts.verbosity >= 1:
            if self.path:
                path_stmt = "path '%s'" % (self.path)
            else:
                path_stmt = 'all paths'
            print >> sys.stderr, 'listening on [any] %d for %s...' % (self.port, path_stmt)
        self.shutdown_cond.wait()

def listen(args, port, path):
    # XXX: Should add support to limit the listening interface.
    server = SimpleWebSocketServer('', port, path, args)
    try:
        server.handle_one_websocket()
    except IOError, e:
        print >> sys.stderr, e

########NEW FILE########
