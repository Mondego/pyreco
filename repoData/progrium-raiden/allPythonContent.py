__FILENAME__ = http.conf
http_port = 8088
backend_port = 9989

def service():
    from raiden.gateways.httpstream import HttpStreamGateway
    from raiden.gateways.websocket import WebSocketGateway
    from raiden.pubsub import MessagingBackend
    from gevent_tools.service import Service
    import gevent, random, json
    
    class HttpStreamer(Service):
        def __init__(self):
            self.backend = MessagingBackend()
            self.http_frontend = HttpStreamGateway(self.backend)
            self.ws_frontend = WebSocketGateway(self.backend, attach_to=self.http_frontend.wsgi_server)
            
            self.add_service(self.backend)
            self.add_service(self.http_frontend)
            self.add_service(self.ws_frontend)
        
        def do_start(self):
            print "Gateway listening on %s..." % self.http_frontend.port
            self.backend.cluster.add('127.0.0.1')
            self.spawn(self.message_publisher)
        
        def message_publisher(self):
            while True:
                self.backend.publish('localhost:%s/test' % self.http_frontend.port, 
                    dict(foo='bar', baz=random.choice(['one', 'two', 'three'])))
                print self.backend.router.subscriber_counts
                gevent.sleep(2)
    
    return HttpStreamer()

########NEW FILE########
__FILENAME__ = test.conf
http_port = 8088
backend_port = 9989

def service():
    from gevent_tools.service import Service
    from raiden.pubsub import MessagingBackend
    from raiden.gateways.httpstream import HttpStreamGateway
    from raiden.gateways.websocket import WebSocketGateway
    
    class MyService(Service):
        def __init__(self):
            self.backend = MessagingBackend()
            self.frontend = HttpStreamGateway(self.backend)
            
            self.add_service(self.backend)
            self.add_service(self.frontend)
            
            self.gateway = WebSocketGateway(attach_to=self.frontend.wsgi_server)
            self.add_service(self.gateway)
        
        def do_start(self):
            pass
    
    return MyService()
########NEW FILE########
__FILENAME__ = httpstream
import json
import errno
import socket

import gevent.pywsgi
import gevent.queue
import webob

from gevent_tools.config import Option
from gevent_tools.service import Service

import raiden.patched
from raiden.pubsub import MessagingBackend
from raiden.pubsub import Subscription

class HttpStreamGateway(Service):
    port = Option('http_port', default=80)
    channel_builder = Option('http_channel_builder', 
                        default=lambda req: '%s%s' % (req.host, req.path))
    
    def __init__(self, backend):
        self.backend = backend
        self.wsgi_server = _WSGIServer(self)
        
        self.add_service(self.wsgi_server)
        
        # This is to catch errno.ECONNRESET error created
        # by WSGIServer when it tries to read after writing
        # to a broken pipe, which is already caught and used 
        # for handling disconnects.
        self.catch(IOError, lambda e,g: None)
    
    def handle(self, env, start_response):
        if env['REQUEST_METHOD'] == 'POST':
            return self.handle_publish(env, start_response)
        elif env['REQUEST_METHOD'] == 'GET':
            return self.handle_subscribe(env, start_response)
        else:
            start_response('405 Method not allowed', [])
            return ["Method not allowed\n"]
    
    def handle_publish(self, env, start_response):
        request = webob.Request(env)
        if request.content_type.endswith('/json'):
            try:
                message = json.loads(request.body)
            except ValueError:
                start_response('400 Invalid JSON', [
                    ('Content-Type', 'text/plain')])
                return ["Invalid JSON"]
        elif request.content_type.startswith('text/'):
            message = {'_': request.body}
        else:
            message = dict(request.str_POST)
        self.backend.publish(
            self.channel_builder(request), message)
        start_response('200 OK', [
            ('Content-Type', 'text/plain')])
        return ["OK\n"]
    
    def handle_subscribe(self, env, start_response):
        request = webob.Request(env)
        filters = request.str_GET.items()
        subscription = self.backend.subscribe(
            self.channel_builder(request), filters=filters)
        yield subscription # send to container to include on disconnect
        
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Connection', 'keep-alive'),
            ('Cache-Control', 'no-cache, must-revalidate'),
            ('Expires', 'Tue, 11 Sep 1985 19:00:00 GMT'),])
        for msgs in subscription:
            if msgs is None:
                yield '\n'
            else:
                yield '%s\n' % '\n'.join(msgs)
    
    def handle_disconnect(self, socket, subscription):
        subscription.cancel()

