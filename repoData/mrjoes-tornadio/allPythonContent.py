__FILENAME__ = chatroom
from os import path as op

import tornado.web
import tornadio
import tornadio.router
import tornadio.server

ROOT = op.normpath(op.dirname(__file__))

class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render("index.html")

class ChatConnection(tornadio.SocketConnection):
    # Class level variable
    participants = set()

    def on_open(self, *args, **kwargs):
        self.participants.add(self)
        self.send("Welcome!")

    def on_message(self, message):
        for p in self.participants:
            p.send(message)

    def on_close(self):
        self.participants.remove(self)
        for p in self.participants:
            p.send("A user has left.")

#use the routes classmethod to build the correct resource
ChatRouter = tornadio.get_router(ChatConnection, {
    'enabled_protocols': [
        'websocket',
        'flashsocket',
        'xhr-multipart',
        'xhr-polling'
    ]
})

#configure the Tornado application
application = tornado.web.Application(
    [(r"/", IndexHandler), ChatRouter.route()],
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8001
)

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    tornadio.server.SocketServer(application)


########NEW FILE########
__FILENAME__ = ping
from os import path as op

from datetime import datetime

import tornado.web
import tornadio
import tornadio.router
import tornadio.server

ROOT = op.normpath(op.dirname(__file__))

class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the ping page"""
    def get(self):
        self.render("index.html")

class PingConnection(tornadio.SocketConnection):
    def on_open(self, request, *args, **kwargs):
        self.ip = request.remote_ip

    def on_message(self, message):
        message['server'] = str(datetime.now())
        message['ip'] = self.ip
        self.send(message)

#use the routes classmethod to build the correct resource
PingRouter = tornadio.get_router(PingConnection)

#configure the Tornado application
application = tornado.web.Application(
    [(r"/", IndexHandler), PingRouter.route()],
    socket_io_port = 8001,
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml')
)

if __name__ == "__main__":
    tornadio.server.SocketServer(application)

########NEW FILE########
__FILENAME__ = transports
from os import path as op

import tornado.web
import tornadio
import tornadio.router
import tornadio.server

ROOT = op.normpath(op.dirname(__file__))

class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render("index.html")

class ChatConnection(tornadio.SocketConnection):
    # Class level variable
    participants = set()

    def on_open(self, *args, **kwargs):
        self.send("Welcome from the server.")

    def on_message(self, message):
        # Pong message back
        self.send(message)

#use the routes classmethod to build the correct resource
ChatRouter = tornadio.get_router(ChatConnection)

#configure the Tornado application
application = tornado.web.Application(
    [(r"/", IndexHandler), ChatRouter.route()],
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8001
)

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    tornadio.server.SocketServer(application)


########NEW FILE########
__FILENAME__ = proto_test
# -*- coding: utf-8 -*-
"""
    tornadio.tests.proto_test
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""

from nose.tools import eq_

from tornadio import proto

def test_encode():
    # Test string encode
    eq_(proto.encode('abc'), '~m~3~m~abc')

    # Test dict encode
    eq_(proto.encode({'a':'b'}), '~m~13~m~~j~{"a": "b"}')

    # Test list encode
    eq_(proto.encode(['a','b']), '~m~1~m~a~m~1~m~b')

    # Test unicode
    eq_(proto.encode(u'\u0430\u0431\u0432'),
        '~m~6~m~' + u'\u0430\u0431\u0432'.encode('utf-8'))

    # Test special characters encoding
    eq_(proto.encode('~m~'), '~m~3~m~~m~')

def test_decode():
    # Test string decode
    eq_(proto.decode(proto.encode('abc')), [('~m~', 'abc')])

    # Test unicode decode
    eq_(proto.decode(proto.encode(u'\u0430\u0431\u0432')),
        [('~m~', u'\u0430\u0431\u0432'.encode('utf-8'))])

    # Test JSON decode
    eq_(proto.decode(proto.encode({'a':'b'})),
        [('~m~', {'a':'b'})])

    # Test seprate messages decoding
    eq_(proto.decode(proto.encode(['a','b'])),
        [('~m~', 'a'), ('~m~', 'b')])

