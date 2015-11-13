__FILENAME__ = connection
from .log import logger
from .protocol import RedisProtocol, _all_commands
import asyncio
import logging


__all__ = ('Connection', )


class Connection:
    """
    Wrapper around the protocol and transport which takes care of establishing
    the connection and reconnecting it.


    ::

        connection = yield from Connection.create(host='localhost', port=6379)
        result = yield from connection.set('key', 'value')
    """
    @classmethod
    @asyncio.coroutine
    def create(cls, host='localhost', port=6379, password=None, db=0,
               encoder=None, auto_reconnect=True, loop=None):
        """
        :param host: Address, either host or unix domain socket path
        :type host: str
        :param port: TCP port. If port is 0 then host assumed to be unix socket path
        :type port: int
        :param password: Redis database password
        :type password: bytes
        :param db: Redis database
        :type db: int
        :param encoder: Encoder to use for encoding to or decoding from redis bytes to a native type.
        :type encoder: :class:`asyncio_redis.encoders.BaseEncoder` instance.
        :param auto_reconnect: Enable auto reconnect
        :type auto_reconnect: bool
        :param loop: (optional) asyncio event loop.
        """
        assert port >= 0, "Unexpected port value: %r" % (port, )
        connection = cls()

        connection.host = host
        connection.port = port
        connection._loop = loop or asyncio.get_event_loop()
        connection._retry_interval = .5
        connection._closed = False

        # Create protocol instance
        def connection_lost():
            if auto_reconnect and not connection._closed:
                asyncio.async(connection._reconnect(), loop=connection._loop)

        # Create protocol instance
        connection.protocol = RedisProtocol(password=password, db=db, encoder=encoder,
                        connection_lost_callback=connection_lost, loop=connection._loop)

        # Connect
        yield from connection._reconnect()

        return connection

    @property
    def transport(self):
        """ The transport instance that the protocol is currently using. """
        return self.protocol.transport

    def _get_retry_interval(self):
        """ Time to wait for a reconnect in seconds. """
        return self._retry_interval

    def _reset_retry_interval(self):
        """ Set the initial retry interval. """
        self._retry_interval = .5

    def _increase_retry_interval(self):
        """ When a connection failed. Increase the interval."""
        self._retry_interval = min(60, 1.5 * self._retry_interval)

    def _reconnect(self):
        """
        Set up Redis connection.
        """
        while True:
            try:
                logger.log(logging.INFO, 'Connecting to redis')
                if self.port:
                    yield from self._loop.create_connection(lambda: self.protocol, self.host, self.port)
                else:
                    yield from self._loop.create_unix_connection(lambda: self.protocol, self.host)
                self._reset_retry_interval()
                return
            except OSError:
                # Sleep and try again
                self._increase_retry_interval()
                interval = self._get_retry_interval()
                logger.log(logging.INFO, 'Connecting to redis failed. Retrying in %i seconds' % interval)
                yield from asyncio.sleep(interval, loop=self._loop)

    def __getattr__(self, name):
        # Only proxy commands.
        if name not in _all_commands:
            raise AttributeError

        return getattr(self.protocol, name)

    def __repr__(self):
        return 'Connection(host=%r, port=%r)' % (self.host, self.port)

    def __del__(self):
        """ When this object is cleaned up. Close the transport. """
        self._closed = True
        if self.protocol.transport:
            self.protocol.transport.close()

########NEW FILE########
__FILENAME__ = cursors
import asyncio
from collections import deque

__all__ = (
    'Cursor',
    'DictCursor',
    'SetCursor',
    'ZCursor',
)


class Cursor:
    """
    Cursor for walking through the results of a :func:`scan
    <asyncio_redis.RedisProtocol.scan>` query.
    """
    def __init__(self, name, scanfunc):
        self._queue = deque()
        self._cursor = 0
        self._name = name
        self._scanfunc = scanfunc
        self._done = False

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self._name)

    @asyncio.coroutine
    def _fetch_more(self):
        """ Get next chunk of keys from Redis """
        if not self._done:
            chunk = yield from self._scanfunc(self._cursor)
            self._cursor = chunk.new_cursor_pos

            if chunk.new_cursor_pos == 0:
                self._done = True

            for i in chunk.items:
                self._queue.append(i)

    @asyncio.coroutine
    def fetchone(self):
        """
        Coroutines that returns the next item.
        It returns `None` after the last item.
        """
        if not self._queue and not self._done:
            yield from self._fetch_more()

        if self._queue:
            return self._queue.popleft()

    @asyncio.coroutine
    def fetchall(self):
        """ Coroutine that reads all the items in one list. """
        results = []

        while True:
            i = yield from self.fetchone()
            if i is None:
                break
            else:
                results.append(i)

        return results


class SetCursor(Cursor):
    """
    Cursor for walking through the results of a :func:`sscan
    <asyncio_redis.RedisProtocol.sscan>` query.
    """
    @asyncio.coroutine
    def fetchall(self):
        result = yield from super().fetchall()
        return set(result)


class DictCursor(Cursor):
    """
    Cursor for walking through the results of a :func:`hscan
    <asyncio_redis.RedisProtocol.hscan>` query.
    """
    def _parse(self, key, value):
        return key, value

    @asyncio.coroutine
    def fetchone(self):
        """
        Get next { key: value } tuple
        It returns `None` after the last item.
        """
        key = yield from super().fetchone()
        value = yield from super().fetchone()

        if key is not None:
            key, value = self._parse(key, value)
            return { key: value }

    @asyncio.coroutine
    def fetchall(self):
        """ Coroutine that reads all the items in one dictionary. """
        results = {}

        while True:
            i = yield from self.fetchone()
            if i is None:
                break
            else:
                results.update(i)

        return results


class ZCursor(DictCursor):
    """
    Cursor for walking through the results of a :func:`zscan
    <asyncio_redis.RedisProtocol.zscan>` query.
    """
    def _parse(self, key, value):
        # Mapping { key: score_as_float }
        return key, float(value)

########NEW FILE########
__FILENAME__ = encoders
"""
The redis protocol only knows about bytes, but we like to have strings inside
Python. This file contains some helper classes for decoding the bytes to
strings and encoding the other way around. We also have a `BytesEncoder`, which
provides raw access to the redis server.
"""

__all__ = (
        'BaseEncoder',
        'BytesEncoder',
        'UTF8Encoder',
)

class BaseEncoder:
    """
    Abstract base class for all encoders.
    """
    #: The native Python type from which we encode, or to which we decode.
    native_type = None

    def encode_from_native(self, data):
        """
        Encodes the native Python type to network bytes.
        Usually this will encode a string object to bytes using the UTF-8
        encoding. You can either override this function, or set the
        `encoding` attribute.
        """
        raise NotImplementedError

    def decode_to_native(self, data):
        """
        Decodes network bytes to a Python native type.
        It should always be the reverse operation of `encode_from_native`.
        """
        raise NotImplementedError


class BytesEncoder(BaseEncoder):
    """
    For raw access to the Redis database.
    """
    #: The native Python type from which we encode, or to which we decode.
    native_type = bytes

    def encode_from_native(self, data):
        return data

    def decode_to_native(self, data):
        return data


class StringEncoder(BaseEncoder):
    """
    Abstract base class for all string encoding encoders.
    """
    #: Redis keeps all values in binary. Set the encoding to be used to
    #: decode/encode Python string values from and to binary.
    encoding = None

    #: The native Python type from which we encode, or to which we decode.
    native_type = str

    def encode_from_native(self, data):
        """ string to bytes """
        return data.encode(self.encoding)

    def decode_to_native(self, data):
        """ bytes to string """
        return data.decode(self.encoding)


class UTF8Encoder(StringEncoder):
    """
    Encode strings to and from utf-8 bytes.
    """
    encoding = 'utf-8'

########NEW FILE########
__FILENAME__ = exceptions
__all__ = (
        'ConnectionLostError',
        'Error',
        'ErrorReply',
        'NoAvailableConnectionsInPoolError',
        'NoRunningScriptError',
        'NotConnectedError',
        'ScriptKilledError',
        'TimeoutError',
        'TransactionError',
)


# See following link for the proper way to create user defined exceptions:
# http://docs.python.org/3.3/tutorial/errors.html#user-defined-exceptions


class Error(Exception):
    """ Base exception. """


class ErrorReply(Exception):
    """ Exception when the redis server returns an error. """


class TransactionError(Error):
    """ Transaction failed. """


class NotConnectedError(Error):
    """ Protocol is not connected. """
    def __init__(self, message='Not connected'):
        super().__init__(message)


class TimeoutError(Error):
    """ Timeout during blocking pop. """


class ConnectionLostError(NotConnectedError):
    """
    Connection lost during query.
    (Special case of ``NotConnectedError``.)
    """
    def __init__(self, exc):
        self.exception = exc


class NoAvailableConnectionsInPoolError(NotConnectedError):
    """
    When the connection pool has no available connections.
    """

class ScriptKilledError(Error):
    """ Script was killed during an evalsha call. """


class NoRunningScriptError(Error):
    """ script_kill was called while no script was running. """

########NEW FILE########
__FILENAME__ = log
import logging


logger = logging.getLogger(__package__)

########NEW FILE########
__FILENAME__ = pool
from .connection import Connection
from .exceptions import NoAvailableConnectionsInPoolError
from .protocol import RedisProtocol, Script

from functools import wraps
import asyncio


__all__ = ('Pool', )


class Pool:
    """
    Pool of connections. Each
    Takes care of setting up the connection and connection pooling.

    When poolsize > 1 and some connections are in use because of transactions
    or blocking requests, the other are preferred.

    ::

        pool = yield from Pool.create(host='localhost', port=6379, poolsize=10)
        result = yield from connection.set('key', 'value')
    """
    @classmethod
    @asyncio.coroutine
    def create(cls, host='localhost', port=6379, password=None, db=0,
               encoder=None, poolsize=1, auto_reconnect=True, loop=None):
        """
        Create a new connection pool instance.

        :param host: Address, either host or unix domain socket path
        :type host: str
        :param port: TCP port. If port is 0 then host assumed to be unix socket path
        :type port: int
        :param password: Redis database password
        :type password: bytes
        :param db: Redis database
        :type db: int
        :param encoder: Encoder to use for encoding to or decoding from redis bytes to a native type.
        :type encoder: :class:`asyncio_redis.encoders.BaseEncoder` instance.
        :param poolsize: The number of parallel connections.
        :type poolsize: int
        :param auto_reconnect: Enable auto reconnect
        :type auto_reconnect: bool
        :param loop: (optional) asyncio event loop.
        """
        self = cls()
        self._host = host
        self._port = port
        self._poolsize = poolsize

        # Create connections
        self._connections = []

        for i in range(poolsize):
            connection = yield from Connection.create(host=host, port=port,
                            password=password, db=db, encoder=encoder,
                            auto_reconnect=auto_reconnect, loop=loop)
            self._connections.append(connection)

        return self

    def __repr__(self):
        return 'Pool(host=%r, port=%r, poolsize=%r)' % (self._host, self._port, self._poolsize)

    @property
    def poolsize(self):
        """ Number of parallel connections in the pool."""
        return self._poolsize

    @property
    def connections_in_use(self):
        """
        Return how many protocols are in use.
        """
        return sum([ 1 for c in self._connections if c.protocol.in_use ])

    @property
    def connections_connected(self):
        """
        The amount of open TCP connections.
        """
        return sum([ 1 for c in self._connections if c.protocol.is_connected ])

    def _get_free_connection(self):
        """
        Return the next protocol instance that's not in use.
        (A protocol in pubsub mode or doing a blocking request is considered busy,
        and can't be used for anything else.)
        """
        self._shuffle_connections()

        for c in self._connections:
            if c.protocol.is_connected and not c.protocol.in_use:
                return c

    def _shuffle_connections(self):
        """
        'shuffle' protocols. Make sure that we devide the load equally among the protocols.
        """
        self._connections = self._connections[1:] + self._connections[:1]

    def __getattr__(self, name):
        """
        Proxy to a protocol. (This will choose a protocol instance that's not
        busy in a blocking request or transaction.)
        """
        connection = self._get_free_connection()

        if connection:
            return getattr(connection, name)
        else:
            raise NoAvailableConnectionsInPoolError('No available connections in the pool: size=%s, in_use=%s, connected=%s' % (
                                self.poolsize, self.connections_in_use, self.connections_connected))


    # Proxy the register_script method, so that the returned object will
    # execute on any available connection in the pool.
    @asyncio.coroutine
    @wraps(RedisProtocol.register_script)
    def register_script(self, script:str) -> Script:
        # Call register_script from the Protocol.
        script = yield from self.__getattr__('register_script')(script)
        assert isinstance(script, Script)

        # Return a new script instead that runs it on any connection of the pool.
        return Script(script.sha, script.code, lambda: self.evalsha)

########NEW FILE########
__FILENAME__ = protocol
#!/usr/bin/env python3
import asyncio
import logging
import types

from asyncio.futures import Future
from asyncio.queues import Queue
from asyncio.streams import StreamReader

from collections import deque
from functools import wraps
from inspect import getfullargspec, formatargspec, getcallargs

from .encoders import BaseEncoder, UTF8Encoder
from .exceptions import (
        ConnectionLostError,
        Error,
        ErrorReply,
        NoRunningScriptError,
        NotConnectedError,
        ScriptKilledError,
        TimeoutError,
        TransactionError,
)
from .log import logger
from .replies import (
        BlockingPopReply,
        ClientListReply,
        ConfigPairReply,
        DictReply,
        EvalScriptReply,
        InfoReply,
        ListReply,
        PubSubReply,
        SetReply,
        StatusReply,
        ZRangeReply,
)


from .cursors import Cursor, SetCursor, DictCursor, ZCursor

__all__ = (
    'RedisProtocol',
    'Transaction',
    'Subscription',
    'Script',

    'ZAggregate',
    'ZScoreBoundary',
)

NoneType = type(None)


class ZScoreBoundary:
    """
    Score boundary for a sorted set.
    for queries like zrangebyscore and similar

    :param value: Value for the boundary.
    :type value: float
    :param exclude_boundary: Exclude the boundary.
    :type exclude_boundary: bool
    """
    def __init__(self, value, exclude_boundary=False):
        assert isinstance(value, float) or value in ('+inf', '-inf')
        self.value = value
        self.exclude_boundary = exclude_boundary

    def __repr__(self):
        return 'ZScoreBoundary(value=%r, exclude_boundary=%r)' % (
                    self.value, self.exclude_boundary)

ZScoreBoundary.MIN_VALUE = ZScoreBoundary('-inf')
ZScoreBoundary.MAX_VALUE = ZScoreBoundary('+inf')


class ZAggregate: # TODO: use the Python 3.4 enum type.
    """
    Aggregation method for zinterstore and zunionstore.
    """
    #: Sum aggregation.
    SUM = 'SUM'

    #: Min aggregation.
    MIN = 'MIN'

    #: Max aggregation.
    MAX = 'MAX'


class PipelinedCall:
    """ Track record for call that is being executed in a protocol. """
    __slots__ = ('cmd', 'is_blocking')

    def __init__(self, cmd, is_blocking):
        self.cmd = cmd
        self.is_blocking = is_blocking


