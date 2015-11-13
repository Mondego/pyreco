__FILENAME__ = core
import asyncio.events
import errno
import re
import sys
import threading
import weakref
import zmq

from asyncio.transports import _FlowControlMixin
from collections import deque, Iterable, Set
from ipaddress import ip_address

from .interface import ZmqTransport
from .selector import ZmqSelector


if sys.platform == 'win32':
    from asyncio.windows_events import SelectorEventLoop
else:
    from asyncio.unix_events import SelectorEventLoop, SafeChildWatcher


__all__ = ['ZmqEventLoop', 'ZmqEventLoopPolicy']


class ZmqEventLoop(SelectorEventLoop):
    """ZeroMQ event loop.

    Follows asyncio.AbstractEventLoop specification, in addition implements
    create_zmq_connection method for working with ZeroMQ sockets.
    """

    def __init__(self, *, zmq_context=None):
        super().__init__(selector=ZmqSelector())
        if zmq_context is None:
            self._zmq_context = zmq.Context.instance()
        else:
            self._zmq_context = zmq_context
        self._zmq_sockets = weakref.WeakSet()

    def close(self):
        for zmq_sock in self._zmq_sockets:
            if not zmq_sock.closed:
                zmq_sock.close()
        super().close()

    @asyncio.coroutine
    def create_zmq_connection(self, protocol_factory, zmq_type, *,
                              bind=None, connect=None, zmq_sock=None):
        """A coroutine which creates a ZeroMQ connection endpoint.

        The return value is a pair of (transport, protocol),
        where transport support ZmqTransport interface.

        protocol_factory should instantiate object with ZmqProtocol interface.

        zmq_type is type of ZeroMQ socket (zmq.REQ, zmq.REP, zmq.PUB, zmq.SUB,
        zmq.PAIR, zmq.DEALER, zmq.ROUTER, zmq.PULL, zmq.PUSH, etc.)

        bind is string or iterable of strings that specifies enpoints.
        Every endpoint creates ending for acceptin connections
        and binds it to the transport.
        Other side should use connect parameter to connect to this transport.
        See http://api.zeromq.org/master:zmq-bind for details.

        connect is string or iterable of strings that specifies enpoints.
        Every endpoint connects transport to specified transport.
        Other side should use bind parameter to wait for incoming connections.
        See http://api.zeromq.org/master:zmq-connect for details.

        endpoint is a string consisting of two parts as follows:
        transport://address.

        The transport part specifies the underlying transport protocol to use.
        The meaning of the address part is specific to the underlying
        transport protocol selected.

        The following transports are defined:

        inproc - local in-process (inter-thread) communication transport,
        see http://api.zeromq.org/master:zmq-inproc.

        ipc - local inter-process communication transport,
        see http://api.zeromq.org/master:zmq-ipc

        tcp - unicast transport using TCP,
        see http://api.zeromq.org/master:zmq_tcp

        pgm, epgm - reliable multicast transport using PGM,
        see http://api.zeromq.org/master:zmq_pgm

        zmq_sock is a zmq.Socket instance to use preexisting object
        with created transport.
        """

        try:
            if zmq_sock is None:
                zmq_sock = self._zmq_context.socket(zmq_type)
            elif zmq_sock.getsockopt(zmq.TYPE) != zmq_type:
                raise ValueError('Invalid zmq_sock type')
        except zmq.ZMQError as exc:
            raise OSError(exc.errno, exc.strerror) from exc

        protocol = protocol_factory()
        waiter = asyncio.Future(loop=self)
        transport = _ZmqTransportImpl(self, zmq_type,
                                      zmq_sock, protocol, waiter)
        yield from waiter

        try:
            if bind is not None:
                if isinstance(bind, str):
                    bind = [bind]
                else:
                    if not isinstance(bind, Iterable):
                        raise ValueError('bind should be str or iterable')
                for endpoint in bind:
                    yield from transport.bind(endpoint)
            if connect is not None:
                if isinstance(connect, str):
                    connect = [connect]
                else:
                    if not isinstance(connect, Iterable):
                        raise ValueError('connect should be '
                                         'str or iterable')
                for endpoint in connect:
                    yield from transport.connect(endpoint)
            self._zmq_sockets.add(zmq_sock)
            return transport, protocol
        except OSError:
            # don't care if zmq_sock.close can raise exception
            # that should never happen
            zmq_sock.close()
            raise


class _EndpointsSet(Set):

    __slots__ = ('_collection',)

    def __init__(self, collection):
        self._collection = collection

    def __len__(self):
        return len(self._collection)

    def __contains__(self, endpoint):
        return endpoint in self._collection

    def __iter__(self):
        return iter(self._collection)

    def __repr__(self):
        return '{' + ', '.join(sorted(self._collection)) + '}'

    __str__ = __repr__


class _ZmqTransportImpl(ZmqTransport, _FlowControlMixin):

    _TCP_RE = re.compile('^tcp://(.+):(\d+)|\*$')

    def __init__(self, loop, zmq_type, zmq_sock, protocol, waiter=None):
        super().__init__(None)
        self._extra['zmq_socket'] = zmq_sock
        self._loop = loop
        self._zmq_sock = zmq_sock
        self._zmq_type = zmq_type
        self._protocol = protocol
        self._closing = False
        self._buffer = deque()
        self._buffer_size = 0
        self._bindings = set()
        self._connections = set()
        self._subscriptions = set()
        self._paused = False

        self._loop.add_reader(self._zmq_sock, self._read_ready)
        self._loop.call_soon(self._protocol.connection_made, self)
        if waiter is not None:
            self._loop.call_soon(waiter.set_result, None)

    def _read_ready(self):
        try:
            try:
                data = self._zmq_sock.recv_multipart(zmq.NOBLOCK)
            except zmq.ZMQError as exc:
                if exc.errno in (errno.EAGAIN, errno.EINTR):
                    return
                else:
                    raise OSError(exc.errno, exc.strerror) from exc
        except Exception as exc:
            self._fatal_error(exc, 'Fatal read error on zmq socket transport')
        else:
            self._protocol.msg_received(data)

    def write(self, data):
        if not data:
            return
        for part in data:
            if not isinstance(part, (bytes, bytearray, memoryview)):
                raise TypeError('data argument must be iterable of '
                                'byte-ish (%r)' % data)
        data_len = sum(len(part) for part in data)

        if not self._buffer:
            try:
                try:
                    self._zmq_sock.send_multipart(data, zmq.DONTWAIT)
                    return
                except zmq.ZMQError as exc:
                    if exc.errno in (errno.EAGAIN, errno.EINTR):
                        self._loop.add_writer(self._zmq_sock,
                                              self._write_ready)
                    else:
                        raise OSError(exc.errno, exc.strerror) from exc
            except Exception as exc:
                self._fatal_error(exc,
                                  'Fatal write error on zmq socket transport')
                return

        self._buffer.append((data_len, data))
        self._buffer_size += data_len
        self._maybe_pause_protocol()

    def _write_ready(self):
        assert self._buffer, 'Data should not be empty'

        try:
            try:
                self._zmq_sock.send_multipart(self._buffer[0][1], zmq.DONTWAIT)
            except zmq.ZMQError as exc:
                if exc.errno in (errno.EAGAIN, errno.EINTR):
                    return
                else:
                    raise OSError(exc.errno, exc.strerror) from exc
        except Exception as exc:
            self._fatal_error(exc,
                              'Fatal write error on zmq socket transport')
        else:
            sent_len, sent_data = self._buffer.popleft()
            self._buffer_size -= sent_len

            self._maybe_resume_protocol()

            if not self._buffer:
                self._loop.remove_writer(self._zmq_sock)
                if self._closing:
                    self._call_connection_lost(None)

    def can_write_eof(self):
        return False

    def abort(self):
        self._force_close(None)

    def close(self):
        if self._closing:
            return
        self._closing = True
        self._loop.remove_reader(self._zmq_sock)
        if not self._buffer:
            self._loop.call_soon(self._call_connection_lost, None)

    def _fatal_error(self, exc, message='Fatal error on transport'):
        # Should be called from exception handler only.
        self._loop.call_exception_handler({
            'message': message,
            'exception': exc,
            'transport': self,
            'protocol': self._protocol,
            })
        self._force_close(exc)

    def _force_close(self, exc):
        if self._buffer:
            self._buffer.clear()
            self._buffer_size = 0
            self._loop.remove_writer(self._zmq_sock)
        if not self._closing:
            self._closing = True
            if not self._paused:
                self._loop.remove_reader(self._zmq_sock)
        self._loop.call_soon(self._call_connection_lost, exc)

    def _call_connection_lost(self, exc):
        try:
            self._protocol.connection_lost(exc)
        finally:
            if not self._zmq_sock.closed:
                self._zmq_sock.close()
            self._zmq_sock = None
            self._protocol = None
            self._loop = None

    def getsockopt(self, option):
        while True:
            try:
                ret = self._zmq_sock.getsockopt(option)
                if option == zmq.LAST_ENDPOINT:
                    ret = ret.decode('utf-8').rstrip('\x00')
                return ret
            except zmq.ZMQError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise OSError(exc.errno, exc.strerror) from exc

    def setsockopt(self, option, value):
        while True:
            try:
                self._zmq_sock.setsockopt(option, value)
                if option == zmq.SUBSCRIBE:
                    self._subscriptions.add(value)
                elif option == zmq.UNSUBSCRIBE:
                    self._subscriptions.discard(value)
                return
            except zmq.ZMQError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise OSError(exc.errno, exc.strerror) from exc

    def get_write_buffer_size(self):
        return self._buffer_size

    def pause_reading(self):
        if self._closing:
            raise RuntimeError('Cannot pause_reading() when closing')
        if self._paused:
            raise RuntimeError('Already paused')
        self._paused = True
        self._loop.remove_reader(self._zmq_sock)

    def resume_reading(self):
        if not self._paused:
            raise RuntimeError('Not paused')
        self._paused = False
        if self._closing:
            return
        self._loop.add_reader(self._zmq_sock, self._read_ready)

    def bind(self, endpoint):
        fut = asyncio.Future(loop=self._loop)
        try:
            if not isinstance(endpoint, str):
                raise TypeError('endpoint should be str, got {!r}'
                                .format(endpoint))
            try:
                self._zmq_sock.bind(endpoint)
                real_endpoint = self.getsockopt(zmq.LAST_ENDPOINT)
            except zmq.ZMQError as exc:
                raise OSError(exc.errno, exc.strerror) from exc
        except Exception as exc:
            fut.set_exception(exc)
        else:
            self._bindings.add(real_endpoint)
            fut.set_result(real_endpoint)
        return fut

    def unbind(self, endpoint):
        fut = asyncio.Future(loop=self._loop)
        try:
            if not isinstance(endpoint, str):
                raise TypeError('endpoint should be str, got {!r}'
                                .format(endpoint))
            try:
                self._zmq_sock.unbind(endpoint)
            except zmq.ZMQError as exc:
                raise OSError(exc.errno, exc.strerror) from exc
            else:
                self._bindings.discard(endpoint)
        except Exception as exc:
            fut.set_exception(exc)
        else:
            fut.set_result(None)
        return fut

    def bindings(self):
        return _EndpointsSet(self._bindings)

    def connect(self, endpoint):
        fut = asyncio.Future(loop=self._loop)
        try:
            if not isinstance(endpoint, str):
                raise TypeError('endpoint should be str, got {!r}'
                                .format(endpoint))
            match = self._TCP_RE.match(endpoint)
            if match:
                ip_address(match.group(1))  # check for correct IPv4 or IPv6
            try:
                self._zmq_sock.connect(endpoint)
            except zmq.ZMQError as exc:
                raise OSError(exc.errno, exc.strerror) from exc
        except Exception as exc:
            fut.set_exception(exc)
        else:
            self._connections.add(endpoint)
            fut.set_result(endpoint)
        return fut

    def disconnect(self, endpoint):
        fut = asyncio.Future(loop=self._loop)
        try:
            if not isinstance(endpoint, str):
                raise TypeError('endpoint should be str, got {!r}'
                                .format(endpoint))
            try:
                self._zmq_sock.disconnect(endpoint)
            except zmq.ZMQError as exc:
                raise OSError(exc.errno, exc.strerror) from exc
        except Exception as exc:
            fut.set_exception(exc)
        else:
            self._connections.discard(endpoint)
            fut.set_result(None)
        return fut

    def connections(self):
        return _EndpointsSet(self._connections)

    def subscribe(self, value):
        if self._zmq_type != zmq.SUB:
            raise NotImplementedError("Not supported ZMQ socket type")
        if not isinstance(value, bytes):
            raise TypeError("value argument should be bytes")
        if value in self._subscriptions:
            return
        self.setsockopt(zmq.SUBSCRIBE, value)

    def unsubscribe(self, value):
        if self._zmq_type != zmq.SUB:
            raise NotImplementedError("Not supported ZMQ socket type")
        if not isinstance(value, bytes):
            raise TypeError("value argument should be bytes")
        self.setsockopt(zmq.UNSUBSCRIBE, value)

    def subscriptions(self):
        if self._zmq_type != zmq.SUB:
            raise NotImplementedError("Not supported ZMQ socket type")
        return _EndpointsSet(self._subscriptions)


class ZmqEventLoopPolicy(asyncio.AbstractEventLoopPolicy):
    """ZeroMQ policy implementation for accessing the event loop.

    In this policy, each thread has its own event loop.  However, we
    only automatically create an event loop by default for the main
    thread; other threads by default have no event loop.
    """

    class _Local(threading.local):
        _loop = None
        _set_called = False

    def __init__(self):
        self._local = self._Local()
        self._watcher = None

    def get_event_loop(self):
        """Get the event loop.

        If current thread is the main thread and there are no
        registered event loop for current thread then the call creates
        new event loop and registers it.

        Return an instance of ZmqEventLoop.
        Raise RuntimeError if there is no registered event loop
        for current thread.
        """
        if (self._local._loop is None and
                not self._local._set_called and
                isinstance(threading.current_thread(), threading._MainThread)):
            self.set_event_loop(self.new_event_loop())
        assert self._local._loop is not None, \
            ('There is no current event loop in thread %r.' %
             threading.current_thread().name)
        return self._local._loop

    def new_event_loop(self):
        """Create a new event loop.

        You must call set_event_loop() to make this the current event
        loop.
        """
        return ZmqEventLoop()

    def set_event_loop(self, loop):
        """Set the event loop.

        As a side effect, if a child watcher was set before, then calling
        .set_event_loop() from the main thread will call .attach_loop(loop) on
        the child watcher.
        """

        self._local._set_called = True
        assert loop is None or isinstance(loop, asyncio.AbstractEventLoop), \
            "loop should be None or AbstractEventLoop instance"
        self._local._loop = loop

        if (self._watcher is not None and
                isinstance(threading.current_thread(), threading._MainThread)):
            self._watcher.attach_loop(loop)

    if sys.platform != 'win32':
        def _init_watcher(self):
            with asyncio.events._lock:
                if self._watcher is None:  # pragma: no branch
                    self._watcher = SafeChildWatcher()
                    if isinstance(threading.current_thread(),
                                  threading._MainThread):
                        self._watcher.attach_loop(self._local._loop)

        def get_child_watcher(self):
            """Get the child watcher.

            If not yet set, a SafeChildWatcher object is automatically created.
            """
            if self._watcher is None:
                self._init_watcher()

            return self._watcher

        def set_child_watcher(self, watcher):
            """Set the child watcher."""

            assert watcher is None or \
                isinstance(watcher, asyncio.AbstractChildWatcher), \
                "watcher should be None or AbstractChildWatcher instance"

            if self._watcher is not None:
                self._watcher.close()

            self._watcher = watcher

########NEW FILE########
__FILENAME__ = interface
from asyncio import BaseProtocol, BaseTransport

__all__ = ['ZmqTransport', 'ZmqProtocol']


class ZmqTransport(BaseTransport):
    """Interface for ZeroMQ transport."""

    def write(self, data):
        """Write message to the transport.

        data is iterable to send as multipart message.

        This does not block; it buffers the data and arranges for it
        to be sent out asynchronously.
        """
        raise NotImplementedError

    def abort(self):
        """Close the transport immediately.

        Buffered data will be lost.  No more data will be received.
        The protocol's connection_lost() method will (eventually) be
        called with None as its argument.
        """
        raise NotImplementedError

    def getsockopt(self, option):
        """Get ZeroMQ socket option.

        option is a constant like zmq.SUBSCRIBE, zmq.UNSUBSCRIBE, zmq.TYPE etc.

        For list of available options please see:
        http://api.zeromq.org/master:zmq-getsockopt
        """
        raise NotImplementedError

    def setsockopt(self, option, value):
        """Set ZeroMQ socket option.

        option is a constant like zmq.SUBSCRIBE, zmq.UNSUBSCRIBE, zmq.TYPE etc.
        value is a new option value, it's type depend of option name.

        For list of available options please see:
        http://api.zeromq.org/master:zmq-setsockopt
        """
        raise NotImplementedError

    def set_write_buffer_limits(self, high=None, low=None):
        """Set the high- and low-water limits for write flow control.

        These two values control when to call the protocol's
        pause_writing() and resume_writing() methods.  If specified,
        the low-water limit must be less than or equal to the
        high-water limit.  Neither value can be negative.

        The defaults are implementation-specific.  If only the
        high-water limit is given, the low-water limit defaults to a
        implementation-specific value less than or equal to the
        high-water limit.  Setting high to zero forces low to zero as
        well, and causes pause_writing() to be called whenever the
        buffer becomes non-empty.  Setting low to zero causes
        resume_writing() to be called only once the buffer is empty.
        Use of zero for either limit is generally sub-optimal as it
        reduces opportunities for doing I/O and computation
        concurrently.
        """
        raise NotImplementedError

    def get_write_buffer_size(self):
        """Return the current size of the write buffer."""
        raise NotImplementedError

    def pause_reading(self):
        """Pause the receiving end.

        No data will be passed to the protocol's msg_received()
        method until resume_reading() is called.
        """
        raise NotImplementedError

    def resume_reading(self):
        """Resume the receiving end.

        Data received will once again be passed to the protocol's
        msg_received() method.
        """
        raise NotImplementedError

    def bind(self, endpoint):
        """Bind transpot to endpoint.

        endpoint is a string in format transport://address as ZeroMQ requires.

        Return bound endpoint, unwinding wildcards if needed.
        """
        raise NotImplementedError

    def unbind(self, endpoint):
        """Unbind transpot from endpoint.
        """
        raise NotImplementedError

    def bindings(self):
        """Return immutable set of endpoints bound to transport.

        N.B. returned endpoints includes only ones that has been bound
        via transport.bind or event_loop.create_zmq_connection calls
        and does not includes bindings that has been done to zmq_sock
        before create_zmq_connection has been called.
        """
        raise NotImplementedError

    def connect(self, endpoint):
        """Connect transpot to endpoint.

        endpoint is a string in format transport://address as ZeroMQ requires.

        For TCP connections endpoint should specify IPv4 or IPv6 address,
        not DNS name.
        Use yield from get_event_loop().getaddrinfo(host, port)
        for translating DNS into address.

        Raise ValueError if endpoint is tcp DNS address.
        Return bound connection, unwinding wildcards if needed.
        """
        raise NotImplementedError

    def disconnect(self, endpoint):
        """Disconnect transpot from endpoint.
        """
        raise NotImplementedError

    def connections(self):
        """Return immutable set of endpoints connected to transport.

        N.B. returned endpoints includes only ones that has been connected
        via transport.connect or event_loop.create_zmq_connection calls
        and does not includes connections that has been done to zmq_sock
        before create_zmq_connection has been called.
        """
        raise NotImplementedError

    def subscribe(self, value):
        """Establish a new message filter on SUB transport.

        Newly created SUB transports filters out all incoming
        messages, therefore you should to call this method to
        establish an initial message filter.

        Value should be bytes.

        An empty (b'') value subscribes to all incoming messages. A
        non-empty value subscribes to all messages beginning with the
        specified prefix. Multiple filters may be attached to a single
        SUB transport, in which case a message shall be accepted if it
        matches at least one filter.
        """
        raise NotImplementedError

    def unsubscribe(self, value):
        """Remove an existing message filter on a SUB transport.

        Value should be bytes.

        The filter specified must match an existing filter previously
        established with the .subscribe(). If the transport has
        several instances of the same filter attached the
        .unsubscribe() removes only one instance, leaving
        the rest in place and functional.
        """
        raise NotImplementedError

    def subscriptions(self):
        """Return immutable set of subscriptions (bytes) subscribed on
        transport.

        N.B. returned subscriptions includes only ones that has been
        subscribed via transport.subscribe call and does not includes
        subscribtions that has been done to zmq_sock before
        create_zmq_connection has been called.
        """
        raise NotImplementedError


class ZmqProtocol(BaseProtocol):
    """Interface for ZeroMQ protocol."""

    def msg_received(self, data):
        """Called when some ZeroMQ message is received.

        data is the multipart tuple of bytes with at least one item.
        """

########NEW FILE########
__FILENAME__ = base
import abc
import asyncio
import inspect
import pprint
import textwrap

from aiozmq import interface
from types import MethodType

from .packer import _Packer
from .log import logger


class Error(Exception):
    """Base RPC exception"""


class GenericError(Error):
    """Error for all untranslated exceptions from rpc method calls."""

    def __init__(self, exc_type, args, exc_repr):
        super().__init__(exc_type, args, exc_repr)
        self.exc_type = exc_type
        self.arguments = args
        self.exc_repr = exc_repr

    def __repr__(self):
        return '<Generic RPC Error {}{}: {}>'.format(self.exc_type,
                                                     self.arguments,
                                                     self.exc_repr)


class NotFoundError(Error, LookupError):
    """Error raised by server if RPC namespace/method lookup failed."""


class ParametersError(Error, ValueError):
    """Error raised by server when RPC method's parameters could not
    be validated against their annotations."""


class ServiceClosedError(Error):
    """RPC Service is closed."""


class AbstractHandler(metaclass=abc.ABCMeta):
    """Abstract class for server-side RPC handlers."""

    __slots__ = ()

    @abc.abstractmethod
    def __getitem__(self, key):
        raise KeyError

    @classmethod
    def __subclasshook__(cls, C):
        if issubclass(C, (str, bytes)):
            return False
        if cls is AbstractHandler:
            if any("__getitem__" in B.__dict__ for B in C.__mro__):
                return True
        return NotImplemented


class AttrHandler(AbstractHandler):
    """Base class for RPC handlers via attribute lookup."""

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError


def method(func):
    """Marks a decorated function as RPC endpoint handler.

    The func object may provide arguments and/or return annotations.
    If so annotations should be callable objects and
    they will be used to validate received arguments and/or return value.
    """
    func.__rpc__ = {}
    func.__signature__ = sig = inspect.signature(func)
    for name, param in sig.parameters.items():
        ann = param.annotation
        if ann is not param.empty and not callable(ann):
            raise ValueError("Expected {!r} annotation to be callable"
                             .format(name))
    ann = sig.return_annotation
    if ann is not sig.empty and not callable(ann):
        raise ValueError("Expected return annotation to be callable")
    return func


class Service(asyncio.AbstractServer):
    """RPC service.

    Instances of Service (or
    descendants) are returned by coroutines that creates clients or
    servers.

    Implementation of AbstractServer.
    """

    def __init__(self, loop, proto):
        self._loop = loop
        self._proto = proto
        self._closing = False

    @property
    def transport(self):
        """Return the transport.

        You can use the transport to dynamically bind/unbind,
        connect/disconnect etc.
        """
        transport = self._proto.transport
        if transport is None:
            raise ServiceClosedError()
        return transport

    def close(self):
        if self._closing:
            return
        self._closing = True
        if self._proto.transport is None:
            return
        self._proto.transport.close()

    @asyncio.coroutine
    def wait_closed(self):
        if self._proto.transport is None:
            return
        waiter = asyncio.Future(loop=self._loop)
        self._proto.done_waiters.append(waiter)
        yield from waiter


class _BaseProtocol(interface.ZmqProtocol):

    def __init__(self, loop, *, translation_table=None):
        self.loop = loop
        self.transport = None
        self.done_waiters = []
        self.packer = _Packer(translation_table=translation_table)

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        self.transport = None
        for waiter in self.done_waiters:
            waiter.set_result(None)


class _BaseServerProtocol(_BaseProtocol):

    def __init__(self, loop, handler, *,
                 translation_table=None, log_exceptions=False):
        super().__init__(loop, translation_table=translation_table)
        if not isinstance(handler, AbstractHandler):
            raise TypeError('handler must implement AbstractHandler ABC')
        self.handler = handler
        self.log_exceptions = log_exceptions
        self.pending_waiters = set()

    def connection_lost(self, exc):
        super().connection_lost(exc)
        for waiter in list(self.pending_waiters):
            if not waiter.cancelled():
                waiter.cancel()

    def dispatch(self, name):
        if not name:
            raise NotFoundError(name)
        namespaces, sep, method = name.rpartition('.')
        handler = self.handler
        if namespaces:
            for part in namespaces.split('.'):
                try:
                    handler = handler[part]
                except KeyError:
                    raise NotFoundError(name)
                else:
                    if not isinstance(handler, AbstractHandler):
                        raise NotFoundError(name)

        try:
            func = handler[method]
        except KeyError:
            raise NotFoundError(name)
        else:
            if isinstance(func, MethodType):
                holder = func.__func__
            else:
                holder = func
            if not hasattr(holder, '__rpc__'):
                raise NotFoundError(name)
            return func

    def check_args(self, func, args, kwargs):
        """Utility function for validating function arguments

        Returns validated (args, kwargs, return annotation) tuple
        """
        try:
            sig = inspect.signature(func)
            bargs = sig.bind(*args, **kwargs)
        except TypeError as exc:
            raise ParametersError(repr(exc)) from exc
        else:
            arguments = bargs.arguments
            marker = object()
            for name, param in sig.parameters.items():
                if param.annotation is param.empty:
                    continue
                val = arguments.get(name, marker)
                if val is marker:
                    continue  # Skip default value
                try:
                    arguments[name] = param.annotation(val)
                except (TypeError, ValueError) as exc:
                    raise ParametersError(
                        'Invalid value for argument {!r}: {!r}'
                        .format(name, exc)) from exc
            if sig.return_annotation is not sig.empty:
                return bargs.args, bargs.kwargs, sig.return_annotation
            return bargs.args, bargs.kwargs, None

    def try_log(self, fut, name, args, kwargs):
        try:
            fut.result()
        except Exception:
            if self.log_exceptions:
                logger.exception(textwrap.dedent("""\
                    An exception from method %r call occurred.
                    args = %s
                    kwargs = %s
                    """),
                    name, pprint.pformat(args), pprint.pformat(kwargs))  # noqa

########NEW FILE########
__FILENAME__ = log
"""Logging configuration."""

import logging

logger = logging.getLogger(__package__)

########NEW FILE########
__FILENAME__ = packer
"""Private utility functions."""

from collections import ChainMap
from datetime import datetime, date, time, timedelta, tzinfo
from functools import partial
from pickle import dumps, loads, HIGHEST_PROTOCOL

from msgpack import ExtType, packb, unpackb


_default = {
    127: (date, partial(dumps, protocol=HIGHEST_PROTOCOL), loads),
    126: (datetime, partial(dumps, protocol=HIGHEST_PROTOCOL), loads),
    125: (time, partial(dumps, protocol=HIGHEST_PROTOCOL), loads),
    124: (timedelta, partial(dumps, protocol=HIGHEST_PROTOCOL), loads),
    123: (tzinfo, partial(dumps, protocol=HIGHEST_PROTOCOL), loads),
}


class _Packer:

    def __init__(self, *, translation_table=None):
        if translation_table is None:
            translation_table = _default
        else:
            translation_table = ChainMap(translation_table, _default)
        self.translation_table = translation_table
        self._pack_cache = {}

    def packb(self, data):
        return packb(data, encoding='utf-8', use_bin_type=True,
                     default=self.ext_type_pack_hook)

    def unpackb(self, packed):
        return unpackb(packed, use_list=False, encoding='utf-8',
                       ext_hook=self.ext_type_unpack_hook)

    def ext_type_pack_hook(self, obj, _sentinel=object()):
        obj_class = obj.__class__
        hit = self._pack_cache.get(obj_class, _sentinel)
        if hit is None:
            # packer has been not found by previous long-lookup
            raise TypeError("Unknown type: {!r}".format(obj))
        elif hit is _sentinel:
            # do long-lookup
            for code in sorted(self.translation_table):
                cls, packer, unpacker = self.translation_table[code]
                if isinstance(obj, cls):
                    self._pack_cache[obj_class] = (code, packer)
                    return ExtType(code, packer(obj))
            else:
                self._pack_cache[obj_class] = None
                raise TypeError("Unknown type: {!r}".format(obj))
        else:
            # do shortcut
            code, packer = hit
            return ExtType(code, packer(obj))

    def ext_type_unpack_hook(self, code, data):
        try:
            cls, packer, unpacker = self.translation_table[code]
            return unpacker(data)
        except KeyError:
            return ExtType(code, data)

########NEW FILE########
__FILENAME__ = pipeline
import asyncio
import zmq

from functools import partial

from .log import logger

from .base import (
    NotFoundError,
    ParametersError,
    Service,
    ServiceClosedError,
    _BaseProtocol,
    _BaseServerProtocol,
    )
from .util import (
    _MethodCall,
    )


