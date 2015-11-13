__FILENAME__ = memcached
"""
Memcached cache backend for Django using pylibmc.

If you want to use the binary protocol, specify `'BINARY': True` in your CACHES
settings.  The default is `False`, using the text protocol.

pylibmc behaviors can be declared as a dict in `CACHES` backend `OPTIONS`
setting.

Unlike the default Django caching backends, this backend lets you pass 0 as a
timeout, which translates to an infinite timeout in memcached.
"""
import logging
import warnings
from threading import local

from django.conf import settings
from django.core.cache.backends.base import InvalidCacheBackendError
from django.core.cache.backends.memcached import BaseMemcachedCache

try:
    import pylibmc
    from pylibmc import Error as MemcachedError
except ImportError:
    raise InvalidCacheBackendError('Could not import pylibmc.')


log = logging.getLogger('django.pylibmc')


MIN_COMPRESS_LEN = getattr(settings, 'PYLIBMC_MIN_COMPRESS_LEN', 0)  # Disabled
if MIN_COMPRESS_LEN > 0 and not pylibmc.support_compression:
    MIN_COMPRESS_LEN = 0
    warnings.warn('A minimum compression length was provided but pylibmc was '
                  'not compiled with support for it.')


COMPRESS_LEVEL = getattr(settings, 'PYLIBMC_COMPRESS_LEVEL', -1)  # zlib.Z_DEFAULT_COMPRESSION
if not COMPRESS_LEVEL == -1:
    if not pylibmc.support_compression:
        warnings.warn('A compression level was provided but pylibmc was '
                      'not compiled with support for it.')
    if not pylibmc.__version__ >= '1.3.0':
        warnings.warn('A compression level was provided but pylibmc 1.3.0 '
                      'or above is required to handle this option.')


# Keyword arguments to configure compression options
# based on capabilities of a provided pylibmc library.
COMPRESS_KWARGS = {
    # Requires pylibmc 1.0 and above. Given that the minumum supported
    # version (as of now) is 1.1, the parameter is always included.
    'min_compress_len': MIN_COMPRESS_LEN,
}
if pylibmc.__version__ >= '1.3.0':
    COMPRESS_KWARGS['compress_level'] = COMPRESS_LEVEL


class PyLibMCCache(BaseMemcachedCache):

    def __init__(self, server, params, username=None, password=None):
        import os
        self._local = local()
        self.binary = int(params.get('BINARY', False))
        self._username = os.environ.get('MEMCACHE_USERNAME', username or params.get('USERNAME'))
        self._password = os.environ.get('MEMCACHE_PASSWORD', password or params.get('PASSWORD'))
        self._server = os.environ.get('MEMCACHE_SERVERS', server)
        super(PyLibMCCache, self).__init__(self._server, params, library=pylibmc,
                                           value_not_found_exception=pylibmc.NotFound)

    @property
    def _cache(self):
        # PylibMC uses cache options as the 'behaviors' attribute.
        # It also needs to use threadlocals, because some versions of
        # PylibMC don't play well with the GIL.
        client = getattr(self._local, 'client', None)
        if client:
            return client

        client_kwargs = {'binary': self.binary}
        if self._username is not None and self._password is not None:
            client_kwargs.update({
                'username': self._username,
                'password': self._password
            })
        client = self._lib.Client(self._servers, **client_kwargs)
        if self._options:
            client.behaviors = self._options

        self._local.client = client

        return client

    def _get_memcache_timeout(self, timeout):
        """
        Special case timeout=0 to allow for infinite timeouts.
        """
        if timeout == 0:
            return timeout
        else:
            return super(PyLibMCCache, self)._get_memcache_timeout(timeout)

    def add(self, key, value, timeout=None, version=None):
        key = self.make_key(key, version=version)
        try:
            return self._cache.add(key, value,
                                   self._get_memcache_timeout(timeout),
                                   **COMPRESS_KWARGS)
        except pylibmc.ServerError:
            log.error('ServerError saving %s (%d bytes)' % (key, len(value)),
                      exc_info=True)
            return False
        except MemcachedError, e:
            log.error('MemcachedError: %s' % e, exc_info=True)
            return False

    def get(self, key, default=None, version=None):
        try:
            return super(PyLibMCCache, self).get(key, default, version)
        except MemcachedError, e:
            log.error('MemcachedError: %s' % e, exc_info=True)
            return default

    def set(self, key, value, timeout=None, version=None):
        key = self.make_key(key, version=version)
        try:
            return self._cache.set(key, value,
                                   self._get_memcache_timeout(timeout),
                                   **COMPRESS_KWARGS)
        except pylibmc.ServerError:
            log.error('ServerError saving %s (%d bytes)' % (key, len(value)),
                      exc_info=True)
            return False
        except MemcachedError, e:
            log.error('MemcachedError: %s' % e, exc_info=True)
            return False

    def delete(self, *args, **kwargs):
        try:
            return super(PyLibMCCache, self).delete(*args, **kwargs)
        except MemcachedError, e:
            log.error('MemcachedError: %s' % e, exc_info=True)
            return False

    def get_many(self, *args, **kwargs):
        try:
            return super(PyLibMCCache, self).get_many(*args, **kwargs)
        except MemcachedError, e:
            log.error('MemcachedError: %s' % e, exc_info=True)
            return {}

    def set_many(self, *args, **kwargs):
        try:
            return super(PyLibMCCache, self).set_many(*args, **kwargs)
        except MemcachedError, e:
            log.error('MemcachedError: %s' % e, exc_info=True)
            return False

    def delete_many(self, *args, **kwargs):
        try:
            return super(PyLibMCCache, self).delete_many(*args, **kwargs)
        except MemcachedError, e:
            log.error('MemcachedError: %s' % e, exc_info=True)
            return False

