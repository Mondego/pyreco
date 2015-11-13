__FILENAME__ = locmem
import django
from django.core.cache.backends import locmem

from caching.compat import DEFAULT_TIMEOUT, FOREVER


if django.VERSION[:2] >= (1, 6):
    Infinity = FOREVER
else:
    class _Infinity(object):
        """Always compares greater than numbers."""

        def __radd__(self, _):
            return self

        def __cmp__(self, o):
            return 0 if self is o else 1

        def __repr__(self):
            return 'Infinity'

    Infinity = _Infinity()
    del _Infinity


# Add infinite timeout support to the locmem backend.  Useful for testing.
class InfinityMixin(object):

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        if timeout == FOREVER:
            timeout = Infinity
        return super(InfinityMixin, self).add(key, value, timeout, version)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        if timeout == FOREVER:
            timeout = Infinity
        return super(InfinityMixin, self).set(key, value, timeout, version)


class CacheClass(InfinityMixin, locmem.CacheClass):
    pass


if django.VERSION[:2] >= (1, 3):
    class LocMemCache(InfinityMixin, locmem.LocMemCache):
        pass

########NEW FILE########
__FILENAME__ = memcached
import django
from django.core.cache.backends import memcached

from caching.compat import DEFAULT_TIMEOUT


# Add infinite timeout support to the memcached backend.
class InfinityMixin(object):

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return super(InfinityMixin, self).add(key, value, timeout, version)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return super(InfinityMixin, self).set(key, value, timeout, version)


if django.VERSION[:2] >= (1, 3):
    class MemcachedCache(InfinityMixin, memcached.MemcachedCache):
        pass

    class PyLibMCCache(InfinityMixin, memcached.PyLibMCCache):
        pass

    class CacheClass(MemcachedCache):
        pass
else:
    class CacheClass(InfinityMixin, memcached.CacheClass):
        pass

########NEW FILE########
__FILENAME__ = base
import functools
import logging

from django.conf import settings
from django.db import models
from django.db.models import signals
from django.db.models.sql import query, EmptyResultSet
from django.utils import encoding

from .compat import DEFAULT_TIMEOUT, FOREVER
from .invalidation import invalidator, flush_key, make_key, byid, cache


class NullHandler(logging.Handler):

    def emit(self, record):
        pass


log = logging.getLogger('caching')
log.addHandler(NullHandler())

NO_CACHE = -1
CACHE_PREFIX = getattr(settings, 'CACHE_PREFIX', '')
FETCH_BY_ID = getattr(settings, 'FETCH_BY_ID', False)
CACHE_EMPTY_QUERYSETS = getattr(settings, 'CACHE_EMPTY_QUERYSETS', False)
TIMEOUT = getattr(settings, 'CACHE_COUNT_TIMEOUT', NO_CACHE)


class CachingManager(models.Manager):

    # Tell Django to use this manager when resolving foreign keys.
    use_for_related_fields = True

    def get_query_set(self):
        return CachingQuerySet(self.model, using=self._db)

    def contribute_to_class(self, cls, name):
        signals.post_save.connect(self.post_save, sender=cls)
        signals.post_delete.connect(self.post_delete, sender=cls)
        return super(CachingManager, self).contribute_to_class(cls, name)

    def post_save(self, instance, **kwargs):
        self.invalidate(instance)

    def post_delete(self, instance, **kwargs):
        self.invalidate(instance)

    def invalidate(self, *objects):
        """Invalidate all the flush lists associated with ``objects``."""
        keys = [k for o in objects for k in o._cache_keys()]
        invalidator.invalidate_keys(keys)

    def raw(self, raw_query, params=None, *args, **kwargs):
        return CachingRawQuerySet(raw_query, self.model, params=params,
                                  using=self._db, *args, **kwargs)

    def cache(self, timeout=DEFAULT_TIMEOUT):
        return self.get_query_set().cache(timeout)

    def no_cache(self):
        return self.cache(NO_CACHE)


class CacheMachine(object):
    """
    Handles all the cache management for a QuerySet.

    Takes the string representation of a query and a function that can be
    called to get an iterator over some database results.
    """

    def __init__(self, query_string, iter_function, timeout=DEFAULT_TIMEOUT, db='default'):
        self.query_string = query_string
        self.iter_function = iter_function
        self.timeout = timeout
        self.db = db

    def query_key(self):
        """
        Generate the cache key for this query.

        Database router info is included to avoid the scenario where related
        cached objects from one DB (e.g. slave) are saved in another DB (e.g.
        master), throwing a Django ValueError in the process. Django prevents
        cross DB model saving among related objects.
        """
        query_db_string = u'qs:%s::db:%s' % (self.query_string, self.db)
        return make_key(query_db_string, with_locale=False)

    def __iter__(self):
        try:
            query_key = self.query_key()
        except query.EmptyResultSet:
            raise StopIteration

        # Try to fetch from the cache.
        cached = cache.get(query_key)
        if cached is not None:
            log.debug('cache hit: %s' % self.query_string)
            for obj in cached:
                obj.from_cache = True
                yield obj
            return

        # Do the database query, cache it once we have all the objects.
        iterator = self.iter_function()

        to_cache = []
        try:
            while True:
                obj = iterator.next()
                obj.from_cache = False
                to_cache.append(obj)
                yield obj
        except StopIteration:
            if to_cache or CACHE_EMPTY_QUERYSETS:
                self.cache_objects(to_cache)
            raise

    def cache_objects(self, objects):
        """Cache query_key => objects, then update the flush lists."""
        query_key = self.query_key()
        query_flush = flush_key(self.query_string)
        cache.add(query_key, objects, timeout=self.timeout)
        invalidator.cache_objects(objects, query_key, query_flush)