class MultiBulkReply:
    """
    Container for a multi bulk reply.
    """
    def __init__(self, protocol, count, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self.queue = Queue(loop=self._loop)
        self.protocol = protocol
        self.count = int(count)

    def iter_raw(self):
        """
        Iterate over all multi bulk packets. This yields futures that won't
        decode bytes yet.
        """
        for i in range(self.count):
            yield self.queue.get()

    def __iter__(self):
        """
        Iterate over the reply. This yields coroutines of the decoded packets.
        It decodes bytes automatically using protocol.decode_to_native.
        """
        @asyncio.coroutine
        def auto_decode(f):
            result = yield from f
            if isinstance(result, (StatusReply, int, float, MultiBulkReply)):
                # Note that MultiBulkReplies can be nested. e.g. in the 'scan' operation.
                return result
            elif isinstance(result, bytes):
                return self.protocol.decode_to_native(result)
            elif result is None:
                return result
            else:
                raise AssertionError('Invalid type: %r' % type(result))

        for f in self.iter_raw():
            # We should immediately wrap this coroutine in async(), to be sure
            # that the order of the queue remains, even if we wrap it in
            # gather:
            #    f1 = next(multibulk)
            #    f2 = next(multibulk)
            #    r1, r2 = gather(f1, f2)
            yield asyncio.async(auto_decode(f), loop=self._loop)

    def __repr__(self):
        return 'MultiBulkReply(protocol=%r, count=%r)' % (self.protocol, self.count)


class _ScanPart:
    """ Internal: result chunk of a scan operation. """
    def __init__(self, new_cursor_pos, items):
        self.new_cursor_pos = new_cursor_pos
        self.items = items


class PostProcessors:
    """
    At the protocol level, we only know about a few basic classes; they
    include: bool, int, StatusReply, MultiBulkReply and bytes.
    This will return a postprocessor function that turns these into more
    meaningful objects.

    For some methods, we have several post processors. E.g. a list can be
    returned either as a ListReply (which has some special streaming
    functionality), but also as a Python list.
    """
    @classmethod
    def get_all(cls, return_type):
        """
        Return list of (suffix, return_type, post_processor)
        """
        default = cls.get_default(return_type)
        alternate = cls.get_alternate_post_processor(return_type)

        result = [ ('', return_type, default) ]
        if alternate:
            result.append(alternate)
        return result

    @classmethod
    def get_default(cls, return_type):
        """ Give post processor function for return type. """
        return {
                ListReply: cls.multibulk_as_list,
                SetReply: cls.multibulk_as_set,
                DictReply: cls.multibulk_as_dict,

                float: cls.bytes_to_float,
                (float, NoneType): cls.bytes_to_float_or_none,
                NativeType: cls.bytes_to_native,
                (NativeType, NoneType): cls.bytes_to_native_or_none,
                InfoReply: cls.bytes_to_info,
                ClientListReply: cls.bytes_to_clientlist,
                str: cls.bytes_to_str,
                bool: cls.int_to_bool,
                BlockingPopReply: cls.multibulk_as_blocking_pop_reply,
                ZRangeReply: cls.multibulk_as_zrangereply,

                StatusReply: None,
                (StatusReply, NoneType): None,
                int: None,
                (int, NoneType): None,
                ConfigPairReply: cls.multibulk_as_configpair,
                ListOf(bool): cls.multibulk_as_boolean_list,
                _ScanPart: cls.multibulk_as_scanpart,
                EvalScriptReply: cls.any_to_evalscript,

                NoneType: None,
        }[return_type]

    @classmethod
    def get_alternate_post_processor(cls, return_type):
        """ For list/set/dict. Create additional post processors that return
        python classes rather than ListReply/SetReply/DictReply """
        original_post_processor = cls.get_default(return_type)

        if return_type == ListReply:
            @asyncio.coroutine
            def as_list(protocol, result):
                result = yield from original_post_processor(protocol, result)
                return (yield from result.aslist())
            return '_aslist', list, as_list

        elif return_type == SetReply:
            @asyncio.coroutine
            def as_set(protocol, result):
                result = yield from original_post_processor(protocol, result)
                return (yield from result.asset())
            return '_asset', set, as_set

        elif return_type in (DictReply, ZRangeReply):
            @asyncio.coroutine
            def as_dict(protocol, result):
                result = yield from original_post_processor(protocol, result)
                return (yield from result.asdict())
            return '_asdict', dict, as_dict

    # === Post processor handlers below. ===

    @asyncio.coroutine
    def multibulk_as_list(protocol, result):
        assert isinstance(result, MultiBulkReply)
        return ListReply(result)

    @asyncio.coroutine
    def multibulk_as_boolean_list(protocol, result):
        # Turn the array of integers into booleans.
        assert isinstance(result, MultiBulkReply)
        values = yield from ListReply(result).aslist()
        return [ bool(v) for v in values ]

    @asyncio.coroutine
    def multibulk_as_set(protocol, result):
        assert isinstance(result, MultiBulkReply)
        return SetReply(result)

    @asyncio.coroutine
    def multibulk_as_dict(protocol, result):
        assert isinstance(result, MultiBulkReply)
        return DictReply(result)

    @asyncio.coroutine
    def multibulk_as_zrangereply(protocol, result):
        assert isinstance(result, MultiBulkReply)
        return ZRangeReply(result)

    @asyncio.coroutine
    def multibulk_as_blocking_pop_reply(protocol, result):
        if result is None:
            raise TimeoutError('Timeout in blocking pop')
        else:
            assert isinstance(result, MultiBulkReply)
            list_name, value = yield from ListReply(result).aslist()
            return BlockingPopReply(list_name, value)

    @asyncio.coroutine
    def multibulk_as_configpair(protocol, result):
        assert isinstance(result, MultiBulkReply)
        parameter, value = yield from ListReply(result).aslist()
        return ConfigPairReply(parameter, value)

    @asyncio.coroutine
    def multibulk_as_scanpart(protocol, result):
        """
        Process scanpart result.
        This is a multibulk reply of length two, where the first item is the
        new cursor position and the second item is a nested multi bulk reply
        containing all the elements.
        """
        # Get outer multi bulk reply.
        assert isinstance(result, MultiBulkReply)
        new_cursor_pos, items_bulk = yield from ListReply(result).aslist()
        assert isinstance(items_bulk, MultiBulkReply)

        # Read all items for scan chunk in memory. This is fine, because it's
        # transmitted in chunks of about 10.
        items = yield from ListReply(items_bulk).aslist()
        return _ScanPart(int(new_cursor_pos), items)

    @asyncio.coroutine
    def bytes_to_info(protocol, result):
        assert isinstance(result, bytes)
        return InfoReply(result)

    @asyncio.coroutine
    def bytes_to_clientlist(protocol, result):
        assert isinstance(result, bytes)
        return ClientListReply(result)

    @asyncio.coroutine
    def int_to_bool(protocol, result):
        assert isinstance(result, int)
        return bool(result) # Convert int to bool

    @asyncio.coroutine
    def bytes_to_native(protocol, result):
        assert isinstance(result, bytes)
        return protocol.decode_to_native(result)

    @asyncio.coroutine
    def bytes_to_str(protocol, result):
        assert isinstance(result, bytes)
        return result.decode('ascii')

    @asyncio.coroutine
    def bytes_to_native_or_none(protocol, result):
        if result is None:
            return result
        else:
            assert isinstance(result, bytes)
            return protocol.decode_to_native(result)

    @asyncio.coroutine
    def bytes_to_float_or_none(protocol, result):
        if result is None:
            return result
        assert isinstance(result, bytes)
        return float(result)

    @asyncio.coroutine
    def bytes_to_float(protocol, result):
        assert isinstance(result, bytes)
        return float(result)

    @asyncio.coroutine
    def any_to_evalscript(protocol, result):
        # Result can be native, int, MultiBulkReply or even a nested structure
        assert isinstance(result, (int, bytes, MultiBulkReply, NoneType))
        return EvalScriptReply(protocol, result)


class ListOf:
    """ Annotation helper for protocol methods. """
    def __init__(self, type_):
        self.type = type_

    def __repr__(self):
        return 'ListOf(%r)' % self.type

    def __eq__(self, other):
        return isinstance(other, ListOf) and other.type == self.type

    def __hash__(self):
        return hash((ListOf, self.type))


class NativeType:
    """
    Constant which represents the native Python type that's used.
    """
    def __new__(cls):
        raise Exception('NativeType is not meant to be initialized.')


class CommandCreator:
    """
    Utility for creating a wrapper around the Redis protocol methods.
    This will also do type checking.

    This wrapper handles (optionally) post processing of the returned data and
    implements some logic where commands behave different in case of a
    transaction or pubsub.

    Warning: We use the annotations of `method` extensively for type checking
             and determining which post processor to choose.
    """
    def __init__(self, method):
        self.method = method

    @property
    def specs(self):
       """ Argspecs """
       return getfullargspec(self.method)

    @property
    def return_type(self):
        """ Return type as defined in the method's annotation. """
        return self.specs.annotations.get('return', None)

    @property
    def params(self):
        return { k:v for k, v in self.specs.annotations.items() if k != 'return' }

    @classmethod
    def get_real_type(cls, protocol, type_):
        """
        Given a protocol instance, and type annotation, return something that
        we can pass to isinstance for the typechecking.
        """
        # If NativeType was given, replace it with the type of the protocol
        # itself.
        if isinstance(type_, tuple):
            return tuple(cls.get_real_type(protocol, t) for t in type_)

        if type_ == NativeType:
            return protocol.native_type
        elif isinstance(type_, ListOf):
            return (list, types.GeneratorType) # We don't check the content of the list.
        else:
            return type_

    def _create_input_typechecker(self):
        """ Return function that does typechecking on input data. """
        params = self.params

        if params:
            def typecheck_input(protocol, *a, **kw):
                """
                Given a protocol instance and *a/**kw of this method, raise TypeError
                when the signature doesn't match.
                """
                if protocol.enable_typechecking:
                    for name, value in getcallargs(self.method, None, *a, **kw).items():
                        if name in params:
                            real_type = self.get_real_type(protocol, params[name])
                            if not isinstance(value, real_type):
                                raise TypeError('RedisProtocol.%s received %r, expected %r' %
                                                (self.method.__name__, type(value).__name__, real_type))
        else:
            def typecheck_input(protocol, *a, **kw):
                pass

        return typecheck_input

    def _create_return_typechecker(self, return_type):
        """ Return function that does typechecking on output data. """
        if return_type and not isinstance(return_type, str): # Exclude 'Transaction'/'Subscription' which are 'str'
            def typecheck_return(protocol, result):
                """
                Given protocol and result value. Raise TypeError if the result is of the wrong type.
                """
                if protocol.enable_typechecking:
                    expected_type = self.get_real_type(protocol, return_type)
                    if not isinstance(result, expected_type):
                        raise TypeError('Got unexpected return type %r in RedisProtocol.%s, expected %r' %
                                        (type(result).__name__, self.method.__name__, expected_type))
        else:
            def typecheck_return(protocol, result):
                pass

        return typecheck_return

    def _get_docstring(self, suffix, return_type):
        # Append the real signature as the first line in the docstring.
        # (This will make the sphinx docs show the real signature instead of
        # (*a, **kw) of the wrapper.)
        # (But don't put the anotations inside the copied signature, that's rather
        # ugly in the docs.)
        signature = formatargspec(* self.specs[:6])

        # Use function annotations to generate param documentation.

        def get_name(type_):
            """ Turn type annotation into doc string. """
            try:
                return {
                    BlockingPopReply: ":class:`BlockingPopReply <asyncio_redis.replies.BlockingPopReply>`",
                    ConfigPairReply: ":class:`ConfigPairReply <asyncio_redis.replies.ConfigPairReply>`",
                    DictReply: ":class:`DictReply <asyncio_redis.replies.DictReply>`",
                    InfoReply: ":class:`InfoReply <asyncio_redis.replies.InfoReply>`",
                    ClientListReply: ":class:`InfoReply <asyncio_redis.replies.ClientListReply>`",
                    ListReply: ":class:`ListReply <asyncio_redis.replies.ListReply>`",
                    MultiBulkReply: ":class:`MultiBulkReply <asyncio_redis.replies.MultiBulkReply>`",
                    NativeType: "Native Python type, as defined by :attr:`~asyncio_redis.encoders.BaseEncoder.native_type`",
                    NoneType: "None",
                    SetReply: ":class:`SetReply <asyncio_redis.replies.SetReply>`",
                    StatusReply: ":class:`StatusReply <asyncio_redis.replies.StatusReply>`",
                    ZRangeReply: ":class:`ZRangeReply <asyncio_redis.replies.ZRangeReply>`",
                    ZScoreBoundary: ":class:`ZScoreBoundary <asyncio_redis.replies.ZScoreBoundary>`",
                    EvalScriptReply: ":class:`EvalScriptReply <asyncio_redis.replies.EvalScriptReply>`",
                    Cursor: ":class:`Cursor <asyncio_redis.cursors.Cursor>`",
                    SetCursor: ":class:`SetCursor <asyncio_redis.cursors.SetCursor>`",
                    DictCursor: ":class:`DictCursor <asyncio_redis.cursors.DictCursor>`",
                    ZCursor: ":class:`ZCursor <asyncio_redis.cursors.ZCursor>`",
                    _ScanPart: ":class:`_ScanPart",
                    int: 'int',
                    bool: 'bool',
                    dict: 'dict',
                    float: 'float',
                    str: 'str',
                    bytes: 'bytes',

                    list: 'list',
                    set: 'set',
                    dict: 'dict',

                    # XXX: Because of circulare references, we cannot use the real types here.
                    'Transaction': ":class:`asyncio_redis.Transaction`",
                    'Subscription': ":class:`asyncio_redis.Subscription`",
                    'Script': ":class:`~asyncio_redis.Script`",
                }[type_]
            except KeyError:
                if isinstance(type_, ListOf):
                    return "List or iterable of %s" % get_name(type_.type)

                elif isinstance(type_, tuple):
                    return ' or '.join(get_name(t) for t in type_)
                else:
                    raise Exception('Unknown annotation %r' % type_)
                    #return "``%s``" % type_.__name__

        def get_param(k, v):
            return ':param %s: %s\n' % (k, get_name(v))

        params_str = [ get_param(k, v) for k, v in self.params.items() ]
        returns = ':returns: (Future of) %s\n' % get_name(return_type) if return_type else ''

        return '%s%s\n%s\n\n%s%s' % (
                self.method.__name__ + suffix, signature,
                self.method.__doc__,
                ''.join(params_str),
                returns
                )

    def get_methods(self):
        """
        Return all the methods to be used in the RedisProtocol class.
        """
        return [ ('', self._get_wrapped_method(None, '', self.return_type)) ]

    def _get_wrapped_method(self, post_process, suffix, return_type):
        """
        Return the wrapped method for use in the `RedisProtocol` class.
        """
        typecheck_input = self._create_input_typechecker()
        typecheck_return = self._create_return_typechecker(return_type)
        method = self.method

        # Wrap it into a check which allows this command to be run either
        # directly on the protocol, outside of transactions or from the
        # transaction object.
        @wraps(method)
        def wrapper(protocol_self, *a, **kw):
            # When calling from a transaction
            if protocol_self.in_transaction:
                # The first arg should be the transaction # object.
                if not a or a[0] != protocol_self._transaction:
                    raise Error('Cannot run command inside transaction (use the Transaction object instead)')

                # In case of a transaction, we receive a Future from the command.
                else:
                    typecheck_input(protocol_self, *a[1:], **kw)
                    future = yield from method(protocol_self, *a[1:], **kw)
                    future2 = Future(loop=protocol_self._loop)

                    # Typecheck the future when the result is available.

                    @asyncio.coroutine
                    def done(result):
                        if post_process:
                            result = yield from post_process(protocol_self, result)
                        typecheck_return(protocol_self, result)
                        future2.set_result(result)

                    future.add_done_callback(lambda f: asyncio.async(done(f.result()), loop=protocol_self._loop))

                    return future2

            # When calling from a pubsub context
            elif protocol_self.in_pubsub:
                if not a or a[0] != protocol_self._subscription:
                    raise Error('Cannot run command inside pubsub subscription.')

                else:
                    typecheck_input(protocol_self, *a[1:], **kw)
                    result = yield from method(protocol_self, *a[1:], **kw)
                    if post_process:
                        result = yield from post_process(protocol_self, result)
                    typecheck_return(protocol_self, result)
                    return (result)

            else:
                typecheck_input(protocol_self, *a, **kw)
                result = yield from method(protocol_self, *a, **kw)
                if post_process:
                    result = yield from post_process(protocol_self, result)
                typecheck_return(protocol_self, result)
                return (result)

        wrapper.__doc__ = self._get_docstring(suffix, return_type)
        return wrapper


class QueryCommandCreator(CommandCreator):
    """
    Like `CommandCreator`, but for methods registered with `_query_command`.
    This are the methods that cause commands to be send to the server.

    Most of the commands get a reply from the server that needs to be post
    processed to get the right Python type. We inspect here the
    'returns'-annotation to determine the correct post processor.
    """
    def get_methods(self):
        # (Some commands, e.g. those that return a ListReply can generate
        # multiple protocol methods.  One that does return the ListReply, but
        # also one with the 'aslist' suffix that returns a Python list.)
        all_post_processors = PostProcessors.get_all(self.return_type)
        result = []

        for suffix, return_type, post_processor in all_post_processors:
            result.append( (suffix, self._get_wrapped_method(post_processor, suffix, return_type)) )

        return result

_SMALL_INTS = list(str(i).encode('ascii') for i in range(1000))


# List of all command methods.
_all_commands = []

class _command:
    """ Mark method as command (to be passed through CommandCreator for the
    creation of a protocol method) """
    creator = CommandCreator

    def __init__(self, method):
        self.method = method


class _query_command(_command):
    """
    Mark method as query command: This will pass through QueryCommandCreator.

    NOTE: be sure to choose the correct 'returns'-annotation. This will automatially
    determine the correct post processor function in :class:`PostProcessors`.
    """
    creator = QueryCommandCreator

    def __init__(self, method):
        super().__init__(method)


class _RedisProtocolMeta(type):
    """
    Metaclass for `RedisProtocol` which applies the _command decorator.
    """
    def __new__(cls, name, bases, attrs):
        for attr_name, value in dict(attrs).items():
            if isinstance(value, _command):
                creator = value.creator(value.method)
                for suffix, method in creator.get_methods():
                    attrs[attr_name + suffix] =  method

                    # Register command.
                    _all_commands.append(attr_name + suffix)

        return type.__new__(cls, name, bases, attrs)


class RedisProtocol(asyncio.Protocol, metaclass=_RedisProtocolMeta):
    """
    The Redis Protocol implementation.

    ::

        self.loop = asyncio.get_event_loop()
        transport, protocol = yield from loop.create_connection(RedisProtocol, 'localhost', 6379)

    :param password: Redis database password
    :type password: Native Python type as defined by the ``encoder`` parameter
    :param encoder: Encoder to use for encoding to or decoding from redis bytes to a native type.
                    (Defaults to :class:`~asyncio_redis.encoders.UTF8Encoder`)
    :type encoder: :class:`~asyncio_redis.encoders.BaseEncoder` instance.
    :param db: Redis database
    :type db: int
    :param enable_typechecking: When ``True``, check argument types for all
                                redis commands. Normally you want to have this
                                enabled.
    :type enable_typechecking: bool
    """
    def __init__(self, password=None, db=0, encoder=None, connection_lost_callback=None, enable_typechecking=True, loop=None):
        if encoder is None:
            encoder = UTF8Encoder()

        assert isinstance(db, int)
        assert isinstance(encoder, BaseEncoder)
        assert encoder.native_type, 'Encoder.native_type not defined'
        assert not password or isinstance(password, encoder.native_type)

        self.password = password
        self.db = db
        self._connection_lost_callback = connection_lost_callback
        self._loop = loop or asyncio.get_event_loop()

        # Take encode / decode settings from encoder
        self.encode_from_native = encoder.encode_from_native
        self.decode_to_native = encoder.decode_to_native
        self.native_type = encoder.native_type
        self.enable_typechecking = enable_typechecking

        self.transport = None
        self._queue = deque() # Input parser queues
        self._messages_queue = None # Pubsub queue
        self._is_connected = False # True as long as the underlying transport is connected.

        # Pubsub state
        self._in_pubsub = False
        self._subscription = None
        self._pubsub_channels = set() # Set of channels
        self._pubsub_patterns = set() # Set of patterns

        # Transaction related stuff.
        self._in_transaction = False
        self._transaction = None
        self._transaction_response_queue = None # Transaction answer queue

        self._line_received_handlers = {
            b'+': self._handle_status_reply,
            b'-': self._handle_error_reply,
            b'$': self._handle_bulk_reply,
            b'*': self._handle_multi_bulk_reply,
            b':': self._handle_int_reply,
        }

    def connection_made(self, transport):
        self.transport = transport
        self._is_connected = True
        logger.log(logging.INFO, 'Redis connection made')

        # Pipelined calls
        self._pipelined_calls = set() # Set of all the pipelined calls.

        # Start parsing reader stream.
        self._reader = StreamReader(loop=self._loop)
        self._reader.set_transport(transport)
        self._reader_f = asyncio.async(self._reader_coroutine(), loop=self._loop)

        @asyncio.coroutine
        def initialize():
            # If a password or database was been given, first connect to that one.
            if self.password:
                yield from self.auth(self.password)

            if self.db:
                yield from self.select(self.db)

            #  If we are in pubsub mode, send channel subscriptions again.
            if self._in_pubsub:
                if self._pubsub_channels:
                    yield from self._subscribe(self._subscription, list(self._pubsub_channels)) # TODO: unittest this

                if self._pubsub_patterns:
                    yield from self._psubscribe(self._subscription, list(self._pubsub_patterns))

        asyncio.async(initialize(), loop=self._loop)

    def data_received(self, data):
        """ Process data received from Redis server.  """
        self._reader.feed_data(data)

    def _encode_int(self, value:int) -> bytes:
        """ Encodes an integer to bytes. (always ascii) """
        if 0 < value < 1000: # For small values, take pre-encoded string.
            return _SMALL_INTS[value]
        else:
            return str(value).encode('ascii')

    def _encode_float(self, value:float) -> bytes:
        """ Encodes a float to bytes. (always ascii) """
        return str(value).encode('ascii')

    def _encode_zscore_boundary(self, value:ZScoreBoundary) -> str:
        """ Encodes a zscore boundary. (always ascii) """
        if isinstance(value.value, str):
            return str(value.value).encode('ascii') # +inf and -inf
        elif value.exclude_boundary:
            return str("(%f" % value.value).encode('ascii')
        else:
            return str("%f" % value.value).encode('ascii')

    def eof_received(self):
        logger.log(logging.INFO, 'EOF received in RedisProtocol')
        self._reader.feed_eof()

    def connection_lost(self, exc):
        if exc is None:
            self._reader.feed_eof()
        else:
            logger.info("Connection lost with exec: %s" % exc)
            self._reader.set_exception(exc)

        if self._reader_f:
            self._reader_f.cancel()

        self._is_connected = False
        self.transport = None
        self._reader = None
        self._reader_f = None

        # Raise exception on all waiting futures.
        while self._queue:
            f = self._queue.popleft()
            if not f.cancelled():
                f.set_exception(ConnectionLostError(exc))

        logger.log(logging.INFO, 'Redis connection lost')

        # Call connection_lost callback
        if self._connection_lost_callback:
            self._connection_lost_callback()

    # Request state

    @property
    def in_blocking_call(self):
        """ True when waiting for answer to blocking command. """
        return any(c.is_blocking for c in self._pipelined_calls)

    @property
    def in_pubsub(self):
        """ True when the protocol is in pubsub mode. """
        return self._in_pubsub

    @property
    def in_transaction(self):
        """ True when we're inside a transaction. """
        return self._in_transaction

    @property
    def in_use(self):
        """ True when this protocol is in use. """
        return self.in_blocking_call or self.in_pubsub or self.in_transaction

    @property
    def is_connected(self):
        """ True when the underlying transport is connected. """
        return self._is_connected

    # Handle replies

    @asyncio.coroutine
    def _reader_coroutine(self):
        """
        Coroutine which reads input from the stream reader and processes it.
        """
        while True:
            try:
                yield from self._handle_item(self._push_answer)
            except ConnectionLostError:
                return

    @asyncio.coroutine
    def _handle_item(self, cb):
        c = yield from self._reader.readexactly(1)
        if c:
            yield from self._line_received_handlers[c](cb)
        else:
            raise ConnectionLostError(None)

    @asyncio.coroutine
    def _handle_status_reply(self, cb):
        line = (yield from self._reader.readline()).rstrip(b'\r\n')
        cb(StatusReply(line.decode('ascii')))

    @asyncio.coroutine
    def _handle_int_reply(self, cb):
        line = (yield from self._reader.readline()).rstrip(b'\r\n')
        cb(int(line))

    @asyncio.coroutine
    def _handle_error_reply(self, cb):
        line = (yield from self._reader.readline()).rstrip(b'\r\n')
        cb(ErrorReply(line.decode('ascii')))

    @asyncio.coroutine
    def _handle_bulk_reply(self, cb):
        length = int((yield from self._reader.readline()).rstrip(b'\r\n'))
        if length == -1:
            # None bulk reply
            cb(None)
        else:
            # Read data
            data = yield from self._reader.readexactly(length)
            cb(data)

            # Ignore trailing newline.
            remaining = yield from self._reader.readline()
            assert remaining.rstrip(b'\r\n') == b''

    @asyncio.coroutine
    def _handle_multi_bulk_reply(self, cb):
                # NOTE: the reason for passing the callback `cb` in here is
                #       mainly because we want to return the result object
                #       especially in this case before the input is read
                #       completely. This allows a streaming API.
        count = int((yield from self._reader.readline()).rstrip(b'\r\n'))

        # Handle multi-bulk none.
        # (Used when a transaction exec fails.)
        if count == -1:
            cb(None)
            return

        reply = MultiBulkReply(self, count, loop=self._loop)

        # Return the empty queue immediately as an answer.
        if self._in_pubsub:
            asyncio.async(self._handle_pubsub_multibulk_reply(reply), loop=self._loop)
        else:
            cb(reply)

        # Wait for all multi bulk reply content.
        for i in range(count):
            yield from self._handle_item(reply.queue.put_nowait)

    @asyncio.coroutine
    def _handle_pubsub_multibulk_reply(self, multibulk_reply):
        result = yield from ListReply(multibulk_reply).aslist()
        assert result[0] in ('message', 'subscribe', 'unsubscribe', 'psubscribe', 'punsubscribe')

        if result[0] == 'message':
            channel, value = result[1], result[2]
            yield from self._subscription._messages_queue.put(PubSubReply(channel, value))

        # We can safely ignore 'subscribe'/'unsubscribe' replies at this point,
        # they don't contain anything really useful.

    # Redis operations.

    def _send_command(self, args):
        """
        Send Redis request command.
        `args` should be a list of bytes to be written to the transport.
        """
        # Create write buffer.
        data = []

        # NOTE: First, I tried to optimize by also flushing this buffer in
        # between the looping through the args. However, I removed that as the
        # advantage was really small. Even when some commands like `hmset`
        # could accept a generator instead of a list/dict, we would need to
        # read out the whole generator in memory in order to write the number
        # of arguments first.

        # Serialize and write header (number of arguments.)
        data += [ b'*', self._encode_int(len(args)), b'\r\n' ]

        # Write arguments.
        for arg in args:
            data += [ b'$', self._encode_int(len(arg)), b'\r\n', arg, b'\r\n' ]

        # Flush the last part
        self.transport.write(b''.join(data))

    @asyncio.coroutine
    def _get_answer(self, answer_f, _bypass=False, call=None):
        """
        Return an answer to the pipelined query.
        (Or when we are in a transaction, return a future for the answer.)
        """
        # Wait for the answer to come in
        result = yield from answer_f

        if self._in_transaction and not _bypass:
            # When the connection is inside a transaction, the query will be queued.
            if result != StatusReply('QUEUED'):
                raise Error('Expected to receive QUEUED for query in transaction, received %r.' % result)

            # Return a future which will contain the result when it arrives.
            f = Future(loop=self._loop)
            self._transaction_response_queue.append( (f, call) )
            return f
        else:
            if call:
                self._pipelined_calls.remove(call)
            return result

    def _push_answer(self, answer):
        """
        Answer future at the queue.
        """
        f = self._queue.popleft()

        if isinstance(answer, Exception):
            f.set_exception(answer)
        elif f.cancelled():
            # Received an answer from Redis, for a query which `Future` got
            # already cancelled. Don't call set_result, that would raise an
            # `InvalidStateError` otherwise.
            pass
        else:
            f.set_result(answer)

    @asyncio.coroutine
    def _query(self, *args, _bypass=False, set_blocking=False):
        """
        Wrapper around both _send_command and _get_answer.

        Coroutine that sends the query to the server, and returns the reply.
        (Where the reply is a simple Redis type: these are `int`,
        `StatusReply`, `bytes` or `MultiBulkReply`) When we are in a transaction,
        this coroutine will return a `Future` of the actual result.
        """
        if not self._is_connected:
            raise NotConnectedError

        call = PipelinedCall(args[0], set_blocking)
        self._pipelined_calls.add(call)

        # Add a new future to our answer queue.
        answer_f = Future(loop=self._loop)
        self._queue.append(answer_f)

        # Send command
        self._send_command(args)

        # Receive answer.
        result = yield from self._get_answer(answer_f, _bypass=_bypass, call=call)
        return result

    # Internal

    @_query_command
    def auth(self, password:NativeType) -> StatusReply:
        """ Authenticate to the server """
        self.password = password
        return self._query(b'auth', self.encode_from_native(password))

    @_query_command
    def select(self, db:int) -> StatusReply:
        """ Change the selected database for the current connection """
        self.db = db
        return self._query(b'select', self._encode_int(db))

    # Strings

    @_query_command
    def set(self, key:NativeType, value:NativeType,
            expire:(int, NoneType)=None, pexpire:(int, NoneType)=None,
            only_if_not_exists:bool=False, only_if_exists:bool=False) -> (StatusReply, NoneType):
        """
        Set the string value of a key

        ::

            yield from protocol.set('key', 'value')
            result = yield from protocol.get('key')
            assert result == 'value'

        To set a value and its expiration, only if key not exists, do:

        ::

            yield from protocol.set('key', 'value', expire=1, only_if_not_exists=True)

        This will send: ``SET key value EX 1 NX`` at the network.
        To set value and its expiration in milliseconds, but only if key already exists:

        ::

            yield from protocol.set('key', 'value', pexpire=1000, only_if_exists=True)
        """
        params = [
            b'set',
            self.encode_from_native(key),
            self.encode_from_native(value)
        ]
        if expire is not None:
            params.extend((b'ex', self._encode_int(expire)))
        if pexpire is not None:
            params.extend((b'px', self._encode_int(pexpire)))
        if only_if_not_exists and only_if_exists:
            raise ValueError("only_if_not_exists and only_if_exists cannot be true simultaniously")
        if only_if_not_exists:
            params.append(b'nx')
        if only_if_exists:
            params.append(b'xx')

        return self._query(*params)

    @_query_command
    def setex(self, key:NativeType, seconds:int, value:NativeType) -> StatusReply:
        """ Set the string value of a key with expire """
        return self._query(b'setex', self.encode_from_native(key),
                           self._encode_int(seconds), self.encode_from_native(value))

    @_query_command
    def setnx(self, key:NativeType, value:NativeType) -> bool:
        """ Set the string value of a key if it does not exist.
        Returns True if value is successfully set """
        return self._query(b'setnx', self.encode_from_native(key), self.encode_from_native(value))

    @_query_command
    def get(self, key:NativeType) -> (NativeType, NoneType):
        """ Get the value of a key """
        return self._query(b'get', self.encode_from_native(key))

    @_query_command
    def mget(self, keys:ListOf(NativeType)) -> ListReply:
        """ Returns the values of all specified keys. """
        return self._query(b'mget', *map(self.encode_from_native, keys))

    @_query_command
    def strlen(self, key:NativeType) -> int:
        """ Returns the length of the string value stored at key. An error is
        returned when key holds a non-string value.  """
        return self._query(b'strlen', self.encode_from_native(key))

    @_query_command
    def append(self, key:NativeType, value:NativeType) -> int:
        """ Append a value to a key """
        return self._query(b'append', self.encode_from_native(key), self.encode_from_native(value))

    @_query_command
    def getset(self, key:NativeType, value:NativeType) -> (NativeType, NoneType):
        """ Set the string value of a key and return its old value """
        return self._query(b'getset', self.encode_from_native(key), self.encode_from_native(value))

    @_query_command
    def incr(self, key:NativeType) -> int:
        """ Increment the integer value of a key by one """
        return self._query(b'incr', self.encode_from_native(key))

    @_query_command
    def incrby(self, key:NativeType, increment:int) -> int:
        """ Increment the integer value of a key by the given amount """
        return self._query(b'incrby', self.encode_from_native(key), self._encode_int(increment))

    @_query_command
    def decr(self, key:NativeType) -> int:
        """ Decrement the integer value of a key by one """
        return self._query(b'decr', self.encode_from_native(key))

    @_query_command
    def decrby(self, key:NativeType, increment:int) -> int:
        """ Decrement the integer value of a key by the given number """
        return self._query(b'decrby', self.encode_from_native(key), self._encode_int(increment))

    @_query_command
    def randomkey(self) -> NativeType:
        """ Return a random key from the keyspace """
        return self._query(b'randomkey')

    @_query_command
    def exists(self, key:NativeType) -> bool:
        """ Determine if a key exists """
        return self._query(b'exists', self.encode_from_native(key))

    @_query_command
    def delete(self, keys:ListOf(NativeType)) -> int:
        """ Delete a key """
        return self._query(b'del', *map(self.encode_from_native, keys))

    @_query_command
    def move(self, key:NativeType, database:int) -> int:
        """ Move a key to another database """
        return self._query(b'move', self.encode_from_native(key), self._encode_int(database)) # TODO: unittest

    @_query_command
    def rename(self, key:NativeType, newkey:NativeType) -> StatusReply:
        """ Rename a key """
        return self._query(b'rename', self.encode_from_native(key), self.encode_from_native(newkey))

    @_query_command
    def renamenx(self, key:NativeType, newkey:NativeType) -> int:
        """ Rename a key, only if the new key does not exist
        (Returns 1 if the key was successfully renamed.) """
        return self._query(b'renamenx', self.encode_from_native(key), self.encode_from_native(newkey))

    @_query_command
    def bitop_and(self, destkey:NativeType, srckeys:ListOf(NativeType)) -> int:
        """ Perform a bitwise AND operation between multiple keys. """
        return self._bitop(b'and', destkey, srckeys)

    @_query_command
    def bitop_or(self, destkey:NativeType, srckeys:ListOf(NativeType)) -> int:
        """ Perform a bitwise OR operation between multiple keys. """
        return self._bitop(b'or', destkey, srckeys)

    @_query_command
    def bitop_xor(self, destkey:NativeType, srckeys:ListOf(NativeType)) -> int:
        """ Perform a bitwise XOR operation between multiple keys. """
        return self._bitop(b'xor', destkey, srckeys)

    def _bitop(self, op, destkey, srckeys):
        return self._query(b'bitop', op, self.encode_from_native(destkey), *map(self.encode_from_native, srckeys))

    @_query_command
    def bitop_not(self, destkey:NativeType, key:NativeType) -> int:
        """ Perform a bitwise NOT operation between multiple keys. """
        return self._query(b'bitop', b'not', self.encode_from_native(destkey), self.encode_from_native(key))

    @_query_command
    def bitcount(self, key:NativeType, start:int=0, end:int=-1) -> int:
        """ Count the number of set bits (population counting) in a string. """
        return self._query(b'bitcount', self.encode_from_native(key), self._encode_int(start), self._encode_int(end))

    @_query_command
    def getbit(self, key:NativeType, offset:int) -> bool:
        """ Returns the bit value at offset in the string value stored at key """
        return self._query(b'getbit', self.encode_from_native(key), self._encode_int(offset))

    @_query_command
    def setbit(self, key:NativeType, offset:int, value:bool) -> bool:
        """ Sets or clears the bit at offset in the string value stored at key """
        return self._query(b'setbit', self.encode_from_native(key), self._encode_int(offset),
                    self._encode_int(int(value)))

    # Keys

    @_query_command
    def keys(self, pattern:NativeType) -> ListReply:
        """
        Find all keys matching the given pattern.

        .. note:: Also take a look at :func:`~asyncio_redis.RedisProtocol.scan`.
        """
        return self._query(b'keys', self.encode_from_native(pattern))

#    @_query_command
#    def dump(self, key:NativeType):
#        """ Return a serialized version of the value stored at the specified key. """
#        # Dump does not work yet. It shouldn't be decoded using utf-8'
#        raise NotImplementedError('Not supported.')

    @_query_command
    def expire(self, key:NativeType, seconds:int) -> int:
        """ Set a key's time to live in seconds """
        return self._query(b'expire', self.encode_from_native(key), self._encode_int(seconds))

    @_query_command
    def pexpire(self, key:NativeType, milliseconds:int) -> int:
        """ Set a key's time to live in milliseconds """
        return self._query(b'pexpire', self.encode_from_native(key), self._encode_int(milliseconds))

    @_query_command
    def expireat(self, key:NativeType, timestamp:int) -> int:
        """ Set the expiration for a key as a UNIX timestamp """
        return self._query(b'expireat', self.encode_from_native(key), self._encode_int(timestamp))

    @_query_command
    def pexpireat(self, key:NativeType, milliseconds_timestamp:int) -> int:
        """ Set the expiration for a key as a UNIX timestamp specified in milliseconds """
        return self._query(b'pexpireat', self.encode_from_native(key), self._encode_int(milliseconds_timestamp))

    @_query_command
    def persist(self, key:NativeType) -> int:
        """ Remove the expiration from a key """
        return self._query(b'persist', self.encode_from_native(key))

    @_query_command
    def ttl(self, key:NativeType) -> int:
        """ Get the time to live for a key """
        return self._query(b'ttl', self.encode_from_native(key))

    @_query_command
    def pttl(self, key:NativeType) -> int:
        """ Get the time to live for a key in milliseconds """
        return self._query(b'pttl', self.encode_from_native(key))

    # Set operations

    @_query_command
    def sadd(self, key:NativeType, members:ListOf(NativeType)) -> int:
        """ Add one or more members to a set """
        return self._query(b'sadd', self.encode_from_native(key), *map(self.encode_from_native, members))

    @_query_command
    def srem(self, key:NativeType, members:ListOf(NativeType)) -> int:
        """ Remove one or more members from a set """
        return self._query(b'srem', self.encode_from_native(key), *map(self.encode_from_native, members))

    @_query_command
    def spop(self, key:NativeType) -> NativeType:
        """ Removes and returns a random element from the set value stored at key. """
        return self._query(b'spop', self.encode_from_native(key))

    @_query_command
    def srandmember(self, key:NativeType, count:int=1) -> SetReply:
        """ Get one or multiple random members from a set
        (Returns a list of members, even when count==1) """
        return self._query(b'srandmember', self.encode_from_native(key), self._encode_int(count))

    @_query_command
    def sismember(self, key:NativeType, value:NativeType) -> bool:
        """ Determine if a given value is a member of a set """
        return self._query(b'sismember', self.encode_from_native(key), self.encode_from_native(value))

    @_query_command
    def scard(self, key:NativeType) -> int:
        """ Get the number of members in a set """
        return self._query(b'scard', self.encode_from_native(key))

    @_query_command
    def smembers(self, key:NativeType) -> SetReply:
        """ Get all the members in a set """
        return self._query(b'smembers', self.encode_from_native(key))

    @_query_command
    def sinter(self, keys:ListOf(NativeType)) -> SetReply:
        """ Intersect multiple sets """
        return self._query(b'sinter', *map(self.encode_from_native, keys))

    @_query_command
    def sinterstore(self, destination:NativeType, keys:ListOf(NativeType)) -> int:
        """ Intersect multiple sets and store the resulting set in a key """
        return self._query(b'sinterstore', self.encode_from_native(destination), *map(self.encode_from_native, keys))

    @_query_command
    def sdiff(self, keys:ListOf(NativeType)) -> SetReply:
        """ Subtract multiple sets """
        return self._query(b'sdiff', *map(self.encode_from_native, keys))

    @_query_command
    def sdiffstore(self, destination:NativeType, keys:ListOf(NativeType)) -> int:
        """ Subtract multiple sets and store the resulting set in a key """
        return self._query(b'sdiffstore', self.encode_from_native(destination),
                *map(self.encode_from_native, keys))

    @_query_command
    def sunion(self, keys:ListOf(NativeType)) -> SetReply:
        """ Add multiple sets """
        return self._query(b'sunion', *map(self.encode_from_native, keys))

    @_query_command
    def sunionstore(self, destination:NativeType, keys:ListOf(NativeType)) -> int:
        """ Add multiple sets and store the resulting set in a key """
        return self._query(b'sunionstore', self.encode_from_native(destination), *map(self.encode_from_native, keys))

    @_query_command
    def smove(self, source:NativeType, destination:NativeType, value:NativeType) -> int:
        """ Move a member from one set to another """
        return self._query(b'smove', self.encode_from_native(source), self.encode_from_native(destination), self.encode_from_native(value))

    # List operations

    @_query_command
    def lpush(self, key:NativeType, values:ListOf(NativeType)) -> int:
        """ Prepend one or multiple values to a list """
        return self._query(b'lpush', self.encode_from_native(key), *map(self.encode_from_native, values))

    @_query_command
    def lpushx(self, key:NativeType, value:NativeType) -> int:
        """ Prepend a value to a list, only if the list exists """
        return self._query(b'lpushx', self.encode_from_native(key), self.encode_from_native(value))

    @_query_command
    def rpush(self, key:NativeType, values:ListOf(NativeType)) -> int:
        """ Append one or multiple values to a list """
        return self._query(b'rpush', self.encode_from_native(key), *map(self.encode_from_native, values))

    @_query_command
    def rpushx(self, key:NativeType, value:NativeType) -> int:
        """ Append a value to a list, only if the list exists """
        return self._query(b'rpushx', self.encode_from_native(key), self.encode_from_native(value))

    @_query_command
    def llen(self, key:NativeType) -> int:
        """ Returns the length of the list stored at key. """
        return self._query(b'llen', self.encode_from_native(key))

    @_query_command
    def lrem(self, key:NativeType, count:int=0, value='') -> int:
        """ Remove elements from a list """
        return self._query(b'lrem', self.encode_from_native(key), self._encode_int(count), self.encode_from_native(value))

    @_query_command
    def lrange(self, key, start:int=0, stop:int=-1) -> ListReply:
        """ Get a range of elements from a list. """
        return self._query(b'lrange', self.encode_from_native(key), self._encode_int(start), self._encode_int(stop))

    @_query_command
    def ltrim(self, key:NativeType, start:int=0, stop:int=-1) -> StatusReply:
        """ Trim a list to the specified range """
        return self._query(b'ltrim', self.encode_from_native(key), self._encode_int(start), self._encode_int(stop))

    @_query_command
    def lpop(self, key:NativeType) -> (NativeType, NoneType):
        """ Remove and get the first element in a list """
        return self._query(b'lpop', self.encode_from_native(key))

    @_query_command
    def rpop(self, key:NativeType) -> (NativeType, NoneType):
        """ Remove and get the last element in a list """
        return self._query(b'rpop', self.encode_from_native(key))

    @_query_command
    def rpoplpush(self, source:NativeType, destination:NativeType) -> NativeType:
        """ Remove the last element in a list, append it to another list and return it """
        return self._query(b'rpoplpush', self.encode_from_native(source), self.encode_from_native(destination))

    @_query_command
    def lindex(self, key:NativeType, index:int) -> (NativeType, NoneType):
        """ Get an element from a list by its index """
        return self._query(b'lindex', self.encode_from_native(key), self._encode_int(index))

    @_query_command
    def blpop(self, keys:ListOf(NativeType), timeout:int=0) -> BlockingPopReply:
        """ Remove and get the first element in a list, or block until one is available.
        This will raise :class:`~asyncio_redis.exceptions.TimeoutError` when
        the timeout was exceeded and Redis returns `None`. """
        return self._blocking_pop(b'blpop', keys, timeout=timeout)

    @_query_command
    def brpop(self, keys:ListOf(NativeType), timeout:int=0) -> BlockingPopReply:
        """ Remove and get the last element in a list, or block until one is available.
        This will raise :class:`~asyncio_redis.exceptions.TimeoutError` when
        the timeout was exceeded and Redis returns `None`. """
        return self._blocking_pop(b'brpop', keys, timeout=timeout)

    def _blocking_pop(self, command, keys, timeout:int=0):
        return self._query(command, *([ self.encode_from_native(k) for k in keys ] + [self._encode_int(timeout)]), set_blocking=True)

    @_command
    @asyncio.coroutine
    def brpoplpush(self, source:NativeType, destination:NativeType, timeout:int=0) -> NativeType:
        """ Pop a value from a list, push it to another list and return it; or block until one is available """
        result = yield from self._query(b'brpoplpush', self.encode_from_native(source), self.encode_from_native(destination),
                    self._encode_int(timeout), set_blocking=True)

        if result is None:
            raise TimeoutError('Timeout in brpoplpush')
        else:
            assert isinstance(result, bytes)
            return self.decode_to_native(result)

    @_query_command
    def lset(self, key:NativeType, index:int, value:NativeType) -> StatusReply:
        """ Set the value of an element in a list by its index. """
        return self._query(b'lset', self.encode_from_native(key), self._encode_int(index), self.encode_from_native(value))

    @_query_command
    def linsert(self, key:NativeType, pivot:NativeType, value:NativeType, before=False) -> int:
        """ Insert an element before or after another element in a list """
        return self._query(b'linsert', self.encode_from_native(key), (b'BEFORE' if before else b'AFTER'),
                self.encode_from_native(pivot), self.encode_from_native(value))

    # Sorted Sets

    @_query_command
    def zadd(self, key:NativeType, values:dict) -> int:
        """
        Add one or more members to a sorted set, or update its score if it already exists

        ::

            yield protocol.zadd('myzset', { 'key': 4, 'key2': 5 })
        """
        data = [ ]
        for k,score in values.items():
            assert isinstance(k, self.native_type)
            assert isinstance(score, (int, float))

            data.append(self._encode_float(score))
            data.append(self.encode_from_native(k))

        return self._query(b'zadd', self.encode_from_native(key), *data)

    @_query_command
    def zrange(self, key:NativeType, start:int=0, stop:int=-1) -> ZRangeReply:
        """
        Return a range of members in a sorted set, by index.

        You can do the following to receive the slice of the sorted set as a
        python dict (mapping the keys to their scores):

        ::

            result = yield protocol.zrange('myzset', start=10, stop=20)
            my_dict = yield result.asdict()

        or the following to retrieve it as a list of keys:

        ::

            result = yield protocol.zrange('myzset', start=10, stop=20)
            my_dict = yield result.aslist()
        """
        return self._query(b'zrange', self.encode_from_native(key),
                    self._encode_int(start), self._encode_int(stop), b'withscores')

    @_query_command
    def zrevrange(self, key:NativeType, start:int=0, stop:int=-1) -> ZRangeReply:
        """
        Return a range of members in a reversed sorted set, by index.

        You can do the following to receive the slice of the sorted set as a
        python dict (mapping the keys to their scores):

        ::

            my_dict = yield protocol.zrevrange_asdict('myzset', start=10, stop=20)

        or the following to retrieve it as a list of keys:

        ::

            zrange_reply = yield protocol.zrevrange('myzset', start=10, stop=20)
            my_dict = yield zrange_reply.aslist()

        """
        return self._query(b'zrevrange', self.encode_from_native(key),
                    self._encode_int(start), self._encode_int(stop), b'withscores')

    @_query_command
    def zrangebyscore(self, key:NativeType,
                min:ZScoreBoundary=ZScoreBoundary.MIN_VALUE,
                max:ZScoreBoundary=ZScoreBoundary.MAX_VALUE) -> ZRangeReply:
        """ Return a range of members in a sorted set, by score """
        return self._query(b'zrangebyscore', self.encode_from_native(key),
                    self._encode_zscore_boundary(min), self._encode_zscore_boundary(max),
                    b'withscores')

    @_query_command
    def zrevrangebyscore(self, key:NativeType,
                max:ZScoreBoundary=ZScoreBoundary.MAX_VALUE,
                min:ZScoreBoundary=ZScoreBoundary.MIN_VALUE) -> ZRangeReply:
        """ Return a range of members in a sorted set, by score, with scores ordered from high to low """
        return self._query(b'zrevrangebyscore', self.encode_from_native(key),
                    self._encode_zscore_boundary(max), self._encode_zscore_boundary(min),
                    b'withscores')

    @_query_command
    def zremrangebyscore(self, key:NativeType,
                min:ZScoreBoundary=ZScoreBoundary.MIN_VALUE,
                max:ZScoreBoundary=ZScoreBoundary.MAX_VALUE) -> int:
        """ Remove all members in a sorted set within the given scores """
        return self._query(b'zremrangebyscore', self.encode_from_native(key),
                    self._encode_zscore_boundary(min), self._encode_zscore_boundary(max))

    @_query_command
    def zremrangebyrank(self, key:NativeType, min:int=0, max:int=-1) -> int:
        """ Remove all members in a sorted set within the given indexes """
        return self._query(b'zremrangebyrank', self.encode_from_native(key),
                    self._encode_int(min), self._encode_int(max))

    @_query_command
    def zcount(self, key:NativeType, min:ZScoreBoundary, max:ZScoreBoundary) -> int:
        """ Count the members in a sorted set with scores within the given values """
        return self._query(b'zcount', self.encode_from_native(key),
                    self._encode_zscore_boundary(min), self._encode_zscore_boundary(max))

    @_query_command
    def zscore(self, key:NativeType, member:NativeType) -> (float, NoneType):
        """ Get the score associated with the given member in a sorted set """
        return self._query(b'zscore', self.encode_from_native(key), self.encode_from_native(member))

    @_query_command
    def zunionstore(self, destination:NativeType, keys:ListOf(NativeType), weights:(NoneType,ListOf(float))=None,
                                    aggregate=ZAggregate.SUM) -> int:
        """ Add multiple sorted sets and store the resulting sorted set in a new key """
        return self._zstore(b'zunionstore', destination, keys, weights, aggregate)

    @_query_command
    def zinterstore(self, destination:NativeType, keys:ListOf(NativeType), weights:(NoneType,ListOf(float))=None,
                                    aggregate=ZAggregate.SUM) -> int:
        """ Intersect multiple sorted sets and store the resulting sorted set in a new key """
        return self._zstore(b'zinterstore', destination, keys, weights, aggregate)

    def _zstore(self, command, destination, keys, weights, aggregate):
        """ Common part for zunionstore and zinterstore. """
        numkeys = len(keys)
        if weights is None:
            weights = [1] * numkeys

        return self._query(*
                [ command, self.encode_from_native(destination), self._encode_int(numkeys) ] +
                list(map(self.encode_from_native, keys)) +
                [ b'weights' ] +
                list(map(self._encode_float, weights)) +
                [ b'aggregate' ] +
                [ {
                        ZAggregate.SUM: b'SUM',
                        ZAggregate.MIN: b'MIN',
                        ZAggregate.MAX: b'MAX' }[aggregate]
                ] )

    @_query_command
    def zcard(self, key:NativeType) -> int:
        """ Get the number of members in a sorted set """
        return self._query(b'zcard', self.encode_from_native(key))

    @_query_command
    def zrank(self, key:NativeType, member:NativeType) -> (int, NoneType):
        """ Determine the index of a member in a sorted set """
        return self._query(b'zrank', self.encode_from_native(key), self.encode_from_native(member))

    @_query_command
    def zrevrank(self, key:NativeType, member:NativeType) -> (int, NoneType):
        """ Determine the index of a member in a sorted set, with scores ordered from high to low """
        return self._query(b'zrevrank', self.encode_from_native(key), self.encode_from_native(member))

    @_query_command
    def zincrby(self, key:NativeType, increment:float, member:NativeType) -> float:
        """ Increment the score of a member in a sorted set """
        return self._query(b'zincrby', self.encode_from_native(key),
                    self._encode_float(increment), self.encode_from_native(member))

    @_query_command
    def zrem(self, key:NativeType, members:ListOf(NativeType)) -> int:
        """ Remove one or more members from a sorted set """
        return self._query(b'zrem', self.encode_from_native(key), *map(self.encode_from_native, members))

    # Hashes

    @_query_command
    def hset(self, key:NativeType, field:NativeType, value:NativeType) -> int:
        """ Set the string value of a hash field """
        return self._query(b'hset', self.encode_from_native(key), self.encode_from_native(field), self.encode_from_native(value))

    @_query_command
    def hmset(self, key:NativeType, values:dict) -> StatusReply:
        """ Set multiple hash fields to multiple values """
        data = [ ]
        for k,v in values.items():
            assert isinstance(k, self.native_type)
            assert isinstance(v, self.native_type)

            data.append(self.encode_from_native(k))
            data.append(self.encode_from_native(v))

        return self._query(b'hmset', self.encode_from_native(key), *data)

    @_query_command
    def hsetnx(self, key:NativeType, field:NativeType, value:NativeType) -> int:
        """ Set the value of a hash field, only if the field does not exist """
        return self._query(b'hsetnx', self.encode_from_native(key), self.encode_from_native(field), self.encode_from_native(value))

    @_query_command
    def hdel(self, key:NativeType, fields:ListOf(NativeType)) -> int:
        """ Delete one or more hash fields """
        return self._query(b'hdel', self.encode_from_native(key), *map(self.encode_from_native, fields))

    @_query_command
    def hget(self, key:NativeType, field:NativeType) -> (NativeType, NoneType):
        """ Get the value of a hash field """
        return self._query(b'hget', self.encode_from_native(key), self.encode_from_native(field))

    @_query_command
    def hexists(self, key:NativeType, field:NativeType) -> bool:
        """ Returns if field is an existing field in the hash stored at key. """
        return self._query(b'hexists', self.encode_from_native(key), self.encode_from_native(field))

    @_query_command
    def hkeys(self, key:NativeType) -> SetReply:
        """ Get all the keys in a hash. (Returns a set) """
        return self._query(b'hkeys', self.encode_from_native(key))

    @_query_command
    def hvals(self, key:NativeType) -> ListReply:
        """ Get all the values in a hash. (Returns a list) """
        return self._query(b'hvals', self.encode_from_native(key))

    @_query_command
    def hlen(self, key:NativeType) -> int:
        """ Returns the number of fields contained in the hash stored at key. """
        return self._query(b'hlen', self.encode_from_native(key))

    @_query_command
    def hgetall(self, key:NativeType) -> DictReply:
        """ Get the value of a hash field """
        return self._query(b'hgetall', self.encode_from_native(key))

    @_query_command
    def hmget(self, key:NativeType, fields:ListOf(NativeType)) -> ListReply:
        """ Get the values of all the given hash fields """
        return self._query(b'hmget', self.encode_from_native(key), *map(self.encode_from_native, fields))

    @_query_command
    def hincrby(self, key:NativeType, field:NativeType, increment) -> int:
        """ Increment the integer value of a hash field by the given number
        Returns: the value at field after the increment operation. """
        assert isinstance(increment, int)
        return self._query(b'hincrby', self.encode_from_native(key), self.encode_from_native(field), self._encode_int(increment))

    @_query_command
    def hincrbyfloat(self, key:NativeType, field:NativeType, increment:(int,float)) -> float:
        """ Increment the float value of a hash field by the given amount
        Returns: the value at field after the increment operation. """
        return self._query(b'hincrbyfloat', self.encode_from_native(key), self.encode_from_native(field), self._encode_float(increment))

    # Pubsub
    # (subscribe, unsubscribe, etc... should be called through the Subscription class.)

    @_command
    def start_subscribe(self, *a) -> 'Subscription':
        """
        Start a pubsub listener.

        ::

            # Create subscription
            subscription = yield from protocol.start_subscribe()
            yield from subscription.subscribe(['key'])
            yield from subscription.psubscribe(['pattern*'])

            while True:
                result = yield from subscription.next_published()
                print(result)

        :returns: :class:`~asyncio_redis.Subscription`
        """
        # (Make coroutine. @asyncio.coroutine breaks documentation. It uses
        # @functools.wraps to make a generator for this function. But _command
        # will no longer be able to read the signature.)
        if False: yield

        if self.in_use:
            raise Error('Cannot start pubsub listener when a protocol is in use.')

        subscription = Subscription(self)

        self._in_pubsub = True
        self._subscription = subscription
        return subscription

    @_command
    def _subscribe(self, channels:ListOf(NativeType)) -> NoneType:
        """ Listen for messages published to the given channels """
        self._pubsub_channels |= set(channels)
        return self._pubsub_method('subscribe', channels)

    @_command
    def _unsubscribe(self, channels:ListOf(NativeType)) -> NoneType:
        """ Stop listening for messages posted to the given channels """
        self._pubsub_channels -= set(channels)
        return self._pubsub_method('unsubscribe', channels)

    @_command
    def _psubscribe(self, patterns:ListOf(NativeType)) -> NoneType:
        """ Listen for messages published to channels matching the given patterns """
        self._pubsub_patterns |= set(patterns)
        return self._pubsub_method('psubscribe', patterns)

    @_command
    def _punsubscribe(self, patterns:ListOf(NativeType)) -> NoneType: # XXX: unittest
        """ Stop listening for messages posted to channels matching the given patterns """
        self._pubsub_patterns -= set(patterns)
        return self._pubsub_method('punsubscribe', patterns)

    @asyncio.coroutine
    def _pubsub_method(self, method, params):
        if not self._in_pubsub:
            raise Error('Cannot call pubsub methods without calling start_subscribe')

        # Send
        self._send_command([method.encode('ascii')] + list(map(self.encode_from_native, params)))

        # Note that we can't use `self._query` here. The reason is that one
        # subscribe/unsubscribe command returns a separate answer for every
        # parameter. It doesn't fit in the same model of all the other queries
        # where one query puts a Future on the queue that is replied with the
        # incoming answer.
        # Redis returns something like [ 'subscribe', 'channel_name', 1] for
        # each parameter, but we can safely ignore those replies that.

    @_query_command
    def publish(self, channel:NativeType, message:NativeType) -> int:
        """ Post a message to a channel
        (Returns the number of clients that received this message.) """
        return self._query(b'publish', self.encode_from_native(channel), self.encode_from_native(message))

    @_query_command
    def pubsub_channels(self, pattern:(NativeType, NoneType)=None) -> ListReply:
        """
        Lists the currently active channels. An active channel is a Pub/Sub
        channel with one ore more subscribers (not including clients subscribed
        to patterns).
        """
        return self._query(b'pubsub', b'channels',
                    (self.encode_from_native(pattern) if pattern else b'*'))

    @_query_command
    def pubsub_numsub(self, channels:ListOf(NativeType)) -> DictReply:
        """Returns the number of subscribers (not counting clients subscribed
        to patterns) for the specified channels.  """
        return self._query(b'pubsub', b'numsub', *[ self.encode_from_native(c) for c in channels ])

    @_query_command
    def pubsub_numpat(self) -> int:
        """ Returns the number of subscriptions to patterns (that are performed
        using the PSUBSCRIBE command). Note that this is not just the count of
        clients subscribed to patterns but the total number of patterns all the
        clients are subscribed to. """
        return self._query(b'pubsub', b'numpat')

    # Server

    @_query_command
    def ping(self) -> StatusReply:
        """ Ping the server (Returns PONG) """
        return self._query(b'ping')

    @_query_command
    def echo(self, string:NativeType) -> NativeType:
        """ Echo the given string """
        return self._query(b'echo', self.encode_from_native(string))

    @_query_command
    def save(self) -> StatusReply:
        """ Synchronously save the dataset to disk """
        return self._query(b'save')

    @_query_command
    def bgsave(self) -> StatusReply:
        """ Asynchronously save the dataset to disk """
        return self._query(b'bgsave')

    @_query_command
    def bgrewriteaof(self) -> StatusReply:
        """ Asynchronously rewrite the append-only file """
        return self._query(b'bgrewriteaof')

    @_query_command
    def lastsave(self) -> int:
        """ Get the UNIX time stamp of the last successful save to disk """
        return self._query(b'lastsave')

    @_query_command
    def dbsize(self) -> int:
        """ Return the number of keys in the currently-selected database. """
        return self._query(b'dbsize')

    @_query_command
    def flushall(self) -> StatusReply:
        """ Remove all keys from all databases """
        return self._query(b'flushall')

    @_query_command
    def flushdb(self) -> StatusReply:
        """ Delete all the keys of the currently selected DB. This command never fails. """
        return self._query(b'flushdb')

#    @_query_command
#    def object(self, subcommand, args):
#        """ Inspect the internals of Redis objects """
#        raise NotImplementedError

    @_query_command
    def type(self, key:NativeType) -> StatusReply:
        """ Determine the type stored at key """
        return self._query(b'type', self.encode_from_native(key))

    @_query_command
    def config_set(self, parameter:str, value:str) -> StatusReply:
        """ Set a configuration parameter to the given value """
        return self._query(b'config', b'set', self.encode_from_native(parameter),
                        self.encode_from_native(value))

    @_query_command
    def config_get(self, parameter:str) -> ConfigPairReply:
        """ Get the value of a configuration parameter """
        return self._query(b'config', b'get', self.encode_from_native(parameter))

    @_query_command
    def config_rewrite(self) -> StatusReply:
        """ Rewrite the configuration file with the in memory configuration """
        return self._query(b'config', b'rewrite')

    @_query_command
    def config_resetstat(self) -> StatusReply:
        """ Reset the stats returned by INFO """
        return self._query(b'config', b'resetstat')

    @_query_command
    def info(self, section:(NativeType, NoneType)=None) -> InfoReply:
        """ Get information and statistics about the server """
        if section is None:
            return self._query(b'info')
        else:
            return self._query(b'info', self.encode_from_native(section))

    @_query_command
    def shutdown(self, save=False) -> StatusReply:
        """ Synchronously save the dataset to disk and then shut down the server """
        return self._query(b'shutdown', (b'save' if save else b'nosave'))

    @_query_command
    def client_getname(self) -> NativeType:
        """ Get the current connection name """
        return self._query(b'client', b'getname')

    @_query_command
    def client_setname(self, name) -> StatusReply:
        """ Set the current connection name """
        return self._query(b'client', b'setname', self.encode_from_native(name))

    @_query_command
    def client_list(self) -> ClientListReply:
        """ Get the list of client connections """
        return self._query(b'client', b'list')

    @_query_command
    def client_kill(self, address:str) -> StatusReply:
        """
        Kill the connection of a client
        `address` should be an "ip:port" string.
        """
        return self._query(b'client', b'kill', address.encode('utf-8'))

    # LUA scripting

    @_command
    def register_script(self, script:str) -> 'Script':
        """
        Register a LUA script.

        ::

            script = yield from protocol.register_script(lua_code)
            result = yield from script.run(keys=[...], args=[...])
        """
        # The register_script APi was made compatible with the redis.py library:
        # https://github.com/andymccurdy/redis-py
        sha = yield from self.script_load(script)
        return Script(sha, script, lambda:self.evalsha)

    @_query_command
    def script_exists(self, shas:ListOf(str)) -> ListOf(bool):
        """ Check existence of scripts in the script cache. """
        return self._query(b'script', b'exists', *[ sha.encode('ascii') for sha in shas ])

    @_query_command
    def script_flush(self) -> StatusReply:
        """ Remove all the scripts from the script cache. """
        return self._query(b'script', b'flush')

    @_query_command
    def script_kill(self) -> StatusReply:
        """
        Kill the script currently in execution.  This raises
        :class:`~asyncio_redis.exceptions.NoRunningScriptError` when there are no
        scrips running.
        """
        try:
            return (yield from self._query(b'script', b'kill'))
        except ErrorReply as e:
            if 'NOTBUSY' in e.args[0]:
                raise NoRunningScriptError
            else:
                raise

    @_query_command
    def evalsha(self, sha:str,
                        keys:(ListOf(NativeType), NoneType)=None,
                        args:(ListOf(NativeType), NoneType)=None) -> EvalScriptReply:
        """
        Evaluates a script cached on the server side by its SHA1 digest.
        Scripts are cached on the server side using the SCRIPT LOAD command.

        The return type/value depends on the script.

        This will raise a :class:`~asyncio_redis.exceptions.ScriptKilledError`
        exception if the script was killed.
        """
        if not keys: keys = []
        if not args: args = []

        try:
            result = yield from self._query(b'evalsha', sha.encode('ascii'),
                        self._encode_int(len(keys)),
                        *map(self.encode_from_native, keys + args))

            return result
        except ErrorReply:
            raise ScriptKilledError

    @_query_command
    def script_load(self, script:str) -> str:
        """ Load script, returns sha1 """
        return self._query(b'script', b'load', script.encode('ascii'))

    # Scanning

    @_command
    def scan(self, match:NativeType='*') -> Cursor:
        """
        Walk through the keys space. You can either fetch the items one by one
        or in bulk.

        ::

            cursor = yield from protocol.scan(match='*')
            while True:
                item = yield from cursor.fetchone()
                if item is None:
                    break
                else:
                    print(item)

        ::

            cursor = yield from protocol.scan(match='*')
            items = yield from cursor.fetchall()

        Also see: :func:`~asyncio_redis.RedisProtocol.sscan`,
        :func:`~asyncio_redis.RedisProtocol.hscan` and
        :func:`~asyncio_redis.RedisProtocol.zscan`

        Redis reference: http://redis.io/commands/scan
        """
        if False: yield

        def scanfunc(cursor):
            return self._scan(cursor, match)

        return Cursor(name='scan(match=%r)' % match, scanfunc=scanfunc)

    @_query_command
    def _scan(self, cursor:int, match:NativeType) -> _ScanPart:
        return self._query(b'scan', self._encode_int(cursor),
                    b'match', self.encode_from_native(match))

    @_command
    def sscan(self, key:NativeType, match:NativeType='*') -> SetCursor:
        """
        Incrementally iterate set elements

        Also see: :func:`~asyncio_redis.RedisProtocol.scan`
        """
        if False: yield
        name = 'sscan(key=%r match=%r)' % (key, match)

        def scan(cursor):
            return self._do_scan(b'sscan', key, cursor, match)

        return SetCursor(name=name, scanfunc=scan)

    @_command
    def hscan(self, key:NativeType, match:NativeType='*') -> DictCursor:
        """
        Incrementally iterate hash fields and associated values
        Also see: :func:`~asyncio_redis.RedisProtocol.scan`
        """
        if False: yield
        name = 'hscan(key=%r match=%r)' % (key, match)

        def scan(cursor):
            return self._do_scan(b'hscan', key, cursor, match)

        return DictCursor(name=name, scanfunc=scan)

    @_command
    def zscan(self, key:NativeType, match:NativeType='*') -> DictCursor:
        """
        Incrementally iterate sorted sets elements and associated scores
        Also see: :func:`~asyncio_redis.RedisProtocol.scan`
        """
        if False: yield
        name = 'zscan(key=%r match=%r)' % (key, match)

        def scan(cursor):
            return self._do_scan(b'zscan', key, cursor, match)

        return ZCursor(name=name, scanfunc=scan)

    @_query_command
    def _do_scan(self, verb:bytes, key:NativeType, cursor:int, match:NativeType) -> _ScanPart:
        return self._query(verb, self.encode_from_native(key),
                self._encode_int(cursor),
                b'match', self.encode_from_native(match))

    # Transaction

    @_command
    @asyncio.coroutine
    def multi(self, watch:(ListOf(NativeType),NoneType)=None) -> 'Transaction':
        """
        Start of transaction.

        ::

            transaction = yield from protocol.multi()

            # Run commands in transaction
            f1 = yield from transaction.set('key', 'value')
            f1 = yield from transaction.set('another_key', 'another_value')

            # Commit transaction
            yield from transaction.exec()

            # Retrieve results (you can also use asyncio.tasks.gather)
            result1 = yield from f1
            result2 = yield from f2

        :returns: A :class:`asyncio_redis.Transaction` instance.
        """
        if (self._in_transaction):
            raise Error('Multi calls can not be nested.')

        # Call watch
        if watch is not None:
            for k in watch:
                result = yield from self._query(b'watch', self.encode_from_native(k))
                assert result == StatusReply('OK')

        # Call multi
        result = yield from self._query(b'multi')
        assert result == StatusReply('OK')

        self._in_transaction = True
        self._transaction_response_queue = deque()

        # Create transaction object.
        t = Transaction(self)
        self._transaction = t
        return t

    @asyncio.coroutine
    def _exec(self):
        """
        Execute all commands issued after MULTI
        """
        if not self._in_transaction:
            raise Error('Not in transaction')

        futures_and_postprocessors = self._transaction_response_queue
        self._transaction_response_queue = None

        # Get transaction answers.
        multi_bulk_reply = yield from self._query(b'exec', _bypass=True)

        if multi_bulk_reply is None:
            # We get None when a transaction failed.
            raise TransactionError('Transaction failed.')
        else:
            assert isinstance(multi_bulk_reply, MultiBulkReply)

        for f in multi_bulk_reply.iter_raw():
            answer = yield from f
            f2, call = futures_and_postprocessors.popleft()

            if isinstance(answer, Exception):
                f2.set_exception(answer)
            else:
                if call:
                    self._pipelined_calls.remove(call)

                f2.set_result(answer)

        self._transaction_response_queue = deque()
        self._in_transaction = False
        self._transaction = None

    @asyncio.coroutine
    def _discard(self):
        """
        Discard all commands issued after MULTI
        """
        if not self._in_transaction:
            raise Error('Not in transaction')

        self._transaction_response_queue = deque()
        self._in_transaction = False
        self._transaction = None
        result = yield from self._query(b'discard')
        assert result == StatusReply('OK')

    @asyncio.coroutine
    def _unwatch(self):
        """
        Forget about all watched keys
        """
        if not self._in_transaction:
            raise Error('Not in transaction')

        result = yield from self._query(b'unwatch')
        assert result == StatusReply('OK')


class Script:
    """ Lua script. """
    def __init__(self, sha, code, get_evalsha_func):
        self.sha = sha
        self.code = code
        self.get_evalsha_func = get_evalsha_func

    def run(self, keys=[], args=[]):
        """
        Returns a coroutine that executes the script.

        ::

            script_reply = yield from script.run(keys=[], args=[])

            # If the LUA script returns something, retrieve the return value
            result = yield from script_reply.return_value()

        This will raise a :class:`~asyncio_redis.exceptions.ScriptKilledError`
        exception if the script was killed.
        """
        return self.get_evalsha_func()(self.sha, keys, args)


class Transaction:
    """
    Transaction context. This is a proxy to a :class:`.RedisProtocol` instance.
    Every redis command called on this object will run inside the transaction.
    The transaction can be finished by calling either ``discard`` or ``exec``.

    More info: http://redis.io/topics/transactions
    """
    def __init__(self, protocol):
        self._protocol = protocol

    def __getattr__(self, name):
        """
        Proxy to a protocol.
        """
        # Only proxy commands.
        if name not in _all_commands:
            raise AttributeError(name)

        method = getattr(self._protocol, name)

        # Wrap the method into something that passes the transaction object as
        # first argument.
        @wraps(method)
        def wrapper(*a, **kw):
            if self._protocol._transaction != self:
                raise Error('Transaction already finished or invalid.')

            return method(self, *a, **kw)
        return wrapper

    def discard(self):
        """
        Discard all commands issued after MULTI
        """
        return self._protocol._discard()

    def exec(self):
        """
        Execute transaction.

        This can raise a :class:`~asyncio_redis.exceptions.TransactionError`
        when the transaction fails.
        """
        return self._protocol._exec()

    def unwatch(self): # XXX: test
        """
        Forget about all watched keys
        """
        return self._protocol._unwatch()


class Subscription:
    """
    Pubsub subscription
    """
    def __init__(self, protocol):
        self.protocol = protocol
        self._messages_queue = Queue(loop=protocol._loop) # Pubsub queue

    @wraps(RedisProtocol._subscribe)
    def subscribe(self, channels):
        return self.protocol._subscribe(self, channels)

    @wraps(RedisProtocol._unsubscribe)
    def unsubscribe(self, channels):
        return self.protocol._unsubscribe(self, channels)

    @wraps(RedisProtocol._psubscribe)
    def psubscribe(self, patterns):
        return self.protocol._psubscribe(self, patterns)

    @wraps(RedisProtocol._punsubscribe)
    def punsubscribe(self, patterns):
        return self.protocol._punsubscribe(self, patterns)

    @asyncio.coroutine
    def next_published(self):
        """
        Coroutine which waits for next pubsub message to be received and
        returns it.

        :returns: instance of :class:`PubSubReply <asyncio_redis.replies.PubSubReply>`
        """
        return (yield from self._messages_queue.get())

########NEW FILE########
__FILENAME__ = replies
import asyncio
from asyncio.tasks import gather

__all__ = (
    'BlockingPopReply',
    'DictReply',
    'ListReply',
    'PubSubReply',
    'SetReply',
    'StatusReply',
    'ZRangeReply',
    'ConfigPairReply',
    'InfoReply',
)


class StatusReply:
    """
    Wrapper for Redis status replies.
    (for messages like OK, QUEUED, etc...)
    """
    def __init__(self, status):
        self.status = status

    def __repr__(self):
        return 'StatusReply(status=%r)' % self.status

    def __eq__(self, other):
        return self.status == other.status


class DictReply:
    """
    Container for a dict reply.

    The content can be retrieved by calling
    :func:`~asyncio_redis.replies.DictReply.asdict` which returns a Python
    dictionary. Or by iterating over it:

    ::

        for f in dict_reply:
            key, value = yield from f
            print(key, value)
    """
    def __init__(self, multibulk_reply):
        self._result = multibulk_reply

    def _parse(self, key, value):
        return key, value

    def __iter__(self):
        """ Yield a list of futures that yield { key: value } tuples. """
        i = iter(self._result)

        @asyncio.coroutine
        def getter(key_f, value_f):
            """ Coroutine which processes one item. """
            key, value = yield from gather(key_f, value_f, loop=self._result._loop)
            key, value = self._parse(key, value)
            return (key, value)

        while True:
            yield asyncio.async(getter(next(i), next(i)), loop=self._result._loop)

    @asyncio.coroutine
    def asdict(self):
        """
        Return the result as a Python dictionary.
        """
        result = { }
        for f in self:
            key, value = yield from f
            result[key] = value
        return result

    def __repr__(self):
        return '%s(length=%r)' % (self.__class__.__name__, int(self._result.count / 2))


class ZRangeReply(DictReply):
    """
    Container for a zrange query result.
    """
    def _parse(self, key, value):
        # Mapping { key: score_as_float }
        return key, float(value)


class SetReply:
    """
    Redis set result.
    The content can be retrieved by calling
    :func:`~asyncio_redis.replies.SetReply.asset` or by iterating over it

    ::

        for f in set_reply:
            item = yield from f
            print(item)
    """
    def __init__(self, multibulk_reply):
        self._result = multibulk_reply

    def __iter__(self):
        """ Yield a list of futures. """
        return iter(self._result)

    @asyncio.coroutine
    def asset(self):
        """ Return the result as a Python ``set``.  """
        result = yield from gather(* list(self._result), loop=self._result._loop)
        return set(result)

    def __repr__(self):
        return 'SetReply(length=%r)' % (self._result.count)


class ListReply:
    """
    Redis list result.
    The content can be retrieved by calling
    :func:`~asyncio_redis.replies.ListReply.aslist` or by iterating over it
    or by iterating over it

    ::

        for f in list_reply:
            item = yield from f
            print(item)
    """
    def __init__(self, multibulk_reply):
        self._result = multibulk_reply

    def __iter__(self):
        """ Yield a list of futures. """
        return iter(self._result)

    def aslist(self):
        """ Return the result as a Python ``list``. """
        return gather(* list(self._result), loop=self._result._loop)

    def __repr__(self):
        return 'ListReply(length=%r)' % (self._result.count, )


class BlockingPopReply:
    """
    :func:`~asyncio_redis.RedisProtocol.blpop` or
    :func:`~asyncio_redis.RedisProtocol.brpop` reply
    """
    def __init__(self, list_name, value):
        self._list_name = list_name
        self._value = value

    @property
    def list_name(self):
        """ List name. """
        return self._list_name

    @property
    def value(self):
        """ Popped value """
        return self._value

    def __repr__(self):
        return 'BlockingPopReply(list_name=%r, value=%r)' % (self.list_name, self.value)


class ConfigPairReply:
    """ :func:`~asyncio_redis.RedisProtocol.config_get` reply. """
    def __init__(self, parameter, value):
        self._paramater = parameter
        self._value = value

    @property
    def parameter(self):
        """ Config parameter name. """
        return self._paramater

    @property
    def value(self):
        """ Config parameter value. """
        return self._value

    def __repr__(self):
        return 'ConfigPairReply(parameter=%r, value=%r)' % (self.parameter, self.value)


class InfoReply:
    """ :func:`~asyncio_redis.RedisProtocol.info` reply. """
    def __init__(self, data):
        self._data = data # TODO: implement parser logic


class ClientListReply:
    """ :func:`~asyncio_redis.RedisProtocol.client_list` reply. """
    def __init__(self, data):
        self._data = data # TODO: implement parser logic


class PubSubReply:
    """ Received pubsub message. """
    def __init__(self, channel, value):
        self._channel = channel
        self._value = value

    @property
    def channel(self):
        """ Channel name """
        return self._channel

    @property
    def value(self):
        """ Received PubSub value """
        return self._value

    def __repr__(self):
        return 'PubSubReply(channel=%r, value=%r)' % (self.channel, self.value)

    def __eq__(self, other):
        return self._channel == other._channel and self._value == other._value


class EvalScriptReply:
    """
    :func:`~asyncio_redis.RedisProtocol.evalsha` reply.

    Lua scripts can return strings/bytes (NativeType), but also ints, lists or
    even nested data structures.
    """
    def __init__(self, protocol, value):
        self._protocol = protocol
        self._value = value

    @asyncio.coroutine
    def return_value(self):
        """
        Coroutine that returns a Python representation of the script's return
        value.
        """
        from asyncio_redis.protocol import MultiBulkReply

        @asyncio.coroutine
        def decode(obj):
            if isinstance(obj, int):
                return obj

            elif isinstance(obj, bytes):
                return self._protocol.decode_to_native(self._value)

            elif isinstance(obj, MultiBulkReply):
                # Unpack MultiBulkReply recursively as Python list.
                result = []
                for f in obj:
                    item = yield from f
                    result.append((yield from decode(item)))
                return result

            else:
                # Nonetype, or decoded bytes.
                return obj

        return (yield from decode(self._value))


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# asyncio_redis documentation build configuration file, created by
# sphinx-quickstart on Thu Oct 31 08:50:13 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Take signatures from docstrings.
autodoc_docstring_signature = True

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'asyncio_redis'
copyright = u'2013, Jonathan Slenders'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

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
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'default'

import os
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
#html_last_updated_fmt = '%b %d, %Y'

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
htmlhelp_basename = 'asyncio_redisdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'asyncio_redis.tex', u'asyncio\\_redis Documentation',
   u'Jonathan Slenders', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'asyncio_redis', u'asyncio_redis Documentation',
     [u'Jonathan Slenders'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'asyncio_redis', u'asyncio_redis Documentation',
   u'Jonathan Slenders', 'asyncio_redis', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = speed_test
#!/usr/bin/env python
"""
Benchmank how long it takes to set 10,000 keys in the database.
"""
import asyncio
import logging
import asyncio_redis
import time

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    # Enable logging
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.INFO)

    def run():
        #connection = yield from asyncio_redis.Connection.create(host='localhost', port=6379)
        connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=50)

        # === Benchmark 1 ==
        print('1. How much time does it take to set 10,000 values in Redis? (without pipelining)')
        print('Starting...')
        start = time.time()

        # Do 10,000 set requests
        for i in range(10 * 1000):
            yield from connection.set('key', 'value') # By using yield from here, we wait for the answer.

        print('Done. Duration=', time.time() - start)
        print()

        # === Benchmark 2 (should be at least 3x as fast) ==

        print('2. How much time does it take if we use asyncio.gather, and pipeline requests?')
        print('Starting...')
        start = time.time()

        # Do 10,000 set requests
        futures = [ asyncio.Task(connection.set('key', 'value')) for x in range(10 * 1000) ]
        yield from asyncio.gather(*futures)

        print('Done. Duration=', time.time() - start)

    loop.run_until_complete(run())