########NEW FILE########
__FILENAME__ = conn
# -*- coding: utf-8 -*-
"""
    tornadio.conn
    ~~~~~~~~~~~~~

    This module implements connection management class.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging, time

from tornadio import proto, periodic

class SocketConnection(object):
    """This class represents basic connection class that you will derive
    from in your application.

    You can override following methods:

    1. on_open, called on incoming client connection
    2. on_message, called on incoming client message. Required.
    3. on_close, called when connection was closed due to error or timeout

    For example:

        class MyClient(SocketConnection):
            def on_open(self, *args, **kwargs):
                print 'Incoming client'

            def on_message(self, message):
                print 'Incoming message: %s' % message

            def on_close(self):
                print 'Client disconnected'
    """
    def __init__(self, protocol, io_loop, heartbeat_interval):
        """Default constructor.

        `protocol`
            Transport protocol implementation object.
        `io_loop`
            Tornado IOLoop instance
        `heartbeat_interval`
            Heartbeat interval for this connection, in seconds.
        """
        self._protocol = protocol

        self._io_loop = io_loop

        # Initialize heartbeats
        self._heartbeat_timer = None
        self._heartbeats = 0
        self._missed_heartbeats = 0
        self._heartbeat_delay = None
        self._heartbeat_interval = heartbeat_interval * 1000

        # Connection is not closed right after creation
        self.is_closed = False

    def on_open(self, *args, **kwargs):
        """Default on_open() handler"""
        pass

    def on_message(self, message):
        """Default on_message handler. Must be overridden"""
        raise NotImplementedError()

    def on_close(self):
        """Default on_close handler."""
        pass

    def send(self, message):
        """Send message to the client.

        `message`
            Message to send.
        """
        self._protocol.send(message)

    def close(self):
        """Focibly close client connection.
        Stop heartbeats as well, as they would cause IOErrors once the connection is closed."""
        self.stop_heartbeat()
        self._protocol.close()

    def raw_message(self, message):
        """Called when raw message was received by underlying transport protocol
        """
        for msg in proto.decode(message):
            if msg[0] == proto.FRAME or msg[0] == proto.JSON:
                self.on_message(msg[1])
            elif msg[0] == proto.HEARTBEAT:
                # TODO: Verify incoming heartbeats
                logging.debug('Incoming Heartbeat')
                self._missed_heartbeats -= 1

    # Heartbeat management
    def reset_heartbeat(self, interval=None):
        """Reset (stop/start) heartbeat timeout"""
        self.stop_heartbeat()

        # TODO: Configurable heartbeats
        if interval is None:
            interval = self._heartbeat_interval

        self._heartbeat_timer = periodic.Callback(self._heartbeat,
                                                  interval,
                                                  self._io_loop)
        self._heartbeat_timer.start()

    def stop_heartbeat(self):
        """Stop heartbeat"""
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.stop()
            self._heartbeat_timer = None

    def delay_heartbeat(self):
        """Delay heartbeat sending"""
        if self._heartbeat_timer is not None:
            self._heartbeat_delay = self._heartbeat_timer.calculate_next_run()

    def send_heartbeat(self):
        """Send heartbeat message to the client"""
        self._heartbeats += 1
        self._missed_heartbeats += 1
        self.send('~h~%d' % self._heartbeats)

    def _heartbeat(self):
        """Heartbeat callback. Sends heartbeat to the client."""
        if (self._heartbeat_delay is not None
            and time.time() < self._heartbeat_delay):
            delay = self._heartbeat_delay
            self._heartbeat_delay = None
            return delay

        logging.debug('Sending heartbeat')

        if self._missed_heartbeats > 5:
            logging.debug('Missed too many heartbeats')
            self.close()
        else:
            self.send_heartbeat()

########NEW FILE########
__FILENAME__ = flashserver
# -*- coding: utf-8 -*-
"""
    tornadio.flashserver
    ~~~~~~~~~~~~~~~~~~~~

    Flash Socket policy server implementation. Merged with minor modifications
    from the SocketTornad.IO project.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
from __future__ import with_statement

import socket
import errno
import functools

from tornado import iostream

