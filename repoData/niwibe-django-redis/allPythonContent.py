__FILENAME__ = cache
# -*- coding: utf-8 -*-

import functools,warnings

from django.conf import settings
from django.core.cache.backends.base import BaseCache

from .util import load_class
from .exceptions import ConnectionInterrupted


DJANGO_REDIS_IGNORE_EXCEPTIONS = getattr(settings, "DJANGO_REDIS_IGNORE_EXCEPTIONS", False)


def omit_exception(method):
    """
    Simple decorator that intercepts connection
    errors and ignores these if settings specify this.

    Note: this doesn't handle the `default` argument in .get().
    """

    @functools.wraps(method)
    def _decorator(self, *args, **kwargs):
        if self._ignore_exceptions:
            try:
                return method(self, *args, **kwargs)
            except ConnectionInterrupted:
                return None
        else:
            return method(self, *args, **kwargs)

    return _decorator


class RedisCache(BaseCache):
    def __init__(self, server, params):
        super(RedisCache, self).__init__(params)
        self._server = server
        self._params = params

        options = params.get("OPTIONS", {})
        self._client_cls = options.get("CLIENT_CLASS", "redis_cache.client.DefaultClient")
        self._client_cls = load_class(self._client_cls)
        self._client = None

        self._ignore_exceptions = options.get("IGNORE_EXCEPTIONS", DJANGO_REDIS_IGNORE_EXCEPTIONS)

    @property
    def client(self):
        """
        Lazy client connection property.
        """
        if self._client is None:
            self._client = self._client_cls(self._server, self._params, self)
        return self._client

    @property
    def raw_client(self):
        """
        Return a raw redis client (connection). Not all
        pluggable clients supports this feature. If not supports
        this raises NotImplementedError
        """
        warnings.warn("raw_client is deprecated. use self.client.get_client instead",
                                  DeprecationWarning, stacklevel=2)
        return self.client.get_client(write=True)

    @omit_exception
    def set(self, *args, **kwargs):
        return self.client.set(*args, **kwargs)

    @omit_exception
    def incr_version(self, *args, **kwargs):
        return self.client.incr_version(*args, **kwargs)

    @omit_exception
    def add(self, *args, **kwargs):
        return self.client.add(*args, **kwargs)

    @omit_exception
    def get(self, key, default=None, version=None, client=None):
        try:
            return self.client.get(key, default=default, version=version,
                                   client=client)
        except ConnectionInterrupted:
            if DJANGO_REDIS_IGNORE_EXCEPTIONS:
                return default
            raise

    @omit_exception
    def delete(self, *args, **kwargs):
        return self.client.delete(*args, **kwargs)

    @omit_exception
    def delete_pattern(self, *args, **kwargs):
        return self.client.delete_pattern(*args, **kwargs)

    @omit_exception
    def delete_many(self, *args, **kwargs):
        return self.client.delete_many(*args, **kwargs)

    @omit_exception
    def clear(self):
        return self.client.clear()

    @omit_exception
    def get_many(self, *args, **kwargs):
        return self.client.get_many(*args, **kwargs)

    @omit_exception
    def set_many(self, *args, **kwargs):
        return self.client.set_many(*args, **kwargs)

    @omit_exception
    def incr(self, *args, **kwargs):
        return self.client.incr(*args, **kwargs)

    @omit_exception
    def decr(self, *args, **kwargs):
        return self.client.decr(*args, **kwargs)

    @omit_exception
    def has_key(self, *args, **kwargs):
        return self.client.has_key(*args, **kwargs)

    @omit_exception
    def keys(self, *args, **kwargs):
        return self.client.keys(*args, **kwargs)

    @omit_exception
    def iter_keys(self, *args, **kwargs):
        return self.client.iter_keys(*args, **kwargs)

    @omit_exception
    def ttl(self, *args, **kwargs):
        return self.client.ttl(*args, **kwargs)

    @omit_exception
    def close(self, **kwargs):
        self.client.close(**kwargs)

########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

# Import the fastest implementation of
# pickle package. This should be removed
# when python3 come the unique supported
# python version
try:
    import cPickle as pickle
except ImportError:
    import pickle

import random
import warnings

try:
    from django.utils.encoding import smart_bytes
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_str as smart_bytes
    from django.utils.encoding import smart_unicode as smart_text

from django.conf import settings
from django.core.cache.backends.base import get_key_func
from django.core.exceptions import ImproperlyConfigured
from django.utils.datastructures import SortedDict

try:
    from django.core.cache.backends.base import DEFAULT_TIMEOUT
except ImportError:
    DEFAULT_TIMEOUT = object()

from redis.exceptions import ConnectionError
from redis.exceptions import ResponseError

from redis_cache.util import CacheKey, integer_types
from redis_cache.exceptions import ConnectionInterrupted
from redis_cache import pool


