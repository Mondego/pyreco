__FILENAME__ = bench_client
import msgpackrpc
import time;

Num = 10000

def run_call():
    client = msgpackrpc.Client(msgpackrpc.Address("localhost", 18800))
    before = time.time()
    for x in range(Num):
        client.call('sum', 1, 2)
    after = time.time()
    diff = after - before

    print("call: {0} qps".format(Num / diff))

def run_call_async():
    client = msgpackrpc.Client(msgpackrpc.Address("localhost", 18800))
    before = time.time()
    for x in range(Num):
        # TODO: replace with more heavy sample
        future = client.call_async('sum', 1, 2)
        future.get()
    after = time.time()
    diff = after - before

    print("async: {0} qps".format(Num / diff))

def run_notify():
    client = msgpackrpc.Client(msgpackrpc.Address("localhost", 18800))
    before = time.time()
    for x in range(Num):
        client.notify('sum', 1, 2)
    after = time.time()
    diff = after - before

    print("notify: {0} qps".format(Num / diff))

run_call()
run_call_async()
run_notify()

########NEW FILE########
__FILENAME__ = bench_server
import msgpackrpc

class SumServer(object):
    def sum(self, x, y):
        return x + y

server = msgpackrpc.Server(SumServer())
server.listen(msgpackrpc.Address("localhost", 18800))
server.start()

########NEW FILE########
__FILENAME__ = echoserver
#!/usr/bin/env python
# coding: utf-8

"""Echo service.
This server using msgpackrpc.Server.
"""

import msgpackrpc

class EchoHandler(object):

    def echo(self, msg):
        return msg

def serve_background(server, daemon=False):
    def _start_server(server):
        server.start()
        server.close()

    import threading
    t = threading.Thread(target=_start_server, args = (server,))
    t.setDaemon(daemon)
    t.start()
    return t

def serve(daemon=False):
    """Serve echo server in background on localhost.
    This returns (server, port). port is number in integer.

    To stop, use ``server.shutdown()``
    """
    for port in xrange(9000, 10000):
        try:
            addr = msgpackrpc.Address('localhost', port)
            server = msgpackrpc.Server(EchoHandler())
            print server
            server.listen(addr)
            thread = serve_background(server, daemon)
            return (addr, server, thread)
        except Exception as err:
            print err
            pass

if __name__ == '__main__':
    port = serve(False)
    print "Serving on localhost:%d\n" % port[1]


########NEW FILE########
__FILENAME__ = test_client
#!/usr/bin/env python
# coding: utf-8

import msgpackrpc
import echoserver

ADDR = SERVER = THREAD = None


def setup():
    global ADDR, SERVER, THREAD
    (ADDR, SERVER, THREAD) = echoserver.serve()


def teardown():
    global SERVER, THREAD
    SERVER.stop()
    THREAD.join()


def test_client():
    global ADDR
    client = msgpackrpc.Client(ADDR, unpack_encoding = 'utf-8')

    f1 = client.call('echo', 'foo')
    f2 = client.call('echo', 'bar')
    f3 = client.call('echo', 'baz')

    assert f2 == 'bar'
    assert f1 == 'foo'
    assert f3 == 'baz'

    print "EchoHandler#echo via msgpackrpc"


if __name__ == '__main__':
    setup()
    test_client()
    teardown()


########NEW FILE########
__FILENAME__ = address
import socket

from tornado.platform.auto import set_close_exec


