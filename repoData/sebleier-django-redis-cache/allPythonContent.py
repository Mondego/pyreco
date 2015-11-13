__FILENAME__ = cache
from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib
from django.utils.datastructures import SortedDict
from .compat import (smart_text, smart_bytes, bytes_type,
                     python_2_unicode_compatible, DEFAULT_TIMEOUT)

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import redis
except ImportError:
    raise InvalidCacheBackendError(
        "Redis cache backend requires the 'redis-py' library")
from redis.connection import UnixDomainSocketConnection, Connection
from redis.connection import DefaultParser


@python_2_unicode_compatible
class CacheKey(object):
    """
    A stub string class that we can use to check if a key was created already.
    """
    def __init__(self, key):
        self._key = key

    def __eq__(self, other):
        return self._key == other

    def __str__(self):
        return smart_text(self._key)

    def __repr__(self):
        return repr(self._key)

    def __hash__(self):
        return hash(self._key)


class CacheConnectionPool(object):

    def __init__(self):
        self._connection_pools = {}

    def get_connection_pool(self, host='127.0.0.1', port=6379, db=1,
                            password=None, parser_class=None,
                            unix_socket_path=None, connection_pool_class=None,
                            connection_pool_class_kwargs=None):
        connection_identifier = (host, port, db, parser_class, unix_socket_path, connection_pool_class)
        if not self._connection_pools.get(connection_identifier):
            connection_class = (
                unix_socket_path and UnixDomainSocketConnection or Connection
            )
            kwargs = {
                'db': db,
                'password': password,
                'connection_class': connection_class,
                'parser_class': parser_class,
            }
            kwargs.update(connection_pool_class_kwargs)
            if unix_socket_path is None:
                kwargs.update({
                    'host': host,
                    'port': port,
                })
            else:
                kwargs['path'] = unix_socket_path
            self._connection_pools[connection_identifier] = connection_pool_class(**kwargs)
        return self._connection_pools[connection_identifier]
pool = CacheConnectionPool()