class DefaultClient(object):
    def __init__(self, server, params, backend):
        self._pickle_version = -1
        self._backend = backend
        self._server = server
        self._params = params

        self.reverse_key = get_key_func(params.get('REVERSE_KEY_FUNCTION') or 'redis_cache.util.default_reverse_key')

        if not self._server:
            raise ImproperlyConfigured("Missing connections string")

        if not isinstance(self._server, (list, tuple, set)):
            self._server = self._server.split(",")

        self._clients = [None] * len(self._server)
        self._options = params.get('OPTIONS', {})

        self.setup_pickle_version()
        self.connection_factory = pool.get_connection_factory(options=self._options)

    def __contains__(self, key):
        return self.has_key(key)

    def get_next_client_index(self, write=True):
        """
        Return a next index for read client.
        This function implements a default behavior for
        get a next read client for master-slave setup.

        Overwrite this function if you want a specific
        behavior.
        """
        if write or len(self._server) == 1:
            return 0

        return random.randint(1, len(self._server) - 1)

    def get_client(self, write=True):
        """
        Method used for obtain a raw redis client.

        This function is used by almost all cache backend
        operations for obtain a native redis client/connection
        instance.
        """
        index = self.get_next_client_index(write=write)

        if self._clients[index] is None:
            self._clients[index] = self.connect(index)

        return self._clients[index]

    def parse_connection_string(self, constring):
        """
        Method that parse a connection string.
        """
        try:
            host, port, db = constring.split(":")
            port = port if host == "unix" else int(port)
            db = int(db)
            return host, port, db
        except (ValueError, TypeError):
            raise ImproperlyConfigured("Incorrect format '%s'" % (constring))

    def connect(self, index=0):
        """
        Given a connection index, returns a new raw redis client/connection
        instance. Index is used for master/slave setups and indicates that
        connection string should be used. In normal setups, index is 0.
        """
        host, port, db = self.parse_connection_string(self._server[index])
        return self.connection_factory.connect(host, port, db)

    def setup_pickle_version(self):
        if "PICKLE_VERSION" in self._options:
            try:
                self._pickle_version = int(self._options['PICKLE_VERSION'])
            except (ValueError, TypeError):
                raise ImproperlyConfigured("PICKLE_VERSION value must be an integer")

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, client=None, nx=False):
        """
        Persist a value to the cache, and set an optional expiration time.
        Also supports optional nx parameter. If set to True - will use redis setnx instead of set.
        """

        if not client:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)
        value = self.pickle(value)

        if timeout is True:
            warnings.warn("Using True as timeout value, is now deprecated.", DeprecationWarning)
            timeout = self._backend.default_timeout

        if timeout == DEFAULT_TIMEOUT:
            timeout = self._backend.default_timeout

        try:
            if nx:
                res = client.setnx(key, value)
                if res and timeout is not None and timeout != 0:
                    return client.expire(key, int(timeout))
                return res
            else:
                if timeout is not None:
                    if timeout > 0:
                        return client.setex(key, value, int(timeout))
                    elif timeout < 0:
                        # redis doesn't support negative timeouts in setex
                        # so it seems that it's better to just delete the key
                        # than to set it and than expire in a pipeline
                        return self.delete(key, client=client)

                return client.set(key, value)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def incr_version(self, key, delta=1, version=None, client=None):
        """
        Adds delta to the cache version for the supplied key. Returns the
        new version.
        """

        if client is None:
            client = self.get_client(write=True)

        if version is None:
            version = self._backend.version

        old_key = self.make_key(key, version)
        value = self.get(old_key, version=version, client=client)

        try:
            ttl = client.ttl(old_key)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

        if value is None:
            raise ValueError("Key '%s' not found" % key)

        if isinstance(key, CacheKey):
            new_key = self.make_key(key.original_key(), version=version + delta)
        else:
            new_key = self.make_key(key, version=version + delta)

        self.set(new_key, value, timeout=ttl, client=client)
        self.delete(old_key, client=client)
        return version + delta

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, client=None):
        """
        Add a value to the cache, failing if the key already exists.

        Returns ``True`` if the object was added, ``False`` if not.
        """
        return self.set(key, value, timeout, client=client, nx=True)

    def get(self, key, default=None, version=None, client=None):
        """
        Retrieve a value from the cache.

        Returns unpickled value if key is found, the default if not.
        """
        if client is None:
            client = self.get_client(write=False)

        key = self.make_key(key, version=version)

        try:
            value = client.get(key)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

        if value is None:
            return default

        return self.unpickle(value)

    def delete(self, key, version=None, client=None):
        """
        Remove a key from the cache.
        """
        if client is None:
            client = self.get_client(write=True)

        try:
            return client.delete(self.make_key(key, version=version))
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def delete_pattern(self, pattern, version=None, client=None):
        """
        Remove all keys matching pattern.
        """

        if client is None:
            client = self.get_client(write=True)

        pattern = self.make_key(pattern, version=version)
        try:
            keys = client.keys(pattern)

            if keys:
                return client.delete(*keys)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def delete_many(self, keys, version=None, client=None):
        """
        Remove multiple keys at once.
        """

        if client is None:
            client = self.get_client(write=True)

        if not keys:
            return

        keys = [self.make_key(k, version=version) for k in keys]
        try:
            return client.delete(*keys)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def clear(self, client=None):
        """
        Flush all cache keys.
        """
        if client is None:
            client = self.get_client(write=True)

        client.flushdb()

    @staticmethod
    def unpickle(value):
        """
        Unpickles the given value.
        """
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = smart_bytes(value)
            value = pickle.loads(value)
        return value

    def pickle(self, value):
        """
        Pickle the given value.
        """

        if isinstance(value, bool) or not isinstance(value, integer_types):
            return pickle.dumps(value, self._pickle_version)

        return value

    def get_many(self, keys, version=None, client=None):
        """
        Retrieve many keys.
        """

        if client is None:
            client = self.get_client(write=False)

        if not keys:
            return {}

        recovered_data = SortedDict()

        new_keys = [self.make_key(k, version=version) for k in keys]
        map_keys = dict(zip(new_keys, keys))

        try:
            results = client.mget(*new_keys)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

        for key, value in zip(new_keys, results):
            if value is None:
                continue
            recovered_data[map_keys[key]] = self.unpickle(value)
        return recovered_data

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None, client=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        if client is None:
            client = self.get_client(write=True)

        try:
            pipeline = client.pipeline()
            for key, value in data.items():
                self.set(key, value, timeout, version=version, client=pipeline)
            pipeline.execute()
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def _incr(self, key, delta=1, version=None, client=None):
        if client is None:
            client = self.get_client(write=True)

        key = self.make_key(key, version=version)

        try:
            if not client.exists(key):
                raise ValueError("Key '%s' not found" % key)

            try:
                value = client.incr(key, delta)
            except ResponseError:
                # if cached value or total value is greater than 64 bit signed
                # integer.
                # elif int is pickled. so redis sees the data as string.
                # In this situations redis will throw ResponseError

                # try to keep TTL of key
                timeout = client.ttl(key)
                value = self.get(key, version=version, client=client) + delta
                self.set(key, value, version=version, timeout=timeout,
                         client=client)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

        return value

    def incr(self, key, delta=1, version=None, client=None):
        """
        Add delta to value in the cache. If the key does not exist, raise a
        ValueError exception.
        """
        return self._incr(key=key, delta=delta, version=version, client=client)

    def decr(self, key, delta=1, version=None, client=None):
        """
        Decreace delta to value in the cache. If the key does not exist, raise a
        ValueError exception.
        """
        return self._incr(key=key, delta=-delta, version=version,
                          client=client)

    def ttl(self, key, version=None, client=None):
        """
        Executes TTL redis command and return the "time-to-live" of specified key.
        If key is a non volatile key, it returns None.
        """
        if client is None:
            client = self.get_client(write=False)

        key = self.make_key(key, version=version)
        if not client.exists(key):
            return 0
        return client.ttl(key)

    def has_key(self, key, version=None, client=None):
        """
        Test if key exists.
        """

        if client is None:
            client = self.get_client(write=False)

        key = self.make_key(key, version=version)
        try:
            return client.exists(key)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def iter_keys(self, search, itersize=None, client=None, version=None):
        """
        Same as keys, but uses redis >= 2.8 cursors
        for make memory efficient keys iteration.
        """

        if client is None:
            client = self.get_client(write=False)

        pattern = self.make_key(search, version=version)
        cursor = b"0"

        while True:
            cursor, data = client.scan(cursor, match=pattern, count=itersize)

            for item in data:
                item = smart_text(item)
                yield self.reverse_key(item)

            if cursor == b"0":
                break

    def keys(self, search, version=None, client=None):
        """
        Execute KEYS command and return matched results.
        Warning: this can return huge number of results, in
        this case, it strongly recommended use iter_keys
        for it.
        """

        if client is None:
            client = self.get_client(write=False)

        pattern = self.make_key(search, version=version)
        try:
            encoding_map = [smart_text(k) for k in client.keys(pattern)]
            return [self.reverse_key(k) for k in encoding_map]
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def make_key(self, key, version=None):
        if isinstance(key, CacheKey):
            return key
        return CacheKey(self._backend.make_key(key, version))

    def close(self, **kwargs):
        if getattr(settings, "DJANGO_REDIS_CLOSE_CONNECTION", False):
            for c in self.client.connection_pool._available_connections:
                c.disconnect()
            del self._client

