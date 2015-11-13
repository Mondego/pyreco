__FILENAME__ = cache
"""This package contains the "front end" classes and functions
for Beaker caching.

Included are the :class:`.Cache` and :class:`.CacheManager` classes,
as well as the function decorators :func:`.region_decorate`,
:func:`.region_invalidate`.

"""
import warnings

import beaker.container as container
import beaker.util as util
from beaker.crypto.util import sha1
from beaker.exceptions import BeakerException, InvalidCacheBackendError
from beaker.synchronization import _threading

import beaker.ext.memcached as memcached
import beaker.ext.database as database
import beaker.ext.sqla as sqla
import beaker.ext.google as google

# Initialize the cache region dict
cache_regions = {}
"""Dictionary of 'region' arguments.

A "region" is a string name that refers to a series of cache
configuration arguments.    An application may have multiple
"regions" - one which stores things in a memory cache, one
which writes data to files, etc.

The dictionary stores string key names mapped to dictionaries
of configuration arguments.  Example::

    from beaker.cache import cache_regions
    cache_regions.update({
        'short_term':{
            'expire':'60',
            'type':'memory'
        },
        'long_term':{
            'expire':'1800',
            'type':'dbm',
            'data_dir':'/tmp',
        }
    })
"""


cache_managers = {}


class _backends(object):
    initialized = False

    def __init__(self, clsmap):
        self._clsmap = clsmap
        self._mutex = _threading.Lock()

    def __getitem__(self, key):
        try:
            return self._clsmap[key]
        except KeyError, e:
            if not self.initialized:
                self._mutex.acquire()
                try:
                    if not self.initialized:
                        self._init()
                        self.initialized = True

                    return self._clsmap[key]
                finally:
                    self._mutex.release()

            raise e

    def _init(self):
        try:
            import pkg_resources

            # Load up the additional entry point defined backends
            for entry_point in pkg_resources.iter_entry_points('beaker.backends'):
                try:
                    namespace_manager = entry_point.load()
                    name = entry_point.name
                    if name in self._clsmap:
                        raise BeakerException("NamespaceManager name conflict,'%s' "
                                              "already loaded" % name)
                    self._clsmap[name] = namespace_manager
                except (InvalidCacheBackendError, SyntaxError):
                    # Ignore invalid backends
                    pass
                except:
                    import sys
                    from pkg_resources import DistributionNotFound
                    # Warn when there's a problem loading a NamespaceManager
                    if not isinstance(sys.exc_info()[1], DistributionNotFound):
                        import traceback
                        from StringIO import StringIO
                        tb = StringIO()
                        traceback.print_exc(file=tb)
                        warnings.warn(
                            "Unable to load NamespaceManager "
                            "entry point: '%s': %s" % (
                                        entry_point,
                                        tb.getvalue()),
                                        RuntimeWarning, 2)
        except ImportError:
            pass

# Initialize the basic available backends
clsmap = _backends({
          'memory': container.MemoryNamespaceManager,
          'dbm': container.DBMNamespaceManager,
          'file': container.FileNamespaceManager,
          'ext:memcached': memcached.MemcachedNamespaceManager,
          'ext:database': database.DatabaseNamespaceManager,
          'ext:sqla': sqla.SqlaNamespaceManager,
          'ext:google': google.GoogleNamespaceManager,
          })


def cache_region(region, *args):
    """Decorate a function such that its return result is cached,
    using a "region" to indicate the cache arguments.

    Example::

        from beaker.cache import cache_regions, cache_region

        # configure regions
        cache_regions.update({
            'short_term':{
                'expire':'60',
                'type':'memory'
            }
        })

        @cache_region('short_term', 'load_things')
        def load(search_term, limit, offset):
            '''Load from a database given a search term, limit, offset.'''
            return database.query(search_term)[offset:offset + limit]

    The decorator can also be used with object methods.  The ``self``
    argument is not part of the cache key.  This is based on the
    actual string name ``self`` being in the first argument
    position (new in 1.6)::

        class MyThing(object):
            @cache_region('short_term', 'load_things')
            def load(self, search_term, limit, offset):
                '''Load from a database given a search term, limit, offset.'''
                return database.query(search_term)[offset:offset + limit]

    Classmethods work as well - use ``cls`` as the name of the class argument,
    and place the decorator around the function underneath ``@classmethod``
    (new in 1.6)::

        class MyThing(object):
            @classmethod
            @cache_region('short_term', 'load_things')
            def load(cls, search_term, limit, offset):
                '''Load from a database given a search term, limit, offset.'''
                return database.query(search_term)[offset:offset + limit]

    :param region: String name of the region corresponding to the desired
      caching arguments, established in :attr:`.cache_regions`.

    :param \*args: Optional ``str()``-compatible arguments which will uniquely
      identify the key used by this decorated function, in addition
      to the positional arguments passed to the function itself at call time.
      This is recommended as it is needed to distinguish between any two functions
      or methods that have the same name (regardless of parent class or not).

    .. note::

        The function being decorated must only be called with
        positional arguments, and the arguments must support
        being stringified with ``str()``.  The concatenation
        of the ``str()`` version of each argument, combined
        with that of the ``*args`` sent to the decorator,
        forms the unique cache key.

    .. note::

        When a method on a class is decorated, the ``self`` or ``cls``
        argument in the first position is
        not included in the "key" used for caching.   New in 1.6.

    """
    return _cache_decorate(args, None, None, region)


def region_invalidate(namespace, region, *args):
    """Invalidate a cache region corresponding to a function
    decorated with :func:`.cache_region`.

    :param namespace: The namespace of the cache to invalidate.  This is typically
      a reference to the original function (as returned by the :func:`.cache_region`
      decorator), where the :func:`.cache_region` decorator applies a "memo" to
      the function in order to locate the string name of the namespace.

    :param region: String name of the region used with the decorator.  This can be
     ``None`` in the usual case that the decorated function itself is passed,
     not the string name of the namespace.

    :param args: Stringifyable arguments that are used to locate the correct
     key.  This consists of the ``*args`` sent to the :func:`.cache_region`
     decorator itself, plus the ``*args`` sent to the function itself
     at runtime.

    Example::

        from beaker.cache import cache_regions, cache_region, region_invalidate

        # configure regions
        cache_regions.update({
            'short_term':{
                'expire':'60',
                'type':'memory'
            }
        })

        @cache_region('short_term', 'load_data')
        def load(search_term, limit, offset):
            '''Load from a database given a search term, limit, offset.'''
            return database.query(search_term)[offset:offset + limit]

        def invalidate_search(search_term, limit, offset):
            '''Invalidate the cached storage for a given search term, limit, offset.'''
            region_invalidate(load, 'short_term', 'load_data', search_term, limit, offset)

    Note that when a method on a class is decorated, the first argument ``cls``
    or ``self`` is not included in the cache key.  This means you don't send
    it to :func:`.region_invalidate`::

        class MyThing(object):
            @cache_region('short_term', 'some_data')
            def load(self, search_term, limit, offset):
                '''Load from a database given a search term, limit, offset.'''
                return database.query(search_term)[offset:offset + limit]

            def invalidate_search(self, search_term, limit, offset):
                '''Invalidate the cached storage for a given search term, limit, offset.'''
                region_invalidate(self.load, 'short_term', 'some_data', search_term, limit, offset)

    """
    if callable(namespace):
        if not region:
            region = namespace._arg_region
        namespace = namespace._arg_namespace

    if not region:
        raise BeakerException("Region or callable function "
                                    "namespace is required")
    else:
        region = cache_regions[region]

    cache = Cache._get_cache(namespace, region)
    _cache_decorator_invalidate(cache, region['key_length'], args)


class Cache(object):
    """Front-end to the containment API implementing a data cache.

    :param namespace: the namespace of this Cache

    :param type: type of cache to use

    :param expire: seconds to keep cached data

    :param expiretime: seconds to keep cached data (legacy support)

    :param starttime: time when cache was cache was

    """
    def __init__(self, namespace, type='memory', expiretime=None,
                 starttime=None, expire=None, **nsargs):
        try:
            cls = clsmap[type]
            if isinstance(cls, InvalidCacheBackendError):
                raise cls
        except KeyError:
            raise TypeError("Unknown cache implementation %r" % type)
        self.namespace_name = namespace
        self.namespace = cls(namespace, **nsargs)
        self.expiretime = expiretime or expire
        self.starttime = starttime
        self.nsargs = nsargs

    @classmethod
    def _get_cache(cls, namespace, kw):
        key = namespace + str(kw)
        try:
            return cache_managers[key]
        except KeyError:
            cache_managers[key] = cache = cls(namespace, **kw)
            return cache

    def put(self, key, value, **kw):
        self._get_value(key, **kw).set_value(value)
    set_value = put

    def get(self, key, **kw):
        """Retrieve a cached value from the container"""
        return self._get_value(key, **kw).get_value()
    get_value = get

    def remove_value(self, key, **kw):
        mycontainer = self._get_value(key, **kw)
        mycontainer.clear_value()
    remove = remove_value

    def _get_value(self, key, **kw):
        if isinstance(key, unicode):
            key = key.encode('ascii', 'backslashreplace')

        if 'type' in kw:
            return self._legacy_get_value(key, **kw)

        kw.setdefault('expiretime', self.expiretime)
        kw.setdefault('starttime', self.starttime)

        return container.Value(key, self.namespace, **kw)

    @util.deprecated("Specifying a "
            "'type' and other namespace configuration with cache.get()/put()/etc. "
            "is deprecated. Specify 'type' and other namespace configuration to "
            "cache_manager.get_cache() and/or the Cache constructor instead.")
    def _legacy_get_value(self, key, type, **kw):
        expiretime = kw.pop('expiretime', self.expiretime)
        starttime = kw.pop('starttime', None)
        createfunc = kw.pop('createfunc', None)
        kwargs = self.nsargs.copy()
        kwargs.update(kw)
        c = Cache(self.namespace.namespace, type=type, **kwargs)
        return c._get_value(key, expiretime=expiretime, createfunc=createfunc,
                            starttime=starttime)

    def clear(self):
        """Clear all the values from the namespace"""
        self.namespace.remove()

    # dict interface
    def __getitem__(self, key):
        return self.get(key)

    def __contains__(self, key):
        return self._get_value(key).has_current_value()

    def has_key(self, key):
        return key in self

    def __delitem__(self, key):
        self.remove_value(key)

    def __setitem__(self, key, value):
        self.put(key, value)


