__FILENAME__ = config
#!/usr/bin/env python
# -*- coding: utf-8 -*-
servers = [
        {'name':'server1','host':'127.0.0.1','port':6379,'db':0},
        {'name':'server2','host':'127.0.0.1','port':6379,'db':0},
        {'name':'server3','host':'127.0.0.1','port':6379,'db':0},
        {'name':'server4','host':'127.0.0.1','port':6379,'db':0},
        #{'name':'server5','host':'127.0.0.1','port':14000,'db':0},
        #{'name':'server6','host':'127.0.0.1','port':15000,'db':0},
        ]

########NEW FILE########
__FILENAME__ = myapp
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from redis_shard.shard import RedisShardAPI
from config import servers
import time

client = RedisShardAPI(servers)
client.set('test', 1)
print client.get('test')
client.zadd('testset', 'first', 1)
client.zadd('testset', 'second', 2)
print client.zrange('testset', 0, -1)
print client.zrank('testset', 'second')
print client.zrank('testset2', 'second')

client.set('foo', 2)
client.set('a{foo}', 5)
client.set('b{foo}', 5)
client.set('c{foo}', 5)
client.set('{foo}d', 6)
client.set('{foo}e', 7)
client.set('e{foo}f', 8)
print client.get_server_name('foo')
print client.get_server_name('c{foo}')
print client.get_server_name('{foo}d')
print client.get_server_name('{foo}e')
print client.get_server_name('e{foo}f')
t0 = time.time()
print client.tag_keys('*{foo}*')
t1 = time.time()
print t1 - t0
print client.keys('*{foo}*')
t2 = time.time()
print t2 - t1

print client.tag_mget('a{foo}', 'b{foo}', '{foo}d')
print client.tag_mget(['a{foo}', 'b{foo}', '{foo}d'])

########NEW FILE########
__FILENAME__ = reshard
#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
from redis_shard.shard import RedisShardAPI

old_servers = [{'name': 'feed1', 'host': 'feedproxy', 'port': 6301, 'db': 0},
               {'name': 'feed2', 'host': 'feedproxy', 'port': 6302, 'db': 0},
               {'name': 'feed3', 'host': 'feedproxy', 'port': 6303, 'db': 0},
               {'name': 'feed4', 'host': 'feedproxy', 'port': 6304, 'db': 0},
               {'name': 'feed5', 'host': 'feedproxy', 'port': 6305, 'db': 0},
               {'name': 'feed6', 'host': 'feedproxy', 'port': 6306, 'db': 0},
               {'name': 'feed7', 'host': 'feedproxy', 'port': 6307, 'db': 0},
               {'name': 'feed8', 'host': 'feedproxy', 'port': 6308, 'db': 0},
               {'name': 'feed9', 'host': 'feedproxy', 'port': 6309, 'db': 0},
               {'name': 'feed10', 'host': 'feedproxy', 'port': 6310, 'db': 0},
               ]

new_servers = [{'name': 'feed1', 'host': 'feedproxy', 'port': 6301, 'db': 0},
               {'name': 'feed2', 'host': 'feedproxy', 'port': 6302, 'db': 0},
               {'name': 'feed3', 'host': 'feedproxy', 'port': 6303, 'db': 0},
               {'name': 'feed4', 'host': 'feedproxy', 'port': 6304, 'db': 0},
               {'name': 'feed5', 'host': 'feedproxy', 'port': 6305, 'db': 0},
               {'name': 'feed6', 'host': 'feedproxy', 'port': 6306, 'db': 0},
               {'name': 'feed7', 'host': 'feedproxy', 'port': 6307, 'db': 0},
               {'name': 'feed8', 'host': 'feedproxy', 'port': 6308, 'db': 0},
               {'name': 'feed9', 'host': 'feedproxy', 'port': 6309, 'db': 0},
               {'name': 'feed10', 'host': 'feedproxy', 'port': 6310, 'db': 0},
               {'name': 'feed11', 'host': 'feedproxy', 'port': 6311, 'db': 0},
               {'name': 'feed12', 'host': 'feedproxy', 'port': 6312, 'db': 0},
               {'name': 'feed13', 'host': 'feedproxy', 'port': 6313, 'db': 0},
               {'name': 'feed14', 'host': 'feedproxy', 'port': 6314, 'db': 0},
               {'name': 'feed15', 'host': 'feedproxy', 'port': 6315, 'db': 0},
               {'name': 'feed16', 'host': 'feedproxy', 'port': 6316, 'db': 0},
               {'name': 'feed17', 'host': 'feedproxy', 'port': 6317, 'db': 0},
               {'name': 'feed18', 'host': 'feedproxy', 'port': 6318, 'db': 0},
               {'name': 'feed19', 'host': 'feedproxy', 'port': 6319, 'db': 0},
               {'name': 'feed20', 'host': 'feedproxy', 'port': 6320, 'db': 0},
               ]