########NEW FILE########
__FILENAME__ = experimental
# -*- coding: utf-8 -*-

from django.conf import settings
try:
    from django.utils.timezone import now as datetime_now
    assert datetime_now
except ImportError:
    import datetime
    datetime_now = datetime.datetime.now
from .default import DefaultClient
from ..exceptions import ConnectionInterrumped
import functools


def auto_failover(method):
    """
    Simple decorator that intercepts connection
    errors and ignores these if settings specify this.
    """

    @functools.wraps(method)
    def _decorator(self, *args, **kwargs):
        if self._in_fallback:
            pass_seconds = (datetime_now() - self._in_fallback_date).total_seconds()
            if pass_seconds > self._options.get("FAILOVER_TIME", 30):
                print("Go to default connection")
                self._client = self._old_client

                self._in_fallback = False
                self._in_fallback_date = None
                del self.fallback_client
            else:
                print("Mantain fallback connection")

        try:
            print("Executing {0}".format(method.__name__))
            return method(self, *args, **kwargs)
        except ConnectionInterrumped:
            if self._fallback and not self._in_fallback:
                print("raised ConnectionInterrumped")
                print("Switching to fallback conection")
                self._old_client = self._client
                self._client = self.fallback_client

                self._in_fallback = True
                self._in_fallback_date = timezone.now()

            return method(self, *args, **kwargs)
    return _decorator


class SimpleFailoverClient(DefaultClient):
    _in_fallback_date = None
    _in_fallback = False

    @property
    def fallback_client(self):
        if hasattr(self, "_fallback_client"):
            return self._fallback_client

        _fallback_client = self._connect(*self._fallback_params)
        self._fallback_client = _fallback_client
        return _fallback_client

    @fallback_client.deleter
    def fallback_client(self):
        if hasattr(self, "_fallback_client"):
            del self._fallback_client

    def connect(self):
        if "/" in self._server:
            self._server, self._fallback = [x.strip() for x in self._server.split("/", 1)]

        host, port, db = self.parse_connection_string(self._server)

        # Check syntax of connection string.
        self._fallback_params = self.parse_connection_string(self._fallback)

        connection = self._connect(host, port, db)
        return connection

    @auto_failover
    def set(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).set(*args, **kwargs)

    @auto_failover
    def incr_version(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).incr_version(*args, **kwargs)

    @auto_failover
    def add(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).add(*args, **kwargs)

    @auto_failover
    def get(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).get(*args, **kwargs)

    @auto_failover
    def delete(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).delete(*args, **kwargs)

    @auto_failover
    def delete_pattern(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).delete_pattern(*args, **kwargs)

    @auto_failover
    def delete_many(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).delete_many(*args, **kwargs)

    @auto_failover
    def clear(self):
        return super(SimpleFailoverClient, self).clear()

    @auto_failover
    def get_many(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).get_many(*args, **kwargs)

    @auto_failover
    def set_many(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).set_many(*args, **kwargs)

    @auto_failover
    def incr(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).incr(*args, **kwargs)

    @auto_failover
    def decr(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).decr(*args, **kwargs)

    @auto_failover
    def has_key(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).has_key(*args, **kwargs)

    @auto_failover
    def keys(self, *args, **kwargs):
        return super(SimpleFailoverClient, self).keys(*args, **kwargs)

    @auto_failover
    def close(self, **kwargs):
        super(SimpleFailoverClient, self).close(**kwargs)

########NEW FILE########
__FILENAME__ = herd
# -*- coding: utf-8 -*-

import random
import time
import warnings

from redis.exceptions import ConnectionError

from django.conf import settings
from django.utils.datastructures import SortedDict

from .default import DEFAULT_TIMEOUT, DefaultClient
from ..exceptions import ConnectionInterrupted


class Marker(object):
    """
    Dummy class for use as
    marker for herded keys.
    """
    pass


CACHE_HERD_TIMEOUT = getattr(settings, 'CACHE_HERD_TIMEOUT', 60)


def _is_expired(x):
    if x >= CACHE_HERD_TIMEOUT:
        return True
    val = x + random.randint(1, CACHE_HERD_TIMEOUT)

    if val >= CACHE_HERD_TIMEOUT:
        return True
    return False


class HerdClient(DefaultClient):
    def __init__(self, *args, **kwargs):
        self._marker = Marker()
        super(HerdClient, self).__init__(*args, **kwargs)

    def _pack(self, value, timeout):
        herd_timeout = ((timeout or self._backend.default_timeout)
                        + int(time.time()))
        return (self._marker, value, herd_timeout)

    def _unpack(self, value):
        try:
            marker, unpacked, herd_timeout = value
        except (ValueError, TypeError):
            return value, False

        if not isinstance(marker, Marker):
            return value, False

        now = int(time.time())
        if herd_timeout < now:
            x = now - herd_timeout
            return unpacked, _is_expired(x)

        return unpacked, False

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None,
            client=None, nx=False):

        if timeout == 0 or timeout is None:
            return super(HerdClient, self).set(key, value, timeout=timeout,
                                               version=version, client=client,
                                               nx=nx)
        if timeout is True:
            warnings.warn("Using True as timeout value, is now deprecated.", DeprecationWarning)
            timeout = self._backend.default_timeout

        if timeout == DEFAULT_TIMEOUT:
            timeout = self._backend.default_timeout

        packed = self._pack(value, timeout)
        real_timeout = (timeout + CACHE_HERD_TIMEOUT)

        return super(HerdClient, self).set(key, packed, timeout=real_timeout,
                                           version=version, client=client,
                                           nx=nx)

    def get(self, key, default=None, version=None, client=None):
        packed = super(HerdClient, self).get(key, default=default,
                                             version=version, client=client)
        val, refresh = self._unpack(packed)

        if refresh:
            return default

        return val

    def get_many(self, keys, version=None, client=None):
        if client is None:
            client = self.get_client(write=False)

        if not keys:
            return {}

        recovered_data = SortedDict()

        new_keys = [self.make_key(key, version=version) for key in keys]
        map_keys = dict(zip(new_keys, keys))

        try:
            results = client.mget(*new_keys)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

        for key, value in zip(new_keys, results):
            if value is None:
                continue

            val, refresh = self._unpack(self.unpickle(value))
            recovered_data[map_keys[key]] = None if refresh else val

        return recovered_data

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None, client=None,
                 herd=True):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        if client is None:
            client = self.get_client(write=True)

        set_function = self.set if herd else super(HerdClient, self).set

        try:
            pipeline = client.pipeline()
            for key, value in data.items():
                set_function(key, value, timeout, version=version, client=pipeline)
            pipeline.execute()
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def incr(self, *args, **kwargs):
        raise NotImplementedError()

    def decr(self, *args, **kwargs):
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = sentinel
# -*- coding: utf-8 -*-

