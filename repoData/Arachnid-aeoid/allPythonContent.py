__FILENAME__ = cache
"""Cache object

The Cache object is used to manage a set of cache files and their
associated backend. The backends can be rotated on the fly by
specifying an alternate type when used.

Advanced users can add new backends in beaker.backends

"""
import warnings

import beaker.container as container
import beaker.util as util
from beaker.exceptions import BeakerException, InvalidCacheBackendError

# Initialize the basic available backends
clsmap = {
          'memory':container.MemoryNamespaceManager,
          'dbm':container.DBMNamespaceManager,
          'file':container.FileNamespaceManager,
          }

# Initialize the cache region dict
cache_regions = {}
cache_managers = {}

# Load legacy-style backends
try:
    import beaker.ext.memcached as memcached
    clsmap['ext:memcached'] = memcached.MemcachedNamespaceManager
except InvalidCacheBackendError, e:
    clsmap['ext:memcached'] = e

try:
    import beaker.ext.database as database
    clsmap['ext:database'] = database.DatabaseNamespaceManager
except InvalidCacheBackendError, e:
    clsmap['ext:database'] = e

try:
    import beaker.ext.sqla as sqla
    clsmap['ext:sqla'] = sqla.SqlaNamespaceManager
except InvalidCacheBackendError, e:
    clsmap['ext:sqla'] = e

try:
    import beaker.ext.google as google
    clsmap['ext:google'] = google.GoogleNamespaceManager
except (InvalidCacheBackendError, SyntaxError), e:
    clsmap['ext:google'] = e


def cache_region(region, *args):
    """Decorate a function to cache itself using a cache region
    
    The region decorator requires arguments if there are more than
    2 of the same named function, in the same module. This is
    because the namespace used for the functions cache is based on
    the functions name and the module.
    
    
    Example::
        
        # Add cache region settings to beaker:
        beaker.cache.cache_regions.update(dict_of_config_region_options))
        
        @cache_region('short_term', 'some_data')
        def populate_things(search_term, limit, offset):
            return load_the_data(search_term, limit, offset)
        
        return load('rabbits', 20, 0)
    
    .. note::
        
        The function being decorated must only be called with
        positional arguments.
    
    """
    cache = [None]
    key = " ".join(str(x) for x in args)
    
    def decorate(func):
        namespace = util.func_namespace(func)
        def cached(*args):
            reg = cache_regions[region]
            if not reg.get('enabled', True):
                return func(*args)
            
            if not cache[0]:
                if region not in cache_regions:
                    raise BeakerException('Cache region not configured: %s' % region)
                cache[0] = cache_managers.setdefault(namespace + str(reg), Cache(namespace, **reg))
            
            cache_key = key + " " + " ".join(str(x) for x in args)
            def go():
                return func(*args)
            
            return cache[0].get_value(cache_key, createfunc=go)
        cached._arg_namespace = namespace
        cached._arg_region = region
        return cached
    return decorate


def region_invalidate(namespace, region, *args):
    """Invalidate a cache region namespace or decorated function
    
    This function only invalidates cache spaces created with the
    cache_region decorator.
    
    namespace
        Either the namespace of the result to invalidate, or the
        cached function reference
    
    region
        The region the function was cached to. If the function was
        cached to a single region then this argument can be None
    
    args
        Arguments that were used to differentiate the cached
        function as well as the arguments passed to the decorated
        function

    Example::
        
        # Add cache region settings to beaker:
        beaker.cache.cache_regions.update(dict_of_config_region_options))
        
        def populate_things(invalidate=False):
            
            @cache_region('short_term', 'some_data')
            def load(search_term, limit, offset):
                return load_the_data(search_term, limit, offset)
            
            # If the results should be invalidated first
            if invalidate:
                region_invalidate(load, None, 'some_data',
                                        'rabbits', 20, 0)
            return load('rabbits', 20, 0)
    
    """
    if callable(namespace):
        if not region:
            region = namespace._arg_region
        namespace = namespace._arg_namespace

    if not region:
        raise BeakerException("Region or callable function namespace is required")
    else:
        region = cache_regions[region]
    
    cache = cache_managers.setdefault(namespace + str(region), Cache(namespace, **region))
    cache_key = " ".join(str(x) for x in args)
    cache.remove_value(cache_key)


class Cache(object):
    """Front-end to the containment API implementing a data cache.

    ``namespace``
        the namespace of this Cache

    ``type``
        type of cache to use

    ``expire``
        seconds to keep cached data

    ``expiretime``
        seconds to keep cached data (legacy support)

    ``starttime``
        time when cache was cache was
    """
    def __init__(self, namespace, type='memory', expiretime=None,
                 starttime=None, expire=None, **nsargs):
        try:
            cls = clsmap[type]
            if isinstance(cls, InvalidCacheBackendError):
                raise cls
        except KeyError:
            raise TypeError("Unknown cache implementation %r" % type)
            
        self.namespace = cls(namespace, **nsargs)
        self.expiretime = expiretime or expire
        self.starttime = starttime
        self.nsargs = nsargs
        
    def put(self, key, value, **kw):
        self._get_value(key, **kw).set_value(value)
    set_value = put
    
    def get(self, key, **kw):
        """Retrieve a cached value from the container"""
        return self._get_value(key, **kw).get_value()
    get_value = get
    
    def remove_value(self, key, **kw):
        mycontainer = self._get_value(key, **kw)
        if mycontainer.has_current_value():
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
    
    def _legacy_get_value(self, key, type, **kw):
        expiretime = kw.pop('expiretime', self.expiretime)
        starttime = kw.pop('starttime', None)
        createfunc = kw.pop('createfunc', None)
        kwargs = self.nsargs.copy()
        kwargs.update(kw)
        c = Cache(self.namespace.namespace, type=type, **kwargs)
        return c._get_value(key, expiretime=expiretime, createfunc=createfunc, 
                            starttime=starttime)
    _legacy_get_value = util.deprecated(_legacy_get_value, "Specifying a "
        "'type' and other namespace configuration with cache.get()/put()/etc. "
        "is deprecated. Specify 'type' and other namespace configuration to "
        "cache_manager.get_cache() and/or the Cache constructor instead.")
    
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
        return cache_managers.setdefault(name + str(kw), Cache(name, **kw))
    
    def get_cache_region(self, name, region):
        if region not in self.regions:
            raise BeakerException('Cache region not configured: %s' % region)
        kw = self.regions[region]
        return cache_managers.setdefault(name + str(kw), Cache(name, **kw))
    
    def region(self, region, *args):
        """Decorate a function to cache itself using a cache region
        
        The region decorator requires arguments if there are more than
        2 of the same named function, in the same module. This is
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
        cache = [None]
        key = " ".join(str(x) for x in args)
        
        def decorate(func):
            namespace = util.func_namespace(func)
            def cached(*args):
                reg = self.regions[region]
                if not reg.get('enabled', True):
                    return func(*args)
                
                if not cache[0]:
                    cache[0] = self.get_cache_region(namespace, region)
                
                cache_key = key + " " + " ".join(str(x) for x in args)
                def go():
                    return func(*args)
                
                return cache[0].get_value(cache_key, createfunc=go)
            cached._arg_namespace = namespace
            cached._arg_region = region
            return cached
        return decorate

    def region_invalidate(self, namespace, region, *args):
        """Invalidate a cache region namespace or decorated function
        
        This function only invalidates cache spaces created with the
        cache_region decorator.
        
        namespace
            Either the namespace of the result to invalidate, or the
            name of the cached function
        
        region
            The region the function was cached to. If the function was
            cached to a single region then this argument can be None
        
        args
            Arguments that were used to differentiate the cached
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
        if callable(namespace):
            if not region:
                region = namespace._arg_region
            namespace = namespace._arg_namespace

        if not region:
            raise BeakerException("Region or callable function namespace is required")
        else:
            region = self.regions[region]
        
        cache = self.get_cache(namespace, **region)
        cache_key = " ".join(str(x) for x in args)
        cache.remove_value(cache_key)

    def cache(self, *args, **kwargs):
        """Decorate a function to cache itself with supplied parameters

        args
            Used to make the key unique for this function, as in region()
            above.

        kwargs
            Parameters to be passed to get_cache(), will override defaults

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
        cache = [None]
        key = " ".join(str(x) for x in args)
        
        def decorate(func):
            namespace = util.func_namespace(func)
            def cached(*args):
                if not cache[0]:
                    cache[0] = self.get_cache(namespace, **kwargs)
                cache_key = key + " " + " ".join(str(x) for x in args)
                def go():
                    return func(*args)
                return cache[0].get_value(cache_key, createfunc=go)
            cached._arg_namespace = namespace
            return cached
        return decorate

    def invalidate(self, func, *args, **kwargs):
        """Invalidate a cache decorated function
        
        This function only invalidates cache spaces created with the
        cache decorator.
        
        func
            Decorated function to invalidate
        
        args
            Used to make the key unique for this function, as in region()
            above.

        kwargs
            Parameters that were passed for use by get_cache(), note that
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
        cache_key = " ".join(str(x) for x in args)
        cache.remove_value(cache_key)

########NEW FILE########
__FILENAME__ = container
"""Container and Namespace classes"""
import anydbm
import cPickle
import logging
import os.path
import time

import beaker.util as util
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
    
    The implementation for setting and retrieving the namespace data is
    handled by subclasses.
    
    NamespaceManager may be used alone, or may be privately accessed by
    one or more Container objects.  Container objects provide per-key
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
    def __init__(self, namespace):
        self.namespace = namespace
        
    def get_creation_lock(self, key):
        raise NotImplementedError()

    def do_remove(self):
        raise NotImplementedError()

    def acquire_read_lock(self):
        pass

    def release_read_lock(self):
        pass

    def acquire_write_lock(self, wait=True):
        return True

    def release_write_lock(self):
        pass

    def has_key(self, key):
        return self.__contains__(key)

    def __getitem__(self, key):
        raise NotImplementedError()
        
    def __setitem__(self, key, value):
        raise NotImplementedError()
    
    def set_value(self, key, value, expiretime=None):
        """Optional set_value() method called by Value.
        
        Allows an expiretime to be passed, for namespace
        implementations which can prune their collections
        using expiretime.
        
        """
        self[key] = value
        
    def __contains__(self, key):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()
    
    def keys(self):
        raise NotImplementedError()
    
    def remove(self):
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

    def do_open(self, flags): 
        raise NotImplementedError()

    def do_close(self): 
        raise NotImplementedError()

    def acquire_read_lock(self): 
        self.access_lock.acquire_read_lock()
        try:
            self.open('r', checkcount = True)
        except:
            self.access_lock.release_read_lock()
            raise
            
    def release_read_lock(self):
        try:
            self.close(checkcount = True)
        finally:
            self.access_lock.release_read_lock()
        
    def acquire_write_lock(self, wait=True): 
        r = self.access_lock.acquire_write_lock(wait)
        try:
            if (wait or r): 
                self.open('c', checkcount = True)
            return r
        except:
            self.access_lock.release_write_lock()
            raise
            
    def release_write_lock(self): 
        try:
            self.close(checkcount=True)
        finally:
            self.access_lock.release_write_lock()

    def open(self, flags, checkcount=False):
        self.mutex.acquire()
        try:
            if checkcount:
                if self.openers == 0: 
                    self.do_open(flags)
                self.openers += 1
            else:
                self.do_open(flags)
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
            return self.namespace.has_key(self.key)
        finally:
            self.namespace.release_read_lock()

    def can_have_value(self):
        return self.has_current_value() or self.createfunc is not None  

    def has_current_value(self):
        self.namespace.acquire_read_lock()
        try:    
            has_value = self.namespace.has_key(self.key)
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
            if self.namespace.has_key(self.key):
                try:
                    del self.namespace[self.key]
                except KeyError:
                    # guard against un-mutexed backends raising KeyError
                    pass
            self.storedtime = -1
        finally:
            self.namespace.release_write_lock()


class MemoryNamespaceManager(NamespaceManager):
    namespaces = util.SyncDict()

    def __init__(self, namespace, **kwargs):
        NamespaceManager.__init__(self, namespace)
        self.dictionary = MemoryNamespaceManager.namespaces.get(self.namespace,
                                                                dict)
    def get_creation_lock(self, key):
        return NameLock(
            identifier="memorycontainer/funclock/%s/%s" % (self.namespace, key),
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


class DBMNamespaceManager(OpenResourceNamespaceManager):
    def __init__(self, namespace, dbmmodule=None, data_dir=None, 
            dbm_dir=None, lock_dir=None, digest_filenames=True, **kwargs):
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

        self.file = util.encoded_path(root= self.dbm_dir,
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
                    identifier = "dbmcontainer/funclock/%s" % self.namespace, 
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

    def do_open(self, flags):
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
        return self.dbm.has_key(key)
        
    def __setitem__(self, key, value):
        self.dbm[key] = cPickle.dumps(value)

    def __delitem__(self, key):
        del self.dbm[key]

    def keys(self):
        return self.dbm.keys()


class FileNamespaceManager(OpenResourceNamespaceManager):
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
                identifier = "filecontainer/funclock/%s" % self.namespace, 
                lock_dir = self.lock_dir
                )
        
    def file_exists(self, file):
        return os.access(file, os.F_OK)

    def do_open(self, flags):
        if self.file_exists(self.file):
            fh = open(self.file, 'rb')
            try:
                self.hash = cPickle.load(fh)
            except (IOError, OSError, EOFError, cPickle.PickleError, ValueError):
                pass
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
        except OSError, err:
            # for instance, because we haven't yet used this cache,
            # but client code has asked for a clear() operation...
            pass
        self.hash = {}
        
    def __getitem__(self, key): 
        return self.hash[key]

    def __contains__(self, key): 
        return self.hash.has_key(key)
        
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


def getKeyLength():
    maxlen = Cipher.getMaxAllowedKeyLength('AES/CTR/NoPadding')
    return min(maxlen, 256) / 8

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

from beaker.util import b64encode

try:
    # Use PyCrypto (if available)
    from Crypto.Hash import HMAC, SHA as SHA1

except ImportError:
    # PyCrypto not available.  Use the Python standard library.
    import hmac as HMAC
    import sys
    # When using the stdlib, we have to make sure the hmac version and sha
    # version are compatible
    if sys.version_info[0:2] <= (2,4):
        # hmac in python2.4 or less require the sha module
        import sha as SHA1
    else:
        # NOTE: We have to use the callable with hashlib (hashlib.sha1),
        # otherwise hmac only accepts the sha module object itself
        from hashlib import sha1 as SHA1

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
        for j in xrange(2, 1+self.__iterations):
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
    result = PBKDF2("X"*64, "pass phrase equals block size", 1200).hexread(32)
    expected = ("139c30c0966bc32ba55fdbf212530ac9"
                "c5ec59f1a452f5cc9ad940fea0598ed1")
    if result != expected:
        raise RuntimeError("self-test failed")
    
    # Test 4
    result = PBKDF2("X"*65, "pass phrase exceeds block size", 1200).hexread(32)
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
"""
Encryption module that uses pycryptopp.
"""
from pycryptopp.cipher import aes

def aesEncrypt(data, key):
    cipher = aes.AES(key)
    return cipher.process(data)


def getKeyLength():
    return 32

########NEW FILE########
__FILENAME__ = exceptions
"""Beaker exception classes"""

class BeakerException(Exception):
    pass


class CreationAbortedError(Exception):
    """Deprecated."""


class InvalidCacheBackendError(BeakerException, ImportError):
    pass


class MissingCacheParameter(BeakerException):
    pass


class LockError(BeakerException):
    pass


class InvalidCryptoBackendError(BeakerException, ImportError):

    def __init__(self):
        Exception.__init__(self,
                           'No supported crypto implementation was found')

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

sa_version = None

log = logging.getLogger(__name__)

try:
    import sqlalchemy as sa
    import sqlalchemy.pool as pool
    from sqlalchemy import types
    sa_version = '0.3'
except ImportError:
    raise InvalidCacheBackendError("Database cache backend requires the 'sqlalchemy' library")

if not hasattr(sa, 'BoundMetaData'):
    sa_version = '0.4'

class DatabaseNamespaceManager(OpenResourceNamespaceManager):
    metadatas = SyncDict()
    tables = SyncDict()
    
    def __init__(self, namespace, url=None, sa_opts=None, optimistic=False,
                 table_name='beaker_cache', data_dir=None, lock_dir=None,
                 **params):
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
                if sa_version == '0.3':
                    if url.startswith('mysql') and not sa_opts:
                        sa_opts['poolclass'] = pool.QueuePool
                    engine = sa.create_engine(url, **sa_opts)
                    meta = sa.BoundMetaData(engine)
                else:
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
                             sa.UniqueConstraint('namespace')
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
            identifier ="databasecontainer/funclock/%s" % self.namespace,
            lock_dir = self.lock_dir)

    def do_open(self, flags):
        # If we already loaded the data, don't bother loading it again
        if self.loaded:
            self.flags = flags
            return
        
        cache = self.cache
        result = sa.select([cache.c.data], 
                           cache.c.namespace==self.namespace
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
                cache.update(cache.c.namespace==self.namespace).execute(
                    data=self.hash, accessed=datetime.now())
        self.flags = None
    
    def do_remove(self):
        cache = self.cache
        cache.delete(cache.c.namespace==self.namespace).execute()
        self.hash = {}
        
        # We can retain the fact that we did a load attempt, but since the
        # file is gone this will be a new namespace should it be saved.
        self._is_new = True

    def __getitem__(self, key): 
        return self.hash[key]

    def __contains__(self, key): 
        return self.hash.has_key(key)
        
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
from __future__ import absolute_import
import cPickle
import logging
from datetime import datetime

from beaker.container import OpenResourceNamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError
from beaker.synchronization import null_synchronizer

log = logging.getLogger(__name__)

try:
    from google.appengine.ext import db
except ImportError:
    raise InvalidCacheBackendError("Datastore cache backend requires the "
                                   "'google.appengine.ext' library")


class GoogleNamespaceManager(OpenResourceNamespaceManager):
    tables = {}
    
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

    def do_open(self, flags):
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
        return self.hash.has_key(key)
        
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
from beaker.container import NamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import file_synchronizer, null_synchronizer
from beaker.util import verify_directory, SyncDict
import warnings

try:
    import pylibmc as memcache
except ImportError:
    try:
        import cmemcache as memcache
        warnings.warn("cmemcache is known to have serious concurrency issues; consider using 'memcache' or 'pylibmc'")
    except ImportError:
        try:
            import memcache
        except ImportError:
            raise InvalidCacheBackendError("Memcached cache backend requires either the 'memcache' or 'cmemcache' library")

class MemcachedNamespaceManager(NamespaceManager):
    clients = SyncDict()
    
    def __init__(self, namespace, url=None, data_dir=None, lock_dir=None, **params):
        NamespaceManager.__init__(self, namespace)
       
        if not url:
            raise MissingCacheParameter("url is required") 
        
        if lock_dir:
            self.lock_dir = lock_dir
        elif data_dir:
            self.lock_dir = data_dir + "/container_mcd_lock"
        if self.lock_dir:
            verify_directory(self.lock_dir)            
        
        self.mc = MemcachedNamespaceManager.clients.get(url, memcache.Client, url.split(';'))

    def get_creation_lock(self, key):
        return file_synchronizer(
            identifier="memcachedcontainer/funclock/%s" % self.namespace,lock_dir = self.lock_dir)

    def _format_key(self, key):
        return self.namespace + '_' + key.replace(' ', '\302\267')

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
        raise NotImplementedError("Memcache caching does not support iteration of all cache keys")

class MemcachedContainer(Container):
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

try:
    import sqlalchemy as sa
except ImportError:
    raise InvalidCacheBackendError('SQLAlchemy, which is required by this backend, is not installed')

log = logging.getLogger(__name__)

class SqlaNamespaceManager(OpenResourceNamespaceManager):
    binds = SyncDict()
    tables = SyncDict()

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
            identifier ="databasecontainer/funclock/%s" % self.namespace,
            lock_dir=self.lock_dir)

    def do_open(self, flags):
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
        return self.hash.has_key(key)

    def __setitem__(self, key, value):
        self.hash[key] = value

    def __delitem__(self, key):
        del self.hash[key]

    def keys(self):
        return self.hash.keys()


class SqlaContainer(Container):
    namespace_manager = SqlaNamespaceManager

def make_cache_table(metadata, table_name='beaker_cache'):
    """Return a ``Table`` object suitable for storing cached values for the
    namespace manager.  Do not create the table."""
    return sa.Table(table_name, metadata,
                    sa.Column('namespace', sa.String(255), primary_key=True),
                    sa.Column('accessed', sa.DateTime, nullable=False),
                    sa.Column('created', sa.DateTime, nullable=False),
                    sa.Column('data', sa.PickleType, nullable=False))

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
        
        The Cache middleware will make a Cache instance available
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
            single dictionary. If config contains *no cache. prefixed
            args*, then *all* of the config options will be used to
            intialize the Cache objects.
        
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
        
        # Assume all keys are intended for cache if none are prefixed with
        # 'cache.'
        if not self.options and config:
            self.options = config
        
        self.options.update(kwargs)
        self.wrap_app = wrap_app
        self.environ_key = environ_key
        
    def __call__(self, environ, start_response):
        session = SessionObject(environ, **self.options)
        if environ.get('paste.registry'):
            if environ['paste.registry'].reglist:
                environ['paste.registry'].register(self.session, session)
        environ[self.environ_key] = session
        environ['beaker.get_session'] = self._get_session
        
        def session_start_response(status, headers, exc_info = None):
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
import cPickle
import Cookie
import hmac
import os
import random
import time
from datetime import datetime, timedelta
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
try:
    # Use PyCrypto (if available)
    from Crypto.Hash import HMAC, SHA as SHA1

except ImportError:
    # PyCrypto not available.  Use the Python standard library.
    import hmac as HMAC
    import sys
    # When using the stdlib, we have to make sure the hmac version and sha
    # version are compatible
    if sys.version_info[0:2] <= (2,4):
        # hmac in python2.4 or less require the sha module
        import sha as SHA1
    else:
        # NOTE: We have to use the callable with hashlib (hashlib.sha1),
        # otherwise hmac only accepts the sha module object itself
        from hashlib import sha1 as SHA1

# Check for pycryptopp encryption for AES
try:
    from beaker.crypto import generateCryptoKeys, aesEncrypt
    crypto_ok = True
except:
    crypto_ok = False

from beaker.cache import clsmap
from beaker.exceptions import BeakerException
from beaker.util import b64decode, b64encode, Set

__all__ = ['SignedCookie', 'Session']

getpid = hasattr(os, 'getpid') and os.getpid or (lambda : '')

class SignedCookie(Cookie.BaseCookie):
    """Extends python cookie to give digital signature support"""
    def __init__(self, secret, input=None):
        self.secret = secret
        Cookie.BaseCookie.__init__(self, input)
    
    def value_decode(self, val):
        val = val.strip('"')
        sig = HMAC.new(self.secret, val[40:], SHA1).hexdigest()
        if sig != val[:40]:
            return None, val
        else:
            return val[40:], val
    
    def value_encode(self, val):
        sig = HMAC.new(self.secret, val, SHA1).hexdigest()
        return str(val), ("%s%s" % (sig, val))


class Session(dict):
    """Session object that uses container package for storage"""
    def __init__(self, request, id=None, invalidate_corrupt=False,
                 use_cookies=True, type=None, data_dir=None,
                 key='beaker.session.id', timeout=None, cookie_expires=True,
                 cookie_domain=None, secret=None, secure=False,
                 namespace_class=None, **namespace_args):
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
        self._path = '/'
        self.was_invalidated = False
        self.secret = secret
        self.secure = secure
        self.id = id
        self.accessed_dict = {}
        
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
            except:
                if invalidate_corrupt:
                    self.invalidate()
                else:
                    raise
        
    def _create_id(self):
        self.id = md5(
            md5("%f%s%f%s" % (time.time(), id({}), random.random(),
                              getpid())).hexdigest(), 
        ).hexdigest()
        self.is_new = True
        self.last_accessed = None
        if self.use_cookies:
            self.cookie[self.key] = self.id
            if self._domain:
                self.cookie[self.key]['domain'] = self._domain
            if self.secure:
                self.cookie[self.key]['secure'] = True
            self.cookie[self.key]['path'] = self._path
            if self.cookie_expires is not True:
                if self.cookie_expires is False:
                    expires = datetime.fromtimestamp( 0x7FFFFFFF )
                elif isinstance(self.cookie_expires, timedelta):
                    expires = datetime.today() + self.cookie_expires
                elif isinstance(self.cookie_expires, datetime):
                    expires = self.cookie_expires
                else:
                    raise ValueError("Invalid argument for cookie_expires: %s"
                                     % repr(self.cookie_expires))
                self.cookie[self.key]['expires'] = \
                    expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT" )
            self.request['cookie_out'] = self.cookie[self.key].output(header='')
            self.request['set_cookie'] = False
    
    def created(self):
        return self['_creation_time']
    created = property(created)
    
    def _set_domain(self, domain):
        self['_domain'] = domain
        self.cookie[self.key]['domain'] = domain
        self.request['cookie_out'] = self.cookie[self.key].output(header='')
        self.request['set_cookie'] = True
    
    def _get_domain(self, domain):
        return self._domain
    
    domain = property(_get_domain, _set_domain)
    
    def _set_path(self, path):
        self['_path'] = path
        self.cookie[self.key]['path'] = path
        self.request['cookie_out'] = self.cookie[self.key].output(header='')
        self.request['set_cookie'] = True
    
    def _get_path(self, domain):
        return self._path
    
    path = property(_get_path, _set_path)

    def _delete_cookie(self):
        self.request['set_cookie'] = True
        self.cookie[self.key] = self.id
        if self._domain:
            self.cookie[self.key]['domain'] = self._domain
        if self.secure:
            self.cookie[self.key]['secure'] = True
        self.cookie[self.key]['path'] = '/'
        expires = datetime.today().replace(year=2003)
        self.cookie[self.key]['expires'] = \
            expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT" )
        self.request['cookie_out'] = self.cookie[self.key].output(header='')
        self.request['set_cookie'] = True

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
            data_dir=self.data_dir, digest_filenames=False,
            **self.namespace_args)
        now = time.time()
        self.request['set_cookie'] = True
        
        self.namespace.acquire_read_lock()
        timed_out = False
        try:
            self.clear()
            try:
                session_data = self.namespace['session']

                # Memcached always returns a key, its None when its not
                # present
                if session_data is None:
                    session_data = {
                        '_creation_time':now,
                        '_accessed_time':now
                    }
                    self.is_new = True
            except (KeyError, TypeError):
                session_data = {
                    '_creation_time':now,
                    '_accessed_time':now
                }
                self.is_new = True
            
            if self.timeout is not None and \
               now - session_data['_accessed_time'] > self.timeout:
                timed_out= True
            else:
                # Properly set the last_accessed time, which is different
                # than the *currently* _accessed_time
                if self.is_new or '_accessed_time' not in session_data:
                    self.last_accessed = None
                else:
                    self.last_accessed = session_data['_accessed_time']
                
                # Update the current _accessed_time
                session_data['_accessed_time'] = now
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
        
        if not hasattr(self, 'namespace'):
            self.namespace = self.namespace_class(
                                    self.id, 
                                    data_dir=self.data_dir,
                                    digest_filenames=False, 
                                    **self.namespace_args)
        
        self.namespace.acquire_write_lock()
        try:
            if accessed_only:
                data = dict(self.accessed_dict.items())
            else:
                data = dict(self.items())
            
            # Save the data
            if not data and 'session' in self.namespace:
                del self.namespace['session']
            else:
                self.namespace['session'] = data
        finally:
            self.namespace.release_write_lock()
        if self.is_new:
            self.request['set_cookie'] = True
    
    def revert(self):
        """Revert the session to its original state from its first
        access in the request"""
        self.clear()
        self.update(self.accessed_dict)
    
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
    
    ``key``
        The name the cookie should be set to.
    ``timeout``
        How long session data is considered valid. This is used 
        regardless of the cookie being present or not to determine
        whether session data is still valid.
    ``encrypt_key``
        The key to use for the session encryption, if not provided the
        session will not be encrypted.
    ``validate_key``
        The key used to sign the encrypted session
    ``cookie_domain``
        Domain to use for the cookie.
    ``secure``
        Whether or not the cookie should only be sent over SSL.
    
    """
    def __init__(self, request, key='beaker.session.id', timeout=None,
                 cookie_expires=True, cookie_domain=None, encrypt_key=None,
                 validate_key=None, secure=False, **kwargs):
        if not crypto_ok and encrypt_key:
            raise BeakerException("pycryptopp is not installed, can't use "
                                  "encrypted cookie-only Session.")
        
        self.request = request
        self.key = key
        self.timeout = timeout
        self.cookie_expires = cookie_expires
        self.encrypt_key = encrypt_key
        self.validate_key = validate_key
        self.request['set_cookie'] = False
        self.secure = secure
        self._domain = cookie_domain
        self._path = '/'
        
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
        
        self['_id'] = self._make_id()
        self.is_new = True
        
        # If we have a cookie, load it
        if self.key in self.cookie and self.cookie[self.key].value is not None:
            self.is_new = False
            try:
                self.update(self._decrypt_data())
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
        
    def _get_domain(self, domain):
        return self._domain
    
    domain = property(_get_domain, _set_domain)
    
    def _set_path(self, path):
        self['_path'] = path
        self._path = path
    
    def _get_path(self, domain):
        return self._path
    
    path = property(_get_path, _set_path)

    def _encrypt_data(self):
        """Serialize, encipher, and base64 the session dict"""
        if self.encrypt_key:
            nonce = b64encode(os.urandom(40))[:8]
            encrypt_key = generateCryptoKeys(self.encrypt_key,
                                             self.validate_key + nonce, 1)
            data = cPickle.dumps(self.copy(), 2)
            return nonce + b64encode(aesEncrypt(data, encrypt_key))
        else:
            data = cPickle.dumps(self.copy(), 2)
            return b64encode(data)
    
    def _decrypt_data(self):
        """Bas64, decipher, then un-serialize the data for the session
        dict"""
        if self.encrypt_key:
            nonce = self.cookie[self.key].value[:8]
            encrypt_key = generateCryptoKeys(self.encrypt_key,
                                             self.validate_key + nonce, 1)
            payload = b64decode(self.cookie[self.key].value[8:])
            data = aesEncrypt(payload, encrypt_key)
            return cPickle.loads(data)
        else:
            data = b64decode(self.cookie[self.key].value)
            return cPickle.loads(data)
    
    def _make_id(self):
        return md5(md5(
            "%f%s%f%s" % (time.time(), id({}), random.random(), getpid())
            ).hexdigest()
        ).hexdigest()
    
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
            self['_id'] = self._make_id()
        self['_accessed_time'] = time.time()
        
        if self.cookie_expires is not True:
            if self.cookie_expires is False:
                expires = datetime.fromtimestamp( 0x7FFFFFFF )
            elif isinstance(self.cookie_expires, timedelta):
                expires = datetime.today() + self.cookie_expires
            elif isinstance(self.cookie_expires, datetime):
                expires = self.cookie_expires
            else:
                raise ValueError("Invalid argument for cookie_expires: %s"
                                 % repr(self.cookie_expires))
            self['_expires'] = expires
        elif '_expires' in self:
            expires = self['_expires']
        else:
            expires = None

        val = self._encrypt_data()
        if len(val) > 4064:
            raise BeakerException("Cookie value is too long to store")
        
        self.cookie[self.key] = val
        if '_domain' in self:
            self.cookie[self.key]['domain'] = self['_domain']
        elif self._domain:
            self.cookie[self.key]['domain'] = self._domain
        if self.secure:
            self.cookie[self.key]['secure'] = True
        
        self.cookie[self.key]['path'] = self.get('_path', '/')
        
        if expires:
            self.cookie[self.key]['expires'] = \
                expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT" )
        self.request['cookie_out'] = self.cookie[self.key].output(header='')
        self.request['set_cookie'] = True
    
    def delete(self):
        """Delete the cookie, and clear the session"""
        # Send a delete cookie request
        self._delete_cookie()
        self.clear()
    
    def invalidate(self):
        """Clear the contents and start a new session"""
        self.delete()
        self['_id'] = self._make_id()


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
        self.__dict__['_headers'] = []
    
    def _session(self):
        """Lazy initial creation of session object"""
        if self.__dict__['_sess'] is None:
            params = self.__dict__['_params']
            environ = self.__dict__['_environ']
            self.__dict__['_headers'] = req = {'cookie_out':None}
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
        return self._session().has_key(key)
    
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

__all__  = ["file_synchronizer", "mutex_synchronizer", "null_synchronizer",
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

    def __init__(self, identifier = None, reentrant = False):
        if identifier is None:
            self._lock = NameLock.NLContainer(reentrant)
        else:
            self._lock = NameLock.locks.get(identifier, NameLock.NLContainer,
                                            reentrant)

    def acquire(self, wait = True):
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
        
    def acquire_read_lock(self, wait = True):
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
    
    def acquire_write_lock(self, wait  = True):
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
    """a synchronizer which locks using flock().

    Adapted for Python/multithreads from Apache::Session::Lock::File,
    http://search.cpan.org/src/CWEST/Apache-Session-1.81/Session/Lock/File.pm
    
    This module does not unlink temporary files, 
    because it interferes with proper locking.  This can cause 
    problems on certain systems (Linux) whose file systems (ext2) do not 
    perform well with lots of files in one directory.  To prevent this
    you should use a script to clean out old files from your lock directory.
    
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

    def do_acquire_read_lock(self, wait = True):    
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
    
    def do_acquire_write_lock(self, wait = True):
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
import string
import types
import weakref
import warnings

try:
    Set = set
except NameError:
    from sets import Set
try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

from beaker.converters import asbool

try:
    from base64 import b64encode, b64decode
except ImportError:
    import binascii

    _translation = [chr(_x) for _x in range(256)]

    # From Python 2.5 base64.py
    def _translate(s, altchars):
        translation = _translation[:]
        for k, v in altchars.items():
            translation[ord(k)] = v
        return s.translate(''.join(translation))

    def b64encode(s, altchars=None):
        """Encode a string using Base64.

        s is the string to encode.  Optional altchars must be a string of at least
        length 2 (additional characters are ignored) which specifies an
        alternative alphabet for the '+' and '/' characters.  This allows an
        application to e.g. generate url or filesystem safe Base64 strings.

        The encoded string is returned.
        """
        # Strip off the trailing newline
        encoded = binascii.b2a_base64(s)[:-1]
        if altchars is not None:
            return _translate(encoded, {'+': altchars[0], '/': altchars[1]})
        return encoded

    def b64decode(s, altchars=None):
        """Decode a Base64 encoded string.

        s is the string to decode.  Optional altchars must be a string of at least
        length 2 (additional characters are ignored) which specifies the
        alternative alphabet used instead of the '+' and '/' characters.

        The decoded string is returned.  A TypeError is raised if s were
        incorrectly padded or if there are non-alphabet characters present in the
        string.
        """
        if altchars is not None:
            s = _translate(s, {altchars[0]: '+', altchars[1]: '/'})
        try:
            return binascii.a2b_base64(s)
        except binascii.Error, msg:
            # Transform this exception for consistency
            raise TypeError(msg)

try:
    from threading import local as _tlocal
except ImportError:
    try:
        from dummy_threading import local as _tlocal
    except ImportError:
        class _tlocal(object):
            def __init__(self):
                self.__dict__['_tdict'] = {}

            def __delattr__(self, key):
                try:
                    del self._tdict[(thread.get_ident(), key)]
                except KeyError:
                    raise AttributeError(key)

            def __getattr__(self, key):
                try:
                    return self._tdict[(thread.get_ident(), key)]
                except KeyError:
                    raise AttributeError(key)

            def __setattr__(self, key, value):
                self._tdict[(thread.get_ident(), key)] = value


__all__  = ["ThreadLocal", "Registry", "WeakValuedRegistry", "SyncDict",
            "encoded_path", "verify_directory"]


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

    
def deprecated(func, message):
    def deprecated_method(*args, **kargs):
        warnings.warn(message, DeprecationWarning, 2)
        return func(*args, **kargs)
    try:
        deprecated_method.__name__ = func.__name__
    except TypeError: # Python < 2.4
        pass
    deprecated_method.__doc__ = "%s\n\n%s" % (message, func.__doc__)
    return deprecated_method

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
            if self.has_key(key):
                return self.dict[key]
            else:
                return self.sync_get(key, createfunc, *args, **kwargs)
        except KeyError:
            return self.sync_get(key, createfunc, *args, **kwargs)

    def sync_get(self, key, createfunc, *args, **kwargs):
        self.mutex.acquire()
        try:
            try:
                if self.has_key(key):
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
        return self.dict.has_key(key)
        
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

            
def encoded_path(root, identifiers, extension = ".enc", depth = 3,
                 digest_filenames=True):
    """Generate a unique file-accessible path from the given list of
    identifiers starting at the given root directory."""
    ident = string.join(identifiers, "_")

    if digest_filenames:
        ident = sha1(ident).hexdigest()
    
    ident = os.path.basename(ident)

    tokens = []
    for d in range(1, depth):
        tokens.append(ident[0:d])
    
    dir = os.path.join(root, *tokens)
    verify_directory(dir)
    
    return os.path.join(dir, ident + extension)


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
        ('lock_dir', (str,), "lock_dir must be a string referring to a "
         "directory."),
        ('type', (str, types.NoneType), "Session type must be a string."),
        ('cookie_expires', (bool, datetime, timedelta), "Cookie expires was "
         "not a boolean, datetime, or timedelta instance."),
        ('cookie_domain', (str, types.NoneType), "Cookie domain must be a "
         "string."),
        ('id', (str,), "Session id must be a string."),
        ('key', (str,), "Session key must be a string."),
        ('secret', (str, types.NoneType), "Session secret must be a string."),
        ('validate_key', (str, types.NoneType), "Session encrypt_key must be "
         "a string."),
        ('encrypt_key', (str, types.NoneType), "Session validate_key must be "
         "a string."),
        ('secure', (bool, types.NoneType), "Session secure must be a boolean."),
        ('timeout', (int, types.NoneType), "Session timeout must be an "
         "integer."),
        ('auto', (bool, types.NoneType), "Session is created if accessed."),
    ]
    return verify_rules(params, rules)


def coerce_cache_params(params):
    rules = [
        ('data_dir', (str, types.NoneType), "data_dir must be a string "
         "referring to a directory."),
        ('lock_dir', (str,), "lock_dir must be a string referring to a "
         "directory."),
        ('type', (str,), "Cache type must be a string."),
        ('enabled', (bool, types.NoneType), "enabled must be true/false "
         "if present."),
        ('expire', (int, types.NoneType), "expire must be an integer representing "
         "how many seconds the cache is valid for"),
        ('regions', (list, tuple, types.NoneType), "Regions must be a "
         "comma seperated list of valid regions")
    ]
    return verify_rules(params, rules)


def parse_cache_config_options(config, include_defaults=True):
    """Parse configuration options and validate for use with the
    CacheManager"""
    # Load default cache options
    if include_defaults:
        options= dict(type='memory', data_dir=None, expire=None, 
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
    if 'enabled' not in options:
        options['enabled'] = True
    
    # Configure region dict if regions are available
    regions = options.pop('regions', None)
    if regions:
        region_configs = {}
        for region in regions:
            # Setup the default cache options
            region_options = dict(data_dir=options.get('data_dir'),
                                  lock_dir=options.get('lock_dir'),
                                  type=options.get('type'),
                                  enabled=options['enabled'],
                                  expire=options.get('expire'))
            region_len = len(region) + 1
            for key in options.keys():
                if key.startswith('%s.' % region):
                    region_options[key[region_len:]] = options.pop(key)
            coerce_cache_params(region_options)
            region_configs[region] = region_options
        options['cache_regions'] = region_configs
    return options

def func_namespace(func):
    """Generates a unique namespace for a function"""
    kls = None
    if hasattr(func, 'im_func'):
        kls = func.im_class
        func = func.im_func
    
    if kls:
        return '%s.%s' % (kls.__module__, kls.__name__)
    else:
        return '%s.%s' % (func.__module__, func.__name__)

########NEW FILE########
__FILENAME__ = handlers
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from openid.consumer.consumer import Consumer
from openid.consumer.discover import DiscoveryFailure
from openid.extensions import sreg
from openid.extensions import ax

from aeoid import store
from aeoid import users

# list of attributes to request via Simple Registration
OPENID_SREG_ATTRS = ['nickname', 'email']

# dict of uris => attributes to request via Attribute Exchange
OPENID_AX_ATTRS = {
    'http://axschema.org/contact/email':        'email',
    'http://axschema.org/namePerson/friendly':  'nickname',
    'http://axschema.org/namePerson/first':     'firstname',
    'http://axschema.org/namePerson/last':      'lastname',
}

class BaseHandler(webapp.RequestHandler):
  def initialize(self, request, response):
    super(BaseHandler, self).initialize(request, response)
    self.session = self.request.environ.get('aeoid.beaker.session')

  def render_template(self, filename, template_args=None):
    if not template_args:
      template_args = {}
    path = os.path.join(os.path.dirname(__file__), 'templates', filename)
    self.response.out.write(template.render(path, template_args))

  def get_consumer(self):
    return Consumer(self.session, store.AppEngineStore())


class BeginLoginHandler(BaseHandler):
  def get(self):
    openid_url = self.request.get('openid_url')
    if not openid_url:
      self.render_template('login.html', {
          'login_url': users.OPENID_LOGIN_PATH,
          'continue': self.request.get('continue', '/')
      })
      return

    consumer = self.get_consumer()
    # if consumer discovery or authentication fails, show error page
    try:
      request = consumer.begin(openid_url)
    except Exception, e:
      logging.error("Unexpected error in OpenID discovery/authentication: %s", e)
      self.render_template('error.html')
      return
    
    # TODO: Support custom specification of extensions
    # TODO: Don't ask for data we already have, perhaps?
    # use Simple Registration if available
    request.addExtension(sreg.SRegRequest(required=OPENID_SREG_ATTRS))
    # or Atribute Exchange if available
    ax_request = ax.FetchRequest()
    for attruri in OPENID_AX_ATTRS:
        ax_request.add(ax.AttrInfo(attruri, required=True, alias=OPENID_AX_ATTRS[attruri]))
    request.addExtension(ax_request)
    # assemble and send redirect
    continue_url = self.request.get('continue', '/')
    return_to = "%s%s?continue=%s" % (self.request.host_url,
                                      users.OPENID_FINISH_PATH, continue_url)
    self.redirect(request.redirectURL(self.request.host_url, return_to))
    self.session.save()

  def post(self):
    self.get()


class FinishLoginHandler(BaseHandler):
  def finish_login(self, response):
    # get sreg data if available
    id_res_data = sreg.SRegResponse.fromSuccessResponse(response)
    if not id_res_data is None:
      id_res_data = dict(id_res_data)
    
    # otherwise get ax data if available
    if id_res_data is None:
      id_res_data = {}
      try:
        ax_data = ax.FetchResponse.fromSuccessResponse(response)
        for attruri in OPENID_AX_ATTRS:
          try:
            attrvalue = ax_data.get(attruri)
            id_res_data[ OPENID_AX_ATTRS[attruri] ] = attrvalue.pop(0)
          except (AttributeError,IndexError,KeyError):
            pass
        # try to ensure we have a nickname (even if we fall back to email)
        if not id_res_data.has_key('nickname'):
          if id_res_data.has_key('firstname') or id_res_data.has_key('lastname'):
            id_res_data['nickname'] = id_res_data.get('firstname', '') + ' ' + id_res_data.get('lastname', '')
          elif id_res_data.has_key('email'):
            id_res_data['nickname'] = id_res_data['email']
      except ax.AXError:
        pass

    user_info = users.UserInfo.update_or_insert(
        response.endpoint.claimed_id,
        server_url=response.endpoint.server_url,
        **id_res_data)

    self.session['aeoid.user'] = str(user_info.key())
    self.session.save()
    users._current_user = users.User(None, _from_model_key=user_info.key(),
                                     _from_model=user_info)
    self.redirect(self.request.get('continue', '/'))

  def get(self):
    consumer = self.get_consumer()
    response = consumer.complete(self.request.GET, self.request.url)
    if response.status == 'success':
      self.finish_login(response)
    elif response.status in ('failure', 'cancel'):
      self.render_template('failure.html', {
          'response': response,
          'login_url': users.OPENID_LOGIN_PATH,
          'continue': self.request.get('continue', '/')
      })
    else:
      logging.error("Unexpected error in OpenID authentication: %s", response)
      self.render_template('error.html', {'identity_url': response.identity_url()})


class LogoutHandler(BaseHandler):
  def get(self):
    # before logging user out, check that http referer contains the current hostname
    httphost = str(self.request.environ.get('HTTP_HOST'))
    httprefer = str(self.request.environ.get('HTTP_REFERER'))
    # if it does, log them out as expected
    if httprefer.startswith(('http://'+httphost,'https://'+httphost)):
      if 'aeoid.user' in self.session:
        del self.session['aeoid.user']
      self.session.save()
      self.redirect(self.request.get('continue', '/'))
    # if it doesn't, prompt them via an interstitial page
    else:
      self.render_template('logout.html', {
          'confirmurl': '?continue='+self.request.get('continue', '/'),
          'cancelurl': self.request.get('continue', '/')
      })


# highly modified from example at:
# http://www.ipsojobs.com/blog/2008/06/17/how-to-create-a-simple-but-powerful-cdn-with-google-app-engine-gae/
class StaticHandler(webapp.RequestHandler):
  allowed_exts = { 'js': 'application/x-javascript', 'css': 'text/css', 'png': 'image/png' }
  
  def get(self, filepath, fileext):
    # build full system path to requested file
    resourcepath = os.path.join( os.path.dirname(__file__), 'resources', filepath + '.' + fileext )
    
    # only allow specified file extensions
    if not self.allowed_exts.has_key(fileext):
      logging.error("Not an allowed file extension: %s" % fileext)
      self.error(404)
      return
    
    # file must exist before we can return it
    if not os.path.isfile(resourcepath):
      logging.error("Not an existing file: '%s'" % resourcepath)
      self.error(404)
      return
    
    # only allow absolute paths (no symlinks or up-level references, for example)
    testpath = os.path.normcase(resourcepath)
    if testpath != os.path.abspath(testpath):
      logging.error("Not an absolute path to file: '%s' != '%s'" % (testpath, os.path.abspath(testpath)) )
      self.error(403)
      return
    
    # set appropriate content-type
    self.response.headers['Content-Type'] = self.allowed_exts[fileext]
    
    # serve file (supporting client-side caching)
    try:
      import datetime
      fileinfo = os.stat(resourcepath)
      lastmod = datetime.datetime.fromtimestamp(fileinfo[8])
      if self.request.headers.has_key('If-Modified-Since'):
        dt = self.request.headers.get('If-Modified-Since').split(';')[0]
        modsince = datetime.datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %Z")
        if modsince >= lastmod:
        # The file is older than the cached copy (or exactly the same)
          self.error(304)
          return
        else:
        # The file is newer
          self.output_file(resourcepath, lastmod)
      else:
        self.output_file(resourcepath, lastmod)
    except Exception, e:
      logging.error("Failed to serve file: %s" % e)
      self.error(404)
      return

  def output_file(self, resourcepath, lastmod):
    import datetime
    try:
      self.response.headers['Cache-Control']='public, max-age=31536000'
      self.response.headers['Last-Modified'] = lastmod.strftime("%a, %d %b %Y %H:%M:%S GMT")
      expires=lastmod+datetime.timedelta(days=365)
      self.response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
      self.response.out.write( file(resourcepath, 'rb').read() )
      return
    except IOError, e:
      logging.error("Failed to output file: %s" % e)
      self.error(404)
      return


handler_map = [
    (users.OPENID_LOGIN_PATH, BeginLoginHandler),
    (users.OPENID_FINISH_PATH, FinishLoginHandler),
    (users.OPENID_LOGOUT_PATH, LogoutHandler),
    (users.OPENID_STATIC_PATH, StaticHandler),
]

########NEW FILE########
__FILENAME__ = middleware
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import sys
sys.path.append(os.path.dirname(__file__))

from beaker.middleware import SessionMiddleware
from google.appengine.ext import webapp

from aeoid import handlers
from aeoid import users


class _MiddlewareImpl(object):
  def __init__(self, application, debug=False):
    self.application = application
    self.oid_app = webapp.WSGIApplication(handlers.handler_map, debug=debug)

  def __call__(self, environ, start_response):
    session = environ['aeoid.beaker.session']
    if 'aeoid.user' in session:
      os.environ['aeoid.user'] = environ['aeoid.user'] = session['aeoid.user']
    try:
      if environ['PATH_INFO'].startswith(users.OPENID_PATH_PREFIX):
        return self.oid_app(environ, start_response)
      else:
        return self.application(environ, start_response)
    finally:
      users._current_user = None


def AeoidMiddleware(application, session_opts=None, debug=False):
  """WSGI middleware that adds support for OpenID user authentication."""

  beaker_opts = {
      'session.type': 'ext:google',
      'session.key': 'aeoid.beaker.session.id',
  }
  if session_opts:
    beaker_opts.update(session_opts)
  application = _MiddlewareImpl(application, debug)
  application = SessionMiddleware(wrap_app=application, config=beaker_opts, environ_key='aeoid.beaker.session')
  return application

########NEW FILE########
__FILENAME__ = association
# -*- test-case-name: openid.test.test_association -*-
"""
This module contains code for dealing with associations between
consumers and servers. Associations contain a shared secret that is
used to sign C{openid.mode=id_res} messages.

Users of the library should not usually need to interact directly with
associations. The L{store<openid.store>},
L{server<openid.server.server>} and
L{consumer<openid.consumer.consumer>} objects will create and manage
the associations. The consumer and server code will make use of a
C{L{SessionNegotiator}} when managing associations, which enables
users to express a preference for what kind of associations should be
allowed, and what kind of exchange should be done to establish the
association.

@var default_negotiator: A C{L{SessionNegotiator}} that allows all
    association types that are specified by the OpenID
    specification. It prefers to use HMAC-SHA1/DH-SHA1, if it's
    available. If HMAC-SHA256 is not supported by your Python runtime,
    HMAC-SHA256 and DH-SHA256 will not be available.

@var encrypted_negotiator: A C{L{SessionNegotiator}} that
    does not support C{'no-encryption'} associations. It prefers
    HMAC-SHA1/DH-SHA1 association types if available.
"""

__all__ = [
    'default_negotiator',
    'encrypted_negotiator',
    'SessionNegotiator',
    'Association',
    ]

import time

from openid import cryptutil
from openid import kvform
from openid import oidutil
from openid.message import OPENID_NS

all_association_types = [
    'HMAC-SHA1',
    'HMAC-SHA256',
    ]

if hasattr(cryptutil, 'hmacSha256'):
    supported_association_types = list(all_association_types)

    default_association_order = [
        ('HMAC-SHA1', 'DH-SHA1'),
        ('HMAC-SHA1', 'no-encryption'),
        ('HMAC-SHA256', 'DH-SHA256'),
        ('HMAC-SHA256', 'no-encryption'),
        ]

    only_encrypted_association_order = [
        ('HMAC-SHA1', 'DH-SHA1'),
        ('HMAC-SHA256', 'DH-SHA256'),
        ]
else:
    supported_association_types = ['HMAC-SHA1']

    default_association_order = [
        ('HMAC-SHA1', 'DH-SHA1'),
        ('HMAC-SHA1', 'no-encryption'),
        ]

    only_encrypted_association_order = [
        ('HMAC-SHA1', 'DH-SHA1'),
        ]

def getSessionTypes(assoc_type):
    """Return the allowed session types for a given association type"""
    assoc_to_session = {
        'HMAC-SHA1': ['DH-SHA1', 'no-encryption'],
        'HMAC-SHA256': ['DH-SHA256', 'no-encryption'],
        }
    return assoc_to_session.get(assoc_type, [])

def checkSessionType(assoc_type, session_type):
    """Check to make sure that this pair of assoc type and session
    type are allowed"""
    if session_type not in getSessionTypes(assoc_type):
        raise ValueError(
            'Session type %r not valid for assocation type %r'
            % (session_type, assoc_type))

class SessionNegotiator(object):
    """A session negotiator controls the allowed and preferred
    association types and association session types. Both the
    C{L{Consumer<openid.consumer.consumer.Consumer>}} and
    C{L{Server<openid.server.server.Server>}} use negotiators when
    creating associations.

    You can create and use negotiators if you:

     - Do not want to do Diffie-Hellman key exchange because you use
       transport-layer encryption (e.g. SSL)

     - Want to use only SHA-256 associations

     - Do not want to support plain-text associations over a non-secure
       channel

    It is up to you to set a policy for what kinds of associations to
    accept. By default, the library will make any kind of association
    that is allowed in the OpenID 2.0 specification.

    Use of negotiators in the library
    =================================

    When a consumer makes an association request, it calls
    C{L{getAllowedType}} to get the preferred association type and
    association session type.

    The server gets a request for a particular association/session
    type and calls C{L{isAllowed}} to determine if it should
    create an association. If it is supported, negotiation is
    complete. If it is not, the server calls C{L{getAllowedType}} to
    get an allowed association type to return to the consumer.

    If the consumer gets an error response indicating that the
    requested association/session type is not supported by the server
    that contains an assocation/session type to try, it calls
    C{L{isAllowed}} to determine if it should try again with the
    given combination of association/session type.

    @ivar allowed_types: A list of association/session types that are
        allowed by the server. The order of the pairs in this list
        determines preference. If an association/session type comes
        earlier in the list, the library is more likely to use that
        type.
    @type allowed_types: [(str, str)]
    """

    def __init__(self, allowed_types):
        self.setAllowedTypes(allowed_types)

    def copy(self):
        return self.__class__(list(self.allowed_types))

    def setAllowedTypes(self, allowed_types):
        """Set the allowed association types, checking to make sure
        each combination is valid."""
        for (assoc_type, session_type) in allowed_types:
            checkSessionType(assoc_type, session_type)

        self.allowed_types = allowed_types

    def addAllowedType(self, assoc_type, session_type=None):
        """Add an association type and session type to the allowed
        types list. The assocation/session pairs are tried in the
        order that they are added."""
        if self.allowed_types is None:
            self.allowed_types = []

        if session_type is None:
            available = getSessionTypes(assoc_type)

            if not available:
                raise ValueError('No session available for association type %r'
                                 % (assoc_type,))

            for session_type in getSessionTypes(assoc_type):
                self.addAllowedType(assoc_type, session_type)
        else:
            checkSessionType(assoc_type, session_type)
            self.allowed_types.append((assoc_type, session_type))


    def isAllowed(self, assoc_type, session_type):
        """Is this combination of association type and session type allowed?"""
        assoc_good = (assoc_type, session_type) in self.allowed_types
        matches = session_type in getSessionTypes(assoc_type)
        return assoc_good and matches

    def getAllowedType(self):
        """Get a pair of assocation type and session type that are
        supported"""
        try:
            return self.allowed_types[0]
        except IndexError:
            return (None, None)

default_negotiator = SessionNegotiator(default_association_order)
encrypted_negotiator = SessionNegotiator(only_encrypted_association_order)

def getSecretSize(assoc_type):
    if assoc_type == 'HMAC-SHA1':
        return 20
    elif assoc_type == 'HMAC-SHA256':
        return 32
    else:
        raise ValueError('Unsupported association type: %r' % (assoc_type,))

class Association(object):
    """
    This class represents an association between a server and a
    consumer.  In general, users of this library will never see
    instances of this object.  The only exception is if you implement
    a custom C{L{OpenIDStore<openid.store.interface.OpenIDStore>}}.

    If you do implement such a store, it will need to store the values
    of the C{L{handle}}, C{L{secret}}, C{L{issued}}, C{L{lifetime}}, and
    C{L{assoc_type}} instance variables.

    @ivar handle: This is the handle the server gave this association.

    @type handle: C{str}


    @ivar secret: This is the shared secret the server generated for
        this association.

    @type secret: C{str}


    @ivar issued: This is the time this association was issued, in
        seconds since 00:00 GMT, January 1, 1970.  (ie, a unix
        timestamp)

    @type issued: C{int}


    @ivar lifetime: This is the amount of time this association is
        good for, measured in seconds since the association was
        issued.

    @type lifetime: C{int}


    @ivar assoc_type: This is the type of association this instance
        represents.  The only valid value of this field at this time
        is C{'HMAC-SHA1'}, but new types may be defined in the future.

    @type assoc_type: C{str}


    @sort: __init__, fromExpiresIn, getExpiresIn, __eq__, __ne__,
        handle, secret, issued, lifetime, assoc_type
    """

    # The ordering and name of keys as stored by serialize
    assoc_keys = [
        'version',
        'handle',
        'secret',
        'issued',
        'lifetime',
        'assoc_type',
        ]


    _macs = {
        'HMAC-SHA1': cryptutil.hmacSha1,
        'HMAC-SHA256': cryptutil.hmacSha256,
        }


    def fromExpiresIn(cls, expires_in, handle, secret, assoc_type):
        """
        This is an alternate constructor used by the OpenID consumer
        library to create associations.  C{L{OpenIDStore
        <openid.store.interface.OpenIDStore>}} implementations
        shouldn't use this constructor.


        @param expires_in: This is the amount of time this association
            is good for, measured in seconds since the association was
            issued.

        @type expires_in: C{int}


        @param handle: This is the handle the server gave this
            association.

        @type handle: C{str}


        @param secret: This is the shared secret the server generated
            for this association.

        @type secret: C{str}


        @param assoc_type: This is the type of association this
            instance represents.  The only valid value of this field
            at this time is C{'HMAC-SHA1'}, but new types may be
            defined in the future.

        @type assoc_type: C{str}
        """
        issued = int(time.time())
        lifetime = expires_in
        return cls(handle, secret, issued, lifetime, assoc_type)

    fromExpiresIn = classmethod(fromExpiresIn)

    def __init__(self, handle, secret, issued, lifetime, assoc_type):
        """
        This is the standard constructor for creating an association.


        @param handle: This is the handle the server gave this
            association.

        @type handle: C{str}


        @param secret: This is the shared secret the server generated
            for this association.

        @type secret: C{str}


        @param issued: This is the time this association was issued,
            in seconds since 00:00 GMT, January 1, 1970.  (ie, a unix
            timestamp)

        @type issued: C{int}


        @param lifetime: This is the amount of time this association
            is good for, measured in seconds since the association was
            issued.

        @type lifetime: C{int}


        @param assoc_type: This is the type of association this
            instance represents.  The only valid value of this field
            at this time is C{'HMAC-SHA1'}, but new types may be
            defined in the future.

        @type assoc_type: C{str}
        """
        if assoc_type not in all_association_types:
            fmt = '%r is not a supported association type'
            raise ValueError(fmt % (assoc_type,))

#         secret_size = getSecretSize(assoc_type)
#         if len(secret) != secret_size:
#             fmt = 'Wrong size secret (%s bytes) for association type %s'
#             raise ValueError(fmt % (len(secret), assoc_type))

        self.handle = handle
        self.secret = secret
        self.issued = issued
        self.lifetime = lifetime
        self.assoc_type = assoc_type

    def getExpiresIn(self, now=None):
        """
        This returns the number of seconds this association is still
        valid for, or C{0} if the association is no longer valid.


        @return: The number of seconds this association is still valid
            for, or C{0} if the association is no longer valid.

        @rtype: C{int}
        """
        if now is None:
            now = int(time.time())

        return max(0, self.issued + self.lifetime - now)

    expiresIn = property(getExpiresIn)

    def __eq__(self, other):
        """
        This checks to see if two C{L{Association}} instances
        represent the same association.


        @return: C{True} if the two instances represent the same
            association, C{False} otherwise.

        @rtype: C{bool}
        """
        return type(self) is type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        """
        This checks to see if two C{L{Association}} instances
        represent different associations.


        @return: C{True} if the two instances represent different
            associations, C{False} otherwise.

        @rtype: C{bool}
        """
        return not (self == other)

    def serialize(self):
        """
        Convert an association to KV form.

        @return: String in KV form suitable for deserialization by
            deserialize.

        @rtype: str
        """
        data = {
            'version':'2',
            'handle':self.handle,
            'secret':oidutil.toBase64(self.secret),
            'issued':str(int(self.issued)),
            'lifetime':str(int(self.lifetime)),
            'assoc_type':self.assoc_type
            }

        assert len(data) == len(self.assoc_keys)
        pairs = []
        for field_name in self.assoc_keys:
            pairs.append((field_name, data[field_name]))

        return kvform.seqToKV(pairs, strict=True)

    def deserialize(cls, assoc_s):
        """
        Parse an association as stored by serialize().

        inverse of serialize


        @param assoc_s: Association as serialized by serialize()

        @type assoc_s: str


        @return: instance of this class
        """
        pairs = kvform.kvToSeq(assoc_s, strict=True)
        keys = []
        values = []
        for k, v in pairs:
            keys.append(k)
            values.append(v)

        if keys != cls.assoc_keys:
            raise ValueError('Unexpected key values: %r', keys)

        version, handle, secret, issued, lifetime, assoc_type = values
        if version != '2':
            raise ValueError('Unknown version: %r' % version)
        issued = int(issued)
        lifetime = int(lifetime)
        secret = oidutil.fromBase64(secret)
        return cls(handle, secret, issued, lifetime, assoc_type)

    deserialize = classmethod(deserialize)

    def sign(self, pairs):
        """
        Generate a signature for a sequence of (key, value) pairs


        @param pairs: The pairs to sign, in order

        @type pairs: sequence of (str, str)


        @return: The binary signature of this sequence of pairs

        @rtype: str
        """
        kv = kvform.seqToKV(pairs)

        try:
            mac = self._macs[self.assoc_type]
        except KeyError:
            raise ValueError(
                'Unknown association type: %r' % (self.assoc_type,))

        return mac(self.secret, kv)


    def getMessageSignature(self, message):
        """Return the signature of a message.

        If I am not a sign-all association, the message must have a
        signed list.

        @return: the signature, base64 encoded

        @rtype: str

        @raises ValueError: If there is no signed list and I am not a sign-all
            type of association.
        """
        pairs = self._makePairs(message)
        return oidutil.toBase64(self.sign(pairs))

    def signMessage(self, message):
        """Add a signature (and a signed list) to a message.

        @return: a new Message object with a signature
        @rtype: L{openid.message.Message}
        """
        if (message.hasKey(OPENID_NS, 'sig') or
            message.hasKey(OPENID_NS, 'signed')):
            raise ValueError('Message already has signed list or signature')

        extant_handle = message.getArg(OPENID_NS, 'assoc_handle')
        if extant_handle and extant_handle != self.handle:
            raise ValueError("Message has a different association handle")

        signed_message = message.copy()
        signed_message.setArg(OPENID_NS, 'assoc_handle', self.handle)
        message_keys = signed_message.toPostArgs().keys()
        signed_list = [k[7:] for k in message_keys
                       if k.startswith('openid.')]
        signed_list.append('signed')
        signed_list.sort()
        signed_message.setArg(OPENID_NS, 'signed', ','.join(signed_list))
        sig = self.getMessageSignature(signed_message)
        signed_message.setArg(OPENID_NS, 'sig', sig)
        return signed_message

    def checkMessageSignature(self, message):
        """Given a message with a signature, calculate a new signature
        and return whether it matches the signature in the message.

        @raises ValueError: if the message has no signature or no signature
            can be calculated for it.
        """        
        message_sig = message.getArg(OPENID_NS, 'sig')
        if not message_sig:
            raise ValueError("%s has no sig." % (message,))
        calculated_sig = self.getMessageSignature(message)
        return calculated_sig == message_sig


    def _makePairs(self, message):
        signed = message.getArg(OPENID_NS, 'signed')
        if not signed:
            raise ValueError('Message has no signed list: %s' % (message,))

        signed_list = signed.split(',')
        pairs = []
        data = message.toPostArgs()
        for field in signed_list:
            pairs.append((field, data.get('openid.' + field, '')))
        return pairs

    def __repr__(self):
        return "<%s.%s %s %s>" % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.assoc_type,
            self.handle)

########NEW FILE########
__FILENAME__ = consumer
# -*- test-case-name: openid.test.test_consumer -*-
"""OpenID support for Relying Parties (aka Consumers).

This module documents the main interface with the OpenID consumer
library.  The only part of the library which has to be used and isn't
documented in full here is the store required to create an
C{L{Consumer}} instance.  More on the abstract store type and
concrete implementations of it that are provided in the documentation
for the C{L{__init__<Consumer.__init__>}} method of the
C{L{Consumer}} class.


OVERVIEW
========

    The OpenID identity verification process most commonly uses the
    following steps, as visible to the user of this library:

        1. The user enters their OpenID into a field on the consumer's
           site, and hits a login button.

        2. The consumer site discovers the user's OpenID provider using
           the Yadis protocol.

        3. The consumer site sends the browser a redirect to the
           OpenID provider.  This is the authentication request as
           described in the OpenID specification.

        4. The OpenID provider's site sends the browser a redirect
           back to the consumer site.  This redirect contains the
           provider's response to the authentication request.

    The most important part of the flow to note is the consumer's site
    must handle two separate HTTP requests in order to perform the
    full identity check.


LIBRARY DESIGN
==============

    This consumer library is designed with that flow in mind.  The
    goal is to make it as easy as possible to perform the above steps
    securely.

    At a high level, there are two important parts in the consumer
    library.  The first important part is this module, which contains
    the interface to actually use this library.  The second is the
    C{L{openid.store.interface}} module, which describes the
    interface to use if you need to create a custom method for storing
    the state this library needs to maintain between requests.

    In general, the second part is less important for users of the
    library to know about, as several implementations are provided
    which cover a wide variety of situations in which consumers may
    use the library.

    This module contains a class, C{L{Consumer}}, with methods
    corresponding to the actions necessary in each of steps 2, 3, and
    4 described in the overview.  Use of this library should be as easy
    as creating an C{L{Consumer}} instance and calling the methods
    appropriate for the action the site wants to take.


SESSIONS, STORES, AND STATELESS MODE
====================================

    The C{L{Consumer}} object keeps track of two types of state:

        1. State of the user's current authentication attempt.  Things like
           the identity URL, the list of endpoints discovered for that
           URL, and in case where some endpoints are unreachable, the list
           of endpoints already tried.  This state needs to be held from
           Consumer.begin() to Consumer.complete(), but it is only applicable
           to a single session with a single user agent, and at the end of
           the authentication process (i.e. when an OP replies with either
           C{id_res} or C{cancel}) it may be discarded.

        2. State of relationships with servers, i.e. shared secrets
           (associations) with servers and nonces seen on signed messages.
           This information should persist from one session to the next and
           should not be bound to a particular user-agent.


    These two types of storage are reflected in the first two arguments of
    Consumer's constructor, C{session} and C{store}.  C{session} is a
    dict-like object and we hope your web framework provides you with one
    of these bound to the user agent.  C{store} is an instance of
    L{openid.store.interface.OpenIDStore}.

    Since the store does hold secrets shared between your application and the
    OpenID provider, you should be careful about how you use it in a shared
    hosting environment.  If the filesystem or database permissions of your
    web host allow strangers to read from them, do not store your data there!
    If you have no safe place to store your data, construct your consumer
    with C{None} for the store, and it will operate only in stateless mode.
    Stateless mode may be slower, put more load on the OpenID provider, and
    trusts the provider to keep you safe from replay attacks.


    Several store implementation are provided, and the interface is
    fully documented so that custom stores can be used as well.  See
    the documentation for the C{L{Consumer}} class for more
    information on the interface for stores.  The implementations that
    are provided allow the consumer site to store the necessary data
    in several different ways, including several SQL databases and
    normal files on disk.


IMMEDIATE MODE
==============

    In the flow described above, the user may need to confirm to the
    OpenID provider that it's ok to disclose his or her identity.
    The provider may draw pages asking for information from the user
    before it redirects the browser back to the consumer's site.  This
    is generally transparent to the consumer site, so it is typically
    ignored as an implementation detail.

    There can be times, however, where the consumer site wants to get
    a response immediately.  When this is the case, the consumer can
    put the library in immediate mode.  In immediate mode, there is an
    extra response possible from the server, which is essentially the
    server reporting that it doesn't have enough information to answer
    the question yet.


USING THIS LIBRARY
==================

    Integrating this library into an application is usually a
    relatively straightforward process.  The process should basically
    follow this plan:

    Add an OpenID login field somewhere on your site.  When an OpenID
    is entered in that field and the form is submitted, it should make
    a request to the your site which includes that OpenID URL.

    First, the application should L{instantiate a Consumer<Consumer.__init__>}
    with a session for per-user state and store for shared state.
    using the store of choice.

    Next, the application should call the 'C{L{begin<Consumer.begin>}}' method on the
    C{L{Consumer}} instance.  This method takes the OpenID URL.  The
    C{L{begin<Consumer.begin>}} method returns an C{L{AuthRequest}}
    object.

    Next, the application should call the
    C{L{redirectURL<AuthRequest.redirectURL>}} method on the
    C{L{AuthRequest}} object.  The parameter C{return_to} is the URL
    that the OpenID server will send the user back to after attempting
    to verify his or her identity.  The C{realm} parameter is the
    URL (or URL pattern) that identifies your web site to the user
    when he or she is authorizing it.  Send a redirect to the
    resulting URL to the user's browser.

    That's the first half of the authentication process.  The second
    half of the process is done after the user's OpenID Provider sends the
    user's browser a redirect back to your site to complete their
    login.

    When that happens, the user will contact your site at the URL
    given as the C{return_to} URL to the
    C{L{redirectURL<AuthRequest.redirectURL>}} call made
    above.  The request will have several query parameters added to
    the URL by the OpenID provider as the information necessary to
    finish the request.

    Get an C{L{Consumer}} instance with the same session and store as
    before and call its C{L{complete<Consumer.complete>}} method,
    passing in all the received query arguments.

    There are multiple possible return types possible from that
    method. These indicate the whether or not the login was
    successful, and include any additional information appropriate for
    their type.

@var SUCCESS: constant used as the status for
    L{SuccessResponse<openid.consumer.consumer.SuccessResponse>} objects.

@var FAILURE: constant used as the status for
    L{FailureResponse<openid.consumer.consumer.FailureResponse>} objects.

@var CANCEL: constant used as the status for
    L{CancelResponse<openid.consumer.consumer.CancelResponse>} objects.

@var SETUP_NEEDED: constant used as the status for
    L{SetupNeededResponse<openid.consumer.consumer.SetupNeededResponse>}
    objects.
"""

import cgi
import copy
from urlparse import urlparse, urldefrag

from openid import fetchers

from openid.consumer.discover import discover, OpenIDServiceEndpoint, \
     DiscoveryFailure, OPENID_1_0_TYPE, OPENID_1_1_TYPE, OPENID_2_0_TYPE
from openid.message import Message, OPENID_NS, OPENID2_NS, OPENID1_NS, \
     IDENTIFIER_SELECT, no_default, BARE_NS
from openid import cryptutil
from openid import oidutil
from openid.association import Association, default_negotiator, \
     SessionNegotiator
from openid.dh import DiffieHellman
from openid.store.nonce import mkNonce, split as splitNonce
from openid.yadis.manager import Discovery
from openid import urinorm


__all__ = ['AuthRequest', 'Consumer', 'SuccessResponse',
           'SetupNeededResponse', 'CancelResponse', 'FailureResponse',
           'SUCCESS', 'FAILURE', 'CANCEL', 'SETUP_NEEDED',
           ]


def makeKVPost(request_message, server_url):
    """Make a Direct Request to an OpenID Provider and return the
    result as a Message object.

    @raises openid.fetchers.HTTPFetchingError: if an error is
        encountered in making the HTTP post.

    @rtype: L{openid.message.Message}
    """
    # XXX: TESTME
    resp = fetchers.fetch(server_url, body=request_message.toURLEncoded())

    # Process response in separate function that can be shared by async code.
    return _httpResponseToMessage(resp, server_url)


def _httpResponseToMessage(response, server_url):
    """Adapt a POST response to a Message.

    @type response: L{openid.fetchers.HTTPResponse}
    @param response: Result of a POST to an OpenID endpoint.

    @rtype: L{openid.message.Message}

    @raises openid.fetchers.HTTPFetchingError: if the server returned a
        status of other than 200 or 400.

    @raises ServerError: if the server returned an OpenID error.
    """
    # Should this function be named Message.fromHTTPResponse instead?
    response_message = Message.fromKVForm(response.body)
    if response.status == 400:
        raise ServerError.fromMessage(response_message)

    elif response.status not in (200, 206):
        fmt = 'bad status code from server %s: %s'
        error_message = fmt % (server_url, response.status)
        raise fetchers.HTTPFetchingError(error_message)

    return response_message



class Consumer(object):
    """An OpenID consumer implementation that performs discovery and
    does session management.

    @ivar consumer: an instance of an object implementing the OpenID
        protocol, but doing no discovery or session management.

    @type consumer: GenericConsumer

    @ivar session: A dictionary-like object representing the user's
        session data.  This is used for keeping state of the OpenID
        transaction when the user is redirected to the server.

    @cvar session_key_prefix: A string that is prepended to session
        keys to ensure that they are unique. This variable may be
        changed to suit your application.
    """
    session_key_prefix = "_openid_consumer_"

    _token = 'last_token'

    _discover = staticmethod(discover)

    def __init__(self, session, store, consumer_class=None):
        """Initialize a Consumer instance.

        You should create a new instance of the Consumer object with
        every HTTP request that handles OpenID transactions.

        @param session: See L{the session instance variable<openid.consumer.consumer.Consumer.session>}

        @param store: an object that implements the interface in
            C{L{openid.store.interface.OpenIDStore}}.  Several
            implementations are provided, to cover common database
            environments.

        @type store: C{L{openid.store.interface.OpenIDStore}}

        @see: L{openid.store.interface}
        @see: L{openid.store}
        """
        self.session = session
        if consumer_class is None:
            consumer_class = GenericConsumer
        self.consumer = consumer_class(store)
        self._token_key = self.session_key_prefix + self._token

    def begin(self, user_url, anonymous=False):
        """Start the OpenID authentication process. See steps 1-2 in
        the overview at the top of this file.

        @param user_url: Identity URL given by the user. This method
            performs a textual transformation of the URL to try and
            make sure it is normalized. For example, a user_url of
            example.com will be normalized to http://example.com/
            normalizing and resolving any redirects the server might
            issue.

        @type user_url: unicode

        @param anonymous: Whether to make an anonymous request of the OpenID
            provider.  Such a request does not ask for an authorization
            assertion for an OpenID identifier, but may be used with
            extensions to pass other data.  e.g. "I don't care who you are,
            but I'd like to know your time zone."

        @type anonymous: bool

        @returns: An object containing the discovered information will
            be returned, with a method for building a redirect URL to
            the server, as described in step 3 of the overview. This
            object may also be used to add extension arguments to the
            request, using its
            L{addExtensionArg<openid.consumer.consumer.AuthRequest.addExtensionArg>}
            method.

        @returntype: L{AuthRequest<openid.consumer.consumer.AuthRequest>}

        @raises openid.consumer.discover.DiscoveryFailure: when I fail to
            find an OpenID server for this URL.  If the C{yadis} package
            is available, L{openid.consumer.discover.DiscoveryFailure} is
            an alias for C{yadis.discover.DiscoveryFailure}.
        """
        disco = Discovery(self.session, user_url, self.session_key_prefix)
        try:
            service = disco.getNextService(self._discover)
        except fetchers.HTTPFetchingError, why:
            raise DiscoveryFailure(
                'Error fetching XRDS document: %s' % (why[0],), None)

        if service is None:
            raise DiscoveryFailure(
                'No usable OpenID services found for %s' % (user_url,), None)
        else:
            return self.beginWithoutDiscovery(service, anonymous)

    def beginWithoutDiscovery(self, service, anonymous=False):
        """Start OpenID verification without doing OpenID server
        discovery. This method is used internally by Consumer.begin
        after discovery is performed, and exists to provide an
        interface for library users needing to perform their own
        discovery.

        @param service: an OpenID service endpoint descriptor.  This
            object and factories for it are found in the
            L{openid.consumer.discover} module.

        @type service:
            L{OpenIDServiceEndpoint<openid.consumer.discover.OpenIDServiceEndpoint>}

        @returns: an OpenID authentication request object.

        @rtype: L{AuthRequest<openid.consumer.consumer.AuthRequest>}

        @See: Openid.consumer.consumer.Consumer.begin
        @see: openid.consumer.discover
        """
        auth_req = self.consumer.begin(service)
        self.session[self._token_key] = auth_req.endpoint

        try:
            auth_req.setAnonymous(anonymous)
        except ValueError, why:
            raise ProtocolError(str(why))

        return auth_req

    def complete(self, query, current_url):
        """Called to interpret the server's response to an OpenID
        request. It is called in step 4 of the flow described in the
        consumer overview.

        @param query: A dictionary of the query parameters for this
            HTTP request.

        @param current_url: The URL used to invoke the application.
            Extract the URL from your application's web
            request framework and specify it here to have it checked
            against the openid.return_to value in the response.  If
            the return_to URL check fails, the status of the
            completion will be FAILURE.

        @returns: a subclass of Response. The type of response is
            indicated by the status attribute, which will be one of
            SUCCESS, CANCEL, FAILURE, or SETUP_NEEDED.

        @see: L{SuccessResponse<openid.consumer.consumer.SuccessResponse>}
        @see: L{CancelResponse<openid.consumer.consumer.CancelResponse>}
        @see: L{SetupNeededResponse<openid.consumer.consumer.SetupNeededResponse>}
        @see: L{FailureResponse<openid.consumer.consumer.FailureResponse>}
        """

        endpoint = self.session.get(self._token_key)

        message = Message.fromPostArgs(query)
        response = self.consumer.complete(message, endpoint, current_url)

        try:
            del self.session[self._token_key]
        except KeyError:
            pass

        if (response.status in ['success', 'cancel'] and
            response.identity_url is not None):

            disco = Discovery(self.session,
                              response.identity_url,
                              self.session_key_prefix)
            # This is OK to do even if we did not do discovery in
            # the first place.
            disco.cleanup(force=True)

        return response

    def setAssociationPreference(self, association_preferences):
        """Set the order in which association types/sessions should be
        attempted. For instance, to only allow HMAC-SHA256
        associations created with a DH-SHA256 association session:

        >>> consumer.setAssociationPreference([('HMAC-SHA256', 'DH-SHA256')])

        Any association type/association type pair that is not in this
        list will not be attempted at all.

        @param association_preferences: The list of allowed
            (association type, association session type) pairs that
            should be allowed for this consumer to use, in order from
            most preferred to least preferred.
        @type association_preferences: [(str, str)]

        @returns: None

        @see: C{L{openid.association.SessionNegotiator}}
        """
        self.consumer.negotiator = SessionNegotiator(association_preferences)

class DiffieHellmanSHA1ConsumerSession(object):
    session_type = 'DH-SHA1'
    hash_func = staticmethod(cryptutil.sha1)
    secret_size = 20
    allowed_assoc_types = ['HMAC-SHA1']

    def __init__(self, dh=None):
        if dh is None:
            dh = DiffieHellman.fromDefaults()

        self.dh = dh

    def getRequest(self):
        cpub = cryptutil.longToBase64(self.dh.public)

        args = {'dh_consumer_public': cpub}

        if not self.dh.usingDefaultValues():
            args.update({
                'dh_modulus': cryptutil.longToBase64(self.dh.modulus),
                'dh_gen': cryptutil.longToBase64(self.dh.generator),
                })

        return args

    def extractSecret(self, response):
        dh_server_public64 = response.getArg(
            OPENID_NS, 'dh_server_public', no_default)
        enc_mac_key64 = response.getArg(OPENID_NS, 'enc_mac_key', no_default)
        dh_server_public = cryptutil.base64ToLong(dh_server_public64)
        enc_mac_key = oidutil.fromBase64(enc_mac_key64)
        return self.dh.xorSecret(dh_server_public, enc_mac_key, self.hash_func)

class DiffieHellmanSHA256ConsumerSession(DiffieHellmanSHA1ConsumerSession):
    session_type = 'DH-SHA256'
    hash_func = staticmethod(cryptutil.sha256)
    secret_size = 32
    allowed_assoc_types = ['HMAC-SHA256']

class PlainTextConsumerSession(object):
    session_type = 'no-encryption'
    allowed_assoc_types = ['HMAC-SHA1', 'HMAC-SHA256']

    def getRequest(self):
        return {}

    def extractSecret(self, response):
        mac_key64 = response.getArg(OPENID_NS, 'mac_key', no_default)
        return oidutil.fromBase64(mac_key64)

class SetupNeededError(Exception):
    """Internally-used exception that indicates that an immediate-mode
    request cancelled."""
    def __init__(self, user_setup_url=None):
        Exception.__init__(self, user_setup_url)
        self.user_setup_url = user_setup_url

class ProtocolError(ValueError):
    """Exception that indicates that a message violated the
    protocol. It is raised and caught internally to this file."""

class TypeURIMismatch(ProtocolError):
    """A protocol error arising from type URIs mismatching
    """

    def __init__(self, expected, endpoint):
        ProtocolError.__init__(self, expected, endpoint)
        self.expected = expected
        self.endpoint = endpoint

    def __str__(self):
        s = '<%s.%s: Required type %s not found in %s for endpoint %s>' % (
            self.__class__.__module__, self.__class__.__name__,
            self.expected, self.endpoint.type_uris, self.endpoint)
        return s



class ServerError(Exception):
    """Exception that is raised when the server returns a 400 response
    code to a direct request."""

    def __init__(self, error_text, error_code, message):
        Exception.__init__(self, error_text)
        self.error_text = error_text
        self.error_code = error_code
        self.message = message

    def fromMessage(cls, message):
        """Generate a ServerError instance, extracting the error text
        and the error code from the message."""
        error_text = message.getArg(
            OPENID_NS, 'error', '<no error message supplied>')
        error_code = message.getArg(OPENID_NS, 'error_code')
        return cls(error_text, error_code, message)

    fromMessage = classmethod(fromMessage)

class GenericConsumer(object):
    """This is the implementation of the common logic for OpenID
    consumers. It is unaware of the application in which it is
    running.

    @ivar negotiator: An object that controls the kind of associations
        that the consumer makes. It defaults to
        C{L{openid.association.default_negotiator}}. Assign a
        different negotiator to it if you have specific requirements
        for how associations are made.
    @type negotiator: C{L{openid.association.SessionNegotiator}}
    """

    # The name of the query parameter that gets added to the return_to
    # URL when using OpenID1. You can change this value if you want or
    # need a different name, but don't make it start with openid,
    # because it's not a standard protocol thing for OpenID1. For
    # OpenID2, the library will take care of the nonce using standard
    # OpenID query parameter names.
    openid1_nonce_query_arg_name = 'janrain_nonce'

    # Another query parameter that gets added to the return_to for
    # OpenID 1; if the user's session state is lost, use this claimed
    # identifier to do discovery when verifying the response.
    openid1_return_to_identifier_name = 'openid1_claimed_id'

    session_types = {
        'DH-SHA1':DiffieHellmanSHA1ConsumerSession,
        'DH-SHA256':DiffieHellmanSHA256ConsumerSession,
        'no-encryption':PlainTextConsumerSession,
        }

    _discover = staticmethod(discover)

    def __init__(self, store):
        self.store = store
        self.negotiator = default_negotiator.copy()

    def begin(self, service_endpoint):
        """Create an AuthRequest object for the specified
        service_endpoint. This method will create an association if
        necessary."""
        if self.store is None:
            assoc = None
        else:
            assoc = self._getAssociation(service_endpoint)

        request = AuthRequest(service_endpoint, assoc)
        request.return_to_args[self.openid1_nonce_query_arg_name] = mkNonce()

        if request.message.isOpenID1():
            request.return_to_args[self.openid1_return_to_identifier_name] = \
                request.endpoint.claimed_id

        return request

    def complete(self, message, endpoint, return_to):
        """Process the OpenID message, using the specified endpoint
        and return_to URL as context. This method will handle any
        OpenID message that is sent to the return_to URL.
        """
        mode = message.getArg(OPENID_NS, 'mode', '<No mode set>')

        modeMethod = getattr(self, '_complete_' + mode,
                             self._completeInvalid)

        return modeMethod(message, endpoint, return_to)

    def _complete_cancel(self, message, endpoint, _):
        return CancelResponse(endpoint)

    def _complete_error(self, message, endpoint, _):
        error = message.getArg(OPENID_NS, 'error')
        contact = message.getArg(OPENID_NS, 'contact')
        reference = message.getArg(OPENID_NS, 'reference')

        return FailureResponse(endpoint, error, contact=contact,
                               reference=reference)

    def _complete_setup_needed(self, message, endpoint, _):
        if not message.isOpenID2():
            return self._completeInvalid(message, endpoint, _)

        user_setup_url = message.getArg(OPENID2_NS, 'user_setup_url')
        return SetupNeededResponse(endpoint, user_setup_url)

    def _complete_id_res(self, message, endpoint, return_to):
        try:
            self._checkSetupNeeded(message)
        except SetupNeededError, why:
            return SetupNeededResponse(endpoint, why.user_setup_url)
        else:
            try:
                return self._doIdRes(message, endpoint, return_to)
            except (ProtocolError, DiscoveryFailure), why:
                return FailureResponse(endpoint, why[0])

    def _completeInvalid(self, message, endpoint, _):
        mode = message.getArg(OPENID_NS, 'mode', '<No mode set>')
        return FailureResponse(endpoint,
                               'Invalid openid.mode: %r' % (mode,))

    def _checkReturnTo(self, message, return_to):
        """Check an OpenID message and its openid.return_to value
        against a return_to URL from an application.  Return True on
        success, False on failure.
        """
        # Check the openid.return_to args against args in the original
        # message.
        try:
            self._verifyReturnToArgs(message.toPostArgs())
        except ProtocolError, why:
            oidutil.log("Verifying return_to arguments: %s" % (why[0],))
            return False

        # Check the return_to base URL against the one in the message.
        msg_return_to = message.getArg(OPENID_NS, 'return_to')

        # The URL scheme, authority, and path MUST be the same between
        # the two URLs.
        app_parts = urlparse(urinorm.urinorm(return_to))
        msg_parts = urlparse(urinorm.urinorm(msg_return_to))

        # (addressing scheme, network location, path) must be equal in
        # both URLs.
        for part in range(0, 3):
            if app_parts[part] != msg_parts[part]:
                return False

        return True

    _makeKVPost = staticmethod(makeKVPost)

    def _checkSetupNeeded(self, message):
        """Check an id_res message to see if it is a
        checkid_immediate cancel response.

        @raises SetupNeededError: if it is a checkid_immediate cancellation
        """
        # In OpenID 1, we check to see if this is a cancel from
        # immediate mode by the presence of the user_setup_url
        # parameter.
        if message.isOpenID1():
            user_setup_url = message.getArg(OPENID1_NS, 'user_setup_url')
            if user_setup_url is not None:
                raise SetupNeededError(user_setup_url)

    def _doIdRes(self, message, endpoint, return_to):
        """Handle id_res responses that are not cancellations of
        immediate mode requests.

        @param message: the response paramaters.
        @param endpoint: the discovered endpoint object. May be None.

        @raises ProtocolError: If the message contents are not
            well-formed according to the OpenID specification. This
            includes missing fields or not signing fields that should
            be signed.

        @raises DiscoveryFailure: If the subject of the id_res message
            does not match the supplied endpoint, and discovery on the
            identifier in the message fails (this should only happen
            when using OpenID 2)

        @returntype: L{Response}
        """
        # Checks for presence of appropriate fields (and checks
        # signed list fields)
        self._idResCheckForFields(message)

        if not self._checkReturnTo(message, return_to):
            raise ProtocolError(
                "return_to does not match return URL. Expected %r, got %r"
                % (return_to, message.getArg(OPENID_NS, 'return_to')))


        # Verify discovery information:
        endpoint = self._verifyDiscoveryResults(message, endpoint)
        oidutil.log("Received id_res response from %s using association %s" %
                    (endpoint.server_url,
                     message.getArg(OPENID_NS, 'assoc_handle')))

        self._idResCheckSignature(message, endpoint.server_url)

        # Will raise a ProtocolError if the nonce is bad
        self._idResCheckNonce(message, endpoint)

        signed_list_str = message.getArg(OPENID_NS, 'signed', no_default)
        signed_list = signed_list_str.split(',')
        signed_fields = ["openid." + s for s in signed_list]
        return SuccessResponse(endpoint, message, signed_fields)

    def _idResGetNonceOpenID1(self, message, endpoint):
        """Extract the nonce from an OpenID 1 response.  Return the
        nonce from the BARE_NS since we independently check the
        return_to arguments are the same as those in the response
        message.

        See the openid1_nonce_query_arg_name class variable

        @returns: The nonce as a string or None
        """
        return message.getArg(BARE_NS, self.openid1_nonce_query_arg_name)

    def _idResCheckNonce(self, message, endpoint):
        if message.isOpenID1():
            # This indicates that the nonce was generated by the consumer
            nonce = self._idResGetNonceOpenID1(message, endpoint)
            server_url = ''
        else:
            nonce = message.getArg(OPENID2_NS, 'response_nonce')
            server_url = endpoint.server_url

        if nonce is None:
            raise ProtocolError('Nonce missing from response')

        try:
            timestamp, salt = splitNonce(nonce)
        except ValueError, why:
            raise ProtocolError('Malformed nonce: %s' % (why[0],))

        if (self.store is not None and
            not self.store.useNonce(server_url, timestamp, salt)):
            raise ProtocolError('Nonce already used or out of range')

    def _idResCheckSignature(self, message, server_url):
        assoc_handle = message.getArg(OPENID_NS, 'assoc_handle')
        if self.store is None:
            assoc = None
        else:
            assoc = self.store.getAssociation(server_url, assoc_handle)

        if assoc:
            if assoc.getExpiresIn() <= 0:
                # XXX: It might be a good idea sometimes to re-start the
                # authentication with a new association. Doing it
                # automatically opens the possibility for
                # denial-of-service by a server that just returns expired
                # associations (or really short-lived associations)
                raise ProtocolError(
                    'Association with %s expired' % (server_url,))

            if not assoc.checkMessageSignature(message):
                raise ProtocolError('Bad signature')

        else:
            # It's not an association we know about.  Stateless mode is our
            # only possible path for recovery.
            # XXX - async framework will not want to block on this call to
            # _checkAuth.
            if not self._checkAuth(message, server_url):
                raise ProtocolError('Server denied check_authentication')

    def _idResCheckForFields(self, message):
        # XXX: this should be handled by the code that processes the
        # response (that is, if a field is missing, we should not have
        # to explicitly check that it's present, just make sure that
        # the fields are actually being used by the rest of the code
        # in tests). Although, which fields are signed does need to be
        # checked somewhere.
        basic_fields = ['return_to', 'assoc_handle', 'sig', 'signed']
        basic_sig_fields = ['return_to', 'identity']

        require_fields = {
            OPENID2_NS: basic_fields + ['op_endpoint'],
            OPENID1_NS: basic_fields + ['identity'],
            }

        require_sigs = {
            OPENID2_NS: basic_sig_fields + ['response_nonce',
                                            'claimed_id',
                                            'assoc_handle',
                                            'op_endpoint',],
            OPENID1_NS: basic_sig_fields,
            }

        for field in require_fields[message.getOpenIDNamespace()]:
            if not message.hasKey(OPENID_NS, field):
                raise ProtocolError('Missing required field %r' % (field,))

        signed_list_str = message.getArg(OPENID_NS, 'signed', no_default)
        signed_list = signed_list_str.split(',')

        for field in require_sigs[message.getOpenIDNamespace()]:
            # Field is present and not in signed list
            if message.hasKey(OPENID_NS, field) and field not in signed_list:
                raise ProtocolError('"%s" not signed' % (field,))


    def _verifyReturnToArgs(query):
        """Verify that the arguments in the return_to URL are present in this
        response.
        """
        message = Message.fromPostArgs(query)
        return_to = message.getArg(OPENID_NS, 'return_to')

        if return_to is None:
            raise ProtocolError('Response has no return_to')

        parsed_url = urlparse(return_to)
        rt_query = parsed_url[4]
        parsed_args = cgi.parse_qsl(rt_query)

        for rt_key, rt_value in parsed_args:
            try:
                value = query[rt_key]
                if rt_value != value:
                    format = ("parameter %s value %r does not match "
                              "return_to's value %r")
                    raise ProtocolError(format % (rt_key, value, rt_value))
            except KeyError:
                format = "return_to parameter %s absent from query %r"
                raise ProtocolError(format % (rt_key, query))

        # Make sure all non-OpenID arguments in the response are also
        # in the signed return_to.
        bare_args = message.getArgs(BARE_NS)
        for pair in bare_args.iteritems():
            if pair not in parsed_args:
                raise ProtocolError("Parameter %s not in return_to URL" % (pair[0],))

    _verifyReturnToArgs = staticmethod(_verifyReturnToArgs)

    def _verifyDiscoveryResults(self, resp_msg, endpoint=None):
        """
        Extract the information from an OpenID assertion message and
        verify it against the original

        @param endpoint: The endpoint that resulted from doing discovery
        @param resp_msg: The id_res message object

        @returns: the verified endpoint
        """
        if resp_msg.getOpenIDNamespace() == OPENID2_NS:
            return self._verifyDiscoveryResultsOpenID2(resp_msg, endpoint)
        else:
            return self._verifyDiscoveryResultsOpenID1(resp_msg, endpoint)


    def _verifyDiscoveryResultsOpenID2(self, resp_msg, endpoint):
        to_match = OpenIDServiceEndpoint()
        to_match.type_uris = [OPENID_2_0_TYPE]
        to_match.claimed_id = resp_msg.getArg(OPENID2_NS, 'claimed_id')
        to_match.local_id = resp_msg.getArg(OPENID2_NS, 'identity')

        # Raises a KeyError when the op_endpoint is not present
        to_match.server_url = resp_msg.getArg(
            OPENID2_NS, 'op_endpoint', no_default)

        # claimed_id and identifier must both be present or both
        # be absent
        if (to_match.claimed_id is None and
            to_match.local_id is not None):
            raise ProtocolError(
                'openid.identity is present without openid.claimed_id')

        elif (to_match.claimed_id is not None and
              to_match.local_id is None):
            raise ProtocolError(
                'openid.claimed_id is present without openid.identity')

        # This is a response without identifiers, so there's really no
        # checking that we can do, so return an endpoint that's for
        # the specified `openid.op_endpoint'
        elif to_match.claimed_id is None:
            return OpenIDServiceEndpoint.fromOPEndpointURL(to_match.server_url)

        # The claimed ID doesn't match, so we have to do discovery
        # again. This covers not using sessions, OP identifier
        # endpoints and responses that didn't match the original
        # request.
        if not endpoint:
            oidutil.log('No pre-discovered information supplied.')
            endpoint = self._discoverAndVerify(to_match.claimed_id, [to_match])
        else:
            # The claimed ID matches, so we use the endpoint that we
            # discovered in initiation. This should be the most common
            # case.
            try:
                self._verifyDiscoverySingle(endpoint, to_match)
            except ProtocolError, e:
                oidutil.log(
                    "Error attempting to use stored discovery information: " +
                    str(e))
                oidutil.log("Attempting discovery to verify endpoint")
                endpoint = self._discoverAndVerify(
                    to_match.claimed_id, [to_match])

        # The endpoint we return should have the claimed ID from the
        # message we just verified, fragment and all.
        if endpoint.claimed_id != to_match.claimed_id:
            endpoint = copy.copy(endpoint)
            endpoint.claimed_id = to_match.claimed_id
        return endpoint

    def _verifyDiscoveryResultsOpenID1(self, resp_msg, endpoint):
        claimed_id = resp_msg.getArg(BARE_NS, self.openid1_return_to_identifier_name)

        if endpoint is None and claimed_id is None:
            raise RuntimeError(
                'When using OpenID 1, the claimed ID must be supplied, '
                'either by passing it through as a return_to parameter '
                'or by using a session, and supplied to the GenericConsumer '
                'as the argument to complete()')
        elif endpoint is not None and claimed_id is None:
            claimed_id = endpoint.claimed_id

        to_match = OpenIDServiceEndpoint()
        to_match.type_uris = [OPENID_1_1_TYPE]
        to_match.local_id = resp_msg.getArg(OPENID1_NS, 'identity')
        # Restore delegate information from the initiation phase
        to_match.claimed_id = claimed_id

        if to_match.local_id is None:
            raise ProtocolError('Missing required field openid.identity')

        to_match_1_0 = copy.copy(to_match)
        to_match_1_0.type_uris = [OPENID_1_0_TYPE]

        if endpoint is not None:
            try:
                try:
                    self._verifyDiscoverySingle(endpoint, to_match)
                except TypeURIMismatch:
                    self._verifyDiscoverySingle(endpoint, to_match_1_0)
            except ProtocolError, e:
                oidutil.log("Error attempting to use stored discovery information: " +
                            str(e))
                oidutil.log("Attempting discovery to verify endpoint")
            else:
                return endpoint

        # Endpoint is either bad (failed verification) or None
        return self._discoverAndVerify(claimed_id, [to_match, to_match_1_0])

    def _verifyDiscoverySingle(self, endpoint, to_match):
        """Verify that the given endpoint matches the information
        extracted from the OpenID assertion, and raise an exception if
        there is a mismatch.

        @type endpoint: openid.consumer.discover.OpenIDServiceEndpoint
        @type to_match: openid.consumer.discover.OpenIDServiceEndpoint

        @rtype: NoneType

        @raises ProtocolError: when the endpoint does not match the
            discovered information.
        """
        # Every type URI that's in the to_match endpoint has to be
        # present in the discovered endpoint.
        for type_uri in to_match.type_uris:
            if not endpoint.usesExtension(type_uri):
                raise TypeURIMismatch(type_uri, endpoint)

        # Fragments do not influence discovery, so we can't compare a
        # claimed identifier with a fragment to discovered information.
        defragged_claimed_id, _ = urldefrag(to_match.claimed_id)
        if defragged_claimed_id != endpoint.claimed_id:
            raise ProtocolError(
                'Claimed ID does not match (different subjects!), '
                'Expected %s, got %s' %
                (defragged_claimed_id, endpoint.claimed_id))

        if to_match.getLocalID() != endpoint.getLocalID():
            raise ProtocolError('local_id mismatch. Expected %s, got %s' %
                                (to_match.getLocalID(), endpoint.getLocalID()))

        # If the server URL is None, this must be an OpenID 1
        # response, because op_endpoint is a required parameter in
        # OpenID 2. In that case, we don't actually care what the
        # discovered server_url is, because signature checking or
        # check_auth should take care of that check for us.
        if to_match.server_url is None:
            assert to_match.preferredNamespace() == OPENID1_NS, (
                """The code calling this must ensure that OpenID 2
                responses have a non-none `openid.op_endpoint' and
                that it is set as the `server_url' attribute of the
                `to_match' endpoint.""")

        elif to_match.server_url != endpoint.server_url:
            raise ProtocolError('OP Endpoint mismatch. Expected %s, got %s' %
                                (to_match.server_url, endpoint.server_url))

    def _discoverAndVerify(self, claimed_id, to_match_endpoints):
        """Given an endpoint object created from the information in an
        OpenID response, perform discovery and verify the discovery
        results, returning the matching endpoint that is the result of
        doing that discovery.

        @type to_match: openid.consumer.discover.OpenIDServiceEndpoint
        @param to_match: The endpoint whose information we're confirming

        @rtype: openid.consumer.discover.OpenIDServiceEndpoint
        @returns: The result of performing discovery on the claimed
            identifier in `to_match'

        @raises DiscoveryFailure: when discovery fails.
        """
        oidutil.log('Performing discovery on %s' % (claimed_id,))
        _, services = self._discover(claimed_id)
        if not services:
            raise DiscoveryFailure('No OpenID information found at %s' %
                                   (claimed_id,), None)
        return self._verifyDiscoveredServices(claimed_id, services,
                                              to_match_endpoints)


    def _verifyDiscoveredServices(self, claimed_id, services, to_match_endpoints):
        """See @L{_discoverAndVerify}"""

        # Search the services resulting from discovery to find one
        # that matches the information from the assertion
        failure_messages = []
        for endpoint in services:
            for to_match_endpoint in to_match_endpoints:
                try:
                    self._verifyDiscoverySingle(
                        endpoint, to_match_endpoint)
                except ProtocolError, why:
                    failure_messages.append(str(why))
                else:
                    # It matches, so discover verification has
                    # succeeded. Return this endpoint.
                    return endpoint
        else:
            oidutil.log('Discovery verification failure for %s' %
                        (claimed_id,))
            for failure_message in failure_messages:
                oidutil.log(' * Endpoint mismatch: ' + failure_message)

            raise DiscoveryFailure(
                'No matching endpoint found after discovering %s'
                % (claimed_id,), None)

    def _checkAuth(self, message, server_url):
        """Make a check_authentication request to verify this message.

        @returns: True if the request is valid.
        @rtype: bool
        """
        oidutil.log('Using OpenID check_authentication')
        request = self._createCheckAuthRequest(message)
        if request is None:
            return False
        try:
            response = self._makeKVPost(request, server_url)
        except (fetchers.HTTPFetchingError, ServerError), e:
            oidutil.log('check_authentication failed: %s' % (e[0],))
            return False
        else:
            return self._processCheckAuthResponse(response, server_url)

    def _createCheckAuthRequest(self, message):
        """Generate a check_authentication request message given an
        id_res message.
        """
        signed = message.getArg(OPENID_NS, 'signed')
        if signed:
            for k in signed.split(','):
                oidutil.log(k)
                val = message.getAliasedArg(k)

                # Signed value is missing
                if val is None:
                    oidutil.log('Missing signed field %r' % (k,))
                    return None

        check_auth_message = message.copy()
        check_auth_message.setArg(OPENID_NS, 'mode', 'check_authentication')
        return check_auth_message

    def _processCheckAuthResponse(self, response, server_url):
        """Process the response message from a check_authentication
        request, invalidating associations if requested.
        """
        is_valid = response.getArg(OPENID_NS, 'is_valid', 'false')

        invalidate_handle = response.getArg(OPENID_NS, 'invalidate_handle')
        if invalidate_handle is not None:
            oidutil.log(
                'Received "invalidate_handle" from server %s' % (server_url,))
            if self.store is None:
                oidutil.log('Unexpectedly got invalidate_handle without '
                            'a store!')
            else:
                self.store.removeAssociation(server_url, invalidate_handle)

        if is_valid == 'true':
            return True
        else:
            oidutil.log('Server responds that checkAuth call is not valid')
            return False

    def _getAssociation(self, endpoint):
        """Get an association for the endpoint's server_url.

        First try seeing if we have a good association in the
        store. If we do not, then attempt to negotiate an association
        with the server.

        If we negotiate a good association, it will get stored.

        @returns: A valid association for the endpoint's server_url or None
        @rtype: openid.association.Association or NoneType
        """
        assoc = self.store.getAssociation(endpoint.server_url)

        if assoc is None or assoc.expiresIn <= 0:
            assoc = self._negotiateAssociation(endpoint)
            if assoc is not None:
                self.store.storeAssociation(endpoint.server_url, assoc)

        return assoc

    def _negotiateAssociation(self, endpoint):
        """Make association requests to the server, attempting to
        create a new association.

        @returns: a new association object

        @rtype: L{openid.association.Association}
        """
        # Get our preferred session/association type from the negotiatior.
        assoc_type, session_type = self.negotiator.getAllowedType()

        try:
            assoc = self._requestAssociation(
                endpoint, assoc_type, session_type)
        except ServerError, why:
            supportedTypes = self._extractSupportedAssociationType(why,
                                                                   endpoint,
                                                                   assoc_type)
            if supportedTypes is not None:
                assoc_type, session_type = supportedTypes
                # Attempt to create an association from the assoc_type
                # and session_type that the server told us it
                # supported.
                try:
                    assoc = self._requestAssociation(
                        endpoint, assoc_type, session_type)
                except ServerError, why:
                    # Do not keep trying, since it rejected the
                    # association type that it told us to use.
                    oidutil.log('Server %s refused its suggested association '
                                'type: session_type=%s, assoc_type=%s'
                                % (endpoint.server_url, session_type,
                                   assoc_type))
                    return None
                else:
                    return assoc
        else:
            return assoc

    def _extractSupportedAssociationType(self, server_error, endpoint,
                                         assoc_type):
        """Handle ServerErrors resulting from association requests.

        @returns: If server replied with an C{unsupported-type} error,
            return a tuple of supported C{association_type}, C{session_type}.
            Otherwise logs the error and returns None.
        @rtype: tuple or None
        """
        # Any error message whose code is not 'unsupported-type'
        # should be considered a total failure.
        if server_error.error_code != 'unsupported-type' or \
               server_error.message.isOpenID1():
            oidutil.log(
                'Server error when requesting an association from %r: %s'
                % (endpoint.server_url, server_error.error_text))
            return None

        # The server didn't like the association/session type
        # that we sent, and it sent us back a message that
        # might tell us how to handle it.
        oidutil.log(
            'Unsupported association type %s: %s' % (assoc_type,
                                                     server_error.error_text,))

        # Extract the session_type and assoc_type from the
        # error message
        assoc_type = server_error.message.getArg(OPENID_NS, 'assoc_type')
        session_type = server_error.message.getArg(OPENID_NS, 'session_type')

        if assoc_type is None or session_type is None:
            oidutil.log('Server responded with unsupported association '
                        'session but did not supply a fallback.')
            return None
        elif not self.negotiator.isAllowed(assoc_type, session_type):
            fmt = ('Server sent unsupported session/association type: '
                   'session_type=%s, assoc_type=%s')
            oidutil.log(fmt % (session_type, assoc_type))
            return None
        else:
            return assoc_type, session_type


    def _requestAssociation(self, endpoint, assoc_type, session_type):
        """Make and process one association request to this endpoint's
        OP endpoint URL.

        @returns: An association object or None if the association
            processing failed.

        @raises ServerError: when the remote OpenID server returns an error.
        """
        assoc_session, args = self._createAssociateRequest(
            endpoint, assoc_type, session_type)

        try:
            response = self._makeKVPost(args, endpoint.server_url)
        except fetchers.HTTPFetchingError, why:
            oidutil.log('openid.associate request failed: %s' % (why[0],))
            return None

        try:
            assoc = self._extractAssociation(response, assoc_session)
        except KeyError, why:
            oidutil.log('Missing required parameter in response from %s: %s'
                        % (endpoint.server_url, why[0]))
            return None
        except ProtocolError, why:
            oidutil.log('Protocol error parsing response from %s: %s' % (
                endpoint.server_url, why[0]))
            return None
        else:
            return assoc

    def _createAssociateRequest(self, endpoint, assoc_type, session_type):
        """Create an association request for the given assoc_type and
        session_type.

        @param endpoint: The endpoint whose server_url will be
            queried. The important bit about the endpoint is whether
            it's in compatiblity mode (OpenID 1.1)

        @param assoc_type: The association type that the request
            should ask for.
        @type assoc_type: str

        @param session_type: The session type that should be used in
            the association request. The session_type is used to
            create an association session object, and that session
            object is asked for any additional fields that it needs to
            add to the request.
        @type session_type: str

        @returns: a pair of the association session object and the
            request message that will be sent to the server.
        @rtype: (association session type (depends on session_type),
                 openid.message.Message)
        """
        session_type_class = self.session_types[session_type]
        assoc_session = session_type_class()

        args = {
            'mode': 'associate',
            'assoc_type': assoc_type,
            }

        if not endpoint.compatibilityMode():
            args['ns'] = OPENID2_NS

        # Leave out the session type if we're in compatibility mode
        # *and* it's no-encryption.
        if (not endpoint.compatibilityMode() or
            assoc_session.session_type != 'no-encryption'):
            args['session_type'] = assoc_session.session_type

        args.update(assoc_session.getRequest())
        message = Message.fromOpenIDArgs(args)
        return assoc_session, message

    def _getOpenID1SessionType(self, assoc_response):
        """Given an association response message, extract the OpenID
        1.X session type.

        This function mostly takes care of the 'no-encryption' default
        behavior in OpenID 1.

        If the association type is plain-text, this function will
        return 'no-encryption'

        @returns: The association type for this message
        @rtype: str

        @raises KeyError: when the session_type field is absent.
        """
        # If it's an OpenID 1 message, allow session_type to default
        # to None (which signifies "no-encryption")
        session_type = assoc_response.getArg(OPENID1_NS, 'session_type')

        # Handle the differences between no-encryption association
        # respones in OpenID 1 and 2:

        # no-encryption is not really a valid session type for
        # OpenID 1, but we'll accept it anyway, while issuing a
        # warning.
        if session_type == 'no-encryption':
            oidutil.log('WARNING: OpenID server sent "no-encryption"'
                        'for OpenID 1.X')

        # Missing or empty session type is the way to flag a
        # 'no-encryption' response. Change the session type to
        # 'no-encryption' so that it can be handled in the same
        # way as OpenID 2 'no-encryption' respones.
        elif session_type == '' or session_type is None:
            session_type = 'no-encryption'

        return session_type

    def _extractAssociation(self, assoc_response, assoc_session):
        """Attempt to extract an association from the response, given
        the association response message and the established
        association session.

        @param assoc_response: The association response message from
            the server
        @type assoc_response: openid.message.Message

        @param assoc_session: The association session object that was
            used when making the request
        @type assoc_session: depends on the session type of the request

        @raises ProtocolError: when data is malformed
        @raises KeyError: when a field is missing

        @rtype: openid.association.Association
        """
        # Extract the common fields from the response, raising an
        # exception if they are not found
        assoc_type = assoc_response.getArg(
            OPENID_NS, 'assoc_type', no_default)
        assoc_handle = assoc_response.getArg(
            OPENID_NS, 'assoc_handle', no_default)

        # expires_in is a base-10 string. The Python parsing will
        # accept literals that have whitespace around them and will
        # accept negative values. Neither of these are really in-spec,
        # but we think it's OK to accept them.
        expires_in_str = assoc_response.getArg(
            OPENID_NS, 'expires_in', no_default)
        try:
            expires_in = int(expires_in_str)
        except ValueError, why:
            raise ProtocolError('Invalid expires_in field: %s' % (why[0],))

        # OpenID 1 has funny association session behaviour.
        if assoc_response.isOpenID1():
            session_type = self._getOpenID1SessionType(assoc_response)
        else:
            session_type = assoc_response.getArg(
                OPENID2_NS, 'session_type', no_default)

        # Session type mismatch
        if assoc_session.session_type != session_type:
            if (assoc_response.isOpenID1() and
                session_type == 'no-encryption'):
                # In OpenID 1, any association request can result in a
                # 'no-encryption' association response. Setting
                # assoc_session to a new no-encryption session should
                # make the rest of this function work properly for
                # that case.
                assoc_session = PlainTextConsumerSession()
            else:
                # Any other mismatch, regardless of protocol version
                # results in the failure of the association session
                # altogether.
                fmt = 'Session type mismatch. Expected %r, got %r'
                message = fmt % (assoc_session.session_type, session_type)
                raise ProtocolError(message)

        # Make sure assoc_type is valid for session_type
        if assoc_type not in assoc_session.allowed_assoc_types:
            fmt = 'Unsupported assoc_type for session %s returned: %s'
            raise ProtocolError(fmt % (assoc_session.session_type, assoc_type))

        # Delegate to the association session to extract the secret
        # from the response, however is appropriate for that session
        # type.
        try:
            secret = assoc_session.extractSecret(assoc_response)
        except ValueError, why:
            fmt = 'Malformed response for %s session: %s'
            raise ProtocolError(fmt % (assoc_session.session_type, why[0]))

        return Association.fromExpiresIn(
            expires_in, assoc_handle, secret, assoc_type)

class AuthRequest(object):
    """An object that holds the state necessary for generating an
    OpenID authentication request. This object holds the association
    with the server and the discovered information with which the
    request will be made.

    It is separate from the consumer because you may wish to add
    things to the request before sending it on its way to the
    server. It also has serialization options that let you encode the
    authentication request as a URL or as a form POST.
    """

    def __init__(self, endpoint, assoc):
        """
        Creates a new AuthRequest object.  This just stores each
        argument in an appropriately named field.

        Users of this library should not create instances of this
        class.  Instances of this class are created by the library
        when needed.
        """
        self.assoc = assoc
        self.endpoint = endpoint
        self.return_to_args = {}
        self.message = Message(endpoint.preferredNamespace())
        self._anonymous = False

    def setAnonymous(self, is_anonymous):
        """Set whether this request should be made anonymously. If a
        request is anonymous, the identifier will not be sent in the
        request. This is only useful if you are making another kind of
        request with an extension in this request.

        Anonymous requests are not allowed when the request is made
        with OpenID 1.

        @raises ValueError: when attempting to set an OpenID1 request
            as anonymous
        """
        if is_anonymous and self.message.isOpenID1():
            raise ValueError('OpenID 1 requests MUST include the '
                             'identifier in the request')
        else:
            self._anonymous = is_anonymous

    def addExtension(self, extension_request):
        """Add an extension to this checkid request.

        @param extension_request: An object that implements the
            extension interface for adding arguments to an OpenID
            message.
        """
        extension_request.toMessage(self.message)

    def addExtensionArg(self, namespace, key, value):
        """Add an extension argument to this OpenID authentication
        request.

        Use caution when adding arguments, because they will be
        URL-escaped and appended to the redirect URL, which can easily
        get quite long.

        @param namespace: The namespace for the extension. For
            example, the simple registration extension uses the
            namespace C{sreg}.

        @type namespace: str

        @param key: The key within the extension namespace. For
            example, the nickname field in the simple registration
            extension's key is C{nickname}.

        @type key: str

        @param value: The value to provide to the server for this
            argument.

        @type value: str
        """
        self.message.setArg(namespace, key, value)

    def getMessage(self, realm, return_to=None, immediate=False):
        """Produce a L{openid.message.Message} representing this request.

        @param realm: The URL (or URL pattern) that identifies your
            web site to the user when she is authorizing it.

        @type realm: str

        @param return_to: The URL that the OpenID provider will send the
            user back to after attempting to verify her identity.

            Not specifying a return_to URL means that the user will not
            be returned to the site issuing the request upon its
            completion.

        @type return_to: str

        @param immediate: If True, the OpenID provider is to send back
            a response immediately, useful for behind-the-scenes
            authentication attempts.  Otherwise the OpenID provider
            may engage the user before providing a response.  This is
            the default case, as the user may need to provide
            credentials or approve the request before a positive
            response can be sent.

        @type immediate: bool

        @returntype: L{openid.message.Message}
        """
        if return_to:
            return_to = oidutil.appendArgs(return_to, self.return_to_args)
        elif immediate:
            raise ValueError(
                '"return_to" is mandatory when using "checkid_immediate"')
        elif self.message.isOpenID1():
            raise ValueError('"return_to" is mandatory for OpenID 1 requests')
        elif self.return_to_args:
            raise ValueError('extra "return_to" arguments were specified, '
                             'but no return_to was specified')

        if immediate:
            mode = 'checkid_immediate'
        else:
            mode = 'checkid_setup'

        message = self.message.copy()
        if message.isOpenID1():
            realm_key = 'trust_root'
        else:
            realm_key = 'realm'

        message.updateArgs(OPENID_NS,
            {
            realm_key:realm,
            'mode':mode,
            'return_to':return_to,
            })

        if not self._anonymous:
            if self.endpoint.isOPIdentifier():
                # This will never happen when we're in compatibility
                # mode, as long as isOPIdentifier() returns False
                # whenever preferredNamespace() returns OPENID1_NS.
                claimed_id = request_identity = IDENTIFIER_SELECT
            else:
                request_identity = self.endpoint.getLocalID()
                claimed_id = self.endpoint.claimed_id

            # This is true for both OpenID 1 and 2
            message.setArg(OPENID_NS, 'identity', request_identity)

            if message.isOpenID2():
                message.setArg(OPENID2_NS, 'claimed_id', claimed_id)

        if self.assoc:
            message.setArg(OPENID_NS, 'assoc_handle', self.assoc.handle)
            assoc_log_msg = 'with assocication %s' % (self.assoc.handle,)
        else:
            assoc_log_msg = 'using stateless mode.'

        oidutil.log("Generated %s request to %s %s" %
                    (mode, self.endpoint.server_url, assoc_log_msg))

        return message

    def redirectURL(self, realm, return_to=None, immediate=False):
        """Returns a URL with an encoded OpenID request.

        The resulting URL is the OpenID provider's endpoint URL with
        parameters appended as query arguments.  You should redirect
        the user agent to this URL.

        OpenID 2.0 endpoints also accept POST requests, see
        C{L{shouldSendRedirect}} and C{L{formMarkup}}.

        @param realm: The URL (or URL pattern) that identifies your
            web site to the user when she is authorizing it.

        @type realm: str

        @param return_to: The URL that the OpenID provider will send the
            user back to after attempting to verify her identity.

            Not specifying a return_to URL means that the user will not
            be returned to the site issuing the request upon its
            completion.

        @type return_to: str

        @param immediate: If True, the OpenID provider is to send back
            a response immediately, useful for behind-the-scenes
            authentication attempts.  Otherwise the OpenID provider
            may engage the user before providing a response.  This is
            the default case, as the user may need to provide
            credentials or approve the request before a positive
            response can be sent.

        @type immediate: bool

        @returns: The URL to redirect the user agent to.

        @returntype: str
        """
        message = self.getMessage(realm, return_to, immediate)
        return message.toURL(self.endpoint.server_url)

    def formMarkup(self, realm, return_to=None, immediate=False,
            form_tag_attrs=None):
        """Get html for a form to submit this request to the IDP.

        @param form_tag_attrs: Dictionary of attributes to be added to
            the form tag. 'accept-charset' and 'enctype' have defaults
            that can be overridden. If a value is supplied for
            'action' or 'method', it will be replaced.
        @type form_tag_attrs: {unicode: unicode}
        """
        message = self.getMessage(realm, return_to, immediate)
        return message.toFormMarkup(self.endpoint.server_url,
                    form_tag_attrs)

    def htmlMarkup(self, realm, return_to=None, immediate=False,
            form_tag_attrs=None):
        """Get an autosubmitting HTML page that submits this request to the
        IDP.  This is just a wrapper for formMarkup.

        @see: formMarkup

        @returns: str
        """
        return oidutil.autoSubmitHTML(self.formMarkup(realm, 
                                                      return_to,
                                                      immediate, 
                                                      form_tag_attrs))

    def shouldSendRedirect(self):
        """Should this OpenID authentication request be sent as a HTTP
        redirect or as a POST (form submission)?

        @rtype: bool
        """
        return self.endpoint.compatibilityMode()

FAILURE = 'failure'
SUCCESS = 'success'
CANCEL = 'cancel'
SETUP_NEEDED = 'setup_needed'

class Response(object):
    status = None

    def setEndpoint(self, endpoint):
        self.endpoint = endpoint
        if endpoint is None:
            self.identity_url = None
        else:
            self.identity_url = endpoint.claimed_id

    def getDisplayIdentifier(self):
        """Return the display identifier for this response.

        The display identifier is related to the Claimed Identifier, but the
        two are not always identical.  The display identifier is something the
        user should recognize as what they entered, whereas the response's
        claimed identifier (in the L{identity_url} attribute) may have extra
        information for better persistence.

        URLs will be stripped of their fragments for display.  XRIs will
        display the human-readable identifier (i-name) instead of the
        persistent identifier (i-number).

        Use the display identifier in your user interface.  Use
        L{identity_url} for querying your database or authorization server.
        """
        if self.endpoint is not None:
            return self.endpoint.getDisplayIdentifier()
        return None

class SuccessResponse(Response):
    """A response with a status of SUCCESS. Indicates that this request is a
    successful acknowledgement from the OpenID server that the
    supplied URL is, indeed controlled by the requesting agent.

    @ivar identity_url: The identity URL that has been authenticated; the Claimed Identifier.
        See also L{getDisplayIdentifier}.

    @ivar endpoint: The endpoint that authenticated the identifier.  You
        may access other discovered information related to this endpoint,
        such as the CanonicalID of an XRI, through this object.
    @type endpoint: L{OpenIDServiceEndpoint<openid.consumer.discover.OpenIDServiceEndpoint>}

    @ivar signed_fields: The arguments in the server's response that
        were signed and verified.

    @cvar status: SUCCESS
    """

    status = SUCCESS

    def __init__(self, endpoint, message, signed_fields=None):
        # Don't use setEndpoint, because endpoint should never be None
        # for a successfull transaction.
        self.endpoint = endpoint
        self.identity_url = endpoint.claimed_id

        self.message = message

        if signed_fields is None:
            signed_fields = []
        self.signed_fields = signed_fields

    def isOpenID1(self):
        """Was this authentication response an OpenID 1 authentication
        response?
        """
        return self.message.isOpenID1()

    def isSigned(self, ns_uri, ns_key):
        """Return whether a particular key is signed, regardless of
        its namespace alias
        """
        return self.message.getKey(ns_uri, ns_key) in self.signed_fields

    def getSigned(self, ns_uri, ns_key, default=None):
        """Return the specified signed field if available,
        otherwise return default
        """
        if self.isSigned(ns_uri, ns_key):
            return self.message.getArg(ns_uri, ns_key, default)
        else:
            return default

    def getSignedNS(self, ns_uri):
        """Get signed arguments from the response message.  Return a
        dict of all arguments in the specified namespace.  If any of
        the arguments are not signed, return None.
        """
        msg_args = self.message.getArgs(ns_uri)

        for key in msg_args.iterkeys():
            if not self.isSigned(ns_uri, key):
                oidutil.log("SuccessResponse.getSignedNS: (%s, %s) not signed."
                            % (ns_uri, key))
                return None

        return msg_args

    def extensionResponse(self, namespace_uri, require_signed):
        """Return response arguments in the specified namespace.

        @param namespace_uri: The namespace URI of the arguments to be
        returned.

        @param require_signed: True if the arguments should be among
        those signed in the response, False if you don't care.

        If require_signed is True and the arguments are not signed,
        return None.
        """
        if require_signed:
            return self.getSignedNS(namespace_uri)
        else:
            return self.message.getArgs(namespace_uri)

    def getReturnTo(self):
        """Get the openid.return_to argument from this response.

        This is useful for verifying that this request was initiated
        by this consumer.

        @returns: The return_to URL supplied to the server on the
            initial request, or C{None} if the response did not contain
            an C{openid.return_to} argument.

        @returntype: str
        """
        return self.getSigned(OPENID_NS, 'return_to')

    def __eq__(self, other):
        return (
            (self.endpoint == other.endpoint) and
            (self.identity_url == other.identity_url) and
            (self.message == other.message) and
            (self.signed_fields == other.signed_fields) and
            (self.status == other.status))

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return '<%s.%s id=%r signed=%r>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.identity_url, self.signed_fields)


class FailureResponse(Response):
    """A response with a status of FAILURE. Indicates that the OpenID
    protocol has failed. This could be locally or remotely triggered.

    @ivar identity_url:  The identity URL for which authenitcation was
        attempted, if it can be determined. Otherwise, None.

    @ivar message: A message indicating why the request failed, if one
        is supplied. otherwise, None.

    @cvar status: FAILURE
    """

    status = FAILURE

    def __init__(self, endpoint, message=None, contact=None,
                 reference=None):
        self.setEndpoint(endpoint)
        self.message = message
        self.contact = contact
        self.reference = reference

    def __repr__(self):
        return "<%s.%s id=%r message=%r>" % (
            self.__class__.__module__, self.__class__.__name__,
            self.identity_url, self.message)


class CancelResponse(Response):
    """A response with a status of CANCEL. Indicates that the user
    cancelled the OpenID authentication request.

    @ivar identity_url: The identity URL for which authenitcation was
        attempted, if it can be determined. Otherwise, None.

    @cvar status: CANCEL
    """

    status = CANCEL

    def __init__(self, endpoint):
        self.setEndpoint(endpoint)

class SetupNeededResponse(Response):
    """A response with a status of SETUP_NEEDED. Indicates that the
    request was in immediate mode, and the server is unable to
    authenticate the user without further interaction.

    @ivar identity_url:  The identity URL for which authenitcation was
        attempted.

    @ivar setup_url: A URL that can be used to send the user to the
        server to set up for authentication. The user should be
        redirected in to the setup_url, either in the current window
        or in a new browser window.  C{None} in OpenID 2.0.

    @cvar status: SETUP_NEEDED
    """

    status = SETUP_NEEDED

    def __init__(self, endpoint, setup_url=None):
        self.setEndpoint(endpoint)
        self.setup_url = setup_url

########NEW FILE########
__FILENAME__ = discover
# -*- test-case-name: openid.test.test_discover -*-
"""Functions to discover OpenID endpoints from identifiers.
"""

__all__ = [
    'DiscoveryFailure',
    'OPENID_1_0_NS',
    'OPENID_1_0_TYPE',
    'OPENID_1_1_TYPE',
    'OPENID_2_0_TYPE',
    'OPENID_IDP_2_0_TYPE',
    'OpenIDServiceEndpoint',
    'discover',
    ]

import urlparse

from openid import oidutil, fetchers, urinorm

from openid import yadis
from openid.yadis.etxrd import nsTag, XRDSError, XRD_NS_2_0
from openid.yadis.services import applyFilter as extractServices
from openid.yadis.discover import discover as yadisDiscover
from openid.yadis.discover import DiscoveryFailure
from openid.yadis import xrires, filters
from openid.yadis import xri

from openid.consumer import html_parse

OPENID_1_0_NS = 'http://openid.net/xmlns/1.0'
OPENID_IDP_2_0_TYPE = 'http://specs.openid.net/auth/2.0/server'
OPENID_2_0_TYPE = 'http://specs.openid.net/auth/2.0/signon'
OPENID_1_1_TYPE = 'http://openid.net/signon/1.1'
OPENID_1_0_TYPE = 'http://openid.net/signon/1.0'

from openid.message import OPENID1_NS as OPENID_1_0_MESSAGE_NS
from openid.message import OPENID2_NS as OPENID_2_0_MESSAGE_NS

class OpenIDServiceEndpoint(object):
    """Object representing an OpenID service endpoint.

    @ivar identity_url: the verified identifier.
    @ivar canonicalID: For XRI, the persistent identifier.
    """

    # OpenID service type URIs, listed in order of preference.  The
    # ordering of this list affects yadis and XRI service discovery.
    openid_type_uris = [
        OPENID_IDP_2_0_TYPE,

        OPENID_2_0_TYPE,
        OPENID_1_1_TYPE,
        OPENID_1_0_TYPE,
        ]

    def __init__(self):
        self.claimed_id = None
        self.server_url = None
        self.type_uris = []
        self.local_id = None
        self.canonicalID = None
        self.used_yadis = False # whether this came from an XRDS
        self.display_identifier = None

    def usesExtension(self, extension_uri):
        return extension_uri in self.type_uris

    def preferredNamespace(self):
        if (OPENID_IDP_2_0_TYPE in self.type_uris or
            OPENID_2_0_TYPE in self.type_uris):
            return OPENID_2_0_MESSAGE_NS
        else:
            return OPENID_1_0_MESSAGE_NS

    def supportsType(self, type_uri):
        """Does this endpoint support this type?

        I consider C{/server} endpoints to implicitly support C{/signon}.
        """
        return (
            (type_uri in self.type_uris) or 
            (type_uri == OPENID_2_0_TYPE and self.isOPIdentifier())
            )

    def getDisplayIdentifier(self):
        """Return the display_identifier if set, else return the claimed_id.
        """
        if self.display_identifier is not None:
            return self.display_identifier
        if self.claimed_id is None:
            return None
        else:
            return urlparse.urldefrag(self.claimed_id)[0]

    def compatibilityMode(self):
        return self.preferredNamespace() != OPENID_2_0_MESSAGE_NS

    def isOPIdentifier(self):
        return OPENID_IDP_2_0_TYPE in self.type_uris

    def parseService(self, yadis_url, uri, type_uris, service_element):
        """Set the state of this object based on the contents of the
        service element."""
        self.type_uris = type_uris
        self.server_url = uri
        self.used_yadis = True

        if not self.isOPIdentifier():
            # XXX: This has crappy implications for Service elements
            # that contain both 'server' and 'signon' Types.  But
            # that's a pathological configuration anyway, so I don't
            # think I care.
            self.local_id = findOPLocalIdentifier(service_element,
                                                  self.type_uris)
            self.claimed_id = yadis_url

    def getLocalID(self):
        """Return the identifier that should be sent as the
        openid.identity parameter to the server."""
        # I looked at this conditional and thought "ah-hah! there's the bug!"
        # but Python actually makes that one big expression somehow, i.e.
        # "x is x is x" is not the same thing as "(x is x) is x".
        # That's pretty weird, dude.  -- kmt, 1/07
        if (self.local_id is self.canonicalID is None):
            return self.claimed_id
        else:
            return self.local_id or self.canonicalID

    def fromBasicServiceEndpoint(cls, endpoint):
        """Create a new instance of this class from the endpoint
        object passed in.

        @return: None or OpenIDServiceEndpoint for this endpoint object"""
        type_uris = endpoint.matchTypes(cls.openid_type_uris)

        # If any Type URIs match and there is an endpoint URI
        # specified, then this is an OpenID endpoint
        if type_uris and endpoint.uri is not None:
            openid_endpoint = cls()
            openid_endpoint.parseService(
                endpoint.yadis_url,
                endpoint.uri,
                endpoint.type_uris,
                endpoint.service_element)
        else:
            openid_endpoint = None

        return openid_endpoint

    fromBasicServiceEndpoint = classmethod(fromBasicServiceEndpoint)

    def fromHTML(cls, uri, html):
        """Parse the given document as HTML looking for an OpenID <link
        rel=...>

        @rtype: [OpenIDServiceEndpoint]
        """
        discovery_types = [
            (OPENID_2_0_TYPE, 'openid2.provider', 'openid2.local_id'),
            (OPENID_1_1_TYPE, 'openid.server', 'openid.delegate'),
            ]

        link_attrs = html_parse.parseLinkAttrs(html)
        services = []
        for type_uri, op_endpoint_rel, local_id_rel in discovery_types:
            op_endpoint_url = html_parse.findFirstHref(
                link_attrs, op_endpoint_rel)
            if op_endpoint_url is None:
                continue

            service = cls()
            service.claimed_id = uri
            service.local_id = html_parse.findFirstHref(
                link_attrs, local_id_rel)
            service.server_url = op_endpoint_url
            service.type_uris = [type_uri]

            services.append(service)

        return services

    fromHTML = classmethod(fromHTML)


    def fromXRDS(cls, uri, xrds):
        """Parse the given document as XRDS looking for OpenID services.

        @rtype: [OpenIDServiceEndpoint]

        @raises XRDSError: When the XRDS does not parse.

        @since: 2.1.0
        """
        return extractServices(uri, xrds, cls)

    fromXRDS = classmethod(fromXRDS)


    def fromDiscoveryResult(cls, discoveryResult):
        """Create endpoints from a DiscoveryResult.

        @type discoveryResult: L{DiscoveryResult}

        @rtype: list of L{OpenIDServiceEndpoint}

        @raises XRDSError: When the XRDS does not parse.

        @since: 2.1.0
        """
        if discoveryResult.isXRDS():
            method = cls.fromXRDS
        else:
            method = cls.fromHTML
        return method(discoveryResult.normalized_uri,
                      discoveryResult.response_text)

    fromDiscoveryResult = classmethod(fromDiscoveryResult)


    def fromOPEndpointURL(cls, op_endpoint_url):
        """Construct an OP-Identifier OpenIDServiceEndpoint object for
        a given OP Endpoint URL

        @param op_endpoint_url: The URL of the endpoint
        @rtype: OpenIDServiceEndpoint
        """
        service = cls()
        service.server_url = op_endpoint_url
        service.type_uris = [OPENID_IDP_2_0_TYPE]
        return service

    fromOPEndpointURL = classmethod(fromOPEndpointURL)


    def __str__(self):
        return ("<%s.%s "
                "server_url=%r "
                "claimed_id=%r "
                "local_id=%r "
                "canonicalID=%r "
                "used_yadis=%s "
                ">"
                 % (self.__class__.__module__, self.__class__.__name__,
                    self.server_url,
                    self.claimed_id,
                    self.local_id,
                    self.canonicalID,
                    self.used_yadis))



def findOPLocalIdentifier(service_element, type_uris):
    """Find the OP-Local Identifier for this xrd:Service element.

    This considers openid:Delegate to be a synonym for xrd:LocalID if
    both OpenID 1.X and OpenID 2.0 types are present. If only OpenID
    1.X is present, it returns the value of openid:Delegate. If only
    OpenID 2.0 is present, it returns the value of xrd:LocalID. If
    there is more than one LocalID tag and the values are different,
    it raises a DiscoveryFailure. This is also triggered when the
    xrd:LocalID and openid:Delegate tags are different.

    @param service_element: The xrd:Service element
    @type service_element: ElementTree.Node

    @param type_uris: The xrd:Type values present in this service
        element. This function could extract them, but higher level
        code needs to do that anyway.
    @type type_uris: [str]

    @raises DiscoveryFailure: when discovery fails.

    @returns: The OP-Local Identifier for this service element, if one
        is present, or None otherwise.
    @rtype: str or unicode or NoneType
    """
    # XXX: Test this function on its own!

    # Build the list of tags that could contain the OP-Local Identifier
    local_id_tags = []
    if (OPENID_1_1_TYPE in type_uris or
        OPENID_1_0_TYPE in type_uris):
        local_id_tags.append(nsTag(OPENID_1_0_NS, 'Delegate'))

    if OPENID_2_0_TYPE in type_uris:
        local_id_tags.append(nsTag(XRD_NS_2_0, 'LocalID'))

    # Walk through all the matching tags and make sure that they all
    # have the same value
    local_id = None
    for local_id_tag in local_id_tags:
        for local_id_element in service_element.findall(local_id_tag):
            if local_id is None:
                local_id = local_id_element.text
            elif local_id != local_id_element.text:
                format = 'More than one %r tag found in one service element'
                message = format % (local_id_tag,)
                raise DiscoveryFailure(message, None)

    return local_id

def normalizeURL(url):
    """Normalize a URL, converting normalization failures to
    DiscoveryFailure"""
    try:
        normalized = urinorm.urinorm(url)
    except ValueError, why:
        raise DiscoveryFailure('Normalizing identifier: %s' % (why[0],), None)
    else:
        return urlparse.urldefrag(normalized)[0]

def normalizeXRI(xri):
    """Normalize an XRI, stripping its scheme if present"""
    if xri.startswith("xri://"):
        xri = xri[6:]
    return xri

def arrangeByType(service_list, preferred_types):
    """Rearrange service_list in a new list so services are ordered by
    types listed in preferred_types.  Return the new list."""

    def enumerate(elts):
        """Return an iterable that pairs the index of an element with
        that element.

        For Python 2.2 compatibility"""
        return zip(range(len(elts)), elts)

    def bestMatchingService(service):
        """Return the index of the first matching type, or something
        higher if no type matches.

        This provides an ordering in which service elements that
        contain a type that comes earlier in the preferred types list
        come before service elements that come later. If a service
        element has more than one type, the most preferred one wins.
        """
        for i, t in enumerate(preferred_types):
            if preferred_types[i] in service.type_uris:
                return i

        return len(preferred_types)

    # Build a list with the service elements in tuples whose
    # comparison will prefer the one with the best matching service
    prio_services = [(bestMatchingService(s), orig_index, s)
                     for (orig_index, s) in enumerate(service_list)]
    prio_services.sort()

    # Now that the services are sorted by priority, remove the sort
    # keys from the list.
    for i in range(len(prio_services)):
        prio_services[i] = prio_services[i][2]

    return prio_services

def getOPOrUserServices(openid_services):
    """Extract OP Identifier services.  If none found, return the
    rest, sorted with most preferred first according to
    OpenIDServiceEndpoint.openid_type_uris.

    openid_services is a list of OpenIDServiceEndpoint objects.

    Returns a list of OpenIDServiceEndpoint objects."""

    op_services = arrangeByType(openid_services, [OPENID_IDP_2_0_TYPE])

    openid_services = arrangeByType(openid_services,
                                    OpenIDServiceEndpoint.openid_type_uris)

    return op_services or openid_services

def discoverYadis(uri):
    """Discover OpenID services for a URI. Tries Yadis and falls back
    on old-style <link rel='...'> discovery if Yadis fails.

    @param uri: normalized identity URL
    @type uri: str

    @return: (claimed_id, services)
    @rtype: (str, list(OpenIDServiceEndpoint))

    @raises DiscoveryFailure: when discovery fails.
    """
    # Might raise a yadis.discover.DiscoveryFailure if no document
    # came back for that URI at all.  I don't think falling back
    # to OpenID 1.0 discovery on the same URL will help, so don't
    # bother to catch it.
    response = yadisDiscover(uri)

    yadis_url = response.normalized_uri
    body = response.response_text
    try:
        openid_services = OpenIDServiceEndpoint.fromXRDS(yadis_url, body)
    except XRDSError:
        # Does not parse as a Yadis XRDS file
        openid_services = []

    if not openid_services:
        # Either not an XRDS or there are no OpenID services.

        if response.isXRDS():
            # if we got the Yadis content-type or followed the Yadis
            # header, re-fetch the document without following the Yadis
            # header, with no Accept header.
            return discoverNoYadis(uri)

        # Try to parse the response as HTML.
        # <link rel="...">
        openid_services = OpenIDServiceEndpoint.fromHTML(yadis_url, body)

    return (yadis_url, getOPOrUserServices(openid_services))

def discoverXRI(iname):
    endpoints = []
    iname = normalizeXRI(iname)
    try:
        canonicalID, services = xrires.ProxyResolver().query(
            iname, OpenIDServiceEndpoint.openid_type_uris)

        if canonicalID is None:
            raise XRDSError('No CanonicalID found for XRI %r' % (iname,))

        flt = filters.mkFilter(OpenIDServiceEndpoint)
        for service_element in services:
            endpoints.extend(flt.getServiceEndpoints(iname, service_element))
    except XRDSError:
        oidutil.log('xrds error on ' + iname)

    for endpoint in endpoints:
        # Is there a way to pass this through the filter to the endpoint
        # constructor instead of tacking it on after?
        endpoint.canonicalID = canonicalID
        endpoint.claimed_id = canonicalID
        endpoint.display_identifier = iname

    # FIXME: returned xri should probably be in some normal form
    return iname, getOPOrUserServices(endpoints)


def discoverNoYadis(uri):
    http_resp = fetchers.fetch(uri)
    if http_resp.status not in (200, 206):
        raise DiscoveryFailure(
            'HTTP Response status from identity URL host is not 200. '
            'Got status %r' % (http_resp.status,), http_resp)

    claimed_id = http_resp.final_url
    openid_services = OpenIDServiceEndpoint.fromHTML(
        claimed_id, http_resp.body)
    return claimed_id, openid_services

def discoverURI(uri):
    parsed = urlparse.urlparse(uri)
    if parsed[0] and parsed[1]:
        if parsed[0] not in ['http', 'https']:
            raise DiscoveryFailure('URI scheme is not HTTP or HTTPS', None)
    else:
        uri = 'http://' + uri

    uri = normalizeURL(uri)
    claimed_id, openid_services = discoverYadis(uri)
    claimed_id = normalizeURL(claimed_id)
    return claimed_id, openid_services

def discover(identifier):
    if xri.identifierScheme(identifier) == "XRI":
        return discoverXRI(identifier)
    else:
        return discoverURI(identifier)

########NEW FILE########
__FILENAME__ = html_parse
"""
This module implements a VERY limited parser that finds <link> tags in
the head of HTML or XHTML documents and parses out their attributes
according to the OpenID spec. It is a liberal parser, but it requires
these things from the data in order to work:

 - There must be an open <html> tag

 - There must be an open <head> tag inside of the <html> tag

 - Only <link>s that are found inside of the <head> tag are parsed
   (this is by design)

 - The parser follows the OpenID specification in resolving the
   attributes of the link tags. This means that the attributes DO NOT
   get resolved as they would by an XML or HTML parser. In particular,
   only certain entities get replaced, and href attributes do not get
   resolved relative to a base URL.

From http://openid.net/specs.bml#linkrel:

 - The openid.server URL MUST be an absolute URL. OpenID consumers
   MUST NOT attempt to resolve relative URLs.

 - The openid.server URL MUST NOT include entities other than &amp;,
   &lt;, &gt;, and &quot;.

The parser ignores SGML comments and <![CDATA[blocks]]>. Both kinds of
quoting are allowed for attributes.

The parser deals with invalid markup in these ways:

 - Tag names are not case-sensitive

 - The <html> tag is accepted even when it is not at the top level

 - The <head> tag is accepted even when it is not a direct child of
   the <html> tag, but a <html> tag must be an ancestor of the <head>
   tag

 - <link> tags are accepted even when they are not direct children of
   the <head> tag, but a <head> tag must be an ancestor of the <link>
   tag

 - If there is no closing tag for an open <html> or <head> tag, the
   remainder of the document is viewed as being inside of the tag. If
   there is no closing tag for a <link> tag, the link tag is treated
   as a short tag. Exceptions to this rule are that <html> closes
   <html> and <body> or <head> closes <head>

 - Attributes of the <link> tag are not required to be quoted.

 - In the case of duplicated attribute names, the attribute coming
   last in the tag will be the value returned.

 - Any text that does not parse as an attribute within a link tag will
   be ignored. (e.g. <link pumpkin rel='openid.server' /> will ignore
   pumpkin)

 - If there are more than one <html> or <head> tag, the parser only
   looks inside of the first one.

 - The contents of <script> tags are ignored entirely, except unclosed
   <script> tags. Unclosed <script> tags are ignored.

 - Any other invalid markup is ignored, including unclosed SGML
   comments and unclosed <![CDATA[blocks.
"""

__all__ = ['parseLinkAttrs']

import re

flags = ( re.DOTALL # Match newlines with '.'
        | re.IGNORECASE
        | re.VERBOSE # Allow comments and whitespace in patterns
        | re.UNICODE # Make \b respect Unicode word boundaries
        )

# Stuff to remove before we start looking for tags
removed_re = re.compile(r'''
  # Comments
  <!--.*?-->

  # CDATA blocks
| <!\[CDATA\[.*?\]\]>

  # script blocks
| <script\b

  # make sure script is not an XML namespace
  (?!:)

  [^>]*>.*?</script>

''', flags)

tag_expr = r'''
# Starts with the tag name at a word boundary, where the tag name is
# not a namespace
<%(tag_name)s\b(?!:)

# All of the stuff up to a ">", hopefully attributes.
(?P<attrs>[^>]*?)

(?: # Match a short tag
    />

|   # Match a full tag
    >

    (?P<contents>.*?)

    # Closed by
    (?: # One of the specified close tags
        </?%(closers)s\s*>

        # End of the string
    |   \Z

    )

)
'''

def tagMatcher(tag_name, *close_tags):
    if close_tags:
        options = '|'.join((tag_name,) + close_tags)
        closers = '(?:%s)' % (options,)
    else:
        closers = tag_name

    expr = tag_expr % locals()
    return re.compile(expr, flags)

# Must contain at least an open html and an open head tag
html_find = tagMatcher('html')
head_find = tagMatcher('head', 'body')
link_find = re.compile(r'<link\b(?!:)', flags)

attr_find = re.compile(r'''
# Must start with a sequence of word-characters, followed by an equals sign
(?P<attr_name>\w+)=

# Then either a quoted or unquoted attribute
(?:

 # Match everything that\'s between matching quote marks
 (?P<qopen>["\'])(?P<q_val>.*?)(?P=qopen)
|

 # If the value is not quoted, match up to whitespace
 (?P<unq_val>(?:[^\s<>/]|/(?!>))+)
)

|

(?P<end_link>[<>])
''', flags)

# Entity replacement:
replacements = {
    'amp':'&',
    'lt':'<',
    'gt':'>',
    'quot':'"',
    }

ent_replace = re.compile(r'&(%s);' % '|'.join(replacements.keys()))
def replaceEnt(mo):
    "Replace the entities that are specified by OpenID"
    return replacements.get(mo.group(1), mo.group())

def parseLinkAttrs(html):
    """Find all link tags in a string representing a HTML document and
    return a list of their attributes.

    @param html: the text to parse
    @type html: str or unicode

    @return: A list of dictionaries of attributes, one for each link tag
    @rtype: [[(type(html), type(html))]]
    """
    stripped = removed_re.sub('', html)
    html_mo = html_find.search(stripped)
    if html_mo is None or html_mo.start('contents') == -1:
        return []

    start, end = html_mo.span('contents')
    head_mo = head_find.search(stripped, start, end)
    if head_mo is None or head_mo.start('contents') == -1:
        return []

    start, end = head_mo.span('contents')
    link_mos = link_find.finditer(stripped, head_mo.start(), head_mo.end())

    matches = []
    for link_mo in link_mos:
        start = link_mo.start() + 5
        link_attrs = {}
        for attr_mo in attr_find.finditer(stripped, start):
            if attr_mo.lastgroup == 'end_link':
                break

            # Either q_val or unq_val must be present, but not both
            # unq_val is a True (non-empty) value if it is present
            attr_name, q_val, unq_val = attr_mo.group(
                'attr_name', 'q_val', 'unq_val')
            attr_val = ent_replace.sub(replaceEnt, unq_val or q_val)

            link_attrs[attr_name] = attr_val

        matches.append(link_attrs)

    return matches

def relMatches(rel_attr, target_rel):
    """Does this target_rel appear in the rel_str?"""
    # XXX: TESTME
    rels = rel_attr.strip().split()
    for rel in rels:
        rel = rel.lower()
        if rel == target_rel:
            return 1

    return 0

def linkHasRel(link_attrs, target_rel):
    """Does this link have target_rel as a relationship?"""
    # XXX: TESTME
    rel_attr = link_attrs.get('rel')
    return rel_attr and relMatches(rel_attr, target_rel)

def findLinksRel(link_attrs_list, target_rel):
    """Filter the list of link attributes on whether it has target_rel
    as a relationship."""
    # XXX: TESTME
    matchesTarget = lambda attrs: linkHasRel(attrs, target_rel)
    return filter(matchesTarget, link_attrs_list)

def findFirstHref(link_attrs_list, target_rel):
    """Return the value of the href attribute for the first link tag
    in the list that has target_rel as a relationship."""
    # XXX: TESTME
    matches = findLinksRel(link_attrs_list, target_rel)
    if not matches:
        return None
    first = matches[0]
    return first.get('href')

########NEW FILE########
__FILENAME__ = cryptutil
"""Module containing a cryptographic-quality source of randomness and
other cryptographically useful functionality

Python 2.4 needs no external support for this module, nor does Python
2.3 on a system with /dev/urandom.

Other configurations will need a quality source of random bytes and
access to a function that will convert binary strings to long
integers. This module will work with the Python Cryptography Toolkit
(pycrypto) if it is present. pycrypto can be found with a search
engine, but is currently found at:

http://www.amk.ca/python/code/crypto
"""

__all__ = [
    'base64ToLong',
    'binaryToLong',
    'hmacSha1',
    'hmacSha256',
    'longToBase64',
    'longToBinary',
    'randomString',
    'randrange',
    'sha1',
    'sha256',
    ]

import hmac
import os
import random

from openid.oidutil import toBase64, fromBase64

try:
    import hashlib
except ImportError:
    import sha as sha1_module

    try:
        from Crypto.Hash import SHA256 as sha256_module
    except ImportError:
        sha256_module = None

else:
    class HashContainer(object):
        def __init__(self, hash_constructor):
            self.new = hash_constructor
            self.digest_size = hash_constructor().digest_size

    sha1_module = HashContainer(hashlib.sha1)
    sha256_module = HashContainer(hashlib.sha256)

def hmacSha1(key, text):
    return hmac.new(key, text, sha1_module).digest()

def sha1(s):
    return sha1_module.new(s).digest()

if sha256_module is not None:
    def hmacSha256(key, text):
        return hmac.new(key, text, sha256_module).digest()

    def sha256(s):
        return sha256_module.new(s).digest()

    SHA256_AVAILABLE = True

else:
    _no_sha256 = NotImplementedError(
        'Use Python 2.5, install pycrypto or install hashlib to use SHA256')

    def hmacSha256(unused_key, unused_text):
        raise _no_sha256

    def sha256(s):
        raise _no_sha256

    SHA256_AVAILABLE = False

try:
    from Crypto.Util.number import long_to_bytes, bytes_to_long
except ImportError:
    import pickle
    try:
        # Check Python compatiblity by raising an exception on import
        # if the needed functionality is not present. Present in
        # Python >= 2.3
        pickle.encode_long
        pickle.decode_long
    except AttributeError:
        raise ImportError(
            'No functionality for serializing long integers found')

    # Present in Python >= 2.4
    try:
        reversed
    except NameError:
        def reversed(seq):
            return map(seq.__getitem__, xrange(len(seq) - 1, -1, -1))

    def longToBinary(l):
        if l == 0:
            return '\x00'

        return ''.join(reversed(pickle.encode_long(l)))

    def binaryToLong(s):
        return pickle.decode_long(''.join(reversed(s)))
else:
    # We have pycrypto

    def longToBinary(l):
        if l < 0:
            raise ValueError('This function only supports positive integers')

        bytes = long_to_bytes(l)
        if ord(bytes[0]) > 127:
            return '\x00' + bytes
        else:
            return bytes

    def binaryToLong(bytes):
        if not bytes:
            raise ValueError('Empty string passed to strToLong')

        if ord(bytes[0]) > 127:
            raise ValueError('This function only supports positive integers')

        return bytes_to_long(bytes)

# A cryptographically safe source of random bytes
try:
    getBytes = os.urandom
except AttributeError:
    try:
        from Crypto.Util.randpool import RandomPool
    except ImportError:
        # Fall back on /dev/urandom, if present. It would be nice to
        # have Windows equivalent here, but for now, require pycrypto
        # on Windows.
        try:
            _urandom = file('/dev/urandom', 'rb')
        except IOError:
            raise ImportError('No adequate source of randomness found!')
        else:
            def getBytes(n):
                bytes = []
                while n:
                    chunk = _urandom.read(n)
                    n -= len(chunk)
                    bytes.append(chunk)
                    assert n >= 0
                return ''.join(bytes)
    else:
        _pool = RandomPool()
        def getBytes(n, pool=_pool):
            if pool.entropy < n:
                pool.randomize()
            return pool.get_bytes(n)

# A randrange function that works for longs
try:
    randrange = random.SystemRandom().randrange
except AttributeError:
    # In Python 2.2's random.Random, randrange does not support
    # numbers larger than sys.maxint for randrange. For simplicity,
    # use this implementation for any Python that does not have
    # random.SystemRandom
    from math import log, ceil

    _duplicate_cache = {}
    def randrange(start, stop=None, step=1):
        if stop is None:
            stop = start
            start = 0

        r = (stop - start) // step
        try:
            (duplicate, nbytes) = _duplicate_cache[r]
        except KeyError:
            rbytes = longToBinary(r)
            if rbytes[0] == '\x00':
                nbytes = len(rbytes) - 1
            else:
                nbytes = len(rbytes)

            mxrand = (256 ** nbytes)

            # If we get a number less than this, then it is in the
            # duplicated range.
            duplicate = mxrand % r

            if len(_duplicate_cache) > 10:
                _duplicate_cache.clear()

            _duplicate_cache[r] = (duplicate, nbytes)

        while 1:
            bytes = '\x00' + getBytes(nbytes)
            n = binaryToLong(bytes)
            # Keep looping if this value is in the low duplicated range
            if n >= duplicate:
                break

        return start + (n % r) * step

def longToBase64(l):
    return toBase64(longToBinary(l))

def base64ToLong(s):
    return binaryToLong(fromBase64(s))

def randomString(length, chrs=None):
    """Produce a string of length random bytes, chosen from chrs."""
    if chrs is None:
        return getBytes(length)
    else:
        n = len(chrs)
        return ''.join([chrs[randrange(n)] for _ in xrange(length)])

########NEW FILE########
__FILENAME__ = dh
from openid import cryptutil
from openid import oidutil

def strxor(x, y):
    if len(x) != len(y):
        raise ValueError('Inputs to strxor must have the same length')

    xor = lambda (a, b): chr(ord(a) ^ ord(b))
    return "".join(map(xor, zip(x, y)))

class DiffieHellman(object):
    DEFAULT_MOD = 155172898181473697471232257763715539915724801966915404479707795314057629378541917580651227423698188993727816152646631438561595825688188889951272158842675419950341258706556549803580104870537681476726513255747040765857479291291572334510643245094715007229621094194349783925984760375594985848253359305585439638443L

    DEFAULT_GEN = 2

    def fromDefaults(cls):
        return cls(cls.DEFAULT_MOD, cls.DEFAULT_GEN)

    fromDefaults = classmethod(fromDefaults)

    def __init__(self, modulus, generator):
        self.modulus = long(modulus)
        self.generator = long(generator)

        self._setPrivate(cryptutil.randrange(1, modulus - 1))

    def _setPrivate(self, private):
        """This is here to make testing easier"""
        self.private = private
        self.public = pow(self.generator, self.private, self.modulus)

    def usingDefaultValues(self):
        return (self.modulus == self.DEFAULT_MOD and
                self.generator == self.DEFAULT_GEN)

    def getSharedSecret(self, composite):
        return pow(composite, self.private, self.modulus)

    def xorSecret(self, composite, secret, hash_func):
        dh_shared = self.getSharedSecret(composite)
        hashed_dh_shared = hash_func(cryptutil.longToBinary(dh_shared))
        return strxor(secret, hashed_dh_shared)

########NEW FILE########
__FILENAME__ = extension
from openid import message as message_module

class Extension(object):
    """An interface for OpenID extensions.

    @ivar ns_uri: The namespace to which to add the arguments for this
        extension
    """
    ns_uri = None
    ns_alias = None

    def getExtensionArgs(self):
        """Get the string arguments that should be added to an OpenID
        message for this extension.

        @returns: A dictionary of completely non-namespaced arguments
            to be added. For example, if the extension's alias is
            'uncle', and this method returns {'meat':'Hot Rats'}, the
            final message will contain {'openid.uncle.meat':'Hot Rats'}
        """
        raise NotImplementedError

    def toMessage(self, message=None):
        """Add the arguments from this extension to the provided
        message, or create a new message containing only those
        arguments.

        @returns: The message with the extension arguments added
        """
        if message is None:
            warnings.warn('Passing None to Extension.toMessage is deprecated. '
                          'Creating a message assuming you want OpenID 2.',
                          DeprecationWarning, stacklevel=2)
            message = message_module.Message(message_module.OPENID2_NS)

        implicit = message.isOpenID1()

        try:
            message.namespaces.addAlias(self.ns_uri, self.ns_alias,
                                        implicit=implicit)
        except KeyError:
            if message.namespaces.getAlias(self.ns_uri) != self.ns_alias:
                raise

        message.updateArgs(self.ns_uri, self.getExtensionArgs())
        return message

########NEW FILE########
__FILENAME__ = ax
# -*- test-case-name: openid.test.test_ax -*-
"""Implements the OpenID Attribute Exchange specification, version 1.0.

@since: 2.1.0
"""

__all__ = [
    'AttributeRequest',
    'FetchRequest',
    'FetchResponse',
    'StoreRequest',
    'StoreResponse',
    ]

from openid import extension
from openid.server.trustroot import TrustRoot
from openid.message import NamespaceMap, OPENID_NS

# Use this as the 'count' value for an attribute in a FetchRequest to
# ask for as many values as the OP can provide.
UNLIMITED_VALUES = "unlimited"

# Minimum supported alias length in characters.  Here for
# completeness.
MINIMUM_SUPPORTED_ALIAS_LENGTH = 32

def checkAlias(alias):
    """
    Check an alias for invalid characters; raise AXError if any are
    found.  Return None if the alias is valid.
    """
    if ',' in alias:
        raise AXError("Alias %r must not contain comma" % (alias,))
    if '.' in alias:
        raise AXError("Alias %r must not contain period" % (alias,))


class AXError(ValueError):
    """Results from data that does not meet the attribute exchange 1.0
    specification"""


class NotAXMessage(AXError):
    """Raised when there is no Attribute Exchange mode in the message."""

    def __repr__(self):
        return self.__class__.__name__

    def __str__(self):
        return self.__class__.__name__


class AXMessage(extension.Extension):
    """Abstract class containing common code for attribute exchange messages

    @cvar ns_alias: The preferred namespace alias for attribute
        exchange messages

    @cvar mode: The type of this attribute exchange message. This must
        be overridden in subclasses.
    """

    # This class is abstract, so it's OK that it doesn't override the
    # abstract method in Extension:
    #
    #pylint:disable-msg=W0223

    ns_alias = 'ax'
    mode = None
    ns_uri = 'http://openid.net/srv/ax/1.0'

    def _checkMode(self, ax_args):
        """Raise an exception if the mode in the attribute exchange
        arguments does not match what is expected for this class.

        @raises NotAXMessage: When there is no mode value in ax_args at all.

        @raises AXError: When mode does not match.
        """
        mode = ax_args.get('mode')
        if mode != self.mode:
            if not mode:
                raise NotAXMessage()
            else:
                raise AXError(
                    'Expected mode %r; got %r' % (self.mode, mode))

    def _newArgs(self):
        """Return a set of attribute exchange arguments containing the
        basic information that must be in every attribute exchange
        message.
        """
        return {'mode':self.mode}


class AttrInfo(object):
    """Represents a single attribute in an attribute exchange
    request. This should be added to an AXRequest object in order to
    request the attribute.

    @ivar required: Whether the attribute will be marked as required
        when presented to the subject of the attribute exchange
        request.
    @type required: bool

    @ivar count: How many values of this type to request from the
        subject. Defaults to one.
    @type count: int

    @ivar type_uri: The identifier that determines what the attribute
        represents and how it is serialized. For example, one type URI
        representing dates could represent a Unix timestamp in base 10
        and another could represent a human-readable string.
    @type type_uri: str

    @ivar alias: The name that should be given to this alias in the
        request. If it is not supplied, a generic name will be
        assigned. For example, if you want to call a Unix timestamp
        value 'tstamp', set its alias to that value. If two attributes
        in the same message request to use the same alias, the request
        will fail to be generated.
    @type alias: str or NoneType
    """

    # It's OK that this class doesn't have public methods (it's just a
    # holder for a bunch of attributes):
    #
    #pylint:disable-msg=R0903

    def __init__(self, type_uri, count=1, required=False, alias=None):
        self.required = required
        self.count = count
        self.type_uri = type_uri
        self.alias = alias

        if self.alias is not None:
            checkAlias(self.alias)

    def wantsUnlimitedValues(self):
        """
        When processing a request for this attribute, the OP should
        call this method to determine whether all available attribute
        values were requested.  If self.count == UNLIMITED_VALUES,
        this returns True.  Otherwise this returns False, in which
        case self.count is an integer.
        """
        return self.count == UNLIMITED_VALUES

def toTypeURIs(namespace_map, alias_list_s):
    """Given a namespace mapping and a string containing a
    comma-separated list of namespace aliases, return a list of type
    URIs that correspond to those aliases.

    @param namespace_map: The mapping from namespace URI to alias
    @type namespace_map: openid.message.NamespaceMap

    @param alias_list_s: The string containing the comma-separated
        list of aliases. May also be None for convenience.
    @type alias_list_s: str or NoneType

    @returns: The list of namespace URIs that corresponds to the
        supplied list of aliases. If the string was zero-length or
        None, an empty list will be returned.

    @raise KeyError: If an alias is present in the list of aliases but
        is not present in the namespace map.
    """
    uris = []

    if alias_list_s:
        for alias in alias_list_s.split(','):
            type_uri = namespace_map.getNamespaceURI(alias)
            if type_uri is None:
                raise KeyError(
                    'No type is defined for attribute name %r' % (alias,))
            else:
                uris.append(type_uri)

    return uris


class FetchRequest(AXMessage):
    """An attribute exchange 'fetch_request' message. This message is
    sent by a relying party when it wishes to obtain attributes about
    the subject of an OpenID authentication request.

    @ivar requested_attributes: The attributes that have been
        requested thus far, indexed by the type URI.
    @type requested_attributes: {str:AttrInfo}

    @ivar update_url: A URL that will accept responses for this
        attribute exchange request, even in the absence of the user
        who made this request.
    """
    mode = 'fetch_request'

    def __init__(self, update_url=None):
        AXMessage.__init__(self)
        self.requested_attributes = {}
        self.update_url = update_url

    def add(self, attribute):
        """Add an attribute to this attribute exchange request.

        @param attribute: The attribute that is being requested
        @type attribute: C{L{AttrInfo}}

        @returns: None

        @raise KeyError: when the requested attribute is already
            present in this fetch request.
        """
        if attribute.type_uri in self.requested_attributes:
            raise KeyError('The attribute %r has already been requested'
                           % (attribute.type_uri,))

        self.requested_attributes[attribute.type_uri] = attribute

    def getExtensionArgs(self):
        """Get the serialized form of this attribute fetch request.

        @returns: The fetch request message parameters
        @rtype: {unicode:unicode}
        """
        aliases = NamespaceMap()

        required = []
        if_available = []

        ax_args = self._newArgs()

        for type_uri, attribute in self.requested_attributes.iteritems():
            if attribute.alias is None:
                alias = aliases.add(type_uri)
            else:
                # This will raise an exception when the second
                # attribute with the same alias is added. I think it
                # would be better to complain at the time that the
                # attribute is added to this object so that the code
                # that is adding it is identified in the stack trace,
                # but it's more work to do so, and it won't be 100%
                # accurate anyway, since the attributes are
                # mutable. So for now, just live with the fact that
                # we'll learn about the error later.
                #
                # The other possible approach is to hide the error and
                # generate a new alias on the fly. I think that would
                # probably be bad.
                alias = aliases.addAlias(type_uri, attribute.alias)

            if attribute.required:
                required.append(alias)
            else:
                if_available.append(alias)

            if attribute.count != 1:
                ax_args['count.' + alias] = str(attribute.count)

            ax_args['type.' + alias] = type_uri

        if required:
            ax_args['required'] = ','.join(required)

        if if_available:
            ax_args['if_available'] = ','.join(if_available)

        return ax_args

    def getRequiredAttrs(self):
        """Get the type URIs for all attributes that have been marked
        as required.

        @returns: A list of the type URIs for attributes that have
            been marked as required.
        @rtype: [str]
        """
        required = []
        for type_uri, attribute in self.requested_attributes.iteritems():
            if attribute.required:
                required.append(type_uri)

        return required

    def fromOpenIDRequest(cls, openid_request):
        """Extract a FetchRequest from an OpenID message

        @param openid_request: The OpenID authentication request
            containing the attribute fetch request
        @type openid_request: C{L{openid.server.server.CheckIDRequest}}

        @rtype: C{L{FetchRequest}} or C{None}
        @returns: The FetchRequest extracted from the message or None, if
            the message contained no AX extension.

        @raises KeyError: if the AuthRequest is not consistent in its use
            of namespace aliases.

        @raises AXError: When parseExtensionArgs would raise same.

        @see: L{parseExtensionArgs}
        """
        message = openid_request.message
        ax_args = message.getArgs(cls.ns_uri)
        self = cls()
        try:
            self.parseExtensionArgs(ax_args)
        except NotAXMessage, err:
            return None

        if self.update_url:
            # Update URL must match the openid.realm of the underlying
            # OpenID 2 message.
            realm = message.getArg(OPENID_NS, 'realm',
                                   message.getArg(OPENID_NS, 'return_to'))

            if not realm:
                raise AXError(("Cannot validate update_url %r " +
                               "against absent realm") % (self.update_url,))

            tr = TrustRoot.parse(realm)
            if not tr.validateURL(self.update_url):
                raise AXError("Update URL %r failed validation against realm %r" %
                              (self.update_url, realm,))

        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, ax_args):
        """Given attribute exchange arguments, populate this FetchRequest.

        @param ax_args: Attribute Exchange arguments from the request.
            As returned from L{Message.getArgs<openid.message.Message.getArgs>}.
        @type ax_args: dict

        @raises KeyError: if the message is not consistent in its use
            of namespace aliases.

        @raises NotAXMessage: If ax_args does not include an Attribute Exchange
            mode.

        @raises AXError: If the data to be parsed does not follow the
            attribute exchange specification. At least when
            'if_available' or 'required' is not specified for a
            particular attribute type.
        """
        # Raises an exception if the mode is not the expected value
        self._checkMode(ax_args)

        aliases = NamespaceMap()

        for key, value in ax_args.iteritems():
            if key.startswith('type.'):
                alias = key[5:]
                type_uri = value
                aliases.addAlias(type_uri, alias)

                count_key = 'count.' + alias
                count_s = ax_args.get(count_key)
                if count_s:
                    try:
                        count = int(count_s)
                        if count <= 0:
                            raise AXError("Count %r must be greater than zero, got %r" % (count_key, count_s,))
                    except ValueError:
                        if count_s != UNLIMITED_VALUES:
                            raise AXError("Invalid count value for %r: %r" % (count_key, count_s,))
                        count = count_s
                else:
                    count = 1

                self.add(AttrInfo(type_uri, alias=alias, count=count))

        required = toTypeURIs(aliases, ax_args.get('required'))

        for type_uri in required:
            self.requested_attributes[type_uri].required = True

        if_available = toTypeURIs(aliases, ax_args.get('if_available'))

        all_type_uris = required + if_available

        for type_uri in aliases.iterNamespaceURIs():
            if type_uri not in all_type_uris:
                raise AXError(
                    'Type URI %r was in the request but not '
                    'present in "required" or "if_available"' % (type_uri,))

        self.update_url = ax_args.get('update_url')

    def iterAttrs(self):
        """Iterate over the AttrInfo objects that are
        contained in this fetch_request.
        """
        return self.requested_attributes.itervalues()

    def __iter__(self):
        """Iterate over the attribute type URIs in this fetch_request
        """
        return iter(self.requested_attributes)

    def has_key(self, type_uri):
        """Is the given type URI present in this fetch_request?
        """
        return type_uri in self.requested_attributes

    __contains__ = has_key


class AXKeyValueMessage(AXMessage):
    """An abstract class that implements a message that has attribute
    keys and values. It contains the common code between
    fetch_response and store_request.
    """

    # This class is abstract, so it's OK that it doesn't override the
    # abstract method in Extension:
    #
    #pylint:disable-msg=W0223

    def __init__(self):
        AXMessage.__init__(self)
        self.data = {}

    def addValue(self, type_uri, value):
        """Add a single value for the given attribute type to the
        message. If there are already values specified for this type,
        this value will be sent in addition to the values already
        specified.

        @param type_uri: The URI for the attribute

        @param value: The value to add to the response to the relying
            party for this attribute
        @type value: unicode

        @returns: None
        """
        try:
            values = self.data[type_uri]
        except KeyError:
            values = self.data[type_uri] = []

        values.append(value)

    def setValues(self, type_uri, values):
        """Set the values for the given attribute type. This replaces
        any values that have already been set for this attribute.

        @param type_uri: The URI for the attribute

        @param values: A list of values to send for this attribute.
        @type values: [unicode]
        """

        self.data[type_uri] = values

    def _getExtensionKVArgs(self, aliases=None):
        """Get the extension arguments for the key/value pairs
        contained in this message.

        @param aliases: An alias mapping. Set to None if you don't
            care about the aliases for this request.
        """
        if aliases is None:
            aliases = NamespaceMap()

        ax_args = {}

        for type_uri, values in self.data.iteritems():
            alias = aliases.add(type_uri)

            ax_args['type.' + alias] = type_uri
            ax_args['count.' + alias] = str(len(values))

            for i, value in enumerate(values):
                key = 'value.%s.%d' % (alias, i + 1)
                ax_args[key] = value

        return ax_args

    def parseExtensionArgs(self, ax_args):
        """Parse attribute exchange key/value arguments into this
        object.

        @param ax_args: The attribute exchange fetch_response
            arguments, with namespacing removed.
        @type ax_args: {unicode:unicode}

        @returns: None

        @raises ValueError: If the message has bad values for
            particular fields

        @raises KeyError: If the namespace mapping is bad or required
            arguments are missing
        """
        self._checkMode(ax_args)

        aliases = NamespaceMap()

        for key, value in ax_args.iteritems():
            if key.startswith('type.'):
                type_uri = value
                alias = key[5:]
                checkAlias(alias)
                aliases.addAlias(type_uri, alias)

        for type_uri, alias in aliases.iteritems():
            try:
                count_s = ax_args['count.' + alias]
            except KeyError:
                value = ax_args['value.' + alias]

                if value == u'':
                    values = []
                else:
                    values = [value]
            else:
                count = int(count_s)
                values = []
                for i in range(1, count + 1):
                    value_key = 'value.%s.%d' % (alias, i)
                    value = ax_args[value_key]
                    values.append(value)

            self.data[type_uri] = values

    def getSingle(self, type_uri, default=None):
        """Get a single value for an attribute. If no value was sent
        for this attribute, use the supplied default. If there is more
        than one value for this attribute, this method will fail.

        @type type_uri: str
        @param type_uri: The URI for the attribute

        @param default: The value to return if the attribute was not
            sent in the fetch_response.

        @returns: The value of the attribute in the fetch_response
            message, or the default supplied
        @rtype: unicode or NoneType

        @raises ValueError: If there is more than one value for this
            parameter in the fetch_response message.
        @raises KeyError: If the attribute was not sent in this response
        """
        values = self.data.get(type_uri)
        if not values:
            return default
        elif len(values) == 1:
            return values[0]
        else:
            raise AXError(
                'More than one value present for %r' % (type_uri,))

    def get(self, type_uri):
        """Get the list of values for this attribute in the
        fetch_response.

        XXX: what to do if the values are not present? default
        parameter? this is funny because it's always supposed to
        return a list, so the default may break that, though it's
        provided by the user's code, so it might be okay. If no
        default is supplied, should the return be None or []?

        @param type_uri: The URI of the attribute

        @returns: The list of values for this attribute in the
            response. May be an empty list.
        @rtype: [unicode]

        @raises KeyError: If the attribute was not sent in the response
        """
        return self.data[type_uri]

    def count(self, type_uri):
        """Get the number of responses for a particular attribute in
        this fetch_response message.

        @param type_uri: The URI of the attribute

        @returns: The number of values sent for this attribute

        @raises KeyError: If the attribute was not sent in the
            response. KeyError will not be raised if the number of
            values was zero.
        """
        return len(self.get(type_uri))


class FetchResponse(AXKeyValueMessage):
    """A fetch_response attribute exchange message
    """
    mode = 'fetch_response'

    def __init__(self, request=None, update_url=None):
        """
        @param request: When supplied, I will use namespace aliases
            that match those in this request.  I will also check to
            make sure I do not respond with attributes that were not
            requested.

        @type request: L{FetchRequest}

        @param update_url: By default, C{update_url} is taken from the
            request.  But if you do not supply the request, you may set
            the C{update_url} here.

        @type update_url: str
        """
        AXKeyValueMessage.__init__(self)
        self.update_url = update_url
        self.request = request

    def getExtensionArgs(self):
        """Serialize this object into arguments in the attribute
        exchange namespace

        @returns: The dictionary of unqualified attribute exchange
            arguments that represent this fetch_response.
        @rtype: {unicode;unicode}
        """

        aliases = NamespaceMap()

        zero_value_types = []

        if self.request is not None:
            # Validate the data in the context of the request (the
            # same attributes should be present in each, and the
            # counts in the response must be no more than the counts
            # in the request)

            for type_uri in self.data:
                if type_uri not in self.request:
                    raise KeyError(
                        'Response attribute not present in request: %r'
                        % (type_uri,))

            for attr_info in self.request.iterAttrs():
                # Copy the aliases from the request so that reading
                # the response in light of the request is easier
                if attr_info.alias is None:
                    aliases.add(attr_info.type_uri)
                else:
                    aliases.addAlias(attr_info.type_uri, attr_info.alias)

                try:
                    values = self.data[attr_info.type_uri]
                except KeyError:
                    values = []
                    zero_value_types.append(attr_info)

                if (attr_info.count != UNLIMITED_VALUES) and \
                       (attr_info.count < len(values)):
                    raise AXError(
                        'More than the number of requested values were '
                        'specified for %r' % (attr_info.type_uri,))

        kv_args = self._getExtensionKVArgs(aliases)

        # Add the KV args into the response with the args that are
        # unique to the fetch_response
        ax_args = self._newArgs()

        # For each requested attribute, put its type/alias and count
        # into the response even if no data were returned.
        for attr_info in zero_value_types:
            alias = aliases.getAlias(attr_info.type_uri)
            kv_args['type.' + alias] = attr_info.type_uri
            kv_args['count.' + alias] = '0'

        update_url = ((self.request and self.request.update_url)
                      or self.update_url)

        if update_url:
            ax_args['update_url'] = update_url

        ax_args.update(kv_args)

        return ax_args

    def parseExtensionArgs(self, ax_args):
        """@see: {Extension.parseExtensionArgs<openid.extension.Extension.parseExtensionArgs>}"""
        super(FetchResponse, self).parseExtensionArgs(ax_args)
        self.update_url = ax_args.get('update_url')

    def fromSuccessResponse(cls, success_response, signed=True):
        """Construct a FetchResponse object from an OpenID library
        SuccessResponse object.

        @param success_response: A successful id_res response object
        @type success_response: openid.consumer.consumer.SuccessResponse

        @param signed: Whether non-signed args should be
            processsed. If True (the default), only signed arguments
            will be processsed.
        @type signed: bool

        @returns: A FetchResponse containing the data from the OpenID
            message, or None if the SuccessResponse did not contain AX
            extension data.

        @raises AXError: when the AX data cannot be parsed.
        """
        self = cls()
        ax_args = success_response.extensionResponse(self.ns_uri, signed)

        try:
            self.parseExtensionArgs(ax_args)
        except NotAXMessage, err:
            return None
        else:
            return self

    fromSuccessResponse = classmethod(fromSuccessResponse)


class StoreRequest(AXKeyValueMessage):
    """A store request attribute exchange message representation
    """
    mode = 'store_request'

    def __init__(self, aliases=None):
        """
        @param aliases: The namespace aliases to use when making this
            store request.  Leave as None to use defaults.
        """
        super(StoreRequest, self).__init__()
        self.aliases = aliases

    def getExtensionArgs(self):
        """
        @see: L{Extension.getExtensionArgs<openid.extension.Extension.getExtensionArgs>}
        """
        ax_args = self._newArgs()
        kv_args = self._getExtensionKVArgs(self.aliases)
        ax_args.update(kv_args)
        return ax_args


class StoreResponse(AXMessage):
    """An indication that the store request was processed along with
    this OpenID transaction.
    """

    SUCCESS_MODE = 'store_response_success'
    FAILURE_MODE = 'store_response_failure'

    def __init__(self, succeeded=True, error_message=None):
        AXMessage.__init__(self)

        if succeeded and error_message is not None:
            raise AXError('An error message may only be included in a '
                             'failing fetch response')
        if succeeded:
            self.mode = self.SUCCESS_MODE
        else:
            self.mode = self.FAILURE_MODE

        self.error_message = error_message

    def succeeded(self):
        """Was this response a success response?"""
        return self.mode == self.SUCCESS_MODE

    def getExtensionArgs(self):
        """@see: {Extension.getExtensionArgs<openid.extension.Extension.getExtensionArgs>}"""
        ax_args = self._newArgs()
        if not self.succeeded() and self.error_message:
            ax_args['error'] = self.error_message

        return ax_args

########NEW FILE########
__FILENAME__ = pape2
"""An implementation of the OpenID Provider Authentication Policy
Extension 1.0

@see: http://openid.net/developers/specs/

@since: 2.1.0
"""

__all__ = [
    'Request',
    'Response',
    'ns_uri',
    'AUTH_PHISHING_RESISTANT',
    'AUTH_MULTI_FACTOR',
    'AUTH_MULTI_FACTOR_PHYSICAL',
    ]

from openid.extension import Extension
import re

ns_uri = "http://specs.openid.net/extensions/pape/1.0"

AUTH_MULTI_FACTOR_PHYSICAL = \
    'http://schemas.openid.net/pape/policies/2007/06/multi-factor-physical'
AUTH_MULTI_FACTOR = \
    'http://schemas.openid.net/pape/policies/2007/06/multi-factor'
AUTH_PHISHING_RESISTANT = \
    'http://schemas.openid.net/pape/policies/2007/06/phishing-resistant'

TIME_VALIDATOR = re.compile('^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$')

class Request(Extension):
    """A Provider Authentication Policy request, sent from a relying
    party to a provider

    @ivar preferred_auth_policies: The authentication policies that
        the relying party prefers
    @type preferred_auth_policies: [str]

    @ivar max_auth_age: The maximum time, in seconds, that the relying
        party wants to allow to have elapsed before the user must
        re-authenticate
    @type max_auth_age: int or NoneType
    """

    ns_alias = 'pape'

    def __init__(self, preferred_auth_policies=None, max_auth_age=None):
        super(Request, self).__init__()
        if not preferred_auth_policies:
            preferred_auth_policies = []

        self.preferred_auth_policies = preferred_auth_policies
        self.max_auth_age = max_auth_age

    def __nonzero__(self):
        return bool(self.preferred_auth_policies or
                    self.max_auth_age is not None)

    def addPolicyURI(self, policy_uri):
        """Add an acceptable authentication policy URI to this request

        This method is intended to be used by the relying party to add
        acceptable authentication types to the request.

        @param policy_uri: The identifier for the preferred type of
            authentication.
        @see: http://openid.net/specs/openid-provider-authentication-policy-extension-1_0-01.html#auth_policies
        """
        if policy_uri not in self.preferred_auth_policies:
            self.preferred_auth_policies.append(policy_uri)

    def getExtensionArgs(self):
        """@see: C{L{Extension.getExtensionArgs}}
        """
        ns_args = {
            'preferred_auth_policies':' '.join(self.preferred_auth_policies)
            }

        if self.max_auth_age is not None:
            ns_args['max_auth_age'] = str(self.max_auth_age)

        return ns_args

    def fromOpenIDRequest(cls, request):
        """Instantiate a Request object from the arguments in a
        C{checkid_*} OpenID message
        """
        self = cls()
        args = request.message.getArgs(self.ns_uri)

        if args == {}:
            return None

        self.parseExtensionArgs(args)
        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, args):
        """Set the state of this request to be that expressed in these
        PAPE arguments

        @param args: The PAPE arguments without a namespace

        @rtype: None

        @raises ValueError: When the max_auth_age is not parseable as
            an integer
        """

        # preferred_auth_policies is a space-separated list of policy URIs
        self.preferred_auth_policies = []

        policies_str = args.get('preferred_auth_policies')
        if policies_str:
            for uri in policies_str.split(' '):
                if uri not in self.preferred_auth_policies:
                    self.preferred_auth_policies.append(uri)

        # max_auth_age is base-10 integer number of seconds
        max_auth_age_str = args.get('max_auth_age')
        self.max_auth_age = None

        if max_auth_age_str:
            try:
                self.max_auth_age = int(max_auth_age_str)
            except ValueError:
                pass

    def preferredTypes(self, supported_types):
        """Given a list of authentication policy URIs that a provider
        supports, this method returns the subsequence of those types
        that are preferred by the relying party.

        @param supported_types: A sequence of authentication policy
            type URIs that are supported by a provider

        @returns: The sub-sequence of the supported types that are
            preferred by the relying party. This list will be ordered
            in the order that the types appear in the supported_types
            sequence, and may be empty if the provider does not prefer
            any of the supported authentication types.

        @returntype: [str]
        """
        return filter(self.preferred_auth_policies.__contains__,
                      supported_types)

Request.ns_uri = ns_uri


class Response(Extension):
    """A Provider Authentication Policy response, sent from a provider
    to a relying party
    """

    ns_alias = 'pape'

    def __init__(self, auth_policies=None, auth_time=None,
                 nist_auth_level=None):
        super(Response, self).__init__()
        if auth_policies:
            self.auth_policies = auth_policies
        else:
            self.auth_policies = []

        self.auth_time = auth_time
        self.nist_auth_level = nist_auth_level

    def addPolicyURI(self, policy_uri):
        """Add a authentication policy to this response

        This method is intended to be used by the provider to add a
        policy that the provider conformed to when authenticating the user.

        @param policy_uri: The identifier for the preferred type of
            authentication.
        @see: http://openid.net/specs/openid-provider-authentication-policy-extension-1_0-01.html#auth_policies
        """
        if policy_uri not in self.auth_policies:
            self.auth_policies.append(policy_uri)

    def fromSuccessResponse(cls, success_response):
        """Create a C{L{Response}} object from a successful OpenID
        library response
        (C{L{openid.consumer.consumer.SuccessResponse}}) response
        message

        @param success_response: A SuccessResponse from consumer.complete()
        @type success_response: C{L{openid.consumer.consumer.SuccessResponse}}

        @rtype: Response or None
        @returns: A provider authentication policy response from the
            data that was supplied with the C{id_res} response or None
            if the provider sent no signed PAPE response arguments.
        """
        self = cls()

        # PAPE requires that the args be signed.
        args = success_response.getSignedNS(self.ns_uri)

        # Only try to construct a PAPE response if the arguments were
        # signed in the OpenID response.  If not, return None.
        if args is not None:
            self.parseExtensionArgs(args)
            return self
        else:
            return None

    def parseExtensionArgs(self, args, strict=False):
        """Parse the provider authentication policy arguments into the
        internal state of this object

        @param args: unqualified provider authentication policy
            arguments

        @param strict: Whether to raise an exception when bad data is
            encountered

        @returns: None. The data is parsed into the internal fields of
            this object.
        """
        policies_str = args.get('auth_policies')
        if policies_str and policies_str != 'none':
            self.auth_policies = policies_str.split(' ')

        nist_level_str = args.get('nist_auth_level')
        if nist_level_str:
            try:
                nist_level = int(nist_level_str)
            except ValueError:
                if strict:
                    raise ValueError('nist_auth_level must be an integer between '
                                     'zero and four, inclusive')
                else:
                    self.nist_auth_level = None
            else:
                if 0 <= nist_level < 5:
                    self.nist_auth_level = nist_level

        auth_time = args.get('auth_time')
        if auth_time:
            if TIME_VALIDATOR.match(auth_time):
                self.auth_time = auth_time
            elif strict:
                raise ValueError("auth_time must be in RFC3339 format")

    fromSuccessResponse = classmethod(fromSuccessResponse)

    def getExtensionArgs(self):
        """@see: C{L{Extension.getExtensionArgs}}
        """
        if len(self.auth_policies) == 0:
            ns_args = {
                'auth_policies':'none',
            }
        else:
            ns_args = {
                'auth_policies':' '.join(self.auth_policies),
                }

        if self.nist_auth_level is not None:
            if self.nist_auth_level not in range(0, 5):
                raise ValueError('nist_auth_level must be an integer between '
                                 'zero and four, inclusive')
            ns_args['nist_auth_level'] = str(self.nist_auth_level)

        if self.auth_time is not None:
            if not TIME_VALIDATOR.match(self.auth_time):
                raise ValueError('auth_time must be in RFC3339 format')

            ns_args['auth_time'] = self.auth_time

        return ns_args

Response.ns_uri = ns_uri

########NEW FILE########
__FILENAME__ = pape5
"""An implementation of the OpenID Provider Authentication Policy
Extension 1.0, Draft 5

@see: http://openid.net/developers/specs/

@since: 2.1.0
"""

__all__ = [
    'Request',
    'Response',
    'ns_uri',
    'AUTH_PHISHING_RESISTANT',
    'AUTH_MULTI_FACTOR',
    'AUTH_MULTI_FACTOR_PHYSICAL',
    'LEVELS_NIST',
    'LEVELS_JISA',
    ]

from openid.extension import Extension
import warnings
import re

ns_uri = "http://specs.openid.net/extensions/pape/1.0"

AUTH_MULTI_FACTOR_PHYSICAL = \
    'http://schemas.openid.net/pape/policies/2007/06/multi-factor-physical'
AUTH_MULTI_FACTOR = \
    'http://schemas.openid.net/pape/policies/2007/06/multi-factor'
AUTH_PHISHING_RESISTANT = \
    'http://schemas.openid.net/pape/policies/2007/06/phishing-resistant'
AUTH_NONE = \
    'http://schemas.openid.net/pape/policies/2007/06/none'

TIME_VALIDATOR = re.compile('^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$')

LEVELS_NIST = 'http://csrc.nist.gov/publications/nistpubs/800-63/SP800-63V1_0_2.pdf'
LEVELS_JISA = 'http://www.jisa.or.jp/spec/auth_level.html'

class PAPEExtension(Extension):
    _default_auth_level_aliases = {
        'nist': LEVELS_NIST,
        'jisa': LEVELS_JISA,
        }

    def __init__(self):
        self.auth_level_aliases = self._default_auth_level_aliases.copy()

    def _addAuthLevelAlias(self, auth_level_uri, alias=None):
        """Add an auth level URI alias to this request.

        @param auth_level_uri: The auth level URI to send in the
            request.

        @param alias: The namespace alias to use for this auth level
            in this message. May be None if the alias is not
            important.
        """
        if alias is None:
            try:
                alias = self._getAlias(auth_level_uri)
            except KeyError:
                alias = self._generateAlias()
        else:
            existing_uri = self.auth_level_aliases.get(alias)
            if existing_uri is not None and existing_uri != auth_level_uri:
                raise KeyError('Attempting to redefine alias %r from %r to %r',
                               alias, existing_uri, auth_level_uri)

        self.auth_level_aliases[alias] = auth_level_uri

    def _generateAlias(self):
        """Return an unused auth level alias"""
        for i in xrange(1000):
            alias = 'cust%d' % (i,)
            if alias not in self.auth_level_aliases:
                return alias

        raise RuntimeError('Could not find an unused alias (tried 1000!)')

    def _getAlias(self, auth_level_uri):
        """Return the alias for the specified auth level URI.

        @raises KeyError: if no alias is defined
        """
        for (alias, existing_uri) in self.auth_level_aliases.iteritems():
            if auth_level_uri == existing_uri:
                return alias

        raise KeyError(auth_level_uri)

class Request(PAPEExtension):
    """A Provider Authentication Policy request, sent from a relying
    party to a provider

    @ivar preferred_auth_policies: The authentication policies that
        the relying party prefers
    @type preferred_auth_policies: [str]

    @ivar max_auth_age: The maximum time, in seconds, that the relying
        party wants to allow to have elapsed before the user must
        re-authenticate
    @type max_auth_age: int or NoneType

    @ivar preferred_auth_level_types: Ordered list of authentication
        level namespace URIs

    @type preferred_auth_level_types: [str]
    """

    ns_alias = 'pape'

    def __init__(self, preferred_auth_policies=None, max_auth_age=None,
                 preferred_auth_level_types=None):
        super(Request, self).__init__()
        if preferred_auth_policies is None:
            preferred_auth_policies = []

        self.preferred_auth_policies = preferred_auth_policies
        self.max_auth_age = max_auth_age
        self.preferred_auth_level_types = []

        if preferred_auth_level_types is not None:
            for auth_level in preferred_auth_level_types:
                self.addAuthLevel(auth_level)

    def __nonzero__(self):
        return bool(self.preferred_auth_policies or
                    self.max_auth_age is not None or
                    self.preferred_auth_level_types)

    def addPolicyURI(self, policy_uri):
        """Add an acceptable authentication policy URI to this request

        This method is intended to be used by the relying party to add
        acceptable authentication types to the request.

        @param policy_uri: The identifier for the preferred type of
            authentication.
        @see: http://openid.net/specs/openid-provider-authentication-policy-extension-1_0-05.html#auth_policies
        """
        if policy_uri not in self.preferred_auth_policies:
            self.preferred_auth_policies.append(policy_uri)

    def addAuthLevel(self, auth_level_uri, alias=None):
        self._addAuthLevelAlias(auth_level_uri, alias)
        if auth_level_uri not in self.preferred_auth_level_types:
            self.preferred_auth_level_types.append(auth_level_uri)

    def getExtensionArgs(self):
        """@see: C{L{Extension.getExtensionArgs}}
        """
        ns_args = {
            'preferred_auth_policies':' '.join(self.preferred_auth_policies),
            }

        if self.max_auth_age is not None:
            ns_args['max_auth_age'] = str(self.max_auth_age)

        if self.preferred_auth_level_types:
            preferred_types = []

            for auth_level_uri in self.preferred_auth_level_types:
                alias = self._getAlias(auth_level_uri)
                ns_args['auth_level.ns.%s' % (alias,)] = auth_level_uri
                preferred_types.append(alias)

            ns_args['preferred_auth_level_types'] = ' '.join(preferred_types)

        return ns_args

    def fromOpenIDRequest(cls, request):
        """Instantiate a Request object from the arguments in a
        C{checkid_*} OpenID message
        """
        self = cls()
        args = request.message.getArgs(self.ns_uri)
        is_openid1 = request.message.isOpenID1()

        if args == {}:
            return None

        self.parseExtensionArgs(args, is_openid1)
        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, args, is_openid1, strict=False):
        """Set the state of this request to be that expressed in these
        PAPE arguments

        @param args: The PAPE arguments without a namespace

        @param strict: Whether to raise an exception if the input is
            out of spec or otherwise malformed. If strict is false,
            malformed input will be ignored.

        @param is_openid1: Whether the input should be treated as part
            of an OpenID1 request

        @rtype: None

        @raises ValueError: When the max_auth_age is not parseable as
            an integer
        """

        # preferred_auth_policies is a space-separated list of policy URIs
        self.preferred_auth_policies = []

        policies_str = args.get('preferred_auth_policies')
        if policies_str:
            for uri in policies_str.split(' '):
                if uri not in self.preferred_auth_policies:
                    self.preferred_auth_policies.append(uri)

        # max_auth_age is base-10 integer number of seconds
        max_auth_age_str = args.get('max_auth_age')
        self.max_auth_age = None

        if max_auth_age_str:
            try:
                self.max_auth_age = int(max_auth_age_str)
            except ValueError:
                if strict:
                    raise

        # Parse auth level information
        preferred_auth_level_types = args.get('preferred_auth_level_types')
        if preferred_auth_level_types:
            aliases = preferred_auth_level_types.strip().split()

            for alias in aliases:
                key = 'auth_level.ns.%s' % (alias,)
                try:
                    uri = args[key]
                except KeyError:
                    if is_openid1:
                        uri = self._default_auth_level_aliases.get(alias)
                    else:
                        uri = None

                if uri is None:
                    if strict:
                        raise ValueError('preferred auth level %r is not '
                                         'defined in this message' % (alias,))
                else:
                    self.addAuthLevel(uri, alias)

    def preferredTypes(self, supported_types):
        """Given a list of authentication policy URIs that a provider
        supports, this method returns the subsequence of those types
        that are preferred by the relying party.

        @param supported_types: A sequence of authentication policy
            type URIs that are supported by a provider

        @returns: The sub-sequence of the supported types that are
            preferred by the relying party. This list will be ordered
            in the order that the types appear in the supported_types
            sequence, and may be empty if the provider does not prefer
            any of the supported authentication types.

        @returntype: [str]
        """
        return filter(self.preferred_auth_policies.__contains__,
                      supported_types)

Request.ns_uri = ns_uri


class Response(PAPEExtension):
    """A Provider Authentication Policy response, sent from a provider
    to a relying party

    @ivar auth_policies: List of authentication policies conformed to
        by this OpenID assertion, represented as policy URIs
    """

    ns_alias = 'pape'

    def __init__(self, auth_policies=None, auth_time=None,
                 auth_levels=None):
        super(Response, self).__init__()
        if auth_policies:
            self.auth_policies = auth_policies
        else:
            self.auth_policies = []

        self.auth_time = auth_time
        self.auth_levels = {}

        if auth_levels is None:
            auth_levels = {}

        for uri, level in auth_levels.iteritems():
            self.setAuthLevel(uri, level)

    def setAuthLevel(self, level_uri, level, alias=None):
        """Set the value for the given auth level type.

        @param level: string representation of an authentication level
            valid for level_uri

        @param alias: An optional namespace alias for the given auth
            level URI. May be omitted if the alias is not
            significant. The library will use a reasonable default for
            widely-used auth level types.
        """
        self._addAuthLevelAlias(level_uri, alias)
        self.auth_levels[level_uri] = level

    def getAuthLevel(self, level_uri):
        """Return the auth level for the specified auth level
        identifier

        @returns: A string that should map to the auth levels defined
            for the auth level type

        @raises KeyError: If the auth level type is not present in
            this message
        """
        return self.auth_levels[level_uri]

    def _getNISTAuthLevel(self):
        try:
            return int(self.getAuthLevel(LEVELS_NIST))
        except KeyError:
            return None

    nist_auth_level = property(
        _getNISTAuthLevel,
        doc="Backward-compatibility accessor for the NIST auth level")

    def addPolicyURI(self, policy_uri):
        """Add a authentication policy to this response

        This method is intended to be used by the provider to add a
        policy that the provider conformed to when authenticating the user.

        @param policy_uri: The identifier for the preferred type of
            authentication.
        @see: http://openid.net/specs/openid-provider-authentication-policy-extension-1_0-01.html#auth_policies
        """
        if policy_uri == AUTH_NONE:
            raise RuntimeError(
                'To send no policies, do not set any on the response.')

        if policy_uri not in self.auth_policies:
            self.auth_policies.append(policy_uri)

    def fromSuccessResponse(cls, success_response):
        """Create a C{L{Response}} object from a successful OpenID
        library response
        (C{L{openid.consumer.consumer.SuccessResponse}}) response
        message

        @param success_response: A SuccessResponse from consumer.complete()
        @type success_response: C{L{openid.consumer.consumer.SuccessResponse}}

        @rtype: Response or None
        @returns: A provider authentication policy response from the
            data that was supplied with the C{id_res} response or None
            if the provider sent no signed PAPE response arguments.
        """
        self = cls()

        # PAPE requires that the args be signed.
        args = success_response.getSignedNS(self.ns_uri)
        is_openid1 = success_response.isOpenID1()

        # Only try to construct a PAPE response if the arguments were
        # signed in the OpenID response.  If not, return None.
        if args is not None:
            self.parseExtensionArgs(args, is_openid1)
            return self
        else:
            return None

    def parseExtensionArgs(self, args, is_openid1, strict=False):
        """Parse the provider authentication policy arguments into the
        internal state of this object

        @param args: unqualified provider authentication policy
            arguments

        @param strict: Whether to raise an exception when bad data is
            encountered

        @returns: None. The data is parsed into the internal fields of
            this object.
        """
        policies_str = args.get('auth_policies')
        if policies_str:
            auth_policies = policies_str.split(' ')
        elif strict:
            raise ValueError('Missing auth_policies')
        else:
            auth_policies = []

        if (len(auth_policies) > 1 and strict and AUTH_NONE in auth_policies):
            raise ValueError('Got some auth policies, as well as the special '
                             '"none" URI: %r' % (auth_policies,))

        if 'none' in auth_policies:
            msg = '"none" used as a policy URI (see PAPE draft < 5)'
            if strict:
                raise ValueError(msg)
            else:
                warnings.warn(msg, stacklevel=2)

        auth_policies = [u for u in auth_policies
                         if u not in ['none', AUTH_NONE]]

        self.auth_policies = auth_policies

        for (key, val) in args.iteritems():
            if key.startswith('auth_level.'):
                alias = key[11:]

                # skip the already-processed namespace declarations
                if alias.startswith('ns.'):
                    continue

                try:
                    uri = args['auth_level.ns.%s' % (alias,)]
                except KeyError:
                    if is_openid1:
                        uri = self._default_auth_level_aliases.get(alias)
                    else:
                        uri = None

                if uri is None:
                    if strict:
                        raise ValueError(
                            'Undefined auth level alias: %r' % (alias,))
                else:
                    self.setAuthLevel(uri, val, alias)

        auth_time = args.get('auth_time')
        if auth_time:
            if TIME_VALIDATOR.match(auth_time):
                self.auth_time = auth_time
            elif strict:
                raise ValueError("auth_time must be in RFC3339 format")

    fromSuccessResponse = classmethod(fromSuccessResponse)

    def getExtensionArgs(self):
        """@see: C{L{Extension.getExtensionArgs}}
        """
        if len(self.auth_policies) == 0:
            ns_args = {
                'auth_policies': AUTH_NONE,
            }
        else:
            ns_args = {
                'auth_policies':' '.join(self.auth_policies),
                }

        for level_type, level in self.auth_levels.iteritems():
            alias = self._getAlias(level_type)
            ns_args['auth_level.ns.%s' % (alias,)] = level_type
            ns_args['auth_level.%s' % (alias,)] = str(level)

        if self.auth_time is not None:
            if not TIME_VALIDATOR.match(self.auth_time):
                raise ValueError('auth_time must be in RFC3339 format')

            ns_args['auth_time'] = self.auth_time

        return ns_args

Response.ns_uri = ns_uri

########NEW FILE########
__FILENAME__ = sreg
"""Simple registration request and response parsing and object representation

This module contains objects representing simple registration requests
and responses that can be used with both OpenID relying parties and
OpenID providers.

  1. The relying party creates a request object and adds it to the
     C{L{AuthRequest<openid.consumer.consumer.AuthRequest>}} object
     before making the C{checkid_} request to the OpenID provider::

      auth_request.addExtension(SRegRequest(required=['email']))

  2. The OpenID provider extracts the simple registration request from
     the OpenID request using C{L{SRegRequest.fromOpenIDRequest}},
     gets the user's approval and data, creates a C{L{SRegResponse}}
     object and adds it to the C{id_res} response::

      sreg_req = SRegRequest.fromOpenIDRequest(checkid_request)
      # [ get the user's approval and data, informing the user that
      #   the fields in sreg_response were requested ]
      sreg_resp = SRegResponse.extractResponse(sreg_req, user_data)
      sreg_resp.toMessage(openid_response.fields)

  3. The relying party uses C{L{SRegResponse.fromSuccessResponse}} to
     extract the data from the OpenID response::

      sreg_resp = SRegResponse.fromSuccessResponse(success_response)

@since: 2.0

@var sreg_data_fields: The names of the data fields that are listed in
    the sreg spec, and a description of them in English

@var sreg_uri: The preferred URI to use for the simple registration
    namespace and XRD Type value
"""

from openid.message import registerNamespaceAlias, \
     NamespaceAliasRegistrationError
from openid.extension import Extension
from openid import oidutil

try:
    basestring #pylint:disable-msg=W0104
except NameError:
    # For Python 2.2
    basestring = (str, unicode) #pylint:disable-msg=W0622

__all__ = [
    'SRegRequest',
    'SRegResponse',
    'data_fields',
    'ns_uri',
    'ns_uri_1_0',
    'ns_uri_1_1',
    'supportsSReg',
    ]

# The data fields that are listed in the sreg spec
data_fields = {
    'fullname':'Full Name',
    'nickname':'Nickname',
    'dob':'Date of Birth',
    'email':'E-mail Address',
    'gender':'Gender',
    'postcode':'Postal Code',
    'country':'Country',
    'language':'Language',
    'timezone':'Time Zone',
    }

def checkFieldName(field_name):
    """Check to see that the given value is a valid simple
    registration data field name.

    @raise ValueError: if the field name is not a valid simple
        registration data field name
    """
    if field_name not in data_fields:
        raise ValueError('%r is not a defined simple registration field' %
                         (field_name,))

# URI used in the wild for Yadis documents advertising simple
# registration support
ns_uri_1_0 = 'http://openid.net/sreg/1.0'

# URI in the draft specification for simple registration 1.1
# <http://openid.net/specs/openid-simple-registration-extension-1_1-01.html>
ns_uri_1_1 = 'http://openid.net/extensions/sreg/1.1'

# This attribute will always hold the preferred URI to use when adding
# sreg support to an XRDS file or in an OpenID namespace declaration.
ns_uri = ns_uri_1_1

try:
    registerNamespaceAlias(ns_uri_1_1, 'sreg')
except NamespaceAliasRegistrationError, e:
    oidutil.log('registerNamespaceAlias(%r, %r) failed: %s' % (ns_uri_1_1,
                                                               'sreg', str(e),))

def supportsSReg(endpoint):
    """Does the given endpoint advertise support for simple
    registration?

    @param endpoint: The endpoint object as returned by OpenID discovery
    @type endpoint: openid.consumer.discover.OpenIDEndpoint

    @returns: Whether an sreg type was advertised by the endpoint
    @rtype: bool
    """
    return (endpoint.usesExtension(ns_uri_1_1) or
            endpoint.usesExtension(ns_uri_1_0))

class SRegNamespaceError(ValueError):
    """The simple registration namespace was not found and could not
    be created using the expected name (there's another extension
    using the name 'sreg')

    This is not I{illegal}, for OpenID 2, although it probably
    indicates a problem, since it's not expected that other extensions
    will re-use the alias that is in use for OpenID 1.

    If this is an OpenID 1 request, then there is no recourse. This
    should not happen unless some code has modified the namespaces for
    the message that is being processed.
    """

def getSRegNS(message):
    """Extract the simple registration namespace URI from the given
    OpenID message. Handles OpenID 1 and 2, as well as both sreg
    namespace URIs found in the wild, as well as missing namespace
    definitions (for OpenID 1)

    @param message: The OpenID message from which to parse simple
        registration fields. This may be a request or response message.
    @type message: C{L{openid.message.Message}}

    @returns: the sreg namespace URI for the supplied message. The
        message may be modified to define a simple registration
        namespace.
    @rtype: C{str}

    @raise ValueError: when using OpenID 1 if the message defines
        the 'sreg' alias to be something other than a simple
        registration type.
    """
    # See if there exists an alias for one of the two defined simple
    # registration types.
    for sreg_ns_uri in [ns_uri_1_1, ns_uri_1_0]:
        alias = message.namespaces.getAlias(sreg_ns_uri)
        if alias is not None:
            break
    else:
        # There is no alias for either of the types, so try to add
        # one. We default to using the modern value (1.1)
        sreg_ns_uri = ns_uri_1_1
        try:
            message.namespaces.addAlias(ns_uri_1_1, 'sreg')
        except KeyError, why:
            # An alias for the string 'sreg' already exists, but it's
            # defined for something other than simple registration
            raise SRegNamespaceError(why[0])

    # we know that sreg_ns_uri defined, because it's defined in the
    # else clause of the loop as well, so disable the warning
    return sreg_ns_uri #pylint:disable-msg=W0631

class SRegRequest(Extension):
    """An object to hold the state of a simple registration request.

    @ivar required: A list of the required fields in this simple
        registration request
    @type required: [str]

    @ivar optional: A list of the optional fields in this simple
        registration request
    @type optional: [str]

    @ivar policy_url: The policy URL that was provided with the request
    @type policy_url: str or NoneType

    @group Consumer: requestField, requestFields, getExtensionArgs, addToOpenIDRequest
    @group Server: fromOpenIDRequest, parseExtensionArgs
    """

    ns_alias = 'sreg'

    def __init__(self, required=None, optional=None, policy_url=None,
                 sreg_ns_uri=ns_uri):
        """Initialize an empty simple registration request"""
        Extension.__init__(self)
        self.required = []
        self.optional = []
        self.policy_url = policy_url
        self.ns_uri = sreg_ns_uri

        if required:
            self.requestFields(required, required=True, strict=True)

        if optional:
            self.requestFields(optional, required=False, strict=True)

    # Assign getSRegNS to a static method so that it can be
    # overridden for testing.
    _getSRegNS = staticmethod(getSRegNS)

    def fromOpenIDRequest(cls, request):
        """Create a simple registration request that contains the
        fields that were requested in the OpenID request with the
        given arguments

        @param request: The OpenID request
        @type request: openid.server.CheckIDRequest

        @returns: The newly created simple registration request
        @rtype: C{L{SRegRequest}}
        """
        self = cls()

        # Since we're going to mess with namespace URI mapping, don't
        # mutate the object that was passed in.
        message = request.message.copy()

        self.ns_uri = self._getSRegNS(message)
        args = message.getArgs(self.ns_uri)
        self.parseExtensionArgs(args)

        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, args, strict=False):
        """Parse the unqualified simple registration request
        parameters and add them to this object.

        This method is essentially the inverse of
        C{L{getExtensionArgs}}. This method restores the serialized simple
        registration request fields.

        If you are extracting arguments from a standard OpenID
        checkid_* request, you probably want to use C{L{fromOpenIDRequest}},
        which will extract the sreg namespace and arguments from the
        OpenID request. This method is intended for cases where the
        OpenID server needs more control over how the arguments are
        parsed than that method provides.

        >>> args = message.getArgs(ns_uri)
        >>> request.parseExtensionArgs(args)

        @param args: The unqualified simple registration arguments
        @type args: {str:str}

        @param strict: Whether requests with fields that are not
            defined in the simple registration specification should be
            tolerated (and ignored)
        @type strict: bool

        @returns: None; updates this object
        """
        for list_name in ['required', 'optional']:
            required = (list_name == 'required')
            items = args.get(list_name)
            if items:
                for field_name in items.split(','):
                    try:
                        self.requestField(field_name, required, strict)
                    except ValueError:
                        if strict:
                            raise

        self.policy_url = args.get('policy_url')

    def allRequestedFields(self):
        """A list of all of the simple registration fields that were
        requested, whether they were required or optional.

        @rtype: [str]
        """
        return self.required + self.optional

    def wereFieldsRequested(self):
        """Have any simple registration fields been requested?

        @rtype: bool
        """
        return bool(self.allRequestedFields())

    def __contains__(self, field_name):
        """Was this field in the request?"""
        return (field_name in self.required or
                field_name in self.optional)

    def requestField(self, field_name, required=False, strict=False):
        """Request the specified field from the OpenID user

        @param field_name: the unqualified simple registration field name
        @type field_name: str

        @param required: whether the given field should be presented
            to the user as being a required to successfully complete
            the request

        @param strict: whether to raise an exception when a field is
            added to a request more than once

        @raise ValueError: when the field requested is not a simple
            registration field or strict is set and the field was
            requested more than once
        """
        checkFieldName(field_name)

        if strict:
            if field_name in self.required or field_name in self.optional:
                raise ValueError('That field has already been requested')
        else:
            if field_name in self.required:
                return

            if field_name in self.optional:
                if required:
                    self.optional.remove(field_name)
                else:
                    return

        if required:
            self.required.append(field_name)
        else:
            self.optional.append(field_name)

    def requestFields(self, field_names, required=False, strict=False):
        """Add the given list of fields to the request

        @param field_names: The simple registration data fields to request
        @type field_names: [str]

        @param required: Whether these values should be presented to
            the user as required

        @param strict: whether to raise an exception when a field is
            added to a request more than once

        @raise ValueError: when a field requested is not a simple
            registration field or strict is set and a field was
            requested more than once
        """
        if isinstance(field_names, basestring):
            raise TypeError('Fields should be passed as a list of '
                            'strings (not %r)' % (type(field_names),))

        for field_name in field_names:
            self.requestField(field_name, required, strict=strict)

    def getExtensionArgs(self):
        """Get a dictionary of unqualified simple registration
        arguments representing this request.

        This method is essentially the inverse of
        C{L{parseExtensionArgs}}. This method serializes the simple
        registration request fields.

        @rtype: {str:str}
        """
        args = {}

        if self.required:
            args['required'] = ','.join(self.required)

        if self.optional:
            args['optional'] = ','.join(self.optional)

        if self.policy_url:
            args['policy_url'] = self.policy_url

        return args

class SRegResponse(Extension):
    """Represents the data returned in a simple registration response
    inside of an OpenID C{id_res} response. This object will be
    created by the OpenID server, added to the C{id_res} response
    object, and then extracted from the C{id_res} message by the
    Consumer.

    @ivar data: The simple registration data, keyed by the unqualified
        simple registration name of the field (i.e. nickname is keyed
        by C{'nickname'})

    @ivar ns_uri: The URI under which the simple registration data was
        stored in the response message.

    @group Server: extractResponse
    @group Consumer: fromSuccessResponse
    @group Read-only dictionary interface: keys, iterkeys, items, iteritems,
        __iter__, get, __getitem__, keys, has_key
    """

    ns_alias = 'sreg'

    def __init__(self, data=None, sreg_ns_uri=ns_uri):
        Extension.__init__(self)
        if data is None:
            self.data = {}
        else:
            self.data = data

        self.ns_uri = sreg_ns_uri

    def extractResponse(cls, request, data):
        """Take a C{L{SRegRequest}} and a dictionary of simple
        registration values and create a C{L{SRegResponse}}
        object containing that data.

        @param request: The simple registration request object
        @type request: SRegRequest

        @param data: The simple registration data for this
            response, as a dictionary from unqualified simple
            registration field name to string (unicode) value. For
            instance, the nickname should be stored under the key
            'nickname'.
        @type data: {str:str}

        @returns: a simple registration response object
        @rtype: SRegResponse
        """
        self = cls()
        self.ns_uri = request.ns_uri
        for field in request.allRequestedFields():
            value = data.get(field)
            if value is not None:
                self.data[field] = value
        return self

    extractResponse = classmethod(extractResponse)

    # Assign getSRegArgs to a static method so that it can be
    # overridden for testing
    _getSRegNS = staticmethod(getSRegNS)

    def fromSuccessResponse(cls, success_response, signed_only=True):
        """Create a C{L{SRegResponse}} object from a successful OpenID
        library response
        (C{L{openid.consumer.consumer.SuccessResponse}}) response
        message

        @param success_response: A SuccessResponse from consumer.complete()
        @type success_response: C{L{openid.consumer.consumer.SuccessResponse}}

        @param signed_only: Whether to process only data that was
            signed in the id_res message from the server.
        @type signed_only: bool

        @rtype: SRegResponse
        @returns: A simple registration response containing the data
            that was supplied with the C{id_res} response.
        """
        self = cls()
        self.ns_uri = self._getSRegNS(success_response.message)
        if signed_only:
            args = success_response.getSignedNS(self.ns_uri)
        else:
            args = success_response.message.getArgs(self.ns_uri)

        if not args:
            return None

        for field_name in data_fields:
            if field_name in args:
                self.data[field_name] = args[field_name]

        return self

    fromSuccessResponse = classmethod(fromSuccessResponse)

    def getExtensionArgs(self):
        """Get the fields to put in the simple registration namespace
        when adding them to an id_res message.

        @see: openid.extension
        """
        return self.data

    # Read-only dictionary interface
    def get(self, field_name, default=None):
        """Like dict.get, except that it checks that the field name is
        defined by the simple registration specification"""
        checkFieldName(field_name)
        return self.data.get(field_name, default)

    def items(self):
        """All of the data values in this simple registration response
        """
        return self.data.items()

    def iteritems(self):
        return self.data.iteritems()

    def keys(self):
        return self.data.keys()

    def iterkeys(self):
        return self.data.iterkeys()

    def has_key(self, key):
        return key in self

    def __contains__(self, field_name):
        checkFieldName(field_name)
        return field_name in self.data

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, field_name):
        checkFieldName(field_name)
        return self.data[field_name]

    def __nonzero__(self):
        return bool(self.data)

########NEW FILE########
__FILENAME__ = fetchers
# -*- test-case-name: openid.test.test_fetchers -*-
"""
This module contains the HTTP fetcher interface and several implementations.
"""

__all__ = ['fetch', 'getDefaultFetcher', 'setDefaultFetcher', 'HTTPResponse',
           'HTTPFetcher', 'createHTTPFetcher', 'HTTPFetchingError',
           'HTTPError']

import urllib2
import time
import cStringIO
import sys

import openid
import openid.urinorm

# Try to import httplib2 for caching support
# http://bitworking.org/projects/httplib2/
try:
    import httplib2
except ImportError:
    # httplib2 not available
    httplib2 = None

# try to import pycurl, which will let us use CurlHTTPFetcher
try:
    import pycurl
except ImportError:
    pycurl = None

USER_AGENT = "python-openid/%s (%s)" % (openid.__version__, sys.platform)
MAX_RESPONSE_KB = 1024

def fetch(url, body=None, headers=None):
    """Invoke the fetch method on the default fetcher. Most users
    should need only this method.

    @raises Exception: any exceptions that may be raised by the default fetcher
    """
    fetcher = getDefaultFetcher()
    return fetcher.fetch(url, body, headers)

def createHTTPFetcher():
    """Create a default HTTP fetcher instance

    prefers Curl to urllib2."""
    if pycurl is None:
        fetcher = Urllib2Fetcher()
    else:
        fetcher = CurlHTTPFetcher()

    return fetcher

# Contains the currently set HTTP fetcher. If it is set to None, the
# library will call createHTTPFetcher() to set it. Do not access this
# variable outside of this module.
_default_fetcher = None

def getDefaultFetcher():
    """Return the default fetcher instance
    if no fetcher has been set, it will create a default fetcher.

    @return: the default fetcher
    @rtype: HTTPFetcher
    """
    global _default_fetcher

    if _default_fetcher is None:
        setDefaultFetcher(createHTTPFetcher())

    return _default_fetcher

def setDefaultFetcher(fetcher, wrap_exceptions=True):
    """Set the default fetcher

    @param fetcher: The fetcher to use as the default HTTP fetcher
    @type fetcher: HTTPFetcher

    @param wrap_exceptions: Whether to wrap exceptions thrown by the
        fetcher wil HTTPFetchingError so that they may be caught
        easier. By default, exceptions will be wrapped. In general,
        unwrapped fetchers are useful for debugging of fetching errors
        or if your fetcher raises well-known exceptions that you would
        like to catch.
    @type wrap_exceptions: bool
    """
    global _default_fetcher
    if fetcher is None or not wrap_exceptions:
        _default_fetcher = fetcher
    else:
        _default_fetcher = ExceptionWrappingFetcher(fetcher)

def usingCurl():
    """Whether the currently set HTTP fetcher is a Curl HTTP fetcher."""
    return isinstance(getDefaultFetcher(), CurlHTTPFetcher)

class HTTPResponse(object):
    """XXX document attributes"""
    headers = None
    status = None
    body = None
    final_url = None

    def __init__(self, final_url=None, status=None, headers=None, body=None):
        self.final_url = final_url
        self.status = status
        self.headers = headers
        self.body = body

    def __repr__(self):
        return "<%s status %s for %s>" % (self.__class__.__name__,
                                          self.status,
                                          self.final_url)

class HTTPFetcher(object):
    """
    This class is the interface for openid HTTP fetchers.  This
    interface is only important if you need to write a new fetcher for
    some reason.
    """

    def fetch(self, url, body=None, headers=None):
        """
        This performs an HTTP POST or GET, following redirects along
        the way. If a body is specified, then the request will be a
        POST. Otherwise, it will be a GET.


        @param headers: HTTP headers to include with the request
        @type headers: {str:str}

        @return: An object representing the server's HTTP response. If
            there are network or protocol errors, an exception will be
            raised. HTTP error responses, like 404 or 500, do not
            cause exceptions.

        @rtype: L{HTTPResponse}

        @raise Exception: Different implementations will raise
            different errors based on the underlying HTTP library.
        """
        raise NotImplementedError

def _allowedURL(url):
    return url.startswith('http://') or url.startswith('https://')

class HTTPFetchingError(Exception):
    """Exception that is wrapped around all exceptions that are raised
    by the underlying fetcher when using the ExceptionWrappingFetcher

    @ivar why: The exception that caused this exception
    """
    def __init__(self, why=None):
        Exception.__init__(self, why)
        self.why = why

class ExceptionWrappingFetcher(HTTPFetcher):
    """Fetcher that wraps another fetcher, causing all exceptions

    @cvar uncaught_exceptions: Exceptions that should be exposed to the
        user if they are raised by the fetch call
    """

    uncaught_exceptions = (SystemExit, KeyboardInterrupt, MemoryError)

    def __init__(self, fetcher):
        self.fetcher = fetcher

    def fetch(self, *args, **kwargs):
        try:
            return self.fetcher.fetch(*args, **kwargs)
        except self.uncaught_exceptions:
            raise
        except:
            exc_cls, exc_inst = sys.exc_info()[:2]
            if exc_inst is None:
                # string exceptions
                exc_inst = exc_cls

            raise HTTPFetchingError(why=exc_inst)

class Urllib2Fetcher(HTTPFetcher):
    """An C{L{HTTPFetcher}} that uses urllib2.
    """

    # Parameterized for the benefit of testing frameworks, see
    # http://trac.openidenabled.com/trac/ticket/85
    urlopen = staticmethod(urllib2.urlopen)

    def fetch(self, url, body=None, headers=None):
        if not _allowedURL(url):
            raise ValueError('Bad URL scheme: %r' % (url,))

        if headers is None:
            headers = {}

        headers.setdefault(
            'User-Agent',
            "%s Python-urllib/%s" % (USER_AGENT, urllib2.__version__,))

        req = urllib2.Request(url, data=body, headers=headers)
        try:
            f = self.urlopen(req)
            try:
                return self._makeResponse(f)
            finally:
                f.close()
        except urllib2.HTTPError, why:
            try:
                return self._makeResponse(why)
            finally:
                why.close()

    def _makeResponse(self, urllib2_response):
        resp = HTTPResponse()
        resp.body = urllib2_response.read(MAX_RESPONSE_KB * 1024)
        resp.final_url = urllib2_response.geturl()
        resp.headers = dict(urllib2_response.info().items())

        if hasattr(urllib2_response, 'code'):
            resp.status = urllib2_response.code
        else:
            resp.status = 200

        return resp

class HTTPError(HTTPFetchingError):
    """
    This exception is raised by the C{L{CurlHTTPFetcher}} when it
    encounters an exceptional situation fetching a URL.
    """
    pass

# XXX: define what we mean by paranoid, and make sure it is.
class CurlHTTPFetcher(HTTPFetcher):
    """
    An C{L{HTTPFetcher}} that uses pycurl for fetching.
    See U{http://pycurl.sourceforge.net/}.
    """
    ALLOWED_TIME = 20 # seconds

    def __init__(self):
        HTTPFetcher.__init__(self)
        if pycurl is None:
            raise RuntimeError('Cannot find pycurl library')

    def _parseHeaders(self, header_file):
        header_file.seek(0)

        # Remove the status line from the beginning of the input
        unused_http_status_line = header_file.readline()
        lines = [line.strip() for line in header_file]

        # and the blank line from the end
        empty_line = lines.pop()
        if empty_line:
            raise HTTPError("No blank line at end of headers: %r" % (line,))

        headers = {}
        for line in lines:
            try:
                name, value = line.split(':', 1)
            except ValueError:
                raise HTTPError(
                    "Malformed HTTP header line in response: %r" % (line,))

            value = value.strip()

            # HTTP headers are case-insensitive
            name = name.lower()
            headers[name] = value

        return headers

    def _checkURL(self, url):
        # XXX: document that this can be overridden to match desired policy
        # XXX: make sure url is well-formed and routeable
        return _allowedURL(url)

    def fetch(self, url, body=None, headers=None):
        stop = int(time.time()) + self.ALLOWED_TIME
        off = self.ALLOWED_TIME

        if headers is None:
            headers = {}

        headers.setdefault('User-Agent',
                           "%s %s" % (USER_AGENT, pycurl.version,))

        header_list = []
        if headers is not None:
            for header_name, header_value in headers.iteritems():
                header_list.append('%s: %s' % (header_name, header_value))

        c = pycurl.Curl()
        try:
            c.setopt(pycurl.NOSIGNAL, 1)

            if header_list:
                c.setopt(pycurl.HTTPHEADER, header_list)

            # Presence of a body indicates that we should do a POST
            if body is not None:
                c.setopt(pycurl.POST, 1)
                c.setopt(pycurl.POSTFIELDS, body)

            while off > 0:
                if not self._checkURL(url):
                    raise HTTPError("Fetching URL not allowed: %r" % (url,))

                data = cStringIO.StringIO()
                def write_data(chunk):
                    if data.tell() > 1024*MAX_RESPONSE_KB:
                        return 0
                    else:
                        return data.write(chunk)
                    
                response_header_data = cStringIO.StringIO()
                c.setopt(pycurl.WRITEFUNCTION, write_data)
                c.setopt(pycurl.HEADERFUNCTION, response_header_data.write)
                c.setopt(pycurl.TIMEOUT, off)
                c.setopt(pycurl.URL, openid.urinorm.urinorm(url))

                c.perform()

                response_headers = self._parseHeaders(response_header_data)
                code = c.getinfo(pycurl.RESPONSE_CODE)
                if code in [301, 302, 303, 307]:
                    url = response_headers.get('location')
                    if url is None:
                        raise HTTPError(
                            'Redirect (%s) returned without a location' % code)

                    # Redirects are always GETs
                    c.setopt(pycurl.POST, 0)

                    # There is no way to reset POSTFIELDS to empty and
                    # reuse the connection, but we only use it once.
                else:
                    resp = HTTPResponse()
                    resp.headers = response_headers
                    resp.status = code
                    resp.final_url = url
                    resp.body = data.getvalue()
                    return resp

                off = stop - int(time.time())

            raise HTTPError("Timed out fetching: %r" % (url,))
        finally:
            c.close()

class HTTPLib2Fetcher(HTTPFetcher):
    """A fetcher that uses C{httplib2} for performing HTTP
    requests. This implementation supports HTTP caching.

    @see: http://bitworking.org/projects/httplib2/
    """

    def __init__(self, cache=None):
        """@param cache: An object suitable for use as an C{httplib2}
            cache. If a string is passed, it is assumed to be a
            directory name.
        """
        if httplib2 is None:
            raise RuntimeError('Cannot find httplib2 library. '
                               'See http://bitworking.org/projects/httplib2/')

        super(HTTPLib2Fetcher, self).__init__()

        # An instance of the httplib2 object that performs HTTP requests
        self.httplib2 = httplib2.Http(cache)

        # We want httplib2 to raise exceptions for errors, just like
        # the other fetchers.
        self.httplib2.force_exception_to_status_code = False

    def fetch(self, url, body=None, headers=None):
        """Perform an HTTP request

        @raises Exception: Any exception that can be raised by httplib2

        @see: C{L{HTTPFetcher.fetch}}
        """
        if body:
            method = 'POST'
        else:
            method = 'GET'

        if headers is None:
            headers = {}

        # httplib2 doesn't check to make sure that the URL's scheme is
        # 'http' so we do it here.
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('URL is not a HTTP URL: %r' % (url,))

        httplib2_response, content = self.httplib2.request(
            url, method, body=body, headers=headers)

        # Translate the httplib2 response to our HTTP response abstraction

        # When a 400 is returned, there is no "content-location"
        # header set. This seems like a bug to me. I can't think of a
        # case where we really care about the final URL when it is an
        # error response, but being careful about it can't hurt.
        try:
            final_url = httplib2_response['content-location']
        except KeyError:
            # We're assuming that no redirects occurred
            assert not httplib2_response.previous

            # And this should never happen for a successful response
            assert httplib2_response.status != 200
            final_url = url

        return HTTPResponse(
            body=content,
            final_url=final_url,
            headers=dict(httplib2_response.items()),
            status=httplib2_response.status,
            )

########NEW FILE########
__FILENAME__ = kvform
__all__ = ['seqToKV', 'kvToSeq', 'dictToKV', 'kvToDict']

from openid import oidutil

import types

class KVFormError(ValueError):
    pass

def seqToKV(seq, strict=False):
    """Represent a sequence of pairs of strings as newline-terminated
    key:value pairs. The pairs are generated in the order given.

    @param seq: The pairs
    @type seq: [(str, (unicode|str))]

    @return: A string representation of the sequence
    @rtype: str
    """
    def err(msg):
        formatted = 'seqToKV warning: %s: %r' % (msg, seq)
        if strict:
            raise KVFormError(formatted)
        else:
            oidutil.log(formatted)

    lines = []
    for k, v in seq:
        if isinstance(k, types.StringType):
            k = k.decode('UTF8')
        elif not isinstance(k, types.UnicodeType):
            err('Converting key to string: %r' % k)
            k = str(k)

        if '\n' in k:
            raise KVFormError(
                'Invalid input for seqToKV: key contains newline: %r' % (k,))

        if ':' in k:
            raise KVFormError(
                'Invalid input for seqToKV: key contains colon: %r' % (k,))

        if k.strip() != k:
            err('Key has whitespace at beginning or end: %r' % (k,))

        if isinstance(v, types.StringType):
            v = v.decode('UTF8')
        elif not isinstance(v, types.UnicodeType):
            err('Converting value to string: %r' % (v,))
            v = str(v)

        if '\n' in v:
            raise KVFormError(
                'Invalid input for seqToKV: value contains newline: %r' % (v,))

        if v.strip() != v:
            err('Value has whitespace at beginning or end: %r' % (v,))

        lines.append(k + ':' + v + '\n')

    return ''.join(lines).encode('UTF8')

def kvToSeq(data, strict=False):
    """

    After one parse, seqToKV and kvToSeq are inverses, with no warnings::

        seq = kvToSeq(s)
        seqToKV(kvToSeq(seq)) == seq
    """
    def err(msg):
        formatted = 'kvToSeq warning: %s: %r' % (msg, data)
        if strict:
            raise KVFormError(formatted)
        else:
            oidutil.log(formatted)

    lines = data.split('\n')
    if lines[-1]:
        err('Does not end in a newline')
    else:
        del lines[-1]

    pairs = []
    line_num = 0
    for line in lines:
        line_num += 1

        # Ignore blank lines
        if not line.strip():
            continue

        pair = line.split(':', 1)
        if len(pair) == 2:
            k, v = pair
            k_s = k.strip()
            if k_s != k:
                fmt = ('In line %d, ignoring leading or trailing '
                       'whitespace in key %r')
                err(fmt % (line_num, k))

            if not k_s:
                err('In line %d, got empty key' % (line_num,))

            v_s = v.strip()
            if v_s != v:
                fmt = ('In line %d, ignoring leading or trailing '
                       'whitespace in value %r')
                err(fmt % (line_num, v))

            pairs.append((k_s.decode('UTF8'), v_s.decode('UTF8')))
        else:
            err('Line %d does not contain a colon' % line_num)

    return pairs

def dictToKV(d):
    seq = d.items()
    seq.sort()
    return seqToKV(seq)

def kvToDict(s):
    return dict(kvToSeq(s))

########NEW FILE########
__FILENAME__ = message
"""Extension argument processing code
"""
__all__ = ['Message', 'NamespaceMap', 'no_default', 'registerNamespaceAlias',
           'OPENID_NS', 'BARE_NS', 'OPENID1_NS', 'OPENID2_NS', 'SREG_URI',
           'IDENTIFIER_SELECT']

import copy
import warnings
import urllib

from openid import oidutil
from openid import kvform
try:
    ElementTree = oidutil.importElementTree()
except ImportError:
    # No elementtree found, so give up, but don't fail to import,
    # since we have fallbacks.
    ElementTree = None

# This doesn't REALLY belong here, but where is better?
IDENTIFIER_SELECT = 'http://specs.openid.net/auth/2.0/identifier_select'

# URI for Simple Registration extension, the only commonly deployed
# OpenID 1.x extension, and so a special case
SREG_URI = 'http://openid.net/sreg/1.0'

# The OpenID 1.X namespace URI
OPENID1_NS = 'http://openid.net/signon/1.0'
THE_OTHER_OPENID1_NS = 'http://openid.net/signon/1.1'

OPENID1_NAMESPACES = OPENID1_NS, THE_OTHER_OPENID1_NS

# The OpenID 2.0 namespace URI
OPENID2_NS = 'http://specs.openid.net/auth/2.0'

# The namespace consisting of pairs with keys that are prefixed with
# "openid."  but not in another namespace.
NULL_NAMESPACE = oidutil.Symbol('Null namespace')

# The null namespace, when it is an allowed OpenID namespace
OPENID_NS = oidutil.Symbol('OpenID namespace')

# The top-level namespace, excluding all pairs with keys that start
# with "openid."
BARE_NS = oidutil.Symbol('Bare namespace')

# Limit, in bytes, of identity provider and return_to URLs, including
# response payload.  See OpenID 1.1 specification, Appendix D.
OPENID1_URL_LIMIT = 2047

# All OpenID protocol fields.  Used to check namespace aliases.
OPENID_PROTOCOL_FIELDS = [
    'ns', 'mode', 'error', 'return_to', 'contact', 'reference',
    'signed', 'assoc_type', 'session_type', 'dh_modulus', 'dh_gen',
    'dh_consumer_public', 'claimed_id', 'identity', 'realm',
    'invalidate_handle', 'op_endpoint', 'response_nonce', 'sig',
    'assoc_handle', 'trust_root', 'openid',
    ]

class UndefinedOpenIDNamespace(ValueError):
    """Raised if the generic OpenID namespace is accessed when there
    is no OpenID namespace set for this message."""

class InvalidOpenIDNamespace(ValueError):
    """Raised if openid.ns is not a recognized value.

    For recognized values, see L{Message.allowed_openid_namespaces}
    """
    def __str__(self):
        s = "Invalid OpenID Namespace"
        if self.args:
            s += " %r" % (self.args[0],)
        return s


# Sentinel used for Message implementation to indicate that getArg
# should raise an exception instead of returning a default.
no_default = object()

# Global namespace / alias registration map.  See
# registerNamespaceAlias.
registered_aliases = {}

class NamespaceAliasRegistrationError(Exception):
    """
    Raised when an alias or namespace URI has already been registered.
    """
    pass

def registerNamespaceAlias(namespace_uri, alias):
    """
    Registers a (namespace URI, alias) mapping in a global namespace
    alias map.  Raises NamespaceAliasRegistrationError if either the
    namespace URI or alias has already been registered with a
    different value.  This function is required if you want to use a
    namespace with an OpenID 1 message.
    """
    global registered_aliases

    if registered_aliases.get(alias) == namespace_uri:
        return

    if namespace_uri in registered_aliases.values():
        raise NamespaceAliasRegistrationError, \
              'Namespace uri %r already registered' % (namespace_uri,)

    if alias in registered_aliases:
        raise NamespaceAliasRegistrationError, \
              'Alias %r already registered' % (alias,)

    registered_aliases[alias] = namespace_uri

class Message(object):
    """
    In the implementation of this object, None represents the global
    namespace as well as a namespace with no key.

    @cvar namespaces: A dictionary specifying specific
        namespace-URI to alias mappings that should be used when
        generating namespace aliases.

    @ivar ns_args: two-level dictionary of the values in this message,
        grouped by namespace URI. The first level is the namespace
        URI.
    """

    allowed_openid_namespaces = [OPENID1_NS, THE_OTHER_OPENID1_NS, OPENID2_NS]

    def __init__(self, openid_namespace=None):
        """Create an empty Message.

        @raises InvalidOpenIDNamespace: if openid_namespace is not in
            L{Message.allowed_openid_namespaces}
        """
        self.args = {}
        self.namespaces = NamespaceMap()
        if openid_namespace is None:
            self._openid_ns_uri = None
        else:
            implicit = openid_namespace in OPENID1_NAMESPACES
            self.setOpenIDNamespace(openid_namespace, implicit)

    def fromPostArgs(cls, args):
        """Construct a Message containing a set of POST arguments.

        """
        self = cls()

        # Partition into "openid." args and bare args
        openid_args = {}
        for key, value in args.items():
            if isinstance(value, list):
                raise TypeError("query dict must have one value for each key, "
                                "not lists of values.  Query is %r" % (args,))


            try:
                prefix, rest = key.split('.', 1)
            except ValueError:
                prefix = None

            if prefix != 'openid':
                self.args[(BARE_NS, key)] = value
            else:
                openid_args[rest] = value

        self._fromOpenIDArgs(openid_args)

        return self

    fromPostArgs = classmethod(fromPostArgs)

    def fromOpenIDArgs(cls, openid_args):
        """Construct a Message from a parsed KVForm message.

        @raises InvalidOpenIDNamespace: if openid.ns is not in
            L{Message.allowed_openid_namespaces}
        """
        self = cls()
        self._fromOpenIDArgs(openid_args)
        return self

    fromOpenIDArgs = classmethod(fromOpenIDArgs)

    def _fromOpenIDArgs(self, openid_args):
        ns_args = []

        # Resolve namespaces
        for rest, value in openid_args.iteritems():
            try:
                ns_alias, ns_key = rest.split('.', 1)
            except ValueError:
                ns_alias = NULL_NAMESPACE
                ns_key = rest

            if ns_alias == 'ns':
                self.namespaces.addAlias(value, ns_key)
            elif ns_alias == NULL_NAMESPACE and ns_key == 'ns':
                # null namespace
                self.setOpenIDNamespace(value, False)
            else:
                ns_args.append((ns_alias, ns_key, value))

        # Implicitly set an OpenID namespace definition (OpenID 1)
        if not self.getOpenIDNamespace():
            self.setOpenIDNamespace(OPENID1_NS, True)

        # Actually put the pairs into the appropriate namespaces
        for (ns_alias, ns_key, value) in ns_args:
            ns_uri = self.namespaces.getNamespaceURI(ns_alias)
            if ns_uri is None:
                # we found a namespaced arg without a namespace URI defined
                ns_uri = self._getDefaultNamespace(ns_alias)
                if ns_uri is None:
                    ns_uri = self.getOpenIDNamespace()
                    ns_key = '%s.%s' % (ns_alias, ns_key)
                else:
                    self.namespaces.addAlias(ns_uri, ns_alias, implicit=True)

            self.setArg(ns_uri, ns_key, value)

    def _getDefaultNamespace(self, mystery_alias):
        """OpenID 1 compatibility: look for a default namespace URI to
        use for this alias."""
        global registered_aliases
        # Only try to map an alias to a default if it's an
        # OpenID 1.x message.
        if self.isOpenID1():
            return registered_aliases.get(mystery_alias)
        else:
            return None

    def setOpenIDNamespace(self, openid_ns_uri, implicit):
        """Set the OpenID namespace URI used in this message.

        @raises InvalidOpenIDNamespace: if the namespace is not in
            L{Message.allowed_openid_namespaces}
        """
        if openid_ns_uri not in self.allowed_openid_namespaces:
            raise InvalidOpenIDNamespace(openid_ns_uri)

        self.namespaces.addAlias(openid_ns_uri, NULL_NAMESPACE, implicit)
        self._openid_ns_uri = openid_ns_uri

    def getOpenIDNamespace(self):
        return self._openid_ns_uri

    def isOpenID1(self):
        return self.getOpenIDNamespace() in OPENID1_NAMESPACES

    def isOpenID2(self):
        return self.getOpenIDNamespace() == OPENID2_NS

    def fromKVForm(cls, kvform_string):
        """Create a Message from a KVForm string"""
        return cls.fromOpenIDArgs(kvform.kvToDict(kvform_string))

    fromKVForm = classmethod(fromKVForm)

    def copy(self):
        return copy.deepcopy(self)

    def toPostArgs(self):
        """Return all arguments with openid. in front of namespaced arguments.
        """
        args = {}

        # Add namespace definitions to the output
        for ns_uri, alias in self.namespaces.iteritems():
            if self.namespaces.isImplicit(ns_uri):
                continue
            if alias == NULL_NAMESPACE:
                ns_key = 'openid.ns'
            else:
                ns_key = 'openid.ns.' + alias
            args[ns_key] = ns_uri

        for (ns_uri, ns_key), value in self.args.iteritems():
            key = self.getKey(ns_uri, ns_key)
            args[key] = value.encode('UTF-8')

        return args

    def toArgs(self):
        """Return all namespaced arguments, failing if any
        non-namespaced arguments exist."""
        # FIXME - undocumented exception
        post_args = self.toPostArgs()
        kvargs = {}
        for k, v in post_args.iteritems():
            if not k.startswith('openid.'):
                raise ValueError(
                    'This message can only be encoded as a POST, because it '
                    'contains arguments that are not prefixed with "openid."')
            else:
                kvargs[k[7:]] = v

        return kvargs

    def toFormMarkup(self, action_url, form_tag_attrs=None,
                     submit_text="Continue"):
        """Generate HTML form markup that contains the values in this
        message, to be HTTP POSTed as x-www-form-urlencoded UTF-8.

        @param action_url: The URL to which the form will be POSTed
        @type action_url: str

        @param form_tag_attrs: Dictionary of attributes to be added to
            the form tag. 'accept-charset' and 'enctype' have defaults
            that can be overridden. If a value is supplied for
            'action' or 'method', it will be replaced.
        @type form_tag_attrs: {unicode: unicode}

        @param submit_text: The text that will appear on the submit
            button for this form.
        @type submit_text: unicode

        @returns: A string containing (X)HTML markup for a form that
            encodes the values in this Message object.
        @rtype: str or unicode
        """
        if ElementTree is None:
            raise RuntimeError('This function requires ElementTree.')

        assert action_url is not None

        form = ElementTree.Element('form')

        if form_tag_attrs:
            for name, attr in form_tag_attrs.iteritems():
                form.attrib[name] = attr

        form.attrib['action'] = action_url
        form.attrib['method'] = 'post'
        form.attrib['accept-charset'] = 'UTF-8'
        form.attrib['enctype'] = 'application/x-www-form-urlencoded'

        for name, value in self.toPostArgs().iteritems():
            attrs = {'type': 'hidden',
                     'name': name,
                     'value': value}
            form.append(ElementTree.Element('input', attrs))

        submit = ElementTree.Element(
                'input', {'type':'submit', 'value':submit_text})
        form.append(submit)

        return ElementTree.tostring(form)

    def toURL(self, base_url):
        """Generate a GET URL with the parameters in this message
        attached as query parameters."""
        return oidutil.appendArgs(base_url, self.toPostArgs())

    def toKVForm(self):
        """Generate a KVForm string that contains the parameters in
        this message. This will fail if the message contains arguments
        outside of the 'openid.' prefix.
        """
        return kvform.dictToKV(self.toArgs())

    def toURLEncoded(self):
        """Generate an x-www-urlencoded string"""
        args = self.toPostArgs().items()
        args.sort()
        return urllib.urlencode(args)

    def _fixNS(self, namespace):
        """Convert an input value into the internally used values of
        this object

        @param namespace: The string or constant to convert
        @type namespace: str or unicode or BARE_NS or OPENID_NS
        """
        if namespace == OPENID_NS:
            if self._openid_ns_uri is None:
                raise UndefinedOpenIDNamespace('OpenID namespace not set')
            else:
                namespace = self._openid_ns_uri

        if namespace != BARE_NS and type(namespace) not in [str, unicode]:
            raise TypeError(
                "Namespace must be BARE_NS, OPENID_NS or a string. got %r"
                % (namespace,))

        if namespace != BARE_NS and ':' not in namespace:
            fmt = 'OpenID 2.0 namespace identifiers SHOULD be URIs. Got %r'
            warnings.warn(fmt % (namespace,), DeprecationWarning)

            if namespace == 'sreg':
                fmt = 'Using %r instead of "sreg" as namespace'
                warnings.warn(fmt % (SREG_URI,), DeprecationWarning,)
                return SREG_URI

        return namespace

    def hasKey(self, namespace, ns_key):
        namespace = self._fixNS(namespace)
        return (namespace, ns_key) in self.args

    def getKey(self, namespace, ns_key):
        """Get the key for a particular namespaced argument"""
        namespace = self._fixNS(namespace)
        if namespace == BARE_NS:
            return ns_key

        ns_alias = self.namespaces.getAlias(namespace)

        # No alias is defined, so no key can exist
        if ns_alias is None:
            return None

        if ns_alias == NULL_NAMESPACE:
            tail = ns_key
        else:
            tail = '%s.%s' % (ns_alias, ns_key)

        return 'openid.' + tail

    def getArg(self, namespace, key, default=None):
        """Get a value for a namespaced key.

        @param namespace: The namespace in the message for this key
        @type namespace: str

        @param key: The key to get within this namespace
        @type key: str

        @param default: The value to use if this key is absent from
            this message. Using the special value
            openid.message.no_default will result in this method
            raising a KeyError instead of returning the default.

        @rtype: str or the type of default
        @raises KeyError: if default is no_default
        @raises UndefinedOpenIDNamespace: if the message has not yet
            had an OpenID namespace set
        """
        namespace = self._fixNS(namespace)
        args_key = (namespace, key)
        try:
            return self.args[args_key]
        except KeyError:
            if default is no_default:
                raise KeyError((namespace, key))
            else:
                return default

    def getArgs(self, namespace):
        """Get the arguments that are defined for this namespace URI

        @returns: mapping from namespaced keys to values
        @returntype: dict
        """
        namespace = self._fixNS(namespace)
        return dict([
            (ns_key, value)
            for ((pair_ns, ns_key), value)
            in self.args.iteritems()
            if pair_ns == namespace
            ])

    def updateArgs(self, namespace, updates):
        """Set multiple key/value pairs in one call

        @param updates: The values to set
        @type updates: {unicode:unicode}
        """
        namespace = self._fixNS(namespace)
        for k, v in updates.iteritems():
            self.setArg(namespace, k, v)

    def setArg(self, namespace, key, value):
        """Set a single argument in this namespace"""
        assert key is not None
        assert value is not None
        namespace = self._fixNS(namespace)
        self.args[(namespace, key)] = value
        if not (namespace is BARE_NS):
            self.namespaces.add(namespace)

    def delArg(self, namespace, key):
        namespace = self._fixNS(namespace)
        del self.args[(namespace, key)]

    def __repr__(self):
        return "<%s.%s %r>" % (self.__class__.__module__,
                               self.__class__.__name__,
                               self.args)

    def __eq__(self, other):
        return self.args == other.args


    def __ne__(self, other):
        return not (self == other)


    def getAliasedArg(self, aliased_key, default=None):
        if aliased_key == 'ns':
            return self.getOpenIDNamespace()

        if aliased_key.startswith('ns.'):
            uri = self.namespaces.getNamespaceURI(aliased_key[3:])
            if uri is None:
                if default == no_default:
                    raise KeyError
                else:
                    return default
            else:
                return uri

        try:
            alias, key = aliased_key.split('.', 1)
        except ValueError:
            # need more than x values to unpack
            ns = None
        else:
            ns = self.namespaces.getNamespaceURI(alias)

        if ns is None:
            key = aliased_key
            ns = self.getOpenIDNamespace()

        return self.getArg(ns, key, default)

class NamespaceMap(object):
    """Maintains a bijective map between namespace uris and aliases.
    """
    def __init__(self):
        self.alias_to_namespace = {}
        self.namespace_to_alias = {}
        self.implicit_namespaces = []

    def getAlias(self, namespace_uri):
        return self.namespace_to_alias.get(namespace_uri)

    def getNamespaceURI(self, alias):
        return self.alias_to_namespace.get(alias)

    def iterNamespaceURIs(self):
        """Return an iterator over the namespace URIs"""
        return iter(self.namespace_to_alias)

    def iterAliases(self):
        """Return an iterator over the aliases"""
        return iter(self.alias_to_namespace)

    def iteritems(self):
        """Iterate over the mapping

        @returns: iterator of (namespace_uri, alias)
        """
        return self.namespace_to_alias.iteritems()

    def addAlias(self, namespace_uri, desired_alias, implicit=False):
        """Add an alias from this namespace URI to the desired alias
        """
        # Check that desired_alias is not an openid protocol field as
        # per the spec.
        assert desired_alias not in OPENID_PROTOCOL_FIELDS, \
               "%r is not an allowed namespace alias" % (desired_alias,)

        # Check that desired_alias does not contain a period as per
        # the spec.
        if type(desired_alias) in [str, unicode]:
            assert '.' not in desired_alias, \
                   "%r must not contain a dot" % (desired_alias,)

        # Check that there is not a namespace already defined for
        # the desired alias
        current_namespace_uri = self.alias_to_namespace.get(desired_alias)
        if (current_namespace_uri is not None
            and current_namespace_uri != namespace_uri):

            fmt = ('Cannot map %r to alias %r. '
                   '%r is already mapped to alias %r')

            msg = fmt % (
                namespace_uri,
                desired_alias,
                current_namespace_uri,
                desired_alias)
            raise KeyError(msg)

        # Check that there is not already a (different) alias for
        # this namespace URI
        alias = self.namespace_to_alias.get(namespace_uri)
        if alias is not None and alias != desired_alias:
            fmt = ('Cannot map %r to alias %r. '
                   'It is already mapped to alias %r')
            raise KeyError(fmt % (namespace_uri, desired_alias, alias))

        assert (desired_alias == NULL_NAMESPACE or
                type(desired_alias) in [str, unicode]), repr(desired_alias)
        assert namespace_uri not in self.implicit_namespaces
        self.alias_to_namespace[desired_alias] = namespace_uri
        self.namespace_to_alias[namespace_uri] = desired_alias
        if implicit:
            self.implicit_namespaces.append(namespace_uri)
        return desired_alias

    def add(self, namespace_uri):
        """Add this namespace URI to the mapping, without caring what
        alias it ends up with"""
        # See if this namespace is already mapped to an alias
        alias = self.namespace_to_alias.get(namespace_uri)
        if alias is not None:
            return alias

        # Fall back to generating a numerical alias
        i = 0
        while True:
            alias = 'ext' + str(i)
            try:
                self.addAlias(namespace_uri, alias)
            except KeyError:
                i += 1
            else:
                return alias

        assert False, "Not reached"

    def isDefined(self, namespace_uri):
        return namespace_uri in self.namespace_to_alias

    def __contains__(self, namespace_uri):
        return self.isDefined(namespace_uri)

    def isImplicit(self, namespace_uri):
        return namespace_uri in self.implicit_namespaces

########NEW FILE########
__FILENAME__ = oidutil
"""This module contains general utility code that is used throughout
the library.

For users of this library, the C{L{log}} function is probably the most
interesting.
"""

__all__ = ['log', 'appendArgs', 'toBase64', 'fromBase64', 'autoSubmitHTML']

import binascii
import sys
import urlparse

from urllib import urlencode

elementtree_modules = [
    'lxml.etree',
    'xml.etree.cElementTree',
    'xml.etree.ElementTree',
    'cElementTree',
    'elementtree.ElementTree',
    ]

def autoSubmitHTML(form, title='OpenID transaction in progress'):
    return """
<html>
<head>
  <title>%s</title>
</head>
<body onload="document.forms[0].submit();">
%s
<script>
var elements = document.forms[0].elements;
for (var i = 0; i < elements.length; i++) {
  elements[i].style.display = "none";
}
</script>
</body>
</html>
""" % (title, form)

def importElementTree(module_names=None):
    """Find a working ElementTree implementation, trying the standard
    places that such a thing might show up.

    >>> ElementTree = importElementTree()

    @param module_names: The names of modules to try to use as
        ElementTree. Defaults to C{L{elementtree_modules}}

    @returns: An ElementTree module
    """
    if module_names is None:
        module_names = elementtree_modules

    for mod_name in module_names:
        try:
            ElementTree = __import__(mod_name, None, None, ['unused'])
        except ImportError:
            pass
        else:
            # Make sure it can actually parse XML
            try:
                ElementTree.XML('<unused/>')
            except (SystemExit, MemoryError, AssertionError):
                raise
            except:
                why = sys.exc_info()[1]
                log('Not using ElementTree library %r because it failed to '
                    'parse a trivial document: %s' % (mod_name, why))
            else:
                return ElementTree
    else:
        raise ImportError('No ElementTree library found. '
                          'You may need to install one. '
                          'Tried importing %r' % (module_names,)
                          )

def log(message, level=0):
    """Handle a log message from the OpenID library.

    This implementation writes the string it to C{sys.stderr},
    followed by a newline.

    Currently, the library does not use the second parameter to this
    function, but that may change in the future.

    To install your own logging hook::

      from openid import oidutil

      def myLoggingFunction(message, level):
          ...

      oidutil.log = myLoggingFunction

    @param message: A string containing a debugging message from the
        OpenID library
    @type message: str

    @param level: The severity of the log message. This parameter is
        currently unused, but in the future, the library may indicate
        more important information with a higher level value.
    @type level: int or None

    @returns: Nothing.
    """

    sys.stderr.write(message)
    sys.stderr.write('\n')

def appendArgs(url, args):
    """Append query arguments to a HTTP(s) URL. If the URL already has
    query arguemtns, these arguments will be added, and the existing
    arguments will be preserved. Duplicate arguments will not be
    detected or collapsed (both will appear in the output).

    @param url: The url to which the arguments will be appended
    @type url: str

    @param args: The query arguments to add to the URL. If a
        dictionary is passed, the items will be sorted before
        appending them to the URL. If a sequence of pairs is passed,
        the order of the sequence will be preserved.
    @type args: A dictionary from string to string, or a sequence of
        pairs of strings.

    @returns: The URL with the parameters added
    @rtype: str
    """
    if hasattr(args, 'items'):
        args = args.items()
        args.sort()
    else:
        args = list(args)

    if len(args) == 0:
        return url

    if '?' in url:
        sep = '&'
    else:
        sep = '?'

    # Map unicode to UTF-8 if present. Do not make any assumptions
    # about the encodings of plain bytes (str).
    i = 0
    for k, v in args:
        if type(k) is not str:
            k = k.encode('UTF-8')

        if type(v) is not str:
            v = v.encode('UTF-8')

        args[i] = (k, v)
        i += 1

    return '%s%s%s' % (url, sep, urlencode(args))

def toBase64(s):
    """Represent string s as base64, omitting newlines"""
    return binascii.b2a_base64(s)[:-1]

def fromBase64(s):
    try:
        return binascii.a2b_base64(s)
    except binascii.Error, why:
        # Convert to a common exception type
        raise ValueError(why[0])

class Symbol(object):
    """This class implements an object that compares equal to others
    of the same type that have the same name. These are distict from
    str or unicode objects.
    """

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return type(self) is type(other) and self.name == other.name

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self.__class__, self.name))
   
    def __repr__(self):
        return '<Symbol %s>' % (self.name,)

########NEW FILE########
__FILENAME__ = server
# -*- test-case-name: openid.test.test_server -*-
"""OpenID server protocol and logic.

Overview
========

    An OpenID server must perform three tasks:

        1. Examine the incoming request to determine its nature and validity.

        2. Make a decision about how to respond to this request.

        3. Format the response according to the protocol.

    The first and last of these tasks may performed by
    the L{decodeRequest<Server.decodeRequest>} and
    L{encodeResponse<Server.encodeResponse>} methods of the
    L{Server} object.  Who gets to do the intermediate task -- deciding
    how to respond to the request -- will depend on what type of request it
    is.

    If it's a request to authenticate a user (a X{C{checkid_setup}} or
    X{C{checkid_immediate}} request), you need to decide if you will assert
    that this user may claim the identity in question.  Exactly how you do
    that is a matter of application policy, but it generally involves making
    sure the user has an account with your system and is logged in, checking
    to see if that identity is hers to claim, and verifying with the user that
    she does consent to releasing that information to the party making the
    request.

    Examine the properties of the L{CheckIDRequest} object, optionally
    check L{CheckIDRequest.returnToVerified}, and and when you've come
    to a decision, form a response by calling L{CheckIDRequest.answer}.

    Other types of requests relate to establishing associations between client
    and server and verifying the authenticity of previous communications.
    L{Server} contains all the logic and data necessary to respond to
    such requests; just pass the request to L{Server.handleRequest}.


OpenID Extensions
=================

    Do you want to provide other information for your users
    in addition to authentication?  Version 2.0 of the OpenID
    protocol allows consumers to add extensions to their requests.
    For example, with sites using the U{Simple Registration
    Extension<http://openid.net/specs/openid-simple-registration-extension-1_0.html>},
    a user can agree to have their nickname and e-mail address sent to a
    site when they sign up.

    Since extensions do not change the way OpenID authentication works,
    code to handle extension requests may be completely separate from the
    L{OpenIDRequest} class here.  But you'll likely want data sent back by
    your extension to be signed.  L{OpenIDResponse} provides methods with
    which you can add data to it which can be signed with the other data in
    the OpenID signature.

    For example::

        # when request is a checkid_* request
        response = request.answer(True)
        # this will a signed 'openid.sreg.timezone' parameter to the response
        # as well as a namespace declaration for the openid.sreg namespace
        response.fields.setArg('http://openid.net/sreg/1.0', 'timezone', 'America/Los_Angeles')

    There are helper modules for a number of extensions, including
    L{Attribute Exchange<openid.extensions.ax>},
    L{PAPE<openid.extensions.pape>}, and
    L{Simple Registration<openid.extensions.sreg>} in the L{openid.extensions}
    package.

Stores
======

    The OpenID server needs to maintain state between requests in order
    to function.  Its mechanism for doing this is called a store.  The
    store interface is defined in C{L{openid.store.interface.OpenIDStore}}.
    Additionally, several concrete store implementations are provided, so that
    most sites won't need to implement a custom store.  For a store backed
    by flat files on disk, see C{L{openid.store.filestore.FileOpenIDStore}}.
    For stores based on MySQL or SQLite, see the C{L{openid.store.sqlstore}}
    module.


Upgrading
=========

From 1.0 to 1.1
---------------

    The keys by which a server looks up associations in its store have changed
    in version 1.2 of this library.  If your store has entries created from
    version 1.0 code, you should empty it.

From 1.1 to 2.0
---------------

    One of the additions to the OpenID protocol was a specified nonce
    format for one-way nonces.  As a result, the nonce table in the store
    has changed.  You'll need to run contrib/upgrade-store-1.1-to-2.0 to
    upgrade your store, or you'll encounter errors about the wrong number
    of columns in the oid_nonces table.

    If you've written your own custom store or code that interacts
    directly with it, you'll need to review the change notes in
    L{openid.store.interface}.

@group Requests: OpenIDRequest, AssociateRequest, CheckIDRequest,
    CheckAuthRequest

@group Responses: OpenIDResponse

@group HTTP Codes: HTTP_OK, HTTP_REDIRECT, HTTP_ERROR

@group Response Encodings: ENCODE_KVFORM, ENCODE_HTML_FORM, ENCODE_URL
"""

import time, warnings
from copy import deepcopy

from openid import cryptutil
from openid import oidutil
from openid import kvform
from openid.dh import DiffieHellman
from openid.store.nonce import mkNonce
from openid.server.trustroot import TrustRoot, verifyReturnTo
from openid.association import Association, default_negotiator, getSecretSize
from openid.message import Message, InvalidOpenIDNamespace, \
     OPENID_NS, OPENID2_NS, IDENTIFIER_SELECT, OPENID1_URL_LIMIT
from openid.urinorm import urinorm

HTTP_OK = 200
HTTP_REDIRECT = 302
HTTP_ERROR = 400

BROWSER_REQUEST_MODES = ['checkid_setup', 'checkid_immediate']

ENCODE_KVFORM = ('kvform',)
ENCODE_URL = ('URL/redirect',)
ENCODE_HTML_FORM = ('HTML form',)

UNUSED = None

class OpenIDRequest(object):
    """I represent an incoming OpenID request.

    @cvar mode: the C{X{openid.mode}} of this request.
    @type mode: str
    """
    mode = None


class CheckAuthRequest(OpenIDRequest):
    """A request to verify the validity of a previous response.

    @cvar mode: "X{C{check_authentication}}"
    @type mode: str

    @ivar assoc_handle: The X{association handle} the response was signed with.
    @type assoc_handle: str
    @ivar signed: The message with the signature which wants checking.
    @type signed: L{Message}

    @ivar invalidate_handle: An X{association handle} the client is asking
        about the validity of.  Optional, may be C{None}.
    @type invalidate_handle: str

    @see: U{OpenID Specs, Mode: check_authentication
        <http://openid.net/specs.bml#mode-check_authentication>}
    """
    mode = "check_authentication"

    required_fields = ["identity", "return_to", "response_nonce"]

    def __init__(self, assoc_handle, signed, invalidate_handle=None):
        """Construct me.

        These parameters are assigned directly as class attributes, see
        my L{class documentation<CheckAuthRequest>} for their descriptions.

        @type assoc_handle: str
        @type signed: L{Message}
        @type invalidate_handle: str
        """
        self.assoc_handle = assoc_handle
        self.signed = signed
        self.invalidate_handle = invalidate_handle
        self.namespace = OPENID2_NS


    def fromMessage(klass, message, op_endpoint=UNUSED):
        """Construct me from an OpenID Message.

        @param message: An OpenID check_authentication Message
        @type message: L{openid.message.Message}

        @returntype: L{CheckAuthRequest}
        """
        self = klass.__new__(klass)
        self.message = message
        self.namespace = message.getOpenIDNamespace()
        self.assoc_handle = message.getArg(OPENID_NS, 'assoc_handle')
        self.sig = message.getArg(OPENID_NS, 'sig')

        if (self.assoc_handle is None or
            self.sig is None):
            fmt = "%s request missing required parameter from message %s"
            raise ProtocolError(
                message, text=fmt % (self.mode, message))

        self.invalidate_handle = message.getArg(OPENID_NS, 'invalidate_handle')

        self.signed = message.copy()
        # openid.mode is currently check_authentication because
        # that's the mode of this request.  But the signature
        # was made on something with a different openid.mode.
        # http://article.gmane.org/gmane.comp.web.openid.general/537
        if self.signed.hasKey(OPENID_NS, "mode"):
            self.signed.setArg(OPENID_NS, "mode", "id_res")

        return self

    fromMessage = classmethod(fromMessage)

    def answer(self, signatory):
        """Respond to this request.

        Given a L{Signatory}, I can check the validity of the signature and
        the X{C{invalidate_handle}}.

        @param signatory: The L{Signatory} to use to check the signature.
        @type signatory: L{Signatory}

        @returns: A response with an X{C{is_valid}} (and, if
           appropriate X{C{invalidate_handle}}) field.
        @returntype: L{OpenIDResponse}
        """
        is_valid = signatory.verify(self.assoc_handle, self.signed)
        # Now invalidate that assoc_handle so it this checkAuth message cannot
        # be replayed.
        signatory.invalidate(self.assoc_handle, dumb=True)
        response = OpenIDResponse(self)
        valid_str = (is_valid and "true") or "false"
        response.fields.setArg(OPENID_NS, 'is_valid', valid_str)

        if self.invalidate_handle:
            assoc = signatory.getAssociation(self.invalidate_handle, dumb=False)
            if not assoc:
                response.fields.setArg(
                    OPENID_NS, 'invalidate_handle', self.invalidate_handle)
        return response


    def __str__(self):
        if self.invalidate_handle:
            ih = " invalidate? %r" % (self.invalidate_handle,)
        else:
            ih = ""
        s = "<%s handle: %r sig: %r: signed: %r%s>" % (
            self.__class__.__name__, self.assoc_handle,
            self.sig, self.signed, ih)
        return s


class PlainTextServerSession(object):
    """An object that knows how to handle association requests with no
    session type.

    @cvar session_type: The session_type for this association
        session. There is no type defined for plain-text in the OpenID
        specification, so we use 'no-encryption'.
    @type session_type: str

    @see: U{OpenID Specs, Mode: associate
        <http://openid.net/specs.bml#mode-associate>}
    @see: AssociateRequest
    """
    session_type = 'no-encryption'
    allowed_assoc_types = ['HMAC-SHA1', 'HMAC-SHA256']

    def fromMessage(cls, unused_request):
        return cls()

    fromMessage = classmethod(fromMessage)

    def answer(self, secret):
        return {'mac_key': oidutil.toBase64(secret)}


class DiffieHellmanSHA1ServerSession(object):
    """An object that knows how to handle association requests with the
    Diffie-Hellman session type.

    @cvar session_type: The session_type for this association
        session.
    @type session_type: str

    @ivar dh: The Diffie-Hellman algorithm values for this request
    @type dh: DiffieHellman

    @ivar consumer_pubkey: The public key sent by the consumer in the
        associate request
    @type consumer_pubkey: long

    @see: U{OpenID Specs, Mode: associate
        <http://openid.net/specs.bml#mode-associate>}
    @see: AssociateRequest
    """
    session_type = 'DH-SHA1'
    hash_func = staticmethod(cryptutil.sha1)
    allowed_assoc_types = ['HMAC-SHA1']

    def __init__(self, dh, consumer_pubkey):
        self.dh = dh
        self.consumer_pubkey = consumer_pubkey

    def fromMessage(cls, message):
        """
        @param message: The associate request message
        @type message: openid.message.Message

        @returntype: L{DiffieHellmanSHA1ServerSession}

        @raises ProtocolError: When parameters required to establish the
            session are missing.
        """
        dh_modulus = message.getArg(OPENID_NS, 'dh_modulus')
        dh_gen = message.getArg(OPENID_NS, 'dh_gen')
        if (dh_modulus is None and dh_gen is not None or
            dh_gen is None and dh_modulus is not None):

            if dh_modulus is None:
                missing = 'modulus'
            else:
                missing = 'generator'

            raise ProtocolError(message,
                                'If non-default modulus or generator is '
                                'supplied, both must be supplied. Missing %s'
                                % (missing,))

        if dh_modulus or dh_gen:
            dh_modulus = cryptutil.base64ToLong(dh_modulus)
            dh_gen = cryptutil.base64ToLong(dh_gen)
            dh = DiffieHellman(dh_modulus, dh_gen)
        else:
            dh = DiffieHellman.fromDefaults()

        consumer_pubkey = message.getArg(OPENID_NS, 'dh_consumer_public')
        if consumer_pubkey is None:
            raise ProtocolError(message, "Public key for DH-SHA1 session "
                                "not found in message %s" % (message,))

        consumer_pubkey = cryptutil.base64ToLong(consumer_pubkey)

        return cls(dh, consumer_pubkey)

    fromMessage = classmethod(fromMessage)

    def answer(self, secret):
        mac_key = self.dh.xorSecret(self.consumer_pubkey,
                                    secret,
                                    self.hash_func)
        return {
            'dh_server_public': cryptutil.longToBase64(self.dh.public),
            'enc_mac_key': oidutil.toBase64(mac_key),
            }

class DiffieHellmanSHA256ServerSession(DiffieHellmanSHA1ServerSession):
    session_type = 'DH-SHA256'
    hash_func = staticmethod(cryptutil.sha256)
    allowed_assoc_types = ['HMAC-SHA256']

class AssociateRequest(OpenIDRequest):
    """A request to establish an X{association}.

    @cvar mode: "X{C{check_authentication}}"
    @type mode: str

    @ivar assoc_type: The type of association.  The protocol currently only
        defines one value for this, "X{C{HMAC-SHA1}}".
    @type assoc_type: str

    @ivar session: An object that knows how to handle association
        requests of a certain type.

    @see: U{OpenID Specs, Mode: associate
        <http://openid.net/specs.bml#mode-associate>}
    """

    mode = "associate"

    session_classes = {
        'no-encryption': PlainTextServerSession,
        'DH-SHA1': DiffieHellmanSHA1ServerSession,
        'DH-SHA256': DiffieHellmanSHA256ServerSession,
        }

    def __init__(self, session, assoc_type):
        """Construct me.

        The session is assigned directly as a class attribute. See my
        L{class documentation<AssociateRequest>} for its description.
        """
        super(AssociateRequest, self).__init__()
        self.session = session
        self.assoc_type = assoc_type
        self.namespace = OPENID2_NS


    def fromMessage(klass, message, op_endpoint=UNUSED):
        """Construct me from an OpenID Message.

        @param message: The OpenID associate request
        @type message: openid.message.Message

        @returntype: L{AssociateRequest}
        """
        if message.isOpenID1():
            session_type = message.getArg(OPENID_NS, 'session_type')
            if session_type == 'no-encryption':
                oidutil.log('Received OpenID 1 request with a no-encryption '
                            'assocaition session type. Continuing anyway.')
            elif not session_type:
                session_type = 'no-encryption'
        else:
            session_type = message.getArg(OPENID2_NS, 'session_type')
            if session_type is None:
                raise ProtocolError(message,
                                    text="session_type missing from request")

        try:
            session_class = klass.session_classes[session_type]
        except KeyError:
            raise ProtocolError(message,
                                "Unknown session type %r" % (session_type,))

        try:
            session = session_class.fromMessage(message)
        except ValueError, why:
            raise ProtocolError(message, 'Error parsing %s session: %s' %
                                (session_class.session_type, why[0]))

        assoc_type = message.getArg(OPENID_NS, 'assoc_type', 'HMAC-SHA1')
        if assoc_type not in session.allowed_assoc_types:
            fmt = 'Session type %s does not support association type %s'
            raise ProtocolError(message, fmt % (session_type, assoc_type))

        self = klass(session, assoc_type)
        self.message = message
        self.namespace = message.getOpenIDNamespace()
        return self

    fromMessage = classmethod(fromMessage)

    def answer(self, assoc):
        """Respond to this request with an X{association}.

        @param assoc: The association to send back.
        @type assoc: L{openid.association.Association}

        @returns: A response with the association information, encrypted
            to the consumer's X{public key} if appropriate.
        @returntype: L{OpenIDResponse}
        """
        response = OpenIDResponse(self)
        response.fields.updateArgs(OPENID_NS, {
            'expires_in': '%d' % (assoc.getExpiresIn(),),
            'assoc_type': self.assoc_type,
            'assoc_handle': assoc.handle,
            })
        response.fields.updateArgs(OPENID_NS,
                                   self.session.answer(assoc.secret))

        if not (self.session.session_type == 'no-encryption' and
                self.message.isOpenID1()):
            # The session type "no-encryption" did not have a name
            # in OpenID v1, it was just omitted.
            response.fields.setArg(
                OPENID_NS, 'session_type', self.session.session_type)

        return response

    def answerUnsupported(self, message, preferred_association_type=None,
                          preferred_session_type=None):
        """Respond to this request indicating that the association
        type or association session type is not supported."""
        if self.message.isOpenID1():
            raise ProtocolError(self.message)

        response = OpenIDResponse(self)
        response.fields.setArg(OPENID_NS, 'error_code', 'unsupported-type')
        response.fields.setArg(OPENID_NS, 'error', message)

        if preferred_association_type:
            response.fields.setArg(
                OPENID_NS, 'assoc_type', preferred_association_type)

        if preferred_session_type:
            response.fields.setArg(
                OPENID_NS, 'session_type', preferred_session_type)

        return response

class CheckIDRequest(OpenIDRequest):
    """A request to confirm the identity of a user.

    This class handles requests for openid modes X{C{checkid_immediate}}
    and X{C{checkid_setup}}.

    @cvar mode: "X{C{checkid_immediate}}" or "X{C{checkid_setup}}"
    @type mode: str

    @ivar immediate: Is this an immediate-mode request?
    @type immediate: bool

    @ivar identity: The OP-local identifier being checked.
    @type identity: str

    @ivar claimed_id: The claimed identifier.  Not present in OpenID 1.x
        messages.
    @type claimed_id: str

    @ivar trust_root: "Are you Frank?" asks the checkid request.  "Who wants
        to know?"  C{trust_root}, that's who.  This URL identifies the party
        making the request, and the user will use that to make her decision
        about what answer she trusts them to have.  Referred to as "realm" in
        OpenID 2.0.
    @type trust_root: str

    @ivar return_to: The URL to send the user agent back to to reply to this
        request.
    @type return_to: str

    @ivar assoc_handle: Provided in smart mode requests, a handle for a
        previously established association.  C{None} for dumb mode requests.
    @type assoc_handle: str
    """

    def __init__(self, identity, return_to, trust_root=None, immediate=False,
                 assoc_handle=None, op_endpoint=None, claimed_id=None):
        """Construct me.

        These parameters are assigned directly as class attributes, see
        my L{class documentation<CheckIDRequest>} for their descriptions.

        @raises MalformedReturnURL: When the C{return_to} URL is not a URL.
        """
        self.assoc_handle = assoc_handle
        self.identity = identity
        self.claimed_id = claimed_id or identity
        self.return_to = return_to
        self.trust_root = trust_root or return_to
        self.op_endpoint = op_endpoint
        assert self.op_endpoint is not None
        if immediate:
            self.immediate = True
            self.mode = "checkid_immediate"
        else:
            self.immediate = False
            self.mode = "checkid_setup"

        if self.return_to is not None and \
               not TrustRoot.parse(self.return_to):
            raise MalformedReturnURL(None, self.return_to)
        if not self.trustRootValid():
            raise UntrustedReturnURL(None, self.return_to, self.trust_root)
        self.message = None

    def _getNamespace(self):
        warnings.warn('The "namespace" attribute of CheckIDRequest objects '
                      'is deprecated. Use "message.getOpenIDNamespace()" '
                      'instead', DeprecationWarning, stacklevel=2)
        return self.message.getOpenIDNamespace()

    namespace = property(_getNamespace)

    def fromMessage(klass, message, op_endpoint):
        """Construct me from an OpenID message.

        @raises ProtocolError: When not all required parameters are present
            in the message.

        @raises MalformedReturnURL: When the C{return_to} URL is not a URL.

        @raises UntrustedReturnURL: When the C{return_to} URL is outside
            the C{trust_root}.

        @param message: An OpenID checkid_* request Message
        @type message: openid.message.Message

        @param op_endpoint: The endpoint URL of the server that this
            message was sent to.
        @type op_endpoint: str

        @returntype: L{CheckIDRequest}
        """
        self = klass.__new__(klass)
        self.message = message
        self.op_endpoint = op_endpoint
        mode = message.getArg(OPENID_NS, 'mode')
        if mode == "checkid_immediate":
            self.immediate = True
            self.mode = "checkid_immediate"
        else:
            self.immediate = False
            self.mode = "checkid_setup"

        self.return_to = message.getArg(OPENID_NS, 'return_to')
        if message.isOpenID1() and not self.return_to:
            fmt = "Missing required field 'return_to' from %r"
            raise ProtocolError(message, text=fmt % (message,))

        self.identity = message.getArg(OPENID_NS, 'identity')
        self.claimed_id = message.getArg(OPENID_NS, 'claimed_id')
        if message.isOpenID1():
            if self.identity is None:
                s = "OpenID 1 message did not contain openid.identity"
                raise ProtocolError(message, text=s)
        else:
            if self.identity and not self.claimed_id:
                s = ("OpenID 2.0 message contained openid.identity but not "
                     "claimed_id")
                raise ProtocolError(message, text=s)
            elif self.claimed_id and not self.identity:
                s = ("OpenID 2.0 message contained openid.claimed_id but not "
                     "identity")
                raise ProtocolError(message, text=s)

        # There's a case for making self.trust_root be a TrustRoot
        # here.  But if TrustRoot isn't currently part of the "public" API,
        # I'm not sure it's worth doing.

        if message.isOpenID1():
            trust_root_param = 'trust_root'
        else:
            trust_root_param = 'realm'

        # Using 'or' here is slightly different than sending a default
        # argument to getArg, as it will treat no value and an empty
        # string as equivalent.
        self.trust_root = (message.getArg(OPENID_NS, trust_root_param)
                           or self.return_to)

        if not message.isOpenID1():
            if self.return_to is self.trust_root is None:
                raise ProtocolError(message, "openid.realm required when " +
                                    "openid.return_to absent")

        self.assoc_handle = message.getArg(OPENID_NS, 'assoc_handle')

        # Using TrustRoot.parse here is a bit misleading, as we're not
        # parsing return_to as a trust root at all.  However, valid URLs
        # are valid trust roots, so we can use this to get an idea if it
        # is a valid URL.  Not all trust roots are valid return_to URLs,
        # however (particularly ones with wildcards), so this is still a
        # little sketchy.
        if self.return_to is not None and \
               not TrustRoot.parse(self.return_to):
            raise MalformedReturnURL(message, self.return_to)

        # I first thought that checking to see if the return_to is within
        # the trust_root is premature here, a logic-not-decoding thing.  But
        # it was argued that this is really part of data validation.  A
        # request with an invalid trust_root/return_to is broken regardless of
        # application, right?
        if not self.trustRootValid():
            raise UntrustedReturnURL(message, self.return_to, self.trust_root)

        return self

    fromMessage = classmethod(fromMessage)

    def idSelect(self):
        """Is the identifier to be selected by the IDP?

        @returntype: bool
        """
        # So IDPs don't have to import the constant
        return self.identity == IDENTIFIER_SELECT

    def trustRootValid(self):
        """Is my return_to under my trust_root?

        @returntype: bool
        """
        if not self.trust_root:
            return True
        tr = TrustRoot.parse(self.trust_root)
        if tr is None:
            raise MalformedTrustRoot(self.message, self.trust_root)

        if self.return_to is not None:
            return tr.validateURL(self.return_to)
        else:
            return True

    def returnToVerified(self):
        """Does the relying party publish the return_to URL for this
        response under the realm? It is up to the provider to set a
        policy for what kinds of realms should be allowed. This
        return_to URL verification reduces vulnerability to data-theft
        attacks based on open proxies, cross-site-scripting, or open
        redirectors.

        This check should only be performed after making sure that the
        return_to URL matches the realm.

        @see: L{trustRootValid}

        @raises openid.yadis.discover.DiscoveryFailure: if the realm
            URL does not support Yadis discovery (and so does not
            support the verification process).

        @raises openid.fetchers.HTTPFetchingError: if the realm URL
            is not reachable.  When this is the case, the RP may be hosted
            on the user's intranet.

        @returntype: bool

        @returns: True if the realm publishes a document with the
            return_to URL listed

        @since: 2.1.0
        """
        return verifyReturnTo(self.trust_root, self.return_to)

    def answer(self, allow, server_url=None, identity=None, claimed_id=None):
        """Respond to this request.

        @param allow: Allow this user to claim this identity, and allow the
            consumer to have this information?
        @type allow: bool

        @param server_url: DEPRECATED.  Passing C{op_endpoint} to the
            L{Server} constructor makes this optional.

            When an OpenID 1.x immediate mode request does not succeed,
            it gets back a URL where the request may be carried out
            in a not-so-immediate fashion.  Pass my URL in here (the
            fully qualified address of this server's endpoint, i.e.
            C{http://example.com/server}), and I will use it as a base for the
            URL for a new request.

            Optional for requests where C{CheckIDRequest.immediate} is C{False}
            or C{allow} is C{True}.

        @type server_url: str

        @param identity: The OP-local identifier to answer with.  Only for use
            when the relying party requested identifier selection.
        @type identity: str or None

        @param claimed_id: The claimed identifier to answer with, for use
            with identifier selection in the case where the claimed identifier
            and the OP-local identifier differ, i.e. when the claimed_id uses
            delegation.

            If C{identity} is provided but this is not, C{claimed_id} will
            default to the value of C{identity}.  When answering requests
            that did not ask for identifier selection, the response
            C{claimed_id} will default to that of the request.

            This parameter is new in OpenID 2.0.
        @type claimed_id: str or None

        @returntype: L{OpenIDResponse}

        @change: Version 2.0 deprecates C{server_url} and adds C{claimed_id}.

        @raises NoReturnError: when I do not have a return_to.
        """
        assert self.message is not None

        if not self.return_to:
            raise NoReturnToError

        if not server_url:
            if not self.message.isOpenID1() and not self.op_endpoint:
                # In other words, that warning I raised in Server.__init__?
                # You should pay attention to it now.
                raise RuntimeError("%s should be constructed with op_endpoint "
                                   "to respond to OpenID 2.0 messages." %
                                   (self,))
            server_url = self.op_endpoint

        if allow:
            mode = 'id_res'
        elif self.message.isOpenID1():
             if self.immediate:
                 mode = 'id_res'
             else:
                 mode = 'cancel'
        else:
            if self.immediate:
                mode = 'setup_needed'
            else:
                mode = 'cancel'

        response = OpenIDResponse(self)

        if claimed_id and self.message.isOpenID1():
            namespace = self.message.getOpenIDNamespace()
            raise VersionError("claimed_id is new in OpenID 2.0 and not "
                               "available for %s" % (namespace,))

        if allow:
            if self.identity == IDENTIFIER_SELECT:
                if not identity:
                    raise ValueError(
                        "This request uses IdP-driven identifier selection."
                        "You must supply an identifier in the response.")
                response_identity = identity
                response_claimed_id = claimed_id or identity

            elif self.identity:
                if identity and (self.identity != identity):
                    normalized_request_identity = urinorm(self.identity)
                    normalized_answer_identity = urinorm(identity)

                    if (normalized_request_identity !=
                        normalized_answer_identity):
                        raise ValueError(
                            "Request was for identity %r, cannot reply "
                            "with identity %r" % (self.identity, identity))

                # The "identity" value in the response shall always be
                # the same as that in the request, otherwise the RP is
                # likely to not validate the response.
                response_identity = self.identity
                response_claimed_id = self.claimed_id
            else:
                if identity:
                    raise ValueError(
                        "This request specified no identity and you "
                        "supplied %r" % (identity,))
                response_identity = None

            if self.message.isOpenID1() and response_identity is None:
                raise ValueError(
                    "Request was an OpenID 1 request, so response must "
                    "include an identifier."
                    )

            response.fields.updateArgs(OPENID_NS, {
                'mode': mode,
                'return_to': self.return_to,
                'response_nonce': mkNonce(),
                })

            if server_url:
                response.fields.setArg(OPENID_NS, 'op_endpoint', server_url)

            if response_identity is not None:
                response.fields.setArg(
                    OPENID_NS, 'identity', response_identity)
                if self.message.isOpenID2():
                    response.fields.setArg(
                        OPENID_NS, 'claimed_id', response_claimed_id)
        else:
            response.fields.setArg(OPENID_NS, 'mode', mode)
            if self.immediate:
                if self.message.isOpenID1() and not server_url:
                    raise ValueError("setup_url is required for allow=False "
                                     "in OpenID 1.x immediate mode.")
                # Make a new request just like me, but with immediate=False.
                setup_request = self.__class__(
                    self.identity, self.return_to, self.trust_root,
                    immediate=False, assoc_handle=self.assoc_handle,
                    op_endpoint=self.op_endpoint, claimed_id=self.claimed_id)

                # XXX: This API is weird.
                setup_request.message = self.message

                setup_url = setup_request.encodeToURL(server_url)
                response.fields.setArg(OPENID_NS, 'user_setup_url', setup_url)

        return response


    def encodeToURL(self, server_url):
        """Encode this request as a URL to GET.

        @param server_url: The URL of the OpenID server to make this request of.
        @type server_url: str

        @returntype: str

        @raises NoReturnError: when I do not have a return_to.
        """
        if not self.return_to:
            raise NoReturnToError

        # Imported from the alternate reality where these classes are used
        # in both the client and server code, so Requests are Encodable too.
        # That's right, code imported from alternate realities all for the
        # love of you, id_res/user_setup_url.
        q = {'mode': self.mode,
             'identity': self.identity,
             'claimed_id': self.claimed_id,
             'return_to': self.return_to}
        if self.trust_root:
            if self.message.isOpenID1():
                q['trust_root'] = self.trust_root
            else:
                q['realm'] = self.trust_root
        if self.assoc_handle:
            q['assoc_handle'] = self.assoc_handle

        response = Message(self.message.getOpenIDNamespace())
        response.updateArgs(OPENID_NS, q)
        return response.toURL(server_url)


    def getCancelURL(self):
        """Get the URL to cancel this request.

        Useful for creating a "Cancel" button on a web form so that operation
        can be carried out directly without another trip through the server.

        (Except you probably want to make another trip through the server so
        that it knows that the user did make a decision.  Or you could simulate
        this method by doing C{.answer(False).encodeToURL()})

        @returntype: str
        @returns: The return_to URL with openid.mode = cancel.

        @raises NoReturnError: when I do not have a return_to.
        """
        if not self.return_to:
            raise NoReturnToError

        if self.immediate:
            raise ValueError("Cancel is not an appropriate response to "
                             "immediate mode requests.")

        response = Message(self.message.getOpenIDNamespace())
        response.setArg(OPENID_NS, 'mode', 'cancel')
        return response.toURL(self.return_to)


    def __repr__(self):
        return '<%s id:%r im:%s tr:%r ah:%r>' % (self.__class__.__name__,
                                                 self.identity,
                                                 self.immediate,
                                                 self.trust_root,
                                                 self.assoc_handle)



class OpenIDResponse(object):
    """I am a response to an OpenID request.

    @ivar request: The request I respond to.
    @type request: L{OpenIDRequest}

    @ivar fields: My parameters as a dictionary with each key mapping to
        one value.  Keys are parameter names with no leading "C{openid.}".
        e.g.  "C{identity}" and "C{mac_key}", never "C{openid.identity}".
    @type fields: L{openid.message.Message}

    @ivar signed: The names of the fields which should be signed.
    @type signed: list of str
    """

    # Implementer's note: In a more symmetric client/server
    # implementation, there would be more types of OpenIDResponse
    # object and they would have validated attributes according to the
    # type of response.  But as it is, Response objects in a server are
    # basically write-only, their only job is to go out over the wire,
    # so this is just a loose wrapper around OpenIDResponse.fields.

    def __init__(self, request):
        """Make a response to an L{OpenIDRequest}.

        @type request: L{OpenIDRequest}
        """
        self.request = request
        self.fields = Message(request.namespace)

    def __str__(self):
        return "%s for %s: %s" % (
            self.__class__.__name__,
            self.request.__class__.__name__,
            self.fields)


    def toFormMarkup(self, form_tag_attrs=None):
        """Returns the form markup for this response.

        @param form_tag_attrs: Dictionary of attributes to be added to
            the form tag. 'accept-charset' and 'enctype' have defaults
            that can be overridden. If a value is supplied for
            'action' or 'method', it will be replaced.

        @returntype: str

        @since: 2.1.0
        """
        return self.fields.toFormMarkup(self.request.return_to,
                                        form_tag_attrs=form_tag_attrs)

    def toHTML(self, form_tag_attrs=None):
        """Returns an HTML document that auto-submits the form markup
        for this response.

        @returntype: str

        @see: toFormMarkup

        @since: 2.1.?
        """
        return oidutil.autoSubmitHTML(self.toFormMarkup(form_tag_attrs))

    def renderAsForm(self):
        """Returns True if this response's encoding is
        ENCODE_HTML_FORM.  Convenience method for server authors.

        @returntype: bool

        @since: 2.1.0
        """
        return self.whichEncoding() == ENCODE_HTML_FORM


    def needsSigning(self):
        """Does this response require signing?

        @returntype: bool
        """
        return self.fields.getArg(OPENID_NS, 'mode') == 'id_res'


    # implements IEncodable

    def whichEncoding(self):
        """How should I be encoded?

        @returns: one of ENCODE_URL, ENCODE_HTML_FORM, or ENCODE_KVFORM.

        @change: 2.1.0 added the ENCODE_HTML_FORM response.
        """
        if self.request.mode in BROWSER_REQUEST_MODES:
            if self.fields.getOpenIDNamespace() == OPENID2_NS and \
               len(self.encodeToURL()) > OPENID1_URL_LIMIT:
                return ENCODE_HTML_FORM
            else:
                return ENCODE_URL
        else:
            return ENCODE_KVFORM


    def encodeToURL(self):
        """Encode a response as a URL for the user agent to GET.

        You will generally use this URL with a HTTP redirect.

        @returns: A URL to direct the user agent back to.
        @returntype: str
        """
        return self.fields.toURL(self.request.return_to)


    def addExtension(self, extension_response):
        """
        Add an extension response to this response message.

        @param extension_response: An object that implements the
            extension interface for adding arguments to an OpenID
            message.
        @type extension_response: L{openid.extension}

        @returntype: None
        """
        extension_response.toMessage(self.fields)


    def encodeToKVForm(self):
        """Encode a response in key-value colon/newline format.

        This is a machine-readable format used to respond to messages which
        came directly from the consumer and not through the user agent.

        @see: OpenID Specs,
           U{Key-Value Colon/Newline format<http://openid.net/specs.bml#keyvalue>}

        @returntype: str
        """
        return self.fields.toKVForm()



class WebResponse(object):
    """I am a response to an OpenID request in terms a web server understands.

    I generally come from an L{Encoder}, either directly or from
    L{Server.encodeResponse}.

    @ivar code: The HTTP code of this response.
    @type code: int

    @ivar headers: Headers to include in this response.
    @type headers: dict

    @ivar body: The body of this response.
    @type body: str
    """

    def __init__(self, code=HTTP_OK, headers=None, body=""):
        """Construct me.

        These parameters are assigned directly as class attributes, see
        my L{class documentation<WebResponse>} for their descriptions.
        """
        self.code = code
        if headers is not None:
            self.headers = headers
        else:
            self.headers = {}
        self.body = body



class Signatory(object):
    """I sign things.

    I also check signatures.

    All my state is encapsulated in an
    L{OpenIDStore<openid.store.interface.OpenIDStore>}, which means
    I'm not generally pickleable but I am easy to reconstruct.

    @cvar SECRET_LIFETIME: The number of seconds a secret remains valid.
    @type SECRET_LIFETIME: int
    """

    SECRET_LIFETIME = 14 * 24 * 60 * 60 # 14 days, in seconds

    # keys have a bogus server URL in them because the filestore
    # really does expect that key to be a URL.  This seems a little
    # silly for the server store, since I expect there to be only one
    # server URL.
    _normal_key = 'http://localhost/|normal'
    _dumb_key = 'http://localhost/|dumb'


    def __init__(self, store):
        """Create a new Signatory.

        @param store: The back-end where my associations are stored.
        @type store: L{openid.store.interface.OpenIDStore}
        """
        assert store is not None
        self.store = store


    def verify(self, assoc_handle, message):
        """Verify that the signature for some data is valid.

        @param assoc_handle: The handle of the association used to sign the
            data.
        @type assoc_handle: str

        @param message: The signed message to verify
        @type message: openid.message.Message

        @returns: C{True} if the signature is valid, C{False} if not.
        @returntype: bool
        """
        assoc = self.getAssociation(assoc_handle, dumb=True)
        if not assoc:
            oidutil.log("failed to get assoc with handle %r to verify "
                        "message %r"
                        % (assoc_handle, message))
            return False

        try:
            valid = assoc.checkMessageSignature(message)
        except ValueError, ex:
            oidutil.log("Error in verifying %s with %s: %s" % (message,
                                                               assoc,
                                                               ex))
            return False
        return valid


    def sign(self, response):
        """Sign a response.

        I take a L{OpenIDResponse}, create a signature for everything
        in its L{signed<OpenIDResponse.signed>} list, and return a new
        copy of the response object with that signature included.

        @param response: A response to sign.
        @type response: L{OpenIDResponse}

        @returns: A signed copy of the response.
        @returntype: L{OpenIDResponse}
        """
        signed_response = deepcopy(response)
        assoc_handle = response.request.assoc_handle
        if assoc_handle:
            # normal mode
            # disabling expiration check because even if the association
            # is expired, we still need to know some properties of the
            # association so that we may preserve those properties when
            # creating the fallback association.
            assoc = self.getAssociation(assoc_handle, dumb=False,
                                        checkExpiration=False)

            if not assoc or assoc.expiresIn <= 0:
                # fall back to dumb mode
                signed_response.fields.setArg(
                    OPENID_NS, 'invalidate_handle', assoc_handle)
                assoc_type = assoc and assoc.assoc_type or 'HMAC-SHA1'
                if assoc and assoc.expiresIn <= 0:
                    # now do the clean-up that the disabled checkExpiration
                    # code didn't get to do.
                    self.invalidate(assoc_handle, dumb=False)
                assoc = self.createAssociation(dumb=True, assoc_type=assoc_type)
        else:
            # dumb mode.
            assoc = self.createAssociation(dumb=True)

        try:
            signed_response.fields = assoc.signMessage(signed_response.fields)
        except kvform.KVFormError, err:
            raise EncodingError(response, explanation=str(err))
        return signed_response


    def createAssociation(self, dumb=True, assoc_type='HMAC-SHA1'):
        """Make a new association.

        @param dumb: Is this association for a dumb-mode transaction?
        @type dumb: bool

        @param assoc_type: The type of association to create.  Currently
            there is only one type defined, C{HMAC-SHA1}.
        @type assoc_type: str

        @returns: the new association.
        @returntype: L{openid.association.Association}
        """
        secret = cryptutil.getBytes(getSecretSize(assoc_type))
        uniq = oidutil.toBase64(cryptutil.getBytes(4))
        handle = '{%s}{%x}{%s}' % (assoc_type, int(time.time()), uniq)

        assoc = Association.fromExpiresIn(
            self.SECRET_LIFETIME, handle, secret, assoc_type)

        if dumb:
            key = self._dumb_key
        else:
            key = self._normal_key
        self.store.storeAssociation(key, assoc)
        return assoc


    def getAssociation(self, assoc_handle, dumb, checkExpiration=True):
        """Get the association with the specified handle.

        @type assoc_handle: str

        @param dumb: Is this association used with dumb mode?
        @type dumb: bool

        @returns: the association, or None if no valid association with that
            handle was found.
        @returntype: L{openid.association.Association}
        """
        # Hmm.  We've created an interface that deals almost entirely with
        # assoc_handles.  The only place outside the Signatory that uses this
        # (and thus the only place that ever sees Association objects) is
        # when creating a response to an association request, as it must have
        # the association's secret.

        if assoc_handle is None:
            raise ValueError("assoc_handle must not be None")

        if dumb:
            key = self._dumb_key
        else:
            key = self._normal_key
        assoc = self.store.getAssociation(key, assoc_handle)
        if assoc is not None and assoc.expiresIn <= 0:
            oidutil.log("requested %sdumb key %r is expired (by %s seconds)" %
                        ((not dumb) and 'not-' or '',
                         assoc_handle, assoc.expiresIn))
            if checkExpiration:
                self.store.removeAssociation(key, assoc_handle)
                assoc = None
        return assoc


    def invalidate(self, assoc_handle, dumb):
        """Invalidates the association with the given handle.

        @type assoc_handle: str

        @param dumb: Is this association used with dumb mode?
        @type dumb: bool
        """
        if dumb:
            key = self._dumb_key
        else:
            key = self._normal_key
        self.store.removeAssociation(key, assoc_handle)



class Encoder(object):
    """I encode responses in to L{WebResponses<WebResponse>}.

    If you don't like L{WebResponses<WebResponse>}, you can do
    your own handling of L{OpenIDResponses<OpenIDResponse>} with
    L{OpenIDResponse.whichEncoding}, L{OpenIDResponse.encodeToURL}, and
    L{OpenIDResponse.encodeToKVForm}.
    """

    responseFactory = WebResponse


    def encode(self, response):
        """Encode a response to a L{WebResponse}.

        @raises EncodingError: When I can't figure out how to encode this
            message.
        """
        encode_as = response.whichEncoding()
        if encode_as == ENCODE_KVFORM:
            wr = self.responseFactory(body=response.encodeToKVForm())
            if isinstance(response, Exception):
                wr.code = HTTP_ERROR
        elif encode_as == ENCODE_URL:
            location = response.encodeToURL()
            wr = self.responseFactory(code=HTTP_REDIRECT,
                                      headers={'location': location})
        elif encode_as == ENCODE_HTML_FORM:
            wr = self.responseFactory(code=HTTP_OK,
                                      body=response.toFormMarkup())
        else:
            # Can't encode this to a protocol message.  You should probably
            # render it to HTML and show it to the user.
            raise EncodingError(response)
        return wr



class SigningEncoder(Encoder):
    """I encode responses in to L{WebResponses<WebResponse>}, signing them when required.
    """

    def __init__(self, signatory):
        """Create a L{SigningEncoder}.

        @param signatory: The L{Signatory} I will make signatures with.
        @type signatory: L{Signatory}
        """
        self.signatory = signatory


    def encode(self, response):
        """Encode a response to a L{WebResponse}, signing it first if appropriate.

        @raises EncodingError: When I can't figure out how to encode this
            message.

        @raises AlreadySigned: When this response is already signed.

        @returntype: L{WebResponse}
        """
        # the isinstance is a bit of a kludge... it means there isn't really
        # an adapter to make the interfaces quite match.
        if (not isinstance(response, Exception)) and response.needsSigning():
            if not self.signatory:
                raise ValueError(
                    "Must have a store to sign this request: %s" %
                    (response,), response)
            if response.fields.hasKey(OPENID_NS, 'sig'):
                raise AlreadySigned(response)
            response = self.signatory.sign(response)
        return super(SigningEncoder, self).encode(response)



class Decoder(object):
    """I decode an incoming web request in to a L{OpenIDRequest}.
    """

    _handlers = {
        'checkid_setup': CheckIDRequest.fromMessage,
        'checkid_immediate': CheckIDRequest.fromMessage,
        'check_authentication': CheckAuthRequest.fromMessage,
        'associate': AssociateRequest.fromMessage,
        }

    def __init__(self, server):
        """Construct a Decoder.

        @param server: The server which I am decoding requests for.
            (Necessary because some replies reference their server.)
        @type server: L{Server}
        """
        self.server = server

    def decode(self, query):
        """I transform query parameters into an L{OpenIDRequest}.

        If the query does not seem to be an OpenID request at all, I return
        C{None}.

        @param query: The query parameters as a dictionary with each
            key mapping to one value.
        @type query: dict

        @raises ProtocolError: When the query does not seem to be a valid
            OpenID request.

        @returntype: L{OpenIDRequest}
        """
        if not query:
            return None

        try:
            message = Message.fromPostArgs(query)
        except InvalidOpenIDNamespace, err:
            # It's useful to have a Message attached to a ProtocolError, so we
            # override the bad ns value to build a Message out of it.  Kinda
            # kludgy, since it's made of lies, but the parts that aren't lies
            # are more useful than a 'None'.
            query = query.copy()
            query['openid.ns'] = OPENID2_NS
            message = Message.fromPostArgs(query)
            raise ProtocolError(message, str(err))

        mode = message.getArg(OPENID_NS, 'mode')
        if not mode:
            fmt = "No mode value in message %s"
            raise ProtocolError(message, text=fmt % (message,))

        handler = self._handlers.get(mode, self.defaultDecoder)
        return handler(message, self.server.op_endpoint)


    def defaultDecoder(self, message, server):
        """Called to decode queries when no handler for that mode is found.

        @raises ProtocolError: This implementation always raises
            L{ProtocolError}.
        """
        mode = message.getArg(OPENID_NS, 'mode')
        fmt = "Unrecognized OpenID mode %r"
        raise ProtocolError(message, text=fmt % (mode,))



class Server(object):
    """I handle requests for an OpenID server.

    Some types of requests (those which are not C{checkid} requests) may be
    handed to my L{handleRequest} method, and I will take care of it and
    return a response.

    For your convenience, I also provide an interface to L{Decoder.decode}
    and L{SigningEncoder.encode} through my methods L{decodeRequest} and
    L{encodeResponse}.

    All my state is encapsulated in an
    L{OpenIDStore<openid.store.interface.OpenIDStore>}, which means
    I'm not generally pickleable but I am easy to reconstruct.

    Example::

        oserver = Server(FileOpenIDStore(data_path), "http://example.com/op")
        request = oserver.decodeRequest(query)
        if request.mode in ['checkid_immediate', 'checkid_setup']:
            if self.isAuthorized(request.identity, request.trust_root):
                response = request.answer(True)
            elif request.immediate:
                response = request.answer(False)
            else:
                self.showDecidePage(request)
                return
        else:
            response = oserver.handleRequest(request)

        webresponse = oserver.encode(response)

    @ivar signatory: I'm using this for associate requests and to sign things.
    @type signatory: L{Signatory}

    @ivar decoder: I'm using this to decode things.
    @type decoder: L{Decoder}

    @ivar encoder: I'm using this to encode things.
    @type encoder: L{Encoder}

    @ivar op_endpoint: My URL.
    @type op_endpoint: str

    @ivar negotiator: I use this to determine which kinds of
        associations I can make and how.
    @type negotiator: L{openid.association.SessionNegotiator}
    """

    signatoryClass = Signatory
    encoderClass = SigningEncoder
    decoderClass = Decoder

    def __init__(self, store, op_endpoint=None):
        """A new L{Server}.

        @param store: The back-end where my associations are stored.
        @type store: L{openid.store.interface.OpenIDStore}

        @param op_endpoint: My URL, the fully qualified address of this
            server's endpoint, i.e. C{http://example.com/server}
        @type op_endpoint: str

        @change: C{op_endpoint} is new in library version 2.0.  It
            currently defaults to C{None} for compatibility with
            earlier versions of the library, but you must provide it
            if you want to respond to any version 2 OpenID requests.
        """
        self.store = store
        self.signatory = self.signatoryClass(self.store)
        self.encoder = self.encoderClass(self.signatory)
        self.decoder = self.decoderClass(self)
        self.negotiator = default_negotiator.copy()

        if not op_endpoint:
            warnings.warn("%s.%s constructor requires op_endpoint parameter "
                          "for OpenID 2.0 servers" %
                          (self.__class__.__module__, self.__class__.__name__),
                          stacklevel=2)
        self.op_endpoint = op_endpoint


    def handleRequest(self, request):
        """Handle a request.

        Give me a request, I will give you a response.  Unless it's a type
        of request I cannot handle myself, in which case I will raise
        C{NotImplementedError}.  In that case, you can handle it yourself,
        or add a method to me for handling that request type.

        @raises NotImplementedError: When I do not have a handler defined
            for that type of request.

        @returntype: L{OpenIDResponse}
        """
        handler = getattr(self, 'openid_' + request.mode, None)
        if handler is not None:
            return handler(request)
        else:
            raise NotImplementedError(
                "%s has no handler for a request of mode %r." %
                (self, request.mode))


    def openid_check_authentication(self, request):
        """Handle and respond to C{check_authentication} requests.

        @returntype: L{OpenIDResponse}
        """
        return request.answer(self.signatory)


    def openid_associate(self, request):
        """Handle and respond to C{associate} requests.

        @returntype: L{OpenIDResponse}
        """
        # XXX: TESTME
        assoc_type = request.assoc_type
        session_type = request.session.session_type
        if self.negotiator.isAllowed(assoc_type, session_type):
            assoc = self.signatory.createAssociation(dumb=False,
                                                     assoc_type=assoc_type)
            return request.answer(assoc)
        else:
            message = ('Association type %r is not supported with '
                       'session type %r' % (assoc_type, session_type))
            (preferred_assoc_type, preferred_session_type) = \
                                   self.negotiator.getAllowedType()
            return request.answerUnsupported(
                message,
                preferred_assoc_type,
                preferred_session_type)


    def decodeRequest(self, query):
        """Transform query parameters into an L{OpenIDRequest}.

        If the query does not seem to be an OpenID request at all, I return
        C{None}.

        @param query: The query parameters as a dictionary with each
            key mapping to one value.
        @type query: dict

        @raises ProtocolError: When the query does not seem to be a valid
            OpenID request.

        @returntype: L{OpenIDRequest}

        @see: L{Decoder.decode}
        """
        return self.decoder.decode(query)


    def encodeResponse(self, response):
        """Encode a response to a L{WebResponse}, signing it first if appropriate.

        @raises EncodingError: When I can't figure out how to encode this
            message.

        @raises AlreadySigned: When this response is already signed.

        @returntype: L{WebResponse}

        @see: L{SigningEncoder.encode}
        """
        return self.encoder.encode(response)



class ProtocolError(Exception):
    """A message did not conform to the OpenID protocol.

    @ivar message: The query that is failing to be a valid OpenID request.
    @type message: openid.message.Message
    """

    def __init__(self, message, text=None, reference=None, contact=None):
        """When an error occurs.

        @param message: The message that is failing to be a valid
            OpenID request.
        @type message: openid.message.Message

        @param text: A message about the encountered error.  Set as C{args[0]}.
        @type text: str
        """
        self.openid_message = message
        self.reference = reference
        self.contact = contact
        assert type(message) not in [str, unicode]
        Exception.__init__(self, text)


    def getReturnTo(self):
        """Get the return_to argument from the request, if any.

        @returntype: str
        """
        if self.openid_message is None:
            return None
        else:
            return self.openid_message.getArg(OPENID_NS, 'return_to')

    def hasReturnTo(self):
        """Did this request have a return_to parameter?

        @returntype: bool
        """
        return self.getReturnTo() is not None

    def toMessage(self):
        """Generate a Message object for sending to the relying party,
        after encoding.
        """
        namespace = self.openid_message.getOpenIDNamespace()
        reply = Message(namespace)
        reply.setArg(OPENID_NS, 'mode', 'error')
        reply.setArg(OPENID_NS, 'error', str(self))

        if self.contact is not None:
            reply.setArg(OPENID_NS, 'contact', str(self.contact))

        if self.reference is not None:
            reply.setArg(OPENID_NS, 'reference', str(self.reference))

        return reply

    # implements IEncodable

    def encodeToURL(self):
        return self.toMessage().toURL(self.getReturnTo())

    def encodeToKVForm(self):
        return self.toMessage().toKVForm()

    def toFormMarkup(self):
        """Encode to HTML form markup for POST.

        @since: 2.1.0
        """
        return self.toMessage().toFormMarkup(self.getReturnTo())

    def toHTML(self):
        """Encode to a full HTML page, wrapping the form markup in a page
        that will autosubmit the form.

        @since: 2.1.?
        """
        return oidutil.autoSubmitHTML(self.toFormMarkup())

    def whichEncoding(self):
        """How should I be encoded?

        @returns: one of ENCODE_URL, ENCODE_KVFORM, or None.  If None,
            I cannot be encoded as a protocol message and should be
            displayed to the user.
        """
        if self.hasReturnTo():
            if self.openid_message.getOpenIDNamespace() == OPENID2_NS and \
               len(self.encodeToURL()) > OPENID1_URL_LIMIT:
                return ENCODE_HTML_FORM
            else:
                return ENCODE_URL

        if self.openid_message is None:
            return None

        mode = self.openid_message.getArg(OPENID_NS, 'mode')
        if mode:
            if mode not in BROWSER_REQUEST_MODES:
                return ENCODE_KVFORM

        # According to the OpenID spec as of this writing, we are probably
        # supposed to switch on request type here (GET versus POST) to figure
        # out if we're supposed to print machine-readable or human-readable
        # content at this point.  GET/POST seems like a pretty lousy way of
        # making the distinction though, as it's just as possible that the
        # user agent could have mistakenly been directed to post to the
        # server URL.

        # Basically, if your request was so broken that you didn't manage to
        # include an openid.mode, I'm not going to worry too much about
        # returning you something you can't parse.
        return None



class VersionError(Exception):
    """Raised when an operation was attempted that is not compatible with
    the protocol version being used."""



class NoReturnToError(Exception):
    """Raised when a response to a request cannot be generated because
    the request contains no return_to URL.
    """
    pass



class EncodingError(Exception):
    """Could not encode this as a protocol message.

    You should probably render it and show it to the user.

    @ivar response: The response that failed to encode.
    @type response: L{OpenIDResponse}
    """

    def __init__(self, response, explanation=None):
        Exception.__init__(self, response)
        self.response = response
        self.explanation = explanation

    def __str__(self):
        if self.explanation:
            s = '%s: %s' % (self.__class__.__name__,
                            self.explanation)
        else:
            s = '%s for Response %s' % (
                self.__class__.__name__, self.response)
        return s


class AlreadySigned(EncodingError):
    """This response is already signed."""



class UntrustedReturnURL(ProtocolError):
    """A return_to is outside the trust_root."""

    def __init__(self, message, return_to, trust_root):
        ProtocolError.__init__(self, message)
        self.return_to = return_to
        self.trust_root = trust_root

    def __str__(self):
        return "return_to %r not under trust_root %r" % (self.return_to,
                                                         self.trust_root)


class MalformedReturnURL(ProtocolError):
    """The return_to URL doesn't look like a valid URL."""
    def __init__(self, openid_message, return_to):
        self.return_to = return_to
        ProtocolError.__init__(self, openid_message)



class MalformedTrustRoot(ProtocolError):
    """The trust root is not well-formed.

    @see: OpenID Specs, U{openid.trust_root<http://openid.net/specs.bml#mode-checkid_immediate>}
    """
    pass


#class IEncodable: # Interface
#     def encodeToURL(return_to):
#         """Encode a response as a URL for redirection.
#
#         @returns: A URL to direct the user agent back to.
#         @returntype: str
#         """
#         pass
#
#     def encodeToKvform():
#         """Encode a response in key-value colon/newline format.
#
#         This is a machine-readable format used to respond to messages which
#         came directly from the consumer and not through the user agent.
#
#         @see: OpenID Specs,
#            U{Key-Value Colon/Newline format<http://openid.net/specs.bml#keyvalue>}
#
#         @returntype: str
#         """
#         pass
#
#     def whichEncoding():
#         """How should I be encoded?
#
#         @returns: one of ENCODE_URL, ENCODE_KVFORM, or None.  If None,
#             I cannot be encoded as a protocol message and should be
#             displayed to the user.
#         """
#         pass

########NEW FILE########
__FILENAME__ = trustroot
# -*- test-case-name: openid.test.test_rpverify -*-
"""
This module contains the C{L{TrustRoot}} class, which helps handle
trust root checking.  This module is used by the
C{L{openid.server.server}} module, but it is also available to server
implementers who wish to use it for additional trust root checking.

It also implements relying party return_to URL verification, based on
the realm.
"""

__all__ = [
    'TrustRoot',
    'RP_RETURN_TO_URL_TYPE',
    'extractReturnToURLs',
    'returnToMatches',
    'verifyReturnTo',
    ]

from openid import oidutil
from openid import urinorm
from openid.yadis import services

from urlparse import urlparse, urlunparse
import re

############################################
_protocols = ['http', 'https']
_top_level_domains = [
    'ac', 'ad', 'ae', 'aero', 'af', 'ag', 'ai', 'al', 'am', 'an',
    'ao', 'aq', 'ar', 'arpa', 'as', 'asia', 'at', 'au', 'aw',
    'ax', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 'bg', 'bh', 'bi',
    'biz', 'bj', 'bm', 'bn', 'bo', 'br', 'bs', 'bt', 'bv', 'bw',
    'by', 'bz', 'ca', 'cat', 'cc', 'cd', 'cf', 'cg', 'ch', 'ci',
    'ck', 'cl', 'cm', 'cn', 'co', 'com', 'coop', 'cr', 'cu', 'cv',
    'cx', 'cy', 'cz', 'de', 'dj', 'dk', 'dm', 'do', 'dz', 'ec',
    'edu', 'ee', 'eg', 'er', 'es', 'et', 'eu', 'fi', 'fj', 'fk',
    'fm', 'fo', 'fr', 'ga', 'gb', 'gd', 'ge', 'gf', 'gg', 'gh',
    'gi', 'gl', 'gm', 'gn', 'gov', 'gp', 'gq', 'gr', 'gs', 'gt',
    'gu', 'gw', 'gy', 'hk', 'hm', 'hn', 'hr', 'ht', 'hu', 'id',
    'ie', 'il', 'im', 'in', 'info', 'int', 'io', 'iq', 'ir', 'is',
    'it', 'je', 'jm', 'jo', 'jobs', 'jp', 'ke', 'kg', 'kh', 'ki',
    'km', 'kn', 'kp', 'kr', 'kw', 'ky', 'kz', 'la', 'lb', 'lc',
    'li', 'lk', 'lr', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'mc',
    'md', 'me', 'mg', 'mh', 'mil', 'mk', 'ml', 'mm', 'mn', 'mo',
    'mobi', 'mp', 'mq', 'mr', 'ms', 'mt', 'mu', 'museum', 'mv',
    'mw', 'mx', 'my', 'mz', 'na', 'name', 'nc', 'ne', 'net', 'nf',
    'ng', 'ni', 'nl', 'no', 'np', 'nr', 'nu', 'nz', 'om', 'org',
    'pa', 'pe', 'pf', 'pg', 'ph', 'pk', 'pl', 'pm', 'pn', 'pr',
    'pro', 'ps', 'pt', 'pw', 'py', 'qa', 're', 'ro', 'rs', 'ru',
    'rw', 'sa', 'sb', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sj',
    'sk', 'sl', 'sm', 'sn', 'so', 'sr', 'st', 'su', 'sv', 'sy',
    'sz', 'tc', 'td', 'tel', 'tf', 'tg', 'th', 'tj', 'tk', 'tl',
    'tm', 'tn', 'to', 'tp', 'tr', 'travel', 'tt', 'tv', 'tw',
    'tz', 'ua', 'ug', 'uk', 'us', 'uy', 'uz', 'va', 'vc', 've',
    'vg', 'vi', 'vn', 'vu', 'wf', 'ws', 'xn--0zwm56d',
    'xn--11b5bs3a9aj6g', 'xn--80akhbyknj4f', 'xn--9t4b11yi5a',
    'xn--deba0ad', 'xn--g6w251d', 'xn--hgbk6aj7f53bba',
    'xn--hlcj6aya9esc7a', 'xn--jxalpdlp', 'xn--kgbechtv',
    'xn--zckzah', 'ye', 'yt', 'yu', 'za', 'zm', 'zw']

# Build from RFC3986, section 3.2.2. Used to reject hosts with invalid
# characters.
host_segment_re = re.compile(
    r"(?:[-a-zA-Z0-9!$&'\(\)\*+,;=._~]|%[a-zA-Z0-9]{2})+$")

class RealmVerificationRedirected(Exception):
    """Attempting to verify this realm resulted in a redirect.

    @since: 2.1.0
    """
    def __init__(self, relying_party_url, rp_url_after_redirects):
        self.relying_party_url = relying_party_url
        self.rp_url_after_redirects = rp_url_after_redirects

    def __str__(self):
        return ("Attempting to verify %r resulted in "
                "redirect to %r" %
                (self.relying_party_url,
                 self.rp_url_after_redirects))


def _parseURL(url):
    try:
        url = urinorm.urinorm(url)
    except ValueError:
        return None
    proto, netloc, path, params, query, frag = urlparse(url)
    if not path:
        # Python <2.4 does not parse URLs with no path properly
        if not query and '?' in netloc:
            netloc, query = netloc.split('?', 1)

        path = '/'

    path = urlunparse(('', '', path, params, query, frag))

    if ':' in netloc:
        try:
            host, port = netloc.split(':')
        except ValueError:
            return None

        if not re.match(r'\d+$', port):
            return None
    else:
        host = netloc
        port = ''

    host = host.lower()
    if not host_segment_re.match(host):
        return None

    return proto, host, port, path

class TrustRoot(object):
    """
    This class represents an OpenID trust root.  The C{L{parse}}
    classmethod accepts a trust root string, producing a
    C{L{TrustRoot}} object.  The method OpenID server implementers
    would be most likely to use is the C{L{isSane}} method, which
    checks the trust root for given patterns that indicate that the
    trust root is too broad or points to a local network resource.

    @sort: parse, isSane
    """

    def __init__(self, unparsed, proto, wildcard, host, port, path):
        self.unparsed = unparsed
        self.proto = proto
        self.wildcard = wildcard
        self.host = host
        self.port = port
        self.path = path

    def isSane(self):
        """
        This method checks the to see if a trust root represents a
        reasonable (sane) set of URLs.  'http://*.com/', for example
        is not a reasonable pattern, as it cannot meaningfully specify
        the site claiming it.  This function attempts to find many
        related examples, but it can only work via heuristics.
        Negative responses from this method should be treated as
        advisory, used only to alert the user to examine the trust
        root carefully.


        @return: Whether the trust root is sane

        @rtype: C{bool}
        """

        if self.host == 'localhost':
            return True

        host_parts = self.host.split('.')
        if self.wildcard:
            assert host_parts[0] == '', host_parts
            del host_parts[0]

        # If it's an absolute domain name, remove the empty string
        # from the end.
        if host_parts and not host_parts[-1]:
            del host_parts[-1]

        if not host_parts:
            return False

        # Do not allow adjacent dots
        if '' in host_parts:
            return False

        tld = host_parts[-1]
        if tld not in _top_level_domains:
            return False

        if len(host_parts) == 1:
            return False

        if self.wildcard:
            if len(tld) == 2 and len(host_parts[-2]) <= 3:
                # It's a 2-letter tld with a short second to last segment
                # so there needs to be more than two segments specified 
                # (e.g. *.co.uk is insane)
                return len(host_parts) > 2

        # Passed all tests for insanity.
        return True

    def validateURL(self, url):
        """
        Validates a URL against this trust root.


        @param url: The URL to check

        @type url: C{str}


        @return: Whether the given URL is within this trust root.

        @rtype: C{bool}
        """

        url_parts = _parseURL(url)
        if url_parts is None:
            return False

        proto, host, port, path = url_parts

        if proto != self.proto:
            return False

        if port != self.port:
            return False

        if '*' in host:
            return False

        if not self.wildcard:
            if host != self.host:
                return False
        elif ((not host.endswith(self.host)) and
              ('.' + host) != self.host):
            return False

        if path != self.path:
            path_len = len(self.path)
            trust_prefix = self.path[:path_len]
            url_prefix = path[:path_len]

            # must be equal up to the length of the path, at least
            if trust_prefix != url_prefix:
                return False

            # These characters must be on the boundary between the end
            # of the trust root's path and the start of the URL's
            # path.
            if '?' in self.path:
                allowed = '&'
            else:
                allowed = '?/'

            return (self.path[-1] in allowed or
                path[path_len] in allowed)

        return True

    def parse(cls, trust_root):
        """
        This method creates a C{L{TrustRoot}} instance from the given
        input, if possible.


        @param trust_root: This is the trust root to parse into a
        C{L{TrustRoot}} object.

        @type trust_root: C{str}


        @return: A C{L{TrustRoot}} instance if trust_root parses as a
        trust root, C{None} otherwise.

        @rtype: C{NoneType} or C{L{TrustRoot}}
        """
        url_parts = _parseURL(trust_root)
        if url_parts is None:
            return None

        proto, host, port, path = url_parts

        # check for valid prototype
        if proto not in _protocols:
            return None

        # check for URI fragment
        if path.find('#') != -1:
            return None

        # extract wildcard if it is there
        if host.find('*', 1) != -1:
            # wildcard must be at start of domain:  *.foo.com, not foo.*.com
            return None

        if host.startswith('*'):
            # Starts with star, so must have a dot after it (if a
            # domain is specified)
            if len(host) > 1 and host[1] != '.':
                return None

            host = host[1:]
            wilcard = True
        else:
            wilcard = False

        # we have a valid trust root
        tr = cls(trust_root, proto, wilcard, host, port, path)

        return tr

    parse = classmethod(parse)

    def checkSanity(cls, trust_root_string):
        """str -> bool

        is this a sane trust root?
        """
        trust_root = cls.parse(trust_root_string)
        if trust_root is None:
            return False
        else:
            return trust_root.isSane()

    checkSanity = classmethod(checkSanity)

    def checkURL(cls, trust_root, url):
        """quick func for validating a url against a trust root.  See the
        TrustRoot class if you need more control."""
        tr = cls.parse(trust_root)
        return tr is not None and tr.validateURL(url)

    checkURL = classmethod(checkURL)

    def buildDiscoveryURL(self):
        """Return a discovery URL for this realm.

        This function does not check to make sure that the realm is
        valid. Its behaviour on invalid inputs is undefined.

        @rtype: str

        @returns: The URL upon which relying party discovery should be run
            in order to verify the return_to URL

        @since: 2.1.0
        """
        if self.wildcard:
            # Use "www." in place of the star
            assert self.host.startswith('.'), self.host
            www_domain = 'www' + self.host
            return '%s://%s%s' % (self.proto, www_domain, self.path)
        else:
            return self.unparsed

    def __repr__(self):
        return "TrustRoot(%r, %r, %r, %r, %r, %r)" % (
            self.unparsed, self.proto, self.wildcard, self.host, self.port,
            self.path)

    def __str__(self):
        return repr(self)

# The URI for relying party discovery, used in realm verification.
#
# XXX: This should probably live somewhere else (like in
# openid.consumer or openid.yadis somewhere)
RP_RETURN_TO_URL_TYPE = 'http://specs.openid.net/auth/2.0/return_to'

def _extractReturnURL(endpoint):
    """If the endpoint is a relying party OpenID return_to endpoint,
    return the endpoint URL. Otherwise, return None.

    This function is intended to be used as a filter for the Yadis
    filtering interface.

    @see: C{L{openid.yadis.services}}
    @see: C{L{openid.yadis.filters}}

    @param endpoint: An XRDS BasicServiceEndpoint, as returned by
        performing Yadis dicovery.

    @returns: The endpoint URL or None if the endpoint is not a
        relying party endpoint.
    @rtype: str or NoneType
    """
    if endpoint.matchTypes([RP_RETURN_TO_URL_TYPE]):
        return endpoint.uri
    else:
        return None

def returnToMatches(allowed_return_to_urls, return_to):
    """Is the return_to URL under one of the supplied allowed
    return_to URLs?

    @since: 2.1.0
    """

    for allowed_return_to in allowed_return_to_urls:
        # A return_to pattern works the same as a realm, except that
        # it's not allowed to use a wildcard. We'll model this by
        # parsing it as a realm, and not trying to match it if it has
        # a wildcard.

        return_realm = TrustRoot.parse(allowed_return_to)
        if (# Parses as a trust root
            return_realm is not None and

            # Does not have a wildcard
            not return_realm.wildcard and

            # Matches the return_to that we passed in with it
            return_realm.validateURL(return_to)
            ):
            return True

    # No URL in the list matched
    return False

def getAllowedReturnURLs(relying_party_url):
    """Given a relying party discovery URL return a list of return_to URLs.

    @since: 2.1.0
    """
    (rp_url_after_redirects, return_to_urls) = services.getServiceEndpoints(
        relying_party_url, _extractReturnURL)

    if rp_url_after_redirects != relying_party_url:
        # Verification caused a redirect
        raise RealmVerificationRedirected(
            relying_party_url, rp_url_after_redirects)

    return return_to_urls

# _vrfy parameter is there to make testing easier
def verifyReturnTo(realm_str, return_to, _vrfy=getAllowedReturnURLs):
    """Verify that a return_to URL is valid for the given realm.

    This function builds a discovery URL, performs Yadis discovery on
    it, makes sure that the URL does not redirect, parses out the
    return_to URLs, and finally checks to see if the current return_to
    URL matches the return_to.

    @raises DiscoveryFailure: When Yadis discovery fails
    @returns: True if the return_to URL is valid for the realm

    @since: 2.1.0
    """
    realm = TrustRoot.parse(realm_str)
    if realm is None:
        # The realm does not parse as a URL pattern
        return False

    try:
        allowable_urls = _vrfy(realm.buildDiscoveryURL())
    except RealmVerificationRedirected, err:
        oidutil.log(str(err))
        return False

    if returnToMatches(allowable_urls, return_to):
        return True
    else:
        oidutil.log("Failed to validate return_to %r for realm %r, was not "
                    "in %s" % (return_to, realm_str, allowable_urls))
        return False

########NEW FILE########
__FILENAME__ = sreg
"""moved to L{openid.extensions.sreg}"""

import warnings
warnings.warn("openid.sreg has moved to openid.extensions.sreg",
              DeprecationWarning)

from openid.extensions.sreg import *

########NEW FILE########
__FILENAME__ = filestore
"""
This module contains an C{L{OpenIDStore}} implementation backed by
flat files.
"""

import string
import os
import os.path
import time

from errno import EEXIST, ENOENT

try:
    from tempfile import mkstemp
except ImportError:
    # Python < 2.3
    import warnings
    warnings.filterwarnings("ignore",
                            "tempnam is a potential security risk",
                            RuntimeWarning,
                            "openid.store.filestore")

    def mkstemp(dir):
        for _ in range(5):
            name = os.tempnam(dir)
            try:
                fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0600)
            except OSError, why:
                if why.errno != EEXIST:
                    raise
            else:
                return fd, name

        raise RuntimeError('Failed to get temp file after 5 attempts')

from openid.association import Association
from openid.store.interface import OpenIDStore
from openid.store import nonce
from openid import cryptutil, oidutil

_filename_allowed = string.ascii_letters + string.digits + '.'
try:
    # 2.4
    set
except NameError:
    try:
        # 2.3
        import sets
    except ImportError:
        # Python < 2.2
        d = {}
        for c in _filename_allowed:
            d[c] = None
        _isFilenameSafe = d.has_key
        del d
    else:
        _isFilenameSafe = sets.Set(_filename_allowed).__contains__
else:
    _isFilenameSafe = set(_filename_allowed).__contains__

def _safe64(s):
    h64 = oidutil.toBase64(cryptutil.sha1(s))
    h64 = h64.replace('+', '_')
    h64 = h64.replace('/', '.')
    h64 = h64.replace('=', '')
    return h64

def _filenameEscape(s):
    filename_chunks = []
    for c in s:
        if _isFilenameSafe(c):
            filename_chunks.append(c)
        else:
            filename_chunks.append('_%02X' % ord(c))
    return ''.join(filename_chunks)

def _removeIfPresent(filename):
    """Attempt to remove a file, returning whether the file existed at
    the time of the call.

    str -> bool
    """
    try:
        os.unlink(filename)
    except OSError, why:
        if why.errno == ENOENT:
            # Someone beat us to it, but it's gone, so that's OK
            return 0
        else:
            raise
    else:
        # File was present
        return 1

def _ensureDir(dir_name):
    """Create dir_name as a directory if it does not exist. If it
    exists, make sure that it is, in fact, a directory.

    Can raise OSError

    str -> NoneType
    """
    try:
        os.makedirs(dir_name)
    except OSError, why:
        if why.errno != EEXIST or not os.path.isdir(dir_name):
            raise

class FileOpenIDStore(OpenIDStore):
    """
    This is a filesystem-based store for OpenID associations and
    nonces.  This store should be safe for use in concurrent systems
    on both windows and unix (excluding NFS filesystems).  There are a
    couple race conditions in the system, but those failure cases have
    been set up in such a way that the worst-case behavior is someone
    having to try to log in a second time.

    Most of the methods of this class are implementation details.
    People wishing to just use this store need only pay attention to
    the C{L{__init__}} method.

    Methods of this object can raise OSError if unexpected filesystem
    conditions, such as bad permissions or missing directories, occur.
    """

    def __init__(self, directory):
        """
        Initializes a new FileOpenIDStore.  This initializes the
        nonce and association directories, which are subdirectories of
        the directory passed in.

        @param directory: This is the directory to put the store
            directories in.

        @type directory: C{str}
        """
        # Make absolute
        directory = os.path.normpath(os.path.abspath(directory))

        self.nonce_dir = os.path.join(directory, 'nonces')

        self.association_dir = os.path.join(directory, 'associations')

        # Temp dir must be on the same filesystem as the assciations
        # directory
        self.temp_dir = os.path.join(directory, 'temp')

        self.max_nonce_age = 6 * 60 * 60 # Six hours, in seconds

        self._setup()

    def _setup(self):
        """Make sure that the directories in which we store our data
        exist.

        () -> NoneType
        """
        _ensureDir(self.nonce_dir)
        _ensureDir(self.association_dir)
        _ensureDir(self.temp_dir)

    def _mktemp(self):
        """Create a temporary file on the same filesystem as
        self.association_dir.

        The temporary directory should not be cleaned if there are any
        processes using the store. If there is no active process using
        the store, it is safe to remove all of the files in the
        temporary directory.

        () -> (file, str)
        """
        fd, name = mkstemp(dir=self.temp_dir)
        try:
            file_obj = os.fdopen(fd, 'wb')
            return file_obj, name
        except:
            _removeIfPresent(name)
            raise

    def getAssociationFilename(self, server_url, handle):
        """Create a unique filename for a given server url and
        handle. This implementation does not assume anything about the
        format of the handle. The filename that is returned will
        contain the domain name from the server URL for ease of human
        inspection of the data directory.

        (str, str) -> str
        """
        if server_url.find('://') == -1:
            raise ValueError('Bad server URL: %r' % server_url)

        proto, rest = server_url.split('://', 1)
        domain = _filenameEscape(rest.split('/', 1)[0])
        url_hash = _safe64(server_url)
        if handle:
            handle_hash = _safe64(handle)
        else:
            handle_hash = ''

        filename = '%s-%s-%s-%s' % (proto, domain, url_hash, handle_hash)

        return os.path.join(self.association_dir, filename)

    def storeAssociation(self, server_url, association):
        """Store an association in the association directory.

        (str, Association) -> NoneType
        """
        association_s = association.serialize()
        filename = self.getAssociationFilename(server_url, association.handle)
        tmp_file, tmp = self._mktemp()

        try:
            try:
                tmp_file.write(association_s)
                os.fsync(tmp_file.fileno())
            finally:
                tmp_file.close()

            try:
                os.rename(tmp, filename)
            except OSError, why:
                if why.errno != EEXIST:
                    raise

                # We only expect EEXIST to happen only on Windows. It's
                # possible that we will succeed in unlinking the existing
                # file, but not in putting the temporary file in place.
                try:
                    os.unlink(filename)
                except OSError, why:
                    if why.errno == ENOENT:
                        pass
                    else:
                        raise

                # Now the target should not exist. Try renaming again,
                # giving up if it fails.
                os.rename(tmp, filename)
        except:
            # If there was an error, don't leave the temporary file
            # around.
            _removeIfPresent(tmp)
            raise

    def getAssociation(self, server_url, handle=None):
        """Retrieve an association. If no handle is specified, return
        the association with the latest expiration.

        (str, str or NoneType) -> Association or NoneType
        """
        if handle is None:
            handle = ''

        # The filename with the empty handle is a prefix of all other
        # associations for the given server URL.
        filename = self.getAssociationFilename(server_url, handle)

        if handle:
            return self._getAssociation(filename)
        else:
            association_files = os.listdir(self.association_dir)
            matching_files = []
            # strip off the path to do the comparison
            name = os.path.basename(filename)
            for association_file in association_files:
                if association_file.startswith(name):
                    matching_files.append(association_file)

            matching_associations = []
            # read the matching files and sort by time issued
            for name in matching_files:
                full_name = os.path.join(self.association_dir, name)
                association = self._getAssociation(full_name)
                if association is not None:
                    matching_associations.append(
                        (association.issued, association))

            matching_associations.sort()

            # return the most recently issued one.
            if matching_associations:
                (_, assoc) = matching_associations[-1]
                return assoc
            else:
                return None

    def _getAssociation(self, filename):
        try:
            assoc_file = file(filename, 'rb')
        except IOError, why:
            if why.errno == ENOENT:
                # No association exists for that URL and handle
                return None
            else:
                raise
        else:
            try:
                assoc_s = assoc_file.read()
            finally:
                assoc_file.close()

            try:
                association = Association.deserialize(assoc_s)
            except ValueError:
                _removeIfPresent(filename)
                return None

        # Clean up expired associations
        if association.getExpiresIn() == 0:
            _removeIfPresent(filename)
            return None
        else:
            return association

    def removeAssociation(self, server_url, handle):
        """Remove an association if it exists. Do nothing if it does not.

        (str, str) -> bool
        """
        assoc = self.getAssociation(server_url, handle)
        if assoc is None:
            return 0
        else:
            filename = self.getAssociationFilename(server_url, handle)
            return _removeIfPresent(filename)

    def useNonce(self, server_url, timestamp, salt):
        """Return whether this nonce is valid.

        str -> bool
        """
        if abs(timestamp - time.time()) > nonce.SKEW:
            return False

        if server_url:
            proto, rest = server_url.split('://', 1)
        else:
            # Create empty proto / rest values for empty server_url,
            # which is part of a consumer-generated nonce.
            proto, rest = '', ''

        domain = _filenameEscape(rest.split('/', 1)[0])
        url_hash = _safe64(server_url)
        salt_hash = _safe64(salt)

        filename = '%08x-%s-%s-%s-%s' % (timestamp, proto, domain,
                                         url_hash, salt_hash)

        filename = os.path.join(self.nonce_dir, filename)
        try:
            fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0200)
        except OSError, why:
            if why.errno == EEXIST:
                return False
            else:
                raise
        else:
            os.close(fd)
            return True

    def _allAssocs(self):
        all_associations = []

        association_filenames = map(
            lambda filename: os.path.join(self.association_dir, filename),
            os.listdir(self.association_dir))
        for association_filename in association_filenames:
            try:
                association_file = file(association_filename, 'rb')
            except IOError, why:
                if why.errno == ENOENT:
                    oidutil.log("%s disappeared during %s._allAssocs" % (
                        association_filename, self.__class__.__name__))
                else:
                    raise
            else:
                try:
                    assoc_s = association_file.read()
                finally:
                    association_file.close()

                # Remove expired or corrupted associations
                try:
                    association = Association.deserialize(assoc_s)
                except ValueError:
                    _removeIfPresent(association_filename)
                else:
                    all_associations.append(
                        (association_filename, association))

        return all_associations

    def cleanup(self):
        """Remove expired entries from the database. This is
        potentially expensive, so only run when it is acceptable to
        take time.

        () -> NoneType
        """
        self.cleanupAssociations()
        self.cleanupNonces()

    def cleanupAssociations(self):
        removed = 0
        for assoc_filename, assoc in self._allAssocs():
            if assoc.getExpiresIn() == 0:
                _removeIfPresent(assoc_filename)
                removed += 1
        return removed

    def cleanupNonces(self):
        nonces = os.listdir(self.nonce_dir)
        now = time.time()

        removed = 0
        # Check all nonces for expiry
        for nonce_fname in nonces:
            timestamp = nonce_fname.split('-', 1)[0]
            timestamp = int(timestamp, 16)
            if abs(timestamp - now) > nonce.SKEW:
                filename = os.path.join(self.nonce_dir, nonce_fname)
                _removeIfPresent(filename)
                removed += 1
        return removed

########NEW FILE########
__FILENAME__ = interface
"""
This module contains the definition of the C{L{OpenIDStore}}
interface.
"""

class OpenIDStore(object):
    """
    This is the interface for the store objects the OpenID library
    uses.  It is a single class that provides all of the persistence
    mechanisms that the OpenID library needs, for both servers and
    consumers.

    @change: Version 2.0 removed the C{storeNonce}, C{getAuthKey}, and C{isDumb}
        methods, and changed the behavior of the C{L{useNonce}} method
        to support one-way nonces.  It added C{L{cleanupNonces}},
        C{L{cleanupAssociations}}, and C{L{cleanup}}.

    @sort: storeAssociation, getAssociation, removeAssociation,
        useNonce
    """

    def storeAssociation(self, server_url, association):
        """
        This method puts a C{L{Association
        <openid.association.Association>}} object into storage,
        retrievable by server URL and handle.


        @param server_url: The URL of the identity server that this
            association is with.  Because of the way the server
            portion of the library uses this interface, don't assume
            there are any limitations on the character set of the
            input string.  In particular, expect to see unescaped
            non-url-safe characters in the server_url field.

        @type server_url: C{str}


        @param association: The C{L{Association
            <openid.association.Association>}} to store.

        @type association: C{L{Association
            <openid.association.Association>}}


        @return: C{None}

        @rtype: C{NoneType}
        """
        raise NotImplementedError

    def getAssociation(self, server_url, handle=None):
        """
        This method returns an C{L{Association
        <openid.association.Association>}} object from storage that
        matches the server URL and, if specified, handle. It returns
        C{None} if no such association is found or if the matching
        association is expired.

        If no handle is specified, the store may return any
        association which matches the server URL.  If multiple
        associations are valid, the recommended return value for this
        method is the one most recently issued.

        This method is allowed (and encouraged) to garbage collect
        expired associations when found. This method must not return
        expired associations.


        @param server_url: The URL of the identity server to get the
            association for.  Because of the way the server portion of
            the library uses this interface, don't assume there are
            any limitations on the character set of the input string.
            In particular, expect to see unescaped non-url-safe
            characters in the server_url field.

        @type server_url: C{str}


        @param handle: This optional parameter is the handle of the
            specific association to get.  If no specific handle is
            provided, any valid association matching the server URL is
            returned.

        @type handle: C{str} or C{NoneType}


        @return: The C{L{Association
            <openid.association.Association>}} for the given identity
            server.

        @rtype: C{L{Association <openid.association.Association>}} or
            C{NoneType}
        """
        raise NotImplementedError

    def removeAssociation(self, server_url, handle):
        """
        This method removes the matching association if it's found,
        and returns whether the association was removed or not.


        @param server_url: The URL of the identity server the
            association to remove belongs to.  Because of the way the
            server portion of the library uses this interface, don't
            assume there are any limitations on the character set of
            the input string.  In particular, expect to see unescaped
            non-url-safe characters in the server_url field.

        @type server_url: C{str}


        @param handle: This is the handle of the association to
            remove.  If there isn't an association found that matches
            both the given URL and handle, then there was no matching
            handle found.

        @type handle: C{str}


        @return: Returns whether or not the given association existed.

        @rtype: C{bool} or C{int}
        """
        raise NotImplementedError

    def useNonce(self, server_url, timestamp, salt):
        """Called when using a nonce.

        This method should return C{True} if the nonce has not been
        used before, and store it for a while to make sure nobody
        tries to use the same value again.  If the nonce has already
        been used or the timestamp is not current, return C{False}.

        You may use L{openid.store.nonce.SKEW} for your timestamp window.

        @change: In earlier versions, round-trip nonces were used and
           a nonce was only valid if it had been previously stored
           with C{storeNonce}.  Version 2.0 uses one-way nonces,
           requiring a different implementation here that does not
           depend on a C{storeNonce} call.  (C{storeNonce} is no
           longer part of the interface.)

        @param server_url: The URL of the server from which the nonce
            originated.

        @type server_url: C{str}

        @param timestamp: The time that the nonce was created (to the
            nearest second), in seconds since January 1 1970 UTC.
        @type timestamp: C{int}

        @param salt: A random string that makes two nonces from the
            same server issued during the same second unique.
        @type salt: str

        @return: Whether or not the nonce was valid.

        @rtype: C{bool}
        """
        raise NotImplementedError

    def cleanupNonces(self):
        """Remove expired nonces from the store.

        Discards any nonce from storage that is old enough that its
        timestamp would not pass L{useNonce}.

        This method is not called in the normal operation of the
        library.  It provides a way for store admins to keep
        their storage from filling up with expired data.

        @return: the number of nonces expired.
        @returntype: int
        """
        raise NotImplementedError

    def cleanupAssociations(self):
        """Remove expired associations from the store.

        This method is not called in the normal operation of the
        library.  It provides a way for store admins to keep
        their storage from filling up with expired data.

        @return: the number of associations expired.
        @returntype: int
        """
        raise NotImplementedError

    def cleanup(self):
        """Shortcut for C{L{cleanupNonces}()}, C{L{cleanupAssociations}()}.

        This method is not called in the normal operation of the
        library.  It provides a way for store admins to keep
        their storage from filling up with expired data.
        """
        return self.cleanupNonces(), self.cleanupAssociations()

########NEW FILE########
__FILENAME__ = memstore
"""A simple store using only in-process memory."""

from openid.store import nonce

import copy
import time

class ServerAssocs(object):
    def __init__(self):
        self.assocs = {}

    def set(self, assoc):
        self.assocs[assoc.handle] = assoc

    def get(self, handle):
        return self.assocs.get(handle)

    def remove(self, handle):
        try:
            del self.assocs[handle]
        except KeyError:
            return False
        else:
            return True

    def best(self):
        """Returns association with the oldest issued date.

        or None if there are no associations.
        """
        best = None
        for assoc in self.assocs.values():
            if best is None or best.issued < assoc.issued:
                best = assoc
        return best

    def cleanup(self):
        """Remove expired associations.

        @return: tuple of (removed associations, remaining associations)
        """
        remove = []
        for handle, assoc in self.assocs.iteritems():
            if assoc.getExpiresIn() == 0:
                remove.append(handle)
        for handle in remove:
            del self.assocs[handle]
        return len(remove), len(self.assocs)



class MemoryStore(object):
    """In-process memory store.

    Use for single long-running processes.  No persistence supplied.
    """
    def __init__(self):
        self.server_assocs = {}
        self.nonces = {}

    def _getServerAssocs(self, server_url):
        try:
            return self.server_assocs[server_url]
        except KeyError:
            assocs = self.server_assocs[server_url] = ServerAssocs()
            return assocs

    def storeAssociation(self, server_url, assoc):
        assocs = self._getServerAssocs(server_url)
        assocs.set(copy.deepcopy(assoc))

    def getAssociation(self, server_url, handle=None):
        assocs = self._getServerAssocs(server_url)
        if handle is None:
            return assocs.best()
        else:
            return assocs.get(handle)

    def removeAssociation(self, server_url, handle):
        assocs = self._getServerAssocs(server_url)
        return assocs.remove(handle)

    def useNonce(self, server_url, timestamp, salt):
        if abs(timestamp - time.time()) > nonce.SKEW:
            return False

        anonce = (str(server_url), int(timestamp), str(salt))
        if anonce in self.nonces:
            return False
        else:
            self.nonces[anonce] = None
            return True

    def cleanupNonces(self):
        now = time.time()
        expired = []
        for anonce in self.nonces.iterkeys():
            if abs(anonce[1] - now) > nonce.SKEW:
                # removing items while iterating over the set could be bad.
                expired.append(anonce)

        for anonce in expired:
            del self.nonces[anonce]
        return len(expired)

    def cleanupAssociations(self):
        remove_urls = []
        removed_assocs = 0
        for server_url, assocs in self.server_assocs.iteritems():
            removed, remaining = assocs.cleanup()
            removed_assocs += removed
            if not remaining:
                remove_urls.append(server_url)

        # Remove entries from server_assocs that had none remaining.
        for server_url in remove_urls:
            del self.server_assocs[server_url]
        return removed_assocs

    def __eq__(self, other):
        return ((self.server_assocs == other.server_assocs) and
                (self.nonces == other.nonces))

    def __ne__(self, other):
        return not (self == other)

########NEW FILE########
__FILENAME__ = nonce
__all__ = [
    'split',
    'mkNonce',
    'checkTimestamp',
    ]

from openid import cryptutil
from time import strptime, strftime, gmtime, time
from calendar import timegm
import string

NONCE_CHARS = string.ascii_letters + string.digits

# Keep nonces for five hours (allow five hours for the combination of
# request time and clock skew). This is probably way more than is
# necessary, but there is not much overhead in storing nonces.
SKEW = 60 * 60 * 5

time_fmt = '%Y-%m-%dT%H:%M:%SZ'
time_str_len = len('0000-00-00T00:00:00Z')

def split(nonce_string):
    """Extract a timestamp from the given nonce string

    @param nonce_string: the nonce from which to extract the timestamp
    @type nonce_string: str

    @returns: A pair of a Unix timestamp and the salt characters
    @returntype: (int, str)

    @raises ValueError: if the nonce does not start with a correctly
        formatted time string
    """
    timestamp_str = nonce_string[:time_str_len]
    try:
        timestamp = timegm(strptime(timestamp_str, time_fmt))
    except AssertionError: # Python 2.2
        timestamp = -1
    if timestamp < 0:
        raise ValueError('time out of range')
    return timestamp, nonce_string[time_str_len:]

def checkTimestamp(nonce_string, allowed_skew=SKEW, now=None):
    """Is the timestamp that is part of the specified nonce string
    within the allowed clock-skew of the current time?

    @param nonce_string: The nonce that is being checked
    @type nonce_string: str

    @param allowed_skew: How many seconds should be allowed for
        completing the request, allowing for clock skew.
    @type allowed_skew: int

    @param now: The current time, as a Unix timestamp
    @type now: int

    @returntype: bool
    @returns: Whether the timestamp is correctly formatted and within
        the allowed skew of the current time.
    """
    try:
        stamp, _ = split(nonce_string)
    except ValueError:
        return False
    else:
        if now is None:
            now = time()

        # Time after which we should not use the nonce
        past = now - allowed_skew

        # Time that is too far in the future for us to allow
        future = now + allowed_skew

        # the stamp is not too far in the future and is not too far in
        # the past
        return past <= stamp <= future

def mkNonce(when=None):
    """Generate a nonce with the current timestamp

    @param when: Unix timestamp representing the issue time of the
        nonce. Defaults to the current time.
    @type when: int

    @returntype: str
    @returns: A string that should be usable as a one-way nonce

    @see: time
    """
    salt = cryptutil.randomString(6, NONCE_CHARS)
    if when is None:
        t = gmtime()
    else:
        t = gmtime(when)

    time_str = strftime(time_fmt, t)
    return time_str + salt

########NEW FILE########
__FILENAME__ = sqlstore
"""
This module contains C{L{OpenIDStore}} implementations that use
various SQL databases to back them.

Example of how to initialize a store database::

    python -c 'from openid.store import sqlstore; import pysqlite2.dbapi2; sqlstore.SQLiteStore(pysqlite2.dbapi2.connect("cstore.db")).createTables()'
"""
import re
import time

from openid.association import Association
from openid.store.interface import OpenIDStore
from openid.store import nonce

def _inTxn(func):
    def wrapped(self, *args, **kwargs):
        return self._callInTransaction(func, self, *args, **kwargs)

    if hasattr(func, '__name__'):
        try:
            wrapped.__name__ = func.__name__[4:]
        except TypeError:
            pass

    if hasattr(func, '__doc__'):
        wrapped.__doc__ = func.__doc__

    return wrapped

class SQLStore(OpenIDStore):
    """
    This is the parent class for the SQL stores, which contains the
    logic common to all of the SQL stores.

    The table names used are determined by the class variables
    C{L{associations_table}} and
    C{L{nonces_table}}.  To change the name of the tables used, pass
    new table names into the constructor.

    To create the tables with the proper schema, see the
    C{L{createTables}} method.

    This class shouldn't be used directly.  Use one of its subclasses
    instead, as those contain the code necessary to use a specific
    database.

    All methods other than C{L{__init__}} and C{L{createTables}}
    should be considered implementation details.


    @cvar associations_table: This is the default name of the table to
        keep associations in

    @cvar nonces_table: This is the default name of the table to keep
        nonces in.


    @sort: __init__, createTables
    """

    associations_table = 'oid_associations'
    nonces_table = 'oid_nonces'

    def __init__(self, conn, associations_table=None, nonces_table=None):
        """
        This creates a new SQLStore instance.  It requires an
        established database connection be given to it, and it allows
        overriding the default table names.


        @param conn: This must be an established connection to a
            database of the correct type for the SQLStore subclass
            you're using.

        @type conn: A python database API compatible connection
            object.


        @param associations_table: This is an optional parameter to
            specify the name of the table used for storing
            associations.  The default value is specified in
            C{L{SQLStore.associations_table}}.

        @type associations_table: C{str}


        @param nonces_table: This is an optional parameter to specify
            the name of the table used for storing nonces.  The
            default value is specified in C{L{SQLStore.nonces_table}}.

        @type nonces_table: C{str}
        """
        self.conn = conn
        self.cur = None
        self._statement_cache = {}
        self._table_names = {
            'associations': associations_table or self.associations_table,
            'nonces': nonces_table or self.nonces_table,
            }
        self.max_nonce_age = 6 * 60 * 60 # Six hours, in seconds

        # DB API extension: search for "Connection Attributes .Error,
        # .ProgrammingError, etc." in
        # http://www.python.org/dev/peps/pep-0249/
        if (hasattr(self.conn, 'IntegrityError') and
            hasattr(self.conn, 'OperationalError')):
            self.exceptions = self.conn

        if not (hasattr(self.exceptions, 'IntegrityError') and
                hasattr(self.exceptions, 'OperationalError')):
            raise RuntimeError("Error using database connection module "
                               "(Maybe it can't be imported?)")

    def blobDecode(self, blob):
        """Convert a blob as returned by the SQL engine into a str object.

        str -> str"""
        return blob

    def blobEncode(self, s):
        """Convert a str object into the necessary object for storing
        in the database as a blob."""
        return s

    def _getSQL(self, sql_name):
        try:
            return self._statement_cache[sql_name]
        except KeyError:
            sql = getattr(self, sql_name)
            sql %= self._table_names
            self._statement_cache[sql_name] = sql
            return sql

    def _execSQL(self, sql_name, *args):
        sql = self._getSQL(sql_name)
        # Kludge because we have reports of postgresql not quoting
        # arguments if they are passed in as unicode instead of str.
        # Currently the strings in our tables just have ascii in them,
        # so this ought to be safe.
        def unicode_to_str(arg):
            if isinstance(arg, unicode):
                return str(arg)
            else:
                return arg
        str_args = map(unicode_to_str, args)
        self.cur.execute(sql, str_args)

    def __getattr__(self, attr):
        # if the attribute starts with db_, use a default
        # implementation that looks up the appropriate SQL statement
        # as an attribute of this object and executes it.
        if attr[:3] == 'db_':
            sql_name = attr[3:] + '_sql'
            def func(*args):
                return self._execSQL(sql_name, *args)
            setattr(self, attr, func)
            return func
        else:
            raise AttributeError('Attribute %r not found' % (attr,))

    def _callInTransaction(self, func, *args, **kwargs):
        """Execute the given function inside of a transaction, with an
        open cursor. If no exception is raised, the transaction is
        comitted, otherwise it is rolled back."""
        # No nesting of transactions
        self.conn.rollback()

        try:
            self.cur = self.conn.cursor()
            try:
                ret = func(*args, **kwargs)
            finally:
                self.cur.close()
                self.cur = None
        except:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

        return ret

    def txn_createTables(self):
        """
        This method creates the database tables necessary for this
        store to work.  It should not be called if the tables already
        exist.
        """
        self.db_create_nonce()
        self.db_create_assoc()

    createTables = _inTxn(txn_createTables)

    def txn_storeAssociation(self, server_url, association):
        """Set the association for the server URL.

        Association -> NoneType
        """
        a = association
        self.db_set_assoc(
            server_url,
            a.handle,
            self.blobEncode(a.secret),
            a.issued,
            a.lifetime,
            a.assoc_type)

    storeAssociation = _inTxn(txn_storeAssociation)

    def txn_getAssociation(self, server_url, handle=None):
        """Get the most recent association that has been set for this
        server URL and handle.

        str -> NoneType or Association
        """
        if handle is not None:
            self.db_get_assoc(server_url, handle)
        else:
            self.db_get_assocs(server_url)

        rows = self.cur.fetchall()
        if len(rows) == 0:
            return None
        else:
            associations = []
            for values in rows:
                assoc = Association(*values)
                assoc.secret = self.blobDecode(assoc.secret)
                if assoc.getExpiresIn() == 0:
                    self.txn_removeAssociation(server_url, assoc.handle)
                else:
                    associations.append((assoc.issued, assoc))

            if associations:
                associations.sort()
                return associations[-1][1]
            else:
                return None

    getAssociation = _inTxn(txn_getAssociation)

    def txn_removeAssociation(self, server_url, handle):
        """Remove the association for the given server URL and handle,
        returning whether the association existed at all.

        (str, str) -> bool
        """
        self.db_remove_assoc(server_url, handle)
        return self.cur.rowcount > 0 # -1 is undefined

    removeAssociation = _inTxn(txn_removeAssociation)

    def txn_useNonce(self, server_url, timestamp, salt):
        """Return whether this nonce is present, and if it is, then
        remove it from the set.

        str -> bool"""
        if abs(timestamp - time.time()) > nonce.SKEW:
            return False

        try:
            self.db_add_nonce(server_url, timestamp, salt)
        except self.exceptions.IntegrityError:
            # The key uniqueness check failed
            return False
        else:
            # The nonce was successfully added
            return True

    useNonce = _inTxn(txn_useNonce)

    def txn_cleanupNonces(self):
        self.db_clean_nonce(int(time.time()) - nonce.SKEW)
        return self.cur.rowcount

    cleanupNonces = _inTxn(txn_cleanupNonces)

    def txn_cleanupAssociations(self):
        self.db_clean_assoc(int(time.time()))
        return self.cur.rowcount

    cleanupAssociations = _inTxn(txn_cleanupAssociations)


class SQLiteStore(SQLStore):
    """
    This is an SQLite-based specialization of C{L{SQLStore}}.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """

    create_nonce_sql = """
    CREATE TABLE %(nonces)s (
        server_url VARCHAR,
        timestamp INTEGER,
        salt CHAR(40),
        UNIQUE(server_url, timestamp, salt)
    );
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url VARCHAR(2047),
        handle VARCHAR(255),
        secret BLOB(128),
        issued INTEGER,
        lifetime INTEGER,
        assoc_type VARCHAR(64),
        PRIMARY KEY (server_url, handle)
    );
    """

    set_assoc_sql = ('INSERT OR REPLACE INTO %(associations)s '
                     '(server_url, handle, secret, issued, '
                     'lifetime, assoc_type) '
                     'VALUES (?, ?, ?, ?, ?, ?);')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type '
                      'FROM %(associations)s WHERE server_url = ?;')
    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type '
        'FROM %(associations)s WHERE server_url = ? AND handle = ?;')

    get_expired_sql = ('SELECT server_url '
                       'FROM %(associations)s WHERE issued + lifetime < ?;')

    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = ? AND handle = ?;')

    clean_assoc_sql = 'DELETE FROM %(associations)s WHERE issued + lifetime < ?;'

    add_nonce_sql = 'INSERT INTO %(nonces)s VALUES (?, ?, ?);'

    clean_nonce_sql = 'DELETE FROM %(nonces)s WHERE timestamp < ?;'

    def blobDecode(self, buf):
        return str(buf)

    def blobEncode(self, s):
        return buffer(s)

    def useNonce(self, *args, **kwargs):
        # Older versions of the sqlite wrapper do not raise
        # IntegrityError as they should, so we have to detect the
        # message from the OperationalError.
        try:
            return super(SQLiteStore, self).useNonce(*args, **kwargs)
        except self.exceptions.OperationalError, why:
            if re.match('^columns .* are not unique$', why[0]):
                return False
            else:
                raise

class MySQLStore(SQLStore):
    """
    This is a MySQL-based specialization of C{L{SQLStore}}.

    Uses InnoDB tables for transaction support.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """

    try:
        import MySQLdb as exceptions
    except ImportError:
        exceptions = None

    create_nonce_sql = """
    CREATE TABLE %(nonces)s (
        server_url BLOB NOT NULL,
        timestamp INTEGER NOT NULL,
        salt CHAR(40) NOT NULL,
        PRIMARY KEY (server_url(255), timestamp, salt)
    )
    ENGINE=InnoDB;
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url BLOB NOT NULL,
        handle VARCHAR(255) NOT NULL,
        secret BLOB NOT NULL,
        issued INTEGER NOT NULL,
        lifetime INTEGER NOT NULL,
        assoc_type VARCHAR(64) NOT NULL,
        PRIMARY KEY (server_url(255), handle)
    )
    ENGINE=InnoDB;
    """

    set_assoc_sql = ('REPLACE INTO %(associations)s '
                     'VALUES (%%s, %%s, %%s, %%s, %%s, %%s);')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type'
                      ' FROM %(associations)s WHERE server_url = %%s;')
    get_expired_sql = ('SELECT server_url '
                       'FROM %(associations)s WHERE issued + lifetime < %%s;')

    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type'
        ' FROM %(associations)s WHERE server_url = %%s AND handle = %%s;')
    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = %%s AND handle = %%s;')

    clean_assoc_sql = 'DELETE FROM %(associations)s WHERE issued + lifetime < %%s;'

    add_nonce_sql = 'INSERT INTO %(nonces)s VALUES (%%s, %%s, %%s);'

    clean_nonce_sql = 'DELETE FROM %(nonces)s WHERE timestamp < %%s;'

    def blobDecode(self, blob):
        if type(blob) is str:
            # Versions of MySQLdb >= 1.2.2
            return blob
        else:
            # Versions of MySQLdb prior to 1.2.2 (as far as we can tell)
            return blob.tostring()

class PostgreSQLStore(SQLStore):
    """
    This is a PostgreSQL-based specialization of C{L{SQLStore}}.

    To create an instance, see C{L{SQLStore.__init__}}.  To create the
    tables it will use, see C{L{SQLStore.createTables}}.

    All other methods are implementation details.
    """

    try:
        import psycopg as exceptions
    except ImportError:
        # psycopg2 has the dbapi extension where the exception classes
        # are available on the connection object. A psycopg2
        # connection will use the correct exception classes because of
        # this, and a psycopg connection will fall through to use the
        # psycopg imported above.
        exceptions = None

    create_nonce_sql = """
    CREATE TABLE %(nonces)s (
        server_url VARCHAR(2047) NOT NULL,
        timestamp INTEGER NOT NULL,
        salt CHAR(40) NOT NULL,
        PRIMARY KEY (server_url, timestamp, salt)
    );
    """

    create_assoc_sql = """
    CREATE TABLE %(associations)s
    (
        server_url VARCHAR(2047) NOT NULL,
        handle VARCHAR(255) NOT NULL,
        secret BYTEA NOT NULL,
        issued INTEGER NOT NULL,
        lifetime INTEGER NOT NULL,
        assoc_type VARCHAR(64) NOT NULL,
        PRIMARY KEY (server_url, handle),
        CONSTRAINT secret_length_constraint CHECK (LENGTH(secret) <= 128)
    );
    """

    def db_set_assoc(self, server_url, handle, secret, issued, lifetime, assoc_type):
        """
        Set an association.  This is implemented as a method because
        REPLACE INTO is not supported by PostgreSQL (and is not
        standard SQL).
        """
        result = self.db_get_assoc(server_url, handle)
        rows = self.cur.fetchall()
        if len(rows):
            # Update the table since this associations already exists.
            return self.db_update_assoc(secret, issued, lifetime, assoc_type,
                                        server_url, handle)
        else:
            # Insert a new record because this association wasn't
            # found.
            return self.db_new_assoc(server_url, handle, secret, issued,
                                     lifetime, assoc_type)

    new_assoc_sql = ('INSERT INTO %(associations)s '
                     'VALUES (%%s, %%s, %%s, %%s, %%s, %%s);')
    update_assoc_sql = ('UPDATE %(associations)s SET '
                        'secret = %%s, issued = %%s, '
                        'lifetime = %%s, assoc_type = %%s '
                        'WHERE server_url = %%s AND handle = %%s;')
    get_assocs_sql = ('SELECT handle, secret, issued, lifetime, assoc_type'
                      ' FROM %(associations)s WHERE server_url = %%s;')
    get_expired_sql = ('SELECT server_url '
                       'FROM %(associations)s WHERE issued + lifetime < %%s;')

    get_assoc_sql = (
        'SELECT handle, secret, issued, lifetime, assoc_type'
        ' FROM %(associations)s WHERE server_url = %%s AND handle = %%s;')
    remove_assoc_sql = ('DELETE FROM %(associations)s '
                        'WHERE server_url = %%s AND handle = %%s;')

    clean_assoc_sql = 'DELETE FROM %(associations)s WHERE issued + lifetime < %%s;'

    add_nonce_sql = 'INSERT INTO %(nonces)s VALUES (%%s, %%s, %%s);'

    clean_nonce_sql = 'DELETE FROM %(nonces)s WHERE timestamp < %%s;'

    def blobEncode(self, blob):
        try:
            from psycopg2 import Binary
        except ImportError:
            from psycopg import Binary

        return Binary(blob)

########NEW FILE########
__FILENAME__ = urinorm
import re

# from appendix B of rfc 3986 (http://www.ietf.org/rfc/rfc3986.txt)
uri_pattern = r'^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?'
uri_re = re.compile(uri_pattern)

# gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
#
# sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
#                  / "*" / "+" / "," / ";" / "="
#
# unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"

uri_illegal_char_re = re.compile(
    "[^-A-Za-z0-9:/?#[\]@!$&'()*+,;=._~%]", re.UNICODE)

authority_pattern = r'^([^@]*@)?([^:]*)(:.*)?'
authority_re = re.compile(authority_pattern)


pct_encoded_pattern = r'%([0-9A-Fa-f]{2})'
pct_encoded_re = re.compile(pct_encoded_pattern)

try:
    unichr(0x10000)
except ValueError:
    # narrow python build
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        ]
else:
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        (0x10000, 0x1FFFD),
        (0x20000, 0x2FFFD),
        (0x30000, 0x3FFFD),
        (0x40000, 0x4FFFD),
        (0x50000, 0x5FFFD),
        (0x60000, 0x6FFFD),
        (0x70000, 0x7FFFD),
        (0x80000, 0x8FFFD),
        (0x90000, 0x9FFFD),
        (0xA0000, 0xAFFFD),
        (0xB0000, 0xBFFFD),
        (0xC0000, 0xCFFFD),
        (0xD0000, 0xDFFFD),
        (0xE1000, 0xEFFFD),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        (0xF0000, 0xFFFFD),
        (0x100000, 0x10FFFD),
        ]


_unreserved = [False] * 256
for _ in range(ord('A'), ord('Z') + 1): _unreserved[_] = True
for _ in range(ord('0'), ord('9') + 1): _unreserved[_] = True
for _ in range(ord('a'), ord('z') + 1): _unreserved[_] = True
_unreserved[ord('-')] = True
_unreserved[ord('.')] = True
_unreserved[ord('_')] = True
_unreserved[ord('~')] = True


_escapeme_re = re.compile('[%s]' % (''.join(
    map(lambda (m, n): u'%s-%s' % (unichr(m), unichr(n)),
        UCSCHAR + IPRIVATE)),))


def _pct_escape_unicode(char_match):
    c = char_match.group()
    return ''.join(['%%%X' % (ord(octet),) for octet in c.encode('utf-8')])


def _pct_encoded_replace_unreserved(mo):
    try:
        i = int(mo.group(1), 16)
        if _unreserved[i]:
            return chr(i)
        else:
            return mo.group().upper()

    except ValueError:
        return mo.group()


def _pct_encoded_replace(mo):
    try:
        return chr(int(mo.group(1), 16))
    except ValueError:
        return mo.group()


def remove_dot_segments(path):
    result_segments = []

    while path:
        if path.startswith('../'):
            path = path[3:]
        elif path.startswith('./'):
            path = path[2:]
        elif path.startswith('/./'):
            path = path[2:]
        elif path == '/.':
            path = '/'
        elif path.startswith('/../'):
            path = path[3:]
            if result_segments:
                result_segments.pop()
        elif path == '/..':
            path = '/'
            if result_segments:
                result_segments.pop()
        elif path == '..' or path == '.':
            path = ''
        else:
            i = 0
            if path[0] == '/':
                i = 1
            i = path.find('/', i)
            if i == -1:
                i = len(path)
            result_segments.append(path[:i])
            path = path[i:]

    return ''.join(result_segments)


def urinorm(uri):
    if isinstance(uri, unicode):
        uri = _escapeme_re.sub(_pct_escape_unicode, uri).encode('ascii')

    illegal_mo = uri_illegal_char_re.search(uri)
    if illegal_mo:
        raise ValueError('Illegal characters in URI: %r at position %s' %
                         (illegal_mo.group(), illegal_mo.start()))

    uri_mo = uri_re.match(uri)

    scheme = uri_mo.group(2)
    if scheme is None:
        raise ValueError('No scheme specified')

    scheme = scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError('Not an absolute HTTP or HTTPS URI: %r' % (uri,))

    authority = uri_mo.group(4)
    if authority is None:
        raise ValueError('Not an absolute URI: %r' % (uri,))

    authority_mo = authority_re.match(authority)
    if authority_mo is None:
        raise ValueError('URI does not have a valid authority: %r' % (uri,))

    userinfo, host, port = authority_mo.groups()

    if userinfo is None:
        userinfo = ''

    if '%' in host:
        host = host.lower()
        host = pct_encoded_re.sub(_pct_encoded_replace, host)
        host = unicode(host, 'utf-8').encode('idna')
    else:
        host = host.lower()

    if port:
        if (port == ':' or
            (scheme == 'http' and port == ':80') or
            (scheme == 'https' and port == ':443')):
            port = ''
    else:
        port = ''

    authority = userinfo + host + port

    path = uri_mo.group(5)
    path = pct_encoded_re.sub(_pct_encoded_replace_unreserved, path)
    path = remove_dot_segments(path)
    if not path:
        path = '/'

    query = uri_mo.group(6)
    if query is None:
        query = ''

    fragment = uri_mo.group(8)
    if fragment is None:
        fragment = ''

    return scheme + '://' + authority + path + query + fragment

########NEW FILE########
__FILENAME__ = accept
"""Functions for generating and parsing HTTP Accept: headers for
supporting server-directed content negotiation.
"""

def generateAcceptHeader(*elements):
    """Generate an accept header value

    [str or (str, float)] -> str
    """
    parts = []
    for element in elements:
        if type(element) is str:
            qs = "1.0"
            mtype = element
        else:
            mtype, q = element
            q = float(q)
            if q > 1 or q <= 0:
                raise ValueError('Invalid preference factor: %r' % q)

            qs = '%0.1f' % (q,)

        parts.append((qs, mtype))

    parts.sort()
    chunks = []
    for q, mtype in parts:
        if q == '1.0':
            chunks.append(mtype)
        else:
            chunks.append('%s; q=%s' % (mtype, q))

    return ', '.join(chunks)

def parseAcceptHeader(value):
    """Parse an accept header, ignoring any accept-extensions

    returns a list of tuples containing main MIME type, MIME subtype,
    and quality markdown.

    str -> [(str, str, float)]
    """
    chunks = [chunk.strip() for chunk in value.split(',')]
    accept = []
    for chunk in chunks:
        parts = [s.strip() for s in chunk.split(';')]

        mtype = parts.pop(0)
        if '/' not in mtype:
            # This is not a MIME type, so ignore the bad data
            continue

        main, sub = mtype.split('/', 1)

        for ext in parts:
            if '=' in ext:
                k, v = ext.split('=', 1)
                if k == 'q':
                    try:
                        q = float(v)
                        break
                    except ValueError:
                        # Ignore poorly formed q-values
                        pass
        else:
            q = 1.0

        accept.append((q, main, sub))

    accept.sort()
    accept.reverse()
    return [(main, sub, q) for (q, main, sub) in accept]

def matchTypes(accept_types, have_types):
    """Given the result of parsing an Accept: header, and the
    available MIME types, return the acceptable types with their
    quality markdowns.

    For example:

    >>> acceptable = parseAcceptHeader('text/html, text/plain; q=0.5')
    >>> matchTypes(acceptable, ['text/plain', 'text/html', 'image/jpeg'])
    [('text/html', 1.0), ('text/plain', 0.5)]


    Type signature: ([(str, str, float)], [str]) -> [(str, float)]
    """
    if not accept_types:
        # Accept all of them
        default = 1
    else:
        default = 0

    match_main = {}
    match_sub = {}
    for (main, sub, q) in accept_types:
        if main == '*':
            default = max(default, q)
            continue
        elif sub == '*':
            match_main[main] = max(match_main.get(main, 0), q)
        else:
            match_sub[(main, sub)] = max(match_sub.get((main, sub), 0), q)

    accepted_list = []
    order_maintainer = 0
    for mtype in have_types:
        main, sub = mtype.split('/')
        if (main, sub) in match_sub:
            q = match_sub[(main, sub)]
        else:
            q = match_main.get(main, default)

        if q:
            accepted_list.append((1 - q, order_maintainer, q, mtype))
            order_maintainer += 1

    accepted_list.sort()
    return [(mtype, q) for (_, _, q, mtype) in accepted_list]

def getAcceptable(accept_header, have_types):
    """Parse the accept header and return a list of available types in
    preferred order. If a type is unacceptable, it will not be in the
    resulting list.

    This is a convenience wrapper around matchTypes and
    parseAcceptHeader.

    (str, [str]) -> [str]
    """
    accepted = parseAcceptHeader(accept_header)
    preferred = matchTypes(accepted, have_types)
    return [mtype for (mtype, _) in preferred]

########NEW FILE########
__FILENAME__ = constants
__all__ = ['YADIS_HEADER_NAME', 'YADIS_CONTENT_TYPE', 'YADIS_ACCEPT_HEADER']
from openid.yadis.accept import generateAcceptHeader

YADIS_HEADER_NAME = 'X-XRDS-Location'
YADIS_CONTENT_TYPE = 'application/xrds+xml'

# A value suitable for using as an accept header when performing YADIS
# discovery, unless the application has special requirements
YADIS_ACCEPT_HEADER = generateAcceptHeader(
    ('text/html', 0.3),
    ('application/xhtml+xml', 0.5),
    (YADIS_CONTENT_TYPE, 1.0),
    )

########NEW FILE########
__FILENAME__ = discover
# -*- test-case-name: openid.test.test_yadis_discover -*-
__all__ = ['discover', 'DiscoveryResult', 'DiscoveryFailure']

from cStringIO import StringIO

from openid import fetchers

from openid.yadis.constants import \
     YADIS_HEADER_NAME, YADIS_CONTENT_TYPE, YADIS_ACCEPT_HEADER
from openid.yadis.parsehtml import MetaNotFound, findHTMLMeta

class DiscoveryFailure(Exception):
    """Raised when a YADIS protocol error occurs in the discovery process"""
    identity_url = None

    def __init__(self, message, http_response):
        Exception.__init__(self, message)
        self.http_response = http_response

class DiscoveryResult(object):
    """Contains the result of performing Yadis discovery on a URI"""

    # The URI that was passed to the fetcher
    request_uri = None

    # The result of following redirects from the request_uri
    normalized_uri = None

    # The URI from which the response text was returned (set to
    # None if there was no XRDS document found)
    xrds_uri = None

    # The content-type returned with the response_text
    content_type = None

    # The document returned from the xrds_uri
    response_text = None

    def __init__(self, request_uri):
        """Initialize the state of the object

        sets all attributes to None except the request_uri
        """
        self.request_uri = request_uri

    def usedYadisLocation(self):
        """Was the Yadis protocol's indirection used?"""
        return self.normalized_uri != self.xrds_uri

    def isXRDS(self):
        """Is the response text supposed to be an XRDS document?"""
        return (self.usedYadisLocation() or
                self.content_type == YADIS_CONTENT_TYPE)

def discover(uri):
    """Discover services for a given URI.

    @param uri: The identity URI as a well-formed http or https
        URI. The well-formedness and the protocol are not checked, but
        the results of this function are undefined if those properties
        do not hold.

    @return: DiscoveryResult object

    @raises Exception: Any exception that can be raised by fetching a URL with
        the given fetcher.
    @raises DiscoveryFailure: When the HTTP response does not have a 200 code.
    """
    result = DiscoveryResult(uri)
    resp = fetchers.fetch(uri, headers={'Accept': YADIS_ACCEPT_HEADER})
    if resp.status not in (200, 206):
        raise DiscoveryFailure(
            'HTTP Response status from identity URL host is not 200. '
            'Got status %r' % (resp.status,), resp)

    # Note the URL after following redirects
    result.normalized_uri = resp.final_url

    # Attempt to find out where to go to discover the document
    # or if we already have it
    result.content_type = resp.headers.get('content-type')

    result.xrds_uri = whereIsYadis(resp)

    if result.xrds_uri and result.usedYadisLocation():
        resp = fetchers.fetch(result.xrds_uri)
        if resp.status not in (200, 206):
            exc = DiscoveryFailure(
                'HTTP Response status from Yadis host is not 200. '
                'Got status %r' % (resp.status,), resp)
            exc.identity_url = result.normalized_uri
            raise exc
        result.content_type = resp.headers.get('content-type')

    result.response_text = resp.body
    return result



def whereIsYadis(resp):
    """Given a HTTPResponse, return the location of the Yadis document.

    May be the URL just retrieved, another URL, or None, if I can't
    find any.

    [non-blocking]

    @returns: str or None
    """
    # Attempt to find out where to go to discover the document
    # or if we already have it
    content_type = resp.headers.get('content-type')

    # According to the spec, the content-type header must be an exact
    # match, or else we have to look for an indirection.
    if (content_type and
        content_type.split(';', 1)[0].lower() == YADIS_CONTENT_TYPE):
        return resp.final_url
    else:
        # Try the header
        yadis_loc = resp.headers.get(YADIS_HEADER_NAME.lower())

        if not yadis_loc:
            # Parse as HTML if the header is missing.
            #
            # XXX: do we want to do something with content-type, like
            # have a whitelist or a blacklist (for detecting that it's
            # HTML)?
            try:
                yadis_loc = findHTMLMeta(StringIO(resp.body))
            except MetaNotFound:
                pass

        return yadis_loc


########NEW FILE########
__FILENAME__ = etxrd
# -*- test-case-name: yadis.test.test_etxrd -*-
"""
ElementTree interface to an XRD document.
"""

__all__ = [
    'nsTag',
    'mkXRDTag',
    'isXRDS',
    'parseXRDS',
    'getCanonicalID',
    'getYadisXRD',
    'getPriorityStrict',
    'getPriority',
    'prioSort',
    'iterServices',
    'expandService',
    'expandServices',
    ]

import sys
import random

from datetime import datetime
from time import strptime

from openid.oidutil import importElementTree
ElementTree = importElementTree()

# the different elementtree modules don't have a common exception
# model. We just want to be able to catch the exceptions that signify
# malformed XML data and wrap them, so that the other library code
# doesn't have to know which XML library we're using.
try:
    # Make the parser raise an exception so we can sniff out the type
    # of exceptions
    ElementTree.XML('> purposely malformed XML <')
except (SystemExit, MemoryError, AssertionError, ImportError):
    raise
except:
    XMLError = sys.exc_info()[0]

from openid.yadis import xri

class XRDSError(Exception):
    """An error with the XRDS document."""

    # The exception that triggered this exception
    reason = None



class XRDSFraud(XRDSError):
    """Raised when there's an assertion in the XRDS that it does not have
    the authority to make.
    """



def parseXRDS(text):
    """Parse the given text as an XRDS document.

    @return: ElementTree containing an XRDS document

    @raises XRDSError: When there is a parse error or the document does
        not contain an XRDS.
    """
    try:
        element = ElementTree.XML(text)
    except XMLError, why:
        exc = XRDSError('Error parsing document as XML')
        exc.reason = why
        raise exc
    else:
        tree = ElementTree.ElementTree(element)
        if not isXRDS(tree):
            raise XRDSError('Not an XRDS document')

        return tree

XRD_NS_2_0 = 'xri://$xrd*($v*2.0)'
XRDS_NS = 'xri://$xrds'

def nsTag(ns, t):
    return '{%s}%s' % (ns, t)

def mkXRDTag(t):
    """basestring -> basestring

    Create a tag name in the XRD 2.0 XML namespace suitable for using
    with ElementTree
    """
    return nsTag(XRD_NS_2_0, t)

def mkXRDSTag(t):
    """basestring -> basestring

    Create a tag name in the XRDS XML namespace suitable for using
    with ElementTree
    """
    return nsTag(XRDS_NS, t)

# Tags that are used in Yadis documents
root_tag = mkXRDSTag('XRDS')
service_tag = mkXRDTag('Service')
xrd_tag = mkXRDTag('XRD')
type_tag = mkXRDTag('Type')
uri_tag = mkXRDTag('URI')
expires_tag = mkXRDTag('Expires')

# Other XRD tags
canonicalID_tag = mkXRDTag('CanonicalID')

def isXRDS(xrd_tree):
    """Is this document an XRDS document?"""
    root = xrd_tree.getroot()
    return root.tag == root_tag

def getYadisXRD(xrd_tree):
    """Return the XRD element that should contain the Yadis services"""
    xrd = None

    # for the side-effect of assigning the last one in the list to the
    # xrd variable
    for xrd in xrd_tree.findall(xrd_tag):
        pass

    # There were no elements found, or else xrd would be set to the
    # last one
    if xrd is None:
        raise XRDSError('No XRD present in tree')

    return xrd

def getXRDExpiration(xrd_element, default=None):
    """Return the expiration date of this XRD element, or None if no
    expiration was specified.

    @type xrd_element: ElementTree node

    @param default: The value to use as the expiration if no
        expiration was specified in the XRD.

    @rtype: datetime.datetime

    @raises ValueError: If the xrd:Expires element is present, but its
        contents are not formatted according to the specification.
    """
    expires_element = xrd_element.find(expires_tag)
    if expires_element is None:
        return default
    else:
        expires_string = expires_element.text

        # Will raise ValueError if the string is not the expected format
        expires_time = strptime(expires_string, "%Y-%m-%dT%H:%M:%SZ")
        return datetime(*expires_time[0:6])

def getCanonicalID(iname, xrd_tree):
    """Return the CanonicalID from this XRDS document.

    @param iname: the XRI being resolved.
    @type iname: unicode

    @param xrd_tree: The XRDS output from the resolver.
    @type xrd_tree: ElementTree

    @returns: The XRI CanonicalID or None.
    @returntype: unicode or None
    """
    xrd_list = xrd_tree.findall(xrd_tag)
    xrd_list.reverse()

    try:
        canonicalID = xri.XRI(xrd_list[0].findall(canonicalID_tag)[0].text)
    except IndexError:
        return None

    childID = canonicalID.lower()

    for xrd in xrd_list[1:]:
        # XXX: can't use rsplit until we require python >= 2.4.
        parent_sought = childID[:childID.rindex('!')]
        parent = xri.XRI(xrd.findtext(canonicalID_tag))
        if parent_sought != parent.lower():
            raise XRDSFraud("%r can not come from %s" % (childID, parent))

        childID = parent_sought

    root = xri.rootAuthority(iname)
    if not xri.providerIsAuthoritative(root, childID):
        raise XRDSFraud("%r can not come from root %r" % (childID, root))

    return canonicalID



class _Max(object):
    """Value that compares greater than any other value.

    Should only be used as a singleton. Implemented for use as a
    priority value for when a priority is not specified."""
    def __cmp__(self, other):
        if other is self:
            return 0

        return 1

Max = _Max()

def getPriorityStrict(element):
    """Get the priority of this element.

    Raises ValueError if the value of the priority is invalid. If no
    priority is specified, it returns a value that compares greater
    than any other value.
    """
    prio_str = element.get('priority')
    if prio_str is not None:
        prio_val = int(prio_str)
        if prio_val >= 0:
            return prio_val
        else:
            raise ValueError('Priority values must be non-negative integers')

    # Any errors in parsing the priority fall through to here
    return Max

def getPriority(element):
    """Get the priority of this element

    Returns Max if no priority is specified or the priority value is invalid.
    """
    try:
        return getPriorityStrict(element)
    except ValueError:
        return Max

def prioSort(elements):
    """Sort a list of elements that have priority attributes"""
    # Randomize the services before sorting so that equal priority
    # elements are load-balanced.
    random.shuffle(elements)

    prio_elems = [(getPriority(e), e) for e in elements]
    prio_elems.sort()
    sorted_elems = [s for (_, s) in prio_elems]
    return sorted_elems

def iterServices(xrd_tree):
    """Return an iterable over the Service elements in the Yadis XRD

    sorted by priority"""
    xrd = getYadisXRD(xrd_tree)
    return prioSort(xrd.findall(service_tag))

def sortedURIs(service_element):
    """Given a Service element, return a list of the contents of all
    URI tags in priority order."""
    return [uri_element.text for uri_element
            in prioSort(service_element.findall(uri_tag))]

def getTypeURIs(service_element):
    """Given a Service element, return a list of the contents of all
    Type tags"""
    return [type_element.text for type_element
            in service_element.findall(type_tag)]

def expandService(service_element):
    """Take a service element and expand it into an iterator of:
    ([type_uri], uri, service_element)
    """
    uris = sortedURIs(service_element)
    if not uris:
        uris = [None]

    expanded = []
    for uri in uris:
        type_uris = getTypeURIs(service_element)
        expanded.append((type_uris, uri, service_element))

    return expanded

def expandServices(service_elements):
    """Take a sorted iterator of service elements and expand it into a
    sorted iterator of:
    ([type_uri], uri, service_element)

    There may be more than one item in the resulting list for each
    service element if there is more than one URI or type for a
    service, but each triple will be unique.

    If there is no URI or Type for a Service element, it will not
    appear in the result.
    """
    expanded = []
    for service_element in service_elements:
        expanded.extend(expandService(service_element))

    return expanded

########NEW FILE########
__FILENAME__ = filters
"""This module contains functions and classes used for extracting
endpoint information out of a Yadis XRD file using the ElementTree XML
parser.
"""

__all__ = [
    'BasicServiceEndpoint',
    'mkFilter',
    'IFilter',
    'TransformFilterMaker',
    'CompoundFilter',
    ]

from openid.yadis.etxrd import expandService

class BasicServiceEndpoint(object):
    """Generic endpoint object that contains parsed service
    information, as well as a reference to the service element from
    which it was generated. If there is more than one xrd:Type or
    xrd:URI in the xrd:Service, this object represents just one of
    those pairs.

    This object can be used as a filter, because it implements
    fromBasicServiceEndpoint.

    The simplest kind of filter you can write implements
    fromBasicServiceEndpoint, which takes one of these objects.
    """
    def __init__(self, yadis_url, type_uris, uri, service_element):
        self.type_uris = type_uris
        self.yadis_url = yadis_url
        self.uri = uri
        self.service_element = service_element

    def matchTypes(self, type_uris):
        """Query this endpoint to see if it has any of the given type
        URIs. This is useful for implementing other endpoint classes
        that e.g. need to check for the presence of multiple versions
        of a single protocol.

        @param type_uris: The URIs that you wish to check
        @type type_uris: iterable of str

        @return: all types that are in both in type_uris and
            self.type_uris
        """
        return [uri for uri in type_uris if uri in self.type_uris]

    def fromBasicServiceEndpoint(endpoint):
        """Trivial transform from a basic endpoint to itself. This
        method exists to allow BasicServiceEndpoint to be used as a
        filter.

        If you are subclassing this object, re-implement this function.

        @param endpoint: An instance of BasicServiceEndpoint
        @return: The object that was passed in, with no processing.
        """
        return endpoint

    fromBasicServiceEndpoint = staticmethod(fromBasicServiceEndpoint)

class IFilter(object):
    """Interface for Yadis filter objects. Other filter-like things
    are convertable to this class."""

    def getServiceEndpoints(self, yadis_url, service_element):
        """Returns an iterator of endpoint objects"""
        raise NotImplementedError

class TransformFilterMaker(object):
    """Take a list of basic filters and makes a filter that transforms
    the basic filter into a top-level filter. This is mostly useful
    for the implementation of mkFilter, which should only be needed
    for special cases or internal use by this library.

    This object is useful for creating simple filters for services
    that use one URI and are specified by one Type (we expect most
    Types will fit this paradigm).

    Creates a BasicServiceEndpoint object and apply the filter
    functions to it until one of them returns a value.
    """

    def __init__(self, filter_functions):
        """Initialize the filter maker's state

        @param filter_functions: The endpoint transformer functions to
            apply to the basic endpoint. These are called in turn
            until one of them does not return None, and the result of
            that transformer is returned.
        """
        self.filter_functions = filter_functions

    def getServiceEndpoints(self, yadis_url, service_element):
        """Returns an iterator of endpoint objects produced by the
        filter functions."""
        endpoints = []

        # Do an expansion of the service element by xrd:Type and xrd:URI
        for type_uris, uri, _ in expandService(service_element):

            # Create a basic endpoint object to represent this
            # yadis_url, Service, Type, URI combination
            endpoint = BasicServiceEndpoint(
                yadis_url, type_uris, uri, service_element)

            e = self.applyFilters(endpoint)
            if e is not None:
                endpoints.append(e)

        return endpoints

    def applyFilters(self, endpoint):
        """Apply filter functions to an endpoint until one of them
        returns non-None."""
        for filter_function in self.filter_functions:
            e = filter_function(endpoint)
            if e is not None:
                # Once one of the filters has returned an
                # endpoint, do not apply any more.
                return e

        return None

class CompoundFilter(object):
    """Create a new filter that applies a set of filters to an endpoint
    and collects their results.
    """
    def __init__(self, subfilters):
        self.subfilters = subfilters

    def getServiceEndpoints(self, yadis_url, service_element):
        """Generate all endpoint objects for all of the subfilters of
        this filter and return their concatenation."""
        endpoints = []
        for subfilter in self.subfilters:
            endpoints.extend(
                subfilter.getServiceEndpoints(yadis_url, service_element))
        return endpoints

# Exception raised when something is not able to be turned into a filter
filter_type_error = TypeError(
    'Expected a filter, an endpoint, a callable or a list of any of these.')

def mkFilter(parts):
    """Convert a filter-convertable thing into a filter

    @param parts: a filter, an endpoint, a callable, or a list of any of these.
    """
    # Convert the parts into a list, and pass to mkCompoundFilter
    if parts is None:
        parts = [BasicServiceEndpoint]

    try:
        parts = list(parts)
    except TypeError:
        return mkCompoundFilter([parts])
    else:
        return mkCompoundFilter(parts)

def mkCompoundFilter(parts):
    """Create a filter out of a list of filter-like things

    Used by mkFilter

    @param parts: list of filter, endpoint, callable or list of any of these
    """
    # Separate into a list of callables and a list of filter objects
    transformers = []
    filters = []
    for subfilter in parts:
        try:
            subfilter = list(subfilter)
        except TypeError:
            # If it's not an iterable
            if hasattr(subfilter, 'getServiceEndpoints'):
                # It's a full filter
                filters.append(subfilter)
            elif hasattr(subfilter, 'fromBasicServiceEndpoint'):
                # It's an endpoint object, so put its endpoint
                # conversion attribute into the list of endpoint
                # transformers
                transformers.append(subfilter.fromBasicServiceEndpoint)
            elif callable(subfilter):
                # It's a simple callable, so add it to the list of
                # endpoint transformers
                transformers.append(subfilter)
            else:
                raise filter_type_error
        else:
            filters.append(mkCompoundFilter(subfilter))

    if transformers:
        filters.append(TransformFilterMaker(transformers))

    if len(filters) == 1:
        return filters[0]
    else:
        return CompoundFilter(filters)

########NEW FILE########
__FILENAME__ = manager
class YadisServiceManager(object):
    """Holds the state of a list of selected Yadis services, managing
    storing it in a session and iterating over the services in order."""

    def __init__(self, starting_url, yadis_url, services, session_key):
        # The URL that was used to initiate the Yadis protocol
        self.starting_url = starting_url

        # The URL after following redirects (the identifier)
        self.yadis_url = yadis_url

        # List of service elements
        self.services = list(services)

        self.session_key = session_key

        # Reference to the current service object
        self._current = None

    def __len__(self):
        """How many untried services remain?"""
        return len(self.services)

    def __iter__(self):
        return self

    def next(self):
        """Return the next service

        self.current() will continue to return that service until the
        next call to this method."""
        try:
            self._current = self.services.pop(0)
        except IndexError:
            raise StopIteration
        else:
            return self._current

    def current(self):
        """Return the current service.

        Returns None if there are no services left.
        """
        return self._current

    def forURL(self, url):
        return url in [self.starting_url, self.yadis_url]

    def started(self):
        """Has the first service been returned?"""
        return self._current is not None

    def store(self, session):
        """Store this object in the session, by its session key."""
        session[self.session_key] = self

class Discovery(object):
    """State management for discovery.

    High-level usage pattern is to call .getNextService(discover) in
    order to find the next available service for this user for this
    session. Once a request completes, call .finish() to clean up the
    session state.

    @ivar session: a dict-like object that stores state unique to the
        requesting user-agent. This object must be able to store
        serializable objects.

    @ivar url: the URL that is used to make the discovery request

    @ivar session_key_suffix: The suffix that will be used to identify
        this object in the session object.
    """

    DEFAULT_SUFFIX = 'auth'
    PREFIX = '_yadis_services_'

    def __init__(self, session, url, session_key_suffix=None):
        """Initialize a discovery object"""
        self.session = session
        self.url = url
        if session_key_suffix is None:
            session_key_suffix = self.DEFAULT_SUFFIX

        self.session_key_suffix = session_key_suffix

    def getNextService(self, discover):
        """Return the next authentication service for the pair of
        user_input and session.  This function handles fallback.


        @param discover: a callable that takes a URL and returns a
            list of services

        @type discover: str -> [service]


        @return: the next available service
        """
        manager = self.getManager()
        if manager is not None and not manager:
            self.destroyManager()

        if not manager:
            yadis_url, services = discover(self.url)
            manager = self.createManager(services, yadis_url)

        if manager:
            service = manager.next()
            manager.store(self.session)
        else:
            service = None

        return service

    def cleanup(self, force=False):
        """Clean up Yadis-related services in the session and return
        the most-recently-attempted service from the manager, if one
        exists.

        @param force: True if the manager should be deleted regardless
        of whether it's a manager for self.url.

        @return: current service endpoint object or None if there is
            no current service
        """
        manager = self.getManager(force=force)
        if manager is not None:
            service = manager.current()
            self.destroyManager(force=force)
        else:
            service = None

        return service

    ### Lower-level methods

    def getSessionKey(self):
        """Get the session key for this starting URL and suffix

        @return: The session key
        @rtype: str
        """
        return self.PREFIX + self.session_key_suffix

    def getManager(self, force=False):
        """Extract the YadisServiceManager for this object's URL and
        suffix from the session.

        @param force: True if the manager should be returned
        regardless of whether it's a manager for self.url.

        @return: The current YadisServiceManager, if it's for this
            URL, or else None
        """
        manager = self.session.get(self.getSessionKey())
        if (manager is not None and (manager.forURL(self.url) or force)):
            return manager
        else:
            return None

    def createManager(self, services, yadis_url=None):
        """Create a new YadisService Manager for this starting URL and
        suffix, and store it in the session.

        @raises KeyError: When I already have a manager.

        @return: A new YadisServiceManager or None
        """
        key = self.getSessionKey()
        if self.getManager():
            raise KeyError('There is already a %r manager for %r' %
                           (key, self.url))

        if not services:
            return None

        manager = YadisServiceManager(self.url, yadis_url, services, key)
        manager.store(self.session)
        return manager

    def destroyManager(self, force=False):
        """Delete any YadisServiceManager with this starting URL and
        suffix from the session.

        If there is no service manager or the service manager is for a
        different URL, it silently does nothing.

        @param force: True if the manager should be deleted regardless
        of whether it's a manager for self.url.
        """
        if self.getManager(force=force) is not None:
            key = self.getSessionKey()
            del self.session[key]

########NEW FILE########
__FILENAME__ = parsehtml
__all__ = ['findHTMLMeta', 'MetaNotFound']

from HTMLParser import HTMLParser, HTMLParseError
import htmlentitydefs
import re

from openid.yadis.constants import YADIS_HEADER_NAME

# Size of the chunks to search at a time (also the amount that gets
# read at a time)
CHUNK_SIZE = 1024 * 16 # 16 KB

class ParseDone(Exception):
    """Exception to hold the URI that was located when the parse is
    finished. If the parse finishes without finding the URI, set it to
    None."""

class MetaNotFound(Exception):
    """Exception to hold the content of the page if we did not find
    the appropriate <meta> tag"""

re_flags = re.IGNORECASE | re.UNICODE | re.VERBOSE
ent_pat = r'''
&

(?: \#x (?P<hex> [a-f0-9]+ )
|   \# (?P<dec> \d+ )
|   (?P<word> \w+ )
)

;'''

ent_re = re.compile(ent_pat, re_flags)

def substituteMO(mo):
    if mo.lastgroup == 'hex':
        codepoint = int(mo.group('hex'), 16)
    elif mo.lastgroup == 'dec':
        codepoint = int(mo.group('dec'))
    else:
        assert mo.lastgroup == 'word'
        codepoint = htmlentitydefs.name2codepoint.get(mo.group('word'))

    if codepoint is None:
        return mo.group()
    else:
        return unichr(codepoint)

def substituteEntities(s):
    return ent_re.sub(substituteMO, s)

class YadisHTMLParser(HTMLParser):
    """Parser that finds a meta http-equiv tag in the head of a html
    document.

    When feeding in data, if the tag is matched or it will never be
    found, the parser will raise ParseDone with the uri as the first
    attribute.

    Parsing state diagram
    =====================

    Any unlisted input does not affect the state::

                1, 2, 5                       8
               +--------------------------+  +-+
               |                          |  | |
            4  |    3       1, 2, 5, 7    v  | v
        TOP -> HTML -> HEAD ----------> TERMINATED
        | |            ^  |               ^  ^
        | | 3          |  |               |  |
        | +------------+  +-> FOUND ------+  |
        |                  6         8       |
        | 1, 2                               |
        +------------------------------------+

      1. any of </body>, </html>, </head> -> TERMINATE
      2. <body> -> TERMINATE
      3. <head> -> HEAD
      4. <html> -> HTML
      5. <html> -> TERMINATE
      6. <meta http-equiv='X-XRDS-Location'> -> FOUND
      7. <head> -> TERMINATE
      8. Any input -> TERMINATE
    """
    TOP = 0
    HTML = 1
    HEAD = 2
    FOUND = 3
    TERMINATED = 4

    def __init__(self):
        HTMLParser.__init__(self)
        self.phase = self.TOP

    def _terminate(self):
        self.phase = self.TERMINATED
        raise ParseDone(None)

    def handle_endtag(self, tag):
        # If we ever see an end of head, body, or html, bail out right away.
        # [1]
        if tag in ['head', 'body', 'html']:
            self._terminate()

    def handle_starttag(self, tag, attrs):
        # if we ever see a start body tag, bail out right away, since
        # we want to prevent the meta tag from appearing in the body
        # [2]
        if tag=='body':
            self._terminate()

        if self.phase == self.TOP:
            # At the top level, allow a html tag or a head tag to move
            # to the head or html phase
            if tag == 'head':
                # [3]
                self.phase = self.HEAD
            elif tag == 'html':
                # [4]
                self.phase = self.HTML

        elif self.phase == self.HTML:
            # if we are in the html tag, allow a head tag to move to
            # the HEAD phase. If we get another html tag, then bail
            # out
            if tag == 'head':
                # [3]
                self.phase = self.HEAD
            elif tag == 'html':
                # [5]
                self._terminate()

        elif self.phase == self.HEAD:
            # If we are in the head phase, look for the appropriate
            # meta tag. If we get a head or body tag, bail out.
            if tag == 'meta':
                attrs_d = dict(attrs)
                http_equiv = attrs_d.get('http-equiv', '').lower()
                if http_equiv == YADIS_HEADER_NAME.lower():
                    raw_attr = attrs_d.get('content')
                    yadis_loc = substituteEntities(raw_attr)
                    # [6]
                    self.phase = self.FOUND
                    raise ParseDone(yadis_loc)

            elif tag in ['head', 'html']:
                # [5], [7]
                self._terminate()

    def feed(self, chars):
        # [8]
        if self.phase in [self.TERMINATED, self.FOUND]:
            self._terminate()

        return HTMLParser.feed(self, chars)

def findHTMLMeta(stream):
    """Look for a meta http-equiv tag with the YADIS header name.

    @param stream: Source of the html text
    @type stream: Object that implements a read() method that works
        like file.read

    @return: The URI from which to fetch the XRDS document
    @rtype: str

    @raises MetaNotFound: raised with the content that was
        searched as the first parameter.
    """
    parser = YadisHTMLParser()
    chunks = []

    while 1:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            # End of file
            break

        chunks.append(chunk)
        try:
            parser.feed(chunk)
        except HTMLParseError, why:
            # HTML parse error, so bail
            chunks.append(stream.read())
            break
        except ParseDone, why:
            uri = why[0]
            if uri is None:
                # Parse finished, but we may need the rest of the file
                chunks.append(stream.read())
                break
            else:
                return uri

    content = ''.join(chunks)
    raise MetaNotFound(content)

########NEW FILE########
__FILENAME__ = services
# -*- test-case-name: openid.test.test_services -*-

from openid.yadis.filters import mkFilter
from openid.yadis.discover import discover, DiscoveryFailure
from openid.yadis.etxrd import parseXRDS, iterServices, XRDSError

def getServiceEndpoints(input_url, flt=None):
    """Perform the Yadis protocol on the input URL and return an
    iterable of resulting endpoint objects.

    @param flt: A filter object or something that is convertable to
        a filter object (using mkFilter) that will be used to generate
        endpoint objects. This defaults to generating BasicEndpoint
        objects.

    @param input_url: The URL on which to perform the Yadis protocol

    @return: The normalized identity URL and an iterable of endpoint
        objects generated by the filter function.

    @rtype: (str, [endpoint])

    @raises DiscoveryFailure: when Yadis fails to obtain an XRDS document.
    """
    result = discover(input_url)
    try:
        endpoints = applyFilter(result.normalized_uri,
                                result.response_text, flt)
    except XRDSError, err:
        raise DiscoveryFailure(str(err), None)
    return (result.normalized_uri, endpoints)

def applyFilter(normalized_uri, xrd_data, flt=None):
    """Generate an iterable of endpoint objects given this input data,
    presumably from the result of performing the Yadis protocol.

    @param normalized_uri: The input URL, after following redirects,
        as in the Yadis protocol.


    @param xrd_data: The XML text the XRDS file fetched from the
        normalized URI.
    @type xrd_data: str

    """
    flt = mkFilter(flt)
    et = parseXRDS(xrd_data)

    endpoints = []
    for service_element in iterServices(et):
        endpoints.extend(
            flt.getServiceEndpoints(normalized_uri, service_element))

    return endpoints

########NEW FILE########
__FILENAME__ = xri
# -*- test-case-name: openid.test.test_xri -*-
"""Utility functions for handling XRIs.

@see: XRI Syntax v2.0 at the U{OASIS XRI Technical Committee<http://www.oasis-open.org/committees/tc_home.php?wg_abbrev=xri>}
"""

import re

XRI_AUTHORITIES = ['!', '=', '@', '+', '$', '(']

try:
    unichr(0x10000)
except ValueError:
    # narrow python build
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        ]
else:
    UCSCHAR = [
        (0xA0, 0xD7FF),
        (0xF900, 0xFDCF),
        (0xFDF0, 0xFFEF),
        (0x10000, 0x1FFFD),
        (0x20000, 0x2FFFD),
        (0x30000, 0x3FFFD),
        (0x40000, 0x4FFFD),
        (0x50000, 0x5FFFD),
        (0x60000, 0x6FFFD),
        (0x70000, 0x7FFFD),
        (0x80000, 0x8FFFD),
        (0x90000, 0x9FFFD),
        (0xA0000, 0xAFFFD),
        (0xB0000, 0xBFFFD),
        (0xC0000, 0xCFFFD),
        (0xD0000, 0xDFFFD),
        (0xE1000, 0xEFFFD),
        ]

    IPRIVATE = [
        (0xE000, 0xF8FF),
        (0xF0000, 0xFFFFD),
        (0x100000, 0x10FFFD),
        ]


_escapeme_re = re.compile('[%s]' % (''.join(
    map(lambda (m, n): u'%s-%s' % (unichr(m), unichr(n)),
        UCSCHAR + IPRIVATE)),))


def identifierScheme(identifier):
    """Determine if this identifier is an XRI or URI.

    @returns: C{"XRI"} or C{"URI"}
    """
    if identifier.startswith('xri://') or (
        identifier and identifier[0] in XRI_AUTHORITIES):
        return "XRI"
    else:
        return "URI"


def toIRINormal(xri):
    """Transform an XRI to IRI-normal form."""
    if not xri.startswith('xri://'):
        xri = 'xri://' + xri
    return escapeForIRI(xri)


_xref_re = re.compile('\((.*?)\)')


def _escape_xref(xref_match):
    """Escape things that need to be escaped if they're in a cross-reference.
    """
    xref = xref_match.group()
    xref = xref.replace('/', '%2F')
    xref = xref.replace('?', '%3F')
    xref = xref.replace('#', '%23')
    return xref


def escapeForIRI(xri):
    """Escape things that need to be escaped when transforming to an IRI."""
    xri = xri.replace('%', '%25')
    xri = _xref_re.sub(_escape_xref, xri)
    return xri


def toURINormal(xri):
    """Transform an XRI to URI normal form."""
    return iriToURI(toIRINormal(xri))


def _percentEscapeUnicode(char_match):
    c = char_match.group()
    return ''.join(['%%%X' % (ord(octet),) for octet in c.encode('utf-8')])


def iriToURI(iri):
    """Transform an IRI to a URI by escaping unicode."""
    # According to RFC 3987, section 3.1, "Mapping of IRIs to URIs"
    return _escapeme_re.sub(_percentEscapeUnicode, iri)


def providerIsAuthoritative(providerID, canonicalID):
    """Is this provider ID authoritative for this XRI?

    @returntype: bool
    """
    # XXX: can't use rsplit until we require python >= 2.4.
    lastbang = canonicalID.rindex('!')
    parent = canonicalID[:lastbang]
    return parent == providerID


def rootAuthority(xri):
    """Return the root authority for an XRI.

    Example::

        rootAuthority("xri://@example") == "xri://@"

    @type xri: unicode
    @returntype: unicode
    """
    if xri.startswith('xri://'):
        xri = xri[6:]
    authority = xri.split('/', 1)[0]
    if authority[0] == '(':
        # Cross-reference.
        # XXX: This is incorrect if someone nests cross-references so there
        #   is another close-paren in there.  Hopefully nobody does that
        #   before we have a real xriparse function.  Hopefully nobody does
        #   that *ever*.
        root = authority[:authority.index(')') + 1]
    elif authority[0] in XRI_AUTHORITIES:
        # Other XRI reference.
        root = authority[0]
    else:
        # IRI reference.  XXX: Can IRI authorities have segments?
        segments = authority.split('!')
        segments = reduce(list.__add__,
            map(lambda s: s.split('*'), segments))
        root = segments[0]

    return XRI(root)


def XRI(xri):
    """An XRI object allowing comparison of XRI.

    Ideally, this would do full normalization and provide comparsion
    operators as per XRI Syntax.  Right now, it just does a bit of
    canonicalization by ensuring the xri scheme is present.

    @param xri: an xri string
    @type xri: unicode
    """
    if not xri.startswith('xri://'):
        xri = 'xri://' + xri
    return xri

########NEW FILE########
__FILENAME__ = xrires
# -*- test-case-name: openid.test.test_xrires -*-
"""XRI resolution.
"""

from urllib import urlencode
from openid import fetchers
from openid.yadis import etxrd
from openid.yadis.xri import toURINormal
from openid.yadis.services import iterServices

DEFAULT_PROXY = 'http://proxy.xri.net/'

class ProxyResolver(object):
    """Python interface to a remote XRI proxy resolver.
    """
    def __init__(self, proxy_url=DEFAULT_PROXY):
        self.proxy_url = proxy_url


    def queryURL(self, xri, service_type=None):
        """Build a URL to query the proxy resolver.

        @param xri: An XRI to resolve.
        @type xri: unicode

        @param service_type: The service type to resolve, if you desire
            service endpoint selection.  A service type is a URI.
        @type service_type: str

        @returns: a URL
        @returntype: str
        """
        # Trim off the xri:// prefix.  The proxy resolver didn't accept it
        # when this code was written, but that may (or may not) change for
        # XRI Resolution 2.0 Working Draft 11.
        qxri = toURINormal(xri)[6:]
        hxri = self.proxy_url + qxri
        args = {
            # XXX: If the proxy resolver will ensure that it doesn't return
            # bogus CanonicalIDs (as per Steve's message of 15 Aug 2006
            # 11:13:42), then we could ask for application/xrd+xml instead,
            # which would give us a bit less to process.
            '_xrd_r': 'application/xrds+xml',
            }
        if service_type:
            args['_xrd_t'] = service_type
        else:
            # Don't perform service endpoint selection.
            args['_xrd_r'] += ';sep=false'
        query = _appendArgs(hxri, args)
        return query


    def query(self, xri, service_types):
        """Resolve some services for an XRI.

        Note: I don't implement any service endpoint selection beyond what
        the resolver I'm querying does, so the Services I return may well
        include Services that were not of the types you asked for.

        May raise fetchers.HTTPFetchingError or L{etxrd.XRDSError} if
        the fetching or parsing don't go so well.

        @param xri: An XRI to resolve.
        @type xri: unicode

        @param service_types: A list of services types to query for.  Service
            types are URIs.
        @type service_types: list of str

        @returns: tuple of (CanonicalID, Service elements)
        @returntype: (unicode, list of C{ElementTree.Element}s)
        """
        # FIXME: No test coverage!
        services = []
        # Make a seperate request to the proxy resolver for each service
        # type, as, if it is following Refs, it could return a different
        # XRDS for each.

        canonicalID = None

        for service_type in service_types:
            url = self.queryURL(xri, service_type)
            response = fetchers.fetch(url)
            if response.status not in (200, 206):
                # XXX: sucks to fail silently.
                # print "response not OK:", response
                continue
            et = etxrd.parseXRDS(response.body)
            canonicalID = etxrd.getCanonicalID(xri, et)
            some_services = list(iterServices(et))
            services.extend(some_services)
        # TODO:
        #  * If we do get hits for multiple service_types, we're almost
        #    certainly going to have duplicated service entries and
        #    broken priority ordering.
        return canonicalID, services


def _appendArgs(url, args):
    """Append some arguments to an HTTP query.
    """
    # to be merged with oidutil.appendArgs when we combine the projects.
    if hasattr(args, 'items'):
        args = args.items()
        args.sort()

    if len(args) == 0:
        return url

    # According to XRI Resolution section "QXRI query parameters":
    #
    # """If the original QXRI had a null query component (only a leading
    #    question mark), or a query component consisting of only question
    #    marks, one additional leading question mark MUST be added when
    #    adding any XRI resolution parameters."""

    if '?' in url.rstrip('?'):
        sep = '&'
    else:
        sep = '?'

    return '%s%s%s' % (url, sep, urlencode(args))

########NEW FILE########
__FILENAME__ = store
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from google.appengine.api import memcache
from openid.association import Association as OpenIDAssociation
from openid.store import interface
from openid.store import nonce


MEMCACHE_NAMESPACE = "aeoid"


class AppEngineStore(interface.OpenIDStore):
  def getAssociationKeys(self, server_url, handle):
    return ("assoc:%s" % (server_url,),
            "assoc:%s:%s" % (server_url, handle))

  def storeAssociation(self, server_url, association):
    data = association.serialize()
    key1, key2 = self.getAssociationKeys(server_url, association.handle)
    memcache.set_multi({key1: data, key2: data},
                       namespace=MEMCACHE_NAMESPACE)

  def getAssociation(self, server_url, handle=None):
    key1, key2 = self.getAssociationKeys(server_url, handle)
    if handle:
      results = memcache.get_multi([key1, key2], namespace=MEMCACHE_NAMESPACE)
    else:
      results = {key1: memcache.get(key1, namespace=MEMCACHE_NAMESPACE)}
    data = results.get(key2) or results.get(key1)
    if data:
      return OpenIDAssociation.deserialize(data)
    else:
      return None

  def removeAssociation(self, server_url, handle):
    key1, key2 = self.getAssociationKeys(server_url, handle)
    return memcache.delete(key2) == 2

  def useNonce(self, server_url, timestamp, salt):
    nonce_key = "nonce:%s:%s" % (server_url, salt)
    expires_at = timestamp + nonce.SKEW
    return memcache.add(nonce_key, None, time=expires_at,
                        namespace=MEMCACHE_NAMESPACE)

########NEW FILE########
__FILENAME__ = users
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import urllib
import urlparse

from google.appengine.ext import db


OPENID_PATH_PREFIX = '/_openid/'
OPENID_LOGIN_PATH = OPENID_PATH_PREFIX + 'login'
OPENID_FINISH_PATH = OPENID_PATH_PREFIX + 'finish'
OPENID_LOGOUT_PATH = OPENID_PATH_PREFIX + 'logout'
OPENID_STATIC_PATH = OPENID_PATH_PREFIX + 'static/(.*)\.([^.]+)'


_current_user = None


class UserInfo(db.Expando):
  """Internal user information for an OpenID-authenticated user."""

  server_url = db.StringProperty()
  nickname = db.StringProperty(indexed=False)
  email = db.StringProperty()

  @property
  def identity_url(self):
    """Returns the user's OpenID identity URL."""
    return self.key().name()

  @classmethod
  def kind(cls):
    return "AeoidUser"

  @classmethod
  def get_by_identity_url(cls, identity_url):
    """Fetches a user by their OpenID URL."""
    return cls.get_by_key_name(identity_url)

  @classmethod
  def update_or_insert(cls, identity_url, **kwargs):
    """Creates an entity, or updates it if it already exists."""
    def _tx():
      user = cls.get_by_identity_url(identity_url)
      if user:
        for k, v in kwargs.iteritems():
          setattr(user, k, v)
      else:
        user = cls(key_name=identity_url, **kwargs)
      user.put()
      return user
    return db.run_in_transaction(_tx)


class User(object):
  """A user.
  
  We provide the email address, nickname, and id for a user.
  
  Note that unlike the native App Engine Users API, nicknames and email
  addresses are not guaranteed to be unique, and because they are entered by
  the user, the email is not guaranteed to be valid and owned by the user in
  question, either - so perform your own validation if you're unsure!
  """

  def __init__(self, identity_url, _from_model_key=None, _from_model=None,
               **kwargs):
    """Constructor.
    
    Args:
      identity_url: The OpenID URL of the user. Required to construct a User
        object.
      email: The user's email address.
      nickname: The user's nickname.
    """
    if _from_model_key:
      self._user_info = _from_model
      if isinstance(_from_model_key, basestring):
        self._user_info_key = db.Key(_from_model_key)
      else:
        self._user_info_key = _from_model_key
    else:
      self._user_info = UserInfo.update_or_insert(identity_url, **kwargs)
      self._user_info_key = self._user_info.key()

  def user_info(self):
    """Returns the internal user_info entity for this user."""
    if not self._user_info:
      self._user_info = db.get(self._user_info_key)
    return self._user_info

  def nickname(self):
    """Return this user's nickname.
    
    The nickname is a human readable identifier for this user, chosen by them
    when they first logged in. It may not be unique!
    """
    return self.user_info().nickname

  def email(self):
    """Return this user's email address.
    
    Unlike the native Users API, aeoid does NOT validate emails, so the address
    provided is not guaranteed to be unique, or even owned by the user in
    question. If in doubt, perform your own validation!
    """
    return self.user_info().email

  def user_id(self):
    """Return a permanent unique identifying string.
    
    In aeoid, the string returned is the user's OpenID URL.
    """
    return self._user_info_key.name()


def _get_current_url():
  if os.environ.get('HTTPS') == 'on':
    url = 'https://'
  else:
    url = 'http://'
  url += os.environ['HTTP_HOST']
  url += urllib.quote(os.environ['SCRIPT_NAME'])
  url += urllib.quote(os.environ['PATH_INFO'])
  if os.environ.get('QUERY_STRING'):
    url += '?' + os.environ['QUERY_STRING']


def _create_redirect_url(target, continue_url):
  current_url = _get_current_url()
  # Convert dest_url to an absolute URL
  continue_url = urlparse.urljoin(current_url, continue_url)
  redirect_url = '%s?continue=%s' % (target, urllib.quote(continue_url))
  # Convert the login URL to an absolute URL
  redirect_url = urlparse.urljoin(current_url, redirect_url)
  return redirect_url


def create_login_url(dest_url):
  """Returns a URL that, when visited, prompts the user to sign in using OpenID.
  
  Args:
    dest_url: str: A full URL or relative path to redirect to after logging in.
  Returns:
    str: A URL to redirect the user to for login.
  """
  return _create_redirect_url(OPENID_LOGIN_PATH, dest_url)


def create_logout_url(dest_url):
  """Returns a URL that, when visited, logs the user out.
  
  Args:
    dest_url: str: A full URL or relative path to redirect to after logging out.
  Returns:
    str: A URL to redirect the user to for logout.
  """
  return _create_redirect_url(OPENID_LOGOUT_PATH, dest_url)
  

def get_current_user():
  """Returns the currently logged in user, or None if no user is logged in."""
  global _current_user
  
  if not _current_user and 'aeoid.user' in os.environ:
    _current_user = User(None, _from_model_key=os.environ['aeoid.user'])
  return _current_user


def is_current_user_admin():
  """Returns True if the current user is signed in and is an administrator."""
  # TODO: Implement
  return False


class UserProperty(db.Property):
  """A user with an OpenID account."""

  def __init__(self,
               verbose_name=None,
               name=None,
               required=False,
               validator=None,
               choices=None,
               auto_current_user=False,
               auto_current_user_add=False,
               indexed=True):
    """Initializes this Property with the given options.
    
    If auto_current_user is True, the property value is set to the currently
    signed-in user whenever the model instance is stored in the datastore,
    overwriting the property's previous value. This is useful for tracking which
    user modifies a model instance.
    
    If auto_current_user_add is True, the property value is set to the currently
    signed-in user the first time the model instance is stored in the datastore,
    unless the property has already been assigned a value. This is useful for
    tracking which user creates a model instance, which may not be the same user
    that modifies it later.
    
    UserProperty does not accept a default value. Default values are set when
    the model class is first imported, and with import caching may not be the
    currently signed-in user.
    
    Args:
      verbose_name: User friendly name of property.
      name: Storage name for property.
      required: Whether property is required.
      validator: User provided method used for validation.
      choices: User provided set of valid property values.
      auto_current_user: If true, the value is set to the current user each time
        the entity is written to the datastore.
      auto_current_user_add: If true, the value is set to the current user the
        first time the entity is written to the datastore.
      indexed: Whether property is indexed.
    """
    super(UserProperty, self).__init__(verbose_name, name, required=required,
                                       validator=validator, choices=choices,
                                       indexed=indexed)
    self.auto_current_user = auto_current_user
    self.auto_current_user_add = auto_current_user_add

  def validate(self, value):
    """Validate user.
    
    Returns:
      A valid value.
    
    Raises:
      BadValueError if property is not an instance of 'User'.
    """
    if value is not None and not isinstance(value, User):
      raise BadValueError('Property %s must be a User' % self.name)
    return value

  def default_value(self):
    """Default value for user.
    
    Returns:
      Value of users.get_current_user() if auto_current_user or
      auto_current_user_add is set; else None.
    """
    if self.auto_current_user or self.auto_current_user_add:
      return get_current_user()
    return None

  def get_value_for_datastore(self, model_instance):
    """Get value from property to send to datastore.
    
    Returns:
      A db.Key to store.
    """
    if self.auto_current_user:
      user = get_current_user()
    else:
      user = super(UserProperty, self).get_value_for_datastore(model_instance)
    if user:
      return user._user_info_key

  def make_value_from_datastore(self, value):
    """Construct a User object from the datastore representation.
    
    Args:
      value: Value retrieved from the datastore entity.
    Returns:
      A User object.
    """
    if value is None:
      return None
    else:
      return User(None, _from_model_key=value)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import logging
import urllib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util
from aeoid import middleware, users


class LoginRecord(db.Model):
  user = users.UserProperty(auto_current_user_add=True, required=True)
  timestamp = db.DateTimeProperty(auto_now_add=True)


class LoginHandler(webapp.RequestHandler):
  def get(self):
    if users.get_current_user():
      login = LoginRecord()
      logging.warn(login.user)
      login.put()
    self.redirect('/')


class AppsFederationHandler(webapp.RequestHandler):
  """Handles openid login for federated Google Apps Marketplace apps."""
  def get(self):
    domain = self.request.get("domain")
    if not domain:
      self.redirect("/login")
    else:
      openid_url = "https://www.google.com/accounts/o8/site-xrds?hd=" + domain
      self.redirect("%s?openid_url=%s" %
                    (users.OPENID_LOGIN_PATH, urllib.quote(openid_url)))


class MainHandler(webapp.RequestHandler):
  def render_template(self, file, template_vals):
    path = os.path.join(os.path.dirname(__file__), 'templates', file)
    self.response.out.write(template.render(path, template_vals))
    
  def get(self):
    user = users.get_current_user()
    logins = LoginRecord.all().order('-timestamp').fetch(20)
    logging.warn([x.user for x in logins])
    self.render_template("index.html", {
        'login_url': users.create_login_url('/login'),
        'logout_url': users.create_logout_url('/'),
        'user': user,
        'logins': logins,
    })


application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/login', LoginHandler),
    ('/apps_login', AppsFederationHandler),
], debug=True)
application = middleware.AeoidMiddleware(application)

def main():
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