class _WSGIServer(gevent.pywsgi.WSGIServer):
    """
    Custom WSGI container that is made to work with HttpStreamGateway, but more
    importantly catches disconnects and passes the event as `handle_disconnect`
    to the gateway. The only weird thing is that we modify the protocol of WSGI
    in that the application's first yield (or first element of returned list,
    but we're streaming, so we use yield) will be some kind of object that will
    be passed to the disconnect handler to identify the request.
    """
    
    class handler_class(raiden.patched.WSGIHandler):
        def process_result(self):
            if hasattr(self.result, 'next'):
                request_obj = self.result.next()
                try:
                    super(self.__class__, self).process_result()
                except socket.error, ex:
                    # Broken pipe, connection reset by peer
                    if ex[0] in (errno.EPIPE, errno.ECONNRESET):
                        self.close_connection = True
                        if hasattr(self.server.gateway, 'handle_disconnect'):
                            self.server.gateway.handle_disconnect(
                                                    self.socket, request_obj)
                    else:
                        raise
            else:
                super(self.__class__, self).process_result()
    
    def __init__(self, gateway):
        self.gateway = gateway
        super(_WSGIServer, self).__init__(
            listener=('127.0.0.1', gateway.port),
            application=gateway.handle,
            spawn=gateway.spawn,
            log=None)
########NEW FILE########
__FILENAME__ = websocket
import json

import gevent.pywsgi
from gevent_tools.config import Option
from gevent_tools.service import Service
from ws4py.server.wsgi.middleware import WebSocketUpgradeMiddleware as HybiUpgrader

import raiden.patched
from raiden.vendor.websocket_hixie import WebSocketUpgradeMiddleware as HixieUpgrader
from raiden.vendor.websocket_hixie import WebSocketError
    
class WebSocketGateway(Service):
    port = Option('websocket_port', default=8080)
    path = Option('websocket_path', default='/-/websocket')
    
    def __init__(self, backend, attach_to=None):
        self.backend = backend
        
        if attach_to is None:
            self.server = gevent.pywsgi.WSGIServer(('127.0.0.1', self.port), 
                            application=WebSocketMiddleware(self.path, self.handle),
                            handler_class=raiden.patched.WSGIHandler)
            self.add_service(self.server)
        else:
            self.server = attach_to
            self.server.application = WebSocketMiddleware(self.path, 
                                        self.handle, self.server.application)
    
    def handle(self, websocket, environ):
        while not websocket.terminated:
            ctl_message = websocket.receive()
            if ctl_message is not None:
                try:
                    ctl_message = json.loads(ctl_message)
                except ValueError:
                    continue # TODO: log error
                if 'cmd' in ctl_message:
                    cmd = ctl_message.pop('cmd')
                    self.spawn(getattr(self, 'handle_%s' % cmd), websocket, **ctl_message)
    
    def handle_subscribe(self, websocket, channel, filters=None):
        subscription = self.backend.subscribe(channel, filters)
        for msgs in subscription:
            if msgs is None:
                websocket.send('\n')
            else:
                websocket.send('%s\n' % '\n'.join(msgs))
        

class WebSocketMiddleware(object):
    def __init__(self, path, handler, fallback_app=None):
        self.path = path
        self.handler = handler
        self.fallback_app = fallback_app or self.default_fallback
        self.upgrader = HybiUpgrader(self.handler, HixieUpgrader(self.handler)) 
    
    def __call__(self, environ, start_response):
        if environ.get('PATH_INFO') == self.path:
            try:
                return self.upgrader(environ, start_response)
            except WebSocketError, e:
                return self.fallback_app(environ, start_response)
        else:
            return self.fallback_app(environ, start_response)

    def default_fallback(self, environ, start_response):
        start_response("404 Not Found", [])
        return ["Not Found"]
########NEW FILE########
__FILENAME__ = patched
from ws4py.server.geventserver import UpgradableWSGIHandler as WSGIHandler
########NEW FILE########
__FILENAME__ = pubsub
import collections
import time
import json