import functools
import random

from django.conf import settings

from redis import Redis
from redis.sentinel import Sentinel
from redis.connection import Connection

from .default import DefaultClient
from ..exceptions import ConnectionInterrupted


class SentinelClient(DefaultClient):
    def __init__(self, server, params, backend):
        """
        Slightly different logic than connection to multiple Redis servers. Reserve only one write and read
        descriptors, as they will be closed on exit anyway.
        """
        super(SentinelClient, self).__init__(server, params, backend)
        self._client_write = None
        self._client_read = None
        self._connection_string = server

    def parse_connection_string(self, constring):
        """
        Parse connection string in format:
            master_name/sentinel_server:port,sentinel_server:port/db_id
        Returns master name, list of tuples with pair (host, port) and db_id
        """
        try:
            connection_params = constring.split('/')
            master_name = connection_params[0]
            servers = [host_port.split(':') for host_port in connection_params[1].split(',')]
            sentinel_hosts = [(host, int(port)) for host, port in servers]
            db = connection_params[2]
        except (ValueError, TypeError):
            raise ImproperlyConfigured("Incorrect format '%s'" % (constring))

        return master_name, sentinel_hosts, db

    def get_client(self, write=True):
        if write:
            if self._client_write is None:
                self._client_write = self.connect(0, write)

            return self._client_write

        if self._client_read is None:
            self._client_read = self.connect(0, write)

        return self._client_read

    def connect(self, index=0, write=True):
        """
        Creates a redis connection with connection pool.
        """
        master_name, sentinel_hosts, db = self.parse_connection_string(self._connection_string)

        sentinel_timeout = self._options.get('SENTINEL_TIMEOUT', 1)
        sentinel = Sentinel(sentinel_hosts, socket_timeout=sentinel_timeout)

        if write:
            host, port = sentinel.discover_master(master_name)
        else:
            host, port = random.choice([sentinel.discover_master(master_name)] + sentinel.discover_slaves(master_name))

        return self.connection_factory.connect(host, port, db)

    def close(self, **kwargs):
        """
        Closing old connections, as master may change in time of inactivity.
        """
        del(self._client_write)
        del(self._client_read)
        self._client_write = None
        self._client_read = None

########NEW FILE########
__FILENAME__ = sharded
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import re

from redis.exceptions import ConnectionError

from django.conf import settings
from django.utils.datastructures import SortedDict

try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

from ..hash_ring import HashRing
from ..exceptions import ConnectionInterrupted
from ..util import CacheKey
from .default import DefaultClient, DEFAULT_TIMEOUT


class ShardClient(DefaultClient):
    _findhash = re.compile('.*\{(.*)\}.*', re.I)

    def __init__(self, *args, **kwargs):
        super(ShardClient, self).__init__(*args, **kwargs)

        if not isinstance(self._server, (list, tuple)):
            self._server = [self._server]

        self._ring = HashRing(self._server)
        self._serverdict = self.connect()

    def get_client(self, write=True):
        raise NotImplementedError

    def connect(self):
        connection_dict = {}
        for name in self._server:
            host, port, db = self.parse_connection_string(name)
            connection_dict[name] = self.connection_factory.connect(host, port, db)
        return connection_dict

    def get_server_name(self, _key):
        key = str(_key)
        g = self._findhash.match(key)
        if g is not None and len(g.groups()) > 0:
            key = g.groups()[0]
        name = self._ring.get_node(key)
        return name

    def get_server(self, key):
        name = self.get_server_name(key)
        return self._serverdict[name]

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, client=None):
        if client is None:
            key = self.make_key(key, version=version)
            client = self.get_server(key)

        return super(ShardClient, self)\
            .add(key=key, value=value, version=version, client=client, timeout=timeout)

    def get(self, key, default=None, version=None, client=None):
        if client is None:
            key = self.make_key(key, version=version)
            client = self.get_server(key)

        return super(ShardClient, self)\
            .get(key=key, default=default, version=version, client=client)

    def get_many(self, keys, version=None):
        if not keys:
            return {}

        recovered_data = SortedDict()

        new_keys = [self.make_key(key, version=version) for key in keys]
        map_keys = dict(zip(new_keys, keys))

        for key in new_keys:
            client = self.get_server(key)
            value = self.get(key=key, version=version, client=client)

            if value is None:
                continue

            recovered_data[map_keys[key]] = value
        return recovered_data

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, client=None, nx=False):
        """
        Persist a value to the cache, and set an optional expiration time.
        """
        if client is None:
            key = self.make_key(key, version=version)
            client = self.get_server(key)

        return super(ShardClient, self).set(key=key, value=value,
                                            timeout=timeout, version=version,
                                            client=client, nx=nx)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        for key, value in data.items():
            self.set(key, value, timeout, version=version)

    def has_key(self, key, version=None, client=None):
        """
        Test if key exists.
        """

        if client is None:
            key = self.make_key(key, version=version)
            client = self.get_server(key)

        key = self.make_key(key, version=version)
        try:
            return client.exists(key)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

    def delete(self, key, version=None, client=None):
        if client is None:
            key = self.make_key(key, version=version)
            client = self.get_server(key)

        return super(ShardClient, self).delete(key=key, version=version, client=client)

    def delete_many(self, keys, version=None):
        """
        Remove multiple keys at once.
        """
        res = 0
        for key in [self.make_key(k, version=version) for k in keys]:
            client = self.get_server(key)
            res += self.delete(key, client=client)
        return res

    def incr_version(self, key, delta=1, version=None, client=None):
        if client is None:
            key = self.make_key(key, version=version)
            client = self.get_server(key)

        if version is None:
            version = self._backend.version

        old_key = self.make_key(key, version)
        value = self.get(old_key, version=version, client=client)

        try:
            ttl = client.ttl(old_key)
        except ConnectionError:
            raise ConnectionInterrupted(connection=client)

        if value is None:
            raise ValueError("Key '%s' not found" % key)

        if isinstance(key, CacheKey):
            new_key = self.make_key(key.original_key(), version=version + delta)
        else:
            new_key = self.make_key(key, version=version + delta)

        self.set(new_key, value, timeout=ttl, client=self.get_server(new_key))
        self.delete(old_key, client=client)
        return version + delta

    def incr(self, key, delta=1, version=None, client=None):
        if client is None:
            key = self.make_key(key, version=version)
            client = self.get_server(key)

        return super(ShardClient, self)\
            .incr(key=key, delta=delta, version=version, client=client)

    def decr(self, key, delta=1, version=None, client=None):
        if client is None:
            key = self.make_key(key, version=version)
            client = self.get_server(key)

        return super(ShardClient, self)\
            .decr(key=key, delta=delta, version=version, client=client)

    def iter_keys(self, key, version=None):
        raise NotImplementedError("iter_keys not supported on sharded client")

    def keys(self, search, version=None):
        pattern = self.make_key(search, version=version)
        keys = []
        try:
            for server, connection in self._serverdict.items():
                keys.extend(connection.keys(pattern))
        except ConnectionError:
            # FIXME: technically all clients should be passed as `connection`.
            client = self.get_server(pattern)
            raise ConnectionInterrupted(connection=client)

        decoded_keys = (smart_text(k) for k in keys)
        return [self.reverse_key(k) for k in decoded_keys]

    def delete_pattern(self, pattern, version=None):
        """
        Remove all keys matching pattern.
        """

        pattern = self.make_key(pattern, version=version)

        keys = []
        for server, connection in self._serverdict.items():
            keys.extend(connection.keys(pattern))

        res = 0
        if keys:
            for server, connection in self._serverdict.items():
                res += connection.delete(*keys)
        return res

    def close(self, **kwargs):
        if getattr(settings, "DJANGO_REDIS_CLOSE_CONNECTION", False):
            for client in self._serverdict.values():
                for c in client.connection_pool._available_connections:
                    c.disconnect()

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-