class CachingQuerySet(models.query.QuerySet):

    def __init__(self, *args, **kw):
        super(CachingQuerySet, self).__init__(*args, **kw)
        self.timeout = DEFAULT_TIMEOUT

    def flush_key(self):
        return flush_key(self.query_key())

    def query_key(self):
        clone = self.query.clone()
        sql, params = clone.get_compiler(using=self.db).as_sql()
        return sql % params

    def iterator(self):
        iterator = super(CachingQuerySet, self).iterator
        if self.timeout == NO_CACHE:
            return iter(iterator())
        else:
            try:
                # Work-around for Django #12717.
                query_string = self.query_key()
            except query.EmptyResultSet:
                return iterator()
            if FETCH_BY_ID:
                iterator = self.fetch_by_id
            return iter(CacheMachine(query_string, iterator, self.timeout, db=self.db))

    def fetch_by_id(self):
        """
        Run two queries to get objects: one for the ids, one for id__in=ids.

        After getting ids from the first query we can try cache.get_many to
        reuse objects we've already seen.  Then we fetch the remaining items
        from the db, and put those in the cache.  This prevents cache
        duplication.
        """
        # Include columns from extra since they could be used in the query's
        # order_by.
        vals = self.values_list('pk', *self.query.extra.keys())
        pks = [val[0] for val in vals]
        keys = dict((byid(self.model._cache_key(pk, self.db)), pk) for pk in pks)
        cached = dict((k, v) for k, v in cache.get_many(keys).items()
                      if v is not None)

        # Pick up the objects we missed.
        missed = [pk for key, pk in keys.items() if key not in cached]
        if missed:
            others = self.fetch_missed(missed)
            # Put the fetched objects back in cache.
            new = dict((byid(o), o) for o in others)
            cache.set_many(new)
        else:
            new = {}

        # Use pks to return the objects in the correct order.
        objects = dict((o.pk, o) for o in cached.values() + new.values())
        for pk in pks:
            yield objects[pk]

    def fetch_missed(self, pks):
        # Reuse the queryset but get a clean query.
        others = self.all()
        others.query.clear_limits()
        # Clear out the default ordering since we order based on the query.
        others = others.order_by().filter(pk__in=pks)
        if hasattr(others, 'no_cache'):
            others = others.no_cache()
        if self.query.select_related:
            others.query.select_related = self.query.select_related
        return others

    def count(self):
        super_count = super(CachingQuerySet, self).count
        try:
            query_string = 'count:%s' % self.query_key()
        except query.EmptyResultSet:
            return 0
        if self.timeout == NO_CACHE or TIMEOUT == NO_CACHE:
            return super_count()
        else:
            return cached_with(self, super_count, query_string, TIMEOUT)

    def cache(self, timeout=DEFAULT_TIMEOUT):
        qs = self._clone()
        qs.timeout = timeout
        return qs

    def no_cache(self):
        return self.cache(NO_CACHE)

    def _clone(self, *args, **kw):
        qs = super(CachingQuerySet, self)._clone(*args, **kw)
        qs.timeout = self.timeout
        return qs


class CachingMixin(object):
    """Inherit from this class to get caching and invalidation helpers."""

    def flush_key(self):
        return flush_key(self)

    @property
    def cache_key(self):
        """Return a cache key based on the object's primary key."""
        return self._cache_key(self.pk, self._state.db)

    @classmethod
    def _cache_key(cls, pk, db):
        """
        Return a string that uniquely identifies the object.

        For the Addon class, with a pk of 2, we get "o:addons.addon:2".
        """
        key_parts = ('o', cls._meta, pk, db)
        return ':'.join(map(encoding.smart_unicode, key_parts))

    def _cache_keys(self):
        """Return the cache key for self plus all related foreign keys."""
        fks = dict((f, getattr(self, f.attname)) for f in self._meta.fields
                    if isinstance(f, models.ForeignKey))

        keys = [fk.rel.to._cache_key(val, self._state.db) for fk, val in fks.items()
                if val is not None and hasattr(fk.rel.to, '_cache_key')]
        return (self.cache_key,) + tuple(keys)


class CachingRawQuerySet(models.query.RawQuerySet):

    def __init__(self, *args, **kw):
        timeout = kw.pop('timeout', DEFAULT_TIMEOUT)
        super(CachingRawQuerySet, self).__init__(*args, **kw)
        self.timeout = timeout

    def __iter__(self):
        iterator = super(CachingRawQuerySet, self).__iter__
        if self.timeout == NO_CACHE:
            iterator = iterator()
            while True:
                yield iterator.next()
        else:
            sql = self.raw_query % tuple(self.params)
            for obj in CacheMachine(sql, iterator, timeout=self.timeout):
                yield obj
            raise StopIteration


def _function_cache_key(key):
    return make_key('f:%s' % key, with_locale=True)