@asyncio.coroutine
def connect_pipeline(*, connect=None, bind=None, loop=None,
                     translation_table=None):
    """A coroutine that creates and connects/binds Pipeline client instance.

    Usually for this function you need to use *connect* parameter, but
    ZeroMQ does not forbid to use *bind*.

    translation_table -- an optional table for custom value translators.

    loop --  an optional parameter to point
    ZmqEventLoop instance.  If loop is None then default
    event loop will be given by asyncio.get_event_loop() call.

    Returns PipelineClient instance.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    transp, proto = yield from loop.create_zmq_connection(
        lambda: _ClientProtocol(loop, translation_table=translation_table),
        zmq.PUSH, connect=connect, bind=bind)
    return PipelineClient(loop, proto)


@asyncio.coroutine
def serve_pipeline(handler, *, connect=None, bind=None, loop=None,
                   translation_table=None, log_exceptions=False):
    """A coroutine that creates and connects/binds Pipeline server instance.

    Usually for this function you need to use *bind* parameter, but
    ZeroMQ does not forbid to use *connect*.

    handler -- an object which processes incoming pipeline calls.
    Usually you like to pass AttrHandler instance.

    log_exceptions -- log exceptions from remote calls if True.

    translation_table -- an optional table for custom value translators.

    loop -- an optional parameter to point
       ZmqEventLoop instance.  If loop is None then default
       event loop will be given by asyncio.get_event_loop() call.

    Returns Service instance.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    trans, proto = yield from loop.create_zmq_connection(
        lambda: _ServerProtocol(loop, handler,
                                translation_table=translation_table,
                                log_exceptions=log_exceptions),
        zmq.PULL, connect=connect, bind=bind)
    return Service(loop, proto)


class _ClientProtocol(_BaseProtocol):

    def call(self, name, args, kwargs):
        if self.transport is None:
            raise ServiceClosedError()
        bname = name.encode('utf-8')
        bargs = self.packer.packb(args)
        bkwargs = self.packer.packb(kwargs)
        self.transport.write([bname, bargs, bkwargs])
        fut = asyncio.Future(loop=self.loop)
        fut.set_result(None)
        return fut


class PipelineClient(Service):

    def __init__(self, loop, proto):
        super().__init__(loop, proto)

    @property
    def notify(self):
        """Return object for dynamic Pipeline calls.

        The usage is:
        yield from client.pipeline.ns.func(1, 2)
        """
        return _MethodCall(self._proto)


class _ServerProtocol(_BaseServerProtocol):

    def msg_received(self, data):
        bname, bargs, bkwargs = data

        args = self.packer.unpackb(bargs)
        kwargs = self.packer.unpackb(bkwargs)
        try:
            name = bname.decode('utf-8')
            func = self.dispatch(name)
            args, kwargs, ret_ann = self.check_args(func, args, kwargs)
        except (NotFoundError, ParametersError) as exc:
            fut = asyncio.Future(loop=self.loop)
            fut.set_exception(exc)
        else:
            if asyncio.iscoroutinefunction(func):
                fut = asyncio.async(func(*args, **kwargs), loop=self.loop)
                self.pending_waiters.add(fut)
            else:
                fut = asyncio.Future(loop=self.loop)
                try:
                    fut.set_result(func(*args, **kwargs))
                except Exception as exc:
                    fut.set_exception(exc)
        fut.add_done_callback(partial(self.process_call_result,
                                      name=name, args=args, kwargs=kwargs))

    def process_call_result(self, fut, *, name, args, kwargs):
        self.pending_waiters.discard(fut)
        try:
            if fut.result() is not None:
                logger.warning("Pipeline handler %r returned not None", name)
        except (NotFoundError, ParametersError) as exc:
            logger.exception("Call to %r caused error: %r", name, exc)
        except asyncio.CancelledError:
            return
        except Exception:
            self.try_log(fut, name, args, kwargs)

########NEW FILE########
__FILENAME__ = pubsub
import asyncio
import zmq
from functools import partial
from collections import Iterable

from .log import logger
from .base import (
    NotFoundError,
    ParametersError,
    Service,
    ServiceClosedError,
    _BaseProtocol,
    _BaseServerProtocol,
    )


@asyncio.coroutine
def connect_pubsub(*, connect=None, bind=None, loop=None,
                   translation_table=None):
    """A coroutine that creates and connects/binds pubsub client.

    Usually for this function you need to use connect parameter, but
    ZeroMQ does not forbid to use bind.

    translation_table -- an optional table for custom value translators.

    loop -- an optional parameter to point
       ZmqEventLoop.  If loop is None then default
       event loop will be given by asyncio.get_event_loop() call.

    Returns PubSubClient instance.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    transp, proto = yield from loop.create_zmq_connection(
        lambda: _ClientProtocol(loop, translation_table=translation_table),
        zmq.PUB, connect=connect, bind=bind)
    return PubSubClient(loop, proto)


@asyncio.coroutine
def serve_pubsub(handler, *, subscribe=None, connect=None, bind=None,
                 loop=None, translation_table=None, log_exceptions=False):
    """A coroutine that creates and connects/binds pubsub server instance.

    Usually for this function you need to use *bind* parameter, but
    ZeroMQ does not forbid to use *connect*.

    handler -- an object which processes incoming pipeline calls.
    Usually you like to pass AttrHandler instance.

    log_exceptions -- log exceptions from remote calls if True.

    subscribe -- subscription specification.
    Subscribe server to topics.
    Allowed parameters are str, bytes, iterable of str or bytes.

    translation_table -- an optional table for custom value translators.

    loop -- an optional parameter to point
       ZmqEventLoop.  If loop is None then default
       event loop will be given by asyncio.get_event_loop() call.

    Returns PubSubService instance.
    Raises OSError on system error.
    Raises TypeError if arguments have inappropriate type.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    transp, proto = yield from loop.create_zmq_connection(
        lambda: _ServerProtocol(loop, handler,
                                translation_table=translation_table,
                                log_exceptions=log_exceptions),
        zmq.SUB, connect=connect, bind=bind)
    serv = PubSubService(loop, proto)
    if subscribe is not None:
        if isinstance(subscribe, (str, bytes)):
            subscribe = [subscribe]
        else:
            if not isinstance(subscribe, Iterable):
                raise TypeError('bind should be str, bytes or iterable')
        for topic in subscribe:
            serv.subscribe(topic)
    return serv


class _ClientProtocol(_BaseProtocol):

    def call(self, topic, name, args, kwargs):
        if self.transport is None:
            raise ServiceClosedError()
        if topic is None:
            btopic = b''
        elif isinstance(topic, str):
            btopic = topic.encode('utf-8')
        elif isinstance(topic, bytes):
            btopic = topic
        else:
            raise TypeError('topic argument should be None, str or bytes '
                            '({!r})'.format(topic))
        bname = name.encode('utf-8')
        bargs = self.packer.packb(args)
        bkwargs = self.packer.packb(kwargs)
        self.transport.write([btopic, bname, bargs, bkwargs])
        fut = asyncio.Future(loop=self.loop)
        fut.set_result(None)
        return fut


class PubSubClient(Service):

    def __init__(self, loop, proto):
        super().__init__(loop, proto)

    def publish(self, topic):
        """Return object for dynamic PubSub calls.

        The usage is:
        yield from client.publish('my_topic').ns.func(1, 2)

        topic argument may be None otherwise must be isntance of str or bytes
        """
        return _MethodCall(self._proto, topic)


class PubSubService(Service):

    def subscribe(self, topic):
        """Subscribe to the topic.

        topic argument must be str or bytes.
        Raises TypeError in other cases
        """
        if isinstance(topic, bytes):
            btopic = topic
        elif isinstance(topic, str):
            btopic = topic.encode('utf-8')
        else:
            raise TypeError('topic should be str or bytes, got {!r}'
                            .format(topic))
        self.transport.subscribe(btopic)

    def unsubscribe(self, topic):
        """Unsubscribe from the topic.

        topic argument must be str or bytes.
        Raises TypeError in other cases
        """
        if isinstance(topic, bytes):
            btopic = topic
        elif isinstance(topic, str):
            btopic = topic.encode('utf-8')
        else:
            raise TypeError('topic should be str or bytes, got {!r}'
                            .format(topic))
        self.transport.unsubscribe(btopic)


class _MethodCall:

    __slots__ = ('_proto', '_topic', '_names')

    def __init__(self, proto, topic, names=()):
        self._proto = proto
        self._topic = topic
        self._names = names

    def __getattr__(self, name):
        return self.__class__(self._proto, self._topic,
                              self._names + (name,))

    def __call__(self, *args, **kwargs):
        if not self._names:
            raise ValueError("PubSub method name is empty")
        return self._proto.call(self._topic, '.'.join(self._names),
                                args, kwargs)


class _ServerProtocol(_BaseServerProtocol):

    def msg_received(self, data):
        btopic, bname, bargs, bkwargs = data

        args = self.packer.unpackb(bargs)
        kwargs = self.packer.unpackb(bkwargs)
        try:
            name = bname.decode('utf-8')
            func = self.dispatch(name)
            args, kwargs, ret_ann = self.check_args(func, args, kwargs)
        except (NotFoundError, ParametersError) as exc:
            fut = asyncio.Future(loop=self.loop)
            fut.set_exception(exc)
        else:
            if asyncio.iscoroutinefunction(func):
                fut = asyncio.async(func(*args, **kwargs), loop=self.loop)
                self.pending_waiters.add(fut)
            else:
                fut = asyncio.Future(loop=self.loop)
                try:
                    fut.set_result(func(*args, **kwargs))
                except Exception as exc:
                    fut.set_exception(exc)
        fut.add_done_callback(partial(self.process_call_result,
                                      name=name, args=args, kwargs=kwargs))

    def process_call_result(self, fut, *, name, args, kwargs):
        self.pending_waiters.discard(fut)
        try:
            if fut.result() is not None:
                logger.warning("PubSub handler %r returned not None", name)
        except asyncio.CancelledError:
            return
        except (NotFoundError, ParametersError) as exc:
            logger.exception("Call to %r caused error: %r", name, exc)
        except Exception:
            self.try_log(fut, name, args, kwargs)

########NEW FILE########
__FILENAME__ = rpc
"""ZeroMQ RPC"""

import asyncio
import os
import random
import struct
import time
import sys

import zmq


from collections import ChainMap
from functools import partial

from .log import logger

from .base import (
    GenericError,
    NotFoundError,
    ParametersError,
    Service,
    ServiceClosedError,
    _BaseProtocol,
    _BaseServerProtocol,
    )
from .util import (
    _MethodCall,
    _fill_error_table,
    )


__all__ = [
    'connect_rpc',
    'serve_rpc',
    ]


@asyncio.coroutine
def connect_rpc(*, connect=None, bind=None, loop=None,
                error_table=None, translation_table=None, timeout=None):
    """A coroutine that creates and connects/binds RPC client.

    Usually for this function you need to use *connect* parameter, but
    ZeroMQ does not forbid to use *bind*.

    error_table -- an optional table for custom exception translators.

    timeout -- an optional timeout for RPC calls. If timeout is not
    None and remote call takes longer than timeout seconds then
    asyncio.TimeoutError will be raised at client side. If the server
    will return an answer after timeout has been raised that answer
    **is ignored**.

    translation_table -- an optional table for custom value translators.

    loop -- an optional parameter to point ZmqEventLoop instance.  If
    loop is None then default event loop will be given by
    asyncio.get_event_loop call.

    Returns a RPCClient instance.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    transp, proto = yield from loop.create_zmq_connection(
        lambda: _ClientProtocol(loop, error_table=error_table,
                                translation_table=translation_table),
        zmq.DEALER, connect=connect, bind=bind)
    return RPCClient(loop, proto, timeout=timeout)


@asyncio.coroutine
def serve_rpc(handler, *, connect=None, bind=None, loop=None,
              translation_table=None, log_exceptions=False):
    """A coroutine that creates and connects/binds RPC server instance.

    Usually for this function you need to use *bind* parameter, but
    ZeroMQ does not forbid to use *connect*.

    handler -- an object which processes incoming RPC calls.
    Usually you like to pass AttrHandler instance.

    log_exceptions -- log exceptions from remote calls if True.

    translation_table -- an optional table for custom value translators.

    loop -- an optional parameter to point ZmqEventLoop instance.  If
    loop is None then default event loop will be given by
    asyncio.get_event_loop call.

    Returns Service instance.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    transp, proto = yield from loop.create_zmq_connection(
        lambda: _ServerProtocol(loop, handler,
                                translation_table=translation_table,
                                log_exceptions=log_exceptions),
        zmq.ROUTER, connect=connect, bind=bind)
    return Service(loop, proto)


_default_error_table = _fill_error_table()


class _ClientProtocol(_BaseProtocol):
    """Client protocol implementation."""

    REQ_PREFIX = struct.Struct('=HH')
    REQ_SUFFIX = struct.Struct('=Ld')
    RESP = struct.Struct('=HHLd?')

    def __init__(self, loop, *, error_table=None, translation_table=None):
        super().__init__(loop, translation_table=translation_table)
        self.calls = {}
        self.prefix = self.REQ_PREFIX.pack(os.getpid() % 0x10000,
                                           random.randrange(0x10000))
        self.counter = 0
        if error_table is None:
            self.error_table = _default_error_table
        else:
            self.error_table = ChainMap(error_table, _default_error_table)

    def msg_received(self, data):
        try:
            header, banswer = data
            pid, rnd, req_id, timestamp, is_error = self.RESP.unpack(header)
            answer = self.packer.unpackb(banswer)
        except Exception:
            logger.critical("Cannot unpack %r", data, exc_info=sys.exc_info())
            return
        call = self.calls.pop(req_id, None)
        if call is None:
            logger.critical("Unknown answer id: %d (%d %d %f %d) -> %s",
                            req_id, pid, rnd, timestamp, is_error, answer)
        elif call.cancelled():
            logger.debug("The future for request #%08x has been cancelled, "
                         "skip the received result.", req_id)
        else:
            if is_error:
                call.set_exception(self._translate_error(*answer))
            else:
                call.set_result(answer)

    def connection_lost(self, exc):
        super().connection_lost(exc)
        for call in self.calls.values():
            if not call.cancelled():
                call.cancel()

    def _translate_error(self, exc_type, exc_args, exc_repr):
        found = self.error_table.get(exc_type)
        if found is None:
            return GenericError(exc_type, exc_args, exc_repr)
        else:
            return found(*exc_args)

    def _new_id(self):
        self.counter += 1
        if self.counter > 0xffffffff:
            self.counter = 0
        return (self.prefix + self.REQ_SUFFIX.pack(self.counter, time.time()),
                self.counter)

    def call(self, name, args, kwargs):
        if self.transport is None:
            raise ServiceClosedError()
        bname = name.encode('utf-8')
        bargs = self.packer.packb(args)
        bkwargs = self.packer.packb(kwargs)
        header, req_id = self._new_id()
        assert req_id not in self.calls, (req_id, self.calls)
        fut = asyncio.Future(loop=self.loop)
        self.calls[req_id] = fut
        self.transport.write([header, bname, bargs, bkwargs])
        return fut


class RPCClient(Service):

    def __init__(self, loop, proto, *, timeout):
        super().__init__(loop, proto)
        self._timeout = timeout

    @property
    def call(self):
        """Return object for dynamic RPC calls.

        The usage is:
        ret = yield from client.call.ns.func(1, 2)
        """
        return _MethodCall(self._proto, timeout=self._timeout)

    def with_timeout(self, timeout):
        """Return a new RPCClient instance with overriden timeout"""
        return self.__class__(self._loop, self._proto, timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        return


class _ServerProtocol(_BaseServerProtocol):

    REQ = struct.Struct('=HHLd')
    RESP_PREFIX = struct.Struct('=HH')
    RESP_SUFFIX = struct.Struct('=Ld?')

    def __init__(self, loop, handler, *,
                 translation_table=None, log_exceptions=False):
        super().__init__(loop, handler,
                         translation_table=translation_table,
                         log_exceptions=log_exceptions)
        self.prefix = self.RESP_PREFIX.pack(os.getpid() % 0x10000,
                                            random.randrange(0x10000))

    def msg_received(self, data):
        try:
            peer, header, bname, bargs, bkwargs = data
            pid, rnd, req_id, timestamp = self.REQ.unpack(header)

            name = bname.decode('utf-8')
            args = self.packer.unpackb(bargs)
            kwargs = self.packer.unpackb(bkwargs)
        except Exception as exc:
            logger.critical("Cannot unpack %r", data, exc_info=sys.exc_info())
            return
        try:
            func = self.dispatch(name)
            args, kwargs, ret_ann = self.check_args(func, args, kwargs)
        except (NotFoundError, ParametersError) as exc:
            fut = asyncio.Future(loop=self.loop)
            fut.add_done_callback(partial(self.process_call_result,
                                          req_id=req_id, peer=peer,
                                          name=name, args=args, kwargs=kwargs))
            fut.set_exception(exc)
        else:
            if asyncio.iscoroutinefunction(func):
                fut = asyncio.async(func(*args, **kwargs), loop=self.loop)
                self.pending_waiters.add(fut)
            else:
                fut = asyncio.Future(loop=self.loop)
                try:
                    fut.set_result(func(*args, **kwargs))
                except Exception as exc:
                    fut.set_exception(exc)
            fut.add_done_callback(partial(self.process_call_result,
                                          req_id=req_id, peer=peer,
                                          return_annotation=ret_ann,
                                          name=name,
                                          args=args,
                                          kwargs=kwargs))

    def process_call_result(self, fut, *, req_id, peer, name,
                            args, kwargs,
                            return_annotation=None):
        self.pending_waiters.discard(fut)
        self.try_log(fut, name, args, kwargs)
        if self.transport is None:
            return
        try:
            ret = fut.result()
            if return_annotation is not None:
                ret = return_annotation(ret)
            prefix = self.prefix + self.RESP_SUFFIX.pack(req_id,
                                                         time.time(), False)
            self.transport.write([peer, prefix, self.packer.packb(ret)])
        except asyncio.CancelledError:
            return
        except Exception as exc:
            prefix = self.prefix + self.RESP_SUFFIX.pack(req_id,
                                                         time.time(), True)
            exc_type = exc.__class__
            exc_info = (exc_type.__module__ + '.' + exc_type.__name__,
                        exc.args, repr(exc))
            self.transport.write([peer, prefix, self.packer.packb(exc_info)])

########NEW FILE########
__FILENAME__ = util
import asyncio
import builtins

from .base import NotFoundError, ParametersError


class _MethodCall:

    __slots__ = ('_proto', '_timeout', '_names')

    def __init__(self, proto, timeout=None, names=()):
        self._proto = proto
        self._timeout = timeout
        self._names = names

    def __getattr__(self, name):
        return self.__class__(self._proto, self._timeout,
                              self._names + (name,))

    def __call__(self, *args, **kwargs):
        if not self._names:
            raise ValueError('RPC method name is empty')
        fut = self._proto.call('.'.join(self._names), args, kwargs)
        return _Waiter(fut, timeout=self._timeout, loop=self._proto.loop)


class _Waiter:

    __slots__ = ('_fut', '_timeout', '_loop')

    def __init__(self, fut, *, timeout=None, loop=None):
        self._fut = fut
        self._timeout = timeout
        self._loop = loop

    def __iter__(self):
        return (yield from asyncio.wait_for(self._fut, self._timeout,
                                            loop=self._loop))


def _fill_error_table():
    # Fill error table with standard exceptions
    error_table = {}
    for name in dir(builtins):
        val = getattr(builtins, name)
        if isinstance(val, type) and issubclass(val, Exception):
            error_table['builtins.'+name] = val
    error_table['aiozmq.rpc.base.NotFoundError'] = NotFoundError
    error_table['aiozmq.rpc.base.ParametersError'] = ParametersError
    return error_table

########NEW FILE########
__FILENAME__ = selector
"""ZMQ pooler for asyncio."""


__all__ = ['ZmqSelector']

import math

try:
    from asyncio.selectors import (BaseSelector, SelectorKey,
                                   EVENT_READ, EVENT_WRITE)
except ImportError:  # pragma: no cover
    from selectors import BaseSelector, SelectorKey, EVENT_READ, EVENT_WRITE
from collections import Mapping
from errno import EINTR
from zmq import (ZMQError, POLLIN, POLLOUT, POLLERR,
                 Socket as ZMQSocket, Poller as ZMQPoller)


def _fileobj_to_fd(fileobj):
    """Return a file descriptor from a file object.

    Parameters:
    fileobj -- file object or file descriptor

    Returns:
    corresponding file descriptor or zmq.Socket instance

    Raises:
    ValueError if the object is invalid
    """
    if isinstance(fileobj, int):
        fd = fileobj
    elif isinstance(fileobj, ZMQSocket):
        return fileobj
    else:
        try:
            fd = int(fileobj.fileno())
        except (AttributeError, TypeError, ValueError):
            raise ValueError("Invalid file object: "
                             "{!r}".format(fileobj)) from None
    if fd < 0:
        raise ValueError("Invalid file descriptor: {}".format(fd))
    return fd


class _SelectorMapping(Mapping):
    """Mapping of file objects to selector keys."""

    def __init__(self, selector):
        self._selector = selector

    def __len__(self):
        return len(self._selector._fd_to_key)

    def __getitem__(self, fileobj):
        try:
            fd = self._selector._fileobj_lookup(fileobj)
            return self._selector._fd_to_key[fd]
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None

    def __iter__(self):
        return iter(self._selector._fd_to_key)


class ZmqSelector(BaseSelector):
    """A selector that can be used with asyncio's selector base event loops."""

    def __init__(self):
        # this maps file descriptors to keys
        self._fd_to_key = {}
        # read-only mapping returned by get_map()
        self._map = _SelectorMapping(self)
        self._poller = ZMQPoller()

    def _fileobj_lookup(self, fileobj):
        """Return a file descriptor from a file object.

        This wraps _fileobj_to_fd() to do an exhaustive search in case
        the object is invalid but we still have it in our map.  This
        is used by unregister() so we can unregister an object that
        was previously registered even if it is closed.  It is also
        used by _SelectorMapping.
        """
        try:
            return _fileobj_to_fd(fileobj)
        except ValueError:
            # Do an exhaustive search.
            for key in self._fd_to_key.values():
                if key.fileobj is fileobj:
                    return key.fd
            # Raise ValueError after all.
            raise

    def register(self, fileobj, events, data=None):
        if (not events) or (events & ~(EVENT_READ | EVENT_WRITE)):
            raise ValueError("Invalid events: {!r}".format(events))

        key = SelectorKey(fileobj, self._fileobj_lookup(fileobj), events, data)

        if key.fd in self._fd_to_key:
            raise KeyError("{!r} (FD {}) is already registered"
                           .format(fileobj, key.fd))

        z_events = 0
        if events & EVENT_READ:
            z_events |= POLLIN
        if events & EVENT_WRITE:
            z_events |= POLLOUT
        try:
            self._poller.register(key.fd, z_events)
        except ZMQError as exc:
            raise OSError(exc.errno, exc.strerror) from exc

        self._fd_to_key[key.fd] = key
        return key

    def unregister(self, fileobj):
        try:
            key = self._fd_to_key.pop(self._fileobj_lookup(fileobj))
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None
        try:
            self._poller.unregister(key.fd)
        except ZMQError as exc:
            self._fd_to_key[key.fd] = key
            raise OSError(exc.errno, exc.strerror) from exc
        return key

    def modify(self, fileobj, events, data=None):
        try:
            fd = self._fileobj_lookup(fileobj)
            key = self._fd_to_key[fd]
        except KeyError:
            raise KeyError("{!r} is not registered".format(fileobj)) from None
        if data == key.data and events == key.events:
            return key
        if events != key.events:
            z_events = 0
            if events & EVENT_READ:
                z_events |= POLLIN
            if events & EVENT_WRITE:
                z_events |= POLLOUT
            try:
                self._poller.modify(fd, z_events)
            except ZMQError as exc:
                raise OSError(exc.errno, exc.strerror) from exc

        key = key._replace(data=data, events=events)
        self._fd_to_key[key.fd] = key
        return key

    def close(self):
        self._fd_to_key.clear()
        self._poller = None

    def get_map(self):
        return self._map

    def _key_from_fd(self, fd):
        """Return the key associated to a given file descriptor.

        Parameters:
        fd -- file descriptor

        Returns:
        corresponding key, or None if not found
        """
        try:
            return self._fd_to_key[fd]
        except KeyError:
            return None

    def select(self, timeout=None):
        if timeout is None:
            timeout = None
        elif timeout <= 0:
            timeout = 0
        else:
            # poll() has a resolution of 1 millisecond, round away from
            # zero to wait *at least* timeout seconds.
            timeout = math.ceil(timeout * 1e3)

        ready = []
        try:
            z_events = self._poller.poll(timeout)
        except ZMQError as exc:
            if exc.errno == EINTR:
                return ready
            else:
                raise OSError(exc.errno, exc.strerror) from exc

        for fd, evt in z_events:
            events = 0
            if evt & POLLIN:
                events |= EVENT_READ
            if evt & POLLOUT:
                events |= EVENT_WRITE
            if evt & POLLERR:
                events = EVENT_READ | EVENT_WRITE

            key = self._key_from_fd(fd)
            if key:
                ready.append((key, events & key.events))

        return ready

########NEW FILE########
__FILENAME__ = _test_util
"""Private test support utulities"""

import contextlib
import functools
import logging
import platform
import socket
import sys
import unittest


class Error(Exception):
    """Base class for regression test exceptions."""


class TestFailed(Error):
    """Test failed."""


def _requires_unix_version(sysname, min_version):  # pragma: no cover
    """Decorator raising SkipTest if the OS is `sysname` and the
    version is less than `min_version`.

    For example, @_requires_unix_version('FreeBSD', (7, 2)) raises SkipTest if
    the FreeBSD version is less than 7.2.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            if platform.system() == sysname:
                version_txt = platform.release().split('-', 1)[0]
                try:
                    version = tuple(map(int, version_txt.split('.')))
                except ValueError:
                    pass
                else:
                    if version < min_version:
                        min_version_txt = '.'.join(map(str, min_version))
                        raise unittest.SkipTest(
                            "%s version %s or higher required, not %s"
                            % (sysname, min_version_txt, version_txt))
            return func(*args, **kw)
        wrapper.min_version = min_version
        return wrapper
    return decorator


def requires_freebsd_version(*min_version):  # pragma: no cover
    """Decorator raising SkipTest if the OS is FreeBSD and the FreeBSD
    version is less than `min_version`.

    For example, @requires_freebsd_version(7, 2) raises SkipTest if the FreeBSD
    version is less than 7.2.
    """
    return _requires_unix_version('FreeBSD', min_version)


def requires_linux_version(*min_version):  # pragma: no cover
    """Decorator raising SkipTest if the OS is Linux and the Linux version is
    less than `min_version`.

    For example, @requires_linux_version(2, 6, 32) raises SkipTest if the Linux
    version is less than 2.6.32.
    """
    return _requires_unix_version('Linux', min_version)


def requires_mac_ver(*min_version):  # pragma: no cover
    """Decorator raising SkipTest if the OS is Mac OS X and the OS X
    version if less than min_version.

    For example, @requires_mac_ver(10, 5) raises SkipTest if the OS X version
    is lesser than 10.5.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            if sys.platform == 'darwin':
                version_txt = platform.mac_ver()[0]
                try:
                    version = tuple(map(int, version_txt.split('.')))
                except ValueError:
                    pass
                else:
                    if version < min_version:
                        min_version_txt = '.'.join(map(str, min_version))
                        raise unittest.SkipTest(
                            "Mac OS X %s or higher required, not %s"
                            % (min_version_txt, version_txt))
            return func(*args, **kw)
        wrapper.min_version = min_version
        return wrapper
    return decorator


# Don't use "localhost", since resolving it uses the DNS under recent
# Windows versions (see issue #18792).
HOST = "127.0.0.1"
HOSTv6 = "::1"


def _is_ipv6_enabled():  # pragma: no cover
    """Check whether IPv6 is enabled on this host."""
    if socket.has_ipv6:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.bind((HOSTv6, 0))
            return True
        except OSError:
            pass
        finally:
            if sock:
                sock.close()
    return False

IPV6_ENABLED = _is_ipv6_enabled()


def find_unused_port(family=socket.AF_INET,
                     socktype=socket.SOCK_STREAM):  # pragma: no cover
    """Returns an unused port that should be suitable for binding.  This is
    achieved by creating a temporary socket with the same family and type as
    the 'sock' parameter (default is AF_INET, SOCK_STREAM), and binding it to
    the specified host address (defaults to 0.0.0.0) with the port set to 0,
    eliciting an unused ephemeral port from the OS.  The temporary socket is
    then closed and deleted, and the ephemeral port is returned.

    Either this method or bind_port() should be used for any tests where a
    server socket needs to be bound to a particular port for the duration of
    the test.  Which one to use depends on whether the calling code is creating
    a python socket, or if an unused port needs to be provided in a constructor
    or passed to an external program (i.e. the -accept argument to openssl's
    s_server mode).  Always prefer bind_port() over find_unused_port() where
    possible.  Hard coded ports should *NEVER* be used.  As soon as a server
    socket is bound to a hard coded port, the ability to run multiple instances
    of the test simultaneously on the same host is compromised, which makes the
    test a ticking time bomb in a buildbot environment. On Unix buildbots, this
    may simply manifest as a failed test, which can be recovered from without
    intervention in most cases, but on Windows, the entire python process can
    completely and utterly wedge, requiring someone to log in to the buildbot
    and manually kill the affected process.

    (This is easy to reproduce on Windows, unfortunately, and can be traced to
    the SO_REUSEADDR socket option having different semantics on Windows versus
    Unix/Linux.  On Unix, you can't have two AF_INET SOCK_STREAM sockets bind,
    listen and then accept connections on identical host/ports.  An EADDRINUSE
    OSError will be raised at some point (depending on the platform and
    the order bind and listen were called on each socket).

    However, on Windows, if SO_REUSEADDR is set on the sockets, no EADDRINUSE
    will ever be raised when attempting to bind two identical host/ports. When
    accept() is called on each socket, the second caller's process will steal
    the port from the first caller, leaving them both in an awkwardly wedged
    state where they'll no longer respond to any signals or graceful kills, and
    must be forcibly killed via OpenProcess()/TerminateProcess().

    The solution on Windows is to use the SO_EXCLUSIVEADDRUSE socket option
    instead of SO_REUSEADDR, which effectively affords the same semantics as
    SO_REUSEADDR on Unix.  Given the propensity of Unix developers in the Open
    Source world compared to Windows ones, this is a common mistake.  A quick
    look over OpenSSL's 0.9.8g source shows that they use SO_REUSEADDR when
    openssl.exe is called with the 's_server' option, for example. See
    http://bugs.python.org/issue2550 for more info.  The following site also
    has a very thorough description about the implications of both REUSEADDR
    and EXCLUSIVEADDRUSE on Windows:
    http://msdn2.microsoft.com/en-us/library/ms740621(VS.85).aspx)

    XXX: although this approach is a vast improvement on previous attempts to
    elicit unused ports, it rests heavily on the assumption that the ephemeral
    port returned to us by the OS won't immediately be dished back out to some
    other process when we close and delete our temporary socket but before our
    calling code has a chance to bind the returned port.  We can deal with this
    issue if/when we come across it.
    """

    tempsock = socket.socket(family, socktype)
    port = bind_port(tempsock)
    tempsock.close()
    del tempsock
    return port


def bind_port(sock, host=HOST):  # pragma: no cover
    """Bind the socket to a free port and return the port number.  Relies on
    ephemeral ports in order to ensure we are using an unbound port.  This is
    important as many tests may be running simultaneously, especially in a
    buildbot environment.  This method raises an exception if the sock.family
    is AF_INET and sock.type is SOCK_STREAM, *and* the socket has SO_REUSEADDR
    or SO_REUSEPORT set on it.  Tests should *never* set these socket options
    for TCP/IP sockets.  The only case for setting these options is testing
    multicasting via multiple UDP sockets.

    Additionally, if the SO_EXCLUSIVEADDRUSE socket option is available (i.e.
    on Windows), it will be set on the socket.  This will prevent anyone else
    from bind()'ing to our host/port for the duration of the test.
    """

    if sock.family == socket.AF_INET and sock.type == socket.SOCK_STREAM:
        if hasattr(socket, 'SO_REUSEADDR'):
            if sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 1:
                raise TestFailed("tests should never set the SO_REUSEADDR "
                                 "socket option on TCP/IP sockets!")
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                if (sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT)
                        == 1):
                    raise TestFailed("tests should never set the SO_REUSEPORT "
                                     "socket option on TCP/IP sockets!")
            except OSError:
                # Python's socket module was compiled using modern headers
                # thus defining SO_REUSEPORT but this process is running
                # under an older kernel that does not support SO_REUSEPORT.
                pass
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)

    sock.bind((host, 0))
    port = sock.getsockname()[1]
    return port