FEED_KEY = "{feed%(user_id)s}:list"

old_shard = RedisShardAPI(old_servers)
new_shard = RedisShardAPI(new_servers)


def main():
    parser = argparse.ArgumentParser(description='Reshard newsfeed instance')
    parser.add_argument(
        '--start', type=int, required=True, help='start user id')
    parser.add_argument('--end', type=int, required=True, help='start user id')
    parser.add_argument('--show_only', type=bool, default=False,
                        help='only showw migrate process')
    parser.add_argument(
        '--delete', type=bool, default=False, help='real delete old data')
    args = parser.parse_args()
    migrate(args.start, args.end, args.delete, args.show_only)


def migrate(start, end, delete, show_only=False):
    for user_id in range(start, end):
        feed_list_key = FEED_KEY % dict(user_id=user_id)
        old_server_name = old_shard.get_server_name(feed_list_key)
        new_server_name = new_shard.get_server_name(feed_list_key)
        if old_server_name != new_server_name:
            print "%s : %s => %s" % (user_id, old_server_name, new_server_name)
            if show_only:
                continue
            old_server = old_shard.get_server(feed_list_key)
            new_server = new_shard.get_server(feed_list_key)
            if not delete:
                for k, v in old_server.zrange(feed_list_key, 0, -1, withscores=True):
                    new_server.zadd(feed_list_key, k, v)
            else:
                old_server.delete(feed_list_key)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = commands
#!/usr/bin/env python
SHARD_METHODS = set(['restore',
                     'debug object',
                     'renamenx',
                     'hincrby',
                     'zrevrank',
                     'zcount',
                     'move',
                     'pop',
                     'hexists',
                     'get_type',
                     'incrbyfloat',
                     'ttl',
                     'sinter',
                     'getbit',
                     'decr',
                     'rpush',
                     'pttl',
                     'zscore',
                     'delete',
                     'dump',
                     'zincrby',
                     'zrevrangebyscore',
                     'persist',
                     'zrem',
                     'zadd',
                     'linsert',
                     'sort',
                     'zcard',
                     'bitcount',
                     'get',
                     'setnx',
                     'watch',
                     'incrby',
                     'lindex',
                     'hget',
                     'hlen',
                     'expireat',
                     'type',
                     'zincr',
                     'lset',
                     'hkeys',
                     'setrange',
                     'del',
                     'hset',
                     'decrby',
                     'zrange',
                     'rename',
                     'set',
                     'exists',
                     'hincrbyfloat',
                     'pexpireat',
                     'hvals',
                     'setex',
                     'sdiff',
                     'blpop',
                     'strlen',
                     'append',
                     'srem',
                     'pexpire',
                     'getrange',
                     'zrevrange',
                     'zremrangebyscore',
                     'hsetnx',
                     'lpushx',
                     'rpushx',
                     'hmset',
                     'srandmember',
                     'sismember',
                     'getset',
                     'smembers',
                     'zrank',
                     'psetex',
                     'zremrangebyrank',
                     'sadd',
                     'ltrim',
                     'spop',
                     'incr',
                     'expire',
                     'brpop',
                     'lrange',
                     'sunion',
                     'setbit',
                     'zrangebyscore',
                     'rpop',
                     'lrem',
                     'lpop',
                     'hgetall',
                     'lpush',
                     'hmget',
                     'push',
                     'hdel',
                     'scard',
                     'llen',
                     'publish'])