class CacheClass(BaseCache):
    def __init__(self, server, params):
        """
        Connect to Redis, and set up cache backend.
        """
        self._init(server, params)

    def _init(self, server, params):
        super(CacheClass, self).__init__(params)
        self._server = server
        self._params = params

        unix_socket_path = None
        if ':' in self.server:
            host, port = self.server.rsplit(':', 1)
            try:
                port = int(port)
            except (ValueError, TypeError):
                raise ImproperlyConfigured("port value must be an integer")
        else:
            host, port = None, None
            unix_socket_path = self.server

        kwargs = {
            'db': self.db,
            'password': self.password,
            'host': host,
            'port': port,
            'unix_socket_path': unix_socket_path,
        }

        connection_pool = pool.get_connection_pool(
            parser_class=self.parser_class,
            connection_pool_class=self.connection_pool_class,
            connection_pool_class_kwargs=self.connection_pool_class_kwargs,
            **kwargs
        )
        self._client = redis.Redis(
            connection_pool=connection_pool,
            **kwargs
        )

    @property
    def server(self):
        return self._server or "127.0.0.1:6379"

    @property
    def params(self):
        return self._params or {}

    @property
    def options(self):
        return self.params.get('OPTIONS', {})

    @property
    def connection_pool_class(self):
        cls = self.options.get('CONNECTION_POOL_CLASS', 'redis.ConnectionPool')
        mod_path, cls_name = cls.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_path)
            pool_class = getattr(mod, cls_name)
        except (AttributeError, ImportError):
            raise ImproperlyConfigured("Could not find connection pool class '%s'" % cls)
        return pool_class

    @property
    def connection_pool_class_kwargs(self):
        return self.options.get('CONNECTION_POOL_CLASS_KWARGS', {})

    @property
    def db(self):
        _db = self.params.get('db', self.options.get('DB', 1))
        try:
            _db = int(_db)
        except (ValueError, TypeError):
            raise ImproperlyConfigured("db value must be an integer")
        return _db

    @property
    def password(self):
        return self.params.get('password', self.options.get('PASSWORD', None))

    @property
    def parser_class(self):
        cls = self.options.get('PARSER_CLASS', None)
        if cls is None:
            return DefaultParser
        mod_path, cls_name = cls.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_path)
            parser_class = getattr(mod, cls_name)
        except (AttributeError, ImportError):
            raise ImproperlyConfigured("Could not find parser class '%s'" % parser_class)
        return parser_class

    def __getstate__(self):
        return {'params': self._params, 'server': self._server}

    def __setstate__(self, state):
        self._init(**state)

    def make_key(self, key, version=None):
        """
        Returns the utf-8 encoded bytestring of the given key as a CacheKey
        instance to be able to check if it was "made" before.
        """
        if not isinstance(key, CacheKey):
            key = CacheKey(key)
        return key

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Add a value to the cache, failing if the key already exists.

        Returns ``True`` if the object was added, ``False`` if not.
        """
        return self.set(key, value, timeout, _add_only=True)

    def get(self, key, default=None, version=None):
        """
        Retrieve a value from the cache.

        Returns unpickled value if key is found, the default if not.
        """
        key = self.make_key(key, version=version)
        value = self._client.get(key)
        if value is None:
            return default
        try:
            result = int(value)
        except (ValueError, TypeError):
            result = self.unpickle(value)
        return result

    def _set(self, key, value, timeout, client, _add_only=False):
        if timeout is None or timeout == 0:
            if _add_only:
                return client.setnx(key, value)
            return client.set(key, value)
        elif timeout > 0:
            if _add_only:
                added = client.setnx(key, value)
                if added:
                    client.expire(key, timeout)
                return added
            return client.setex(key, value, timeout)
        else:
            return False

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None, client=None, _add_only=False):
        """
        Persist a value to the cache, and set an optional expiration time.
        """
        if not client:
            client = self._client
        key = self.make_key(key, version=version)
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout
        if timeout is not None:
            timeout = int(timeout)

        # If ``value`` is not an int, then pickle it
        if not isinstance(value, int) or isinstance(value, bool):
            result = self._set(key, pickle.dumps(value), timeout, client, _add_only)
        else:
            result = self._set(key, value, timeout, client, _add_only)
        # result is a boolean
        return result

    def delete(self, key, version=None):
        """
        Remove a key from the cache.
        """
        self._client.delete(self.make_key(key, version=version))

    def delete_many(self, keys, version=None):
        """
        Remove multiple keys at once.
        """
        if keys:
            keys = map(lambda key: self.make_key(key, version=version), keys)
            self._client.delete(*keys)

    def clear(self):
        """
        Flush all cache keys.
        """
        # TODO : potential data loss here, should we only delete keys based on the correct version ?
        self._client.flushdb()

    def unpickle(self, value):
        """
        Unpickles the given value.
        """
        value = smart_bytes(value)
        return pickle.loads(value)

    def get_many(self, keys, version=None):
        """
        Retrieve many keys.
        """
        if not keys:
            return {}
        recovered_data = SortedDict()
        new_keys = list(map(lambda key: self.make_key(key, version=version), keys))
        map_keys = dict(zip(new_keys, keys))
        results = self._client.mget(new_keys)
        for key, value in zip(new_keys, results):
            if value is None:
                continue
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = self.unpickle(value)
            if isinstance(value, bytes_type):
                value = smart_text(value)
            recovered_data[map_keys[key]] = value
        return recovered_data

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        pipeline = self._client.pipeline()
        for key, value in data.items():
            self.set(key, value, timeout, version=version, client=pipeline)
        pipeline.execute()

    def incr(self, key, delta=1, version=None):
        """
        Add delta to value in the cache. If the key does not exist, raise a
        ValueError exception.
        """
        key = self.make_key(key, version=version)
        exists = self._client.exists(key)
        if not exists:
            raise ValueError("Key '%s' not found" % key)
        try:
            value = self._client.incr(key, delta)
        except redis.ResponseError:
            value = self.get(key) + delta
            self.set(key, value)
        return value

    def ttl(self, key, version=None):
        """
        Returns the 'time-to-live' of a key.  If the key is not volitile, i.e.
        it has not set expiration, then the value returned is None.  Otherwise,
        the value is the number of seconds remaining.  If the key does not exist,
        0 is returned.
        """
        key = self.make_key(key, version=version)
        if self._client.exists(key):
            return self._client.ttl(key)
        return 0

    def has_key(self, key, version=None):
        """
        Returns True if the key is in the cache and has not expired.
        """
        key = self.make_key(key, version=version)
        return self._client.exists(key)


class RedisCache(CacheClass):
    """
    A subclass that is supposed to be used on Django >= 1.3.
    """

    def make_key(self, key, version=None):
        if not isinstance(key, CacheKey):
            key = CacheKey(super(CacheClass, self).make_key(key, version))
        return key

    def incr_version(self, key, delta=1, version=None):
        """
        Adds delta to the cache version for the supplied key. Returns the
        new version.

        Note: In Redis 2.0 you cannot rename a volitile key, so we have to move
        the value from the old key to the new key and maintain the ttl.
        """
        if version is None:
            version = self.version
        old_key = self.make_key(key, version)
        value = self.get(old_key, version=version)
        ttl = self._client.ttl(old_key)
        if value is None:
            raise ValueError("Key '%s' not found" % key)
        new_key = self.make_key(key, version=version + delta)
        # TODO: See if we can check the version of Redis, since 2.2 will be able
        # to rename volitile keys.
        self.set(new_key, value, timeout=ttl)
        self.delete(old_key)
        return version + delta


########NEW FILE########
__FILENAME__ = compat
import sys
import django

PY3 = (sys.version_info >= (3,))

try:
    # Django 1.5+
    from django.utils.encoding import smart_text, smart_bytes
except ImportError:
    # older Django, thus definitely Python 2
    from django.utils.encoding import smart_unicode, smart_str
    smart_text = smart_unicode
    smart_bytes = smart_str


if PY3:
    bytes_type = bytes
else:
    bytes_type = str

if django.VERSION[:2] >= (1, 6):
    from django.core.cache.backends.base import DEFAULT_TIMEOUT as DJANGO_DEFAULT_TIMEOUT
    DEFAULT_TIMEOUT = DJANGO_DEFAULT_TIMEOUT
else:
    DEFAULT_TIMEOUT = None


def python_2_unicode_compatible(klass):
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.

    Backported from Django 1.5+.
    """
    if not PY3:
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
    return klass