########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python
"""
Simple example that sets a key, and retrieves it again.
"""
import asyncio
from asyncio_redis import RedisProtocol

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    def run():
        # Create connection
        transport, protocol = yield from loop.create_connection(RedisProtocol, 'localhost', 6379)

        # Set a key
        yield from protocol.set('key', 'value')

        # Retrieve a key
        result = yield from protocol.get('key')

        # Print result
        print ('Succeeded', result == 'value')

    loop.run_until_complete(run())

########NEW FILE########
__FILENAME__ = receiver
#!/usr/bin/env python
import asyncio
import logging
import asyncio_redis

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    # Enable logging
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.INFO)

    def run():
        # Create a new redis connection (this will also auto reconnect)
        connection = yield from asyncio_redis.Connection.create('localhost', 6379)

        # Subscribe to a channel.
        subscriber = yield from connection.start_subscribe()
        yield from subscriber.subscribe([ 'our-channel' ])

        # Print published values in a while/true loop.
        while True:
            reply = yield from subscriber.next_published()
            print('Received: ', repr(reply.value), 'on channel', reply.channel)

    loop.run_until_complete(run())

########NEW FILE########
__FILENAME__ = sender
#!/usr/bin/env python
import asyncio
import asyncio_redis
import logging


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    # Enable logging
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.INFO)

    def run():
        # Create a new redis connection (this will also auto reconnect)
        connection = yield from asyncio_redis.Connection.create('localhost', 6379)

        while True:
            # Get input (always use executor for blocking calls)
            text = yield from loop.run_in_executor(None, input, 'Enter message: ')

            # Publish value
            try:
                yield from connection.publish('our-channel', text)
                print('Published.')
            except asyncio_redis.Error as e:
                print('Published failed', repr(e))

    loop.run_until_complete(run())

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
"""
Example of how the connection should reconnect to the server.
It's a loop that publishes 'message' in 'our-channel'.
"""
import asyncio
import logging
import asyncio_redis

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    # Enable logging
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.INFO)

    def run():
        connection = yield from asyncio_redis.Connection.create(host='localhost', port=6379)

        while True:
            yield from asyncio.sleep(.5)

            try:
                # Try to send message
                yield from connection.publish('our-channel', 'message')
            except Exception as e:
                print ('errero', repr(e))

    loop.run_until_complete(run())

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
"""
Example of how an 'smembers' call gets streamed when it's a big reply, covering
multiple IP packets.
"""
import asyncio
import logging
import asyncio_redis

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    # Enable logging
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.INFO)

    def run():
        connection = yield from asyncio_redis.Connection.create(host='localhost', port=6379)

        # Create a set that contains a million items
        print('Creating big set contains a million items (Can take about half a minute)')

        yield from connection.delete(['my-big-set'])

        # We will suffix all the items with a very long key, just to be sure
        # that this needs many IP packets, in order to send or receive this.
        long_string = 'abcdefghij' * 1000 # len=10k

        for prefix in range(10):
            print('Callidng redis sadd:', prefix, '/10')
            yield from connection.sadd('my-big-set', ('%s-%s-%s' % (prefix, i, long_string)  for i in range(10 * 1000) ))
        print('Done\n')

        # Now stream the values from the database:
        print('Streaming values, calling smembers')

        # The following smembers call will block until the first IP packet
        # containing the head of the multi bulk reply comes in. This will
        # contain the size of the multi bulk reply and that's enough
        # information to create a SetReply instance. Probably the first packet
        # will also contain the first X members, so we don't have to wait for
        # these anymore.
        set_reply = yield from connection.smembers('my-big-set')
        print('Got: ', set_reply)

        # Stream the items, this will probably wait for the next IP packets to come in.
        count = 0
        for f in set_reply:
            m = yield from f
            count += 1
            if count % 1000 == 0:
                print('Received %i items' % count)

    loop.run_until_complete(run())

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python