import msgpack
import gevent.queue
from gevent_zeromq import zmq

from gevent_tools.config import Option
from gevent_tools.service import Service
from gevent_tools.service import require_ready

context = zmq.Context()

class MessagingException(Exception): pass

class Subscription(gevent.queue.Queue):
    keepalive_secs = Option('keepalive', default=30)
    
    def __init__(self, router, channel, filters=None):
        super(Subscription, self).__init__(maxsize=64)
        self.channel = str(channel)
        self.router = router
        self.filters = filters
        router.subscribe(channel, self)
        router.spawn(self._keepalive)
    
    def _keepalive(self):
        while self.router:
            self.put(None)
            gevent.sleep(self.keepalive_secs)
    
    def cancel(self):
        self.router.unsubscribe(self.channel, self)
        self.router = None
    
    def put(self, messages):
        # Always allow None since it represents a keepalive
        if messages is not None: 
            # Perform any filtering
            if self.filters and len(messages):
                def _filter(message):
                    # Make sure all keys in filter are in message
                    required_keys = set([k for k,v in self.filters])
                    if not required_keys.issubset(message.keys()): 
                        return False
                    # OR across filters with same key, AND across keys
                    matches = []
                    for key in message:
                        values = [v for k,v in self.filters if k == key]
                        if len(values):
                            matches.append(message[key] in values)
                    return all(matches)
                messages = filter(_filter, messages)
                if not len(messages): return
            # Serialize to JSON strings
            messages = map(json.dumps, messages)
        super(Subscription, self).put(messages)
    
    def __del__(self):
        if self.router:
            self.cancel()
        

class Observable(object):
    # TODO: move to a util module
    
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if not observer in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        try:
            self._observers.remove(observer)
        except ValueError:
            pass

    def notify(self, *args, **kwargs):
        for observer in self._observers:
            if hasattr(observer, '__call__'):
                observer(*args, **kwargs)
            else:
                observer.update(*args, **kawrgs)

class ClusterRoster(Observable):
    def __init__(self):
        super(ClusterRoster, self).__init__()
        self._roster = set()
    
    def add(self, host):
        self._roster.add(host)
        self.notify(add=host)
    
    def remove(self, host):
        self._roster.discard(host)
        self.notify(remove=host)
    
    def __iter__(self):
        return self._roster.__iter__()
    

class MessagingBackend(Service):
    port = Option('backend_port')
    
    def __init__(self):
        self.cluster = ClusterRoster()
        self.publisher = MessagePublisher(self.cluster, self.port)
        self.router = MessageRouter('tcp://127.0.0.1:%s' % self.port)
        
        self.add_service(self.publisher)
        self.add_service(self.router)
    
    def publish(self, channel, message):
        self.publisher.publish(channel, message)
    
    def subscribe(self, channel, filters=None):
        return Subscription(self.router, channel, filters)

class MessagePublisher(Service):
    # TODO: batching socket sends based on publish frequency.
    # Although that probably won't provide benefit unless under
    # SUPER high load.
    
    def __init__(self, cluster, port):
        self.cluster = cluster
        self.port = port
        self.socket = context.socket(zmq.PUB)
    
    def do_start(self):
        for host in self.cluster:
            self.connect(host)
        def connector(add=None, remove=None):
            if add: self.connect(add)
        self.cluster.attach(connector)
    
    def connect(self, host):
        self.socket.connect('tcp://%s:%s' % (host, self.port))
    
    @require_ready
    def publish(self, channel, message):
        self.socket.send_multipart([str(channel).lower(), msgpack.packb(message)])