class FlashPolicyServer(object):
    """Flash Policy server, listens on port 843 by default (useless otherwise)
    """
    def __init__(self, io_loop, port=843, policy_file='flashpolicy.xml'):
        self.policy_file = policy_file
        self.port = port

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        sock.bind(('', self.port))
        sock.listen(128)

        self.io_loop = io_loop
        callback = functools.partial(self.connection_ready, sock)
        self.io_loop.add_handler(sock.fileno(), callback, self.io_loop.READ)

    def connection_ready(self, sock, _fd, _events):
        """Connection ready callback"""
        while True:
            try:
                connection, address = sock.accept()
            except socket.error, ex:
                if ex[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                return
            connection.setblocking(0)
            self.stream = iostream.IOStream(connection, self.io_loop)
            self.stream.read_bytes(22, self._handle_request)

    def _handle_request(self, request):
        """Send policy response"""
        if request != '<policy-file-request/>':
            self.stream.close()
        else:
            with open(self.policy_file, 'rb') as file_handle:
                self.stream.write(file_handle.read() + '\0')

########NEW FILE########
__FILENAME__ = periodic
# -*- coding: utf-8 -*-
"""
    tornadio.flashserver
    ~~~~~~~~~~~~~~~~~~~~

    This module implements customized PeriodicCallback from tornado with
    support of the sliding window.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time, logging

class Callback(object):
    def __init__(self, callback, callback_time, io_loop):
        self.callback = callback
        self.callback_time = callback_time
        self.io_loop = io_loop
        self._running = False

    def calculate_next_run(self):
        return time.time() + self.callback_time / 1000.0

    def start(self, timeout=None):
        self._running = True

        if timeout is None:
            timeout = self.calculate_next_run()

        self.io_loop.add_timeout(timeout, self._run)

    def stop(self):
        self._running = False

    def _run(self):
        if not self._running:
            return

        next_call = None

        try:
            next_call = self.callback()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.error("Error in periodic callback", exc_info=True)

        if self._running:
            self.start(next_call)

########NEW FILE########
__FILENAME__ = persistent
# -*- coding: utf-8 -*-
"""
    tornadio.persistent
    ~~~~~~~~~~~~~~~~~~~

    Persistent transport implementations.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

import tornado
from tornado.websocket import WebSocketHandler

from tornadio import proto

class TornadioWebSocketHandler(WebSocketHandler):
    """WebSocket handler.
    """
    def __init__(self, router, session_id):
        logging.debug('Initializing WebSocket handler...')

        self.router = router
        self.connection = None

        super(TornadioWebSocketHandler, self).__init__(router.application,
                                                       router.request)

    # HAProxy websocket fix.
    # Merged from:
    # https://github.com/facebook/tornado/commit/86bd681ff841f272c5205f24cd2a613535ed2e00
    def _execute(self, transforms, *args, **kwargs):
        # Next Tornado will have the built-in support for HAProxy
        if tornado.version_info < (1, 2, 0):
            # Write the initial headers before attempting to read the challenge.
            # This is necessary when using proxies (such as HAProxy),
            # need to see the Upgrade headers before passing through the
            # non-HTTP traffic that follows.
            self.stream.write(
                "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
                "Upgrade: WebSocket\r\n"
                "Connection: Upgrade\r\n"
                "Server: TornadoServer/%(version)s\r\n"
                "Sec-WebSocket-Origin: %(origin)s\r\n"
                "Sec-WebSocket-Location: ws://%(host)s%(path)s\r\n\r\n" % (dict(
                        version=tornado.version,
                        origin=self.request.headers["Origin"],
                        host=self.request.host,
                        path=self.request.path)))

        super(TornadioWebSocketHandler, self)._execute(transforms, *args,
                                                       **kwargs)


    def _write_response(self, challenge):
        if tornado.version_info < (1, 2, 0):
            self.stream.write("%s" % challenge)
            self.async_callback(self.open)(*self.open_args, **self.open_kwargs)
            self._receive_message()
        else:
            super(TornadioWebSocketHandler, self)._write_response(challenge)

    def open(self, *args, **kwargs):
        # Create connection instance
        heartbeat_interval = self.router.settings['heartbeat_interval']
        self.connection = self.router.connection(self,
                                                 self.router.io_loop,
                                                 heartbeat_interval)

        # Initialize heartbeats
        self.connection.reset_heartbeat()

        # Fix me: websocket is dropping connection if we don't send first
        # message
        self.send('no_session')

        self.connection.on_open(self.request, *args, **kwargs)

    def on_message(self, message):
        self.async_callback(self.connection.raw_message)(message)

    def on_close(self):
        if self.connection is not None:
            try:
                self.connection.on_close()
            finally:
                self.connection.is_closed = True
                self.connection.stop_heartbeat()

    def send(self, message):
        self.write_message(proto.encode(message))
        self.connection.delay_heartbeat()

class TornadioFlashSocketHandler(TornadioWebSocketHandler):
    def __init__(self, router, session_id):
        logging.debug('Initializing FlashSocket handler...')

        super(TornadioFlashSocketHandler, self).__init__(router, session_id)

########NEW FILE########
__FILENAME__ = polling
# -*- coding: utf-8 -*-
"""
    tornadio.polling
    ~~~~~~~~~~~~~~~~

    This module implements socket.io polling transports.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time
try:
    import simplejson as json
except ImportError:
    import json

from urllib import unquote
from tornado.web import RequestHandler, HTTPError, asynchronous

from tornadio import pollingsession

class TornadioPollingHandlerBase(RequestHandler):
    """All polling transport implementations derive from this class.

    Polling transports have following things in common:

    1. They use GET to read data from the server
    2. They use POST to send data to the server
    3. They use sessions - first message sent back from the server is session_id
    4. Session is used to create one virtual connection for one or more HTTP
    connections
    5. If GET request is not running, data will be cached on server side. On
    next GET request, all cached data will be sent to the client in one batch
    6. If there were no GET requests for more than 15 seconds (default), virtual
    connection will be closed - session entry will expire
    """
    def __init__(self, router, session_id):
        """Default constructor.

        Accepts router instance and session_id (if available) and handles
        request.
        """
        self.router = router
        self.session_id = session_id
        self.session = None

        super(TornadioPollingHandlerBase, self).__init__(router.application,
                                                         router.request)

    def _execute(self, transforms, *args, **kwargs):
        # Initialize session either by creating new one or
        # getting it from container
        if not self.session_id:
            session_expiry = self.router.settings['session_expiry']

            self.session = self.router.sessions.create(
                pollingsession.PollingSession,
                session_expiry,
                router=self.router,
                args=args,
                kwargs=kwargs)
        else:
            self.session = self.router.sessions.get(self.session_id)

            if self.session is None or self.session.is_closed:
                # TODO: Send back disconnect message?
                raise HTTPError(401, 'Invalid session')

        super(TornadioPollingHandlerBase, self)._execute(transforms,
                                                         *args, **kwargs)

    @asynchronous
    def get(self, *args, **kwargs):
        """Default GET handler."""
        raise NotImplementedError()

    @asynchronous
    def post(self, *args, **kwargs):
        """Default POST handler."""
        raise NotImplementedError()

    def data_available(self, raw_data):
        """Called by the session when some data is available"""
        raise NotImplementedError()

    @asynchronous
    def options(self, *args, **kwargs):
        """XHR cross-domain OPTIONS handler"""
        self.preflight()
        self.finish()

    def preflight(self):
        """Handles request authentication"""
        if self.request.headers.has_key('Origin'):
            if self.verify_origin():
                self.set_header('Access-Control-Allow-Origin',
                                self.request.headers['Origin'])

                self.set_header('Access-Control-Allow-Credentials', 'true')

                return True
            else:
                return False
        else:
            return True

    def verify_origin(self):
        """Verify if request can be served"""
        # TODO: Verify origin
        return True

class TornadioXHRPollingSocketHandler(TornadioPollingHandlerBase):
    """XHR polling transport implementation.

    Polling mechanism uses long-polling AJAX GET to read data from the server
    and POST to send data to the server.

    Properties of the XHR polling transport:

    1. If there was no data for more than 20 seconds (by default) from the
    server, GET connection will be closed to avoid HTTP timeouts. In this case
    socket.io client-side will just make another GET request.
    2. When new data is available on server-side, it will be sent through the
    open GET connection or cached otherwise.
    """
    def __init__(self, router, session_id):
        self._timeout = None

        self._timeout_interval = router.settings['xhr_polling_timeout']

        super(TornadioXHRPollingSocketHandler, self).__init__(router,
                                                              session_id)

    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            # Check to avoid double connections
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        if not self.session.send_queue:
            self._timeout = self.router.io_loop.add_timeout(
                time.time() + self._timeout_interval,
                self._polling_timeout)
        else:
            self.session.flush()

    def _polling_timeout(self):
        # TODO: Fix me
        if self.session:
            self.data_available('')

    @asynchronous
    def post(self, *args, **kwargs):
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        # Special case for IE XDomainRequest
        ctype = self.request.headers.get("Content-Type", "").split(";")[0]
        if ctype == '':
            data = None
            body = self.request.body

            if body.startswith('data='):
                data = unquote(body[5:])
        else:
            data = self.get_argument('data', None)

        self.async_callback(self.session.raw_message)(data)

        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.write('ok')
        self.finish()

    def _detach(self):
        if self.session:
            self.session.remove_handler(self)
            self.session = None

    def on_connection_close(self):
        self._detach()

    def data_available(self, raw_data):
        self.preflight()
        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.set_header('Content-Length', len(raw_data))
        self.write(raw_data)
        self.finish()

        # Detach connection
        self._detach()

class TornadioXHRMultipartSocketHandler(TornadioPollingHandlerBase):
    """XHR Multipart transport implementation.

    Transport properties:
    1. One persistent GET connection used to receive data from the server
    2. Sends heartbeat messages to keep connection alive each 12 seconds
    (by default)
    """
    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        self.set_header('Content-Type',
                        'multipart/x-mixed-replace;boundary="socketio; charset=UTF-8"')
        self.set_header('Connection', 'keep-alive')
        self.write('--socketio\n')

        # Dump any queued messages
        self.session.flush()

        # We need heartbeats
        self.session.reset_heartbeat()

    @asynchronous
    def post(self, *args, **kwargs):
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        data = self.get_argument('data')
        self.async_callback(self.session.raw_message)(data)

        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.write('ok')
        self.finish()

    def on_connection_close(self):
        if self.session:
            self.session.stop_heartbeat()
            self.session.remove_handler(self)

    def data_available(self, raw_data):
        self.preflight()
        self.write("Content-Type: text/plain; charset=UTF-8\n\n")
        self.write(raw_data + '\n')
        self.write('--socketio\n')
        self.flush()

        self.session.delay_heartbeat()

class TornadioHtmlFileSocketHandler(TornadioPollingHandlerBase):
    """IE HtmlFile protocol implementation.

    Uses hidden frame to stream data from the server in one connection.

    Unfortunately, it is unknown if this transport works, as socket.io
    client-side fails in IE7/8.
    """
    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            raise HTTPError(401, 'Forbidden')

        self.set_header('Content-Type', 'text/html; charset=UTF-8')
        self.set_header('Connection', 'keep-alive')
        self.set_header('Transfer-Encoding', 'chunked')
        self.write('<html><body>%s' % (' ' * 244))

        # Dump any queued messages
        self.session.flush()

        # We need heartbeats
        self.session.reset_heartbeat()

    @asynchronous
    def post(self, *args, **kwargs):
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        data = self.get_argument('data')
        self.async_callback(self.session.raw_message)(data)

        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.write('ok')
        self.finish()

    def on_connection_close(self):
        if self.session:
            self.session.stop_heartbeat()
            self.session.remove_handler(self)

    def data_available(self, raw_data):
        self.write(
            '<script>parent.s_(%s),document);</script>' % json.dumps(raw_data)
            )
        self.flush()

        self.session.delay_heartbeat()

class TornadioJSONPSocketHandler(TornadioXHRPollingSocketHandler):
    """JSONP protocol implementation.
    """
    def __init__(self, router, session_id):
        self._index = None

        super(TornadioJSONPSocketHandler, self).__init__(router, session_id)

    @asynchronous
    def get(self, *args, **kwargs):
        self._index = kwargs.get('jsonp_index', None)
        super(TornadioJSONPSocketHandler, self).get(*args, **kwargs)

    @asynchronous
    def post(self, *args, **kwargs):
        self._index = kwargs.get('jsonp_index', None)
        super(TornadioJSONPSocketHandler, self).post(*args, **kwargs)

    def data_available(self, raw_data):
        if not self._index:
            raise HTTPError(401, 'unauthorized')

        message = 'io.JSONP[%s]._(%s);' % (
            self._index,
            json.dumps(raw_data)
            )

        self.preflight()
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        self.write(message)
        self.finish()

        # Detach connection
        self._detach()

########NEW FILE########
__FILENAME__ = pollingsession
# -*- coding: utf-8 -*-
"""
    tornadio.pollingsession
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module implements polling session class.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
from tornadio import proto, session

class PollingSession(session.Session):
    """This class represents virtual protocol connection for polling transports.

    For disconnected protocols, like XHR-Polling, it will cache outgoing
    messages, if there is on going GET connection - will pass cached/current
    messages to the actual transport protocol implementation.
    """
    def __init__(self, session_id, expiry, router,
                 args, kwargs):
        # Initialize session
        super(PollingSession, self).__init__(session_id, expiry)

        # Set connection
        self.connection = router.connection(self,
                                     router.io_loop,
                                     router.settings['heartbeat_interval'])

        self.handler = None
        self.send_queue = []

        # Forward some methods to connection
        self.on_open = self.connection.on_open
        self.raw_message = self.connection.raw_message
        self.on_close = self.connection.on_close

        self.reset_heartbeat = self.connection.reset_heartbeat
        self.stop_heartbeat = self.connection.stop_heartbeat
        self.delay_heartbeat = self.connection.delay_heartbeat

        # Send session_id
        self.send(session_id)

        # Notify that channel was opened
        self.on_open(router.request, *args, **kwargs)

    def on_delete(self, forced):
        """Called by the session management class when item is
        about to get deleted/expired. If item is getting expired,
        there is possibility to force rescheduling of the item
        somewhere in the future, so it won't be deleted.

        Rescheduling is used in case when there is on-going GET
        connection.
        """
        if not forced and self.handler is not None and not self.is_closed:
            self.promote()
        else:
            self.close()

    def set_handler(self, handler):
        """Associate request handler with this virtual connection.

        If there is already handler associated, it won't be changed.
        """
        if self.handler is not None:
            return False

        self.handler = handler

        # Promote session item
        self.promote()

        return True

    def remove_handler(self, handler):
        """Remove associated Tornado handler.

        Promotes session in the cache, so time between two calls can't
        be greater than 15 seconds (by default)
        """
        if self.handler != handler:
            # TODO: Assert
            return False

        self.handler = None

        # Promote session so session item will live a bit longer
        # after disconnection
        self.promote()

    def flush(self):
        """Send all pending messages to the associated request handler (if any)
        """
        if self.handler is None:
            return

        if not self.send_queue:
            return

        self.handler.data_available(proto.encode(self.send_queue))
        self.send_queue = []

    def send(self, message):
        """Append message to the queue and send it right away, if there's
        connection available.
        """
        self.send_queue.append(message)

        self.flush()

    def close(self):
        """Forcibly close connection and notify connection object about that.
        """
        if not self.connection.is_closed:
            try:
                # Notify that connection was closed
                self.connection.on_close()
            finally:
                self.connection.is_closed = True

    @property
    def is_closed(self):
        """Check if connection was closed or not"""
        return self.connection.is_closed

########NEW FILE########
__FILENAME__ = proto
# -*- coding: utf-8 -*-
"""
    tornadio.proto
    ~~~~~~~~~~~~~~

    Socket.IO 0.6.x protocol codec.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
try:
    import simplejson as json
    json_decimal_args = {"use_decimal":True}
except ImportError:
    import json
    import decimal
    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                return float(o)
            return super(DecimalEncoder, self).default(o)
    json_decimal_args = {"cls":DecimalEncoder}

FRAME = '~m~'
HEARTBEAT = '~h~'
JSON = '~j~'

def encode(message):
    """Encode message to the socket.io wire format.

    1. If message is list, it will encode each separate list item as a message
    2. If message is a unicode or ascii string, it will be encoded as is
    3. If message some arbitrary python object or a dict, it will be JSON
    encoded
    """
    encoded = ''
    if isinstance(message, list):
        for msg in message:
            encoded += encode(msg)
    elif (not isinstance(message, (unicode, str))
          and isinstance(message, (object, dict))):
        if message is not None:
            encoded += encode('~j~' + json.dumps(message, **json_decimal_args))
    else:
        msg = message.encode('utf-8')
        encoded += "%s%d%s%s" % (FRAME, len(msg), FRAME, msg)

    return encoded

def decode(data):
    """Decode socket.io messages

    Returns message tuples, first item in a tuple is message type (see
    message declarations in the beginning of the file) and second item
    is decoded message.
    """
    messages = []

    idx = 0

    while data[idx:idx+3] == FRAME:
        # Skip frame
        idx += 3

        len_start = idx
        while data[idx].isdigit():
            idx += 1

        msg_len = int(data[len_start:idx])

        msg_type = data[idx:idx + 3]

        # Skip message type
        idx += 3

        msg_data = data[idx:idx + msg_len]

        if msg_data.startswith(JSON):
            msg_data = json.loads(msg_data[3:])
        elif msg_data.startswith(HEARTBEAT):
            msg_type = HEARTBEAT
            msg_data = msg_data[3:]

        messages.append((msg_type, msg_data))

        idx += msg_len

    return messages

########NEW FILE########
__FILENAME__ = router
# -*- coding: utf-8 -*-
"""
    tornadio.router
    ~~~~~~~~~~~~~~~

    Transport protocol router and main entry point for all socket.io clients.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

from tornado import ioloop
from tornado.web import RequestHandler, HTTPError

from tornadio import persistent, polling, session

PROTOCOLS = {
    'websocket': persistent.TornadioWebSocketHandler,
    'flashsocket': persistent.TornadioFlashSocketHandler,
    'xhr-polling': polling.TornadioXHRPollingSocketHandler,
    'xhr-multipart': polling.TornadioXHRMultipartSocketHandler,
    'htmlfile': polling.TornadioHtmlFileSocketHandler,
    'jsonp-polling': polling.TornadioJSONPSocketHandler,
    }

DEFAULT_SETTINGS = {
    # Sessions check interval in seconds
    'session_check_interval': 15,
    # Session expiration in seconds
    'session_expiry': 30,
    # Heartbeat time in seconds. Do not change this value unless
    # you absolutely sure that new value will work.
    'heartbeat_interval': 12,
    # Enabled protocols
    'enabled_protocols': ['websocket', 'flashsocket', 'xhr-multipart',
                          'xhr-polling', 'jsonp-polling', 'htmlfile'],
    # XHR-Polling request timeout, in seconds
    'xhr_polling_timeout': 20,
    }


class SocketRouterBase(RequestHandler):
    """Main request handler.

    Manages creation of appropriate transport protocol implementations and
    passing control to them.
    """
    _connection = None
    _route = None
    _sessions = None
    _sessions_cleanup = None
    settings = None

    def _execute(self, transforms, *args, **kwargs):
        try:
            extra = kwargs['extra']
            proto_name = kwargs['protocol']
            proto_init = kwargs['protocol_init']
            session_id = kwargs['session_id']

            logging.debug('Incoming session %s(%s) Session ID: %s Extra: %s' % (
                proto_name,
                proto_init,
                session_id,
                extra
                ))

            # If protocol is disabled, raise HTTPError
            if proto_name not in self.settings['enabled_protocols']:
                raise HTTPError(403, 'Forbidden')

            protocol = PROTOCOLS.get(proto_name, None)

            if protocol:
                handler = protocol(self, session_id)
                handler._execute(transforms, *extra, **kwargs)
            else:
                raise Exception('Handler for protocol "%s" is not available' %
                                proto_name)
        except ValueError:
            # TODO: Debugging
            raise HTTPError(403, 'Forbidden')

    @property
    def connection(self):
        """Return associated connection class."""
        return self._connection

    @property
    def sessions(self):
        return self._sessions

    @classmethod
    def route(cls):
        """Returns prepared Tornado routes"""
        return cls._route

    @classmethod
    def tornadio_initialize(cls, connection, user_settings, resource,
                            io_loop=None, extra_re=None, extra_sep=None):
        """Initialize class with the connection and resource.

        Does all behind the scenes work to setup routes, etc. Partially
        copied from SocketTornad.IO implementation.
        """


        # Associate connection object
        cls._connection = connection

        # Initialize io_loop
        cls.io_loop = io_loop or ioloop.IOLoop.instance()

        # Associate settings
        settings = DEFAULT_SETTINGS.copy()

        if user_settings is not None:
            settings.update(user_settings)

        cls.settings = settings

        # Initialize sessions
        cls._sessions = session.SessionContainer()

        check_interval = settings['session_check_interval'] * 1000
        cls._sessions_cleanup = ioloop.PeriodicCallback(cls._sessions.expire,
                                                        check_interval,
                                                        cls.io_loop).start()

        # Copied from SocketTornad.IO with minor formatting
        if extra_re:
            if not extra_re.startswith('(?P<extra>'):
                extra_re = r'(?P<extra>%s)' % extra_re
            if extra_sep:
                extra_re = extra_sep + extra_re
        else:
            extra_re = "(?P<extra>)"

        proto_re = "|".join(PROTOCOLS.keys())

        cls._route = (r"/(?P<resource>%s)%s/"
                      "(?P<protocol>%s)/?"
                      "(?P<session_id>[0-9a-zA-Z]*)/?"
                      "(?P<protocol_init>\d*?)|(?P<xhr_path>\w*?)/?"
                      "(?P<jsonp_index>\d*?)" % (resource,
                                                 extra_re,
                                                 proto_re),
                      cls)

def get_router(handler, settings=None, resource='socket.io/*',
               io_loop=None, extra_re=None, extra_sep=None):
    """Create new router class with desired properties.

    Use this function to create new socket.io server. For example:

       class PongConnection(SocketConnection):
           def on_message(self, message):
               self.send(message)

       PongRouter = get_router(PongConnection)

       application = tornado.web.Application([PongRouter.route()])
    """
    router = type('SocketRouter', (SocketRouterBase,), {})
    router.tornadio_initialize(handler, settings, resource,
                               io_loop, extra_re, extra_sep)
    return router

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
"""
    tornadio.router
    ~~~~~~~~~~~~~~~

    Implements handy wrapper to start FlashSocket server (if FlashSocket
    protocol is enabled). Shamesly borrowed from the SocketTornad.IO project.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

from tornado import ioloop
from tornado.httpserver import HTTPServer

from tornadio.flashserver import FlashPolicyServer

class SocketServer(HTTPServer):
    """HTTP Server which does some configuration and automatic setup
    of Socket.IO based on configuration.
    Starts the IOLoop and listening automatically
    in contrast to the Tornado default behavior.
    If FlashSocket is enabled, starts up the policy server also."""

    def __init__(self, application,
                 no_keep_alive=False, io_loop=None,
                 xheaders=False, ssl_options=None, 
                 auto_start=True
                 ):
        """Initializes the server with the given request callback.

        If you use pre-forking/start() instead of the listen() method to
        start your server, you should not pass an IOLoop instance to this
        constructor. Each pre-forked child process will create its own
        IOLoop instance after the forking process.
        """
        settings = application.settings

        flash_policy_file = settings.get('flash_policy_file', None)
        flash_policy_port = settings.get('flash_policy_port', None)
        socket_io_port = settings.get('socket_io_port', 8001)
        socket_io_address = settings.get('socket_io_address', '')

        io_loop = io_loop or ioloop.IOLoop.instance()

        HTTPServer.__init__(self,
                            application,
                            no_keep_alive,
                            io_loop,
                            xheaders,
                            ssl_options)

        logging.info('Starting up tornadio server on port \'%s\'',
                     socket_io_port)

        self.listen(socket_io_port, socket_io_address)

        if flash_policy_file is not None and flash_policy_port is not None:
            try:
                logging.info('Starting Flash policy server on port \'%d\'',
                             flash_policy_port)

                FlashPolicyServer(
                    io_loop = io_loop,
                    port=flash_policy_port,
                    policy_file=flash_policy_file)
            except Exception, ex:
                logging.error('Failed to start Flash policy server: %s', ex)

        # Set auto_start to False in order to have opportunities 
        # to work with server object and/or perform some actions 
        # after server is already created but before ioloop will start.
        # Attention: if you use auto_start param set to False 
        # you should start ioloop manually
        if auto_start:
            logging.info('Entering IOLoop...')
            io_loop.start()

########NEW FILE########
__FILENAME__ = session
# -*- coding: utf-8 -*-
"""
    tornadio.session
    ~~~~~~~~~~~~~~~~

    Simple heapq-based session implementation with sliding expiration window
    support.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""

from heapq import heappush, heappop
from time import time
from hashlib import md5
from random import random

class Session(object):
    """Represents one session object stored in the session container.
    Derive from this object to store additional data.
    """

    def __init__(self, session_id, expiry=None):
        self.session_id = session_id
        self.promoted = None
        self.expiry = expiry

        if self.expiry is not None:
            self.expiry_date = time() + self.expiry

    def promote(self):
        """Mark object is living, so it won't be collected during next
        run of the session garbage collector.
        """
        if self.expiry is not None:
            self.promoted = time() + self.expiry

    def on_delete(self, forced):
        """Triggered when object was expired or deleted."""
        pass

    def __cmp__(self, other):
        return cmp(self.expiry_date, other.expiry_date)

    def __repr__(self):
        return '%f %s %d' % (getattr(self, 'expiry_date', -1),
                             self.session_id,
                             self.promoted or 0)

def _random_key():
    """Return random session key"""
    i = md5()
    i.update('%s%s' % (random(), time()))
    return i.hexdigest()

class SessionContainer(object):
    def __init__(self):
        self._items = dict()
        self._queue = []

    def create(self, session, expiry=None, **kwargs):
        """Create new session object."""
        kwargs['session_id'] = _random_key()
        kwargs['expiry'] = expiry

        session = session(**kwargs)

        self._items[session.session_id] = session

        if expiry is not None:
            heappush(self._queue, session)

        return session

    def get(self, session_id):
        """Return session object or None if it is not available"""
        return self._items.get(session_id, None)

    def remove(self, session_id):
        """Remove session object from the container"""
        session = self._items.get(session_id, None)

        if session is not None:
            session.promoted = -1
            session.on_delete(True)
            return True

        return False

    def expire(self, current_time=None):
        """Expire any old entries"""
        if not self._queue:
            return

        if current_time is None:
            current_time = time()

        while self._queue:
            # Top most item is not expired yet
            top = self._queue[0]

            # Early exit if item was not promoted and its expiration time
            # is greater than now.
            if top.promoted is None and top.expiry_date > current_time:
                break

            # Pop item from the stack
            top = heappop(self._queue)

            need_reschedule = (top.promoted is not None
                               and top.promoted > current_time)

            # Give chance to reschedule
            if not need_reschedule:
                top.promoted = None
                top.on_delete(False)

                need_reschedule = (top.promoted is not None
                                   and top.promoted > current_time)

            # If item is promoted and expiration time somewhere in future
            # just reschedule it
            if need_reschedule:
                top.expiry_date = top.promoted
                top.promoted = None
                heappush(self._queue, top)
            else:
                del self._items[top.session_id]

########NEW FILE########