def check_errno(errno, exc):
    assert exc.errno == errno, (exc, errno)


class TestHandler(logging.Handler):

    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        self.queue.put_nowait(record)


@contextlib.contextmanager
def log_hook(logname, queue):
    logger = logging.getLogger(logname)
    handler = TestHandler(queue)
    logger.addHandler(handler)
    yield
    logger.removeHandler(handler)

########NEW FILE########
__FILENAME__ = simple
import aiozmq
import aiozmq.rpc
import argparse
import asyncio
import gc
import multiprocessing
import random
import sys
import threading
import time
import zmq

from scipy.stats import norm, tmean, tvar, tstd
from numpy import array, arange
import matplotlib.pyplot as plt
from matplotlib import cm


def test_raw_zmq(count):
    """single thread raw zmq"""
    print('.', end='', flush=True)
    ctx = zmq.Context()
    router = ctx.socket(zmq.ROUTER)
    router.bind('tcp://127.0.0.1:*')
    address = router.getsockopt(zmq.LAST_ENDPOINT).rstrip(b'\0')
    dealer = ctx.socket(zmq.DEALER)
    dealer.connect(address)
    msg = b'func', b'\0'*200

    gc.collect()
    t1 = time.monotonic()
    for i in range(count):
        dealer.send_multipart(msg)
        addr, m1, m2 = router.recv_multipart()
        router.send_multipart((addr, m1, m2))
        dealer.recv_multipart()
    t2 = time.monotonic()
    gc.collect()
    router.close()
    dealer.close()
    ctx.destroy()
    return t2 - t1


def test_zmq_with_poller(count):
    """single thread zmq with poller"""
    print('.', end='', flush=True)
    ctx = zmq.Context()
    router = ctx.socket(zmq.ROUTER)
    router.bind('tcp://127.0.0.1:*')
    address = router.getsockopt(zmq.LAST_ENDPOINT).rstrip(b'\0')
    dealer = ctx.socket(zmq.DEALER)
    dealer.connect(address)
    msg = b'func', b'\0'*200

    poller = zmq.Poller()
    poller.register(router)
    poller.register(dealer)

    def wait(socket, event=zmq.POLLIN):
        while True:
            ret = poller.poll()
            for sock, ev in ret:
                if ev & event and sock == socket:
                    return

    gc.collect()
    t1 = time.monotonic()
    for i in range(count):
        dealer.send_multipart(msg, zmq.DONTWAIT)
        wait(router)
        addr, m1, m2 = router.recv_multipart(zmq.NOBLOCK)
        router.send_multipart((addr, m1, m2), zmq.DONTWAIT)
        wait(dealer)
        dealer.recv_multipart(zmq.NOBLOCK)
    t2 = time.monotonic()
    gc.collect()
    router.close()
    dealer.close()
    ctx.destroy()
    return t2 - t1


def test_zmq_with_thread(count):
    """zmq with threads"""
    print('.', end='', flush=True)
    ctx = zmq.Context()
    dealer = ctx.socket(zmq.DEALER)
    dealer.bind('tcp://127.0.0.1:*')
    address = dealer.getsockopt(zmq.LAST_ENDPOINT).rstrip(b'\0')
    msg = b'func', b'\0'*200

    def router_thread():
        router = ctx.socket(zmq.ROUTER)
        router.connect(address)

        for i in range(count):
            addr, m1, m2 = router.recv_multipart()
            router.send_multipart((addr, m1, m2))

        router.close()

    th = threading.Thread(target=router_thread)
    th.start()
    gc.collect()
    t1 = time.monotonic()
    for i in range(count):
        dealer.send_multipart(msg)
        dealer.recv_multipart()
    t2 = time.monotonic()
    gc.collect()
    th.join()
    dealer.close()
    ctx.destroy()
    return t2 - t1


class ZmqRouterProtocol(aiozmq.ZmqProtocol):

    transport = None

    def __init__(self, on_close):
        self.on_close = on_close

    def connection_made(self, transport):
        self.transport = transport

    def msg_received(self, msg):
        self.transport.write(msg)

    def connection_lost(self, exc):
        self.on_close.set_result(exc)


class ZmqDealerProtocol(aiozmq.ZmqProtocol):

    transport = None

    def __init__(self, count, on_close):
        self.count = count
        self.on_close = on_close

    def connection_made(self, transport):
        self.transport = transport

    def msg_received(self, msg):
        self.count -= 1
        if self.count:
            self.transport.write(msg)
        else:
            self.transport.close()

    def connection_lost(self, exc):
        self.on_close.set_result(exc)


def test_core_aiozmq(count):
    """core aiozmq"""
    print('.', end='', flush=True)
    loop = asyncio.get_event_loop()

    @asyncio.coroutine
    def go():
        router_closed = asyncio.Future()
        dealer_closed = asyncio.Future()
        router, _ = yield from loop.create_zmq_connection(
            lambda: ZmqRouterProtocol(router_closed),
            zmq.ROUTER,
            bind='tcp://127.0.0.1:*')

        addr = next(iter(router.bindings()))
        dealer, _ = yield from loop.create_zmq_connection(
            lambda: ZmqDealerProtocol(count, dealer_closed),
            zmq.DEALER,
            connect=addr)

        msg = b'func', b'\0'*200

        gc.collect()
        t1 = time.monotonic()
        dealer.write(msg)
        yield from dealer_closed
        t2 = time.monotonic()
        gc.collect()
        router.close()
        yield from router_closed
        return t2 - t1

    return loop.run_until_complete(go())


class Handler(aiozmq.rpc.AttrHandler):

    @aiozmq.rpc.method
    def func(self, data):
        return data


def test_aiozmq_rpc(count):
    """aiozmq.rpc"""
    print('.', end='', flush=True)
    loop = asyncio.get_event_loop()

    @asyncio.coroutine
    def go():
        server = yield from aiozmq.rpc.serve_rpc(Handler(),
                                                 bind='tcp://127.0.0.1:*')
        addr = next(iter(server.transport.bindings()))
        client = yield from aiozmq.rpc.connect_rpc(connect=addr)

        data = b'\0'*200

        gc.collect()
        t1 = time.monotonic()
        for i in range(count):
            yield from client.call.func(data)
        t2 = time.monotonic()
        gc.collect()
        server.close()
        yield from server.wait_closed()
        client.close()
        yield from client.wait_closed()
        return t2 - t1

    return loop.run_until_complete(go())


avail_tests = {f.__name__: f for f in [test_raw_zmq, test_zmq_with_poller,
                                       test_aiozmq_rpc, test_core_aiozmq,
                                       test_zmq_with_thread]}


ARGS = argparse.ArgumentParser(description="Run benchmark.")
ARGS.add_argument(
    '-n', '--count', action="store",
    nargs='?', type=int, default=1000, help='iterations count')
ARGS.add_argument(
    '-t', '--tries', action="store",
    nargs='?', type=int, default=30, help='count of tries')
ARGS.add_argument(
    '-p', '--plot-file-name', action="store",
    type=str, default=None,
    dest='plot_file_name', help='file name for plot')
ARGS.add_argument(
    '-v', '--verbose', action="count",
    help='verbosity level')
ARGS.add_argument(
    '--without-multiprocessing', action="store_false", default=True,
    dest='use_multiprocessing',
    help="don't use multiprocessing")
ARGS.add_argument(
    dest='tests', type=str,
    nargs='*', help='tests, {} by default'.format(
        list(sorted(avail_tests))))


def run_tests(tries, count, use_multiprocessing, funcs):
    results = {func.__doc__: [] for func in funcs}
    queue = []
    print('Run tests for {}*{} iterations: {}'
          .format(tries, count, sorted(results)))
    test_plan = [func for func in funcs for i in range(tries)]
    random.shuffle(test_plan)

    if use_multiprocessing:
        with multiprocessing.Pool() as pool:
            for test in test_plan:
                res = pool.apply_async(test, (count,))
                queue.append((test.__doc__, res))
            pool.close()
            pool.join()
        for name, res in queue:
            results[name].append(res.get())
    else:
        for test in test_plan:
            results[test.__doc__].append(test(count))
    print()
    return results


def print_and_plot_results(count, results, verbose, plot_file_name):
    print("RPS calculated as 95% confidence interval")

    rps_mean_ar = []
    rps_err_ar = []
    test_name_ar = []

    for test_name in sorted(results):
        data = results[test_name]
        rps = count / array(data)
        rps_mean = tmean(rps)
        rps_var = tvar(rps)
        low, high = norm.interval(0.95, loc=rps_mean, scale=rps_var**0.5)
        times = array(data) * 1000000 / count
        times_mean = tmean(times)
        times_stdev = tstd(times)
        print('Results for', test_name)
        print('RPS: {:d}: [{:d}, {:d}],\tmean: {:.3f} μs,'
              '\tstandard deviation {:.3f} μs'
              .format(int(rps_mean),
                      int(low),
                      int(high),
                      times_mean,
                      times_stdev))

        test_name_ar.append(test_name)
        rps_mean_ar.append(rps_mean)
        rps_err_ar.append(high - rps_mean)

        if verbose:
            print('    from', times)
        print()

    if plot_file_name is not None:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        L = len(rps_mean_ar)
        color = [cm.autumn(float(c) / (L - 1)) for c in arange(L)]
        bars = ax.bar(
            arange(L), rps_mean_ar,
            color=color, yerr=rps_err_ar, ecolor='k')
        # order of legend is reversed for visual appeal
        ax.legend(
            reversed(bars), reversed(test_name_ar),
            loc='upper left', framealpha=0.5)
        ax.get_xaxis().set_visible(False)
        plt.ylabel('Requets per Second', fontsize=16)
        plt.savefig(plot_file_name, dpi=96)
        print("Plot is saved to {}".format(plot_file_name))
        if verbose:
            plt.show()


def main(argv):
    args = ARGS.parse_args()

    count = args.count
    tries = args.tries
    verbose = args.verbose
    plot_file_name = args.plot_file_name
    use_multiprocessing = args.use_multiprocessing
    tests = args.tests
    if tests:
        tests = [avail_tests[t] for t in tests]
    else:
        tests = avail_tests.values()

    res = run_tests(tries, count, use_multiprocessing, tests)

    print()

    print_and_plot_results(count, res, verbose, plot_file_name)


if __name__ == '__main__':
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# aiozmq documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 17 15:12:47 2014.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

sys.version

#sys.path.insert(0, os.path.abspath('..'))
#import aiozmq


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.viewcode', 'sphinx.ext.autodoc',
              'sphinx.ext.intersphinx']

intersphinx_mapping = {'python': ('http://docs.python.org/3', None),
                       'pyzmq': ('http://zeromq.github.io/pyzmq', None)}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'aiozmq'
copyright = '2014, Nikolay Kim and Andrew Svetlov'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
#version = '.'.join(str(i) for i in aiozmq.version_info[:2])
# The full version, including alpha/beta/rc tags.
#release = aiozmq.__version__
version = "0.4"
release = "0.4 alpha"


# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

highlight_language = 'python3'


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'default'

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if on_rtd:
    html_theme = 'default'
else:
    try:
        import sphinx_rtd_theme
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    except ImportError:
        html_theme = 'pyramid'


# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'aiozmqdoc'

########NEW FILE########
__FILENAME__ = rpc_custom_translator
import asyncio
import aiozmq
import aiozmq.rpc
import msgpack


class Point:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if isinstance(other, Point):
            return (self.x, self.y) == (other.x, other.y)
        return NotImplemented


translation_table = {
    0: (Point,
        lambda value: msgpack.packb((value.x, value.y)),
        lambda binary: Point(*msgpack.unpackb(binary))),
}


class ServerHandler(aiozmq.rpc.AttrHandler):
    @aiozmq.rpc.method
    def remote(self, val):
        return val


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.serve_rpc(
        ServerHandler(), bind='tcp://*:*',
        translation_table=translation_table)
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.connect_rpc(
        connect=server_addr,
        translation_table=translation_table)

    ret = yield from client.call.remote(Point(1, 2))
    assert ret == Point(1, 2)

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rpc_dict_handler
import asyncio
import aiozmq
import aiozmq.rpc


@aiozmq.rpc.method
def a():
    return 'a'


@aiozmq.rpc.method
def b():
    return 'b'


handlers_dict = {'a': a,
                 'subnamespace': {'b': b}}


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.start_server(
        handlers_dict, bind='tcp://*:*')
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.open_client(
        connect=server_addr)

    ret = yield from client.call.a()
    assert 'a' == ret

    ret = yield from client.call.subnamespace.b()
    assert 'b' == ret

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rpc_dynamic
import asyncio
import aiozmq
import aiozmq.rpc


class DynamicHandler(aiozmq.rpc.AttrHandler):

    def __init__(self, namespace=()):
        self.namespace = namespace

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            return DynamicHandler(self.namespace + (key,))

    @aiozmq.rpc.method
    def func(self):
        return (self.namespace, 'val')


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.start_server(
        DynamicHandler(), bind='tcp://*:*')
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.open_client(
        connect=server_addr)

    ret = yield from client.call.func()
    assert ((), 'val') == ret, ret

    ret = yield from client.call.a.func()
    assert (('a',), 'val') == ret, ret

    ret = yield from client.call.a.b.func()
    assert (('a', 'b'), 'val') == ret, ret

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rpc_exception_translator
import asyncio
import aiozmq
import aiozmq.rpc


class CustomError(Exception):

    def __init__(self, val):
        self.val = val
        super().__init__(val)


exc_name = CustomError.__module__+'.'+CustomError.__name__
error_table = {exc_name: CustomError}


class ServerHandler(aiozmq.rpc.AttrHandler):
    @aiozmq.rpc.method
    def remote(self, val):
        raise CustomError(val)


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.start_server(
        ServerHandler(), bind='tcp://*:*')
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.open_client(
        connect=server_addr,
        error_table=error_table)

    try:
        yield from client.call.remote('value')
    except CustomError as exc:
        exc.val == 'value'

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rpc_incorrect_calls
import asyncio
import aiozmq
import aiozmq.rpc


class ServerHandler(aiozmq.rpc.AttrHandler):

    @aiozmq.rpc.method
    def remote_func(self, a: int, b: int) -> int:
        return a + b


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.start_server(
        ServerHandler(), bind='tcp://*:*')
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.open_client(
        connect=server_addr)

    try:
        yield from client.call.unknown_function()
    except aiozmq.rpc.NotFoundError as exc:
        print("client.rpc.unknown_function(): {}".format(exc))

    try:
        yield from client.call.remote_func(bad_arg=1)
    except aiozmq.rpc.ParametersError as exc:
        print("client.rpc.remote_func(bad_arg=1): {}".format(exc))

    try:
        yield from client.call.remote_func(1)
    except aiozmq.rpc.ParametersError as exc:
        print("client.rpc.remote_func(1): {}".format(exc))

    try:
        yield from client.call.remote_func('a', 'b')
    except aiozmq.rpc.ParametersError as exc:
        print("client.rpc.remote_func('a', 'b'): {}".format(exc))

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rpc_pipeline
import asyncio
import aiozmq
import aiozmq.rpc


class ServerHandler(aiozmq.rpc.AttrHandler):

    @aiozmq.rpc.method
    def remote_func(self, a: int, b: int):
        pass


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.serve_pipeline(
        ServerHandler(), bind='tcp://*:*')
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.connect_pipeline(
        connect=server_addr)

    yield from client.notify.remote_func(1, 2)

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rpc_pubsub
import asyncio
import aiozmq
import aiozmq.rpc


class ServerHandler(aiozmq.rpc.AttrHandler):

    @aiozmq.rpc.method
    def remote_func(self, a: int, b: int):
        pass


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.serve_pubsub(
        ServerHandler(), subscribe='topic', bind='tcp://*:*')
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.connect_pubsub(
        connect=server_addr)

    yield from client.publish('topic').remote_func(1, 2)

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rpc_simple
import asyncio
import aiozmq
import aiozmq.rpc


class ServerHandler(aiozmq.rpc.AttrHandler):

    @aiozmq.rpc.method
    def remote_func(self, a: int, b: int) -> int:
        return a + b


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.serve_rpc(
        ServerHandler(), bind='tcp://*:*')
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.connect_rpc(
        connect=server_addr)

    ret = yield from client.call.remote_func(1, 2)
    assert 3 == ret

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rpc_with_subhandlers
import asyncio
import aiozmq
import aiozmq.rpc


class Handler(aiozmq.rpc.AttrHandler):

    def __init__(self, ident):
        self.ident = ident
        self.subhandler = SubHandler(self.ident, 'subident')

    @aiozmq.rpc.method
    def a(self):
        return (self.ident, 'a')


class SubHandler(aiozmq.rpc.AttrHandler):

    def __init__(self, ident, subident):
        self.ident = ident
        self.subident = subident

    @aiozmq.rpc.method
    def b(self):
        return (self.ident, self.subident, 'b')


@asyncio.coroutine
def go():
    server = yield from aiozmq.rpc.start_server(
        Handler('ident'), bind='tcp://*:*')
    server_addr = next(iter(server.transport.bindings()))

    client = yield from aiozmq.rpc.open_client(
        connect=server_addr)

    ret = yield from client.call.a()
    assert ('ident', 'a') == ret

    ret = yield from client.call.subhandler.b()
    assert ('ident', 'subident', 'b') == ret

    server.close()
    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())
    print("DONE")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = runtests
"""Run aiozmq unittests.

Usage:
  python3 runtests.py [flags] [pattern] ...

Patterns are matched against the fully qualified name of the test,
including package, module, class and method,
e.g. 'tests.test_events.PolicyTests.testPolicy'.

For full help, try --help.

runtests.py --coverage is equivalent of:

  $(COVERAGE) run --branch runtests.py -v
  $(COVERAGE) html $(list of files)
  $(COVERAGE) report -m $(list of files)

"""

# Originally written by Beech Horn (for NDB).

import argparse
import gc
import logging
import os
import re
import shutil
import sys
import unittest
import traceback
import textwrap
import importlib.machinery

try:
    import coverage
except ImportError:
    coverage = None

from unittest.signals import installHandler

assert sys.version >= '3.3', 'Please use Python 3.3 or higher.'

ARGS = argparse.ArgumentParser(description="Run all unittests.")
ARGS.add_argument(
    '-v', action="store", dest='verbose',
    nargs='?', const=1, type=int, default=0, help='verbose')
ARGS.add_argument(
    '-x', action="store_true", dest='exclude', help='exclude tests')
ARGS.add_argument(
    '-f', '--failfast', action="store_true", default=False,
    dest='failfast', help='Stop on first fail or error')
ARGS.add_argument(
    '-c', '--catch', action="store_true", default=False,
    dest='catchbreak', help='Catch control-C and display results')
ARGS.add_argument(
    '--forever', action="store_true", dest='forever', default=False,
    help='run tests forever to catch sporadic errors')
ARGS.add_argument(
    '--findleaks', action='store_true', dest='findleaks',
    help='detect tests that leak memory')
ARGS.add_argument(
    '-q', action="store_true", dest='quiet', help='quiet')
ARGS.add_argument(
    '--tests', action="store", dest='testsdir', default='tests',
    help='tests directory')
ARGS.add_argument(
    '--coverage', action="store_true", dest='coverage',
    help='enable html coverage report')
ARGS.add_argument(
    'pattern', action="store", nargs="*",
    help='optional regex patterns to match test ids (default all tests)')

COV_ARGS = argparse.ArgumentParser(description="Run all unittests.")
COV_ARGS.add_argument(
    '--coverage', action="store", dest='coverage', nargs='?', const='',
    help='enable coverage report and provide python files directory')


def load_modules(basedir, suffix='.py', *, verbose=False):
    def list_dir(prefix, dir):
        files = []

        modpath = os.path.join(dir, '__init__.py')
        if os.path.isfile(modpath):
            mod = os.path.split(dir)[-1]
            files.append(('{}{}'.format(prefix, mod), modpath))

            prefix = '{}{}.'.format(prefix, mod)

        for name in os.listdir(dir):
            path = os.path.join(dir, name)

            if os.path.isdir(path):
                files.extend(list_dir('{}{}.'.format(prefix, name), path))
            else:
                if (name != '__init__.py' and
                    name.endswith(suffix) and
                    not name.startswith(('.', '_'))):
                    files.append(('{}{}'.format(prefix, name[:-3]), path))

        return files

    mods = []
    for modname, sourcefile in list_dir('', basedir):
        if modname == 'runtests':
            continue
        try:
            loader = importlib.machinery.SourceFileLoader(modname, sourcefile)
            mods.append((loader.load_module(), sourcefile))
        except SyntaxError:
            raise
        except Exception as err:
            print("Skipping '{}': {}".format(modname, err), file=sys.stderr)
            if verbose:
                try:
                    traceback.print_exc()
                except Exception:
                    pass
    return mods


class TestsFinder:

    def __init__(self, testsdir, includes=(), excludes=(), *,
                 verbose=False):
        self._testsdir = testsdir
        self._includes = includes
        self._excludes = excludes
        self._verbose = verbose
        self.find_available_tests()

    def find_available_tests(self):
        """
        Find available test classes without instantiating them.
        """
        self._test_factories = []
        mods = [mod for mod, _ in load_modules(self._testsdir,
                                               verbose=self._verbose)]
        for mod in mods:
            for name in set(dir(mod)):
                if name.endswith('Tests'):
                    self._test_factories.append(getattr(mod, name))

    def load_tests(self):
        """
        Load test cases from the available test classes and apply
        optional include / exclude filters.
        """
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        for test_factory in self._test_factories:
            tests = loader.loadTestsFromTestCase(test_factory)
            if self._includes:
                tests = [test
                         for test in tests
                         if any(re.search(pat, test.id())
                                for pat in self._includes)]
            if self._excludes:
                tests = [test
                         for test in tests
                         if not any(re.search(pat, test.id())
                                    for pat in self._excludes)]
            suite.addTests(tests)
        return suite


class TestResult(unittest.TextTestResult):

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.leaks = []

    def startTest(self, test):
        super().startTest(test)
        gc.collect()

    def addSuccess(self, test):
        super().addSuccess(test)
        gc.collect()
        if gc.garbage:
            if self.showAll:
                self.stream.writeln(
                    "    Warning: test created {} uncollectable "
                    "object(s).".format(len(gc.garbage)))
            # move the uncollectable objects somewhere so we don't see
            # them again
            self.leaks.append((self.getDescription(test), gc.garbage[:]))
            del gc.garbage[:]


class TestRunner(unittest.TextTestRunner):
    resultclass = TestResult

    def run(self, test):
        result = super().run(test)
        if result.leaks:
            self.stream.writeln("{} tests leaks:".format(len(result.leaks)))
            for name, leaks in result.leaks:
                self.stream.writeln(' '*4 + name + ':')
                for leak in leaks:
                    self.stream.writeln(' '*8 + repr(leak))
        return result


def runtests():
    args = ARGS.parse_args()

    if args.coverage and coverage is None:
        URL = "bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py"
        print(textwrap.dedent("""
            coverage package is not installed.

            To install coverage3 for Python 3, you need:
              - Setuptools (https://pypi.python.org/pypi/setuptools)

              What worked for me:
              - download {0}
                 * curl -O https://{0}
              - python3 ez_setup.py
              - python3 -m easy_install coverage
        """.format(URL)).strip())
        sys.exit(1)

    testsdir = os.path.abspath(args.testsdir)
    if not os.path.isdir(testsdir):
        print("Tests directory is not found: {}\n".format(testsdir))
        ARGS.print_help()
        return

    excludes = includes = []
    if args.exclude:
        excludes = args.pattern
    else:
        includes = args.pattern

    v = 0 if args.quiet else args.verbose + 1
    failfast = args.failfast
    catchbreak = args.catchbreak
    findleaks = args.findleaks
    runner_factory = TestRunner if findleaks else unittest.TextTestRunner

    if args.coverage:
        cov = coverage.coverage(branch=True,
                                source=['aiozmq'],
                                )
        cov.start()

    finder = TestsFinder(args.testsdir, includes, excludes,
                         verbose=args.verbose)
    logger = logging.getLogger()
    if v == 0:
        logger.setLevel(logging.CRITICAL)
    elif v == 1:
        logger.setLevel(logging.ERROR)
    elif v == 2:
        logger.setLevel(logging.WARNING)
    elif v == 3:
        logger.setLevel(logging.INFO)
    elif v >= 4:
        logger.setLevel(logging.DEBUG)
    if catchbreak:
        installHandler()
    try:
        if args.forever:
            while True:
                tests = finder.load_tests()
                result = runner_factory(verbosity=v,
                                        failfast=failfast,
                                        warnings="always").run(tests)
                if not result.wasSuccessful():
                    sys.exit(1)
        else:
            tests = finder.load_tests()
            result = runner_factory(verbosity=v,
                                    failfast=failfast,
                                    warnings="always").run(tests)
            sys.exit(not result.wasSuccessful())
    finally:
        if args.coverage:
            cov.stop()
            cov.save()
            if os.path.exists('htmlcov'):
                shutil.rmtree('htmlcov')
            cov.html_report(directory='htmlcov')
            print("\nCoverage report:")
            cov.report(show_missing=False)
            here = os.path.dirname(os.path.abspath(__file__))
            print("\nFor html report:")
            print("open file://{}/htmlcov/index.html".format(here))


if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = echo
import os

if __name__ == '__main__':
    while True:
        buf = os.read(0, 1024)
        os.write(1, buf)

########NEW FILE########
__FILENAME__ = echo2
import os

if __name__ == '__main__':
    buf = os.read(0, 1024)
    os.write(1, b'OUT:'+buf)
    os.write(2, b'ERR:'+buf)

########NEW FILE########
__FILENAME__ = echo3
import os

if __name__ == '__main__':
    while True:
        buf = os.read(0, 1024)
        try:
            os.write(1, b'OUT:'+buf)
        except OSError as ex:
            os.write(2, b'ERR:' + ex.__class__.__name__.encode('ascii'))

########NEW FILE########
__FILENAME__ = events_test
"""Tests for events.py."""

import functools
import gc
import io
import os
import platform
import signal
import socket
try:
    import ssl
except ImportError:
    ssl = None
    HAS_SNI = False
else:
    from ssl import HAS_SNI
import subprocess
import sys
import threading
import time
import errno
import unittest

from aiozmq._test_util import (find_unused_port,
                               IPV6_ENABLED,
                               requires_mac_ver,
                               requires_freebsd_version)


import asyncio
from asyncio import selector_events
from asyncio import test_utils


import aiozmq

if sys.platform == 'win32':
    raise unittest.SkipTest("don't check")


def data_file(filename):
    fullname = os.path.join(os.path.dirname(__file__), filename)
    if os.path.isfile(fullname):
        return fullname
    raise FileNotFoundError(filename)


def osx_tiger():
    """Return True if the platform is Mac OS 10.4 or older."""
    if sys.platform != 'darwin':
        return False
    version = platform.mac_ver()[0]
    version = tuple(map(int, version.split('.')))
    return version < (10, 5)


ONLYCERT = data_file('ssl_cert.pem')
ONLYKEY = data_file('ssl_key.pem')
SIGNED_CERTFILE = data_file('keycert3.pem')
SIGNING_CA = data_file('pycacert.pem')


class MyBaseProto(asyncio.Protocol):
    connected = None
    done = None

    def __init__(self, loop=None):
        self.transport = None
        self.state = 'INITIAL'
        self.nbytes = 0
        if loop is not None:
            self.connected = asyncio.Future(loop=loop)
            self.done = asyncio.Future(loop=loop)

    def connection_made(self, transport):
        self.transport = transport
        assert self.state == 'INITIAL', self.state
        self.state = 'CONNECTED'
        if self.connected:
            self.connected.set_result(None)

    def data_received(self, data):
        assert self.state == 'CONNECTED', self.state
        self.nbytes += len(data)

    def eof_received(self):
        assert self.state == 'CONNECTED', self.state
        self.state = 'EOF'

    def connection_lost(self, exc):
        assert self.state in ('CONNECTED', 'EOF'), self.state
        self.state = 'CLOSED'
        if self.done:
            self.done.set_result(None)