class CacheManager(object):
    def __init__(self, **kwargs):
        """Initialize a CacheManager object with a set of options

        Options should be parsed with the
        :func:`~beaker.util.parse_cache_config_options` function to
        ensure only valid options are used.

        """
        self.kwargs = kwargs
        self.regions = kwargs.pop('cache_regions', {})

        # Add these regions to the module global
        cache_regions.update(self.regions)

    def get_cache(self, name, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        return Cache._get_cache(name, kw)

    def get_cache_region(self, name, region):
        if region not in self.regions:
            raise BeakerException('Cache region not configured: %s' % region)
        kw = self.regions[region]
        return Cache._get_cache(name, kw)

    def region(self, region, *args):
        """Decorate a function to cache itself using a cache region

        The region decorator requires arguments if there are more than
        two of the same named function, in the same module. This is
        because the namespace used for the functions cache is based on
        the functions name and the module.


        Example::

            # Assuming a cache object is available like:
            cache = CacheManager(dict_of_config_options)


            def populate_things():

                @cache.region('short_term', 'some_data')
                def load(search_term, limit, offset):
                    return load_the_data(search_term, limit, offset)

                return load('rabbits', 20, 0)

        .. note::

            The function being decorated must only be called with
            positional arguments.

        """
        return cache_region(region, *args)

    def region_invalidate(self, namespace, region, *args):
        """Invalidate a cache region namespace or decorated function

        This function only invalidates cache spaces created with the
        cache_region decorator.

        :param namespace: Either the namespace of the result to invalidate, or the
           cached function

        :param region: The region the function was cached to. If the function was
            cached to a single region then this argument can be None

        :param args: Arguments that were used to differentiate the cached
            function as well as the arguments passed to the decorated
            function

        Example::

            # Assuming a cache object is available like:
            cache = CacheManager(dict_of_config_options)

            def populate_things(invalidate=False):

                @cache.region('short_term', 'some_data')
                def load(search_term, limit, offset):
                    return load_the_data(search_term, limit, offset)

                # If the results should be invalidated first
                if invalidate:
                    cache.region_invalidate(load, None, 'some_data',
                                            'rabbits', 20, 0)
                return load('rabbits', 20, 0)


        """
        return region_invalidate(namespace, region, *args)

    def cache(self, *args, **kwargs):
        """Decorate a function to cache itself with supplied parameters

        :param args: Used to make the key unique for this function, as in region()
            above.

        :param kwargs: Parameters to be passed to get_cache(), will override defaults

        Example::

            # Assuming a cache object is available like:
            cache = CacheManager(dict_of_config_options)


            def populate_things():

                @cache.cache('mycache', expire=15)
                def load(search_term, limit, offset):
                    return load_the_data(search_term, limit, offset)

                return load('rabbits', 20, 0)

        .. note::

            The function being decorated must only be called with
            positional arguments.

        """
        return _cache_decorate(args, self, kwargs, None)

    def invalidate(self, func, *args, **kwargs):
        """Invalidate a cache decorated function

        This function only invalidates cache spaces created with the
        cache decorator.

        :param func: Decorated function to invalidate

        :param args: Used to make the key unique for this function, as in region()
            above.

        :param kwargs: Parameters that were passed for use by get_cache(), note that
            this is only required if a ``type`` was specified for the
            function

        Example::

            # Assuming a cache object is available like:
            cache = CacheManager(dict_of_config_options)


            def populate_things(invalidate=False):

                @cache.cache('mycache', type="file", expire=15)
                def load(search_term, limit, offset):
                    return load_the_data(search_term, limit, offset)

                # If the results should be invalidated first
                if invalidate:
                    cache.invalidate(load, 'mycache', 'rabbits', 20, 0, type="file")
                return load('rabbits', 20, 0)

        """
        namespace = func._arg_namespace

        cache = self.get_cache(namespace, **kwargs)
        if hasattr(func, '_arg_region'):
            key_length = cache_regions[func._arg_region]['key_length']
        else:
            key_length = kwargs.pop('key_length', 250)
        _cache_decorator_invalidate(cache, key_length, args)


def _cache_decorate(deco_args, manager, kwargs, region):
    """Return a caching function decorator."""

    cache = [None]

    def decorate(func):
        namespace = util.func_namespace(func)
        skip_self = util.has_self_arg(func)

        def cached(*args):
            if not cache[0]:
                if region is not None:
                    if region not in cache_regions:
                        raise BeakerException(
                            'Cache region not configured: %s' % region)
                    reg = cache_regions[region]
                    if not reg.get('enabled', True):
                        return func(*args)
                    cache[0] = Cache._get_cache(namespace, reg)
                elif manager:
                    cache[0] = manager.get_cache(namespace, **kwargs)
                else:
                    raise Exception("'manager + kwargs' or 'region' "
                                    "argument is required")

            if skip_self:
                try:
                    cache_key = " ".join(map(str, deco_args + args[1:]))
                except UnicodeEncodeError:
                    cache_key = " ".join(map(unicode, deco_args + args[1:]))
            else:
                try:
                    cache_key = " ".join(map(str, deco_args + args))
                except UnicodeEncodeError:
                    cache_key = " ".join(map(unicode, deco_args + args))
            if region:
                key_length = cache_regions[region]['key_length']
            else:
                key_length = kwargs.pop('key_length', 250)
            if len(cache_key) + len(namespace) > int(key_length):
                if util.py3k:
                    cache_key = cache_key.encode('utf-8')
                cache_key = sha1(cache_key).hexdigest()

            def go():
                return func(*args)

            return cache[0].get_value(cache_key, createfunc=go)
        cached._arg_namespace = namespace
        if region is not None:
            cached._arg_region = region
        return cached
    return decorate


def _cache_decorator_invalidate(cache, key_length, args):
    """Invalidate a cache key based on function arguments."""

    try:
        cache_key = " ".join(map(str, args))
    except UnicodeEncodeError:
        cache_key = " ".join(map(unicode, args))
    if len(cache_key) + len(cache.namespace_name) > key_length:
        if util.py3k:
            cache_key = cache_key.encode('utf-8')
        cache_key = sha1(cache_key).hexdigest()
    cache.remove_value(cache_key)

########NEW FILE########
__FILENAME__ = container
"""Container and Namespace classes"""

import beaker.util as util
if util.py3k:
    try:
        import dbm as anydbm
    except:
        import dumbdbm as anydbm
else:
    import anydbm
import cPickle
import logging
import os
import time

from beaker.exceptions import CreationAbortedError, MissingCacheParameter
from beaker.synchronization import _threading, file_synchronizer, \
     mutex_synchronizer, NameLock, null_synchronizer

__all__ = ['Value', 'Container', 'ContainerContext',
           'MemoryContainer', 'DBMContainer', 'NamespaceManager',
           'MemoryNamespaceManager', 'DBMNamespaceManager', 'FileContainer',
           'OpenResourceNamespaceManager',
           'FileNamespaceManager', 'CreationAbortedError']


logger = logging.getLogger('beaker.container')
if logger.isEnabledFor(logging.DEBUG):
    debug = logger.debug
else:
    def debug(message, *args):
        pass


class NamespaceManager(object):
    """Handles dictionary operations and locking for a namespace of
    values.

    :class:`.NamespaceManager` provides a dictionary-like interface,
    implementing ``__getitem__()``, ``__setitem__()``, and
    ``__contains__()``, as well as functions related to lock
    acquisition.

    The implementation for setting and retrieving the namespace data is
    handled by subclasses.

    NamespaceManager may be used alone, or may be accessed by
    one or more :class:`.Value` objects.  :class:`.Value` objects provide per-key
    services like expiration times and automatic recreation of values.

    Multiple NamespaceManagers created with a particular name will all
    share access to the same underlying datasource and will attempt to
    synchronize against a common mutex object.  The scope of this
    sharing may be within a single process or across multiple
    processes, depending on the type of NamespaceManager used.

    The NamespaceManager itself is generally threadsafe, except in the
    case of the DBMNamespaceManager in conjunction with the gdbm dbm
    implementation.

    """

    @classmethod
    def _init_dependencies(cls):
        """Initialize module-level dependent libraries required
        by this :class:`.NamespaceManager`."""

    def __init__(self, namespace):
        self._init_dependencies()
        self.namespace = namespace

    def get_creation_lock(self, key):
        """Return a locking object that is used to synchronize
        multiple threads or processes which wish to generate a new
        cache value.

        This function is typically an instance of
        :class:`.FileSynchronizer`, :class:`.ConditionSynchronizer`,
        or :class:`.null_synchronizer`.

        The creation lock is only used when a requested value
        does not exist, or has been expired, and is only used
        by the :class:`.Value` key-management object in conjunction
        with a "createfunc" value-creation function.

        """
        raise NotImplementedError()

    def do_remove(self):
        """Implement removal of the entire contents of this
        :class:`.NamespaceManager`.

        e.g. for a file-based namespace, this would remove
        all the files.

        The front-end to this method is the
        :meth:`.NamespaceManager.remove` method.

        """
        raise NotImplementedError()

    def acquire_read_lock(self):
        """Establish a read lock.

        This operation is called before a key is read.    By
        default the function does nothing.

        """

    def release_read_lock(self):
        """Release a read lock.

        This operation is called after a key is read.    By
        default the function does nothing.

        """

    def acquire_write_lock(self, wait=True, replace=False):
        """Establish a write lock.

        This operation is called before a key is written.
        A return value of ``True`` indicates the lock has
        been acquired.

        By default the function returns ``True`` unconditionally.

        'replace' is a hint indicating the full contents
        of the namespace may be safely discarded. Some backends
        may implement this (i.e. file backend won't unpickle the
        current contents).

        """
        return True

    def release_write_lock(self):
        """Release a write lock.

        This operation is called after a new value is written.
        By default this function does nothing.

        """

    def has_key(self, key):
        """Return ``True`` if the given key is present in this
        :class:`.Namespace`.
        """
        return self.__contains__(key)

    def __getitem__(self, key):
        raise NotImplementedError()

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def set_value(self, key, value, expiretime=None):
        """Sets a value in this :class:`.NamespaceManager`.

        This is the same as ``__setitem__()``, but
        also allows an expiration time to be passed
        at the same time.

        """
        self[key] = value

    def __contains__(self, key):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def keys(self):
        """Return the list of all keys.

        This method may not be supported by all
        :class:`.NamespaceManager` implementations.

        """
        raise NotImplementedError()

    def remove(self):
        """Remove the entire contents of this
        :class:`.NamespaceManager`.

        e.g. for a file-based namespace, this would remove
        all the files.
        """
        self.do_remove()


class OpenResourceNamespaceManager(NamespaceManager):
    """A NamespaceManager where read/write operations require opening/
    closing of a resource which is possibly mutexed.

    """
    def __init__(self, namespace):
        NamespaceManager.__init__(self, namespace)
        self.access_lock = self.get_access_lock()
        self.openers = 0
        self.mutex = _threading.Lock()

    def get_access_lock(self):
        raise NotImplementedError()

    def do_open(self, flags, replace):
        raise NotImplementedError()

    def do_close(self):
        raise NotImplementedError()

    def acquire_read_lock(self):
        self.access_lock.acquire_read_lock()
        try:
            self.open('r', checkcount=True)
        except:
            self.access_lock.release_read_lock()
            raise

    def release_read_lock(self):
        try:
            self.close(checkcount=True)
        finally:
            self.access_lock.release_read_lock()

    def acquire_write_lock(self, wait=True, replace=False):
        r = self.access_lock.acquire_write_lock(wait)
        try:
            if (wait or r):
                self.open('c', checkcount=True, replace=replace)
            return r
        except:
            self.access_lock.release_write_lock()
            raise

    def release_write_lock(self):
        try:
            self.close(checkcount=True)
        finally:
            self.access_lock.release_write_lock()

    def open(self, flags, checkcount=False, replace=False):
        self.mutex.acquire()
        try:
            if checkcount:
                if self.openers == 0:
                    self.do_open(flags, replace)
                self.openers += 1
            else:
                self.do_open(flags, replace)
                self.openers = 1
        finally:
            self.mutex.release()

    def close(self, checkcount=False):
        self.mutex.acquire()
        try:
            if checkcount:
                self.openers -= 1
                if self.openers == 0:
                    self.do_close()
            else:
                if self.openers > 0:
                    self.do_close()
                self.openers = 0
        finally:
            self.mutex.release()

    def remove(self):
        self.access_lock.acquire_write_lock()
        try:
            self.close(checkcount=False)
            self.do_remove()
        finally:
            self.access_lock.release_write_lock()


class Value(object):
    """Implements synchronization, expiration, and value-creation logic
    for a single value stored in a :class:`.NamespaceManager`.

    """

    __slots__ = 'key', 'createfunc', 'expiretime', 'expire_argument', 'starttime', 'storedtime',\
                'namespace'

    def __init__(self, key, namespace, createfunc=None, expiretime=None, starttime=None):
        self.key = key
        self.createfunc = createfunc
        self.expire_argument = expiretime
        self.starttime = starttime
        self.storedtime = -1
        self.namespace = namespace

    def has_value(self):
        """return true if the container has a value stored.

        This is regardless of it being expired or not.

        """
        self.namespace.acquire_read_lock()
        try:
            return self.key in self.namespace
        finally:
            self.namespace.release_read_lock()

    def can_have_value(self):
        return self.has_current_value() or self.createfunc is not None

    def has_current_value(self):
        self.namespace.acquire_read_lock()
        try:
            has_value = self.key in self.namespace
            if has_value:
                try:
                    stored, expired, value = self._get_value()
                    return not self._is_expired(stored, expired)
                except KeyError:
                    pass
            return False
        finally:
            self.namespace.release_read_lock()

    def _is_expired(self, storedtime, expiretime):
        """Return true if this container's value is expired."""
        return (
            (
                self.starttime is not None and
                storedtime < self.starttime
            )
            or
            (
                expiretime is not None and
                time.time() >= expiretime + storedtime
            )
        )

    def get_value(self):
        self.namespace.acquire_read_lock()
        try:
            has_value = self.has_value()
            if has_value:
                try:
                    stored, expired, value = self._get_value()
                    if not self._is_expired(stored, expired):
                        return value
                except KeyError:
                    # guard against un-mutexed backends raising KeyError
                    has_value = False

            if not self.createfunc:
                raise KeyError(self.key)
        finally:
            self.namespace.release_read_lock()

        has_createlock = False
        creation_lock = self.namespace.get_creation_lock(self.key)
        if has_value:
            if not creation_lock.acquire(wait=False):
                debug("get_value returning old value while new one is created")
                return value
            else:
                debug("lock_creatfunc (didnt wait)")
                has_createlock = True

        if not has_createlock:
            debug("lock_createfunc (waiting)")
            creation_lock.acquire()
            debug("lock_createfunc (waited)")

        try:
            # see if someone created the value already
            self.namespace.acquire_read_lock()
            try:
                if self.has_value():
                    try:
                        stored, expired, value = self._get_value()
                        if not self._is_expired(stored, expired):
                            return value
                    except KeyError:
                        # guard against un-mutexed backends raising KeyError
                        pass
            finally:
                self.namespace.release_read_lock()

            debug("get_value creating new value")
            v = self.createfunc()
            self.set_value(v)
            return v
        finally:
            creation_lock.release()
            debug("released create lock")

    def _get_value(self):
        value = self.namespace[self.key]
        try:
            stored, expired, value = value
        except ValueError:
            if not len(value) == 2:
                raise
            # Old format: upgrade
            stored, value = value
            expired = self.expire_argument
            debug("get_value upgrading time %r expire time %r", stored, self.expire_argument)
            self.namespace.release_read_lock()
            self.set_value(value, stored)
            self.namespace.acquire_read_lock()
        except TypeError:
            # occurs when the value is None.  memcached
            # may yank the rug from under us in which case
            # that's the result
            raise KeyError(self.key)
        return stored, expired, value

    def set_value(self, value, storedtime=None):
        self.namespace.acquire_write_lock()
        try:
            if storedtime is None:
                storedtime = time.time()
            debug("set_value stored time %r expire time %r", storedtime, self.expire_argument)
            self.namespace.set_value(self.key, (storedtime, self.expire_argument, value))
        finally:
            self.namespace.release_write_lock()

    def clear_value(self):
        self.namespace.acquire_write_lock()
        try:
            debug("clear_value")
            if self.key in self.namespace:
                try:
                    del self.namespace[self.key]
                except KeyError:
                    # guard against un-mutexed backends raising KeyError
                    pass
            self.storedtime = -1
        finally:
            self.namespace.release_write_lock()


class AbstractDictionaryNSManager(NamespaceManager):
    """A subclassable NamespaceManager that places data in a dictionary.

    Subclasses should provide a "dictionary" attribute or descriptor
    which returns a dict-like object.   The dictionary will store keys
    that are local to the "namespace" attribute of this manager, so
    ensure that the dictionary will not be used by any other namespace.

    e.g.::

        import collections
        cached_data = collections.defaultdict(dict)

        class MyDictionaryManager(AbstractDictionaryNSManager):
            def __init__(self, namespace):
                AbstractDictionaryNSManager.__init__(self, namespace)
                self.dictionary = cached_data[self.namespace]

    The above stores data in a global dictionary called "cached_data",
    which is structured as a dictionary of dictionaries, keyed
    first on namespace name to a sub-dictionary, then on actual
    cache key to value.

    """

    def get_creation_lock(self, key):
        return NameLock(
            identifier="memorynamespace/funclock/%s/%s" %
                        (self.namespace, key),
            reentrant=True
        )

    def __getitem__(self, key):
        return self.dictionary[key]

    def __contains__(self, key):
        return self.dictionary.__contains__(key)

    def has_key(self, key):
        return self.dictionary.__contains__(key)

    def __setitem__(self, key, value):
        self.dictionary[key] = value

    def __delitem__(self, key):
        del self.dictionary[key]

    def do_remove(self):
        self.dictionary.clear()

    def keys(self):
        return self.dictionary.keys()


class MemoryNamespaceManager(AbstractDictionaryNSManager):
    """:class:`.NamespaceManager` that uses a Python dictionary for storage."""

    namespaces = util.SyncDict()

    def __init__(self, namespace, **kwargs):
        AbstractDictionaryNSManager.__init__(self, namespace)
        self.dictionary = MemoryNamespaceManager.\
                                namespaces.get(self.namespace, dict)


class DBMNamespaceManager(OpenResourceNamespaceManager):
    """:class:`.NamespaceManager` that uses ``dbm`` files for storage."""

    def __init__(self, namespace, dbmmodule=None, data_dir=None,
            dbm_dir=None, lock_dir=None,
            digest_filenames=True, **kwargs):
        self.digest_filenames = digest_filenames

        if not dbm_dir and not data_dir:
            raise MissingCacheParameter("data_dir or dbm_dir is required")
        elif dbm_dir:
            self.dbm_dir = dbm_dir
        else:
            self.dbm_dir = data_dir + "/container_dbm"
        util.verify_directory(self.dbm_dir)

        if not lock_dir and not data_dir:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        elif lock_dir:
            self.lock_dir = lock_dir
        else:
            self.lock_dir = data_dir + "/container_dbm_lock"
        util.verify_directory(self.lock_dir)

        self.dbmmodule = dbmmodule or anydbm

        self.dbm = None
        OpenResourceNamespaceManager.__init__(self, namespace)

        self.file = util.encoded_path(root=self.dbm_dir,
                                      identifiers=[self.namespace],
                                      extension='.dbm',
                                      digest_filenames=self.digest_filenames)

        debug("data file %s", self.file)
        self._checkfile()

    def get_access_lock(self):
        return file_synchronizer(identifier=self.namespace,
                                 lock_dir=self.lock_dir)

    def get_creation_lock(self, key):
        return file_synchronizer(
                    identifier="dbmcontainer/funclock/%s/%s" % (
                        self.namespace, key
                    ),
                    lock_dir=self.lock_dir
                )

    def file_exists(self, file):
        if os.access(file, os.F_OK):
            return True
        else:
            for ext in ('db', 'dat', 'pag', 'dir'):
                if os.access(file + os.extsep + ext, os.F_OK):
                    return True

        return False

    def _checkfile(self):
        if not self.file_exists(self.file):
            g = self.dbmmodule.open(self.file, 'c')
            g.close()

    def get_filenames(self):
        list = []
        if os.access(self.file, os.F_OK):
            list.append(self.file)

        for ext in ('pag', 'dir', 'db', 'dat'):
            if os.access(self.file + os.extsep + ext, os.F_OK):
                list.append(self.file + os.extsep + ext)
        return list

    def do_open(self, flags, replace):
        debug("opening dbm file %s", self.file)
        try:
            self.dbm = self.dbmmodule.open(self.file, flags)
        except:
            self._checkfile()
            self.dbm = self.dbmmodule.open(self.file, flags)

    def do_close(self):
        if self.dbm is not None:
            debug("closing dbm file %s", self.file)
            self.dbm.close()

    def do_remove(self):
        for f in self.get_filenames():
            os.remove(f)

    def __getitem__(self, key):
        return cPickle.loads(self.dbm[key])

    def __contains__(self, key):
        return key in self.dbm

    def __setitem__(self, key, value):
        self.dbm[key] = cPickle.dumps(value)

    def __delitem__(self, key):
        del self.dbm[key]

    def keys(self):
        return self.dbm.keys()


class FileNamespaceManager(OpenResourceNamespaceManager):
    """:class:`.NamespaceManager` that uses binary files for storage.

    Each namespace is implemented as a single file storing a
    dictionary of key/value pairs, serialized using the Python
    ``pickle`` module.

    """
    def __init__(self, namespace, data_dir=None, file_dir=None, lock_dir=None,
                 digest_filenames=True, **kwargs):
        self.digest_filenames = digest_filenames

        if not file_dir and not data_dir:
            raise MissingCacheParameter("data_dir or file_dir is required")
        elif file_dir:
            self.file_dir = file_dir
        else:
            self.file_dir = data_dir + "/container_file"
        util.verify_directory(self.file_dir)

        if not lock_dir and not data_dir:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        elif lock_dir:
            self.lock_dir = lock_dir
        else:
            self.lock_dir = data_dir + "/container_file_lock"
        util.verify_directory(self.lock_dir)
        OpenResourceNamespaceManager.__init__(self, namespace)

        self.file = util.encoded_path(root=self.file_dir,
                                      identifiers=[self.namespace],
                                      extension='.cache',
                                      digest_filenames=self.digest_filenames)
        self.hash = {}

        debug("data file %s", self.file)

    def get_access_lock(self):
        return file_synchronizer(identifier=self.namespace,
                                 lock_dir=self.lock_dir)

    def get_creation_lock(self, key):
        return file_synchronizer(
                identifier="dbmcontainer/funclock/%s/%s" % (
                    self.namespace, key
                ),
                lock_dir=self.lock_dir
                )

    def file_exists(self, file):
        return os.access(file, os.F_OK)

    def do_open(self, flags, replace):
        if not replace and self.file_exists(self.file):
            fh = open(self.file, 'rb')
            self.hash = cPickle.load(fh)
            fh.close()

        self.flags = flags

    def do_close(self):
        if self.flags == 'c' or self.flags == 'w':
            fh = open(self.file, 'wb')
            cPickle.dump(self.hash, fh)
            fh.close()

        self.hash = {}
        self.flags = None

    def do_remove(self):
        try:
            os.remove(self.file)
        except OSError:
            # for instance, because we haven't yet used this cache,
            # but client code has asked for a clear() operation...
            pass
        self.hash = {}

    def __getitem__(self, key):
        return self.hash[key]

    def __contains__(self, key):
        return key in self.hash

    def __setitem__(self, key, value):
        self.hash[key] = value

    def __delitem__(self, key):
        del self.hash[key]

    def keys(self):
        return self.hash.keys()


#### legacy stuff to support the old "Container" class interface

namespace_classes = {}

ContainerContext = dict


class ContainerMeta(type):
    def __init__(cls, classname, bases, dict_):
        namespace_classes[cls] = cls.namespace_class
        return type.__init__(cls, classname, bases, dict_)

    def __call__(self, key, context, namespace, createfunc=None,
                 expiretime=None, starttime=None, **kwargs):
        if namespace in context:
            ns = context[namespace]
        else:
            nscls = namespace_classes[self]
            context[namespace] = ns = nscls(namespace, **kwargs)
        return Value(key, ns, createfunc=createfunc,
                     expiretime=expiretime, starttime=starttime)


class Container(object):
    """Implements synchronization and value-creation logic
    for a 'value' stored in a :class:`.NamespaceManager`.

    :class:`.Container` and its subclasses are deprecated.   The
    :class:`.Value` class is now used for this purpose.

    """
    __metaclass__ = ContainerMeta
    namespace_class = NamespaceManager


class FileContainer(Container):
    namespace_class = FileNamespaceManager


class MemoryContainer(Container):
    namespace_class = MemoryNamespaceManager


class DBMContainer(Container):
    namespace_class = DBMNamespaceManager

DbmContainer = DBMContainer

########NEW FILE########
__FILENAME__ = converters


# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
def asbool(obj):
    if isinstance(obj, (str, unicode)):
        obj = obj.strip().lower()
        if obj in ['true', 'yes', 'on', 'y', 't', '1']:
            return True
        elif obj in ['false', 'no', 'off', 'n', 'f', '0']:
            return False
        else:
            raise ValueError(
                "String is not true/false: %r" % obj)
    return bool(obj)


def aslist(obj, sep=None, strip=True):
    if isinstance(obj, (str, unicode)):
        lst = obj.split(sep)
        if strip:
            lst = [v.strip() for v in lst]
        return lst
    elif isinstance(obj, (list, tuple)):
        return obj
    elif obj is None:
        return []
    else:
        return [obj]

########NEW FILE########
__FILENAME__ = jcecrypto
"""
Encryption module that uses the Java Cryptography Extensions (JCE).

Note that in default installations of the Java Runtime Environment, the
maximum key length is limited to 128 bits due to US export
restrictions. This makes the generated keys incompatible with the ones
generated by pycryptopp, which has no such restrictions. To fix this,
download the "Unlimited Strength Jurisdiction Policy Files" from Sun,
which will allow encryption using 256 bit AES keys.
"""
from javax.crypto import Cipher
from javax.crypto.spec import SecretKeySpec, IvParameterSpec

import jarray

# Initialization vector filled with zeros
_iv = IvParameterSpec(jarray.zeros(16, 'b'))


def aesEncrypt(data, key):
    cipher = Cipher.getInstance('AES/CTR/NoPadding')
    skeySpec = SecretKeySpec(key, 'AES')
    cipher.init(Cipher.ENCRYPT_MODE, skeySpec, _iv)
    return cipher.doFinal(data).tostring()

# magic.
aesDecrypt = aesEncrypt


def getKeyLength():
    maxlen = Cipher.getMaxAllowedKeyLength('AES/CTR/NoPadding')
    return min(maxlen, 256) / 8

########NEW FILE########
__FILENAME__ = nsscrypto
"""Encryption module that uses nsscrypto"""
import nss.nss

nss.nss.nss_init_nodb()

# Apparently the rest of beaker doesn't care about the particluar cipher,
# mode and padding used.
# NOTE: A constant IV!!! This is only secure if the KEY is never reused!!!
_mech = nss.nss.CKM_AES_CBC_PAD
_iv = '\0' * nss.nss.get_iv_length(_mech)

def aesEncrypt(data, key):
    slot = nss.nss.get_best_slot(_mech)

    key_obj = nss.nss.import_sym_key(slot, _mech, nss.nss.PK11_OriginGenerated,
                                     nss.nss.CKA_ENCRYPT, nss.nss.SecItem(key))

    param = nss.nss.param_from_iv(_mech, nss.nss.SecItem(_iv))
    ctx = nss.nss.create_context_by_sym_key(_mech, nss.nss.CKA_ENCRYPT, key_obj,
                                            param)
    l1 = ctx.cipher_op(data)
    # Yes, DIGEST.  This needs fixing in NSS, but apparently nobody (including
    # me :( ) cares enough.
    l2 = ctx.digest_final()

    return l1 + l2

def aesDecrypt(data, key):
    slot = nss.nss.get_best_slot(_mech)

    key_obj = nss.nss.import_sym_key(slot, _mech, nss.nss.PK11_OriginGenerated,
                                     nss.nss.CKA_DECRYPT, nss.nss.SecItem(key))

    param = nss.nss.param_from_iv(_mech, nss.nss.SecItem(_iv))
    ctx = nss.nss.create_context_by_sym_key(_mech, nss.nss.CKA_DECRYPT, key_obj,
                                            param)
    l1 = ctx.cipher_op(data)
    # Yes, DIGEST.  This needs fixing in NSS, but apparently nobody (including
    # me :( ) cares enough.
    l2 = ctx.digest_final()

    return l1 + l2

def getKeyLength():
    return 32

########NEW FILE########
__FILENAME__ = pbkdf2
#!/usr/bin/python
# -*- coding: ascii -*-
###########################################################################
# PBKDF2.py - PKCS#5 v2.0 Password-Based Key Derivation
#
# Copyright (C) 2007 Dwayne C. Litzenberger <dlitz@dlitz.net>
# All rights reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation.
#
# THE AUTHOR PROVIDES THIS SOFTWARE ``AS IS'' AND ANY EXPRESSED OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Country of origin: Canada
#
###########################################################################
# Sample PBKDF2 usage:
#   from Crypto.Cipher import AES
#   from PBKDF2 import PBKDF2
#   import os
#
#   salt = os.urandom(8)    # 64-bit salt
#   key = PBKDF2("This passphrase is a secret.", salt).read(32) # 256-bit key
#   iv = os.urandom(16)     # 128-bit IV
#   cipher = AES.new(key, AES.MODE_CBC, iv)
#     ...
#
# Sample crypt() usage:
#   from PBKDF2 import crypt
#   pwhash = crypt("secret")
#   alleged_pw = raw_input("Enter password: ")
#   if pwhash == crypt(alleged_pw, pwhash):
#       print "Password good"
#   else:
#       print "Invalid password"
#
###########################################################################
# History:
#
#  2007-07-27 Dwayne C. Litzenberger <dlitz@dlitz.net>
#   - Initial Release (v1.0)
#
#  2007-07-31 Dwayne C. Litzenberger <dlitz@dlitz.net>
#   - Bugfix release (v1.1)
#   - SECURITY: The PyCrypto XOR cipher (used, if available, in the _strxor
#   function in the previous release) silently truncates all keys to 64
#   bytes.  The way it was used in the previous release, this would only be
#   problem if the pseudorandom function that returned values larger than
#   64 bytes (so SHA1, SHA256 and SHA512 are fine), but I don't like
#   anything that silently reduces the security margin from what is
#   expected.
#
###########################################################################

__version__ = "1.1"

from struct import pack
from binascii import b2a_hex
from random import randint

from base64 import b64encode

from beaker.crypto.util import hmac as HMAC, hmac_sha1 as SHA1


def strxor(a, b):
    return "".join([chr(ord(x) ^ ord(y)) for (x, y) in zip(a, b)])


class PBKDF2(object):
    """PBKDF2.py : PKCS#5 v2.0 Password-Based Key Derivation

    This implementation takes a passphrase and a salt (and optionally an
    iteration count, a digest module, and a MAC module) and provides a
    file-like object from which an arbitrarily-sized key can be read.

    If the passphrase and/or salt are unicode objects, they are encoded as
    UTF-8 before they are processed.

    The idea behind PBKDF2 is to derive a cryptographic key from a
    passphrase and a salt.

    PBKDF2 may also be used as a strong salted password hash.  The
    'crypt' function is provided for that purpose.

    Remember: Keys generated using PBKDF2 are only as strong as the
    passphrases they are derived from.
    """

    def __init__(self, passphrase, salt, iterations=1000,
                 digestmodule=SHA1, macmodule=HMAC):
        if not callable(macmodule):
            macmodule = macmodule.new
        self.__macmodule = macmodule
        self.__digestmodule = digestmodule
        self._setup(passphrase, salt, iterations, self._pseudorandom)

    def _pseudorandom(self, key, msg):
        """Pseudorandom function.  e.g. HMAC-SHA1"""
        return self.__macmodule(key=key, msg=msg,
            digestmod=self.__digestmodule).digest()

    def read(self, bytes):
        """Read the specified number of key bytes."""
        if self.closed:
            raise ValueError("file-like object is closed")

        size = len(self.__buf)
        blocks = [self.__buf]
        i = self.__blockNum
        while size < bytes:
            i += 1
            if i > 0xffffffff:
                # We could return "" here, but
                raise OverflowError("derived key too long")
            block = self.__f(i)
            blocks.append(block)
            size += len(block)
        buf = "".join(blocks)
        retval = buf[:bytes]
        self.__buf = buf[bytes:]
        self.__blockNum = i
        return retval

    def __f(self, i):
        # i must fit within 32 bits
        assert (1 <= i and i <= 0xffffffff)
        U = self.__prf(self.__passphrase, self.__salt + pack("!L", i))
        result = U
        for j in xrange(2, 1 + self.__iterations):
            U = self.__prf(self.__passphrase, U)
            result = strxor(result, U)
        return result

    def hexread(self, octets):
        """Read the specified number of octets. Return them as hexadecimal.

        Note that len(obj.hexread(n)) == 2*n.
        """
        return b2a_hex(self.read(octets))

    def _setup(self, passphrase, salt, iterations, prf):
        # Sanity checks:

        # passphrase and salt must be str or unicode (in the latter
        # case, we convert to UTF-8)
        if isinstance(passphrase, unicode):
            passphrase = passphrase.encode("UTF-8")
        if not isinstance(passphrase, str):
            raise TypeError("passphrase must be str or unicode")
        if isinstance(salt, unicode):
            salt = salt.encode("UTF-8")
        if not isinstance(salt, str):
            raise TypeError("salt must be str or unicode")

        # iterations must be an integer >= 1
        if not isinstance(iterations, (int, long)):
            raise TypeError("iterations must be an integer")
        if iterations < 1:
            raise ValueError("iterations must be at least 1")

        # prf must be callable
        if not callable(prf):
            raise TypeError("prf must be callable")

        self.__passphrase = passphrase
        self.__salt = salt
        self.__iterations = iterations
        self.__prf = prf
        self.__blockNum = 0
        self.__buf = ""
        self.closed = False

    def close(self):
        """Close the stream."""
        if not self.closed:
            del self.__passphrase
            del self.__salt
            del self.__iterations
            del self.__prf
            del self.__blockNum
            del self.__buf
            self.closed = True


def crypt(word, salt=None, iterations=None):
    """PBKDF2-based unix crypt(3) replacement.

    The number of iterations specified in the salt overrides the 'iterations'
    parameter.

    The effective hash length is 192 bits.
    """

    # Generate a (pseudo-)random salt if the user hasn't provided one.
    if salt is None:
        salt = _makesalt()

    # salt must be a string or the us-ascii subset of unicode
    if isinstance(salt, unicode):
        salt = salt.encode("us-ascii")
    if not isinstance(salt, str):
        raise TypeError("salt must be a string")

    # word must be a string or unicode (in the latter case, we convert to UTF-8)
    if isinstance(word, unicode):
        word = word.encode("UTF-8")
    if not isinstance(word, str):
        raise TypeError("word must be a string or unicode")

    # Try to extract the real salt and iteration count from the salt
    if salt.startswith("$p5k2$"):
        (iterations, salt, dummy) = salt.split("$")[2:5]
        if iterations == "":
            iterations = 400
        else:
            converted = int(iterations, 16)
            if iterations != "%x" % converted:  # lowercase hex, minimum digits
                raise ValueError("Invalid salt")
            iterations = converted
            if not (iterations >= 1):
                raise ValueError("Invalid salt")

    # Make sure the salt matches the allowed character set
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./"
    for ch in salt:
        if ch not in allowed:
            raise ValueError("Illegal character %r in salt" % (ch,))

    if iterations is None or iterations == 400:
        iterations = 400
        salt = "$p5k2$$" + salt
    else:
        salt = "$p5k2$%x$%s" % (iterations, salt)
    rawhash = PBKDF2(word, salt, iterations).read(24)
    return salt + "$" + b64encode(rawhash, "./")

# Add crypt as a static method of the PBKDF2 class
# This makes it easier to do "from PBKDF2 import PBKDF2" and still use
# crypt.
PBKDF2.crypt = staticmethod(crypt)


def _makesalt():
    """Return a 48-bit pseudorandom salt for crypt().

    This function is not suitable for generating cryptographic secrets.
    """
    binarysalt = "".join([pack("@H", randint(0, 0xffff)) for i in range(3)])
    return b64encode(binarysalt, "./")


def test_pbkdf2():
    """Module self-test"""
    from binascii import a2b_hex

    #
    # Test vectors from RFC 3962
    #

    # Test 1
    result = PBKDF2("password", "ATHENA.MIT.EDUraeburn", 1).read(16)
    expected = a2b_hex("cdedb5281bb2f801565a1122b2563515")
    if result != expected:
        raise RuntimeError("self-test failed")

    # Test 2
    result = PBKDF2("password", "ATHENA.MIT.EDUraeburn", 1200).hexread(32)
    expected = ("5c08eb61fdf71e4e4ec3cf6ba1f5512b"
                "a7e52ddbc5e5142f708a31e2e62b1e13")
    if result != expected:
        raise RuntimeError("self-test failed")

    # Test 3
    result = PBKDF2("X" * 64, "pass phrase equals block size", 1200).hexread(32)
    expected = ("139c30c0966bc32ba55fdbf212530ac9"
                "c5ec59f1a452f5cc9ad940fea0598ed1")
    if result != expected:
        raise RuntimeError("self-test failed")

    # Test 4
    result = PBKDF2("X" * 65, "pass phrase exceeds block size", 1200).hexread(32)
    expected = ("9ccad6d468770cd51b10e6a68721be61"
                "1a8b4d282601db3b36be9246915ec82a")
    if result != expected:
        raise RuntimeError("self-test failed")

    #
    # Other test vectors
    #

    # Chunked read
    f = PBKDF2("kickstart", "workbench", 256)
    result = f.read(17)
    result += f.read(17)
    result += f.read(1)
    result += f.read(2)
    result += f.read(3)
    expected = PBKDF2("kickstart", "workbench", 256).read(40)
    if result != expected:
        raise RuntimeError("self-test failed")

    #
    # crypt() test vectors
    #

    # crypt 1
    result = crypt("cloadm", "exec")
    expected = '$p5k2$$exec$r1EWMCMk7Rlv3L/RNcFXviDefYa0hlql'
    if result != expected:
        raise RuntimeError("self-test failed")

    # crypt 2
    result = crypt("gnu", '$p5k2$c$u9HvcT4d$.....')
    expected = '$p5k2$c$u9HvcT4d$Sd1gwSVCLZYAuqZ25piRnbBEoAesaa/g'
    if result != expected:
        raise RuntimeError("self-test failed")

    # crypt 3
    result = crypt("dcl", "tUsch7fU", iterations=13)
    expected = "$p5k2$d$tUsch7fU$nqDkaxMDOFBeJsTSfABsyn.PYUXilHwL"
    if result != expected:
        raise RuntimeError("self-test failed")

    # crypt 4 (unicode)
    result = crypt(u'\u0399\u03c9\u03b1\u03bd\u03bd\u03b7\u03c2',
        '$p5k2$$KosHgqNo$9mjN8gqjt02hDoP0c2J0ABtLIwtot8cQ')
    expected = '$p5k2$$KosHgqNo$9mjN8gqjt02hDoP0c2J0ABtLIwtot8cQ'
    if result != expected:
        raise RuntimeError("self-test failed")

if __name__ == '__main__':
    test_pbkdf2()

# vim:set ts=4 sw=4 sts=4 expandtab:

########NEW FILE########
__FILENAME__ = pycrypto
"""Encryption module that uses pycryptopp or pycrypto"""
try:
    # Pycryptopp is preferred over Crypto because Crypto has had
    # various periods of not being maintained, and pycryptopp uses
    # the Crypto++ library which is generally considered the 'gold standard'
    # of crypto implementations
    from pycryptopp.cipher import aes

    def aesEncrypt(data, key):
        cipher = aes.AES(key)
        return cipher.process(data)

    # magic.
    aesDecrypt = aesEncrypt

except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util import Counter

    def aesEncrypt(data, key):
        cipher = AES.new(key, AES.MODE_CTR,
                         counter=Counter.new(128, initial_value=0))

        return cipher.encrypt(data)

    def aesDecrypt(data, key):
        cipher = AES.new(key, AES.MODE_CTR,
                         counter=Counter.new(128, initial_value=0))
        return cipher.decrypt(data)



def getKeyLength():
    return 32

########NEW FILE########
__FILENAME__ = util
from warnings import warn
from beaker import util


try:
    # Use PyCrypto (if available)
    from Crypto.Hash import HMAC as hmac, SHA as hmac_sha1
    sha1 = hmac_sha1.new

except ImportError:

    # PyCrypto not available.  Use the Python standard library.
    import hmac

    # When using the stdlib, we have to make sure the hmac version and sha
    # version are compatible
    if util.py24:
        from sha import sha as sha1
        import sha as hmac_sha1
    else:
        # NOTE: We have to use the callable with hashlib (hashlib.sha1),
        # otherwise hmac only accepts the sha module object itself
        from hashlib import sha1
        hmac_sha1 = sha1


if util.py24:
    from md5 import md5
else:
    from hashlib import md5

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Beaker documentation build configuration file, created by
# sphinx-quickstart on Fri Sep 19 15:12:15 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.insert(0, os.path.abspath('../..'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Beaker'
copyright = u'2008-2012, Ben Bangert, Mike Bayer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.6'
# The full version, including alpha/beta/rc tags.
release = '1.6.4'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'pastie'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
# html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
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

# html_index = 'contents.html'

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {'index': 'indexsidebar.html'}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {'index': 'index.html'}

html_theme_options = {
    "bgcolor": "#fff",
    "footertextcolor": "#666",
    "relbarbgcolor": "#fff",
    "relbarlinkcolor": "#590915",
    "relbartextcolor": "#FFAA2D",
    "sidebarlinkcolor": "#590915",
    "sidebarbgcolor": "#fff",
    "sidebartextcolor": "#333",
    "footerbgcolor": "#fff",
    "linkcolor": "#590915",
    "bodyfont": "helvetica, 'bitstream vera sans', sans-serif",
    "headfont": "georgia, 'bitstream vera sans serif', 'lucida grande', helvetica, verdana, sans-serif",
    "headbgcolor": "#fff",
    "headtextcolor": "#12347A",
    "codebgcolor": "#fff",
}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
html_use_opensearch = 'http://beaker.rtfd.org/'

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Beakerdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('contents', 'Beaker.tex', u'Beaker Documentation',
   u'Ben Bangert, Mike Bayer', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
latex_preamble = '''
\usepackage{palatino}
\definecolor{TitleColor}{rgb}{0.7,0,0}
\definecolor{InnerLinkColor}{rgb}{0.7,0,0}
\definecolor{OuterLinkColor}{rgb}{0.8,0,0}
\definecolor{VerbatimColor}{rgb}{0.985,0.985,0.985}
\definecolor{VerbatimBorderColor}{rgb}{0.8,0.8,0.8}
'''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
latex_use_modindex = False

# Added to handle docs in middleware.py
autoclass_content = "both"

########NEW FILE########
__FILENAME__ = exceptions
"""Beaker exception classes"""


class BeakerException(Exception):
    pass


class BeakerWarning(RuntimeWarning):
    """Issued at runtime."""


class CreationAbortedError(Exception):
    """Deprecated."""


class InvalidCacheBackendError(BeakerException, ImportError):
    pass


class MissingCacheParameter(BeakerException):
    pass


class LockError(BeakerException):
    pass


class InvalidCryptoBackendError(BeakerException):
    pass

########NEW FILE########
__FILENAME__ = database
import cPickle
import logging
import pickle
from datetime import datetime

from beaker.container import OpenResourceNamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import file_synchronizer, null_synchronizer
from beaker.util import verify_directory, SyncDict

log = logging.getLogger(__name__)

sa = None
pool = None
types = None


class DatabaseNamespaceManager(OpenResourceNamespaceManager):
    metadatas = SyncDict()
    tables = SyncDict()

    @classmethod
    def _init_dependencies(cls):
        global sa, pool, types
        if sa is not None:
            return
        try:
            import sqlalchemy as sa
            import sqlalchemy.pool as pool
            from sqlalchemy import types
        except ImportError:
            raise InvalidCacheBackendError("Database cache backend requires "
                                            "the 'sqlalchemy' library")

    def __init__(self, namespace, url=None, sa_opts=None, optimistic=False,
                 table_name='beaker_cache', data_dir=None, lock_dir=None,
                 schema_name=None, **params):
        """Creates a database namespace manager

        ``url``
            SQLAlchemy compliant db url
        ``sa_opts``
            A dictionary of SQLAlchemy keyword options to initialize the engine
            with.
        ``optimistic``
            Use optimistic session locking, note that this will result in an
            additional select when updating a cache value to compare version
            numbers.
        ``table_name``
            The table name to use in the database for the cache.
        ``schema_name``
            The schema name to use in the database for the cache.
        """
        OpenResourceNamespaceManager.__init__(self, namespace)

        if sa_opts is None:
            sa_opts = params

        if lock_dir:
            self.lock_dir = lock_dir
        elif data_dir:
            self.lock_dir = data_dir + "/container_db_lock"
        if self.lock_dir:
            verify_directory(self.lock_dir)

        # Check to see if the table's been created before
        url = url or sa_opts['sa.url']
        table_key = url + table_name

        def make_cache():
            # Check to see if we have a connection pool open already
            meta_key = url + table_name

            def make_meta():
                # SQLAlchemy pops the url, this ensures it sticks around
                # later
                sa_opts['sa.url'] = url
                engine = sa.engine_from_config(sa_opts, 'sa.')
                meta = sa.MetaData()
                meta.bind = engine
                return meta
            meta = DatabaseNamespaceManager.metadatas.get(meta_key, make_meta)
            # Create the table object and cache it now
            cache = sa.Table(table_name, meta,
                             sa.Column('id', types.Integer, primary_key=True),
                             sa.Column('namespace', types.String(255), nullable=False),
                             sa.Column('accessed', types.DateTime, nullable=False),
                             sa.Column('created', types.DateTime, nullable=False),
                             sa.Column('data', types.PickleType, nullable=False),
                             sa.UniqueConstraint('namespace'),
                             schema=schema_name if schema_name else meta.schema
            )
            cache.create(checkfirst=True)
            return cache
        self.hash = {}
        self._is_new = False
        self.loaded = False
        self.cache = DatabaseNamespaceManager.tables.get(table_key, make_cache)

    def get_access_lock(self):
        return null_synchronizer()

    def get_creation_lock(self, key):
        return file_synchronizer(
            identifier="databasecontainer/funclock/%s/%s" % (
                self.namespace, key
            ),
            lock_dir=self.lock_dir)

    def do_open(self, flags, replace):
        # If we already loaded the data, don't bother loading it again
        if self.loaded:
            self.flags = flags
            return

        cache = self.cache
        result = sa.select([cache.c.data],
                           cache.c.namespace == self.namespace
                          ).execute().fetchone()
        if not result:
            self._is_new = True
            self.hash = {}
        else:
            self._is_new = False
            try:
                self.hash = result['data']
            except (IOError, OSError, EOFError, cPickle.PickleError,
                    pickle.PickleError):
                log.debug("Couln't load pickle data, creating new storage")
                self.hash = {}
                self._is_new = True
        self.flags = flags
        self.loaded = True

    def do_close(self):
        if self.flags is not None and (self.flags == 'c' or self.flags == 'w'):
            cache = self.cache
            if self._is_new:
                cache.insert().execute(namespace=self.namespace, data=self.hash,
                                       accessed=datetime.now(),
                                       created=datetime.now())
                self._is_new = False
            else:
                cache.update(cache.c.namespace == self.namespace).execute(
                    data=self.hash, accessed=datetime.now())
        self.flags = None

    def do_remove(self):
        cache = self.cache
        cache.delete(cache.c.namespace == self.namespace).execute()
        self.hash = {}

        # We can retain the fact that we did a load attempt, but since the
        # file is gone this will be a new namespace should it be saved.
        self._is_new = True

    def __getitem__(self, key):
        return self.hash[key]

    def __contains__(self, key):
        return key in self.hash

    def __setitem__(self, key, value):
        self.hash[key] = value

    def __delitem__(self, key):
        del self.hash[key]

    def keys(self):
        return self.hash.keys()


class DatabaseContainer(Container):
    namespace_manager = DatabaseNamespaceManager

########NEW FILE########
__FILENAME__ = google
import cPickle
import logging
from datetime import datetime

from beaker.container import OpenResourceNamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError
from beaker.synchronization import null_synchronizer

log = logging.getLogger(__name__)

db = None


class GoogleNamespaceManager(OpenResourceNamespaceManager):
    tables = {}

    @classmethod
    def _init_dependencies(cls):
        global db
        if db is not None:
            return
        try:
            db = __import__('google.appengine.ext.db').appengine.ext.db
        except ImportError:
            raise InvalidCacheBackendError("Datastore cache backend requires the "
                                           "'google.appengine.ext' library")

    def __init__(self, namespace, table_name='beaker_cache', **params):
        """Creates a datastore namespace manager"""
        OpenResourceNamespaceManager.__init__(self, namespace)

        def make_cache():
            table_dict = dict(created=db.DateTimeProperty(),
                              accessed=db.DateTimeProperty(),
                              data=db.BlobProperty())
            table = type(table_name, (db.Model,), table_dict)
            return table
        self.table_name = table_name
        self.cache = GoogleNamespaceManager.tables.setdefault(table_name, make_cache())
        self.hash = {}
        self._is_new = False
        self.loaded = False
        self.log_debug = logging.DEBUG >= log.getEffectiveLevel()

        # Google wants namespaces to start with letters, change the namespace
        # to start with a letter
        self.namespace = 'p%s' % self.namespace

    def get_access_lock(self):
        return null_synchronizer()

    def get_creation_lock(self, key):
        # this is weird, should probably be present
        return null_synchronizer()

    def do_open(self, flags, replace):
        # If we already loaded the data, don't bother loading it again
        if self.loaded:
            self.flags = flags
            return

        item = self.cache.get_by_key_name(self.namespace)

        if not item:
            self._is_new = True
            self.hash = {}
        else:
            self._is_new = False
            try:
                self.hash = cPickle.loads(str(item.data))
            except (IOError, OSError, EOFError, cPickle.PickleError):
                if self.log_debug:
                    log.debug("Couln't load pickle data, creating new storage")
                self.hash = {}
                self._is_new = True
        self.flags = flags
        self.loaded = True

    def do_close(self):
        if self.flags is not None and (self.flags == 'c' or self.flags == 'w'):
            if self._is_new:
                item = self.cache(key_name=self.namespace)
                item.data = cPickle.dumps(self.hash)
                item.created = datetime.now()
                item.accessed = datetime.now()
                item.put()
                self._is_new = False
            else:
                item = self.cache.get_by_key_name(self.namespace)
                item.data = cPickle.dumps(self.hash)
                item.accessed = datetime.now()
                item.put()
        self.flags = None

    def do_remove(self):
        item = self.cache.get_by_key_name(self.namespace)
        item.delete()
        self.hash = {}

        # We can retain the fact that we did a load attempt, but since the
        # file is gone this will be a new namespace should it be saved.
        self._is_new = True

    def __getitem__(self, key):
        return self.hash[key]

    def __contains__(self, key):
        return key in self.hash

    def __setitem__(self, key, value):
        self.hash[key] = value

    def __delitem__(self, key):
        del self.hash[key]

    def keys(self):
        return self.hash.keys()


class GoogleContainer(Container):
    namespace_class = GoogleNamespaceManager

########NEW FILE########
__FILENAME__ = memcached
from __future__ import with_statement
from beaker.container import NamespaceManager, Container
from beaker.crypto.util import sha1
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import file_synchronizer
from beaker.util import verify_directory, SyncDict, parse_memcached_behaviors, py3k
import warnings

MAX_KEY_LENGTH = 250

_client_libs = {}


def _load_client(name='auto'):
    if name in _client_libs:
        return _client_libs[name]

    def _pylibmc():
        global pylibmc
        import pylibmc
        return pylibmc

    def _cmemcache():
        global cmemcache
        import cmemcache
        warnings.warn("cmemcache is known to have serious "
                    "concurrency issues; consider using 'memcache' "
                    "or 'pylibmc'")
        return cmemcache

    def _memcache():
        global memcache
        import memcache
        return memcache

    def _bmemcached():
        global bmemcached
        import bmemcached
        return bmemcached

    def _auto():
        for _client in (_pylibmc, _cmemcache, _memcache, _bmemcached):
            try:
                return _client()
            except ImportError:
                pass
        else:
            raise InvalidCacheBackendError(
                    "Memcached cache backend requires one "
                    "of: 'pylibmc' or 'memcache' to be installed.")

    clients = {
        'pylibmc': _pylibmc,
        'cmemcache': _cmemcache,
        'memcache': _memcache,
        'bmemcached': _bmemcached,
        'auto': _auto
    }
    _client_libs[name] = clib = clients[name]()
    return clib


def _is_configured_for_pylibmc(memcache_module_config, memcache_client):
    return memcache_module_config == 'pylibmc' or \
        memcache_client.__name__.startswith('pylibmc')


class MemcachedNamespaceManager(NamespaceManager):
    """Provides the :class:`.NamespaceManager` API over a memcache client library."""

    clients = SyncDict()

    def __new__(cls, *args, **kw):
        memcache_module = kw.pop('memcache_module', 'auto')

        memcache_client = _load_client(memcache_module)

        if _is_configured_for_pylibmc(memcache_module, memcache_client):
            return object.__new__(PyLibMCNamespaceManager)
        else:
            return object.__new__(MemcachedNamespaceManager)

    def __init__(self, namespace, url,
                        memcache_module='auto',
                        data_dir=None, lock_dir=None,
                        **kw):
        NamespaceManager.__init__(self, namespace)

        _memcache_module = _client_libs[memcache_module]

        if not url:
            raise MissingCacheParameter("url is required")

        self.lock_dir = None

        if lock_dir:
            self.lock_dir = lock_dir
        elif data_dir:
            self.lock_dir = data_dir + "/container_mcd_lock"
        if self.lock_dir:
            verify_directory(self.lock_dir)

        # Check for pylibmc namespace manager, in which case client will be
        # instantiated by subclass __init__, to handle behavior passing to the
        # pylibmc client
        if not _is_configured_for_pylibmc(memcache_module, _memcache_module):
            self.mc = MemcachedNamespaceManager.clients.get(
                        (memcache_module, url),
                        _memcache_module.Client,
                        url.split(';'))

    def get_creation_lock(self, key):
        return file_synchronizer(
            identifier="memcachedcontainer/funclock/%s/%s" %
                    (self.namespace, key), lock_dir=self.lock_dir)

    def _format_key(self, key):
        if not isinstance(key, str):
            key = key.decode('ascii')
        formated_key = (self.namespace + '_' + key).replace(' ', '\302\267')
        if len(formated_key) > MAX_KEY_LENGTH:
            if py3k:
                formated_key = formated_key.encode('utf-8')
            formated_key = sha1(formated_key).hexdigest()
        return formated_key

    def __getitem__(self, key):
        return self.mc.get(self._format_key(key))

    def __contains__(self, key):
        value = self.mc.get(self._format_key(key))
        return value is not None

    def has_key(self, key):
        return key in self

    def set_value(self, key, value, expiretime=None):
        if expiretime:
            self.mc.set(self._format_key(key), value, time=expiretime)
        else:
            self.mc.set(self._format_key(key), value)

    def __setitem__(self, key, value):
        self.set_value(key, value)

    def __delitem__(self, key):
        self.mc.delete(self._format_key(key))

    def do_remove(self):
        self.mc.flush_all()

    def keys(self):
        raise NotImplementedError(
                "Memcache caching does not "
                "support iteration of all cache keys")


class PyLibMCNamespaceManager(MemcachedNamespaceManager):
    """Provide thread-local support for pylibmc."""

    def __init__(self, *arg, **kw):
        super(PyLibMCNamespaceManager, self).__init__(*arg, **kw)

        memcache_module = kw.get('memcache_module', 'auto')
        _memcache_module = _client_libs[memcache_module]
        protocol = kw.get('protocol', 'text')
        username = kw.get('username', None)
        password = kw.get('password', None)
        url = kw.get('url')
        behaviors = parse_memcached_behaviors(kw)

        self.mc = MemcachedNamespaceManager.clients.get(
                        (memcache_module, url),
                        _memcache_module.Client,
                        servers=url.split(';'), behaviors=behaviors,
                        binary=(protocol == 'binary'), username=username,
                        password=password)
        self.pool = pylibmc.ThreadMappedPool(self.mc)

    def __getitem__(self, key):
        with self.pool.reserve() as mc:
            return mc.get(self._format_key(key))

    def __contains__(self, key):
        with self.pool.reserve() as mc:
            value = mc.get(self._format_key(key))
            return value is not None

    def has_key(self, key):
        return key in self

    def set_value(self, key, value, expiretime=None):
        with self.pool.reserve() as mc:
            if expiretime:
                mc.set(self._format_key(key), value, time=expiretime)
            else:
                mc.set(self._format_key(key), value)

    def __setitem__(self, key, value):
        self.set_value(key, value)

    def __delitem__(self, key):
        with self.pool.reserve() as mc:
            mc.delete(self._format_key(key))

    def do_remove(self):
        with self.pool.reserve() as mc:
            mc.flush_all()


class MemcachedContainer(Container):
    """Container class which invokes :class:`.MemcacheNamespaceManager`."""
    namespace_class = MemcachedNamespaceManager

########NEW FILE########
__FILENAME__ = sqla
import cPickle
import logging
import pickle
from datetime import datetime

from beaker.container import OpenResourceNamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import file_synchronizer, null_synchronizer
from beaker.util import verify_directory, SyncDict


log = logging.getLogger(__name__)

sa = None


class SqlaNamespaceManager(OpenResourceNamespaceManager):
    binds = SyncDict()
    tables = SyncDict()

    @classmethod
    def _init_dependencies(cls):
        global sa
        if sa is not None:
            return
        try:
            import sqlalchemy as sa
        except ImportError:
            raise InvalidCacheBackendError("SQLAlchemy, which is required by "
                                            "this backend, is not installed")

    def __init__(self, namespace, bind, table, data_dir=None, lock_dir=None,
                 **kwargs):
        """Create a namespace manager for use with a database table via
        SQLAlchemy.

        ``bind``
            SQLAlchemy ``Engine`` or ``Connection`` object

        ``table``
            SQLAlchemy ``Table`` object in which to store namespace data.
            This should usually be something created by ``make_cache_table``.
        """
        OpenResourceNamespaceManager.__init__(self, namespace)

        if lock_dir:
            self.lock_dir = lock_dir
        elif data_dir:
            self.lock_dir = data_dir + "/container_db_lock"
        if self.lock_dir:
            verify_directory(self.lock_dir)

        self.bind = self.__class__.binds.get(str(bind.url), lambda: bind)
        self.table = self.__class__.tables.get('%s:%s' % (bind.url, table.name),
                                               lambda: table)
        self.hash = {}
        self._is_new = False
        self.loaded = False

    def get_access_lock(self):
        return null_synchronizer()

    def get_creation_lock(self, key):
        return file_synchronizer(
            identifier="databasecontainer/funclock/%s" % self.namespace,
            lock_dir=self.lock_dir)

    def do_open(self, flags, replace):
        if self.loaded:
            self.flags = flags
            return
        select = sa.select([self.table.c.data],
                           (self.table.c.namespace == self.namespace))
        result = self.bind.execute(select).fetchone()
        if not result:
            self._is_new = True
            self.hash = {}
        else:
            self._is_new = False
            try:
                self.hash = result['data']
            except (IOError, OSError, EOFError, cPickle.PickleError,
                    pickle.PickleError):
                log.debug("Couln't load pickle data, creating new storage")
                self.hash = {}
                self._is_new = True
        self.flags = flags
        self.loaded = True

    def do_close(self):
        if self.flags is not None and (self.flags == 'c' or self.flags == 'w'):
            if self._is_new:
                insert = self.table.insert()
                self.bind.execute(insert, namespace=self.namespace, data=self.hash,
                                  accessed=datetime.now(), created=datetime.now())
                self._is_new = False
            else:
                update = self.table.update(self.table.c.namespace == self.namespace)
                self.bind.execute(update, data=self.hash, accessed=datetime.now())
        self.flags = None

    def do_remove(self):
        delete = self.table.delete(self.table.c.namespace == self.namespace)
        self.bind.execute(delete)
        self.hash = {}
        self._is_new = True

    def __getitem__(self, key):
        return self.hash[key]

    def __contains__(self, key):
        return key in self.hash

    def __setitem__(self, key, value):
        self.hash[key] = value

    def __delitem__(self, key):
        del self.hash[key]

    def keys(self):
        return self.hash.keys()


class SqlaContainer(Container):
    namespace_manager = SqlaNamespaceManager


def make_cache_table(metadata, table_name='beaker_cache', schema_name=None):
    """Return a ``Table`` object suitable for storing cached values for the
    namespace manager.  Do not create the table."""
    return sa.Table(table_name, metadata,
                    sa.Column('namespace', sa.String(255), primary_key=True),
                    sa.Column('accessed', sa.DateTime, nullable=False),
                    sa.Column('created', sa.DateTime, nullable=False),
                    sa.Column('data', sa.PickleType, nullable=False),
                    schema=schema_name if schema_name else metadata.schema)

########NEW FILE########
__FILENAME__ = middleware
import warnings

try:
    from paste.registry import StackedObjectProxy
    beaker_session = StackedObjectProxy(name="Beaker Session")
    beaker_cache = StackedObjectProxy(name="Cache Manager")
except:
    beaker_cache = None
    beaker_session = None

from beaker.cache import CacheManager
from beaker.session import Session, SessionObject
from beaker.util import coerce_cache_params, coerce_session_params, \
    parse_cache_config_options


class CacheMiddleware(object):
    cache = beaker_cache

    def __init__(self, app, config=None, environ_key='beaker.cache', **kwargs):
        """Initialize the Cache Middleware

        The Cache middleware will make a CacheManager instance available
        every request under the ``environ['beaker.cache']`` key by
        default. The location in environ can be changed by setting
        ``environ_key``.

        ``config``
            dict  All settings should be prefixed by 'cache.'. This
            method of passing variables is intended for Paste and other
            setups that accumulate multiple component settings in a
            single dictionary. If config contains *no cache. prefixed
            args*, then *all* of the config options will be used to
            intialize the Cache objects.

        ``environ_key``
            Location where the Cache instance will keyed in the WSGI
            environ

        ``**kwargs``
            All keyword arguments are assumed to be cache settings and
            will override any settings found in ``config``

        """
        self.app = app
        config = config or {}

        self.options = {}

        # Update the options with the parsed config
        self.options.update(parse_cache_config_options(config))

        # Add any options from kwargs, but leave out the defaults this
        # time
        self.options.update(
            parse_cache_config_options(kwargs, include_defaults=False))

        # Assume all keys are intended for cache if none are prefixed with
        # 'cache.'
        if not self.options and config:
            self.options = config

        self.options.update(kwargs)
        self.cache_manager = CacheManager(**self.options)
        self.environ_key = environ_key

    def __call__(self, environ, start_response):
        if environ.get('paste.registry'):
            if environ['paste.registry'].reglist:
                environ['paste.registry'].register(self.cache,
                                                   self.cache_manager)
        environ[self.environ_key] = self.cache_manager
        return self.app(environ, start_response)


class SessionMiddleware(object):
    session = beaker_session

    def __init__(self, wrap_app, config=None, environ_key='beaker.session',
                 **kwargs):
        """Initialize the Session Middleware

        The Session middleware will make a lazy session instance
        available every request under the ``environ['beaker.session']``
        key by default. The location in environ can be changed by
        setting ``environ_key``.

        ``config``
            dict  All settings should be prefixed by 'session.'. This
            method of passing variables is intended for Paste and other
            setups that accumulate multiple component settings in a
            single dictionary. If config contains *no session. prefixed
            args*, then *all* of the config options will be used to
            intialize the Session objects.

        ``environ_key``
            Location where the Session instance will keyed in the WSGI
            environ

        ``**kwargs``
            All keyword arguments are assumed to be session settings and
            will override any settings found in ``config``

        """
        config = config or {}

        # Load up the default params
        self.options = dict(invalidate_corrupt=True, type=None,
                           data_dir=None, key='beaker.session.id',
                           timeout=None, secret=None, log_file=None)

        # Pull out any config args meant for beaker session. if there are any
        for dct in [config, kwargs]:
            for key, val in dct.iteritems():
                if key.startswith('beaker.session.'):
                    self.options[key[15:]] = val
                if key.startswith('session.'):
                    self.options[key[8:]] = val
                if key.startswith('session_'):
                    warnings.warn('Session options should start with session. '
                                  'instead of session_.', DeprecationWarning, 2)
                    self.options[key[8:]] = val

        # Coerce and validate session params
        coerce_session_params(self.options)

        # Assume all keys are intended for session if none are prefixed with
        # 'session.'
        if not self.options and config:
            self.options = config

        self.options.update(kwargs)
        self.wrap_app = self.app = wrap_app
        self.environ_key = environ_key

    def __call__(self, environ, start_response):
        session = SessionObject(environ, **self.options)
        if environ.get('paste.registry'):
            if environ['paste.registry'].reglist:
                environ['paste.registry'].register(self.session, session)
        environ[self.environ_key] = session
        environ['beaker.get_session'] = self._get_session

        if 'paste.testing_variables' in environ and 'webtest_varname' in self.options:
            environ['paste.testing_variables'][self.options['webtest_varname']] = session

        def session_start_response(status, headers, exc_info=None):
            if session.accessed():
                session.persist()
                if session.__dict__['_headers']['set_cookie']:
                    cookie = session.__dict__['_headers']['cookie_out']
                    if cookie:
                        headers.append(('Set-cookie', cookie))
            return start_response(status, headers, exc_info)
        return self.wrap_app(environ, session_start_response)

    def _get_session(self):
        return Session({}, use_cookies=False, **self.options)


def session_filter_factory(global_conf, **kwargs):
    def filter(app):
        return SessionMiddleware(app, global_conf, **kwargs)
    return filter


def session_filter_app_factory(app, global_conf, **kwargs):
    return SessionMiddleware(app, global_conf, **kwargs)

########NEW FILE########
__FILENAME__ = session
import Cookie
import os
from datetime import datetime, timedelta
import time
from beaker.crypto import hmac as HMAC, hmac_sha1 as SHA1, sha1
from beaker import crypto, util
from beaker.cache import clsmap
from beaker.exceptions import BeakerException, InvalidCryptoBackendError
from base64 import b64encode, b64decode


__all__ = ['SignedCookie', 'Session']


try:
    import uuid

    def _session_id():
        return uuid.uuid4().hex
except ImportError:
    import random
    if hasattr(os, 'getpid'):
        getpid = os.getpid
    else:
        def getpid():
            return ''

    def _session_id():
        id_str = "%f%s%f%s" % (
                    time.time(),
                    id({}),
                    random.random(),
                    getpid()
                )
        # NB: nothing against second parameter to b64encode, but it seems
        #     to be slower than simple chained replacement
        if util.py3k:
            raw_id = b64encode(sha1(id_str.encode('ascii')).digest())
            return str(raw_id.replace(b'+', b'-').replace(b'/', b'_').rstrip(b'='))
        else:
            raw_id = b64encode(sha1(id_str).digest())
            return raw_id.replace('+', '-').replace('/', '_').rstrip('=')


class SignedCookie(Cookie.BaseCookie):
    """Extends python cookie to give digital signature support"""
    def __init__(self, secret, input=None):
        self.secret = secret.encode('UTF-8')
        Cookie.BaseCookie.__init__(self, input)

    def value_decode(self, val):
        val = val.strip('"')
        sig = HMAC.new(self.secret, val[40:].encode('UTF-8'), SHA1).hexdigest()

        # Avoid timing attacks
        invalid_bits = 0
        input_sig = val[:40]
        if len(sig) != len(input_sig):
            return None, val

        for a, b in zip(sig, input_sig):
            invalid_bits += a != b

        if invalid_bits:
            return None, val
        else:
            return val[40:], val

    def value_encode(self, val):
        sig = HMAC.new(self.secret, val.encode('UTF-8'), SHA1).hexdigest()
        return str(val), ("%s%s" % (sig, val))


class Session(dict):
    """Session object that uses container package for storage.

    :param invalidate_corrupt: How to handle corrupt data when loading. When
                               set to True, then corrupt data will be silently
                               invalidated and a new session created,
                               otherwise invalid data will cause an exception.
    :type invalidate_corrupt: bool
    :param use_cookies: Whether or not cookies should be created. When set to
                        False, it is assumed the user will handle storing the
                        session on their own.
    :type use_cookies: bool
    :param type: What data backend type should be used to store the underlying
                 session data
    :param key: The name the cookie should be set to.
    :param timeout: How long session data is considered valid. This is used
                    regardless of the cookie being present or not to determine
                    whether session data is still valid.
    :type timeout: int
    :param cookie_expires: Expiration date for cookie
    :param cookie_domain: Domain to use for the cookie.
    :param cookie_path: Path to use for the cookie.
    :param secure: Whether or not the cookie should only be sent over SSL.
    :param httponly: Whether or not the cookie should only be accessible by
                     the browser not by JavaScript.
    :param encrypt_key: The key to use for the local session encryption, if not
                        provided the session will not be encrypted.
    :param validate_key: The key used to sign the local encrypted session

    """
    def __init__(self, request, id=None, invalidate_corrupt=False,
                 use_cookies=True, type=None, data_dir=None,
                 key='beaker.session.id', timeout=None, cookie_expires=True,
                 cookie_domain=None, cookie_path='/', secret=None,
                 secure=False, namespace_class=None, httponly=False,
                 encrypt_key=None, validate_key=None, **namespace_args):
        if not type:
            if data_dir:
                self.type = 'file'
            else:
                self.type = 'memory'
        else:
            self.type = type

        self.namespace_class = namespace_class or clsmap[self.type]

        self.namespace_args = namespace_args

        self.request = request
        self.data_dir = data_dir
        self.key = key

        self.timeout = timeout
        self.use_cookies = use_cookies
        self.cookie_expires = cookie_expires

        # Default cookie domain/path
        self._domain = cookie_domain
        self._path = cookie_path
        self.was_invalidated = False
        self.secret = secret
        self.secure = secure
        self.httponly = httponly
        self.encrypt_key = encrypt_key
        self.validate_key = validate_key
        self.id = id
        self.accessed_dict = {}
        self.invalidate_corrupt = invalidate_corrupt

        if self.use_cookies:
            cookieheader = request.get('cookie', '')
            if secret:
                try:
                    self.cookie = SignedCookie(secret, input=cookieheader)
                except Cookie.CookieError:
                    self.cookie = SignedCookie(secret, input=None)
            else:
                self.cookie = Cookie.SimpleCookie(input=cookieheader)

            if not self.id and self.key in self.cookie:
                self.id = self.cookie[self.key].value

        self.is_new = self.id is None
        if self.is_new:
            self._create_id()
            self['_accessed_time'] = self['_creation_time'] = time.time()
        else:
            try:
                self.load()
            except Exception, e:
                if invalidate_corrupt:
                    util.warn(
                        "Invalidating corrupt session %s; "
                        "error was: %s.  Set invalidate_corrupt=False "
                        "to propagate this exception." % (self.id, e))
                    self.invalidate()
                else:
                    raise

    def has_key(self, name):
        return name in self

    def _set_cookie_values(self, expires=None):
        self.cookie[self.key] = self.id
        if self._domain:
            self.cookie[self.key]['domain'] = self._domain
        if self.secure:
            self.cookie[self.key]['secure'] = True
        self._set_cookie_http_only()
        self.cookie[self.key]['path'] = self._path

        self._set_cookie_expires(expires)

    def _set_cookie_expires(self, expires):
        if expires is None:
            if self.cookie_expires is not True:
                if self.cookie_expires is False:
                    expires = datetime.fromtimestamp(0x7FFFFFFF)
                elif isinstance(self.cookie_expires, timedelta):
                    expires = datetime.utcnow() + self.cookie_expires
                elif isinstance(self.cookie_expires, datetime):
                    expires = self.cookie_expires
                else:
                    raise ValueError("Invalid argument for cookie_expires: %s"
                                     % repr(self.cookie_expires))
            else:
                expires = None
        if expires is not None:
            if not self.cookie or self.key not in self.cookie:
                self.cookie[self.key] = self.id
            self.cookie[self.key]['expires'] = \
                expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
        return expires

    def _update_cookie_out(self, set_cookie=True):
        self.request['cookie_out'] = self.cookie[self.key].output(header='')
        self.request['set_cookie'] = set_cookie

    def _set_cookie_http_only(self):
        try:
            if self.httponly:
                self.cookie[self.key]['httponly'] = True
        except Cookie.CookieError, e:
            if 'Invalid Attribute httponly' not in str(e):
                raise
            util.warn('Python 2.6+ is required to use httponly')

    def _create_id(self, set_new=True):
        self.id = _session_id()

        if set_new:
            self.is_new = True
            self.last_accessed = None
        if self.use_cookies:
            self._set_cookie_values()
            sc = set_new == False
            self._update_cookie_out(set_cookie=sc)

    @property
    def created(self):
        return self['_creation_time']

    def _set_domain(self, domain):
        self['_domain'] = domain
        self.cookie[self.key]['domain'] = domain
        self._update_cookie_out()

    def _get_domain(self):
        return self._domain

    domain = property(_get_domain, _set_domain)

    def _set_path(self, path):
        self['_path'] = self._path = path
        self.cookie[self.key]['path'] = path
        self._update_cookie_out()

    def _get_path(self):
        return self._path

    path = property(_get_path, _set_path)

    def _encrypt_data(self, session_data=None):
        """Serialize, encipher, and base64 the session dict"""
        session_data = session_data or self.copy()
        if self.encrypt_key:
            nonce = b64encode(os.urandom(6))[:8]
            encrypt_key = crypto.generateCryptoKeys(self.encrypt_key,
                                             self.validate_key + nonce, 1)
            data = util.pickle.dumps(session_data, 2)
            return nonce + b64encode(crypto.aesEncrypt(data, encrypt_key))
        else:
            data = util.pickle.dumps(session_data, 2)
            return b64encode(data)

    def _decrypt_data(self, session_data):
        """Bas64, decipher, then un-serialize the data for the session
        dict"""
        if self.encrypt_key:
            try:
                nonce = session_data[:8]
                encrypt_key = crypto.generateCryptoKeys(self.encrypt_key,
                                                 self.validate_key + nonce, 1)
                payload = b64decode(session_data[8:])
                data = crypto.aesDecrypt(payload, encrypt_key)
            except:
                # As much as I hate a bare except, we get some insane errors
                # here that get tossed when crypto fails, so we raise the
                # 'right' exception
                if self.invalidate_corrupt:
                    return None
                else:
                    raise
            try:
                return util.pickle.loads(data)
            except:
                if self.invalidate_corrupt:
                    return None
                else:
                    raise
        else:
            data = b64decode(session_data)
            return util.pickle.loads(data)

    def _delete_cookie(self):
        self.request['set_cookie'] = True
        expires = datetime.utcnow() - timedelta(365)
        self._set_cookie_values(expires)
        self._update_cookie_out()

    def delete(self):
        """Deletes the session from the persistent storage, and sends
        an expired cookie out"""
        if self.use_cookies:
            self._delete_cookie()
        self.clear()

    def invalidate(self):
        """Invalidates this session, creates a new session id, returns
        to the is_new state"""
        self.clear()
        self.was_invalidated = True
        self._create_id()
        self.load()

    def load(self):
        "Loads the data from this session from persistent storage"
        self.namespace = self.namespace_class(self.id,
            data_dir=self.data_dir,
            digest_filenames=False,
            **self.namespace_args)
        now = time.time()
        if self.use_cookies:
            self.request['set_cookie'] = True

        self.namespace.acquire_read_lock()
        timed_out = False
        try:
            self.clear()
            try:
                session_data = self.namespace['session']

                if (session_data is not None and self.encrypt_key):
                    session_data = self._decrypt_data(session_data)

                # Memcached always returns a key, its None when its not
                # present
                if session_data is None:
                    session_data = {
                        '_creation_time': now,
                        '_accessed_time': now
                    }
                    self.is_new = True
            except (KeyError, TypeError):
                session_data = {
                    '_creation_time': now,
                    '_accessed_time': now
                }
                self.is_new = True

            if session_data is None or len(session_data) == 0:
                session_data = {
                    '_creation_time': now,
                    '_accessed_time': now
                }
                self.is_new = True

            if self.timeout is not None and \
               now - session_data['_accessed_time'] > self.timeout:
                timed_out = True
            else:
                # Properly set the last_accessed time, which is different
                # than the *currently* _accessed_time
                if self.is_new or '_accessed_time' not in session_data:
                    self.last_accessed = None
                else:
                    self.last_accessed = session_data['_accessed_time']

                # Update the current _accessed_time
                session_data['_accessed_time'] = now

                # Set the path if applicable
                if '_path' in session_data:
                    self._path = session_data['_path']
                self.update(session_data)
                self.accessed_dict = session_data.copy()
        finally:
            self.namespace.release_read_lock()
        if timed_out:
            self.invalidate()

    def save(self, accessed_only=False):
        """Saves the data for this session to persistent storage

        If accessed_only is True, then only the original data loaded
        at the beginning of the request will be saved, with the updated
        last accessed time.

        """
        # Look to see if its a new session that was only accessed
        # Don't save it under that case
        if accessed_only and self.is_new:
            return None

        # this session might not have a namespace yet or the session id
        # might have been regenerated
        if not hasattr(self, 'namespace') or self.namespace.namespace != self.id:
            self.namespace = self.namespace_class(
                                    self.id,
                                    data_dir=self.data_dir,
                                    digest_filenames=False,
                                    **self.namespace_args)

        self.namespace.acquire_write_lock(replace=True)
        try:
            if accessed_only:
                data = dict(self.accessed_dict.items())
            else:
                data = dict(self.items())

            if self.encrypt_key:
                data = self._encrypt_data(data)

            # Save the data
            if not data and 'session' in self.namespace:
                del self.namespace['session']
            else:
                self.namespace['session'] = data
        finally:
            self.namespace.release_write_lock()
        if self.use_cookies and self.is_new:
            self.request['set_cookie'] = True

    def revert(self):
        """Revert the session to its original state from its first
        access in the request"""
        self.clear()
        self.update(self.accessed_dict)

    def regenerate_id(self):
        """
            creates a new session id, retains all session data

            Its a good security practice to regnerate the id after a client
            elevates priviliges.

        """
        self._create_id(set_new=False)

    # TODO: I think both these methods should be removed.  They're from
    # the original mod_python code i was ripping off but they really
    # have no use here.
    def lock(self):
        """Locks this session against other processes/threads.  This is
        automatic when load/save is called.

        ***use with caution*** and always with a corresponding 'unlock'
        inside a "finally:" block, as a stray lock typically cannot be
        unlocked without shutting down the whole application.

        """
        self.namespace.acquire_write_lock()

    def unlock(self):
        """Unlocks this session against other processes/threads.  This
        is automatic when load/save is called.

        ***use with caution*** and always within a "finally:" block, as
        a stray lock typically cannot be unlocked without shutting down
        the whole application.

        """
        self.namespace.release_write_lock()


class CookieSession(Session):
    """Pure cookie-based session

    Options recognized when using cookie-based sessions are slightly
    more restricted than general sessions.

    :param key: The name the cookie should be set to.
    :param timeout: How long session data is considered valid. This is used
                    regardless of the cookie being present or not to determine
                    whether session data is still valid.
    :type timeout: int
    :param cookie_expires: Expiration date for cookie
    :param cookie_domain: Domain to use for the cookie.
    :param cookie_path: Path to use for the cookie.
    :param secure: Whether or not the cookie should only be sent over SSL.
    :param httponly: Whether or not the cookie should only be accessible by
                     the browser not by JavaScript.
    :param encrypt_key: The key to use for the local session encryption, if not
                        provided the session will not be encrypted.
    :param validate_key: The key used to sign the local encrypted session

    """
    def __init__(self, request, key='beaker.session.id', timeout=None,
                 cookie_expires=True, cookie_domain=None, cookie_path='/',
                 encrypt_key=None, validate_key=None, secure=False,
                 httponly=False, **kwargs):

        if not crypto.has_aes and encrypt_key:
            raise InvalidCryptoBackendError("No AES library is installed, can't generate "
                                  "encrypted cookie-only Session.")

        self.request = request
        self.key = key
        self.timeout = timeout
        self.cookie_expires = cookie_expires
        self.encrypt_key = encrypt_key
        self.validate_key = validate_key
        self.request['set_cookie'] = False
        self.secure = secure
        self.httponly = httponly
        self._domain = cookie_domain
        self._path = cookie_path

        try:
            cookieheader = request['cookie']
        except KeyError:
            cookieheader = ''

        if validate_key is None:
            raise BeakerException("No validate_key specified for Cookie only "
                                  "Session.")

        try:
            self.cookie = SignedCookie(validate_key, input=cookieheader)
        except Cookie.CookieError:
            self.cookie = SignedCookie(validate_key, input=None)

        self['_id'] = _session_id()
        self.is_new = True

        # If we have a cookie, load it
        if self.key in self.cookie and self.cookie[self.key].value is not None:
            self.is_new = False
            try:
                cookie_data = self.cookie[self.key].value
                self.update(self._decrypt_data(cookie_data))
                self._path = self.get('_path', '/')
            except:
                pass
            if self.timeout is not None and time.time() - \
               self['_accessed_time'] > self.timeout:
                self.clear()
            self.accessed_dict = self.copy()
            self._create_cookie()

    def created(self):
        return self['_creation_time']
    created = property(created)

    def id(self):
        return self['_id']
    id = property(id)

    def _set_domain(self, domain):
        self['_domain'] = domain
        self._domain = domain

    def _get_domain(self):
        return self._domain

    domain = property(_get_domain, _set_domain)

    def _set_path(self, path):
        self['_path'] = self._path = path

    def _get_path(self):
        return self._path

    path = property(_get_path, _set_path)

    def save(self, accessed_only=False):
        """Saves the data for this session to persistent storage"""
        if accessed_only and self.is_new:
            return
        if accessed_only:
            self.clear()
            self.update(self.accessed_dict)
        self._create_cookie()

    def expire(self):
        """Delete the 'expires' attribute on this Session, if any."""

        self.pop('_expires', None)

    def _create_cookie(self):
        if '_creation_time' not in self:
            self['_creation_time'] = time.time()
        if '_id' not in self:
            self['_id'] = _session_id()
        self['_accessed_time'] = time.time()

        val = self._encrypt_data()
        if len(val) > 4064:
            raise BeakerException("Cookie value is too long to store")

        self.cookie[self.key] = val

        if '_expires' in self:
            expires = self['_expires']
        else:
            expires = None
        expires = self._set_cookie_expires(expires)
        if expires is not None:
            self['_expires'] = expires

        if '_domain' in self:
            self.cookie[self.key]['domain'] = self['_domain']
        elif self._domain:
            self.cookie[self.key]['domain'] = self._domain
        if self.secure:
            self.cookie[self.key]['secure'] = True
        self._set_cookie_http_only()

        self.cookie[self.key]['path'] = self.get('_path', '/')

        self.request['cookie_out'] = self.cookie[self.key].output(header='')
        self.request['set_cookie'] = True

    def delete(self):
        """Delete the cookie, and clear the session"""
        # Send a delete cookie request
        self._delete_cookie()
        self.clear()

    def invalidate(self):
        """Clear the contents and start a new session"""
        self.clear()
        self['_id'] = _session_id()


class SessionObject(object):
    """Session proxy/lazy creator

    This object proxies access to the actual session object, so that in
    the case that the session hasn't been used before, it will be
    setup. This avoid creating and loading the session from persistent
    storage unless its actually used during the request.

    """
    def __init__(self, environ, **params):
        self.__dict__['_params'] = params
        self.__dict__['_environ'] = environ
        self.__dict__['_sess'] = None
        self.__dict__['_headers'] = {}

    def _session(self):
        """Lazy initial creation of session object"""
        if self.__dict__['_sess'] is None:
            params = self.__dict__['_params']
            environ = self.__dict__['_environ']
            self.__dict__['_headers'] = req = {'cookie_out': None}
            req['cookie'] = environ.get('HTTP_COOKIE')
            if params.get('type') == 'cookie':
                self.__dict__['_sess'] = CookieSession(req, **params)
            else:
                self.__dict__['_sess'] = Session(req, use_cookies=True,
                                                 **params)
        return self.__dict__['_sess']

    def __getattr__(self, attr):
        return getattr(self._session(), attr)

    def __setattr__(self, attr, value):
        setattr(self._session(), attr, value)

    def __delattr__(self, name):
        self._session().__delattr__(name)

    def __getitem__(self, key):
        return self._session()[key]

    def __setitem__(self, key, value):
        self._session()[key] = value

    def __delitem__(self, key):
        self._session().__delitem__(key)

    def __repr__(self):
        return self._session().__repr__()

    def __iter__(self):
        """Only works for proxying to a dict"""
        return iter(self._session().keys())

    def __contains__(self, key):
        return key in self._session()

    def has_key(self, key):
        return key in self._session()

    def get_by_id(self, id):
        """Loads a session given a session ID"""
        params = self.__dict__['_params']
        session = Session({}, use_cookies=False, id=id, **params)
        if session.is_new:
            return None
        return session

    def save(self):
        self.__dict__['_dirty'] = True

    def delete(self):
        self.__dict__['_dirty'] = True
        self._session().delete()

    def persist(self):
        """Persist the session to the storage

        If its set to autosave, then the entire session will be saved
        regardless of if save() has been called. Otherwise, just the
        accessed time will be updated if save() was not called, or
        the session will be saved if save() was called.

        """
        if self.__dict__['_params'].get('auto'):
            self._session().save()
        else:
            if self.__dict__.get('_dirty'):
                self._session().save()
            else:
                self._session().save(accessed_only=True)

    def dirty(self):
        return self.__dict__.get('_dirty', False)

    def accessed(self):
        """Returns whether or not the session has been accessed"""
        return self.__dict__['_sess'] is not None

########NEW FILE########
__FILENAME__ = synchronization
"""Synchronization functions.

File- and mutex-based mutual exclusion synchronizers are provided,
as well as a name-based mutex which locks within an application
based on a string name.

"""

import os
import sys
import tempfile

try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading

# check for fcntl module
try:
    sys.getwindowsversion()
    has_flock = False
except:
    try:
        import fcntl
        has_flock = True
    except ImportError:
        has_flock = False

from beaker import util
from beaker.exceptions import LockError

__all__ = ["file_synchronizer", "mutex_synchronizer", "null_synchronizer",
            "NameLock", "_threading"]


class NameLock(object):
    """a proxy for an RLock object that is stored in a name based
    registry.

    Multiple threads can get a reference to the same RLock based on the
    name alone, and synchronize operations related to that name.

    """
    locks = util.WeakValuedRegistry()

    class NLContainer(object):
        def __init__(self, reentrant):
            if reentrant:
                self.lock = _threading.RLock()
            else:
                self.lock = _threading.Lock()

        def __call__(self):
            return self.lock

    def __init__(self, identifier=None, reentrant=False):
        if identifier is None:
            self._lock = NameLock.NLContainer(reentrant)
        else:
            self._lock = NameLock.locks.get(identifier, NameLock.NLContainer,
                                            reentrant)

    def acquire(self, wait=True):
        return self._lock().acquire(wait)

    def release(self):
        self._lock().release()


_synchronizers = util.WeakValuedRegistry()


def _synchronizer(identifier, cls, **kwargs):
    return _synchronizers.sync_get((identifier, cls), cls, identifier, **kwargs)


def file_synchronizer(identifier, **kwargs):
    if not has_flock or 'lock_dir' not in kwargs:
        return mutex_synchronizer(identifier)
    else:
        return _synchronizer(identifier, FileSynchronizer, **kwargs)


def mutex_synchronizer(identifier, **kwargs):
    return _synchronizer(identifier, ConditionSynchronizer, **kwargs)


class null_synchronizer(object):
    """A 'null' synchronizer, which provides the :class:`.SynchronizerImpl` interface
    without any locking.

    """
    def acquire_write_lock(self, wait=True):
        return True

    def acquire_read_lock(self):
        pass

    def release_write_lock(self):
        pass

    def release_read_lock(self):
        pass
    acquire = acquire_write_lock
    release = release_write_lock


class SynchronizerImpl(object):
    """Base class for a synchronization object that allows
    multiple readers, single writers.

    """
    def __init__(self):
        self._state = util.ThreadLocal()

    class SyncState(object):
        __slots__ = 'reentrantcount', 'writing', 'reading'

        def __init__(self):
            self.reentrantcount = 0
            self.writing = False
            self.reading = False

    def state(self):
        if not self._state.has():
            state = SynchronizerImpl.SyncState()
            self._state.put(state)
            return state
        else:
            return self._state.get()
    state = property(state)

    def release_read_lock(self):
        state = self.state

        if state.writing:
            raise LockError("lock is in writing state")
        if not state.reading:
            raise LockError("lock is not in reading state")

        if state.reentrantcount == 1:
            self.do_release_read_lock()
            state.reading = False

        state.reentrantcount -= 1

    def acquire_read_lock(self, wait=True):
        state = self.state

        if state.writing:
            raise LockError("lock is in writing state")

        if state.reentrantcount == 0:
            x = self.do_acquire_read_lock(wait)
            if (wait or x):
                state.reentrantcount += 1
                state.reading = True
            return x
        elif state.reading:
            state.reentrantcount += 1
            return True

    def release_write_lock(self):
        state = self.state

        if state.reading:
            raise LockError("lock is in reading state")
        if not state.writing:
            raise LockError("lock is not in writing state")

        if state.reentrantcount == 1:
            self.do_release_write_lock()
            state.writing = False

        state.reentrantcount -= 1

    release = release_write_lock

    def acquire_write_lock(self, wait=True):
        state = self.state

        if state.reading:
            raise LockError("lock is in reading state")

        if state.reentrantcount == 0:
            x = self.do_acquire_write_lock(wait)
            if (wait or x):
                state.reentrantcount += 1
                state.writing = True
            return x
        elif state.writing:
            state.reentrantcount += 1
            return True

    acquire = acquire_write_lock

    def do_release_read_lock(self):
        raise NotImplementedError()

    def do_acquire_read_lock(self):
        raise NotImplementedError()

    def do_release_write_lock(self):
        raise NotImplementedError()

    def do_acquire_write_lock(self):
        raise NotImplementedError()


class FileSynchronizer(SynchronizerImpl):
    """A synchronizer which locks using flock().

    """
    def __init__(self, identifier, lock_dir):
        super(FileSynchronizer, self).__init__()
        self._filedescriptor = util.ThreadLocal()

        if lock_dir is None:
            lock_dir = tempfile.gettempdir()
        else:
            lock_dir = lock_dir

        self.filename = util.encoded_path(
                            lock_dir,
                            [identifier],
                            extension='.lock'
                        )

    def _filedesc(self):
        return self._filedescriptor.get()
    _filedesc = property(_filedesc)

    def _open(self, mode):
        filedescriptor = self._filedesc
        if filedescriptor is None:
            filedescriptor = os.open(self.filename, mode)
            self._filedescriptor.put(filedescriptor)
        return filedescriptor

    def do_acquire_read_lock(self, wait):
        filedescriptor = self._open(os.O_CREAT | os.O_RDONLY)
        if not wait:
            try:
                fcntl.flock(filedescriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
                return True
            except IOError:
                os.close(filedescriptor)
                self._filedescriptor.remove()
                return False
        else:
            fcntl.flock(filedescriptor, fcntl.LOCK_SH)
            return True

    def do_acquire_write_lock(self, wait):
        filedescriptor = self._open(os.O_CREAT | os.O_WRONLY)
        if not wait:
            try:
                fcntl.flock(filedescriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except IOError:
                os.close(filedescriptor)
                self._filedescriptor.remove()
                return False
        else:
            fcntl.flock(filedescriptor, fcntl.LOCK_EX)
            return True

    def do_release_read_lock(self):
        self._release_all_locks()

    def do_release_write_lock(self):
        self._release_all_locks()

    def _release_all_locks(self):
        filedescriptor = self._filedesc
        if filedescriptor is not None:
            fcntl.flock(filedescriptor, fcntl.LOCK_UN)
            os.close(filedescriptor)
            self._filedescriptor.remove()


class ConditionSynchronizer(SynchronizerImpl):
    """a synchronizer using a Condition."""

    def __init__(self, identifier):
        super(ConditionSynchronizer, self).__init__()

        # counts how many asynchronous methods are executing
        self.async = 0

        # pointer to thread that is the current sync operation
        self.current_sync_operation = None

        # condition object to lock on
        self.condition = _threading.Condition(_threading.Lock())

    def do_acquire_read_lock(self, wait=True):
        self.condition.acquire()
        try:
            # see if a synchronous operation is waiting to start
            # or is already running, in which case we wait (or just
            # give up and return)
            if wait:
                while self.current_sync_operation is not None:
                    self.condition.wait()
            else:
                if self.current_sync_operation is not None:
                    return False

            self.async += 1
        finally:
            self.condition.release()

        if not wait:
            return True

    def do_release_read_lock(self):
        self.condition.acquire()
        try:
            self.async -= 1

            # check if we are the last asynchronous reader thread
            # out the door.
            if self.async == 0:
                # yes. so if a sync operation is waiting, notifyAll to wake
                # it up
                if self.current_sync_operation is not None:
                    self.condition.notifyAll()
            elif self.async < 0:
                raise LockError("Synchronizer error - too many "
                                "release_read_locks called")
        finally:
            self.condition.release()

    def do_acquire_write_lock(self, wait=True):
        self.condition.acquire()
        try:
            # here, we are not a synchronous reader, and after returning,
            # assuming waiting or immediate availability, we will be.

            if wait:
                # if another sync is working, wait
                while self.current_sync_operation is not None:
                    self.condition.wait()
            else:
                # if another sync is working,
                # we dont want to wait, so forget it
                if self.current_sync_operation is not None:
                    return False

            # establish ourselves as the current sync
            # this indicates to other read/write operations
            # that they should wait until this is None again
            self.current_sync_operation = _threading.currentThread()

            # now wait again for asyncs to finish
            if self.async > 0:
                if wait:
                    # wait
                    self.condition.wait()
                else:
                    # we dont want to wait, so forget it
                    self.current_sync_operation = None
                    return False
        finally:
            self.condition.release()

        if not wait:
            return True

    def do_release_write_lock(self):
        self.condition.acquire()
        try:
            if self.current_sync_operation is not _threading.currentThread():
                raise LockError("Synchronizer error - current thread doesnt "
                                "have the write lock")

            # reset the current sync operation so
            # another can get it
            self.current_sync_operation = None

            # tell everyone to get ready
            self.condition.notifyAll()
        finally:
            # everyone go !!
            self.condition.release()

########NEW FILE########
__FILENAME__ = util
"""Beaker utilities"""

try:
    import thread as _thread
    import threading as _threading
except ImportError:
    import dummy_thread as _thread
    import dummy_threading as _threading

from datetime import datetime, timedelta
import os
import re
import string
import types
import weakref
import warnings
import sys
import inspect

py3k = getattr(sys, 'py3kwarning', False) or sys.version_info >= (3, 0)
py24 = sys.version_info < (2, 5)
jython = sys.platform.startswith('java')

if py3k or jython:
    import pickle
else:
    import cPickle as pickle

from beaker.converters import asbool
from beaker import exceptions
from threading import local as _tlocal


__all__ = ["ThreadLocal", "WeakValuedRegistry", "SyncDict", "encoded_path",
           "verify_directory"]


def function_named(fn, name):
    """Return a function with a given __name__.

    Will assign to __name__ and return the original function if possible on
    the Python implementation, otherwise a new function will be constructed.

    """
    fn.__name__ = name
    return fn


def skip_if(predicate, reason=None):
    """Skip a test if predicate is true."""
    reason = reason or predicate.__name__

    from nose import SkipTest

    def decorate(fn):
        fn_name = fn.__name__

        def maybe(*args, **kw):
            if predicate():
                msg = "'%s' skipped: %s" % (
                    fn_name, reason)
                raise SkipTest(msg)
            else:
                return fn(*args, **kw)
        return function_named(maybe, fn_name)
    return decorate


def assert_raises(except_cls, callable_, *args, **kw):
    """Assert the given exception is raised by the given function + arguments."""

    try:
        callable_(*args, **kw)
        success = False
    except except_cls:
        success = True

    # assert outside the block so it works for AssertionError too !
    assert success, "Callable did not raise an exception"


def verify_directory(dir):
    """verifies and creates a directory.  tries to
    ignore collisions with other threads and processes."""

    tries = 0
    while not os.access(dir, os.F_OK):
        try:
            tries += 1
            os.makedirs(dir)
        except:
            if tries > 5:
                raise


def has_self_arg(func):
    """Return True if the given function has a 'self' argument."""
    args = inspect.getargspec(func)
    if args and args[0] and args[0][0] in ('self', 'cls'):
        return True
    else:
        return False


def warn(msg, stacklevel=3):
    """Issue a warning."""
    if isinstance(msg, basestring):
        warnings.warn(msg, exceptions.BeakerWarning, stacklevel=stacklevel)
    else:
        warnings.warn(msg, stacklevel=stacklevel)


def deprecated(message):
    def wrapper(fn):
        def deprecated_method(*args, **kargs):
            warnings.warn(message, DeprecationWarning, 2)
            return fn(*args, **kargs)
        # TODO: use decorator ?  functools.wrapper ?
        deprecated_method.__name__ = fn.__name__
        deprecated_method.__doc__ = "%s\n\n%s" % (message, fn.__doc__)
        return deprecated_method
    return wrapper


class ThreadLocal(object):
    """stores a value on a per-thread basis"""

    __slots__ = '_tlocal'

    def __init__(self):
        self._tlocal = _tlocal()

    def put(self, value):
        self._tlocal.value = value

    def has(self):
        return hasattr(self._tlocal, 'value')

    def get(self, default=None):
        return getattr(self._tlocal, 'value', default)

    def remove(self):
        del self._tlocal.value


class SyncDict(object):
    """
    An efficient/threadsafe singleton map algorithm, a.k.a.
    "get a value based on this key, and create if not found or not
    valid" paradigm:

        exists && isvalid ? get : create

    Designed to work with weakref dictionaries to expect items
    to asynchronously disappear from the dictionary.

    Use python 2.3.3 or greater !  a major bug was just fixed in Nov.
    2003 that was driving me nuts with garbage collection/weakrefs in
    this section.

    """
    def __init__(self):
        self.mutex = _thread.allocate_lock()
        self.dict = {}

    def get(self, key, createfunc, *args, **kwargs):
        try:
            if key in self.dict:
                return self.dict[key]
            else:
                return self.sync_get(key, createfunc, *args, **kwargs)
        except KeyError:
            return self.sync_get(key, createfunc, *args, **kwargs)

    def sync_get(self, key, createfunc, *args, **kwargs):
        self.mutex.acquire()
        try:
            try:
                if key in self.dict:
                    return self.dict[key]
                else:
                    return self._create(key, createfunc, *args, **kwargs)
            except KeyError:
                return self._create(key, createfunc, *args, **kwargs)
        finally:
            self.mutex.release()

    def _create(self, key, createfunc, *args, **kwargs):
        self[key] = obj = createfunc(*args, **kwargs)
        return obj

    def has_key(self, key):
        return key in self.dict

    def __contains__(self, key):
        return self.dict.__contains__(key)

    def __getitem__(self, key):
        return self.dict.__getitem__(key)

    def __setitem__(self, key, value):
        self.dict.__setitem__(key, value)

    def __delitem__(self, key):
        return self.dict.__delitem__(key)

    def clear(self):
        self.dict.clear()


class WeakValuedRegistry(SyncDict):
    def __init__(self):
        self.mutex = _threading.RLock()
        self.dict = weakref.WeakValueDictionary()

sha1 = None


def encoded_path(root, identifiers, extension=".enc", depth=3,
                 digest_filenames=True):

    """Generate a unique file-accessible path from the given list of
    identifiers starting at the given root directory."""
    ident = "_".join(identifiers)

    global sha1
    if sha1 is None:
        from beaker.crypto import sha1

    if digest_filenames:
        if py3k:
            ident = sha1(ident.encode('utf-8')).hexdigest()
        else:
            ident = sha1(ident).hexdigest()

    ident = os.path.basename(ident)

    tokens = []
    for d in range(1, depth):
        tokens.append(ident[0:d])

    dir = os.path.join(root, *tokens)
    verify_directory(dir)

    return os.path.join(dir, ident + extension)


def asint(obj):
    if isinstance(obj, int):
        return obj
    elif isinstance(obj, basestring) and re.match(r'^\d+$', obj):
        return int(obj)
    else:
        raise Exception("This is not a proper int")


def verify_options(opt, types, error):
    if not isinstance(opt, types):
        if not isinstance(types, tuple):
            types = (types,)
        coerced = False
        for typ in types:
            try:
                if typ in (list, tuple):
                    opt = [x.strip() for x in opt.split(',')]
                else:
                    if typ == bool:
                        typ = asbool
                    elif typ == int:
                        typ = asint
                    elif typ in (timedelta, datetime):
                        if not isinstance(opt, typ):
                            raise Exception("%s requires a timedelta type", typ)
                    opt = typ(opt)
                coerced = True
            except:
                pass
            if coerced:
                break
        if not coerced:
            raise Exception(error)
    elif isinstance(opt, str) and not opt.strip():
        raise Exception("Empty strings are invalid for: %s" % error)
    return opt


def verify_rules(params, ruleset):
    for key, types, message in ruleset:
        if key in params:
            params[key] = verify_options(params[key], types, message)
    return params


def coerce_session_params(params):
    rules = [
        ('data_dir', (str, types.NoneType), "data_dir must be a string "
         "referring to a directory."),
        ('lock_dir', (str, types.NoneType), "lock_dir must be a string referring to a "
         "directory."),
        ('type', (str, types.NoneType), "Session type must be a string."),
        ('cookie_expires', (bool, datetime, timedelta, int), "Cookie expires was "
         "not a boolean, datetime, int, or timedelta instance."),
        ('cookie_domain', (str, types.NoneType), "Cookie domain must be a "
         "string."),
        ('cookie_path', (str, types.NoneType), "Cookie path must be a "
         "string."),
        ('id', (str,), "Session id must be a string."),
        ('key', (str,), "Session key must be a string."),
        ('secret', (str, types.NoneType), "Session secret must be a string."),
        ('validate_key', (str, types.NoneType), "Session encrypt_key must be "
         "a string."),
        ('encrypt_key', (str, types.NoneType), "Session validate_key must be "
         "a string."),
        ('secure', (bool, types.NoneType), "Session secure must be a boolean."),
        ('httponly', (bool, types.NoneType), "Session httponly must be a boolean."),
        ('timeout', (int, types.NoneType), "Session timeout must be an "
         "integer."),
        ('auto', (bool, types.NoneType), "Session is created if accessed."),
        ('webtest_varname', (str, types.NoneType), "Session varname must be "
         "a string."),
    ]
    opts = verify_rules(params, rules)
    cookie_expires = opts.get('cookie_expires')
    if cookie_expires and isinstance(cookie_expires, int) and \
       not isinstance(cookie_expires, bool):
        opts['cookie_expires'] = timedelta(seconds=cookie_expires)
    return opts


def coerce_cache_params(params):
    rules = [
        ('data_dir', (str, types.NoneType), "data_dir must be a string "
         "referring to a directory."),
        ('lock_dir', (str, types.NoneType), "lock_dir must be a string referring to a "
         "directory."),
        ('type', (str,), "Cache type must be a string."),
        ('enabled', (bool, types.NoneType), "enabled must be true/false "
         "if present."),
        ('expire', (int, types.NoneType), "expire must be an integer representing "
         "how many seconds the cache is valid for"),
        ('regions', (list, tuple, types.NoneType), "Regions must be a "
         "comma seperated list of valid regions"),
        ('key_length', (int, types.NoneType), "key_length must be an integer "
         "which indicates the longest a key can be before hashing"),
    ]
    return verify_rules(params, rules)


def coerce_memcached_behaviors(behaviors):
    rules = [
        ('cas', (bool, int), 'cas must be a boolean or an integer'),
        ('no_block', (bool, int), 'no_block must be a boolean or an integer'),
        ('receive_timeout', (int,), 'receive_timeout must be an integer'),
        ('send_timeout', (int,), 'send_timeout must be an integer'),
        ('ketama_hash', (str,), 'ketama_hash must be a string designating '
         'a valid hashing strategy option'),
        ('_poll_timeout', (int,), '_poll_timeout must be an integer'),
        ('auto_eject', (bool, int), 'auto_eject must be an integer'),
        ('retry_timeout', (int,), 'retry_timeout must be an integer'),
        ('_sort_hosts', (bool, int), '_sort_hosts must be an integer'),
        ('_io_msg_watermark', (int,), '_io_msg_watermark must be an integer'),
        ('ketama', (bool, int), 'ketama must be a boolean or an integer'),
        ('ketama_weighted', (bool, int), 'ketama_weighted must be a boolean or '
         'an integer'),
        ('_io_key_prefetch', (int, bool), '_io_key_prefetch must be a boolean '
         'or an integer'),
        ('_hash_with_prefix_key', (bool, int), '_hash_with_prefix_key must be '
         'a boolean or an integer'),
        ('tcp_nodelay', (bool, int), 'tcp_nodelay must be a boolean or an '
         'integer'),
        ('failure_limit', (int,), 'failure_limit must be an integer'),
        ('buffer_requests', (bool, int), 'buffer_requests must be a boolean '
         'or an integer'),
        ('_socket_send_size', (int,), '_socket_send_size must be an integer'),
        ('num_replicas', (int,), 'num_replicas must be an integer'),
        ('remove_failed', (int,), 'remove_failed must be an integer'),
        ('_noreply', (bool, int), '_noreply must be a boolean or an integer'),
        ('_io_bytes_watermark', (int,), '_io_bytes_watermark must be an '
         'integer'),
        ('_socket_recv_size', (int,), '_socket_recv_size must be an integer'),
        ('distribution', (str,), 'distribution must be a string designating '
         'a valid distribution option'),
        ('connect_timeout', (int,), 'connect_timeout must be an integer'),
        ('hash', (str,), 'hash must be a string designating a valid hashing '
         'option'),
        ('verify_keys', (bool, int), 'verify_keys must be a boolean or an integer'),
        ('dead_timeout', (int,), 'dead_timeout must be an integer')
    ]
    return verify_rules(behaviors, rules)


def parse_cache_config_options(config, include_defaults=True):
    """Parse configuration options and validate for use with the
    CacheManager"""

    # Load default cache options
    if include_defaults:
        options = dict(type='memory', data_dir=None, expire=None,
                           log_file=None)
    else:
        options = {}
    for key, val in config.iteritems():
        if key.startswith('beaker.cache.'):
            options[key[13:]] = val
        if key.startswith('cache.'):
            options[key[6:]] = val
    coerce_cache_params(options)

    # Set cache to enabled if not turned off
    if 'enabled' not in options and include_defaults:
        options['enabled'] = True

    # Configure region dict if regions are available
    regions = options.pop('regions', None)
    if regions:
        region_configs = {}
        for region in regions:
            if not region:  # ensure region name is valid
                continue
            # Setup the default cache options
            region_options = dict(data_dir=options.get('data_dir'),
                                  lock_dir=options.get('lock_dir'),
                                  type=options.get('type'),
                                  enabled=options['enabled'],
                                  expire=options.get('expire'),
                                  key_length=options.get('key_length', 250))
            region_prefix = '%s.' % region
            region_len = len(region_prefix)
            for key in options.keys():
                if key.startswith(region_prefix):
                    region_options[key[region_len:]] = options.pop(key)
            coerce_cache_params(region_options)
            region_configs[region] = region_options
        options['cache_regions'] = region_configs
    return options


def parse_memcached_behaviors(config):
    """Parse behavior options and validate for use with pylibmc
    client/PylibMCNamespaceManager, or potentially other memcached
    NamespaceManagers that support behaviors"""
    behaviors = {}

    for key, val in config.iteritems():
        if key.startswith('behavior.'):
            behaviors[key[9:]] = val

    coerce_memcached_behaviors(behaviors)
    return behaviors


def func_namespace(func):
    """Generates a unique namespace for a function"""
    kls = None
    if hasattr(func, 'im_func'):
        kls = func.im_class
        func = func.im_func

    if kls:
        return '%s.%s' % (kls.__module__, kls.__name__)
    else:
        return '%s|%s' % (inspect.getsourcefile(func), func.__name__)

########NEW FILE########
__FILENAME__ = test_cache
# coding: utf-8
import os
import platform
import shutil
import tarfile
import tempfile
import time
from beaker.middleware import CacheMiddleware
from beaker import util
from beaker.cache import Cache
from nose import SkipTest
from beaker.util import skip_if
import base64
import zlib
try:
    from webtest import TestApp
except ImportError:
    TestApp = None

# Tarballs of the output of:
# >>> from beaker.cache import Cache
# >>> c = Cache('test', data_dir='db', type='dbm')
# >>> c['foo'] = 'bar'
# in the old format, Beaker @ revision: 24f57102d310
dbm_cache_tar = """\
eJzt3EtOwkAAgOEBjTHEBDfu2ekKZ6bTTnsBL+ABzPRB4osSRBMXHsNruXDl3nMYLaEbpYRAaIn6
f8kwhFcn/APLSeNTUTdZsL4/m4Pg21wSqiCt9D1PC6mUZ7Xo+bWvrHB/N3HjXk+MrrLhQ/a48HXL
nv+l0vg0yYcTdznMxhdpfFvHbpj1lyv0N8oq+jdhrr/b/A5Yo79R9G9ERX8XbXgLrNHfav7/G1Hd
30XGhYPMT5JYRbELVGISGVov9SKVRaGNQj2I49TrF+8oxpJrTAMHxizob+b7ay+Y/v5lE1/AP+8v
9o5ccdsWYvdViMPpIwdCtMRsiP3yTrucd8r5pJxbz8On9/KT2uVo3H5rG1cFAAAAAOD3aIuP7lv3
pRjbXgkAAAAAAFjVyc1Idc6U1lYGgbSmL0Mjpe248+PYjY87I91x/UGeb3udAAAAAACgfh+fAAAA
AADgr/t5/sPFTZ5cb/38D19Lzn9pRHX/zR4CtEZ/o+nfiEX9N3kI0Gr9vWl/W0z0BwAAAAAAAAAA
AAAAAAAAqPAFyOvcKA==
"""
if util.py3k:
    dbm_cache_tar = dbm_cache_tar.encode('ascii')
dbm_cache_tar = zlib.decompress(base64.b64decode(dbm_cache_tar))

# dumbdbm format
dumbdbm_cache_tar = """\
eJzt191qgzAYBmCPvYqc2UGx+ZKY6A3scCe7gJKoha6binOD3f2yn5Ouf3TTlNH3AQlEJcE3nyGV
W0RT457Jsq9W6632W0Se0JI49/1E0vCIZZPPzHt5HmzPWNQ91M1r/XbwuVP3/6nKLcq2Gey6qftl
5Z6mWA3n56/IKOQfwk7+dvwV8Iv8FSH/IPbkb4uRl8BZ+fvg/WUE8g9if/62UDZf1VlZOiqc1VSq
kudGVrKgushNkYuVc5VM/Rups5vjY3wErJU6nD+Z7fyFNFpEjIf4AFeef7Jq22TOZnzOpLiJLz0d
CGyE+q/scHyMk/Wv+E79G0L9hzC7JSFMpv0PN0+J4rv7xNk+iTuKh07E6aXnB9Mao/7X/fExzt//
FecS9R8C9v/r9rP+l49tubnk+e/z/J8JjvMfAAAAAAAAAADAn70DFJAAwQ==
"""
if util.py3k:
    dumbdbm_cache_tar = dumbdbm_cache_tar.encode('ascii')
dumbdbm_cache_tar = zlib.decompress(base64.b64decode(dumbdbm_cache_tar))

def simple_app(environ, start_response):
    clear = False
    if environ.get('beaker.clear'):
        clear = True
    cache = environ['beaker.cache'].get_cache('testcache')
    if clear:
        cache.clear()
    try:
        value = cache.get_value('value')
    except:
        value = 0
    cache.set_value('value', value+1)
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %s' % cache.get_value('value')]

def cache_manager_app(environ, start_response):
    cm = environ['beaker.cache']
    cm.get_cache('test')['test_key'] = 'test value'

    start_response('200 OK', [('Content-type', 'text/plain')])
    yield "test_key is: %s\n" % cm.get_cache('test')['test_key']
    cm.get_cache('test').clear()

    try:
        test_value = cm.get_cache('test')['test_key']
    except KeyError:
        yield "test_key cleared"
    else:
        yield "test_key wasn't cleared, is: %s\n" % \
            cm.get_cache('test')['test_key']

def test_has_key():
    cache = Cache('test', data_dir='./cache', type='dbm')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    assert not cache.has_key("foo")
    assert "foo" not in cache
    cache.remove_value("test")
    assert not cache.has_key("test")

def test_expire_changes():
    cache = Cache('test_bar', data_dir='./cache', type='dbm')
    cache.set_value('test', 10)
    assert cache.has_key('test')
    assert cache['test'] == 10

    # ensure that we can change a never-expiring value
    cache.set_value('test', 20, expiretime=1)
    assert cache.has_key('test')
    assert cache['test'] == 20
    time.sleep(1)
    assert not cache.has_key('test')

    # test that we can change it before its expired
    cache.set_value('test', 30, expiretime=50)
    assert cache.has_key('test')
    assert cache['test'] == 30

    cache.set_value('test', 40, expiretime=3)
    assert cache.has_key('test')
    assert cache['test'] == 40
    time.sleep(3)
    assert not cache.has_key('test')

def test_fresh_createfunc():
    cache = Cache('test_foo', data_dir='./cache', type='dbm')
    x = cache.get_value('test', createfunc=lambda: 10, expiretime=2)
    assert x == 10
    x = cache.get_value('test', createfunc=lambda: 12, expiretime=2)
    assert x == 10
    x = cache.get_value('test', createfunc=lambda: 14, expiretime=2)
    assert x == 10
    time.sleep(2)
    x = cache.get_value('test', createfunc=lambda: 16, expiretime=2)
    assert x == 16
    x = cache.get_value('test', createfunc=lambda: 18, expiretime=2)
    assert x == 16

    cache.remove_value('test')
    assert not cache.has_key('test')
    x = cache.get_value('test', createfunc=lambda: 20, expiretime=2)
    assert x == 20

def test_has_key_multicache():
    cache = Cache('test', data_dir='./cache', type='dbm')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    cache = Cache('test', data_dir='./cache', type='dbm')
    assert cache.has_key("test")

def test_unicode_keys():
    cache = Cache('test', data_dir='./cache', type='dbm')
    o = object()
    cache.set_value(u'hiŏ', o)
    assert u'hiŏ' in cache
    assert u'hŏa' not in cache
    cache.remove_value(u'hiŏ')
    assert u'hiŏ' not in cache

def test_remove_stale():
    """test that remove_value() removes even if the value is expired."""

    cache = Cache('test', type='memory')
    o = object()
    cache.namespace[b'key'] = (time.time() - 60, 5, o)
    container = cache._get_value('key')
    assert not container.has_current_value()
    assert b'key' in container.namespace
    cache.remove_value('key')
    assert b'key' not in container.namespace

    # safe to call again
    cache.remove_value('key')

def test_multi_keys():
    cache = Cache('newtests', data_dir='./cache', type='dbm')
    cache.clear()
    called = {}
    def create_func():
        called['here'] = True
        return 'howdy'

    try:
        cache.get_value('key1')
    except KeyError:
        pass
    else:
        raise Exception("Failed to keyerror on nonexistent key")

    assert 'howdy' == cache.get_value('key2', createfunc=create_func)
    assert called['here'] == True
    del called['here']

    try:
        cache.get_value('key3')
    except KeyError:
        pass
    else:
        raise Exception("Failed to keyerror on nonexistent key")
    try:
        cache.get_value('key1')
    except KeyError:
        pass
    else:
        raise Exception("Failed to keyerror on nonexistent key")

    assert 'howdy' == cache.get_value('key2', createfunc=create_func)
    assert called == {}

@skip_if(lambda: TestApp is None, "webtest not installed")
def test_increment():
    app = TestApp(CacheMiddleware(simple_app))
    res = app.get('/', extra_environ={'beaker.type':type, 'beaker.clear':True})
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

@skip_if(lambda: TestApp is None, "webtest not installed")
def test_cache_manager():
    app = TestApp(CacheMiddleware(cache_manager_app))
    res = app.get('/')
    assert 'test_key is: test value' in res
    assert 'test_key cleared' in res

def test_clsmap_nonexistent():
    from beaker.cache import clsmap

    try:
        clsmap['fake']
        assert False
    except KeyError:
        pass

def test_clsmap_present():
    from beaker.cache import clsmap

    assert clsmap['memory']


def test_legacy_cache():
    cache = Cache('newtests', data_dir='./cache', type='dbm')

    cache.set_value('x', '1')
    assert cache.get_value('x') == '1'

    cache.set_value('x', '2', type='file', data_dir='./cache')
    assert cache.get_value('x') == '1'
    assert cache.get_value('x', type='file', data_dir='./cache') == '2'

    cache.remove_value('x')
    cache.remove_value('x', type='file', data_dir='./cache')

    assert cache.get_value('x', expiretime=1, createfunc=lambda: '5') == '5'
    assert cache.get_value('x', expiretime=1, createfunc=lambda: '6', type='file', data_dir='./cache') == '6'
    assert cache.get_value('x', expiretime=1, createfunc=lambda: '7') == '5'
    assert cache.get_value('x', expiretime=1, createfunc=lambda: '8', type='file', data_dir='./cache') == '6'
    time.sleep(1)
    assert cache.get_value('x', expiretime=1, createfunc=lambda: '9') == '9'
    assert cache.get_value('x', expiretime=1, createfunc=lambda: '10', type='file', data_dir='./cache') == '10'
    assert cache.get_value('x', expiretime=1, createfunc=lambda: '11') == '9'
    assert cache.get_value('x', expiretime=1, createfunc=lambda: '12', type='file', data_dir='./cache') == '10'


def test_upgrade():
    # If we're on OSX, lets run this since its OSX dump files, otherwise
    # we have to skip it
    if platform.system() != 'Darwin':
        return
    for test in _test_upgrade_has_key, _test_upgrade_in, _test_upgrade_setitem:
        for mod, tar in (('dbm', dbm_cache_tar),
                         ('dumbdbm', dumbdbm_cache_tar)):
            try:
                __import__(mod)
            except ImportError:
                continue
            dir = tempfile.mkdtemp()
            fd, name = tempfile.mkstemp(dir=dir)
            fp = os.fdopen(fd, 'wb')
            fp.write(tar)
            fp.close()
            tar = tarfile.open(name)
            for member in tar.getmembers():
                tar.extract(member, dir)
            tar.close()
            try:
                test(os.path.join(dir, 'db'))
            finally:
                shutil.rmtree(dir)

def _test_upgrade_has_key(dir):
    cache = Cache('test', data_dir=dir, type='dbm')
    assert cache.has_key('foo')
    assert cache.has_key('foo')

def _test_upgrade_in(dir):
    cache = Cache('test', data_dir=dir, type='dbm')
    assert 'foo' in cache
    assert 'foo' in cache

def _test_upgrade_setitem(dir):
    cache = Cache('test', data_dir=dir, type='dbm')
    assert cache['foo'] == 'bar'
    assert cache['foo'] == 'bar'


def teardown():
    import shutil
    shutil.rmtree('./cache', True)

########NEW FILE########
__FILENAME__ = test_cachemanager
import time
from datetime import datetime

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 2}

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def make_cache_obj(**kwargs):
    opts = defaults.copy()
    opts.update(kwargs)
    cache = CacheManager(**parse_cache_config_options(opts))
    return cache

def make_region_cached_func():
    global _cache_obj
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    @cache.region('short_term', 'region_loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    _cache_obj = cache
    return load

def make_cached_func():
    global _cache_obj
    cache = make_cache_obj()

    @cache.cache('loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    _cache_obj = cache
    return load

def test_parse_doesnt_allow_none():
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    for region, params in parse_cache_config_options(opts)['cache_regions'].items():
        for k, v in params.items():
            assert v != 'None', k

def test_parse_doesnt_allow_empty_region_name():
    opts = {}
    opts['cache.regions'] = ''
    regions = parse_cache_config_options(opts)['cache_regions']
    assert len(regions) == 0

def test_decorators():
    for func in (make_region_cached_func, make_cached_func):
        yield check_decorator, func()

def check_decorator(func):
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2

    result3 = func('George')
    assert 'George' in result3
    result4 = func('George')
    assert result3 == result4

    time.sleep(2)
    result2 = func('Fred')
    assert result != result2

def test_check_invalidate_region():
    func = make_region_cached_func()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2
    _cache_obj.region_invalidate(func, None, 'region_loader', 'Fred')

    result3 = func('Fred')
    assert result3 != result2

    result2 = func('Fred')
    assert result3 == result2

    # Invalidate a non-existent key
    _cache_obj.region_invalidate(func, None, 'region_loader', 'Fredd')
    assert result3 == result2

def test_check_invalidate():
    func = make_cached_func()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2
    _cache_obj.invalidate(func, 'loader', 'Fred')

    result3 = func('Fred')
    assert result3 != result2

    result2 = func('Fred')
    assert result3 == result2

    # Invalidate a non-existent key
    _cache_obj.invalidate(func, 'loader', 'Fredd')
    assert result3 == result2

def test_long_name():
    func = make_cached_func()
    name = 'Fred' * 250
    result = func(name)
    assert name in result
    
    result2 = func(name)
    assert result == result2
    # This won't actually invalidate it since the key won't be sha'd
    _cache_obj.invalidate(func, 'loader', name, key_length=8000)

    result3 = func(name)
    assert result3 == result2
    
    # And now this should invalidate it
    _cache_obj.invalidate(func, 'loader', name)
    result4 = func(name)
    assert result3 != result4

########NEW FILE########
__FILENAME__ = test_cache_decorator
import time
from datetime import datetime

import beaker.cache as cache
from beaker.cache import CacheManager, cache_region, region_invalidate
from beaker import util

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 2}

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

@cache_region('short_term')
def fred(x):
    return time.time()

@cache_region('short_term')
def george(x):
    return time.time()

def make_cache_obj(**kwargs):
    opts = defaults.copy()
    opts.update(kwargs)
    cache = CacheManager(**util.parse_cache_config_options(opts))
    return cache

def make_cached_func(**opts):
    cache = make_cache_obj(**opts)
    @cache.cache()
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return cache, load

def make_region_cached_func():
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    @cache_region('short_term', 'region_loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return load

def make_region_cached_func_2():
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    @cache_region('short_term')
    def load_person(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return load_person

def test_check_region_decorator():
    func = make_region_cached_func()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2

    result3 = func('George')
    assert 'George' in result3
    result4 = func('George')
    assert result3 == result4

    time.sleep(2)
    result2 = func('Fred')
    assert result != result2

def test_different_default_names():
    result = fred(1)
    time.sleep(1)
    result2 = george(1)
    assert result != result2

def test_check_invalidate_region():
    func = make_region_cached_func()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2
    region_invalidate(func, None, 'region_loader', 'Fred')

    result3 = func('Fred')
    assert result3 != result2

    result2 = func('Fred')
    assert result3 == result2

    # Invalidate a non-existent key
    region_invalidate(func, None, 'region_loader', 'Fredd')
    assert result3 == result2


def test_check_invalidate_region_2():
    func = make_region_cached_func_2()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2
    region_invalidate(func, None, 'Fred')

    result3 = func('Fred')
    assert result3 != result2

    result2 = func('Fred')
    assert result3 == result2

    # Invalidate a non-existent key
    region_invalidate(func, None, 'Fredd')
    assert result3 == result2

def test_invalidate_cache():
    cache, func = make_cached_func()
    val = func('foo')
    time.sleep(.1)
    val2 = func('foo')
    assert val == val2

    cache.invalidate(func, 'foo')
    val3 = func('foo')
    assert val3 != val

def test_class_key_cache():
    cache = make_cache_obj()

    class Foo(object):
        @cache.cache('method')
        def go(self, x, y):
            return "hi foo"

    @cache.cache('standalone')
    def go(x, y):
        return "hi standalone"

    x = Foo().go(1, 2)
    y = go(1, 2)

    ns = go._arg_namespace
    assert cache.get_cache(ns).get('method 1 2') == x
    assert cache.get_cache(ns).get('standalone 1 2') == y

def test_func_namespace():
    def go(x, y):
        return "hi standalone"

    assert 'test_cache_decorator' in util.func_namespace(go)
    assert util.func_namespace(go).endswith('go')

def test_class_key_region():
    opts = {}
    opts['cache.regions'] = 'short_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    class Foo(object):
        @cache_region('short_term', 'method')
        def go(self, x, y):
            return "hi foo"

    @cache_region('short_term', 'standalone')
    def go(x, y):
        return "hi standalone"

    x = Foo().go(1, 2)
    y = go(1, 2)
    ns = go._arg_namespace
    assert cache.get_cache_region(ns, 'short_term').get('method 1 2') == x
    assert cache.get_cache_region(ns, 'short_term').get('standalone 1 2') == y

def test_classmethod_key_region():
    opts = {}
    opts['cache.regions'] = 'short_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    class Foo(object):
        @classmethod
        @cache_region('short_term', 'method')
        def go(cls, x, y):
            return "hi"

    x = Foo.go(1, 2)
    ns = Foo.go._arg_namespace
    assert cache.get_cache_region(ns, 'short_term').get('method 1 2') == x

def test_class_key_region_invalidate():
    opts = {}
    opts['cache.regions'] = 'short_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    class Foo(object):
        @cache_region('short_term', 'method')
        def go(self, x, y):
            now = datetime.now()
            return "hi %s" % now

        def invalidate(self, x, y):
            region_invalidate(self.go, None, "method", x, y)

    x = Foo().go(1, 2)
    time.sleep(1)
    y = Foo().go(1, 2)
    Foo().invalidate(1, 2)
    z = Foo().go(1, 2)

    assert x == y
    assert x != z

########NEW FILE########
__FILENAME__ = test_container
import os
import random
import time
from beaker.container import *
from beaker.synchronization import _synchronizers
from beaker.cache import clsmap
from threading import Thread

class CachedWidget(object):
    totalcreates = 0
    delay = 0

    def __init__(self):
        CachedWidget.totalcreates += 1
        time.sleep(CachedWidget.delay)
        self.time = time.time()

def _run_container_test(cls, totaltime, expiretime, delay, threadlocal):
    print "\ntesting %s for %d secs with expiretime %s delay %d" % (
        cls, totaltime, expiretime, delay)

    CachedWidget.totalcreates = 0
    CachedWidget.delay = delay

    # allow for python overhead when checking current time against expire times
    fudge = 10

    starttime = time.time()

    running = [True]
    class RunThread(Thread):
        def run(self):
            print "%s starting" % self

            if threadlocal:
                localvalue = Value(
                                'test', 
                                cls('test', data_dir='./cache'), 
                                createfunc=CachedWidget, 
                                expiretime=expiretime, 
                                starttime=starttime)
                localvalue.clear_value()
            else:
                localvalue = value

            try:
                while running[0]:
                    item = localvalue.get_value()
                    if expiretime is not None:
                        currenttime = time.time()
                        itemtime = item.time
                        assert itemtime + expiretime + delay + fudge >= currenttime, \
                            "created: %f expire: %f delay: %f currenttime: %f" % \
                            (itemtime, expiretime, delay, currenttime)
                    time.sleep(random.random() * .00001)
            except:
                running[0] = False
                raise
            print "%s finishing" % self

    if not threadlocal:
        value = Value(
                    'test', 
                    cls('test', data_dir='./cache'), 
                    createfunc=CachedWidget, 
                    expiretime=expiretime, 
                    starttime=starttime)
        value.clear_value()
    else:
        value = None

    threads = [RunThread() for i in range(1, 8)]

    for t in threads:
        t.start()

    time.sleep(totaltime)

    failed = not running[0]
    running[0] = False

    for t in threads:
        t.join()

    assert not failed, "One or more threads failed"
    if expiretime is None:
        expected = 1
    else:
        expected = totaltime / expiretime + 1
    assert CachedWidget.totalcreates <= expected, \
            "Number of creates %d exceeds expected max %d" % (CachedWidget.totalcreates, expected)

def test_memory_container(totaltime=10, expiretime=None, delay=0, threadlocal=False):
    _run_container_test(clsmap['memory'],
                  totaltime, expiretime, delay, threadlocal)

def test_dbm_container(totaltime=10, expiretime=None, delay=0):
    _run_container_test(clsmap['dbm'], totaltime, expiretime, delay, False)

def test_file_container(totaltime=10, expiretime=None, delay=0, threadlocal=False):
    _run_container_test(clsmap['file'], totaltime, expiretime, delay, threadlocal)

def test_memory_container_tlocal():
    test_memory_container(expiretime=15, delay=2, threadlocal=True)

def test_memory_container_2():
    test_memory_container(expiretime=12)

def test_memory_container_3():
    test_memory_container(expiretime=15, delay=2)

def test_dbm_container_2():
    test_dbm_container(expiretime=12)

def test_dbm_container_3():
    test_dbm_container(expiretime=15, delay=2)

def test_file_container_2():
    test_file_container(expiretime=12)

def test_file_container_3():
    test_file_container(expiretime=15, delay=2)

def test_file_container_tlocal():
    test_file_container(expiretime=15, delay=2, threadlocal=True)

def test_file_open_bug():
    """ensure errors raised during reads or writes don't lock the namespace open."""

    value = Value('test', clsmap['file']('reentrant_test', data_dir='./cache'))
    if os.path.exists(value.namespace.file):
        os.remove(value.namespace.file)

    value.set_value("x")

    f = open(value.namespace.file, 'w')
    f.write("BLAH BLAH BLAH")
    f.close()

    # TODO: do we have an assertRaises() in nose to use here ?
    try:
        value.set_value("y")
        assert False
    except:
        pass

    _synchronizers.clear()

    value = Value('test', clsmap['file']('reentrant_test', data_dir='./cache'))

    # TODO: do we have an assertRaises() in nose to use here ?
    try:
        value.set_value("z")
        assert False
    except:
        pass


def test_removing_file_refreshes():
    """test that the cache doesn't ignore file removals"""

    x = [0]
    def create():
        x[0] += 1
        return x[0]

    value = Value('test', 
                    clsmap['file']('refresh_test', data_dir='./cache'), 
                    createfunc=create, starttime=time.time()
                    )
    if os.path.exists(value.namespace.file):
        os.remove(value.namespace.file)
    assert value.get_value() == 1
    assert value.get_value() == 1
    os.remove(value.namespace.file)
    assert value.get_value() == 2


def teardown():
    import shutil
    shutil.rmtree('./cache', True)

########NEW FILE########
__FILENAME__ = test_converters
import unittest

from beaker.converters import asbool, aslist


class AsBool(unittest.TestCase):
    def test_truth_str(self):
        for v in ('true', 'yes', 'on', 'y', 't', '1'):
            self.assertTrue(asbool(v), "%s should be considered True" % (v,))
            v = v.upper()
            self.assertTrue(asbool(v), "%s should be considered True" % (v,))

    def test_false_str(self):
        for v in ('false', 'no', 'off', 'n', 'f', '0'):
            self.assertFalse(asbool(v), v)
            v = v.upper()
            self.assertFalse(asbool(v), v)

    def test_coerce(self):
        """Things that can coerce right straight to booleans."""
        self.assertTrue(asbool(True))
        self.assertTrue(asbool(1))
        self.assertTrue(asbool(42))
        self.assertFalse(asbool(False))
        self.assertFalse(asbool(0))

    def test_bad_values(self):
        self.assertRaises(ValueError, asbool, ('mommy!'))
        self.assertRaises(ValueError, asbool, (u'Blargl?'))


class AsList(unittest.TestCase):
    def test_string(self):
        self.assertEqual(aslist('abc'), ['abc'])
        self.assertEqual(aslist('1a2a3', 'a'), ['1', '2', '3'])

    def test_None(self):
        self.assertEqual(aslist(None), [])

    def test_listy_noops(self):
        """Lists and tuples should come back unchanged."""
        x = [1, 2, 3]
        self.assertEqual(aslist(x), x)
        y = ('z', 'y', 'x')
        self.assertEqual(aslist(y), y)

    def test_listify(self):
        """Other objects should just result in a single item list."""
        self.assertEqual(aslist(dict()), [{}])


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_cookie_domain_only
import re
import os

import beaker.session
from beaker.middleware import SessionMiddleware
from nose import SkipTest

try:
    from webtest import TestApp
except ImportError:
    raise SkipTest("webtest not installed")

from beaker import crypto
if not crypto.has_aes:
    raise SkipTest("No AES library is installed, can't test cookie-only "
                   "Sessions")

def simple_app(environ, start_response):
    session = environ['beaker.session']
    if not session.has_key('value'):
        session['value'] = 0
    session['value'] += 1
    domain = environ.get('domain')
    if domain:
        session.domain = domain
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d and cookie is %s' % (session['value'], session)]

def test_increment():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/', extra_environ=dict(domain='.hoop.com'))
    assert 'current value is: 2' in res
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']
    res = app.get('/')
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']
    assert 'current value is: 3' in res


if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)

########NEW FILE########
__FILENAME__ = test_cookie_expires
from beaker.middleware import SessionMiddleware
from beaker.session import Session
from nose.tools import *
import datetime
import re

def test_cookie_expires():
    """Explore valid arguments for cookie_expires."""
    def app(*args, **kw):
        pass

    key = 'beaker.session.cookie_expires'
    now = datetime.datetime.now()

    values = ['300', 300,
        True,  'True',  'true',  't',
        False, 'False', 'false', 'f',
        datetime.timedelta(minutes=5), now]

    expected = [datetime.timedelta(seconds=300),
            datetime.timedelta(seconds=300), 
            True, True, True, True,
            False, False, False, False,
            datetime.timedelta(minutes=5), now]

    actual = []

    for pos, v in enumerate(values):
        try:
            s = SessionMiddleware(app, config={key:v})
            val = s.options['cookie_expires']
        except:
            val = None
        assert_equal(val, expected[pos])


def test_cookie_exprires_2():
    """Exhibit Set-Cookie: values."""
    expires = Session(
            {}, cookie_expires=True
            ).cookie.output()

    assert re.match('Set-Cookie: beaker.session.id=[0-9a-f]{32}; Path=/', expires), expires
    no_expires = Session(
            {}, cookie_expires=False
            ).cookie.output()

    assert re.match('Set-Cookie: beaker.session.id=[0-9a-f]{32}; expires=(Mon|Tue), 1[89]-Jan-2038 [0-9:]{8} GMT; Path=/', no_expires), no_expires


########NEW FILE########
__FILENAME__ = test_cookie_only
import datetime
import re
import os

import beaker.session
from beaker.middleware import SessionMiddleware
from nose import SkipTest
try:
    from webtest import TestApp
except ImportError:
    raise SkipTest("webtest not installed")

from beaker import crypto
if not crypto.has_aes:
    raise SkipTest("No AES library is installed, can't test cookie-only "
                   "Sessions")

def simple_app(environ, start_response):
    session = environ['beaker.session']
    if not session.has_key('value'):
        session['value'] = 0
    session['value'] += 1
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d and cookie is %s' % (session['value'], session)]

def test_increment():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

def test_expires():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie',
               'session.cookie_expires': datetime.timedelta(days=1)}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'expires=' in res.headers.getall('Set-Cookie')[0]
    assert 'current value is: 1' in res

def test_different_sessions():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    app2 = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    res = app2.get('/')
    res = app2.get('/')
    res2 = app.get('/')
    assert 'current value is: 2' in res2
    assert 'current value is: 4' in res

def test_nosave():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/nosave')
    assert 'current value is: 1' in res
    assert [] == res.headers.getall('Set-Cookie')
    res = app.get('/nosave')
    assert 'current value is: 1' in res

    res = app.get('/')
    assert 'current value is: 1' in res
    assert len(res.headers.getall('Set-Cookie')) > 0
    res = app.get('/')
    assert 'current value is: 2' in res

def test_increment_with_encryption():
    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

def test_different_sessions_with_encryption():
    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    app2 = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    res = app2.get('/')
    res = app2.get('/')
    res2 = app.get('/')
    assert 'current value is: 2' in res2
    assert 'current value is: 4' in res

def test_nosave_with_encryption():
    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/nosave')
    assert 'current value is: 1' in res
    assert [] == res.headers.getall('Set-Cookie')
    res = app.get('/nosave')
    assert 'current value is: 1' in res

    res = app.get('/')
    assert 'current value is: 1' in res
    assert len(res.headers.getall('Set-Cookie')) > 0
    res = app.get('/')
    assert 'current value is: 2' in res

def test_cookie_id():
    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert "_id':" in res
    sess_id = re.sub(r".*'_id': '(.*?)'.*", r'\1', res.body)
    res = app.get('/')
    new_id = re.sub(r".*'_id': '(.*?)'.*", r'\1', res.body)
    assert new_id == sess_id

def test_invalidate_with_save_does_not_delete_session():
    def invalidate_session_app(environ, start_response):
        session = environ['beaker.session']
        session.invalidate()
        session.save()
        start_response('200 OK', [('Content-type', 'text/plain')])
        return ['Cookie is %s' % session]

    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(invalidate_session_app, **options))
    res = app.get('/')
    assert 'expires=' not in res.headers.getall('Set-Cookie')[0]

if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)

########NEW FILE########
__FILENAME__ = test_database
# coding: utf-8
from beaker.cache import clsmap, Cache, util
from beaker.exceptions import InvalidCacheBackendError
from beaker.middleware import CacheMiddleware
from nose import SkipTest

try:
    from webtest import TestApp
except ImportError:
    TestApp = None


try:
    clsmap['ext:database']._init_dependencies()
except InvalidCacheBackendError:
    raise SkipTest("an appropriate SQLAlchemy backend is not installed")

db_url = 'sqlite:///test.db'

def simple_app(environ, start_response):
    extra_args = {}
    clear = False
    if environ.get('beaker.clear'):
        clear = True
    extra_args['type'] = 'ext:database'
    extra_args['url'] = db_url
    extra_args['data_dir'] = './cache'
    cache = environ['beaker.cache'].get_cache('testcache', **extra_args)
    if clear:
        cache.clear()
    try:
        value = cache.get_value('value')
    except:
        value = 0
    cache.set_value('value', value+1)
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %s' % cache.get_value('value')]

def cache_manager_app(environ, start_response):
    cm = environ['beaker.cache']
    cm.get_cache('test')['test_key'] = 'test value'

    start_response('200 OK', [('Content-type', 'text/plain')])
    yield "test_key is: %s\n" % cm.get_cache('test')['test_key']
    cm.get_cache('test').clear()

    try:
        test_value = cm.get_cache('test')['test_key']
    except KeyError:
        yield "test_key cleared"
    else:
        yield "test_key wasn't cleared, is: %s\n" % \
            cm.get_cache('test')['test_key']

def test_has_key():
    cache = Cache('test', data_dir='./cache', url=db_url, type='ext:database')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    assert not cache.has_key("foo")
    assert "foo" not in cache
    cache.remove_value("test")
    assert not cache.has_key("test")

def test_has_key_multicache():
    cache = Cache('test', data_dir='./cache', url=db_url, type='ext:database')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    cache = Cache('test', data_dir='./cache', url=db_url, type='ext:database')
    assert cache.has_key("test")
    cache.remove_value('test')

def test_clear():
    cache = Cache('test', data_dir='./cache', url=db_url, type='ext:database')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    cache.clear()
    assert not cache.has_key("test")

def test_unicode_keys():
    cache = Cache('test', data_dir='./cache', url=db_url, type='ext:database')
    o = object()
    cache.set_value(u'hiŏ', o)
    assert u'hiŏ' in cache
    assert u'hŏa' not in cache
    cache.remove_value(u'hiŏ')
    assert u'hiŏ' not in cache

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_increment():
    app = TestApp(CacheMiddleware(simple_app))
    res = app.get('/', extra_environ={'beaker.clear':True})
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_cache_manager():
    app = TestApp(CacheMiddleware(cache_manager_app))
    res = app.get('/')
    assert 'test_key is: test value' in res
    assert 'test_key cleared' in res

########NEW FILE########
__FILENAME__ = test_domain_setting
import re
import os

from beaker.middleware import SessionMiddleware
from nose import SkipTest
try:
    from webtest import TestApp
except ImportError:
    raise SkipTest("webtest not installed")

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def simple_app(environ, start_response):
    session = environ['beaker.session']
    domain = environ.get('domain')
    if domain:
        session.domain = domain
    if not session.has_key('value'):
        session['value'] = 0
    session['value'] += 1
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d, session id is %s' % (session['value'],
                                                            session.id)]