def cached(function, key_, duration=DEFAULT_TIMEOUT):
    """Only calls the function if ``key`` is not already in the cache."""
    key = _function_cache_key(key_)
    val = cache.get(key)
    if val is None:
        log.debug('cache miss for %s' % key)
        val = function()
        cache.set(key, val, duration)
    else:
        log.debug('cache hit for %s' % key)
    return val


def cached_with(obj, f, f_key, timeout=DEFAULT_TIMEOUT):
    """Helper for caching a function call within an object's flush list."""

    try:
        obj_key = (obj.query_key() if hasattr(obj, 'query_key')
                   else obj.cache_key)
    except (AttributeError, EmptyResultSet):
        log.warning(u'%r cannot be cached.' % encoding.smart_str(obj))
        return f()

    key = '%s:%s' % tuple(map(encoding.smart_str, (f_key, obj_key)))
    # Put the key generated in cached() into this object's flush list.
    invalidator.add_to_flush_list(
        {obj.flush_key(): [_function_cache_key(key)]})
    return cached(f, key, timeout)


class cached_method(object):
    """
    Decorator to cache a method call in this object's flush list.

    The external cache will only be used once per (instance, args).  After that
    a local cache on the object will be used.

    Lifted from werkzeug.
    """
    def __init__(self, func):
        self.func = func
        functools.update_wrapper(self, func)

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        _missing = object()
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            w = MethodWrapper(obj, self.func)
            obj.__dict__[self.__name__] = w
            return w
        return value


class MethodWrapper(object):
    """
    Wraps around an object's method for two-level caching.

    The first call for a set of (args, kwargs) will use an external cache.
    After that, an object-local dict cache will be used.
    """
    def __init__(self, obj, func):
        self.obj = obj
        self.func = func
        functools.update_wrapper(self, func)
        self.cache = {}

    def __call__(self, *args, **kwargs):
        k = lambda o: o.cache_key if hasattr(o, 'cache_key') else o
        arg_keys = map(k, args)
        kwarg_keys = [(key, k(val)) for key, val in kwargs.items()]
        key_parts = ('m', self.obj.cache_key, self.func.__name__,
                     arg_keys, kwarg_keys)
        key = ':'.join(map(encoding.smart_unicode, key_parts))
        if key not in self.cache:
            f = functools.partial(self.func, self.obj, *args, **kwargs)
            self.cache[key] = cached_with(self.obj, f, key)
        return self.cache[key]

########NEW FILE########
__FILENAME__ = compat
import django

__all__ = ['DEFAULT_TIMEOUT', 'FOREVER']


if django.VERSION[:2] >= (1, 6):
  from django.core.cache.backends.base import DEFAULT_TIMEOUT as DJANGO_DEFAULT_TIMEOUT
  DEFAULT_TIMEOUT = DJANGO_DEFAULT_TIMEOUT
  FOREVER = None
else:
  DEFAULT_TIMEOUT = None
  FOREVER = 0

########NEW FILE########
__FILENAME__ = ext
from django.conf import settings
from django.utils import encoding

from jinja2 import nodes
from jinja2.ext import Extension

import caching.base


class FragmentCacheExtension(Extension):
    """
    Cache a chunk of template code based on a queryset.  Since looping over
    querysets is the slowest thing we do, you should wrap you for loop with the
    cache tag.  Uses the default timeout unless you pass a second argument.

    {% cache queryset[, timeout] %}
      ...template code...
    {% endcache %}

    Derived from the jinja2 documentation example.
    """
    tags = set(['cache'])

    def __init__(self, environment):
        super(FragmentCacheExtension, self).__init__(environment)

    def preprocess(self, source, name, filename=None):
        self.name = filename or name
        return source

    def parse(self, parser):
        # the first token is the token that started the tag.  In our case
        # we only listen to ``'cache'`` so this will be a name token with
        # `cache` as value.  We get the line number so that we can give
        # that line number to the nodes we create by hand.
        lineno = parser.stream.next().lineno

        # Use the filename + line number and first object for the cache key.
        name = '%s+%s' % (self.name, lineno)
        args = [nodes.Const(name), parser.parse_expression()]

        # If there is a comma, the user provided a timeout.  If not, use
        # None as second parameter.
        timeout = nodes.Const(None)
        extra = nodes.Const([])
        while parser.stream.skip_if('comma'):
            x = parser.parse_expression()
            if parser.stream.current.type == 'assign':
                next(parser.stream)
                extra = parser.parse_expression()
            else:
                timeout = x
        args.extend([timeout, extra])

        body = parser.parse_statements(['name:endcache'], drop_needle=True)

        self.process_cache_arguments(args)

        # now return a `CallBlock` node that calls our _cache_support
        # helper method on this extension.
        return nodes.CallBlock(self.call_method('_cache_support', args),
                               [], [], body).set_lineno(lineno)

    def process_cache_arguments(self, args):
        """Extension point for adding anything extra to the cache_support."""
        pass

    def _cache_support(self, name, obj, timeout, extra, caller):
        """Cache helper callback."""
        if settings.TEMPLATE_DEBUG:
            return caller()
        extra = ':'.join(map(encoding.smart_str, extra))
        key = 'fragment:%s:%s' % (name, extra)
        return caching.base.cached_with(obj, caller, key, timeout)


# Nice import name.
cache = FragmentCacheExtension

########NEW FILE########
__FILENAME__ = invalidation
import collections
import functools
import hashlib
import logging
import socket