class ConnectionInterrumped(Exception):
    """Deprecated exception name with a typo."""
    def __init__(self, connection):
        self.connection = connection


class ConnectionInterrupted(ConnectionInterrumped):
    pass

########NEW FILE########
__FILENAME__ = hash_ring
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import bisect
import hashlib


class HashRing(object):
    nodes = []

    def __init__(self, nodes=(), replicas=128):
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []

        for node in nodes:
            self.add_node(node)

    def add_node(self, node):
        self.nodes.append(node)

        for x in range(self.replicas):
            _key = "{0}:{1}".format(node, x)
            _hash = hashlib.sha256(_key.encode('utf-8')).hexdigest()

            self.ring[_hash] = node
            self.sorted_keys.append(_hash)

        self.sorted_keys.sort()

    def remove_node(self, node):
        self.nodes.remove(node)
        for x in range(self.replicas):
            _hash = hashlib.sha256("%s:%d" % (node, x)).hexdigest()
            self.ring.remove(_hash)
            self.sorted_keys.remove(_hash)

    def get_node(self, key):
        n, i = self.get_node_pos(key)
        return n

    def get_node_pos(self, key):
        if len(self.ring) == 0:
            return (None, None)

        _hash = hashlib.sha256(key.encode('utf-8')).hexdigest()
        idx = bisect.bisect(self.sorted_keys, _hash)
        idx = min(idx-1, (self.replicas * len(self.nodes))-1)
        return (self.ring[self.sorted_keys[idx]], idx)

    def iter_nodes(self, key):
        if len(self.ring) == 0: yield None, None
        node, pos = self.get_node_pos(key)
        for k in self.sorted_keys[pos:]:
            yield k, self.ring[k]

    def __call__(self, key):
        return self.get_node(key)

########NEW FILE########
__FILENAME__ = pool
# -*- coding: utf-8 -*-

from django.conf import settings

from redis import Redis
from redis.connection import Connection
from redis.connection import DefaultParser
from redis.connection import UnixDomainSocketConnection

from . import util


class ConnectionFactory(object):

    #: Store connection pool by cache backend options.
    #: _pools is a process-global, as
    #: otherwise _pools is cleared every time ConnectionFactory is instiated,
    #: as Django creates new cache client (DefaultClient) instance for every request.
    _pools = {}

    def __init__(self, options):
        pool_cls_path = options.get("CONNECTION_POOL_CLASS",
                                    "redis.connection.ConnectionPool")
        self.pool_cls = util.load_class(pool_cls_path)
        self.pool_cls_kwargs = options.get("CONNECTION_POOL_KWARGS", {})
        self.options = options

    def make_connection_params(self, host, port, db):
        """
        Given a main connection parameters, build a complete
        dict of connection parameters.
        """

        kwargs = {
            "db": db,
            "parser_class": self.get_parser_cls(),
            "password": self.options.get('PASSWORD', None),
        }

        if host == "unix":
            kwargs.update({'path': port, 'connection_class': UnixDomainSocketConnection})
        else:
            kwargs.update({'host': host, 'port': port, 'connection_class': Connection})

        if 'SOCKET_TIMEOUT' in self.options:
            timeout = self.options['SOCKET_TIMEOUT']
            assert isinstance(timeout, (int, float)), "Socket timeout should be float or integer"
            kwargs['socket_timeout'] = timeout

        return kwargs

    def connect(self, host, port, db):
        """
        Given a basic connection parameters,
        return a new connection.
        """
        params = self.make_connection_params(host, port, db)
        return self.get_connection(params)

    def get_connection(self, params):
        """
        Given a now preformated params, return a
        new connection.

        The default implementation uses a cached pools
        for create new connection.
        """
        return Redis(connection_pool=self.get_or_create_connection_pool(params))

    def get_parser_cls(self):
        cls = self.options.get('PARSER_CLASS', None)
        if cls is None:
            return DefaultParser
        return util.load_class(cls)

    def get_or_create_connection_pool(self, params):
        """
        Given a connection parameters and return a new
        or cached connection pool for them.

        Reimplement this method if you want distinct
        connection pool instance caching behavior.
        """
        key = frozenset((k, repr(v)) for (k, v) in params.items())
        if key not in self._pools:
            self._pools[key] = self.get_connection_pool(params)
        return self._pools[key]

    def get_connection_pool(self, params):
        """
        Given a connection parameters, return a new
        connection pool for them.

        Overwrite this method if you want a custom
        behavior on creating connection pool.
        """
        cp_params = dict(params)
        cp_params.update(self.pool_cls_kwargs)
        return self.pool_cls(**cp_params)


def get_connection_factory(path=None, options=None):
    if path is None:
        path = getattr(settings, "DJANGO_REDIS_CONNECTION_FACTORY",
                       "redis_cache.pool.ConnectionFactory")

    cls = util.load_class(path)
    return cls(options or {})

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
import sys

try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

try:
    from django.utils.encoding import smart_bytes
except ImportError:
    from django.utils.encoding import smart_str as smart_bytes

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.core.cache.backends.base import get_key_func

from redis import ConnectionPool as RedisConnectionPool
from redis.connection import UnixDomainSocketConnection, Connection
from redis.connection import DefaultParser

from collections import defaultdict
from django.utils.importlib import import_module

if sys.version_info[0] < 3:
    integer_types = (int, long,)
else:
    integer_types = (int,)


class CacheKey(object):
    """
    A stub string class that we can use to check if a key was created already.
    """
    def __init__(self, key):
        self._key = key

    if sys.version_info[0] < 3:
        def __str__(self):
            return smart_bytes(self._key)

        def __unicode__(self):
            return smart_text(self._key)

    else:
        def __str__(self):
            return smart_text(self._key)

    def original_key(self):
        key = self._key.rsplit(":", 1)[1]
        return key