from asyncio.futures import Future
from asyncio.tasks import gather

from asyncio_redis import (
        Connection,
        Error,
        ErrorReply,
        NoAvailableConnectionsInPoolError,
        NoRunningScriptError,
        NotConnectedError,
        Pool,
        RedisProtocol,
        Script,
        ScriptKilledError,
        Subscription,
        Transaction,
        TransactionError,
        ZScoreBoundary,
)
from asyncio_redis.replies import (
        BlockingPopReply,
        ClientListReply,
        ConfigPairReply,
        DictReply,
        EvalScriptReply,
        InfoReply,
        ListReply,
        PubSubReply,
        SetReply,
        StatusReply,
        ZRangeReply,
)
from asyncio_redis.exceptions import TimeoutError
from asyncio_redis.cursors import Cursor
from asyncio_redis.encoders import BytesEncoder

import asyncio
import unittest
import os

PORT = int(os.environ.get('REDIS_PORT', 6379))
HOST = os.environ.get('REDIS_HOST', 'localhost')
START_REDIS_SERVER = bool(os.environ.get('START_REDIS_SERVER', False))


@asyncio.coroutine
def connect(loop, protocol=RedisProtocol):
    """ Connect to redis server. Return transport/protocol pair. """
    if PORT:
        transport, protocol = yield from loop.create_connection(
                lambda: protocol(loop=loop), HOST, PORT)
        return transport, protocol
    else:
        transport, protocol = yield from loop.create_unix_connection(
                lambda: protocol(loop=loop), HOST)
        return transport, protocol