class MyProto(MyBaseProto):
    def connection_made(self, transport):
        super().connection_made(transport)
        transport.write(b'GET / HTTP/1.0\r\nHost: example.com\r\n\r\n')


class MyDatagramProto(asyncio.DatagramProtocol):
    done = None

    def __init__(self, loop=None):
        self.state = 'INITIAL'
        self.nbytes = 0
        if loop is not None:
            self.done = asyncio.Future(loop=loop)

    def connection_made(self, transport):
        self.transport = transport
        assert self.state == 'INITIAL', self.state
        self.state = 'INITIALIZED'

    def datagram_received(self, data, addr):
        assert self.state == 'INITIALIZED', self.state
        self.nbytes += len(data)

    def error_received(self, exc):
        assert self.state == 'INITIALIZED', self.state

    def connection_lost(self, exc):
        assert self.state == 'INITIALIZED', self.state
        self.state = 'CLOSED'
        if self.done:
            self.done.set_result(None)


class MyReadPipeProto(asyncio.Protocol):
    done = None

    def __init__(self, loop=None):
        self.state = ['INITIAL']
        self.nbytes = 0
        self.transport = None
        if loop is not None:
            self.done = asyncio.Future(loop=loop)

    def connection_made(self, transport):
        self.transport = transport
        assert self.state == ['INITIAL'], self.state
        self.state.append('CONNECTED')

    def data_received(self, data):
        assert self.state == ['INITIAL', 'CONNECTED'], self.state
        self.nbytes += len(data)

    def eof_received(self):
        assert self.state == ['INITIAL', 'CONNECTED'], self.state
        self.state.append('EOF')

    def connection_lost(self, exc):
        if 'EOF' not in self.state:
            self.state.append('EOF')  # It is okay if EOF is missed.
        assert self.state == ['INITIAL', 'CONNECTED', 'EOF'], self.state
        self.state.append('CLOSED')
        if self.done:
            self.done.set_result(None)


class MyWritePipeProto(asyncio.BaseProtocol):
    done = None

    def __init__(self, loop=None):
        self.state = 'INITIAL'
        self.transport = None
        if loop is not None:
            self.done = asyncio.Future(loop=loop)

    def connection_made(self, transport):
        self.transport = transport
        assert self.state == 'INITIAL', self.state
        self.state = 'CONNECTED'

    def connection_lost(self, exc):
        assert self.state == 'CONNECTED', self.state
        self.state = 'CLOSED'
        if self.done:
            self.done.set_result(None)


class MySubprocessProtocol(asyncio.SubprocessProtocol):

    def __init__(self, loop):
        self.state = 'INITIAL'
        self.transport = None
        self.connected = asyncio.Future(loop=loop)
        self.completed = asyncio.Future(loop=loop)
        self.disconnects = {fd: asyncio.Future(loop=loop) for fd in range(3)}
        self.data = {1: b'', 2: b''}
        self.returncode = None
        self.got_data = {1: asyncio.Event(loop=loop),
                         2: asyncio.Event(loop=loop)}

    def connection_made(self, transport):
        self.transport = transport
        assert self.state == 'INITIAL', self.state
        self.state = 'CONNECTED'
        self.connected.set_result(None)

    def connection_lost(self, exc):
        assert self.state == 'CONNECTED', self.state
        self.state = 'CLOSED'
        self.completed.set_result(None)

    def pipe_data_received(self, fd, data):
        assert self.state == 'CONNECTED', self.state
        self.data[fd] += data
        self.got_data[fd].set()

    def pipe_connection_lost(self, fd, exc):
        assert self.state == 'CONNECTED', self.state
        if exc:
            self.disconnects[fd].set_exception(exc)
        else:
            self.disconnects[fd].set_result(exc)

    def process_exited(self):
        assert self.state == 'CONNECTED', self.state
        self.returncode = self.transport.get_returncode()


class EventLoopTestsMixin:

    def setUp(self):
        super().setUp()
        self.loop = self.create_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        # just in case if we have transport close callbacks
        test_utils.run_briefly(self.loop)

        self.loop.close()
        gc.collect()
        asyncio.set_event_loop(None)
        super().tearDown()

    def test_run_until_complete_nesting(self):
        @asyncio.coroutine
        def coro1():
            yield

        @asyncio.coroutine
        def coro2():
            self.assertTrue(self.loop.is_running())
            self.loop.run_until_complete(coro1())

        self.assertRaises(
            RuntimeError, self.loop.run_until_complete, coro2())

    # Note: because of the default Windows timing granularity of
    # 15.6 msec, we use fairly long sleep times here (~100 msec).

    def test_run_until_complete(self):
        t0 = self.loop.time()
        self.loop.run_until_complete(asyncio.sleep(0.1, loop=self.loop))
        t1 = self.loop.time()
        self.assertTrue(0.08 <= t1-t0 <= 0.8, t1-t0)

    def test_run_until_complete_stopped(self):
        @asyncio.coroutine
        def cb():
            self.loop.stop()
            yield from asyncio.sleep(0.1, loop=self.loop)
        task = cb()
        self.assertRaises(RuntimeError,
                          self.loop.run_until_complete, task)

    def test_call_later(self):
        results = []

        def callback(arg):
            results.append(arg)
            self.loop.stop()

        self.loop.call_later(0.1, callback, 'hello world')
        t0 = time.monotonic()
        self.loop.run_forever()
        t1 = time.monotonic()
        self.assertEqual(results, ['hello world'])
        self.assertTrue(0.08 <= t1-t0 <= 0.8, t1-t0)

    def test_call_soon(self):
        results = []

        def callback(arg1, arg2):
            results.append((arg1, arg2))
            self.loop.stop()

        self.loop.call_soon(callback, 'hello', 'world')
        self.loop.run_forever()
        self.assertEqual(results, [('hello', 'world')])

    def test_call_soon_threadsafe(self):
        results = []
        lock = threading.Lock()

        def callback(arg):
            results.append(arg)
            if len(results) >= 2:
                self.loop.stop()

        def run_in_thread():
            self.loop.call_soon_threadsafe(callback, 'hello')
            lock.release()

        lock.acquire()
        t = threading.Thread(target=run_in_thread)
        t.start()

        with lock:
            self.loop.call_soon(callback, 'world')
            self.loop.run_forever()
        t.join()
        self.assertEqual(results, ['hello', 'world'])

    def test_call_soon_threadsafe_same_thread(self):
        results = []

        def callback(arg):
            results.append(arg)
            if len(results) >= 2:
                self.loop.stop()

        self.loop.call_soon_threadsafe(callback, 'hello')
        self.loop.call_soon(callback, 'world')
        self.loop.run_forever()
        self.assertEqual(results, ['hello', 'world'])

    def test_run_in_executor(self):
        def run(arg):
            return (arg, threading.get_ident())
        f2 = self.loop.run_in_executor(None, run, 'yo')
        res, thread_id = self.loop.run_until_complete(f2)
        self.assertEqual(res, 'yo')
        self.assertNotEqual(thread_id, threading.get_ident())

    def test_reader_callback(self):
        r, w = test_utils.socketpair()
        r.setblocking(False)
        bytes_read = bytearray()

        def reader():
            try:
                data = r.recv(1024)
            except BlockingIOError:
                # Spurious readiness notifications are possible
                # at least on Linux -- see man select.
                return
            if data:
                bytes_read.extend(data)
            else:
                self.assertTrue(self.loop.remove_reader(r.fileno()))
                r.close()

        self.loop.add_reader(r.fileno(), reader)
        self.loop.call_soon(w.send, b'abc')
        test_utils.run_until(self.loop, lambda: len(bytes_read) >= 3)
        self.loop.call_soon(w.send, b'def')
        test_utils.run_until(self.loop, lambda: len(bytes_read) >= 6)
        self.loop.call_soon(w.close)
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()
        self.assertEqual(bytes_read, b'abcdef')

    def test_writer_callback(self):
        r, w = test_utils.socketpair()
        w.setblocking(False)

        def writer(data):
            w.send(data)
            self.loop.stop()

        data = b'x' * 1024
        self.loop.add_writer(w.fileno(), writer, data)
        self.loop.run_forever()

        self.assertTrue(self.loop.remove_writer(w.fileno()))
        self.assertFalse(self.loop.remove_writer(w.fileno()))

        w.close()
        read = r.recv(len(data) * 2)
        r.close()
        self.assertEqual(read, data)

    def _basetest_sock_client_ops(self, httpd, sock):
        sock.setblocking(False)
        self.loop.run_until_complete(
            self.loop.sock_connect(sock, httpd.address))
        self.loop.run_until_complete(
            self.loop.sock_sendall(sock, b'GET / HTTP/1.0\r\n\r\n'))
        data = self.loop.run_until_complete(
            self.loop.sock_recv(sock, 1024))
        # consume data
        self.loop.run_until_complete(
            self.loop.sock_recv(sock, 1024))
        sock.close()
        self.assertTrue(data.startswith(b'HTTP/1.0 200 OK'))

    def test_sock_client_ops(self):
        with test_utils.run_test_server() as httpd:
            sock = socket.socket()
            self._basetest_sock_client_ops(httpd, sock)

    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'No UNIX Sockets')
    def test_unix_sock_client_ops(self):
        with test_utils.run_test_unix_server() as httpd:
            sock = socket.socket(socket.AF_UNIX)
            self._basetest_sock_client_ops(httpd, sock)

    def test_sock_client_fail(self):
        # Make sure that we will get an unused port
        address = None
        try:
            s = socket.socket()
            s.bind(('127.0.0.1', 0))
            address = s.getsockname()
        finally:
            s.close()

        sock = socket.socket()
        sock.setblocking(False)
        with self.assertRaises(ConnectionRefusedError):
            self.loop.run_until_complete(
                self.loop.sock_connect(sock, address))
        sock.close()

    def test_sock_accept(self):
        listener = socket.socket()
        listener.setblocking(False)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        client = socket.socket()
        client.connect(listener.getsockname())

        f = self.loop.sock_accept(listener)
        conn, addr = self.loop.run_until_complete(f)
        self.assertEqual(conn.gettimeout(), 0)
        self.assertEqual(addr, client.getsockname())
        self.assertEqual(client.getpeername(), listener.getsockname())
        client.close()
        conn.close()
        listener.close()

    @unittest.skipUnless(hasattr(signal, 'SIGKILL'), 'No SIGKILL')
    def test_add_signal_handler(self):
        caught = 0

        def my_handler():
            nonlocal caught
            caught += 1

        # Check error behavior first.
        self.assertRaises(
            TypeError, self.loop.add_signal_handler, 'boom', my_handler)
        self.assertRaises(
            TypeError, self.loop.remove_signal_handler, 'boom')
        self.assertRaises(
            ValueError, self.loop.add_signal_handler, signal.NSIG+1,
            my_handler)
        self.assertRaises(
            ValueError, self.loop.remove_signal_handler, signal.NSIG+1)
        self.assertRaises(
            ValueError, self.loop.add_signal_handler, 0, my_handler)
        self.assertRaises(
            ValueError, self.loop.remove_signal_handler, 0)
        self.assertRaises(
            ValueError, self.loop.add_signal_handler, -1, my_handler)
        self.assertRaises(
            ValueError, self.loop.remove_signal_handler, -1)
        self.assertRaises(
            RuntimeError, self.loop.add_signal_handler, signal.SIGKILL,
            my_handler)
        # Removing SIGKILL doesn't raise, since we don't call signal().
        self.assertFalse(self.loop.remove_signal_handler(signal.SIGKILL))
        # Now set a handler and handle it.
        self.loop.add_signal_handler(signal.SIGINT, my_handler)

        os.kill(os.getpid(), signal.SIGINT)
        test_utils.run_until(self.loop, lambda: caught)

        # Removing it should restore the default handler.
        self.assertTrue(self.loop.remove_signal_handler(signal.SIGINT))
        self.assertEqual(signal.getsignal(signal.SIGINT),
                         signal.default_int_handler)
        # Removing again returns False.
        self.assertFalse(self.loop.remove_signal_handler(signal.SIGINT))

    @unittest.skipUnless(hasattr(signal, 'SIGALRM'), 'No SIGALRM')
    def test_signal_handling_while_selecting(self):
        # Test with a signal actually arriving during a select() call.
        caught = 0

        def my_handler():
            nonlocal caught
            caught += 1
            self.loop.stop()

        self.loop.add_signal_handler(signal.SIGALRM, my_handler)

        signal.setitimer(signal.ITIMER_REAL, 0.01, 0)  # Send SIGALRM once.
        self.loop.run_forever()
        self.assertEqual(caught, 1)

    @unittest.skipUnless(hasattr(signal, 'SIGALRM'), 'No SIGALRM')
    def test_signal_handling_args(self):
        some_args = (42,)
        caught = 0

        def my_handler(*args):
            nonlocal caught
            caught += 1
            self.assertEqual(args, some_args)

        self.loop.add_signal_handler(signal.SIGALRM, my_handler, *some_args)

        signal.setitimer(signal.ITIMER_REAL, 0.1, 0)  # Send SIGALRM once.
        self.loop.call_later(0.5, self.loop.stop)
        self.loop.run_forever()
        self.assertEqual(caught, 1)

    def _basetest_create_connection(self, connection_fut, check_sockname=True):
        tr, pr = self.loop.run_until_complete(connection_fut)
        self.assertIsInstance(tr, asyncio.Transport)
        self.assertIsInstance(pr, asyncio.Protocol)
        if check_sockname:
            self.assertIsNotNone(tr.get_extra_info('sockname'))
        self.loop.run_until_complete(pr.done)
        self.assertGreater(pr.nbytes, 0)
        tr.close()

    def test_create_connection(self):
        with test_utils.run_test_server() as httpd:
            conn_fut = self.loop.create_connection(
                lambda: MyProto(loop=self.loop), *httpd.address)
            self._basetest_create_connection(conn_fut)

    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'No UNIX Sockets')
    def test_create_unix_connection(self):
        # Issue #20682: On Mac OS X Tiger, getsockname() returns a
        # zero-length address for UNIX socket.
        check_sockname = not osx_tiger()

        with test_utils.run_test_unix_server() as httpd:
            conn_fut = self.loop.create_unix_connection(
                lambda: MyProto(loop=self.loop), httpd.address)
            self._basetest_create_connection(conn_fut, check_sockname)

    def test_create_connection_sock(self):
        with test_utils.run_test_server() as httpd:
            sock = None
            infos = self.loop.run_until_complete(
                self.loop.getaddrinfo(
                    *httpd.address, type=socket.SOCK_STREAM))
            for family, type, proto, cname, address in infos:
                try:
                    sock = socket.socket(family=family, type=type, proto=proto)
                    sock.setblocking(False)
                    self.loop.run_until_complete(
                        self.loop.sock_connect(sock, address))
                except:
                    pass
                else:
                    break
            else:
                assert False, 'Can not create socket.'

            f = self.loop.create_connection(
                lambda: MyProto(loop=self.loop), sock=sock)
            tr, pr = self.loop.run_until_complete(f)
            self.assertIsInstance(tr, asyncio.Transport)
            self.assertIsInstance(pr, asyncio.Protocol)
            self.loop.run_until_complete(pr.done)
            self.assertGreater(pr.nbytes, 0)
            tr.close()

    def _basetest_create_ssl_connection(self, connection_fut,
                                        check_sockname=True):
        tr, pr = self.loop.run_until_complete(connection_fut)
        self.assertIsInstance(tr, asyncio.Transport)
        self.assertIsInstance(pr, asyncio.Protocol)
        self.assertTrue('ssl' in tr.__class__.__name__.lower())
        if check_sockname:
            self.assertIsNotNone(tr.get_extra_info('sockname'))
        self.loop.run_until_complete(pr.done)
        self.assertGreater(pr.nbytes, 0)
        tr.close()

    @unittest.skipIf(ssl is None, 'No ssl module')
    @unittest.expectedFailure
    def test_create_ssl_connection(self):
        with test_utils.run_test_server(use_ssl=True) as httpd:
            conn_fut = self.loop.create_connection(
                lambda: MyProto(loop=self.loop),
                *httpd.address,
                ssl=test_utils.dummy_ssl_context())

            self._basetest_create_ssl_connection(conn_fut)

    @unittest.skipIf(ssl is None, 'No ssl module')
    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'No UNIX Sockets')
    @unittest.expectedFailure
    def test_create_ssl_unix_connection(self):
        # Issue #20682: On Mac OS X Tiger, getsockname() returns a
        # zero-length address for UNIX socket.
        check_sockname = not osx_tiger()

        with test_utils.run_test_unix_server(use_ssl=True) as httpd:
            conn_fut = self.loop.create_unix_connection(
                lambda: MyProto(loop=self.loop),
                httpd.address,
                ssl=test_utils.dummy_ssl_context(),
                server_hostname='127.0.0.1')

            self._basetest_create_ssl_connection(conn_fut, check_sockname)

    def test_create_connection_local_addr(self):
        with test_utils.run_test_server() as httpd:
            port = find_unused_port()
            f = self.loop.create_connection(
                lambda: MyProto(loop=self.loop),
                *httpd.address, local_addr=(httpd.address[0], port))
            tr, pr = self.loop.run_until_complete(f)
            expected = pr.transport.get_extra_info('sockname')[1]
            self.assertEqual(port, expected)
            tr.close()

    def test_create_connection_local_addr_in_use(self):
        with test_utils.run_test_server() as httpd:
            f = self.loop.create_connection(
                lambda: MyProto(loop=self.loop),
                *httpd.address, local_addr=httpd.address)
            with self.assertRaises(OSError) as cm:
                self.loop.run_until_complete(f)
            self.assertEqual(cm.exception.errno, errno.EADDRINUSE)
            self.assertIn(str(httpd.address), cm.exception.strerror)

    def test_create_server(self):
        proto = MyProto(self.loop)
        f = self.loop.create_server(lambda: proto, '0.0.0.0', 0)
        server = self.loop.run_until_complete(f)
        self.assertEqual(len(server.sockets), 1)
        sock = server.sockets[0]
        host, port = sock.getsockname()
        self.assertEqual(host, '0.0.0.0')
        client = socket.socket()
        client.connect(('127.0.0.1', port))
        client.sendall(b'xxx')

        self.loop.run_until_complete(proto.connected)
        self.assertEqual('CONNECTED', proto.state)

        test_utils.run_until(self.loop, lambda: proto.nbytes > 0)
        self.assertEqual(3, proto.nbytes)

        # extra info is available
        self.assertIsNotNone(proto.transport.get_extra_info('sockname'))
        self.assertEqual('127.0.0.1',
                         proto.transport.get_extra_info('peername')[0])

        # close connection
        proto.transport.close()
        self.loop.run_until_complete(proto.done)

        self.assertEqual('CLOSED', proto.state)

        # the client socket must be closed after to avoid ECONNRESET upon
        # recv()/send() on the serving socket
        client.close()

        # close server
        server.close()

    def _make_unix_server(self, factory, **kwargs):
        path = test_utils.gen_unix_socket_path()
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))

        f = self.loop.create_unix_server(factory, path, **kwargs)
        server = self.loop.run_until_complete(f)

        return server, path

    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'No UNIX Sockets')
    def test_create_unix_server(self):
        proto = MyProto(loop=self.loop)
        server, path = self._make_unix_server(lambda: proto)
        self.assertEqual(len(server.sockets), 1)

        client = socket.socket(socket.AF_UNIX)
        client.connect(path)
        client.sendall(b'xxx')

        self.loop.run_until_complete(proto.connected)
        self.assertEqual('CONNECTED', proto.state)
        test_utils.run_until(self.loop, lambda: proto.nbytes > 0)
        self.assertEqual(3, proto.nbytes)

        # close connection
        proto.transport.close()
        self.loop.run_until_complete(proto.done)

        self.assertEqual('CLOSED', proto.state)

        # the client socket must be closed after to avoid ECONNRESET upon
        # recv()/send() on the serving socket
        client.close()

        # close server
        server.close()

    def _create_ssl_context(self, certfile, keyfile=None):
        sslcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext.options |= ssl.OP_NO_SSLv2
        sslcontext.load_cert_chain(certfile, keyfile)
        return sslcontext

    def _make_ssl_server(self, factory, certfile, keyfile=None):
        sslcontext = self._create_ssl_context(certfile, keyfile)

        f = self.loop.create_server(factory, '127.0.0.1', 0, ssl=sslcontext)
        server = self.loop.run_until_complete(f)

        sock = server.sockets[0]
        host, port = sock.getsockname()
        self.assertEqual(host, '127.0.0.1')
        return server, host, port

    def _make_ssl_unix_server(self, factory, certfile, keyfile=None):
        sslcontext = self._create_ssl_context(certfile, keyfile)
        return self._make_unix_server(factory, ssl=sslcontext)

    @unittest.skipIf(ssl is None, 'No ssl module')
    def test_create_server_ssl(self):
        proto = MyProto(loop=self.loop)
        server, host, port = self._make_ssl_server(
            lambda: proto, ONLYCERT, ONLYKEY)

        f_c = self.loop.create_connection(MyBaseProto, host, port,
                                          ssl=test_utils.dummy_ssl_context())
        client, pr = self.loop.run_until_complete(f_c)

        client.write(b'xxx')
        self.loop.run_until_complete(proto.connected)
        self.assertEqual('CONNECTED', proto.state)

        test_utils.run_until(self.loop, lambda: proto.nbytes > 0)
        self.assertEqual(3, proto.nbytes)

        # extra info is available
        self.assertIsNotNone(proto.transport.get_extra_info('sockname'))
        self.assertEqual('127.0.0.1',
                         proto.transport.get_extra_info('peername')[0])

        # close connection
        proto.transport.close()
        self.loop.run_until_complete(proto.done)
        self.assertEqual('CLOSED', proto.state)

        # the client socket must be closed after to avoid ECONNRESET upon
        # recv()/send() on the serving socket
        client.close()

        # stop serving
        server.close()

    @unittest.skipIf(ssl is None, 'No ssl module')
    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'No UNIX Sockets')
    def test_create_unix_server_ssl(self):
        proto = MyProto(loop=self.loop)
        server, path = self._make_ssl_unix_server(
            lambda: proto, ONLYCERT, ONLYKEY)

        f_c = self.loop.create_unix_connection(
            MyBaseProto, path, ssl=test_utils.dummy_ssl_context(),
            server_hostname='')

        client, pr = self.loop.run_until_complete(f_c)

        client.write(b'xxx')
        self.loop.run_until_complete(proto.connected)
        self.assertEqual('CONNECTED', proto.state)
        test_utils.run_until(self.loop, lambda: proto.nbytes > 0)
        self.assertEqual(3, proto.nbytes)

        # close connection
        proto.transport.close()
        self.loop.run_until_complete(proto.done)
        self.assertEqual('CLOSED', proto.state)

        # the client socket must be closed after to avoid ECONNRESET upon
        # recv()/send() on the serving socket
        client.close()

        # stop serving
        server.close()

    @unittest.skipIf(ssl is None, 'No ssl module')
    @unittest.skipUnless(HAS_SNI, 'No SNI support in ssl module')
    def test_create_server_ssl_verify_failed(self):
        proto = MyProto(loop=self.loop)
        server, host, port = self._make_ssl_server(
            lambda: proto, SIGNED_CERTFILE)

        sslcontext_client = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext_client.options |= ssl.OP_NO_SSLv2
        sslcontext_client.verify_mode = ssl.CERT_REQUIRED
        if hasattr(sslcontext_client, 'check_hostname'):
            sslcontext_client.check_hostname = True

        # no CA loaded
        f_c = self.loop.create_connection(MyProto, host, port,
                                          ssl=sslcontext_client)
        with self.assertRaisesRegex(ssl.SSLError,
                                    'certificate verify failed '):
            self.loop.run_until_complete(f_c)

        # close connection
        self.assertIsNone(proto.transport)
        server.close()

    @unittest.skipIf(ssl is None, 'No ssl module')
    @unittest.skipUnless(HAS_SNI, 'No SNI support in ssl module')
    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'No UNIX Sockets')
    def test_create_unix_server_ssl_verify_failed(self):
        proto = MyProto(loop=self.loop)
        server, path = self._make_ssl_unix_server(
            lambda: proto, SIGNED_CERTFILE)

        sslcontext_client = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext_client.options |= ssl.OP_NO_SSLv2
        sslcontext_client.verify_mode = ssl.CERT_REQUIRED
        if hasattr(sslcontext_client, 'check_hostname'):
            sslcontext_client.check_hostname = True

        # no CA loaded
        f_c = self.loop.create_unix_connection(MyProto, path,
                                               ssl=sslcontext_client,
                                               server_hostname='invalid')
        with self.assertRaisesRegex(ssl.SSLError,
                                    'certificate verify failed '):
            self.loop.run_until_complete(f_c)

        # close connection
        self.assertIsNone(proto.transport)
        server.close()

    @unittest.skipIf(ssl is None, 'No ssl module')
    @unittest.skipUnless(HAS_SNI, 'No SNI support in ssl module')
    def test_create_server_ssl_match_failed(self):
        proto = MyProto(loop=self.loop)
        server, host, port = self._make_ssl_server(
            lambda: proto, SIGNED_CERTFILE)

        sslcontext_client = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext_client.options |= ssl.OP_NO_SSLv2
        sslcontext_client.verify_mode = ssl.CERT_REQUIRED
        sslcontext_client.load_verify_locations(
            cafile=SIGNING_CA)
        if hasattr(sslcontext_client, 'check_hostname'):
            sslcontext_client.check_hostname = True

        # incorrect server_hostname
        f_c = self.loop.create_connection(MyProto, host, port,
                                          ssl=sslcontext_client)
        with self.assertRaisesRegex(
                ssl.CertificateError,
                "hostname '127.0.0.1' doesn't match 'localhost'"):
            self.loop.run_until_complete(f_c)

        # close connection
        proto.transport.close()
        server.close()

    @unittest.skipIf(ssl is None, 'No ssl module')
    @unittest.skipUnless(HAS_SNI, 'No SNI support in ssl module')
    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'No UNIX Sockets')
    def test_create_unix_server_ssl_verified(self):
        proto = MyProto(loop=self.loop)
        server, path = self._make_ssl_unix_server(
            lambda: proto, SIGNED_CERTFILE)

        sslcontext_client = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext_client.options |= ssl.OP_NO_SSLv2
        sslcontext_client.verify_mode = ssl.CERT_REQUIRED
        sslcontext_client.load_verify_locations(cafile=SIGNING_CA)
        if hasattr(sslcontext_client, 'check_hostname'):
            sslcontext_client.check_hostname = True

        # Connection succeeds with correct CA and server hostname.
        f_c = self.loop.create_unix_connection(MyProto, path,
                                               ssl=sslcontext_client,
                                               server_hostname='localhost')
        client, pr = self.loop.run_until_complete(f_c)

        # close connection
        proto.transport.close()
        client.close()
        server.close()

    @unittest.skipIf(ssl is None, 'No ssl module')
    @unittest.skipUnless(HAS_SNI, 'No SNI support in ssl module')
    def test_create_server_ssl_verified(self):
        proto = MyProto(loop=self.loop)
        server, host, port = self._make_ssl_server(
            lambda: proto, SIGNED_CERTFILE)

        sslcontext_client = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sslcontext_client.options |= ssl.OP_NO_SSLv2
        sslcontext_client.verify_mode = ssl.CERT_REQUIRED
        sslcontext_client.load_verify_locations(cafile=SIGNING_CA)
        if hasattr(sslcontext_client, 'check_hostname'):
            sslcontext_client.check_hostname = True

        # Connection succeeds with correct CA and server hostname.
        f_c = self.loop.create_connection(MyProto, host, port,
                                          ssl=sslcontext_client,
                                          server_hostname='localhost')
        client, pr = self.loop.run_until_complete(f_c)

        # close connection
        proto.transport.close()
        client.close()
        server.close()

    def test_create_server_sock(self):
        proto = asyncio.Future(loop=self.loop)

        class TestMyProto(MyProto):
            def connection_made(self, transport):
                super().connection_made(transport)
                proto.set_result(self)

        sock_ob = socket.socket(type=socket.SOCK_STREAM)
        sock_ob.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_ob.bind(('0.0.0.0', 0))

        f = self.loop.create_server(TestMyProto, sock=sock_ob)
        server = self.loop.run_until_complete(f)
        sock = server.sockets[0]
        self.assertIs(sock, sock_ob)

        host, port = sock.getsockname()
        self.assertEqual(host, '0.0.0.0')
        client = socket.socket()
        client.connect(('127.0.0.1', port))
        client.send(b'xxx')
        client.close()
        server.close()

    def test_create_server_addr_in_use(self):
        sock_ob = socket.socket(type=socket.SOCK_STREAM)
        sock_ob.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_ob.bind(('0.0.0.0', 0))

        f = self.loop.create_server(MyProto, sock=sock_ob)
        server = self.loop.run_until_complete(f)
        sock = server.sockets[0]
        host, port = sock.getsockname()

        f = self.loop.create_server(MyProto, host=host, port=port)
        with self.assertRaises(OSError) as cm:
            self.loop.run_until_complete(f)
        self.assertEqual(cm.exception.errno, errno.EADDRINUSE)

        server.close()

    @unittest.skipUnless(IPV6_ENABLED, 'IPv6 not supported or enabled')
    def test_create_server_dual_stack(self):
        f_proto = asyncio.Future(loop=self.loop)

        class TestMyProto(MyProto):
            def connection_made(self, transport):
                super().connection_made(transport)
                f_proto.set_result(self)

        try_count = 0
        while True:
            try:
                port = find_unused_port()
                f = self.loop.create_server(TestMyProto, host=None, port=port)
                server = self.loop.run_until_complete(f)
            except OSError as ex:
                if ex.errno == errno.EADDRINUSE:
                    try_count += 1
                    self.assertGreaterEqual(5, try_count)
                    continue
                else:
                    raise
            else:
                break
        client = socket.socket()
        client.connect(('127.0.0.1', port))
        client.send(b'xxx')
        proto = self.loop.run_until_complete(f_proto)
        proto.transport.close()
        client.close()

        f_proto = asyncio.Future(loop=self.loop)
        client = socket.socket(socket.AF_INET6)
        client.connect(('::1', port))
        client.send(b'xxx')
        proto = self.loop.run_until_complete(f_proto)
        proto.transport.close()
        client.close()

        server.close()

    def test_server_close(self):
        f = self.loop.create_server(MyProto, '0.0.0.0', 0)
        server = self.loop.run_until_complete(f)
        sock = server.sockets[0]
        host, port = sock.getsockname()

        client = socket.socket()
        client.connect(('127.0.0.1', port))
        client.send(b'xxx')
        client.close()

        server.close()

        client = socket.socket()
        self.assertRaises(
            ConnectionRefusedError, client.connect, ('127.0.0.1', port))
        client.close()

    def test_create_datagram_endpoint(self):
        class TestMyDatagramProto(MyDatagramProto):
            def __init__(inner_self):
                super().__init__(loop=self.loop)

            def datagram_received(self, data, addr):
                super().datagram_received(data, addr)
                self.transport.sendto(b'resp:'+data, addr)

        coro = self.loop.create_datagram_endpoint(
            TestMyDatagramProto, local_addr=('127.0.0.1', 0))
        s_transport, server = self.loop.run_until_complete(coro)
        host, port = s_transport.get_extra_info('sockname')

        coro = self.loop.create_datagram_endpoint(
            lambda: MyDatagramProto(loop=self.loop),
            remote_addr=(host, port))
        transport, client = self.loop.run_until_complete(coro)

        self.assertEqual('INITIALIZED', client.state)
        transport.sendto(b'xxx')
        test_utils.run_until(self.loop, lambda: server.nbytes)
        self.assertEqual(3, server.nbytes)
        test_utils.run_until(self.loop, lambda: client.nbytes)

        # received
        self.assertEqual(8, client.nbytes)

        # extra info is available
        self.assertIsNotNone(transport.get_extra_info('sockname'))

        # close connection
        transport.close()
        self.loop.run_until_complete(client.done)
        self.assertEqual('CLOSED', client.state)
        server.transport.close()

    def test_internal_fds(self):
        loop = self.create_event_loop()
        if not isinstance(loop, selector_events.BaseSelectorEventLoop):
            self.skipTest('loop is not a BaseSelectorEventLoop')

        self.assertEqual(1, loop._internal_fds)
        loop.close()
        self.assertEqual(0, loop._internal_fds)
        self.assertIsNone(loop._csock)
        self.assertIsNone(loop._ssock)

    @unittest.skipUnless(sys.platform != 'win32',
                         "Don't support pipes for Windows")
    def test_read_pipe(self):
        proto = MyReadPipeProto(loop=self.loop)

        rpipe, wpipe = os.pipe()
        pipeobj = io.open(rpipe, 'rb', 1024)

        @asyncio.coroutine
        def connect():
            t, p = yield from self.loop.connect_read_pipe(
                lambda: proto, pipeobj)
            self.assertIs(p, proto)
            self.assertIs(t, proto.transport)
            self.assertEqual(['INITIAL', 'CONNECTED'], proto.state)
            self.assertEqual(0, proto.nbytes)

        self.loop.run_until_complete(connect())

        os.write(wpipe, b'1')
        test_utils.run_until(self.loop, lambda: proto.nbytes >= 1)
        self.assertEqual(1, proto.nbytes)

        os.write(wpipe, b'2345')
        test_utils.run_until(self.loop, lambda: proto.nbytes >= 5)
        self.assertEqual(['INITIAL', 'CONNECTED'], proto.state)
        self.assertEqual(5, proto.nbytes)

        os.close(wpipe)
        self.loop.run_until_complete(proto.done)
        self.assertEqual(
            ['INITIAL', 'CONNECTED', 'EOF', 'CLOSED'], proto.state)
        # extra info is available
        self.assertIsNotNone(proto.transport.get_extra_info('pipe'))

    @unittest.skipUnless(sys.platform != 'win32',
                         "Don't support pipes for Windows")
    # select, poll and kqueue don't support character devices (PTY) on Mac OS X
    # older than 10.6 (Snow Leopard)
    @requires_mac_ver(10, 6)
    # Issue #20495: The test hangs on FreeBSD 7.2 but pass on FreeBSD 9
    @requires_freebsd_version(8)
    def test_read_pty_output(self):
        proto = MyReadPipeProto(loop=self.loop)

        master, slave = os.openpty()
        master_read_obj = io.open(master, 'rb', 0)

        @asyncio.coroutine
        def connect():
            t, p = yield from self.loop.connect_read_pipe(lambda: proto,
                                                          master_read_obj)
            self.assertIs(p, proto)
            self.assertIs(t, proto.transport)
            self.assertEqual(['INITIAL', 'CONNECTED'], proto.state)
            self.assertEqual(0, proto.nbytes)

        self.loop.run_until_complete(connect())

        os.write(slave, b'1')
        test_utils.run_until(self.loop, lambda: proto.nbytes)
        self.assertEqual(1, proto.nbytes)

        os.write(slave, b'2345')
        test_utils.run_until(self.loop, lambda: proto.nbytes >= 5)
        self.assertEqual(['INITIAL', 'CONNECTED'], proto.state)
        self.assertEqual(5, proto.nbytes)

        os.close(slave)
        self.loop.run_until_complete(proto.done)
        self.assertEqual(
            ['INITIAL', 'CONNECTED', 'EOF', 'CLOSED'], proto.state)
        # extra info is available
        self.assertIsNotNone(proto.transport.get_extra_info('pipe'))

    @unittest.skipUnless(sys.platform != 'win32',
                         "Don't support pipes for Windows")
    def test_write_pipe(self):
        rpipe, wpipe = os.pipe()
        pipeobj = io.open(wpipe, 'wb', 1024)

        proto = MyWritePipeProto(loop=self.loop)
        connect = self.loop.connect_write_pipe(lambda: proto, pipeobj)
        transport, p = self.loop.run_until_complete(connect)
        self.assertIs(p, proto)
        self.assertIs(transport, proto.transport)
        self.assertEqual('CONNECTED', proto.state)

        transport.write(b'1')

        data = bytearray()

        def reader(data):
            chunk = os.read(rpipe, 1024)
            data += chunk
            return len(data)

        test_utils.run_until(self.loop, lambda: reader(data) >= 1)
        self.assertEqual(b'1', data)

        transport.write(b'2345')
        test_utils.run_until(self.loop, lambda: reader(data) >= 5)
        self.assertEqual(b'12345', data)
        self.assertEqual('CONNECTED', proto.state)

        os.close(rpipe)

        # extra info is available
        self.assertIsNotNone(proto.transport.get_extra_info('pipe'))

        # close connection
        proto.transport.close()
        self.loop.run_until_complete(proto.done)
        self.assertEqual('CLOSED', proto.state)

    @unittest.skipUnless(sys.platform != 'win32',
                         "Don't support pipes for Windows")
    def test_write_pipe_disconnect_on_close(self):
        rsock, wsock = test_utils.socketpair()
        pipeobj = io.open(wsock.detach(), 'wb', 1024)

        proto = MyWritePipeProto(loop=self.loop)
        connect = self.loop.connect_write_pipe(lambda: proto, pipeobj)
        transport, p = self.loop.run_until_complete(connect)
        self.assertIs(p, proto)
        self.assertIs(transport, proto.transport)
        self.assertEqual('CONNECTED', proto.state)

        transport.write(b'1')
        data = self.loop.run_until_complete(self.loop.sock_recv(rsock, 1024))
        self.assertEqual(b'1', data)

        rsock.close()

        self.loop.run_until_complete(proto.done)
        self.assertEqual('CLOSED', proto.state)

    @unittest.skipUnless(sys.platform != 'win32',
                         "Don't support pipes for Windows")
    # select, poll and kqueue don't support character devices (PTY) on Mac OS X
    # older than 10.6 (Snow Leopard)
    @requires_mac_ver(10, 6)
    def test_write_pty(self):
        master, slave = os.openpty()
        slave_write_obj = io.open(slave, 'wb', 0)

        proto = MyWritePipeProto(loop=self.loop)
        connect = self.loop.connect_write_pipe(lambda: proto, slave_write_obj)
        transport, p = self.loop.run_until_complete(connect)
        self.assertIs(p, proto)
        self.assertIs(transport, proto.transport)
        self.assertEqual('CONNECTED', proto.state)

        transport.write(b'1')

        data = bytearray()

        def reader(data):
            chunk = os.read(master, 1024)
            data += chunk
            return len(data)

        test_utils.run_until(self.loop, lambda: reader(data) >= 1,
                             timeout=10)
        self.assertEqual(b'1', data)

        transport.write(b'2345')
        test_utils.run_until(self.loop, lambda: reader(data) >= 5,
                             timeout=10)
        self.assertEqual(b'12345', data)
        self.assertEqual('CONNECTED', proto.state)

        os.close(master)

        # extra info is available
        self.assertIsNotNone(proto.transport.get_extra_info('pipe'))

        # close connection
        proto.transport.close()
        self.loop.run_until_complete(proto.done)
        self.assertEqual('CLOSED', proto.state)

    def test_prompt_cancellation(self):
        r, w = test_utils.socketpair()
        r.setblocking(False)
        f = self.loop.sock_recv(r, 1)
        ov = getattr(f, 'ov', None)
        if ov is not None:
            self.assertTrue(ov.pending)

        @asyncio.coroutine
        def main():
            try:
                self.loop.call_soon(f.cancel)
                yield from f
            except asyncio.CancelledError:
                res = 'cancelled'
            else:
                res = None
            finally:
                self.loop.stop()
            return res

        start = time.monotonic()
        t = asyncio.Task(main(), loop=self.loop)
        self.loop.run_forever()
        elapsed = time.monotonic() - start

        self.assertLess(elapsed, 0.1)
        self.assertEqual(t.result(), 'cancelled')
        self.assertRaises(asyncio.CancelledError, f.result)
        if ov is not None:
            self.assertFalse(ov.pending)
        self.loop._stop_serving(r)

        r.close()
        w.close()

    def test_timeout_rounding(self):
        def _run_once():
            self.loop._run_once_counter += 1
            orig_run_once()

        orig_run_once = self.loop._run_once
        self.loop._run_once_counter = 0
        self.loop._run_once = _run_once

        @asyncio.coroutine
        def wait():
            loop = self.loop
            yield from asyncio.sleep(1e-2, loop=loop)
            yield from asyncio.sleep(1e-4, loop=loop)
            yield from asyncio.sleep(1e-6, loop=loop)
            yield from asyncio.sleep(1e-8, loop=loop)
            yield from asyncio.sleep(1e-10, loop=loop)

        self.loop.run_until_complete(wait())
        # The ideal number of call is 12, but on some platforms, the selector
        # may sleep at little bit less than timeout depending on the resolution
        # of the clock used by the kernel. Tolerate a few useless calls on
        # these platforms.
        self.assertLessEqual(
            self.loop._run_once_counter, 20,
            {'clock_resolution': self.loop._clock_resolution,
             'selector': self.loop._selector.__class__.__name__})

    def test_sock_connect_address(self):
        addresses = [(socket.AF_INET, ('www.python.org', 80))]
        if IPV6_ENABLED:
            addresses.extend((
                (socket.AF_INET6, ('www.python.org', 80)),
                (socket.AF_INET6, ('www.python.org', 80, 0, 0)),
            ))

        for family, address in addresses:
            for sock_type in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
                sock = socket.socket(family, sock_type)
                with sock:
                    connect = self.loop.sock_connect(sock, address)
                    with self.assertRaises(ValueError) as cm:
                        self.loop.run_until_complete(connect)
                    self.assertIn('address must be resolved',
                                  str(cm.exception))

    def xtest_remove_fds_after_closing(self):
        loop = self.create_event_loop()
        callback = lambda: None
        r, w = test_utils.socketpair()
        self.addCleanup(r.close)
        self.addCleanup(w.close)
        loop.add_reader(r, callback)
        loop.add_writer(w, callback)
        loop.close()
        self.assertFalse(loop.remove_reader(r))
        self.assertFalse(loop.remove_writer(w))

    def xtest_add_fds_after_closing(self):
        loop = self.create_event_loop()
        callback = lambda: None
        r, w = test_utils.socketpair()
        self.addCleanup(r.close)
        self.addCleanup(w.close)
        loop.close()
        with self.assertRaises(RuntimeError):
            loop.add_reader(r, callback)
        with self.assertRaises(RuntimeError):
            loop.add_writer(w, callback)