########NEW FILE########
__FILENAME__ = sockettests
#!/usr/bin/env python
import sys
from os.path import dirname, abspath
from django.conf import settings


cache_settings = {
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    'INSTALLED_APPS': [
        'tests.testapp',
    ],
    'ROOT_URLCONF': 'tests.urls',
    'CACHES': {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': '/tmp/redis.sock',
            'OPTIONS': {
                'DB': 15,
                'PASSWORD': 'yadayada',
                'PARSER_CLASS': 'redis.connection.HiredisParser'
            },
        },
    },
}

if not settings.configured:
    settings.configure(**cache_settings)

from django.test.simple import DjangoTestSuiteRunner

def runtests(*test_args):
    if not test_args:
        test_args = ['testapp']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    runner = DjangoTestSuiteRunner(verbosity=1, interactive=True, failfast=False)
    failures = runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = tcptests
#!/usr/bin/env python
import sys
from os.path import dirname, abspath
from django.conf import settings


cache_settings = {
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    'INSTALLED_APPS': [
        'tests.testapp',
    ],
    'ROOT_URLCONF': 'tests.urls',
    'CACHES': {
        'default': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': '127.0.0.1:6379',
            'OPTIONS': {
                'DB': 15,
                'PARSER_CLASS': 'redis.connection.HiredisParser',
                'CONNECTION_POOL_CLASS': 'redis.ConnectionPool',
                'CONNECTION_POOL_CLASS_KWARGS': {
                    'max_connections': 2
                }
            },
        },
    },
}