def redis_test(function):
    """
    Decorator for methods (which are coroutines) in RedisProtocolTest

    Wraps the coroutine inside `run_until_complete`.
    """
    function = asyncio.coroutine(function)

    def wrapper(self):
        @asyncio.coroutine
        def c():
            # Create connection
            transport, protocol = yield from connect(self.loop, self.protocol_class)

            # Run test
            try:
                yield from function(self, transport, protocol)

            # Close connection
            finally:
                transport.close()

            # Give a little time to clean up and close everything after each
            # test before we close the loop. (We can get a "ResourceWarning,
            # unclosed socket" in some rare cases otherwise.)
            yield from asyncio.sleep(.1, loop=self.loop)

        self.loop.run_until_complete(c())
    return wrapper


class RedisProtocolTest(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.protocol_class = RedisProtocol

    def tearDown(self):
        pass

    @redis_test
    def test_ping(self, transport, protocol):
        result = yield from protocol.ping()
        self.assertEqual(result, StatusReply('PONG'))
        self.assertEqual(repr(result), u"StatusReply(status='PONG')")

    @redis_test
    def test_echo(self, transport, protocol):
        result = yield from protocol.echo(u'my string')
        self.assertEqual(result, u'my string')

    @redis_test
    def test_set_and_get(self, transport, protocol):
        # Set
        value = yield from protocol.set(u'my_key', u'my_value')
        self.assertEqual(value, StatusReply('OK'))

        # Get
        value = yield from protocol.get(u'my_key')
        self.assertEqual(value, u'my_value')

        # Getset
        value = yield from protocol.getset(u'my_key', u'new_value')
        self.assertEqual(value, u'my_value')

        value = yield from protocol.get(u'my_key')
        self.assertEqual(value, u'new_value')

    @redis_test
    def test_extended_set(self, transport, protocol):
        yield from protocol.delete([u'my_key', u'other_key'])
        # set with expire only if not exists
        value = yield from protocol.set(u'my_key', u'my_value',
                                        expire=10, only_if_not_exists=True)
        self.assertEqual(value, StatusReply('OK'))
        value = yield from protocol.ttl(u'my_key')
        self.assertIn(value, (10, 9))

        # check NX flag for SET command
        value = yield from protocol.set(u'my_key', u'my_value',
                                        expire=10, only_if_not_exists=True)
        self.assertIsNone(value)

        # check XX flag for SET command
        value = yield from protocol.set(u'other_key', 'some_value', only_if_exists=True)

        self.assertIsNone(value)

        # set with pexpire only if key exists
        value = yield from protocol.set(u'my_key', u'other_value',
                                        pexpire=20000, only_if_exists=True)
        self.assertEqual(value, StatusReply('OK'))

        value = yield from protocol.get(u'my_key')

        self.assertEqual(value, u'other_value')

        value = yield from protocol.ttl(u'my_key')
        self.assertIn(value, (20, 19))

    @redis_test
    def test_setex(self, transport, protocol):
        # Set
        value = yield from protocol.setex(u'my_key', 10, u'my_value')
        self.assertEqual(value, StatusReply('OK'))

        # TTL
        value = yield from protocol.ttl(u'my_key')
        self.assertIn(value, (10, 9)) # may be some delay

        # Get
        value = yield from protocol.get(u'my_key')
        self.assertEqual(value, u'my_value')

    @redis_test
    def test_setnx(self, transport, protocol):
        yield from protocol.delete([u'my_key'])

        # Setnx while key does not exists
        value = yield from protocol.setnx(u'my_key', u'my_value')
        self.assertEqual(value, True)

        # Get
        value = yield from protocol.get(u'my_key')
        self.assertEqual(value, u'my_value')

        # Setnx if key exists
        value = yield from protocol.setnx(u'my_key', u'other_value')
        self.assertEqual(value, False)

        # Get old value
        value = yield from protocol.get(u'my_key')
        self.assertEqual(value, u'my_value')

    @redis_test
    def test_special_characters(self, transport, protocol):
        # Test some special unicode values and spaces.
        value = u'my value with special chars " # éçåø´¨åø´h '

        result = yield from protocol.set(u'my key with spaces', value)
        result = yield from protocol.get(u'my key with spaces')
        self.assertEqual(result, value)

        # Test newlines
        value = u'ab\ncd\ref\r\ngh'
        result = yield from protocol.set(u'my-key', value)
        result = yield from protocol.get(u'my-key')
        self.assertEqual(result, value)

    @redis_test
    def test_mget(self, transport, protocol):
        # mget
        yield from protocol.set(u'my_key', u'a')
        yield from protocol.set(u'my_key2', u'b')
        result = yield from protocol.mget([ u'my_key', u'my_key2', u'not_exists'])
        self.assertIsInstance(result, ListReply)
        result = yield from result.aslist()
        self.assertEqual(result, [u'a', u'b', None])

    @redis_test
    def test_strlen(self, transport, protocol):
        yield from protocol.delete([ u'my_key' ])
        yield from protocol.delete([ u'my_key2' ])
        yield from protocol.delete([ u'my_key3' ])
        yield from protocol.set(u'my_key', u'my_value')
        yield from protocol.hset(u'my_key3', u'a', u'b')

        # strlen
        value = yield from protocol.strlen(u'my_key')
        self.assertEqual(value, len(u'my_value'))

        value = yield from protocol.strlen(u'my_key2')
        self.assertEqual(value, 0)

        with self.assertRaises(ErrorReply):
            yield from protocol.strlen(u'my_key3')
        # Redis exception: b'ERR Operation against a key holding the wrong kind of value')

    @redis_test
    def test_exists_and_delete(self, transport, protocol):
        # Set
        yield from protocol.set(u'my_key', u'aaa')
        value = yield from protocol.append(u'my_key', u'bbb')
        self.assertEqual(value, 6) # Total length
        value = yield from protocol.get(u'my_key')
        self.assertEqual(value, u'aaabbb')

    @redis_test
    def test_exists_and_delete2(self, transport, protocol):
        # Exists
        value = yield from protocol.exists(u'unknown_key')
        self.assertEqual(value, False)

        # Set
        value = yield from protocol.set(u'known_key', u'value')
        value = yield from protocol.exists(u'known_key')
        self.assertEqual(value, True)

        # Delete
        value = yield from protocol.set(u'known_key2', u'value')
        value = yield from protocol.delete([ u'known_key', u'known_key2' ])
        self.assertEqual(value, 2)

        value = yield from protocol.delete([ u'known_key' ])
        self.assertEqual(value, 0)

        value = yield from protocol.exists(u'known_key')
        self.assertEqual(value, False)

    @redis_test
    def test_rename(self, transport, protocol):
        # Set
        value = yield from protocol.set(u'old_key', u'value')
        value = yield from protocol.exists(u'old_key')
        self.assertEqual(value, True)

        # Rename
        value = yield from protocol.rename(u'old_key', u'new_key')
        self.assertEqual(value, StatusReply('OK'))

        value = yield from protocol.exists(u'old_key')
        self.assertEqual(value, False)
        value = yield from protocol.exists(u'new_key')
        self.assertEqual(value, True)

        value = yield from protocol.get(u'old_key')
        self.assertEqual(value, None)
        value = yield from protocol.get(u'new_key')
        self.assertEqual(value, 'value')

        # RenameNX
        yield from protocol.delete([ u'key3' ])
        value = yield from protocol.renamenx(u'new_key', u'key3')
        self.assertEqual(value, 1)

        yield from protocol.set(u'key4', u'existing-value')
        value = yield from protocol.renamenx(u'key3', u'key4')
        self.assertEqual(value, 0)

    @redis_test
    def test_expire(self, transport, protocol):
        # Set
        value = yield from protocol.set(u'key', u'value')

        # Expire (10s)
        value = yield from protocol.expire(u'key', 10)
        self.assertEqual(value, 1)

        value = yield from protocol.exists(u'key')
        self.assertEqual(value, True)

        # TTL
        value = yield from protocol.ttl(u'key')
        self.assertIsInstance(value, int)
        self.assertLessEqual(value, 10)

        # PTTL
        value = yield from protocol.pttl(u'key')
        self.assertIsInstance(value, int)
        self.assertLessEqual(value, 10 * 1000)

        # Pexpire
        value = yield from protocol.pexpire(u'key', 10*1000)
        self.assertEqual(value, 1) # XXX: check this
        value = yield from protocol.pttl(u'key')
        self.assertLessEqual(value, 10 * 1000)

        # Expire (1s) and wait
        value = yield from protocol.expire(u'key', 1)
        value = yield from protocol.exists(u'key')
        self.assertEqual(value, True)

        yield from asyncio.sleep(2, loop=self.loop)

        value = yield from protocol.exists(u'key')
        self.assertEqual(value, False)

        # Test persist
        yield from protocol.set(u'key', u'value')
        yield from protocol.expire(u'key', 1)
        value = yield from protocol.persist(u'key')
        self.assertEqual(value, 1)
        value = yield from protocol.persist(u'key')
        self.assertEqual(value, 0)

        yield from asyncio.sleep(2, loop=self.loop)

        value = yield from protocol.exists(u'key')
        self.assertEqual(value, True)

        # Test expireat
        value = yield from protocol.expireat(u'key', 1293840000)
        self.assertIsInstance(value, int)

        # Test pexpireat
        value = yield from protocol.pexpireat(u'key', 1555555555005)
        self.assertIsInstance(value, int)

    @redis_test
    def test_set(self, transport, protocol):
        # Create set
        value = yield from protocol.delete([ u'our_set' ])
        value = yield from protocol.sadd(u'our_set', [u'a', u'b'])
        value = yield from protocol.sadd(u'our_set', [u'c'])
        self.assertEqual(value, 1)

        # scard
        value = yield from protocol.scard(u'our_set')
        self.assertEqual(value, 3)

        # Smembers
        value = yield from protocol.smembers(u'our_set')
        self.assertIsInstance(value, SetReply)
        self.assertEqual(repr(value), u"SetReply(length=3)")
        value = yield from value.asset()
        self.assertEqual(value, { u'a', u'b', u'c' })

        # sismember
        value = yield from protocol.sismember(u'our_set', 'a')
        self.assertEqual(value, True)
        value = yield from protocol.sismember(u'our_set', 'd')
        self.assertEqual(value, False)

        # Intersection, union and diff
        yield from protocol.delete([ u'set2' ])
        yield from protocol.sadd(u'set2', [u'b', u'c', u'd', u'e'])

        value = yield from protocol.sunion([ u'our_set', 'set2' ])
        self.assertIsInstance(value, SetReply)
        value = yield from value.asset()
        self.assertEqual(value, set([u'a', u'b', u'c', u'd', u'e']))

        value = yield from protocol.sinter([ u'our_set', 'set2' ])
        value = yield from value.asset()
        self.assertEqual(value, set([u'b', u'c']))

        value = yield from protocol.sdiff([ u'our_set', 'set2' ])
        self.assertIsInstance(value, SetReply)
        value = yield from value.asset()
        self.assertEqual(value, set([u'a']))
        value = yield from protocol.sdiff([ u'set2', u'our_set' ])
        value = yield from value.asset()
        self.assertEqual(value, set([u'd', u'e']))

        # Interstore
        value = yield from protocol.sinterstore(u'result', [u'our_set', 'set2'])
        self.assertEqual(value, 2)
        value = yield from protocol.smembers(u'result')
        self.assertIsInstance(value, SetReply)
        value = yield from value.asset()
        self.assertEqual(value, set([u'b', u'c']))

        # Unionstore
        value = yield from protocol.sunionstore(u'result', [u'our_set', 'set2'])
        self.assertEqual(value, 5)
        value = yield from protocol.smembers(u'result')
        self.assertIsInstance(value, SetReply)
        value = yield from value.asset()
        self.assertEqual(value, set([u'a', u'b', u'c', u'd', u'e']))

        # Sdiffstore
        value = yield from protocol.sdiffstore(u'result', [u'set2', 'our_set'])
        self.assertEqual(value, 2)
        value = yield from protocol.smembers(u'result')
        self.assertIsInstance(value, SetReply)
        value = yield from value.asset()
        self.assertEqual(value, set([u'd', u'e']))

    @redis_test
    def test_srem(self, transport, protocol):
        yield from protocol.delete([ u'our_set' ])
        yield from protocol.sadd(u'our_set', [u'a', u'b', u'c', u'd'])

        # Call srem
        result = yield from protocol.srem(u'our_set', [u'b', u'c'])
        self.assertEqual(result, 2)

        result = yield from protocol.smembers(u'our_set')
        self.assertIsInstance(result, SetReply)
        result = yield from result.asset()
        self.assertEqual(result, set([u'a', u'd']))

    @redis_test
    def test_spop(self, transport, protocol):
        @asyncio.coroutine
        def setup():
            yield from protocol.delete([ u'my_set' ])
            yield from protocol.sadd(u'my_set', [u'value1'])
            yield from protocol.sadd(u'my_set', [u'value2'])

        # Test spop
        yield from setup()
        result = yield from protocol.spop(u'my_set')
        self.assertIn(result, [u'value1', u'value2'])
        result = yield from protocol.smembers(u'my_set')
        self.assertIsInstance(result, SetReply)
        result = yield from result.asset()
        self.assertEqual(len(result), 1)

        # Test srandmember
        yield from setup()
        result = yield from protocol.srandmember(u'my_set')
        self.assertIsInstance(result, SetReply)
        result = yield from result.asset()
        self.assertIn(list(result)[0], [u'value1', u'value2'])
        result = yield from protocol.smembers(u'my_set')
        self.assertIsInstance(result, SetReply)
        result = yield from result.asset()
        self.assertEqual(len(result), 2)

    @redis_test
    def test_type(self, transport, protocol):
        # Setup
        yield from protocol.delete([ u'key1' ])
        yield from protocol.delete([ u'key2' ])
        yield from protocol.delete([ u'key3' ])

        yield from protocol.set(u'key1', u'value')
        yield from protocol.lpush(u'key2', [u'value'])
        yield from protocol.sadd(u'key3', [u'value'])

        # Test types
        value = yield from protocol.type(u'key1')
        self.assertEqual(value, StatusReply('string'))

        value = yield from protocol.type(u'key2')
        self.assertEqual(value, StatusReply('list'))

        value = yield from protocol.type(u'key3')
        self.assertEqual(value, StatusReply('set'))

    @redis_test
    def test_list(self, transport, protocol):
        # Create list
        yield from protocol.delete([ u'my_list' ])
        value = yield from protocol.lpush(u'my_list', [u'v1', u'v2'])
        value = yield from protocol.rpush(u'my_list', [u'v3', u'v4'])
        self.assertEqual(value, 4)

        # lrange
        value = yield from protocol.lrange(u'my_list')
        self.assertIsInstance(value, ListReply)
        self.assertEqual(repr(value), u"ListReply(length=4)")
        value = yield from value.aslist()
        self.assertEqual(value, [ u'v2', 'v1', 'v3', 'v4'])

        # lset
        value = yield from protocol.lset(u'my_list', 3, 'new-value')
        self.assertEqual(value, StatusReply('OK'))

        value = yield from protocol.lrange(u'my_list')
        self.assertIsInstance(value, ListReply)
        value = yield from value.aslist()
        self.assertEqual(value, [ u'v2', 'v1', 'v3', 'new-value'])

        # lindex
        value = yield from protocol.lindex(u'my_list', 1)
        self.assertEqual(value, 'v1')
        value = yield from protocol.lindex(u'my_list', 10) # Unknown index
        self.assertEqual(value, None)

        # Length
        value = yield from protocol.llen(u'my_list')
        self.assertEqual(value, 4)

        # Remove element from list.
        value = yield from protocol.lrem(u'my_list', value=u'new-value')
        self.assertEqual(value, 1)

        # Pop
        value = yield from protocol.rpop(u'my_list')
        self.assertEqual(value, u'v3')
        value = yield from protocol.lpop(u'my_list')
        self.assertEqual(value, u'v2')
        value = yield from protocol.lpop(u'my_list')
        self.assertEqual(value, u'v1')
        value = yield from protocol.lpop(u'my_list')
        self.assertEqual(value, None)

        # Blocking lpop
        test_order = []

        @asyncio.coroutine
        def blpop():
            test_order.append('#1')
            value = yield from protocol.blpop([u'my_list'])
            self.assertIsInstance(value, BlockingPopReply)
            self.assertEqual(value.list_name, u'my_list')
            self.assertEqual(value.value, u'value')
            test_order.append('#3')
        f = asyncio.async(blpop(), loop=self.loop)

        transport2, protocol2 = yield from connect(self.loop)

        test_order.append('#2')
        yield from protocol2.rpush(u'my_list', [u'value'])
        yield from f
        self.assertEqual(test_order, ['#1', '#2', '#3'])

        # Blocking rpop
        @asyncio.coroutine
        def blpop():
            value = yield from protocol.brpop([u'my_list'])
            self.assertIsInstance(value, BlockingPopReply)
            self.assertEqual(value.list_name, u'my_list')
            self.assertEqual(value.value, u'value2')
        f = asyncio.async(blpop(), loop=self.loop)

        yield from protocol2.rpush(u'my_list', [u'value2'])
        yield from f

        transport2.close()

    @redis_test
    def test_brpoplpush(self, transport, protocol):
        yield from protocol.delete([ u'from' ])
        yield from protocol.delete([ u'to' ])
        yield from protocol.lpush(u'to', [u'1'])

        @asyncio.coroutine
        def brpoplpush():
            result = yield from protocol.brpoplpush(u'from', u'to')
            self.assertEqual(result, u'my_value')
        f = asyncio.async(brpoplpush(), loop=self.loop)

        transport2, protocol2 = yield from connect(self.loop)
        yield from protocol2.rpush(u'from', [u'my_value'])
        yield from f

        transport2.close()

    @redis_test
    def test_blocking_timeout(self, transport, protocol):
        yield from protocol.delete([u'from'])
        yield from protocol.delete([u'to'])

        # brpoplpush
        with self.assertRaises(TimeoutError) as e:
            result = yield from protocol.brpoplpush(u'from', u'to', 1)
        self.assertIn('Timeout in brpoplpush', e.exception.args[0])

        # brpop
        with self.assertRaises(TimeoutError) as e:
            result = yield from protocol.brpop([u'from'], 1)
        self.assertIn('Timeout in blocking pop', e.exception.args[0])

        # blpop
        with self.assertRaises(TimeoutError) as e:
            result = yield from protocol.blpop([u'from'], 1)
        self.assertIn('Timeout in blocking pop', e.exception.args[0])

    @redis_test
    def test_linsert(self, transport, protocol):
        # Prepare
        yield from protocol.delete([ u'my_list' ])
        yield from protocol.rpush(u'my_list', [u'1'])
        yield from protocol.rpush(u'my_list', [u'2'])
        yield from protocol.rpush(u'my_list', [u'3'])

        # Insert after
        result = yield from protocol.linsert(u'my_list', u'1', u'A')
        self.assertEqual(result, 4)
        result = yield from protocol.lrange(u'my_list')
        self.assertIsInstance(result, ListReply)
        result = yield from result.aslist()
        self.assertEqual(result, [u'1', u'A', u'2', u'3'])

        # Insert before
        result = yield from protocol.linsert(u'my_list', u'3', u'B', before=True)
        self.assertEqual(result, 5)
        result = yield from protocol.lrange(u'my_list')
        self.assertIsInstance(result, ListReply)
        result = yield from result.aslist()
        self.assertEqual(result, [u'1', u'A', u'2', u'B', u'3'])

    @redis_test
    def test_rpoplpush(self, transport, protocol):
        # Prepare
        yield from protocol.delete([ u'my_list' ])
        yield from protocol.delete([ u'my_list2' ])
        yield from protocol.lpush(u'my_list', [u'value'])
        yield from protocol.lpush(u'my_list2', [u'value2'])

        value = yield from protocol.llen(u'my_list')
        value2 = yield from protocol.llen(u'my_list2')
        self.assertEqual(value, 1)
        self.assertEqual(value2, 1)

        # rpoplpush
        result = yield from protocol.rpoplpush(u'my_list', u'my_list2')
        self.assertEqual(result, u'value')

    @redis_test
    def test_pushx(self, transport, protocol):
        yield from protocol.delete([ u'my_list' ])

        # rpushx
        result = yield from protocol.rpushx(u'my_list', u'a')
        self.assertEqual(result, 0)

        yield from protocol.rpush(u'my_list', [u'a'])
        result = yield from protocol.rpushx(u'my_list', u'a')
        self.assertEqual(result, 2)

        # lpushx
        yield from protocol.delete([ u'my_list' ])
        result = yield from protocol.lpushx(u'my_list', u'a')
        self.assertEqual(result, 0)

        yield from protocol.rpush(u'my_list', [u'a'])
        result = yield from protocol.lpushx(u'my_list', u'a')
        self.assertEqual(result, 2)

    @redis_test
    def test_ltrim(self, transport, protocol):
        yield from protocol.delete([ u'my_list' ])
        yield from protocol.lpush(u'my_list', [u'a'])
        yield from protocol.lpush(u'my_list', [u'b'])
        result = yield from protocol.ltrim(u'my_list')
        self.assertEqual(result, StatusReply('OK'))

    @redis_test
    def test_hashes(self, transport, protocol):
        yield from protocol.delete([ u'my_hash' ])

        # Set in hash
        result = yield from protocol.hset(u'my_hash', u'key', u'value')
        self.assertEqual(result, 1)
        result = yield from protocol.hset(u'my_hash', u'key2', u'value2')
        self.assertEqual(result, 1)

        # hlen
        result = yield from protocol.hlen(u'my_hash')
        self.assertEqual(result, 2)

        # hexists
        result = yield from protocol.hexists(u'my_hash', u'key')
        self.assertEqual(result, True)
        result = yield from protocol.hexists(u'my_hash', u'unknown_key')
        self.assertEqual(result, False)

        # Get from hash
        result = yield from protocol.hget(u'my_hash', u'key2')
        self.assertEqual(result, u'value2')
        result = yield from protocol.hget(u'my_hash', u'unknown-key')
        self.assertEqual(result, None)

        result = yield from protocol.hgetall(u'my_hash')
        self.assertIsInstance(result, DictReply)
        self.assertEqual(repr(result), u"DictReply(length=2)")
        result = yield from result.asdict()
        self.assertEqual(result, {u'key': u'value', u'key2': u'value2' })

        result = yield from protocol.hkeys(u'my_hash')
        self.assertIsInstance(result, SetReply)
        result = yield from result.asset()
        self.assertIsInstance(result, set)
        self.assertEqual(result, {u'key', u'key2' })

        result = yield from protocol.hvals(u'my_hash')
        self.assertIsInstance(result, ListReply)
        result = yield from result.aslist()
        self.assertIsInstance(result, list)
        self.assertEqual(set(result), {u'value', u'value2' })

        # HDel
        result = yield from protocol.hdel(u'my_hash', [u'key2'])
        self.assertEqual(result, 1)
        result = yield from protocol.hdel(u'my_hash', [u'key2'])
        self.assertEqual(result, 0)

        result = yield from protocol.hkeys(u'my_hash')
        self.assertIsInstance(result, SetReply)
        result = yield from result.asset()
        self.assertEqual(result, { u'key' })

    @redis_test
    def test_keys(self, transport, protocol):
        # Create some keys in this 'namespace'
        yield from protocol.set('our-keytest-key1', 'a')
        yield from protocol.set('our-keytest-key2', 'a')
        yield from protocol.set('our-keytest-key3', 'a')

        # Test 'keys'
        multibulk = yield from protocol.keys(u'our-keytest-key*')
        generator = [ (yield from f) for f in multibulk ]
        all_keys = yield from generator
        self.assertEqual(set(all_keys), {
                            'our-keytest-key1',
                            'our-keytest-key2',
                            'our-keytest-key3' })

    @redis_test
    def test_hmset_get(self, transport, protocol):
        yield from protocol.delete([ u'my_hash' ])
        yield from protocol.hset(u'my_hash', u'a', u'1')

        # HMSet
        result = yield from protocol.hmset(u'my_hash', { 'b':'2', 'c': '3'})
        self.assertEqual(result, StatusReply('OK'))

        # HMGet
        result = yield from protocol.hmget(u'my_hash', [u'a', u'b', u'c'])
        self.assertIsInstance(result, ListReply)
        result = yield from result.aslist()
        self.assertEqual(result, [ u'1', u'2', u'3'])

        result = yield from protocol.hmget(u'my_hash', [u'c', u'b'])
        self.assertIsInstance(result, ListReply)
        result = yield from result.aslist()
        self.assertEqual(result, [ u'3', u'2' ])

        # Hsetnx
        result = yield from protocol.hsetnx(u'my_hash', u'b', '4')
        self.assertEqual(result, 0) # Existing key. Not set
        result = yield from protocol.hget(u'my_hash', u'b')
        self.assertEqual(result, u'2')

        result = yield from protocol.hsetnx(u'my_hash', u'd', '5')
        self.assertEqual(result, 1) # New key, set
        result = yield from protocol.hget(u'my_hash', u'd')
        self.assertEqual(result, u'5')

    @redis_test
    def test_hincr(self, transport, protocol):
        yield from protocol.delete([ u'my_hash' ])
        yield from protocol.hset(u'my_hash', u'a', u'10')

        # hincrby
        result = yield from protocol.hincrby(u'my_hash', u'a', 2)
        self.assertEqual(result, 12)

        # hincrbyfloat
        result = yield from protocol.hincrbyfloat(u'my_hash', u'a', 3.7)
        self.assertEqual(result, 15.7)

    @redis_test
    def test_pubsub(self, transport, protocol):
        @asyncio.coroutine
        def listener():
            # Subscribe
            transport2, protocol2 = yield from connect(self.loop)

            self.assertEqual(protocol2.in_pubsub, False)
            subscription = yield from protocol2.start_subscribe()
            self.assertIsInstance(subscription, Subscription)
            self.assertEqual(protocol2.in_pubsub, True)
            yield from subscription.subscribe([u'our_channel'])

            value = yield from subscription.next_published()
            self.assertIsInstance(value, PubSubReply)
            self.assertEqual(value.channel, u'our_channel')
            self.assertEqual(value.value, u'message1')

            value = yield from subscription.next_published()
            self.assertIsInstance(value, PubSubReply)
            self.assertEqual(value.channel, u'our_channel')
            self.assertEqual(value.value, u'message2')
            self.assertEqual(repr(value), u"PubSubReply(channel='our_channel', value='message2')")

            return transport2

        f = asyncio.async(listener(), loop=self.loop)

        @asyncio.coroutine
        def sender():
            value = yield from protocol.publish(u'our_channel', 'message1')
            self.assertGreaterEqual(value, 1) # Nr of clients that received the message
            value = yield from protocol.publish(u'our_channel', 'message2')
            self.assertGreaterEqual(value, 1)

            # Test pubsub_channels
            result = yield from protocol.pubsub_channels()
            self.assertIsInstance(result, ListReply)
            result = yield from result.aslist()
            self.assertIn(u'our_channel', result)

            result = yield from protocol.pubsub_channels_aslist(u'our_c*')
            self.assertIn(u'our_channel', result)

            result = yield from protocol.pubsub_channels_aslist(u'unknown-channel-prefix*')
            self.assertEqual(result, [])

            # Test pubsub numsub.
            result = yield from protocol.pubsub_numsub([ u'our_channel', u'some_unknown_channel' ])
            self.assertIsInstance(result, DictReply)
            result = yield from result.asdict()
            self.assertEqual(len(result), 2)
            self.assertGreater(int(result['our_channel']), 0)
                    # XXX: the cast to int is required, because the redis
                    #      protocol currently returns strings instead of
                    #      integers for the count. See:
                    #      https://github.com/antirez/redis/issues/1561
            self.assertEqual(int(result['some_unknown_channel']), 0)

            # Test pubsub numpat
            result = yield from protocol.pubsub_numpat()
            self.assertIsInstance(result, int)

        yield from asyncio.sleep(.5, loop=self.loop)
        yield from sender()
        transport2 = yield from f
        transport2.close()

    @redis_test
    def test_pubsub_many(self, transport, protocol):
        """ Create a listener that listens to several channels. """
        @asyncio.coroutine
        def listener():
            # Subscribe
            transport2, protocol2 = yield from connect(self.loop)

            self.assertEqual(protocol2.in_pubsub, False)
            subscription = yield from protocol2.start_subscribe()
            yield from subscription.subscribe(['channel1', 'channel2'])
            yield from subscription.subscribe(['channel3', 'channel4'])

            results = []
            for i in range(4):
                results.append((yield from subscription.next_published()))

            self.assertEqual(results, [
                    PubSubReply('channel1', 'message1'),
                    PubSubReply('channel2', 'message2'),
                    PubSubReply('channel3', 'message3'),
                    PubSubReply('channel4', 'message4'),
                ])

            transport2.close()

        f = asyncio.async(listener(), loop=self.loop)

        @asyncio.coroutine
        def sender():
            # Should not be received
            yield from protocol.publish('channel5', 'message5')

            # These for should be received.
            yield from protocol.publish('channel1', 'message1')
            yield from protocol.publish('channel2', 'message2')
            yield from protocol.publish('channel3', 'message3')
            yield from protocol.publish('channel4', 'message4')

        yield from asyncio.sleep(.5, loop=self.loop)
        yield from sender()
        yield from f

    @redis_test
    def test_incr(self, transport, protocol):
        yield from protocol.set(u'key1', u'3')

        # Incr
        result = yield from protocol.incr(u'key1')
        self.assertEqual(result, 4)
        result = yield from protocol.incr(u'key1')
        self.assertEqual(result, 5)

        # Incrby
        result = yield from protocol.incrby(u'key1', 10)
        self.assertEqual(result, 15)

        # Decr
        result = yield from protocol.decr(u'key1')
        self.assertEqual(result, 14)

        # Decrby
        result = yield from protocol.decrby(u'key1', 4)
        self.assertEqual(result, 10)

    @redis_test
    def test_bitops(self, transport, protocol):
        yield from protocol.set('a', 'fff')
        yield from protocol.set('b', '555')

        a = b'f'[0]
        b = b'5'[0]

        # Calculate set bits in the character 'f'
        set_bits = len([ c for c in bin(a) if c == '1' ])

        # Bitcount
        result = yield from protocol.bitcount('a')
        self.assertEqual(result, set_bits * 3)

        # And
        result = yield from protocol.bitop_and('result', ['a', 'b'])
        self.assertEqual(result, 3)
        result = yield from protocol.get('result')
        self.assertEqual(result, chr(a & b) * 3)

        # Or
        result = yield from protocol.bitop_or('result', ['a', 'b'])
        self.assertEqual(result, 3)
        result = yield from protocol.get('result')
        self.assertEqual(result, chr(a | b) * 3)

        # Xor
        result = yield from protocol.bitop_xor('result', ['a', 'b'])
        self.assertEqual(result, 3)
        result = yield from protocol.get('result')
        self.assertEqual(result, chr(a ^ b) * 3)

        # Not
        result = yield from protocol.bitop_not('result', 'a')
        self.assertEqual(result, 3)

            # Check result using bytes protocol
        bytes_transport, bytes_protocol = yield from connect(self.loop, lambda **kw: RedisProtocol(encoder=BytesEncoder(), **kw))
        result = yield from bytes_protocol.get(b'result')
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, bytes((~a % 256, ~a % 256, ~a % 256)))

        bytes_transport.close()

    @redis_test
    def test_setbit(self, transport, protocol):
        yield from protocol.set('a', 'fff')

        value = yield from protocol.getbit('a', 3)
        self.assertIsInstance(value, bool)
        self.assertEqual(value, False)

        value = yield from protocol.setbit('a', 3, True)
        self.assertIsInstance(value, bool)
        self.assertEqual(value, False) # Set returns the old value.

        value = yield from protocol.getbit('a', 3)
        self.assertIsInstance(value, bool)
        self.assertEqual(value, True)

    @redis_test
    def test_zscore(self, transport, protocol):
        yield from protocol.delete([ 'myzset' ])

        # Test zscore return value for NIL server response
        value = yield from protocol.zscore('myzset', 'key')
        self.assertIsNone(value)

        # zadd key 4.0
        result = yield from protocol.zadd('myzset', { 'key': 4})
        self.assertEqual(result, 1)

        # Test zscore value for existing zset members
        value = yield from protocol.zscore('myzset', 'key')
        self.assertEqual(value, 4.0)

    @redis_test
    def test_zset(self, transport, protocol):
        yield from protocol.delete([ 'myzset' ])

        # Test zadd
        result = yield from protocol.zadd('myzset', { 'key': 4, 'key2': 5, 'key3': 5.5 })
        self.assertEqual(result, 3)

        # Test zcard
        result = yield from protocol.zcard('myzset')
        self.assertEqual(result, 3)

        # Test zrank
        result = yield from protocol.zrank('myzset', 'key')
        self.assertEqual(result, 0)
        result = yield from protocol.zrank('myzset', 'key3')
        self.assertEqual(result, 2)

        result = yield from protocol.zrank('myzset', 'unknown-key')
        self.assertEqual(result, None)

        # Test revrank
        result = yield from protocol.zrevrank('myzset', 'key')
        self.assertEqual(result, 2)
        result = yield from protocol.zrevrank('myzset', 'key3')
        self.assertEqual(result, 0)

        result = yield from protocol.zrevrank('myzset', 'unknown-key')
        self.assertEqual(result, None)

        # Test zrange
        result = yield from protocol.zrange('myzset')
        self.assertIsInstance(result, ZRangeReply)
        self.assertEqual(repr(result), u"ZRangeReply(length=3)")
        self.assertEqual((yield from result.asdict()),
                { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })

        result = yield from protocol.zrange('myzset')
        self.assertIsInstance(result, ZRangeReply)

        etalon = [ ('key', 4.0), ('key2', 5.0), ('key3', 5.5) ]
        for i, f in enumerate(result): # Ordering matter
            d = yield from f
            self.assertEqual(d, etalon[i])

        # Test zrange_asdict
        result = yield from protocol.zrange_asdict('myzset')
        self.assertEqual(result, { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })

        # Test zrange with negative indexes
        result = yield from protocol.zrange('myzset', -2, -1)
        self.assertEqual((yield from result.asdict()),
                {'key2': 5.0, 'key3': 5.5 })
        result = yield from protocol.zrange('myzset', -2, -1)
        self.assertIsInstance(result, ZRangeReply)

        for f in result:
            d = yield from f
            self.assertIn(d, [ ('key2', 5.0), ('key3', 5.5) ])

        # Test zrangebyscore
        result = yield from protocol.zrangebyscore('myzset')
        self.assertEqual((yield from result.asdict()),
                { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })

        result = yield from protocol.zrangebyscore('myzset', min=ZScoreBoundary(4.5))
        self.assertEqual((yield from result.asdict()),
                { 'key2': 5.0, 'key3': 5.5 })

        result = yield from protocol.zrangebyscore('myzset', max=ZScoreBoundary(5.5))
        self.assertEqual((yield from result.asdict()),
                { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })
        result = yield from protocol.zrangebyscore('myzset',
                        max=ZScoreBoundary(5.5, exclude_boundary=True))
        self.assertEqual((yield from result.asdict()),
                { 'key': 4.0, 'key2': 5.0 })

        # Test zrevrangebyscore (identical to zrangebyscore, unless we call aslist)
        result = yield from protocol.zrevrangebyscore('myzset')
        self.assertIsInstance(result, DictReply)
        self.assertEqual((yield from result.asdict()),
                { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })

        self.assertEqual((yield from protocol.zrevrangebyscore_asdict('myzset')),
                { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })

        result = yield from protocol.zrevrangebyscore('myzset', min=ZScoreBoundary(4.5))
        self.assertEqual((yield from result.asdict()),
                { 'key2': 5.0, 'key3': 5.5 })

        result = yield from protocol.zrevrangebyscore('myzset', max=ZScoreBoundary(5.5))
        self.assertIsInstance(result, DictReply)
        self.assertEqual((yield from result.asdict()),
                { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })
        result = yield from protocol.zrevrangebyscore('myzset',
                        max=ZScoreBoundary(5.5, exclude_boundary=True))
        self.assertEqual((yield from result.asdict()),
                { 'key': 4.0, 'key2': 5.0 })


    @redis_test
    def test_zrevrange(self, transport, protocol):
        yield from protocol.delete([ 'myzset' ])

        # Test zadd
        result = yield from protocol.zadd('myzset', { 'key': 4, 'key2': 5, 'key3': 5.5 })
        self.assertEqual(result, 3)

        # Test zrevrange
        result = yield from protocol.zrevrange('myzset')
        self.assertIsInstance(result, ZRangeReply)
        self.assertEqual(repr(result), u"ZRangeReply(length=3)")
        self.assertEqual((yield from result.asdict()),
                { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })

        self.assertEqual((yield from protocol.zrevrange_asdict('myzset')),
                { 'key': 4.0, 'key2': 5.0, 'key3': 5.5 })

        result = yield from protocol.zrevrange('myzset')
        self.assertIsInstance(result, ZRangeReply)

        etalon = [ ('key3', 5.5), ('key2', 5.0), ('key', 4.0) ]
        for i, f in enumerate(result): # Ordering matter
            d = yield from f
            self.assertEqual(d, etalon[i])

    @redis_test
    def test_zset_zincrby(self, transport, protocol):
        yield from protocol.delete([ 'myzset' ])
        yield from protocol.zadd('myzset', { 'key': 4, 'key2': 5, 'key3': 5.5 })

        # Test zincrby
        result = yield from protocol.zincrby('myzset', 1.1, 'key')
        self.assertEqual(result, 5.1)

        result = yield from protocol.zrange('myzset')
        self.assertEqual((yield from result.asdict()),
                { 'key': 5.1, 'key2': 5.0, 'key3': 5.5 })

    @redis_test
    def test_zset_zrem(self, transport, protocol):
        yield from protocol.delete([ 'myzset' ])
        yield from protocol.zadd('myzset', { 'key': 4, 'key2': 5, 'key3': 5.5 })

        # Test zrem
        result = yield from protocol.zrem('myzset', ['key'])
        self.assertEqual(result, 1)

        result = yield from protocol.zrem('myzset', ['key'])
        self.assertEqual(result, 0)

        result = yield from protocol.zrange('myzset')
        self.assertEqual((yield from result.asdict()),
                { 'key2': 5.0, 'key3': 5.5 })

    @redis_test
    def test_zset_zrembyscore(self, transport, protocol):
        # Test zremrangebyscore (1)
        yield from protocol.delete([ 'myzset' ])
        yield from protocol.zadd('myzset', { 'key': 4, 'key2': 5, 'key3': 5.5 })

        result = yield from protocol.zremrangebyscore('myzset', min=ZScoreBoundary(5.0))
        self.assertEqual(result, 2)
        result = yield from protocol.zrange('myzset')
        self.assertEqual((yield from result.asdict()), { 'key': 4.0 })

        # Test zremrangebyscore (2)
        yield from protocol.delete([ 'myzset' ])
        yield from protocol.zadd('myzset', { 'key': 4, 'key2': 5, 'key3': 5.5 })

        result = yield from protocol.zremrangebyscore('myzset', max=ZScoreBoundary(5.0))
        self.assertEqual(result, 2)
        result = yield from protocol.zrange('myzset')
        self.assertEqual((yield from result.asdict()), { 'key3': 5.5 })

    @redis_test
    def test_zset_zremrangebyrank(self, transport, protocol):
        @asyncio.coroutine
        def setup():
            yield from protocol.delete([ 'myzset' ])
            yield from protocol.zadd('myzset', { 'key': 4, 'key2': 5, 'key3': 5.5 })

        # Test zremrangebyrank (1)
        yield from setup()
        result = yield from protocol.zremrangebyrank('myzset')
        self.assertEqual(result, 3)
        result = yield from protocol.zrange('myzset')
        self.assertEqual((yield from result.asdict()), { })

        # Test zremrangebyrank (2)
        yield from setup()
        result = yield from protocol.zremrangebyrank('myzset', min=2)
        self.assertEqual(result, 1)
        result = yield from protocol.zrange('myzset')
        self.assertEqual((yield from result.asdict()), { 'key': 4.0, 'key2': 5.0 })

        # Test zremrangebyrank (3)
        yield from setup()
        result = yield from protocol.zremrangebyrank('myzset', max=1)
        self.assertEqual(result, 2)
        result = yield from protocol.zrange('myzset')
        self.assertEqual((yield from result.asdict()), { 'key3': 5.5 })

    @redis_test
    def test_zunionstore(self, transport, protocol):
        yield from protocol.delete([ 'set_a', 'set_b' ])
        yield from protocol.zadd('set_a', { 'key': 4, 'key2': 5, 'key3': 5.5 })
        yield from protocol.zadd('set_b', { 'key': -1, 'key2': 1.1, 'key4': 9 })

        # Call zunionstore
        result = yield from protocol.zunionstore('union_key', [ 'set_a', 'set_b' ])
        self.assertEqual(result, 4)
        result = yield from protocol.zrange('union_key')
        result = yield from result.asdict()
        self.assertEqual(result, { 'key': 3.0, 'key2': 6.1, 'key3': 5.5, 'key4': 9.0 })

        # Call zunionstore with weights.
        result = yield from protocol.zunionstore('union_key', [ 'set_a', 'set_b' ], [1, 1.5])
        self.assertEqual(result, 4)
        result = yield from protocol.zrange('union_key')
        result = yield from result.asdict()
        self.assertEqual(result, { 'key': 2.5, 'key2': 6.65, 'key3': 5.5, 'key4': 13.5 })

    @redis_test
    def test_zinterstore(self, transport, protocol):
        yield from protocol.delete([ 'set_a', 'set_b' ])
        yield from protocol.zadd('set_a', { 'key': 4, 'key2': 5, 'key3': 5.5 })
        yield from protocol.zadd('set_b', { 'key': -1, 'key2': 1.5, 'key4': 9 })

        # Call zinterstore
        result = yield from protocol.zinterstore('inter_key', [ 'set_a', 'set_b' ])
        self.assertEqual(result, 2)
        result = yield from protocol.zrange('inter_key')
        result = yield from result.asdict()
        self.assertEqual(result, { 'key': 3.0, 'key2': 6.5 })

        # Call zinterstore with weights.
        result = yield from protocol.zinterstore('inter_key', [ 'set_a', 'set_b' ], [1, 1.5])
        self.assertEqual(result, 2)
        result = yield from protocol.zrange('inter_key')
        result = yield from result.asdict()
        self.assertEqual(result, { 'key': 2.5, 'key2': 7.25, })

    @redis_test
    def test_randomkey(self, transport, protocol):
        yield from protocol.set(u'key1', u'value')
        result = yield from protocol.randomkey()
        self.assertIsInstance(result, str)

    @redis_test
    def test_dbsize(self, transport, protocol):
        result = yield from protocol.dbsize()
        self.assertIsInstance(result, int)

    @redis_test
    def test_client_names(self, transport, protocol):
        # client_setname
        result = yield from protocol.client_setname(u'my-connection-name')
        self.assertEqual(result, StatusReply('OK'))

        # client_getname
        result = yield from protocol.client_getname()
        self.assertEqual(result, u'my-connection-name')

        # client list
        result = yield from protocol.client_list()
        self.assertIsInstance(result, ClientListReply)

    @redis_test
    def test_lua_script(self, transport, protocol):
        code = """
        local value = redis.call('GET', KEYS[1])
        value = tonumber(value)
        return value * ARGV[1]
        """
        yield from protocol.set('foo', '2')

        # Register script
        script = yield from protocol.register_script(code)
        self.assertIsInstance(script, Script)

        # Call script.
        result = yield from script.run(keys=['foo'], args=['5'])
        self.assertIsInstance(result, EvalScriptReply)
        result = yield from result.return_value()
        self.assertEqual(result, 10)

        # Test evalsha directly
        result = yield from protocol.evalsha(script.sha, keys=['foo'], args=['5'])
        self.assertIsInstance(result, EvalScriptReply)
        result = yield from result.return_value()
        self.assertEqual(result, 10)

        # Test script exists
        result = yield from protocol.script_exists([ script.sha, script.sha, 'unknown-script' ])
        self.assertEqual(result, [ True, True, False ])

        # Test script flush
        result = yield from protocol.script_flush()
        self.assertEqual(result, StatusReply('OK'))

        result = yield from protocol.script_exists([ script.sha, script.sha, 'unknown-script' ])
        self.assertEqual(result, [ False, False, False ])

        # Test another script where evalsha returns a string.
        code2 = """
        return "text"
        """
        script2 = yield from protocol.register_script(code2)
        result = yield from protocol.evalsha(script2.sha)
        self.assertIsInstance(result, EvalScriptReply)
        result = yield from result.return_value()
        self.assertIsInstance(result, str)
        self.assertEqual(result, u'text')

    @redis_test
    def test_script_return_types(self, transport, protocol):
        #  Test whether LUA scripts are returning correct return values.
        script_and_return_values = {
            'return "string" ': "string", # str
            'return 5 ': 5, # int
            'return ': None, # NoneType
            'return {1, 2, 3}': [1, 2, 3], # list

            # Complex nested data structure.
            'return {1, 2, "text", {3, { 4, 5 }, 6, { 7, 8 } } }': [1, 2, "text", [3, [ 4, 5 ], 6, [ 7, 8 ] ] ],
        }
        for code, return_value in script_and_return_values.items():
            # Register script
            script = yield from protocol.register_script(code)

            # Call script.
            scriptreply = yield from script.run()
            result = yield from scriptreply.return_value()
            self.assertEqual(result, return_value)

    @redis_test
    def test_script_kill(self, transport, protocol):
        # Test script kill (when nothing is running.)
        with self.assertRaises(NoRunningScriptError):
            result = yield from protocol.script_kill()

        # Test script kill (when a while/true is running.)

        @asyncio.coroutine
        def run_while_true():
            code = """
            local i = 0
            while true do
                i = i + 1
            end
            """
            transport, protocol = yield from connect(self.loop, RedisProtocol)

            script = yield from protocol.register_script(code)
            with self.assertRaises(ScriptKilledError):
                yield from script.run()

            transport.close()

        # (start script)
        asyncio.async(run_while_true(), loop=self.loop)
        yield from asyncio.sleep(.5, loop=self.loop)

        result = yield from protocol.script_kill()
        self.assertEqual(result, StatusReply('OK'))

    @redis_test
    def test_transaction(self, transport, protocol):
        # Prepare
        yield from protocol.set(u'my_key', u'a')
        yield from protocol.set(u'my_key2', u'b')
        yield from protocol.set(u'my_key3', u'c')
        yield from protocol.delete([ u'my_hash' ])
        yield from protocol.hmset(u'my_hash', {'a':'1', 'b':'2', 'c':'3'})

        # Start transaction
        self.assertEqual(protocol.in_transaction, False)
        transaction = yield from protocol.multi()
        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(protocol.in_transaction, True)

        # Run commands
        f1 = yield from transaction.get('my_key')
        f2 = yield from transaction.mget(['my_key', 'my_key2'])
        f3 = yield from transaction.get('my_key3')
        f4 = yield from transaction.mget(['my_key2', 'my_key3'])
        f5 = yield from transaction.hgetall('my_hash')

        for f in [ f1, f2, f3, f4, f5]:
            self.assertIsInstance(f, Future)

        # Running commands directly on protocol should fail.
        with self.assertRaises(Error) as e:
            yield from protocol.set('a', 'b')
        self.assertEqual(e.exception.args[0], 'Cannot run command inside transaction (use the Transaction object instead)')

        # Calling subscribe inside transaction should fail.
        with self.assertRaises(Error) as e:
            yield from transaction.start_subscribe()
        self.assertEqual(e.exception.args[0], 'Cannot start pubsub listener when a protocol is in use.')

        # Complete transaction
        result = yield from transaction.exec()
        self.assertEqual(result, None)

        # Read futures
        r1 = yield from f1
        r3 = yield from f3 # 2 & 3 switched by purpose. (order shouldn't matter.)
        r2 = yield from f2
        r4 = yield from f4
        r5 = yield from f5

        r2 = yield from r2.aslist()
        r4 = yield from r4.aslist()
        r5 = yield from r5.asdict()

        self.assertEqual(r1, u'a')
        self.assertEqual(r2, [u'a', u'b'])
        self.assertEqual(r3, u'c')
        self.assertEqual(r4, [u'b', u'c'])
        self.assertEqual(r5, { 'a': '1', 'b': '2', 'c': '3' })

    @redis_test
    def test_discard_transaction(self, transport, protocol):
        yield from protocol.set(u'my_key', u'a')

        transaction = yield from protocol.multi()
        yield from transaction.set(u'my_key', 'b')

        # Discard
        result = yield from transaction.discard()
        self.assertEqual(result, None)

        result = yield from protocol.get(u'my_key')
        self.assertEqual(result, u'a')

        # Calling anything on the transaction after discard should fail.
        with self.assertRaises(Error) as e:
            result = yield from transaction.get(u'my_key')
        self.assertEqual(e.exception.args[0], 'Transaction already finished or invalid.')

    @redis_test
    def test_nesting_transactions(self, transport, protocol):
        # That should fail.
        transaction = yield from protocol.multi()

        with self.assertRaises(Error) as e:
            transaction = yield from transaction.multi()
        self.assertEqual(e.exception.args[0], 'Multi calls can not be nested.')

    @redis_test
    def test_password(self, transport, protocol):
        # Set password
        result = yield from protocol.config_set('requirepass', 'newpassword')
        self.assertIsInstance(result, StatusReply)

        # Further redis queries should fail without re-authenticating.
        with self.assertRaises(ErrorReply) as e:
            yield from protocol.set('my-key', 'value')
        self.assertEqual(e.exception.args[0], 'NOAUTH Authentication required.')

        # Reconnect:
        result = yield from protocol.auth('newpassword')
        self.assertIsInstance(result, StatusReply)

        # Redis queries should work again.
        result = yield from protocol.set('my-key', 'value')
        self.assertIsInstance(result, StatusReply)

        # Try connecting through new Protocol instance.
        transport2, protocol2 = yield from connect(self.loop, lambda **kw: RedisProtocol(password='newpassword', **kw))
        result = yield from protocol2.set('my-key', 'value')
        self.assertIsInstance(result, StatusReply)
        transport2.close()

        # Reset password
        result = yield from protocol.config_set('requirepass', '')
        self.assertIsInstance(result, StatusReply)

    @redis_test
    def test_condfig(self, transport, protocol):
        # Config get
        result = yield from protocol.config_get('loglevel')
        self.assertIsInstance(result, ConfigPairReply)
        self.assertEqual(result.parameter, 'loglevel')
        self.assertIsInstance(result.value, str)

        # Config set
        result = yield from protocol.config_set('loglevel', result.value)
        self.assertIsInstance(result, StatusReply)

        # Resetstat
        result = yield from protocol.config_resetstat()
        self.assertIsInstance(result, StatusReply)

        # XXX: config_rewrite not tested.

    @redis_test
    def test_info(self, transport, protocol):
        result = yield from protocol.info()
        self.assertIsInstance(result, InfoReply)
        # TODO: implement and test InfoReply class

        result = yield from protocol.info('CPU')
        self.assertIsInstance(result, InfoReply)

    @redis_test
    def test_scan(self, transport, protocol):
        # Run scan command
        cursor = yield from protocol.scan(match='*')
        self.assertIsInstance(cursor, Cursor)

        # Walk through cursor
        received = []
        while True:
            i = yield from cursor.fetchone()
            if not i: break

            self.assertIsInstance(i, str)
            received.append(i)

        # The amount of keys should equal 'dbsize'
        dbsize = yield from protocol.dbsize()
        self.assertEqual(dbsize, len(received))

        # Test fetchall
        cursor = yield from protocol.scan(match='*')
        received2 = yield from cursor.fetchall()
        self.assertIsInstance(received2, list)
        self.assertEqual(set(received), set(received2))

    @redis_test
    def test_set_scan(self, transport, protocol):
        """ Test sscan """
        size = 1000
        items = [ 'value-%i' % i for i in range(size) ]

        # Create a huge set
        yield from protocol.delete(['my-set'])
        yield from protocol.sadd('my-set', items)

        # Scan this set.
        cursor = yield from protocol.sscan('my-set')

        received = []
        while True:
            i = yield from cursor.fetchone()
            if not i: break

            self.assertIsInstance(i, str)
            received.append(i)

        # Check result
        self.assertEqual(len(received), size)
        self.assertEqual(set(received), set(items))

        # Test fetchall
        cursor = yield from protocol.sscan('my-set')
        received2 = yield from cursor.fetchall()
        self.assertIsInstance(received2, set)
        self.assertEqual(set(received), received2)

    @redis_test
    def test_dict_scan(self, transport, protocol):
        """ Test hscan """
        size = 1000
        items = { 'key-%i' % i: 'values-%i' % i for i in range(size) }

        # Create a huge set
        yield from protocol.delete(['my-dict'])
        yield from protocol.hmset('my-dict', items)

        # Scan this set.
        cursor = yield from protocol.hscan('my-dict')

        received = {}
        while True:
            i = yield from cursor.fetchone()
            if not i: break

            self.assertIsInstance(i, dict)
            received.update(i)

        # Check result
        self.assertEqual(len(received), size)
        self.assertEqual(received, items)

        # Test fetchall
        cursor = yield from protocol.hscan('my-dict')
        received2 = yield from cursor.fetchall()
        self.assertIsInstance(received2, dict)
        self.assertEqual(received, received2)

    @redis_test
    def test_sorted_dict_scan(self, transport, protocol):
        """ Test zscan """
        size = 1000
        items = { 'key-%i' % i: (i + 0.1) for i in range(size) }

        # Create a huge set
        yield from protocol.delete(['my-z'])
        yield from protocol.zadd('my-z', items)

        # Scan this set.
        cursor = yield from protocol.zscan('my-z')

        received = {}
        while True:
            i = yield from cursor.fetchone()
            if not i: break

            self.assertIsInstance(i, dict)
            received.update(i)

        # Check result
        self.assertEqual(len(received), size)
        self.assertEqual(received, items)

        # Test fetchall
        cursor = yield from protocol.zscan('my-z')
        received2 = yield from cursor.fetchall()
        self.assertIsInstance(received2, dict)
        self.assertEqual(received, received2)

    @redis_test
    def test_alternate_gets(self, transport, protocol):
        """
        Test _asdict/_asset/_aslist suffixes.
        """
        # Prepare
        yield from protocol.set(u'my_key', u'a')
        yield from protocol.set(u'my_key2', u'b')

        yield from protocol.delete([ u'my_set' ])
        yield from protocol.sadd(u'my_set', [u'value1'])
        yield from protocol.sadd(u'my_set', [u'value2'])

        yield from protocol.delete([ u'my_hash' ])
        yield from protocol.hmset(u'my_hash', {'a':'1', 'b':'2', 'c':'3'})

        # Test mget_aslist
        result = yield from protocol.mget_aslist(['my_key', 'my_key2'])
        self.assertEqual(result, [u'a', u'b'])
        self.assertIsInstance(result, list)

        # Test keys_aslist
        result = yield from protocol.keys_aslist('some-prefix-')
        self.assertIsInstance(result, list)

        # Test smembers
        result = yield from protocol.smembers_asset(u'my_set')
        self.assertEqual(result, { u'value1', u'value2' })
        self.assertIsInstance(result, set)

        # Test hgetall_asdict
        result = yield from protocol.hgetall_asdict('my_hash')
        self.assertEqual(result, {'a':'1', 'b':'2', 'c':'3'})
        self.assertIsInstance(result, dict)

        # test all inside a transaction.
        transaction = yield from protocol.multi()
        f1 = yield from transaction.mget_aslist(['my_key', 'my_key2'])
        f2 = yield from transaction.smembers_asset(u'my_set')
        f3 = yield from transaction.hgetall_asdict('my_hash')
        yield from transaction.exec()

        result1 = yield from f1
        result2 = yield from f2
        result3 = yield from f3

        self.assertEqual(result1, [u'a', u'b'])
        self.assertIsInstance(result1, list)

        self.assertEqual(result2, { u'value1', u'value2' })
        self.assertIsInstance(result2, set)

        self.assertEqual(result3, {'a':'1', 'b':'2', 'c':'3'})
        self.assertIsInstance(result3, dict)

    @redis_test
    def test_cancellation(self, transport, protocol):
        """ Test CancelledError: when a query gets cancelled. """
        yield from protocol.delete(['key'])

        # Start a coroutine that runs a blocking command for 3seconds
        @asyncio.coroutine
        def run():
            yield from protocol.brpop(['key'], 3)
        f = asyncio.async(run(), loop=self.loop)

        # We cancel the coroutine before the answer arrives.
        yield from asyncio.sleep(.5, loop=self.loop)
        f.cancel()

        # Now there's a cancelled future in protocol._queue, the
        # protocol._push_answer function should notice that and ignore the
        # incoming result from our `brpop` in this case.
        yield from protocol.set('key', 'value')