from django.conf import settings
from django.core.cache import cache as default_cache, get_cache, parse_backend_uri
from django.core.cache.backends.base import InvalidCacheBackendError
from django.utils import encoding, translation

try:
    import redis as redislib
except ImportError:
    redislib = None

# Look for an own cache first before falling back to the default cache
try:
    cache = get_cache('cache_machine')
except (InvalidCacheBackendError, ValueError):
    cache = default_cache


CACHE_PREFIX = getattr(settings, 'CACHE_PREFIX', '')
FETCH_BY_ID = getattr(settings, 'FETCH_BY_ID', False)
FLUSH = CACHE_PREFIX + ':flush:'

log = logging.getLogger('caching.invalidation')


def make_key(k, with_locale=True):
    """Generate the full key for ``k``, with a prefix."""
    key = encoding.smart_str('%s:%s' % (CACHE_PREFIX, k))
    if with_locale:
        key += encoding.smart_str(translation.get_language())
    # memcached keys must be < 250 bytes and w/o whitespace, but it's nice
    # to see the keys when using locmem.
    return hashlib.md5(key).hexdigest()


def flush_key(obj):
    """We put flush lists in the flush: namespace."""
    key = obj if isinstance(obj, basestring) else obj.cache_key
    return FLUSH + make_key(key, with_locale=False)


def byid(obj):
    key = obj if isinstance(obj, basestring) else obj.cache_key
    return make_key('byid:' + key)