def test_domain():
    options = {'session.data_dir':'./cache', 'session.secret':'blah', 'session.cookie_domain': '.test.com'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/', extra_environ=dict(domain='.hoop.com'))
    assert 'current value is: 1' in res
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']
    res = app.get('/')
    assert 'current value is: 2' in res
    assert [] == res.headers.getall('Set-Cookie')
    res = app.get('/', extra_environ=dict(domain='.hoop.co.uk'))
    assert 'current value is: 3' in res
    assert 'Domain=.hoop.co.uk' in res.headers['Set-Cookie']



if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)

########NEW FILE########
__FILENAME__ = test_increment
import re
import os

from beaker.middleware import SessionMiddleware
from nose import SkipTest
try:
    from webtest import TestApp
except ImportError:
    raise SkipTest("webtest not installed")


def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def no_save_app(environ, start_response):
    session = environ['beaker.session']
    sess_id = environ.get('SESSION_ID')
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %s, session id is %s' % (session.get('value'),
                                                            session.id)]

def simple_app(environ, start_response):
    session = environ['beaker.session']
    sess_id = environ.get('SESSION_ID')
    if sess_id:
        session = session.get_by_id(sess_id)
    if not session:
        start_response('200 OK', [('Content-type', 'text/plain')])
        return ["No session id of %s found." % sess_id]
    if not 'value' in session:
        session['value'] = 0
    session['value'] += 1
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d, session id is %s' % (session['value'],
                                                            session.id)]

