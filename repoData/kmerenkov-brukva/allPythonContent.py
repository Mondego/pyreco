__FILENAME__ = adisp
# -*- coding:utf-8 -*-
'''
Adisp is a library that allows structuring code with asynchronous calls and
callbacks without defining callbacks as separate functions. The code then
becomes sequential and easy to read. The library is not a framework by itself
and can be used in other environments that provides asynchronous working model
(see an example with Tornado server in proxy_example.py).

Usage:

## Organizing calling code

All the magic is done with Python 2.5 decorators that allow for control flow to
leave a function, do sometihing else for some time and then return into the
calling function with a result. So the function that makes asynchronous calls
should look like this:

    @process
    def my_handler():
        response = yield some_async_func()
        data = parse_response(response)
        result = yield some_other_async_func(data)
        store_result(result)

Each `yield` is where the function returns and lets the framework around it to
do its job. And the code after `yield` is what usually goes in a callback.

The @process decorator is needed around such a function. It makes it callable
as an ordinary function and takes care of dispatching callback calls back into
it.

## Writing asynchronous function

In the example above functions "some_async_func" and "some_other_async_func"
are those that actually run an asynchronous process. They should follow two
conditions:

- accept a "callback" parameter with a callback function that they should call
  after an asynchronous process is finished
- a callback should be called with one parameter -- the result
- be wrapped in the @async decorator

The @async decorator makes a function call lazy allowing the @process that
calls it to provide a callback to call.

Using async with @-syntax is most convenient when you write your own
asynchronous function (and can make your callback parameter to be named
"callback"). But when you want to call some library function you can wrap it in
async in place.

    # call http.fetch(url, callback=callback)
    result = yield async(http.fetch)

    # call http.fetch(url, cb=safewrap(callback))
    result = yield async(http.fetch, cbname='cb', cbwrapper=safewrap)(url)

Here you can use two optional parameters for async:

- `cbname`: a name of a parameter in which the function expects callbacks
- `cbwrapper`: a wrapper for the callback iself that will be applied before
  calling it

## Chain calls

@async function can also be @process'es allowing to effectively chain
asynchronous calls as it can be done with normal functions. In this case the
@async decorator shuold be the outer one:

    @async
    @process
    def async_calling_other_asyncs(arg, callback):
        # ....

## Multiple asynchronous calls

The library also allows to call multiple asynchronous functions in parallel and
get all their result for processing at once:

    @async
    def async_http_get(url, callback):
        # get url asynchronously
        # call callback(response) at the end

    @process
    def get_stat():
        urls = ['http://.../', 'http://.../', ... ]
        responses = yield map(async_http_get, urls)

After *all* the asynchronous calls will complete `responses` will be a list of
responses corresponding to given urls.
'''
from functools import partial

class CallbackDispatcher(object):
    def __init__(self, generator):
        self.g = generator
        try:
            self.call(self.g.next())
        except StopIteration:
            pass

    def _send_result(self, results, single):
        try:
            result = results[0] if single else results
            self.call(self.g.send(result))
        except StopIteration:
            pass

    def call(self, callers):
        single = not hasattr(callers, '__iter__')
        if single:
            callers = [callers]
        self.call_count = len(list(callers))
        results = [None] * self.call_count
        if self.call_count == 0:
            self._send_result(results, single)
        else:
            for count, caller in enumerate(callers):
                caller(callback=partial(self.callback, results, count, single))

    def callback(self, results, index, single, arg):
        self.call_count -= 1
        results[index] = arg
        if self.call_count > 0:
            return
        self._send_result(results, single)

def process(func):
    def wrapper(*args, **kwargs):
        CallbackDispatcher(func(*args, **kwargs))
    return wrapper

def async(func, cbname='callback', cbwrapper=lambda x: x):
    def wrapper(*args, **kwargs):
        def caller(callback):
            kwargs[cbname] = cbwrapper(callback)
            return func(*args, **kwargs)
        return caller
    return wrapper

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-
import socket
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from adisp import async, process

from functools import partial
from itertools import izip
from datetime import datetime
from brukva.exceptions import RedisError, ConnectionError, ResponseError, InvalidResponse

class Message(object):
    def __init__(self, kind, channel, body):
        self.kind = kind
        self.channel = channel
        self.body = body

class CmdLine(object):
    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return self.cmd + '(' + str(self.args)  + ',' + str(self.kwargs) + ')'

def string_keys_to_dict(key_string, callback):
    return dict([(key, callback) for key in key_string.split()])

def dict_merge(*dicts):
    merged = {}
    [merged.update(d) for d in dicts]
    return merged

def encode(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, unicode):
        return value.encode('utf-8')
    # pray and hope
    return str(value)

def format(*tokens):
    cmds = []
    for t in tokens:
        e_t = encode(t)
        cmds.append('$%s\r\n%s\r\n' % (len(e_t), e_t))
    return '*%s\r\n%s' % (len(tokens), ''.join(cmds))

def format_pipeline_request(command_stack):
    return ''.join(format(c.cmd, *c.args, **c.kwargs) for c in command_stack)