def load_class(path):
    """
    Load class from path.
    """

    mod_name, klass_name = path.rsplit('.', 1)

    try:
        mod = import_module(mod_name)
    except AttributeError as e:
        raise ImproperlyConfigured('Error importing {0}: "{1}"'.format(mod_name, e))

    try:
        klass = getattr(mod, klass_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "{0}" does not define a "{1}" class'.format(mod_name, klass_name))

    return klass

def default_reverse_key(key):
    return key.split(':', 2)[2]

########NEW FILE########
__FILENAME__ = runtests-herd
# -*- coding: utf-8 -*-

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_sqlite_herd")
sys.path.insert(0, 'tests')


if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    args = sys.argv
    args.insert(1, "test")

    execute_from_command_line(args)

########NEW FILE########
__FILENAME__ = runtests-sharded
# -*- coding: utf-8 -*-

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_sqlite_sharding")
sys.path.insert(0, 'tests')

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    args = sys.argv
    args.insert(1, "test")

    execute_from_command_line(args)

########NEW FILE########
__FILENAME__ = runtests-unixsockets
# -*- coding: utf-8 -*-

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_sqlite_usock")
sys.path.insert(0, 'tests')


if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    args = sys.argv
    args.insert(1, "test")

    execute_from_command_line(args)

########NEW FILE########
__FILENAME__ = runtests
# -*- coding: utf-8 -*-

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_sqlite")
sys.path.insert(0, 'tests')


if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    args = sys.argv
    args.insert(1, "test")

    execute_from_command_line(args)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-



########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from django.test import TestCase

from redis_cache.hash_ring import HashRing


class Node(object):
    def __init__(self, id):
        self.id = id

    def __str__(self):
        return "node:{0}".format(self.id)

    def __repr__(self):
        return "<Node {}>".format(self.id)


class HashRingTest(TestCase):
    def setUp(self):
        self.node0 = Node(0)
        self.node1 = Node(1)
        self.node2 = Node(2)

        self.nodes = [self.node0, self.node1, self.node2]
        self.ring = HashRing(self.nodes)

    def test_hashring(self):
        ids = []

        for key in ["test{0}".format(x) for x in range(10)]:
            node = self.ring.get_node(key)
            ids.append(node.id)

        self.assertEqual(ids, [0, 2, 1, 2, 2, 2, 2, 0, 1, 1])

    def test_hashring_brute_force(self):
        for key in ("test{0}".format(x) for x in range(10000)):
            node = self.ring.get_node(key)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals, print_function

import sys
import time
import datetime

from django.conf import settings
from django.core.cache import cache, get_cache
from django.test import TestCase
import redis_cache.cache

from redis_cache.client import herd


herd.CACHE_HERD_TIMEOUT = 2

if sys.version_info[0] < 3:
    text_type = unicode
    bytes_type = str
else:
    text_type = str
    bytes_type = bytes
    long = int


def make_key(key, prefix, version):
    return "{}#{}#{}".format(prefix, version, key)

def reverse_key(key):
    return key.split("#", 2)[2]

class DjangoRedisCacheTestCustomKeyFunction(TestCase):
    def setUp(self):
        self.old_kf = settings.CACHES['default'].get('KEY_FUNCTION')
        self.old_rkf = settings.CACHES['default'].get('REVERSE_KEY_FUNCTION')
        settings.CACHES['default']['KEY_FUNCTION'] = 'redis_backend_testapp.tests.make_key'
        settings.CACHES['default']['REVERSE_KEY_FUNCTION'] = 'redis_backend_testapp.tests.reverse_key'

        self.cache = get_cache('default')
        try:
            self.cache.clear()
        except Exception:
            pass


    def test_custom_key_function(self):
        for key in ["foo-aa","foo-ab", "foo-bb","foo-bc"]:
            self.cache.set(key, "foo")

        res = self.cache.delete_pattern("*foo-a*")
        self.assertTrue(bool(res))

        keys = self.cache.keys("foo*")
        self.assertEqual(set(keys), set(["foo-bb","foo-bc"]))
        # ensure our custom function was actually called
        try:
            self.assertEqual(set(k.decode('utf-8') for k in self.cache.raw_client.keys('*')),
                set(['#1#foo-bc', '#1#foo-bb']))
        except NotImplementedError:
            # not all clients support .keys()
            pass

    def tearDown(self):
        settings.CACHES['default']['KEY_FUNCTION'] = self.old_kf
        settings.CACHES['default']['REVERSE_KEY_FUNCTION'] = self.old_rkf


class DjangoRedisCacheTests(TestCase):
    def setUp(self):
        self.cache = cache

        try:
            self.cache.clear()
        except Exception:
            pass

    def test_setnx(self):
        # we should ensure there is no test_key_nx in redis
        self.cache.delete("test_key_nx")
        res = self.cache.get("test_key_nx", None)
        self.assertEqual(res, None)

        res = self.cache.set("test_key_nx", 1, nx=True)
        self.assertTrue(res)
        # test that second set will have
        res = self.cache.set("test_key_nx", 2, nx=True)
        self.assertFalse(res)
        res = self.cache.get("test_key_nx")
        self.assertEqual(res, 1)

        self.cache.delete("test_key_nx")
        res = self.cache.get("test_key_nx", None)
        self.assertEqual(res, None)

    def test_setnx_timeout(self):
        # test that timeout still works for nx=True
        res = self.cache.set("test_key_nx", 1, timeout=2, nx=True)
        self.assertTrue(res)
        time.sleep(3)
        res = self.cache.get("test_key_nx", None)
        self.assertEqual(res, None)

        # test that timeout will not affect key, if it was there
        self.cache.set("test_key_nx", 1)
        res = self.cache.set("test_key_nx", 2, timeout=2, nx=True)
        self.assertFalse(res)
        time.sleep(3)
        res = self.cache.get("test_key_nx", None)
        self.assertEqual(res, 1)

        self.cache.delete("test_key_nx")
        res = self.cache.get("test_key_nx", None)
        self.assertEqual(res, None)

    def test_save_and_integer(self):
        self.cache.set("test_key", 2)
        res = self.cache.get("test_key", "Foo")

        self.assertIsInstance(res, int)
        self.assertEqual(res, 2)

    def test_save_string(self):
        self.cache.set("test_key", "hello")
        res = self.cache.get("test_key")

        self.assertIsInstance(res, text_type)
        self.assertEqual(res, "hello")

        self.cache.set("test_key", "2")
        res = self.cache.get("test_key")

        self.assertIsInstance(res, text_type)
        self.assertEqual(res, "2")

    def test_save_unicode(self):
        self.cache.set("test_key", "heló")
        res = self.cache.get("test_key")

        self.assertIsInstance(res, text_type)
        self.assertEqual(res, "heló")

    def test_save_dict(self):
        now_dt = datetime.datetime.now()
        test_dict = {"id":1, "date": now_dt, "name": "Foo"}

        self.cache.set("test_key", test_dict)
        res = self.cache.get("test_key")

        self.assertIsInstance(res, dict)
        self.assertEqual(res["id"], 1)
        self.assertEqual(res["name"], "Foo")
        self.assertEqual(res["date"], now_dt)

    def test_save_float(self):
        float_val = 1.345620002

        self.cache.set("test_key", float_val)
        res = self.cache.get("test_key")

        self.assertIsInstance(res, float)
        self.assertEqual(res, float_val)

    def test_timeout(self):
        self.cache.set("test_key", 222, timeout=3)
        time.sleep(4)

        res = self.cache.get("test_key", None)
        self.assertEqual(res, None)

    def test_timeout_0(self):
        self.cache.set("test_key", 222, timeout=0)
        res = self.cache.get("test_key", None)
        self.assertEqual(res, 222)

    def test_timeout_negative(self):
        self.cache.set("test_key", 222, timeout=-1)
        res = self.cache.get("test_key", None)
        self.assertIsNone(res)

        self.cache.set("test_key", 222, timeout=0)
        self.cache.set("test_key", 222, timeout=-1)
        res = self.cache.get("test_key", None)
        self.assertIsNone(res)

        # nx=True should not overwrite expire of key already in db
        self.cache.set("test_key", 222, timeout=0)
        self.cache.set("test_key", 222, timeout=-1, nx=True)
        res = self.cache.get("test_key", None)
        self.assertEqual(res, 222)

    def test_set_add(self):
        self.cache.set("add_key", "Initial value")
        self.cache.add("add_key", "New value")
        res = cache.get("add_key")

        self.assertEqual(res, "Initial value")

    def test_get_many(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.cache.set("c", 3)

        res = self.cache.get_many(["a","b","c"])
        self.assertEqual(res, {"a": 1, "b": 2, "c": 3})

    def test_get_many_unicode(self):
        self.cache.set("a", "1")
        self.cache.set("b", "2")
        self.cache.set("c", "3")

        res = self.cache.get_many(["a","b","c"])
        self.assertEqual(res, {"a": "1", "b": "2", "c": "3"})

    def test_set_many(self):
        self.cache.set_many({"a": 1, "b": 2, "c": 3})
        res = self.cache.get_many(["a", "b", "c"])
        self.assertEqual(res, {"a": 1, "b": 2, "c": 3})

    def test_delete(self):
        self.cache.set_many({"a": 1, "b": 2, "c": 3})
        res = self.cache.delete("a")
        self.assertTrue(bool(res))

        res = self.cache.get_many(["a", "b", "c"])
        self.assertEqual(res, {"b": 2, "c": 3})

        res = self.cache.delete("a")
        self.assertFalse(bool(res))

    def test_delete_many(self):
        self.cache.set_many({"a": 1, "b": 2, "c": 3})
        res = self.cache.delete_many(["a","b"])
        self.assertTrue(bool(res))

        res = self.cache.get_many(["a", "b", "c"])
        self.assertEqual(res, {"c": 3})

        res = self.cache.delete_many(["a","b"])
        self.assertFalse(bool(res))

    def test_incr(self):
        try:
            self.cache.set("num", 1)

            self.cache.incr("num")
            res = self.cache.get("num")
            self.assertEqual(res, 2)

            self.cache.incr("num", 10)
            res = self.cache.get("num")
            self.assertEqual(res, 12)

            #max 64 bit signed int
            self.cache.set("num", 9223372036854775807)

            self.cache.incr("num")
            res = self.cache.get("num")
            self.assertEqual(res, 9223372036854775808)

            self.cache.incr("num", 2)
            res = self.cache.get("num")
            self.assertEqual(res, 9223372036854775810)

            self.cache.set("num", long(3))

            self.cache.incr("num", 2)
            res = self.cache.get("num")
            self.assertEqual(res, 5)

        except NotImplementedError as e:
            print(e)

    def test_get_set_bool(self):
        self.cache.set("bool", True)
        res = self.cache.get("bool")

        self.assertIsInstance(res, bool)
        self.assertEqual(res, True)

        self.cache.set("bool", False)
        res = self.cache.get("bool")

        self.assertIsInstance(res, bool)
        self.assertEqual(res, False)

    def test_decr(self):
        try:
            self.cache.set("num", 20)

            self.cache.decr("num")
            res = self.cache.get("num")
            self.assertEqual(res, 19)

            self.cache.decr("num", 20)
            res = self.cache.get("num")
            self.assertEqual(res, -1)

            self.cache.decr("num", long(2))
            res = self.cache.get("num")
            self.assertEqual(res, -3)

            self.cache.set("num", long(20))

            self.cache.decr("num")
            res = self.cache.get("num")
            self.assertEqual(res, 19)

            #max 64 bit signed int + 1
            self.cache.set("num", 9223372036854775808)

            self.cache.decr("num")
            res = self.cache.get("num")
            self.assertEqual(res, 9223372036854775807)

            self.cache.decr("num", 2)
            res = self.cache.get("num")
            self.assertEqual(res, 9223372036854775805)
        except NotImplementedError as e:
            print(e)

    def test_version(self):
        self.cache.set("keytest", 2, version=2)
        res = self.cache.get("keytest")
        self.assertEqual(res, None)

        res = self.cache.get("keytest", version=2)
        self.assertEqual(res, 2)

    def test_incr_version(self):
        try:
            self.cache.set("keytest", 2)
            self.cache.incr_version("keytest")

            res = self.cache.get("keytest")
            self.assertEqual(res, None)

            res = self.cache.get("keytest", version=2)
            self.assertEqual(res, 2)
        except NotImplementedError as e:
            print(e)

    def test_delete_pattern(self):
        for key in ["foo-aa","foo-ab", "foo-bb","foo-bc"]:
            self.cache.set(key, "foo")

        res = self.cache.delete_pattern("*foo-a*")
        self.assertTrue(bool(res))

        keys = self.cache.keys("foo*")
        self.assertEqual(set(keys), set(["foo-bb","foo-bc"]))

        res = self.cache.delete_pattern("*foo-a*")
        self.assertFalse(bool(res))

    def test_close(self):
        cache = get_cache("default")
        cache.set("f", "1")
        cache.close()

    def test_ttl(self):
        cache = get_cache("default")
        _params = cache._params
        _is_herd = (_params["OPTIONS"]["CLIENT_CLASS"] ==
                    "redis_cache.client.HerdClient")
        _is_shard = (_params["OPTIONS"]["CLIENT_CLASS"] ==
                    "redis_cache.client.ShardClient")

        # Not supported for shard client.
        if _is_shard:
            return

        # Test ttl
        cache.set("foo", "bar", 10)
        ttl = cache.ttl("foo")

        if _is_herd:
            self.assertAlmostEqual(ttl, 12)
        else:
            self.assertAlmostEqual(ttl, 10)

        # Test ttl None
        cache.set("foo", "foo", timeout=None)
        ttl = cache.ttl("foo")
        self.assertEqual(ttl, None)

        # Test ttl with expired key
        cache.set("foo", "foo", timeout=-1)
        ttl = cache.ttl("foo")

        # Test ttl with not existent key
        ttl = cache.ttl("not-existent-key")
        self.assertEqual(ttl, 0)

    def test_iter_keys(self):
        cache = get_cache("default")
        _params = cache._params
        _is_shard = (_params["OPTIONS"]["CLIENT_CLASS"] ==
                    "redis_cache.client.ShardClient")

        if _is_shard:
            return

        cache.set("foo1", 1)
        cache.set("foo2", 1)
        cache.set("foo3", 1)

        # Test simple result
        result = set(cache.iter_keys("foo*"))
        self.assertEqual(result, set(["foo1", "foo2", "foo3"]))

        # Test limited result
        result = list(cache.iter_keys("foo*", itersize=2))
        self.assertEqual(len(result), 3)

        # Test generator object
        result = cache.iter_keys("foo*")
        self.assertNotEqual(next(result), None)

    def test_master_slave_switching(self):
        try:
            cache = get_cache("sample")
            client = cache.client
            client._server = ["foo", "bar",]
            client._clients = ["Foo", "Bar"]

            self.assertEqual(client.get_client(write=True), "Foo")
            self.assertEqual(client.get_client(write=False), "Bar")
        except NotImplementedError:
            pass


class DjangoOmitExceptionsTests(TestCase):
    def setUp(self):
        self._orig_setting = redis_cache.cache.DJANGO_REDIS_IGNORE_EXCEPTIONS
        redis_cache.cache.DJANGO_REDIS_IGNORE_EXCEPTIONS = True
        self.cache = get_cache("doesnotexist")

    def tearDown(self):
        redis_cache.cache.DJANGO_REDIS_IGNORE_EXCEPTIONS = self._orig_setting

    def test_get(self):
        self.assertIsNone(self.cache.get("key"))
        self.assertEqual(self.cache.get("key", "default"), "default")
        self.assertEqual(self.cache.get("key", default="default"), "default")


from django.contrib.sessions.backends.cache import SessionStore as CacheSession
from django.contrib.sessions.tests import SessionTestsMixin


class SessionTests(SessionTestsMixin, TestCase):
    backend = CacheSession

    def test_actual_expiry(self):
        pass

########NEW FILE########
__FILENAME__ = shell
# -*- coding: utf-8 -*-

import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_sqlite")
sys.path.insert(0, '..')

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    args = sys.argv
    args.insert(1, "shell")

    execute_from_command_line(args)

########NEW FILE########
__FILENAME__ = test_sqlite
# This is an example test settings file for use with the Django test suite.
#
# The 'sqlite3' backend requires only the ENGINE setting (an in-
# memory database will be used). All other backends will require a
# NAME and potentially authentication information. See the
# following section in the docs for more information:
#
# https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/
#
# The different databases that Django supports behave differently in certain
# situations, so it is recommended to run the test suite against as many
# database backends as possible.  You may want to create a separate settings
# file for each of the backends you test against.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    },
}

SECRET_KEY = "django_tests_secret_key"
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': [
            '127.0.0.1:6379:1',
            '127.0.0.1:6379:1',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
        }
    },
    'doesnotexist': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:56379:1',
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
        }
    },
    'sample': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:6379:1,127.0.0.1:6379:1',
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
        }
    },
}

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