########NEW FILE########
__FILENAME__ = models
from django.db import models
from datetime import datetime

def expensive_calculation():
    expensive_calculation.num_runs += 1
    return datetime.now()

class Poll(models.Model):
    question = models.CharField(max_length=200)
    answer = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published', default=expensive_calculation)

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'testing',
        'SUPPORTS_TRANSACTIONS': False,
    },
}

INSTALLED_APPS = (
    'app',
)

CACHES = {
    'default': {
        'BACKEND': 'django_pylibmc.memcached.PyLibMCCache',
        'LOCATION': 'localhost:11211',
        'TIMEOUT': 500,
        'BINARY': True,
        'USERNAME': 'test_username',
        'PASSWORD': 'test_password',
        'OPTIONS': {
            'tcp_nodelay': True,
            'ketama': True
        }
    }
}

PYLIBMC_MIN_COMPRESS_LEN = 150 * 1024
PYLIBMC_COMPRESS_LEVEL = 1  # zlib.Z_BEST_SPEED

SECRET_KEY = 'secret'

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import os
import sys
import time
import unittest


test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(test_dir, os.path.pardir))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.test import simple
from django.core.cache import get_cache

from app.models import Poll, expensive_calculation


# functions/classes for complex data type tests
def f():
    return 42
class C:
    def m(n):
        return 24


# Lifted from django/regressiontests/cache/tests.py.
class BaseCacheTests(object):
    # A common set of tests to apply to all cache backends
    def tearDown(self):
        self.cache.clear()

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
        my_poll = Poll.objects.create(question="What?")
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
        my_poll = Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        self.cache.set('deferred_queryset', defer_qs)
        self.assertEqual(expensive_calculation.num_runs, 1)
        runs_before_cache_read = expensive_calculation.num_runs
        cached_polls = self.cache.get('deferred_queryset')
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

    def test_unicode(self):
        # Unicode values can be cached
        stuff = {
            u'ascii': u'ascii_value',
            u'unicode_ascii': u'Iñtërnâtiônàlizætiøn1',
            u'Iñtërnâtiônàlizætiøn': u'Iñtërnâtiônàlizætiøn2',
            u'ascii': {u'x': 1}
            }
        for (key, value) in stuff.items():
            self.cache.set(key, value)
            self.assertEqual(self.cache.get(key), value)

    def test_binary_string(self):
        # Binary strings should be cachable
        from zlib import compress, decompress
        value = 'value_to_be_compressed'
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

    def test_gt_1MB_value(self):
        # Test value > 1M gets compressed and stored
        big_value = 'x' * 2 * 1024 * 1024
        self.cache.set('big_value', big_value)
        self.assertEqual(self.cache.get('big_value'), big_value)

    def test_too_big_value(self):
        # A value larger than 1M after compression will fail and return False
        super_big_value = 'x' * 400 * 1024 * 1024
        self.assertFalse(self.cache.set('super_big_value', super_big_value))


class PylibmcCacheTests(unittest.TestCase, BaseCacheTests):

    def setUp(self):
        self.cache = get_cache('django_pylibmc.memcached.PyLibMCCache')

class PylibmcCacheWithBinaryTests(unittest.TestCase, BaseCacheTests):

    def setUp(self):
        self.cache = get_cache('django_pylibmc.memcached.PyLibMCCache',
                               BINARY=True)

class PylibmcCacheWithOptionsTests(unittest.TestCase, BaseCacheTests):

    def setUp(self):
        self.cache = get_cache('django_pylibmc.memcached.PyLibMCCache',
                               OPTIONS={'tcp_nodelay': True, 'ketama': True})


if __name__ == '__main__':
    runner = simple.DjangoTestSuiteRunner()
    try:
        old_config = runner.setup_databases()
        unittest.main()
    finally:
        runner.teardown_databases(old_config)

########NEW FILE########
