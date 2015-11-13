__FILENAME__ = cache
try:
    import cPickle as pickle        # NOQA
except ImportError:
    import pickle                   # NOQA

import errno
import socket
import time

from django.core.cache.backends.memcached import MemcachedCache
from memcachepool.pool import ClientPool


DEFAULT_ITEM_SIZE = 1000 * 1000


# XXX not sure if keeping the base BaseMemcachedCache class has anymore value
class UMemcacheCache(MemcachedCache):
    "An implementation of a cache binding using python-memcached"

    _FLAG_SERIALIZED = 1
    _FLAG_INT = 1 << 1
    _FLAG_LONG = 1 << 2

    def __init__(self, server, params):
        from memcachepool import client
        kls = super(MemcachedCache, self)
        kls.__init__(server, params, library=client,
                     value_not_found_exception=ValueError)
        # see how to pass the pool value
        self.maxsize = int(params.get('MAX_POOL_SIZE', 35))
        self.blacklist_time = int(params.get('BLACKLIST_TIME', 60))
        self.socktimeout = int(params.get('SOCKET_TIMEOUT', 4))
        self.max_item_size = long(params.get('MAX_ITEM_SIZE',
                                             DEFAULT_ITEM_SIZE))
        self._pool = ClientPool(self._get_client, maxsize=self.maxsize,
                                wait_for_connection=self.socktimeout)
        self._blacklist = {}
        self.retries = int(params.get('MAX_RETRIES', 3))
        self._pick_index = 0

    def call(self, func, *args, **kwargs):
        retries = 0
        while retries < self.retries:
            with self._pool.reserve() as conn:
                try:
                    return getattr(conn, func)(*args, **kwargs)
                except Exception, exc:
                    # log
                    retries += 1
        raise exc

    # XXX using python-memcached style pickling
    # but maybe we could use something else like
    # json
    #
    # at least this makes it compatible with
    # existing data
    def serialize(self, data):
        return pickle.dumps(data, pickle.HIGHEST_PROTOCOL)

    def unserialize(self, data):
        return pickle.loads(data)

    def _get_memcache_timeout(self, timeout):
        if timeout == 0:
            return timeout
        return super(UMemcacheCache, self)._get_memcache_timeout(timeout)

    def _pick_server(self):
        # update the blacklist
        for server, age in self._blacklist.items():
            if time.time() - age > self.blacklist_time:
                del self._blacklist[server]

        # build the list of available servers
        choices = list(set(self._servers) ^ set(self._blacklist.keys()))

        if not choices:
            return None

        if self._pick_index >= len(choices):
            self._pick_index = 0

        choice = choices[self._pick_index]
        self._pick_index += 1
        return choice

    def _blacklist_server(self, server):
        self._blacklist[server] = time.time()

    def _get_client(self):
        server = self._pick_server()
        last_error = None

        def create_client(server):
            cli = self._lib.Client(server, max_item_size=self.max_item_size)
            cli.sock.settimeout(self.socktimeout)
            return cli

        while server is not None:
            cli = create_client(server)
            try:
                cli.connect()
                return cli
            except (socket.timeout, socket.error), e:
                if not isinstance(e, socket.timeout):
                    if e.errno != errno.ECONNREFUSED:
                        # unmanaged case yet
                        raise

                # well that's embarrassing, let's blacklist this one
                # and try again
                self._blacklist_server(server)
                server = self._pick_server()
                last_error = e

        if last_error is not None:
            raise last_error
        else:
            raise socket.timeout('No server left in the pool')

    def _flag_for_value(self, value):
        if isinstance(value, int):
            return self._FLAG_INT
        elif isinstance(value, long):
            return self._FLAG_LONG
        return self._FLAG_SERIALIZED

    def _value_for_flag(self, value, flag):
        if flag == self._FLAG_INT:
            return int(value)
        elif flag == self._FLAG_LONG:
            return long(value)
        return self.unserialize(value)

    def add(self, key, value, timeout=0, version=None):
        flag = self._flag_for_value(value)
        if flag == self._FLAG_SERIALIZED:
            value = self.serialize(value)
        else:
            value = '%d' % value

        key = self.make_key(key, version=version)

        return self.call('add', value, self._get_memcache_timeout(timeout),
                         flag)

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        val = self.call('get', key)

        if val is None:
            return default

        return self._value_for_flag(value=val[0], flag=val[1])

    def set(self, key, value, timeout=0, version=None):
        flag = self._flag_for_value(value)
        if flag == self._FLAG_SERIALIZED:
            value = self.serialize(value)
        else:
            value = '%d' % value
        key = self.make_key(key, version=version)
        self.call('set', key, value, self._get_memcache_timeout(timeout), flag)

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.call('delete', key)

    def get_many(self, keys, version=None):
        if keys == {}:
            return {}

        new_keys = map(lambda x: self.make_key(x, version=version), keys)

        ret = {}

        for key in new_keys:
            res = self.call('get', key)
            if res is None:
                continue
            ret[key] = res

        if ret:
            res = {}
            m = dict(zip(new_keys, keys))

            for k, v in ret.items():
                res[m[k]] = self._value_for_flag(value=v[0], flag=v[1])

            return res

        return ret

    def close(self, **kwargs):
        # XXX none of your business Django
        pass

    def incr(self, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        try:
            val = self.call('incr', key, delta)

        # python-memcache responds to incr on non-existent keys by
        # raising a ValueError, pylibmc by raising a pylibmc.NotFound
        # and Cmemcache returns None. In all cases,
        # we should raise a ValueError though.
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    def decr(self, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        try:
            val = self.call('decr', key, delta)

        # python-memcache responds to incr on non-existent keys by
        # raising a ValueError, pylibmc by raising a pylibmc.NotFound
        # and Cmemcache returns None. In all cases,
        # we should raise a ValueError though.
        except self.LibraryValueNotFoundException:
            val = None
        if val is None:
            raise ValueError("Key '%s' not found" % key)
        return val

    def set_many(self, data, timeout=0, version=None):
        safe_data = {}
        for key, value in data.items():
            key = self.make_key(key, version=version)
            flag = self._flag_for_value(value)
            if flag == self._FLAG_SERIALIZED:
                value = self.serialize(value)
            else:
                value = '%d' % value
            safe_data[key] = value

        for key, value in safe_data.items():
            self.call('set', key, value, self._get_memcache_timeout(timeout),
                      flag)

    def delete_many(self, keys, version=None):
        for key in keys:
            self.call('delete', self.make_key(key, version=version))

    def clear(self):
        self.call('flush_all')

########NEW FILE########
__FILENAME__ = client
import socket
import time
from errno import EISCONN, EINVAL
from functools import wraps

from umemcache import Client as OriginalClient
from umemcache import MemcachedError


_RETRY = ('set', 'get', 'gets', 'get_multi', 'gets_multi',
          'add', 'replace', 'append', 'prepend', 'delete',
          'cas', 'incr', 'decr', 'stats', 'flush_all',
          'version')
_ERRORS = (IOError, RuntimeError, MemcachedError, socket.error)


class Client(object):
    """On connection errors, tries to reconnect
    """
    def __init__(self, address, max_item_size=None, max_connect_retries=5,
                 reconnect_delay=.5):
        self.address = address
        self.max_item_size = max_item_size
        self._client = None
        self.funcs = []
        self._create_client()
        self.max_connect_retries = max_connect_retries
        self.reconnect_delay = reconnect_delay

    def _create_connector(self):
        if self.max_item_size is not None:
            self._client = OriginalClient(self.address, self.max_item_size)
        else:
            self._client = OriginalClient(self.address)

        self.funcs = [func for func in dir(self._client)
                      if not func.startswith('_')]

    def _create_client(self):
        reconnect = self._client is not None

        if reconnect:
            try:
                self._client.close()
            except Exception:
                pass

        self._create_connector()

        if reconnect:
            retries = 0
            delay = self.reconnect_delay
            while retries < self.max_connect_retries:
                try:
                    self._client.connect()
                except socket.error, exc:
                    if exc.errno == EISCONN:
                        return   # we're good
                    if exc.errno == EINVAL:
                        # we're doomed, retry
                        self._create_connector()

                    time.sleep(delay)
                    retries += 1
                    delay *= 2      # growing the delay

            raise exc

    def _with_retry(self, func):
        @wraps(func)
        def __with_retry(*args, **kw):
            retries = 0
            delay = self.reconnect_delay
            current_func = func

            while retries < self.max_connect_retries:
                try:
                    return current_func(*args, **kw)
                except _ERRORS, exc:
                    self._create_client()
                    current_func = getattr(self._client, func.__name__)
                    time.sleep(delay)
                    retries += 1
                    delay *= 3      # growing the delay

            raise exc
        return __with_retry

    def __getattr__(self, name):
        if not name in self.funcs:
            return self.__dict__[name]

        original = getattr(self._client, name)

        if name in _RETRY:
            return self._with_retry(original)

        return original

########NEW FILE########
__FILENAME__ = pool
import Queue
import time
import contextlib
import sys

# Sentinel used to mark an empty slot in the MCClientPool queue.
# Using sys.maxint as the timestamp ensures that empty slots will always
# sort *after* live connection objects in the queue.
EMPTY_SLOT = (sys.maxint, None)


class ClientPool(object):

    def __init__(self, factory, maxsize=None, timeout=60,
                 wait_for_connection=None):
        self.factory = factory
        self.maxsize = maxsize
        self.timeout = timeout
        self.clients = Queue.PriorityQueue(maxsize)
        self.wait_for_connection = wait_for_connection
        # If there is a maxsize, prime the queue with empty slots.
        if maxsize is not None:
            for _ in xrange(maxsize):
                self.clients.put(EMPTY_SLOT)

    @contextlib.contextmanager
    def reserve(self):
        """Context-manager to obtain a Client object from the pool."""
        ts, client = self._checkout_connection()
        try:
            yield client
        finally:
            self._checkin_connection(ts, client)

    def _checkout_connection(self):
        # If there's no maxsize, no need to block waiting for a connection.
        blocking = self.maxsize is not None
        # Loop until we get a non-stale connection, or we create a new one.
        while True:
            try:
                ts, client = self.clients.get(blocking,
                                              self.wait_for_connection)
            except Queue.Empty:
                if blocking:
                    #timeout
                    raise Exception("No connections available in the pool")
                else:
                    # No maxsize and no free connections, create a new one.
                    # XXX TODO: we should be using a monotonic clock here.
                    now = int(time.time())
                    return now, self.factory()
            else:
                now = int(time.time())
                # If we got an empty slot placeholder, create a new connection.
                if client is None:
                    try:
                        return now, self.factory()
                    except Exception, e:
                        if self.maxsize is not None:
                            # return slot to queue
                            self.clients.put(EMPTY_SLOT)
                        raise e
                # If the connection is not stale, go ahead and use it.
                if ts + self.timeout > now:
                    return ts, client
                # Otherwise, the connection is stale.
                # Close it, push an empty slot onto the queue, and retry.
                client.disconnect()
                self.clients.put(EMPTY_SLOT)
                continue

    def _checkin_connection(self, ts, client):
        """Return a connection to the pool."""
        # If the connection is now stale, don't return it to the pool.
        # Push an empty slot instead so that it will be refreshed when needed.
        now = int(time.time())
        if ts + self.timeout > now:
            self.clients.put((ts, client))
        else:
            if self.maxsize is not None:
                self.clients.put(EMPTY_SLOT)

########NEW FILE########
__FILENAME__ = settings
ok = 1
SECRET_KEY = 'secret'

########NEW FILE########
__FILENAME__ = test_cache
import socket
import time
from unittest import TestCase


class TestCache(TestCase):

    def test_pool(self):
        from memcachepool.cache import UMemcacheCache

        # creating the cache class
        cache = UMemcacheCache('127.0.0.1:11211', {})

        # simple calls
        cache.set('a', '1')
        self.assertEqual(cache.get('a'), '1')

        # should support any type and deal with serialization
        # like python-memcached does
        cache.set('a', 1)
        self.assertEqual(cache.get('a'), 1)
        cache.delete('a')
        self.assertEqual(cache.get('a'), None)

    def test_many(self):
        # make sure all the 'many' APIs work
        from memcachepool.cache import UMemcacheCache

        # creating the cache class
        cache = UMemcacheCache('127.0.0.1:11211', {})

        cache.set_many({'a': 1, 'b': 2})

        res = cache.get_many(['a', 'b']).values()
        self.assertTrue(1 in res)
        self.assertTrue(2 in res)

        cache.delete_many(['a', 'b'])
        self.assertEqual(cache.get_many(['a', 'b']), {})

    def test_incr_decr(self):
        # Testing incr and decr operations
        from memcachepool.cache import UMemcacheCache

        # creating the cache class
        cache = UMemcacheCache('127.0.0.1:11211', {})
        cache.set('a', 1)
        cache.incr('a', 1)
        self.assertEquals(cache.get('a'), 2)
        cache.decr('a', 1)
        self.assertEquals(cache.get('a'), 1)

    def test_types(self):
        # Testing if correct types are returned
        from memcachepool.cache import UMemcacheCache

        # creating the cache class
        cache = UMemcacheCache('127.0.0.1:11211', {})
        cache.set('a', int(1))
        self.assertEquals(cache.get('a'), 1)
        self.assertTrue(isinstance(cache.get('a'), int))

        cache.set('a', long(1))
        self.assertEquals(cache.get('a'), 1)
        self.assertTrue(isinstance(cache.get('a'), long))

    def test_loadbalance(self):
        from memcachepool.cache import UMemcacheCache

        # creating the cache class with two backends (one is off)
        params = {'SOCKET_TIMEOUT': 1, 'BLACKLIST_TIME': 1}
        cache = UMemcacheCache('127.0.0.1:11214;127.0.0.2:11213', params)

        # the load balancer should blacklist both IPs.
        # and return an error
        self.assertRaises(socket.error, cache.set, 'a', '1')
        self.assertTrue(len(cache._blacklist), 2)

        # wait for two seconds.
        time.sleep(1.1)

        # calling _pick_server should purge the blacklist
        cache._pick_server()
        self.assertEqual(len(cache._blacklist), 0)

########NEW FILE########