INSTALLED_APPS = (
    'redis_backend_testapp',
    'hashring_test',
)

########NEW FILE########
__FILENAME__ = test_sqlite_failover
# This is an example test settings file for use with the Django test suite.
#
# The 'sqlite3' backend requires only the ENGINE setting (an in-
# memory database will be used). All other backends will require a
# NAME and potentially authentication information. See the
# following section in the docs for more information:
#
# https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/
#
# The different databases that Django supports behave differently in certain
# situations, so it is recommended to run the test suite against as many
# database backends as possible.  You may want to create a separate settings
# file for each of the backends you test against.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    },
}

SECRET_KEY = "django_tests_secret_key"
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:6379:1/127.0.0.1:6380:1',
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.SimpleFailoverClient',
        }
    },
}

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

INSTALLED_APPS = (
    'redis_backend_testapp',
    'hashring_test',
)

########NEW FILE########
__FILENAME__ = test_sqlite_herd
# This is an example test settings file for use with the Django test suite.
#
# The 'sqlite3' backend requires only the ENGINE setting (an in-
# memory database will be used). All other backends will require a
# NAME and potentially authentication information. See the
# following section in the docs for more information:
#
# https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/
#
# The different databases that Django supports behave differently in certain
# situations, so it is recommended to run the test suite against as many
# database backends as possible.  You may want to create a separate settings
# file for each of the backends you test against.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    },
}