class MessageRouter(Service):
    max_channels = Option('max_channels', default=65536)
    max_subscribers = Option('max_subscribers', default=65536)
    
    def __init__(self, address):
        self.address = address
        self.socket = context.socket(zmq.SUB)
        
        self.channels = dict()
        self.subscriber_counts = collections.Counter()
    
    def do_start(self):
        self.socket.bind(self.address)
        self.spawn(self._listen)
    
    def subscribe(self, channel, subscriber):
        channel = str(channel).lower()
        
        # Initialize channel if necessary
        if not self.channels.get(channel):
            if len(self.channels) >= self.max_channels:
                raise MessagingException(
                        "Unable to init channel. Max channels reached: %s" % 
                            self.max_channels)
            self.channels[channel] = ChannelDispatcher(self)
        
        # Create subscription unless max reached
        if sum(self.subscriber_counts.values()) >= self.max_subscribers:
            raise MessagingException(
                    "Unable to subscribe. Max subscribers reached: %s" % 
                        self.max_subscribers)
        self.socket.setsockopt(zmq.SUBSCRIBE, channel)
        self.subscriber_counts[channel] += 1
        self.channels[channel].add(subscriber)
    
    def unsubscribe(self, channel, subscriber):
        channel = str(channel).lower()
        
        self.socket.setsockopt(zmq.UNSUBSCRIBE, channel)
        self.subscriber_counts[channel] -= 1
        self.channels[channel].remove(subscriber)
        
        # Clean up counts and ChannelDispatchers with no subscribers
        self.subscriber_counts += collections.Counter()
        if not self.subscriber_counts[channel]:
            del self.channels[channel]
    
    def _listen(self):
        while True:
            channel, message = self.socket.recv_multipart()
            if self.subscriber_counts[channel]:
                self.channels[channel].send(msgpack.unpackb(message))

class ChannelDispatcher(object):
    def __init__(self, router):
        self.router = router
        self.purge()
    
    def purge(self):
        self.buffer = []
        self.subscribers = set()
        self.draining = False
    
    def send(self, message):
        self.buffer.append(message)
        self.drain()
    
    def add(self, subscriber):
        self.subscribers.add(subscriber)
    
    def remove(self, subscriber):
        self.subscribers.remove(subscriber)
        if not len(self.subscribers):
            self.purge()
    
    def drain(self):
        """
        Unless already draining, this creates a greenlet that will flush the 
        buffer to subscribers then delay the next flush depending on how many 
        subscribers there are. This continues until the buffer remains empty.
        It will start again with the next call to send(). Since the buffer is 
        flushed to a subscriber and a subscriber is ultimately an open socket, 
        this helps reduce the number of socket operations when there are a 
        large number of open sockets.
        """
        if self.draining:
            return
        def _drain():
            self.draining = True
            while self.draining and self.buffer:
                start_time = time.time()
                batch = self.buffer[:]
                if batch:
                    del self.buffer[:]
                    for subscriber in self.subscribers:
                        if hasattr(subscriber, 'put'):
                            subscriber.put(batch)
                        else:
                            subscriber(batch)
                delta_time = time.time() - start_time
                interval = self._batch_interval()
                if delta_time > interval:
                    gevent.sleep(0.0) # yield
                else:
                    gevent.sleep(interval - delta_time)
            self.draining = False
        self.router.spawn(_drain)
    
    def _batch_interval(self):
        if len(self.subscribers) <= 10:
            return 0.0
        elif len(self.subscribers) <= 100:
            return 0.25
        elif len(self.subscribers) <= 1000:
            return 0.5
        else:
            return 1.0
########NEW FILE########
__FILENAME__ = websocket_hixie
import re
import struct
from hashlib import md5
from socket import error

from gevent.pywsgi import WSGIHandler
from gevent.event import Event
from gevent.coros import Semaphore

# This module implements the Websocket protocol draft version as of May 23, 2010
# based on the gevent-websocket project by Jeffrey Gelens

class WebSocketError(error):
    pass