class SubprocessTestsMixin:

    def check_terminated(self, returncode):
        if sys.platform == 'win32':
            self.assertIsInstance(returncode, int)
            # expect 1 but sometimes get 0
        else:
            self.assertEqual(-signal.SIGTERM, returncode)

    def check_killed(self, returncode):
        if sys.platform == 'win32':
            self.assertIsInstance(returncode, int)
            # expect 1 but sometimes get 0
        else:
            self.assertEqual(-signal.SIGKILL, returncode)

    def test_subprocess_exec(self):
        prog = os.path.join(os.path.dirname(__file__), 'echo.py')

        connect = self.loop.subprocess_exec(
            functools.partial(MySubprocessProtocol, self.loop),
            sys.executable, prog)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)
        self.assertEqual('CONNECTED', proto.state)

        stdin = transp.get_pipe_transport(0)
        stdin.write(b'Python The Winner')
        self.loop.run_until_complete(proto.got_data[1].wait())
        transp.close()
        self.loop.run_until_complete(proto.completed)
        self.check_terminated(proto.returncode)
        self.assertEqual(b'Python The Winner', proto.data[1])

    def test_subprocess_interactive(self):
        prog = os.path.join(os.path.dirname(__file__), 'echo.py')

        connect = self.loop.subprocess_exec(
            functools.partial(MySubprocessProtocol, self.loop),
            sys.executable, prog)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)
        self.assertEqual('CONNECTED', proto.state)

        try:
            stdin = transp.get_pipe_transport(0)
            stdin.write(b'Python ')
            self.loop.run_until_complete(proto.got_data[1].wait())
            proto.got_data[1].clear()
            self.assertEqual(b'Python ', proto.data[1])

            stdin.write(b'The Winner')
            self.loop.run_until_complete(proto.got_data[1].wait())
            self.assertEqual(b'Python The Winner', proto.data[1])
        finally:
            transp.close()

        self.loop.run_until_complete(proto.completed)
        self.check_terminated(proto.returncode)

    def test_subprocess_shell(self):
        connect = self.loop.subprocess_shell(
            functools.partial(MySubprocessProtocol, self.loop),
            'echo Python')
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)

        transp.get_pipe_transport(0).close()
        self.loop.run_until_complete(proto.completed)
        self.assertEqual(0, proto.returncode)
        self.assertTrue(all(f.done() for f in proto.disconnects.values()))
        self.assertEqual(proto.data[1].rstrip(b'\r\n'), b'Python')
        self.assertEqual(proto.data[2], b'')

    def test_subprocess_exitcode(self):
        connect = self.loop.subprocess_shell(
            functools.partial(MySubprocessProtocol, self.loop),
            'exit 7', stdin=None, stdout=None, stderr=None)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.completed)
        self.assertEqual(7, proto.returncode)

    def test_subprocess_close_after_finish(self):
        connect = self.loop.subprocess_shell(
            functools.partial(MySubprocessProtocol, self.loop),
            'exit 7', stdin=None, stdout=None, stderr=None)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.assertIsNone(transp.get_pipe_transport(0))
        self.assertIsNone(transp.get_pipe_transport(1))
        self.assertIsNone(transp.get_pipe_transport(2))
        self.loop.run_until_complete(proto.completed)
        self.assertEqual(7, proto.returncode)
        self.assertIsNone(transp.close())

    def test_subprocess_kill(self):
        prog = os.path.join(os.path.dirname(__file__), 'echo.py')

        connect = self.loop.subprocess_exec(
            functools.partial(MySubprocessProtocol, self.loop),
            sys.executable, prog)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)

        transp.kill()
        self.loop.run_until_complete(proto.completed)
        self.check_killed(proto.returncode)

    def test_subprocess_terminate(self):
        prog = os.path.join(os.path.dirname(__file__), 'echo.py')

        connect = self.loop.subprocess_exec(
            functools.partial(MySubprocessProtocol, self.loop),
            sys.executable, prog)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)

        transp.terminate()
        self.loop.run_until_complete(proto.completed)
        self.check_terminated(proto.returncode)

    @unittest.skipIf(sys.platform == 'win32', "Don't have SIGHUP")
    def test_subprocess_send_signal(self):
        prog = os.path.join(os.path.dirname(__file__), 'echo.py')

        connect = self.loop.subprocess_exec(
            functools.partial(MySubprocessProtocol, self.loop),
            sys.executable, prog)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)

        transp.send_signal(signal.SIGHUP)
        self.loop.run_until_complete(proto.completed)
        self.assertEqual(-signal.SIGHUP, proto.returncode)

    def test_subprocess_stderr(self):
        prog = os.path.join(os.path.dirname(__file__), 'echo2.py')

        connect = self.loop.subprocess_exec(
            functools.partial(MySubprocessProtocol, self.loop),
            sys.executable, prog)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)

        stdin = transp.get_pipe_transport(0)
        stdin.write(b'test')

        self.loop.run_until_complete(proto.completed)

        transp.close()
        self.assertEqual(b'OUT:test', proto.data[1])
        self.assertTrue(proto.data[2].startswith(b'ERR:test'), proto.data[2])
        self.assertEqual(0, proto.returncode)

    def test_subprocess_stderr_redirect_to_stdout(self):
        prog = os.path.join(os.path.dirname(__file__), 'echo2.py')

        connect = self.loop.subprocess_exec(
            functools.partial(MySubprocessProtocol, self.loop),
            sys.executable, prog, stderr=subprocess.STDOUT)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)

        stdin = transp.get_pipe_transport(0)
        self.assertIsNotNone(transp.get_pipe_transport(1))
        self.assertIsNone(transp.get_pipe_transport(2))

        stdin.write(b'test')
        self.loop.run_until_complete(proto.completed)
        self.assertTrue(proto.data[1].startswith(b'OUT:testERR:test'),
                        proto.data[1])
        self.assertEqual(b'', proto.data[2])

        transp.close()
        self.assertEqual(0, proto.returncode)

    def test_subprocess_close_client_stream(self):
        prog = os.path.join(os.path.dirname(__file__), 'echo3.py')

        connect = self.loop.subprocess_exec(
            functools.partial(MySubprocessProtocol, self.loop),
            sys.executable, prog)
        transp, proto = self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.connected)

        stdin = transp.get_pipe_transport(0)
        stdout = transp.get_pipe_transport(1)
        stdin.write(b'test')
        self.loop.run_until_complete(proto.got_data[1].wait())
        self.assertEqual(b'OUT:test', proto.data[1])

        stdout.close()
        self.loop.run_until_complete(proto.disconnects[1])
        stdin.write(b'xxx')
        self.loop.run_until_complete(proto.got_data[2].wait())
        if sys.platform != 'win32':
            self.assertEqual(b'ERR:BrokenPipeError', proto.data[2])
        else:
            # After closing the read-end of a pipe, writing to the
            # write-end using os.write() fails with errno==EINVAL and
            # GetLastError()==ERROR_INVALID_NAME on Windows!?!  (Using
            # WriteFile() we get ERROR_BROKEN_PIPE as expected.)
            self.assertEqual(b'ERR:OSError', proto.data[2])
        transp.close()
        self.loop.run_until_complete(proto.completed)
        self.check_terminated(proto.returncode)

    def test_subprocess_wait_no_same_group(self):
        # start the new process in a new session
        connect = self.loop.subprocess_shell(
            functools.partial(MySubprocessProtocol, self.loop),
            'exit 7', stdin=None, stdout=None, stderr=None,
            start_new_session=True)
        _, proto = yield self.loop.run_until_complete(connect)
        self.assertIsInstance(proto, MySubprocessProtocol)
        self.loop.run_until_complete(proto.completed)
        self.assertEqual(7, proto.returncode)

    def test_subprocess_exec_invalid_args(self):
        @asyncio.coroutine
        def connect(**kwds):
            yield from self.loop.subprocess_exec(
                asyncio.SubprocessProtocol,
                'pwd', **kwds)

        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect(universal_newlines=True))
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect(bufsize=4096))
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect(shell=True))

    def test_subprocess_shell_invalid_args(self):
        @asyncio.coroutine
        def connect(cmd=None, **kwds):
            if not cmd:
                cmd = 'pwd'
            yield from self.loop.subprocess_shell(
                asyncio.SubprocessProtocol,
                cmd, **kwds)

        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect(['ls', '-l']))
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect(universal_newlines=True))
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect(bufsize=4096))
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect(shell=False))


class ZmqSelectorEventLoopTests(EventLoopTestsMixin, unittest.TestCase):

    def create_event_loop(self):
        return aiozmq.ZmqEventLoop()

########NEW FILE########
__FILENAME__ = interface_test
import unittest
import aiozmq


class ZmqTransportTests(unittest.TestCase):

    def test_interface(self):
        tr = aiozmq.ZmqTransport()
        self.assertRaises(NotImplementedError, tr.write, [b'data'])
        self.assertRaises(NotImplementedError, tr.abort)
        self.assertRaises(NotImplementedError, tr.getsockopt, 1)
        self.assertRaises(NotImplementedError, tr.setsockopt, 1, 2)
        self.assertRaises(NotImplementedError, tr.set_write_buffer_limits)
        self.assertRaises(NotImplementedError, tr.get_write_buffer_size)
        self.assertRaises(NotImplementedError, tr.pause_reading)
        self.assertRaises(NotImplementedError, tr.resume_reading)
        self.assertRaises(NotImplementedError, tr.bind, 'endpoint')
        self.assertRaises(NotImplementedError, tr.unbind, 'endpoint')
        self.assertRaises(NotImplementedError, tr.bindings)
        self.assertRaises(NotImplementedError, tr.connect, 'endpoint')
        self.assertRaises(NotImplementedError, tr.disconnect, 'endpoint')
        self.assertRaises(NotImplementedError, tr.connections)
        self.assertRaises(NotImplementedError, tr.subscribe, b'filter')
        self.assertRaises(NotImplementedError, tr.unsubscribe, b'filter')
        self.assertRaises(NotImplementedError, tr.subscriptions)


class ZmqProtocolTests(unittest.TestCase):

    def test_interface(self):
        pr = aiozmq.ZmqProtocol()
        self.assertIsNone(pr.msg_received((b'data',)))

########NEW FILE########
__FILENAME__ = policy_test
import asyncio
import sys
import threading
import unittest
from unittest import mock

import aiozmq


class PolicyTests(unittest.TestCase):

    def setUp(self):
        self.policy = aiozmq.ZmqEventLoopPolicy()

    def test_get_event_loop(self):
        self.assertIsNone(self.policy._local._loop)

        loop = self.policy.get_event_loop()
        self.assertIsInstance(loop, asyncio.AbstractEventLoop)

        self.assertIs(self.policy._local._loop, loop)
        self.assertIs(loop, self.policy.get_event_loop())
        loop.close()

    def test_get_event_loop_calls_set_event_loop(self):
        with mock.patch.object(
                self.policy, "set_event_loop",
                wraps=self.policy.set_event_loop) as m_set_event_loop:

            loop = self.policy.get_event_loop()

            # policy._local._loop must be set through .set_event_loop()
            # (the unix DefaultEventLoopPolicy needs this call to attach
            # the child watcher correctly)
            m_set_event_loop.assert_called_with(loop)

        loop.close()

    def test_get_event_loop_after_set_none(self):
        self.policy.set_event_loop(None)
        self.assertRaises(AssertionError, self.policy.get_event_loop)

    @mock.patch('aiozmq.core.threading.current_thread')
    def test_get_event_loop_thread(self, m_current_thread):

        def f():
            self.assertRaises(AssertionError, self.policy.get_event_loop)

        th = threading.Thread(target=f)
        th.start()
        th.join()

    def test_new_event_loop(self):
        loop = self.policy.new_event_loop()
        self.assertIsInstance(loop, asyncio.AbstractEventLoop)
        loop.close()

    def test_set_event_loop(self):
        old_loop = self.policy.get_event_loop()

        self.assertRaises(AssertionError, self.policy.set_event_loop, object())

        loop = self.policy.new_event_loop()
        self.policy.set_event_loop(loop)
        self.assertIs(loop, self.policy.get_event_loop())
        self.assertIsNot(old_loop, self.policy.get_event_loop())
        loop.close()
        old_loop.close()

    @unittest.skipIf(sys.platform == 'win32',
                     "Windows doesn't support child watchers")
    def test_get_child_watcher(self):
        self.assertIsNone(self.policy._watcher)

        watcher = self.policy.get_child_watcher()
        self.assertIsInstance(watcher, asyncio.SafeChildWatcher)

        self.assertIs(self.policy._watcher, watcher)

        self.assertIs(watcher, self.policy.get_child_watcher())
        self.assertIsNone(watcher._loop)

    @unittest.skipIf(sys.platform == 'win32',
                     "Windows doesn't support child watchers")
    def test_get_child_watcher_after_set(self):
        watcher = asyncio.FastChildWatcher()

        self.policy.set_child_watcher(watcher)
        self.assertIs(self.policy._watcher, watcher)
        self.assertIs(watcher, self.policy.get_child_watcher())

    @unittest.skipIf(sys.platform == 'win32',
                     "Windows doesn't support child watchers")
    def test_get_child_watcher_with_mainloop_existing(self):
        loop = self.policy.get_event_loop()

        self.assertIsNone(self.policy._watcher)
        watcher = self.policy.get_child_watcher()

        self.assertIsInstance(watcher, asyncio.SafeChildWatcher)
        self.assertIs(watcher._loop, loop)

        loop.close()

    @unittest.skipIf(sys.platform == 'win32',
                     "Windows doesn't support child watchers")
    def test_get_child_watcher_thread(self):

        def f():
            self.policy.set_event_loop(self.policy.new_event_loop())

            self.assertIsInstance(self.policy.get_event_loop(),
                                  asyncio.AbstractEventLoop)
            watcher = self.policy.get_child_watcher()

            self.assertIsInstance(watcher, asyncio.SafeChildWatcher)
            self.assertIsNone(watcher._loop)

            self.policy.get_event_loop().close()

        th = threading.Thread(target=f)
        th.start()
        th.join()

    @unittest.skipIf(sys.platform == 'win32',
                     "Windows doesn't support child watchers")
    def test_child_watcher_replace_mainloop_existing(self):
        loop = self.policy.get_event_loop()

        watcher = self.policy.get_child_watcher()

        self.assertIs(watcher._loop, loop)

        new_loop = self.policy.new_event_loop()
        self.policy.set_event_loop(new_loop)

        self.assertIs(watcher._loop, new_loop)

        self.policy.set_event_loop(None)

        self.assertIs(watcher._loop, None)

        loop.close()
        new_loop.close()

    @unittest.skipIf(sys.platform == 'win32',
                     "Windows doesn't support child watchers")
    def test_get_child_watcher_to_override_existing_one(self):
        watcher = asyncio.FastChildWatcher()

        # initializes default watcher as side-effect
        self.policy.get_child_watcher()

        self.policy.set_child_watcher(watcher)
        self.assertIs(self.policy._watcher, watcher)
        self.assertIs(watcher, self.policy.get_child_watcher())

########NEW FILE########
__FILENAME__ = rpc_func_annotations
import unittest
import asyncio

import aiozmq
import aiozmq.rpc
from aiozmq._test_util import find_unused_port


def my_checker(val):
    if isinstance(val, int) or val is None:
        return val
    else:
        raise ValueError('bad value')


class MyHandler(aiozmq.rpc.AttrHandler):

    @aiozmq.rpc.method
    @asyncio.coroutine
    def no_params(self, arg):
        return arg + 1
        yield

    @aiozmq.rpc.method
    @asyncio.coroutine
    def single_param(self, arg: int):
        return arg + 1
        yield

    @aiozmq.rpc.method
    @asyncio.coroutine
    def custom_annotation(self, arg: my_checker):
        return arg
        yield

    @aiozmq.rpc.method
    @asyncio.coroutine
    def ret_annotation(self, arg: int=1) -> float:
        return float(arg)
        yield

    @aiozmq.rpc.method
    @asyncio.coroutine
    def bad_return(self, arg) -> int:
        return arg
        yield

    @aiozmq.rpc.method
    def has_default(self, arg: int=None):
        return arg