class Address(object):
    """\
    The class to represent the RPC address.
    """

    def __init__(self, host, port):
        self._host = host
        self._port = port

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    def unpack(self):
        return (self._host, self._port)

    def socket(self, family=socket.AF_UNSPEC):
        res = socket.getaddrinfo(self._host, self._port, family,
                                 socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[0]
        af, socktype, proto, canonname, sockaddr = res
        sock = socket.socket(af, socktype, proto)
        set_close_exec(sock.fileno())
        sock.setblocking(0)
        if af == socket.AF_INET6:
            if hasattr(socket, "IPPROTO_IPV6"):
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

        return sock

########NEW FILE########
__FILENAME__ = client
from msgpackrpc import Loop
from msgpackrpc import session
from msgpackrpc.transport import tcp

class Client(session.Session):
    """\
    Client is usaful for MessagePack RPC API.
    """

    def __init__(self, address, timeout=10, loop=None, builder=tcp, reconnect_limit=5, pack_encoding='utf-8', unpack_encoding=None):
        loop = loop or Loop()
        session.Session.__init__(self, address, timeout, loop, builder, reconnect_limit, pack_encoding, unpack_encoding)

        if timeout:
            loop.attach_periodic_callback(self.step_timeout, 1000) # each 1s

    @classmethod
    def open(cls, *args):
        assert cls is Client, "should only be called on sub-classes"

        client = Client(*args)
        return Client.Context(client)

    class Context(object):
        """\
        For with statement
        """

        def __init__(self, client):
            self._client = client

        def __enter__(self):
            return self._client

        def __exit__(self, type, value, traceback):
            self._client.close()
            if type:
                return False
            return True

########NEW FILE########
__FILENAME__ = compat
import sys
inPy3k = sys.version_info[0] == 3

if inPy3k:
    def force_str(s):
        if isinstance(s, bytes):
            return s.decode('utf-8')
        return str(s)

    def iteritems(d):
        return d.items()
else:
    def force_str(s):
        return str(s)

    def iteritems(d):
        return d.iteritems()

########NEW FILE########
__FILENAME__ = error
class RPCError(Exception):
    CODE = ".RPCError"

    def __init__(self, message):
        Exception.__init__(self, message)

    @property
    def code(self):
        return self.__class__.CODE

    def to_msgpack(self):
        return [self.message]

    @staticmethod
    def from_msgpack(message):
        return RPCError(message)

class TimeoutError(RPCError):
    CODE = ".TimeoutError"
    pass

class TransportError(RPCError):
    CODE = ".TransportError"
    pass

class CallError(RPCError):
    CODE = ".NoMethodError"
    pass

class NoMethodError(CallError):
    CODE = ".CallError.NoMethodError"
    pass

class ArgumentError(CallError):
    CODE = ".CallError.ArgumentError"
    pass

########NEW FILE########
__FILENAME__ = future
from msgpackrpc import error


class Future(object):
    """
    This class is used as the result of asynchronous call.
    By using join(), the caller is able to wait for the completion.
    """

    def __init__(self, loop, timeout, callback=None):
        self._loop = loop
        self._error = None
        self._result = None
        self._set_flag = False
        self._timeout = timeout
        self._callback = callback
        self._error_handler = None
        self._result_handler = None

    def join(self):
        while (not self._set_flag):
            self._loop.start()

    def get(self):
        self.join()

        assert self._set_flag == True
        if not self._set_flag:
            # TODO: should be designed error !!
            raise error.RPCError(128)

        if self._result is not None:
            if self._result_handler is None:
                return self._result
            else:
                self._result_handler(self._result)
        else:
            if self._error is not None:
                if self._error_handler is not None:
                    self._error_handler(self._error)
                else:
                    if isinstance(self._error, error.RPCError):
                        raise self._error
                    else:
                        raise error.RPCError(self._error)
            else:
                return self._result

    def set(self, error=None, result=None):
        self._error = error
        self._result = result

        if self._callback is not None:
            self._callback(self)

    @property
    def result(self):
        return self._result

    def set_result(self, result):
        self.set(result=result)
        self._set_flag = True

    @property
    def error(self):
        return self._error

    def set_error(self, error):
        self.set(error=error)
        self._set_flag = True

    def attach_callback(self, callback):
        self._callback = callback

    def attach_error_handler(self, handler):
        self._error_handler = handler

    def attach_result_handler(self, handler):
        self._result_handler = handler

    # better name?
    def step_timeout(self):
        if self._timeout < 1:
            return True
        else:
            self._timeout -= 1
            return False


########NEW FILE########
__FILENAME__ = loop
from tornado import ioloop

class Loop(object):
    """\
    An I/O loop class which wraps the Tornado's ioloop.
    """

    @staticmethod
    def instance():
        return Loop(ioloop.IOLoop.instance())

    def __init__(self, loop=None):
        self._ioloop = loop or ioloop.IOLoop()
        self._periodic_callback = None

    def start(self):
        """\
        Starts the Tornado's ioloop if it's not running.
        """

        if not self._ioloop.running():
            self._ioloop.start()

    def stop(self):
        """\
        Stops the Tornado's ioloop if it's running.
        """

        if self._ioloop.running():
            try:
                self._ioloop.stop()
            except:
                return

    def attach_periodic_callback(self, callback, callback_time):
        if self._periodic_callback is not None:
            self.dettach_periodic_callback()

        self._periodic_callback = ioloop.PeriodicCallback(callback, callback_time, self._ioloop)
        self._periodic_callback.start()

    def dettach_periodic_callback(self):
        if self._periodic_callback is not None:
            self._periodic_callback.stop()
        self._periodic_callback = None

########NEW FILE########
__FILENAME__ = message
REQUEST = 0
RESPONSE = 1
NOTIFY = 2

########NEW FILE########
__FILENAME__ = server
import msgpack

from msgpackrpc.compat import force_str
from msgpackrpc import error
from msgpackrpc import Loop
from msgpackrpc import message
from msgpackrpc import session
from msgpackrpc.transport import tcp

class Server(session.Session):
    """\
    Server is usaful for MessagePack RPC Server.
    """

    def __init__(self, dispatcher, loop=None, builder=tcp, pack_encoding='utf-8', unpack_encoding=None):
        self._loop = loop or Loop()
        self._builder = builder
        self._encodings = (pack_encoding, unpack_encoding)
        self._listeners = []
        self._dispatcher = dispatcher

    def listen(self, address):
        listener = self._builder.ServerTransport(address, self._encodings)
        listener.listen(self)
        self._listeners.append(listener)

    def start(self):
        self._loop.start()

    def stop(self):
        self._loop.stop()

    def close(self):
        for listener in self._listeners:
            listener.close()

    def on_request(self, sendable, msgid, method, param):
        self.dispatch(method, param, _Responder(sendable, msgid))

    def on_notify(self, method, param):
        self.dispatch(method, param, _NullResponder())

    def dispatch(self, method, param, responder):
        try:
            method = force_str(method)
            if not hasattr(self._dispatcher, method):
                raise error.NoMethodError("'{0}' method not found".format(method))

            result = getattr(self._dispatcher, method)(*param)
            if isinstance(result, AsyncResult):
                result.set_responder(responder)
            else:
                responder.set_result(result)
        except Exception as e:
            responder.set_error(str(e))

        # TODO: Support advanced and async return


class AsyncResult:
    def __init__(self):
        self._responder = None
        self._result = None

    def set_result(self, value, error=None):
        if self._responder is not None:
            self._responder.set_result(value, error)
        else:
            self._result = [value, error]

    def set_error(self, error, value=None):
        self.set_result(value, error)

    def set_responder(self, responder):
        self._responder = responder
        if self._result is not None:
            self._responder.set_result(*self._result)
            self._result = None


class _Responder:
    def __init__(self, sendable, msgid):
        self._sendable = sendable
        self._msgid = msgid
        self._sent = False

    def set_result(self, value, error=None, packer=msgpack.Packer()):
        if not self._sent:
            self._sendable.send_message([message.RESPONSE, self._msgid, error, value])
            self._sent = True

    def set_error(self, error, value=None):
        self.set_result(value, error)


class _NullResponder:
    def set_result(self, value, error=None):
        pass

    def set_error(self, error, value=None):
        pass

########NEW FILE########
__FILENAME__ = session
from msgpackrpc import Loop
from msgpackrpc import message
from msgpackrpc.future import Future
from msgpackrpc.transport import tcp
from msgpackrpc.compat import iteritems
from msgpackrpc.error import TimeoutError


class Session(object):
    """\
    Session processes send/recv request of the message, by using underlying
    transport layer.

    self._request_table(request table) stores the relationship between messageid and
    corresponding future. When the new requets are sent, the Session generates
    new message id and new future. Then the Session registers them to request table.

    When it receives the message, the Session lookups the request table and set the
    result to the corresponding future.
    """

    def __init__(self, address, timeout, loop=None, builder=tcp, reconnect_limit=5, pack_encoding='utf-8', unpack_encoding=None):
        """\
        :param address: address of the server.
        :param loop:    context object.
        :param builder: builder for creating transport layer
        """

        self._loop = loop or Loop()
        self._address = address
        self._timeout = timeout
        self._transport = builder.ClientTransport(self, self._address, reconnect_limit, encodings=(pack_encoding, unpack_encoding))
        self._generator = _NoSyncIDGenerator()
        self._request_table = {}

    @property
    def address(self):
        return self._address

    def call(self, method, *args):
        return self.send_request(method, args).get()

    def call_async(self, method, *args):
        return self.send_request(method, args)

    def send_request(self, method, args):
        # need lock?
        msgid = next(self._generator)
        future = Future(self._loop, self._timeout)
        self._request_table[msgid] = future
        self._transport.send_message([message.REQUEST, msgid, method, args])
        return future

    def notify(self, method, *args):
        def callback():
            self._loop.stop()
        self._transport.send_message([message.NOTIFY, method, args], callback=callback)
        self._loop.start()

    def close(self):
        if self._transport:
            self._transport.close()
        self._transport = None
        self._request_table = {}

    def on_connect_failed(self, reason):
        """
        The callback called when the connection failed.
        Called by the transport layer.
        """
        # set error for all requests
        for msgid, future in iteritems(self._request_table):
            future.set_error(reason)

        self._request_table = {}
        self.close()
        self._loop.stop()

    def on_response(self, msgid, error, result):
        """\
        The callback called when the message arrives.
        Called by the transport layer.
        """

        if not msgid in self._request_table:
            # TODO: Check timed-out msgid?
            #raise RPCError("Unknown msgid: id = {0}".format(msgid))
            return
        future = self._request_table.pop(msgid)

        if error is not None:
            future.set_error(error)
        else:
            future.set_result(result)
        self._loop.stop()

    def on_timeout(self, msgid):
        future = self._request_table.pop(msgid)
        future.set_error("Request timed out")

    def step_timeout(self):
        timeouts = []
        for msgid, future in iteritems(self._request_table):
            if future.step_timeout():
                timeouts.append(msgid)

        if len(timeouts) == 0:
            return

        self._loop.stop()
        for timeout in timeouts:
            future = self._request_table.pop(timeout)
            future.set_error(TimeoutError("Request timed out"))
        self._loop.start()


def _NoSyncIDGenerator():
    """
    Message ID Generator.

    NOTE: Don't use in multithread. If you want use this
    in multithreaded application, use lock.
    """
    counter = 0
    while True:
        yield counter
        counter += 1
        if counter > (1 << 30):
            counter = 0

########NEW FILE########
__FILENAME__ = tcp
import msgpack
from tornado import netutil
from tornado.iostream import IOStream

import msgpackrpc.message
from msgpackrpc.error import RPCError, TransportError


class BaseSocket(object):
    def __init__(self, stream, encodings):
        self._stream = stream
        self._packer = msgpack.Packer(encoding=encodings[0], default=lambda x: x.to_msgpack())
        self._unpacker = msgpack.Unpacker(encoding=encodings[1])

    def close(self):
        self._stream.close()

    def send_message(self, message, callback=None):
        self._stream.write(self._packer.pack(message), callback=callback)

    def on_read(self, data):
        self._unpacker.feed(data)
        for message in self._unpacker:
            self.on_message(message)

    def on_message(self, message, *args):
        msgsize = len(message)
        if msgsize != 4 and msgsize != 3:
            raise RPCError("Invalid MessagePack-RPC protocol: message = {0}".format(message))

        msgtype = message[0]
        if msgtype == msgpackrpc.message.REQUEST:
            self.on_request(message[1], message[2], message[3])
        elif msgtype == msgpackrpc.message.RESPONSE:
            self.on_response(message[1], message[2], message[3])
        elif msgtype == msgpackrpc.message.NOTIFY:
            self.on_notify(message[1], message[2])
        else:
            raise RPCError("Unknown message type: type = {0}".format(msgtype))

    def on_request(self, msgid, method, param):
        raise NotImplementedError("on_request not implemented");

    def on_response(self, msgid, error, result):
        raise NotImplementedError("on_response not implemented");

    def on_notify(self, method, param):
        raise NotImplementedError("on_notify not implemented");


class ClientSocket(BaseSocket):
    def __init__(self, stream, transport, encodings):
        BaseSocket.__init__(self, stream, encodings)
        self._transport = transport
        self._stream.set_close_callback(self.on_close)

    def connect(self):
        self._stream.connect(self._transport._address.unpack(), self.on_connect)

    def on_connect(self):
        self._stream.read_until_close(self.on_read, self.on_read)
        self._transport.on_connect(self)

    def on_connect_failed(self):
        self._transport.on_connect_failed(self)

    def on_close(self):
        self._transport.on_close(self)

    def on_response(self, msgid, error, result):
        self._transport._session.on_response(msgid, error, result)


class ClientTransport(object):
    def __init__(self, session, address, reconnect_limit, encodings=('utf-8', None)):
        self._session = session
        self._address = address
        self._encodings = encodings
        self._reconnect_limit = reconnect_limit;

        self._connecting = 0
        self._pending = []
        self._sockets = []
        self._closed  = False

    def send_message(self, message, callback=None):
        if len(self._sockets) == 0:
            if self._connecting == 0:
                self.connect()
                self._connecting = 1
            self._pending.append((message, callback))
        else:
            sock = self._sockets[0]
            sock.send_message(message, callback)

    def connect(self):
        stream = IOStream(self._address.socket(), io_loop=self._session._loop._ioloop)
        socket = ClientSocket(stream, self, self._encodings)
        socket.connect();

    def close(self):
        for sock in self._sockets:
            sock.close()

        self._connecting = 0
        self._pending = []
        self._sockets = []
        self._closed  = True

    def on_connect(self, sock):
        self._sockets.append(sock)
        for pending, callback in self._pending:
            sock.send_message(pending, callback)
        self._pending = []

    def on_connect_failed(self, sock):
        if self._connecting < self._reconnect_limit:
            self.connect()
            self._connecting += 1
        else:
            self._connecting = 0
            self._pending = []
            self._session.on_connect_failed(TransportError("Retry connection over the limit"))

    def on_close(self, sock):
        # Avoid calling self.on_connect_failed after self.close called.
        if self._closed:
            return

        if sock in self._sockets:
            self._sockets.remove(sock)
        else:
            # Tornado does not have on_connect_failed event.
            self.on_connect_failed(sock)


class ServerSocket(BaseSocket):
    def __init__(self, stream, transport, encodings):
        BaseSocket.__init__(self, stream, encodings)
        self._transport = transport
        self._stream.read_until_close(self.on_read, self.on_read)

    def on_close(self):
        self._transport.on_close(self)

    def on_request(self, msgid, method, param):
        self._transport._server.on_request(self, msgid, method, param)

    def on_notify(self, method, param):
        self._transport._server.on_notify(method, param)


class MessagePackServer(netutil.TCPServer):
    def __init__(self, transport, io_loop=None, encodings=None):
        self._transport = transport
        self._encodings = encodings
        netutil.TCPServer.__init__(self, io_loop=io_loop)

    def handle_stream(self, stream, address):
        ServerSocket(stream, self._transport, self._encodings)


class ServerTransport(object):
    def __init__(self, address, encodings=('utf-8', None)):
        self._address = address;
        self._encodings = encodings

    def listen(self, server):
        self._server = server;
        self._mp_server = MessagePackServer(self, io_loop=self._server._loop._ioloop, encodings=self._encodings)
        self._mp_server.listen(self._address.port, address=self._address.host)

    def close(self):
        self._mp_server.stop()

########NEW FILE########
__FILENAME__ = _version
__version__ = '0.3.1'

########NEW FILE########
__FILENAME__ = helper
import os
import sys

def unused_port():
    import socket

    sock = socket.socket()
    sock.bind(("localhost", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

########NEW FILE########
__FILENAME__ = test_msgpackrpc
from time import sleep
import threading
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import helper
import msgpackrpc
from msgpackrpc import error


class TestMessagePackRPC(unittest.TestCase):
    ENABLE_TIMEOUT_TEST = False

    class TestArg:
        ''' this class must know completely how to deserialize '''
        def __init__(self, a, b, c):
            self.a = a
            self.b = b
            self.c = c

        def to_msgpack(self):
            return (self.a, self.b, self.c)

        def add(self, rhs):
            self.a += rhs.a
            self.b -= rhs.b
            self.c *= rhs.c
            return self

        def __eq__(self, rhs):
            return (self.a == rhs.a and self.b == rhs.b and self.c == rhs.c)

        @staticmethod
        def from_msgpack(arg):
            return TestMessagePackRPC.TestArg(arg[0], arg[1], arg[2])

    class TestServer(object):
        def hello(self):
            return "world"

        def sum(self, x, y):
            return x + y

        def nil(self):
            return None

        def add_arg(self, arg0, arg1):
            lhs = TestMessagePackRPC.TestArg.from_msgpack(arg0)
            rhs = TestMessagePackRPC.TestArg.from_msgpack(arg1)
            return lhs.add(rhs)

        def raise_error(self):
            raise Exception('error')

        def long_exec(self):
            sleep(3)
            return 'finish!'

        def async_result(self):
            ar = msgpackrpc.server.AsyncResult()
            def do_async():
                sleep(2)
                ar.set_result("You are async!")
            threading.Thread(target=do_async).start()
            return ar

    def setUp(self):
        self._address = msgpackrpc.Address('localhost', helper.unused_port())

    def setup_env(self):
        def _on_started():
            self._server._loop.dettach_periodic_callback()
            lock.release()
        def _start_server(server):
            server._loop.attach_periodic_callback(_on_started, 1)
            server.start()
            server.close()

        self._server = msgpackrpc.Server(TestMessagePackRPC.TestServer())
        self._server.listen(self._address)
        self._thread = threading.Thread(target=_start_server, args=(self._server,))

        lock = threading.Lock()
        self._thread.start()
        lock.acquire()
        lock.acquire()   # wait for the server to start

        self._client = msgpackrpc.Client(self._address, unpack_encoding='utf-8')
        return self._client;

    def tearDown(self):
        self._client.close();
        self._server.stop();
        self._thread.join();

    def test_call(self):
        client = self.setup_env();

        result1 = client.call('hello')
        result2 = client.call('sum', 1, 2)
        result3 = client.call('nil')

        self.assertEqual(result1, "world", "'hello' result is incorrect")
        self.assertEqual(result2, 3, "'sum' result is incorrect")
        self.assertIsNone(result3, "'nil' result is incorrect")

    def test_call_userdefined_arg(self):
        client = self.setup_env();

        arg = TestMessagePackRPC.TestArg(0, 1, 2)
        arg2 = TestMessagePackRPC.TestArg(23, 3, -23)

        result1 = TestMessagePackRPC.TestArg.from_msgpack(client.call('add_arg', arg, arg2))
        self.assertEqual(result1, arg.add(arg2))

        result2 = TestMessagePackRPC.TestArg.from_msgpack(client.call('add_arg', arg2, arg))
        self.assertEqual(result2, arg2.add(arg))

        result3 = TestMessagePackRPC.TestArg.from_msgpack(client.call('add_arg', result1, result2))
        self.assertEqual(result3, result1.add(result2))

    def test_call_async(self):
        client = self.setup_env();

        future1 = client.call_async('hello')
        future2 = client.call_async('sum', 1, 2)
        future3 = client.call_async('nil')
        future1.join()
        future2.join()
        future3.join()

        self.assertEqual(future1.result, "world", "'hello' result is incorrect in call_async")
        self.assertEqual(future2.result, 3, "'sum' result is incorrect in call_async")
        self.assertIsNone(future3.result, "'nil' result is incorrect in call_async")

    def test_notify(self):
        client = self.setup_env();

        result = True
        try:
            client.notify('hello')
            client.notify('sum', 1, 2)
            client.notify('nil')
        except:
            result = False

        self.assertTrue(result)

    def test_raise_error(self):
        client = self.setup_env();
        self.assertRaises(error.RPCError, lambda: client.call('raise_error'))

    def test_unknown_method(self):
        client = self.setup_env();
        self.assertRaises(error.RPCError, lambda: client.call('unknown', True))
        try:
            client.call('unknown', True)
            self.assertTrue(False)
        except error.RPCError as e:
            message = e.args[0]
            self.assertEqual(message, "'unknown' method not found", "Error message mismatched")

    def test_async_result(self):
        client = self.setup_env();
        self.assertEqual(client.call('async_result'), "You are async!")

    def test_connect_failed(self):
        client = self.setup_env();
        port = helper.unused_port()
        client = msgpackrpc.Client(msgpackrpc.Address('localhost', port), unpack_encoding='utf-8')
        self.assertRaises(error.TransportError, lambda: client.call('hello'))

    def test_timeout(self):
        client = self.setup_env();

        if self.__class__.ENABLE_TIMEOUT_TEST:
            self.assertEqual(client.call('long_exec'), 'finish!', "'long_exec' result is incorrect")

            client = msgpackrpc.Client(self._address, timeout=1, unpack_encoding='utf-8')
            self.assertRaises(error.TimeoutError, lambda: client.call('long_exec'))
        else:
            print("Skip test_timeout")


if __name__ == '__main__':
    import sys

    try:
        sys.argv.remove('--timeout-test')
        TestMessagePackRPC.ENABLE_TIMEOUT_TEST = True
    except:
        pass

    unittest.main()

########NEW FILE########