class WebSocket(object):
    def __init__(self, sock, environ):
        self.rfile = sock.makefile('rb', -1)
        self.socket = sock
        self.origin = environ.get('HTTP_ORIGIN')
        self.protocol = environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL', 'unknown')
        self.path = environ.get('PATH_INFO')
        self._writelock = Semaphore(1)

    def send(self, message):
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        elif isinstance(message, str):
            message = unicode(message).encode('utf-8')
        else:
            raise Exception("Invalid message encoding")

        with self._writelock:
            self.socket.sendall("\x00" + message + "\xFF")

    @property
    def terminated(self):
        """
        Returns True if both the client and server have been
        marked as terminated.
        """
        return self.socket is None

    def detach(self):
        self.socket = None
        self.rfile = None
        self.handler = None

    def close(self):
        # TODO implement graceful close with 0xFF frame
        if self.socket is not None:
            try:
                self.socket.close()
            except Exception:
                pass
            self.detach()


    def _message_length(self):
        # TODO: buildin security agains lengths greater than 2**31 or 2**32
        length = 0

        while True:
            byte_str = self.rfile.read(1)

            if not byte_str:
                return 0
            else:
                byte = ord(byte_str)

            if byte != 0x00:
                length = length * 128 + (byte & 0x7f)
                if (byte & 0x80) != 0x80:
                    break

        return length

    def _read_until(self):
        bytes = []

        while True:
            byte = self.rfile.read(1)
            if ord(byte) != 0xff:
                bytes.append(byte)
            else:
                break

        return ''.join(bytes)

    def receive(self):
        while not self.terminated:
            frame_str = self.rfile.read(1)
            if not frame_str:
                # Connection lost?
                self.close()
                break
            else:
                frame_type = ord(frame_str)


            if (frame_type & 0x80) == 0x00: # most significant byte is not set
                if frame_type == 0x00:
                    bytes = self._read_until()
                    return bytes.decode("utf-8", "replace")
                else:
                    self.close()
            elif (frame_type & 0x80) == 0x80: # most significant byte is set
                # Read binary data (forward-compatibility)
                if frame_type != 0xff:
                    self.close()
                    break
                else:
                    length = self._message_length()
                    if length == 0:
                        self.close()
                        break
                    else:
                        self.rfile.read(length) # discard the bytes
            else:
                raise IOError("Reveiced an invalid message")

class WebSocketUpgradeMiddleware(object):
    """ Automatically upgrades the connection to websockets. """
    def __init__(self, handler):
        self.handler = handler

    def __call__(self, environ, start_response):
        if environ.get('upgrade.protocol') != 'websocket':
            raise WebSocketError("Not a websocket upgrade")
        
        self.environ = environ
        self.socket = self.environ.get('upgrade.socket')
        self.websocket = WebSocket(self.socket, self.environ)

        headers = [
            ("Upgrade", "WebSocket"),
            ("Connection", "Upgrade"),
        ]

        # Detect the Websocket protocol
        if "HTTP_SEC_WEBSOCKET_KEY1" in environ:
            version = 76
        else:
            version = 75

        if version == 75:
            headers.extend([
                ("WebSocket-Origin", self.websocket.origin),
                ("WebSocket-Protocol", self.websocket.protocol),
                ("WebSocket-Location", "ws://%s%s" % (self.environ.get('HTTP_HOST'), self.websocket.path)),
            ])
            start_response("101 Web Socket Hixie Handshake", headers)
        elif version == 76:
            challenge = self._get_challenge()
            headers.extend([
                ("Sec-WebSocket-Origin", self.websocket.origin),
                ("Sec-WebSocket-Protocol", self.websocket.protocol),
                ("Sec-WebSocket-Location", "ws://%s%s" % (self.environ.get('HTTP_HOST'), self.websocket.path)),
            ])

            start_response("101 Web Socket Hixie Handshake", headers)
            self.socket.sendall(challenge)
        else:
            raise WebSocketError("WebSocket version not supported")

        self.environ['websocket.version'] = 'hixie%s' % version

        self.handler(self.websocket, self.environ)
        #self.websocket.finished.wait()


    def _get_key_value(self, key_value):
        key_number = int(re.sub("\\D", "", key_value))
        spaces = re.subn(" ", "", key_value)[1]

        if key_number % spaces != 0:
            raise WebSocketError("key_number %d is not an intergral multiple of"
                                 " spaces %d" % (key_number, spaces))

        return key_number / spaces

    def _get_challenge(self):
        key1 = self.environ.get('HTTP_SEC_WEBSOCKET_KEY1')
        key2 = self.environ.get('HTTP_SEC_WEBSOCKET_KEY2')

        if not key1:
            raise WebSocketError("SEC-WEBSOCKET-KEY1 header is missing")
        if not key2:
            raise WebSocketError("SEC-WEBSOCKET-KEY2 header is missing")

        part1 = self._get_key_value(self.environ['HTTP_SEC_WEBSOCKET_KEY1'])
        part2 = self._get_key_value(self.environ['HTTP_SEC_WEBSOCKET_KEY2'])

        # This request should have 8 bytes of data in the body
        key3 = self.environ.get('wsgi.input').rfile.read(8)

        return md5(struct.pack("!II", part1, part2) + key3).digest()


########NEW FILE########