def safe_redis(return_type):
    """
    Decorator to catch and log any redis errors.

    return_type (optionally a callable) will be returned if there is an error.
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kw):
            try:
                return f(*args, **kw)
            except (socket.error, redislib.RedisError), e:
                log.error('redis error: %s' % e)
                # log.error('%r\n%r : %r' % (f.__name__, args[1:], kw))
                if hasattr(return_type, '__call__'):
                    return return_type()
                else:
                    return return_type
        return wrapper
    return decorator


class Invalidator(object):

    def invalidate_keys(self, keys):
        """Invalidate all the flush lists named by the list of ``keys``."""
        if not keys:
            return
        flush, flush_keys = self.find_flush_lists(keys)

        if flush:
            cache.delete_many(flush)
        if flush_keys:
            self.clear_flush_lists(flush_keys)

    def cache_objects(self, objects, query_key, query_flush):
        # Add this query to the flush list of each object.  We include
        # query_flush so that other things can be cached against the queryset
        # and still participate in invalidation.
        flush_keys = [o.flush_key() for o in objects]

        flush_lists = collections.defaultdict(set)
        for key in flush_keys:
            flush_lists[key].add(query_flush)
        flush_lists[query_flush].add(query_key)

        # Add each object to the flush lists of its foreign keys.
        for obj in objects:
            obj_flush = obj.flush_key()
            for key in map(flush_key, obj._cache_keys()):
                if key != obj_flush:
                    flush_lists[key].add(obj_flush)
                if FETCH_BY_ID:
                    flush_lists[key].add(byid(obj))
        self.add_to_flush_list(flush_lists)

    def find_flush_lists(self, keys):
        """
        Recursively search for flush lists and objects to invalidate.

        The search starts with the lists in `keys` and expands to any flush
        lists found therein.  Returns ({objects to flush}, {flush keys found}).
        """
        new_keys = keys = set(map(flush_key, keys))
        flush = set(keys)

        # Add other flush keys from the lists, which happens when a parent
        # object includes a foreign key.
        while 1:
            to_flush = self.get_flush_lists(new_keys)
            flush.update(to_flush)
            new_keys = set(k for k in to_flush if k.startswith(FLUSH))
            diff = new_keys.difference(keys)
            if diff:
                keys.update(new_keys)
            else:
                return flush, keys

    def add_to_flush_list(self, mapping):
        """Update flush lists with the {flush_key: [query_key,...]} map."""
        flush_lists = collections.defaultdict(set)
        flush_lists.update(cache.get_many(mapping.keys()))
        for key, list_ in mapping.items():
            if flush_lists[key] is None:
                flush_lists[key] = set(list_)
            else:
                flush_lists[key].update(list_)
        cache.set_many(flush_lists)

    def get_flush_lists(self, keys):
        """Return a set of object keys from the lists in `keys`."""
        return set(e for flush_list in
                   filter(None, cache.get_many(keys).values())
                   for e in flush_list)

    def clear_flush_lists(self, keys):
        """Remove the given keys from the database."""
        cache.delete_many(keys)


class RedisInvalidator(Invalidator):

    def safe_key(self, key):
        if ' ' in key or '\n' in key:
            log.warning('BAD KEY: "%s"' % key)
            return ''
        return key

    @safe_redis(None)
    def add_to_flush_list(self, mapping):
        """Update flush lists with the {flush_key: [query_key,...]} map."""
        pipe = redis.pipeline(transaction=False)
        for key, list_ in mapping.items():
            for query_key in list_:
                pipe.sadd(self.safe_key(key), query_key)
        pipe.execute()

    @safe_redis(set)
    def get_flush_lists(self, keys):
        return redis.sunion(map(self.safe_key, keys))

    @safe_redis(None)
    def clear_flush_lists(self, keys):
        redis.delete(*map(self.safe_key, keys))


class NullInvalidator(Invalidator):

    def add_to_flush_list(self, mapping):
        return


def get_redis_backend():
    """Connect to redis from a string like CACHE_BACKEND."""
    # From django-redis-cache.
    _, server, params = parse_backend_uri(settings.REDIS_BACKEND)
    db = params.pop('db', 1)
    try:
        db = int(db)
    except (ValueError, TypeError):
        db = 1
    try:
        socket_timeout = float(params.pop('socket_timeout'))
    except (KeyError, ValueError):
        socket_timeout = None
    password = params.pop('password', None)
    if ':' in server:
        host, port = server.split(':')
        try:
            port = int(port)
        except (ValueError, TypeError):
            port = 6379
    else:
        host = 'localhost'
        port = 6379
    return redislib.Redis(host=host, port=port, db=db, password=password,
                          socket_timeout=socket_timeout)


if getattr(settings, 'CACHE_MACHINE_NO_INVALIDATION', False):
    invalidator = NullInvalidator()
elif getattr(settings, 'CACHE_MACHINE_USE_REDIS', False):
    redis = get_redis_backend()
    invalidator = RedisInvalidator()
else:
    invalidator = Invalidator()

########NEW FILE########
__FILENAME__ = conf
import os
import sys

sys.path.append(os.path.abspath('..'))

import caching

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

extensions = ['sphinx.ext.autodoc']

# General information about the project.
project = u'Cache Machine'
copyright = u'2010, The Zamboni Collective'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# version: The short X.Y version.
# release: The full version, including alpha/beta/rc tags.
version = release = caching.__version__

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

########NEW FILE########
__FILENAME__ = custom_backend
from settings import *

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'cache_machine': {
        'BACKEND': 'caching.backends.memcached.MemcachedCache',
        'LOCATION': 'localhost:11211',
    },
}

########NEW FILE########
__FILENAME__ = locmem_settings
from settings import *

CACHES = {
    'default': {
        'BACKEND': 'caching.backends.locmem.CacheClass',
    },
}

########NEW FILE########
__FILENAME__ = memcache_byid
from settings import *

FETCH_BY_ID = True

########NEW FILE########
__FILENAME__ = redis_byid
from redis_settings import *

FETCH_BY_ID = True

########NEW FILE########
__FILENAME__ = redis_settings
from settings import *

CACHE_MACHINE_USE_REDIS = True
REDIS_BACKEND = 'redis://'

########NEW FILE########
__FILENAME__ = settings
CACHES = {
    'default': {
        'BACKEND': 'caching.backends.memcached.MemcachedCache',
        'LOCATION': 'localhost:11211',
    },
}

TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

DATABASES = {
    'default': {
        'NAME': ':memory:',
        'ENGINE': 'django.db.backends.sqlite3',
    },
    'slave': {
        'NAME': 'test_slave.db',
        'ENGINE': 'django.db.backends.sqlite3',
        }
}

INSTALLED_APPS = (
    'django_nose',
    'tests.testapp',
)

SECRET_KEY = 'ok'

########NEW FILE########
__FILENAME__ = fabfile
"""
Creating standalone Django apps is a PITA because you're not in a project, so
you don't have a settings.py file.  I can never remember to define
DJANGO_SETTINGS_MODULE, so I run these commands which get the right env
automatically.
"""
import functools
import os

from fabric.api import local, cd, env
from fabric.contrib.project import rsync_project

NAME = os.path.basename(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.dirname(__file__))

os.environ['PYTHONPATH'] = os.pathsep.join([ROOT,
                                            os.path.join(ROOT, 'examples')])

env.hosts = ['jbalogh.me']

local = functools.partial(local, capture=False)


def doc(kind='html'):
    with cd('docs'):
        local('make clean %s' % kind)


SETTINGS = ('locmem_settings',
            'settings',
            'memcache_byid',
            'custom_backend')

try:
    import redis
    redis.Redis(host='localhost', port=6379).info()
    SETTINGS += ('redis_settings', 'redis_byid')
except Exception:
    print 'WARNING: Skipping redis tests.'

def test():
    for settings in SETTINGS:
        print settings
        os.environ['DJANGO_SETTINGS_MODULE'] = 'cache_machine.%s' % settings
        local('django-admin.py test')


def updoc():
    doc('dirhtml')
    rsync_project('p/%s' % NAME, 'docs/_build/dirhtml/', delete=True)

########NEW FILE########
__FILENAME__ = models
from django.db import models

import mock

from caching.base import CachingMixin, CachingManager, cached_method


# This global call counter will be shared among all instances of an Addon.
call_counter = mock.Mock()


class User(CachingMixin, models.Model):
    name = models.CharField(max_length=30)

    objects = CachingManager()


class Addon(CachingMixin, models.Model):
    val = models.IntegerField()
    author1 = models.ForeignKey(User)
    author2 = models.ForeignKey(User, related_name='author2_set')

    objects = CachingManager()

    @cached_method
    def calls(self, arg=1):
        """This is a docstring for calls()"""
        call_counter()
        return arg, call_counter.call_count

########NEW FILE########
__FILENAME__ = test_cache
# -*- coding: utf-8 -*-
import django
from django.conf import settings
from django.test import TestCase
from django.utils import translation, encoding

import jinja2
import mock
from nose.tools import eq_

from caching import base, invalidation

cache = invalidation.cache

from testapp.models import Addon, User

if django.get_version().startswith('1.3'):
    class settings_patch(object):
        def __init__(self, **kwargs):
            self.options = kwargs

        def __enter__(self):
            self._old_settings = dict((k, getattr(settings, k, None)) for k in self.options)
            for k, v in self.options.items():
                setattr(settings, k, v)

        def __exit__(self, *args):
            for k in self.options:
                setattr(settings, k, self._old_settings[k])

    TestCase.settings = settings_patch


class CachingTestCase(TestCase):
    multi_db = True
    fixtures = ['tests/testapp/fixtures/testapp/test_cache.json']
    extra_apps = ['tests.testapp']

    def setUp(self):
        cache.clear()
        self.old_timeout = base.TIMEOUT
        if getattr(settings, 'CACHE_MACHINE_USE_REDIS', False):
            invalidation.redis.flushall()

    def tearDown(self):
        base.TIMEOUT = self.old_timeout

    def test_flush_key(self):
        """flush_key should work for objects or strings."""
        a = Addon.objects.get(id=1)
        eq_(base.flush_key(a.cache_key), base.flush_key(a))

    def test_cache_key(self):
        a = Addon.objects.get(id=1)
        eq_(a.cache_key, 'o:testapp.addon:1:default')

        keys = set((a.cache_key, a.author1.cache_key, a.author2.cache_key))
        eq_(set(a._cache_keys()), keys)

    def test_cache(self):
        """Basic cache test: second get comes from cache."""
        assert Addon.objects.get(id=1).from_cache is False
        assert Addon.objects.get(id=1).from_cache is True

    def test_filter_cache(self):
        assert Addon.objects.filter(id=1)[0].from_cache is False
        assert Addon.objects.filter(id=1)[0].from_cache is True

    def test_slice_cache(self):
        assert Addon.objects.filter(id=1)[:1][0].from_cache is False
        assert Addon.objects.filter(id=1)[:1][0].from_cache is True

    def test_invalidation(self):
        assert Addon.objects.get(id=1).from_cache is False
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is False

        assert Addon.objects.get(id=1).from_cache is True
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is True

        a.save()
        assert Addon.objects.get(id=1).from_cache is False
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is False

        assert Addon.objects.get(id=1).from_cache is True
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is True

    def test_invalidation_cross_locale(self):
        assert Addon.objects.get(id=1).from_cache is False
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is False

        assert Addon.objects.get(id=1).from_cache is True
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is True

        # Do query & invalidation in a different locale.
        old_locale = translation.get_language()
        translation.activate('fr')
        assert Addon.objects.get(id=1).from_cache is True
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is True

        a.save()

        translation.activate(old_locale)
        assert Addon.objects.get(id=1).from_cache is False
        a = [x for x in Addon.objects.all() if x.id == 1][0]
        assert a.from_cache is False

    def test_fk_invalidation(self):
        """When an object is invalidated, its foreign keys get invalidated."""
        a = Addon.objects.get(id=1)
        assert User.objects.get(name='clouseroo').from_cache is False
        a.save()

        assert User.objects.get(name='clouseroo').from_cache is False

    def test_fk_parent_invalidation(self):
        """When a foreign key changes, any parent objects get invalidated."""
        assert Addon.objects.get(id=1).from_cache is False
        a = Addon.objects.get(id=1)
        assert a.from_cache is True

        u = User.objects.get(id=a.author1.id)
        assert u.from_cache is True
        u.name = 'fffuuu'
        u.save()

        assert User.objects.get(id=a.author1.id).from_cache is False
        a = Addon.objects.get(id=1)
        assert a.from_cache is False
        eq_(a.author1.name, 'fffuuu')

    def test_raw_cache(self):
        sql = 'SELECT * FROM %s WHERE id = 1' % Addon._meta.db_table
        raw = list(Addon.objects.raw(sql))
        eq_(len(raw), 1)
        raw_addon = raw[0]
        a = Addon.objects.get(id=1)
        for field in Addon._meta.fields:
            eq_(getattr(a, field.name), getattr(raw_addon, field.name))
        assert raw_addon.from_cache is False

        cached = list(Addon.objects.raw(sql))
        eq_(len(cached), 1)
        cached_addon = cached[0]
        a = Addon.objects.get(id=1)
        for field in Addon._meta.fields:
            eq_(getattr(a, field.name), getattr(cached_addon, field.name))
        assert cached_addon.from_cache is True

    def test_raw_cache_params(self):
        """Make sure the query params are included in the cache key."""
        sql = 'SELECT * from %s WHERE id = %%s' % Addon._meta.db_table
        raw = list(Addon.objects.raw(sql, [1]))[0]
        eq_(raw.id, 1)

        raw2 = list(Addon.objects.raw(sql, [2]))[0]
        eq_(raw2.id, 2)

    @mock.patch('caching.base.CacheMachine')
    def test_raw_nocache(self, CacheMachine):
        base.TIMEOUT = 60
        sql = 'SELECT * FROM %s WHERE id = 1' % Addon._meta.db_table
        raw = list(Addon.objects.raw(sql, timeout=base.NO_CACHE))
        eq_(len(raw), 1)
        raw_addon = raw[0]
        assert not hasattr(raw_addon, 'from_cache')
        assert not CacheMachine.called

    @mock.patch('caching.base.cache')
    def test_count_cache(self, cache_mock):
        base.TIMEOUT = 60
        cache_mock.scheme = 'memcached'
        cache_mock.get.return_value = None

        q = Addon.objects.all()
        count = q.count()

        args, kwargs = cache_mock.set.call_args
        key, value, timeout = args
        eq_(value, 2)
        eq_(timeout, 60)

    @mock.patch('caching.base.cached')
    def test_count_none_timeout(self, cached_mock):
        base.TIMEOUT = base.NO_CACHE
        Addon.objects.count()
        eq_(cached_mock.call_count, 0)

    @mock.patch('caching.base.cached')
    def test_count_nocache(self, cached_mock):
        base.TIMEOUT = 60
        Addon.objects.no_cache().count()
        eq_(cached_mock.call_count, 0)

    def test_queryset_flush_list(self):
        """Check that we're making a flush list for the queryset."""
        q = Addon.objects.all()
        objects = list(q)  # Evaluate the queryset so it gets cached.
        base.invalidator.add_to_flush_list({q.flush_key(): ['remove-me']})
        cache.set('remove-me', 15)

        Addon.objects.invalidate(objects[0])
        assert cache.get(q.flush_key()) is None
        assert cache.get('remove-me') is None

    def test_jinja_cache_tag_queryset(self):
        env = jinja2.Environment(extensions=['caching.ext.cache'])
        def check(q, expected):
            t = env.from_string(
                "{% cache q %}{% for x in q %}{{ x.id }}:{{ x.val }};"
                "{% endfor %}{% endcache %}")
            eq_(t.render(q=q), expected)

        # Get the template in cache, then hijack iterator to make sure we're
        # hitting the cached fragment.
        check(Addon.objects.all(), '1:42;2:42;')
        qs = Addon.objects.all()
        qs.iterator = mock.Mock()
        check(qs, '1:42;2:42;')
        assert not qs.iterator.called

        # Make changes, make sure we dropped the cached fragment.
        a = Addon.objects.get(id=1)
        a.val = 17
        a.save()

        q = Addon.objects.all()
        flush = cache.get(q.flush_key())
        assert cache.get(q.flush_key()) is None

        check(Addon.objects.all(), '1:17;2:42;')
        qs = Addon.objects.all()
        qs.iterator = mock.Mock()
        check(qs, '1:17;2:42;')

    def test_jinja_cache_tag_object(self):
        env = jinja2.Environment(extensions=['caching.ext.cache'])
        addon = Addon.objects.get(id=1)

        def check(obj, expected):
            t = env.from_string(
                '{% cache obj, 30 %}{{ obj.id }}:{{ obj.val }}{% endcache %}')
            eq_(t.render(obj=obj), expected)

        check(addon, '1:42')
        addon.val = 17
        addon.save()
        check(addon, '1:17')

    def test_jinja_multiple_tags(self):
        env = jinja2.Environment(extensions=['caching.ext.cache'])
        addon = Addon.objects.get(id=1)
        template = ("{% cache obj %}{{ obj.id }}{% endcache %}\n"
                    "{% cache obj %}{{ obj.val }}{% endcache %}")

        def check(obj, expected):
            t = env.from_string(template)
            eq_(t.render(obj=obj), expected)

        check(addon, '1\n42')
        addon.val = 17
        addon.save()
        check(addon, '1\n17')

    def test_jinja_cache_tag_extra(self):
        env = jinja2.Environment(extensions=['caching.ext.cache'])
        addon = Addon.objects.get(id=1)

        template = ('{% cache obj, extra=[obj.key] %}{{ obj.id }}:'
                    '{{ obj.key }}{% endcache %}')

        def check(obj, expected):
            t = env.from_string(template)
            eq_(t.render(obj=obj), expected)

        addon.key = 1
        check(addon, '1:1')
        addon.key = 2
        check(addon, '1:2')

        template = ('{% cache obj, 10, extra=[obj.key] %}{{ obj.id }}:'
                    '{{ obj.key }}{% endcache %}')
        addon.key = 1
        check(addon, '1:1')
        addon.key = 2
        check(addon, '1:2')

    def test_cached_with(self):
        counter = mock.Mock()
        def expensive():
            counter()
            return counter.call_count

        a = Addon.objects.get(id=1)
        f = lambda: base.cached_with(a, expensive, 'key')

        # Only gets called once.
        eq_(f(), 1)
        eq_(f(), 1)

        # Switching locales does not reuse the cache.
        old_locale = translation.get_language()
        translation.activate('fr')
        eq_(f(), 2)

        # Called again after flush.
        a.save()
        eq_(f(), 3)

        translation.activate(old_locale)
        eq_(f(), 4)

        counter.reset_mock()
        q = Addon.objects.filter(id=1)
        f = lambda: base.cached_with(q, expensive, 'key')

        # Only gets called once.
        eq_(f(), 1)
        eq_(f(), 1)

        # Called again after flush.
        list(q)[0].save()
        eq_(f(), 2)
        eq_(f(), 2)

    def test_cached_with_bad_object(self):
        """cached_with shouldn't fail if the object is missing a cache key."""
        counter = mock.Mock()
        def f():
            counter()
            return counter.call_count

        eq_(base.cached_with([], f, 'key'), 1)

    def test_cached_with_unicode(self):
        u = ':'.join(map(encoding.smart_str, [u'תיאור אוסף']))
        obj = mock.Mock()
        obj.query_key.return_value = u'xxx'
        obj.flush_key.return_value = 'key'
        f = lambda: 1
        eq_(base.cached_with(obj, f, 'adf:%s' % u), 1)

    def test_cached_method(self):
        a = Addon.objects.get(id=1)
        eq_(a.calls(), (1, 1))
        eq_(a.calls(), (1, 1))

        a.save()
        # Still returns 1 since the object has it's own local cache.
        eq_(a.calls(), (1, 1))
        eq_(a.calls(3), (3, 2))

        a = Addon.objects.get(id=1)
        eq_(a.calls(), (1, 3))
        eq_(a.calls(4), (4, 4))
        eq_(a.calls(3), (3, 2))

        b = Addon.objects.create(id=5, val=32, author1_id=1, author2_id=2)
        eq_(b.calls(), (1, 5))

        # Make sure we're updating the wrapper's docstring.
        eq_(b.calls.__doc__, Addon.calls.__doc__)

    @mock.patch('caching.base.CacheMachine')
    def test_no_cache_from_manager(self, CacheMachine):
        a = Addon.objects.no_cache().get(id=1)
        eq_(a.id, 1)
        assert not hasattr(a, 'from_cache')
        assert not CacheMachine.called

    @mock.patch('caching.base.CacheMachine')
    def test_no_cache_from_queryset(self, CacheMachine):
        a = Addon.objects.all().no_cache().get(id=1)
        eq_(a.id, 1)
        assert not hasattr(a, 'from_cache')
        assert not CacheMachine.called

    def test_timeout_from_manager(self):
        q = Addon.objects.cache(12).filter(id=1)
        eq_(q.timeout, 12)
        a = q.get()
        assert hasattr(a, 'from_cache')
        eq_(a.id, 1)

    def test_timeout_from_queryset(self):
        q = Addon.objects.all().cache(12).filter(id=1)
        eq_(q.timeout, 12)
        a = q.get()
        assert hasattr(a, 'from_cache')
        eq_(a.id, 1)

    def test_cache_and_no_cache(self):
        """Whatever happens last sticks."""
        q = Addon.objects.no_cache().cache(12).filter(id=1)
        eq_(q.timeout, 12)

        no_cache = q.no_cache()

        # The querysets don't share anything.
        eq_(q.timeout, 12)
        assert no_cache.timeout != 12

        assert not hasattr(no_cache.get(), 'from_cache')

        eq_(q.get().id, 1)
        assert hasattr(q.get(), 'from_cache')

    @mock.patch('caching.base.cache')
    def test_cache_machine_timeout(self, cache):
        cache.scheme = 'memcached'
        cache.get.return_value = None
        cache.get_many.return_value = {}

        a = Addon.objects.cache(12).get(id=1)
        eq_(a.id, 1)

        assert cache.add.called
        args, kwargs = cache.add.call_args
        eq_(kwargs, {'timeout': 12})

    def test_unicode_key(self):
        list(User.objects.filter(name=u'ümlaüt'))

    def test_empty_in(self):
        # Raised an exception before fixing #2.
        eq_([], list(User.objects.filter(pk__in=[])))

    def test_empty_queryset(self):
        for k in (1, 1):
            with self.assertNumQueries(k):
                eq_(len(Addon.objects.filter(pk=42)), 0)

    @mock.patch('caching.base.CACHE_EMPTY_QUERYSETS', True)
    def test_cache_empty_queryset(self):
        for k in (1, 0):
            with self.assertNumQueries(k):
                eq_(len(Addon.objects.filter(pk=42)), 0)

    def test_invalidate_empty_queryset(self):
        u = User.objects.create()
        eq_(list(u.addon_set.all()), [])
        Addon.objects.create(val=42, author1=u, author2=u)
        eq_([a.val for a in u.addon_set.all()], [42])

    def test_invalidate_new_object(self):
        u = User.objects.create()
        Addon.objects.create(val=42, author1=u, author2=u)
        eq_([a.val for a in u.addon_set.all()], [42])
        Addon.objects.create(val=17, author1=u, author2=u)
        eq_([a.val for a in u.addon_set.all()], [42, 17])

    def test_make_key_unicode(self):
        translation.activate(u'en-US')
        f = 'fragment\xe9\x9b\xbb\xe8\x85\xa6\xe7\x8e'
        # This would crash with a unicode error.
        base.make_key(f, with_locale=True)
        translation.deactivate()

    @mock.patch('caching.invalidation.cache.get_many')
    def test_get_flush_lists_none(self, cache_mock):
        if not getattr(settings, 'CACHE_MACHINE_USE_REDIS', False):
            cache_mock.return_value.values.return_value = [None, [1]]
            eq_(base.invalidator.get_flush_lists(None), set([1]))

    def test_multidb_cache(self):
        """ Test where master and slave DB result in two different cache keys """
        assert Addon.objects.get(id=1).from_cache is False
        assert Addon.objects.get(id=1).from_cache is True

        from_slave = Addon.objects.using('slave').get(id=1)
        assert from_slave.from_cache is False
        assert from_slave._state.db == 'slave'

    def test_multidb_fetch_by_id(self):
        """ Test where master and slave DB result in two different cache keys with FETCH_BY_ID"""
        with self.settings(FETCH_BY_ID=True):
            assert Addon.objects.get(id=1).from_cache is False
            assert Addon.objects.get(id=1).from_cache is True

            from_slave = Addon.objects.using('slave').get(id=1)
            assert from_slave.from_cache is False
            assert from_slave._state.db == 'slave'

########NEW FILE########