if not settings.configured:
    settings.configure(**cache_settings)

from django.test.simple import DjangoTestSuiteRunner

def runtests(*test_args):
    if not test_args:
        test_args = ['testapp']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    runner = DjangoTestSuiteRunner(verbosity=1, interactive=True, failfast=False)
    failures = runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = benchmark
"""
A quick and dirty benchmarking script.  GitPython is an optional dependency
which you can use to change branches via the command line.

Usage::

    python benchmark.py
    python benchmark.py master
    python benchamrk.py some-branch
"""

import os
import sys
from time import time
from django.core import cache
from hashlib import sha1 as sha

try:
    from git import Repo
except ImportError:
    pass
else:
    if len(sys.argv) > 1:
        repo_path = os.path.dirname(__file__)
        repo = Repo(repo_path)
        repo.branches[sys.argv[1]].checkout()
        print "Testing %s" % repo.active_branch


def h(value):
    return sha(str(value)).hexdigest()

class BenchmarkRegistry(type):
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'benchmarks'):
            cls.benchmarks = []
        else:
            cls.benchmarks.append(cls)


class Benchmark(object):
    __metaclass__ = BenchmarkRegistry

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def timetrial(self):
        self.setUp()
        start = time()
        self.run()
        t = time() - start
        self.tearDown()
        return t

    def run(self):
        pass

    @classmethod
    def run_benchmarks(cls):
        for benchmark in cls.benchmarks:
            benchmark = benchmark()
            print benchmark.__doc__
            print "Time: %s" % (benchmark.timetrial())


class GetAndSetBenchmark(Benchmark):
    "Settings and Getting Mixed"

    def setUp(self):
        self.cache = cache.get_cache('default')
        self.values = {}
        for i in range(30000):
            self.values[h(i)] = i
            self.values[h(h(i))] = h(i)


    def run(self):
        for k, v in self.values.items():
            self.cache.set(k, v)
        for k, v in self.values.items():
            value = self.cache.get(k)


class IncrBenchmark(Benchmark):
    "Incrementing integers"
    def setUp(self):
        self.cache = cache.get_cache('default')
        self.values = {}
        self.ints = []
        self.strings = []
        for i in range(30000):
            self.values[h(i)] = i
            self.values[h(h(i))] = h(i)
            self.ints.append(i)
            self.strings.append(h(i))

    def run(self):
        for i in self.ints:
            self.cache.incr(h(i), 100)


class MsetAndMGet(Benchmark):
    "Getting and setting many mixed values"

    def setUp(self):
        self.cache = cache.get_cache('default')
        self.values = {}
        for i in range(30000):
            self.values[h(i)] = i
            self.values[h(h(i))] = h(i)

    def run(self):
        self.cache.set_many(self.values)
        value = self.cache.get_many(self.values.keys())


if __name__ == "__main__":
    Benchmark.run_benchmarks()
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = [
    'tests.testapp',
]

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '127.0.0.1:6379',
        'OPTIONS': {  # optional
            'DB': 15,
            'PASSWORD': 'yadayada',
            'MAX_CONNECTIONS': 2,
        },
    },
}

ROOT_URLCONF = 'tests.urls'

SECRET_KEY = 'blabla'

########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from django.db import models

def expensive_calculation():
    expensive_calculation.num_runs += 1
    return datetime.now()

class Poll(models.Model):
    question = models.CharField(max_length=200)
    answer = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published', default=expensive_calculation)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

import time

try:
    import cPickle as pickle
except ImportError:
    import pickle