class FuncAnnotationsTests(unittest.TestCase):

    def setUp(self):
        self.loop = aiozmq.ZmqEventLoop()
        asyncio.set_event_loop(None)
        self.client = self.server = None

    def tearDown(self):
        if self.client is not None:
            self.close(self.client)
        if self.server is not None:
            self.close(self.server)
        self.loop.close()
        asyncio.set_event_loop(None)

    def close(self, service):
        service.close()
        self.loop.run_until_complete(service.wait_closed())

    def make_rpc_pair(self):
        port = find_unused_port()

        @asyncio.coroutine
        def create():
            server = yield from aiozmq.rpc.serve_rpc(
                MyHandler(),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)

            client = yield from aiozmq.rpc.connect_rpc(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)
            return client, server

        self.client, self.server = self.loop.run_until_complete(create())

        return self.client, self.server

    def test_valid_annotations(self):

        msg = "Expected 'bad_arg' annotation to be callable"
        with self.assertRaisesRegex(ValueError, msg):
            @aiozmq.rpc.method
            def test(good_arg: int, bad_arg: 0):
                pass

        msg = "Expected return annotation to be callable"
        with self.assertRaisesRegex(ValueError, msg):
            @aiozmq.rpc.method
            def test2() -> 'bad annotation':
                pass

    def test_no_params(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.no_params(1)
            self.assertEqual(ret, 2)

        self.loop.run_until_complete(communicate())

    def test_single_param(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.single_param(1)
            self.assertEqual(ret, 2)
            ret = yield from client.call.single_param('1')
            self.assertEqual(ret, 2)
            ret = yield from client.call.single_param(1.0)
            self.assertEqual(ret, 2)

            msg = "Invalid value for argument 'arg'"
            with self.assertRaisesRegex(aiozmq.rpc.ParametersError, msg):
                yield from client.call.single_param('1.0')
            with self.assertRaisesRegex(aiozmq.rpc.ParametersError, msg):
                yield from client.call.single_param('bad value')
            with self.assertRaisesRegex(aiozmq.rpc.ParametersError, msg):
                yield from client.call.single_param({})
            with self.assertRaisesRegex(aiozmq.rpc.ParametersError, msg):
                yield from client.call.single_param(None)

            msg = "TypeError.*'arg' parameter lacking default value"
            with self.assertRaisesRegex(aiozmq.rpc.ParametersError, msg):
                yield from client.call.single_param()
            with self.assertRaisesRegex(aiozmq.rpc.ParametersError, msg):
                yield from client.call.single_param(bad='value')

            msg = "TypeError.*too many keyword arguments"
            with self.assertRaisesRegex(aiozmq.rpc.ParametersError, msg):
                yield from client.call.single_param(1, bad='value')

        self.loop.run_until_complete(communicate())

    def test_custom_annotation(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.custom_annotation(1)
            self.assertEqual(ret, 1)
            ret = yield from client.call.custom_annotation(None)
            self.assertIsNone(ret)

            msg = "Invalid value for argument 'arg': ValueError.*bad value.*"
            with self.assertRaisesRegex(aiozmq.rpc.ParametersError, msg):
                yield from client.call.custom_annotation(1.0)

        self.loop.run_until_complete(communicate())

    def test_ret_annotation(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.ret_annotation(1)
            self.assertEqual(ret, 1.0)
            ret = yield from client.call.ret_annotation('2')
            self.assertEqual(ret, 2.0)

        self.loop.run_until_complete(communicate())

    def test_bad_return(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.bad_return(1)
            self.assertEqual(ret, 1)
            ret = yield from client.call.bad_return(1.2)
            self.assertEqual(ret, 1)
            ret = yield from client.call.bad_return('2')
            self.assertEqual(ret, 2)

            with self.assertRaises(ValueError):
                yield from client.call.bad_return('1.0')
            with self.assertRaises(TypeError):
                yield from client.call.bad_return(None)

        self.loop.run_until_complete(communicate())

    def test_default_value_not_passed_to_annotation(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.has_default(1)
            self.assertEqual(ret, 1)

            ret = yield from client.call.has_default()
            self.assertEqual(ret, None)

            with self.assertRaises(ValueError):
                yield from client.call.has_default(None)

        self.loop.run_until_complete(communicate())

########NEW FILE########
__FILENAME__ = rpc_namespace_test
import unittest
import asyncio
import aiozmq
import aiozmq.rpc

from aiozmq._test_util import find_unused_port


class MyHandler(aiozmq.rpc.AttrHandler):

    @aiozmq.rpc.method
    @asyncio.coroutine
    def func(self, arg):
        return arg + 1
        yield


class RootHandler(aiozmq.rpc.AttrHandler):
    ns = MyHandler()


class RpcNamespaceTests(unittest.TestCase):

    def setUp(self):
        self.loop = aiozmq.ZmqEventLoop()
        asyncio.set_event_loop(None)
        self.client = self.server = None

    def tearDown(self):
        if self.client is not None:
            self.close(self.client)
        if self.server is not None:
            self.close(self.server)
        self.loop.close()
        asyncio.set_event_loop(None)

    def close(self, service):
        service.close()
        self.loop.run_until_complete(service.wait_closed())

    def make_rpc_pair(self):
        port = find_unused_port()

        @asyncio.coroutine
        def create():
            server = yield from aiozmq.rpc.serve_rpc(
                RootHandler(),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)
            client = yield from aiozmq.rpc.connect_rpc(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)
            return client, server

        self.client, self.server = self.loop.run_until_complete(create())

        return self.client, self.server

    def test_ns_func(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.ns.func(1)
            self.assertEqual(2, ret)

        self.loop.run_until_complete(communicate())

    def test_not_found(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaisesRegex(aiozmq.rpc.NotFoundError, 'ns1.func'):
                yield from client.call.ns1.func(1)

        self.loop.run_until_complete(communicate())

    def test_bad_handler(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaisesRegex(aiozmq.rpc.NotFoundError,
                                        'ns.func.foo'):
                yield from client.call.ns.func.foo(1)

        self.loop.run_until_complete(communicate())

    def test_missing_namespace_method(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaisesRegex(aiozmq.rpc.NotFoundError, 'ns'):
                yield from client.call.ns(1)

        self.loop.run_until_complete(communicate())

########NEW FILE########
__FILENAME__ = rpc_packer_test
import unittest
import datetime

from aiozmq.rpc.packer import _Packer

from unittest import mock
from msgpack import ExtType, packb
from pickle import dumps, loads, HIGHEST_PROTOCOL
from functools import partial


class Point:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if isinstance(other, Point):
            return (self.x, self.y) == (other.x, other.y)
        return NotImplemented


class PackerTests(unittest.TestCase):

    def test_packb_simple(self):
        packer = _Packer()
        self.assertEqual(packb('test'), packer.packb('test'))
        self.assertEqual(packb([123]), packer.packb([123]))
        self.assertEqual(packb((123,)), packer.packb([123]))

    def test_unpackb_simple(self):
        packer = _Packer()
        self.assertEqual('test', packer.unpackb(packb('test')))
        self.assertEqual((123,), packer.unpackb(packb([123])))
        self.assertEqual((123,), packer.unpackb(packb((123,))))

    @mock.patch('aiozmq.rpc.packer.ExtType')
    def test_ext_type__date(self, ExtTypeMock):
        packer = _Packer()

        CODE = 127
        dt = datetime.date(2014, 3, 25)
        data = dumps(dt, protocol=HIGHEST_PROTOCOL)

        self.assertEqual(dt, packer.ext_type_unpack_hook(CODE, data))

        packer.ext_type_pack_hook(dt)
        ExtTypeMock.assert_called_once_with(CODE, data)

    @mock.patch('aiozmq.rpc.packer.ExtType')
    def test_ext_type__datetime(self, ExtTypeMock):
        packer = _Packer()

        CODE = 126
        dt = datetime.datetime(2014, 3, 25, 15, 18)
        data = dumps(dt, protocol=HIGHEST_PROTOCOL)

        self.assertEqual(dt, packer.ext_type_unpack_hook(CODE, data))

        packer.ext_type_pack_hook(dt)
        ExtTypeMock.assert_called_once_with(CODE, data)

    @mock.patch('aiozmq.rpc.packer.ExtType')
    def test_ext_type__datetime_tzinfo(self, ExtTypeMock):
        packer = _Packer()

        CODE = 126
        dt = datetime.datetime(2014, 3, 25, 16, 12,
                               tzinfo=datetime.timezone.utc)
        data = dumps(dt, protocol=HIGHEST_PROTOCOL)

        self.assertEqual(dt, packer.ext_type_unpack_hook(CODE, data))

        packer.ext_type_pack_hook(dt)
        ExtTypeMock.assert_called_once_with(CODE, data)

    @mock.patch('aiozmq.rpc.packer.ExtType')
    def test_ext_type__time(self, ExtTypeMock):
        packer = _Packer()

        CODE = 125
        tm = datetime.time(15, 51, 0)
        data = dumps(tm, protocol=HIGHEST_PROTOCOL)

        self.assertEqual(tm, packer.ext_type_unpack_hook(CODE, data))

        packer.ext_type_pack_hook(tm)
        ExtTypeMock.assert_called_once_with(CODE, data)

    @mock.patch('aiozmq.rpc.packer.ExtType')
    def test_ext_type__time_tzinfo(self, ExtTypeMock):
        packer = _Packer()

        CODE = 125
        tm = datetime.time(15, 51, 0, tzinfo=datetime.timezone.utc)
        data = dumps(tm, protocol=HIGHEST_PROTOCOL)

        self.assertEqual(tm, packer.ext_type_unpack_hook(CODE, data))

        packer.ext_type_pack_hook(tm)
        ExtTypeMock.assert_called_once_with(CODE, data)

    @mock.patch('aiozmq.rpc.packer.ExtType')
    def test_ext_type__timedelta(self, ExtTypeMock):
        packer = _Packer()

        CODE = 124
        td = datetime.timedelta(days=1, hours=2, minutes=3, seconds=4)
        data = dumps(td, protocol=HIGHEST_PROTOCOL)

        self.assertEqual(td, packer.ext_type_unpack_hook(CODE, data))

        packer.ext_type_pack_hook(td)
        ExtTypeMock.assert_called_once_with(CODE, data)

    @mock.patch('aiozmq.rpc.packer.ExtType')
    def test_ext_type__tzinfo(self, ExtTypeMock):
        packer = _Packer()

        CODE = 123
        tz = datetime.timezone.utc
        data = dumps(tz, protocol=HIGHEST_PROTOCOL)

        self.assertEqual(tz, packer.ext_type_unpack_hook(CODE, data))

        packer.ext_type_pack_hook(tz)
        ExtTypeMock.assert_called_once_with(CODE, data)

    def test_ext_type_errors(self):
        packer = _Packer()

        with self.assertRaisesRegex(TypeError, "Unknown type: "):
            packer.ext_type_pack_hook(packer)
        self.assertIn(_Packer, packer._pack_cache)
        self.assertIsNone(packer._pack_cache[_Packer])
        # lets try again just for good coverage
        with self.assertRaisesRegex(TypeError, "Unknown type: "):
            packer.ext_type_pack_hook(packer)

        self.assertEqual(ExtType(1, b''), packer.ext_type_unpack_hook(1, b''))

        # TODO: should be more specific errors
        with self.assertRaises(Exception):
            packer.ext_type_unpack_hook(127, b'bad data')

    def test_simple_translators(self):
        translation_table = {
            0: (Point, partial(dumps, protocol=HIGHEST_PROTOCOL), loads),
        }
        packer = _Packer(translation_table=translation_table)

        pt = Point(1, 2)
        data = dumps(pt, protocol=HIGHEST_PROTOCOL)

        self.assertEqual(pt, packer.unpackb(packer.packb(pt)))
        self.assertEqual(ExtType(0, data), packer.ext_type_pack_hook(pt))

        self.assertEqual(pt, packer.ext_type_unpack_hook(0, data))

    def test_override_translators(self):
        translation_table = {
            125: (Point, partial(dumps, protocol=HIGHEST_PROTOCOL), loads),
        }
        packer = _Packer(translation_table=translation_table)

        pt = Point(3, 4)
        data = dumps(pt, protocol=HIGHEST_PROTOCOL)

        dt = datetime.time(15, 2)

        self.assertEqual(ExtType(125, data), packer.ext_type_pack_hook(pt))
        with self.assertRaisesRegex(TypeError, "Unknown type: "):
            packer.ext_type_pack_hook(dt)

########NEW FILE########
__FILENAME__ = rpc_pipeline_test
import unittest
import asyncio
import aiozmq
import aiozmq.rpc
import logging

from unittest import mock
from asyncio.test_utils import run_briefly
from aiozmq._test_util import log_hook


class MyHandler(aiozmq.rpc.AttrHandler):

    def __init__(self, queue, loop):
        self.queue = queue
        self.loop = loop

    @asyncio.coroutine
    @aiozmq.rpc.method
    def coro(self, arg):
        yield from self.queue.put(arg)

    @aiozmq.rpc.method
    def func(self, arg):
        self.queue.put_nowait(arg)

    @asyncio.coroutine
    @aiozmq.rpc.method
    def add(self, arg: int=1):
        yield from self.queue.put(arg + 1)

    @aiozmq.rpc.method
    def func_error(self):
        raise ValueError

    @aiozmq.rpc.method
    def suspicious(self, arg: int):
        self.queue.put_nowait(arg)
        return 3

    @aiozmq.rpc.method
    @asyncio.coroutine
    def fut(self):
        f = asyncio.Future(loop=self.loop)
        yield from self.queue.put(f)
        yield from f


class PipelineTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        logger = logging.getLogger()
        self.log_level = logger.getEffectiveLevel()
        logger.setLevel(logging.DEBUG)

    @classmethod
    def tearDownClass(self):
        logger = logging.getLogger()
        logger.setLevel(self.log_level)

    def setUp(self):
        self.loop = aiozmq.ZmqEventLoop()
        asyncio.set_event_loop(None)
        self.client = self.server = None
        self.queue = asyncio.Queue(loop=self.loop)
        self.err_queue = asyncio.Queue(loop=self.loop)
        self.loop.set_exception_handler(self.exception_handler)

    def tearDown(self):
        if self.client is not None:
            self.close(self.client)
        if self.server is not None:
            self.close(self.server)
        self.loop.close()
        asyncio.set_event_loop(None)

    def close(self, service):
        service.close()
        self.loop.run_until_complete(service.wait_closed())

    def exception_handler(self, loop, context):
        self.err_queue.put_nowait(context)

    def make_pipeline_pair(self, log_exceptions=False):

        @asyncio.coroutine
        def create():
            server = yield from aiozmq.rpc.serve_pipeline(
                MyHandler(self.queue, self.loop),
                bind='tcp://127.0.0.1:*',
                loop=self.loop,
                log_exceptions=log_exceptions)
            connect = next(iter(server.transport.bindings()))
            client = yield from aiozmq.rpc.connect_pipeline(
                connect=connect,
                loop=self.loop)
            return client, server

        self.client, self.server = self.loop.run_until_complete(create())
        return self.client, self.server

    def test_coro(self):
        client, server = self.make_pipeline_pair()

        @asyncio.coroutine
        def communicate():
            yield from client.notify.coro(1)
            ret = yield from self.queue.get()
            self.assertEqual(1, ret)

            yield from client.notify.coro(2)
            ret = yield from self.queue.get()
            self.assertEqual(2, ret)

        self.loop.run_until_complete(communicate())

    def test_add(self):
        client, server = self.make_pipeline_pair()

        @asyncio.coroutine
        def communicate():
            yield from client.notify.add()
            ret = yield from self.queue.get()
            self.assertEqual(ret, 2)
            yield from client.notify.add(2)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 3)

        self.loop.run_until_complete(communicate())

    def test_bad_handler(self):
        client, server = self.make_pipeline_pair()

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                yield from client.notify.bad_handler()

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.ERROR, ret.levelno)
                self.assertEqual("Call to %r caused error: %r", ret.msg)
                self.assertEqual(('bad_handler', mock.ANY),
                                 ret.args)
                self.assertIsNotNone(ret.exc_info)

        self.loop.run_until_complete(communicate())

    def test_func(self):
        client, server = self.make_pipeline_pair()

        @asyncio.coroutine
        def communicate():
            yield from client.notify.func(123)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 123)

        self.loop.run_until_complete(communicate())

    def test_func_error(self):
        client, server = self.make_pipeline_pair(log_exceptions=True)

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                yield from client.notify.func_error()

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.ERROR, ret.levelno)
                self.assertEqual("An exception from method %r "
                                 "call occurred.\n"
                                 "args = %s\nkwargs = %s\n", ret.msg)
                self.assertEqual(('func_error', '()', '{}'),
                                 ret.args)
                self.assertIsNotNone(ret.exc_info)

        self.loop.run_until_complete(communicate())

    def test_default_event_loop(self):
        asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())

        @asyncio.coroutine
        def create():
            server = yield from aiozmq.rpc.serve_pipeline(
                MyHandler(self.queue, self.loop),
                bind='tcp://127.0.0.1:*',
                loop=None)
            connect = next(iter(server.transport.bindings()))
            client = yield from aiozmq.rpc.connect_pipeline(
                connect=connect,
                loop=None)
            return client, server

        self.loop = loop = asyncio.get_event_loop()
        self.client, self.server = loop.run_until_complete(create())

    def test_warning_if_remote_return_not_None(self):
        client, server = self.make_pipeline_pair()

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                yield from client.notify.suspicious(1)
                ret = yield from self.queue.get()
                self.assertEqual(1, ret)

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.WARNING, ret.levelno)
                self.assertEqual('Pipeline handler %r returned not None',
                                 ret.msg)
                self.assertEqual(('suspicious',), ret.args)
                self.assertIsNone(ret.exc_info)

        self.loop.run_until_complete(communicate())
        run_briefly(self.loop)

    def test_call_closed_pipeline(self):
        client, server = self.make_pipeline_pair()

        @asyncio.coroutine
        def communicate():
            client.close()
            yield from client.wait_closed()
            with self.assertRaises(aiozmq.rpc.ServiceClosedError):
                yield from client.notify.func()

        self.loop.run_until_complete(communicate())

    def test_server_close(self):
        client, server = self.make_pipeline_pair()

        @asyncio.coroutine
        def communicate():
            client.notify.fut()
            fut = yield from self.queue.get()
            self.assertEqual(1, len(server._proto.pending_waiters))
            task = next(iter(server._proto.pending_waiters))
            self.assertIsInstance(task, asyncio.Task)
            server.close()
            yield from server.wait_closed()
            yield from asyncio.sleep(0, loop=self.loop)
            self.assertEqual(0, len(server._proto.pending_waiters))
            fut.cancel()

        self.loop.run_until_complete(communicate())

########NEW FILE########
__FILENAME__ = rpc_pubsub_test
import unittest
import asyncio
import aiozmq
import aiozmq.rpc
import logging

from unittest import mock
from aiozmq._test_util import find_unused_port, log_hook


class MyHandler(aiozmq.rpc.AttrHandler):

    def __init__(self, queue, loop):
        super().__init__()
        self.queue = queue
        self.loop = loop

    @aiozmq.rpc.method
    @asyncio.coroutine
    def start(self):
        yield from self.queue.put('started')

    @aiozmq.rpc.method
    @asyncio.coroutine
    def coro(self, arg):
        yield from self.queue.put(arg)

    @aiozmq.rpc.method
    def func(self, arg: int):
        self.queue.put_nowait(arg + 1)

    @aiozmq.rpc.method
    def func_raise_error(self):
        raise RuntimeError

    @aiozmq.rpc.method
    def suspicious(self, arg: int):
        self.queue.put_nowait(arg + 1)
        return 3

    @aiozmq.rpc.method
    @asyncio.coroutine
    def fut(self):
        f = asyncio.Future(loop=self.loop)
        yield from self.queue.put(f)
        yield from f


class PubSubTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        logger = logging.getLogger()
        self.log_level = logger.getEffectiveLevel()
        logger.setLevel(logging.DEBUG)

    @classmethod
    def tearDownClass(self):
        logger = logging.getLogger()
        logger.setLevel(self.log_level)

    def setUp(self):
        self.loop = aiozmq.ZmqEventLoop()
        asyncio.set_event_loop(None)
        self.client = self.server = None
        self.queue = asyncio.Queue(loop=self.loop)
        self.err_queue = asyncio.Queue(loop=self.loop)

    def tearDown(self):
        if self.client:
            self.close(self.client)
        if self.server:
            self.close(self.server)
        self.loop.close()
        asyncio.set_event_loop(None)

    def close(self, service):
        service.close()
        self.loop.run_until_complete(service.wait_closed())

    def make_pubsub_pair(self, subscribe=None, log_exceptions=False):

        @asyncio.coroutine
        def create():
            server = yield from aiozmq.rpc.serve_pubsub(
                MyHandler(self.queue, self.loop),
                subscribe=subscribe,
                bind='tcp://127.0.0.1:*',
                loop=self.loop,
                log_exceptions=log_exceptions)
            connect = next(iter(server.transport.bindings()))
            client = yield from aiozmq.rpc.connect_pubsub(
                connect=connect,
                loop=self.loop)

            if subscribe is not None:
                if not isinstance(subscribe, (str, bytes)):
                    pub = subscribe[0]
                else:
                    pub = subscribe
                for i in range(3):
                    try:
                        yield from client.publish(pub).start()
                        ret = yield from asyncio.wait_for(self.queue.get(),
                                                          0.1, loop=self.loop)
                        self.assertEqual(ret, 'started')
                        break
                    except asyncio.TimeoutError:
                        self.assertLess(i, 3)
                else:
                    self.fail('Cannot connect')
            return client, server

        self.client, self.server = self.loop.run_until_complete(create())
        return self.client, self.server

    def test_coro(self):
        client, server = self.make_pubsub_pair('my-topic')

        @asyncio.coroutine
        def communicate():
            yield from client.publish('my-topic').coro(1)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 1)

            yield from client.publish('other-topic').coro(1)
            self.assertTrue(self.queue.empty())

        self.loop.run_until_complete(communicate())

    def test_coro__multiple_topics(self):
        client, server = self.make_pubsub_pair(('topic1', 'topic2'))

        @asyncio.coroutine
        def communicate():
            yield from client.publish('topic1').coro(1)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 1)

            yield from client.publish('topic2').coro(1)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 1)

        self.loop.run_until_complete(communicate())

    def test_coro__subscribe_to_all(self):
        client, server = self.make_pubsub_pair('')

        @asyncio.coroutine
        def communicate():
            yield from client.publish('sometopic').coro(123)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 123)

            yield from client.publish(None).coro('abc')
            ret = yield from self.queue.get()
            self.assertEqual(ret, 'abc')

            yield from client.publish('').coro(1)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 1)

        self.loop.run_until_complete(communicate())

    def test_call_error(self):
        client, server = self.make_pubsub_pair()

        with self.assertRaisesRegex(ValueError, "PubSub method name is empty"):
            client.publish('topic')()

    def test_not_found(self):
        client, server = self.make_pubsub_pair('my-topic')

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                yield from client.publish('my-topic').bad.method(1, 2)

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.ERROR, ret.levelno)
                self.assertEqual("Call to %r caused error: %r", ret.msg)
                self.assertEqual(('bad.method', mock.ANY),
                                 ret.args)
                self.assertIsNotNone(ret.exc_info)

        self.loop.run_until_complete(communicate())

    def test_func(self):
        client, server = self.make_pubsub_pair('my-topic')

        @asyncio.coroutine
        def communicate():
            yield from client.publish('my-topic').func(1)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 2)

        self.loop.run_until_complete(communicate())

    def test_func__arg_error(self):
        client, server = self.make_pubsub_pair('my-topic')

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                yield from client.publish('my-topic').func('abc')

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.ERROR, ret.levelno)
                self.assertEqual("Call to %r caused error: %r", ret.msg)
                self.assertEqual(('func', mock.ANY),
                                 ret.args)
                self.assertIsNotNone(ret.exc_info)

                self.assertTrue(self.queue.empty())

        self.loop.run_until_complete(communicate())

    def test_func_raises_error(self):
        client, server = self.make_pubsub_pair('my-topic', log_exceptions=True)

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                yield from client.publish('my-topic').func_raise_error()

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.ERROR, ret.levelno)
                self.assertEqual('An exception from method %r call occurred.\n'
                                 'args = %s\nkwargs = %s\n', ret.msg)
                self.assertEqual(('func_raise_error', '()', '{}'),
                                 ret.args)
                self.assertIsNotNone(ret.exc_info)

        self.loop.run_until_complete(communicate())

    def test_subscribe_to_bytes(self):
        client, server = self.make_pubsub_pair(b'my-topic')

        @asyncio.coroutine
        def communicate():
            yield from client.publish(b'my-topic').func(1)
            ret = yield from self.queue.get()
            self.assertEqual(ret, 2)

        self.loop.run_until_complete(communicate())

    def test_subscribe_to_invalid(self):
        @asyncio.coroutine
        def go():
            server = yield from aiozmq.rpc.serve_pubsub(
                MyHandler(self.queue, self.loop),
                bind='tcp://127.0.0.1:*',
                loop=self.loop)
            self.assertRaises(TypeError, server.subscribe, 123)

        self.loop.run_until_complete(go())

    def test_unsubscribe(self):
        @asyncio.coroutine
        def go():
            server = yield from aiozmq.rpc.serve_pubsub(
                MyHandler(self.queue, self.loop),
                bind='tcp://127.0.0.1:*',
                loop=self.loop)
            self.assertRaises(TypeError, server.subscribe, 123)

            server.subscribe('topic')
            server.unsubscribe('topic')
            self.assertNotIn('topic', server.transport.subscriptions())

            server.subscribe(b'btopic')
            server.unsubscribe(b'btopic')
            self.assertNotIn(b'btopic', server.transport.subscriptions())

            self.assertRaises(TypeError, server.unsubscribe, 123)

        self.loop.run_until_complete(go())

    def test_default_event_loop(self):
        port = find_unused_port()

        asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
        queue = asyncio.Queue()

        @asyncio.coroutine
        def create():
            server = yield from aiozmq.rpc.serve_pubsub(
                MyHandler(queue, self.loop),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=None,
                subscribe='topic')
            client = yield from aiozmq.rpc.connect_pubsub(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=None)
            return client, server

        self.loop = loop = asyncio.get_event_loop()
        self.client, self.server = loop.run_until_complete(create())

        @asyncio.coroutine
        def communicate():
            for i in range(3):
                try:
                    yield from self.client.publish('topic').start()
                    ret = yield from asyncio.wait_for(queue.get(),
                                                      0.1)
                    self.assertEqual(ret, 'started')
                    break
                except asyncio.TimeoutError:
                    self.assertLess(i, 3)
            else:
                self.fail('Cannot connect')

            yield from self.client.publish('topic').func(1)
            ret = yield from queue.get()
            self.assertEqual(2, ret)

        loop.run_until_complete(communicate())

    def test_serve_bad_subscription(self):
        port = find_unused_port()

        @asyncio.coroutine
        def create():
            with self.assertRaises(TypeError):
                yield from aiozmq.rpc.serve_pubsub(
                    {},
                    bind='tcp://127.0.0.1:{}'.format(port),
                    loop=self.loop,
                    subscribe=123)

        self.loop.run_until_complete(create())

    def test_publish_to_invalid_topic(self):
        client, server = self.make_pubsub_pair('')

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(TypeError):
                yield from client.publish(123).coro(123)

        self.loop.run_until_complete(communicate())

    def test_warning_if_remote_return_not_None(self):
        client, server = self.make_pubsub_pair('topic')

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                yield from client.publish('topic').suspicious(1)
                ret = yield from self.queue.get()
                self.assertEqual(2, ret)

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.WARNING, ret.levelno)
                self.assertEqual('PubSub handler %r returned not None',
                                 ret.msg)
                self.assertEqual(('suspicious',), ret.args)
                self.assertIsNone(ret.exc_info)

        self.loop.run_until_complete(communicate())

    def test_call_closed_pubsub(self):
        client, server = self.make_pubsub_pair()

        @asyncio.coroutine
        def communicate():
            client.close()
            yield from client.wait_closed()
            with self.assertRaises(aiozmq.rpc.ServiceClosedError):
                yield from client.publish('ab').func()

        self.loop.run_until_complete(communicate())

    def test_server_close(self):
        client, server = self.make_pubsub_pair('my-topic')

        @asyncio.coroutine
        def communicate():
            client.publish('my-topic').fut()
            fut = yield from self.queue.get()
            self.assertEqual(1, len(server._proto.pending_waiters))
            task = next(iter(server._proto.pending_waiters))
            self.assertIsInstance(task, asyncio.Task)
            server.close()
            yield from server.wait_closed()
            yield from asyncio.sleep(0, loop=self.loop)
            self.assertEqual(0, len(server._proto.pending_waiters))
            fut.cancel()

        self.loop.run_until_complete(communicate())

########NEW FILE########
__FILENAME__ = rpc_test
import unittest
import asyncio
import aiozmq
import aiozmq.rpc
import datetime
import logging
import time
from unittest import mock
import zmq
import msgpack
import struct

from aiozmq._test_util import find_unused_port, log_hook
from aiozmq.rpc.log import logger


class MyException(Exception):
    pass


class MyHandler(aiozmq.rpc.AttrHandler):

    def __init__(self, loop):
        self.loop = loop

    @aiozmq.rpc.method
    def func(self, arg):
        return arg + 1

    @aiozmq.rpc.method
    @asyncio.coroutine
    def coro(self, arg):
        return arg + 1
        yield

    @aiozmq.rpc.method
    def exc(self, arg):
        raise RuntimeError("bad arg", arg)

    @aiozmq.rpc.method
    @asyncio.coroutine
    def exc_coro(self, arg):
        raise RuntimeError("bad arg 2", arg)
        yield

    @aiozmq.rpc.method
    def add(self, a1, a2):
        return a1 + a2

    @aiozmq.rpc.method
    def generic_exception(self):
        raise MyException('additional', 'data')

    @aiozmq.rpc.method
    @asyncio.coroutine
    def slow_call(self):
        yield from asyncio.sleep(0.2, loop=self.loop)

    @aiozmq.rpc.method
    @asyncio.coroutine
    def fut(self):
        return asyncio.Future(loop=self.loop)

    @aiozmq.rpc.method
    @asyncio.coroutine
    def cancelled_fut(self):
        ret = asyncio.Future(loop=self.loop)
        ret.cancel()
        return ret


class Protocol(aiozmq.ZmqProtocol):

    def __init__(self, loop):
        self.transport = None
        self.connected = asyncio.Future(loop=loop)
        self.closed = asyncio.Future(loop=loop)
        self.state = 'INITIAL'
        self.received = asyncio.Queue(loop=loop)

    def connection_made(self, transport):
        self.transport = transport
        assert self.state == 'INITIAL', self.state
        self.state = 'CONNECTED'
        self.connected.set_result(None)

    def connection_lost(self, exc):
        assert self.state == 'CONNECTED', self.state
        self.state = 'CLOSED'
        self.closed.set_result(None)
        self.transport = None

    def pause_writing(self):
        pass

    def resume_writing(self):
        pass

    def msg_received(self, data):
        assert isinstance(data, tuple), data
        assert self.state == 'CONNECTED', self.state
        self.received.put_nowait(data)