class RedisBytesProtocolTest(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.protocol_class = lambda **kw: RedisProtocol(encoder=BytesEncoder(), **kw)

    @redis_test
    def test_bytes_protocol(self, transport, protocol):
        # When passing string instead of bytes, this protocol should raise an exception.
        with self.assertRaises(TypeError):
            result = yield from protocol.set('key', 'value')

        # Setting bytes
        result = yield from protocol.set(b'key', b'value')
        self.assertEqual(result, StatusReply('OK'))

        # Getting bytes
        result = yield from protocol.get(b'key')
        self.assertEqual(result, b'value')


class NoTypeCheckingTest(unittest.TestCase):
    def test_protocol(self):
        # Override protocol, disabling type checking.
        def factory(**kw):
            return RedisProtocol(encoder=BytesEncoder(), enable_typechecking=False, **kw)

        loop = asyncio.get_event_loop()

        @asyncio.coroutine
        def test():
            transport, protocol = yield from connect(loop, protocol=factory)

            # Setting values should still work.
            result = yield from protocol.set(b'key', b'value')
            self.assertEqual(result, StatusReply('OK'))

            transport.close()

        loop.run_until_complete(test())


class RedisConnectionTest(unittest.TestCase):
    """ Test connection class. """
    def setUp(self):
        self.loop = asyncio.get_event_loop()

    def test_connection(self):
        @asyncio.coroutine
        def test():
            # Create connection
            connection = yield from Connection.create(host=HOST, port=PORT)
            self.assertEqual(repr(connection), "Connection(host=%r, port=%r)" % (HOST, PORT))

            # Test get/set
            yield from connection.set('key', 'value')
            result = yield from connection.get('key')
            self.assertEqual(result, 'value')

        self.loop.run_until_complete(test())


class RedisPoolTest(unittest.TestCase):
    """ Test connection pooling. """
    def setUp(self):
        self.loop = asyncio.get_event_loop()

    def test_pool(self):
        """ Test creation of Connection instance. """
        @asyncio.coroutine
        def test():
            # Create pool
            connection = yield from Pool.create(host=HOST, port=PORT)
            self.assertEqual(repr(connection), "Pool(host=%r, port=%r, poolsize=1)" % (HOST, PORT))

            # Test get/set
            yield from connection.set('key', 'value')
            result = yield from connection.get('key')
            self.assertEqual(result, 'value')

            # Test default poolsize
            self.assertEqual(connection.poolsize, 1)

        self.loop.run_until_complete(test())

    def test_connection_in_use(self):
        """
        When a blocking call is running, it's impossible to use the same
        protocol for another call.
        """
        @asyncio.coroutine
        def test():
            # Create connection
            connection = yield from Pool.create(host=HOST, port=PORT)
            self.assertEqual(connection.connections_in_use, 0)

            # Wait for ever. (This blocking pop doesn't return.)
            yield from connection.delete([ 'unknown-key' ])
            asyncio.async(connection.blpop(['unknown-key']), loop=self.loop)
            yield from asyncio.sleep(.1, loop=self.loop) # Sleep to make sure that the above coroutine started executing.

            # Run command in other thread.
            with self.assertRaises(NoAvailableConnectionsInPoolError) as e:
                yield from connection.set('key', 'value')
            self.assertIn('No available connections in the pool', e.exception.args[0])

            self.assertEqual(connection.connections_in_use, 1)

        self.loop.run_until_complete(test())

    def test_parallel_requests(self):
        """
        Test a blocking pop and a set using a connection pool.
        """
        @asyncio.coroutine
        def test():
            # Create connection
            connection = yield from Pool.create(host=HOST, port=PORT, poolsize=2)
            yield from connection.delete([ 'my-list' ])

            results = []

            # Sink: receive items using blocking pop
            @asyncio.coroutine
            def sink():
                for i in range(0, 5):
                    reply = yield from connection.blpop(['my-list'])
                    self.assertIsInstance(reply, BlockingPopReply)
                    self.assertIsInstance(reply.value, str)
                    results.append(reply.value)
                    self.assertIn(u"BlockingPopReply(list_name='my-list', value='", repr(reply))

            # Source: Push items on the queue
            @asyncio.coroutine
            def source():
                for i in range(0, 5):
                    yield from connection.rpush('my-list', [str(i)])
                    yield from asyncio.sleep(.5, loop=self.loop)

            # Run both coroutines.
            f1 = asyncio.async(source(), loop=self.loop)
            f2 = asyncio.async(sink(), loop=self.loop)
            yield from gather(f1, f2)

            # Test results.
            self.assertEqual(results, [ str(i) for i in range(0, 5) ])

        self.loop.run_until_complete(test())

    def test_select_db(self):
        """
        Connect to two different DBs.
        """
        @asyncio.coroutine
        def test():
            c1 = yield from Pool.create(host=HOST, port=PORT, poolsize=10, db=1)
            c2 = yield from Pool.create(host=HOST, port=PORT, poolsize=10, db=2)

            c3 = yield from Pool.create(host=HOST, port=PORT, poolsize=10, db=1)
            c4 = yield from Pool.create(host=HOST, port=PORT, poolsize=10, db=2)

            yield from c1.set('key', 'A')
            yield from c2.set('key', 'B')

            r1 = yield from c3.get('key')
            r2 = yield from c4.get('key')

            self.assertEqual(r1, 'A')
            self.assertEqual(r2, 'B')

        self.loop.run_until_complete(test())

    def test_in_use_flag(self):
        """
        Do several blocking calls and see whether in_use increments.
        """
        @asyncio.coroutine
        def test():
            # Create connection
            connection = yield from Pool.create(host=HOST, port=PORT, poolsize=10)
            for i in range(0, 10):
                yield from connection.delete([ 'my-list-%i' % i ])

            @asyncio.coroutine
            def sink(i):
                the_list, result = yield from connection.blpop(['my-list-%i' % i])

            for i in range(0, 10):
                self.assertEqual(connection.connections_in_use, i)
                asyncio.async(sink(i), loop=self.loop)
                yield from asyncio.sleep(.1, loop=self.loop) # Sleep to make sure that the above coroutine started executing.

            # One more blocking call should fail.
            with self.assertRaises(NoAvailableConnectionsInPoolError) as e:
                yield from connection.delete([ 'my-list-one-more' ])
                yield from connection.blpop(['my-list-one-more'])
            self.assertIn('No available connections in the pool', e.exception.args[0])

        self.loop.run_until_complete(test())

    def test_lua_script_in_pool(self):
        @asyncio.coroutine
        def test():
            # Create connection
            connection = yield from Pool.create(host=HOST, port=PORT, poolsize=3)

            # Register script
            script = yield from connection.register_script("return 100")
            self.assertIsInstance(script, Script)

            # Run script
            scriptreply = yield from script.run()
            result = yield from scriptreply.return_value()
            self.assertEqual(result, 100)

        self.loop.run_until_complete(test())

    def test_transactions(self):
        """
        Do several transactions in parallel.
        """
        @asyncio.coroutine
        def test():
            # Create connection
            connection = yield from Pool.create(host=HOST, port=PORT, poolsize=3)

            t1 = yield from connection.multi()
            t2 = yield from connection.multi()
            yield from connection.multi()

            # Fourth transaction should fail. (Pool is full)
            with self.assertRaises(NoAvailableConnectionsInPoolError) as e:
                yield from connection.multi()
            self.assertIn('No available connections in the pool', e.exception.args[0])

            # Run commands in transaction
            yield from t1.set(u'key', u'value')
            yield from t2.set(u'key2', u'value2')

            # Commit.
            yield from t1.exec()
            yield from t2.exec()

            # Check
            result1 = yield from connection.get(u'key')
            result2 = yield from connection.get(u'key2')

            self.assertEqual(result1, u'value')
            self.assertEqual(result2, u'value2')

        self.loop.run_until_complete(test())

    def test_watch(self):
        """
        Test a transaction, using watch
        """
        # Test using the watched key inside the transaction.
        @asyncio.coroutine
        def test():
            # Setup
            connection = yield from Pool.create(host=HOST, port=PORT, poolsize=3)
            yield from connection.set(u'key', u'0')
            yield from connection.set(u'other_key', u'0')

            # Test
            t = yield from connection.multi(watch=['other_key'])
            yield from t.set(u'key', u'value')
            yield from t.set(u'other_key', u'my_value')
            yield from t.exec()

            # Check
            result = yield from connection.get(u'key')
            self.assertEqual(result, u'value')
            result = yield from connection.get(u'other_key')
            self.assertEqual(result, u'my_value')

        self.loop.run_until_complete(test())

        # Test using the watched key outside the transaction.
        # (the transaction should fail in this case.)
        @asyncio.coroutine
        def test():
            # Setup
            connection = yield from Pool.create(host=HOST, port=PORT, poolsize=3)
            yield from connection.set(u'key', u'0')
            yield from connection.set(u'other_key', u'0')

            # Test
            t = yield from connection.multi(watch=['other_key'])
            yield from connection.set('other_key', 'other_value')
            yield from t.set(u'other_key', u'value')

            with self.assertRaises(TransactionError):
                yield from t.exec()

            # Check
            result = yield from connection.get(u'other_key')
            self.assertEqual(result, u'other_value')

        self.loop.run_until_complete(test())

    def test_connection_reconnect(self):
        """
        Test whether the connection reconnects.
        (needs manual interaction.)
        """
        @asyncio.coroutine
        def test():
            connection = yield from Pool.create(host=HOST, port=PORT, poolsize=1)
            yield from connection.set('key', 'value')

            transport = connection._connections[0].transport
            transport.close()

            yield from asyncio.sleep(1, loop=self.loop) # Give asyncio time to reconnect.

            # Test get/set
            yield from connection.set('key', 'value')

        self.loop.run_until_complete(test())

    def test_connection_lost(self):
        """
        When the transport is closed, any further commands should raise
        NotConnectedError. (Unless the transport would be auto-reconnecting and
        have established a new connection.)
        """
        @asyncio.coroutine
        def test():
            # Create connection
            transport, protocol = yield from connect(self.loop, RedisProtocol)
            yield from protocol.set('key', 'value')

            # Close transport
            self.assertEqual(protocol.is_connected, True)
            transport.close()
            yield from asyncio.sleep(.5, loop=self.loop)
            self.assertEqual(protocol.is_connected, False)

            # Test get/set
            with self.assertRaises(NotConnectedError):
                yield from protocol.set('key', 'value')

            transport.close()

        self.loop.run_until_complete(test())

        # Test connection lost in connection pool.
        @asyncio.coroutine
        def test():
            # Create connection
            connection = yield from Pool.create(host=HOST, port=PORT, poolsize=1, auto_reconnect=False)
            yield from connection.set('key', 'value')

            # Close transport
            transport = connection._connections[0].transport
            transport.close()
            yield from asyncio.sleep(.5, loop=self.loop)

            # Test get/set
            with self.assertRaises(NoAvailableConnectionsInPoolError) as e:
                yield from connection.set('key', 'value')
            self.assertIn('No available connections in the pool: size=1, in_use=0, connected=0', e.exception.args[0])

        self.loop.run_until_complete(test())


class NoGlobalLoopTest(unittest.TestCase):
    """
    If we set the global loop variable to None, everything should still work.
    """
    def test_no_global_loop(self):
        old_loop = asyncio.get_event_loop()
        try:
            # Remove global loop and create a new one.
            asyncio.set_event_loop(None)
            new_loop = asyncio.new_event_loop()

            # ** Run code on the new loop. **

            # Create connection
            connection = new_loop.run_until_complete(Connection.create(host=HOST, port=PORT, loop=new_loop))
            self.assertIsInstance(connection, Connection)

            # Delete keys
            new_loop.run_until_complete(connection.delete(['key1', 'key2']))

            # Get/set
            new_loop.run_until_complete(connection.set('key1', 'value'))
            result = new_loop.run_until_complete(connection.get('key1'))

            # hmset/hmget (something that uses a MultiBulkReply)
            new_loop.run_until_complete(connection.hmset('key2', { 'a': 'b', 'c': 'd' }))
            result = new_loop.run_until_complete(connection.hgetall_asdict('key2'))
            self.assertEqual(result, { 'a': 'b', 'c': 'd' })
        finally:
            asyncio.set_event_loop(old_loop)


class RedisProtocolWithoutGlobalEventloopTest(RedisProtocolTest):
    """ Run all the tests from `RedisProtocolTest` again without a global event loop. """
    def setUp(self):
        super().setUp()

        # Remove global loop and create a new one.
        self._old_loop = asyncio.get_event_loop()
        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(self._old_loop)


class RedisBytesWithoutGlobalEventloopProtocolTest(RedisBytesProtocolTest):
    """ Run all the tests from `RedisBytesProtocolTest`` again without a global event loop. """
    def setUp(self):
        super().setUp()

        # Remove global loop and create a new one.
        self._old_loop = asyncio.get_event_loop()
        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(self._old_loop)


def _start_redis_server(loop):
    print('Running Redis server REDIS_HOST=%r REDIS_PORT=%r...' % (HOST, PORT))

    redis_srv = loop.run_until_complete(
                asyncio.create_subprocess_exec(
                    'redis-server',
                    '--port', str(PORT),
                    ('--bind' if PORT else '--unixsocket'), HOST,
                    '--maxclients', '100',
                    '--save', '""',
                    '--loglevel', 'warning',
                    loop=loop,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL))
    loop.run_until_complete(asyncio.sleep(.05, loop=loop))
    return redis_srv


if __name__ == '__main__':
    if START_REDIS_SERVER:
        redis_srv = _start_redis_server(asyncio.get_event_loop())

    try:
        unittest.main()
    finally:
        if START_REDIS_SERVER:
            redis_srv.terminate()


########NEW FILE########