SECRET_KEY = "django_tests_secret_key"
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': [
            '127.0.0.1:6379:5',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.HerdClient',
        }
    },
    'doesnotexist': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:56379:1',
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.HerdClient',
        }
    },
    'sample': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:6379:1,127.0.0.1:6379:1',
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.HerdClient',
        }
    },
}

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

INSTALLED_APPS = (
    'redis_backend_testapp',
    'hashring_test',
)

########NEW FILE########
__FILENAME__ = test_sqlite_sharding
# This is an example test settings file for use with the Django test suite.
#
# The 'sqlite3' backend requires only the ENGINE setting (an in-
# memory database will be used). All other backends will require a
# NAME and potentially authentication information. See the
# following section in the docs for more information:
#
# https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/
#
# The different databases that Django supports behave differently in certain
# situations, so it is recommended to run the test suite against as many
# database backends as possible.  You may want to create a separate settings
# file for each of the backends you test against.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    },
}

SECRET_KEY = "django_tests_secret_key"
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': [
            '127.0.0.1:6379:1',
            '127.0.0.1:6379:2',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.ShardClient',
        }
    },
    'doesnotexist': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': [
            '127.0.0.1:56379:1',
            '127.0.0.1:56379:2',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.ShardClient',
        }
    },
    'sample': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:6379:1,127.0.0.1:6379:1',
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.ShardClient',
        }
    },
}

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

INSTALLED_APPS = (
    'redis_backend_testapp',
    'hashring_test',
)

########NEW FILE########
__FILENAME__ = test_sqlite_usock
# This is an example test settings file for use with the Django test suite.
#
# The 'sqlite3' backend requires only the ENGINE setting (an in-
# memory database will be used). All other backends will require a
# NAME and potentially authentication information. See the
# following section in the docs for more information:
#
# https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/
#
# The different databases that Django supports behave differently in certain
# situations, so it is recommended to run the test suite against as many
# database backends as possible.  You may want to create a separate settings
# file for each of the backends you test against.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    },
}

SECRET_KEY = "django_tests_secret_key"
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = ()

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': [
            'unix:/tmp/redis.sock:1',
            'unix:/tmp/redis.sock:1',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
        }
    },
    'doesnotexist': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:56379:1',
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
        }
    },
    'sample': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:6379:1,127.0.0.1:6379:1',
        'OPTIONS': {
            'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
        }
    },
}

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

INSTALLED_APPS = (
    'redis_backend_testapp',
    'hashring_test',
)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-



########NEW FILE########