class RpcTests(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        root_logger = logging.getLogger()
        self.log_level = logger.getEffectiveLevel()
        root_logger.setLevel(logging.DEBUG)

    @classmethod
    def tearDownClass(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

    def setUp(self):
        self.loop = aiozmq.ZmqEventLoop()
        asyncio.set_event_loop(None)
        self.client = self.server = None
        self.err_queue = asyncio.Queue(loop=self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)

    def close(self, server):
        server.close()
        self.loop.run_until_complete(server.wait_closed())

    def make_rpc_pair(self, *, error_table=None, timeout=None,
                      log_exceptions=False):
        @asyncio.coroutine
        def create():
            port = find_unused_port()
            server = yield from aiozmq.rpc.serve_rpc(
                MyHandler(self.loop),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop,
                log_exceptions=log_exceptions)
            client = yield from aiozmq.rpc.connect_rpc(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop, error_table=error_table, timeout=timeout)

            return client, server

        self.client, self.server = self.loop.run_until_complete(create())

        return self.client, self.server

    def test_func(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.func(1)
            self.assertEqual(2, ret)
            client.close()
            yield from client.wait_closed()

        self.loop.run_until_complete(communicate())

    def test_exc(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(RuntimeError) as exc:
                yield from client.call.exc(1)
            self.assertEqual(('bad arg', 1), exc.exception.args)

        self.loop.run_until_complete(communicate())

    def test_not_found(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(aiozmq.rpc.NotFoundError) as exc:
                yield from client.call.unknown_method(1, 2, 3)
            self.assertEqual(('unknown_method',), exc.exception.args)

        self.loop.run_until_complete(communicate())

    def test_coro(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.coro(2)
            self.assertEqual(3, ret)

        self.loop.run_until_complete(communicate())

    def test_exc_coro(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(RuntimeError) as exc:
                yield from client.call.exc_coro(1)
            self.assertEqual(('bad arg 2', 1), exc.exception.args)

        self.loop.run_until_complete(communicate())

    def test_datetime_translators(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.add(datetime.date(2014, 3, 21),
                                             datetime.timedelta(days=2))
            self.assertEqual(datetime.date(2014, 3, 23), ret)

        self.loop.run_until_complete(communicate())

    def test_not_found_empty_name(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(ValueError) as exc:
                yield from client.call(1, 2, 3)
            self.assertEqual(('RPC method name is empty',), exc.exception.args)

        self.loop.run_until_complete(communicate())

    def test_not_found_empty_name_on_server(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(aiozmq.rpc.NotFoundError) as exc:
                yield from client._proto.call('', (), {})
            self.assertEqual(('',), exc.exception.args)

        self.loop.run_until_complete(communicate())

    def test_generic_exception(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(aiozmq.rpc.GenericError) as exc:
                yield from client.call.generic_exception()
            self.assertEqual(('rpc_test.MyException',
                              ('additional', 'data'),
                              "MyException('additional', 'data')"),
                             exc.exception.args)
            self.assertEqual("<Generic RPC Error "
                             "rpc_test.MyException('additional', 'data'): "
                             "MyException('additional', 'data')>",
                             repr(exc.exception))

        self.loop.run_until_complete(communicate())

    def test_exception_translator(self):
        client, server = self.make_rpc_pair(
            error_table={__name__+'.MyException': MyException})

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(MyException) as exc:
                yield from client.call.generic_exception()
            self.assertEqual(('additional', 'data'), exc.exception.args)

        self.loop.run_until_complete(communicate())

    def test_default_event_loop(self):
        asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())

        @asyncio.coroutine
        def create():
            port = find_unused_port()
            server = yield from aiozmq.rpc.serve_rpc(
                MyHandler(self.loop),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=None)
            client = yield from aiozmq.rpc.connect_rpc(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=None)
            return client, server

        self.loop = loop = asyncio.get_event_loop()
        self.client, self.server = loop.run_until_complete(create())

        @asyncio.coroutine
        def communicate():
            ret = yield from self.client.call.func(1)
            self.assertEqual(2, ret)

        loop.run_until_complete(communicate())

    def test_service_transport(self):
        client, server = self.make_rpc_pair()

        self.assertIsInstance(client.transport, aiozmq.ZmqTransport)
        self.assertIsInstance(server.transport, aiozmq.ZmqTransport)

        client.close()
        self.loop.run_until_complete(client.wait_closed())
        with self.assertRaises(aiozmq.rpc.ServiceClosedError):
            client.transport

        server.close()
        self.loop.run_until_complete(server.wait_closed())
        with self.assertRaises(aiozmq.rpc.ServiceClosedError):
            server.transport

    def test_client_timeout(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                with self.assertRaises(asyncio.TimeoutError):
                    with client.with_timeout(0.1) as timedout:
                        yield from timedout.call.slow_call()

                t0 = time.monotonic()
                with self.assertRaises(asyncio.TimeoutError):
                    yield from client.with_timeout(0.1).call.slow_call()
                t1 = time.monotonic()
                self.assertTrue(0.08 <= t1-t0 <= 0.12, t1-t0)

                ret = yield from self.err_queue.get()
                # TODO: make a test for several unexpected calls
                # This test should to do that but result is a bit suspicious
                # self.assertEqual(1, self.err_queue.qsize())
                self.assertEqual(logging.DEBUG, ret.levelno)
                self.assertEqual("The future for request #%08x "
                                 "has been cancelled, "
                                 "skip the received result.", ret.msg)
                self.assertEqual((1,), ret.args)
                self.assertIsNone(ret.exc_info)

        self.loop.run_until_complete(communicate())

    def test_client_override_global_timeout(self):
        client, server = self.make_rpc_pair(timeout=10)

        @asyncio.coroutine
        def communicate():
            with self.assertRaises(asyncio.TimeoutError):
                with client.with_timeout(0.1) as timedout:
                    yield from timedout.call.slow_call()

            t0 = time.monotonic()
            with self.assertRaises(asyncio.TimeoutError):
                yield from client.with_timeout(0.1).call.slow_call()
            t1 = time.monotonic()
            self.assertTrue(0.08 <= t1-t0 <= 0.12, t1-t0)
            server.close()
            client.close()
            yield from asyncio.gather(server.wait_closed(),
                                      client.wait_closed(),
                                      loop=self.loop)

        self.loop.run_until_complete(communicate())

    def test_type_of_handler(self):

        @asyncio.coroutine
        def go():
            with self.assertRaises(TypeError):
                yield from aiozmq.rpc.serve_rpc(
                    "Bad Handler",
                    bind='tcp://127.0.0.1:*',
                    loop=self.loop)

        self.loop.run_until_complete(go())

    def test_unknown_format_at_server(self):
        @asyncio.coroutine
        def go():
            port = find_unused_port()
            server = yield from aiozmq.rpc.serve_rpc(
                MyHandler(self.loop),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop), zmq.DEALER,
                connect='tcp://127.0.0.1:{}'.format(port))

            yield from asyncio.sleep(0.001, loop=self.loop)

            with log_hook('aiozmq.rpc', self.err_queue):
                tr.write([b'invalid', b'structure'])

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.CRITICAL, ret.levelno)
                self.assertEqual("Cannot unpack %r", ret.msg)
                self.assertEqual(([mock.ANY, b'invalid', b'structure'],),
                                 ret.args)
                self.assertIsNotNone(ret.exc_info)

            self.assertTrue(pr.received.empty())
            server.close()

        self.loop.run_until_complete(go())

    def test_malformed_args(self):
        @asyncio.coroutine
        def go():
            port = find_unused_port()
            server = yield from aiozmq.rpc.serve_rpc(
                MyHandler(self.loop),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop), zmq.DEALER,
                connect='tcp://127.0.0.1:{}'.format(port))

            with log_hook('aiozmq.rpc', self.err_queue):
                tr.write([struct.pack('=HHLd', 1, 2, 3, 4),
                          b'bad args', b'bad_kwargs'])

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.CRITICAL, ret.levelno)
                self.assertEqual("Cannot unpack %r", ret.msg)
                self.assertEqual(
                    ([mock.ANY, mock.ANY, b'bad args', b'bad_kwargs'],),
                    ret.args)
                self.assertIsNotNone(ret.exc_info)

            self.assertTrue(pr.received.empty())
            server.close()

        self.loop.run_until_complete(go())

    def test_malformed_kwargs(self):
        @asyncio.coroutine
        def go():
            port = find_unused_port()
            server = yield from aiozmq.rpc.serve_rpc(
                MyHandler(self.loop),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop), zmq.DEALER,
                connect='tcp://127.0.0.1:{}'.format(port))

            with log_hook('aiozmq.rpc', self.err_queue):
                tr.write([struct.pack('=HHLd', 1, 2, 3, 4),
                          msgpack.packb((1, 2)), b'bad_kwargs'])

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.CRITICAL, ret.levelno)
                self.assertEqual("Cannot unpack %r", ret.msg)
                self.assertEqual(
                    ([mock.ANY, mock.ANY, mock.ANY, b'bad_kwargs'],),
                    ret.args)
                self.assertIsNotNone(ret.exc_info)

            self.assertTrue(pr.received.empty())
            server.close()

        self.loop.run_until_complete(go())

    def test_unknown_format_at_client(self):
        @asyncio.coroutine
        def go():
            port = find_unused_port()
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop), zmq.DEALER,
                bind='tcp://127.0.0.1:{}'.format(port))

            client = yield from aiozmq.rpc.connect_rpc(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)

            with log_hook('aiozmq.rpc', self.err_queue):
                tr.write([b'invalid', b'structure'])

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.CRITICAL, ret.levelno)
                self.assertEqual("Cannot unpack %r", ret.msg)
                self.assertEqual(
                    ([b'invalid', b'structure'],),
                    ret.args)
                self.assertIsNotNone(ret.exc_info)

            client.close()

        self.loop.run_until_complete(go())

    def test_malformed_answer_at_client(self):
        @asyncio.coroutine
        def go():
            port = find_unused_port()

            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop), zmq.DEALER,
                bind='tcp://127.0.0.1:{}'.format(port))

            client = yield from aiozmq.rpc.connect_rpc(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)

            with log_hook('aiozmq.rpc', self.err_queue):
                tr.write([struct.pack('=HHLd?', 1, 2, 3, 4, True),
                          b'bad_answer'])

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.CRITICAL, ret.levelno)
                self.assertEqual("Cannot unpack %r", ret.msg)
                self.assertEqual(
                    ([mock.ANY, b'bad_answer'],),
                    ret.args)
                self.assertIsNotNone(ret.exc_info)

            client.close()
            tr.close()

        self.loop.run_until_complete(go())

    def test_unknown_req_id_at_client(self):
        @asyncio.coroutine
        def go():
            port = find_unused_port()
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop), zmq.DEALER,
                bind='tcp://127.0.0.1:{}'.format(port))

            client = yield from aiozmq.rpc.connect_rpc(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop)

            with log_hook('aiozmq.rpc', self.err_queue):
                tr.write([struct.pack('=HHLd?', 1, 2, 34435, 4, True),
                          msgpack.packb((1, 2))])

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.CRITICAL, ret.levelno)
                self.assertEqual("Unknown answer id: %d (%d %d %f %d) -> %s",
                                 ret.msg)
                self.assertEqual(
                    (mock.ANY, 1, 2, 4.0, True, (1, 2)),
                    ret.args)
                self.assertIsNone(ret.exc_info)

            client.close()

        self.loop.run_until_complete(go())

    def test_overflow_client_counter(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            client._proto.counter = 0xffffffff
            ret = yield from client.call.func(1)
            self.assertEqual(2, ret)
            self.assertEqual(0, client._proto.counter)
            client.close()
            yield from client.wait_closed()
            server.close()

        self.loop.run_until_complete(communicate())

    def test_log_exceptions(self):
        client, server = self.make_rpc_pair(log_exceptions=True)

        @asyncio.coroutine
        def communicate():
            with log_hook('aiozmq.rpc', self.err_queue):
                with self.assertRaises(RuntimeError) as exc:
                    yield from client.call.exc(1)
                self.assertEqual(('bad arg', 1), exc.exception.args)

                ret = yield from self.err_queue.get()
                self.assertEqual(logging.ERROR, ret.levelno)
                self.assertEqual('An exception from method %r '
                                 'call occurred.\n'
                                 'args = %s\nkwargs = %s\n', ret.msg)
                self.assertEqual(
                    ('exc', '(1,)', '{}'),
                    ret.args)
                self.assertIsNotNone(ret.exc_info)

        self.loop.run_until_complete(communicate())

    def test_call_closed_rpc(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            client.close()
            yield from client.wait_closed()
            with self.assertRaises(aiozmq.rpc.ServiceClosedError):
                yield from client.call.func()

        self.loop.run_until_complete(communicate())

    def test_call_closed_rpc_cancelled(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            server.close()
            waiter = client.call.func()
            server.close()
            yield from server.wait_closed()
            client.close()
            yield from client.wait_closed()
            with self.assertRaises(asyncio.CancelledError):
                yield from waiter

        self.loop.run_until_complete(communicate())

    def test_server_close(self):
        client, server = self.make_rpc_pair()

        @asyncio.coroutine
        def communicate():
            waiter = client.call.fut()
            yield from asyncio.sleep(0.01, loop=self.loop)
            self.assertEqual(1, len(server._proto.pending_waiters))
            task = next(iter(server._proto.pending_waiters))
            self.assertIsInstance(task, asyncio.Task)
            server.close()
            yield from server.wait_closed()
            yield from asyncio.sleep(0.01, loop=self.loop)
            self.assertEqual(0, len(server._proto.pending_waiters))
            del waiter

        self.loop.run_until_complete(communicate())


class AbstractHandlerTests(unittest.TestCase):

    def test___getitem__(self):

        class MyHandler(aiozmq.rpc.AbstractHandler):

            def __getitem__(self, key):
                return super().__getitem__(key)

        with self.assertRaises(KeyError):
            MyHandler()[1]

    def test_subclass(self):
        self.assertTrue(issubclass(dict, aiozmq.rpc.AbstractHandler))
        self.assertIsInstance({}, aiozmq.rpc.AbstractHandler)
        self.assertFalse(issubclass(object, aiozmq.rpc.AbstractHandler))
        self.assertNotIsInstance(object(), aiozmq.rpc.AbstractHandler)
        self.assertNotIsInstance('string', aiozmq.rpc.AbstractHandler)
        self.assertNotIsInstance(b'bytes', aiozmq.rpc.AbstractHandler)


class TestLogger(unittest.TestCase):

    def test_logger_name(self):
        self.assertEqual('aiozmq.rpc', logger.name)

########NEW FILE########
__FILENAME__ = rpc_translators_test
import unittest
import asyncio
import aiozmq
import aiozmq.rpc
import msgpack

from aiozmq._test_util import find_unused_port


class Point:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        if isinstance(other, Point):
            return (self.x, self.y) == (other.x, other.y)
        return NotImplemented


translation_table = {
    0: (Point,
        lambda value: msgpack.packb((value.x, value.y)),
        lambda binary: Point(*msgpack.unpackb(binary))),
}


class MyHandler(aiozmq.rpc.AttrHandler):

    @aiozmq.rpc.method
    @asyncio.coroutine
    def func(self, point):
        assert isinstance(point, Point)
        return point
        yield


class RpcTranslatorsTests(unittest.TestCase):

    def setUp(self):
        self.loop = aiozmq.ZmqEventLoop()
        asyncio.set_event_loop(None)
        self.client = self.server = None

    def tearDown(self):
        if self.client is not None:
            self.close(self.client)
        if self.server is not None:
            self.close(self.server)
        self.loop.close()
        asyncio.set_event_loop(None)

    def close(self, server):
        server.close()
        self.loop.run_until_complete(server.wait_closed())

    def make_rpc_pair(self, *, error_table=None):
        port = find_unused_port()

        @asyncio.coroutine
        def create():
            server = yield from aiozmq.rpc.serve_rpc(
                MyHandler(),
                bind='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop,
                translation_table=translation_table)
            client = yield from aiozmq.rpc.connect_rpc(
                connect='tcp://127.0.0.1:{}'.format(port),
                loop=self.loop, error_table=error_table,
                translation_table=translation_table)
            return client, server

        self.client, self.server = self.loop.run_until_complete(create())

        return self.client, self.server

    def test_simple(self):
        client, server = self.make_rpc_pair()
        pt = Point(1, 2)

        @asyncio.coroutine
        def communicate():
            ret = yield from client.call.func(pt)
            self.assertEqual(ret, pt)

        self.loop.run_until_complete(communicate())

########NEW FILE########
__FILENAME__ = selectors_test
import errno
import os
import random
import signal
import socket
from time import sleep
import unittest
from unittest import mock
try:
    from time import monotonic as time
except ImportError:
    from time import time as time
try:
    import resource
except ImportError:
    resource = None
import zmq

from aiozmq.selector import ZmqSelector, EVENT_READ, EVENT_WRITE, SelectorKey
from aiozmq._test_util import requires_mac_ver


if hasattr(socket, 'socketpair'):
    socketpair = socket.socketpair
else:
    def socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
        with socket.socket(family, type, proto) as l:
            l.bind(('127.0.0.1', 0))
            l.listen(3)
            c = socket.socket(family, type, proto)
            try:
                c.connect(l.getsockname())
                caddr = c.getsockname()
                while True:
                    a, addr = l.accept()
                    # check that we've got the correct client
                    if addr == caddr:
                        return c, a
                    a.close()
            except OSError:
                c.close()
                raise


def find_ready_matching(ready, flag):
    match = []
    for key, events in ready:
        if events & flag:
            match.append(key.fileobj)
    return match


class SelectorTests(unittest.TestCase):

    SELECTOR = ZmqSelector

    def make_socketpair(self):
        rd, wr = socketpair()
        self.addCleanup(rd.close)
        self.addCleanup(wr.close)
        return rd, wr

    def test_register(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        key = s.register(rd, EVENT_READ, "data")
        self.assertIsInstance(key, SelectorKey)
        self.assertEqual(key.fileobj, rd)
        self.assertEqual(key.fd, rd.fileno())
        self.assertEqual(key.events, EVENT_READ)
        self.assertEqual(key.data, "data")

        # register an unknown event
        self.assertRaises(ValueError, s.register, 0, 999999)

        # register an invalid FD
        self.assertRaises(ValueError, s.register, -10, EVENT_READ)

        # register twice
        self.assertRaises(KeyError, s.register, rd, EVENT_READ)

        # register the same FD, but with a different object
        self.assertRaises(KeyError, s.register, rd.fileno(),
                          EVENT_READ)

        # register an invalid fd type
        self.assertRaises(ValueError, s.register, 'abc', EVENT_READ)

    def test_register_with_zmq_error(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        m = mock.Mock()
        m.side_effect = zmq.ZMQError(errno.EFAULT, 'not a socket')
        s._poller.register = m

        with self.assertRaises(OSError) as ctx:
            s.register(1, EVENT_READ)
        self.assertEqual(errno.EFAULT, ctx.exception.errno)
        self.assertNotIn(1, s.get_map())

    def test_unregister(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        s.register(rd, EVENT_READ)
        s.unregister(rd)

        # unregister an unknown file obj
        self.assertRaises(KeyError, s.unregister, 999999)

        # unregister twice
        self.assertRaises(KeyError, s.unregister, rd)

    def test_unregister_with_zmq_error(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()
        s.register(rd, EVENT_READ)

        m = mock.Mock()
        m.side_effect = zmq.ZMQError(errno.EFAULT, 'not a socket')
        s._poller.unregister = m

        with self.assertRaises(OSError) as ctx:
            s.unregister(rd)
        self.assertEqual(errno.EFAULT, ctx.exception.errno)
        self.assertIn(rd, s.get_map())

    def test_unregister_after_fd_close(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)
        rd, wr = self.make_socketpair()
        r, w = rd.fileno(), wr.fileno()
        s.register(r, EVENT_READ)
        s.register(w, EVENT_WRITE)
        rd.close()
        wr.close()
        s.unregister(r)
        s.unregister(w)

    @unittest.skipUnless(os.name == 'posix', "requires posix")
    def test_unregister_after_fd_close_and_reuse(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)
        rd, wr = self.make_socketpair()
        r, w = rd.fileno(), wr.fileno()
        s.register(r, EVENT_READ)
        s.register(w, EVENT_WRITE)
        rd2, wr2 = self.make_socketpair()
        rd.close()
        wr.close()
        os.dup2(rd2.fileno(), r)
        os.dup2(wr2.fileno(), w)
        self.addCleanup(os.close, r)
        self.addCleanup(os.close, w)
        s.unregister(r)
        s.unregister(w)

    def test_unregister_after_socket_close(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)
        rd, wr = self.make_socketpair()
        s.register(rd, EVENT_READ)
        s.register(wr, EVENT_WRITE)
        rd.close()
        wr.close()
        s.unregister(rd)
        s.unregister(wr)

    def test_modify(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        key = s.register(rd, EVENT_READ)

        # modify events
        key2 = s.modify(rd, EVENT_WRITE)
        self.assertNotEqual(key.events, key2.events)
        self.assertEqual(key2, s.get_key(rd))

        s.unregister(rd)

        # modify data
        d1 = object()
        d2 = object()

        key = s.register(rd, EVENT_READ, d1)
        key2 = s.modify(rd, EVENT_READ, d2)
        self.assertEqual(key.events, key2.events)
        self.assertNotEqual(key.data, key2.data)
        self.assertEqual(key2, s.get_key(rd))
        self.assertEqual(key2.data, d2)

        key3 = s.modify(rd, EVENT_READ, d2)
        self.assertIs(key3, key2)

        # modify unknown file obj
        self.assertRaises(KeyError, s.modify, 999999, EVENT_READ)

        # modify use a shortcut
        d3 = object()
        s.register = mock.Mock()
        s.unregister = mock.Mock()

        s.modify(rd, EVENT_READ, d3)
        self.assertFalse(s.register.called)
        self.assertFalse(s.unregister.called)

    def test_modify_with_zmq_error(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()
        s.register(rd, EVENT_READ)

        m = mock.Mock()
        m.side_effect = zmq.ZMQError(errno.EFAULT, 'not a socket')
        s._poller.modify = m

        with self.assertRaises(OSError) as ctx:
            s.modify(rd, EVENT_WRITE)
        self.assertEqual(errno.EFAULT, ctx.exception.errno)
        self.assertIn(rd, s.get_map())

    def test_close(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        s.register(rd, EVENT_READ)
        s.register(wr, EVENT_WRITE)

        s.close()
        self.assertRaises(KeyError, s.get_key, rd)
        self.assertRaises(KeyError, s.get_key, wr)

    def test_get_key(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        key = s.register(rd, EVENT_READ, "data")
        self.assertEqual(key, s.get_key(rd))

        # unknown file obj
        self.assertRaises(KeyError, s.get_key, 999999)

    def test_get_map(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        keys = s.get_map()
        self.assertFalse(keys)
        self.assertEqual(len(keys), 0)
        self.assertEqual(list(keys), [])
        key = s.register(rd, EVENT_READ, "data")
        self.assertIn(rd, keys)
        self.assertEqual(key, keys[rd])
        self.assertEqual(len(keys), 1)
        self.assertEqual(list(keys), [rd.fileno()])
        self.assertEqual(list(keys.values()), [key])

        # unknown file obj
        with self.assertRaises(KeyError):
            keys[999999]

        # Read-only mapping
        with self.assertRaises(TypeError):
            del keys[rd]

    def test_select(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        s.register(rd, EVENT_READ)
        wr_key = s.register(wr, EVENT_WRITE)

        result = s.select()
        for key, events in result:
            self.assertTrue(isinstance(key, SelectorKey))
            self.assertTrue(events)
            self.assertFalse(events & ~(EVENT_READ |
                                        EVENT_WRITE))

        self.assertEqual([(wr_key, EVENT_WRITE)], result)

    def test_select_with_zmq_error(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()
        s.register(rd, EVENT_READ)

        m = mock.Mock()
        m.side_effect = zmq.ZMQError(errno.EFAULT, 'not a socket')
        s._poller.poll = m

        with self.assertRaises(OSError) as ctx:
            s.select()
        self.assertEqual(errno.EFAULT, ctx.exception.errno)

    def test_select_without_key(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        s.register(wr, EVENT_WRITE)

        s._fd_to_key = {}

        result = s.select()
        self.assertFalse(result)

    def test_context_manager(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        with s as sel:
            sel.register(rd, EVENT_READ)
            sel.register(wr, EVENT_WRITE)

        self.assertRaises(KeyError, s.get_key, rd)
        self.assertRaises(KeyError, s.get_key, wr)

    def test_fileno(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        if hasattr(s, 'fileno'):
            fd = s.fileno()
            self.assertTrue(isinstance(fd, int))
            self.assertGreaterEqual(fd, 0)

    def test_selector(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        NUM_SOCKETS = 12
        MSG = b" This is a test."
        MSG_LEN = len(MSG)
        readers = []
        writers = []
        r2w = {}
        w2r = {}

        for i in range(NUM_SOCKETS):
            rd, wr = self.make_socketpair()
            s.register(rd, EVENT_READ)
            s.register(wr, EVENT_WRITE)
            readers.append(rd)
            writers.append(wr)
            r2w[rd] = wr
            w2r[wr] = rd

        bufs = []

        while writers:
            ready = s.select()
            ready_writers = find_ready_matching(ready, EVENT_WRITE)
            if not ready_writers:
                self.fail("no sockets ready for writing")
            wr = random.choice(ready_writers)
            wr.send(MSG)

            for i in range(10):
                ready = s.select()
                ready_readers = find_ready_matching(ready,
                                                    EVENT_READ)
                if ready_readers:
                    break
                # there might be a delay between the write to the write end and
                # the read end is reported ready
                sleep(0.1)
            else:
                self.fail("no sockets ready for reading")
            self.assertEqual([w2r[wr]], ready_readers)
            rd = ready_readers[0]
            buf = rd.recv(MSG_LEN)
            self.assertEqual(len(buf), MSG_LEN)
            bufs.append(buf)
            s.unregister(r2w[rd])
            s.unregister(rd)
            writers.remove(r2w[rd])

        self.assertEqual(bufs, [MSG] * NUM_SOCKETS)

    def test_timeout(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        s.register(wr, EVENT_WRITE)
        t = time()
        self.assertEqual(1, len(s.select(0)))
        self.assertEqual(1, len(s.select(-1)))
        self.assertLess(time() - t, 0.5)

        s.unregister(wr)
        s.register(rd, EVENT_READ)
        t = time()
        self.assertFalse(s.select(0))
        self.assertFalse(s.select(-1))
        self.assertLess(time() - t, 0.5)

        t0 = time()
        self.assertFalse(s.select(1))
        t1 = time()
        dt = t1 - t0
        self.assertTrue(0.8 <= dt <= 1.6, dt)

    @unittest.skipUnless(hasattr(signal, "alarm"),
                         "signal.alarm() required for this test")
    def test_select_interrupt(self):
        s = self.SELECTOR()
        self.addCleanup(s.close)

        rd, wr = self.make_socketpair()

        orig_alrm_handler = signal.signal(signal.SIGALRM, lambda *args: None)
        self.addCleanup(signal.signal, signal.SIGALRM, orig_alrm_handler)
        self.addCleanup(signal.alarm, 0)

        signal.alarm(1)

        s.register(rd, EVENT_READ)
        t = time()
        self.assertFalse(s.select(2))
        self.assertLess(time() - t, 2.5)

    # see issue #18963 for why it's skipped on older OS X versions
    @requires_mac_ver(10, 5)
    @unittest.skipUnless(resource, "Test needs resource module")
    def test_above_fd_setsize(self):
        # A scalable implementation should have no problem with more than
        # FD_SETSIZE file descriptors. Since we don't know the value, we just
        # try to set the soft RLIMIT_NOFILE to the hard RLIMIT_NOFILE ceiling.
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
            self.addCleanup(resource.setrlimit, resource.RLIMIT_NOFILE,
                            (soft, hard))
            NUM_FDS = hard
        except (OSError, ValueError):
            NUM_FDS = soft

        # guard for already allocated FDs (stdin, stdout...)
        NUM_FDS -= 32

        s = self.SELECTOR()
        self.addCleanup(s.close)

        for i in range(NUM_FDS // 2):
            try:
                rd, wr = self.make_socketpair()
            except OSError:
                # too many FDs, skip - note that we should only catch EMFILE
                # here, but apparently *BSD and Solaris can fail upon connect()
                # or bind() with EADDRNOTAVAIL, so let's be safe
                self.skipTest("FD limit reached")

            try:
                s.register(rd, EVENT_READ)
                s.register(wr, EVENT_WRITE)
            except OSError as e:
                if e.errno == errno.ENOSPC:
                    # this can be raised by epoll if we go over
                    # fs.epoll.max_user_watches sysctl
                    self.skipTest("FD limit reached")
                raise

        self.assertEqual(NUM_FDS // 2, len(s.select()))

########NEW FILE########
__FILENAME__ = transport_test
import unittest

import asyncio
import zmq
import aiozmq
import errno

from collections import deque

from asyncio import test_utils
from aiozmq.core import _ZmqTransportImpl
from unittest import mock

from aiozmq._test_util import check_errno


class TransportTests(unittest.TestCase):

    def setUp(self):
        self.loop = test_utils.TestLoop()
        self.sock = mock.Mock()
        self.sock.closed = False
        self.proto = test_utils.make_test_protocol(aiozmq.ZmqProtocol)
        self.tr = _ZmqTransportImpl(self.loop, zmq.SUB, self.sock, self.proto)
        self.exc_handler = mock.Mock()
        self.loop.set_exception_handler(self.exc_handler)

    def test_empty_write(self):
        self.tr.write([b''])
        self.assertTrue(self.sock.send_multipart.called)
        self.assertFalse(self.proto.pause_writing.called)
        self.assertFalse(self.tr._buffer)
        self.assertEqual(0, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.assertNotIn(self.sock, self.loop.writers)

    def test_write(self):
        self.tr.write((b'a', b'b'))
        self.sock.send_multipart.assert_called_with((b'a', b'b'), zmq.DONTWAIT)
        self.assertFalse(self.proto.pause_writing.called)
        self.assertFalse(self.tr._buffer)
        self.assertEqual(0, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.assertNotIn(self.sock, self.loop.writers)

    def test_partial_write(self):
        self.sock.send_multipart.side_effect = zmq.ZMQError(errno.EAGAIN)
        self.tr.write((b'a', b'b'))
        self.sock.send_multipart.assert_called_with((b'a', b'b'), zmq.DONTWAIT)
        self.assertFalse(self.proto.pause_writing.called)
        self.assertEqual([(2, (b'a', b'b'))], list(self.tr._buffer))
        self.assertEqual(2, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.loop.assert_writer(self.sock, self.tr._write_ready)

    def test_partial_double_write(self):
        self.sock.send_multipart.side_effect = zmq.ZMQError(errno.EAGAIN)
        self.tr.write((b'a', b'b'))
        self.tr.write((b'c',))
        self.sock.send_multipart.mock_calls = [
            mock.call((b'a', b'b'), zmq.DONTWAIT)]
        self.assertFalse(self.proto.pause_writing.called)
        self.assertEqual([(2, (b'a', b'b')), (1, (b'c',))],
                         list(self.tr._buffer))
        self.assertEqual(3, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.loop.assert_writer(self.sock, self.tr._write_ready)

    def test__write_ready(self):
        self.tr._buffer.append((2, (b'a', b'b')))
        self.tr._buffer.append((1, (b'c',)))
        self.tr._buffer_size = 3
        self.loop.add_writer(self.sock, self.tr._write_ready)

        self.tr._write_ready()

        self.sock.send_multipart.mock_calls = [
            mock.call((b'a', b'b'), zmq.DONTWAIT)]
        self.assertFalse(self.proto.pause_writing.called)
        self.assertEqual([(1, (b'c',))], list(self.tr._buffer))
        self.assertEqual(1, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.loop.assert_writer(self.sock, self.tr._write_ready)

    def test__write_ready_sent_whole_buffer(self):
        self.tr._buffer.append((2, (b'a', b'b')))
        self.tr._buffer_size = 2
        self.loop.add_writer(self.sock, self.tr._write_ready)

        self.sock.send_multipart.mock_calls = [
            mock.call((b'a', b'b'), zmq.DONTWAIT)]
        self.tr._write_ready()

        self.assertFalse(self.proto.pause_writing.called)
        self.assertFalse(self.tr._buffer)
        self.assertEqual(0, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.assertEqual(1, self.loop.remove_writer_count[self.sock])

    def test__write_ready_raises_ZMQError(self):
        self.tr._buffer.append((2, (b'a', b'b')))
        self.tr._buffer_size = 2
        self.loop.add_writer(self.sock, self.tr._write_ready)

        self.sock.send_multipart.side_effect = zmq.ZMQError(errno.ENOTSUP,
                                                            'not supported')
        self.tr._write_ready()
        self.assertFalse(self.proto.pause_writing.called)
        self.assertFalse(self.tr._buffer)
        self.assertEqual(0, self.tr._buffer_size)
        self.assertTrue(self.exc_handler.called)
        self.assertEqual(1, self.loop.remove_writer_count[self.sock])
        self.assertTrue(self.tr._closing)
        self.assertEqual(1, self.loop.remove_reader_count[self.sock])

    def test__write_ready_raises_EAGAIN(self):
        self.tr._buffer.append((2, (b'a', b'b')))
        self.tr._buffer_size = 2
        self.loop.add_writer(self.sock, self.tr._write_ready)

        self.sock.send_multipart.side_effect = zmq.ZMQError(errno.EAGAIN,
                                                            'try again')
        self.tr._write_ready()
        self.assertFalse(self.proto.pause_writing.called)
        self.assertEqual([(2, (b'a', b'b',))], list(self.tr._buffer))
        self.assertEqual(2, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.loop.assert_writer(self.sock, self.tr._write_ready)
        self.assertFalse(self.tr._closing)
        self.loop.assert_reader(self.sock, self.tr._read_ready)

    def test_close_with_empty_buffer(self):
        self.tr.close()

        self.assertTrue(self.tr._closing)
        self.assertEqual(1, self.loop.remove_reader_count[self.sock])
        self.assertFalse(self.tr._buffer)
        self.assertEqual(0, self.tr._buffer_size)
        self.assertIsNotNone(self.tr._protocol)
        self.assertIsNotNone(self.tr._zmq_sock)
        self.assertIsNotNone(self.tr._loop)
        self.assertFalse(self.sock.close.called)

        test_utils.run_briefly(self.loop)

        self.proto.connection_lost.assert_called_with(None)
        self.assertIsNone(self.tr._protocol)
        self.assertIsNone(self.tr._zmq_sock)
        self.assertIsNone(self.tr._loop)
        self.sock.close.assert_called_with()

    def test_close_with_waiting_buffer(self):
        self.tr._buffer = deque([(b'data',)])
        self.tr._buffer_size = 4
        self.loop.add_writer(self.sock, self.tr._write_ready)

        self.tr.close()

        self.assertEqual(1, self.loop.remove_reader_count[self.sock])
        self.assertEqual(0, self.loop.remove_writer_count[self.sock])
        self.assertEqual([(b'data',)], list(self.tr._buffer))
        self.assertEqual(4, self.tr._buffer_size)
        self.assertTrue(self.tr._closing)

        self.assertIsNotNone(self.tr._protocol)
        self.assertIsNotNone(self.tr._zmq_sock)
        self.assertIsNotNone(self.tr._loop)
        self.assertFalse(self.sock.close.called)

        test_utils.run_briefly(self.loop)

        self.assertIsNotNone(self.tr._protocol)
        self.assertIsNotNone(self.tr._zmq_sock)
        self.assertIsNotNone(self.tr._loop)
        self.assertFalse(self.sock.close.called)
        self.assertFalse(self.proto.connection_lost.called)

    def test_double_closing(self):
        self.tr.close()
        self.tr.close()
        self.assertEqual(1, self.loop.remove_reader_count[self.sock])

    def test_close_on_last__write_ready(self):
        self.tr._buffer = deque([(4, (b'data',))])
        self.tr._buffer_size = 4
        self.loop.add_writer(self.sock, self.tr._write_ready)

        self.tr.close()
        self.tr._write_ready()

        self.assertFalse(self.tr._buffer)
        self.assertEqual(0, self.tr._buffer_size)
        self.assertIsNone(self.tr._protocol)
        self.assertIsNone(self.tr._zmq_sock)
        self.assertIsNone(self.tr._loop)
        self.proto.connection_lost.assert_called_with(None)
        self.sock.close.assert_called_with()

    def test_write_eof(self):
        self.assertFalse(self.tr.can_write_eof())

    def test_dns_address(self):
        @asyncio.coroutine
        def go():
            with self.assertRaises(ValueError):
                yield from self.tr.connect('tcp://example.com:8080')

    def test_write_none(self):
        self.tr.write(None)
        self.assertFalse(self.sock.called)

    def test_write_noniterable(self):
        self.assertRaises(TypeError, self.tr.write, 1)
        self.assertFalse(self.sock.called)

    def test_write_nonbytes(self):
        self.assertRaises(TypeError, self.tr.write, [1])
        self.assertFalse(self.sock.called)

    def test_abort_with_empty_buffer(self):
        self.tr.abort()

        self.assertTrue(self.tr._closing)
        self.assertEqual(1, self.loop.remove_reader_count[self.sock])
        self.assertFalse(self.tr._buffer)
        self.assertEqual(0, self.tr._buffer_size)
        self.assertIsNotNone(self.tr._protocol)
        self.assertIsNotNone(self.tr._zmq_sock)
        self.assertIsNotNone(self.tr._loop)
        self.assertFalse(self.sock.close.called)

        test_utils.run_briefly(self.loop)

        self.proto.connection_lost.assert_called_with(None)
        self.assertIsNone(self.tr._protocol)
        self.assertIsNone(self.tr._zmq_sock)
        self.assertIsNone(self.tr._loop)
        self.sock.close.assert_called_with()

    def test_abort_with_waiting_buffer(self):
        self.tr._buffer = deque([(b'data',)])
        self.tr._buffer_size = 4
        self.loop.add_writer(self.sock, self.tr._write_ready)

        self.tr.abort()

        self.assertEqual(1, self.loop.remove_reader_count[self.sock])
        self.assertEqual(1, self.loop.remove_writer_count[self.sock])
        self.assertEqual([], list(self.tr._buffer))
        self.assertEqual(0, self.tr._buffer_size)
        self.assertTrue(self.tr._closing)

        test_utils.run_briefly(self.loop)

        self.assertIsNone(self.tr._protocol)
        self.assertIsNone(self.tr._zmq_sock)
        self.assertIsNone(self.tr._loop)
        self.assertTrue(self.proto.connection_lost.called)
        self.assertTrue(self.sock.close.called)

    def test_abort_with_close_on_waiting_buffer(self):
        self.tr._buffer = deque([(b'data',)])
        self.tr._buffer_size = 4
        self.loop.add_writer(self.sock, self.tr._write_ready)

        self.tr.close()
        self.tr.abort()

        self.assertEqual(1, self.loop.remove_reader_count[self.sock])
        self.assertEqual(1, self.loop.remove_writer_count[self.sock])
        self.assertEqual([], list(self.tr._buffer))
        self.assertEqual(0, self.tr._buffer_size)
        self.assertTrue(self.tr._closing)

        test_utils.run_briefly(self.loop)

        self.assertIsNone(self.tr._protocol)
        self.assertIsNone(self.tr._zmq_sock)
        self.assertIsNone(self.tr._loop)
        self.assertTrue(self.proto.connection_lost.called)
        self.assertTrue(self.sock.close.called)

    def test__read_ready_got_EAGAIN(self):
        self.sock.recv_multipart.side_effect = zmq.ZMQError(errno.EAGAIN)
        self.tr._fatal_error = mock.Mock()

        self.tr._read_ready()

        self.assertFalse(self.tr._fatal_error.called)
        self.assertFalse(self.proto.msg_received.called)

    def test__read_ready_got_fatal_error(self):
        self.sock.recv_multipart.side_effect = zmq.ZMQError(errno.EINVAL)
        self.tr._fatal_error = mock.Mock()

        self.tr._read_ready()

        self.assertFalse(self.proto.msg_received.called)
        exc = self.tr._fatal_error.call_args[0][0]
        self.assertIsInstance(exc, OSError)
        self.assertEqual(exc.errno, errno.EINVAL)

    def test_setsockopt_EINTR(self):
        self.sock.setsockopt.side_effect = [zmq.ZMQError(errno.EINTR), None]
        self.assertIsNone(self.tr.setsockopt('opt', 'val'))
        self.assertEqual([mock.call('opt', 'val'), mock.call('opt', 'val')],
                         self.sock.setsockopt.call_args_list)

    def test_getsockopt_EINTR(self):
        self.sock.getsockopt.side_effect = [zmq.ZMQError(errno.EINTR), 'val']
        self.assertEqual('val', self.tr.getsockopt('opt'))
        self.assertEqual([mock.call('opt'), mock.call('opt')],
                         self.sock.getsockopt.call_args_list)

    def test_write_EAGAIN(self):
        self.sock.send_multipart.side_effect = zmq.ZMQError(errno.EAGAIN)
        self.tr.write((b'a', b'b'))
        self.sock.send_multipart.assert_called_once_with(
            (b'a', b'b'), zmq.DONTWAIT)
        self.assertFalse(self.proto.pause_writing.called)
        self.assertEqual([(2, (b'a', b'b'))], list(self.tr._buffer))
        self.assertEqual(2, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.loop.assert_writer(self.sock, self.tr._write_ready)

    def test_write_EINTR(self):
        self.sock.send_multipart.side_effect = zmq.ZMQError(errno.EINTR)
        self.tr.write((b'a', b'b'))
        self.sock.send_multipart.assert_called_once_with(
            (b'a', b'b'), zmq.DONTWAIT)
        self.assertFalse(self.proto.pause_writing.called)
        self.assertEqual([(2, (b'a', b'b'))], list(self.tr._buffer))
        self.assertEqual(2, self.tr._buffer_size)
        self.assertFalse(self.exc_handler.called)
        self.loop.assert_writer(self.sock, self.tr._write_ready)

    def test_write_common_error(self):
        self.sock.send_multipart.side_effect = zmq.ZMQError(errno.ENOTSUP)
        self.tr.write((b'a', b'b'))
        self.sock.send_multipart.assert_called_once_with(
            (b'a', b'b'), zmq.DONTWAIT)
        self.assertFalse(self.proto.pause_writing.called)
        self.assertFalse(self.tr._buffer)
        self.assertEqual(0, self.tr._buffer_size)
        self.assertNotIn(self.sock, self.loop.writers)
        check_errno(errno.ENOTSUP,
                    self.exc_handler.call_args[0][1]['exception'])

    def test_subscribe_invalid_socket_type(self):
        self.tr._zmq_type = zmq.PUB
        self.assertRaises(NotImplementedError, self.tr.subscribe, b'a')
        self.assertRaises(NotImplementedError, self.tr.unsubscribe, b'a')
        self.assertRaises(NotImplementedError, self.tr.subscriptions)

    def test_double_subscribe(self):
        self.tr.subscribe(b'val')
        self.tr.subscribe(b'val')
        self.assertEqual({b'val'}, self.tr.subscriptions())
        self.sock.setsockopt.assert_called_once_with(zmq.SUBSCRIBE, b'val')

    def test_subscribe_bad_value_type(self):
        self.assertRaises(TypeError, self.tr.subscribe, 'a')
        self.assertFalse(self.tr.subscriptions())
        self.assertRaises(TypeError, self.tr.unsubscribe, 'a')
        self.assertFalse(self.sock.setsockopt.called)
        self.assertFalse(self.tr.subscriptions())

    def test_unsubscribe(self):
        self.tr.subscribe(b'val')

        self.tr.unsubscribe(b'val')
        self.assertFalse(self.tr.subscriptions())
        self.sock.setsockopt.assert_called_with(zmq.UNSUBSCRIBE, b'val')

    def test_pause_resume_reading(self):
        self.assertFalse(self.tr._paused)
        self.loop.assert_reader(self.sock, self.tr._read_ready)
        self.tr.pause_reading()
        self.assertTrue(self.tr._paused)
        self.assertNotIn(self.sock, self.loop.readers)
        self.tr.resume_reading()
        self.assertFalse(self.tr._paused)
        self.loop.assert_reader(self.sock, self.tr._read_ready)
        with self.assertRaises(RuntimeError):
            self.tr.resume_reading()

########NEW FILE########
__FILENAME__ = version_test
import unittest

from aiozmq import _parse_version


class VersionTests(unittest.TestCase):

    def test_alpha(self):
        self.assertEqual((0, 1, 2, 'alpha', 2), _parse_version('0.1.2a2'))
        self.assertEqual((1, 2, 3, 'alpha', 0), _parse_version('1.2.3a'))

    def test_beta(self):
        self.assertEqual((0, 1, 2, 'beta', 2), _parse_version('0.1.2b2'))
        self.assertEqual((0, 1, 2, 'beta', 0), _parse_version('0.1.2b'))

    def test_rc(self):
        self.assertEqual((0, 1, 2, 'candidate', 5), _parse_version('0.1.2rc5'))
        self.assertEqual((0, 1, 2, 'candidate', 0), _parse_version('0.1.2rc'))

    def test_final(self):
        self.assertEqual((0, 1, 2, 'final', 0), _parse_version('0.1.2'))

    def test_invalid(self):
        self.assertRaises(ImportError, _parse_version, '0.1')
        self.assertRaises(ImportError, _parse_version, '0.1.1.2')
        self.assertRaises(ImportError, _parse_version, '0.1.1z2')

########NEW FILE########
__FILENAME__ = zmq_events_test
import asyncio
import errno
import os
import sys
import unittest
from unittest import mock

import aiozmq
import zmq
from aiozmq._test_util import find_unused_port


class Protocol(aiozmq.ZmqProtocol):

    def __init__(self, loop):
        self.transport = None
        self.connected = asyncio.Future(loop=loop)
        self.closed = asyncio.Future(loop=loop)
        self.state = 'INITIAL'
        self.received = asyncio.Queue(loop=loop)

    def connection_made(self, transport):
        self.transport = transport
        assert self.state == 'INITIAL', self.state
        self.state = 'CONNECTED'
        self.connected.set_result(None)

    def connection_lost(self, exc):
        assert self.state == 'CONNECTED', self.state
        self.state = 'CLOSED'
        self.closed.set_result(None)
        self.transport = None

    def pause_writing(self):
        pass

    def resume_writing(self):
        pass

    def msg_received(self, data):
        assert isinstance(data, list), data
        assert self.state == 'CONNECTED', self.state
        self.received.put_nowait(data)


class ZmqEventLoopTests(unittest.TestCase):

    def setUp(self):
        self.loop = aiozmq.ZmqEventLoop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_req_rep(self):
        @asyncio.coroutine
        def connect_req():
            tr1, pr1 = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.REQ,
                bind='inproc://test')
            self.assertEqual('CONNECTED', pr1.state)
            yield from pr1.connected
            return tr1, pr1

        tr1, pr1 = self.loop.run_until_complete(connect_req())

        @asyncio.coroutine
        def connect_rep():
            tr2, pr2 = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.REP,
                connect='inproc://test')
            self.assertEqual('CONNECTED', pr2.state)
            yield from pr2.connected
            return tr2, pr2

        tr2, pr2 = self.loop.run_until_complete(connect_rep())

        @asyncio.coroutine
        def communicate():
            tr1.write([b'request'])
            request = yield from pr2.received.get()
            self.assertEqual([b'request'], request)
            tr2.write([b'answer'])
            answer = yield from pr1.received.get()
            self.assertEqual([b'answer'], answer)

        self.loop.run_until_complete(communicate())

        @asyncio.coroutine
        def closing():
            tr1.close()
            tr2.close()

            yield from pr1.closed
            self.assertEqual('CLOSED', pr1.state)
            yield from pr2.closed
            self.assertEqual('CLOSED', pr2.state)

        self.loop.run_until_complete(closing())

    def test_pub_sub(self):
        port = find_unused_port()

        @asyncio.coroutine
        def connect_pub():
            tr1, pr1 = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.PUB,
                bind='tcp://127.0.0.1:{}'.format(port))
            self.assertEqual('CONNECTED', pr1.state)
            yield from pr1.connected
            return tr1, pr1

        tr1, pr1 = self.loop.run_until_complete(connect_pub())

        @asyncio.coroutine
        def connect_sub():
            tr2, pr2 = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                connect='tcp://127.0.0.1:{}'.format(port))
            self.assertEqual('CONNECTED', pr2.state)
            yield from pr2.connected
            tr2.setsockopt(zmq.SUBSCRIBE, b'node_id')
            return tr2, pr2

        tr2, pr2 = self.loop.run_until_complete(connect_sub())

        @asyncio.coroutine
        def communicate():
            for i in range(5):
                tr1.write([b'node_id', b'publish'])
                try:
                    request = yield from asyncio.wait_for(pr2.received.get(),
                                                          0.1,
                                                          loop=self.loop)
                    self.assertEqual([b'node_id', b'publish'], request)
                    break
                except asyncio.TimeoutError:
                    pass
                else:
                    raise AssertionError("Cannot get message in subscriber")

        self.loop.run_until_complete(communicate())

        @asyncio.coroutine
        def closing():
            tr1.close()
            tr2.close()

            yield from pr1.closed
            self.assertEqual('CLOSED', pr1.state)
            yield from pr2.closed
            self.assertEqual('CLOSED', pr2.state)

        self.loop.run_until_complete(closing())

    def test_getsockopt(self):
        port = find_unused_port()

        @asyncio.coroutine
        def coro():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.DEALER,
                bind='tcp://127.0.0.1:{}'.format(port))
            yield from pr.connected
            self.assertEqual(zmq.DEALER, tr.getsockopt(zmq.TYPE))
            return tr, pr

        self.loop.run_until_complete(coro())

    def test_dealer_router(self):
        port = find_unused_port()

        @asyncio.coroutine
        def connect_req():
            tr1, pr1 = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.DEALER,
                bind='tcp://127.0.0.1:{}'.format(port))
            self.assertEqual('CONNECTED', pr1.state)
            yield from pr1.connected
            return tr1, pr1

        tr1, pr1 = self.loop.run_until_complete(connect_req())

        @asyncio.coroutine
        def connect_rep():
            tr2, pr2 = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.ROUTER,
                connect='tcp://127.0.0.1:{}'.format(port))
            self.assertEqual('CONNECTED', pr2.state)
            yield from pr2.connected
            return tr2, pr2

        tr2, pr2 = self.loop.run_until_complete(connect_rep())

        @asyncio.coroutine
        def communicate():
            tr1.write([b'request'])
            request = yield from pr2.received.get()
            self.assertEqual([mock.ANY, b'request'], request)
            tr2.write([request[0], b'answer'])
            answer = yield from pr1.received.get()
            self.assertEqual([b'answer'], answer)

        self.loop.run_until_complete(communicate())

        @asyncio.coroutine
        def closing():
            tr1.close()
            tr2.close()

            yield from pr1.closed
            self.assertEqual('CLOSED', pr1.state)
            yield from pr2.closed
            self.assertEqual('CLOSED', pr2.state)

        self.loop.run_until_complete(closing())

    def test_binds(self):
        port1 = find_unused_port()
        port2 = find_unused_port()
        addr1 = 'tcp://127.0.0.1:{}'.format(port1)
        addr2 = 'tcp://127.0.0.1:{}'.format(port2)

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.REQ,
                bind=[addr1, addr2])
            yield from pr.connected

            self.assertEqual({addr1, addr2}, tr.bindings())

            addr3 = yield from tr.bind('tcp://127.0.0.1:*')
            self.assertEqual({addr1, addr2, addr3}, tr.bindings())
            yield from tr.unbind(addr2)
            self.assertEqual({addr1, addr3}, tr.bindings())
            self.assertIn(addr1, tr.bindings())
            self.assertRegex(repr(tr.bindings()),
                             r'{tcp://127.0.0.1:.\d+, tcp://127.0.0.1:\d+}')
            tr.close()

        self.loop.run_until_complete(connect())

    def test_connects(self):
        port1 = find_unused_port()
        port2 = find_unused_port()
        port3 = find_unused_port()
        addr1 = 'tcp://127.0.0.1:{}'.format(port1)
        addr2 = 'tcp://127.0.0.1:{}'.format(port2)
        addr3 = 'tcp://127.0.0.1:{}'.format(port3)

        @asyncio.coroutine
        def go():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.REQ,
                connect=[addr1, addr2])
            yield from pr.connected

            self.assertEqual({addr1, addr2}, tr.connections())
            yield from tr.connect(addr3)
            self.assertEqual({addr1, addr3, addr2}, tr.connections())
            yield from tr.disconnect(addr1)
            self.assertEqual({addr2, addr3}, tr.connections())
            tr.close()

        self.loop.run_until_complete(go())

    def test_zmq_socket(self):
        zmq_sock = self.loop._zmq_context.socket(zmq.PUB)

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.PUB,
                zmq_sock=zmq_sock)
            yield from pr.connected
            return tr, pr

        tr, pr = self.loop.run_until_complete(connect())
        self.assertIs(zmq_sock, tr._zmq_sock)
        self.assertFalse(zmq_sock.closed)
        tr.close()

    def test_zmq_socket_invalid_type(self):
        zmq_sock = self.loop._zmq_context.socket(zmq.PUB)

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                zmq_sock=zmq_sock)
            yield from pr.connected
            return tr, pr

        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect())
        self.assertFalse(zmq_sock.closed)

    def test_create_zmq_connection_ZMQError(self):
        zmq_sock = self.loop._zmq_context.socket(zmq.PUB)
        zmq_sock.close()

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                zmq_sock=zmq_sock)
            yield from pr.connected
            return tr, pr

        with self.assertRaises(OSError) as ctx:
            self.loop.run_until_complete(connect())
        self.assertIn(ctx.exception.errno, (zmq.ENOTSUP, zmq.ENOTSOCK))

    def test_create_zmq_connection_invalid_bind(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                bind=2)

        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect())

    def test_create_zmq_connection_invalid_connect(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                connect=2)

        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect())

    @unittest.skipIf(sys.platform == 'win32',
                     "Windows calls abort() on bad socket")
    def test_create_zmq_connection_closes_socket_on_bad_bind(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                bind='badaddr')
            yield from pr.connected
            return tr, pr

        with self.assertRaises(OSError):
            self.loop.run_until_complete(connect())

    @unittest.skipIf(sys.platform == 'win32',
                     "Windows calls abort() on bad socket")
    def test_create_zmq_connection_closes_socket_on_bad_connect(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                connect='badaddr')
            yield from pr.connected
            return tr, pr

        with self.assertRaises(OSError):
            self.loop.run_until_complete(connect())

    def test_create_zmq_connection_dns_in_connect(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                connect='tcp://example.com:5555')
            yield from pr.connected
            return tr, pr

        with self.assertRaises(ValueError):
            self.loop.run_until_complete(connect())

    def test_getsockopt_badopt(self):
        port = find_unused_port()

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                connect='tcp://127.0.0.1:{}'.format(port))
            yield from pr.connected
            return tr, pr

        tr, pr = self.loop.run_until_complete(connect())

        with self.assertRaises(OSError) as ctx:
            tr.getsockopt(1111)  # invalid option
        self.assertEqual(zmq.EINVAL, ctx.exception.errno)

    def test_setsockopt_badopt(self):
        port = find_unused_port()

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                connect='tcp://127.0.0.1:{}'.format(port))
            yield from pr.connected
            return tr, pr

        tr, pr = self.loop.run_until_complete(connect())

        with self.assertRaises(OSError) as ctx:
            tr.setsockopt(1111, 1)  # invalid option
        self.assertEqual(zmq.EINVAL, ctx.exception.errno)

    def test_unbind_from_nonbinded_addr(self):
        port = find_unused_port()
        addr = 'tcp://127.0.0.1:{}'.format(port)

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                bind=addr)
            yield from pr.connected

            self.assertEqual({addr}, tr.bindings())
            with self.assertRaises(OSError) as ctx:
                yield from tr.unbind('ipc:///some-addr')  # non-bound addr

            # TODO: check travis build and remove skip when test passed.
            if (ctx.exception.errno == zmq.EAGAIN and
                    os.environ.get('TRAVIS')):
                raise unittest.SkipTest("Travis has a bug, it returns "
                                        "EAGAIN for unknown endpoint")
            self.assertIn(ctx.exception.errno,
                          (errno.ENOENT, zmq.EPROTONOSUPPORT))
            self.assertEqual({addr}, tr.bindings())

        self.loop.run_until_complete(connect())

    def test_disconnect_from_nonbinded_addr(self):
        port = find_unused_port()
        addr = 'tcp://127.0.0.1:{}'.format(port)

        @asyncio.coroutine
        def go():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                connect=addr)
            yield from pr.connected

            self.assertEqual({addr}, tr.connections())
            with self.assertRaises(OSError) as ctx:
                yield from tr.disconnect('ipc:///some-addr')  # non-bound addr

            # TODO: check travis build and remove skip when test passed.
            if (ctx.exception.errno == zmq.EAGAIN and
                    os.environ.get('TRAVIS')):
                raise unittest.SkipTest("Travis has a bug, it returns "
                                        "EAGAIN for unknown endpoint")
            self.assertIn(ctx.exception.errno,
                          (errno.ENOENT, zmq.EPROTONOSUPPORT))
            self.assertEqual({addr}, tr.connections())

        self.loop.run_until_complete(go())

    def test_subscriptions_of_invalid_socket(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.PUSH,
                bind='tcp://127.0.0.1:*')
            yield from pr.connected
            return tr, pr

        tr, pr = self.loop.run_until_complete(connect())
        self.assertRaises(NotImplementedError, tr.subscribe, b'a')
        self.assertRaises(NotImplementedError, tr.unsubscribe, b'a')
        self.assertRaises(NotImplementedError, tr.subscriptions)

    def test_double_subscribe(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                bind='tcp://127.0.0.1:*')
            yield from pr.connected
            return tr, pr

        tr, pr = self.loop.run_until_complete(connect())
        tr.subscribe(b'val')
        self.assertEqual({b'val'}, tr.subscriptions())

        tr.subscribe(b'val')
        self.assertEqual({b'val'}, tr.subscriptions())

    def test_double_unsubscribe(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                bind='tcp://127.0.0.1:*')
            yield from pr.connected
            return tr, pr

        tr, pr = self.loop.run_until_complete(connect())
        tr.subscribe(b'val')
        self.assertEqual({b'val'}, tr.subscriptions())

        tr.unsubscribe(b'val')
        self.assertFalse(tr.subscriptions())
        tr.unsubscribe(b'val')
        self.assertFalse(tr.subscriptions())

    def test_unsubscribe_unknown_filter(self):

        @asyncio.coroutine
        def connect():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.SUB,
                bind='tcp://127.0.0.1:*')
            yield from pr.connected
            return tr, pr

        tr, pr = self.loop.run_until_complete(connect())

        tr.unsubscribe(b'val')
        self.assertFalse(tr.subscriptions())
        tr.unsubscribe(b'val')
        self.assertFalse(tr.subscriptions())

    def test_endpoint_is_not_a_str(self):

        @asyncio.coroutine
        def go():
            tr, pr = yield from self.loop.create_zmq_connection(
                lambda: Protocol(self.loop),
                zmq.PUSH,
                bind='tcp://127.0.0.1:*')
            yield from pr.connected

            with self.assertRaises(TypeError):
                yield from tr.bind(123)

            with self.assertRaises(TypeError):
                yield from tr.unbind(123)

            with self.assertRaises(TypeError):
                yield from tr.connect(123)

            with self.assertRaises(TypeError):
                yield from tr.disconnect(123)

        self.loop.run_until_complete(go())

########NEW FILE########