########NEW FILE########
__FILENAME__ = hashring
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 consistent hashing for nosql client
 based on ezmobius client (redis-rb)
 and see this article http://amix.dk/blog/viewEntry/19367
"""

import zlib
import bisect

from ._compat import xrange, b


class HashRing(object):
    """Consistent hash for nosql API"""
    def __init__(self, nodes=[], replicas=128):
        """Manages a hash ring.

        `nodes` is a list of objects that have a proper __str__ representation.
        `replicas` indicates how many virtual points should be used pr. node,
        replicas are required to improve the distribution.
        """
        self.nodes = []
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []

        for n in nodes:
            self.add_node(n)

    def add_node(self, node):
        """Adds a `node` to the hash ring (including a number of replicas).
        """
        self.nodes.append(node)
        for x in xrange(self.replicas):
            crckey = zlib.crc32(b("%s:%d" % (node, x)))
            self.ring[crckey] = node
            self.sorted_keys.append(crckey)

        self.sorted_keys.sort()

    def remove_node(self, node):
        """Removes `node` from the hash ring and its replicas.
        """
        self.nodes.remove(node)
        for x in xrange(self.replicas):
            crckey = zlib.crc32(b("%s:%d" % (node, x)))
            self.ring.remove(crckey)
            self.sorted_keys.remove(crckey)

    def get_node(self, key):
        """Given a string key a corresponding node in the hash ring is returned.

        If the hash ring is empty, `None` is returned.
        """
        n, i = self.get_node_pos(key)
        return n

    def get_node_pos(self, key):
        """Given a string key a corresponding node in the hash ring is returned
        along with it's position in the ring.

        If the hash ring is empty, (`None`, `None`) is returned.
        """
        if len(self.ring) == 0:
            return [None, None]
        crc = zlib.crc32(b(key))
        idx = bisect.bisect(self.sorted_keys, crc)
        idx = min(idx, (self.replicas * len(self.nodes)) - 1)
                  # prevents out of range index
        return [self.ring[self.sorted_keys[idx]], idx]

    def iter_nodes(self, key):
        """Given a string key it returns the nodes as a generator that can hold the key.
        """
        if len(self.ring) == 0:
            yield None, None
        node, pos = self.get_node_pos(key)
        for k in self.sorted_keys[pos:]:
            yield k, self.ring[k]

    def __call__(self, key):
        return self.get_node(key)

########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from .url import parse_url


def format_config(settings):
    """
    There's three config formats

    - list

    servers = [
        {'name':'node1','host':'127.0.0.1','port':10000,'db':0},
        {'name':'node2','host':'127.0.0.1','port':11000,'db':0},
        {'name':'node3','host':'127.0.0.1','port':12000,'db':0},
        ]

    - dict

    servers =
        { 'node1': {'host':'127.0.0.1','port':10000,'db':0},
            'node2': {'host':'127.0.0.1','port':11000,'db':0},
            'node3': {'host':'127.0.0.1','port':12000,'db':0},
        }

    - url_schema

    servers = ['redis://127.0.0.1:10000/0?name=node1',
                'redis://127.0.0.1:11000/0?name=node2',
                'redis://127.0.0.1:12000/0?name=node3'
        ]

    """
    configs = []
    if isinstance(settings, list):
        _type = type(settings[0])
        if _type == dict:
            return settings
        if (sys.version_info[0] == 3 and _type in [str, bytes]) \
                or (sys.version_info[0] == 2 and _type in [str, unicode]):
            for config in settings:
                configs.append(parse_url(config))
        else:
            raise ValueError("invalid server config")
    elif isinstance(settings, dict):
        for name, config in settings.items():
            config['name'] = name
            configs.append(config)
    else:
        raise ValueError("server's config must be list or dict")
    return configs

########NEW FILE########
__FILENAME__ = pipeline

import functools
from .commands import SHARD_METHODS
from ._compat import basestring, dictvalues


class Pipeline(object):

    def __init__(self, shard_api):
        self.shard_api = shard_api
        self.pipelines = {}
        self.__counter = 0
        self.__indexes = {}
        self.shard_api._build_pool()

    def get_pipeline(self, key):
        name = self.shard_api.get_server_name(key)
        if name not in self.pipelines:
            self.pipelines[name] = self.shard_api.connections[name].pipeline()
        return self.pipelines[name]

    def __record_index(self, pipeline):
        if pipeline not in self.__indexes:
            self.__indexes[pipeline] = [self.__counter]
        else:
            self.__indexes[pipeline].append(self.__counter)
        self.__counter += 1

    def __wrap(self, method, *args, **kwargs):
        try:
            key = args[0]
            assert isinstance(key, basestring)
        except:
            raise ValueError("method '%s' requires a key param as the first argument" % method)
        pipeline = self.get_pipeline(key)
        f = getattr(pipeline, method)
        r = f(*args, **kwargs)
        self.__record_index(pipeline)
        return r

    def __wrap_eval(self, method, script_or_sha, numkeys, *keys_and_args):
        if numkeys != 1:
            raise NotImplementedError("The key must be single string;mutiple keys cannot be sharded")
        key = keys_and_args[0]
        pipeline = self.get_pipeline(key)
        f = getattr(pipeline, method)
        r = f(script_or_sha, numkeys, *keys_and_args)
        self.__record_index(pipeline)
        return r

    def __wrap_tag(self, method, *args, **kwargs):
        key = args[0]
        if isinstance(key, basestring) and '{' in key:
            pipeline = self.get_pipeline(key)
        elif isinstance(key, list) and '{' in key[0]:
            pipeline = self.get_pipeline(key[0])
        else:
            raise ValueError("method '%s' requires tag key params as its arguments" % method)
        method = method.lstrip("tag_")
        f = getattr(pipeline, method)
        r = f(*args, **kwargs)
        self.__record_index(pipeline)
        return r

    def execute(self):
        results = []

        # Pipeline concurrently
        values = self.shard_api.pool.map(self.__unit_execute, dictvalues(self.pipelines))
        for v in values:
            results.extend(v)

        self.__counter = 0
        self.__indexes = {}

        results.sort(key=lambda x: x[0])
        results = [r[1] for r in results]
        return results

    def __unit_execute(self, pipeline):
        result = pipeline.execute()
        return zip(self.__indexes[pipeline], result)

    def __getattr__(self, method):
        if method in SHARD_METHODS:
            return functools.partial(self.__wrap, method)
        elif method in ('eval', 'evalsha'):
            return functools.partial(self.__wrap_eval, method)
        elif method.startswith("tag_"):
            return functools.partial(self.__wrap_tag, method)
        else:
            raise NotImplementedError(
                "method '%s' cannot be pipelined" % method)

########NEW FILE########
__FILENAME__ = shard
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import functools
import redis
from multiprocessing.dummy import Pool as ThreadPool

from redis.client import Lock

from .hashring import HashRing
from .pipeline import Pipeline
from .helpers import format_config
from .commands import SHARD_METHODS
from ._compat import basestring, iteritems

_findhash = re.compile('.*\{(.*)\}.*', re.I)


def list_or_args(keys, args):
    # returns a single list combining keys and args
    try:
        iter(keys)
        # a string can be iterated, but indicates
        # keys wasn't passed as a list
        if isinstance(keys, basestring):
            keys = [keys]
    except TypeError:
        keys = [keys]
    if args:
        keys.extend(args)
    return keys


class RedisShardAPI(object):

    def __init__(self, settings=None):
        self.nodes = []
        self.connections = {}
        self.pool = None
        settings = format_config(settings)
        for server_config in settings:
            name = server_config.pop('name')
            conn = redis.Redis(**server_config)
            if name in self.connections:
                raise ValueError("server's name config must be unique")
            server_config['name'] = name
            self.connections[name] = conn
            self.nodes.append(name)
        self.ring = HashRing(self.nodes)

    def get_server_name(self, key):
        g = _findhash.match(key)
        if g is not None and len(g.groups()) > 0:
            key = g.groups()[0]
        name = self.ring.get_node(key)
        return name

    def get_server(self, key):
        name = self.get_server_name(key)
        return self.connections[name]

    def _build_pool(self):
        if self.pool is None:
            self.pool = ThreadPool(len(self.nodes))

    def __wrap(self, method, *args, **kwargs):
        try:
            key = args[0]
            assert isinstance(key, basestring)
        except:
            raise ValueError("method '%s' requires a key param as the first argument" % method)
        server = self.get_server(key)
        f = getattr(server, method)
        return f(*args, **kwargs)

    def __wrap_eval(self, method, script_or_sha, numkeys, *keys_and_args):
        if numkeys != 1:
            raise NotImplementedError("The key must be single string;mutiple keys cannot be sharded")
        key = keys_and_args[0]
        server = self.get_server(key)
        f = getattr(server, method)
        return f(script_or_sha, numkeys, *keys_and_args)

    def __wrap_tag(self, method, *args, **kwargs):
        key = args[0]
        if isinstance(key, basestring) and '{' in key:
            server = self.get_server(key)
        elif isinstance(key, list) and '{' in key[0]:
            server = self.get_server(key[0])
        else:
            raise ValueError("method '%s' requires tag key params as its arguments" % method)
        method = method.lstrip("tag_")
        f = getattr(server, method)
        return f(*args, **kwargs)

    def __getattr__(self, method):
        if method in SHARD_METHODS:
            return functools.partial(self.__wrap, method)
        elif method in ('eval', 'evalsha'):
            return functools.partial(self.__wrap_eval, method)
        elif method.startswith("tag_"):
            return functools.partial(self.__wrap_tag, method)
        else:
            raise NotImplementedError("method '%s' cannot be sharded" % method)

    #########################################
    ###  some methods implement as needed ###
    ########################################
    def brpop(self, key, timeout=0):
        if not isinstance(key, basestring):
            raise NotImplementedError("The key must be single string;mutiple keys cannot be sharded")
        server = self.get_server(key)
        return server.brpop(key, timeout)

    def blpop(self, key, timeout=0):
        if not isinstance(key, basestring):
            raise NotImplementedError("The key must be single string;mutiple keys cannot be sharded")
        server = self.get_server(key)
        return server.blpop(key, timeout)

    def keys(self, key):
        _keys = []
        for node in self.nodes:
            server = self.connections[node]
            _keys.extend(server.keys(key))
        return _keys

    def mget(self, keys, *args):
        """
        Returns a list of values ordered identically to ``keys``
        """
        args = list_or_args(keys, args)
        server_keys = {}
        ret_dict = {}
        for key in args:
            server_name = self.get_server_name(key)
            server_keys[server_name] = server_keys.get(server_name, [])
            server_keys[server_name].append(key)
        for server_name, sub_keys in iteritems(server_keys):
            values = self.connections[server_name].mget(sub_keys)
            ret_dict.update(dict(zip(sub_keys, values)))
        result = []
        for key in args:
            result.append(ret_dict.get(key, None))
        return result

    def mset(self, mapping):
        """
        Sets each key in the ``mapping`` dict to its corresponding value
        """
        servers = {}
        for key, value in mapping.items():
            server_name = self.get_server_name(key)
            servers.setdefault(server_name, [])
            servers[server_name].append((key, value))
        for name, items in servers.items():
            self.connections[name].mset(dict(items))
        return True

    def flushdb(self):
        for node in self.nodes:
            server = self.connections[node]
            server.flushdb()

    def lock(self, name, timeout=None, sleep=0.1):
        """
        Return a new Lock object using key ``name`` that mimics
        the behavior of threading.Lock.

        If specified, ``timeout`` indicates a maximum life for the lock.
        By default, it will remain locked until release() is called.

        ``sleep`` indicates the amount of time to sleep per loop iteration
        when the lock is in blocking mode and another client is currently
        holding the lock.
        """
        return Lock(self, name, timeout=timeout, sleep=sleep)

    def pipeline(self):
        return Pipeline(self)

    def script_load(self, script):
        shas = []
        for node in self.nodes:
            server = self.connections[node]
            shas.append(server.script_load(script))
        if not all(x == shas[0] for x in shas):
            raise ValueError('not all server returned same sha')
        return shas[0]

########NEW FILE########
__FILENAME__ = url
try:
    # python2
    from urllib import unquote
    from urlparse import urlparse
    from urlparse import parse_qsl
except ImportError:
    # python3
    from urllib.parse import unquote
    from urllib.parse import urlparse
    from cgi import parse_qsl  # noqa


def _parse_url(url):
    scheme = urlparse(url).scheme
    schemeless = url[len(scheme) + 3:]
    # parse with HTTP URL semantics
    parts = urlparse('http://' + schemeless)

    # The first pymongo.Connection() argument (host) can be
    # a mongodb connection URI. If this is the case, don't
    # use port but let pymongo get the port(s) from the URI instead.
    # This enables the use of replica sets and sharding.
    # See pymongo.Connection() for more info.
    port = scheme != 'mongodb' and parts.port or None
    hostname = schemeless if scheme == 'mongodb' else parts.hostname
    path = parts.path or ''
    path = path[1:] if path and path[0] == '/' else path
    return (scheme, unquote(hostname or '') or None, port,
            unquote(parts.username or '') or None,
            unquote(parts.password or '') or None,
            unquote(path or '') or None,
            dict(parse_qsl(parts.query)))


def parse_url(url):
    scheme, host, port, user, password, db, query = _parse_url(url)
    assert scheme == 'redis'
    return dict(host=host, port=port, password=password, db=db, **query)

########NEW FILE########
__FILENAME__ = _compat
"""Internal module for Python 2 backwards compatibility."""
import sys


if sys.version_info[0] < 3:
    from urlparse import urlparse
    from itertools import imap, izip
    from string import letters as ascii_letters
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

    iteritems = lambda x: x.iteritems()
    dictkeys = lambda x: x.keys()
    dictvalues = lambda x: x.values()
    nativestr = lambda x: \
        x if isinstance(x, str) else x.encode('utf-8', 'replace')
    u = lambda x: x.decode()
    b = lambda x: x
    next = lambda x: x.next()
    byte_to_chr = lambda x: x
    unichr = unichr
    xrange = xrange
    basestring = basestring
    unicode = unicode
    bytes = str
    long = long
else:
    from urllib.parse import urlparse
    from io import BytesIO
    from string import ascii_letters

    iteritems = lambda x: x.items()
    dictkeys = lambda x: list(x.keys())
    dictvalues = lambda x: list(x.values())
    byte_to_chr = lambda x: chr(x)
    nativestr = lambda x: \
        x if isinstance(x, str) else x.decode('utf-8', 'replace')
    u = lambda x: x
    b = lambda x: x.encode('iso-8859-1') if not isinstance(x, bytes) else x
    next = next
    unichr = chr
    imap = map
    izip = zip
    xrange = range
    basestring = str
    unicode = str
    bytes = bytes
    long = int

try: # Python 3
    from queue import LifoQueue, Empty, Full
except ImportError:
    from Queue import Empty, Full
    try: # Python 2.6 - 2.7
        from Queue import LifoQueue
    except ImportError: # Python 2.5
        from Queue import Queue
        # From the Python 2.7 lib. Python 2.5 already extracted the core
        # methods to aid implementating different queue organisations.
        class LifoQueue(Queue):
            """Override queue methods to implement a last-in first-out queue."""

            def _init(self, maxsize):
                self.maxsize = maxsize
                self.queue = []

            def _qsize(self, len=len):
                return len(self.queue)

            def _put(self, item):
                self.queue.append(item)

            def _get(self):
                return self.queue.pop()


########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python
# -*- coding: utf-8 -*-

# you should use multiple instance of redis, here just for travis-ci tests
servers = [
    {'name': 'node1', 'host': '127.0.0.1', 'port': 6379, 'db': 0},
    {'name': 'node2', 'host': '127.0.0.1', 'port': 6379, 'db': 1},
    {'name': 'node3', 'host': '127.0.0.1', 'port': 6379, 'db': 2},
]

try:
    from .local_config import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = test_normal
#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
from redis_shard.shard import RedisShardAPI
from redis_shard._compat import b
from nose.tools import eq_
from .config import servers


class TestShard(unittest.TestCase):

    def setUp(self):
        self.client = RedisShardAPI(servers)
        self.clear_db()

    def tearDown(self):
        pass

    def clear_db(self):
        self.client.delete('testset')
        self.client.delete('testzset')
        self.client.delete('testlist')
        self.client.delete('test1')
        self.client.delete('test2')
        self.client.delete('test3')
        self.client.delete('test7')
        self.client.delete('test8')

    def test_zset(self):
        self.client.zadd('testzset', 'first', 1)
        self.client.zadd('testzset', 'second', 2)
        self.client.zrange('testzset', 0, -1) == ['first', 'second']

    def test_list(self):
        self.client.rpush('testlist', 0)
        self.client.rpush('testlist', 1)
        self.client.rpush('testlist', 2)
        self.client.rpush('testlist', 3)
        self.client.rpop('testlist')
        self.client.lpop('testlist')
        self.client.lrange('testlist', 0, -1) == ['1', '2']

    def test_mget(self):
        self.client.set('test1', 1)
        self.client.set('test2', 2)
        self.client.set('test3', 3)
        eq_(self.client.mget('test1', 'test2', 'test3'), [b('1'), b('2'), b('3')])

    def test_mset(self):
        self.client.mset({'test4': 4, 'test5': 5, 'test6': 6})
        eq_(self.client.get('test4'), b('4'))
        eq_(self.client.mget('test4', 'test5', 'test6'), [b('4'), b('5'), b('6')])

    def test_eval(self):
        self.client.eval("""
            return redis.call('set', KEYS[1], ARGV[1])
        """, 1, 'test7', '7')
        eq_(self.client.get('test7'), b('7'))

    def test_evalsha(self):
        sha = self.client.script_load("""
            return redis.call('set', KEYS[1], ARGV[1])
        """)
        eq_(self.client.evalsha(sha, 1, 'test8', b('8')), b('OK'))
        eq_(self.client.get('test8'), b('8'))

########NEW FILE########
__FILENAME__ = test_pipeline
#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import eq_
from redis_shard.shard import RedisShardAPI
from redis_shard._compat import b
from .config import servers


class TestShard(unittest.TestCase):

    def setUp(self):
        self.client = RedisShardAPI(servers)
        self.clear_db()

    def tearDown(self):
        pass

    def clear_db(self):
        self.client.delete('testset')
        self.client.delete('testzset')
        self.client.delete('testlist')

    def test_pipeline(self):
        self.client.set('test', '1')
        pipe = self.client.pipeline()
        pipe.set('test', '2')
        pipe.zadd('testzset', 'first', 1)
        pipe.zincrby('testzset', 'first')
        pipe.zadd('testzset', 'second', 2)
        pipe.execute()
        self.client.get('test') == '2'
        self.client.zscore('testzset', 'fist') == '3.0'

    def test_pipeline_script(self):
        pipe = self.client.pipeline()
        for i in range(100):
            pipe.eval("""
                redis.call('set', KEYS[1], ARGV[1])
            """, 1, 'testx%d' % i, i)
        pipe.execute()
        for i in range(100):
            eq_(self.client.get('testx%d' % i), b('%d' % i))

########NEW FILE########
__FILENAME__ = test_tag

########NEW FILE########