from django import VERSION
from django.core.cache import get_cache
from django.test import TestCase
from .models import Poll, expensive_calculation
import redis
from redis.connection import UnixDomainSocketConnection
from redis_cache.cache import RedisCache, ImproperlyConfigured, pool


# functions/classes for complex data type tests
def f():
    return 42


class C:
    def m(n):
        return 24


class RedisCacheTests(TestCase):
    """
    A common set of tests derived from Django's own cache tests

    """
    def setUp(self):
        # use DB 16 for testing and hope there isn't any important data :->
        self.reset_pool()
        self.cache = self.get_cache()

    def tearDown(self):
        self.cache.clear()

    def reset_pool(self):
        if hasattr(self, 'cache'):
            self.cache._client.connection_pool.disconnect()

    def get_cache(self, backend=None):
        if VERSION[0] == 1 and VERSION[1] < 3:
            cache = get_cache(backend or 'redis_cache.cache://127.0.0.1:6379?db=15')
        elif VERSION[0] == 1 and VERSION[1] >= 3:
            cache = get_cache(backend or 'default')
        return cache

    def test_bad_db_initialization(self):
        self.assertRaises(ImproperlyConfigured, self.get_cache, 'redis_cache.cache://127.0.0.1:6379?db=not_a_number')

    def test_bad_port_initialization(self):
        self.assertRaises(ImproperlyConfigured, self.get_cache, 'redis_cache.cache://127.0.0.1:not_a_number?db=15')

    def test_default_initialization(self):
        self.reset_pool()
        if VERSION[0] == 1 and VERSION[1] < 3:
            self.cache = self.get_cache('redis_cache.cache://')
        elif VERSION[0] == 1 and VERSION[1] >= 3:
            self.cache = self.get_cache('redis_cache.cache.CacheClass')
        connection_class = self.cache._client.connection_pool.connection_class
        if connection_class is not UnixDomainSocketConnection:
            self.assertEqual(self.cache._client.connection_pool.connection_kwargs['host'], '127.0.0.1')
            self.assertEqual(self.cache._client.connection_pool.connection_kwargs['port'], 6379)
        self.assertEqual(self.cache._client.connection_pool.connection_kwargs['db'], 1)

    def test_simple(self):
        # Simple cache set/get works
        self.cache.set("key", "value")
        self.assertEqual(self.cache.get("key"), "value")

    def test_add(self):
        # A key can be added to a cache
        self.cache.add("addkey1", "value")
        result = self.cache.add("addkey1", "newvalue")
        self.assertEqual(result, False)
        self.assertEqual(self.cache.get("addkey1"), "value")

    def test_non_existent(self):
        # Non-existent cache keys return as None/default
        # get with non-existent keys
        self.assertEqual(self.cache.get("does_not_exist"), None)
        self.assertEqual(self.cache.get("does_not_exist", "bang!"), "bang!")

    def test_get_many(self):
        # Multiple cache keys can be returned using get_many
        self.cache.set('a', 'a')
        self.cache.set('b', 'b')
        self.cache.set('c', 'c')
        self.cache.set('d', 'd')
        self.assertEqual(self.cache.get_many(['a', 'c', 'd']), {'a' : 'a', 'c' : 'c', 'd' : 'd'})
        self.assertEqual(self.cache.get_many(['a', 'b', 'e']), {'a' : 'a', 'b' : 'b'})

    def test_get_many_with_manual_integer_insertion(self):
        keys = ['a', 'b', 'c', 'd']
        cache_keys = map(self.cache.make_key, keys)
        # manually set integers and then get_many
        for i, key in enumerate(cache_keys):
            self.cache._client.set(key, i)
        self.assertEqual(self.cache.get_many(keys), {'a': 0, 'b': 1, 'c': 2, 'd': 3})

    def test_get_many_with_automatic_integer_insertion(self):
        keys = ['a', 'b', 'c', 'd']
        for i, key in enumerate(keys):
            self.cache.set(key, i)
        self.assertEqual(self.cache.get_many(keys), {'a': 0, 'b': 1, 'c': 2, 'd': 3})

    def test_delete(self):
        # Cache keys can be deleted
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.assertEqual(self.cache.get("key1"), "spam")
        self.cache.delete("key1")
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), "eggs")

    def test_has_key(self):
        # The cache can be inspected for cache keys
        self.cache.set("hello1", "goodbye1")
        self.assertEqual(self.cache.has_key("hello1"), True)
        self.assertEqual(self.cache.has_key("goodbye1"), False)

    def test_in(self):
        # The in operator can be used to inspet cache contents
        self.cache.set("hello2", "goodbye2")
        self.assertEqual("hello2" in self.cache, True)
        self.assertEqual("goodbye2" in self.cache, False)

    def test_incr(self):
        # Cache values can be incremented
        self.cache.set('answer', 41)
        self.assertEqual(self.cache.get('answer'), 41)
        self.assertEqual(self.cache.incr('answer'), 42)
        self.assertEqual(self.cache.get('answer'), 42)
        self.assertEqual(self.cache.incr('answer', 10), 52)
        self.assertEqual(self.cache.get('answer'), 52)
        self.assertRaises(ValueError, self.cache.incr, 'does_not_exist')

    def test_decr(self):
        # Cache values can be decremented
        self.cache.set('answer', 43)
        self.assertEqual(self.cache.decr('answer'), 42)
        self.assertEqual(self.cache.get('answer'), 42)
        self.assertEqual(self.cache.decr('answer', 10), 32)
        self.assertEqual(self.cache.get('answer'), 32)
        self.assertRaises(ValueError, self.cache.decr, 'does_not_exist')

    def test_data_types(self):
        # Many different data types can be cached
        stuff = {
            'string'    : 'this is a string',
            'int'       : 42,
            'list'      : [1, 2, 3, 4],
            'tuple'     : (1, 2, 3, 4),
            'dict'      : {'A': 1, 'B' : 2},
            'function'  : f,
            'class'     : C,
        }
        self.cache.set("stuff", stuff)
        self.assertEqual(self.cache.get("stuff"), stuff)

    def test_cache_read_for_model_instance(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        my_poll = Poll.objects.create(question="Well?")
        self.assertEqual(Poll.objects.count(), 1)
        pub_date = my_poll.pub_date
        self.cache.set('question', my_poll)
        cached_poll = self.cache.get('question')
        self.assertEqual(cached_poll.pub_date, pub_date)
        # We only want the default expensive calculation run once
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_write_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache write
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        self.assertEqual(expensive_calculation.num_runs, 1)
        self.cache.set('deferred_queryset', defer_qs)
        # cache set should not re-evaluate default functions
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_read_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        self.cache.set('deferred_queryset', defer_qs)
        self.assertEqual(expensive_calculation.num_runs, 1)
        runs_before_cache_read = expensive_calculation.num_runs
        self.cache.get('deferred_queryset')
        # We only want the default expensive calculation run on creation and set
        self.assertEqual(expensive_calculation.num_runs, runs_before_cache_read)

    def test_expiration(self):
        # Cache values can be set to expire
        self.cache.set('expire1', 'very quickly', 1)
        self.cache.set('expire2', 'very quickly', 1)
        self.cache.set('expire3', 'very quickly', 1)

        time.sleep(2)
        self.assertEqual(self.cache.get("expire1"), None)

        self.cache.add("expire2", "newvalue")
        self.assertEqual(self.cache.get("expire2"), "newvalue")
        self.assertEqual(self.cache.has_key("expire3"), False)

    def test_set_expiration_default_timeout(self):
        self.cache.set('a', 'a')
        self.assertTrue(self.cache._client.ttl(self.cache.make_key('a')) > 0)

    def test_set_expiration_no_timeout(self):
        self.cache.set('a', 'a', timeout=None)
        self.assertTrue(self.cache._client.ttl(self.cache.make_key('a')) is None)

    def test_set_expiration_timeout_zero(self):
        key, value = self.cache.make_key('key'), 'value'
        self.cache.set(key, value, timeout=0)
        self.assertTrue(self.cache._client.ttl(key) is None)
        self.assertTrue(self.cache.has_key(key))

    def test_set_expiration_timeout_negative(self):
        key, value = self.cache.make_key('key'), 'value'
        self.cache.set(key, value, timeout=-1)
        self.assertTrue(self.cache._client.ttl(key) is None)
        self.assertFalse(self.cache.has_key(key))

    def test_unicode(self):
        # Unicode values can be cached
        stuff = {
            u'ascii': u'ascii_value',
            u'unicode_ascii': u'Iñtërnâtiônàlizætiøn1',
            u'Iñtërnâtiônàlizætiøn': u'Iñtërnâtiônàlizætiøn2',
            u'ascii': {u'x' : 1 }
        }
        for (key, value) in stuff.items():
            self.cache.set(key, value)
            self.assertEqual(self.cache.get(key), value)

    def test_binary_string(self):
        # Binary strings should be cachable
        from zlib import compress, decompress
        value = b'value_to_be_compressed'
        compressed_value = compress(value)
        self.cache.set('binary1', compressed_value)
        compressed_result = self.cache.get('binary1')
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result))

    def test_set_many(self):
        # Multiple keys can be set using set_many
        self.cache.set_many({"key1": "spam", "key2": "eggs"})
        self.assertEqual(self.cache.get("key1"), "spam")
        self.assertEqual(self.cache.get("key2"), "eggs")

    def test_set_many_expiration(self):
        # set_many takes a second ``timeout`` parameter
        self.cache.set_many({"key1": "spam", "key2": "eggs"}, 1)
        time.sleep(2)
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)

    def test_delete_many(self):
        # Multiple keys can be deleted using delete_many
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.cache.set("key3", "ham")
        self.cache.delete_many(["key1", "key2"])
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)
        self.assertEqual(self.cache.get("key3"), "ham")

    def test_clear(self):
        # The cache can be emptied using clear
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.cache.clear()
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)

    def test_long_timeout(self):
        '''
        Using a timeout greater than 30 days makes memcached think
        it is an absolute expiration timestamp instead of a relative
        offset. Test that we honour this convention. Refs #12399.
        '''
        self.cache.set('key1', 'eggs', 60*60*24*30 + 1) #30 days + 1 second
        self.assertEqual(self.cache.get('key1'), 'eggs')

        self.cache.add('key2', 'ham', 60*60*24*30 + 1)
        self.assertEqual(self.cache.get('key2'), 'ham')

        self.cache.set_many({'key3': 'sausage', 'key4': 'lobster bisque'}, 60*60*24*30 + 1)
        self.assertEqual(self.cache.get('key3'), 'sausage')
        self.assertEqual(self.cache.get('key4'), 'lobster bisque')

    def test_incr_version(self):
        if isinstance(self.cache, RedisCache):
            old_key = "key1"
            self.cache.set(old_key, "spam", version=1)
            self.assertEqual(self.cache.make_key(old_key), ':1:key1')
            new_version = self.cache.incr_version(old_key, 1)
            self.assertEqual(new_version, 2)
            new_key = self.cache.make_key(old_key, version=new_version)
            self.assertEqual(new_key, ':2:key1')
            self.assertEqual(self.cache.get(old_key), None)
            self.assertEqual(self.cache.get(new_key), 'spam')

    def test_incr_with_pickled_integer(self):
        "Testing case where there exists a pickled integer and we increment it"
        number = 42
        key = self.cache.make_key("key")

        # manually set value using the redis client
        self.cache._client.set(key, pickle.dumps(number))
        new_value = self.cache.incr(key)
        self.assertEqual(new_value, number + 1)

        # Test that the pickled value was converted to an integer
        value = int(self.cache._client.get(key))
        self.assertTrue(isinstance(value, int))

        # now that the value is an integer, let's increment it again.
        new_value = self.cache.incr(key, 7)
        self.assertEqual(new_value, number + 8)

    def test_pickling_cache_object(self):
        p = pickle.dumps(self.cache)
        cache = pickle.loads(p)
        # Now let's do a simple operation using the unpickled cache object
        cache.add("addkey1", "value")
        result = cache.add("addkey1", "newvalue")
        self.assertEqual(result, False)
        self.assertEqual(cache.get("addkey1"), "value")

    def test_float_caching(self):
        self.cache.set('a', 1.1)
        a = self.cache.get('a')
        self.assertEqual(a, 1.1)

    def test_string_float_caching(self):
        self.cache.set('a', '1.1')
        a = self.cache.get('a')
        self.assertEqual(a, '1.1')

    def test_multiple_connection_pool_connections(self):
        pool._connection_pools = {}
        get_cache('redis_cache.cache://127.0.0.1:6379?db=15')
        self.assertEqual(len(pool._connection_pools), 1)
        get_cache('redis_cache.cache://127.0.0.1:6379?db=14')
        self.assertEqual(len(pool._connection_pools), 2)
        get_cache('redis_cache.cache://127.0.0.1:6379?db=15')
        self.assertEqual(len(pool._connection_pools), 2)

    def test_setting_string_integer_retrieves_string(self):
        self.assertTrue(self.cache.set("foo", "1"))
        self.assertEqual(self.cache.get("foo"), "1")

    def test_setting_bool_retrieves_bool(self):
        self.assertTrue(self.cache.set("bool_t", True))
        self.assertEqual(self.cache.get("bool_t"), True)
        self.assertTrue(self.cache.set("bool_f", False))
        self.assertEqual(self.cache.get("bool_f"), False)

    def test_max_connections(self):
        pool._connection_pools = {}
        cache = get_cache('default')

        def noop(*args, **kwargs):
            pass

        release = cache._client.connection_pool.release
        cache._client.connection_pool.release = noop
        cache.set('a', 'a')
        cache.set('a', 'a')

        with self.assertRaises(redis.ConnectionError):
            cache.set('a', 'a')

        cache._client.connection_pool.release = release
        cache._client.connection_pool.max_connections = 2**31

    def test_ttl_set_expiry(self):
        self.cache.set('a', 'a', 10)
        ttl = self.cache.ttl('a')
        self.assertAlmostEqual(ttl, 10)

    def test_ttl_no_expiry(self):
        self.cache.set('a', 'a', timeout=None)
        ttl = self.cache.ttl('a')
        self.assertTrue(ttl is None)

    def test_ttl_past_expiry(self):
        self.cache.set('a', 'a', timeout=1)
        ttl = self.cache.ttl('a')
        self.assertAlmostEqual(ttl, 1)

        time.sleep(2)

        ttl = self.cache.ttl('a')
        self.assertEqual(ttl, 0)

    def test_non_existent_key(self):
        """ Non-existent keys are semantically the same as keys that have
        expired.
        """
        ttl = self.cache.ttl('does_not_exist')
        self.assertEqual(ttl, 0)

    def test_has_key_with_no_key(self):
        self.assertFalse(self.cache.has_key('does_not_exist'))

    def test_has_key_with_key(self):
        self.cache.set('a', 'a')
        self.assertTrue(self.cache.has_key('a'))


if __name__ == '__main__':
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('',
    (r'^$', 'tests.views.someview'),
)
########NEW FILE########
__FILENAME__ = views
from django.core.cache import get_cache
from django.http import HttpResponse


def someview(request):
    cache = get_cache('redis_cache.cache://127.0.0.1')
    cache.set("foo", "bar")
    return HttpResponse("Pants")
########NEW FILE########