def simple_auto_app(environ, start_response):
    """Like the simple_app, but assume that sessions auto-save"""
    session = environ['beaker.session']
    sess_id = environ.get('SESSION_ID')
    if sess_id:
        session = session.get_by_id(sess_id)
    if not session:
        start_response('200 OK', [('Content-type', 'text/plain')])
        return ["No session id of %s found." % sess_id]
    if not 'value' in session:
        session['value'] = 0
    session['value'] += 1
    if environ['PATH_INFO'].startswith('/nosave'):
        session.revert()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d, session id is %s' % (session.get('value', 0),
                                                            session.id)]

def test_no_save():
    options = {'session.data_dir':'./cache', 'session.secret':'blah'}
    app = TestApp(SessionMiddleware(no_save_app, **options))
    res = app.get('/')
    assert 'current value is: None' in res
    assert [] == res.headers.getall('Set-Cookie')


def test_increment():
    options = {'session.data_dir':'./cache', 'session.secret':'blah'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

def test_increment_auto():
    options = {'session.data_dir':'./cache', 'session.secret':'blah'}
    app = TestApp(SessionMiddleware(simple_auto_app, auto=True, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res


def test_different_sessions():
    options = {'session.data_dir':'./cache', 'session.secret':'blah'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    app2 = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    res = app2.get('/')
    res = app2.get('/')
    res2 = app.get('/')
    assert 'current value is: 2' in res2
    assert 'current value is: 4' in res

def test_different_sessions_auto():
    options = {'session.data_dir':'./cache', 'session.secret':'blah'}
    app = TestApp(SessionMiddleware(simple_auto_app, auto=True, **options))
    app2 = TestApp(SessionMiddleware(simple_auto_app, auto=True, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    res = app2.get('/')
    res = app2.get('/')
    res2 = app.get('/')
    assert 'current value is: 2' in res2
    assert 'current value is: 4' in res

def test_nosave():
    options = {'session.data_dir':'./cache', 'session.secret':'blah'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/nosave')
    assert 'current value is: 1' in res
    res = app.get('/nosave')
    assert 'current value is: 1' in res

    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res

def test_revert():
    options = {'session.data_dir':'./cache', 'session.secret':'blah'}
    app = TestApp(SessionMiddleware(simple_auto_app, auto=True, **options))
    res = app.get('/nosave')
    assert 'current value is: 0' in res
    res = app.get('/nosave')
    assert 'current value is: 0' in res

    res = app.get('/')
    assert 'current value is: 1' in res
    assert [] == res.headers.getall('Set-Cookie')
    res = app.get('/')
    assert [] == res.headers.getall('Set-Cookie')
    assert 'current value is: 2' in res

    # Finally, ensure that reverting shows the proper one
    res = app.get('/nosave')
    assert [] == res.headers.getall('Set-Cookie')
    assert 'current value is: 2' in res

def test_load_session_by_id():
    options = {'session.data_dir':'./cache', 'session.secret':'blah'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    res = app.get('/')
    assert 'current value is: 3' in res
    old_id = re.sub(r'^.*?session id is (\S+)$', r'\1', res.body, re.M)

    # Clear the cookies and do a new request
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res

    # Load a bogus session to see that its not there
    res = app.get('/', extra_environ={'SESSION_ID':'jil2j34il2j34ilj23'})
    assert 'No session id of' in res

    # Saved session was at 3, now it'll be 4
    res = app.get('/', extra_environ={'SESSION_ID':old_id})
    assert 'current value is: 4' in res

    # Prior request is now up to 2
    res = app.get('/')
    assert 'current value is: 2' in res


if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)

########NEW FILE########
__FILENAME__ = test_memcached
# coding: utf-8
import mock
import os

from beaker.cache import clsmap, Cache, CacheManager, util
from beaker.middleware import CacheMiddleware, SessionMiddleware
from beaker.exceptions import InvalidCacheBackendError
from beaker.util import parse_cache_config_options
from nose import SkipTest
import unittest

try:
    from webtest import TestApp
except ImportError:
    TestApp = None

try:
    from beaker.ext import memcached
    client = memcached._load_client()
except InvalidCacheBackendError:
    raise SkipTest("an appropriate memcached backend is not installed")

mc_url = '127.0.0.1:11211'

c =client.Client([mc_url])
c.set('x', 'y')
if not c.get('x'):
    raise SkipTest("Memcached is not running at %s" % mc_url)

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def simple_session_app(environ, start_response):
    session = environ['beaker.session']
    sess_id = environ.get('SESSION_ID')
    if environ['PATH_INFO'].startswith('/invalid'):
        # Attempt to access the session
        id = session.id
        session['value'] = 2
    else:
        if sess_id:
            session = session.get_by_id(sess_id)
        if not session:
            start_response('200 OK', [('Content-type', 'text/plain')])
            return ["No session id of %s found." % sess_id]
        if not session.has_key('value'):
            session['value'] = 0
        session['value'] += 1
        if not environ['PATH_INFO'].startswith('/nosave'):
            session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d, session id is %s' % (session['value'],
                                                            session.id)]

def simple_app(environ, start_response):
    extra_args = {}
    clear = False
    if environ.get('beaker.clear'):
        clear = True
    extra_args['type'] = 'ext:memcached'
    extra_args['url'] = mc_url
    extra_args['data_dir'] = './cache'
    cache = environ['beaker.cache'].get_cache('testcache', **extra_args)
    if clear:
        cache.clear()
    try:
        value = cache.get_value('value')
    except:
        value = 0
    cache.set_value('value', value+1)
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %s' % cache.get_value('value')]


def using_none_app(environ, start_response):
    extra_args = {}
    clear = False
    if environ.get('beaker.clear'):
        clear = True
    extra_args['type'] = 'ext:memcached'
    extra_args['url'] = mc_url
    extra_args['data_dir'] = './cache'
    cache = environ['beaker.cache'].get_cache('testcache', **extra_args)
    if clear:
        cache.clear()
    try:
        value = cache.get_value('value')
    except:
        value = 10
    cache.set_value('value', None)
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %s' % value]


def cache_manager_app(environ, start_response):
    cm = environ['beaker.cache']
    cm.get_cache('test')['test_key'] = 'test value'

    start_response('200 OK', [('Content-type', 'text/plain')])
    yield "test_key is: %s\n" % cm.get_cache('test')['test_key']
    cm.get_cache('test').clear()

    try:
        test_value = cm.get_cache('test')['test_key']
    except KeyError:
        yield "test_key cleared"
    else:
        yield "test_key wasn't cleared, is: %s\n" % \
            cm.get_cache('test')['test_key']

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_session():
    app = TestApp(SessionMiddleware(simple_session_app, data_dir='./cache', type='ext:memcached', url=mc_url))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res


@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_session_invalid():
    app = TestApp(SessionMiddleware(simple_session_app, data_dir='./cache', type='ext:memcached', url=mc_url))
    res = app.get('/invalid', headers=dict(Cookie='beaker.session.id=df7324911e246b70b5781c3c58328442; Path=/'))
    assert 'current value is: 2' in res


def test_has_key():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    assert not cache.has_key("foo")
    assert "foo" not in cache
    cache.remove_value("test")
    assert not cache.has_key("test")

def test_dropping_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    cache.set_value('test', 20)
    cache.set_value('fred', 10)
    assert cache.has_key('test')
    assert 'test' in cache
    assert cache.has_key('fred')

    # Directly nuke the actual key, to simulate it being removed by memcached
    cache.namespace.mc.delete('test_test')
    assert not cache.has_key('test')
    assert cache.has_key('fred')

    # Nuke the keys dict, it might die, who knows
    cache.namespace.mc.delete('test:keys')
    assert cache.has_key('fred')

    # And we still need clear to work, even if it won't work well
    cache.clear()

def test_deleting_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    cache.set_value('test', 20)

    # Nuke the keys dict, it might die, who knows
    cache.namespace.mc.delete('test:keys')

    assert cache.has_key('test')

    # make sure we can still delete keys even though our keys dict got nuked
    del cache['test']

    assert not cache.has_key('test')

def test_has_key_multicache():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    assert cache.has_key("test")

def test_unicode_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    cache.set_value(u'hiŏ', o)
    assert u'hiŏ' in cache
    assert u'hŏa' not in cache
    cache.remove_value(u'hiŏ')
    assert u'hiŏ' not in cache

def test_long_unicode_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    long_str = u'Очень длинная строка, которая не влезает в сто двадцать восемь байт и поэтому не проходит ограничение в check_key, что очень прискорбно, не правда ли, друзья? Давайте же скорее исправим это досадное недоразумение!'
    cache.set_value(long_str, o)
    assert long_str in cache
    cache.remove_value(long_str)
    assert long_str not in cache

def test_spaces_in_unicode_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    cache.set_value(u'hi ŏ', o)
    assert u'hi ŏ' in cache
    assert u'hŏa' not in cache
    cache.remove_value(u'hi ŏ')
    assert u'hi ŏ' not in cache

def test_spaces_in_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    cache.set_value("has space", 24)
    assert cache.has_key("has space")
    assert 24 == cache.get_value("has space")
    cache.set_value("hasspace", 42)
    assert cache.has_key("hasspace")
    assert 42 == cache.get_value("hasspace")

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_increment():
    app = TestApp(CacheMiddleware(simple_app))
    res = app.get('/', extra_environ={'beaker.clear':True})
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

    app = TestApp(CacheMiddleware(simple_app))
    res = app.get('/', extra_environ={'beaker.clear':True})
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_cache_manager():
    app = TestApp(CacheMiddleware(cache_manager_app))
    res = app.get('/')
    assert 'test_key is: test value' in res
    assert 'test_key cleared' in res

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_store_none():
    app = TestApp(CacheMiddleware(using_none_app))
    res = app.get('/', extra_environ={'beaker.clear':True})
    assert 'current value is: 10' in res
    res = app.get('/')
    assert 'current value is: None' in res

class TestPylibmcInit(unittest.TestCase):
    def setUp(self):

        from beaker.ext import memcached
        try:
            import pylibmc as memcache
        except:
            import memcache
            memcached._client_libs['pylibmc'] = memcached.pylibmc = memcache
            from contextlib import contextmanager
            class ThreadMappedPool(dict):
                "a mock of pylibmc's ThreadMappedPool"

                def __init__(self, master):
                    self.master = master

                @contextmanager
                def reserve(self):
                    yield self.master
            memcache.ThreadMappedPool = ThreadMappedPool

    def test_uses_pylibmc_client(self):
        from beaker.ext import memcached
        cache = Cache('test', data_dir='./cache', 
                            memcache_module='pylibmc', 
                            url=mc_url, type="ext:memcached")
        assert isinstance(cache.namespace, memcached.PyLibMCNamespaceManager)

    def test_dont_use_pylibmc_client(self):
        from beaker.ext.memcached import _load_client
        load_mock = mock.Mock()
        load_mock.return_value = _load_client('memcache')
        with mock.patch('beaker.ext.memcached._load_client', load_mock):
            cache = Cache('test', data_dir='./cache', url=mc_url, type="ext:memcached")
            assert not isinstance(cache.namespace, memcached.PyLibMCNamespaceManager)
            assert isinstance(cache.namespace, memcached.MemcachedNamespaceManager)

    def test_client(self):
        cache = Cache('test', data_dir='./cache', url=mc_url, type="ext:memcached", 
                      protocol='binary')
        o = object()
        cache.set_value("test", o)
        assert cache.has_key("test")
        assert "test" in cache
        assert not cache.has_key("foo")
        assert "foo" not in cache
        cache.remove_value("test")
        assert not cache.has_key("test")

    def test_client_behaviors(self):
        config = {
            'cache.lock_dir':'./lock', 
            'cache.data_dir':'./cache',  
            'cache.type':'ext:memcached', 
            'cache.url':mc_url,
            'cache.memcache_module':'pylibmc', 
            'cache.protocol':'binary', 
            'cache.behavior.ketama': 'True', 
            'cache.behavior.cas':False, 
            'cache.behavior.receive_timeout':'3600',
            'cache.behavior.send_timeout':1800, 
            'cache.behavior.tcp_nodelay':1,
            'cache.behavior.auto_eject':"0"
        }
        cache_manager = CacheManager(**parse_cache_config_options(config))
        cache = cache_manager.get_cache('test_behavior', expire=6000)
        
        with cache.namespace.pool.reserve() as mc:
            assert "ketama" in mc.behaviors
            assert mc.behaviors["ketama"] == 1
            assert "cas" in mc.behaviors
            assert mc.behaviors["cas"] == 0
            assert "receive_timeout" in mc.behaviors
            assert mc.behaviors["receive_timeout"] == 3600
            assert "send_timeout" in mc.behaviors
            assert mc.behaviors["send_timeout"] == 1800
            assert "tcp_nodelay" in mc.behaviors
            assert mc.behaviors["tcp_nodelay"] == 1
            assert "auto_eject" in mc.behaviors
            assert mc.behaviors["auto_eject"] == 0
            
########NEW FILE########
__FILENAME__ = test_namespacing
import os
import sys


def teardown():
    import shutil
    shutil.rmtree('./cache', True)


def test_consistent_namespacing():
    sys.path.append(os.path.dirname(__file__))
    from tests.test_namespacing_files.namespace_go import go
    go()

########NEW FILE########
__FILENAME__ = namespace_get
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from datetime import datetime

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 60, 'cache.regions': 'short_term'}

cache = CacheManager(**parse_cache_config_options(defaults))

def get_cached_value():
    @cache.region('short_term', 'test_namespacing')
    def get_value():
        return datetime.now()

    return get_value()


########NEW FILE########
__FILENAME__ = namespace_go
from __future__ import print_function
import time


def go():
    import namespace_get
    a = namespace_get.get_cached_value()
    time.sleep(0.3)
    b = namespace_get.get_cached_value()

    time.sleep(0.3)

    import test_namespacing_files.namespace_get
    c = test_namespacing_files.namespace_get.get_cached_value()
    time.sleep(0.3)
    d = test_namespacing_files.namespace_get.get_cached_value()

    print(a)
    print(b)
    print(c)
    print(d)

    assert a == b, 'Basic caching problem - should never happen'
    assert c == d, 'Basic caching problem - should never happen'
    assert a == c, 'Namespaces not consistent when using different import paths'

########NEW FILE########
__FILENAME__ = test_session
# -*- coding: utf-8 -*-
import sys
import time
import warnings

from nose import SkipTest

from beaker.crypto import has_aes
from beaker.session import Session
from beaker import util


def get_session(**kwargs):
    """A shortcut for creating :class:`Session` instance"""
    options = {}
    options.update(**kwargs)
    return Session({}, **options)


def test_save_load():
    """Test if the data is actually persistent across requests"""
    session = get_session()
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id)
    assert u'Suomi' in session
    assert u'Great Britain' in session
    assert u'Deutchland' in session

    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'


def test_save_load_encryption():
    """Test if the data is actually persistent across requests"""
    if not has_aes:
        raise SkipTest()
    session = get_session(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id, encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    assert u'Suomi' in session
    assert u'Great Britain' in session
    assert u'Deutchland' in session

    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'


def test_decryption_failure():
    """Test if the data fails without the right keys"""
    if not has_aes:
        raise SkipTest()
    session = get_session(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id, encrypt_key='asfdasdfadsfsadf',
                          validate_key='hoobermas', invalidate_corrupt=True)
    assert u'Suomi' not in session
    assert u'Great Britain' not in session


def test_delete():
    """Test :meth:`Session.delete`"""
    session = get_session()
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.delete()

    assert u'Suomi' not in session
    assert u'Great Britain' not in session
    assert u'Deutchland' not in session


def test_revert():
    """Test :meth:`Session.revert`"""
    session = get_session()
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id)
    del session[u'Suomi']
    session[u'Great Britain'] = u'Lewis Hamilton'
    session[u'Deutchland'] = u'Michael Schumacher'
    session[u'España'] = u'Fernando Alonso'
    session.revert()

    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'
    assert u'España' not in session


def test_invalidate():
    """Test :meth:`Session.invalidate`"""
    session = get_session()
    id = session.id
    created = session.created
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.invalidate()

    assert session.id != id
    assert session.created != created
    assert u'Suomi' not in session
    assert u'Great Britain' not in session
    assert u'Deutchland' not in session


def test_regenerate_id():
    """Test :meth:`Session.regenerate_id`"""
    # new session & save
    session = get_session()
    orig_id = session.id
    session[u'foo'] = u'bar'
    session.save()

    # load session
    session = get_session(id=session.id)
    # data should still be there
    assert session[u'foo'] == u'bar'

    # regenerate the id
    session.regenerate_id()

    assert session.id != orig_id

    # data is still there
    assert session[u'foo'] == u'bar'

    # should be the new id
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']

    # get a new session before calling save
    bunk_sess = get_session(id=session.id)
    assert u'foo' not in bunk_sess

    # save it
    session.save()

    # make sure we get the data back
    session = get_session(id=session.id)
    assert session[u'foo'] == u'bar'


def test_timeout():
    """Test if the session times out properly"""
    session = get_session(timeout=2)
    id = session.id
    created = session.created
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id, timeout=2)
    assert session.id == id
    assert session.created == created
    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'

    time.sleep(2)
    session = get_session(id=session.id, timeout=2)
    assert session.id != id
    assert session.created != created
    assert u'Suomi' not in session
    assert u'Great Britain' not in session
    assert u'Deutchland' not in session


def test_cookies_enabled():
    """
    Test if cookies are sent out properly when ``use_cookies``
    is set to ``True``
    """
    session = get_session(use_cookies=True)
    assert 'cookie_out' in session.request
    assert session.request['set_cookie'] == False

    session.domain = 'example.com'
    session.path = '/example'
    assert session.request['set_cookie'] == True
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']
    assert 'Domain=example.com' in session.request['cookie_out']
    assert 'Path=/' in session.request['cookie_out']

    session = get_session(use_cookies=True)
    session.save()
    assert session.request['set_cookie'] == True
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']

    session = get_session(use_cookies=True, id=session.id)
    session.delete()
    assert session.request['set_cookie'] == True
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']
    assert 'expires=' in session.request['cookie_out']

    # test for secure
    session = get_session(use_cookies=True, secure=True)
    assert 'secure' in session.request['cookie_out']

    # test for httponly
    class ShowWarning(object):
        def __init__(self):
            self.msg = None
        def __call__(self, message, category, filename, lineno, file=None, line=None):
            self.msg = str(message)
    orig_sw = warnings.showwarning
    sw = ShowWarning()
    warnings.showwarning = sw
    session = get_session(use_cookies=True, httponly=True)
    if sys.version_info < (2, 6):
        assert sw.msg == 'Python 2.6+ is required to use httponly'
    else:
        assert 'httponly' in session.request['cookie_out']
    warnings.showwarning = orig_sw

def test_cookies_disabled():
    """
    Test that no cookies are sent when ``use_cookies`` is set to ``False``
    """
    session = get_session(use_cookies=False)
    assert 'set_cookie' not in session.request
    assert 'cookie_out' not in session.request

    session.save()
    assert 'set_cookie' not in session.request
    assert 'cookie_out' not in session.request

    session = get_session(use_cookies=False, id=session.id)
    assert 'set_cookie' not in session.request
    assert 'cookie_out' not in session.request

    session.delete()
    assert 'set_cookie' not in session.request
    assert 'cookie_out' not in session.request


def test_file_based_replace_optimization():
    """Test the file-based backend with session,
    which includes the 'replace' optimization.

    """

    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache')

    session['foo'] = 'foo'
    session['bar'] = 'bar'
    session.save()

    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache', id=session.id)
    assert session['foo'] == 'foo'
    assert session['bar'] == 'bar'

    session['bar'] = 'bat'
    session['bat'] = 'hoho'
    session.save()

    session.namespace.do_open('c', False)
    session.namespace['test'] = 'some test'
    session.namespace.do_close()

    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache', id=session.id)

    session.namespace.do_open('r', False)
    assert session.namespace['test'] == 'some test'
    session.namespace.do_close()

    assert session['foo'] == 'foo'
    assert session['bar'] == 'bat'
    assert session['bat'] == 'hoho'
    session.save()

    # the file has been replaced, so our out-of-session
    # key is gone
    session.namespace.do_open('r', False)
    assert 'test' not in session.namespace
    session.namespace.do_close()


def test_invalidate_corrupt():
    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache')
    session['foo'] = 'bar'
    session.save()

    f = open(session.namespace.file, 'w')
    f.write("crap")
    f.close()

    util.assert_raises(
        util.pickle.UnpicklingError,
        get_session,
        use_cookies=False, type='file',
                data_dir='./cache', id=session.id
    )

    session = get_session(use_cookies=False, type='file',
                            invalidate_corrupt=True,
                            data_dir='./cache', id=session.id)
    assert "foo" not in dict(session)

########NEW FILE########
__FILENAME__ = test_sqla
# coding: utf-8
from beaker.cache import clsmap, Cache, util
from beaker.exceptions import InvalidCacheBackendError
from beaker.middleware import CacheMiddleware
from nose import SkipTest

try:
    from webtest import TestApp
except ImportError:
    TestApp = None

try:
    clsmap['ext:sqla']._init_dependencies()
except InvalidCacheBackendError:
    raise SkipTest("an appropriate SQLAlchemy backend is not installed")

import sqlalchemy as sa
from beaker.ext.sqla import make_cache_table

engine = sa.create_engine('sqlite://')
metadata = sa.MetaData()
cache_table = make_cache_table(metadata)
metadata.create_all(engine)

def simple_app(environ, start_response):
    extra_args = {}
    clear = False
    if environ.get('beaker.clear'):
        clear = True
    extra_args['type'] = 'ext:sqla'
    extra_args['bind'] = engine
    extra_args['table'] = cache_table
    extra_args['data_dir'] = './cache'
    cache = environ['beaker.cache'].get_cache('testcache', **extra_args)
    if clear:
        cache.clear()
    try:
        value = cache.get_value('value')
    except:
        value = 0
    cache.set_value('value', value+1)
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %s' % cache.get_value('value')]

def cache_manager_app(environ, start_response):
    cm = environ['beaker.cache']
    cm.get_cache('test')['test_key'] = 'test value'

    start_response('200 OK', [('Content-type', 'text/plain')])
    yield "test_key is: %s\n" % cm.get_cache('test')['test_key']
    cm.get_cache('test').clear()

    try:
        test_value = cm.get_cache('test')['test_key']
    except KeyError:
        yield "test_key cleared"
    else:
        yield "test_key wasn't cleared, is: %s\n" % \
            cm.get_cache('test')['test_key']

def make_cache():
    """Return a ``Cache`` for use by the unit tests."""
    return Cache('test', data_dir='./cache', bind=engine, table=cache_table,
                 type='ext:sqla')

def test_has_key():
    cache = make_cache()
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    assert not cache.has_key("foo")
    assert "foo" not in cache
    cache.remove_value("test")
    assert not cache.has_key("test")

def test_has_key_multicache():
    cache = make_cache()
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    cache = make_cache()
    assert cache.has_key("test")
    cache.remove_value('test')

def test_clear():
    cache = make_cache()
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    cache.clear()
    assert not cache.has_key("test")

def test_unicode_keys():
    cache = make_cache()
    o = object()
    cache.set_value(u'hiŏ', o)
    assert u'hiŏ' in cache
    assert u'hŏa' not in cache
    cache.remove_value(u'hiŏ')
    assert u'hiŏ' not in cache

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_increment():
    app = TestApp(CacheMiddleware(simple_app))
    res = app.get('/', extra_environ={'beaker.clear': True})
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_cache_manager():
    app = TestApp(CacheMiddleware(cache_manager_app))
    res = app.get('/')
    assert 'test_key is: test value' in res
    assert 'test_key cleared' in res

########NEW FILE########
__FILENAME__ = test_syncdict
from beaker.util import SyncDict, WeakValuedRegistry
import random, time, weakref
import threading

class Value(object):
    values = {}

    def do_something(self, id):
        Value.values[id] = self

    def stop_doing_something(self, id):
        del Value.values[id]

mutex = threading.Lock()

def create(id):
    assert not Value.values, "values still remain"
    global totalcreates
    totalcreates += 1
    return Value()

def threadtest(s, id):
    print "create thread %d starting" % id

    global running
    global totalgets
    while running:
        try:
            value = s.get('test', lambda: create(id))
            value.do_something(id)
        except Exception, e:
            print "Error", e
            running = False
            break
        else:
            totalgets += 1
            time.sleep(random.random() * .01)
            value.stop_doing_something(id)
            del value
            time.sleep(random.random() * .01)

def runtest(s):

    global values
    values = {}

    global totalcreates
    totalcreates = 0

    global totalgets
    totalgets = 0

    global running
    running = True

    threads = []
    for id_ in range(1, 20):
        t = threading.Thread(target=threadtest, args=(s, id_))
        t.start()
        threads.append(t)

    for i in range(0, 10):
        if not running:
            break
        time.sleep(1)

    failed = not running

    running = False

    for t in threads:
        t.join()

    assert not failed, "test failed"

    print "total object creates %d" % totalcreates
    print "total object gets %d" % totalgets


def test_dict():
    # normal dictionary test, where we will remove the value
    # periodically. the number of creates should be equal to
    # the number of removes plus one.
    print "\ntesting with normal dict"
    runtest(SyncDict())


def test_weakdict():
    print "\ntesting with weak dict"
    runtest(WeakValuedRegistry())

########NEW FILE########
__FILENAME__ = test_synchronizer
from beaker.synchronization import *

# TODO: spawn threads, test locking.


def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def test_reentrant_file():
    sync1 = file_synchronizer('test', lock_dir='./cache')
    sync2 = file_synchronizer('test', lock_dir='./cache')
    sync1.acquire_write_lock()
    sync2.acquire_write_lock()
    sync2.release_write_lock()
    sync1.release_write_lock()

def test_null():
    sync = null_synchronizer()
    assert sync.acquire_write_lock()
    sync.release_write_lock()

def test_mutex():
    sync = mutex_synchronizer('someident')
    sync.acquire_write_lock()
    sync.release_write_lock()


########NEW FILE########
__FILENAME__ = test_unicode_cache_keys
# coding: utf-8
"""If we try to use a character not in ascii range as a cache key, we get an 
unicodeencode error. See 
https://bitbucket.org/bbangert/beaker/issue/31/cached-function-decorators-break-when-some
for more on this
"""

from nose.tools import *
from beaker.cache import CacheManager

memory_cache = CacheManager(type='memory')

@memory_cache.cache('foo')
def foo(whatever):
    return whatever

class bar(object):

    @memory_cache.cache('baz')
    def baz(self, qux):
        return qux

    @classmethod
    @memory_cache.cache('bar')
    def quux(cls, garply):
        return garply

def test_A_unicode_encode_key_str():
    eq_(foo('Espanol'), 'Espanol')
    eq_(foo(12334), 12334)
    eq_(foo(u'Espanol'), u'Espanol')
    eq_(foo(u'Español'), u'Español')
    b = bar()
    eq_(b.baz('Espanol'), 'Espanol')
    eq_(b.baz(12334), 12334)
    eq_(b.baz(u'Espanol'), u'Espanol')
    eq_(b.baz(u'Español'), u'Español')
    eq_(b.quux('Espanol'), 'Espanol')
    eq_(b.quux(12334), 12334)
    eq_(b.quux(u'Espanol'), u'Espanol')
    eq_(b.quux(u'Español'), u'Español')


def test_B_replacing_non_ascii():
    """we replace the offending character with other non ascii one. Since
    the function distinguishes between the two it should not return the
    past value
    """
    assert_false(foo(u'Espaáol')==u'Español') 
    eq_(foo(u'Espaáol'), u'Espaáol')

def test_C_more_unicode():
    """We again test the same stuff but this time we use 
    http://tools.ietf.org/html/draft-josefsson-idn-test-vectors-00#section-5
    as keys"""
    keys = [
        # arabic (egyptian)
        u"\u0644\u064a\u0647\u0645\u0627\u0628\u062a\u0643\u0644\u0645\u0648\u0634\u0639\u0631\u0628\u064a\u061f",
        # Chinese (simplified)
        u"\u4ed6\u4eec\u4e3a\u4ec0\u4e48\u4e0d\u8bf4\u4e2d\u6587",
        # Chinese (traditional)
        u"\u4ed6\u5011\u7232\u4ec0\u9ebd\u4e0d\u8aaa\u4e2d\u6587",
        # czech
        u"\u0050\u0072\u006f\u010d\u0070\u0072\u006f\u0073\u0074\u011b\u006e\u0065\u006d\u006c\u0075\u0076\u00ed\u010d\u0065\u0073\u006b\u0079",
        # hebrew
        u"\u05dc\u05de\u05d4\u05d4\u05dd\u05e4\u05e9\u05d5\u05d8\u05dc\u05d0\u05de\u05d3\u05d1\u05e8\u05d9\u05dd\u05e2\u05d1\u05e8\u05d9\u05ea",
        # Hindi (Devanagari)
        u"\u092f\u0939\u0932\u094b\u0917\u0939\u093f\u0928\u094d\u0926\u0940\u0915\u094d\u092f\u094b\u0902\u0928\u0939\u0940\u0902\u092c\u094b\u0932\u0938\u0915\u0924\u0947\u0939\u0948\u0902",
        # Japanese (kanji and hiragana)
        u"\u306a\u305c\u307f\u3093\u306a\u65e5\u672c\u8a9e\u3092\u8a71\u3057\u3066\u304f\u308c\u306a\u3044\u306e\u304b",
        # Russian (Cyrillic)
        u"\u043f\u043e\u0447\u0435\u043c\u0443\u0436\u0435\u043e\u043d\u0438\u043d\u0435\u0433\u043e\u0432\u043e\u0440\u044f\u0442\u043f\u043e\u0440\u0443\u0441\u0441\u043a\u0438",
        # Spanish
        u"\u0050\u006f\u0072\u0071\u0075\u00e9\u006e\u006f\u0070\u0075\u0065\u0064\u0065\u006e\u0073\u0069\u006d\u0070\u006c\u0065\u006d\u0065\u006e\u0074\u0065\u0068\u0061\u0062\u006c\u0061\u0072\u0065\u006e\u0045\u0073\u0070\u0061\u00f1\u006f\u006c",
        # Vietnamese
        u"\u0054\u1ea1\u0069\u0073\u0061\u006f\u0068\u1ecd\u006b\u0068\u00f4\u006e\u0067\u0074\u0068\u1ec3\u0063\u0068\u1ec9\u006e\u00f3\u0069\u0074\u0069\u1ebf\u006e\u0067\u0056\u0069\u1ec7\u0074",
        # Japanese
        u"\u0033\u5e74\u0042\u7d44\u91d1\u516b\u5148\u751f",
        # Japanese
        u"\u5b89\u5ba4\u5948\u7f8e\u6075\u002d\u0077\u0069\u0074\u0068\u002d\u0053\u0055\u0050\u0045\u0052\u002d\u004d\u004f\u004e\u004b\u0045\u0059\u0053",
        # Japanese
        u"\u0048\u0065\u006c\u006c\u006f\u002d\u0041\u006e\u006f\u0074\u0068\u0065\u0072\u002d\u0057\u0061\u0079\u002d\u305d\u308c\u305e\u308c\u306e\u5834\u6240",
        # Japanese
        u"\u3072\u3068\u3064\u5c4b\u6839\u306e\u4e0b\u0032",
        # Japanese
        u"\u004d\u0061\u006a\u0069\u3067\u004b\u006f\u0069\u3059\u308b\u0035\u79d2\u524d",
        # Japanese
        u"\u30d1\u30d5\u30a3\u30fc\u0064\u0065\u30eb\u30f3\u30d0",
        # Japanese
        u"\u305d\u306e\u30b9\u30d4\u30fc\u30c9\u3067",
        # greek
        u"\u03b5\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac",
        # Maltese (Malti)
        u"\u0062\u006f\u006e\u0121\u0075\u0073\u0061\u0127\u0127\u0061",
        # Russian (Cyrillic)
        u"\u043f\u043e\u0447\u0435\u043c\u0443\u0436\u0435\u043e\u043d\u0438\u043d\u0435\u0433\u043e\u0432\u043e\u0440\u044f\u0442\u043f\u043e\u0440\u0443\u0441\u0441\u043a\u0438"
    ]
    for i in keys:
        eq_(foo(i),i)

def test_D_invalidate():
    """Invalidate cache"""
    memory_cache.invalidate(foo)
    eq_(foo('Espanol'), 'Espanol')

########NEW FILE########