class Connection(object):
    def __init__(self, host, port, timeout=None, io_loop=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._stream = None
        self._io_loop = io_loop

        self.in_progress = False
        self.read_queue = []

    def connect(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            self._stream = IOStream(sock, io_loop=self._io_loop)
        except socket.error, e:
            raise ConnectionError(str(e))

    def disconnect(self):
        try:
            self._stream.close()
        except socket.error, e:
            pass
        self._stream = None

    def write(self, data):
        self._stream.write(data)

    def consume(self, length):
        self._stream.read_bytes(length, NOOP_CB)

    def read(self, length, callback):
        self._stream.read_bytes(length, callback)

    def readline(self, callback):
        self._stream.read_until('\r\n', callback)

    def try_to_perform_read(self):
        if not self.in_progress and self.read_queue:
            self.in_progress = True
            self._io_loop.add_callback(partial(self.read_queue.pop(0), None) )

    @async
    def queue_wait(self, callback):
        self.read_queue.append(callback)
        self.try_to_perform_read()

    def read_done(self):
        self.in_progress = False
        self.try_to_perform_read()

def reply_to_bool(r, *args, **kwargs):
    return bool(r)

def make_reply_assert_msg(msg):
    def reply_assert_msg(r, *args, **kwargs):
        return r == msg
    return reply_assert_msg

def reply_set(r, *args, **kwargs):
    return set(r)

def reply_dict_from_pairs(r, *args, **kwargs):
    return dict(izip(r[::2], r[1::2]))

def reply_str(r, *args, **kwargs):
    return r or ''

def reply_int(r, *args, **kwargs):
    return int(r) if r is not None else None

def reply_float(r, *args, **kwargs):
    return float(r) if r is not None else None

def reply_datetime(r, *args, **kwargs):
    return datetime.fromtimestamp(int(r))

def reply_pubsub_message(r, *args, **kwargs):
    return Message(*r)

def reply_zset(r, *args, **kwargs):
    if (not r ) or (not 'WITHSCORES' in args):
        return r
    return zip(r[::2], map(float, r[1::2]))

def reply_info(response):
    info = {}
    def get_value(value):
        if ',' not in value:
            return value
        sub_dict = {}
        for item in value.split(','):
            k, v = item.split('=')
            try:
                sub_dict[k] = int(v)
            except ValueError:
                sub_dict[k] = v
        return sub_dict
    for line in response.splitlines():
        key, value = line.split(':')
        try:
            info[key] = int(value)
        except ValueError:
            info[key] = get_value(value)
    return info

def reply_ttl(r, *args, **kwargs):
    return r != -1 and r or None

class Client(object):
    def __init__(self, host='localhost', port=6379, io_loop=None):
        self._io_loop = io_loop or IOLoop.instance()

        self.connection = Connection(host, port, io_loop=self._io_loop)
        self.queue = []
        self.current_cmd_line = None
        self.subscribed = False
        self.REPLY_MAP = dict_merge(
                string_keys_to_dict('AUTH BGREWRITEAOF BGSAVE DEL EXISTS EXPIRE HDEL HEXISTS '
                                    'HMSET MOVE MSET MSETNX SAVE SETNX',
                                    reply_to_bool),
                string_keys_to_dict('FLUSHALL FLUSHDB SELECT SET SETEX SHUTDOWN '
                                    'RENAME RENAMENX WATCH UNWATCH',
                                    make_reply_assert_msg('OK')),
                string_keys_to_dict('SMEMBERS SINTER SUNION SDIFF',
                                    reply_set),
                string_keys_to_dict('HGETALL',
                                    reply_dict_from_pairs),
                string_keys_to_dict('HGET',
                                    reply_str),
                string_keys_to_dict('SUBSCRIBE UNSUBSCRIBE LISTEN',
                                    reply_pubsub_message),
                string_keys_to_dict('ZRANK ZREVRANK',
                                    reply_int),
                string_keys_to_dict('ZSCORE ZINCRBY',
                                    reply_int),
                string_keys_to_dict('ZRANGE ZRANGEBYSCORE ZREVRANGE',
                                    reply_zset),
                {'PING': make_reply_assert_msg('PONG')},
                {'LASTSAVE': reply_datetime },
                {'TTL': reply_ttl } ,
                {'INFO': reply_info},
                {'MULTI_PART': make_reply_assert_msg('QUEUED')},
            )

        self._pipeline = None

    def __repr__(self):
        return 'Brukva client (host=%s, port=%s)' % (self.connection.host, self.connection.port)

    def pipeline(self, transactional=False):
        if not self._pipeline:
            self._pipeline =  Pipeline(io_loop = self._io_loop, transactional=transactional)
            self._pipeline.connection = self.connection
        return self._pipeline

    #### connection
    def connect(self):
        self.connection.connect()

    def disconnect(self):
        self.connection.disconnect()
    ####

    #### formatting
    def encode(self, value):
        if isinstance(value, str):
            return value
        elif isinstance(value, unicode):
            return value.encode('utf-8')
        # pray and hope
        return str(value)

    def format(self, *tokens):
        cmds = []
        for t in tokens:
            e_t = self.encode(t)
            cmds.append('$%s\r\n%s\r\n' % (len(e_t), e_t))
        return '*%s\r\n%s' % (len(tokens), ''.join(cmds))

    def format_reply(self, cmd_line, data):
        if cmd_line.cmd not in self.REPLY_MAP:
            return data
        try:
            res =  self.REPLY_MAP[cmd_line.cmd](data, *cmd_line.args, **cmd_line.kwargs)
        except Exception, e:
            res = ResponseError('failed to format reply, raw data: %s' % data, cmd_line)
        return res
    ####

    #### new AsIO
    def call_callbacks(self, callbacks, *args, **kwargs):
        for cb in callbacks:
            cb(*args, **kwargs)

    def _sudden_disconnect(self, callbacks):
        self.connection.disconnect()
        self.call_callbacks(callbacks, (ConnectionError("Socket closed on remote end"), None))

    @process
    def execute_command(self, cmd, callbacks, *args, **kwargs):
        if callbacks is None:
            callbacks = []
        elif not hasattr(callbacks, '__iter__'):
            callbacks = [callbacks]
        try:
            self.connection.write(self.format(cmd, *args, **kwargs))
        except IOError:
            self._sudden_disconnect(callbacks)
            return

        cmd_line = CmdLine(cmd, *args, **kwargs)
        yield self.connection.queue_wait()

        data = yield async(self.connection.readline)()
        if not data:
            result = None
            error = Exception('todo')
        else:
            try:
                error, response = yield self.process_data(data, cmd_line)
                result = self.format_reply(cmd_line, response)
            except Exception, e:
                error, result = e, None

        self.connection.read_done()
        self.call_callbacks(callbacks, (error, result))

    @async
    @process
    def process_data(self, data, cmd_line, callback):
        error, response = None, None

        data = data[:-2] # strip \r\n

        if data == '$-1':
            response =  None
        elif data == '*0' or data == '*-1':
            response = []
        else:
            head, tail = data[0], data[1:]

            if head == '*':
                error, response = yield self.consume_multibulk(int(tail), cmd_line)
            elif head == '$':
                error, response = yield self.consume_bulk(int(tail)+2)
            elif head == '+':
                response = tail
            elif head == ':':
                response = int(tail)
            elif head == '-':
                if tail.startswith('ERR'):
                    tail = tail[4:]
                error = ResponseError(tail, cmd_line)
            else:
                error = ResponseError('Unknown response type %s' % head, cmd_line)

        callback( (error, response) )

    @async
    @process
    def consume_multibulk(self, length, cmd_line, callback):
        tokens = []
        errors = {}
        idx = 0
        while len(tokens) < length:
            data = yield async(self.connection.readline)()
            if not data:
                break

            error, token = yield self.process_data(data, cmd_line) #FIXME error
            tokens.append( token )
            if error:
                errors[idx] = error

            idx += 1
        callback( (errors, tokens) )

    @async
    @process
    def consume_bulk(self, length, callback):
        data = yield async(self.connection.read)(length)
        error = None
        if not data:
            error = ResponseError('EmptyResponse')
        else:
            data = data[:-2]
        callback( (error, data) )
    ####

    ### MAINTENANCE
    def bgrewriteaof(self, callbacks=None):
        self.execute_command('BGREWRITEAOF', callbacks)

    def dbsize(self, callbacks=None):
        self.execute_command('DBSIZE', callbacks)

    def flushall(self, callbacks=None):
        self.execute_command('FLUSHALL', callbacks)

    def flushdb(self, callbacks=None):
        self.execute_command('FLUSHDB', callbacks)

    def ping(self, callbacks=None):
        self.execute_command('PING', callbacks)

    def info(self, callbacks=None):
        self.execute_command('INFO', callbacks)

    def select(self, db, callbacks=None):
        self.execute_command('SELECT', callbacks, db)

    def shutdown(self, callbacks=None):
        self.execute_command('SHUTDOWN', callbacks)

    def save(self, callbacks=None):
        self.execute_command('SAVE', callbacks)

    def bgsave(self, callbacks=None):
        self.execute_command('BGSAVE', callbacks)

    def lastsave(self, callbacks=None):
        self.execute_command('LASTSAVE', callbacks)

    def keys(self, pattern, callbacks=None):
        self.execute_command('KEYS', callbacks, pattern)

    def auth(self, password, callbacks=None):
        self.execute_command('AUTH', callbacks, password)

    ### BASIC KEY COMMANDS
    def append(self, key, value, callbacks=None):
        self.execute_command('APPEND', callbacks, key, value)

    def expire(self, key, ttl, callbacks=None):
        self.execute_command('EXPIRE', callbacks, key, ttl)

    def ttl(self, key, callbacks=None):
        self.execute_command('TTL', callbacks, key)

    def type(self, key, callbacks=None):
        self.execute_command('TYPE', callbacks, key)

    def randomkey(self, callbacks=None):
        self.execute_command('RANDOMKEY', callbacks)

    def rename(self, src, dst, callbacks=None):
        self.execute_command('RENAME', callbacks, src, dst)

    def renamenx(self, src, dst, callbacks=None):
        self.execute_command('RENAMENX', callbacks, src, dst)

    def move(self, key, db, callbacks=None):
        self.execute_command('MOVE', callbacks, key, db)

    def substr(self, key, start, end, callbacks=None):
        self.execute_command('SUBSTR', callbacks, key, start, end)

    def delete(self, key, callbacks=None):
        self.execute_command('DEL', callbacks, key)

    def set(self, key, value, callbacks=None):
        self.execute_command('SET', callbacks, key, value)

    def setex(self, key, ttl, value, callbacks=None):
        self.execute_command('SETEX', callbacks, key, ttl, value)

    def setnx(self, key, value, callbacks=None):
        self.execute_command('SETNX', callbacks, key, value)

    def mset(self, mapping, callbacks=None):
        items = []
        [ items.extend(pair) for pair in mapping.iteritems() ]
        self.execute_command('MSET', callbacks, *items)

    def msetnx(self, mapping, callbacks=None):
        items = []
        [ items.extend(pair) for pair in mapping.iteritems() ]
        self.execute_command('MSETNX', callbacks, *items)

    def get(self, key, callbacks=None):
        self.execute_command('GET', callbacks, key)

    def mget(self, keys, callbacks=None):
        self.execute_command('MGET', callbacks, *keys)

    def getset(self, key, value, callbacks=None):
        self.execute_command('GETSET', callbacks, key, value)

    def exists(self, key, callbacks=None):
        self.execute_command('EXISTS', callbacks, key)

    def sort(self, key, start=None, num=None, by=None, get=None, desc=False, alpha=False, store=None, callbacks=None):
        if (start is not None and num is None) or (num is not None and start is None):
            raise ValueError("``start`` and ``num`` must both be specified")

        tokens = [key]
        if by is not None:
            tokens.append('BY')
            tokens.append(by)
        if start is not None and num is not None:
            tokens.append('LIMIT')
            tokens.append(start)
            tokens.append(num)
        if get is not None:
            tokens.append('GET')
            tokens.append(get)
        if desc:
            tokens.append('DESC')
        if alpha:
            tokens.append('ALPHA')
        if store is not None:
            tokens.append('STORE')
            tokens.append(store)
        return self.execute_command('SORT', callbacks, *tokens)

    ### COUNTERS COMMANDS
    def incr(self, key, callbacks=None):
        self.execute_command('INCR', callbacks, key)

    def decr(self, key, callbacks=None):
        self.execute_command('DECR', callbacks, key)

    def incrby(self, key, amount, callbacks=None):
        self.execute_command('INCRBY', callbacks, key, amount)

    def decrby(self, key, amount, callbacks=None):
        self.execute_command('DECRBY', callbacks, key, amount)

    ### LIST COMMANDS
    def blpop(self, keys, timeout=0, callbacks=None):
        tokens = list(keys)
        tokens.append(timeout)
        self.execute_command('BLPOP', callbacks, *tokens)

    def brpop(self, keys, timeout=0, callbacks=None):
        tokens = list(keys)
        tokens.append(timeout)
        self.execute_command('BRPOP', callbacks, *tokens)

    def lindex(self, key, index, callbacks=None):
        self.execute_command('LINDEX', callbacks, key, index)

    def llen(self, key, callbacks=None):
        self.execute_command('LLEN', callbacks, key)

    def lrange(self, key, start, end, callbacks=None):
        self.execute_command('LRANGE', callbacks, key, start, end)

    def lrem(self, key, value, num=0, callbacks=None):
        self.execute_command('LREM', callbacks, key, num, value)

    def lset(self, key, index, value, callbacks=None):
        self.execute_command('LSET', callbacks, key, index, value)

    def ltrim(self, key, start, end, callbacks=None):
        self.execute_command('LTRIM', callbacks, key, start, end)

    def lpush(self, key, value, callbacks=None):
        self.execute_command('LPUSH', callbacks, key, value)

    def rpush(self, key, value, callbacks=None):
        self.execute_command('RPUSH', callbacks, key, value)

    def lpop(self, key, callbacks=None):
        self.execute_command('LPOP', callbacks, key)

    def rpop(self, key, callbacks=None):
        self.execute_command('RPOP', callbacks, key)

    def rpoplpush(self, src, dst, callbacks=None):
        self.execute_command('RPOPLPUSH', callbacks, src, dst)

    ### SET COMMANDS
    def sadd(self, key, value, callbacks=None):
        self.execute_command('SADD', callbacks, key, value)

    def srem(self, key, value, callbacks=None):
        self.execute_command('SREM', callbacks, key, value)

    def scard(self, key, callbacks=None):
        self.execute_command('SCARD', callbacks, key)

    def spop(self, key, callbacks=None):
        self.execute_command('SPOP', callbacks, key)

    def smove(self, src, dst, value, callbacks=None):
        self.execute_command('SMOVE', callbacks, src, dst, value)

    def sismember(self, key, value, callbacks=None):
        self.execute_command('SISMEMBER', callbacks, key, value)

    def smembers(self, key, callbacks=None):
        self.execute_command('SMEMBERS', callbacks, key)

    def srandmember(self, key, callbacks=None):
        self.execute_command('SRANDMEMBER', callbacks, key)

    def sinter(self, keys, callbacks=None):
        self.execute_command('SINTER', callbacks, *keys)

    def sdiff(self, keys, callbacks=None):
        self.execute_command('SDIFF', callbacks, *keys)

    def sunion(self, keys, callbacks=None):
        self.execute_command('SUNION', callbacks, *keys)

    def sinterstore(self, keys, dst, callbacks=None):
        self.execute_command('SINTERSTORE', callbacks, dst, *keys)

    def sunionstore(self, keys, dst, callbacks=None):
        self.execute_command('SUNIONSTORE', callbacks, dst, *keys)

    def sdiffstore(self, keys, dst, callbacks=None):
        self.execute_command('SDIFFSTORE', callbacks, dst, *keys)

    ### SORTED SET COMMANDS
    def zadd(self, key, score, value, callbacks=None):
        self.execute_command('ZADD', callbacks, key, score, value)

    def zcard(self, key, callbacks=None):
        self.execute_command('ZCARD', callbacks, key)

    def zincrby(self, key, value, amount, callbacks=None):
        self.execute_command('ZINCRBY', callbacks, key, amount, value)

    def zrank(self, key, value, callbacks=None):
        self.execute_command('ZRANK', callbacks, key, value)

    def zrevrank(self, key, value, callbacks=None):
        self.execute_command('ZREVRANK', callbacks, key, value)

    def zrem(self, key, value, callbacks=None):
        self.execute_command('ZREM', callbacks, key, value)

    def zscore(self, key, value, callbacks=None):
        self.execute_command('ZSCORE', callbacks, key, value)

    def zrange(self, key, start, num, with_scores, callbacks=None):
        tokens = [key, start, num]
        if with_scores:
            tokens.append('WITHSCORES')
        self.execute_command('ZRANGE', callbacks, *tokens)

    def zrevrange(self, key, start, num, with_scores, callbacks=None):
        tokens = [key, start, num]
        if with_scores:
            tokens.append('WITHSCORES')
        self.execute_command('ZREVRANGE', callbacks, *tokens)

    def zrangebyscore(self, key, start, end, offset=None, limit=None, with_scores=False, callbacks=None):
        tokens = [key, start, end]
        if offset is not None:
            tokens.append('LIMIT')
            tokens.append(offset)
            tokens.append(limit)
        if with_scores:
            tokens.append('WITHSCORES')
        self.execute_command('ZRANGEBYSCORE', callbacks, *tokens)

    def zremrangebyrank(self, key, start, end, callbacks=None):
        self.execute_command('ZREMRANGEBYRANK', callbacks, key, start, end)

    def zremrangebyscore(self, key, start, end, callbacks=None):
        self.execute_command('ZREMRANGEBYSCORE', callbacks, key, start, end)

    def zinterstore(self, dest, keys, aggregate=None, callbacks=None):
        return self._zaggregate('ZINTERSTORE', dest, keys, aggregate, callbacks)

    def zunionstore(self, dest, keys, aggregate=None, callbacks=None):
        return self._zaggregate('ZUNIONSTORE', dest, keys, aggregate, callbacks)

    def _zaggregate(self, command, dest, keys, aggregate, callbacks):
        tokens = [dest, len(keys)]
        if isinstance(keys, dict):
            items = keys.items()
            keys = [i[0] for i in items]
            weights = [i[1] for i in items]
        else:
            weights = None
        tokens.extend(keys)
        if weights:
            tokens.append('WEIGHTS')
            tokens.extend(weights)
        if aggregate:
            tokens.append('AGGREGATE')
            tokens.append(aggregate)
        return self.execute_command(command, callbacks, *tokens)

    ### HASH COMMANDS
    def hgetall(self, key, callbacks=None):
        self.execute_command('HGETALL', callbacks, key)

    def hmset(self, key, mapping, callbacks=None):
        items = []
        [ items.extend(pair) for pair in mapping.iteritems() ]
        self.execute_command('HMSET', callbacks, key, *items)

    def hset(self, key, field, value, callbacks=None):
        self.execute_command('HSET', callbacks, key, field, value)

    def hget(self, key, field, callbacks=None):
        self.execute_command('HGET', callbacks, key, field)

    def hdel(self, key, field, callbacks=None):
        self.execute_command('HDEL', callbacks, key, field)

    def hlen(self, key, callbacks=None):
        self.execute_command('HLEN', callbacks, key)

    def hexists(self, key, field, callbacks=None):
        self.execute_command('HEXISTS', callbacks, key, field)

    def hincrby(self, key, field, amount=1, callbacks=None):
        self.execute_command('HINCRBY', callbacks, key, field, amount)

    def hkeys(self, key, callbacks=None):
        self.execute_command('HKEYS', callbacks, key)

    def hmget(self, key, fields, callbacks=None):
        self.execute_command('HMGET', callbacks, key, *fields)

    def hvals(self, key, callbacks=None):
        self.execute_command('HVALS', callbacks, key)

    ### PUBSUB
    def subscribe(self, channels, callbacks=None):
        callbacks = callbacks or []
        if isinstance(channels, basestring):
            channels = [channels]
        callbacks = list(callbacks) + [self.on_subscribed]
        self.execute_command('SUBSCRIBE', callbacks, *channels)

    def on_subscribed(self, result):
        (e, _) = result
        if not e:
            self.subscribed = True

    def unsubscribe(self, channels, callbacks=None):
        callbacks = callbacks or []
        if isinstance(channels, basestring):
            channels = [channels]
        callbacks = list(callbacks) + [self.on_unsubscribed]
        self.execute_command('UNSUBSCRIBE', callbacks, *channels)

    def on_unsubscribed(self, result):
        (e, _) = result
        if not e:
            self.subscribed = False

    def publish(self, channel, message, callbacks=None):
        self.execute_command('PUBLISH', callbacks, channel, message)

    @process
    def listen(self, callbacks=None):
        # 'LISTEN' is just for exception information, it is not actually sent anywhere
        callbacks = callbacks or []
        if not hasattr(callbacks, '__iter__'):
            callbacks = [callbacks]

        yield self.connection.queue_wait()
        cmd_listen = CmdLine('LISTEN')
        while self.subscribed:
            data = yield async(self.connection.readline)()
            try:
                error, response = yield self.process_data(data, cmd_listen)
                result = self.format_reply(cmd_listen, response)
            except Exception, e:
                error, result = e, None

            self.call_callbacks(callbacks, (error, result) )

    ### CAS
    def watch(self, key, callbacks=None):
        self.execute_command('WATCH', callbacks, key)

    def unwatch(self, callbacks=None):
        self.execute_command('UNWATCH', callbacks)

class Pipeline(Client):
    def __init__(self, transactional, *args, **kwargs):
        super(Pipeline, self).__init__(*args, **kwargs)
        self.transactional = transactional
        self.command_stack = []

    def execute_command(self, cmd, callbacks, *args, **kwargs):
        if cmd in ('AUTH'):
            raise Exception('403')
        self.command_stack.append(CmdLine(cmd, *args, **kwargs))

    def discard(self): # actually do nothing with redis-server, just flush command_stack
        self.command_stack = []

    @process
    def execute(self, callbacks):
        command_stack = self.command_stack
        self.command_stack = []

        if callbacks is None:
            callbacks = []
        elif not hasattr(callbacks, '__iter__'):
            callbacks = [callbacks]

        if self.transactional:
            command_stack = [CmdLine('MULTI')] + command_stack + [CmdLine('EXEC')]

        request =  format_pipeline_request(command_stack)
        try:
            self.connection.write(request)
        except IOError:
            self.command_stack = []
            self._sudden_disconnect(callbacks)
            return

        yield self.connection.queue_wait()
        responses = []
        total = len(command_stack)
        cmds = iter(command_stack)
        while len(responses) < total:
            data = yield async(self.connection.readline)()
            if not data:
                break
            try:
                cmd_line = cmds.next()
                if self.transactional and cmd_line.cmd != 'EXEC':
                    error, response = yield self.process_data(data, CmdLine('MULTI_PART'))
                else:
                    error, response = yield self.process_data(data, cmd_line)
            except Exception, e:
                error, response  = e, None

            responses.append((error, response ) )
        self.connection.read_done()

        def format_replies(cmd_lines, responses):
            result = []

            for cmd_line, (error, response) in zip(cmd_lines, responses):
                if not error:
                    result.append((None,  self.format_reply(cmd_line, response)))
                else:
                    result.append((error, response))
            return result

        if self.transactional:
            command_stack = command_stack[:-1]
            errors, tr_responses = responses[-1] # actual data only from EXEC command
            responses = [
                (errors.get(idx, None), tr_responses[idx])
                for idx in xrange(len(tr_responses))
            ]

            result = format_replies(command_stack[1:], responses)

        else:
            result = format_replies(command_stack, responses)

        self.call_callbacks(callbacks, result)



########NEW FILE########
__FILENAME__ = exceptions
class RedisError(Exception):
    pass


class ConnectionError(RedisError):
    pass


class ResponseError(RedisError):
    def __init__(self, message, cmd_line):
        self.message = message
        self.cmd_line = cmd_line

    def __repr__(self):
        return 'ResponseError (on %s [%s, %s]): %s' % (self.cmd_line.cmd, self.cmd_line.args, self.cmd_line.kwargs, self.message)

    __str__ = __repr__


class InvalidResponse(RedisError):
    pass

########NEW FILE########
__FILENAME__ = app
import brukva
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop
from functools import partial
import redis


r = redis.Redis(db=9)


async = partial(brukva.adisp.async, cbname='callbacks')


c = brukva.Client()
c.connect()

c.select(9)
c.set('foo', 'bar')
c.set('foo2', 'bar2')


class BrukvaHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @brukva.adisp.process
    def get(self):
        ((_, foo), (_, foo2)) = yield [ async(c.get)('foo'), async(c.get)('foo2') ]
        self.set_header('Content-Type', 'text/plain')
        self.write(foo)
        self.write(foo2)
        self.finish()


class RedisHandler(tornado.web.RequestHandler):
    def get(self):
        foo = r.get('foo')
        foo2 = r.get('foo2')
        self.set_header('Content-Type', 'text/plain')
        self.write(foo)
        self.write(foo2)
        self.finish()


class HelloHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'text/plain')
        self.write('Hello world!')
        self.finish()


application = tornado.web.Application([
    (r'/brukva', BrukvaHandler),
    (r'/redis', RedisHandler),
    (r'/hello', HelloHandler),
])


if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = app
import brukva
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop
from brukva import adisp
import logging
from functools import partial


logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger('app')


c = brukva.Client()
c.connect()


def on_set(result):
    (error, data) = result
    log.debug("set result: %s" % (error or data,))


async = partial(adisp.async, cbname='callbacks')


c.set('foo', 'Lorem ipsum #1', on_set)
c.set('bar', 'Lorem ipsum #2', on_set)
c.set('zar', 'Lorem ipsum #3', on_set)


class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @adisp.process
    def get(self):
        (_, foo) = yield async(c.get)('foo')
        (_, bar) = yield async(c.get)('bar')
        (_, zar) = yield async(c.get)('zar')
        self.set_header('Content-Type', 'text/html')
        self.render("template.html", title="Simple demo", foo=foo, bar=bar, zar=zar)


application = tornado.web.Application([
    (r'/', MainHandler),
])


if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = app
# Demo application for brukva
# In order to use:
#  1. $ python app.py
#  2. Open in your browser that supports websockets: http://localhost:8888/
#     You should see text that says "Connected..."
#  3. $ curl http://localhost:8888/msg -d 'message=Hello!'
#     You should see 'Hello!' in your browser

import brukva
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop


c = brukva.Client()
c.connect()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("template.html", title="Websocket test")


class NewMessage(tornado.web.RequestHandler):
    def post(self):
        message = self.get_argument('message')
        c.publish('test_channel', message)
        self.set_header('Content-Type', 'text/plain')
        self.write('sent: %s' % (message,))


class MessagesCatcher(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(MessagesCatcher, self).__init__(*args, **kwargs)
        self.client = brukva.Client()
        self.client.connect()
        self.client.subscribe('test_channel')

    def open(self):
        self.client.listen(self.on_message)

    def on_message(self, result):
        (error, data) = result
        if not error:
            self.write_message(str(data.body))

    def close(self):
        self.client.unsubscribe('test_channel')
        self.client.disconnect()


application = tornado.web.Application([
    (r'/', MainHandler),
    (r'/msg', NewMessage),
    (r'/track', MessagesCatcher),
])

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = show_coverage
# -*- coding: utf-8 -*-

REDIS_COMMANDS = ('QUIT',
                  'AUTH',
                  'EXISTS',
                  'DELETE', # come on :-)
                  'TYPE',
                  'KEYS',
                  'RANDOMKEY',
                  'RENAME',
                  'RENAMENX',
                  'DBSIZE',
                  'EXPIRE',
                  'TTL',
                  'SELECT',
                  'MOVE',
                  'FLUSHDB',
                  'FLUSHALL',
                  'SET',
                  'GET',
                  'GETSET',
                  'MGET',
                  'SETNX',
                  'SETEX',
                  'MSET',
                  'MSETNX',
                  'INCR',
                  'INCRBY',
                  'DECR',
                  'DECRBY',
                  'APPEND',
                  'SUBSTR',
                  'RPUSH',
                  'LPUSH',
                  'LLEN',
                  'LRANGE',
                  'LTRIM',
                  'LINDEX',
                  'LSET',
                  'LREM',
                  'LPOP',
                  'RPOP',
                  'BLPOP',
                  'BRPOP',
                  'RPOPLPUSH',
                  'SADD',
                  'SREM',
                  'SPOP',
                  'SMOVE',
                  'SCARD',
                  'SISMEMBER',
                  'SINTER',
                  'SINTERSTORE',
                  'SUNION',
                  'SUNIONSTORE',
                  'SDIFF',
                  'SDIFFSTORE',
                  'SMEMBERS',
                  'SRANDMEMBER',
                  'ZADD',
                  'ZREM',
                  'ZINCRBY',
                  'ZRANK',
                  'ZREVRANK',
                  'ZRANGE',
                  'ZREVRANGE',
                  'ZRANGEBYSCORE',
                  'ZCARD',
                  'ZSCORE',
                  'ZREMRANGEBYRANK',
                  'ZREMRANGEBYSCORE',
                  'ZUNIONSTORE',
                  'ZINTERSTORE',
                  'HSET',
                  'HGET',
                  'HMSET',
                  'HINCRBY',
                  'HEXISTS',
                  'HDEL',
                  'HLEN',
                  'HKEYS',
                  'HVALS',
                  'HGETALL',
                  'SORT',
                  'SUBSCRIBE',
                  'UNSUBSCRIBE',
                  'PUBLISH',
                  'SAVE',
                  'BGSAVE',
                  'LASTSAVE',
                  'SHUTDOWN',
                  'BGREWRITEAOF',
                  'INFO',
                  'SLAVEOF',
                  'CONFIG')

from brukva import Client

covered_commands = set(c.upper() for c in dir(Client))
uncovered_commands = set(REDIS_COMMANDS).difference(covered_commands)

if __name__ == '__main__':
    if not uncovered_commands:
        exit(0)
    print 'Uncovered commmands:'
    for c in sorted(uncovered_commands):
        print '\t%s' % c
    print 'Commands to cover: %d' % len(uncovered_commands)
    print 'Already covered: %d' % len(set(REDIS_COMMANDS).intersection(covered_commands))


########NEW FILE########
__FILENAME__ = server_commands
import brukva
from brukva.exceptions import ResponseError
import unittest
import sys
from datetime import datetime, timedelta
from tornado.ioloop import IOLoop

def callable(obj):
    return hasattr(obj, '__call__')

class CustomAssertionError(AssertionError):
    io_loop = None

    def __init__(self, *args, **kwargs):
        super(CustomAssertionError, self).__init__(*args, **kwargs)
        CustomAssertionError.io_loop.stop()


class TestIOLoop(IOLoop):
    def handle_callback_exception(self, callback):
        (type, value, traceback) = sys.exc_info()
        raise type, value, traceback


class TornadoTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TornadoTestCase, self).__init__(*args, **kwargs)
        self.failureException = CustomAssertionError

    def setUp(self):
        self.loop = TestIOLoop()
        CustomAssertionError.io_loop = self.loop
        self.client = brukva.Client(io_loop=self.loop)
        self.client.connection.connect()
        self.client.select(9)
        self.client.flushdb()

    def tearDown(self):
        self.finish()

    def expect(self, expected):
        def callback(result):
            error, data = result
            if error:
                self.assertFalse(error, data)
            if callable(expected):
                self.assertTrue(expected(data))
            else:
                self.assertEqual(expected, data)
        return callback

    def pexpect(self, expected_list, list_without_errors=True):
        if list_without_errors:
            expected_list = [(None, el) for el in expected_list]
        def callback(result):
            self.assertEqual(len(result), len(expected_list) )
            for (e, d), (exp_e, exp_d)  in zip(result, expected_list):
                if exp_e:
                    self.assertTrue( isinstance(e, exp_e) )

                if callable(exp_d):
                    self.assertTrue(exp_d(d))
                else:
                    self.assertEqual(d, exp_d)
        return callback

    def finish(self, *args):
        self.loop.stop()

    def start(self):
        self.loop.start()

class ServerCommandsTestCase(TornadoTestCase):
    def test_set(self):
        self.client.set('foo', 'bar', [self.expect(True), self.finish])
        self.start()

    def test_setex(self):
        self.client.setex('foo', 5, 'bar', self.expect(True))
        self.client.ttl('foo', [self.expect(5), self.finish])
        self.start()

    def test_setnx(self):
        self.client.setnx('a', 1, self.expect(True))
        self.client.setnx('a', 0, [self.expect(False), self.finish])
        self.start()

    def test_get(self):
        self.client.set('foo', 'bar', self.expect(True))
        self.client.get('foo', [self.expect('bar'), self.finish])
        self.start()

    def test_randomkey(self):
        self.client.set('a', 1, self.expect(True))
        self.client.set('b', 1, self.expect(True))
        self.client.randomkey(self.expect(lambda k: k in ['a', 'b']))
        self.client.randomkey(self.expect(lambda k: k in ['a', 'b']))
        self.client.randomkey([self.expect(lambda k: k in ['a', 'b']), self.finish])
        self.start()

    def test_substr(self):
        self.client.set('foo', 'lorem ipsum', self.expect(True))
        self.client.substr('foo', 2, 4, [self.expect('rem'), self.finish])
        self.start()

    def test_append(self):
        self.client.set('foo', 'lorem ipsum', self.expect(True))
        self.client.append('foo', ' bar', self.expect(15))
        self.client.get('foo', [self.expect('lorem ipsum bar'), self.finish])
        self.start()

    def test_dbsize(self):
        self.client.set('a', 1, self.expect(True))
        self.client.set('b', 2, self.expect(True))
        self.client.dbsize([self.expect(2), self.finish])
        self.start()

    def test_save(self):
        self.client.save(self.expect(True))
        now = datetime.now().replace(microsecond=0)
        self.client.lastsave([self.expect(lambda d: d >= now), self.finish])
        self.start()

    def test_keys(self):
        self.client.set('a', 1, self.expect(True))
        self.client.set('b', 2, self.expect(True))
        self.client.keys('*', self.expect(['a', 'b']))
        self.client.keys('', self.expect([]))

        self.client.set('foo_a', 1, self.expect(True))
        self.client.set('foo_b', 2, self.expect(True))
        self.client.keys('foo_*', [self.expect(['foo_a', 'foo_b']), self.finish])
        self.start()

    def test_expire(self):
        self.client.set('a', 1, self.expect(True))
        self.client.expire('a', 10, self.expect(True))
        self.client.ttl('a', [self.expect(10), self.finish])
        self.start()

    def test_type(self):
        self.client.set('a', 1, self.expect(True))
        self.client.type('a', self.expect('string'))
        self.client.rpush('b', 1, self.expect(True))
        self.client.type('b', self.expect('list'))
        self.client.sadd('c', 1, self.expect(True))
        self.client.type('c', self.expect('set'))
        self.client.hset('d', 'a', 1, self.expect(True))
        self.client.type('d', self.expect('hash'))
        self.client.zadd('e', 1, 1, self.expect(True))
        self.client.type('e', [self.expect('zset'), self.finish])
        self.start()

    def test_rename(self):
        self.client.set('a', 1, self.expect(True))
        self.client.rename('a', 'b', self.expect(True))
        self.client.set('c', 1, self.expect(True))
        self.client.renamenx('c', 'b', [self.expect(False), self.finish])
        self.start()

    def test_move(self):
        self.client.select(8, self.expect(True))
        self.client.delete('a', self.expect(True))
        self.client.select(9, self.expect(True))
        self.client.set('a', 1, self.expect(True))
        self.client.move('a', 8, self.expect(True))
        self.client.exists('a', self.expect(False))
        self.client.select(8, self.expect(True))
        self.client.get('a', [self.expect('1'), self.finish])
        self.start()

    def test_exists(self):
        self.client.set('a', 1, self.expect(True))
        self.client.exists('a', self.expect(True))
        self.client.delete('a', self.expect(True))
        self.client.exists('a', [self.expect(False), self.finish])
        self.start()

    def test_mset_mget(self):
        self.client.mset({'a': 1, 'b': 2}, self.expect(True))
        self.client.get('a', self.expect('1'))
        self.client.get('b', self.expect('2'))
        self.client.mget(['a', 'b'], [self.expect(['1', '2']), self.finish])
        self.start()

    def test_msetnx(self):
        self.client.msetnx({'a': 1, 'b': 2}, self.expect(True))
        self.client.msetnx({'b': 3, 'c': 4}, [self.expect(False), self.finish])
        self.start()

    def test_getset(self):
        self.client.set('a', 1, self.expect(True))
        self.client.getset('a', 2, self.expect('1'))
        self.client.get('a', [self.expect('2'), self.finish])
        self.start()

    def test_hash(self):
        self.client.hmset('foo', {'a': 1, 'b': 2}, self.expect(True))
        self.client.hgetall('foo', self.expect({'a': '1', 'b': '2'}))
        self.client.hdel('foo', 'a', self.expect(True))
        self.client.hgetall('foo', self.expect({'b': '2'}))
        self.client.hget('foo', 'a', self.expect(''))
        self.client.hget('foo', 'b', self.expect('2'))
        self.client.hlen('foo', self.expect(1))
        self.client.hincrby('foo', 'b', 3, self.expect(5))
        self.client.hkeys('foo', self.expect(['b']))
        self.client.hvals('foo', self.expect(['5']))
        self.client.hmget('foo', 'b', self.expect(['5']))
        self.client.hexists('foo', 'b', [self.expect(True), self.finish])
        self.start()

    def test_incrdecr(self):
        self.client.incr('foo', self.expect(1))
        self.client.incrby('foo', 10, self.expect(11))
        self.client.decr('foo', self.expect(10))
        self.client.decrby('foo', 10, self.expect(0))
        self.client.decr('foo', [self.expect(-1), self.finish])
        self.start()

    def test_ping(self):
        self.client.ping([self.expect(True), self.finish])
        self.start()

    def test_lists(self):
        self.client.lpush('foo', 1, self.expect(True))
        self.client.llen('foo', self.expect(1))
        self.client.lrange('foo', 0, -1, self.expect(['1']))
        self.client.rpop('foo', self.expect('1'))
        self.client.llen('foo', [self.expect(0), self.finish])
        self.start()

    def test_sets(self):
        self.client.smembers('foo', self.expect(set()))
        self.client.sadd('foo', 'a', self.expect(1))
        self.client.sadd('foo', 'b', self.expect(1))
        self.client.sadd('foo', 'c', self.expect(1))
        self.client.srandmember('foo', self.expect(lambda x: x in ['a', 'b', 'c']))
        self.client.scard('foo', self.expect(3))
        self.client.srem('foo', 'a', self.expect(True))
        self.client.smove('foo', 'bar', 'b', self.expect(True))
        self.client.smembers('bar', self.expect(set(['b'])))
        self.client.sismember('foo', 'c', self.expect(True))
        self.client.spop('foo', [self.expect('c'), self.finish])
        self.start()

    def test_sets2(self):
        self.client.sadd('foo', 'a', self.expect(1))
        self.client.sadd('foo', 'b', self.expect(1))
        self.client.sadd('foo', 'c', self.expect(1))
        self.client.sadd('bar', 'b', self.expect(1))
        self.client.sadd('bar', 'c', self.expect(1))
        self.client.sadd('bar', 'd', self.expect(1))

        self.client.sdiff(['foo', 'bar'], self.expect(set(['a'])))
        self.client.sdiff(['bar', 'foo'], self.expect(set(['d'])))
        self.client.sinter(['foo', 'bar'], self.expect(set(['b', 'c'])))
        self.client.sunion(['foo', 'bar'], [self.expect(set(['a', 'b', 'c', 'd'])), self.finish])
        self.start()

    def test_sets3(self):
        self.client.sadd('foo', 'a', self.expect(1))
        self.client.sadd('foo', 'b', self.expect(1))
        self.client.sadd('foo', 'c', self.expect(1))
        self.client.sadd('bar', 'b', self.expect(1))
        self.client.sadd('bar', 'c', self.expect(1))
        self.client.sadd('bar', 'd', self.expect(1))

        self.client.sdiffstore(['foo', 'bar'], 'zar', self.expect(1))
        self.client.smembers('zar', self.expect(set(['a'])))
        self.client.delete('zar', self.expect(True))

        self.client.sinterstore(['foo', 'bar'], 'zar', self.expect(2))
        self.client.smembers('zar', self.expect(set(['b', 'c'])))
        self.client.delete('zar', self.expect(True))

        self.client.sunionstore(['foo', 'bar'], 'zar', self.expect(4))
        self.client.smembers('zar', [self.expect(set(['a', 'b', 'c', 'd'])), self.finish])
        self.start()

    def test_zsets(self):
        self.client.zadd('foo', 1, 'a', self.expect(1))
        self.client.zadd('foo', 2, 'b', self.expect(1))
        self.client.zscore('foo', 'a', self.expect(1))
        self.client.zscore('foo', 'b', self.expect(2))
        self.client.zrank('foo', 'a', self.expect(0))
        self.client.zrank('foo', 'b', self.expect(1))
        self.client.zrevrank('foo', 'a', self.expect(1))
        self.client.zrevrank('foo', 'b', self.expect(0))
        self.client.zincrby('foo', 'a', 1, self.expect(2))
        self.client.zincrby('foo', 'b', 1, self.expect(3))
        self.client.zscore('foo', 'a', self.expect(2))
        self.client.zscore('foo', 'b', self.expect(3))
        self.client.zrange('foo', 0, -1, True, self.expect([('a', 2.0), ('b', 3.0)]))
        self.client.zrange('foo', 0, -1, False, self.expect(['a', 'b']))
        self.client.zrevrange('foo', 0, -1, True, self.expect([('b', 3.0), ('a', 2.0)]))
        self.client.zrevrange('foo', 0, -1, False, self.expect(['b', 'a']))
        self.client.zcard('foo', [self.expect(2)])
        self.client.zadd('foo', 3.5, 'c', self.expect(1))
        self.client.zrangebyscore('foo', '-inf', '+inf', None, None, False, self.expect(['a', 'b', 'c']))
        self.client.zrangebyscore('foo', '2.1', '+inf', None, None, True, self.expect([('b', 3.0), ('c', 3.5)]))
        self.client.zrangebyscore('foo', '-inf', '3.0', 0, 1, False, self.expect(['a']))
        self.client.zrangebyscore('foo', '-inf', '+inf', 1, 2, False, self.expect(['b', 'c']))

        self.client.delete('foo', self.expect(True))
        self.client.zadd('foo', 1, 'a', self.expect(1))
        self.client.zadd('foo', 2, 'b', self.expect(1))
        self.client.zadd('foo', 3, 'c', self.expect(1))
        self.client.zadd('foo', 4, 'd', self.expect(1))
        self.client.zremrangebyrank('foo', 2, 4, self.expect(2))
        self.client.zremrangebyscore('foo', 0, 2, [self.expect(2), self.finish()])

        self.client.zadd('a', 1, 'a1', self.expect(1))
        self.client.zadd('a', 1, 'a2', self.expect(1))
        self.client.zadd('a', 1, 'a3', self.expect(1))
        self.client.zadd('b', 2, 'a1', self.expect(1))
        self.client.zadd('b', 2, 'a3', self.expect(1))
        self.client.zadd('b', 2, 'a4', self.expect(1))
        self.client.zadd('c', 6, 'a1', self.expect(1))
        self.client.zadd('c', 5, 'a3', self.expect(1))
        self.client.zadd('c', 4, 'a4', self.expect(1))

        # ZINTERSTORE
        # sum, no weight
        self.client.zinterstore('z', ['a', 'b', 'c'], callbacks=self.expect(2))
        self.client.zrange('z', 0, -1, with_scores=True, callbacks=self.expect([('a3', 8),
                                                                                ('a1', 9),
                                                                                ]))
        # max, no weight
        self.client.zinterstore('z', ['a', 'b', 'c'], aggregate='MAX', callbacks=self.expect(2))
        self.client.zrange('z', 0, -1, with_scores=True, callbacks=self.expect([('a3', 5),
                                                                                ('a1', 6),
                                                                                ]))
        # with weight
        self.client.zinterstore('z', {'a': 1, 'b': 2, 'c': 3}, callbacks=self.expect(2))
        self.client.zrange('z', 0, -1, with_scores=True, callbacks=[self.expect([('a3', 20),
                                                                                 ('a1', 23),
                                                                                 ]),
                                                                    self.finish()])

        # ZUNIONSTORE
        # sum, no weight
        self.client.zunionstore('z', ['a', 'b', 'c'], callbacks=self.expect(5))
        self.client.zrange('z', 0, -1, with_scores=True, callbacks=self.expect([('a2', 1),
                                                                                ('a3', 3),
                                                                                ('a5', 4),
                                                                                ('a4', 7),
                                                                                ('a1', 9),
                                                                                ]))
        # max, no weight
        self.client.zunionstore('z', ['a', 'b', 'c'], aggregate='MAX', callbacks=self.expect(5))
        self.client.zrange('z', 0, -1, with_scores=True, callbacks=self.expect([('a2', 1),
                                                                                ('a3', 2),
                                                                                ('a5', 4),
                                                                                ('a4', 5),
                                                                                ('a1', 6),
                                                                                ]))
        # with weight
        self.client.zunionstore('z', {'a': 1, 'b': 2, 'c': 3}, callbacks=self.expect(5))
        self.client.zrange('z', 0, -1, with_scores=True, callbacks=[self.expect([('a2', 1),
                                                                                 ('a3', 5),
                                                                                 ('a5', 12),
                                                                                 ('a4', 19),
                                                                                 ('a1', 23),
                                                                                 ]),
                                                                    self.finish(),
                                                                    ])
        self.start()

    def test_sort(self):
        def make_list(key, items):
            self.client.delete(key, callbacks=self.expect(True))
            for i in items:
                self.client.rpush(key, i)
        self.client.sort('a', callbacks=self.expect([]))
        make_list('a', '3214')
        self.client.sort('a', callbacks=self.expect(['1', '2', '3', '4']))
        self.client.sort('a', start=1, num=2, callbacks=self.expect(['2', '3']))

        self.client.set('score:1', 8, callbacks=self.expect(True))
        self.client.set('score:2', 3, callbacks=self.expect(True))
        self.client.set('score:3', 5, callbacks=self.expect(True))
        make_list('a_values', '123')
        self.client.sort('a_values', by='score:*', callbacks=self.expect(['2', '3', '1']))

        self.client.set('user:1', 'u1', callbacks=self.expect(True))
        self.client.set('user:2', 'u2', callbacks=self.expect(True))
        self.client.set('user:3', 'u3', callbacks=self.expect(True))

        make_list('a', '231')
        self.client.sort('a', get='user:*', callbacks=self.expect(['u1', 'u2', 'u3']))

        make_list('a', '231')
        self.client.sort('a', desc=True, callbacks=self.expect(['3', '2', '1']))

        make_list('a', 'ecdba')
        self.client.sort('a', alpha=True, callbacks=self.expect(['a', 'b', 'c', 'd', 'e']))

        make_list('a', '231')
        self.client.sort('a', store='sorted_values', callbacks=self.expect(3))
        self.client.lrange('a', 0, -1, callbacks=self.expect(['1', '2', '3']))

        self.client.set('user:1:username', 'zeus')
        self.client.set('user:2:username', 'titan')
        self.client.set('user:3:username', 'hermes')
        self.client.set('user:4:username', 'hercules')
        self.client.set('user:5:username', 'apollo')
        self.client.set('user:6:username', 'athena')
        self.client.set('user:7:username', 'hades')
        self.client.set('user:8:username', 'dionysus')
        self.client.set('user:1:favorite_drink', 'yuengling')
        self.client.set('user:2:favorite_drink', 'rum')
        self.client.set('user:3:favorite_drink', 'vodka')
        self.client.set('user:4:favorite_drink', 'milk')
        self.client.set('user:5:favorite_drink', 'pinot noir')
        self.client.set('user:6:favorite_drink', 'water')
        self.client.set('user:7:favorite_drink', 'gin')
        self.client.set('user:8:favorite_drink', 'apple juice')
        make_list('gods', '12345678')
        self.client.sort('gods',
                         start=2,
                         num=4,
                         by='user:*:username',
                         get='user:*:favorite_drink',
                         desc=True,
                         alpha=True,
                         store='sorted',
                         callbacks=self.expect(4))
        self.client.lrange('sorted', 0, -1, callbacks=[self.expect(['vodka',
                                                                    'milk',
                                                                    'gin',
                                                                    'apple juice',
                                                                    ]),
                                                       self.finish()])
        self.start()

    ### Pipeline ###
    def test_pipe_simple(self):
        pipe = self.client.pipeline()
        pipe.set('foo', '123')
        pipe.set('bar', '456')
        pipe.mget( ('foo', 'bar') )

        pipe.execute([self.pexpect([True , True, ['123', '456',]]), self.finish])
        self.start()

    def test_pipe_multi(self):
        pipe = self.client.pipeline(transactional=True)
        pipe.set('foo', '123')
        pipe.set('bar', '456')
        pipe.mget( ('foo', 'bar') )

        pipe.execute([self.pexpect([True , True, ['123', '456',]]), self.finish])
        self.start()

    def test_pipe_error(self):
        pipe = self.client.pipeline()
        pipe.sadd('foo', 1)
        pipe.sadd('foo', 2)
        pipe.rpop('foo')

        pipe.execute([self.pexpect([(None, True), (None, True), (ResponseError, None)], False), self.finish])
        self.start()

    def test_two_pipes(self):
        pipe = self.client.pipeline()

        pipe.rpush('foo', '1')
        pipe.rpush('foo', '2')
        pipe.lrange('foo', 0, -1)
        pipe.execute([self.pexpect([True, 2, ['1', '2']]) ] )

        pipe.sadd('bar', '3')
        pipe.sadd('bar', '4')
        pipe.smembers('bar')
        pipe.scard('bar')
        pipe.execute([self.pexpect([1, 1, set(['3', '4']), 2]), self.finish])

        self.start()

    def test_mix_with_pipe(self):
        pipe = self.client.pipeline()

        self.client.set('foo', '123', self.expect(True))
        self.client.hmset('bar', {'zar': 'gza'},)

        pipe.get('foo')
        self.client.get('foo', self.expect('123') )

        pipe.hgetall('bar')

        pipe.execute([self.pexpect(['123', {'zar': 'gza'}]), self.finish])
        self.start()

    def test_mix_with_pipe_multi(self):
        pipe = self.client.pipeline(transactional=True)

        self.client.set('foo', '123', self.expect(True))
        self.client.hmset('bar', {'zar': 'gza'},)

        pipe.get('foo')
        self.client.get('foo', self.expect('123') )

        pipe.hgetall('bar')

        pipe.execute([self.pexpect(['123', {'zar': 'gza'}]), self.finish])
        self.start()

    def test_pipe_watch(self):
        self.client.watch('foo', self.expect(True))
        self.client.set('bar', 'zar', self.expect(True))
        pipe = self.client.pipeline(transactional=True)
        pipe.get('bar')
        pipe.execute([self.pexpect(['zar',]), self.finish])
        self.start()

    def test_pipe_watch2(self):
        self.client.set('foo', 'bar', self.expect(True))
        self.client.watch('foo', self.expect(True))
        self.client.set('foo', 'zar', self.expect(True))
        pipe = self.client.pipeline(transactional=True)
        pipe.get('foo')
        pipe.execute([self.pexpect([]), self.finish])
        self.start()

    def test_pipe_unwatch(self):
        self.client.set('foo', 'bar', self.expect(True))
        self.client.watch('foo', self.expect(True))
        self.client.set('foo', 'zar', self.expect(True))
        self.client.unwatch(callbacks=self.expect(True))
        pipe = self.client.pipeline(transactional=True)
        pipe.get('foo')
        pipe.execute([self.pexpect(['zar']), self.finish])
        self.start()

    def test_pipe_zsets(self):
        pipe = self.client.pipeline(transactional=True)

        pipe.zadd('foo', 1, 'a')
        pipe.zadd('foo', 2, 'b')
        pipe.zscore('foo', 'a')
        pipe.zscore('foo', 'b' )
        pipe.zrank('foo', 'a', )
        pipe.zrank('foo', 'b', )

        pipe.zrange('foo', 0, -1, True )
        pipe.zrange('foo', 0, -1, False)

        pipe.execute([
            self.pexpect([
                1, 1,
                1, 2,
                0, 1,
                [('a', 1.0), ('b', 2.0)],
                ['a', 'b'],
            ]),
            self.finish,
        ])

    def test_pipe_zsets2(self):
        pipe = self.client.pipeline(transactional=False)

        pipe.zadd('foo', 1, 'a')
        pipe.zadd('foo', 2, 'b')
        pipe.zscore('foo', 'a')
        pipe.zscore('foo', 'b' )
        pipe.zrank('foo', 'a', )
        pipe.zrank('foo', 'b', )

        pipe.zrange('foo', 0, -1, True )
        pipe.zrange('foo', 0, -1, False)

        pipe.execute([
            self.pexpect([
                1, 1,
                1, 2,
                0, 1,
                [('a', 1.0), ('b', 2.0)],
                ['a', 'b'],
            ]),
            self.finish,
        ])
        self.start()

    def test_pipe_hsets(self):
        pipe = self.client.pipeline(transactional=True)
        pipe.hset('foo', 'bar', 'aaa')
        pipe.hset('foo', 'zar', 'bbb')
        pipe.hgetall('foo')

        pipe.execute([
            self.pexpect([
                True,
                True,
                {'bar': 'aaa', 'zar': 'bbb'}
            ]),
            self.finish,
        ])
        self.start()

    def test_pipe_hsets2(self):
        pipe = self.client.pipeline(transactional=False)
        pipe.hset('foo', 'bar', 'aaa')
        pipe.hset('foo', 'zar', 'bbb')
        pipe.hgetall('foo')

        pipe.execute([
            self.pexpect([
                True,
                True,
                {'bar': 'aaa', 'zar': 'bbb'}
            ]),
            self.finish,
        ])
        self.start()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pipe
#! /usr/bin/env python

from functools import partial
import time
import os
from pprint import pprint

import brukva

c = brukva.Client()
c.connect()

def delayed(dt, cmd,  *args, **kwargs):
    c._io_loop.add_timeout(
        time.time()+dt,
        partial(cmd, *args, **kwargs)
    )

def ac(cmd, *args, **kwargs):
    c._io_loop.add_callback(
        partial(cmd, *args, **kwargs)
    )

stt = time.time()
def on_resp(res):

    pprint(res)
    print (time.time() - stt)

c.set('gt', 'er', on_resp)
c.mget(['gt','sdfas'], on_resp)
c.get('gt', on_resp)
c.flushdb()
p = c.pipeline()#transactional=True)

p.set('foo1', 'bar')
p.get('foo1')
p.set('bar', '123')
p.mget(['foo1', 'bar',])
p.sadd('zar', '1')
p.sadd('zar', '4')
p.smembers('zar')
p.scard('zar')


c.zadd('nya', 1, 'n', on_resp)
c.zadd('nya', 2, 'sf', on_resp)

p.zrange('nya', 0, -1, with_scores=True, callbacks=on_resp)

ac( p.execute, [on_resp,])

delayed(0.1, p.set, 'aaa', '132')
delayed(0.1, p.set, 'bbb', 'eft')
delayed(0.1, p.mget, ('aaa', 'ccc', 'bbb'))
delayed(0.1, p.sadd, 'foo', '13d2')
delayed(0.1, p.sadd, 'foo', 'efdt')
delayed(0.1, p.lpop, 'aaa') # must fail
delayed(0.1, p.mget, ('aaa', 'bbb'))
delayed(0.1, p.smembers, 'foo' )
delayed(0.1, p.execute, [on_resp,])

delayed(0.3, os.sys.exit)
c.connection._stream.io_loop.start()

########NEW FILE########
