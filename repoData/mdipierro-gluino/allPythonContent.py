__FILENAME__ = bottle_example
from bottle import run, route, request, get, post, static_file, redirect
from gluino import wrapper, DAL, Field, SQLFORM, cache, IS_NOT_EMPTY
import time

# configure the gluino wrapper
wrapper.debug = True
wrapper.redirect = lambda status,url: redirect(url)

# create database and table
db=DAL('sqlite://storage.sqlite')
db.define_table('person',Field('name',requires=IS_NOT_EMPTY()))

# define action
@get('/index')
@post('/index')
@wrapper(view='templates/index.html',dbs=[db])
def index():
    vars = wrapper.extract_vars(request.forms)
    form = SQLFORM(db.person)
    if form.accepts(vars):
        message = 'hello %s' % form.vars.name
    else:
        message = 'hello anonymous'
    people = db(db.person).select()
    now  = cache.ram('time',lambda:time.ctime(),10)
    return locals()

# handle static files
@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='static')

#start web server
if __name__=='__main__':
    run(host='localhost', port=8080)

########NEW FILE########
__FILENAME__ = flask_example
from flask import Flask, request, session, redirect
from gluino import wrapper, DAL, Field, SQLFORM, cache, IS_NOT_EMPTY
import time

# configure the gluino wrapper                                      
wrapper.debug = True
wrapper.redirect = lambda status, url: redirect(url)

# initialize flask
app = Flask(__name__)
app.config.from_object(__name__)

# create database and table
db=DAL('sqlite://storage.sqlite')
db.define_table('person',Field('name',requires=IS_NOT_EMPTY()))

# define action
@app.route('/index',methods=['GET','POST'])
@wrapper(view='templates/index.html',dbs=[db])
def index():
    vars = wrapper.extract_vars(request.form)
    form = SQLFORM(db.person)
    if form.accepts(vars):
        message = 'hello %s' % form.vars.name
    else:
        message = 'hello anonymous'
    people = db(db.person).select()
    now  = cache.ram('time',lambda:time.ctime(),10)
    return locals()

# start web server
if __name__=='__main__':
    print 'serving from port 8080...'
    app.run(port=8080)

########NEW FILE########
__FILENAME__ = cache
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Basic caching classes and methods
=================================

- Cache - The generic caching object interfacing with the others
- CacheInRam - providing caching in ram
- CacheOnDisk - provides caches on disk

Memcache is also available via a different module (see gluino.contrib.memcache)

When web2py is running on Google App Engine,
caching will be provided by the GAE memcache
(see gluino.contrib.gae_memcache)
"""
import traceback
import time
import portalocker
import shelve
import thread
import os
import logging
import re
import hashlib
import datetime
try:
    import settings
    have_settings = True
except ImportError:
    have_settings = False

logger = logging.getLogger("web2py.cache")

__all__ = ['Cache', 'lazy_cache']


DEFAULT_TIME_EXPIRE = 300


class CacheAbstract(object):
    """
    Abstract class for cache implementations.
    Main function is now to provide referenced api documentation.

    Use CacheInRam or CacheOnDisk instead which are derived from this class.

    Attentions, Michele says:

    There are signatures inside gdbm files that are used directly
    by the python gdbm adapter that often are lagging behind in the
    detection code in python part.
    On every occasion that a gdbm store is probed by the python adapter,
    the probe fails, because gdbm file version is newer.
    Using gdbm directly from C would work, because there is backward
    compatibility, but not from python!
    The .shelve file is discarded and a new one created (with new
    signature) and it works until it is probed again...
    The possible consequences are memory leaks and broken sessions.
    """

    cache_stats_name = 'web2py_cache_statistics'

    def __init__(self, request=None):
        """
        Paremeters
        ----------
        request:
            the global request object
        """
        raise NotImplementedError

    def __call__(self, key, f,
                 time_expire=DEFAULT_TIME_EXPIRE):
        """
        Tries retrieve the value corresponding to `key` from the cache of the
        object exists and if it did not expire, else it called the function `f`
        and stores the output in the cache corresponding to `key`. In the case
        the output of the function is returned.

        :param key: the key of the object to be store or retrieved
        :param f: the function, whose output is to be cached
        :param time_expire: expiration of the cache in microseconds

        - `time_expire` is used to compare the current time with the time when
            the requested object was last saved in cache. It does not affect
            future requests.
        - Setting `time_expire` to 0 or negative value forces the cache to
            refresh.

        If the function `f` is `None` the cache is cleared.
        """
        raise NotImplementedError

    def clear(self, regex=None):
        """
        Clears the cache of all keys that match the provided regular expression.
        If no regular expression is provided, it clears all entries in cache.

        Parameters
        ----------
        regex:
            if provided, only keys matching the regex will be cleared.
            Otherwise all keys are cleared.
        """

        raise NotImplementedError

    def increment(self, key, value=1):
        """
        Increments the cached value for the given key by the amount in value

        Parameters
        ----------
        key:
            key for the cached object to be incremeneted
        value:
            amount of the increment (defaults to 1, can be negative)
        """
        raise NotImplementedError

    def _clear(self, storage, regex):
        """
        Auxiliary function called by `clear` to search and clear cache entries
        """
        r = re.compile(regex)
        for (key, value) in storage.items():
            if r.match(str(key)):
                del storage[key]


class CacheInRam(CacheAbstract):
    """
    Ram based caching

    This is implemented as global (per process, shared by all threads)
    dictionary.
    A mutex-lock mechanism avoid conflicts.
    """

    locker = thread.allocate_lock()
    meta_storage = {}

    def __init__(self, request=None):
        self.initialized = False
        self.request = request
        self.storage = {}

    def initialize(self):
        if self.initialized:
            return
        else:
            self.initialized = True
        self.locker.acquire()
        request = self.request
        if request:
            app = request.application
        else:
            app = ''
        if not app in self.meta_storage:
            self.storage = self.meta_storage[app] = {
                CacheAbstract.cache_stats_name: {'hit_total': 0, 'misses': 0}}
        else:
            self.storage = self.meta_storage[app]
        self.locker.release()

    def clear(self, regex=None):
        self.initialize()
        self.locker.acquire()
        storage = self.storage
        if regex is None:
            storage.clear()
        else:
            self._clear(storage, regex)

        if not CacheAbstract.cache_stats_name in storage.keys():
            storage[CacheAbstract.cache_stats_name] = {
                'hit_total': 0, 'misses': 0}

        self.locker.release()

    def __call__(self, key, f,
                 time_expire=DEFAULT_TIME_EXPIRE,
                 destroyer=None):
        """
        Attention! cache.ram does not copy the cached object. It just stores a reference to it.
        Turns out the deepcopying the object has some problems:
        1) would break backward compatibility
        2) would be limiting because people may want to cache live objects
        3) would work unless we deepcopy no storage and retrival which would make things slow.
        Anyway. You can deepcopy explicitly in the function generating the value to be cached.
        """
        self.initialize()

        dt = time_expire
        now = time.time()

        self.locker.acquire()
        item = self.storage.get(key, None)
        if item and f is None:
            del self.storage[key]
            if destroyer:
                destroyer(item[1])
        self.storage[CacheAbstract.cache_stats_name]['hit_total'] += 1
        self.locker.release()

        if f is None:
            return None
        if item and (dt is None or item[0] > now - dt):
            return item[1]
        elif item and (item[0] < now - dt) and destroyer:
            destroyer(item[1])
        value = f()

        self.locker.acquire()
        self.storage[key] = (now, value)
        self.storage[CacheAbstract.cache_stats_name]['misses'] += 1
        self.locker.release()
        return value

    def increment(self, key, value=1):
        self.initialize()
        self.locker.acquire()
        try:
            if key in self.storage:
                value = self.storage[key][1] + value
            self.storage[key] = (time.time(), value)
        except BaseException, e:
            self.locker.release()
            raise e
        self.locker.release()
        return value


class CacheOnDisk(CacheAbstract):
    """
    Disk based cache

    This is implemented as a shelve object and it is shared by multiple web2py
    processes (and threads) as long as they share the same filesystem.
    The file is locked when accessed.

    Disk cache provides persistance when web2py is started/stopped but it slower
    than `CacheInRam`

    Values stored in disk cache must be pickable.
    """

    def _close_shelve_and_unlock(self):
        try:
            if self.storage:
                self.storage.close()
        finally:
            if self.locker and self.locked:
                portalocker.unlock(self.locker)
                self.locker.close()
                self.locked = False

    def _open_shelve_and_lock(self):
        """Open and return a shelf object, obtaining an exclusive lock
        on self.locker first. Replaces the close method of the
        returned shelf instance with one that releases the lock upon
        closing."""

        storage = None
        locker = None
        locked = False
        try:
            locker = locker = open(self.locker_name, 'a')
            portalocker.lock(locker, portalocker.LOCK_EX)
            locked = True
            try:
                storage = shelve.open(self.shelve_name)
            except:
                logger.error('corrupted cache file %s, will try rebuild it'
                             % (self.shelve_name))
                storage = None
            if not storage and os.path.exists(self.shelve_name):
                os.unlink(self.shelve_name)
                storage = shelve.open(self.shelve_name)
            if not CacheAbstract.cache_stats_name in storage.keys():
                storage[CacheAbstract.cache_stats_name] = {
                    'hit_total': 0, 'misses': 0}
            storage.sync()
        except Exception, e:
            if storage:
                storage.close()
                storage = None
            if locked:
                portalocker.unlock(locker)
                locker.close()
            locked = False
            raise RuntimeError(
                'unable to create/re-create cache file %s' % self.shelve_name)
        self.locker = locker
        self.locked = locked
        self.storage = storage
        return storage

    def __init__(self, request=None, folder=None):
        self.initialized = False
        self.request = request
        self.folder = folder
        self.storage = {}

    def initialize(self):
        if self.initialized:
            return
        else:
            self.initialized = True
        folder = self.folder
        request = self.request

        # Lets test if the cache folder exists, if not
        # we are going to create it
        folder = folder or os.path.join(request.folder, 'cache')

        if not os.path.exists(folder):
            os.mkdir(folder)

        ### we need this because of a possible bug in shelve that may
        ### or may not lock
        self.locker_name = os.path.join(folder, 'cache.lock')
        self.shelve_name = os.path.join(folder, 'cache.shelve')

    def clear(self, regex=None):
        self.initialize()
        storage = self._open_shelve_and_lock()
        try:
            if regex is None:
                storage.clear()
            else:
                self._clear(storage, regex)
            storage.sync()
        finally:
            self._close_shelve_and_unlock()

    def __call__(self, key, f,
                 time_expire=DEFAULT_TIME_EXPIRE):
        self.initialize()
        dt = time_expire
        storage = self._open_shelve_and_lock()
        try:
            item = storage.get(key, None)
            storage[CacheAbstract.cache_stats_name]['hit_total'] += 1
            if item and f is None:
                del storage[key]
                storage.sync()
            now = time.time()
            if f is None:
                value = None
            elif item and (dt is None or item[0] > now - dt):
                value = item[1]
            else:
                value = f()
                storage[key] = (now, value)
                storage[CacheAbstract.cache_stats_name]['misses'] += 1
                storage.sync()
        finally:
            self._close_shelve_and_unlock()

        return value

    def increment(self, key, value=1):
        self.initialize()
        storage = self._open_shelve_and_lock()
        try:
            if key in storage:
                value = storage[key][1] + value
            storage[key] = (time.time(), value)
            storage.sync()
        finally:
            self._close_shelve_and_unlock()
        return value

class CacheAction(object):
    def __init__(self, func, key, time_expire, cache, cache_model):
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.func = func
        self.key = key
        self.time_expire = time_expire
        self.cache = cache
        self.cache_model = cache_model

    def __call__(self, *a, **b):
        if not self.key:
            key2 = self.__name__ + ':' + repr(a) + ':' + repr(b)
        else:
            key2 = self.key.replace('%(name)s', self.__name__)\
                .replace('%(args)s', str(a)).replace('%(vars)s', str(b))
        cache_model = self.cache_model
        if not cache_model or isinstance(cache_model, str):
            cache_model = getattr(self.cache, cache_model or 'ram')
        return cache_model(key2,
                           lambda a=a, b=b: self.func(*a, **b),
                           self.time_expire)


class Cache(object):
    """
    Sets up generic caching, creating an instance of both CacheInRam and
    CacheOnDisk.
    In case of GAE will make use of gluino.contrib.gae_memcache.

    - self.ram is an instance of CacheInRam
    - self.disk is an instance of CacheOnDisk
    """

    autokey = ':%(name)s:%(args)s:%(vars)s'

    def __init__(self, request):
        """
        Parameters
        ----------
        request:
            the global request object
        """
        # GAE will have a special caching
        if have_settings and settings.global_settings.web2py_runtime_gae:
            from contrib.gae_memcache import MemcacheClient
            self.ram = self.disk = MemcacheClient(request)
        else:
            # Otherwise use ram (and try also disk)
            self.ram = CacheInRam(request)
            try:
                self.disk = CacheOnDisk(request)
            except IOError:
                logger.warning('no cache.disk (IOError)')
            except AttributeError:
                # normally not expected anymore, as GAE has already
                # been accounted for
                logger.warning('no cache.disk (AttributeError)')

    def action(self, time_expire=DEFAULT_TIME_EXPIRE, cache_model=None,
             prefix=None, session=False, vars=True, lang=True,
             user_agent=False, public=True, valid_statuses=None,
             quick=None):
        """
        Experimental!
        Currently only HTTP 1.1 compliant
        reference : http://code.google.com/p/doctype-mirror/wiki/ArticleHttpCaching
        time_expire: same as @cache
        cache_model: same as @cache
        prefix: add a prefix to the calculated key
        session: adds response.session_id to the key
        vars: adds request.env.query_string
        lang: adds T.accepted_language
        user_agent: if True, adds is_mobile and is_tablet to the key.
            Pass a dict to use all the needed values (uses str(.items())) (e.g. user_agent=request.user_agent())
            used only if session is not True
        public: if False forces the Cache-Control to be 'private'
        valid_statuses: by default only status codes starting with 1,2,3 will be cached.
            pass an explicit list of statuses on which turn the cache on
        quick: Session,Vars,Lang,User-agent,Public:
            fast overrides with initial strings, e.g. 'SVLP' or 'VLP', or 'VLP'
        """
        from gluino import current
        from gluino.http import HTTP
        def wrap(func):
            def wrapped_f():
                if current.request.env.request_method != 'GET':
                    return func()
                if time_expire:
                    cache_control = 'max-age=%(time_expire)s, s-maxage=%(time_expire)s' % dict(time_expire=time_expire)
                    if quick:
                        session_ = True if 'S' in quick else False
                        vars_ = True if 'V' in quick else False
                        lang_ = True if 'L' in quick else False
                        user_agent_ = True if 'U' in quick else False
                        public_ = True if 'P' in quick else False
                    else:
                        session_, vars_, lang_, user_agent_, public_ = session, vars, lang, user_agent, public
                    if not session_ and public_:
                        cache_control += ', public'
                        expires = (current.request.utcnow + datetime.timedelta(seconds=time_expire)).strftime('%a, %d %b %Y %H:%M:%S GMT')
                        vary = None
                    else:
                        cache_control += ', private'
                        expires = 'Fri, 01 Jan 1990 00:00:00 GMT'
                if cache_model:
                    #figure out the correct cache key
                    cache_key = [current.request.env.path_info, current.response.view]
                    if session_:
                        cache_key.append(current.response.session_id)
                    elif user_agent_:
                        if user_agent_ is True:
                            cache_key.append("%(is_mobile)s_%(is_tablet)s" % current.request.user_agent())
                        else:
                            cache_key.append(str(user_agent_.items()))
                    if vars_:
                        cache_key.append(current.request.env.query_string)
                    if lang_:
                        cache_key.append(current.T.accepted_language)
                    cache_key = hashlib.md5('__'.join(cache_key)).hexdigest()
                    if prefix:
                        cache_key = prefix + cache_key
                    try:
                        #action returns something
                        rtn = cache_model(cache_key, lambda : func(), time_expire=time_expire)
                        http, status = None, current.response.status
                    except HTTP, e:
                        #action raises HTTP (can still be valid)
                        rtn = cache_model(cache_key, lambda : e.body, time_expire=time_expire)
                        http, status = HTTP(e.status, rtn, **e.headers), e.status
                    else:
                        #action raised a generic exception
                        http = None
                else:
                    #no server-cache side involved
                    try:
                        #action returns something
                        rtn = func()
                        http, status = None, current.response.status
                    except HTTP, e:
                        #action raises HTTP (can still be valid)
                        status = e.status
                        http = HTTP(e.status, e.body, **e.headers)
                    else:
                        #action raised a generic exception
                        http = None
                send_headers = False
                if http and isinstance(valid_statuses, list):
                    if status in valid_statuses:
                        send_headers = True
                elif valid_statuses is None:
                    if str(status)[0] in '123':
                        send_headers = True
                if send_headers:
                    headers = {
                        'Pragma' : None,
                        'Expires' : expires,
                        'Cache-Control' : cache_control
                        }
                    current.response.headers.update(headers)
                if cache_model and not send_headers:
                    #we cached already the value, but the status is not valid
                    #so we need to delete the cached value
                    cache_model(cache_key, None)
                if http:
                    if send_headers:
                        http.headers.update(current.response.headers)
                    raise http
                return rtn
            wrapped_f.__name__ = func.__name__
            wrapped_f.__doc__ = func.__doc__
            return wrapped_f
        return wrap

    def __call__(self,
                 key=None,
                 time_expire=DEFAULT_TIME_EXPIRE,
                 cache_model=None):
        """
        Decorator function that can be used to cache any function/method.

        Example::

            @cache('key', 5000, cache.ram)
            def f():
                return time.ctime()

        When the function f is called, web2py tries to retrieve
        the value corresponding to `key` from the cache of the
        object exists and if it did not expire, else it calles the function `f`
        and stores the output in the cache corresponding to `key`. In the case
        the output of the function is returned.

        :param key: the key of the object to be store or retrieved
        :param time_expire: expiration of the cache in microseconds
        :param cache_model: "ram", "disk", or other
            (like "memcache" if defined). It defaults to "ram".

        Notes
        -----
        `time_expire` is used to compare the curret time with the time when the
        requested object was last saved in cache. It does not affect future
        requests.
        Setting `time_expire` to 0 or negative value forces the cache to
        refresh.

        If the function `f` is an action, we suggest using
        @cache.client instead
        """

        def tmp(func, cache=self, cache_model=cache_model):
            return CacheAction(func, key, time_expire, self, cache_model)
        return tmp

    @staticmethod
    def with_prefix(cache_model, prefix):
        """
        allow replacing cache.ram with cache.with_prefix(cache.ram,'prefix')
        it will add prefix to all the cache keys used.
        """
        return lambda key, f, time_expire=DEFAULT_TIME_EXPIRE, prefix=prefix:\
            cache_model(prefix + key, f, time_expire)


def lazy_cache(key=None, time_expire=None, cache_model='ram'):
    """
    can be used to cache any function including in modules,
    as long as the cached function is only called within a web2py request
    if a key is not provided, one is generated from the function name
    the time_expire defaults to None (no cache expiration)
    if cache_model is "ram" then the model is current.cache.ram, etc.
    """
    def decorator(f, key=key, time_expire=time_expire, cache_model=cache_model):
        key = key or repr(f)

        def g(*c, **d):
            from gluino import current
            return current.cache(key, time_expire, cache_model)(f)(*c, **d)
        g.__name__ = f.__name__
        return g
    return decorator

########NEW FILE########
__FILENAME__ = contenttype
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

CONTENT_TYPE dictionary created against freedesktop.org' shared mime info
database version 1.1.

Deviations from official standards:
- '.md': 'application/x-genesis-rom' --> 'text/x-markdown'
- '.png': 'image/x-apple-ios-png' --> 'image/png'
Additions:
- '.load': 'text/html'
- '.json': 'application/json'
- '.jsonp': 'application/jsonp'
- '.pickle': 'application/python-pickle'
- '.w2p': 'application/w2p'
"""

__all__ = ['contenttype']

CONTENT_TYPE = {
    '.123': 'application/vnd.lotus-1-2-3',
    '.3ds': 'image/x-3ds',
    '.3g2': 'video/3gpp2',
    '.3ga': 'video/3gpp',
    '.3gp': 'video/3gpp',
    '.3gp2': 'video/3gpp2',
    '.3gpp': 'video/3gpp',
    '.3gpp2': 'video/3gpp2',
    '.602': 'application/x-t602',
    '.669': 'audio/x-mod',
    '.7z': 'application/x-7z-compressed',
    '.a': 'application/x-archive',
    '.aac': 'audio/aac',
    '.abw': 'application/x-abiword',
    '.abw.crashed': 'application/x-abiword',
    '.abw.gz': 'application/x-abiword',
    '.ac3': 'audio/ac3',
    '.ace': 'application/x-ace',
    '.adb': 'text/x-adasrc',
    '.ads': 'text/x-adasrc',
    '.afm': 'application/x-font-afm',
    '.ag': 'image/x-applix-graphics',
    '.ai': 'application/illustrator',
    '.aif': 'audio/x-aiff',
    '.aifc': 'audio/x-aifc',
    '.aiff': 'audio/x-aiff',
    '.aiffc': 'audio/x-aifc',
    '.al': 'application/x-perl',
    '.alz': 'application/x-alz',
    '.amr': 'audio/amr',
    '.amz': 'audio/x-amzxml',
    '.ani': 'application/x-navi-animation',
    '.anim[1-9j]': 'video/x-anim',
    '.anx': 'application/annodex',
    '.ape': 'audio/x-ape',
    '.apk': 'application/vnd.android.package-archive',
    '.ar': 'application/x-archive',
    '.arj': 'application/x-arj',
    '.arw': 'image/x-sony-arw',
    '.as': 'application/x-applix-spreadsheet',
    '.asc': 'text/plain',
    '.asf': 'video/x-ms-asf',
    '.asp': 'application/x-asp',
    '.ass': 'text/x-ssa',
    '.asx': 'audio/x-ms-asx',
    '.atom': 'application/atom+xml',
    '.au': 'audio/basic',
    '.avf': 'video/x-msvideo',
    '.avi': 'video/x-msvideo',
    '.aw': 'application/x-applix-word',
    '.awb': 'audio/amr-wb',
    '.awk': 'application/x-awk',
    '.axa': 'audio/annodex',
    '.axv': 'video/annodex',
    '.bak': 'application/x-trash',
    '.bcpio': 'application/x-bcpio',
    '.bdf': 'application/x-font-bdf',
    '.bdm': 'video/mp2t',
    '.bdmv': 'video/mp2t',
    '.bib': 'text/x-bibtex',
    '.bin': 'application/octet-stream',
    '.blend': 'application/x-blender',
    '.blender': 'application/x-blender',
    '.bmp': 'image/bmp',
    '.bz': 'application/x-bzip',
    '.bz2': 'application/x-bzip',
    '.c': 'text/x-csrc',
    '.c++': 'text/x-c++src',
    '.cab': 'application/vnd.ms-cab-compressed',
    '.cap': 'application/vnd.tcpdump.pcap',
    '.cb7': 'application/x-cb7',
    '.cbl': 'text/x-cobol',
    '.cbr': 'application/x-cbr',
    '.cbt': 'application/x-cbt',
    '.cbz': 'application/x-cbz',
    '.cc': 'text/x-c++src',
    '.ccmx': 'application/x-ccmx',
    '.cdf': 'application/x-netcdf',
    '.cdr': 'application/vnd.corel-draw',
    '.cer': 'application/pkix-cert',
    '.cert': 'application/x-x509-ca-cert',
    '.cgm': 'image/cgm',
    '.chm': 'application/vnd.ms-htmlhelp',
    '.chrt': 'application/x-kchart',
    '.class': 'application/x-java',
    '.clpi': 'video/mp2t',
    '.cls': 'text/x-tex',
    '.cmake': 'text/x-cmake',
    '.cob': 'text/x-cobol',
    '.cpi': 'video/mp2t',
    '.cpio': 'application/x-cpio',
    '.cpio.gz': 'application/x-cpio-compressed',
    '.cpp': 'text/x-c++src',
    '.cr2': 'image/x-canon-cr2',
    '.crl': 'application/pkix-crl',
    '.crt': 'application/x-x509-ca-cert',
    '.crw': 'image/x-canon-crw',
    '.cs': 'text/x-csharp',
    '.csh': 'application/x-csh',
    '.css': 'text/css',
    '.cssl': 'text/css',
    '.csv': 'text/csv',
    '.cue': 'application/x-cue',
    '.cur': 'image/x-win-bitmap',
    '.cxx': 'text/x-c++src',
    '.d': 'text/x-dsrc',
    '.dar': 'application/x-dar',
    '.dbf': 'application/x-dbf',
    '.dc': 'application/x-dc-rom',
    '.dcl': 'text/x-dcl',
    '.dcm': 'application/dicom',
    '.dcr': 'image/x-kodak-dcr',
    '.dds': 'image/x-dds',
    '.deb': 'application/x-deb',
    '.der': 'application/x-x509-ca-cert',
    '.desktop': 'application/x-desktop',
    '.di': 'text/x-dsrc',
    '.dia': 'application/x-dia-diagram',
    '.diff': 'text/x-patch',
    '.divx': 'video/x-msvideo',
    '.djv': 'image/vnd.djvu',
    '.djvu': 'image/vnd.djvu',
    '.dmg': 'application/x-apple-diskimage',
    '.dmp': 'application/vnd.tcpdump.pcap',
    '.dng': 'image/x-adobe-dng',
    '.doc': 'application/msword',
    '.docbook': 'application/x-docbook+xml',
    '.docm': 'application/vnd.ms-word.document.macroenabled.12',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.dot': 'text/vnd.graphviz',
    '.dotm': 'application/vnd.ms-word.template.macroenabled.12',
    '.dotx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
    '.dsl': 'text/x-dsl',
    '.dtd': 'application/xml-dtd',
    '.dts': 'audio/vnd.dts',
    '.dtshd': 'audio/vnd.dts.hd',
    '.dtx': 'text/x-tex',
    '.dv': 'video/dv',
    '.dvi': 'application/x-dvi',
    '.dvi.bz2': 'application/x-bzdvi',
    '.dvi.gz': 'application/x-gzdvi',
    '.dwg': 'image/vnd.dwg',
    '.dxf': 'image/vnd.dxf',
    '.e': 'text/x-eiffel',
    '.egon': 'application/x-egon',
    '.eif': 'text/x-eiffel',
    '.el': 'text/x-emacs-lisp',
    '.emf': 'image/x-emf',
    '.eml': 'message/rfc822',
    '.emp': 'application/vnd.emusic-emusic_package',
    '.ent': 'application/xml-external-parsed-entity',
    '.eps': 'image/x-eps',
    '.eps.bz2': 'image/x-bzeps',
    '.eps.gz': 'image/x-gzeps',
    '.epsf': 'image/x-eps',
    '.epsf.bz2': 'image/x-bzeps',
    '.epsf.gz': 'image/x-gzeps',
    '.epsi': 'image/x-eps',
    '.epsi.bz2': 'image/x-bzeps',
    '.epsi.gz': 'image/x-gzeps',
    '.epub': 'application/epub+zip',
    '.erl': 'text/x-erlang',
    '.es': 'application/ecmascript',
    '.etheme': 'application/x-e-theme',
    '.etx': 'text/x-setext',
    '.exe': 'application/x-ms-dos-executable',
    '.exr': 'image/x-exr',
    '.ez': 'application/andrew-inset',
    '.f': 'text/x-fortran',
    '.f4a': 'audio/mp4',
    '.f4b': 'audio/x-m4b',
    '.f4v': 'video/mp4',
    '.f90': 'text/x-fortran',
    '.f95': 'text/x-fortran',
    '.fb2': 'application/x-fictionbook+xml',
    '.fig': 'image/x-xfig',
    '.fits': 'image/fits',
    '.fl': 'application/x-fluid',
    '.flac': 'audio/flac',
    '.flc': 'video/x-flic',
    '.fli': 'video/x-flic',
    '.flv': 'video/x-flv',
    '.flw': 'application/x-kivio',
    '.fo': 'text/x-xslfo',
    '.fodg': 'application/vnd.oasis.opendocument.graphics-flat-xml',
    '.fodp': 'application/vnd.oasis.opendocument.presentation-flat-xml',
    '.fods': 'application/vnd.oasis.opendocument.spreadsheet-flat-xml',
    '.fodt': 'application/vnd.oasis.opendocument.text-flat-xml',
    '.for': 'text/x-fortran',
    '.fxm': 'video/x-javafx',
    '.g3': 'image/fax-g3',
    '.gb': 'application/x-gameboy-rom',
    '.gba': 'application/x-gba-rom',
    '.gcrd': 'text/vcard',
    '.ged': 'application/x-gedcom',
    '.gedcom': 'application/x-gedcom',
    '.gem': 'application/x-tar',
    '.gen': 'application/x-genesis-rom',
    '.gf': 'application/x-tex-gf',
    '.gg': 'application/x-sms-rom',
    '.gif': 'image/gif',
    '.glade': 'application/x-glade',
    '.gml': 'application/gml+xml',
    '.gmo': 'application/x-gettext-translation',
    '.gnc': 'application/x-gnucash',
    '.gnd': 'application/gnunet-directory',
    '.gnucash': 'application/x-gnucash',
    '.gnumeric': 'application/x-gnumeric',
    '.gnuplot': 'application/x-gnuplot',
    '.go': 'text/x-go',
    '.gp': 'application/x-gnuplot',
    '.gpg': 'application/pgp-encrypted',
    '.gplt': 'application/x-gnuplot',
    '.gra': 'application/x-graphite',
    '.gsf': 'application/x-font-type1',
    '.gsm': 'audio/x-gsm',
    '.gtar': 'application/x-tar',
    '.gv': 'text/vnd.graphviz',
    '.gvp': 'text/x-google-video-pointer',
    '.gz': 'application/gzip',
    '.h': 'text/x-chdr',
    '.h++': 'text/x-c++hdr',
    '.h4': 'application/x-hdf',
    '.h5': 'application/x-hdf',
    '.hdf': 'application/x-hdf',
    '.hdf4': 'application/x-hdf',
    '.hdf5': 'application/x-hdf',
    '.hh': 'text/x-c++hdr',
    '.hlp': 'application/winhlp',
    '.hp': 'text/x-c++hdr',
    '.hpgl': 'application/vnd.hp-hpgl',
    '.hpp': 'text/x-c++hdr',
    '.hs': 'text/x-haskell',
    '.htm': 'text/html',
    '.html': 'text/html',
    '.hwp': 'application/x-hwp',
    '.hwt': 'application/x-hwt',
    '.hxx': 'text/x-c++hdr',
    '.ica': 'application/x-ica',
    '.icb': 'image/x-tga',
    '.icc': 'application/vnd.iccprofile',
    '.icm': 'application/vnd.iccprofile',
    '.icns': 'image/x-icns',
    '.ico': 'image/vnd.microsoft.icon',
    '.ics': 'text/calendar',
    '.idl': 'text/x-idl',
    '.ief': 'image/ief',
    '.iff': 'image/x-ilbm',
    '.ilbm': 'image/x-ilbm',
    '.ime': 'text/x-imelody',
    '.imy': 'text/x-imelody',
    '.ins': 'text/x-tex',
    '.iptables': 'text/x-iptables',
    '.iso': 'application/x-cd-image',
    '.iso9660': 'application/x-cd-image',
    '.it': 'audio/x-it',
    '.it87': 'application/x-it87',
    '.j2k': 'image/jp2',
    '.jad': 'text/vnd.sun.j2me.app-descriptor',
    '.jar': 'application/x-java-archive',
    '.java': 'text/x-java',
    '.jceks': 'application/x-java-jce-keystore',
    '.jks': 'application/x-java-keystore',
    '.jng': 'image/x-jng',
    '.jnlp': 'application/x-java-jnlp-file',
    '.jp2': 'image/jp2',
    '.jpc': 'image/jp2',
    '.jpe': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.jpf': 'image/jp2',
    '.jpg': 'image/jpeg',
    '.jpr': 'application/x-jbuilder-project',
    '.jpx': 'image/jp2',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.jsonp': 'application/jsonp',
    '.k25': 'image/x-kodak-k25',
    '.kar': 'audio/midi',
    '.karbon': 'application/x-karbon',
    '.kdc': 'image/x-kodak-kdc',
    '.kdelnk': 'application/x-desktop',
    '.kexi': 'application/x-kexiproject-sqlite3',
    '.kexic': 'application/x-kexi-connectiondata',
    '.kexis': 'application/x-kexiproject-shortcut',
    '.kfo': 'application/x-kformula',
    '.kil': 'application/x-killustrator',
    '.kino': 'application/smil',
    '.kml': 'application/vnd.google-earth.kml+xml',
    '.kmz': 'application/vnd.google-earth.kmz',
    '.kon': 'application/x-kontour',
    '.kpm': 'application/x-kpovmodeler',
    '.kpr': 'application/x-kpresenter',
    '.kpt': 'application/x-kpresenter',
    '.kra': 'application/x-krita',
    '.ks': 'application/x-java-keystore',
    '.ksp': 'application/x-kspread',
    '.kud': 'application/x-kugar',
    '.kwd': 'application/x-kword',
    '.kwt': 'application/x-kword',
    '.la': 'application/x-shared-library-la',
    '.latex': 'text/x-tex',
    '.lbm': 'image/x-ilbm',
    '.ldif': 'text/x-ldif',
    '.lha': 'application/x-lha',
    '.lhs': 'text/x-literate-haskell',
    '.lhz': 'application/x-lhz',
    '.load' : 'text/html',
    '.log': 'text/x-log',
    '.lrz': 'application/x-lrzip',
    '.ltx': 'text/x-tex',
    '.lua': 'text/x-lua',
    '.lwo': 'image/x-lwo',
    '.lwob': 'image/x-lwo',
    '.lwp': 'application/vnd.lotus-wordpro',
    '.lws': 'image/x-lws',
    '.ly': 'text/x-lilypond',
    '.lyx': 'application/x-lyx',
    '.lz': 'application/x-lzip',
    '.lzh': 'application/x-lha',
    '.lzma': 'application/x-lzma',
    '.lzo': 'application/x-lzop',
    '.m': 'text/x-matlab',
    '.m15': 'audio/x-mod',
    '.m1u': 'video/vnd.mpegurl',
    '.m2t': 'video/mp2t',
    '.m2ts': 'video/mp2t',
    '.m3u': 'application/vnd.apple.mpegurl',
    '.m3u8': 'application/vnd.apple.mpegurl',
    '.m4': 'application/x-m4',
    '.m4a': 'audio/mp4',
    '.m4b': 'audio/x-m4b',
    '.m4u': 'video/vnd.mpegurl',
    '.m4v': 'video/mp4',
    '.mab': 'application/x-markaby',
    '.mak': 'text/x-makefile',
    '.man': 'application/x-troff-man',
    '.manifest': 'text/cache-manifest',
    '.markdown': 'text/x-markdown',
    '.mbox': 'application/mbox',
    '.md': 'text/x-markdown',
    '.mdb': 'application/vnd.ms-access',
    '.mdi': 'image/vnd.ms-modi',
    '.me': 'text/x-troff-me',
    '.med': 'audio/x-mod',
    '.meta4': 'application/metalink4+xml',
    '.metalink': 'application/metalink+xml',
    '.mgp': 'application/x-magicpoint',
    '.mht': 'application/x-mimearchive',
    '.mhtml': 'application/x-mimearchive',
    '.mid': 'audio/midi',
    '.midi': 'audio/midi',
    '.mif': 'application/x-mif',
    '.minipsf': 'audio/x-minipsf',
    '.mk': 'text/x-makefile',
    '.mka': 'audio/x-matroska',
    '.mkd': 'text/x-markdown',
    '.mkv': 'video/x-matroska',
    '.ml': 'text/x-ocaml',
    '.mli': 'text/x-ocaml',
    '.mm': 'text/x-troff-mm',
    '.mmf': 'application/x-smaf',
    '.mml': 'application/mathml+xml',
    '.mng': 'video/x-mng',
    '.mo': 'text/x-modelica',
    '.mo3': 'audio/x-mo3',
    '.mobi': 'application/x-mobipocket-ebook',
    '.moc': 'text/x-moc',
    '.mod': 'audio/x-mod',
    '.mof': 'text/x-mof',
    '.moov': 'video/quicktime',
    '.mov': 'video/quicktime',
    '.movie': 'video/x-sgi-movie',
    '.mp+': 'audio/x-musepack',
    '.mp2': 'video/mpeg',
    '.mp3': 'audio/mpeg',
    '.mp4': 'video/mp4',
    '.mpc': 'audio/x-musepack',
    '.mpe': 'video/mpeg',
    '.mpeg': 'video/mpeg',
    '.mpg': 'video/mpeg',
    '.mpga': 'audio/mpeg',
    '.mpl': 'video/mp2t',
    '.mpls': 'video/mp2t',
    '.mpp': 'audio/x-musepack',
    '.mrl': 'text/x-mrml',
    '.mrml': 'text/x-mrml',
    '.mrw': 'image/x-minolta-mrw',
    '.ms': 'text/x-troff-ms',
    '.msi': 'application/x-msi',
    '.msod': 'image/x-msod',
    '.msx': 'application/x-msx-rom',
    '.mtm': 'audio/x-mod',
    '.mts': 'video/mp2t',
    '.mup': 'text/x-mup',
    '.mxf': 'application/mxf',
    '.mxu': 'video/vnd.mpegurl',
    '.n64': 'application/x-n64-rom',
    '.nb': 'application/mathematica',
    '.nc': 'application/x-netcdf',
    '.nds': 'application/x-nintendo-ds-rom',
    '.nef': 'image/x-nikon-nef',
    '.nes': 'application/x-nes-rom',
    '.nfo': 'text/x-nfo',
    '.not': 'text/x-mup',
    '.nsc': 'application/x-netshow-channel',
    '.nsv': 'video/x-nsv',
    '.nzb': 'application/x-nzb',
    '.o': 'application/x-object',
    '.obj': 'application/x-tgif',
    '.ocl': 'text/x-ocl',
    '.oda': 'application/oda',
    '.odb': 'application/vnd.oasis.opendocument.database',
    '.odc': 'application/vnd.oasis.opendocument.chart',
    '.odf': 'application/vnd.oasis.opendocument.formula',
    '.odg': 'application/vnd.oasis.opendocument.graphics',
    '.odi': 'application/vnd.oasis.opendocument.image',
    '.odm': 'application/vnd.oasis.opendocument.text-master',
    '.odp': 'application/vnd.oasis.opendocument.presentation',
    '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
    '.odt': 'application/vnd.oasis.opendocument.text',
    '.oga': 'audio/ogg',
    '.ogg': 'application/ogg',
    '.ogm': 'video/x-ogm+ogg',
    '.ogv': 'video/ogg',
    '.ogx': 'application/ogg',
    '.old': 'application/x-trash',
    '.oleo': 'application/x-oleo',
    '.ooc': 'text/x-ooc',
    '.opml': 'text/x-opml+xml',
    '.oprc': 'application/vnd.palm',
    '.ora': 'image/openraster',
    '.orf': 'image/x-olympus-orf',
    '.otc': 'application/vnd.oasis.opendocument.chart-template',
    '.otf': 'application/x-font-otf',
    '.otg': 'application/vnd.oasis.opendocument.graphics-template',
    '.oth': 'application/vnd.oasis.opendocument.text-web',
    '.otp': 'application/vnd.oasis.opendocument.presentation-template',
    '.ots': 'application/vnd.oasis.opendocument.spreadsheet-template',
    '.ott': 'application/vnd.oasis.opendocument.text-template',
    '.owl': 'application/rdf+xml',
    '.oxps': 'application/oxps',
    '.oxt': 'application/vnd.openofficeorg.extension',
    '.p': 'text/x-pascal',
    '.p10': 'application/pkcs10',
    '.p12': 'application/x-pkcs12',
    '.p7b': 'application/x-pkcs7-certificates',
    '.p7c': 'application/pkcs7-mime',
    '.p7m': 'application/pkcs7-mime',
    '.p7s': 'application/pkcs7-signature',
    '.p8': 'application/pkcs8',
    '.pack': 'application/x-java-pack200',
    '.pak': 'application/x-pak',
    '.par2': 'application/x-par2',
    '.pas': 'text/x-pascal',
    '.patch': 'text/x-patch',
    '.pbm': 'image/x-portable-bitmap',
    '.pcap': 'application/vnd.tcpdump.pcap',
    '.pcd': 'image/x-photo-cd',
    '.pcf': 'application/x-cisco-vpn-settings',
    '.pcf.gz': 'application/x-font-pcf',
    '.pcf.z': 'application/x-font-pcf',
    '.pcl': 'application/vnd.hp-pcl',
    '.pct': 'image/x-pict',
    '.pcx': 'image/x-pcx',
    '.pdb': 'chemical/x-pdb',
    '.pdc': 'application/x-aportisdoc',
    '.pdf': 'application/pdf',
    '.pdf.bz2': 'application/x-bzpdf',
    '.pdf.gz': 'application/x-gzpdf',
    '.pdf.xz': 'application/x-xzpdf',
    '.pef': 'image/x-pentax-pef',
    '.pem': 'application/x-x509-ca-cert',
    '.perl': 'application/x-perl',
    '.pfa': 'application/x-font-type1',
    '.pfb': 'application/x-font-type1',
    '.pfx': 'application/x-pkcs12',
    '.pgm': 'image/x-portable-graymap',
    '.pgn': 'application/x-chess-pgn',
    '.pgp': 'application/pgp-encrypted',
    '.php': 'application/x-php',
    '.php3': 'application/x-php',
    '.php4': 'application/x-php',
    '.php5': 'application/x-php',
    '.phps': 'application/x-php',
    '.pict': 'image/x-pict',
    '.pict1': 'image/x-pict',
    '.pict2': 'image/x-pict',
    '.pk': 'application/x-tex-pk',
    '.pkipath': 'application/pkix-pkipath',
    '.pkr': 'application/pgp-keys',
    '.pl': 'application/x-perl',
    '.pla': 'audio/x-iriver-pla',
    '.pln': 'application/x-planperfect',
    '.pls': 'audio/x-scpls',
    '.pm': 'application/x-perl',
    '.png': 'image/png',
    '.pnm': 'image/x-portable-anymap',
    '.pntg': 'image/x-macpaint',
    '.po': 'text/x-gettext-translation',
    '.por': 'application/x-spss-por',
    '.pot': 'text/x-gettext-translation-template',
    '.potm': 'application/vnd.ms-powerpoint.template.macroenabled.12',
    '.potx': 'application/vnd.openxmlformats-officedocument.presentationml.template',
    '.ppam': 'application/vnd.ms-powerpoint.addin.macroenabled.12',
    '.ppm': 'image/x-portable-pixmap',
    '.pps': 'application/vnd.ms-powerpoint',
    '.ppsm': 'application/vnd.ms-powerpoint.slideshow.macroenabled.12',
    '.ppsx': 'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptm': 'application/vnd.ms-powerpoint.presentation.macroenabled.12',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.ppz': 'application/vnd.ms-powerpoint',
    '.pqa': 'application/vnd.palm',
    '.prc': 'application/vnd.palm',
    '.ps': 'application/postscript',
    '.ps.bz2': 'application/x-bzpostscript',
    '.ps.gz': 'application/x-gzpostscript',
    '.psd': 'image/vnd.adobe.photoshop',
    '.psf': 'audio/x-psf',
    '.psf.gz': 'application/x-gz-font-linux-psf',
    '.psflib': 'audio/x-psflib',
    '.psid': 'audio/prs.sid',
    '.psw': 'application/x-pocket-word',
    '.pw': 'application/x-pw',
    '.py': 'text/x-python',
    '.pyc': 'application/x-python-bytecode',
    '.pickle': 'application/python-pickle',
    '.pyo': 'application/x-python-bytecode',
    '.qif': 'image/x-quicktime',
    '.qml': 'text/x-qml',
    '.qt': 'video/quicktime',
    '.qti': 'application/x-qtiplot',
    '.qti.gz': 'application/x-qtiplot',
    '.qtif': 'image/x-quicktime',
    '.qtl': 'application/x-quicktime-media-link',
    '.qtvr': 'video/quicktime',
    '.ra': 'audio/vnd.rn-realaudio',
    '.raf': 'image/x-fuji-raf',
    '.ram': 'application/ram',
    '.rar': 'application/x-rar',
    '.ras': 'image/x-cmu-raster',
    '.raw': 'image/x-panasonic-raw',
    '.rax': 'audio/vnd.rn-realaudio',
    '.rb': 'application/x-ruby',
    '.rdf': 'application/rdf+xml',
    '.rdfs': 'application/rdf+xml',
    '.reg': 'text/x-ms-regedit',
    '.rej': 'text/x-reject',
    '.rgb': 'image/x-rgb',
    '.rle': 'image/rle',
    '.rm': 'application/vnd.rn-realmedia',
    '.rmj': 'application/vnd.rn-realmedia',
    '.rmm': 'application/vnd.rn-realmedia',
    '.rms': 'application/vnd.rn-realmedia',
    '.rmvb': 'application/vnd.rn-realmedia',
    '.rmx': 'application/vnd.rn-realmedia',
    '.rnc': 'application/relax-ng-compact-syntax',
    '.rng': 'application/xml',
    '.roff': 'text/troff',
    '.rp': 'image/vnd.rn-realpix',
    '.rpm': 'application/x-rpm',
    '.rss': 'application/rss+xml',
    '.rt': 'text/vnd.rn-realtext',
    '.rtf': 'application/rtf',
    '.rtx': 'text/richtext',
    '.rv': 'video/vnd.rn-realvideo',
    '.rvx': 'video/vnd.rn-realvideo',
    '.rw2': 'image/x-panasonic-raw2',
    '.s3m': 'audio/x-s3m',
    '.sam': 'application/x-amipro',
    '.sami': 'application/x-sami',
    '.sav': 'application/x-spss-sav',
    '.scala': 'text/x-scala',
    '.scm': 'text/x-scheme',
    '.sda': 'application/vnd.stardivision.draw',
    '.sdc': 'application/vnd.stardivision.calc',
    '.sdd': 'application/vnd.stardivision.impress',
    '.sdp': 'application/sdp',
    '.sds': 'application/vnd.stardivision.chart',
    '.sdw': 'application/vnd.stardivision.writer',
    '.sgf': 'application/x-go-sgf',
    '.sgi': 'image/x-sgi',
    '.sgl': 'application/vnd.stardivision.writer',
    '.sgm': 'text/sgml',
    '.sgml': 'text/sgml',
    '.sh': 'application/x-shellscript',
    '.shape': 'application/x-dia-shape',
    '.shar': 'application/x-shar',
    '.shn': 'application/x-shorten',
    '.siag': 'application/x-siag',
    '.sid': 'audio/prs.sid',
    '.sik': 'application/x-trash',
    '.sis': 'application/vnd.symbian.install',
    '.sisx': 'x-epoc/x-sisx-app',
    '.sit': 'application/x-stuffit',
    '.siv': 'application/sieve',
    '.sk': 'image/x-skencil',
    '.sk1': 'image/x-skencil',
    '.skr': 'application/pgp-keys',
    '.sldm': 'application/vnd.ms-powerpoint.slide.macroenabled.12',
    '.sldx': 'application/vnd.openxmlformats-officedocument.presentationml.slide',
    '.slk': 'text/spreadsheet',
    '.smaf': 'application/x-smaf',
    '.smc': 'application/x-snes-rom',
    '.smd': 'application/vnd.stardivision.mail',
    '.smf': 'application/vnd.stardivision.math',
    '.smi': 'application/x-sami',
    '.smil': 'application/smil',
    '.sml': 'application/smil',
    '.sms': 'application/x-sms-rom',
    '.snd': 'audio/basic',
    '.so': 'application/x-sharedlib',
    '.spc': 'application/x-pkcs7-certificates',
    '.spd': 'application/x-font-speedo',
    '.spec': 'text/x-rpm-spec',
    '.spl': 'application/x-shockwave-flash',
    '.spm': 'application/x-source-rpm',
    '.spx': 'audio/x-speex',
    '.sql': 'text/x-sql',
    '.sr2': 'image/x-sony-sr2',
    '.src': 'application/x-wais-source',
    '.src.rpm': 'application/x-source-rpm',
    '.srf': 'image/x-sony-srf',
    '.srt': 'application/x-subrip',
    '.ss': 'text/x-scheme',
    '.ssa': 'text/x-ssa',
    '.stc': 'application/vnd.sun.xml.calc.template',
    '.std': 'application/vnd.sun.xml.draw.template',
    '.sti': 'application/vnd.sun.xml.impress.template',
    '.stm': 'audio/x-stm',
    '.stw': 'application/vnd.sun.xml.writer.template',
    '.sty': 'text/x-tex',
    '.sub': 'text/x-subviewer',
    '.sun': 'image/x-sun-raster',
    '.sv': 'text/x-svsrc',
    '.sv4cpio': 'application/x-sv4cpio',
    '.sv4crc': 'application/x-sv4crc',
    '.svg': 'image/svg+xml',
    '.svgz': 'image/svg+xml-compressed',
    '.svh': 'text/x-svhdr',
    '.swf': 'application/x-shockwave-flash',
    '.swm': 'application/x-ms-wim',
    '.sxc': 'application/vnd.sun.xml.calc',
    '.sxd': 'application/vnd.sun.xml.draw',
    '.sxg': 'application/vnd.sun.xml.writer.global',
    '.sxi': 'application/vnd.sun.xml.impress',
    '.sxm': 'application/vnd.sun.xml.math',
    '.sxw': 'application/vnd.sun.xml.writer',
    '.sylk': 'text/spreadsheet',
    '.t': 'text/troff',
    '.t2t': 'text/x-txt2tags',
    '.tar': 'application/x-tar',
    '.tar.bz': 'application/x-bzip-compressed-tar',
    '.tar.bz2': 'application/x-bzip-compressed-tar',
    '.tar.gz': 'application/x-compressed-tar',
    '.tar.lrz': 'application/x-lrzip-compressed-tar',
    '.tar.lzma': 'application/x-lzma-compressed-tar',
    '.tar.lzo': 'application/x-tzo',
    '.tar.xz': 'application/x-xz-compressed-tar',
    '.tar.z': 'application/x-tarz',
    '.taz': 'application/x-tarz',
    '.tb2': 'application/x-bzip-compressed-tar',
    '.tbz': 'application/x-bzip-compressed-tar',
    '.tbz2': 'application/x-bzip-compressed-tar',
    '.tcl': 'text/x-tcl',
    '.tex': 'text/x-tex',
    '.texi': 'text/x-texinfo',
    '.texinfo': 'text/x-texinfo',
    '.tga': 'image/x-tga',
    '.tgz': 'application/x-compressed-tar',
    '.theme': 'application/x-theme',
    '.themepack': 'application/x-windows-themepack',
    '.tif': 'image/tiff',
    '.tiff': 'image/tiff',
    '.tk': 'text/x-tcl',
    '.tlrz': 'application/x-lrzip-compressed-tar',
    '.tlz': 'application/x-lzma-compressed-tar',
    '.tnef': 'application/vnd.ms-tnef',
    '.tnf': 'application/vnd.ms-tnef',
    '.toc': 'application/x-cdrdao-toc',
    '.torrent': 'application/x-bittorrent',
    '.tpic': 'image/x-tga',
    '.tr': 'text/troff',
    '.ts': 'video/mp2t',
    '.tsv': 'text/tab-separated-values',
    '.tta': 'audio/x-tta',
    '.ttc': 'application/x-font-ttf',
    '.ttf': 'application/x-font-ttf',
    '.ttx': 'application/x-font-ttx',
    '.txt': 'text/plain',
    '.txz': 'application/x-xz-compressed-tar',
    '.tzo': 'application/x-tzo',
    '.ufraw': 'application/x-ufraw',
    '.ui': 'application/x-gtk-builder',
    '.uil': 'text/x-uil',
    '.ult': 'audio/x-mod',
    '.uni': 'audio/x-mod',
    '.url': 'application/x-mswinurl',
    '.ustar': 'application/x-ustar',
    '.uue': 'text/x-uuencode',
    '.v': 'text/x-verilog',
    '.vala': 'text/x-vala',
    '.vapi': 'text/x-vala',
    '.vcard': 'text/vcard',
    '.vcf': 'text/vcard',
    '.vcs': 'text/calendar',
    '.vct': 'text/vcard',
    '.vda': 'image/x-tga',
    '.vhd': 'text/x-vhdl',
    '.vhdl': 'text/x-vhdl',
    '.viv': 'video/vivo',
    '.vivo': 'video/vivo',
    '.vlc': 'audio/x-mpegurl',
    '.vob': 'video/mpeg',
    '.voc': 'audio/x-voc',
    '.vor': 'application/vnd.stardivision.writer',
    '.vrm': 'model/vrml',
    '.vrml': 'model/vrml',
    '.vsd': 'application/vnd.visio',
    '.vss': 'application/vnd.visio',
    '.vst': 'image/x-tga',
    '.vsw': 'application/vnd.visio',
    '.vtt': 'text/vtt',
    '.w2p': 'application/w2p',
    '.wav': 'audio/x-wav',
    '.wax': 'audio/x-ms-asx',
    '.wb1': 'application/x-quattropro',
    '.wb2': 'application/x-quattropro',
    '.wb3': 'application/x-quattropro',
    '.wbmp': 'image/vnd.wap.wbmp',
    '.wcm': 'application/vnd.ms-works',
    '.wdb': 'application/vnd.ms-works',
    '.webm': 'video/webm',
    '.wim': 'application/x-ms-wim',
    '.wk1': 'application/vnd.lotus-1-2-3',
    '.wk3': 'application/vnd.lotus-1-2-3',
    '.wk4': 'application/vnd.lotus-1-2-3',
    '.wks': 'application/vnd.ms-works',
    '.wma': 'audio/x-ms-wma',
    '.wmf': 'image/x-wmf',
    '.wml': 'text/vnd.wap.wml',
    '.wmls': 'text/vnd.wap.wmlscript',
    '.wmv': 'video/x-ms-wmv',
    '.wmx': 'audio/x-ms-asx',
    '.woff': 'application/font-woff',
    '.wp': 'application/vnd.wordperfect',
    '.wp4': 'application/vnd.wordperfect',
    '.wp5': 'application/vnd.wordperfect',
    '.wp6': 'application/vnd.wordperfect',
    '.wpd': 'application/vnd.wordperfect',
    '.wpg': 'application/x-wpg',
    '.wpl': 'application/vnd.ms-wpl',
    '.wpp': 'application/vnd.wordperfect',
    '.wps': 'application/vnd.ms-works',
    '.wri': 'application/x-mswrite',
    '.wrl': 'model/vrml',
    '.wsgi': 'text/x-python',
    '.wv': 'audio/x-wavpack',
    '.wvc': 'audio/x-wavpack-correction',
    '.wvp': 'audio/x-wavpack',
    '.wvx': 'audio/x-ms-asx',
    '.wwf': 'application/x-wwf',
    '.x3f': 'image/x-sigma-x3f',
    '.xac': 'application/x-gnucash',
    '.xbel': 'application/x-xbel',
    '.xbl': 'application/xml',
    '.xbm': 'image/x-xbitmap',
    '.xcf': 'image/x-xcf',
    '.xcf.bz2': 'image/x-compressed-xcf',
    '.xcf.gz': 'image/x-compressed-xcf',
    '.xhtml': 'application/xhtml+xml',
    '.xi': 'audio/x-xi',
    '.xla': 'application/vnd.ms-excel',
    '.xlam': 'application/vnd.ms-excel.addin.macroenabled.12',
    '.xlc': 'application/vnd.ms-excel',
    '.xld': 'application/vnd.ms-excel',
    '.xlf': 'application/x-xliff',
    '.xliff': 'application/x-xliff',
    '.xll': 'application/vnd.ms-excel',
    '.xlm': 'application/vnd.ms-excel',
    '.xlr': 'application/vnd.ms-works',
    '.xls': 'application/vnd.ms-excel',
    '.xlsb': 'application/vnd.ms-excel.sheet.binary.macroenabled.12',
    '.xlsm': 'application/vnd.ms-excel.sheet.macroenabled.12',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xlt': 'application/vnd.ms-excel',
    '.xltm': 'application/vnd.ms-excel.template.macroenabled.12',
    '.xltx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
    '.xlw': 'application/vnd.ms-excel',
    '.xm': 'audio/x-xm',
    '.xmf': 'audio/x-xmf',
    '.xmi': 'text/x-xmi',
    '.xml': 'application/xml',
    '.xpi': 'application/x-xpinstall',
    '.xpm': 'image/x-xpixmap',
    '.xps': 'application/oxps',
    '.xsd': 'application/xml',
    '.xsl': 'application/xslt+xml',
    '.xslfo': 'text/x-xslfo',
    '.xslt': 'application/xslt+xml',
    '.xspf': 'application/xspf+xml',
    '.xul': 'application/vnd.mozilla.xul+xml',
    '.xwd': 'image/x-xwindowdump',
    '.xyz': 'chemical/x-pdb',
    '.xz': 'application/x-xz',
    '.yaml': 'application/x-yaml',
    '.yml': 'application/x-yaml',
    '.z': 'application/x-compress',
    '.zabw': 'application/x-abiword',
    '.zip': 'application/zip',
    '.zoo': 'application/x-zoo',
}


def contenttype(filename, default='text/plain'):
    """
    Returns the Content-Type string matching extension of the given filename.
    """

    i = filename.rfind('.')
    if i >= 0:
        default = CONTENT_TYPE.get(filename[i:].lower(), default)
        j = filename.rfind('.', 0, i)
        if j >= 0:
            default = CONTENT_TYPE.get(filename[j:].lower(), default)
    if default.startswith('text/'):
        default += '; charset=utf-8'
    return default

########NEW FILE########
__FILENAME__ = custom_import
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import __builtin__
import os
import re
import sys
import threading
import traceback
from gluino import current

NATIVE_IMPORTER = __builtin__.__import__
INVALID_MODULES = set(('', 'gluino', 'applications', 'custom_import'))

# backward compatibility API


def custom_import_install():
    if __builtin__.__import__ == NATIVE_IMPORTER:
        INVALID_MODULES.update(sys.modules.keys())
        __builtin__.__import__ = custom_importer


def track_changes(track=True):
    assert track in (True, False), "must be True or False"
    current.request._custom_import_track_changes = track


def is_tracking_changes():
    return current.request._custom_import_track_changes


class CustomImportException(ImportError):
    pass


def custom_importer(name, globals=None, locals=None, fromlist=None, level=-1):
    """
    The web2py custom importer. Like the standard Python importer but it
    tries to transform import statements as something like
    "import applications.app_name.modules.x".
    If the import failed, fall back on naive_importer
    """

    globals = globals or {}
    locals = locals or {}
    fromlist = fromlist or []

    try:
        if current.request._custom_import_track_changes:
            base_importer = TRACK_IMPORTER
        else:
            base_importer = NATIVE_IMPORTER
    except:  # there is no current.request (should never happen)
        base_importer = NATIVE_IMPORTER

    # if not relative and not from applications:
    if hasattr(current, 'request') \
            and level <= 0 \
            and not name.split('.')[0] in INVALID_MODULES \
            and isinstance(globals, dict):
        import_tb = None
        try:
            try:
                oname = name if not name.startswith('.') else '.'+name
                return NATIVE_IMPORTER(oname, globals, locals, fromlist, level)
            except ImportError:
                items = current.request.folder.split(os.path.sep)
                if not items[-1]:
                    items = items[:-1]
                modules_prefix = '.'.join(items[-2:]) + '.modules'
                if not fromlist:
                    # import like "import x" or "import x.y"
                    result = None
                    for itemname in name.split("."):
                        new_mod = base_importer(
                            modules_prefix, globals, locals, [itemname], level)
                        try:
                            result = result or new_mod.__dict__[itemname]
                        except KeyError, e:
                            raise ImportError, 'Cannot import module %s' % str(e)
                        modules_prefix += "." + itemname
                    return result
                else:
                    # import like "from x import a, b, ..."
                    pname = modules_prefix + "." + name
                    return base_importer(pname, globals, locals, fromlist, level)
        except ImportError, e1:
            import_tb = sys.exc_info()[2]
            try:
                return NATIVE_IMPORTER(name, globals, locals, fromlist, level)
            except ImportError, e3:
                raise ImportError, e1, import_tb  # there an import error in the module
        except Exception, e2:
            raise e2  # there is an error in the module
        finally:
            if import_tb:
                import_tb = None

    return NATIVE_IMPORTER(name, globals, locals, fromlist, level)


class TrackImporter(object):
    """
    An importer tracking the date of the module files and reloading them when
    they have changed.
    """

    THREAD_LOCAL = threading.local()
    PACKAGE_PATH_SUFFIX = os.path.sep + "__init__.py"

    def __init__(self):
        self._import_dates = {}  # Import dates of the files of the modules

    def __call__(self, name, globals=None, locals=None, fromlist=None, level=-1):
        """
        The import method itself.
        """
        globals = globals or {}
        locals = locals or {}
        fromlist = fromlist or []
        if not hasattr(self.THREAD_LOCAL, '_modules_loaded'):
            self.THREAD_LOCAL._modules_loaded = set()
        try:
            # Check the date and reload if needed:
            self._update_dates(name, globals, locals, fromlist, level)
            # Try to load the module and update the dates if it works:
            result = NATIVE_IMPORTER(name, globals, locals, fromlist, level)
            # Module maybe loaded for the 1st time so we need to set the date
            self._update_dates(name, globals, locals, fromlist, level)
            return result
        except Exception, e:
            raise  # Don't hide something that went wrong

    def _update_dates(self, name, globals, locals, fromlist, level):
        """
        Update all the dates associated to the statement import. A single
        import statement may import many modules.
        """

        self._reload_check(name, globals, locals, level)
        for fromlist_name in fromlist or []:
            pname = "%s.%s" % (name, fromlist_name)
            self._reload_check(pname, globals, locals, level)

    def _reload_check(self, name, globals, locals, level):
        """
        Update the date associated to the module and reload the module if
        the file has changed.
        """
        module = sys.modules.get(name)
        file = self._get_module_file(module)
        if file:
            date = self._import_dates.get(file)
            new_date = None
            reload_mod = False
            mod_to_pack = False  # Module turning into a package? (special case)
            try:
                new_date = os.path.getmtime(file)
            except:
                self._import_dates.pop(file, None)  # Clean up
                # Handle module changing in package and
                #package changing in module:
                if file.endswith(".py"):
                    # Get path without file ext:
                    file = os.path.splitext(file)[0]
                    reload_mod = os.path.isdir(file) \
                        and os.path.isfile(file + self.PACKAGE_PATH_SUFFIX)
                    mod_to_pack = reload_mod
                else:  # Package turning into module?
                    file += ".py"
                    reload_mod = os.path.isfile(file)
                if reload_mod:
                    new_date = os.path.getmtime(file)  # Refresh file date
            if reload_mod or not date or new_date > date:
                self._import_dates[file] = new_date
            if reload_mod or (date and new_date > date):
                if module not in self.THREAD_LOCAL._modules_loaded:
                    if mod_to_pack:
                        # Module turning into a package:
                        mod_name = module.__name__
                        del sys.modules[mod_name]  # Delete the module
                        # Reload the module:
                        NATIVE_IMPORTER(mod_name, globals, locals, [], level)
                    else:
                        reload(module)
                        self.THREAD_LOCAL._modules_loaded.add(module)

    def _get_module_file(self, module):
        """
        Get the absolute path file associated to the module or None.
        """
        file = getattr(module, "__file__", None)
        if file:
            # Make path absolute if not:
            file = os.path.splitext(file)[0] + ".py"  # Change .pyc for .py
            if file.endswith(self.PACKAGE_PATH_SUFFIX):
                file = os.path.dirname(file)  # Track dir for packages
        return file

TRACK_IMPORTER = TrackImporter()

########NEW FILE########
__FILENAME__ = dal
#!/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Thanks to
    * Niall Sweeny <niall.sweeny@fonjax.com> for MS SQL support
    * Marcel Leuthi <mluethi@mlsystems.ch> for Oracle support
    * Denes
    * Chris Clark
    * clach05
    * Denes Lengyel
    * and many others who have contributed to current and previous versions

This file contains the DAL support for many relational databases,
including:
- SQLite & SpatiaLite
- MySQL
- Postgres
- Firebird
- Oracle
- MS SQL
- DB2
- Interbase
- Ingres
- Informix (9+ and SE)
- SapDB (experimental)
- Cubrid (experimental)
- CouchDB (experimental)
- MongoDB (in progress)
- Google:nosql
- Google:sql
- Teradata
- IMAP (experimental)

Example of usage:

>>> # from dal import DAL, Field

### create DAL connection (and create DB if it doesn't exist)
>>> db = DAL(('sqlite://storage.sqlite','mysql://a:b@localhost/x'),
... folder=None)

### define a table 'person' (create/alter as necessary)
>>> person = db.define_table('person',Field('name','string'))

### insert a record
>>> id = person.insert(name='James')

### retrieve it by id
>>> james = person(id)

### retrieve it by name
>>> james = person(name='James')

### retrieve it by arbitrary query
>>> query = (person.name=='James') & (person.name.startswith('J'))
>>> james = db(query).select(person.ALL)[0]

### update one record
>>> james.update_record(name='Jim')
<Row {'id': 1, 'name': 'Jim'}>

### update multiple records by query
>>> db(person.name.like('J%')).update(name='James')
1

### delete records by query
>>> db(person.name.lower() == 'jim').delete()
0

### retrieve multiple records (rows)
>>> people = db(person).select(orderby=person.name,
... groupby=person.name, limitby=(0,100))

### further filter them
>>> james = people.find(lambda row: row.name == 'James').first()
>>> print james.id, james.name
1 James

### check aggregates
>>> counter = person.id.count()
>>> print db(person).select(counter).first()(counter)
1

### delete one record
>>> james.delete_record()
1

### delete (drop) entire database table
>>> person.drop()

Supported field types:
id string text boolean integer double decimal password upload
blob time date datetime

Supported DAL URI strings:
'sqlite://test.db'
'spatialite://test.db'
'sqlite:memory'
'spatialite:memory'
'jdbc:sqlite://test.db'
'mysql://root:none@localhost/test'
'postgres://mdipierro:password@localhost/test'
'postgres:psycopg2://mdipierro:password@localhost/test'
'postgres:pg8000://mdipierro:password@localhost/test'
'jdbc:postgres://mdipierro:none@localhost/test'
'mssql://web2py:none@A64X2/web2py_test'
'mssql2://web2py:none@A64X2/web2py_test' # alternate mappings
'oracle://username:password@database'
'firebird://user:password@server:3050/database'
'db2://DSN=dsn;UID=user;PWD=pass'
'firebird://username:password@hostname/database'
'firebird_embedded://username:password@c://path'
'informix://user:password@server:3050/database'
'informixu://user:password@server:3050/database' # unicode informix
'ingres://database'  # or use an ODBC connection string, e.g. 'ingres://dsn=dsn_name'
'google:datastore' # for google app engine datastore
'google:sql' # for google app engine with sql (mysql compatible)
'teradata://DSN=dsn;UID=user;PWD=pass; DATABASE=database' # experimental
'imap://user:password@server:port' # experimental
'mongodb://user:password@server:port/database' # experimental

For more info:
help(DAL)
help(Field)
"""

###################################################################################
# this file only exposes DAL and Field
###################################################################################

__all__ = ['DAL', 'Field']

DEFAULTLENGTH = {'string':512,
                 'password':512,
                 'upload':512,
                 'text':2**15,
                 'blob':2**31}
TIMINGSSIZE = 100
SPATIALLIBS = {
    'Windows':'libspatialite',
    'Linux':'libspatialite.so',
    'Darwin':'libspatialite.dylib'
    }
DEFAULT_URI = 'sqlite://dummy.db'

import re
import sys
import locale
import os
import types
import datetime
import threading
import time
import csv
import cgi
import copy
import socket
import logging
import base64
import shutil
import marshal
import decimal
import struct
import urllib
import hashlib
import uuid
import glob
import traceback
import platform

PYTHON_VERSION = sys.version_info[0]
if PYTHON_VERSION == 2:
    import cPickle as pickle
    import cStringIO as StringIO
    import copy_reg as copyreg
    hashlib_md5 = hashlib.md5
    bytes, unicode = str, unicode
else:
    import pickle
    from io import StringIO as StringIO
    import copyreg
    long = int
    hashlib_md5 = lambda s: hashlib.md5(bytes(s,'utf8'))
    bytes, unicode = bytes, str

CALLABLETYPES = (types.LambdaType, types.FunctionType,
                 types.BuiltinFunctionType,
                 types.MethodType, types.BuiltinMethodType)

TABLE_ARGS = set(
    ('migrate','primarykey','fake_migrate','format','redefine',
     'singular','plural','trigger_name','sequence_name',
     'common_filter','polymodel','table_class','on_define','actual_name'))

SELECT_ARGS = set(
    ('orderby', 'groupby', 'limitby','required', 'cache', 'left',
     'distinct', 'having', 'join','for_update', 'processor','cacheable', 'orderby_on_limitby'))

ogetattr = object.__getattribute__
osetattr = object.__setattr__
exists = os.path.exists
pjoin = os.path.join

###################################################################################
# following checks allow the use of dal without web2py, as a standalone module
###################################################################################
try:
    from utils import web2py_uuid
except (ImportError, SystemError):
    import uuid
    def web2py_uuid(): return str(uuid.uuid4())

try:
    import portalocker
    have_portalocker = True
except ImportError:
    have_portalocker = False

try:
    import serializers
    have_serializers = True
except ImportError:
    have_serializers = False
    try:
        import json as simplejson
    except ImportError:
        try:
            import gluino.contrib.simplejson as simplejson
        except ImportError:
            simplejson = None

try:
    import validators
    have_validators = True
except (ImportError, SyntaxError):
    have_validators = False

LOGGER = logging.getLogger("web2py.dal")
DEFAULT = lambda:0

GLOBAL_LOCKER = threading.RLock()
THREAD_LOCAL = threading.local()

# internal representation of tables with field
#  <table>.<field>, tables and fields may only be [a-zA-Z0-9_]

REGEX_TYPE = re.compile('^([\w\_\:]+)')
REGEX_DBNAME = re.compile('^(\w+)(\:\w+)*')
REGEX_W = re.compile('^\w+$')
REGEX_TABLE_DOT_FIELD = re.compile('^(\w+)\.(\w+)$')
REGEX_UPLOAD_PATTERN = re.compile('(?P<table>[\w\-]+)\.(?P<field>[\w\-]+)\.(?P<uuidkey>[\w\-]+)\.(?P<name>\w+)\.\w+$')
REGEX_CLEANUP_FN = re.compile('[\'"\s;]+')
REGEX_UNPACK = re.compile('(?<!\|)\|(?!\|)')
REGEX_PYTHON_KEYWORDS = re.compile('^(and|del|from|not|while|as|elif|global|or|with|assert|else|if|pass|yield|break|except|import|print|class|exec|in|raise|continue|finally|is|return|def|for|lambda|try)$')
REGEX_SELECT_AS_PARSER = re.compile("\s+AS\s+(\S+)")
REGEX_CONST_STRING = re.compile('(\"[^\"]*?\")|(\'[^\']*?\')')
REGEX_SEARCH_PATTERN = re.compile('^{[^\.]+\.[^\.]+(\.(lt|gt|le|ge|eq|ne|contains|startswith|year|month|day|hour|minute|second))?(\.not)?}$')
REGEX_SQUARE_BRACKETS = re.compile('^.+\[.+\]$')
REGEX_STORE_PATTERN = re.compile('\.(?P<e>\w{1,5})$')
REGEX_QUOTES = re.compile("'[^']*'")
REGEX_ALPHANUMERIC = re.compile('^[0-9a-zA-Z]\w*$')
REGEX_PASSWORD = re.compile('\://([^:@]*)\:')
REGEX_NOPASSWD = re.compile('\/\/[\w\.\-]+[\:\/](.+)(?=@)') # was '(?<=[\:\/])([^:@/]+)(?=@.+)'

# list of drivers will be built on the fly
# and lists only what is available
DRIVERS = []

try:
    from new import classobj
    from google.appengine.ext import db as gae
    from google.appengine.api import namespace_manager, rdbms
    from google.appengine.api.datastore_types import Key  ### for belongs on ID
    from google.appengine.ext.db.polymodel import PolyModel
    DRIVERS.append('google')
except ImportError:
    pass

if not 'google' in DRIVERS:

    try:
        from pysqlite2 import dbapi2 as sqlite2
        DRIVERS.append('SQLite(sqlite2)')
    except ImportError:
        LOGGER.debug('no SQLite drivers pysqlite2.dbapi2')

    try:
        from sqlite3 import dbapi2 as sqlite3
        DRIVERS.append('SQLite(sqlite3)')
    except ImportError:
        LOGGER.debug('no SQLite drivers sqlite3')

    try:
        # first try contrib driver, then from site-packages (if installed)
        try:
            import contrib.pymysql as pymysql
            # monkeypatch pymysql because they havent fixed the bug:
            # https://github.com/petehunt/PyMySQL/issues/86
            pymysql.ESCAPE_REGEX = re.compile("'")
            pymysql.ESCAPE_MAP = {"'": "''"}
            # end monkeypatch
        except ImportError:
            import pymysql
        DRIVERS.append('MySQL(pymysql)')
    except ImportError:
        LOGGER.debug('no MySQL driver pymysql')

    try:
        import MySQLdb
        DRIVERS.append('MySQL(MySQLdb)')
    except ImportError:
        LOGGER.debug('no MySQL driver MySQLDB')


    try:
        import psycopg2
        from psycopg2.extensions import adapt as psycopg2_adapt
        DRIVERS.append('PostgreSQL(psycopg2)')
    except ImportError:
        LOGGER.debug('no PostgreSQL driver psycopg2')

    try:
        # first try contrib driver, then from site-packages (if installed)
        try:
            import contrib.pg8000.dbapi as pg8000
        except ImportError:
            import pg8000.dbapi as pg8000
        DRIVERS.append('PostgreSQL(pg8000)')
    except ImportError:
        LOGGER.debug('no PostgreSQL driver pg8000')

    try:
        import cx_Oracle
        DRIVERS.append('Oracle(cx_Oracle)')
    except ImportError:
        LOGGER.debug('no Oracle driver cx_Oracle')

    try:
        try:
            import pyodbc
        except ImportError:
            try:
                import contrib.pypyodbc as pyodbc
            except Exception, e:
                raise ImportError(str(e))
        DRIVERS.append('MSSQL(pyodbc)')
        DRIVERS.append('DB2(pyodbc)')
        DRIVERS.append('Teradata(pyodbc)')
        DRIVERS.append('Ingres(pyodbc)')
    except ImportError:
        LOGGER.debug('no MSSQL/DB2/Teradata/Ingres driver pyodbc')

    try:
        import Sybase
        DRIVERS.append('Sybase(Sybase)')
    except ImportError:
        LOGGER.debug('no Sybase driver')

    try:
        import kinterbasdb
        DRIVERS.append('Interbase(kinterbasdb)')
        DRIVERS.append('Firebird(kinterbasdb)')
    except ImportError:
        LOGGER.debug('no Firebird/Interbase driver kinterbasdb')

    try:
        import fdb
        DRIVERS.append('Firebird(fdb)')
    except ImportError:
        LOGGER.debug('no Firebird driver fdb')
#####
    try:
        import firebirdsql
        DRIVERS.append('Firebird(firebirdsql)')
    except ImportError:
        LOGGER.debug('no Firebird driver firebirdsql')

    try:
        import informixdb
        DRIVERS.append('Informix(informixdb)')
        LOGGER.warning('Informix support is experimental')
    except ImportError:
        LOGGER.debug('no Informix driver informixdb')

    try:
        import sapdb
        DRIVERS.append('SQL(sapdb)')
        LOGGER.warning('SAPDB support is experimental')
    except ImportError:
        LOGGER.debug('no SAP driver sapdb')

    try:
        import cubriddb
        DRIVERS.append('Cubrid(cubriddb)')
        LOGGER.warning('Cubrid support is experimental')
    except ImportError:
        LOGGER.debug('no Cubrid driver cubriddb')

    try:
        from com.ziclix.python.sql import zxJDBC
        import java.sql
        # Try sqlite jdbc driver from http://www.zentus.com/sqlitejdbc/
        from org.sqlite import JDBC # required by java.sql; ensure we have it
        zxJDBC_sqlite = java.sql.DriverManager
        DRIVERS.append('PostgreSQL(zxJDBC)')
        DRIVERS.append('SQLite(zxJDBC)')
        LOGGER.warning('zxJDBC support is experimental')
        is_jdbc = True
    except ImportError:
        LOGGER.debug('no SQLite/PostgreSQL driver zxJDBC')
        is_jdbc = False

    try:
        import couchdb
        DRIVERS.append('CouchDB(couchdb)')
    except ImportError:
        LOGGER.debug('no Couchdb driver couchdb')

    try:
        import pymongo
        DRIVERS.append('MongoDB(pymongo)')
    except:
        LOGGER.debug('no MongoDB driver pymongo')

    try:
        import imaplib
        DRIVERS.append('IMAP(imaplib)')
    except:
        LOGGER.debug('no IMAP driver imaplib')

PLURALIZE_RULES = [
    (re.compile('child$'), re.compile('child$'), 'children'),
    (re.compile('oot$'), re.compile('oot$'), 'eet'),
    (re.compile('ooth$'), re.compile('ooth$'), 'eeth'),
    (re.compile('l[eo]af$'), re.compile('l([eo])af$'), 'l\\1aves'),
    (re.compile('sis$'), re.compile('sis$'), 'ses'),
    (re.compile('man$'), re.compile('man$'), 'men'),
    (re.compile('ife$'), re.compile('ife$'), 'ives'),
    (re.compile('eau$'), re.compile('eau$'), 'eaux'),
    (re.compile('lf$'), re.compile('lf$'), 'lves'),
    (re.compile('[sxz]$'), re.compile('$'), 'es'),
    (re.compile('[^aeioudgkprt]h$'), re.compile('$'), 'es'),
    (re.compile('(qu|[^aeiou])y$'), re.compile('y$'), 'ies'),
    (re.compile('$'), re.compile('$'), 's'),
    ]

def pluralize(singular, rules=PLURALIZE_RULES):
    for line in rules:
        re_search, re_sub, replace = line
        plural = re_search.search(singular) and re_sub.sub(replace, singular)
        if plural: return plural

def hide_password(uri):
    if isinstance(uri,(list,tuple)):
        return [hide_password(item) for item in uri]
    return REGEX_NOPASSWD.sub('******',uri)

def OR(a,b):
    return a|b

def AND(a,b):
    return a&b

def IDENTITY(x): return x

def varquote_aux(name,quotestr='%s'):
    return name if REGEX_W.match(name) else quotestr % name

def quote_keyword(a,keyword='timestamp'):
    regex = re.compile('\.keyword(?=\w)')
    a = regex.sub('."%s"' % keyword,a)
    return a

if 'google' in DRIVERS:

    is_jdbc = False

    class GAEDecimalProperty(gae.Property):
        """
        GAE decimal implementation
        """
        data_type = decimal.Decimal

        def __init__(self, precision, scale, **kwargs):
            super(GAEDecimalProperty, self).__init__(self, **kwargs)
            d = '1.'
            for x in range(scale):
                d += '0'
            self.round = decimal.Decimal(d)

        def get_value_for_datastore(self, model_instance):
            value = super(GAEDecimalProperty, self)\
                .get_value_for_datastore(model_instance)
            if value is None or value == '':
                return None
            else:
                return str(value)

        def make_value_from_datastore(self, value):
            if value is None or value == '':
                return None
            else:
                return decimal.Decimal(value).quantize(self.round)

        def validate(self, value):
            value = super(GAEDecimalProperty, self).validate(value)
            if value is None or isinstance(value, decimal.Decimal):
                return value
            elif isinstance(value, basestring):
                return decimal.Decimal(value)
            raise gae.BadValueError("Property %s must be a Decimal or string."\
                                        % self.name)

###################################################################################
# class that handles connection pooling (all adapters are derived from this one)
###################################################################################

class ConnectionPool(object):

    POOLS = {}
    check_active_connection = True

    @staticmethod
    def set_folder(folder):
        THREAD_LOCAL.folder = folder

    # ## this allows gluon to commit/rollback all dbs in this thread

    def close(self,action='commit',really=True):
        if action:
            if callable(action):
                action(self)
            else:
                getattr(self, action)()
        # ## if you want pools, recycle this connection
        if self.pool_size:
            GLOBAL_LOCKER.acquire()
            pool = ConnectionPool.POOLS[self.uri]
            if len(pool) < self.pool_size:
                pool.append(self.connection)
                really = False
            GLOBAL_LOCKER.release()
        if really:
            self.close_connection()
        self.connection = None

    @staticmethod
    def close_all_instances(action):
        """ to close cleanly databases in a multithreaded environment """
        dbs = getattr(THREAD_LOCAL,'db_instances',{}).items()
        for db_uid, db_group in dbs:
            for db in db_group:
                if hasattr(db,'_adapter'):
                    db._adapter.close(action)
        getattr(THREAD_LOCAL,'db_instances',{}).clear()
        getattr(THREAD_LOCAL,'db_instances_zombie',{}).clear()
        if callable(action):
            action(None)
        return

    def find_or_make_work_folder(self):
        """ this actually does not make the folder. it has to be there """
        self.folder = getattr(THREAD_LOCAL,'folder','')

        # Creating the folder if it does not exist
        if False and self.folder and not exists(self.folder):
            os.mkdir(self.folder)

    def after_connection_hook(self):
        """hook for the after_connection parameter"""
        if callable(self._after_connection):
            self._after_connection(self)
        self.after_connection()

    def after_connection(self):
        """ this it is supposed to be overloaded by adapters"""
        pass

    def reconnect(self, f=None, cursor=True):
        """
        this function defines: self.connection and self.cursor
        (iff cursor is True)
        if self.pool_size>0 it will try pull the connection from the pool
        if the connection is not active (closed by db server) it will loop
        if not self.pool_size or no active connections in pool makes a new one
        """
        if getattr(self,'connection', None) != None:
            return
        if f is None:
            f = self.connector

        # if not hasattr(self, "driver") or self.driver is None:
        #     LOGGER.debug("Skipping connection since there's no driver")
        #     return

        if not self.pool_size:
            self.connection = f()
            self.cursor = cursor and self.connection.cursor()
        else:
            uri = self.uri
            POOLS = ConnectionPool.POOLS
            while True:
                GLOBAL_LOCKER.acquire()
                if not uri in POOLS:
                    POOLS[uri] = []
                if POOLS[uri]:
                    self.connection = POOLS[uri].pop()
                    GLOBAL_LOCKER.release()
                    self.cursor = cursor and self.connection.cursor()
                    try:
                        if self.cursor and self.check_active_connection:
                            self.execute('SELECT 1;')
                        break
                    except:
                        pass
                else:
                    GLOBAL_LOCKER.release()
                    self.connection = f()
                    self.cursor = cursor and self.connection.cursor()
                    break
        self.after_connection_hook()


###################################################################################
# this is a generic adapter that does nothing; all others are derived from this one
###################################################################################

class BaseAdapter(ConnectionPool):
    native_json = False
    driver = None
    driver_name = None
    drivers = () # list of drivers from which to pick
    connection = None
    commit_on_alter_table = False
    support_distributed_transaction = False
    uploads_in_blob = False
    can_select_for_update = True

    TRUE = 'T'
    FALSE = 'F'
    T_SEP = ' '
    QUOTE_TEMPLATE = '"%s"'

    types = {
        'boolean': 'CHAR(1)',
        'string': 'CHAR(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'CHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'CHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'INTEGER',
        'float':'DOUBLE',
        'double': 'DOUBLE',
        'decimal': 'DOUBLE',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        # the two below are only used when DAL(...bigint_id=True) and replace 'id','reference'
        'big-id': 'BIGINT PRIMARY KEY AUTOINCREMENT',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    def id_query(self, table):
        return table._id != None

    def adapt(self, obj):
        return "'%s'" % obj.replace("'", "''")

    def smart_adapt(self, obj):
        if isinstance(obj,(int,float)):
            return str(obj)
        return self.adapt(str(obj))

    def file_exists(self, filename):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        return exists(filename)

    def file_open(self, filename, mode='rb', lock=True):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        if have_portalocker and lock:
            fileobj = portalocker.LockedFile(filename,mode)
        else:
            fileobj = open(filename,mode)
        return fileobj

    def file_close(self, fileobj):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        if fileobj:
            fileobj.close()

    def file_delete(self, filename):
        os.unlink(filename)

    def find_driver(self,adapter_args,uri=None):
        if getattr(self,'driver',None) != None:
            return
        drivers_available = [driver for driver in self.drivers
                             if driver in globals()]
        if uri:
            items = uri.split('://',1)[0].split(':')
            request_driver = items[1] if len(items)>1 else None
        else:
            request_driver = None
        request_driver = request_driver or adapter_args.get('driver')
        if request_driver:
            if request_driver in drivers_available:
                self.driver_name = request_driver
                self.driver = globals().get(request_driver)
            else:
                raise RuntimeError("driver %s not available" % request_driver)
        elif drivers_available:
            self.driver_name = drivers_available[0]
            self.driver = globals().get(self.driver_name)
        else:
            raise RuntimeError("no driver available %s" % str(self.drivers))

    def __init__(self, db,uri,pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={},do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "None"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        class Dummy(object):
            lastrowid = 1
            def __getattr__(self, value):
                return lambda *a, **b: []
        self.connection = Dummy()
        self.cursor = Dummy()

    def sequence_name(self,tablename):
        return '%s_sequence' % tablename

    def trigger_name(self,tablename):
        return '%s_sequence' % tablename

    def varquote(self,name):
        return name

    def create_table(self, table,
                     migrate=True,
                     fake_migrate=False,
                     polymodel=None):
        db = table._db
        fields = []
        # PostGIS geo fields are added after the table has been created
        postcreation_fields = []
        sql_fields = {}
        sql_fields_aux = {}
        TFK = {}
        tablename = table._tablename
        sortable = 0
        types = self.types
        for field in table:
            sortable += 1
            field_name = field.name
            field_type = field.type
            if isinstance(field_type,SQLCustomType):
                ftype = field_type.native or field_type.type
            elif field_type.startswith('reference'):
                referenced = field_type[10:].strip()
                if referenced == '.':
                    referenced = tablename
                constraint_name = self.constraint_name(tablename, field_name)
                if not '.' in referenced \
                        and referenced != tablename \
                        and hasattr(table,'_primarykey'):
                    ftype = types['integer']
                else:
                    if hasattr(table,'_primarykey'):
                        rtablename,rfieldname = referenced.split('.')
                        rtable = db[rtablename]
                        rfield = rtable[rfieldname]
                        # must be PK reference or unique
                        if rfieldname in rtable._primarykey or \
                                rfield.unique:
                            ftype = types[rfield.type[:9]] % \
                                dict(length=rfield.length)
                            # multicolumn primary key reference?
                            if not rfield.unique and len(rtable._primarykey)>1:
                                # then it has to be a table level FK
                                if rtablename not in TFK:
                                    TFK[rtablename] = {}
                                TFK[rtablename][rfieldname] = field_name
                            else:
                                ftype = ftype + \
                                    types['reference FK'] % dict(
                                    constraint_name = constraint_name, # should be quoted
                                    foreign_key = '%s (%s)' % (rtablename,
                                                               rfieldname),
                                    table_name = tablename,
                                    field_name = field_name,
                                    on_delete_action=field.ondelete)
                    else:
                        # make a guess here for circular references
                        if referenced in db:
                            id_fieldname = db[referenced]._id.name
                        elif referenced == tablename:
                            id_fieldname = table._id.name
                        else: #make a guess
                            id_fieldname = 'id'
                        ftype = types[field_type[:9]] % dict(
                            index_name = field_name+'__idx',
                            field_name = field_name,
                            constraint_name = constraint_name,
                            foreign_key = '%s (%s)' % (referenced,
                                                       id_fieldname),
                            on_delete_action=field.ondelete)
            elif field_type.startswith('list:reference'):
                ftype = types[field_type[:14]]
            elif field_type.startswith('decimal'):
                precision, scale = map(int,field_type[8:-1].split(','))
                ftype = types[field_type[:7]] % \
                    dict(precision=precision,scale=scale)
            elif field_type.startswith('geo'):
                if not hasattr(self,'srid'):
                    raise RuntimeError('Adapter does not support geometry')
                srid = self.srid
                geotype, parms = field_type[:-1].split('(')
                if not geotype in types:
                    raise SyntaxError(
                        'Field: unknown field type: %s for %s' \
                        % (field_type, field_name))
                ftype = types[geotype]
                if self.dbengine == 'postgres' and geotype == 'geometry':
                    # parameters: schema, srid, dimension
                    dimension = 2 # GIS.dimension ???
                    parms = parms.split(',')
                    if len(parms) == 3:
                        schema, srid, dimension = parms
                    elif len(parms) == 2:
                        schema, srid = parms
                    else:
                        schema = parms[0]
                    ftype = "SELECT AddGeometryColumn ('%%(schema)s', '%%(tablename)s', '%%(fieldname)s', %%(srid)s, '%s', %%(dimension)s);" % types[geotype]
                    ftype = ftype % dict(schema=schema,
                                         tablename=tablename,
                                         fieldname=field_name, srid=srid,
                                         dimension=dimension)
                    postcreation_fields.append(ftype)
            elif not field_type in types:
                raise SyntaxError('Field: unknown field type: %s for %s' % \
                    (field_type, field_name))
            else:
                ftype = types[field_type]\
                     % dict(length=field.length)
            if not field_type.startswith('id') and \
                    not field_type.startswith('reference'):
                if field.notnull:
                    ftype += ' NOT NULL'
                else:
                    ftype += self.ALLOW_NULL()
                if field.unique:
                    ftype += ' UNIQUE'
                if field.custom_qualifier:
                    ftype += ' %s' % field.custom_qualifier

            # add to list of fields
            sql_fields[field_name] = dict(
                length=field.length,
                unique=field.unique,
                notnull=field.notnull,
                sortable=sortable,
                type=str(field_type),
                sql=ftype)

            if field.notnull and not field.default is None:
                # Caveat: sql_fields and sql_fields_aux
                # differ for default values.
                # sql_fields is used to trigger migrations and sql_fields_aux
                # is used for create tables.
                # The reason is that we do not want to trigger
                # a migration simply because a default value changes.
                not_null = self.NOT_NULL(field.default, field_type)
                ftype = ftype.replace('NOT NULL', not_null)
            sql_fields_aux[field_name] = dict(sql=ftype)
            # Postgres - PostGIS:
            # geometry fields are added after the table has been created, not now
            if not (self.dbengine == 'postgres' and \
                        field_type.startswith('geom')):
                fields.append('%s %s' % (field_name, ftype))
        other = ';'

        # backend-specific extensions to fields
        if self.dbengine == 'mysql':
            if not hasattr(table, "_primarykey"):
                fields.append('PRIMARY KEY(%s)' % table._id.name)
            other = ' ENGINE=InnoDB CHARACTER SET utf8;'

        fields = ',\n    '.join(fields)
        for rtablename in TFK:
            rfields = TFK[rtablename]
            pkeys = db[rtablename]._primarykey
            fkeys = [ rfields[k] for k in pkeys ]
            fields = fields + ',\n    ' + \
                types['reference TFK'] % dict(
                table_name = tablename,
                field_name=', '.join(fkeys),
                foreign_table = rtablename,
                foreign_key = ', '.join(pkeys),
                on_delete_action = field.ondelete)

        if getattr(table,'_primarykey',None):
            query = "CREATE TABLE %s(\n    %s,\n    %s) %s" % \
                (tablename, fields,
                 self.PRIMARY_KEY(', '.join(table._primarykey)),other)
        else:
            query = "CREATE TABLE %s(\n    %s\n)%s" % \
                (tablename, fields, other)

        if self.uri.startswith('sqlite:///') \
                or self.uri.startswith('spatialite:///'):
            path_encoding = sys.getfilesystemencoding() \
                or locale.getdefaultlocale()[1] or 'utf8'
            dbpath = self.uri[9:self.uri.rfind('/')]\
                .decode('utf8').encode(path_encoding)
        else:
            dbpath = self.folder

        if not migrate:
            return query
        elif self.uri.startswith('sqlite:memory')\
                or self.uri.startswith('spatialite:memory'):
            table._dbt = None
        elif isinstance(migrate, str):
            table._dbt = pjoin(dbpath, migrate)
        else:
            table._dbt = pjoin(
                dbpath, '%s_%s.table' % (table._db._uri_hash, tablename))

        if table._dbt:
            table._loggername = pjoin(dbpath, 'sql.log')
            logfile = self.file_open(table._loggername, 'a')
        else:
            logfile = None
        if not table._dbt or not self.file_exists(table._dbt):
            if table._dbt:
                logfile.write('timestamp: %s\n'
                               % datetime.datetime.today().isoformat())
                logfile.write(query + '\n')
            if not fake_migrate:
                self.create_sequence_and_triggers(query,table)
                table._db.commit()
                # Postgres geom fields are added now,
                # after the table has been created
                for query in postcreation_fields:
                    self.execute(query)
                    table._db.commit()
            if table._dbt:
                tfile = self.file_open(table._dbt, 'w')
                pickle.dump(sql_fields, tfile)
                self.file_close(tfile)
                if fake_migrate:
                    logfile.write('faked!\n')
                else:
                    logfile.write('success!\n')
        else:
            tfile = self.file_open(table._dbt, 'r')
            try:
                sql_fields_old = pickle.load(tfile)
            except EOFError:
                self.file_close(tfile)
                self.file_close(logfile)
                raise RuntimeError('File %s appears corrupted' % table._dbt)
            self.file_close(tfile)
            if sql_fields != sql_fields_old:
                self.migrate_table(table,
                                   sql_fields, sql_fields_old,
                                   sql_fields_aux, logfile,
                                   fake_migrate=fake_migrate)
        self.file_close(logfile)
        return query

    def migrate_table(
        self,
        table,
        sql_fields,
        sql_fields_old,
        sql_fields_aux,
        logfile,
        fake_migrate=False,
        ):
        db = table._db
        db._migrated.append(table._tablename)
        tablename = table._tablename
        def fix(item):
            k,v=item
            if not isinstance(v,dict):
                v=dict(type='unknown',sql=v)
            return k.lower(),v
        # make sure all field names are lower case to avoid
        # migrations because of case cahnge
        sql_fields = dict(map(fix,sql_fields.iteritems()))
        sql_fields_old = dict(map(fix,sql_fields_old.iteritems()))
        sql_fields_aux = dict(map(fix,sql_fields_aux.iteritems()))
        if db._debug:
            logging.debug('migrating %s to %s' % (sql_fields_old,sql_fields))

        keys = sql_fields.keys()
        for key in sql_fields_old:
            if not key in keys:
                keys.append(key)
        new_add = self.concat_add(tablename)

        metadata_change = False
        sql_fields_current = copy.copy(sql_fields_old)
        for key in keys:
            query = None
            if not key in sql_fields_old:
                sql_fields_current[key] = sql_fields[key]
                if self.dbengine in ('postgres',) and \
                   sql_fields[key]['type'].startswith('geometry'):
                    # 'sql' == ftype in sql
                    query = [ sql_fields[key]['sql'] ]
                else:
                    query = ['ALTER TABLE %s ADD %s %s;' % \
                         (tablename, key,
                          sql_fields_aux[key]['sql'].replace(', ', new_add))]
                metadata_change = True
            elif self.dbengine in ('sqlite', 'spatialite'):
                if key in sql_fields:
                    sql_fields_current[key] = sql_fields[key]
                metadata_change = True
            elif not key in sql_fields:
                del sql_fields_current[key]
                ftype = sql_fields_old[key]['type']
                if self.dbengine in ('postgres',) and ftype.startswith('geometry'):
                    geotype, parms = ftype[:-1].split('(')
                    schema = parms.split(',')[0]
                    query = [ "SELECT DropGeometryColumn ('%(schema)s', '%(table)s', '%(field)s');" %
                              dict(schema=schema, table=tablename, field=key,) ]
                elif self.dbengine in ('firebird',):
                    query = ['ALTER TABLE %s DROP %s;' % (tablename, key)]
                else:
                    query = ['ALTER TABLE %s DROP COLUMN %s;'
                             % (tablename, key)]
                metadata_change = True
            elif sql_fields[key]['sql'] != sql_fields_old[key]['sql'] \
                  and not (key in table.fields and
                           isinstance(table[key].type, SQLCustomType)) \
                  and not sql_fields[key]['type'].startswith('reference')\
                  and not sql_fields[key]['type'].startswith('double')\
                  and not sql_fields[key]['type'].startswith('id'):
                sql_fields_current[key] = sql_fields[key]
                t = tablename
                tt = sql_fields_aux[key]['sql'].replace(', ', new_add)
                if self.dbengine in ('firebird',):
                    drop_expr = 'ALTER TABLE %s DROP %s;'
                else:
                    drop_expr = 'ALTER TABLE %s DROP COLUMN %s;'
                key_tmp = key + '__tmp'
                query = ['ALTER TABLE %s ADD %s %s;' % (t, key_tmp, tt),
                         'UPDATE %s SET %s=%s;' % (t, key_tmp, key),
                         drop_expr % (t, key),
                         'ALTER TABLE %s ADD %s %s;' % (t, key, tt),
                         'UPDATE %s SET %s=%s;' % (t, key, key_tmp),
                         drop_expr % (t, key_tmp)]
                metadata_change = True
            elif sql_fields[key]['type'] != sql_fields_old[key]['type']:
                sql_fields_current[key] = sql_fields[key]
                metadata_change = True

            if query:
                logfile.write('timestamp: %s\n'
                              % datetime.datetime.today().isoformat())
                db['_lastsql'] = '\n'.join(query)
                for sub_query in query:
                    logfile.write(sub_query + '\n')
                    if fake_migrate:
                        if db._adapter.commit_on_alter_table:
                            self.save_dbt(table,sql_fields_current)
                        logfile.write('faked!\n')
                    else:
                        self.execute(sub_query)
                        # Caveat: mysql, oracle and firebird do not allow multiple alter table
                        # in one transaction so we must commit partial transactions and
                        # update table._dbt after alter table.
                        if db._adapter.commit_on_alter_table:
                            db.commit()
                            self.save_dbt(table,sql_fields_current)
                            logfile.write('success!\n')

            elif metadata_change:
                self.save_dbt(table,sql_fields_current)

        if metadata_change and not (query and db._adapter.commit_on_alter_table):
            db.commit()
            self.save_dbt(table,sql_fields_current)
            logfile.write('success!\n')

    def save_dbt(self,table, sql_fields_current):
        tfile = self.file_open(table._dbt, 'w')
        pickle.dump(sql_fields_current, tfile)
        self.file_close(tfile)

    def LOWER(self, first):
        return 'LOWER(%s)' % self.expand(first)

    def UPPER(self, first):
        return 'UPPER(%s)' % self.expand(first)

    def COUNT(self, first, distinct=None):
        return ('COUNT(%s)' if not distinct else 'COUNT(DISTINCT %s)') \
            % self.expand(first)

    def EXTRACT(self, first, what):
        return "EXTRACT(%s FROM %s)" % (what, self.expand(first))

    def EPOCH(self, first):
        return self.EXTRACT(first, 'epoch')

    def LENGTH(self, first):
        return "LENGTH(%s)" % self.expand(first)

    def AGGREGATE(self, first, what):
        return "%s(%s)" % (what, self.expand(first))

    def JOIN(self):
        return 'JOIN'

    def LEFT_JOIN(self):
        return 'LEFT JOIN'

    def RANDOM(self):
        return 'Random()'

    def NOT_NULL(self, default, field_type):
        return 'NOT NULL DEFAULT %s' % self.represent(default,field_type)

    def COALESCE(self, first, second):
        expressions = [self.expand(first)]+[self.expand(e) for e in second]
        return 'COALESCE(%s)' % ','.join(expressions)

    def COALESCE_ZERO(self, first):
        return 'COALESCE(%s,0)' % self.expand(first)

    def RAW(self, first):
        return first

    def ALLOW_NULL(self):
        return ''

    def SUBSTRING(self, field, parameters):
        return 'SUBSTR(%s,%s,%s)' % (self.expand(field), parameters[0], parameters[1])

    def PRIMARY_KEY(self, key):
        return 'PRIMARY KEY(%s)' % key

    def _drop(self, table, mode):
        return ['DROP TABLE %s;' % table]

    def drop(self, table, mode=''):
        db = table._db
        if table._dbt:
            logfile = self.file_open(table._loggername, 'a')
        queries = self._drop(table, mode)
        for query in queries:
            if table._dbt:
                logfile.write(query + '\n')
            self.execute(query)
        db.commit()
        del db[table._tablename]
        del db.tables[db.tables.index(table._tablename)]
        db._remove_references_to(table)
        if table._dbt:
            self.file_delete(table._dbt)
            logfile.write('success!\n')

    def _insert(self, table, fields):
        if fields:
            keys = ','.join(f.name for f, v in fields)
            values = ','.join(self.expand(v, f.type) for f, v in fields)
            return 'INSERT INTO %s(%s) VALUES (%s);' % (table, keys, values)
        else:
            return self._insert_empty(table)

    def _insert_empty(self, table):
        return 'INSERT INTO %s DEFAULT VALUES;' % table

    def insert(self, table, fields):
        query = self._insert(table,fields)
        try:
            self.execute(query)
        except Exception:
            e = sys.exc_info()[1]
            if hasattr(table,'_on_insert_error'):
                return table._on_insert_error(table,fields,e)
            raise e
        if hasattr(table,'_primarykey'):
            return dict([(k[0].name, k[1]) for k in fields \
                             if k[0].name in table._primarykey])
        id = self.lastrowid(table)
        if not isinstance(id,int):
            return id
        rid = Reference(id)
        (rid._table, rid._record) = (table, None)
        return rid

    def bulk_insert(self, table, items):
        return [self.insert(table,item) for item in items]

    def NOT(self, first):
        return '(NOT %s)' % self.expand(first)

    def AND(self, first, second):
        return '(%s AND %s)' % (self.expand(first), self.expand(second))

    def OR(self, first, second):
        return '(%s OR %s)' % (self.expand(first), self.expand(second))

    def BELONGS(self, first, second):
        if isinstance(second, str):
            return '(%s IN (%s))' % (self.expand(first), second[:-1])
        elif not second:
            return '(1=0)'
        items = ','.join(self.expand(item, first.type) for item in second)
        return '(%s IN (%s))' % (self.expand(first), items)

    def REGEXP(self, first, second):
        "regular expression operator"
        raise NotImplementedError

    def LIKE(self, first, second):
        "case sensitive like operator"
        raise NotImplementedError

    def ILIKE(self, first, second):
        "case in-sensitive like operator"
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand(second, 'string'))

    def STARTSWITH(self, first, second):
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand(second+'%', 'string'))

    def ENDSWITH(self, first, second):
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand('%'+second, 'string'))

    def CONTAINS(self,first,second,case_sensitive=False):
        if first.type in ('string','text', 'json'):
            if isinstance(second,Expression):
                second = Expression(None,self.CONCAT('%',Expression(
                            None,self.REPLACE(second,('%','%%'))),'%'))
            else:
                second = '%'+str(second).replace('%','%%')+'%'
        elif first.type.startswith('list:'):
            if isinstance(second,Expression):
                second = Expression(None,self.CONCAT(
                        '%|',Expression(None,self.REPLACE(
                                Expression(None,self.REPLACE(
                                        second,('%','%%'))),('|','||'))),'|%'))
            else:
                second = '%|'+str(second).replace('%','%%')\
                    .replace('|','||')+'|%'
        op = case_sensitive and self.LIKE or self.ILIKE
        return op(first,second)

    def EQ(self, first, second=None):
        if second is None:
            return '(%s IS NULL)' % self.expand(first)
        return '(%s = %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def NE(self, first, second=None):
        if second is None:
            return '(%s IS NOT NULL)' % self.expand(first)
        return '(%s <> %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def LT(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s < None" % first)
        return '(%s < %s)' % (self.expand(first),
                              self.expand(second,first.type))

    def LE(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s <= None" % first)
        return '(%s <= %s)' % (self.expand(first),
                               self.expand(second,first.type))

    def GT(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s > None" % first)
        return '(%s > %s)' % (self.expand(first),
                              self.expand(second,first.type))

    def GE(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s >= None" % first)
        return '(%s >= %s)' % (self.expand(first),
                               self.expand(second,first.type))

    def is_numerical_type(self, ftype):
        return ftype in ('integer','boolean','double','bigint') or \
            ftype.startswith('decimal')

    def REPLACE(self, first, (second, third)):
        return 'REPLACE(%s,%s,%s)' % (self.expand(first,'string'),
                                      self.expand(second,'string'),
                                      self.expand(third,'string'))

    def CONCAT(self, *items):
        return '(%s)' % ' || '.join(self.expand(x,'string') for x in items)

    def ADD(self, first, second):
        if self.is_numerical_type(first.type):
            return '(%s + %s)' % (self.expand(first),
                                  self.expand(second, first.type))
        else:
            return self.CONCAT(first, second)

    def SUB(self, first, second):
        return '(%s - %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MUL(self, first, second):
        return '(%s * %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def DIV(self, first, second):
        return '(%s / %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MOD(self, first, second):
        return '(%s %% %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def AS(self, first, second):
        return '%s AS %s' % (self.expand(first), second)

    def ON(self, first, second):
        if use_common_filters(second):
            second = self.common_filter(second,[first._tablename])
        return '%s ON %s' % (self.expand(first), self.expand(second))

    def INVERT(self, first):
        return '%s DESC' % self.expand(first)

    def COMMA(self, first, second):
        return '%s, %s' % (self.expand(first), self.expand(second))

    def expand(self, expression, field_type=None):
        if isinstance(expression, Field):
            out = '%s.%s' % (expression.table._tablename, expression.name)
            if field_type == 'string' and not expression.type in (
                'string','text','json','password'):
                out = 'CAST(%s AS %s)' % (out, self.types['text'])
            return out
        elif isinstance(expression, (Expression, Query)):
            first = expression.first
            second = expression.second
            op = expression.op
            optional_args = expression.optional_args or {}
            if not second is None:
                out = op(first, second, **optional_args)
            elif not first is None:
                out = op(first,**optional_args)
            elif isinstance(op, str):
                if op.endswith(';'):
                    op=op[:-1]
                out = '(%s)' % op
            else:
                out = op()
            return out
        elif field_type:
            return str(self.represent(expression,field_type))
        elif isinstance(expression,(list,tuple)):
            return ','.join(self.represent(item,field_type) \
                                for item in expression)
        elif isinstance(expression, bool):
            return '1' if expression else '0'
        else:
            return str(expression)

    def table_alias(self,name):
        return str(name if isinstance(name,Table) else self.db[name])

    def alias(self, table, alias):
        """
        Given a table object, makes a new table object
        with alias name.
        """
        other = copy.copy(table)
        other['_ot'] = other._ot or other._tablename
        other['ALL'] = SQLALL(other)
        other['_tablename'] = alias
        for fieldname in other.fields:
            other[fieldname] = copy.copy(other[fieldname])
            other[fieldname]._tablename = alias
            other[fieldname].tablename = alias
            other[fieldname].table = other
        table._db[alias] = other
        return other

    def _truncate(self, table, mode=''):
        tablename = table._tablename
        return ['TRUNCATE TABLE %s %s;' % (tablename, mode or '')]

    def truncate(self, table, mode= ' '):
        # Prepare functions "write_to_logfile" and "close_logfile"
        if table._dbt:
            logfile = self.file_open(table._loggername, 'a')
        else:
            class Logfile(object):
                def write(self, value):
                    pass
                def close(self):
                    pass
            logfile = Logfile()

        try:
            queries = table._db._adapter._truncate(table, mode)
            for query in queries:
                logfile.write(query + '\n')
                self.execute(query)
            table._db.commit()
            logfile.write('success!\n')
        finally:
            logfile.close()

    def _update(self, tablename, query, fields):
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename])
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_v = ','.join(['%s=%s' % (field.name,
                                     self.expand(value, field.type)) \
                              for (field, value) in fields])
        tablename = "%s" % self.db[tablename]
        return 'UPDATE %s SET %s%s;' % (tablename, sql_v, sql_w)

    def update(self, tablename, query, fields):
        sql = self._update(tablename, query, fields)
        try:
            self.execute(sql)
        except Exception:
            e = sys.exc_info()[1]
            table = self.db[tablename]
            if hasattr(table,'_on_update_error'):
                return table._on_update_error(table,query,fields,e)
            raise e
        try:
            return self.cursor.rowcount
        except:
            return None

    def _delete(self, tablename, query):
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename])
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        return 'DELETE FROM %s%s;' % (tablename, sql_w)

    def delete(self, tablename, query):
        sql = self._delete(tablename, query)
        ### special code to handle CASCADE in SQLite & SpatiaLite
        db = self.db
        table = db[tablename]
        if self.dbengine in ('sqlite', 'spatialite') and table._referenced_by:
            deleted = [x[table._id.name] for x in db(query).select(table._id)]
        ### end special code to handle CASCADE in SQLite & SpatiaLite
        self.execute(sql)
        try:
            counter = self.cursor.rowcount
        except:
            counter =  None
        ### special code to handle CASCADE in SQLite & SpatiaLite
        if self.dbengine in ('sqlite', 'spatialite') and counter:
            for field in table._referenced_by:
                if field.type=='reference '+table._tablename \
                        and field.ondelete=='CASCADE':
                    db(field.belongs(deleted)).delete()
        ### end special code to handle CASCADE in SQLite & SpatiaLite
        return counter

    def get_table(self, query):
        tablenames = self.tables(query)
        if len(tablenames)==1:
            return tablenames[0]
        elif len(tablenames)<1:
            raise RuntimeError("No table selected")
        else:
            raise RuntimeError("Too many tables selected")

    def expand_all(self, fields, tablenames):
        db = self.db
        new_fields = []
        append = new_fields.append
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item._table
            elif isinstance(item,str):
                if REGEX_TABLE_DOT_FIELD.match(item):
                    tablename,fieldname = item.split('.')
                    append(db[tablename][fieldname])
                else:
                    append(Expression(db,lambda item=item:item))
            else:
                append(item)
        # ## if no fields specified take them all from the requested tables
        if not new_fields:
            for table in tablenames:
                for field in db[table]:
                    append(field)
        return new_fields

    def _select(self, query, fields, attributes):
        tables = self.tables
        for key in set(attributes.keys())-SELECT_ARGS:
            raise SyntaxError('invalid select attribute: %s' % key)
        args_get = attributes.get
        tablenames = tables(query)
        tablenames_for_common_filters = tablenames
        for field in fields:
            if isinstance(field, basestring) \
                    and REGEX_TABLE_DOT_FIELD.match(field):
                tn,fn = field.split('.')
                field = self.db[tn][fn]
            for tablename in tables(field):
                if not tablename in tablenames:
                    tablenames.append(tablename)

        if len(tablenames) < 1:
            raise SyntaxError('Set: no tables selected')
        self._colnames = map(self.expand, fields)
        def geoexpand(field):
            if isinstance(field.type,str) and field.type.startswith('geometry'):
                field = field.st_astext()
            return self.expand(field)
        sql_f = ', '.join(map(geoexpand, fields))
        sql_o = ''
        sql_s = ''
        left = args_get('left', False)
        inner_join = args_get('join', False)
        distinct = args_get('distinct', False)
        groupby = args_get('groupby', False)
        orderby = args_get('orderby', False)
        having = args_get('having', False)
        limitby = args_get('limitby', False)
        orderby_on_limitby = args_get('orderby_on_limitby', True)
        for_update = args_get('for_update', False)
        if self.can_select_for_update is False and for_update is True:
            raise SyntaxError('invalid select attribute: for_update')
        if distinct is True:
            sql_s += 'DISTINCT'
        elif distinct:
            sql_s += 'DISTINCT ON (%s)' % distinct
        if inner_join:
            icommand = self.JOIN()
            if not isinstance(inner_join, (tuple, list)):
                inner_join = [inner_join]
            ijoint = [t._tablename for t in inner_join
                      if not isinstance(t,Expression)]
            ijoinon = [t for t in inner_join if isinstance(t, Expression)]
            itables_to_merge={} #issue 490
            [itables_to_merge.update(
                    dict.fromkeys(tables(t))) for t in ijoinon]
            ijoinont = [t.first._tablename for t in ijoinon]
            [itables_to_merge.pop(t) for t in ijoinont
             if t in itables_to_merge] #issue 490
            iimportant_tablenames = ijoint + ijoinont + itables_to_merge.keys()
            iexcluded = [t for t in tablenames
                         if not t in iimportant_tablenames]
        if left:
            join = attributes['left']
            command = self.LEFT_JOIN()
            if not isinstance(join, (tuple, list)):
                join = [join]
            joint = [t._tablename for t in join
                     if not isinstance(t, Expression)]
            joinon = [t for t in join if isinstance(t, Expression)]
            #patch join+left patch (solves problem with ordering in left joins)
            tables_to_merge={}
            [tables_to_merge.update(
                    dict.fromkeys(tables(t))) for t in joinon]
            joinont = [t.first._tablename for t in joinon]
            [tables_to_merge.pop(t) for t in joinont if t in tables_to_merge]
            tablenames_for_common_filters = [t for t in tablenames
                        if not t in joinont ]
            important_tablenames = joint + joinont + tables_to_merge.keys()
            excluded = [t for t in tablenames
                        if not t in important_tablenames ]
        else:
            excluded = tablenames

        if use_common_filters(query):
            query = self.common_filter(query,tablenames_for_common_filters)
        sql_w = ' WHERE ' + self.expand(query) if query else ''

        if inner_join and not left:
            sql_t = ', '.join([self.table_alias(t) for t in iexcluded + \
                                   itables_to_merge.keys()])
            for t in ijoinon:
                sql_t += ' %s %s' % (icommand, t)
        elif not inner_join and left:
            sql_t = ', '.join([self.table_alias(t) for t in excluded + \
                                   tables_to_merge.keys()])
            if joint:
                sql_t += ' %s %s' % (command,
                                     ','.join([self.table_alias(t) for t in joint]))
            for t in joinon:
                sql_t += ' %s %s' % (command, t)
        elif inner_join and left:
            all_tables_in_query = set(important_tablenames + \
                                      iimportant_tablenames + \
                                      tablenames)
            tables_in_joinon = set(joinont + ijoinont)
            tables_not_in_joinon = \
                all_tables_in_query.difference(tables_in_joinon)
            sql_t = ','.join([self.table_alias(t) for t in tables_not_in_joinon])
            for t in ijoinon:
                sql_t += ' %s %s' % (icommand, t)
            if joint:
                sql_t += ' %s %s' % (command,
                                     ','.join([self.table_alias(t) for t in joint]))
            for t in joinon:
                sql_t += ' %s %s' % (command, t)
        else:
            sql_t = ', '.join(self.table_alias(t) for t in tablenames)
        if groupby:
            if isinstance(groupby, (list, tuple)):
                groupby = xorify(groupby)
            sql_o += ' GROUP BY %s' % self.expand(groupby)
            if having:
                sql_o += ' HAVING %s' % attributes['having']
        if orderby:
            if isinstance(orderby, (list, tuple)):
                orderby = xorify(orderby)
            if str(orderby) == '<random>':
                sql_o += ' ORDER BY %s' % self.RANDOM()
            else:
                sql_o += ' ORDER BY %s' % self.expand(orderby)
        if limitby:
            if orderby_on_limitby and not orderby and tablenames:
                sql_o += ' ORDER BY %s' % ', '.join(['%s.%s'%(t,x) for t in tablenames for x in (hasattr(self.db[t],'_primarykey') and self.db[t]._primarykey or [self.db[t]._id.name])])
            # oracle does not support limitby
        sql = self.select_limitby(sql_s, sql_f, sql_t, sql_w, sql_o, limitby)
        if for_update and self.can_select_for_update is True:
            sql = sql.rstrip(';') + ' FOR UPDATE;'
        return sql

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' LIMIT %i OFFSET %i' % (lmax - lmin, lmin)
        return 'SELECT %s %s FROM %s%s%s;' % \
            (sql_s, sql_f, sql_t, sql_w, sql_o)

    def _fetchall(self):
        return self.cursor.fetchall()

    def _select_aux(self,sql,fields,attributes):
        args_get = attributes.get
        cache = args_get('cache',None)
        if not cache:
            self.execute(sql)
            rows = self._fetchall()
        else:
            (cache_model, time_expire) = cache
            key = self.uri + '/' + sql + '/rows'
            if len(key)>200: key = hashlib_md5(key).hexdigest()
            def _select_aux2():
                self.execute(sql)
                return self._fetchall()
            rows = cache_model(key,_select_aux2,time_expire)
        if isinstance(rows,tuple):
            rows = list(rows)
        limitby = args_get('limitby', None) or (0,)
        rows = self.rowslice(rows,limitby[0],None)
        processor = args_get('processor',self.parse)
        cacheable = args_get('cacheable',False)
        return processor(rows,fields,self._colnames,cacheable=cacheable)

    def select(self, query, fields, attributes):
        """
        Always returns a Rows object, possibly empty.
        """
        sql = self._select(query, fields, attributes)
        cache = attributes.get('cache', None)
        if cache and attributes.get('cacheable',False):
            del attributes['cache']
            (cache_model, time_expire) = cache
            key = self.uri + '/' + sql
            if len(key)>200: key = hashlib_md5(key).hexdigest()
            args = (sql,fields,attributes)
            return cache_model(
                key,
                lambda self=self,args=args:self._select_aux(*args),
                time_expire)
        else:
            return self._select_aux(sql,fields,attributes)

    def _count(self, query, distinct=None):
        tablenames = self.tables(query)
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, tablenames)
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_t = ','.join(self.table_alias(t) for t in tablenames)
        if distinct:
            if isinstance(distinct,(list, tuple)):
                distinct = xorify(distinct)
            sql_d = self.expand(distinct)
            return 'SELECT count(DISTINCT %s) FROM %s%s;' % \
                (sql_d, sql_t, sql_w)
        return 'SELECT count(*) FROM %s%s;' % (sql_t, sql_w)

    def count(self, query, distinct=None):
        self.execute(self._count(query, distinct))
        return self.cursor.fetchone()[0]

    def tables(self, *queries):
        tables = set()
        for query in queries:
            if isinstance(query, Field):
                tables.add(query.tablename)
            elif isinstance(query, (Expression, Query)):
                if not query.first is None:
                    tables = tables.union(self.tables(query.first))
                if not query.second is None:
                    tables = tables.union(self.tables(query.second))
        return list(tables)

    def commit(self):
        if self.connection: return self.connection.commit()

    def rollback(self):
        if self.connection: return self.connection.rollback()

    def close_connection(self):
        if self.connection: return self.connection.close()

    def distributed_transaction_begin(self, key):
        return

    def prepare(self, key):
        if self.connection: self.connection.prepare()

    def commit_prepared(self, key):
        if self.connection: self.connection.commit()

    def rollback_prepared(self, key):
        if self.connection: self.connection.rollback()

    def concat_add(self, tablename):
        return ', ADD '

    def constraint_name(self, table, fieldname):
        return '%s_%s__constraint' % (table,fieldname)

    def create_sequence_and_triggers(self, query, table, **args):
        self.execute(query)

    def log_execute(self, *a, **b):
        if not self.connection: return None
        command = a[0]
        if hasattr(self,'filter_sql_command'):
            command = self.filter_sql_command(command)
        if self.db._debug:
            LOGGER.debug('SQL: %s' % command)
        self.db._lastsql = command
        t0 = time.time()
        ret = self.cursor.execute(command, *a[1:], **b)
        self.db._timings.append((command,time.time()-t0))
        del self.db._timings[:-TIMINGSSIZE]
        return ret

    def execute(self, *a, **b):
        return self.log_execute(*a, **b)

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if isinstance(obj, CALLABLETYPES):
            obj = obj()
        if isinstance(fieldtype, SQLCustomType):
            value = fieldtype.encoder(obj)
            if fieldtype.type in ('string','text', 'json'):
                return self.adapt(value)
            return value
        if isinstance(obj, (Expression, Field)):
            return str(obj)
        if field_is_type('list:'):
            if not obj:
                obj = []
            elif not isinstance(obj, (list, tuple)):
                obj = [obj]
            if field_is_type('list:string'):
                obj = map(str,obj)
            else:
                obj = map(int,[o for o in obj if o != ''])
        # we don't want to bar_encode json objects
        if isinstance(obj, (list, tuple)) and (not fieldtype == "json"):
            obj = bar_encode(obj)
        if obj is None:
            return 'NULL'
        if obj == '' and not fieldtype[:2] in ['st', 'te', 'js', 'pa', 'up']:
            return 'NULL'
        r = self.represent_exceptions(obj, fieldtype)
        if not r is None:
            return r
        if fieldtype == 'boolean':
            if obj and not str(obj)[:1].upper() in '0F':
                return self.smart_adapt(self.TRUE)
            else:
                return self.smart_adapt(self.FALSE)
        if fieldtype == 'id' or fieldtype == 'integer':
            return str(long(obj))
        if field_is_type('decimal'):
            return str(obj)
        elif field_is_type('reference'): # reference
            if fieldtype.find('.')>0:
                return repr(obj)
            elif isinstance(obj, (Row, Reference)):
                return str(obj['id'])
            return str(long(obj))
        elif fieldtype == 'double':
            return repr(float(obj))
        if isinstance(obj, unicode):
            obj = obj.encode(self.db_codec)
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
        elif fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat(self.T_SEP)[:19]
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+' 00:00:00'
            else:
                obj = str(obj)
        elif fieldtype == 'time':
            if isinstance(obj, datetime.time):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
        elif fieldtype == 'json':
            if not self.native_json:
                if have_serializers:
                    obj = serializers.json(obj)
                elif simplejson:
                    obj = simplejson.dumps(obj)
                else:
                    raise RuntimeError("missing simplejson")
        if not isinstance(obj,bytes):
            obj = bytes(obj)
        try:
            obj.decode(self.db_codec)
        except:
            obj = obj.decode('latin1').encode(self.db_codec)
        return self.adapt(obj)

    def represent_exceptions(self, obj, fieldtype):
        return None

    def lastrowid(self, table):
        return None

    def rowslice(self, rows, minimum=0, maximum=None):
        """
        By default this function does nothing;
        overload when db does not do slicing.
        """
        return rows

    def parse_value(self, value, field_type, blob_decode=True):
        if field_type != 'blob' and isinstance(value, str):
            try:
                value = value.decode(self.db._db_codec)
            except Exception:
                pass
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if isinstance(field_type, SQLCustomType):
            value = field_type.decoder(value)
        if not isinstance(field_type, str) or value is None:
            return value
        elif field_type in ('string', 'text', 'password', 'upload', 'dict'):
            return value
        elif field_type.startswith('geo'):
            return value
        elif field_type == 'blob' and not blob_decode:
            return value
        else:
            key = REGEX_TYPE.match(field_type).group(0)
            return self.parsemap[key](value,field_type)

    def parse_reference(self, value, field_type):
        referee = field_type[10:].strip()
        if not '.' in referee:
            value = Reference(value)
            value._table, value._record = self.db[referee], None
        return value

    def parse_boolean(self, value, field_type):
        return value == self.TRUE or str(value)[:1].lower() == 't'

    def parse_date(self, value, field_type):
        if isinstance(value, datetime.datetime):
            return value.date()
        if not isinstance(value, (datetime.date,datetime.datetime)):
            (y, m, d) = map(int, str(value)[:10].strip().split('-'))
            value = datetime.date(y, m, d)
        return value

    def parse_time(self, value, field_type):
        if not isinstance(value, datetime.time):
            time_items = map(int,str(value)[:8].strip().split(':')[:3])
            if len(time_items) == 3:
                (h, mi, s) = time_items
            else:
                (h, mi, s) = time_items + [0]
            value = datetime.time(h, mi, s)
        return value

    def parse_datetime(self, value, field_type):
        if not isinstance(value, datetime.datetime):
            value = str(value)
            date_part,time_part,timezone = value[:10],value[11:19],value[19:]
            if '+' in timezone:
                ms,tz = timezone.split('+')
                h,m = tz.split(':')
                dt = datetime.timedelta(seconds=3600*int(h)+60*int(m))
            elif '-' in timezone:
                ms,tz = timezone.split('-')
                h,m = tz.split(':')
                dt = -datetime.timedelta(seconds=3600*int(h)+60*int(m))
            else:
                dt = None
            (y, m, d) = map(int,date_part.split('-'))
            time_parts = time_part and time_part.split(':')[:3] or (0,0,0)
            while len(time_parts)<3: time_parts.append(0)
            time_items = map(int,time_parts)
            (h, mi, s) = time_items
            value = datetime.datetime(y, m, d, h, mi, s)
            if dt:
                value = value + dt
        return value

    def parse_blob(self, value, field_type):
        return base64.b64decode(str(value))

    def parse_decimal(self, value, field_type):
        decimals = int(field_type[8:-1].split(',')[-1])
        if self.dbengine in ('sqlite', 'spatialite'):
            value = ('%.' + str(decimals) + 'f') % value
        if not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(value))
        return value

    def parse_list_integers(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_integer(value)
        return value

    def parse_list_references(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_integer(value)
        return [self.parse_reference(r, field_type[5:]) for r in value]

    def parse_list_strings(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_string(value)
        return value

    def parse_id(self, value, field_type):
        return long(value)

    def parse_integer(self, value, field_type):
        return long(value)

    def parse_double(self, value, field_type):
        return float(value)

    def parse_json(self, value, field_type):
        if not self.native_json:
            if not isinstance(value, basestring):
                raise RuntimeError('json data not a string')
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            if have_serializers:
                value = serializers.loads_json(value)
            elif simplejson:
                value = simplejson.loads(value)
            else:
                raise RuntimeError("missing simplejson")
        return value

    def build_parsemap(self):
        self.parsemap = {
            'id':self.parse_id,
            'integer':self.parse_integer,
            'bigint':self.parse_integer,
            'float':self.parse_double,
            'double':self.parse_double,
            'reference':self.parse_reference,
            'boolean':self.parse_boolean,
            'date':self.parse_date,
            'time':self.parse_time,
            'datetime':self.parse_datetime,
            'blob':self.parse_blob,
            'decimal':self.parse_decimal,
            'json':self.parse_json,
            'list:integer':self.parse_list_integers,
            'list:reference':self.parse_list_references,
            'list:string':self.parse_list_strings,
            }

    def parse(self, rows, fields, colnames, blob_decode=True,
              cacheable = False):
        self.build_parsemap()
        db = self.db
        virtualtables = []
        new_rows = []
        tmps = []
        for colname in colnames:
            if not REGEX_TABLE_DOT_FIELD.match(colname):
                tmps.append(None)
            else:
                (tablename, fieldname) = colname.split('.')
                table = db[tablename]
                field = table[fieldname]
                ft = field.type
                tmps.append((tablename,fieldname,table,field,ft))
        for (i,row) in enumerate(rows):
            new_row = Row()
            for (j,colname) in enumerate(colnames):
                value = row[j]
                tmp = tmps[j]
                if tmp:
                    (tablename,fieldname,table,field,ft) = tmp
                    if tablename in new_row:
                        colset = new_row[tablename]
                    else:
                        colset = new_row[tablename] = Row()
                        if tablename not in virtualtables:
                            virtualtables.append(tablename)
                    value = self.parse_value(value,ft,blob_decode)
                    if field.filter_out:
                        value = field.filter_out(value)
                    colset[fieldname] = value

                    # for backward compatibility
                    if ft=='id' and fieldname!='id' and \
                            not 'id' in table.fields:
                        colset['id'] = value

                    if ft == 'id' and not cacheable:
                        # temporary hack to deal with
                        # GoogleDatastoreAdapter
                        # references
                        if isinstance(self, GoogleDatastoreAdapter):
                            id = value.key().id_or_name()
                            colset[fieldname] = id
                            colset.gae_item = value
                        else:
                            id = value
                        colset.update_record = RecordUpdater(colset,table,id)
                        colset.delete_record = RecordDeleter(table,id)
                        for rfield in table._referenced_by:
                            referee_link = db._referee_name and \
                                db._referee_name % dict(
                                table=rfield.tablename,field=rfield.name)
                            if referee_link and not referee_link in colset:
                                colset[referee_link] = LazySet(rfield,id)
                else:
                    if not '_extra' in new_row:
                        new_row['_extra'] = Row()
                    new_row['_extra'][colname] = \
                        self.parse_value(value,
                                         fields[j].type,blob_decode)
                    new_column_name = \
                        REGEX_SELECT_AS_PARSER.search(colname)
                    if not new_column_name is None:
                        column_name = new_column_name.groups(0)
                        setattr(new_row,column_name[0],value)
            new_rows.append(new_row)
        rowsobj = Rows(db, new_rows, colnames, rawrows=rows)

        for tablename in virtualtables:
            ### new style virtual fields
            table = db[tablename]
            fields_virtual = [(f,v) for (f,v) in table.iteritems()
                              if isinstance(v,FieldVirtual)]
            fields_lazy = [(f,v) for (f,v) in table.iteritems()
                           if isinstance(v,FieldMethod)]
            if fields_virtual or fields_lazy:
                for row in rowsobj.records:
                    box = row[tablename]
                    for f,v in fields_virtual:
                        box[f] = v.f(row)
                    for f,v in fields_lazy:
                        box[f] = (v.handler or VirtualCommand)(v.f,row)

            ### old style virtual fields
            for item in table.virtualfields:
                try:
                    rowsobj = rowsobj.setvirtualfields(**{tablename:item})
                except (KeyError, AttributeError):
                    # to avoid breaking virtualfields when partial select
                    pass
        return rowsobj

    def common_filter(self, query, tablenames):
        tenant_fieldname = self.db._request_tenant

        for tablename in tablenames:
            table = self.db[tablename]

            # deal with user provided filters
            if table._common_filter != None:
                query = query & table._common_filter(query)

            # deal with multi_tenant filters
            if tenant_fieldname in table:
                default = table[tenant_fieldname].default
                if not default is None:
                    newquery = table[tenant_fieldname] == default
                    if query is None:
                        query = newquery
                    else:
                        query = query & newquery
        return query

    def CASE(self,query,t,f):
        def represent(x):
            types = {type(True):'boolean',type(0):'integer',type(1.0):'double'}
            if x is None: return 'NULL'
            elif isinstance(x,Expression): return str(x)
            else: return self.represent(x,types.get(type(x),'string'))
        return Expression(self.db,'CASE WHEN %s THEN %s ELSE %s END' % \
                              (self.expand(query),represent(t),represent(f)))

###################################################################################
# List of all the available adapters; they all extend BaseAdapter.
###################################################################################

class SQLiteAdapter(BaseAdapter):
    drivers = ('sqlite2','sqlite3')

    can_select_for_update = None    # support ourselves with BEGIN TRANSACTION

    def EXTRACT(self,field,what):
        return "web2py_extract('%s',%s)" % (what, self.expand(field))

    @staticmethod
    def web2py_extract(lookup, s):
        table = {
            'year': (0, 4),
            'month': (5, 7),
            'day': (8, 10),
            'hour': (11, 13),
            'minute': (14, 16),
            'second': (17, 19),
            }
        try:
            if lookup != 'epoch':
                (i, j) = table[lookup]
                return int(s[i:j])
            else:
                return time.mktime(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S').timetuple())
        except:
            return None

    @staticmethod
    def web2py_regexp(expression, item):
        return re.compile(expression).search(item) is not None

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "sqlite"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.pool_size = 0
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        path_encoding = sys.getfilesystemencoding() \
            or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('sqlite:memory'):
            dbpath = ':memory:'
        else:
            dbpath = uri.split('://',1)[1]
            if dbpath[0] != '/':
                if PYTHON_VERSION == 2:
                    dbpath = pjoin(
                        self.folder.decode(path_encoding).encode('utf8'), dbpath)
                else:
                    dbpath = pjoin(self.folder, dbpath)
        if not 'check_same_thread' in driver_args:
            driver_args['check_same_thread'] = False
        if not 'detect_types' in driver_args and do_connect:
            driver_args['detect_types'] = self.driver.PARSE_DECLTYPES
        def connector(dbpath=dbpath, driver_args=driver_args):
            return self.driver.Connection(dbpath, **driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.create_function('web2py_extract', 2,
                                        SQLiteAdapter.web2py_extract)
        self.connection.create_function("REGEXP", 2,
                                        SQLiteAdapter.web2py_regexp)

    def _truncate(self, table, mode=''):
        tablename = table._tablename
        return ['DELETE FROM %s;' % tablename,
                "DELETE FROM sqlite_sequence WHERE name='%s';" % tablename]

    def lastrowid(self, table):
        return self.cursor.lastrowid

    def REGEXP(self,first,second):
        return '(%s REGEXP %s)' % (self.expand(first),
                                   self.expand(second,'string'))

    def select(self, query, fields, attributes):
        """
        Simulate SELECT ... FOR UPDATE with BEGIN IMMEDIATE TRANSACTION.
        Note that the entire database, rather than one record, is locked
        (it will be locked eventually anyway by the following UPDATE).
        """
        if attributes.get('for_update', False) and not 'cache' in attributes:
            self.execute('BEGIN IMMEDIATE TRANSACTION;')
        return super(SQLiteAdapter, self).select(query, fields, attributes)

class SpatiaLiteAdapter(SQLiteAdapter):
    drivers = ('sqlite3','sqlite2')

    types = copy.copy(BaseAdapter.types)
    types.update(geometry='GEOMETRY')

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, srid=4326, after_connection=None):
        self.db = db
        self.dbengine = "spatialite"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.pool_size = 0
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        self.srid = srid
        path_encoding = sys.getfilesystemencoding() \
            or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('spatialite:memory'):
            dbpath = ':memory:'
        else:
            dbpath = uri.split('://',1)[1]
            if dbpath[0] != '/':
                dbpath = pjoin(
                    self.folder.decode(path_encoding).encode('utf8'), dbpath)
        if not 'check_same_thread' in driver_args:
            driver_args['check_same_thread'] = False
        if not 'detect_types' in driver_args and do_connect:
            driver_args['detect_types'] = self.driver.PARSE_DECLTYPES
        def connector(dbpath=dbpath, driver_args=driver_args):
            return self.driver.Connection(dbpath, **driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.enable_load_extension(True)
        # for Windows, rename libspatialite-2.dll to libspatialite.dll
        # Linux uses libspatialite.so
        # Mac OS X uses libspatialite.dylib
        libspatialite = SPATIALLIBS[platform.system()]
        self.execute(r'SELECT load_extension("%s");' % libspatialite)

        self.connection.create_function('web2py_extract', 2,
                                        SQLiteAdapter.web2py_extract)
        self.connection.create_function("REGEXP", 2,
                                        SQLiteAdapter.web2py_regexp)

    # GIS functions

    def ST_ASGEOJSON(self, first, second):
        return 'AsGeoJSON(%s,%s,%s)' %(self.expand(first),
            second['precision'], second['options'])

    def ST_ASTEXT(self, first):
        return 'AsText(%s)' %(self.expand(first))

    def ST_CONTAINS(self, first, second):
        return 'Contains(%s,%s)' %(self.expand(first),
                                   self.expand(second, first.type))

    def ST_DISTANCE(self, first, second):
        return 'Distance(%s,%s)' %(self.expand(first),
                                   self.expand(second, first.type))

    def ST_EQUALS(self, first, second):
        return 'Equals(%s,%s)' %(self.expand(first),
                                 self.expand(second, first.type))

    def ST_INTERSECTS(self, first, second):
        return 'Intersects(%s,%s)' %(self.expand(first),
                                     self.expand(second, first.type))

    def ST_OVERLAPS(self, first, second):
        return 'Overlaps(%s,%s)' %(self.expand(first),
                                   self.expand(second, first.type))

    def ST_SIMPLIFY(self, first, second):
        return 'Simplify(%s,%s)' %(self.expand(first),
                                   self.expand(second, 'double'))

    def ST_TOUCHES(self, first, second):
        return 'Touches(%s,%s)' %(self.expand(first),
                                  self.expand(second, first.type))

    def ST_WITHIN(self, first, second):
        return 'Within(%s,%s)' %(self.expand(first),
                                 self.expand(second, first.type))

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if field_is_type('geo'):
            srid = 4326 # Spatialite default srid for geometry
            geotype, parms = fieldtype[:-1].split('(')
            parms = parms.split(',')
            if len(parms) >= 2:
                schema, srid = parms[:2]
#             if field_is_type('geometry'):
            value = "ST_GeomFromText('%s',%s)" %(obj, srid)
#             elif field_is_type('geography'):
#                 value = "ST_GeogFromText('SRID=%s;%s')" %(srid, obj)
#             else:
#                 raise SyntaxError, 'Invalid field type %s' %fieldtype
            return value
        return BaseAdapter.represent(self, obj, fieldtype)


class JDBCSQLiteAdapter(SQLiteAdapter):
    drivers = ('zxJDBC_sqlite',)

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "sqlite"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        path_encoding = sys.getfilesystemencoding() \
            or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('sqlite:memory'):
            dbpath = ':memory:'
        else:
            dbpath = uri.split('://',1)[1]
            if dbpath[0] != '/':
                dbpath = pjoin(
                    self.folder.decode(path_encoding).encode('utf8'), dbpath)
        def connector(dbpath=dbpath,driver_args=driver_args):
            return self.driver.connect(
                self.driver.getConnection('jdbc:sqlite:'+dbpath),
                **driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        # FIXME http://www.zentus.com/sqlitejdbc/custom_functions.html for UDFs
        self.connection.create_function('web2py_extract', 2,
                                        SQLiteAdapter.web2py_extract)

    def execute(self, a):
        return self.log_execute(a)


class MySQLAdapter(BaseAdapter):
    drivers = ('MySQLdb','pymysql')

    commit_on_alter_table = True
    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'LONGTEXT',
        'json': 'LONGTEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'LONGBLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'DATETIME',
        'id': 'INT AUTO_INCREMENT NOT NULL',
        'reference': 'INT, INDEX %(index_name)s (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'LONGTEXT',
        'list:string': 'LONGTEXT',
        'list:reference': 'LONGTEXT',
        'big-id': 'BIGINT AUTO_INCREMENT NOT NULL',
        'big-reference': 'BIGINT, INDEX %(index_name)s (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    QUOTE_TEMPLATE = "`%s`"

    def varquote(self,name):
        return varquote_aux(name,'`%s`')

    def RANDOM(self):
        return 'RAND()'

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s,%s,%s)' % (self.expand(field),
                                        parameters[0], parameters[1])

    def EPOCH(self, first):
        return "UNIX_TIMESTAMP(%s)" % self.expand(first)

    def CONCAT(self, *items):
        return 'CONCAT(%s)' % ','.join(self.expand(x,'string') for x in items)

    def REGEXP(self,first,second):
        return '(%s REGEXP %s)' % (self.expand(first),
                                   self.expand(second,'string'))

    def _drop(self,table,mode):
        # breaks db integrity but without this mysql does not drop table
        return ['SET FOREIGN_KEY_CHECKS=0;','DROP TABLE %s;' % table,
                'SET FOREIGN_KEY_CHECKS=1;']

    def _insert_empty(self, table):
        return 'INSERT INTO %s VALUES (DEFAULT);' % table

    def distributed_transaction_begin(self,key):
        self.execute('XA START;')

    def prepare(self,key):
        self.execute("XA END;")
        self.execute("XA PREPARE;")

    def commit_prepared(self,ley):
        self.execute("XA COMMIT;")

    def rollback_prepared(self,key):
        self.execute("XA ROLLBACK;")

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^?]+)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "mysql"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = int(m.group('port') or '3306')
        charset = m.group('charset') or 'utf8'
        driver_args.update(db=db,
                           user=credential_decoder(user),
                           passwd=credential_decoder(password),
                           host=host,
                           port=port,
                           charset=charset)


        def connector(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.execute('SET FOREIGN_KEY_CHECKS=1;')
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")

    def lastrowid(self,table):
        self.execute('select last_insert_id();')
        return int(self.cursor.fetchone()[0])


class PostgreSQLAdapter(BaseAdapter):
    drivers = ('psycopg2','pg8000')

    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BYTEA',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'SERIAL PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        'geometry': 'GEOMETRY',
        'geography': 'GEOGRAPHY',
        'big-id': 'BIGSERIAL PRIMARY KEY',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',

        }

    def varquote(self,name):
        return varquote_aux(name,'"%s"')

    def adapt(self,obj):
        if self.driver_name == 'psycopg2':
            return psycopg2_adapt(obj).getquoted()
        elif self.driver_name == 'pg8000':
            return "'%s'" % str(obj).replace("%","%%").replace("'","''")
        else:
            return "'%s'" % str(obj).replace("'","''")

    def sequence_name(self,table):
        return '%s_id_Seq' % table

    def RANDOM(self):
        return 'RANDOM()'

    def ADD(self, first, second):
        t = first.type
        if t in ('text','string','password', 'json', 'upload','blob'):
            return '(%s || %s)' % (self.expand(first), self.expand(second, t))
        else:
            return '(%s + %s)' % (self.expand(first), self.expand(second, t))

    def distributed_transaction_begin(self,key):
        return

    def prepare(self,key):
        self.execute("PREPARE TRANSACTION '%s';" % key)

    def commit_prepared(self,key):
        self.execute("COMMIT PREPARED '%s';" % key)

    def rollback_prepared(self,key):
        self.execute("ROLLBACK PREPARED '%s';" % key)

    def create_sequence_and_triggers(self, query, table, **args):
        # following lines should only be executed if table._sequence_name does not exist
        # self.execute('CREATE SEQUENCE %s;' % table._sequence_name)
        # self.execute("ALTER TABLE %s ALTER COLUMN %s SET DEFAULT NEXTVAL('%s');" \
        #              % (table._tablename, table._fieldname, table._sequence_name))
        self.execute(query)

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:@]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?sslmode=(?P<sslmode>.+))?$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, srid=4326,
                 after_connection=None):
        self.db = db
        self.dbengine = "postgres"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.srid = srid
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in DAL")
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = m.group('port') or '5432'
        sslmode = m.group('sslmode')
        if sslmode:
            msg = ("dbname='%s' user='%s' host='%s' "
                   "port=%s password='%s' sslmode='%s'") \
                   % (db, user, host, port, password, sslmode)
        else:
            msg = ("dbname='%s' user='%s' host='%s' "
                   "port=%s password='%s'") \
                   % (db, user, host, port, password)
        # choose diver according uri
        if self.driver:
            self.__version__ = "%s %s" % (self.driver.__name__,
                                          self.driver.__version__)
        else:
            self.__version__ = None
        def connector(msg=msg,driver_args=driver_args):
            return self.driver.connect(msg,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.set_client_encoding('UTF8')
        self.execute("SET standard_conforming_strings=on;")
        self.try_json()

    def lastrowid(self,table):
        self.execute("select currval('%s')" % table._sequence_name)
        return int(self.cursor.fetchone()[0])

    def try_json(self):
        # check JSON data type support
        # (to be added to after_connection)
        if self.driver_name == "pg8000":
            supports_json = self.connection.server_version >= "9.2.0"
        elif (self.driver_name == "psycopg2") and \
             (self.driver.__version__ >= "2.0.12"):
            supports_json = self.connection.server_version >= 90200
        elif self.driver_name == "zxJDBC":
            supports_json = self.connection.dbversion >= "9.2.0"
        else: supports_json = None
        if supports_json:
            self.types["json"] = "JSON"
            self.native_json = True
        else: LOGGER.debug("Your database version does not support the JSON data type (using TEXT instead)")

    def LIKE(self,first,second):
        args = (self.expand(first), self.expand(second,'string'))
        if not first.type in ('string', 'text', 'json'):
            return '(CAST(%s AS CHAR(%s)) LIKE %s)' % (args[0], first.length, args[1])
        else:
            return '(%s LIKE %s)' % args

    def ILIKE(self,first,second):
        args = (self.expand(first), self.expand(second,'string'))
        if not first.type in ('string', 'text', 'json'):
            return '(CAST(%s AS CHAR(%s)) LIKE %s)' % (args[0], first.length, args[1])
        else:
            return '(%s ILIKE %s)' % args

    def REGEXP(self,first,second):
        return '(%s ~ %s)' % (self.expand(first),
                              self.expand(second,'string'))

    def STARTSWITH(self,first,second):
        return '(%s ILIKE %s)' % (self.expand(first),
                                  self.expand(second+'%','string'))

    def ENDSWITH(self,first,second):
        return '(%s ILIKE %s)' % (self.expand(first),
                                  self.expand('%'+second,'string'))

    # GIS functions

    def ST_ASGEOJSON(self, first, second):
        """
        http://postgis.org/docs/ST_AsGeoJSON.html
        """
        return 'ST_AsGeoJSON(%s,%s,%s,%s)' %(second['version'],
            self.expand(first), second['precision'], second['options'])

    def ST_ASTEXT(self, first):
        """
        http://postgis.org/docs/ST_AsText.html
        """
        return 'ST_AsText(%s)' %(self.expand(first))

    def ST_X(self, first):
        """
        http://postgis.org/docs/ST_X.html
        """
        return 'ST_X(%s)' %(self.expand(first))

    def ST_Y(self, first):
        """
        http://postgis.org/docs/ST_Y.html
        """
        return 'ST_Y(%s)' %(self.expand(first))

    def ST_CONTAINS(self, first, second):
        """
        http://postgis.org/docs/ST_Contains.html
        """
        return 'ST_Contains(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_DISTANCE(self, first, second):
        """
        http://postgis.org/docs/ST_Distance.html
        """
        return 'ST_Distance(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_EQUALS(self, first, second):
        """
        http://postgis.org/docs/ST_Equals.html
        """
        return 'ST_Equals(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_INTERSECTS(self, first, second):
        """
        http://postgis.org/docs/ST_Intersects.html
        """
        return 'ST_Intersects(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_OVERLAPS(self, first, second):
        """
        http://postgis.org/docs/ST_Overlaps.html
        """
        return 'ST_Overlaps(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_SIMPLIFY(self, first, second):
        """
        http://postgis.org/docs/ST_Simplify.html
        """
        return 'ST_Simplify(%s,%s)' %(self.expand(first), self.expand(second, 'double'))

    def ST_TOUCHES(self, first, second):
        """
        http://postgis.org/docs/ST_Touches.html
        """
        return 'ST_Touches(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_WITHIN(self, first, second):
        """
        http://postgis.org/docs/ST_Within.html
        """
        return 'ST_Within(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if field_is_type('geo'):
            srid = 4326 # postGIS default srid for geometry
            geotype, parms = fieldtype[:-1].split('(')
            parms = parms.split(',')
            if len(parms) >= 2:
                schema, srid = parms[:2]
            if field_is_type('geometry'):
                value = "ST_GeomFromText('%s',%s)" %(obj, srid)
            elif field_is_type('geography'):
                value = "ST_GeogFromText('SRID=%s;%s')" %(srid, obj)
#             else:
#                 raise SyntaxError('Invalid field type %s' %fieldtype)
            return value
        return BaseAdapter.represent(self, obj, fieldtype)

class NewPostgreSQLAdapter(PostgreSQLAdapter):
    drivers = ('psycopg2','pg8000')

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BYTEA',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'SERIAL PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BIGINT[]',
        'list:string': 'TEXT[]',
        'list:reference': 'BIGINT[]',
        'geometry': 'GEOMETRY',
        'geography': 'GEOGRAPHY',
        'big-id': 'BIGSERIAL PRIMARY KEY',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    def parse_list_integers(self, value, field_type):
        return value

    def parse_list_references(self, value, field_type):
        return [self.parse_reference(r, field_type[5:]) for r in value]

    def parse_list_strings(self, value, field_type):
        return value

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if field_is_type('list:'):
            if not obj:
                obj = []
            elif not isinstance(obj, (list, tuple)):
                obj = [obj]
            if field_is_type('list:string'):
                obj = map(str,obj)
            else:
                obj = map(int,obj)
            return 'ARRAY[%s]' % ','.join(repr(item) for item in obj)
        return BaseAdapter.represent(self, obj, fieldtype)


class JDBCPostgreSQLAdapter(PostgreSQLAdapter):
    drivers = ('zxJDBC',)

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None    ):
        self.db = db
        self.dbengine = "postgres"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in DAL")
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = m.group('port') or '5432'
        msg = ('jdbc:postgresql://%s:%s/%s' % (host, port, db), user, password)
        def connector(msg=msg,driver_args=driver_args):
            return self.driver.connect(*msg,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.set_client_encoding('UTF8')
        self.execute('BEGIN;')
        self.execute("SET CLIENT_ENCODING TO 'UNICODE';")
        self.try_json()


class OracleAdapter(BaseAdapter):
    drivers = ('cx_Oracle',)

    commit_on_alter_table = False
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR2(%(length)s)',
        'text': 'CLOB',
        'json': 'CLOB',
        'password': 'VARCHAR2(%(length)s)',
        'blob': 'CLOB',
        'upload': 'VARCHAR2(%(length)s)',
        'integer': 'INT',
        'bigint': 'NUMBER',
        'float': 'FLOAT',
        'double': 'BINARY_DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'CHAR(8)',
        'datetime': 'DATE',
        'id': 'NUMBER PRIMARY KEY',
        'reference': 'NUMBER, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        'big-id': 'NUMBER PRIMARY KEY',
        'big-reference': 'NUMBER, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }

    def sequence_name(self,tablename):
        return '%s_sequence' % tablename

    def trigger_name(self,tablename):
        return '%s_trigger' % tablename

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'dbms_random.value'

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def _drop(self,table,mode):
        sequence_name = table._sequence_name
        return ['DROP TABLE %s %s;' % (table, mode), 'DROP SEQUENCE %s;' % sequence_name]

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if len(sql_w) > 1:
                sql_w_row = sql_w + ' AND w_row > %i' % lmin
            else:
                sql_w_row = 'WHERE w_row > %i' % lmin
            return 'SELECT %s %s FROM (SELECT w_tmp.*, ROWNUM w_row FROM (SELECT %s FROM %s%s%s) w_tmp WHERE ROWNUM<=%i) %s %s %s;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, sql_t, sql_w_row, sql_o)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def constraint_name(self, tablename, fieldname):
        constraint_name = BaseAdapter.constraint_name(self, tablename, fieldname)
        if len(constraint_name)>30:
            constraint_name = '%s_%s__constraint' % (tablename[:10], fieldname[:7])
        return constraint_name

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
            return ":CLOB('%s')" % obj
        elif fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
            return "to_date('%s','yyyy-mm-dd')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T',' ')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+' 00:00:00'
            else:
                obj = str(obj)
            return "to_date('%s','yyyy-mm-dd hh24:mi:ss')" % obj
        return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "oracle"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        if not 'threaded' in driver_args:
            driver_args['threaded']=True
        def connector(uri=ruri,driver_args=driver_args):
            return self.driver.connect(uri,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS';")
        self.execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS';")

    oracle_fix = re.compile("[^']*('[^']*'[^']*)*\:(?P<clob>CLOB\('([^']+|'')*'\))")

    def execute(self, command, args=None):
        args = args or []
        i = 1
        while True:
            m = self.oracle_fix.match(command)
            if not m:
                break
            command = command[:m.start('clob')] + str(i) + command[m.end('clob'):]
            args.append(m.group('clob')[6:-2].replace("''", "'"))
            i += 1
        if command[-1:]==';':
            command = command[:-1]
        return self.log_execute(command, args)

    def create_sequence_and_triggers(self, query, table, **args):
        tablename = table._tablename
        id_name = table._id.name
        sequence_name = table._sequence_name
        trigger_name = table._trigger_name
        self.execute(query)
        self.execute('CREATE SEQUENCE %s START WITH 1 INCREMENT BY 1 NOMAXVALUE MINVALUE -1;' % sequence_name)
        self.execute("""
            CREATE OR REPLACE TRIGGER %(trigger_name)s BEFORE INSERT ON %(tablename)s FOR EACH ROW
            DECLARE
                curr_val NUMBER;
                diff_val NUMBER;
                PRAGMA autonomous_transaction;
            BEGIN
                IF :NEW.%(id)s IS NOT NULL THEN
                    EXECUTE IMMEDIATE 'SELECT %(sequence_name)s.nextval FROM dual' INTO curr_val;
                    diff_val := :NEW.%(id)s - curr_val - 1;
                    IF diff_val != 0 THEN
                      EXECUTE IMMEDIATE 'alter sequence %(sequence_name)s increment by '|| diff_val;
                      EXECUTE IMMEDIATE 'SELECT %(sequence_name)s.nextval FROM dual' INTO curr_val;
                      EXECUTE IMMEDIATE 'alter sequence %(sequence_name)s increment by 1';
                    END IF;
                END IF;
                SELECT %(sequence_name)s.nextval INTO :NEW.%(id)s FROM DUAL;
            END;
        """ % dict(trigger_name=trigger_name, tablename=tablename,
                   sequence_name=sequence_name,id=id_name))

    def lastrowid(self,table):
        sequence_name = table._sequence_name
        self.execute('SELECT %s.currval FROM dual;' % sequence_name)
        return long(self.cursor.fetchone()[0])

    #def parse_value(self, value, field_type, blob_decode=True):
    #    if blob_decode and isinstance(value, cx_Oracle.LOB):
    #        try:
    #            value = value.read()
    #        except self.driver.ProgrammingError:
    #            # After a subsequent fetch the LOB value is not valid anymore
    #            pass
    #    return BaseAdapter.parse_value(self, value, field_type, blob_decode)

    def _fetchall(self):
        if any(x[1]==cx_Oracle.CLOB for x in self.cursor.description):
            return [tuple([(c.read() if type(c) == cx_Oracle.LOB else c) \
                               for c in r]) for r in self.cursor]
        else:
            return self.cursor.fetchall()

class MSSQLAdapter(BaseAdapter):
    drivers = ('pyodbc',)
    T_SEP = 'T'

    QUOTE_TEMPLATE = "[%s]"

    types = {
        'boolean': 'BIT',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        'geometry': 'geometry',
        'geography': 'geography',
        'big-id': 'BIGINT IDENTITY PRIMARY KEY',
        'big-reference': 'BIGINT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }

    def concat_add(self,tablename):
        return '; ALTER TABLE %s ADD ' % tablename

    def varquote(self,name):
        return varquote_aux(name,'[%s]')

    def EXTRACT(self,field,what):
        return "DATEPART(%s,%s)" % (what, self.expand(field))

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'NEWID()'

    def ALLOW_NULL(self):
        return ' NULL'

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s,%s,%s)' % (self.expand(field), parameters[0], parameters[1])

    def PRIMARY_KEY(self,key):
        return 'PRIMARY KEY CLUSTERED (%s)' % key

    def AGGREGATE(self, first, what):
        if what == 'LENGTH':
            what = 'LEN'
        return "%s(%s)" % (what, self.expand(first))


    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_s += ' TOP %i' % lmax
        if 'GROUP BY' in sql_o:
            orderfound = sql_o.find('ORDER BY ')
            if orderfound >= 0:
                sql_o = sql_o[:orderfound]
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    TRUE = 1
    FALSE = 0

    REGEX_DSN = re.compile('^(?P<dsn>.+)$')
    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?(?P<urlargs>.*))?$')
    REGEX_ARGPATTERN = re.compile('(?P<argkey>[^=]+)=(?P<argvalue>[^&]*)')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, srid=4326,
                 after_connection=None):
        self.db = db
        self.dbengine = "mssql"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.srid = srid
        self.find_or_make_work_folder()
        # ## read: http://bytes.com/groups/python/460325-cx_oracle-utf8
        ruri = uri.split('://',1)[1]
        if '@' not in ruri:
            try:
                m = self.REGEX_DSN.match(ruri)
                if not m:
                    raise SyntaxError(
                        'Parsing uri string(%s) has no result' % self.uri)
                dsn = m.group('dsn')
                if not dsn:
                    raise SyntaxError('DSN required')
            except SyntaxError:
                e = sys.exc_info()[1]
                LOGGER.error('NdGpatch error')
                raise e
            # was cnxn = 'DSN=%s' % dsn
            cnxn = dsn
        else:
            m = self.REGEX_URI.match(ruri)
            if not m:
                raise SyntaxError(
                    "Invalid URI string in DAL: %s" % self.uri)
            user = credential_decoder(m.group('user'))
            if not user:
                raise SyntaxError('User required')
            password = credential_decoder(m.group('password'))
            if not password:
                password = ''
            host = m.group('host')
            if not host:
                raise SyntaxError('Host name required')
            db = m.group('db')
            if not db:
                raise SyntaxError('Database name required')
            port = m.group('port') or '1433'
            # Parse the optional url name-value arg pairs after the '?'
            # (in the form of arg1=value1&arg2=value2&...)
            # Default values (drivers like FreeTDS insist on uppercase parameter keys)
            argsdict = { 'DRIVER':'{SQL Server}' }
            urlargs = m.group('urlargs') or ''
            for argmatch in self.REGEX_ARGPATTERN.finditer(urlargs):
                argsdict[str(argmatch.group('argkey')).upper()] = argmatch.group('argvalue')
            urlargs = ';'.join(['%s=%s' % (ak, av) for (ak, av) in argsdict.iteritems()])
            cnxn = 'SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s;%s' \
                % (host, port, db, user, password, urlargs)
        def connector(cnxn=cnxn,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def lastrowid(self,table):
        #self.execute('SELECT @@IDENTITY;')
        self.execute('SELECT SCOPE_IDENTITY();')
        return long(self.cursor.fetchone()[0])

    def rowslice(self,rows,minimum=0,maximum=None):
        if maximum is None:
            return rows[minimum:]
        return rows[minimum:maximum]

    def EPOCH(self, first):
        return "DATEDIFF(second, '1970-01-01 00:00:00', %s)" % self.expand(first)

    def CONCAT(self, *items):
        return '(%s)' % ' + '.join(self.expand(x,'string') for x in items)

    # GIS Spatial Extensions

    # No STAsGeoJSON in MSSQL

    def ST_ASTEXT(self, first):
        return '%s.STAsText()' %(self.expand(first))

    def ST_CONTAINS(self, first, second):
        return '%s.STContains(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def ST_DISTANCE(self, first, second):
        return '%s.STDistance(%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_EQUALS(self, first, second):
        return '%s.STEquals(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def ST_INTERSECTS(self, first, second):
        return '%s.STIntersects(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def ST_OVERLAPS(self, first, second):
        return '%s.STOverlaps(%s)=1' %(self.expand(first), self.expand(second, first.type))

    # no STSimplify in MSSQL

    def ST_TOUCHES(self, first, second):
        return '%s.STTouches(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def ST_WITHIN(self, first, second):
        return '%s.STWithin(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if field_is_type('geometry'):
            srid = 0 # MS SQL default srid for geometry
            geotype, parms = fieldtype[:-1].split('(')
            if parms:
                srid = parms
            return "geometry::STGeomFromText('%s',%s)" %(obj, srid)
        elif fieldtype == 'geography':
            srid = 4326 # MS SQL default srid for geography
            geotype, parms = fieldtype[:-1].split('(')
            if parms:
                srid = parms
            return "geography::STGeomFromText('%s',%s)" %(obj, srid)
#             else:
#                 raise SyntaxError('Invalid field type %s' %fieldtype)
            return "geometry::STGeomFromText('%s',%s)" %(obj, srid)
        return BaseAdapter.represent(self, obj, fieldtype)


class MSSQL3Adapter(MSSQLAdapter):
    """ experimental support for pagination in MSSQL"""
    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if lmin == 0:
                sql_s += ' TOP %i' % lmax
                return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)
            lmin += 1
            sql_o_inner = sql_o[sql_o.find('ORDER BY ')+9:]
            sql_g_inner = sql_o[:sql_o.find('ORDER BY ')]
            sql_f_outer = ['f_%s' % f for f in range(len(sql_f.split(',')))]
            sql_f_inner = [f for f in sql_f.split(',')]
            sql_f_iproxy = ['%s AS %s' % (o, n) for (o, n) in zip(sql_f_inner, sql_f_outer)]
            sql_f_iproxy = ', '.join(sql_f_iproxy)
            sql_f_oproxy = ', '.join(sql_f_outer)
            return 'SELECT %s %s FROM (SELECT %s ROW_NUMBER() OVER (ORDER BY %s) AS w_row, %s FROM %s%s%s) TMP WHERE w_row BETWEEN %i AND %s;' % (sql_s,sql_f_oproxy,sql_s,sql_f,sql_f_iproxy,sql_t,sql_w,sql_g_inner,lmin,lmax)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s,sql_f,sql_t,sql_w,sql_o)
    def rowslice(self,rows,minimum=0,maximum=None):
        return rows


class MSSQL2Adapter(MSSQLAdapter):
    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'NVARCHAR(%(length)s)',
        'text': 'NTEXT',
        'json': 'NTEXT',
        'password': 'NVARCHAR(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'NVARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'NTEXT',
        'list:string': 'NTEXT',
        'list:reference': 'NTEXT',
        'big-id': 'BIGINT IDENTITY PRIMARY KEY',
        'big-reference': 'BIGINT, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }

    def represent(self, obj, fieldtype):
        value = BaseAdapter.represent(self, obj, fieldtype)
        if fieldtype in ('string','text', 'json') and value[:1]=="'":
            value = 'N'+value
        return value

    def execute(self,a):
        return self.log_execute(a.decode('utf8'))

class VerticaAdapter(MSSQLAdapter):
    drivers = ('pyodbc',)
    T_SEP = ' '

    types = {
        'boolean': 'BOOLEAN',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BYTEA',
        'json': 'VARCHAR(%(length)s)',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BYTEA',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE PRECISION',
        'decimal': 'DECIMAL(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'DATETIME',
        'id': 'IDENTITY',
        'reference': 'INT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BYTEA',
        'list:string': 'BYTEA',
        'list:reference': 'BYTEA',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }


    def EXTRACT(self, first, what):
        return "DATE_PART('%s', TIMESTAMP %s)" % (what, self.expand(first))

    def _truncate(self, table, mode=''):
        tablename = table._tablename
        return ['TRUNCATE %s %s;' % (tablename, mode or '')]

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' LIMIT %i OFFSET %i' % (lmax - lmin, lmin)
        return 'SELECT %s %s FROM %s%s%s;' % \
            (sql_s, sql_f, sql_t, sql_w, sql_o)

    def lastrowid(self,table):
        self.execute('SELECT LAST_INSERT_ID();')
        return long(self.cursor.fetchone()[0])

    def execute(self, a):
        return self.log_execute(a)

class SybaseAdapter(MSSQLAdapter):
    drivers = ('Sybase',)

    types = {
        'boolean': 'BIT',
        'string': 'CHAR VARYING(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'CHAR VARYING(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'CHAR VARYING(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        'geometry': 'geometry',
        'geography': 'geography',
        'big-id': 'BIGINT IDENTITY PRIMARY KEY',
        'big-reference': 'BIGINT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }


    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, srid=4326,
                 after_connection=None):
        self.db = db
        self.dbengine = "sybase"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.srid = srid
        self.find_or_make_work_folder()
        # ## read: http://bytes.com/groups/python/460325-cx_oracle-utf8
        ruri = uri.split('://',1)[1]
        if '@' not in ruri:
            try:
                m = self.REGEX_DSN.match(ruri)
                if not m:
                    raise SyntaxError(
                        'Parsing uri string(%s) has no result' % self.uri)
                dsn = m.group('dsn')
                if not dsn:
                    raise SyntaxError('DSN required')
            except SyntaxError:
                e = sys.exc_info()[1]
                LOGGER.error('NdGpatch error')
                raise e
        else:
            m = self.REGEX_URI.match(uri)
            if not m:
                raise SyntaxError(
                    "Invalid URI string in DAL: %s" % self.uri)
            user = credential_decoder(m.group('user'))
            if not user:
                raise SyntaxError('User required')
            password = credential_decoder(m.group('password'))
            if not password:
                password = ''
            host = m.group('host')
            if not host:
                raise SyntaxError('Host name required')
            db = m.group('db')
            if not db:
                raise SyntaxError('Database name required')
            port = m.group('port') or '1433'

            dsn = 'sybase:host=%s:%s;dbname=%s' % (host,port,db)

            driver_args.update(user = credential_decoder(user),
                               password = credential_decoder(password))

        def connector(dsn=dsn,driver_args=driver_args):
            return self.driver.connect(dsn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()


class FireBirdAdapter(BaseAdapter):
    drivers = ('kinterbasdb','firebirdsql','fdb','pyodbc')

    commit_on_alter_table = False
    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BLOB SUB_TYPE 1',
        'json': 'BLOB SUB_TYPE 1',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB SUB_TYPE 0',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE PRECISION',
        'decimal': 'DECIMAL(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BLOB SUB_TYPE 1',
        'list:string': 'BLOB SUB_TYPE 1',
        'list:reference': 'BLOB SUB_TYPE 1',
        'big-id': 'BIGINT PRIMARY KEY',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    def sequence_name(self,tablename):
        return 'genid_%s' % tablename

    def trigger_name(self,tablename):
        return 'trg_id_%s' % tablename

    def RANDOM(self):
        return 'RAND()'

    def EPOCH(self, first):
        return "DATEDIFF(second, '1970-01-01 00:00:00', %s)" % self.expand(first)

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s from %s for %s)' % (self.expand(field), parameters[0], parameters[1])

    def LENGTH(self, first):
        return "CHAR_LENGTH(%s)" % self.expand(first)

    def CONTAINS(self,first,second,case_sensitive=False):
        if first.type.startswith('list:'):
            second = Expression(None,self.CONCAT('|',Expression(
                        None,self.REPLACE(second,('|','||'))),'|'))
        return '(%s CONTAINING %s)' % (self.expand(first),
                                       self.expand(second, 'string'))

    def _drop(self,table,mode):
        sequence_name = table._sequence_name
        return ['DROP TABLE %s %s;' % (table, mode), 'DROP GENERATOR %s;' % sequence_name]

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_s = ' FIRST %i SKIP %i %s' % (lmax - lmin, lmin, sql_s)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def _truncate(self,table,mode = ''):
        return ['DELETE FROM %s;' % table._tablename,
                'SET GENERATOR %s TO 0;' % table._sequence_name]

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+?)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "firebird"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        port = int(m.group('port') or 3050)
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        charset = m.group('charset') or 'UTF8'
        driver_args.update(dsn='%s/%s:%s' % (host,port,db),
                           user = credential_decoder(user),
                           password = credential_decoder(password),
                           charset = charset)

        def connector(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def create_sequence_and_triggers(self, query, table, **args):
        tablename = table._tablename
        sequence_name = table._sequence_name
        trigger_name = table._trigger_name
        self.execute(query)
        self.execute('create generator %s;' % sequence_name)
        self.execute('set generator %s to 0;' % sequence_name)
        self.execute('create trigger %s for %s active before insert position 0 as\nbegin\nif(new.id is null) then\nbegin\nnew.id = gen_id(%s, 1);\nend\nend;' % (trigger_name, tablename, sequence_name))

    def lastrowid(self,table):
        sequence_name = table._sequence_name
        self.execute('SELECT gen_id(%s, 0) FROM rdb$database' % sequence_name)
        return long(self.cursor.fetchone()[0])


class FireBirdEmbeddedAdapter(FireBirdAdapter):
    drivers = ('kinterbasdb','firebirdsql','fdb','pyodbc')

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<path>[^\?]+)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "firebird"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        pathdb = m.group('path')
        if not pathdb:
            raise SyntaxError('Path required')
        charset = m.group('charset')
        if not charset:
            charset = 'UTF8'
        host = ''
        driver_args.update(host=host,
                           database=pathdb,
                           user=credential_decoder(user),
                           password=credential_decoder(password),
                           charset=charset)

        def connector(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

class InformixAdapter(BaseAdapter):
    drivers = ('informixdb',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BLOB SUB_TYPE 1',
        'json': 'BLOB SUB_TYPE 1',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB SUB_TYPE 0',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE PRECISION',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'SERIAL',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BLOB SUB_TYPE 1',
        'list:string': 'BLOB SUB_TYPE 1',
        'list:reference': 'BLOB SUB_TYPE 1',
        'big-id': 'BIGSERIAL',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': 'REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s CONSTRAINT FK_%(table_name)s_%(field_name)s',
        'reference TFK': 'FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s CONSTRAINT TFK_%(table_name)s_%(field_name)s',
        }

    def RANDOM(self):
        return 'Random()'

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            fetch_amt = lmax - lmin
            dbms_version = int(self.connection.dbms_version.split('.')[0])
            if lmin and (dbms_version >= 10):
                # Requires Informix 10.0+
                sql_s += ' SKIP %d' % (lmin, )
            if fetch_amt and (dbms_version >= 9):
                # Requires Informix 9.0+
                sql_s += ' FIRST %d' % (fetch_amt, )
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
            return "to_date('%s','%%Y-%%m-%%d')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T',' ')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+' 00:00:00'
            else:
                obj = str(obj)
            return "to_date('%s','%%Y-%%m-%%d %%H:%%M:%%S')" % obj
        return None

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "informix"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        user = credential_decoder(user)
        password = credential_decoder(password)
        dsn = '%s@%s' % (db,host)
        driver_args.update(user=user,password=password,autocommit=True)
        def connector(dsn=dsn,driver_args=driver_args):
            return self.driver.connect(dsn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def execute(self,command):
        if command[-1:]==';':
            command = command[:-1]
        return self.log_execute(command)

    def lastrowid(self,table):
        return self.cursor.sqlerrd[1]

class InformixSEAdapter(InformixAdapter):
    """ work in progress """

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        return 'SELECT %s %s FROM %s%s%s;' % \
            (sql_s, sql_f, sql_t, sql_w, sql_o)

    def rowslice(self,rows,minimum=0,maximum=None):
        if maximum is None:
            return rows[minimum:]
        return rows[minimum:maximum]

class DB2Adapter(BaseAdapter):
    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'json': 'CLOB',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'REAL',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY NOT NULL',
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        'big-id': 'BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY NOT NULL',
        'big-reference': 'BIGINT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'RAND()'

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' FETCH FIRST %i ROWS ONLY' % lmax
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
            return "BLOB('%s')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T','-').replace(':','.')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+'-00.00.00'
            return "'%s'" % obj
        return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "db2"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://', 1)[1]
        def connector(cnxn=ruri,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def execute(self,command):
        if command[-1:]==';':
            command = command[:-1]
        return self.log_execute(command)

    def lastrowid(self,table):
        self.execute('SELECT DISTINCT IDENTITY_VAL_LOCAL() FROM %s;' % table)
        return long(self.cursor.fetchone()[0])

    def rowslice(self,rows,minimum=0,maximum=None):
        if maximum is None:
            return rows[minimum:]
        return rows[minimum:maximum]


class TeradataAdapter(BaseAdapter):
    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'json': 'CLOB',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'REAL',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        # Modified Constraint syntax for Teradata.
        # Teradata does not support ON DELETE.
        'id': 'INT GENERATED ALWAYS AS IDENTITY',  # Teradata Specific
        'reference': 'INT',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        'big-id': 'BIGINT GENERATED ALWAYS AS IDENTITY',  # Teradata Specific
        'big-reference': 'BIGINT',
        'reference FK': ' REFERENCES %(foreign_key)s',
        'reference TFK': ' FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s)',
        }

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "teradata"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://', 1)[1]
        def connector(cnxn=ruri,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    # Similar to MSSQL, Teradata can't specify a range (for Pageby)
    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_s += ' TOP %i' % lmax
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def _truncate(self, table, mode=''):
        tablename = table._tablename
        return ['DELETE FROM %s ALL;' % (tablename)]

INGRES_SEQNAME='ii***lineitemsequence' # NOTE invalid database object name
                                       # (ANSI-SQL wants this form of name
                                       # to be a delimited identifier)

class IngresAdapter(BaseAdapter):
    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'json': 'CLOB',
        'password': 'VARCHAR(%(length)s)',  ## Not sure what this contains utf8 or nvarchar. Or even bytes?
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',  ## FIXME utf8 or nvarchar... or blob? what is this type?
        'integer': 'INTEGER4', # or int8...
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'ANSIDATE',
        'time': 'TIME WITHOUT TIME ZONE',
        'datetime': 'TIMESTAMP WITHOUT TIME ZONE',
        'id': 'int not null unique with default next value for %s' % INGRES_SEQNAME,
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        'big-id': 'bigint not null unique with default next value for %s' % INGRES_SEQNAME,
        'big-reference': 'BIGINT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s', ## FIXME TODO
        }

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'RANDOM()'

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            fetch_amt = lmax - lmin
            if fetch_amt:
                sql_s += ' FIRST %d ' % (fetch_amt, )
            if lmin:
                # Requires Ingres 9.2+
                sql_o += ' OFFSET %d' % (lmin, )
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "ingres"
        self._driver = pyodbc
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        connstr = uri.split(':', 1)[1]
        # Simple URI processing
        connstr = connstr.lstrip()
        while connstr.startswith('/'):
            connstr = connstr[1:]
        if '=' in connstr:
            # Assume we have a regular ODBC connection string and just use it
            ruri  = connstr
        else:
            # Assume only (local) dbname is passed in with OS auth
            database_name = connstr
            default_driver_name = 'Ingres'
            vnode = '(local)'
            servertype = 'ingres'
            ruri = 'Driver={%s};Server=%s;Database=%s' % (default_driver_name, vnode, database_name)
        def connector(cnxn=ruri,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)

        self.connector = connector

        # TODO if version is >= 10, set types['id'] to Identity column, see http://community.actian.com/wiki/Using_Ingres_Identity_Columns
        if do_connect: self.reconnect()

    def create_sequence_and_triggers(self, query, table, **args):
        # post create table auto inc code (if needed)
        # modify table to btree for performance....
        # Older Ingres releases could use rule/trigger like Oracle above.
        if hasattr(table,'_primarykey'):
            modify_tbl_sql = 'modify %s to btree unique on %s' % \
                (table._tablename,
                 ', '.join(["'%s'" % x for x in table.primarykey]))
            self.execute(modify_tbl_sql)
        else:
            tmp_seqname='%s_iisq' % table._tablename
            query=query.replace(INGRES_SEQNAME, tmp_seqname)
            self.execute('create sequence %s' % tmp_seqname)
            self.execute(query)
            self.execute('modify %s to btree unique on %s' % (table._tablename, 'id'))


    def lastrowid(self,table):
        tmp_seqname='%s_iisq' % table
        self.execute('select current value for %s' % tmp_seqname)
        return long(self.cursor.fetchone()[0]) # don't really need int type cast here...


class IngresUnicodeAdapter(IngresAdapter):

    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'NVARCHAR(%(length)s)',
        'text': 'NCLOB',
        'json': 'NCLOB',
        'password': 'NVARCHAR(%(length)s)',  ## Not sure what this contains utf8 or nvarchar. Or even bytes?
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',  ## FIXME utf8 or nvarchar... or blob? what is this type?
        'integer': 'INTEGER4', # or int8...
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'ANSIDATE',
        'time': 'TIME WITHOUT TIME ZONE',
        'datetime': 'TIMESTAMP WITHOUT TIME ZONE',
        'id': 'INTEGER4 not null unique with default next value for %s'% INGRES_SEQNAME,
        'reference': 'INTEGER4, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'NCLOB',
        'list:string': 'NCLOB',
        'list:reference': 'NCLOB',
        'big-id': 'BIGINT not null unique with default next value for %s'% INGRES_SEQNAME,
        'big-reference': 'BIGINT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s', ## FIXME TODO
        }

class SAPDBAdapter(BaseAdapter):
    drivers = ('sapdb',)

    support_distributed_transaction = False
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'LONG',
        'json': 'LONG',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'LONG',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE PRECISION',
        'decimal': 'FIXED(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INT PRIMARY KEY',
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'LONG',
        'list:string': 'LONG',
        'list:reference': 'LONG',
        'big-id': 'BIGINT PRIMARY KEY',
        'big-reference': 'BIGINT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    def sequence_name(self,table):
        return '%s_id_Seq' % table

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if len(sql_w) > 1:
                sql_w_row = sql_w + ' AND w_row > %i' % lmin
            else:
                sql_w_row = 'WHERE w_row > %i' % lmin
            return '%s %s FROM (SELECT w_tmp.*, ROWNO w_row FROM (SELECT %s FROM %s%s%s) w_tmp WHERE ROWNO=%i) %s %s %s;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, sql_t, sql_w_row, sql_o)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def create_sequence_and_triggers(self, query, table, **args):
        # following lines should only be executed if table._sequence_name does not exist
        self.execute('CREATE SEQUENCE %s;' % table._sequence_name)
        self.execute("ALTER TABLE %s ALTER COLUMN %s SET DEFAULT NEXTVAL('%s');" \
                         % (table._tablename, table._id.name, table._sequence_name))
        self.execute(query)

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:@]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?sslmode=(?P<sslmode>.+))?$')


    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "sapdb"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in DAL")
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        def connector(user=user, password=password, database=db,
                    host=host, driver_args=driver_args):
            return self.driver.Connection(user, password, database,
                                          host, **driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def lastrowid(self,table):
        self.execute("select %s.NEXTVAL from dual" % table._sequence_name)
        return long(self.cursor.fetchone()[0])

class CubridAdapter(MySQLAdapter):
    drivers = ('cubriddb',)

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^?]+)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "cubrid"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = int(m.group('port') or '30000')
        charset = m.group('charset') or 'utf8'
        user = credential_decoder(user)
        passwd = credential_decoder(password)
        def connector(host=host,port=port,db=db,
                    user=user,passwd=password,driver_args=driver_args):
            return self.driver.connect(host,port,db,user,passwd,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.execute('SET FOREIGN_KEY_CHECKS=1;')
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")


######## GAE MySQL ##########

class DatabaseStoredFile:

    web2py_filesystem = False

    def escape(self,obj):
        return self.db._adapter.escape(obj)

    def __init__(self,db,filename,mode):
        if not db._adapter.dbengine in ('mysql', 'postgres'):
            raise RuntimeError("only MySQL/Postgres can store metadata .table files in database for now")
        self.db = db
        self.filename = filename
        self.mode = mode
        if not self.web2py_filesystem:
            if db._adapter.dbengine == 'mysql':
                sql = "CREATE TABLE IF NOT EXISTS web2py_filesystem (path VARCHAR(255), content LONGTEXT, PRIMARY KEY(path) ) ENGINE=InnoDB;"
            elif db._adapter.dbengine == 'postgres':
                sql = "CREATE TABLE IF NOT EXISTS web2py_filesystem (path VARCHAR(255), content TEXT, PRIMARY KEY(path));"
            self.db.executesql(sql)
            DatabaseStoredFile.web2py_filesystem = True
        self.p=0
        self.data = ''
        if mode in ('r','rw','a'):
            query = "SELECT content FROM web2py_filesystem WHERE path='%s'" \
                % filename
            rows = self.db.executesql(query)
            if rows:
                self.data = rows[0][0]
            elif exists(filename):
                datafile = open(filename, 'r')
                try:
                    self.data = datafile.read()
                finally:
                    datafile.close()
            elif mode in ('r','rw'):
                raise RuntimeError("File %s does not exist" % filename)

    def read(self, bytes):
        data = self.data[self.p:self.p+bytes]
        self.p += len(data)
        return data

    def readline(self):
        i = self.data.find('\n',self.p)+1
        if i>0:
            data, self.p = self.data[self.p:i], i
        else:
            data, self.p = self.data[self.p:], len(self.data)
        return data

    def write(self,data):
        self.data += data

    def close_connection(self):
        if self.db is not None:
            self.db.executesql(
                "DELETE FROM web2py_filesystem WHERE path='%s'" % self.filename)
            query = "INSERT INTO web2py_filesystem(path,content) VALUES ('%s','%s')"\
                % (self.filename, self.data.replace("'","''"))
            self.db.executesql(query)
            self.db.commit()
            self.db = None

    def close(self):
        self.close_connection()

    @staticmethod
    def exists(db, filename):
        if exists(filename):
            return True
        query = "SELECT path FROM web2py_filesystem WHERE path='%s'" % filename
        if db.executesql(query):
            return True
        return False


class UseDatabaseStoredFile:

    def file_exists(self, filename):
        return DatabaseStoredFile.exists(self.db,filename)

    def file_open(self, filename, mode='rb', lock=True):
        return DatabaseStoredFile(self.db,filename,mode)

    def file_close(self, fileobj):
        fileobj.close_connection()

    def file_delete(self,filename):
        query = "DELETE FROM web2py_filesystem WHERE path='%s'" % filename
        self.db.executesql(query)
        self.db.commit()

class GoogleSQLAdapter(UseDatabaseStoredFile,MySQLAdapter):
    uploads_in_blob = True

    REGEX_URI = re.compile('^(?P<instance>.*)/(?P<db>.*)$')

    def __init__(self, db, uri='google:sql://realm:domain/database',
                 pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):

        self.db = db
        self.dbengine = "mysql"
        self.uri = uri
        self.pool_size = pool_size
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.folder = folder or pjoin('$HOME',THREAD_LOCAL.folder.split(
                os.sep+'applications'+os.sep,1)[1])
        ruri = uri.split("://")[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in SQLDB: %s" % self.uri)
        instance = credential_decoder(m.group('instance'))
        self.dbstring = db = credential_decoder(m.group('db'))
        driver_args['instance'] = instance
        if not 'charset' in driver_args:
            driver_args['charset'] = 'utf8'
        self.createdb = createdb = adapter_args.get('createdb',True)
        if not createdb:
            driver_args['database'] = db
        def connector(driver_args=driver_args):
            return rdbms.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        if self.createdb:
            # self.execute('DROP DATABASE %s' % self.dbstring)
            self.execute('CREATE DATABASE IF NOT EXISTS %s' % self.dbstring)
            self.execute('USE %s' % self.dbstring)
        self.execute("SET FOREIGN_KEY_CHECKS=1;")
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")

    def execute(self, command, *a, **b):
        return self.log_execute(command.decode('utf8'), *a, **b)

class NoSQLAdapter(BaseAdapter):
    can_select_for_update = False

    @staticmethod
    def to_unicode(obj):
        if isinstance(obj, str):
            return obj.decode('utf8')
        elif not isinstance(obj, unicode):
            return unicode(obj)
        return obj

    def id_query(self, table):
        return table._id > 0

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if isinstance(obj, CALLABLETYPES):
            obj = obj()
        if isinstance(fieldtype, SQLCustomType):
            return fieldtype.encoder(obj)
        if isinstance(obj, (Expression, Field)):
            raise SyntaxError("non supported on GAE")
        if self.dbengine == 'google:datastore':
            if isinstance(fieldtype, gae.Property):
                return obj
        is_string = isinstance(fieldtype,str)
        is_list = is_string and field_is_type('list:')
        if is_list:
            if not obj:
                obj = []
            if not isinstance(obj, (list, tuple)):
                obj = [obj]
        if obj == '' and not \
                (is_string and fieldtype[:2] in ['st','te', 'pa','up']):
            return None
        if not obj is None:
            if isinstance(obj, list) and not is_list:
                obj = [self.represent(o, fieldtype) for o in obj]
            elif fieldtype in ('integer','bigint','id'):
                obj = long(obj)
            elif fieldtype == 'double':
                obj = float(obj)
            elif is_string and field_is_type('reference'):
                if isinstance(obj, (Row, Reference)):
                    obj = obj['id']
                obj = long(obj)
            elif fieldtype == 'boolean':
                if obj and not str(obj)[0].upper() in '0F':
                    obj = True
                else:
                    obj = False
            elif fieldtype == 'date':
                if not isinstance(obj, datetime.date):
                    (y, m, d) = map(int,str(obj).strip().split('-'))
                    obj = datetime.date(y, m, d)
                elif isinstance(obj,datetime.datetime):
                    (y, m, d) = (obj.year, obj.month, obj.day)
                    obj = datetime.date(y, m, d)
            elif fieldtype == 'time':
                if not isinstance(obj, datetime.time):
                    time_items = map(int,str(obj).strip().split(':')[:3])
                    if len(time_items) == 3:
                        (h, mi, s) = time_items
                    else:
                        (h, mi, s) = time_items + [0]
                    obj = datetime.time(h, mi, s)
            elif fieldtype == 'datetime':
                if not isinstance(obj, datetime.datetime):
                    (y, m, d) = map(int,str(obj)[:10].strip().split('-'))
                    time_items = map(int,str(obj)[11:].strip().split(':')[:3])
                    while len(time_items)<3:
                        time_items.append(0)
                    (h, mi, s) = time_items
                    obj = datetime.datetime(y, m, d, h, mi, s)
            elif fieldtype == 'blob':
                pass
            elif fieldtype == 'json':
                if isinstance(obj, basestring):
                    obj = self.to_unicode(obj)
                    if have_serializers:
                        obj = serializers.loads_json(obj)
                    elif simplejson:
                        obj = simplejson.loads(obj)
                    else:
                        raise RuntimeError("missing simplejson")
            elif is_string and field_is_type('list:string'):
                return map(self.to_unicode,obj)
            elif is_list:
                return map(int,obj)
            else:
                obj = self.to_unicode(obj)
        return obj

    def _insert(self,table,fields):
        return 'insert %s in %s' % (fields, table)

    def _count(self,query,distinct=None):
        return 'count %s' % repr(query)

    def _select(self,query,fields,attributes):
        return 'select %s where %s' % (repr(fields), repr(query))

    def _delete(self,tablename, query):
        return 'delete %s where %s' % (repr(tablename),repr(query))

    def _update(self,tablename,query,fields):
        return 'update %s (%s) where %s' % (repr(tablename),
                                            repr(fields),repr(query))

    def commit(self):
        """
        remember: no transactions on many NoSQL
        """
        pass

    def rollback(self):
        """
        remember: no transactions on many NoSQL
        """
        pass

    def close_connection(self):
        """
        remember: no transactions on many NoSQL
        """
        pass


    # these functions should never be called!
    def OR(self,first,second): raise SyntaxError("Not supported")
    def AND(self,first,second): raise SyntaxError("Not supported")
    def AS(self,first,second): raise SyntaxError("Not supported")
    def ON(self,first,second): raise SyntaxError("Not supported")
    def STARTSWITH(self,first,second=None): raise SyntaxError("Not supported")
    def ENDSWITH(self,first,second=None): raise SyntaxError("Not supported")
    def ADD(self,first,second): raise SyntaxError("Not supported")
    def SUB(self,first,second): raise SyntaxError("Not supported")
    def MUL(self,first,second): raise SyntaxError("Not supported")
    def DIV(self,first,second): raise SyntaxError("Not supported")
    def LOWER(self,first): raise SyntaxError("Not supported")
    def UPPER(self,first): raise SyntaxError("Not supported")
    def EXTRACT(self,first,what): raise SyntaxError("Not supported")
    def LENGTH(self, first): raise SyntaxError("Not supported")
    def AGGREGATE(self,first,what): raise SyntaxError("Not supported")
    def LEFT_JOIN(self): raise SyntaxError("Not supported")
    def RANDOM(self): raise SyntaxError("Not supported")
    def SUBSTRING(self,field,parameters):  raise SyntaxError("Not supported")
    def PRIMARY_KEY(self,key):  raise SyntaxError("Not supported")
    def ILIKE(self,first,second): raise SyntaxError("Not supported")
    def drop(self,table,mode):  raise SyntaxError("Not supported")
    def alias(self,table,alias): raise SyntaxError("Not supported")
    def migrate_table(self,*a,**b): raise SyntaxError("Not supported")
    def distributed_transaction_begin(self,key): raise SyntaxError("Not supported")
    def prepare(self,key): raise SyntaxError("Not supported")
    def commit_prepared(self,key): raise SyntaxError("Not supported")
    def rollback_prepared(self,key): raise SyntaxError("Not supported")
    def concat_add(self,table): raise SyntaxError("Not supported")
    def constraint_name(self, table, fieldname): raise SyntaxError("Not supported")
    def create_sequence_and_triggers(self, query, table, **args): pass
    def log_execute(self,*a,**b): raise SyntaxError("Not supported")
    def execute(self,*a,**b): raise SyntaxError("Not supported")
    def represent_exceptions(self, obj, fieldtype): raise SyntaxError("Not supported")
    def lastrowid(self,table): raise SyntaxError("Not supported")
    def rowslice(self,rows,minimum=0,maximum=None): raise SyntaxError("Not supported")


class GAEF(object):
    def __init__(self,name,op,value,apply):
        self.name=name=='id' and '__key__' or name
        self.op=op
        self.value=value
        self.apply=apply
    def __repr__(self):
        return '(%s %s %s:%s)' % (self.name, self.op, repr(self.value), type(self.value))

class GoogleDatastoreAdapter(NoSQLAdapter):
    uploads_in_blob = True
    types = {}

    def file_exists(self, filename): pass
    def file_open(self, filename, mode='rb', lock=True): pass
    def file_close(self, fileobj): pass

    REGEX_NAMESPACE = re.compile('.*://(?P<namespace>.+)')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.types.update({
                'boolean': gae.BooleanProperty,
                'string': (lambda **kwargs: gae.StringProperty(multiline=True, **kwargs)),
                'text': gae.TextProperty,
                'json': gae.TextProperty,
                'password': gae.StringProperty,
                'blob': gae.BlobProperty,
                'upload': gae.StringProperty,
                'integer': gae.IntegerProperty,
                'bigint': gae.IntegerProperty,
                'float': gae.FloatProperty,
                'double': gae.FloatProperty,
                'decimal': GAEDecimalProperty,
                'date': gae.DateProperty,
                'time': gae.TimeProperty,
                'datetime': gae.DateTimeProperty,
                'id': None,
                'reference': gae.IntegerProperty,
                'list:string': (lambda **kwargs: gae.StringListProperty(default=None, **kwargs)),
                'list:integer': (lambda **kwargs: gae.ListProperty(int,default=None, **kwargs)),
                'list:reference': (lambda **kwargs: gae.ListProperty(int,default=None, **kwargs)),
                })
        self.db = db
        self.uri = uri
        self.dbengine = 'google:datastore'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self._after_connection = after_connection
        self.pool_size = 0
        match = self.REGEX_NAMESPACE.match(uri)
        if match:
            namespace_manager.set_namespace(match.group('namespace'))

    def parse_id(self, value, field_type):
        return value

    def create_table(self,table,migrate=True,fake_migrate=False, polymodel=None):
        myfields = {}
        for field in table:
            if isinstance(polymodel,Table) and field.name in polymodel.fields():
                continue
            attr = {}
            if isinstance(field.custom_qualifier, dict):
                #this is custom properties to add to the GAE field declartion
                attr = field.custom_qualifier
            field_type = field.type
            if isinstance(field_type, SQLCustomType):
                ftype = self.types[field_type.native or field_type.type](**attr)
            elif isinstance(field_type, gae.Property):
                ftype = field_type
            elif field_type.startswith('id'):
                continue
            elif field_type.startswith('decimal'):
                precision, scale = field_type[7:].strip('()').split(',')
                precision = int(precision)
                scale = int(scale)
                ftype = GAEDecimalProperty(precision, scale, **attr)
            elif field_type.startswith('reference'):
                if field.notnull:
                    attr = dict(required=True)
                referenced = field_type[10:].strip()
                ftype = self.types[field_type[:9]](referenced, **attr)
            elif field_type.startswith('list:reference'):
                if field.notnull:
                    attr['required'] = True
                referenced = field_type[15:].strip()
                ftype = self.types[field_type[:14]](**attr)
            elif field_type.startswith('list:'):
                ftype = self.types[field_type](**attr)
            elif not field_type in self.types\
                 or not self.types[field_type]:
                raise SyntaxError('Field: unknown field type: %s' % field_type)
            else:
                ftype = self.types[field_type](**attr)
            myfields[field.name] = ftype
        if not polymodel:
            table._tableobj = classobj(table._tablename, (gae.Model, ), myfields)
        elif polymodel==True:
            table._tableobj = classobj(table._tablename, (PolyModel, ), myfields)
        elif isinstance(polymodel,Table):
            table._tableobj = classobj(table._tablename, (polymodel._tableobj, ), myfields)
        else:
            raise SyntaxError("polymodel must be None, True, a table or a tablename")
        return None

    def expand(self,expression,field_type=None):
        if isinstance(expression,Field):
            if expression.type in ('text', 'blob', 'json'):
                raise SyntaxError('AppEngine does not index by: %s' % expression.type)
            return expression.name
        elif isinstance(expression, (Expression, Query)):
            if not expression.second is None:
                return expression.op(expression.first, expression.second)
            elif not expression.first is None:
                return expression.op(expression.first)
            else:
                return expression.op()
        elif field_type:
                return self.represent(expression,field_type)
        elif isinstance(expression,(list,tuple)):
            return ','.join([self.represent(item,field_type) for item in expression])
        else:
            return str(expression)

    ### TODO from gql.py Expression
    def AND(self,first,second):
        a = self.expand(first)
        b = self.expand(second)
        if b[0].name=='__key__' and a[0].name!='__key__':
            return b+a
        return a+b

    def EQ(self,first,second=None):
        if isinstance(second, Key):
            return [GAEF(first.name,'=',second,lambda a,b:a==b)]
        return [GAEF(first.name,'=',self.represent(second,first.type),lambda a,b:a==b)]

    def NE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'!=',self.represent(second,first.type),lambda a,b:a!=b)]
        else:
            if not second is None:
                second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'!=',second,lambda a,b:a!=b)]

    def LT(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'<',self.represent(second,first.type),lambda a,b:a<b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'<',second,lambda a,b:a<b)]

    def LE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'<=',self.represent(second,first.type),lambda a,b:a<=b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'<=',second,lambda a,b:a<=b)]

    def GT(self,first,second=None):
        if first.type != 'id' or second==0 or second == '0':
            return [GAEF(first.name,'>',self.represent(second,first.type),lambda a,b:a>b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'>',second,lambda a,b:a>b)]

    def GE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'>=',self.represent(second,first.type),lambda a,b:a>=b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'>=',second,lambda a,b:a>=b)]

    def INVERT(self,first):
        return '-%s' % first.name

    def COMMA(self,first,second):
        return '%s, %s' % (self.expand(first),self.expand(second))

    def BELONGS(self,first,second=None):
        if not isinstance(second,(list, tuple)):
            raise SyntaxError("Not supported")
        if first.type != 'id':
            return [GAEF(first.name,'in',self.represent(second,first.type),lambda a,b:a in b)]
        else:
            second = [Key.from_path(first._tablename, int(i)) for i in second]
            return [GAEF(first.name,'in',second,lambda a,b:a in b)]

    def CONTAINS(self,first,second,case_sensitive=False):
        # silently ignoring: GAE can only do case sensitive matches!
        if not first.type.startswith('list:'):
            raise SyntaxError("Not supported")
        return [GAEF(first.name,'=',self.expand(second,first.type[5:]),lambda a,b:b in a)]

    def NOT(self,first):
        nops = { self.EQ: self.NE,
                 self.NE: self.EQ,
                 self.LT: self.GE,
                 self.GT: self.LE,
                 self.LE: self.GT,
                 self.GE: self.LT}
        if not isinstance(first,Query):
            raise SyntaxError("Not suported")
        nop = nops.get(first.op,None)
        if not nop:
            raise SyntaxError("Not suported %s" % first.op.__name__)
        first.op = nop
        return self.expand(first)

    def truncate(self,table,mode):
        self.db(self.db._adapter.id_query(table)).delete()

    def select_raw(self,query,fields=None,attributes=None):
        db = self.db
        fields = fields or []
        attributes = attributes or {}
        args_get = attributes.get
        new_fields = []
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item._table
            else:
                new_fields.append(item)
        fields = new_fields
        if query:
            tablename = self.get_table(query)
        elif fields:
            tablename = fields[0].tablename
            query = db._adapter.id_query(fields[0].table)
        else:
            raise SyntaxError("Unable to determine a tablename")

        if query:
            if use_common_filters(query):
                query = self.common_filter(query,[tablename])

        #tableobj is a GAE Model class (or subclass)
        tableobj = db[tablename]._tableobj
        filters = self.expand(query)

        projection = None
        if len(db[tablename].fields) == len(fields):
            #getting all fields, not a projection query
            projection = None
        elif args_get('projection') == True:
            projection = []
            for f in fields:
                if f.type in ['text', 'blob', 'json']:
                    raise SyntaxError(
                        "text and blob field types not allowed in projection queries")
                else:
                    projection.append(f.name)
        elif args_get('filterfields') == True:
            projection = []
            for f in fields:
                projection.append(f.name)

        # real projection's can't include 'id'.
        # it will be added to the result later
        query_projection = [
            p for p in projection if \
                p != db[tablename]._id.name] if projection and \
                args_get('projection') == True\
                else None

        cursor = None
        if isinstance(args_get('reusecursor'), str):
            cursor = args_get('reusecursor')
        items = gae.Query(tableobj, projection=query_projection,
                          cursor=cursor)

        for filter in filters:
            if args_get('projection') == True and \
               filter.name in query_projection and \
               filter.op in ['=', '<=', '>=']:
                raise SyntaxError(
                    "projection fields cannot have equality filters")
            if filter.name=='__key__' and filter.op=='>' and filter.value==0:
                continue
            elif filter.name=='__key__' and filter.op=='=':
                if filter.value==0:
                    items = []
                elif isinstance(filter.value, Key):
                    # key qeuries return a class instance,
                    # can't use projection
                    # extra values will be ignored in post-processing later
                    item = tableobj.get(filter.value)
                    items = (item and [item]) or []
                else:
                    # key qeuries return a class instance,
                    # can't use projection
                    # extra values will be ignored in post-processing later
                    item = tableobj.get_by_id(filter.value)
                    items = (item and [item]) or []
            elif isinstance(items,list): # i.e. there is a single record!
                items = [i for i in items if filter.apply(
                        getattr(item,filter.name),filter.value)]
            else:
                if filter.name=='__key__' and filter.op != 'in':
                    items.order('__key__')
                items = items.filter('%s %s' % (filter.name,filter.op),
                                     filter.value)
        if not isinstance(items,list):
            if args_get('left', None):
                raise SyntaxError('Set: no left join in appengine')
            if args_get('groupby', None):
                raise SyntaxError('Set: no groupby in appengine')
            orderby = args_get('orderby', False)
            if orderby:
                ### THIS REALLY NEEDS IMPROVEMENT !!!
                if isinstance(orderby, (list, tuple)):
                    orderby = xorify(orderby)
                if isinstance(orderby,Expression):
                    orderby = self.expand(orderby)
                orders = orderby.split(', ')
                for order in orders:
                    order={'-id':'-__key__','id':'__key__'}.get(order,order)
                    items = items.order(order)
            if args_get('limitby', None):
                (lmin, lmax) = attributes['limitby']
                (limit, offset) = (lmax - lmin, lmin)
                rows = items.fetch(limit,offset=offset)
                #cursor is only useful if there was a limit and we didn't return
                # all results
                if args_get('reusecursor'):
                    db['_lastcursor'] = items.cursor()
                items = rows
        return (items, tablename, projection or db[tablename].fields)

    def select(self,query,fields,attributes):
        """
        This is the GAE version of select.  some notes to consider:
         - db['_lastsql'] is not set because there is not SQL statement string
           for a GAE query
         - 'nativeRef' is a magical fieldname used for self references on GAE
         - optional attribute 'projection' when set to True will trigger
           use of the GAE projection queries.  note that there are rules for
           what is accepted imposed by GAE: each field must be indexed,
           projection queries cannot contain blob or text fields, and you
           cannot use == and also select that same field.  see https://developers.google.com/appengine/docs/python/datastore/queries#Query_Projection
         - optional attribute 'filterfields' when set to True web2py will only
           parse the explicitly listed fields into the Rows object, even though
           all fields are returned in the query.  This can be used to reduce
           memory usage in cases where true projection queries are not
           usable.
         - optional attribute 'reusecursor' allows use of cursor with queries
           that have the limitby attribute.  Set the attribute to True for the
           first query, set it to the value of db['_lastcursor'] to continue
           a previous query.  The user must save the cursor value between
           requests, and the filters must be identical.  It is up to the user
           to follow google's limitations: https://developers.google.com/appengine/docs/python/datastore/queries#Query_Cursors
        """

        (items, tablename, fields) = self.select_raw(query,fields,attributes)
        # self.db['_lastsql'] = self._select(query,fields,attributes)
        rows = [[(t==self.db[tablename]._id.name and item) or \
                 (t=='nativeRef' and item) or getattr(item, t) \
                     for t in fields] for item in items]
        colnames = ['%s.%s' % (tablename, t) for t in fields]
        processor = attributes.get('processor',self.parse)
        return processor(rows,fields,colnames,False)

    def count(self,query,distinct=None,limit=None):
        if distinct:
            raise RuntimeError("COUNT DISTINCT not supported")
        (items, tablename, fields) = self.select_raw(query)
        # self.db['_lastsql'] = self._count(query)
        try:
            return len(items)
        except TypeError:
            return items.count(limit=limit)

    def delete(self,tablename, query):
        """
        This function was changed on 2010-05-04 because according to
        http://code.google.com/p/googleappengine/issues/detail?id=3119
        GAE no longer supports deleting more than 1000 records.
        """
        # self.db['_lastsql'] = self._delete(tablename,query)
        (items, tablename, fields) = self.select_raw(query)
        # items can be one item or a query
        if not isinstance(items,list):
            #use a keys_only query to ensure that this runs as a datastore
            # small operations
            leftitems = items.fetch(1000, keys_only=True)
            counter = 0
            while len(leftitems):
                counter += len(leftitems)
                gae.delete(leftitems)
                leftitems = items.fetch(1000, keys_only=True)
        else:
            counter = len(items)
            gae.delete(items)
        return counter

    def update(self,tablename,query,update_fields):
        # self.db['_lastsql'] = self._update(tablename,query,update_fields)
        (items, tablename, fields) = self.select_raw(query)
        counter = 0
        for item in items:
            for field, value in update_fields:
                setattr(item, field.name, self.represent(value,field.type))
            item.put()
            counter += 1
        LOGGER.info(str(counter))
        return counter

    def insert(self,table,fields):
        dfields=dict((f.name,self.represent(v,f.type)) for f,v in fields)
        # table._db['_lastsql'] = self._insert(table,fields)
        tmp = table._tableobj(**dfields)
        tmp.put()
        rid = Reference(tmp.key().id())
        (rid._table, rid._record, rid._gaekey) = (table, None, tmp.key())
        return rid

    def bulk_insert(self,table,items):
        parsed_items = []
        for item in items:
            dfields=dict((f.name,self.represent(v,f.type)) for f,v in item)
            parsed_items.append(table._tableobj(**dfields))
        gae.put(parsed_items)
        return True

def uuid2int(uuidv):
    return uuid.UUID(uuidv).int

def int2uuid(n):
    return str(uuid.UUID(int=n))

class CouchDBAdapter(NoSQLAdapter):
    drivers = ('couchdb',)

    uploads_in_blob = True
    types = {
                'boolean': bool,
                'string': str,
                'text': str,
                'json': str,
                'password': str,
                'blob': str,
                'upload': str,
                'integer': long,
                'bigint': long,
                'float': float,
                'double': float,
                'date': datetime.date,
                'time': datetime.time,
                'datetime': datetime.datetime,
                'id': long,
                'reference': long,
                'list:string': list,
                'list:integer': list,
                'list:reference': list,
        }

    def file_exists(self, filename): pass
    def file_open(self, filename, mode='rb', lock=True): pass
    def file_close(self, fileobj): pass

    def expand(self,expression,field_type=None):
        if isinstance(expression,Field):
            if expression.type=='id':
                return "%s._id" % expression.tablename
        return BaseAdapter.expand(self,expression,field_type)

    def AND(self,first,second):
        return '(%s && %s)' % (self.expand(first),self.expand(second))

    def OR(self,first,second):
        return '(%s || %s)' % (self.expand(first),self.expand(second))

    def EQ(self,first,second):
        if second is None:
            return '(%s == null)' % self.expand(first)
        return '(%s == %s)' % (self.expand(first),self.expand(second,first.type))

    def NE(self,first,second):
        if second is None:
            return '(%s != null)' % self.expand(first)
        return '(%s != %s)' % (self.expand(first),self.expand(second,first.type))

    def COMMA(self,first,second):
        return '%s + %s' % (self.expand(first),self.expand(second))

    def represent(self, obj, fieldtype):
        value = NoSQLAdapter.represent(self, obj, fieldtype)
        if fieldtype=='id':
            return repr(str(long(value)))
        elif fieldtype in ('date','time','datetime','boolean'):
            return serializers.json(value)
        return repr(not isinstance(value,unicode) and value \
                        or value and value.encode('utf8'))

    def __init__(self,db,uri='couchdb://127.0.0.1:5984',
                 pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.dbengine = 'couchdb'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self._after_connection = after_connection
        self.pool_size = pool_size

        url='http://'+uri[10:]
        def connector(url=url,driver_args=driver_args):
            return self.driver.Server(url,**driver_args)
        self.reconnect(connector,cursor=False)

    def create_table(self, table, migrate=True, fake_migrate=False, polymodel=None):
        if migrate:
            try:
                self.connection.create(table._tablename)
            except:
                pass

    def insert(self,table,fields):
        id = uuid2int(web2py_uuid())
        ctable = self.connection[table._tablename]
        values = dict((k.name,self.represent(v,k.type)) for k,v in fields)
        values['_id'] = str(id)
        ctable.save(values)
        return id

    def _select(self,query,fields,attributes):
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        for key in set(attributes.keys())-SELECT_ARGS:
            raise SyntaxError('invalid select attribute: %s' % key)
        new_fields=[]
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item._table
            else:
                new_fields.append(item)
        def uid(fd):
            return fd=='id' and '_id' or fd
        def get(row,fd):
            return fd=='id' and long(row['_id']) or row.get(fd,None)
        fields = new_fields
        tablename = self.get_table(query)
        fieldnames = [f.name for f in (fields or self.db[tablename])]
        colnames = ['%s.%s' % (tablename,k) for k in fieldnames]
        fields = ','.join(['%s.%s' % (tablename,uid(f)) for f in fieldnames])
        fn="(function(%(t)s){if(%(query)s)emit(%(order)s,[%(fields)s]);})" %\
            dict(t=tablename,
                 query=self.expand(query),
                 order='%s._id' % tablename,
                 fields=fields)
        return fn, colnames

    def select(self,query,fields,attributes):
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        fn, colnames = self._select(query,fields,attributes)
        tablename = colnames[0].split('.')[0]
        ctable = self.connection[tablename]
        rows = [cols['value'] for cols in ctable.query(fn)]
        processor = attributes.get('processor',self.parse)
        return processor(rows,fields,colnames,False)

    def delete(self,tablename,query):
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        if query.first.type=='id' and query.op==self.EQ:
            id = query.second
            tablename = query.first.tablename
            assert(tablename == query.first.tablename)
            ctable = self.connection[tablename]
            try:
                del ctable[str(id)]
                return 1
            except couchdb.http.ResourceNotFound:
                return 0
        else:
            tablename = self.get_table(query)
            rows = self.select(query,[self.db[tablename]._id],{})
            ctable = self.connection[tablename]
            for row in rows:
                del ctable[str(row.id)]
            return len(rows)

    def update(self,tablename,query,fields):
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        if query.first.type=='id' and query.op==self.EQ:
            id = query.second
            tablename = query.first.tablename
            ctable = self.connection[tablename]
            try:
                doc = ctable[str(id)]
                for key,value in fields:
                    doc[key.name] = self.represent(value,self.db[tablename][key.name].type)
                ctable.save(doc)
                return 1
            except couchdb.http.ResourceNotFound:
                return 0
        else:
            tablename = self.get_table(query)
            rows = self.select(query,[self.db[tablename]._id],{})
            ctable = self.connection[tablename]
            table = self.db[tablename]
            for row in rows:
                doc = ctable[str(row.id)]
                for key,value in fields:
                    doc[key.name] = self.represent(value,table[key.name].type)
                ctable.save(doc)
            return len(rows)

    def count(self,query,distinct=None):
        if distinct:
            raise RuntimeError("COUNT DISTINCT not supported")
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        tablename = self.get_table(query)
        rows = self.select(query,[self.db[tablename]._id],{})
        return len(rows)

def cleanup(text):
    """
    validates that the given text is clean: only contains [0-9a-zA-Z_]
    """
    if not REGEX_ALPHANUMERIC.match(text):
        raise SyntaxError('invalid table or field name: %s' % text)
    return text

class MongoDBAdapter(NoSQLAdapter):
    native_json = True
    drivers = ('pymongo',)

    uploads_in_blob = True

    types = {
                'boolean': bool,
                'string': str,
                'text': str,
                'json': str,
                'password': str,
                'blob': str,
                'upload': str,
                'integer': long,
                'bigint': long,
                'float': float,
                'double': float,
                'date': datetime.date,
                'time': datetime.time,
                'datetime': datetime.datetime,
                'id': long,
                'reference': long,
                'list:string': list,
                'list:integer': list,
                'list:reference': list,
        }

    error_messages = {"javascript_needed": "This must yet be replaced" +
                      " with javascript in order to work."}

    def __init__(self,db,uri='mongodb://127.0.0.1:5984/db',
                 pool_size=0, folder=None, db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):

        self.db = db
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        import random
        from bson.objectid import ObjectId
        from bson.son import SON
        import pymongo.uri_parser

        m = pymongo.uri_parser.parse_uri(uri)

        self.SON = SON
        self.ObjectId = ObjectId
        self.random = random

        self.dbengine = 'mongodb'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self._after_connection = after_connection
        self.pool_size = pool_size
        #this is the minimum amount of replicates that it should wait
        # for on insert/update
        self.minimumreplication = adapter_args.get('minimumreplication',0)
        # by default all inserts and selects are performand asynchronous,
        # but now the default is
        # synchronous, except when overruled by either this default or
        # function parameter
        self.safe = adapter_args.get('safe',True)

        if isinstance(m,tuple):
            m = {"database" : m[1]}
        if m.get('database')==None:
            raise SyntaxError("Database is required!")

        def connector(uri=self.uri,m=m):
            # Connection() is deprecated
            if hasattr(self.driver, "MongoClient"):
                Connection = self.driver.MongoClient
            else:
                Connection = self.driver.Connection
            return Connection(uri)[m.get('database')]

        self.reconnect(connector,cursor=False)

    def object_id(self, arg=None):
        """ Convert input to a valid Mongodb ObjectId instance

        self.object_id("<random>") -> ObjectId (not unique) instance """
        if not arg:
            arg = 0
        if isinstance(arg, basestring):
            # we assume an integer as default input
            rawhex = len(arg.replace("0x", "").replace("L", "")) == 24
            if arg.isdigit() and (not rawhex):
                arg = int(arg)
            elif arg == "<random>":
                arg = int("0x%sL" % \
                "".join([self.random.choice("0123456789abcdef") \
                for x in range(24)]), 0)
            elif arg.isalnum():
                if not arg.startswith("0x"):
                    arg = "0x%s" % arg
                try:
                    arg = int(arg, 0)
                except ValueError, e:
                    raise ValueError(
                            "invalid objectid argument string: %s" % e)
            else:
                raise ValueError("Invalid objectid argument string. " +
                                 "Requires an integer or base 16 value")
        elif isinstance(arg, self.ObjectId):
            return arg

        if not isinstance(arg, (int, long)):
            raise TypeError("object_id argument must be of type " +
                            "ObjectId or an objectid representable integer")
        if arg == 0:
            hexvalue = "".zfill(24)
        else:
            hexvalue = hex(arg)[2:].replace("L", "")
        return self.ObjectId(hexvalue)

    def parse_reference(self, value, field_type):
        # here we have to check for ObjectID before base parse
        if isinstance(value, self.ObjectId):
            value = long(str(value), 16)
        return super(MongoDBAdapter,
                     self).parse_reference(value, field_type)

    def parse_id(self, value, field_type):
        if isinstance(value, self.ObjectId):
            value = long(str(value), 16)
        return super(MongoDBAdapter,
                     self).parse_id(value, field_type)

    def represent(self, obj, fieldtype):
        # the base adatpter does not support MongoDB ObjectId
        if isinstance(obj, self.ObjectId):
            value = obj
        else:
            value = NoSQLAdapter.represent(self, obj, fieldtype)
        # reference types must be convert to ObjectID
        if fieldtype  =='date':
            if value == None:
                return value
            # this piece of data can be stripped off based on the fieldtype
            t = datetime.time(0, 0, 0)
            # mongodb doesn't has a date object and so it must datetime,
            # string or integer
            return datetime.datetime.combine(value, t)
        elif fieldtype == 'time':
            if value == None:
                return value
            # this piece of data can be stripped of based on the fieldtype
            d = datetime.date(2000, 1, 1)
            # mongodb doesn't has a  time object and so it must datetime,
            # string or integer
            return datetime.datetime.combine(d, value)
        elif (isinstance(fieldtype, basestring) and
              fieldtype.startswith('list:')):
            if fieldtype.startswith('list:reference'):
                newval = []
                for v in value:
                    newval.append(self.object_id(v))
                return newval
            return value
        elif ((isinstance(fieldtype, basestring) and
               fieldtype.startswith("reference")) or
               (isinstance(fieldtype, Table)) or fieldtype=="id"):
            value = self.object_id(value)
        return value

    def create_table(self, table, migrate=True, fake_migrate=False,
                     polymodel=None, isCapped=False):
        if isCapped:
            raise RuntimeError("Not implemented")

    def count(self, query, distinct=None, snapshot=True):
        if distinct:
            raise RuntimeError("COUNT DISTINCT not supported")
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        tablename = self.get_table(query)
        return long(self.select(query,[self.db[tablename]._id], {},
                                count=True,snapshot=snapshot)['count'])
        # Maybe it would be faster if we just implemented the pymongo
        # .count() function which is probably quicker?
        # therefor call __select() connection[table].find(query).count()
        # Since this will probably reduce the return set?

    def expand(self, expression, field_type=None):
        if isinstance(expression, Query):
            # any query using 'id':=
            # set name as _id (as per pymongo/mongodb primary key)
            # convert second arg to an objectid field
            # (if its not already)
            # if second arg is 0 convert to objectid
            if isinstance(expression.first,Field) and \
                    ((expression.first.type == 'id') or \
                    ("reference" in expression.first.type)):
                if expression.first.type == 'id':
                    expression.first.name = '_id'
                # cast to Mongo ObjectId
                if isinstance(expression.second, (tuple, list, set)):
                    expression.second = [self.object_id(item) for
                                         item in expression.second]
                else:
                    expression.second = self.object_id(expression.second)
                result = expression.op(expression.first, expression.second)

        if isinstance(expression, Field):
            if expression.type=='id':
                result = "_id"
            else:
                result =  expression.name
        elif isinstance(expression, (Expression, Query)):
            if not expression.second is None:
                result = expression.op(expression.first, expression.second)
            elif not expression.first is None:
                result = expression.op(expression.first)
            elif not isinstance(expression.op, str):
                result = expression.op()
            else:
                result = expression.op
        elif field_type:
            result = self.represent(expression,field_type)
        elif isinstance(expression,(list,tuple)):
            result = ','.join(self.represent(item,field_type) for
                              item in expression)
        else:
            result = expression
        return result

    def drop(self, table, mode=''):
        ctable = self.connection[table._tablename]
        ctable.drop()

    def truncate(self, table, mode, safe=None):
        if safe == None:
            safe=self.safe
        ctable = self.connection[table._tablename]
        ctable.remove(None, safe=True)

    def _select(self, query, fields, attributes):
        if 'for_update' in attributes:
            logging.warn('mongodb does not support for_update')
        for key in set(attributes.keys())-set(('limitby',
                                               'orderby','for_update')):
            if attributes[key]!=None:
                logging.warn('select attribute not implemented: %s' % key)

        new_fields=[]
        mongosort_list = []

        # try an orderby attribute
        orderby = attributes.get('orderby', False)
        limitby = attributes.get('limitby', False)
        # distinct = attributes.get('distinct', False)
        if orderby:
            if isinstance(orderby, (list, tuple)):
                orderby = xorify(orderby)

            # !!!! need to add 'random'
            for f in self.expand(orderby).split(','):
                if f.startswith('-'):
                    mongosort_list.append((f[1:], -1))
                else:
                    mongosort_list.append((f, 1))
        if limitby:
            limitby_skip, limitby_limit = limitby
        else:
            limitby_skip = limitby_limit = 0

        mongofields_dict = self.SON()
        mongoqry_dict = {}
        for item in fields:
            if isinstance(item, SQLALL):
                new_fields += item._table
            else:
                new_fields.append(item)
        fields = new_fields
        if isinstance(query,Query):
            tablename = self.get_table(query)
        elif len(fields) != 0:
            tablename = fields[0].tablename
        else:
            raise SyntaxError("The table name could not be found in " +
                              "the query nor from the select statement.")
        mongoqry_dict = self.expand(query)
        fields = fields or self.db[tablename]
        for field in fields:
            mongofields_dict[field.name] = 1

        return tablename, mongoqry_dict, mongofields_dict, mongosort_list, \
            limitby_limit, limitby_skip

    def select(self, query, fields, attributes, count=False,
               snapshot=False):
        # TODO: support joins
        tablename, mongoqry_dict, mongofields_dict, mongosort_list, \
        limitby_limit, limitby_skip = self._select(query, fields, attributes)
        ctable = self.connection[tablename]

        if count:
            return {'count' : ctable.find(
                    mongoqry_dict, mongofields_dict,
                    skip=limitby_skip, limit=limitby_limit,
                    sort=mongosort_list, snapshot=snapshot).count()}
        else:
            # pymongo cursor object
            mongo_list_dicts = ctable.find(mongoqry_dict,
                                mongofields_dict, skip=limitby_skip,
                                limit=limitby_limit, sort=mongosort_list,
                                snapshot=snapshot)
        rows = []
        # populate row in proper order
        # Here we replace ._id with .id to follow the standard naming
        colnames = []
        newnames = []
        for field in fields:
            colname = str(field)
            colnames.append(colname)
            tablename, fieldname = colname.split(".")
            if fieldname == "_id":
                # Mongodb reserved uuid key
                field.name = "id"
            newnames.append(".".join((tablename, field.name)))

        for record in mongo_list_dicts:
            row=[]
            for colname in colnames:
                tablename, fieldname = colname.split(".")
                # switch to Mongo _id uuids for retrieving
                # record id's
                if fieldname == "id": fieldname = "_id"
                if fieldname in record:
                    value = record[fieldname]
                else:
                    value = None
                row.append(value)
            rows.append(row)

        processor = attributes.get('processor', self.parse)
        result = processor(rows, fields, newnames, False)
        return result

    def _insert(self, table, fields):
        values = dict()
        for k, v in fields:
            if not k.name in ["id", "safe"]:
                fieldname = k.name
                fieldtype = table[k.name].type
                values[fieldname] = self.represent(v, fieldtype)
        return values

    # Safe determines whether a asynchronious request is done or a
    # synchronious action is done
    # For safety, we use by default synchronous requests
    def insert(self, table, fields, safe=None):
        if safe==None:
            safe = self.safe
        ctable = self.connection[table._tablename]
        values = self._insert(table, fields)
        ctable.insert(values, safe=safe)
        return long(str(values['_id']), 16)

    #this function returns a dict with the where clause and update fields
    def _update(self, tablename, query, fields):
        if not isinstance(query, Query):
            raise SyntaxError("Not Supported")
        filter = None
        if query:
            filter = self.expand(query)
        modify = {'$set': dict((k.name, self.represent(v, k.type)) for
                  k, v in fields)}
        return modify, filter

    def update(self, tablename, query, fields, safe=None):
        if safe == None:
            safe = self.safe
        # return amount of adjusted rows or zero, but no exceptions
        # @ related not finding the result
        if not isinstance(query, Query):
            raise RuntimeError("Not implemented")
        amount = self.count(query, False)
        modify, filter = self._update(tablename, query, fields)
        try:
            result = self.connection[tablename].update(filter,
                       modify, multi=True, safe=safe)
            if safe:
                try:
                    # if result count is available fetch it
                    return result["n"]
                except (KeyError, AttributeError, TypeError):
                    return amount
            else:
                return amount
        except Exception, e:
            # TODO Reverse update query to verifiy that the query succeded
            raise RuntimeError("uncaught exception when updating rows: %s" % e)

    def _delete(self, tablename, query):
        if not isinstance(query, Query):
            raise RuntimeError("query type %s is not supported" % \
                               type(query))
        return self.expand(query)

    def delete(self, tablename, query, safe=None):
        if safe is None:
            safe = self.safe
        amount = 0
        amount = self.count(query, False)
        filter = self._delete(tablename, query)
        self.connection[tablename].remove(filter, safe=safe)
        return amount

    def bulk_insert(self, table, items):
        return [self.insert(table,item) for item in items]

    ## OPERATORS
    def INVERT(self, first):
        #print "in invert first=%s" % first
        return '-%s' % self.expand(first)

    # TODO This will probably not work:(
    def NOT(self, first):
        result = {}
        result["$not"] = self.expand(first)
        return result

    def AND(self,first,second):
        f = self.expand(first)
        s = self.expand(second)
        f.update(s)
        return f

    def OR(self,first,second):
        # pymongo expects: .find({'$or': [{'name':'1'}, {'name':'2'}]})
        result = {}
        f = self.expand(first)
        s = self.expand(second)
        result['$or'] = [f,s]
        return result

    def BELONGS(self, first, second):
        if isinstance(second, str):
            return {self.expand(first) : {"$in" : [ second[:-1]]} }
        elif second==[] or second==() or second==set():
            return {1:0}
        items = [self.expand(item, first.type) for item in second]
        return {self.expand(first) : {"$in" : items} }

    def EQ(self,first,second):
        result = {}
        result[self.expand(first)] = self.expand(second)
        return result

    def NE(self, first, second=None):
        result = {}
        result[self.expand(first)] = {'$ne': self.expand(second)}
        return result

    def LT(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s < None" % first)
        result = {}
        result[self.expand(first)] = {'$lt': self.expand(second)}
        return result

    def LE(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s <= None" % first)
        result = {}
        result[self.expand(first)] = {'$lte': self.expand(second)}
        return result

    def GT(self,first,second):
        result = {}
        result[self.expand(first)] = {'$gt': self.expand(second)}
        return result

    def GE(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s >= None" % first)
        result = {}
        result[self.expand(first)] = {'$gte': self.expand(second)}
        return result

    def ADD(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '%s + %s' % (self.expand(first),
                            self.expand(second, first.type))

    def SUB(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '(%s - %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MUL(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '(%s * %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def DIV(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '(%s / %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MOD(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '(%s %% %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def AS(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '%s AS %s' % (self.expand(first), second)

    # We could implement an option that simulates a full featured SQL
    # database. But I think the option should be set explicit or
    # implemented as another library.
    def ON(self, first, second):
        raise NotImplementedError("This is not possible in NoSQL" +
                                  " but can be simulated with a wrapper.")
        return '%s ON %s' % (self.expand(first), self.expand(second))

    # BLOW ARE TWO IMPLEMENTATIONS OF THE SAME FUNCITONS
    # WHICH ONE IS BEST?

    def COMMA(self, first, second):
        return '%s, %s' % (self.expand(first), self.expand(second))

    def LIKE(self, first, second):
        #escaping regex operators?
        return {self.expand(first): ('%s' % \
                self.expand(second, 'string').replace('%','/'))}

    def STARTSWITH(self, first, second):
        #escaping regex operators?
        return {self.expand(first): ('/^%s/' % \
        self.expand(second, 'string'))}

    def ENDSWITH(self, first, second):
        #escaping regex operators?
        return {self.expand(first): ('/%s^/' % \
        self.expand(second, 'string'))}

    def CONTAINS(self, first, second, case_sensitive=False):
        # silently ignore, only case sensitive
        # There is a technical difference, but mongodb doesn't support
        # that, but the result will be the same
        val = second if isinstance(second,self.ObjectId) else \
            {'$regex':".*" + re.escape(self.expand(second, 'string')) + ".*"}
        return {self.expand(first) : val}

    def LIKE(self, first, second):
        import re
        return {self.expand(first): {'$regex': \
                re.escape(self.expand(second,
                                      'string')).replace('%','.*')}}

    #TODO verify full compatibilty with official SQL Like operator
    def STARTSWITH(self, first, second):
        #TODO  Solve almost the same problem as with endswith
        import re
        return {self.expand(first): {'$regex' : '^' +
                                     re.escape(self.expand(second,
                                                           'string'))}}

    #TODO verify full compatibilty with official SQL Like operator
    def ENDSWITH(self, first, second):
        #escaping regex operators?
        #TODO if searched for a name like zsa_corbitt and the function
        # is endswith('a') then this is also returned.
        # Aldo it end with a t
        import re
        return {self.expand(first): {'$regex': \
        re.escape(self.expand(second, 'string')) + '$'}}

    #TODO verify full compatibilty with official oracle contains operator
    def CONTAINS(self, first, second, case_sensitive=False):
        # silently ignore, only case sensitive
        #There is a technical difference, but mongodb doesn't support
        # that, but the result will be the same
        #TODO contains operators need to be transformed to Regex
        return {self.expand(first) : {'$regex': \
        ".*" + re.escape(self.expand(second, 'string')) + ".*"}}


class IMAPAdapter(NoSQLAdapter):
    drivers = ('imaplib',)

    """ IMAP server adapter

      This class is intended as an interface with
    email IMAP servers to perform simple queries in the
    web2py DAL query syntax, so email read, search and
    other related IMAP mail services (as those implemented
    by brands like Google(r), and Yahoo!(r)
    can be managed from web2py applications.

    The code uses examples by Yuji Tomita on this post:
    http://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/#comment-1137
    and is based in docs for Python imaplib, python email
    and email IETF's (i.e. RFC2060 and RFC3501)

    This adapter was tested with a small set of operations with Gmail(r). Other
    services requests could raise command syntax and response data issues.

    It creates its table and field names "statically",
    meaning that the developer should leave the table and field
    definitions to the DAL instance by calling the adapter's
    .define_tables() method. The tables are defined with the
    IMAP server mailbox list information.

    .define_tables() returns a dictionary mapping dal tablenames
    to the server mailbox names with the following structure:

    {<tablename>: str <server mailbox name>}

    Here is a list of supported fields:

    Field       Type            Description
    ################################################################
    uid         string
    answered    boolean        Flag
    created     date
    content     list:string    A list of text or html parts
    to          string
    cc          string
    bcc         string
    size        integer        the amount of octets of the message*
    deleted     boolean        Flag
    draft       boolean        Flag
    flagged     boolean        Flag
    sender      string
    recent      boolean        Flag
    seen        boolean        Flag
    subject     string
    mime        string         The mime header declaration
    email       string         The complete RFC822 message**
    attachments <type list>    Each non text part as dict
    encoding    string         The main detected encoding

    *At the application side it is measured as the length of the RFC822
    message string

    WARNING: As row id's are mapped to email sequence numbers,
    make sure your imap client web2py app does not delete messages
    during select or update actions, to prevent
    updating or deleting different messages.
    Sequence numbers change whenever the mailbox is updated.
    To avoid this sequence numbers issues, it is recommended the use
    of uid fields in query references (although the update and delete
    in separate actions rule still applies).

    # This is the code recommended to start imap support
    # at the app's model:

    imapdb = DAL("imap://user:password@server:port", pool_size=1) # port 993 for ssl
    imapdb.define_tables()

    Here is an (incomplete) list of possible imap commands:

    # Count today's unseen messages
    # smaller than 6000 octets from the
    # inbox mailbox

    q = imapdb.INBOX.seen == False
    q &= imapdb.INBOX.created == datetime.date.today()
    q &= imapdb.INBOX.size < 6000
    unread = imapdb(q).count()

    # Fetch last query messages
    rows = imapdb(q).select()

    # it is also possible to filter query select results with limitby and
    # sequences of mailbox fields

    set.select(<fields sequence>, limitby=(<int>, <int>))

    # Mark last query messages as seen
    messages = [row.uid for row in rows]
    seen = imapdb(imapdb.INBOX.uid.belongs(messages)).update(seen=True)

    # Delete messages in the imap database that have mails from mr. Gumby

    deleted = 0
    for mailbox in imapdb.tables
        deleted += imapdb(imapdb[mailbox].sender.contains("gumby")).delete()

    # It is possible also to mark messages for deletion instead of ereasing them
    # directly with set.update(deleted=True)


    # This object give access
    # to the adapter auto mailbox
    # mapped names (which native
    # mailbox has what table name)

    imapdb.mailboxes <dict> # tablename, server native name pairs

    # To retrieve a table native mailbox name use:
    imapdb.<table>.mailbox

    ### New features v2.4.1:

    # Declare mailboxes statically with tablename, name pairs
    # This avoids the extra server names retrieval

    imapdb.define_tables({"inbox": "INBOX"})

    # Selects without content/attachments/email columns will only
    # fetch header and flags

    imapdb(q).select(imapdb.INBOX.sender, imapdb.INBOX.subject)
    """

    types = {
                'string': str,
                'text': str,
                'date': datetime.date,
                'datetime': datetime.datetime,
                'id': long,
                'boolean': bool,
                'integer': int,
                'bigint': long,
                'blob': str,
                'list:string': str,
        }

    dbengine = 'imap'

    REGEX_URI = re.compile('^(?P<user>[^:]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:@]+)(\:(?P<port>[0-9]+))?$')

    def __init__(self,
                 db,
                 uri,
                 pool_size=0,
                 folder=None,
                 db_codec ='UTF-8',
                 credential_decoder=IDENTITY,
                 driver_args={},
                 adapter_args={},
                 do_connect=True,
                 after_connection=None):

        # db uri: user@example.com:password@imap.server.com:123
        # TODO: max size adapter argument for preventing large mail transfers

        self.db = db
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.pool_size=pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.credential_decoder = credential_decoder
        self.driver_args = driver_args
        self.adapter_args = adapter_args
        self.mailbox_size = None
        self.static_names = None
        self.charset = sys.getfilesystemencoding()
        # imap class
        self.imap4 = None
        uri = uri.split("://")[1]

        """ MESSAGE is an identifier for sequence number"""

        self.flags = ['\\Deleted', '\\Draft', '\\Flagged',
                      '\\Recent', '\\Seen', '\\Answered']
        self.search_fields = {
            'id': 'MESSAGE', 'created': 'DATE',
            'uid': 'UID', 'sender': 'FROM',
            'to': 'TO', 'cc': 'CC',
            'bcc': 'BCC', 'content': 'TEXT',
            'size': 'SIZE', 'deleted': '\\Deleted',
            'draft': '\\Draft', 'flagged': '\\Flagged',
            'recent': '\\Recent', 'seen': '\\Seen',
            'subject': 'SUBJECT', 'answered': '\\Answered',
            'mime': None, 'email': None,
            'attachments': None
            }

        db['_lastsql'] = ''

        m = self.REGEX_URI.match(uri)
        user = m.group('user')
        password = m.group('password')
        host = m.group('host')
        port = int(m.group('port'))
        over_ssl = False
        if port==993:
            over_ssl = True

        driver_args.update(host=host,port=port, password=password, user=user)
        def connector(driver_args=driver_args):
            # it is assumed sucessful authentication alLways
            # TODO: support direct connection and login tests
            if over_ssl:
                self.imap4 = self.driver.IMAP4_SSL
            else:
                self.imap4 = self.driver.IMAP4
            connection = self.imap4(driver_args["host"], driver_args["port"])
            data = connection.login(driver_args["user"], driver_args["password"])

            # static mailbox list
            connection.mailbox_names = None

            # dummy cursor function
            connection.cursor = lambda : True

            return connection

        self.db.define_tables = self.define_tables
        self.connector = connector
        if do_connect: self.reconnect()

    def reconnect(self, f=None, cursor=True):
        """
        IMAP4 Pool connection method

        imap connection lacks of self cursor command.
        A custom command should be provided as a replacement
        for connection pooling to prevent uncaught remote session
        closing

        """
        if getattr(self,'connection',None) != None:
            return
        if f is None:
            f = self.connector

        if not self.pool_size:
            self.connection = f()
            self.cursor = cursor and self.connection.cursor()
        else:
            POOLS = ConnectionPool.POOLS
            uri = self.uri
            while True:
                GLOBAL_LOCKER.acquire()
                if not uri in POOLS:
                    POOLS[uri] = []
                if POOLS[uri]:
                    self.connection = POOLS[uri].pop()
                    GLOBAL_LOCKER.release()
                    self.cursor = cursor and self.connection.cursor()
                    if self.cursor and self.check_active_connection:
                        try:
                            # check if connection is alive or close it
                            result, data = self.connection.list()
                        except:
                            # Possible connection reset error
                            # TODO: read exception class
                            self.connection = f()
                    break
                else:
                    GLOBAL_LOCKER.release()
                    self.connection = f()
                    self.cursor = cursor and self.connection.cursor()
                    break
        self.after_connection_hook()

    def get_last_message(self, tablename):
        last_message = None
        # request mailbox list to the server
        # if needed
        if not isinstance(self.connection.mailbox_names, dict):
            self.get_mailboxes()
        try:
            result = self.connection.select(self.connection.mailbox_names[tablename])
            last_message = int(result[1][0])
        except (IndexError, ValueError, TypeError, KeyError):
            e = sys.exc_info()[1]
            LOGGER.debug("Error retrieving the last mailbox sequence number. %s" % str(e))
        return last_message

    def get_uid_bounds(self, tablename):
        if not isinstance(self.connection.mailbox_names, dict):
            self.get_mailboxes()
        # fetch first and last messages
        # return (first, last) messages uid's
        last_message = self.get_last_message(tablename)
        result, data = self.connection.uid("search", None, "(ALL)")
        uid_list = data[0].strip().split()
        if len(uid_list) <= 0:
            return None
        else:
            return (uid_list[0], uid_list[-1])

    def convert_date(self, date, add=None):
        if add is None:
            add = datetime.timedelta()
        """ Convert a date object to a string
        with d-Mon-Y style for IMAP or the inverse
        case

        add <timedelta> adds to the date object
        """
        months = [None, "JAN","FEB","MAR","APR","MAY","JUN",
                  "JUL", "AUG","SEP","OCT","NOV","DEC"]
        if isinstance(date, basestring):
            # Prevent unexpected date response format
            try:
                dayname, datestring = date.split(",")
                date_list = datestring.strip().split()
                year = int(date_list[2])
                month = months.index(date_list[1].upper())
                day = int(date_list[0])
                hms = map(int, date_list[3].split(":"))
                return datetime.datetime(year, month, day,
                    hms[0], hms[1], hms[2]) + add
            except (ValueError, AttributeError, IndexError), e:
                LOGGER.error("Could not parse date text: %s. %s" %
                             (date, e))
                return None
        elif isinstance(date, (datetime.datetime, datetime.date)):
            return (date + add).strftime("%d-%b-%Y")
        else:
            return None

    @staticmethod
    def header_represent(f, r):
        from email.header import decode_header
        text, encoding = decode_header(f)[0]
        if encoding:
            text = text.decode(encoding).encode('utf-8')
        return text

    def encode_text(self, text, charset, errors="replace"):
        """ convert text for mail to unicode"""
        if text is None:
            text = ""
        else:
            if isinstance(text, str):
                if charset is None:
                    text = unicode(text, "utf-8", errors)
                else:
                    text = unicode(text, charset, errors)
            else:
                raise Exception("Unsupported mail text type %s" % type(text))
        return text.encode("utf-8")

    def get_charset(self, message):
        charset = message.get_content_charset()
        return charset

    def get_mailboxes(self):
        """ Query the mail database for mailbox names """
        if self.static_names:
            # statically defined mailbox names
            self.connection.mailbox_names = self.static_names
            return self.static_names.keys()

        mailboxes_list = self.connection.list()
        self.connection.mailbox_names = dict()
        mailboxes = list()
        x = 0
        for item in mailboxes_list[1]:
            x = x + 1
            item = item.strip()
            if not "NOSELECT" in item.upper():
                sub_items = item.split("\"")
                sub_items = [sub_item for sub_item in sub_items \
                if len(sub_item.strip()) > 0]
                # mailbox = sub_items[len(sub_items) -1]
                mailbox = sub_items[-1]
                # remove unwanted characters and store original names
                # Don't allow leading non alphabetic characters
                mailbox_name = re.sub('^[_0-9]*', '', re.sub('[^_\w]','',re.sub('[/ ]','_',mailbox)))
                mailboxes.append(mailbox_name)
                self.connection.mailbox_names[mailbox_name] = mailbox

        return mailboxes

    def get_query_mailbox(self, query):
        nofield = True
        tablename = None
        attr = query
        while nofield:
            if hasattr(attr, "first"):
                attr = attr.first
                if isinstance(attr, Field):
                    return attr.tablename
                elif isinstance(attr, Query):
                    pass
                else:
                    return None
            else:
                return None
        return tablename

    def is_flag(self, flag):
        if self.search_fields.get(flag, None) in self.flags:
            return True
        else:
            return False

    def define_tables(self, mailbox_names=None):
        """
        Auto create common IMAP fileds

        This function creates fields definitions "statically"
        meaning that custom fields as in other adapters should
        not be supported and definitions handled on a service/mode
        basis (local syntax for Gmail(r), Ymail(r)

        Returns a dictionary with tablename, server native mailbox name
        pairs.
        """
        if mailbox_names:
            # optional statically declared mailboxes
            self.static_names = mailbox_names
        else:
            self.static_names = None
        if not isinstance(self.connection.mailbox_names, dict):
            self.get_mailboxes()

        names = self.connection.mailbox_names.keys()

        for name in names:
            self.db.define_table("%s" % name,
                            Field("uid", "string", writable=False),
                            Field("answered", "boolean"),
                            Field("created", "datetime", writable=False),
                            Field("content", "list:string", writable=False),
                            Field("to", "string", writable=False),
                            Field("cc", "string", writable=False),
                            Field("bcc", "string", writable=False),
                            Field("size", "integer", writable=False),
                            Field("deleted", "boolean"),
                            Field("draft", "boolean"),
                            Field("flagged", "boolean"),
                            Field("sender", "string", writable=False),
                            Field("recent", "boolean", writable=False),
                            Field("seen", "boolean"),
                            Field("subject", "string", writable=False),
                            Field("mime", "string", writable=False),
                            Field("email", "string", writable=False, readable=False),
                            Field("attachments", list, writable=False, readable=False),
                            Field("encoding", writable=False)
                            )

            # Set a special _mailbox attribute for storing
            # native mailbox names
            self.db[name].mailbox = \
                self.connection.mailbox_names[name]

            # decode quoted printable
            self.db[name].to.represent = self.db[name].cc.represent = \
            self.db[name].bcc.represent = self.db[name].sender.represent = \
            self.db[name].subject.represent = self.header_represent

        # Set the db instance mailbox collections
        self.db.mailboxes = self.connection.mailbox_names
        return self.db.mailboxes

    def create_table(self, *args, **kwargs):
        # not implemented
        # but required by DAL
        pass

    def _select(self, query, fields, attributes):
        if use_common_filters(query):
            query = self.common_filter(query, [self.get_query_mailbox(query),])
        return str(query)

    def select(self, query, fields, attributes):
        """  Search and Fetch records and return web2py rows
        """
        # move this statement elsewhere (upper-level)
        if use_common_filters(query):
            query = self.common_filter(query, [self.get_query_mailbox(query),])

        import email
        # get records from imap server with search + fetch
        # convert results to a dictionary
        tablename = None
        fetch_results = list()

        if isinstance(query, Query):
            tablename = self.get_table(query)
            mailbox = self.connection.mailbox_names.get(tablename, None)
            if mailbox is None:
                 raise ValueError("Mailbox name not found: %s" % mailbox)
            else:
                # select with readonly
                result, selected = self.connection.select(mailbox, True)
                if result != "OK":
                    raise Exception("IMAP error: %s" % selected)
                self.mailbox_size = int(selected[0])
                search_query = "(%s)" % str(query).strip()
                search_result = self.connection.uid("search", None, search_query)
                # Normal IMAP response OK is assumed (change this)
                if search_result[0] == "OK":
                    # For "light" remote server responses just get the first
                    # ten records (change for non-experimental implementation)
                    # However, light responses are not guaranteed with this
                    # approach, just fewer messages.
                    limitby = attributes.get('limitby', None)
                    messages_set = search_result[1][0].split()
                    # descending order
                    messages_set.reverse()
                    if limitby is not None:
                        # TODO: orderby, asc/desc, limitby from complete message set
                        messages_set = messages_set[int(limitby[0]):int(limitby[1])]

                    # keep the requests small for header/flags
                    if any([(field.name in ["content", "size",
                                            "attachments", "email"]) for
                           field in fields]):
                        imap_fields = "(RFC822 FLAGS)"
                    else:
                        imap_fields = "(RFC822.HEADER FLAGS)"

                    if len(messages_set) > 0:
                        # create fetch results object list
                        # fetch each remote message and store it in memmory
                        # (change to multi-fetch command syntax for faster
                        # transactions)
                        for uid in messages_set:
                            # fetch the RFC822 message body
                            typ, data = self.connection.uid("fetch", uid, imap_fields)
                            if typ == "OK":
                                fr = {"message": int(data[0][0].split()[0]),
                                      "uid": long(uid),
                                      "email": email.message_from_string(data[0][1]),
                                      "raw_message": data[0][1]}
                                fr["multipart"] = fr["email"].is_multipart()
                                # fetch flags for the message
                                fr["flags"] = self.driver.ParseFlags(data[1])
                                fetch_results.append(fr)
                            else:
                                # error retrieving the message body
                                raise Exception("IMAP error retrieving the body: %s" % data)
                else:
                    raise Exception("IMAP search error: %s" % search_result[1])
        elif isinstance(query, (Expression, basestring)):
            raise NotImplementedError()
        else:
            raise TypeError("Unexpected query type")

        imapqry_dict = {}
        imapfields_dict = {}

        if len(fields) == 1 and isinstance(fields[0], SQLALL):
            allfields = True
        elif len(fields) == 0:
            allfields = True
        else:
            allfields = False
        if allfields:
            colnames = ["%s.%s" % (tablename, field) for field in self.search_fields.keys()]
        else:
            colnames = ["%s.%s" % (tablename, field.name) for field in fields]

        for k in colnames:
            imapfields_dict[k] = k

        imapqry_list = list()
        imapqry_array = list()
        for fr in fetch_results:
            attachments = []
            content = []
            size = 0
            n = int(fr["message"])
            item_dict = dict()
            message = fr["email"]
            uid = fr["uid"]
            charset = self.get_charset(message)
            flags = fr["flags"]
            raw_message = fr["raw_message"]
            # Return messages data mapping static fields
            # and fetched results. Mapping should be made
            # outside the select function (with auxiliary
            # instance methods)

            # pending: search flags states trough the email message
            # instances for correct output

            # preserve subject encoding (ASCII/quoted printable)

            if "%s.id" % tablename in colnames:
                item_dict["%s.id" % tablename] = n
            if "%s.created" % tablename in colnames:
                item_dict["%s.created" % tablename] = self.convert_date(message["Date"])
            if "%s.uid" % tablename in colnames:
                item_dict["%s.uid" % tablename] = uid
            if "%s.sender" % tablename in colnames:
                # If there is no encoding found in the message header
                # force utf-8 replacing characters (change this to
                # module's defaults). Applies to .sender, .to, .cc and .bcc fields
                item_dict["%s.sender" % tablename] = message["From"]
            if "%s.to" % tablename in colnames:
                item_dict["%s.to" % tablename] = message["To"]
            if "%s.cc" % tablename in colnames:
                if "Cc" in message.keys():
                    item_dict["%s.cc" % tablename] = message["Cc"]
                else:
                    item_dict["%s.cc" % tablename] = ""
            if "%s.bcc" % tablename in colnames:
                if "Bcc" in message.keys():
                    item_dict["%s.bcc" % tablename] = message["Bcc"]
                else:
                    item_dict["%s.bcc" % tablename] = ""
            if "%s.deleted" % tablename in colnames:
                item_dict["%s.deleted" % tablename] = "\\Deleted" in flags
            if "%s.draft" % tablename in colnames:
                item_dict["%s.draft" % tablename] = "\\Draft" in flags
            if "%s.flagged" % tablename in colnames:
                item_dict["%s.flagged" % tablename] = "\\Flagged" in flags
            if "%s.recent" % tablename in colnames:
                item_dict["%s.recent" % tablename] = "\\Recent" in flags
            if "%s.seen" % tablename in colnames:
                item_dict["%s.seen" % tablename] = "\\Seen" in flags
            if "%s.subject" % tablename in colnames:
                item_dict["%s.subject" % tablename] = message["Subject"]
            if "%s.answered" % tablename in colnames:
                item_dict["%s.answered" % tablename] = "\\Answered" in flags
            if "%s.mime" % tablename in colnames:
                item_dict["%s.mime" % tablename] = message.get_content_type()
            if "%s.encoding" % tablename in colnames:
                item_dict["%s.encoding" % tablename] = charset

            # Here goes the whole RFC822 body as an email instance
            # for controller side custom processing
            # The message is stored as a raw string
            # >> email.message_from_string(raw string)
            # returns a Message object for enhanced object processing
            if "%s.email" % tablename in colnames:
                # WARNING: no encoding performed (raw message)
                item_dict["%s.email" % tablename] = raw_message

            # Size measure as suggested in a Velocity Reviews post
            # by Tim Williams: "how to get size of email attachment"
            # Note: len() and server RFC822.SIZE reports doesn't match
            # To retrieve the server size for representation would add a new
            # fetch transaction to the process
            for part in message.walk():
                maintype = part.get_content_maintype()
                if ("%s.attachments" % tablename in colnames) or \
                   ("%s.content" % tablename in colnames):
                    if "%s.attachments" % tablename in colnames:
                        if not ("text" in maintype):
                            payload = part.get_payload(decode=True)
                            if payload:
                                attachment = {
                                    "payload": payload,
                                    "filename": part.get_filename(),
                                    "encoding": part.get_content_charset(),
                                    "mime": part.get_content_type(),
                                    "disposition": part["Content-Disposition"]}
                                attachments.append(attachment)
                    if "%s.content" % tablename in colnames:
                        payload = part.get_payload(decode=True)
                        part_charset = self.get_charset(part)
                        if "text" in maintype:
                            if payload:
                                content.append(self.encode_text(payload, part_charset))
                if "%s.size" % tablename in colnames:
                    if part is not None:
                        size += len(str(part))
            item_dict["%s.content" % tablename] = content
            item_dict["%s.attachments" % tablename] = attachments
            item_dict["%s.size" % tablename] = size
            imapqry_list.append(item_dict)

        # extra object mapping for the sake of rows object
        # creation (sends an array or lists)
        for item_dict in imapqry_list:
            imapqry_array_item = list()
            for fieldname in colnames:
                imapqry_array_item.append(item_dict[fieldname])
            imapqry_array.append(imapqry_array_item)

        # parse result and return a rows object
        colnames = colnames
        processor = attributes.get('processor',self.parse)
        return processor(imapqry_array, fields, colnames)

    def _update(self, tablename, query, fields, commit=False):
        # TODO: the adapter should implement an .expand method
        commands = list()
        if use_common_filters(query):
            query = self.common_filter(query, [tablename,])
        mark = []
        unmark = []
        if query:
            for item in fields:
                field = item[0]
                name = field.name
                value = item[1]
                if self.is_flag(name):
                    flag = self.search_fields[name]
                    if (value is not None) and (flag != "\\Recent"):
                        if value:
                            mark.append(flag)
                        else:
                            unmark.append(flag)
            result, data = self.connection.select(
                self.connection.mailbox_names[tablename])
            string_query = "(%s)" % query
            result, data = self.connection.search(None, string_query)
            store_list = [item.strip() for item in data[0].split()
                          if item.strip().isdigit()]
            # build commands for marked flags
            for number in store_list:
                result = None
                if len(mark) > 0:
                    commands.append((number, "+FLAGS", "(%s)" % " ".join(mark)))
                if len(unmark) > 0:
                    commands.append((number, "-FLAGS", "(%s)" % " ".join(unmark)))
        return commands

    def update(self, tablename, query, fields):
        rowcount = 0
        commands = self._update(tablename, query, fields)
        for command in commands:
            result, data = self.connection.store(*command)
            if result == "OK":
                rowcount += 1
            else:
                raise Exception("IMAP storing error: %s" % data)
        return rowcount

    def _count(self, query, distinct=None):
        raise NotImplementedError()

    def count(self,query,distinct=None):
        counter = 0
        tablename = self.get_query_mailbox(query)
        if query and tablename is not None:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename,])
            result, data = self.connection.select(self.connection.mailbox_names[tablename])
            string_query = "(%s)" % query
            result, data = self.connection.search(None, string_query)
            store_list = [item.strip() for item in data[0].split() if item.strip().isdigit()]
            counter = len(store_list)
        return counter

    def delete(self, tablename, query):
        counter = 0
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename,])
            result, data = self.connection.select(self.connection.mailbox_names[tablename])
            string_query = "(%s)" % query
            result, data = self.connection.search(None, string_query)
            store_list = [item.strip() for item in data[0].split() if item.strip().isdigit()]
            for number in store_list:
                result, data = self.connection.store(number, "+FLAGS", "(\\Deleted)")
                if result == "OK":
                    counter += 1
                else:
                    raise Exception("IMAP store error: %s" % data)
            if counter > 0:
                result, data = self.connection.expunge()
        return counter

    def BELONGS(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            values = [str(val) for val in second if str(val).isdigit()]
            result = "%s" % ",".join(values).strip()

        elif name == "UID":
            values = [str(val) for val in second if str(val).isdigit()]
            result = "UID %s" % ",".join(values).strip()

        else:
            raise Exception("Operation not supported")
        # result = "(%s %s)" % (self.expand(first), self.expand(second))
        return result

    def CONTAINS(self, first, second, case_sensitive=False):
        # silently ignore, only case sensitive
        result = None
        name = self.search_fields[first.name]

        if name in ("FROM", "TO", "SUBJECT", "TEXT"):
            result = "%s \"%s\"" % (name, self.expand(second))
        else:
            if first.name in ("cc", "bcc"):
                result = "%s \"%s\"" % (first.name.upper(), self.expand(second))
            elif first.name == "mime":
                result = "HEADER Content-Type \"%s\"" % self.expand(second)
            else:
                raise Exception("Operation not supported")
        return result

    def GT(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            last_message = self.get_last_message(first.tablename)
            result = "%d:%d" % (int(self.expand(second)) + 1, last_message)
        elif name == "UID":
            # GT and LT may not return
            # expected sets depending on
            # the uid format implemented
            try:
                pedestal, threshold = self.get_uid_bounds(first.tablename)
            except TypeError:
                e = sys.exc_info()[1]
                LOGGER.debug("Error requesting uid bounds: %s", str(e))
                return ""
            try:
                lower_limit = int(self.expand(second)) + 1
            except (ValueError, TypeError):
                e = sys.exc_info()[1]
                raise Exception("Operation not supported (non integer UID)")
            result = "UID %s:%s" % (lower_limit, threshold)
        elif name == "DATE":
            result = "SINCE %s" % self.convert_date(second, add=datetime.timedelta(1))
        elif name == "SIZE":
            result = "LARGER %s" % self.expand(second)
        else:
            raise Exception("Operation not supported")
        return result

    def GE(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            last_message = self.get_last_message(first.tablename)
            result = "%s:%s" % (self.expand(second), last_message)
        elif name == "UID":
            # GT and LT may not return
            # expected sets depending on
            # the uid format implemented
            try:
                pedestal, threshold = self.get_uid_bounds(first.tablename)
            except TypeError:
                e = sys.exc_info()[1]
                LOGGER.debug("Error requesting uid bounds: %s", str(e))
                return ""
            lower_limit = self.expand(second)
            result = "UID %s:%s" % (lower_limit, threshold)
        elif name == "DATE":
            result = "SINCE %s" % self.convert_date(second)
        else:
            raise Exception("Operation not supported")
        return result

    def LT(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            result = "%s:%s" % (1, int(self.expand(second)) - 1)
        elif name == "UID":
            try:
                pedestal, threshold = self.get_uid_bounds(first.tablename)
            except TypeError:
                e = sys.exc_info()[1]
                LOGGER.debug("Error requesting uid bounds: %s", str(e))
                return ""
            try:
                upper_limit = int(self.expand(second)) - 1
            except (ValueError, TypeError):
                e = sys.exc_info()[1]
                raise Exception("Operation not supported (non integer UID)")
            result = "UID %s:%s" % (pedestal, upper_limit)
        elif name == "DATE":
            result = "BEFORE %s" % self.convert_date(second)
        elif name == "SIZE":
            result = "SMALLER %s" % self.expand(second)
        else:
            raise Exception("Operation not supported")
        return result

    def LE(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            result = "%s:%s" % (1, self.expand(second))
        elif name == "UID":
            try:
                pedestal, threshold = self.get_uid_bounds(first.tablename)
            except TypeError:
                e = sys.exc_info()[1]
                LOGGER.debug("Error requesting uid bounds: %s", str(e))
                return ""
            upper_limit = int(self.expand(second))
            result = "UID %s:%s" % (pedestal, upper_limit)
        elif name == "DATE":
            result = "BEFORE %s" % self.convert_date(second, add=datetime.timedelta(1))
        else:
            raise Exception("Operation not supported")
        return result

    def NE(self, first, second=None):
        if (second is None) and isinstance(first, Field):
            # All records special table query
            if first.type == "id":
                return self.GE(first, 1)
        result = self.NOT(self.EQ(first, second))
        result =  result.replace("NOT NOT", "").strip()
        return result

    def EQ(self,first,second):
        name = self.search_fields[first.name]
        result = None
        if name is not None:
            if name == "MESSAGE":
                # query by message sequence number
                result = "%s" % self.expand(second)
            elif name == "UID":
                result = "UID %s" % self.expand(second)
            elif name == "DATE":
                result = "ON %s" % self.convert_date(second)

            elif name in self.flags:
                if second:
                    result = "%s" % (name.upper()[1:])
                else:
                    result = "NOT %s" % (name.upper()[1:])
            else:
                raise Exception("Operation not supported")
        else:
            raise Exception("Operation not supported")
        return result

    def AND(self, first, second):
        result = "%s %s" % (self.expand(first), self.expand(second))
        return result

    def OR(self, first, second):
        result = "OR %s %s" % (self.expand(first), self.expand(second))
        return "%s" % result.replace("OR OR", "OR")

    def NOT(self, first):
        result = "NOT %s" % self.expand(first)
        return result

########################################################################
# end of adapters
########################################################################

ADAPTERS = {
    'sqlite': SQLiteAdapter,
    'spatialite': SpatiaLiteAdapter,
    'sqlite:memory': SQLiteAdapter,
    'spatialite:memory': SpatiaLiteAdapter,
    'mysql': MySQLAdapter,
    'postgres': PostgreSQLAdapter,
    'postgres:psycopg2': PostgreSQLAdapter,
    'postgres:pg8000': PostgreSQLAdapter,
    'postgres2:psycopg2': NewPostgreSQLAdapter,
    'postgres2:pg8000': NewPostgreSQLAdapter,
    'oracle': OracleAdapter,
    'mssql': MSSQLAdapter,
    'mssql2': MSSQL2Adapter,
    'mssql3': MSSQL3Adapter,
    'vertica': VerticaAdapter,
    'sybase': SybaseAdapter,
    'db2': DB2Adapter,
    'teradata': TeradataAdapter,
    'informix': InformixAdapter,
    'informix-se': InformixSEAdapter,
    'firebird': FireBirdAdapter,
    'firebird_embedded': FireBirdAdapter,
    'ingres': IngresAdapter,
    'ingresu': IngresUnicodeAdapter,
    'sapdb': SAPDBAdapter,
    'cubrid': CubridAdapter,
    'jdbc:sqlite': JDBCSQLiteAdapter,
    'jdbc:sqlite:memory': JDBCSQLiteAdapter,
    'jdbc:postgres': JDBCPostgreSQLAdapter,
    'gae': GoogleDatastoreAdapter, # discouraged, for backward compatibility
    'google:datastore': GoogleDatastoreAdapter,
    'google:sql': GoogleSQLAdapter,
    'couchdb': CouchDBAdapter,
    'mongodb': MongoDBAdapter,
    'imap': IMAPAdapter
}

def sqlhtml_validators(field):
    """
    Field type validation, using web2py's validators mechanism.

    makes sure the content of a field is in line with the declared
    fieldtype
    """
    db = field.db
    if not have_validators:
        return []
    field_type, field_length = field.type, field.length
    if isinstance(field_type, SQLCustomType):
        if hasattr(field_type, 'validator'):
            return field_type.validator
        else:
            field_type = field_type.type
    elif not isinstance(field_type,str):
        return []
    requires=[]
    def ff(r,id):
        row=r(id)
        if not row:
            return id
        elif hasattr(r, '_format') and isinstance(r._format,str):
            return r._format % row
        elif hasattr(r, '_format') and callable(r._format):
            return r._format(row)
        else:
            return id
    if field_type in (('string', 'text', 'password')):
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'json':
        requires.append(validators.IS_EMPTY_OR(validators.IS_JSON()))
    elif field_type == 'double' or field_type == 'float':
        requires.append(validators.IS_FLOAT_IN_RANGE(-1e100, 1e100))
    elif field_type in ('integer','bigint'):
        requires.append(validators.IS_INT_IN_RANGE(-1e100, 1e100))
    elif field_type.startswith('decimal'):
        requires.append(validators.IS_DECIMAL_IN_RANGE(-10**10, 10**10))
    elif field_type == 'date':
        requires.append(validators.IS_DATE())
    elif field_type == 'time':
        requires.append(validators.IS_TIME())
    elif field_type == 'datetime':
        requires.append(validators.IS_DATETIME())
    elif db and field_type.startswith('reference') and \
            field_type.find('.') < 0 and \
            field_type[10:] in db.tables:
        referenced = db[field_type[10:]]
        def repr_ref(id, row=None, r=referenced, f=ff): return f(r, id)
        field.represent = field.represent or repr_ref
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db,referenced._id,
                                           referenced._format)
            if field.unique:
                requires._and = validators.IS_NOT_IN_DB(db,field)
            if field.tablename == field_type[10:]:
                return validators.IS_EMPTY_OR(requires)
            return requires
    elif db and field_type.startswith('list:reference') and \
            field_type.find('.') < 0 and \
            field_type[15:] in db.tables:
        referenced = db[field_type[15:]]
        def list_ref_repr(ids, row=None, r=referenced, f=ff):
            if not ids:
                return None
            refs = None
            db, id = r._db, r._id
            if isinstance(db._adapter, GoogleDatastoreAdapter):
                def count(values): return db(id.belongs(values)).select(id)
                rx = range(0, len(ids), 30)
                refs = reduce(lambda a,b:a&b, [count(ids[i:i+30]) for i in rx])
            else:
                refs = db(id.belongs(ids)).select(id)
            return (refs and ', '.join(str(f(r,x.id)) for x in refs) or '')
        field.represent = field.represent or list_ref_repr
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db,referenced._id,
                                           referenced._format,multiple=True)
        else:
            requires = validators.IS_IN_DB(db,referenced._id,
                                           multiple=True)
        if field.unique:
            requires._and = validators.IS_NOT_IN_DB(db,field)
        return requires
    elif field_type.startswith('list:'):
        def repr_list(values,row=None): return', '.join(str(v) for v in (values or []))
        field.represent = field.represent or repr_list
    if field.unique:
        requires.insert(0,validators.IS_NOT_IN_DB(db,field))
    sff = ['in', 'do', 'da', 'ti', 'de', 'bo']
    if field.notnull and not field_type[:2] in sff:
        requires.insert(0, validators.IS_NOT_EMPTY())
    elif not field.notnull and field_type[:2] in sff and requires:
        requires[-1] = validators.IS_EMPTY_OR(requires[-1])
    return requires


def bar_escape(item):
    return str(item).replace('|', '||')

def bar_encode(items):
    return '|%s|' % '|'.join(bar_escape(item) for item in items if str(item).strip())

def bar_decode_integer(value):
    if not hasattr(value,'split') and hasattr(value,'read'):
        value = value.read()
    return [long(x) for x in value.split('|') if x.strip()]

def bar_decode_string(value):
    return [x.replace('||', '|') for x in
            REGEX_UNPACK.split(value[1:-1]) if x.strip()]


class Row(object):

    """
    a dictionary that lets you do d['a'] as well as d.a
    this is only used to store a Row
    """

    __init__ = lambda self,*args,**kwargs: self.__dict__.update(*args,**kwargs)

    def __getitem__(self, k):
        key=str(k)
        _extra = self.__dict__.get('_extra', None)
        if _extra is not None:
            v = _extra.get(key, None)
            if v:
                return v
        m = REGEX_TABLE_DOT_FIELD.match(key)
        if m:
            try:
                return ogetattr(self, m.group(1))[m.group(2)]
            except (KeyError,AttributeError,TypeError):
                key = m.group(2)
        return ogetattr(self, key)

    __setitem__ = lambda self, key, value: setattr(self, str(key), value)

    __delitem__ = object.__delattr__

    __copy__ = lambda self: Row(self)

    __call__ = __getitem__

    get = lambda self, key, default=None: self.__dict__.get(key,default)


    has_key = __contains__ = lambda self, key: key in self.__dict__

    __nonzero__ = lambda self: len(self.__dict__)>0

    update = lambda self, *args, **kwargs:  self.__dict__.update(*args, **kwargs)

    keys = lambda self: self.__dict__.keys()

    items = lambda self: self.__dict__.items()

    values = lambda self: self.__dict__.values()

    __iter__ = lambda self: self.__dict__.__iter__()

    iteritems = lambda self: self.__dict__.iteritems()

    __str__ = __repr__ = lambda self: '<Row %s>' % self.as_dict()

    __int__ = lambda self: object.__getattribute__(self,'id')

    __long__ = lambda self: long(object.__getattribute__(self,'id'))


    def __eq__(self,other):
        try:
            return self.as_dict() == other.as_dict()
        except AttributeError:
            return False

    def __ne__(self,other):
        return not (self == other)

    def __copy__(self):
        return Row(dict(self))

    def as_dict(self, datetime_to_str=False, custom_types=None):
        SERIALIZABLE_TYPES = [str, unicode, int, long, float, bool, list, dict]
        if isinstance(custom_types,(list,tuple,set)):
            SERIALIZABLE_TYPES += custom_types
        elif custom_types:
            SERIALIZABLE_TYPES.append(custom_types)
        d = dict(self)
        for k in copy.copy(d.keys()):
            v=d[k]
            if d[k] is None:
                continue
            elif isinstance(v,Row):
                d[k]=v.as_dict()
            elif isinstance(v,Reference):
                d[k]=long(v)
            elif isinstance(v,decimal.Decimal):
                d[k]=float(v)
            elif isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
                if datetime_to_str:
                    d[k] = v.isoformat().replace('T',' ')[:19]
            elif not isinstance(v,tuple(SERIALIZABLE_TYPES)):
                del d[k]
        return d

    def as_xml(self, row_name="row", colnames=None, indent='  '):
        def f(row,field,indent='  '):
            if isinstance(row,Row):
                spc = indent+'  \n'
                items = [f(row[x],x,indent+'  ') for x in row]
                return '%s<%s>\n%s\n%s</%s>' % (
                    indent,
                    field,
                    spc.join(item for item in items if item),
                    indent,
                    field)
            elif not callable(row):
                if REGEX_ALPHANUMERIC.match(field):
                    return '%s<%s>%s</%s>' % (indent,field,row,field)
                else:
                    return '%s<extra name="%s">%s</extra>' % \
                        (indent,field,row)
            else:
                return None
        return f(self, row_name, indent=indent)

    def as_json(self, mode="object", default=None, colnames=None,
                serialize=True, **kwargs):
        """
        serializes the row to a JSON object
        kwargs are passed to .as_dict method
        only "object" mode supported

        serialize = False used by Rows.as_json
        TODO: return array mode with query column order

        mode and colnames are not implemented
        """

        item = self.as_dict(**kwargs)
        if serialize:
            if have_serializers:
                return serializers.json(item,
                                        default=default or
                                        serializers.custom_json)
            elif simplejson:
                return simplejson.dumps(item)
            else:
                raise RuntimeError("missing simplejson")
        else:
            return item


################################################################################
# Everything below should be independent of the specifics of the database
# and should work for RDBMs and some NoSQL databases
################################################################################

class SQLCallableList(list):
    def __call__(self):
        return copy.copy(self)

def smart_query(fields,text):
    if not isinstance(fields,(list,tuple)):
        fields = [fields]
    new_fields = []
    for field in fields:
        if isinstance(field,Field):
            new_fields.append(field)
        elif isinstance(field,Table):
            for ofield in field:
                new_fields.append(ofield)
        else:
            raise RuntimeError("fields must be a list of fields")
    fields = new_fields
    field_map = {}
    for field in fields:
        n = field.name.lower()
        if not n in field_map:
            field_map[n] = field
        n = str(field).lower()
        if not n in field_map:
            field_map[n] = field
    constants = {}
    i = 0
    while True:
        m = REGEX_CONST_STRING.search(text)
        if not m: break
        text = text[:m.start()]+('#%i' % i)+text[m.end():]
        constants[str(i)] = m.group()[1:-1]
        i+=1
    text = re.sub('\s+',' ',text).lower()
    for a,b in [('&','and'),
                ('|','or'),
                ('~','not'),
                ('==','='),
                ('<','<'),
                ('>','>'),
                ('<=','<='),
                ('>=','>='),
                ('<>','!='),
                ('=<','<='),
                ('=>','>='),
                ('=','='),
                (' less or equal than ','<='),
                (' greater or equal than ','>='),
                (' equal or less than ','<='),
                (' equal or greater than ','>='),
                (' less or equal ','<='),
                (' greater or equal ','>='),
                (' equal or less ','<='),
                (' equal or greater ','>='),
                (' not equal to ','!='),
                (' not equal ','!='),
                (' equal to ','='),
                (' equal ','='),
                (' equals ','='),
                (' less than ','<'),
                (' greater than ','>'),
                (' starts with ','startswith'),
                (' ends with ','endswith'),
                (' not in ' , 'notbelongs'),
                (' in ' , 'belongs'),
                (' is ','=')]:
        if a[0]==' ':
            text = text.replace(' is'+a,' %s ' % b)
        text = text.replace(a,' %s ' % b)
    text = re.sub('\s+',' ',text).lower()
    text = re.sub('(?P<a>[\<\>\!\=])\s+(?P<b>[\<\>\!\=])','\g<a>\g<b>',text)
    query = field = neg = op = logic = None
    for item in text.split():
        if field is None:
            if item == 'not':
                neg = True
            elif not neg and not logic and item in ('and','or'):
                logic = item
            elif item in field_map:
                field = field_map[item]
            else:
                raise RuntimeError("Invalid syntax")
        elif not field is None and op is None:
            op = item
        elif not op is None:
            if item.startswith('#'):
                if not item[1:] in constants:
                    raise RuntimeError("Invalid syntax")
                value = constants[item[1:]]
            else:
                value = item
                if field.type in ('text', 'string', 'json'):
                    if op == '=': op = 'like'
            if op == '=': new_query = field==value
            elif op == '<': new_query = field<value
            elif op == '>': new_query = field>value
            elif op == '<=': new_query = field<=value
            elif op == '>=': new_query = field>=value
            elif op == '!=': new_query = field!=value
            elif op == 'belongs': new_query = field.belongs(value.split(','))
            elif op == 'notbelongs': new_query = ~field.belongs(value.split(','))
            elif field.type in ('text', 'string', 'json'):
                if op == 'contains': new_query = field.contains(value)
                elif op == 'like': new_query = field.like(value)
                elif op == 'startswith': new_query = field.startswith(value)
                elif op == 'endswith': new_query = field.endswith(value)
                else: raise RuntimeError("Invalid operation")
            elif field._db._adapter.dbengine=='google:datastore' and \
                 field.type in ('list:integer', 'list:string', 'list:reference'):
                if op == 'contains': new_query = field.contains(value)
                else: raise RuntimeError("Invalid operation")
            else: raise RuntimeError("Invalid operation")
            if neg: new_query = ~new_query
            if query is None:
                query = new_query
            elif logic == 'and':
                query &= new_query
            elif logic == 'or':
                query |= new_query
            field = op = neg = logic = None
    return query

class DAL(object):

    """
    an instance of this class represents a database connection

    Example::

       db = DAL('sqlite://test.db')

       or

       db = DAL({"uri": ..., "items": ...}) # experimental

       db.define_table('tablename', Field('fieldname1'),
                                    Field('fieldname2'))
    """

    def __new__(cls, uri='sqlite://dummy.db', *args, **kwargs):
        if not hasattr(THREAD_LOCAL,'db_instances'):
            THREAD_LOCAL.db_instances = {}
        if not hasattr(THREAD_LOCAL,'db_instances_zombie'):
            THREAD_LOCAL.db_instances_zombie = {}
        if uri == '<zombie>':
            db_uid = kwargs['db_uid'] # a zombie must have a db_uid!
            if db_uid in THREAD_LOCAL.db_instances:
                db_group = THREAD_LOCAL.db_instances[db_uid]
                db = db_group[-1]
            elif db_uid in THREAD_LOCAL.db_instances_zombie:
                db = THREAD_LOCAL.db_instances_zombie[db_uid]
            else:
                db = super(DAL, cls).__new__(cls)
                THREAD_LOCAL.db_instances_zombie[db_uid] = db
        else:
            db_uid = kwargs.get('db_uid',hashlib_md5(repr(uri)).hexdigest())
            if db_uid in THREAD_LOCAL.db_instances_zombie:
                db = THREAD_LOCAL.db_instances_zombie[db_uid]
                del THREAD_LOCAL.db_instances_zombie[db_uid]
            else:
                db = super(DAL, cls).__new__(cls)
            db_group = THREAD_LOCAL.db_instances.get(db_uid,[])
            db_group.append(db)
            THREAD_LOCAL.db_instances[db_uid] = db_group
        db._db_uid = db_uid
        return db

    @staticmethod
    def set_folder(folder):
        """
        # ## this allows gluon to set a folder for this thread
        # ## <<<<<<<<< Should go away as new DAL replaces old sql.py
        """
        BaseAdapter.set_folder(folder)

    @staticmethod
    def get_instances():
        """
        Returns a dictionary with uri as key with timings and defined tables
        {'sqlite://storage.sqlite': {
            'dbstats': [(select auth_user.email from auth_user, 0.02009)],
            'dbtables': {
                'defined': ['auth_cas', 'auth_event', 'auth_group',
                    'auth_membership', 'auth_permission', 'auth_user'],
                'lazy': '[]'
                }
            }
        }
        """
        dbs = getattr(THREAD_LOCAL,'db_instances',{}).items()
        infos = {}
        for db_uid, db_group in dbs:
            for db in db_group:
                if not db._uri:
                    continue
                k = hide_password(db._uri)
                infos[k] = dict(dbstats = [(row[0], row[1]) for row in db._timings],
                                dbtables = {'defined':
                                    sorted(list(set(db.tables) -
                                                set(db._LAZY_TABLES.keys()))),
                               'lazy': sorted(db._LAZY_TABLES.keys())}
                                 )
        return infos

    @staticmethod
    def distributed_transaction_begin(*instances):
        if not instances:
            return
        thread_key = '%s.%s' % (socket.gethostname(), threading.currentThread())
        keys = ['%s.%i' % (thread_key, i) for (i,db) in instances]
        instances = enumerate(instances)
        for (i, db) in instances:
            if not db._adapter.support_distributed_transaction():
                raise SyntaxError(
                    'distributed transaction not suported by %s' % db._dbname)
        for (i, db) in instances:
            db._adapter.distributed_transaction_begin(keys[i])

    @staticmethod
    def distributed_transaction_commit(*instances):
        if not instances:
            return
        instances = enumerate(instances)
        thread_key = '%s.%s' % (socket.gethostname(), threading.currentThread())
        keys = ['%s.%i' % (thread_key, i) for (i,db) in instances]
        for (i, db) in instances:
            if not db._adapter.support_distributed_transaction():
                raise SyntaxError(
                    'distributed transaction not suported by %s' % db._dbanme)
        try:
            for (i, db) in instances:
                db._adapter.prepare(keys[i])
        except:
            for (i, db) in instances:
                db._adapter.rollback_prepared(keys[i])
            raise RuntimeError('failure to commit distributed transaction')
        else:
            for (i, db) in instances:
                db._adapter.commit_prepared(keys[i])
        return

    def __init__(self, uri=DEFAULT_URI,
                 pool_size=0, folder=None,
                 db_codec='UTF-8', check_reserved=None,
                 migrate=True, fake_migrate=False,
                 migrate_enabled=True, fake_migrate_all=False,
                 decode_credentials=False, driver_args=None,
                 adapter_args=None, attempts=5, auto_import=False,
                 bigint_id=False,debug=False,lazy_tables=False,
                 db_uid=None, do_connect=True, after_connection=None):
        """
        Creates a new Database Abstraction Layer instance.

        Keyword arguments:

        :uri: string that contains information for connecting to a database.
               (default: 'sqlite://dummy.db')

                experimental: you can specify a dictionary as uri
                parameter i.e. with
                db = DAL({"uri": "sqlite://storage.sqlite",
                          "items": {...}, ...})

                for an example of dict input you can check the output
                of the scaffolding db model with

                db.as_dict()

                Note that for compatibility with Python older than
                version 2.6.5 you should cast your dict input keys
                to str due to a syntax limitation on kwarg names.
                for proper DAL dictionary input you can use one of:

                obj = serializers.cast_keys(dict, [encoding="utf-8"])

                or else (for parsing json input)

                obj = serializers.loads_json(data, unicode_keys=False)

        :pool_size: How many open connections to make to the database object.
        :folder: where .table files will be created.
                 automatically set within web2py
                 use an explicit path when using DAL outside web2py
        :db_codec: string encoding of the database (default: 'UTF-8')
        :check_reserved: list of adapters to check tablenames and column names
                         against sql/nosql reserved keywords. (Default None)

        * 'common' List of sql keywords that are common to all database types
                such as "SELECT, INSERT". (recommended)
        * 'all' Checks against all known SQL keywords. (not recommended)
                <adaptername> Checks against the specific adapters list of keywords
                (recommended)
        * '<adaptername>_nonreserved' Checks against the specific adapters
                list of nonreserved keywords. (if available)
        :migrate (defaults to True) sets default migrate behavior for all tables
        :fake_migrate (defaults to False) sets default fake_migrate behavior for all tables
        :migrate_enabled (defaults to True). If set to False disables ALL migrations
        :fake_migrate_all (defaults to False). If sets to True fake migrates ALL tables
        :attempts (defaults to 5). Number of times to attempt connecting
        :auto_import (defaults to False). If set, import automatically table definitions from the
                 databases folder
        :bigint_id (defaults to False): If set, turn on bigint instead of int for id fields
        :lazy_tables (defaults to False): delay table definition until table access
        :after_connection (defaults to None): a callable that will be execute after the connection
        """

        items = None
        if isinstance(uri, dict):
            if "items" in uri:
                items = uri.pop("items")
            try:
                newuri = uri.pop("uri")
            except KeyError:
                newuri = DEFAULT_URI
            locals().update(uri)
            uri = newuri

        if uri == '<zombie>' and db_uid is not None: return
        if not decode_credentials:
            credential_decoder = lambda cred: cred
        else:
            credential_decoder = lambda cred: urllib.unquote(cred)
        self._folder = folder
        if folder:
            self.set_folder(folder)
        self._uri = uri
        self._pool_size = pool_size
        self._db_codec = db_codec
        self._lastsql = ''
        self._timings = []
        self._pending_references = {}
        self._request_tenant = 'request_tenant'
        self._common_fields = []
        self._referee_name = '%(table)s'
        self._bigint_id = bigint_id
        self._debug = debug
        self._migrated = []
        self._LAZY_TABLES = {}
        self._lazy_tables = lazy_tables
        self._tables = SQLCallableList()
        self._driver_args = driver_args
        self._adapter_args = adapter_args
        self._check_reserved = check_reserved
        self._decode_credentials = decode_credentials
        self._attempts = attempts
        self._do_connect = do_connect

        if not str(attempts).isdigit() or attempts < 0:
            attempts = 5
        if uri:
            uris = isinstance(uri,(list,tuple)) and uri or [uri]
            error = ''
            connected = False
            for k in range(attempts):
                for uri in uris:
                    try:
                        if is_jdbc and not uri.startswith('jdbc:'):
                            uri = 'jdbc:'+uri
                        self._dbname = REGEX_DBNAME.match(uri).group()
                        if not self._dbname in ADAPTERS:
                            raise SyntaxError("Error in URI '%s' or database not supported" % self._dbname)
                        # notice that driver args or {} else driver_args
                        # defaults to {} global, not correct
                        kwargs = dict(db=self,uri=uri,
                                      pool_size=pool_size,
                                      folder=folder,
                                      db_codec=db_codec,
                                      credential_decoder=credential_decoder,
                                      driver_args=driver_args or {},
                                      adapter_args=adapter_args or {},
                                      do_connect=do_connect,
                                      after_connection=after_connection)
                        self._adapter = ADAPTERS[self._dbname](**kwargs)
                        types = ADAPTERS[self._dbname].types
                        # copy so multiple DAL() possible
                        self._adapter.types = copy.copy(types)
                        if bigint_id:
                            if 'big-id' in types and 'reference' in types:
                                self._adapter.types['id'] = types['big-id']
                                self._adapter.types['reference'] = types['big-reference']
                        connected = True
                        break
                    except SyntaxError:
                        raise
                    except Exception:
                        tb = traceback.format_exc()
                        sys.stderr.write('DEBUG: connect attempt %i, connection error:\n%s' % (k, tb))
                if connected:
                    break
                else:
                    time.sleep(1)
            if not connected:
                raise RuntimeError("Failure to connect, tried %d times:\n%s" % (attempts, tb))
        else:
            self._adapter = BaseAdapter(db=self,pool_size=0,
                                        uri='None',folder=folder,
                                        db_codec=db_codec, after_connection=after_connection)
            migrate = fake_migrate = False
        adapter = self._adapter
        self._uri_hash = hashlib_md5(adapter.uri).hexdigest()
        self.check_reserved = check_reserved
        if self.check_reserved:
            from reserved_sql_keywords import ADAPTERS as RSK
            self.RSK = RSK
        self._migrate = migrate
        self._fake_migrate = fake_migrate
        self._migrate_enabled = migrate_enabled
        self._fake_migrate_all = fake_migrate_all
        if auto_import or items:
            self.import_table_definitions(adapter.folder,
                                          items=items)

    @property
    def tables(self):
        return self._tables

    def import_table_definitions(self, path, migrate=False,
                                 fake_migrate=False, items=None):
        pattern = pjoin(path,self._uri_hash+'_*.table')
        if items:
            for tablename, table in items.iteritems():
                # TODO: read all field/table options
                fields = []
                # remove unsupported/illegal Table arguments
                [table.pop(name) for name in ("name", "fields") if
                 name in table]
                if "items" in table:
                    for fieldname, field in table.pop("items").iteritems():
                        # remove unsupported/illegal Field arguments
                        [field.pop(key) for key in ("requires", "name",
                         "compute", "colname") if key in field]
                        fields.append(Field(str(fieldname), **field))
                self.define_table(str(tablename), *fields, **table)
        else:
            for filename in glob.glob(pattern):
                tfile = self._adapter.file_open(filename, 'r')
                try:
                    sql_fields = pickle.load(tfile)
                    name = filename[len(pattern)-7:-6]
                    mf = [(value['sortable'],
                           Field(key,
                                 type=value['type'],
                                 length=value.get('length',None),
                                 notnull=value.get('notnull',False),
                                 unique=value.get('unique',False))) \
                              for key, value in sql_fields.iteritems()]
                    mf.sort(lambda a,b: cmp(a[0],b[0]))
                    self.define_table(name,*[item[1] for item in mf],
                                      **dict(migrate=migrate,
                                             fake_migrate=fake_migrate))
                finally:
                    self._adapter.file_close(tfile)

    def check_reserved_keyword(self, name):
        """
        Validates ``name`` against SQL keywords
        Uses self.check_reserve which is a list of
        operators to use.
        self.check_reserved
        ['common', 'postgres', 'mysql']
        self.check_reserved
        ['all']
        """
        for backend in self.check_reserved:
            if name.upper() in self.RSK[backend]:
                raise SyntaxError(
                    'invalid table/column name "%s" is a "%s" reserved SQL/NOSQL keyword' % (name, backend.upper()))

    def parse_as_rest(self,patterns,args,vars,queries=None,nested_select=True):
        """
        EXAMPLE:

db.define_table('person',Field('name'),Field('info'))
db.define_table('pet',Field('ownedby',db.person),Field('name'),Field('info'))

@request.restful()
def index():
    def GET(*args,**vars):
        patterns = [
            "/friends[person]",
            "/{person.name}/:field",
            "/{person.name}/pets[pet.ownedby]",
            "/{person.name}/pets[pet.ownedby]/{pet.name}",
            "/{person.name}/pets[pet.ownedby]/{pet.name}/:field",
            ("/dogs[pet]", db.pet.info=='dog'),
            ("/dogs[pet]/{pet.name.startswith}", db.pet.info=='dog'),
            ]
        parser = db.parse_as_rest(patterns,args,vars)
        if parser.status == 200:
            return dict(content=parser.response)
        else:
            raise HTTP(parser.status,parser.error)

    def POST(table_name,**vars):
        if table_name == 'person':
            return db.person.validate_and_insert(**vars)
        elif table_name == 'pet':
            return db.pet.validate_and_insert(**vars)
        else:
            raise HTTP(400)
    return locals()
        """

        db = self
        re1 = REGEX_SEARCH_PATTERN
        re2 = REGEX_SQUARE_BRACKETS

        def auto_table(table,base='',depth=0):
            patterns = []
            for field in db[table].fields:
                if base:
                    tag = '%s/%s' % (base,field.replace('_','-'))
                else:
                    tag = '/%s/%s' % (table.replace('_','-'),field.replace('_','-'))
                f = db[table][field]
                if not f.readable: continue
                if f.type=='id' or 'slug' in field or f.type.startswith('reference'):
                    tag += '/{%s.%s}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('boolean'):
                    tag += '/{%s.%s}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type in ('float','double','integer','bigint'):
                    tag += '/{%s.%s.ge}/{%s.%s.lt}' % (table,field,table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('list:'):
                    tag += '/{%s.%s.contains}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type in ('date','datetime'):
                    tag+= '/{%s.%s.year}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.month}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.day}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                if f.type in ('datetime','time'):
                    tag+= '/{%s.%s.hour}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.minute}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.second}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                if depth>0:
                    for f in db[table]._referenced_by:
                        tag+='/%s[%s.%s]' % (table,f.tablename,f.name)
                        patterns.append(tag)
                        patterns += auto_table(table,base=tag,depth=depth-1)
            return patterns

        if patterns == 'auto':
            patterns=[]
            for table in db.tables:
                if not table.startswith('auth_'):
                    patterns.append('/%s[%s]' % (table,table))
                    patterns += auto_table(table,base='',depth=1)
        else:
            i = 0
            while i<len(patterns):
                pattern = patterns[i]
                if not isinstance(pattern,str):
                    pattern = pattern[0]
                tokens = pattern.split('/')
                if tokens[-1].startswith(':auto') and re2.match(tokens[-1]):
                    new_patterns = auto_table(tokens[-1][tokens[-1].find('[')+1:-1],
                                              '/'.join(tokens[:-1]))
                    patterns = patterns[:i]+new_patterns+patterns[i+1:]
                    i += len(new_patterns)
                else:
                    i += 1
        if '/'.join(args) == 'patterns':
            return Row({'status':200,'pattern':'list',
                        'error':None,'response':patterns})
        for pattern in patterns:
            basequery, exposedfields = None, []
            if isinstance(pattern,tuple):
                if len(pattern)==2:
                    pattern, basequery = pattern
                elif len(pattern)>2:
                    pattern, basequery, exposedfields = pattern[0:3]
            otable=table=None
            if not isinstance(queries,dict):
                dbset=db(queries)
                if basequery is not None:
                    dbset = dbset(basequery)
            i=0
            tags = pattern[1:].split('/')
            if len(tags)!=len(args):
                continue
            for tag in tags:
                if re1.match(tag):
                    # print 're1:'+tag
                    tokens = tag[1:-1].split('.')
                    table, field = tokens[0], tokens[1]
                    if not otable or table == otable:
                        if len(tokens)==2 or tokens[2]=='eq':
                            query = db[table][field]==args[i]
                        elif tokens[2]=='ne':
                            query = db[table][field]!=args[i]
                        elif tokens[2]=='lt':
                            query = db[table][field]<args[i]
                        elif tokens[2]=='gt':
                            query = db[table][field]>args[i]
                        elif tokens[2]=='ge':
                            query = db[table][field]>=args[i]
                        elif tokens[2]=='le':
                            query = db[table][field]<=args[i]
                        elif tokens[2]=='year':
                            query = db[table][field].year()==args[i]
                        elif tokens[2]=='month':
                            query = db[table][field].month()==args[i]
                        elif tokens[2]=='day':
                            query = db[table][field].day()==args[i]
                        elif tokens[2]=='hour':
                            query = db[table][field].hour()==args[i]
                        elif tokens[2]=='minute':
                            query = db[table][field].minutes()==args[i]
                        elif tokens[2]=='second':
                            query = db[table][field].seconds()==args[i]
                        elif tokens[2]=='startswith':
                            query = db[table][field].startswith(args[i])
                        elif tokens[2]=='contains':
                            query = db[table][field].contains(args[i])
                        else:
                            raise RuntimeError("invalid pattern: %s" % pattern)
                        if len(tokens)==4 and tokens[3]=='not':
                            query = ~query
                        elif len(tokens)>=4:
                            raise RuntimeError("invalid pattern: %s" % pattern)
                        if not otable and isinstance(queries,dict):
                            dbset = db(queries[table])
                            if basequery is not None:
                                dbset = dbset(basequery)
                        dbset=dbset(query)
                    else:
                        raise RuntimeError("missing relation in pattern: %s" % pattern)
                elif re2.match(tag) and args[i]==tag[:tag.find('[')]:
                    ref = tag[tag.find('[')+1:-1]
                    if '.' in ref and otable:
                        table,field = ref.split('.')
                        selfld = '_id'
                        if db[table][field].type.startswith('reference '):
                            refs = [ x.name for x in db[otable] if x.type == db[table][field].type ]
                        else:
                            refs = [ x.name for x in db[table]._referenced_by if x.tablename==otable ]
                        if refs:
                            selfld = refs[0]
                        if nested_select:
                            try:
                                dbset=db(db[table][field].belongs(dbset._select(db[otable][selfld])))
                            except ValueError:
                                return Row({'status':400,'pattern':pattern,
                                            'error':'invalid path','response':None})
                        else:
                            items = [item.id for item in dbset.select(db[otable][selfld])]
                            dbset=db(db[table][field].belongs(items))
                    else:
                        table = ref
                        if not otable and isinstance(queries,dict):
                            dbset = db(queries[table])
                        dbset=dbset(db[table])
                elif tag==':field' and table:
                    # print 're3:'+tag
                    field = args[i]
                    if not field in db[table]: break
                    # hand-built patterns should respect .readable=False as well
                    if not db[table][field].readable:
                        return Row({'status':418,'pattern':pattern,
                                    'error':'I\'m a teapot','response':None})
                    try:
                        distinct = vars.get('distinct', False) == 'True'
                        offset = long(vars.get('offset',None) or 0)
                        limits = (offset,long(vars.get('limit',None) or 1000)+offset)
                    except ValueError:
                        return Row({'status':400,'error':'invalid limits','response':None})
                    items =  dbset.select(db[table][field], distinct=distinct, limitby=limits)
                    if items:
                        return Row({'status':200,'response':items,
                                    'pattern':pattern})
                    else:
                        return Row({'status':404,'pattern':pattern,
                                    'error':'no record found','response':None})
                elif tag != args[i]:
                    break
                otable = table
                i += 1
                if i==len(tags) and table:
                    ofields = vars.get('order',db[table]._id.name).split('|')
                    try:
                        orderby = [db[table][f] if not f.startswith('~') else ~db[table][f[1:]] for f in ofields]
                    except (KeyError, AttributeError):
                        return Row({'status':400,'error':'invalid orderby','response':None})
                    if exposedfields:
                        fields = [field for field in db[table] if str(field).split('.')[-1] in exposedfields and field.readable]
                    else:
                        fields = [field for field in db[table] if field.readable]
                    count = dbset.count()
                    try:
                        offset = long(vars.get('offset',None) or 0)
                        limits = (offset,long(vars.get('limit',None) or 1000)+offset)
                    except ValueError:
                        return Row({'status':400,'error':'invalid limits','response':None})
                    if count > limits[1]-limits[0]:
                        return Row({'status':400,'error':'too many records','response':None})
                    try:
                        response = dbset.select(limitby=limits,orderby=orderby,*fields)
                    except ValueError:
                        return Row({'status':400,'pattern':pattern,
                                    'error':'invalid path','response':None})
                    return Row({'status':200,'response':response,
                                'pattern':pattern,'count':count})
        return Row({'status':400,'error':'no matching pattern','response':None})

    def define_table(
        self,
        tablename,
        *fields,
        **args
        ):
        if not isinstance(tablename,str):
            raise SyntaxError("missing table name")
        elif hasattr(self,tablename) or tablename in self.tables:
            if not args.get('redefine',False):
                raise SyntaxError('table already defined: %s' % tablename)
        elif tablename.startswith('_') or hasattr(self,tablename) or \
                REGEX_PYTHON_KEYWORDS.match(tablename):
            raise SyntaxError('invalid table name: %s' % tablename)
        elif self.check_reserved:
            self.check_reserved_keyword(tablename)
        else:
            invalid_args = set(args)-TABLE_ARGS
            if invalid_args:
                raise SyntaxError('invalid table "%s" attributes: %s' \
                    % (tablename,invalid_args))
        if self._lazy_tables and not tablename in self._LAZY_TABLES:
            self._LAZY_TABLES[tablename] = (tablename,fields,args)
            table = None
        else:
            table = self.lazy_define_table(tablename,*fields,**args)
        if not tablename in self.tables:
            self.tables.append(tablename)
        return table

    def lazy_define_table(
        self,
        tablename,
        *fields,
        **args
        ):
        args_get = args.get
        common_fields = self._common_fields
        if common_fields:
            fields = list(fields) + list(common_fields)

        table_class = args_get('table_class',Table)
        table = table_class(self, tablename, *fields, **args)
        table._actual = True
        self[tablename] = table
        # must follow above line to handle self references
        table._create_references()
        for field in table:
            if field.requires == DEFAULT:
                field.requires = sqlhtml_validators(field)

        migrate = self._migrate_enabled and args_get('migrate',self._migrate)
        if migrate and not self._uri in (None,'None') \
                or self._adapter.dbengine=='google:datastore':
            fake_migrate = self._fake_migrate_all or \
                args_get('fake_migrate',self._fake_migrate)
            polymodel = args_get('polymodel',None)
            try:
                GLOBAL_LOCKER.acquire()
                self._lastsql = self._adapter.create_table(
                    table,migrate=migrate,
                    fake_migrate=fake_migrate,
                    polymodel=polymodel)
            finally:
                GLOBAL_LOCKER.release()
        else:
            table._dbt = None
        on_define = args_get('on_define',None)
        if on_define: on_define(table)
        return table

    def as_dict(self, flat=False, sanitize=True, field_options=True):
        dbname = db_uid = uri = None
        if not sanitize:
            uri, dbname, db_uid = (self._uri, self._dbname, self._db_uid)
        db_as_dict = dict(items={}, tables=[], uri=uri, dbname=dbname,
                          db_uid=db_uid,
                          **dict([(k, getattr(self, "_" + k)) for
                          k in 'pool_size','folder','db_codec',
                          'check_reserved','migrate','fake_migrate',
                          'migrate_enabled','fake_migrate_all',
                          'decode_credentials','driver_args',
                          'adapter_args', 'attempts',
                          'bigint_id','debug','lazy_tables',
                          'do_connect']))

        for table in self:
            tablename = str(table)
            db_as_dict["tables"].append(tablename)
            db_as_dict["items"][tablename] = table.as_dict(flat=flat,
                                         sanitize=sanitize,
                                         field_options=field_options)
        return db_as_dict

    def as_xml(self, sanitize=True, field_options=True):
        if not have_serializers:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize,
                         field_options=field_options)
        return serializers.xml(d)

    def as_json(self, sanitize=True, field_options=True):
        if not have_serializers:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize,
                         field_options=field_options)
        return serializers.json(d)

    def as_yaml(self, sanitize=True, field_options=True):
        if not have_serializers:
            raise ImportError("No YAML serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize,
                         field_options=field_options)
        return serializers.yaml(d)

    def __contains__(self, tablename):
        try:
            return tablename in self.tables
        except AttributeError:
            # The instance has no .tables attribute yet
            return False

    has_key = __contains__

    def get(self,key,default=None):
        return self.__dict__.get(key,default)

    def __iter__(self):
        for tablename in self.tables:
            yield self[tablename]

    def __getitem__(self, key):
        return self.__getattr__(str(key))

    def __getattr__(self, key):
        if ogetattr(self,'_lazy_tables') and \
                key in ogetattr(self,'_LAZY_TABLES'):
            tablename, fields, args = self._LAZY_TABLES.pop(key)
            return self.lazy_define_table(tablename,*fields,**args)
        return ogetattr(self, key)

    def __setitem__(self, key, value):
        osetattr(self, str(key), value)

    def __setattr__(self, key, value):
        if key[:1]!='_' and key in self:
            raise SyntaxError(
                'Object %s exists and cannot be redefined' % key)
        osetattr(self,key,value)

    __delitem__ = object.__delattr__

    def __repr__(self):
        if hasattr(self,'_uri'):
            return '<DAL uri="%s">' % hide_password(str(self._uri))
        else:
            return '<DAL db_uid="%s">' % self._db_uid

    def smart_query(self,fields,text):
        return Set(self, smart_query(fields,text))

    def __call__(self, query=None, ignore_common_filters=None):
        if isinstance(query,Table):
            query = self._adapter.id_query(query)
        elif isinstance(query,Field):
            query = query!=None
        elif isinstance(query, dict):
            icf = query.get("ignore_common_filters")
            if icf: ignore_common_filters = icf
        return Set(self, query, ignore_common_filters=ignore_common_filters)

    def commit(self):
        self._adapter.commit()

    def rollback(self):
        self._adapter.rollback()

    def close(self):
        self._adapter.close()
        if self._db_uid in THREAD_LOCAL.db_instances:
            db_group = THREAD_LOCAL.db_instances[self._db_uid]
            db_group.remove(self)
            if not db_group:
                del THREAD_LOCAL.db_instances[self._db_uid]

    def executesql(self, query, placeholders=None, as_dict=False,
                   fields=None, colnames=None):
        """
        placeholders is optional and will always be None.
        If using raw SQL with placeholders, placeholders may be
        a sequence of values to be substituted in
        or, (if supported by the DB driver), a dictionary with keys
        matching named placeholders in your SQL.

        Added 2009-12-05 "as_dict" optional argument. Will always be
        None when using DAL. If using raw SQL can be set to True
        and the results cursor returned by the DB driver will be
        converted to a sequence of dictionaries keyed with the db
        field names. Tested with SQLite but should work with any database
        since the cursor.description used to get field names is part of the
        Python dbi 2.0 specs. Results returned with as_dict=True are
        the same as those returned when applying .to_list() to a DAL query.

        [{field1: value1, field2: value2}, {field1: value1b, field2: value2b}]

        Added 2012-08-24 "fields" and "colnames" optional arguments. If either
        is provided, the results cursor returned by the DB driver will be
        converted to a DAL Rows object using the db._adapter.parse() method.

        The "fields" argument is a list of DAL Field objects that match the
        fields returned from the DB. The Field objects should be part of one or
        more Table objects defined on the DAL object. The "fields" list can
        include one or more DAL Table objects in addition to or instead of
        including Field objects, or it can be just a single table (not in a
        list). In that case, the Field objects will be extracted from the
        table(s).

        Instead of specifying the "fields" argument, the "colnames" argument
        can be specified as a list of field names in tablename.fieldname format.
        Again, these should represent tables and fields defined on the DAL
        object.

        It is also possible to specify both "fields" and the associated
        "colnames". In that case, "fields" can also include DAL Expression
        objects in addition to Field objects. For Field objects in "fields",
        the associated "colnames" must still be in tablename.fieldname format.
        For Expression objects in "fields", the associated "colnames" can
        be any arbitrary labels.

        Note, the DAL Table objects referred to by "fields" or "colnames" can
        be dummy tables and do not have to represent any real tables in the
        database. Also, note that the "fields" and "colnames" must be in the
        same order as the fields in the results cursor returned from the DB.
        """
        adapter = self._adapter
        if placeholders:
            adapter.execute(query, placeholders)
        else:
            adapter.execute(query)
        if as_dict:
            if not hasattr(adapter.cursor,'description'):
                raise RuntimeError("database does not support executesql(...,as_dict=True)")
            # Non-DAL legacy db query, converts cursor results to dict.
            # sequence of 7-item sequences. each sequence tells about a column.
            # first item is always the field name according to Python Database API specs
            columns = adapter.cursor.description
            # reduce the column info down to just the field names
            fields = [f[0] for f in columns]
            # will hold our finished resultset in a list
            data = adapter._fetchall()
            # convert the list for each row into a dictionary so it's
            # easier to work with. row['field_name'] rather than row[0]
            return [dict(zip(fields,row)) for row in data]
        try:
            data = adapter._fetchall()
        except:
            return None
        if fields or colnames:
            fields = [] if fields is None else fields
            if not isinstance(fields, list):
                fields = [fields]
            extracted_fields = []
            for field in fields:
                if isinstance(field, Table):
                    extracted_fields.extend([f for f in field])
                else:
                    extracted_fields.append(field)
            if not colnames:
                colnames = ['%s.%s' % (f.tablename, f.name)
                            for f in extracted_fields]
            data = adapter.parse(
                data, fields=extracted_fields, colnames=colnames)
        return data

    def _remove_references_to(self, thistable):
        for table in self:
            table._referenced_by = [field for field in table._referenced_by
                                    if not field.table==thistable]

    def export_to_csv_file(self, ofile, *args, **kwargs):
        step = long(kwargs.get('max_fetch_rows,',500))
        write_colnames = kwargs['write_colnames'] = \
            kwargs.get("write_colnames", True)
        for table in self.tables:
            ofile.write('TABLE %s\r\n' % table)
            query = self._adapter.id_query(self[table])
            nrows = self(query).count()
            kwargs['write_colnames'] = write_colnames
            for k in range(0,nrows,step):
                self(query).select(limitby=(k,k+step)).export_to_csv_file(
                    ofile, *args, **kwargs)
                kwargs['write_colnames'] = False
            ofile.write('\r\n\r\n')
        ofile.write('END')

    def import_from_csv_file(self, ifile, id_map=None, null='<NULL>',
                             unique='uuid', map_tablenames=None,
                             ignore_missing_tables=False,
                             *args, **kwargs):
        #if id_map is None: id_map={}
        id_offset = {} # only used if id_map is None
        map_tablenames = map_tablenames or {}
        for line in ifile:
            line = line.strip()
            if not line:
                continue
            elif line == 'END':
                return
            elif not line.startswith('TABLE ') or \
                    not line[6:] in self.tables:
                raise SyntaxError('invalid file format')
            else:
                tablename = line[6:]
                tablename = map_tablenames.get(tablename,tablename)
                if tablename is not None and tablename in self.tables:
                    self[tablename].import_from_csv_file(
                        ifile, id_map, null, unique, id_offset,
                        *args, **kwargs)
                elif tablename is None or ignore_missing_tables:
                    # skip all non-empty lines
                    for line in ifile:
                        if not line.strip():
                            breal
                else:
                    raise RuntimeError("Unable to import table that does not exist.\nTry db.import_from_csv_file(..., map_tablenames={'table':'othertable'},ignore_missing_tables=True)")


def DAL_unpickler(db_uid):
    return DAL('<zombie>',db_uid=db_uid)

def DAL_pickler(db):
    return DAL_unpickler, (db._db_uid,)

copyreg.pickle(DAL, DAL_pickler, DAL_unpickler)

class SQLALL(object):
    """
    Helper class providing a comma-separated string having all the field names
    (prefixed by table name and '.')

    normally only called from within gluino.sql
    """

    def __init__(self, table):
        self._table = table

    def __str__(self):
        return ', '.join([str(field) for field in self._table])

# class Reference(int):
class Reference(long):

    def __allocate(self):
        if not self._record:
            self._record = self._table[long(self)]
        if not self._record:
            raise RuntimeError(
                "Using a recursive select but encountered a broken reference: %s %d"%(self._table, long(self)))

    def __getattr__(self, key):
        if key == 'id':
            return long(self)
        self.__allocate()
        return self._record.get(key, None)

    def get(self, key, default=None):
        return self.__getattr__(key, default)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            long.__setattr__(self, key, value)
            return
        self.__allocate()
        self._record[key] =  value

    def __getitem__(self, key):
        if key == 'id':
            return long(self)
        self.__allocate()
        return self._record.get(key, None)

    def __setitem__(self,key,value):
        self.__allocate()
        self._record[key] = value


def Reference_unpickler(data):
    return marshal.loads(data)

def Reference_pickler(data):
    try:
        marshal_dump = marshal.dumps(long(data))
    except AttributeError:
        marshal_dump = 'i%s' % struct.pack('<i', long(data))
    return (Reference_unpickler, (marshal_dump,))

copyreg.pickle(Reference, Reference_pickler, Reference_unpickler)

class MethodAdder(object):
    def __init__(self,table):
        self.table = table
    def __call__(self):
        return self.register()
    def __getattr__(self,method_name):
        return self.register(method_name)
    def register(self,method_name=None):
        def _decorated(f):
            instance = self.table
            import types
            method = types.MethodType(f, instance, instance.__class__)
            name = method_name or f.func_name
            setattr(instance, name, method)
            return f
        return _decorated

class Table(object):

    """
    an instance of this class represents a database table

    Example::

        db = DAL(...)
        db.define_table('users', Field('name'))
        db.users.insert(name='me') # print db.users._insert(...) to see SQL
        db.users.drop()
    """

    def __init__(
        self,
        db,
        tablename,
        *fields,
        **args
        ):
        """
        Initializes the table and performs checking on the provided fields.

        Each table will have automatically an 'id'.

        If a field is of type Table, the fields (excluding 'id') from that table
        will be used instead.

        :raises SyntaxError: when a supplied field is of incorrect type.
        """
        self._actual = False # set to True by define_table()
        self._tablename = tablename
        self._ot = args.get('actual_name')
        self._sequence_name = args.get('sequence_name') or \
            db and db._adapter.sequence_name(tablename)
        self._trigger_name = args.get('trigger_name') or \
            db and db._adapter.trigger_name(tablename)
        self._common_filter = args.get('common_filter')
        self._format = args.get('format')
        self._singular = args.get(
            'singular',tablename.replace('_',' ').capitalize())
        self._plural = args.get(
            'plural',pluralize(self._singular.lower()).capitalize())
        # horrible but for backard compatibility of appamdin:
        if 'primarykey' in args and args['primarykey'] is not None:
            self._primarykey = args.get('primarykey')

        self._before_insert = []
        self._before_update = [Set.delete_uploaded_files]
        self._before_delete = [Set.delete_uploaded_files]
        self._after_insert = []
        self._after_update = []
        self._after_delete = []

        self.add_method = MethodAdder(self)

        fieldnames,newfields=set(),[]
        if hasattr(self,'_primarykey'):
            if not isinstance(self._primarykey,list):
                raise SyntaxError(
                    "primarykey must be a list of fields from table '%s'" \
                    % tablename)
            if len(self._primarykey)==1:
                self._id = [f for f in fields if isinstance(f,Field) \
                                and f.name==self._primarykey[0]][0]
        elif not [f for f in fields if isinstance(f,Field) and f.type=='id']:
            field = Field('id', 'id')
            newfields.append(field)
            fieldnames.add('id')
            self._id = field
        virtual_fields = []
        for field in fields:
            if isinstance(field, (FieldMethod, FieldVirtual)):
                virtual_fields.append(field)
            elif isinstance(field, Field) and not field.name in fieldnames:
                if field.db is not None:
                    field = copy.copy(field)
                newfields.append(field)
                fieldnames.add(field.name)
                if field.type=='id':
                    self._id = field
            elif isinstance(field, Table):
                table = field
                for field in table:
                    if not field.name in fieldnames and not field.type=='id':
                        t2 = not table._actual and self._tablename
                        field = field.clone(point_self_references_to=t2)
                        newfields.append(field)
                        fieldnames.add(field.name)
            elif not isinstance(field, (Field, Table)):
                raise SyntaxError(
                    'define_table argument is not a Field or Table: %s' % field)
        fields = newfields
        self._db = db
        tablename = tablename
        self._fields = SQLCallableList()
        self.virtualfields = []
        fields = list(fields)

        if db and db._adapter.uploads_in_blob==True:
            uploadfields = [f.name for f in fields if f.type=='blob']
            for field in fields:
                fn = field.uploadfield
                if isinstance(field, Field) and field.type == 'upload'\
                        and fn is True:
                    fn = field.uploadfield = '%s_blob' % field.name
                if isinstance(fn,str) and not fn in uploadfields:
                    fields.append(Field(fn,'blob',default='',
                                        writable=False,readable=False))

        lower_fieldnames = set()
        reserved = dir(Table) + ['fields']
        for field in fields:
            field_name = field.name
            if db and db.check_reserved:
                db.check_reserved_keyword(field_name)
            elif field_name in reserved:
                raise SyntaxError("field name %s not allowed" % field_name)

            if field_name.lower() in lower_fieldnames:
                raise SyntaxError("duplicate field %s in table %s" \
                    % (field_name, tablename))
            else:
                lower_fieldnames.add(field_name.lower())

            self.fields.append(field_name)
            self[field_name] = field
            if field.type == 'id':
                self['id'] = field
            field.tablename = field._tablename = tablename
            field.table = field._table = self
            field.db = field._db = db
        self.ALL = SQLALL(self)

        if hasattr(self,'_primarykey'):
            for k in self._primarykey:
                if k not in self.fields:
                    raise SyntaxError(
                        "primarykey must be a list of fields from table '%s " % tablename)
                else:
                    self[k].notnull = True
        for field in virtual_fields:
            self[field.name] = field

    @property
    def fields(self):
        return self._fields

    def update(self,*args,**kwargs):
        raise RuntimeError("Syntax Not Supported")

    def _enable_record_versioning(self,
                                  archive_db=None,
                                  archive_name = '%(tablename)s_archive',
                                  current_record = 'current_record',
                                  is_active = 'is_active'):
        archive_db = archive_db or self._db
        archive_name = archive_name % dict(tablename=self._tablename)
        if archive_name in archive_db.tables():
            return # do not try define the archive if already exists
        fieldnames = self.fields()
        same_db = archive_db is self._db
        field_type = self if same_db else 'bigint'
        clones = []
        for field in self:
            clones.append(field.clone(
                    unique=False, type=field.type if same_db else 'bigint'))
        archive_db.define_table(
            archive_name, Field(current_record,field_type), *clones)
        self._before_update.append(
            lambda qset,fs,db=archive_db,an=archive_name,cn=current_record:
                archive_record(qset,fs,db[an],cn))
        if is_active and is_active in fieldnames:
            self._before_delete.append(
                lambda qset: qset.update(is_active=False))
            newquery = lambda query, t=self: t.is_active == True
            query = self._common_filter
            if query:
                newquery = query & newquery
            self._common_filter = newquery

    def _validate(self,**vars):
        errors = Row()
        for key,value in vars.iteritems():
            value,error = self[key].validate(value)
            if error:
                errors[key] = error
        return errors

    def _create_references(self):
        db = self._db
        pr = db._pending_references
        self._referenced_by = []
        for field in self:
            fieldname = field.name
            field_type = field.type
            if isinstance(field_type,str) and field_type[:10] == 'reference ':
                ref = field_type[10:].strip()
                if not ref.split():
                    raise SyntaxError('Table: reference to nothing: %s' %ref)
                refs = ref.split('.')
                rtablename = refs[0]
                if not rtablename in db:
                    pr[rtablename] = pr.get(rtablename,[]) + [field]
                    continue
                rtable = db[rtablename]
                if len(refs)==2:
                    rfieldname = refs[1]
                    if not hasattr(rtable,'_primarykey'):
                        raise SyntaxError(
                            'keyed tables can only reference other keyed tables (for now)')
                    if rfieldname not in rtable.fields:
                        raise SyntaxError(
                            "invalid field '%s' for referenced table '%s' in table '%s'" \
                            % (rfieldname, rtablename, self._tablename))
                rtable._referenced_by.append(field)
        for referee in pr.get(self._tablename,[]):
            self._referenced_by.append(referee)

    def _filter_fields(self, record, id=False):
        return dict([(k, v) for (k, v) in record.iteritems() if k
                     in self.fields and (self[k].type!='id' or id)])

    def _build_query(self,key):
        """ for keyed table only """
        query = None
        for k,v in key.iteritems():
            if k in self._primarykey:
                if query:
                    query = query & (self[k] == v)
                else:
                    query = (self[k] == v)
            else:
                raise SyntaxError(
                'Field %s is not part of the primary key of %s' % \
                (k,self._tablename))
        return query

    def __getitem__(self, key):
        if not key:
            return None
        elif isinstance(key, dict):
            """ for keyed table """
            query = self._build_query(key)
            rows = self._db(query).select()
            if rows:
                return rows[0]
            return None
        elif str(key).isdigit() or 'google' in DRIVERS and isinstance(key, Key):
            return self._db(self._id == key).select(limitby=(0,1), orderby_on_limitby=False).first()
        elif key:
            return ogetattr(self, str(key))

    def __call__(self, key=DEFAULT, **kwargs):
        for_update = kwargs.get('_for_update',False)
        if '_for_update' in kwargs: del kwargs['_for_update']

        orderby = kwargs.get('_orderby',None)
        if '_orderby' in kwargs: del kwargs['_orderby']

        if not key is DEFAULT:
            if isinstance(key, Query):
                record = self._db(key).select(
                    limitby=(0,1),for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
            elif not str(key).isdigit():
                record = None
            else:
                record = self._db(self._id == key).select(
                    limitby=(0,1),for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
            if record:
                for k,v in kwargs.iteritems():
                    if record[k]!=v: return None
            return record
        elif kwargs:
            query = reduce(lambda a,b:a&b,[self[k]==v for k,v in kwargs.iteritems()])
            return self._db(query).select(limitby=(0,1),for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
        else:
            return None

    def __setitem__(self, key, value):
        if isinstance(key, dict) and isinstance(value, dict):
            """ option for keyed table """
            if set(key.keys()) == set(self._primarykey):
                value = self._filter_fields(value)
                kv = {}
                kv.update(value)
                kv.update(key)
                if not self.insert(**kv):
                    query = self._build_query(key)
                    self._db(query).update(**self._filter_fields(value))
            else:
                raise SyntaxError(
                    'key must have all fields from primary key: %s'%\
                    (self._primarykey))
        elif str(key).isdigit():
            if key == 0:
                self.insert(**self._filter_fields(value))
            elif self._db(self._id == key)\
                    .update(**self._filter_fields(value)) is None:
                raise SyntaxError('No such record: %s' % key)
        else:
            if isinstance(key, dict):
                raise SyntaxError(
                    'value must be a dictionary: %s' % value)
            osetattr(self, str(key), value)

    __getattr__ = __getitem__

    def __setattr__(self, key, value):
        if key[:1]!='_' and key in self:
            raise SyntaxError('Object exists and cannot be redefined: %s' % key)
        osetattr(self,key,value)

    def __delitem__(self, key):
        if isinstance(key, dict):
            query = self._build_query(key)
            if not self._db(query).delete():
                raise SyntaxError('No such record: %s' % key)
        elif not str(key).isdigit() or \
                not self._db(self._id == key).delete():
            raise SyntaxError('No such record: %s' % key)

    def __contains__(self,key):
        return hasattr(self,key)

    has_key = __contains__

    def items(self):
        return self.__dict__.items()

    def __iter__(self):
        for fieldname in self.fields:
            yield self[fieldname]

    def iteritems(self):
        return self.__dict__.iteritems()


    def __repr__(self):
        return '<Table %s (%s)>' % (self._tablename,','.join(self.fields()))

    def __str__(self):
        if self._ot is not None:
            ot = self._db._adapter.QUOTE_TEMPLATE % self._ot
            if 'Oracle' in str(type(self._db._adapter)):
                return '%s %s' % (ot, self._tablename)
            return '%s AS %s' % (ot, self._tablename)
        return self._tablename

    def _drop(self, mode = ''):
        return self._db._adapter._drop(self, mode)

    def drop(self, mode = ''):
        return self._db._adapter.drop(self,mode)

    def _listify(self,fields,update=False):
        new_fields = {} # format: new_fields[name] = (field,value)

        # store all fields passed as input in new_fields
        for name in fields:
            if not name in self.fields:
                if name != 'id':
                    raise SyntaxError(
                        'Field %s does not belong to the table' % name)
            else:
                field = self[name]
                value = fields[name]
                if field.filter_in:
                    value = field.filter_in(value)
                new_fields[name] = (field,value)

        # check all fields that should be in the table but are not passed
        to_compute = []
        for ofield in self:
            name = ofield.name
            if not name in new_fields:
                # if field is supposed to be computed, compute it!
                if ofield.compute: # save those to compute for later
                    to_compute.append((name,ofield))
                # if field is required, check its default value
                elif not update and not ofield.default is None:
                    value = ofield.default
                    fields[name] = value
                    new_fields[name] = (ofield,value)
                # if this is an update, user the update field instead
                elif update and not ofield.update is None:
                    value = ofield.update
                    fields[name] = value
                    new_fields[name] = (ofield,value)
                # if the field is still not there but it should, error
                elif not update and ofield.required:
                    raise RuntimeError(
                        'Table: missing required field: %s' % name)
        # now deal with fields that are supposed to be computed
        if to_compute:
            row = Row(fields)
            for name,ofield in to_compute:
                # try compute it
                try:
                    row[name] = new_value = ofield.compute(row)
                    new_fields[name] = (ofield, new_value)
                except (KeyError, AttributeError):
                    # error silently unless field is required!
                    if ofield.required:
                        raise SyntaxError('unable to compute field: %s' % name)
        return new_fields.values()

    def _attempt_upload(self, fields):
        for field in self:
            if field.type=='upload' and field.name in fields:
                value = fields[field.name]
                if value and not isinstance(value,str):
                    if hasattr(value,'file') and hasattr(value,'filename'):
                        new_name = field.store(value.file,filename=value.filename)
                    elif hasattr(value,'read') and hasattr(value,'name'):
                        new_name = field.store(value,filename=value.name)
                    else:
                        raise RuntimeError("Unable to handle upload")
                    fields[field.name] = new_name

    def _defaults(self, fields):
        "If there are no fields/values specified, return table defaults"
        if not fields:
            fields = {}
            for field in self:
                if field.type != "id":
                    fields[field.name] = field.default
        return fields

    def _insert(self, **fields):
        fields = self._defaults(fields)
        return self._db._adapter._insert(self, self._listify(fields))

    def insert(self, **fields):
        fields = self._defaults(fields)
        self._attempt_upload(fields)
        if any(f(fields) for f in self._before_insert): return 0
        ret =  self._db._adapter.insert(self, self._listify(fields))
        if ret and self._after_insert:
            fields = Row(fields)
            [f(fields,ret) for f in self._after_insert]
        return ret

    def validate_and_insert(self,**fields):
        response = Row()
        response.errors = Row()
        new_fields = copy.copy(fields)
        for key,value in fields.iteritems():
            value,error = self[key].validate(value)
            if error:
                response.errors[key] = "%s" % error
            else:
                new_fields[key] = value
        if not response.errors:
            response.id = self.insert(**new_fields)
        else:
            response.id = None
        return response

    def update_or_insert(self, _key=DEFAULT, **values):
        if _key is DEFAULT:
            record = self(**values)
        elif isinstance(_key,dict):
            record = self(**_key)
        else:
            record = self(_key)
        if record:
            record.update_record(**values)
            newid = None
        else:
            newid = self.insert(**values)
        return newid

    def bulk_insert(self, items):
        """
        here items is a list of dictionaries
        """
        items = [self._listify(item) for item in items]
        if any(f(item) for item in items for f in self._before_insert):return 0
        ret = self._db._adapter.bulk_insert(self,items)
        ret and [[f(item,ret[k]) for k,item in enumerate(items)] for f in self._after_insert]
        return ret

    def _truncate(self, mode = None):
        return self._db._adapter._truncate(self, mode)

    def truncate(self, mode = None):
        return self._db._adapter.truncate(self, mode)

    def import_from_csv_file(
        self,
        csvfile,
        id_map=None,
        null='<NULL>',
        unique='uuid',
        id_offset=None, # id_offset used only when id_map is None
        *args, **kwargs
        ):
        """
        Import records from csv file.
        Column headers must have same names as table fields.
        Field 'id' is ignored.
        If column names read 'table.file' the 'table.' prefix is ignored.
        'unique' argument is a field which must be unique
            (typically a uuid field)
        'restore' argument is default False;
            if set True will remove old values in table first.
        'id_map' ff set to None will not map ids.
        The import will keep the id numbers in the restored table.
        This assumes that there is an field of type id that
        is integer and in incrementing order.
        Will keep the id numbers in restored table.
        """

        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        restore = kwargs.get('restore', False)
        if restore:
            self._db[self].truncate()

        reader = csv.reader(csvfile, delimiter=delimiter,
                            quotechar=quotechar, quoting=quoting)
        colnames = None
        if isinstance(id_map, dict):
            if not self._tablename in id_map:
                id_map[self._tablename] = {}
            id_map_self = id_map[self._tablename]

        def fix(field, value, id_map, id_offset):
            list_reference_s='list:reference'
            if value == null:
                value = None
            elif field.type=='blob':
                value = base64.b64decode(value)
            elif field.type=='double' or field.type=='float':
                if not value.strip():
                    value = None
                else:
                    value = float(value)
            elif field.type in ('integer','bigint'):
                if not value.strip():
                    value = None
                else:
                    value = long(value)
            elif field.type.startswith('list:string'):
                value = bar_decode_string(value)
            elif field.type.startswith(list_reference_s):
                ref_table = field.type[len(list_reference_s):].strip()
                if id_map is not None:
                    value = [id_map[ref_table][long(v)] \
                             for v in bar_decode_string(value)]
                else:
                    value = [v for v in bar_decode_string(value)]
            elif field.type.startswith('list:'):
                value = bar_decode_integer(value)
            elif id_map and field.type.startswith('reference'):
                try:
                    value = id_map[field.type[9:].strip()][long(value)]
                except KeyError:
                    pass
            elif id_offset and field.type.startswith('reference'):
                try:
                    value = id_offset[field.type[9:].strip()]+long(value)
                except KeyError:
                    pass
            return (field.name, value)

        def is_id(colname):
            if colname in self:
                return self[colname].type == 'id'
            else:
                return False

        first = True
        unique_idx = None
        for line in reader:
            if not line:
                break
            if not colnames:
                colnames = [x.split('.',1)[-1] for x in line][:len(line)]
                cols, cid = [], None
                for i,colname in enumerate(colnames):
                    if is_id(colname):
                        cid = i
                    else:
                        cols.append(i)
                    if colname == unique:
                        unique_idx = i
            else:
                items = [fix(self[colnames[i]], line[i], id_map, id_offset) \
                             for i in cols if colnames[i] in self.fields]

                if not id_map and cid is not None and id_offset is not None and not unique_idx:
                    csv_id = long(line[cid])
                    curr_id = self.insert(**dict(items))
                    if first:
                        first = False
                        # First curr_id is bigger than csv_id,
                        # then we are not restoring but
                        # extending db table with csv db table
                        if curr_id>csv_id:
                            id_offset[self._tablename] = curr_id-csv_id
                        else:
                            id_offset[self._tablename] = 0
                    # create new id until we get the same as old_id+offset
                    while curr_id<csv_id+id_offset[self._tablename]:
                        self._db(self._db[self][colnames[cid]] == curr_id).delete()
                        curr_id = self.insert(**dict(items))
                # Validation. Check for duplicate of 'unique' &,
                # if present, update instead of insert.
                elif not unique_idx:
                    new_id = self.insert(**dict(items))
                else:
                    unique_value = line[unique_idx]
                    query = self._db[self][unique] == unique_value
                    record = self._db(query).select().first()
                    if record:
                        record.update_record(**dict(items))
                        new_id = record[self._id.name]
                    else:
                        new_id = self.insert(**dict(items))
                if id_map and cid is not None:
                    id_map_self[long(line[cid])] = new_id

    def as_dict(self, flat=False, sanitize=True, field_options=True):
        tablename = str(self)
        table_as_dict = dict(name=tablename, items={}, fields=[],
        sequence_name=self._sequence_name,
        trigger_name=self._trigger_name,
        common_filter=self._common_filter, format=self._format,
        singular=self._singular, plural=self._plural)

        for field in self:
            if (field.readable or field.writable) or (not sanitize):
                table_as_dict["fields"].append(field.name)
                table_as_dict["items"][field.name] = \
                    field.as_dict(flat=flat, sanitize=sanitize,
                                  options=field_options)
        return table_as_dict

    def as_xml(self, sanitize=True, field_options=True):
        if not have_serializers:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize,
                         field_options=field_options)
        return serializers.xml(d)

    def as_json(self, sanitize=True, field_options=True):
        if not have_serializers:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize,
                         field_options=field_options)
        return serializers.json(d)

    def as_yaml(self, sanitize=True, field_options=True):
        if not have_serializers:
            raise ImportError("No YAML serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize,
                         field_options=field_options)
        return serializers.yaml(d)

    def with_alias(self, alias):
        return self._db._adapter.alias(self,alias)

    def on(self, query):
        return Expression(self._db,self._db._adapter.ON,self,query)

def archive_record(qset,fs,archive_table,current_record):
    tablenames = qset.db._adapter.tables(qset.query)
    if len(tablenames)!=1: raise RuntimeError("cannot update join")
    table = qset.db[tablenames[0]]
    for row in qset.select():
        fields = archive_table._filter_fields(row)
        fields[current_record] = row.id
        archive_table.insert(**fields)
    return False



class Expression(object):

    def __init__(
        self,
        db,
        op,
        first=None,
        second=None,
        type=None,
        **optional_args
        ):

        self.db = db
        self.op = op
        self.first = first
        self.second = second
        self._table = getattr(first,'_table',None)
        ### self._tablename =  first._tablename ## CHECK
        if not type and first and hasattr(first,'type'):
            self.type = first.type
        else:
            self.type = type
        self.optional_args = optional_args

    def sum(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'SUM', self.type)

    def max(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'MAX', self.type)

    def min(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'MIN', self.type)

    def len(self):
        db = self.db
        return Expression(db, db._adapter.LENGTH, self, None, 'integer')

    def avg(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'AVG', self.type)

    def abs(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'ABS', self.type)

    def lower(self):
        db = self.db
        return Expression(db, db._adapter.LOWER, self, None, self.type)

    def upper(self):
        db = self.db
        return Expression(db, db._adapter.UPPER, self, None, self.type)

    def replace(self,a,b):
        db = self.db
        return Expression(db, db._adapter.REPLACE, self, (a,b), self.type)

    def year(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'year', 'integer')

    def month(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'month', 'integer')

    def day(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'day', 'integer')

    def hour(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'hour', 'integer')

    def minutes(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'minute', 'integer')

    def coalesce(self,*others):
        db = self.db
        return Expression(db, db._adapter.COALESCE, self, others, self.type)

    def coalesce_zero(self):
        db = self.db
        return Expression(db, db._adapter.COALESCE_ZERO, self, None, self.type)

    def seconds(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'second', 'integer')

    def epoch(self):
        db = self.db
        return Expression(db, db._adapter.EPOCH, self, None, 'integer')

    def __getslice__(self, start, stop):
        db = self.db
        if start < 0:
            pos0 = '(%s - %d)' % (self.len(), abs(start) - 1)
        else:
            pos0 = start + 1

        if stop < 0:
            length = '(%s - %d - %s)' % (self.len(), abs(stop) - 1, pos0)
        elif stop == sys.maxint:
            length = self.len()
        else:
            length = '(%s - %s)' % (stop + 1, pos0)
        return Expression(db,db._adapter.SUBSTRING,
                          self, (pos0, length), self.type)

    def __getitem__(self, i):
        return self[i:i + 1]

    def __str__(self):
        return self.db._adapter.expand(self,self.type)

    def __or__(self, other):  # for use in sortby
        db = self.db
        return Expression(db,db._adapter.COMMA,self,other,self.type)

    def __invert__(self):
        db = self.db
        if hasattr(self,'_op') and self.op == db._adapter.INVERT:
            return self.first
        return Expression(db,db._adapter.INVERT,self,type=self.type)

    def __add__(self, other):
        db = self.db
        return Expression(db,db._adapter.ADD,self,other,self.type)

    def __sub__(self, other):
        db = self.db
        if self.type in ('integer','bigint'):
            result_type = 'integer'
        elif self.type in ['date','time','datetime','double','float']:
            result_type = 'double'
        elif self.type.startswith('decimal('):
            result_type = self.type
        else:
            raise SyntaxError("subtraction operation not supported for type")
        return Expression(db,db._adapter.SUB,self,other,result_type)

    def __mul__(self, other):
        db = self.db
        return Expression(db,db._adapter.MUL,self,other,self.type)

    def __div__(self, other):
        db = self.db
        return Expression(db,db._adapter.DIV,self,other,self.type)

    def __mod__(self, other):
        db = self.db
        return Expression(db,db._adapter.MOD,self,other,self.type)

    def __eq__(self, value):
        db = self.db
        return Query(db, db._adapter.EQ, self, value)

    def __ne__(self, value):
        db = self.db
        return Query(db, db._adapter.NE, self, value)

    def __lt__(self, value):
        db = self.db
        return Query(db, db._adapter.LT, self, value)

    def __le__(self, value):
        db = self.db
        return Query(db, db._adapter.LE, self, value)

    def __gt__(self, value):
        db = self.db
        return Query(db, db._adapter.GT, self, value)

    def __ge__(self, value):
        db = self.db
        return Query(db, db._adapter.GE, self, value)

    def like(self, value, case_sensitive=False):
        db = self.db
        op = case_sensitive and db._adapter.LIKE or db._adapter.ILIKE
        return Query(db, op, self, value)

    def regexp(self, value):
        db = self.db
        return Query(db, db._adapter.REGEXP, self, value)

    def belongs(self, *value):
        """
        Accepts the following inputs:
           field.belongs(1,2)
           field.belongs((1,2))
           field.belongs(query)

        Does NOT accept:
           field.belongs(1)
        """
        db = self.db
        if len(value) == 1:
            value = value[0]
        if isinstance(value,Query):
            value = db(value)._select(value.first._table._id)
        return Query(db, db._adapter.BELONGS, self, value)

    def startswith(self, value):
        db = self.db
        if not self.type in ('string', 'text', 'json'):
            raise SyntaxError("startswith used with incompatible field type")
        return Query(db, db._adapter.STARTSWITH, self, value)

    def endswith(self, value):
        db = self.db
        if not self.type in ('string', 'text', 'json'):
            raise SyntaxError("endswith used with incompatible field type")
        return Query(db, db._adapter.ENDSWITH, self, value)

    def contains(self, value, all=False, case_sensitive=False):
        """
        The case_sensitive parameters is only useful for PostgreSQL
        For other RDMBs it is ignored and contains is always case in-sensitive
        For MongoDB and GAE contains is always case sensitive
        """
        db = self.db
        if isinstance(value,(list, tuple)):
            subqueries = [self.contains(str(v).strip(),case_sensitive=case_sensitive)
                          for v in value if str(v).strip()]
            if not subqueries:
                return self.contains('')
            else:
                return reduce(all and AND or OR,subqueries)
        if not self.type in ('string', 'text', 'json') and not self.type.startswith('list:'):
            raise SyntaxError("contains used with incompatible field type")
        return Query(db, db._adapter.CONTAINS, self, value, case_sensitive=case_sensitive)

    def with_alias(self, alias):
        db = self.db
        return Expression(db, db._adapter.AS, self, alias, self.type)

    # GIS expressions

    def st_asgeojson(self, precision=15, options=0, version=1):
        return Expression(self.db, self.db._adapter.ST_ASGEOJSON, self,
                          dict(precision=precision, options=options,
                               version=version), 'string')

    def st_astext(self):
        db = self.db
        return Expression(db, db._adapter.ST_ASTEXT, self, type='string')

    def st_x(self):
        db = self.db
        return Expression(db, db._adapter.ST_X, self, type='string')

    def st_y(self):
        db = self.db
        return Expression(db, db._adapter.ST_Y, self, type='string')

    def st_distance(self, other):
        db = self.db
        return Expression(db,db._adapter.ST_DISTANCE,self,other, 'double')

    def st_simplify(self, value):
        db = self.db
        return Expression(db, db._adapter.ST_SIMPLIFY, self, value, self.type)

    # GIS queries

    def st_contains(self, value):
        db = self.db
        return Query(db, db._adapter.ST_CONTAINS, self, value)

    def st_equals(self, value):
        db = self.db
        return Query(db, db._adapter.ST_EQUALS, self, value)

    def st_intersects(self, value):
        db = self.db
        return Query(db, db._adapter.ST_INTERSECTS, self, value)

    def st_overlaps(self, value):
        db = self.db
        return Query(db, db._adapter.ST_OVERLAPS, self, value)

    def st_touches(self, value):
        db = self.db
        return Query(db, db._adapter.ST_TOUCHES, self, value)

    def st_within(self, value):
        db = self.db
        return Query(db, db._adapter.ST_WITHIN, self, value)

    # for use in both Query and sortby


class SQLCustomType(object):
    """
    allows defining of custom SQL types

    Example::

        decimal = SQLCustomType(
            type ='double',
            native ='integer',
            encoder =(lambda x: int(float(x) * 100)),
            decoder = (lambda x: Decimal("0.00") + Decimal(str(float(x)/100)) )
            )

        db.define_table(
            'example',
            Field('value', type=decimal)
            )

    :param type: the web2py type (default = 'string')
    :param native: the backend type
    :param encoder: how to encode the value to store it in the backend
    :param decoder: how to decode the value retrieved from the backend
    :param validator: what validators to use ( default = None, will use the
        default validator for type)
    """

    def __init__(
        self,
        type='string',
        native=None,
        encoder=None,
        decoder=None,
        validator=None,
        _class=None,
        ):

        self.type = type
        self.native = native
        self.encoder = encoder or (lambda x: x)
        self.decoder = decoder or (lambda x: x)
        self.validator = validator
        self._class = _class or type

    def startswith(self, text=None):
        try:
            return self.type.startswith(self, text)
        except TypeError:
            return False

    def __getslice__(self, a=0, b=100):
        return None

    def __getitem__(self, i):
        return None

    def __str__(self):
        return self._class

class FieldVirtual(object):
    def __init__(self, name, f=None, ftype='string',label=None,table_name=None):
        # for backward compatibility
        (self.name, self.f) = (name, f) if f else ('unknown', name)
        self.type = ftype
        self.label = label or self.name.capitalize().replace('_',' ')
        self.represent = lambda v,r:v
        self.formatter = IDENTITY
        self.comment = None
        self.readable = True
        self.writable = False
        self.requires = None
        self.widget = None
        self.tablename = table_name
        self.filter_out = None
    def __str__(self):
        return '%s.%s' % (self.tablename, self.name)

class FieldMethod(object):
    def __init__(self, name, f=None, handler=None):
        # for backward compatibility
        (self.name, self.f) = (name, f) if f else ('unknown', name)
        self.handler = handler

def list_represent(x,r=None):
    return ', '.join(str(y) for y in x or [])

class Field(Expression):

    Virtual = FieldVirtual
    Method = FieldMethod
    Lazy = FieldMethod # for backward compatibility

    """
    an instance of this class represents a database field

    example::

        a = Field(name, 'string', length=32, default=None, required=False,
            requires=IS_NOT_EMPTY(), ondelete='CASCADE',
            notnull=False, unique=False,
            uploadfield=True, widget=None, label=None, comment=None,
            uploadfield=True, # True means store on disk,
                              # 'a_field_name' means store in this field in db
                              # False means file content will be discarded.
            writable=True, readable=True, update=None, authorize=None,
            autodelete=False, represent=None, uploadfolder=None,
            uploadseparate=False # upload to separate directories by uuid_keys
                                 # first 2 character and tablename.fieldname
                                 # False - old behavior
                                 # True - put uploaded file in
                                 #   <uploaddir>/<tablename>.<fieldname>/uuid_key[:2]
                                 #        directory)
            uploadfs=None     # a pyfilesystem where to store upload

    to be used as argument of DAL.define_table

    allowed field types:
    string, boolean, integer, double, text, blob,
    date, time, datetime, upload, password

    """

    def __init__(
        self,
        fieldname,
        type='string',
        length=None,
        default=DEFAULT,
        required=False,
        requires=DEFAULT,
        ondelete='CASCADE',
        notnull=False,
        unique=False,
        uploadfield=True,
        widget=None,
        label=None,
        comment=None,
        writable=True,
        readable=True,
        update=None,
        authorize=None,
        autodelete=False,
        represent=None,
        uploadfolder=None,
        uploadseparate=False,
        uploadfs=None,
        compute=None,
        custom_store=None,
        custom_retrieve=None,
        custom_retrieve_file_properties=None,
        custom_delete=None,
        filter_in = None,
        filter_out = None,
        custom_qualifier = None,
        map_none = None,
        ):
        self._db = self.db = None # both for backward compatibility
        self.op = None
        self.first = None
        self.second = None
        self.name = fieldname = cleanup(fieldname)
        if not isinstance(fieldname,str) or hasattr(Table,fieldname) or \
                fieldname[0] == '_' or REGEX_PYTHON_KEYWORDS.match(fieldname):
            raise SyntaxError('Field: invalid field name: %s' % fieldname)
        self.type = type if not isinstance(type, (Table,Field)) else 'reference %s' % type
        self.length = length if not length is None else DEFAULTLENGTH.get(self.type,512)
        self.default = default if default!=DEFAULT else (update or None)
        self.required = required  # is this field required
        self.ondelete = ondelete.upper()  # this is for reference fields only
        self.notnull = notnull
        self.unique = unique
        self.uploadfield = uploadfield
        self.uploadfolder = uploadfolder
        self.uploadseparate = uploadseparate
        self.uploadfs = uploadfs
        self.widget = widget
        self.comment = comment
        self.writable = writable
        self.readable = readable
        self.update = update
        self.authorize = authorize
        self.autodelete = autodelete
        self.represent = list_represent if \
            represent==None and type in ('list:integer','list:string') else represent
        self.compute = compute
        self.isattachment = True
        self.custom_store = custom_store
        self.custom_retrieve = custom_retrieve
        self.custom_retrieve_file_properties = custom_retrieve_file_properties
        self.custom_delete = custom_delete
        self.filter_in = filter_in
        self.filter_out = filter_out
        self.custom_qualifier = custom_qualifier
        self.label = label if label!=None else fieldname.replace('_',' ').title()
        self.requires = requires if requires!=None else []
        self.map_none = map_none

    def set_attributes(self,*args,**attributes):
        self.__dict__.update(*args,**attributes)

    def clone(self,point_self_references_to=False,**args):
        field = copy.copy(self)
        if point_self_references_to and \
                field.type == 'reference %s'+field._tablename:
            field.type = 'reference %s' % point_self_references_to
        field.__dict__.update(args)
        return field

    def store(self, file, filename=None, path=None):
        if self.custom_store:
            return self.custom_store(file,filename,path)
        if isinstance(file, cgi.FieldStorage):
            filename = filename or file.filename
            file = file.file
        elif not filename:
            filename = file.name
        filename = os.path.basename(filename.replace('/', os.sep)\
                                        .replace('\\', os.sep))
        m = REGEX_STORE_PATTERN.search(filename)
        extension = m and m.group('e') or 'txt'
        uuid_key = web2py_uuid().replace('-', '')[-16:]
        encoded_filename = base64.b16encode(filename).lower()
        newfilename = '%s.%s.%s.%s' % \
            (self._tablename, self.name, uuid_key, encoded_filename)
        newfilename = newfilename[:(self.length - 1 - len(extension))] + '.' + extension
        self_uploadfield = self.uploadfield
        if isinstance(self_uploadfield,Field):
            blob_uploadfield_name = self_uploadfield.uploadfield
            keys={self_uploadfield.name: newfilename,
                  blob_uploadfield_name: file.read()}
            self_uploadfield.table.insert(**keys)
        elif self_uploadfield == True:
            if path:
                pass
            elif self.uploadfolder:
                path = self.uploadfolder
            elif self.db._adapter.folder:
                path = pjoin(self.db._adapter.folder, '..', 'uploads')
            else:
                raise RuntimeError(
                    "you must specify a Field(...,uploadfolder=...)")
            if self.uploadseparate:
                if self.uploadfs:
                    raise RuntimeError("not supported")
                path = pjoin(path,"%s.%s" %(self._tablename, self.name),
                                    uuid_key[:2])
            if not exists(path):
                os.makedirs(path)
            pathfilename = pjoin(path, newfilename)
            if self.uploadfs:
                dest_file = self.uploadfs.open(newfilename, 'wb')
            else:
                dest_file = open(pathfilename, 'wb')
            try:
                shutil.copyfileobj(file, dest_file)
            except IOError:
                raise IOError(
                    'Unable to store file "%s" because invalid permissions, readonly file system, or filename too long' % pathfilename)
            dest_file.close()
        return newfilename

    def retrieve(self, name, path=None, nameonly=False):
        """
        if nameonly==True return (filename, fullfilename) instead of
        (filename, stream)
        """
        self_uploadfield = self.uploadfield
        if self.custom_retrieve:
            return self.custom_retrieve(name, path)
        import http
        if self.authorize or isinstance(self_uploadfield, str):
            row = self.db(self == name).select().first()
            if not row:
                raise http.HTTP(404)
        if self.authorize and not self.authorize(row):
            raise http.HTTP(403)
        m = REGEX_UPLOAD_PATTERN.match(name)
        if not m or not self.isattachment:
            raise TypeError('Can\'t retrieve %s' % name)
        file_properties = self.retrieve_file_properties(name,path)
        filename = file_properties['filename']
        if isinstance(self_uploadfield, str):  # ## if file is in DB
            stream = StringIO.StringIO(row[self_uploadfield] or '')
        elif isinstance(self_uploadfield,Field):
            blob_uploadfield_name = self_uploadfield.uploadfield
            query = self_uploadfield == name
            data = self_uploadfield.table(query)[blob_uploadfield_name]
            stream = StringIO.StringIO(data)
        elif self.uploadfs:
            # ## if file is on pyfilesystem
            stream = self.uploadfs.open(name, 'rb')
        else:
            # ## if file is on regular filesystem
            # this is intentially a sting with filename and not a stream
            # this propagates and allows stream_file_or_304_or_206 to be called
            fullname = pjoin(file_properties['path'],name)
            if nameonly:
                return (filename, fullname)
            stream = open(fullname,'rb')
        return (filename, stream)

    def retrieve_file_properties(self, name, path=None):
        self_uploadfield = self.uploadfield
        if self.custom_retrieve_file_properties:
            return self.custom_retrieve_file_properties(name, path)
        try:
            m = REGEX_UPLOAD_PATTERN.match(name)
            if not m or not self.isattachment:
                raise TypeError('Can\'t retrieve %s file properties' % name)
            filename = base64.b16decode(m.group('name'), True)
            filename = REGEX_CLEANUP_FN.sub('_', filename)
        except (TypeError, AttributeError):
            filename = name
        if isinstance(self_uploadfield, str):  # ## if file is in DB
            return dict(path=None,filename=filename)
        elif isinstance(self_uploadfield,Field):
            return dict(path=None,filename=filename)
        else:
            # ## if file is on filesystem
            if path:
                pass
            elif self.uploadfolder:
                path = self.uploadfolder
            else:
                path = pjoin(self.db._adapter.folder, '..', 'uploads')
            if self.uploadseparate:
                t = m.group('table')
                f = m.group('field')
                u = m.group('uuidkey')
                path = pjoin(path,"%s.%s" % (t,f),u[:2])
            return dict(path=path,filename=filename)


    def formatter(self, value):
        requires = self.requires
        if value is None or not requires:
            return value or self.map_none
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        elif isinstance(requires, tuple):
            requires = list(requires)
        else:
            requires = copy.copy(requires)
        requires.reverse()
        for item in requires:
            if hasattr(item, 'formatter'):
                value = item.formatter(value)
        return value

    def validate(self, value):
        if not self.requires or self.requires == DEFAULT:
            return ((value if value!=self.map_none else None), None)
        requires = self.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for validator in requires:
            (value, error) = validator(value)
            if error:
                return (value, error)
        return ((value if value!=self.map_none else None), None)

    def count(self, distinct=None):
        return Expression(self.db, self.db._adapter.COUNT, self, distinct, 'integer')

    def as_dict(self, flat=False, sanitize=True, options=True):

        attrs = ('type', 'length', 'default', 'required',
                 'ondelete', 'notnull', 'unique', 'uploadfield',
                 'widget', 'label', 'comment', 'writable', 'readable',
                 'update', 'authorize', 'autodelete', 'represent',
                 'uploadfolder', 'uploadseparate', 'uploadfs',
                 'compute', 'custom_store', 'custom_retrieve',
                 'custom_retrieve_file_properties', 'custom_delete',
                 'filter_in', 'filter_out', 'custom_qualifier',
                 'map_none', 'name')

        SERIALIZABLE_TYPES = (int, long, basestring, dict, list,
                              float, tuple, bool, type(None))

        def flatten(obj):
            if flat:
                if isinstance(obj, flatten.__class__):
                    return str(type(obj))
                elif isinstance(obj, type):
                    try:
                        return str(obj).split("'")[1]
                    except IndexError:
                        return str(obj)
                elif not isinstance(obj, SERIALIZABLE_TYPES):
                    return str(obj)
                elif isinstance(obj, dict):
                    newobj = dict()
                    for k, v in obj.items():
                        newobj[k] = flatten(v)
                    return newobj
                elif isinstance(obj, (list, tuple, set)):
                    return [flatten(v) for v in obj]
                else:
                    return obj
            elif isinstance(obj, (dict, set)):
                return obj.copy()
            else: return obj

        def filter_requires(t, r, options=True):
            if sanitize and any([keyword in str(t).upper() for
                                 keyword in ("CRYPT", "IS_STRONG")]):
                return None

            if not isinstance(r, dict):
                if options and hasattr(r, "options"):
                    if callable(r.options):
                        r.options()
                newr = r.__dict__.copy()
            else:
                newr = r.copy()

            # remove options if not required
            if not options and newr.has_key("labels"):
                [newr.update({key:None}) for key in
                 ("labels", "theset") if (key in newr)]

            for k, v in newr.items():
                if k == "other":
                    if isinstance(v, dict):
                        otype, other = v.popitem()
                    else:
                        otype = flatten(type(v))
                        other = v
                    newr[k] = {otype: filter_requires(otype, other,
                                                      options=options)}
                else:
                    newr[k] = flatten(v)
            return newr

        if isinstance(self.requires, (tuple, list, set)):
            requires = dict([(flatten(type(r)),
                             filter_requires(type(r), r,
                                             options=options)) for
                             r in self.requires])
        else:
            requires = {flatten(type(self.requires)):
                        filter_requires(type(self.requires),
                            self.requires, options=options)}

        d = dict(colname="%s.%s" % (self.tablename, self.name),
                 requires=requires)
        d.update([(attr, flatten(getattr(self, attr))) for attr in attrs])
        return d

    def as_xml(self, sanitize=True, options=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize,
                         options=options)
        return xml(d)

    def as_json(self, sanitize=True, options=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize,
                         options=options)
        return json(d)

    def as_yaml(self, sanitize=True, options=True):
        if have_serializers:
            d = self.as_dict(flat=True, sanitize=sanitize,
                             options=options)
            return serializers.yaml(d)
        else:
            raise ImportError("No YAML serializers available")

    def __nonzero__(self):
        return True

    def __str__(self):
        try:
            return '%s.%s' % (self.tablename, self.name)
        except:
            return '<no table>.%s' % self.name


class Query(object):

    """
    a query object necessary to define a set.
    it can be stored or can be passed to DAL.__call__() to obtain a Set

    Example::

        query = db.users.name=='Max'
        set = db(query)
        records = set.select()

    """

    def __init__(
        self,
        db,
        op,
        first=None,
        second=None,
        ignore_common_filters = False,
        **optional_args
        ):
        self.db = self._db = db
        self.op = op
        self.first = first
        self.second = second
        self.ignore_common_filters = ignore_common_filters
        self.optional_args = optional_args

    def __repr__(self):
        return '<Query %s>' % BaseAdapter.expand(self.db._adapter,self)

    def __str__(self):
        return self.db._adapter.expand(self)

    def __and__(self, other):
        return Query(self.db,self.db._adapter.AND,self,other)

    __rand__ = __and__

    def __or__(self, other):
        return Query(self.db,self.db._adapter.OR,self,other)

    __ror__ = __or__

    def __invert__(self):
        if self.op==self.db._adapter.NOT:
            return self.first
        return Query(self.db,self.db._adapter.NOT,self)

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __ne__(self, other):
        return not (self == other)

    def case(self,t=1,f=0):
        return self.db._adapter.CASE(self,t,f)

    def as_dict(self, flat=False, sanitize=True):
        """Experimental stuff

        This allows to return a plain dictionary with the basic
        query representation. Can be used with json/xml services
        for client-side db I/O

        Example:
        >>> q = db.auth_user.id != 0
        >>> q.as_dict(flat=True)
        {"op": "NE", "first":{"tablename": "auth_user",
                              "fieldname": "id"},
                     "second":0}
        """

        SERIALIZABLE_TYPES = (tuple, dict, list, int, long, float,
                              basestring, type(None), bool)
        def loop(d):
            newd = dict()
            for k, v in d.items():
                if k in ("first", "second"):
                    if isinstance(v, self.__class__):
                        newd[k] = loop(v.__dict__)
                    elif isinstance(v, Field):
                        newd[k] = {"tablename": v._tablename,
                                   "fieldname": v.name}
                    elif isinstance(v, Expression):
                        newd[k] = loop(v.__dict__)
                    elif isinstance(v, SERIALIZABLE_TYPES):
                        newd[k] = v
                    elif isinstance(v, (datetime.date,
                                        datetime.time,
                                        datetime.datetime)):
                        newd[k] = unicode(v)
                elif k == "op":
                    if callable(v):
                        newd[k] = v.__name__
                    elif isinstance(v, basestring):
                        newd[k] = v
                    else: pass # not callable or string
                elif isinstance(v, SERIALIZABLE_TYPES):
                    if isinstance(v, dict):
                        newd[k] = loop(v)
                    else: newd[k] = v
            return newd

        if flat:
            return loop(self.__dict__)
        else: return self.__dict__


    def as_xml(self, sanitize=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return xml(d)

    def as_json(self, sanitize=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return json(d)

def xorify(orderby):
    if not orderby:
        return None
    orderby2 = orderby[0]
    for item in orderby[1:]:
        orderby2 = orderby2 | item
    return orderby2

def use_common_filters(query):
    return (query and hasattr(query,'ignore_common_filters') and \
                not query.ignore_common_filters)

class Set(object):

    """
    a Set represents a set of records in the database,
    the records are identified by the query=Query(...) object.
    normally the Set is generated by DAL.__call__(Query(...))

    given a set, for example
       set = db(db.users.name=='Max')
    you can:
       set.update(db.users.name='Massimo')
       set.delete() # all elements in the set
       set.select(orderby=db.users.id, groupby=db.users.name, limitby=(0,10))
    and take subsets:
       subset = set(db.users.id<5)
    """

    def __init__(self, db, query, ignore_common_filters = None):
        self.db = db
        self._db = db # for backward compatibility
        self.dquery = None

        # if query is a dict, parse it
        if isinstance(query, dict):
            query = self.parse(query)

        if not ignore_common_filters is None and \
                use_common_filters(query) == ignore_common_filters:
            query = copy.copy(query)
            query.ignore_common_filters = ignore_common_filters
        self.query = query

    def __repr__(self):
        return '<Set %s>' % BaseAdapter.expand(self.db._adapter,self.query)

    def __call__(self, query, ignore_common_filters=False):
        if query is None:
            return self
        elif isinstance(query,Table):
            query = self.db._adapter.id_query(query)
        elif isinstance(query,str):
            query = Expression(self.db,query)
        elif isinstance(query,Field):
            query = query!=None
        if self.query:
            return Set(self.db, self.query & query,
                       ignore_common_filters=ignore_common_filters)
        else:
            return Set(self.db, query,
                       ignore_common_filters=ignore_common_filters)

    def _count(self,distinct=None):
        return self.db._adapter._count(self.query,distinct)

    def _select(self, *fields, **attributes):
        adapter = self.db._adapter
        tablenames = adapter.tables(self.query,
                                    attributes.get('join',None),
                                    attributes.get('left',None),
                                    attributes.get('orderby',None),
                                    attributes.get('groupby',None))
        fields = adapter.expand_all(fields, tablenames)
        return adapter._select(self.query,fields,attributes)

    def _delete(self):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        return db._adapter._delete(tablename,self.query)

    def _update(self, **update_fields):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        fields = db[tablename]._listify(update_fields,update=True)
        return db._adapter._update(tablename,self.query,fields)

    def as_dict(self, flat=False, sanitize=True):
        if flat:
            uid = dbname = uri = None
            codec = self.db._db_codec
            if not sanitize:
                uri, dbname, uid = (self.db._dbname, str(self.db),
                                    self.db._db_uid)
            d = {"query": self.query.as_dict(flat=flat)}
            d["db"] = {"uid": uid, "codec": codec,
                       "name": dbname, "uri": uri}
            return d
        else: return self.__dict__

    def as_xml(self, sanitize=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return xml(d)

    def as_json(self, sanitize=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return json(d)

    def parse(self, dquery):
        "Experimental: Turn a dictionary into a Query object"
        self.dquery = dquery
        return self.build(self.dquery)

    def build(self, d):
        "Experimental: see .parse()"
        op, first, second = (d["op"], d["first"],
                             d.get("second", None))
        left = right = built = None

        if op in ("AND", "OR"):
            if not (type(first), type(second)) == (dict, dict):
                raise SyntaxError("Invalid AND/OR query")
            if op == "AND":
                built = self.build(first) & self.build(second)
            else: built = self.build(first) | self.build(second)

        elif op == "NOT":
            if first is None:
                raise SyntaxError("Invalid NOT query")
            built = ~self.build(first)
        else:
            # normal operation (GT, EQ, LT, ...)
            for k, v in {"left": first, "right": second}.items():
                if isinstance(v, dict) and v.get("op"):
                    v = self.build(v)
                if isinstance(v, dict) and ("tablename" in v):
                    v = self.db[v["tablename"]][v["fieldname"]]
                if k == "left": left = v
                else: right = v

            if hasattr(self.db._adapter, op):
                opm = getattr(self.db._adapter, op)

            if op == "EQ": built = left == right
            elif op == "NE": built = left != right
            elif op == "GT": built = left > right
            elif op == "GE": built = left >= right
            elif op == "LT": built = left < right
            elif op == "LE": built = left <= right
            elif op in ("JOIN", "LEFT_JOIN", "RANDOM", "ALLOW_NULL"):
                built = Expression(self.db, opm)
            elif op in ("LOWER", "UPPER", "EPOCH", "PRIMARY_KEY",
                        "COALESCE_ZERO", "RAW", "INVERT"):
                built = Expression(self.db, opm, left)
            elif op in ("COUNT", "EXTRACT", "AGGREGATE", "SUBSTRING",
                        "REGEXP", "LIKE", "ILIKE", "STARTSWITH",
                        "ENDSWITH", "ADD", "SUB", "MUL", "DIV",
                        "MOD", "AS", "ON", "COMMA", "NOT_NULL",
                        "COALESCE", "CONTAINS", "BELONGS"):
                built = Expression(self.db, opm, left, right)
            # expression as string
            elif not (left or right): built = Expression(self.db, op)
            else:
                raise SyntaxError("Operator not supported: %s" % op)

        return built

    def isempty(self):
        return not self.select(limitby=(0,1), orderby_on_limitby=False)

    def count(self,distinct=None, cache=None):
        db = self.db
        if cache:
            cache_model, time_expire = cache
            sql = self._count(distinct=distinct)
            key = db._uri + '/' + sql
            if len(key)>200: key = hashlib_md5(key).hexdigest()
            return cache_model(
                key,
                (lambda self=self,distinct=distinct: \
                  db._adapter.count(self.query,distinct)),
                time_expire)
        return db._adapter.count(self.query,distinct)

    def select(self, *fields, **attributes):
        adapter = self.db._adapter
        tablenames = adapter.tables(self.query,
                                    attributes.get('join',None),
                                    attributes.get('left',None),
                                    attributes.get('orderby',None),
                                    attributes.get('groupby',None))
        fields = adapter.expand_all(fields, tablenames)
        return adapter.select(self.query,fields,attributes)

    def nested_select(self,*fields,**attributes):
        return Expression(self.db,self._select(*fields,**attributes))

    def delete(self):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        table = db[tablename]
        if any(f(self) for f in table._before_delete): return 0
        ret = db._adapter.delete(tablename,self.query)
        ret and [f(self) for f in table._after_delete]
        return ret

    def update(self, **update_fields):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        table = db[tablename]
        table._attempt_upload(update_fields)
        if any(f(self,update_fields) for f in table._before_update):
            return 0
        fields = table._listify(update_fields,update=True)
        if not fields:
            raise SyntaxError("No fields to update")
        ret = db._adapter.update("%s" % table,self.query,fields)
        ret and [f(self,update_fields) for f in table._after_update]
        return ret

    def update_naive(self, **update_fields):
        """
        same as update but does not call table._before_update and _after_update
        """
        tablename = self.db._adapter.get_table(self.query)
        table = self.db[tablename]
        fields = table._listify(update_fields,update=True)
        if not fields: raise SyntaxError("No fields to update")

        ret = self.db._adapter.update("%s" % table,self.query,fields)
        return ret

    def validate_and_update(self, **update_fields):
        tablename = self.db._adapter.get_table(self.query)
        response = Row()
        response.errors = Row()
        new_fields = copy.copy(update_fields)
        for key,value in update_fields.iteritems():
            value,error = self.db[tablename][key].validate(value)
            if error:
                response.errors[key] = error
            else:
                new_fields[key] = value
        table = self.db[tablename]
        if response.errors:
            response.updated = None
        else:
            if not any(f(self,new_fields) for f in table._before_update):
                fields = table._listify(new_fields,update=True)
                if not fields: raise SyntaxError("No fields to update")
                ret = self.db._adapter.update(tablename,self.query,fields)
                ret and [f(self,new_fields) for f in table._after_update]
            else:
                ret = 0
            response.updated = ret
        return response

    def delete_uploaded_files(self, upload_fields=None):
        table = self.db[self.db._adapter.tables(self.query)[0]]
        # ## mind uploadfield==True means file is not in DB
        if upload_fields:
            fields = upload_fields.keys()
        else:
            fields = table.fields
        fields = [f for f in fields if table[f].type == 'upload'
                   and table[f].uploadfield == True
                   and table[f].autodelete]
        if not fields:
            return False
        for record in self.select(*[table[f] for f in fields]):
            for fieldname in fields:
                field = table[fieldname]
                oldname = record.get(fieldname, None)
                if not oldname:
                    continue
                if upload_fields and oldname == upload_fields[fieldname]:
                    continue
                if field.custom_delete:
                    field.custom_delete(oldname)
                else:
                    uploadfolder = field.uploadfolder
                    if not uploadfolder:
                        uploadfolder = pjoin(
                            self.db._adapter.folder, '..', 'uploads')
                    if field.uploadseparate:
                        items = oldname.split('.')
                        uploadfolder = pjoin(
                            uploadfolder,
                            "%s.%s" % (items[0], items[1]),
                            items[2][:2])
                    oldpath = pjoin(uploadfolder, oldname)
                    if exists(oldpath):
                        os.unlink(oldpath)
        return False

class RecordUpdater(object):
    def __init__(self, colset, table, id):
        self.colset, self.db, self.tablename, self.id = \
            colset, table._db, table._tablename, id

    def __call__(self, **fields):
        colset, db, tablename, id = self.colset, self.db, self.tablename, self.id
        table = db[tablename]
        newfields = fields or dict(colset)
        for fieldname in newfields.keys():
            if not fieldname in table.fields or table[fieldname].type=='id':
                del newfields[fieldname]
        table._db(table._id==id,ignore_common_filters=True).update(**newfields)
        colset.update(newfields)
        return colset

class RecordDeleter(object):
    def __init__(self, table, id):
        self.db, self.tablename, self.id = table._db, table._tablename, id
    def __call__(self):
        return self.db(self.db[self.tablename]._id==self.id).delete()

class LazySet(object):
    def __init__(self, field, id):
        self.db, self.tablename, self.fieldname, self.id = \
            field.db, field._tablename, field.name, id
    def _getset(self):
        query = self.db[self.tablename][self.fieldname]==self.id
        return Set(self.db,query)
    def __repr__(self):
        return repr(self._getset())
    def __call__(self, query, ignore_common_filters=False):
        return self._getset()(query, ignore_common_filters)
    def _count(self,distinct=None):
        return self._getset()._count(distinct)
    def _select(self, *fields, **attributes):
        return self._getset()._select(*fields,**attributes)
    def _delete(self):
        return self._getset()._delete()
    def _update(self, **update_fields):
        return self._getset()._update(**update_fields)
    def isempty(self):
        return self._getset().isempty()
    def count(self,distinct=None, cache=None):
        return self._getset().count(distinct,cache)
    def select(self, *fields, **attributes):
        return self._getset().select(*fields,**attributes)
    def nested_select(self,*fields,**attributes):
        return self._getset().nested_select(*fields,**attributes)
    def delete(self):
        return self._getset().delete()
    def update(self, **update_fields):
        return self._getset().update(**update_fields)
    def update_naive(self, **update_fields):
        return self._getset().update_naive(**update_fields)
    def validate_and_update(self, **update_fields):
        return self._getset().validate_and_update(**update_fields)
    def delete_uploaded_files(self, upload_fields=None):
        return self._getset().delete_uploaded_files(upload_fields)

class VirtualCommand(object):
    def __init__(self,method,row):
        self.method=method
        self.row=row
    def __call__(self,*args,**kwargs):
        return self.method(self.row,*args,**kwargs)

def lazy_virtualfield(f):
    f.__lazy__ = True
    return f

class Rows(object):

    """
    A wrapper for the return value of a select. It basically represents a table.
    It has an iterator and each row is represented as a dictionary.
    """

    # ## TODO: this class still needs some work to care for ID/OID

    def __init__(
        self,
        db=None,
        records=[],
        colnames=[],
        compact=True,
        rawrows=None
        ):
        self.db = db
        self.records = records
        self.colnames = colnames
        self.compact = compact
        self.response = rawrows

    def __repr__(self):
        return '<Rows (%s)>' % len(self.records)

    def setvirtualfields(self,**keyed_virtualfields):
        """
        db.define_table('x',Field('number','integer'))
        if db(db.x).isempty(): [db.x.insert(number=i) for i in range(10)]

        from gluino.dal import lazy_virtualfield

        class MyVirtualFields(object):
            # normal virtual field (backward compatible, discouraged)
            def normal_shift(self): return self.x.number+1
            # lazy virtual field (because of @staticmethod)
            @lazy_virtualfield
            def lazy_shift(instance,row,delta=4): return row.x.number+delta
        db.x.virtualfields.append(MyVirtualFields())

        for row in db(db.x).select():
            print row.number, row.normal_shift, row.lazy_shift(delta=7)
        """
        if not keyed_virtualfields:
            return self
        for row in self.records:
            for (tablename,virtualfields) in keyed_virtualfields.iteritems():
                attributes = dir(virtualfields)
                if not tablename in row:
                    box = row[tablename] = Row()
                else:
                    box = row[tablename]
                updated = False
                for attribute in attributes:
                    if attribute[0] != '_':
                        method = getattr(virtualfields,attribute)
                        if hasattr(method,'__lazy__'):
                            box[attribute]=VirtualCommand(method,row)
                        elif type(method)==types.MethodType:
                            if not updated:
                                virtualfields.__dict__.update(row)
                                updated = True
                            box[attribute]=method()
        return self

    def __and__(self,other):
        if self.colnames!=other.colnames:
            raise Exception('Cannot & incompatible Rows objects')
        records = self.records+other.records
        return Rows(self.db,records,self.colnames)

    def __or__(self,other):
        if self.colnames!=other.colnames:
            raise Exception('Cannot | incompatible Rows objects')
        records = self.records
        records += [record for record in other.records \
                        if not record in records]
        return Rows(self.db,records,self.colnames)

    def __nonzero__(self):
        if len(self.records):
            return 1
        return 0

    def __len__(self):
        return len(self.records)

    def __getslice__(self, a, b):
        return Rows(self.db,self.records[a:b],self.colnames,compact=self.compact)

    def __getitem__(self, i):
        row = self.records[i]
        keys = row.keys()
        if self.compact and len(keys) == 1 and keys[0] != '_extra':
            return row[row.keys()[0]]
        return row

    def __iter__(self):
        """
        iterator over records
        """

        for i in xrange(len(self)):
            yield self[i]

    def __str__(self):
        """
        serializes the table into a csv file
        """

        s = StringIO.StringIO()
        self.export_to_csv_file(s)
        return s.getvalue()

    def first(self):
        if not self.records:
            return None
        return self[0]

    def last(self):
        if not self.records:
            return None
        return self[-1]

    def find(self,f,limitby=None):
        """
        returns a new Rows object, a subset of the original object,
        filtered by the function f
        """
        if not self:
            return Rows(self.db, [], self.colnames)
        records = []
        if limitby:
            a,b = limitby
        else:
            a,b = 0,len(self)
        k = 0
        for row in self:
            if f(row):
                if a<=k: records.append(row)
                k += 1
                if k==b: break
        return Rows(self.db, records, self.colnames)

    def exclude(self, f):
        """
        removes elements from the calling Rows object, filtered by the function f,
        and returns a new Rows object containing the removed elements
        """
        if not self.records:
            return Rows(self.db, [], self.colnames)
        removed = []
        i=0
        while i<len(self):
            row = self[i]
            if f(row):
                removed.append(self.records[i])
                del self.records[i]
            else:
                i += 1
        return Rows(self.db, removed, self.colnames)

    def sort(self, f, reverse=False):
        """
        returns a list of sorted elements (not sorted in place)
        """
        rows = Rows(self.db,[],self.colnames,compact=False)
        rows.records = sorted(self,key=f,reverse=reverse)
        return rows


    def group_by_value(self, field):
        """
        regroups the rows, by one of the fields
        """
        if not self.records:
            return {}
        key = str(field)
        grouped_row_group = dict()

        for row in self:
            value = row[key]
            if not value in grouped_row_group:
                grouped_row_group[value] = [row]
            else:
                grouped_row_group[value].append(row)
        return grouped_row_group

    def render(self, i=None, fields=None):
        """
        Takes an index and returns a copy of the indexed row with values
        transformed via the "represent" attributes of the associated fields.

        If no index is specified, a generator is returned for iteration
        over all the rows.

        fields -- a list of fields to transform (if None, all fields with
                  "represent" attributes will be transformed).
        """


        if i is None:
            return (self.repr(i, fields=fields) for i in range(len(self)))
        import sqlhtml
        row = copy.deepcopy(self.records[i])
        keys = row.keys()
        tables = [f.tablename for f in fields] if fields \
            else [k for k in keys if k != '_extra']
        for table in tables:
            repr_fields = [f.name for f in fields if f.tablename == table] \
                if fields else [k for k in row[table].keys()
                                if (hasattr(self.db[table], k) and
                                    isinstance(self.db[table][k], Field)
                                    and self.db[table][k].represent)]
            for field in repr_fields:
                row[table][field] = sqlhtml.represent(
                    self.db[table][field], row[table][field], row[table])
        if self.compact and len(keys) == 1 and keys[0] != '_extra':
            return row[keys[0]]
        return row

    def as_list(self,
                compact=True,
                storage_to_dict=True,
                datetime_to_str=False,
                custom_types=None):
        """
        returns the data as a list or dictionary.
        :param storage_to_dict: when True returns a dict, otherwise a list(default True)
        :param datetime_to_str: convert datetime fields as strings (default False)
        """
        (oc, self.compact) = (self.compact, compact)
        if storage_to_dict:
            items = [item.as_dict(datetime_to_str, custom_types) for item in self]
        else:
            items = [item for item in self]
        self.compact = compact
        return items


    def as_dict(self,
                key='id',
                compact=True,
                storage_to_dict=True,
                datetime_to_str=False,
                custom_types=None):
        """
        returns the data as a dictionary of dictionaries (storage_to_dict=True) or records (False)

        :param key: the name of the field to be used as dict key, normally the id
        :param compact: ? (default True)
        :param storage_to_dict: when True returns a dict, otherwise a list(default True)
        :param datetime_to_str: convert datetime fields as strings (default False)
        """

        # test for multiple rows
        multi = False
        f = self.first()
        if f and isinstance(key, basestring):
            multi = any([isinstance(v, f.__class__) for v in f.values()])
            if (not "." in key) and multi:
                # No key provided, default to int indices
                def new_key():
                    i = 0
                    while True:
                        yield i
                        i += 1
                key_generator = new_key()
                key = lambda r: key_generator.next()

        rows = self.as_list(compact, storage_to_dict, datetime_to_str, custom_types)
        if isinstance(key,str) and key.count('.')==1:
            (table, field) = key.split('.')
            return dict([(r[table][field],r) for r in rows])
        elif isinstance(key,str):
            return dict([(r[key],r) for r in rows])
        else:
            return dict([(key(r),r) for r in rows])

    def export_to_csv_file(self, ofile, null='<NULL>', *args, **kwargs):
        """
        export data to csv, the first line contains the column names

        :param ofile: where the csv must be exported to
        :param null: how null values must be represented (default '<NULL>')
        :param delimiter: delimiter to separate values (default ',')
        :param quotechar: character to use to quote string values (default '"')
        :param quoting: quote system, use csv.QUOTE_*** (default csv.QUOTE_MINIMAL)
        :param represent: use the fields .represent value (default False)
        :param colnames: list of column names to use (default self.colnames)
                         This will only work when exporting rows objects!!!!
                         DO NOT use this with db.export_to_csv()
        """
        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        represent = kwargs.get('represent', False)
        writer = csv.writer(ofile, delimiter=delimiter,
                            quotechar=quotechar, quoting=quoting)
        colnames = kwargs.get('colnames', self.colnames)
        write_colnames = kwargs.get('write_colnames',True)
        # a proper csv starting with the column names
        if write_colnames:
            writer.writerow(colnames)

        def none_exception(value):
            """
            returns a cleaned up value that can be used for csv export:
            - unicode text is encoded as such
            - None values are replaced with the given representation (default <NULL>)
            """
            if value is None:
                return null
            elif isinstance(value, unicode):
                return value.encode('utf8')
            elif isinstance(value,Reference):
                return long(value)
            elif hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            elif isinstance(value, (list,tuple)): # for type='list:..'
                return bar_encode(value)
            return value

        for record in self:
            row = []
            for col in colnames:
                if not REGEX_TABLE_DOT_FIELD.match(col):
                    row.append(record._extra[col])
                else:
                    (t, f) = col.split('.')
                    field = self.db[t][f]
                    if isinstance(record.get(t, None), (Row,dict)):
                        value = record[t][f]
                    else:
                        value = record[f]
                    if field.type=='blob' and not value is None:
                        value = base64.b64encode(value)
                    elif represent and field.represent:
                        value = field.represent(value)
                    row.append(none_exception(value))
            writer.writerow(row)

    def xml(self,strict=False,row_name='row',rows_name='rows'):
        """
        serializes the table using sqlhtml.SQLTABLE (if present)
        """

        if strict:
            ncols = len(self.colnames)
            return '<%s>\n%s\n</%s>' % (rows_name,
                '\n'.join(row.as_xml(row_name=row_name,
                                     colnames=self.colnames) for
                          row in self), rows_name)

        import sqlhtml
        return sqlhtml.SQLTABLE(self).xml()

    def as_xml(self,row_name='row',rows_name='rows'):
        return self.xml(strict=True, row_name=row_name, rows_name=rows_name)

    def as_json(self, mode='object', default=None):
        """
        serializes the rows to a JSON list or object with objects
        mode='object' is not implemented (should return a nested
        object structure)
        """

        items = [record.as_json(mode=mode, default=default,
                                serialize=False,
                                colnames=self.colnames) for
                 record in self]

        if have_serializers:
            return serializers.json(items,
                                    default=default or
                                    serializers.custom_json)
        elif simplejson:
            return simplejson.dumps(items)
        else:
            raise RuntimeError("missing simplejson")

    # for consistent naming yet backwards compatible
    as_csv = __str__
    json = as_json

################################################################################
# dummy function used to define some doctests
################################################################################

def test_all():
    """

    >>> if len(sys.argv)<2: db = DAL(\"sqlite://test.db\")
    >>> if len(sys.argv)>1: db = DAL(sys.argv[1])
    >>> tmp = db.define_table('users',\
              Field('stringf', 'string', length=32, required=True),\
              Field('booleanf', 'boolean', default=False),\
              Field('passwordf', 'password', notnull=True),\
              Field('uploadf', 'upload'),\
              Field('blobf', 'blob'),\
              Field('integerf', 'integer', unique=True),\
              Field('doublef', 'double', unique=True,notnull=True),\
              Field('jsonf', 'json'),\
              Field('datef', 'date', default=datetime.date.today()),\
              Field('timef', 'time'),\
              Field('datetimef', 'datetime'),\
              migrate='test_user.table')

   Insert a field

    >>> db.users.insert(stringf='a', booleanf=True, passwordf='p', blobf='0A',\
                       uploadf=None, integerf=5, doublef=3.14,\
                       jsonf={"j": True},\
                       datef=datetime.date(2001, 1, 1),\
                       timef=datetime.time(12, 30, 15),\
                       datetimef=datetime.datetime(2002, 2, 2, 12, 30, 15))
    1

    Drop the table

    >>> db.users.drop()

    Examples of insert, select, update, delete

    >>> tmp = db.define_table('person',\
              Field('name'),\
              Field('birth','date'),\
              migrate='test_person.table')
    >>> person_id = db.person.insert(name=\"Marco\",birth='2005-06-22')
    >>> person_id = db.person.insert(name=\"Massimo\",birth='1971-12-21')

    commented len(db().select(db.person.ALL))
    commented 2

    >>> me = db(db.person.id==person_id).select()[0] # test select
    >>> me.name
    'Massimo'
    >>> db.person[2].name
    'Massimo'
    >>> db.person(2).name
    'Massimo'
    >>> db.person(name='Massimo').name
    'Massimo'
    >>> db.person(db.person.name=='Massimo').name
    'Massimo'
    >>> row = db.person[2]
    >>> row.name == row['name'] == row['person.name'] == row('person.name')
    True
    >>> db(db.person.name=='Massimo').update(name='massimo') # test update
    1
    >>> db(db.person.name=='Marco').select().first().delete_record() # test delete
    1

    Update a single record

    >>> me.update_record(name=\"Max\")
    <Row {'name': 'Max', 'birth': datetime.date(1971, 12, 21), 'id': 2}>
    >>> me.name
    'Max'

    Examples of complex search conditions

    >>> len(db((db.person.name=='Max')&(db.person.birth<'2003-01-01')).select())
    1
    >>> len(db((db.person.name=='Max')&(db.person.birth<datetime.date(2003,01,01))).select())
    1
    >>> len(db((db.person.name=='Max')|(db.person.birth<'2003-01-01')).select())
    1
    >>> me = db(db.person.id==person_id).select(db.person.name)[0]
    >>> me.name
    'Max'

    Examples of search conditions using extract from date/datetime/time

    >>> len(db(db.person.birth.month()==12).select())
    1
    >>> len(db(db.person.birth.year()>1900).select())
    1

    Example of usage of NULL

    >>> len(db(db.person.birth==None).select()) ### test NULL
    0
    >>> len(db(db.person.birth!=None).select()) ### test NULL
    1

    Examples of search conditions using lower, upper, and like

    >>> len(db(db.person.name.upper()=='MAX').select())
    1
    >>> len(db(db.person.name.like('%ax')).select())
    1
    >>> len(db(db.person.name.upper().like('%AX')).select())
    1
    >>> len(db(~db.person.name.upper().like('%AX')).select())
    0

    orderby, groupby and limitby

    >>> people = db().select(db.person.name, orderby=db.person.name)
    >>> order = db.person.name|~db.person.birth
    >>> people = db().select(db.person.name, orderby=order)

    >>> people = db().select(db.person.name, orderby=db.person.name, groupby=db.person.name)

    >>> people = db().select(db.person.name, orderby=order, limitby=(0,100))

    Example of one 2 many relation

    >>> tmp = db.define_table('dog',\
               Field('name'),\
               Field('birth','date'),\
               Field('owner',db.person),\
               migrate='test_dog.table')
    >>> db.dog.insert(name='Snoopy', birth=None, owner=person_id)
    1

    A simple JOIN

    >>> len(db(db.dog.owner==db.person.id).select())
    1

    >>> len(db().select(db.person.ALL, db.dog.name,left=db.dog.on(db.dog.owner==db.person.id)))
    1

    Drop tables

    >>> db.dog.drop()
    >>> db.person.drop()

    Example of many 2 many relation and Set

    >>> tmp = db.define_table('author', Field('name'),\
                            migrate='test_author.table')
    >>> tmp = db.define_table('paper', Field('title'),\
                            migrate='test_paper.table')
    >>> tmp = db.define_table('authorship',\
            Field('author_id', db.author),\
            Field('paper_id', db.paper),\
            migrate='test_authorship.table')
    >>> aid = db.author.insert(name='Massimo')
    >>> pid = db.paper.insert(title='QCD')
    >>> tmp = db.authorship.insert(author_id=aid, paper_id=pid)

    Define a Set

    >>> authored_papers = db((db.author.id==db.authorship.author_id)&(db.paper.id==db.authorship.paper_id))
    >>> rows = authored_papers.select(db.author.name, db.paper.title)
    >>> for row in rows: print row.author.name, row.paper.title
    Massimo QCD

    Example of search condition using  belongs

    >>> set = (1, 2, 3)
    >>> rows = db(db.paper.id.belongs(set)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of search condition using nested select

    >>> nested_select = db()._select(db.authorship.paper_id)
    >>> rows = db(db.paper.id.belongs(nested_select)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of expressions

    >>> mynumber = db.define_table('mynumber', Field('x', 'integer'))
    >>> db(mynumber).delete()
    0
    >>> for i in range(10): tmp = mynumber.insert(x=i)
    >>> db(mynumber).select(mynumber.x.sum())[0](mynumber.x.sum())
    45

    >>> db(mynumber.x+2==5).select(mynumber.x + 2)[0](mynumber.x + 2)
    5

    Output in csv

    >>> print str(authored_papers.select(db.author.name, db.paper.title)).strip()
    author.name,paper.title\r
    Massimo,QCD

    Delete all leftover tables

    >>> DAL.distributed_transaction_commit(db)

    >>> db.mynumber.drop()
    >>> db.authorship.drop()
    >>> db.author.drop()
    >>> db.paper.drop()
    """
################################################################################
# deprecated since the new DAL; here only for backward compatibility
################################################################################

SQLField = Field
SQLTable = Table
SQLXorable = Expression
SQLQuery = Query
SQLSet = Set
SQLRows = Rows
SQLStorage = Row
SQLDB = DAL
GQLDB = DAL
DAL.Field = Field  # was necessary in gluon/globals.py session.connect
DAL.Table = Table  # was necessary in gluon/globals.py session.connect

################################################################################
# Geodal utils
################################################################################

def geoPoint(x,y):
    return "POINT (%f %f)" % (x,y)

def geoLine(*line):
    return "LINESTRING (%s)" % ','.join("%f %f" % item for item in line)

def geoPolygon(*line):
    return "POLYGON ((%s))" % ','.join("%f %f" % item for item in line)

################################################################################
# run tests
################################################################################

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = decoder
import codecs
import encodings

"""Caller will hand this library a buffer and ask it to either convert
it or auto-detect the type.

Based on http://code.activestate.com/recipes/52257/

Licensed under the PSF License
"""

# None represents a potentially variable byte. "##" in the XML spec...
autodetect_dict = {  # bytepattern     : ("name",
                                         (0x00, 0x00, 0xFE, 0xFF): ("ucs4_be"),
    (0xFF, 0xFE, 0x00, 0x00): ("ucs4_le"),
    (0xFE, 0xFF, None, None): ("utf_16_be"),
    (0xFF, 0xFE, None, None): ("utf_16_le"),
    (0x00, 0x3C, 0x00, 0x3F): ("utf_16_be"),
    (0x3C, 0x00, 0x3F, 0x00): ("utf_16_le"),
    (0x3C, 0x3F, 0x78, 0x6D): ("utf_8"),
    (0x4C, 0x6F, 0xA7, 0x94): ("EBCDIC")
}


def autoDetectXMLEncoding(buffer):
    """ buffer -> encoding_name
    The buffer should be at least 4 bytes long.
        Returns None if encoding cannot be detected.
        Note that encoding_name might not have an installed
        decoder (e.g. EBCDIC)
    """
    # a more efficient implementation would not decode the whole
    # buffer at once but otherwise we'd have to decode a character at
    # a time looking for the quote character...that's a pain

    encoding = "utf_8"  # according to the XML spec, this is the default
                          # this code successively tries to refine the default
                          # whenever it fails to refine, it falls back to
                          # the last place encoding was set.
    if len(buffer) >= 4:
        bytes = (byte1, byte2, byte3, byte4) = tuple(map(ord, buffer[0:4]))
        enc_info = autodetect_dict.get(bytes, None)
        if not enc_info:  # try autodetection again removing potentially
            # variable bytes
            bytes = (byte1, byte2, None, None)
            enc_info = autodetect_dict.get(bytes)
    else:
        enc_info = None

    if enc_info:
        encoding = enc_info  # we've got a guess... these are
                            #the new defaults

        # try to find a more precise encoding using xml declaration
        secret_decoder_ring = codecs.lookup(encoding)[1]
        (decoded, length) = secret_decoder_ring(buffer)
        first_line = decoded.split("\n")[0]
        if first_line and first_line.startswith(u"<?xml"):
            encoding_pos = first_line.find(u"encoding")
            if encoding_pos != -1:
                # look for double quote
                quote_pos = first_line.find('"', encoding_pos)

                if quote_pos == -1:                 # look for single quote
                    quote_pos = first_line.find("'", encoding_pos)

                if quote_pos > -1:
                    quote_char, rest = (first_line[quote_pos],
                                        first_line[quote_pos + 1:])
                    encoding = rest[:rest.find(quote_char)]

    return encoding


def decoder(buffer):
    encoding = autoDetectXMLEncoding(buffer)
    return buffer.decode(encoding).encode('utf8')

########NEW FILE########
__FILENAME__ = globals
import threading
current = threading.local()

########NEW FILE########
__FILENAME__ = highlight
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import re
import cgi

__all__ = ['highlight']


class Highlighter(object):

    """
    Do syntax highlighting.
    """

    def __init__(
        self,
        mode,
        link=None,
        styles=None,
    ):
        """
        Initialise highlighter:
            mode = language (PYTHON, WEB2PY,C, CPP, HTML, HTML_PLAIN)
        """
        styles = styles or {}
        mode = mode.upper()
        if link and link[-1] != '/':
            link = link + '/'
        self.link = link
        self.styles = styles
        self.output = []
        self.span_style = None
        if mode == 'WEB2PY':
            (mode, self.suppress_tokens) = ('PYTHON', [])
        elif mode == 'PYTHON':
            self.suppress_tokens = ['GOTOHTML']
        elif mode == 'CPP':
            (mode, self.suppress_tokens) = ('C', [])
        elif mode == 'C':
            self.suppress_tokens = ['CPPKEYWORD']
        elif mode == 'HTML_PLAIN':
            (mode, self.suppress_tokens) = ('HTML', ['GOTOPYTHON'])
        elif mode == 'HTML':
            self.suppress_tokens = []
        else:
            raise SyntaxError('Unknown mode: %s' % mode)
        self.mode = mode

    def c_tokenizer(
        self,
        token,
        match,
        style,
    ):
        """
        Callback for C specific highlighting.
        """

        value = cgi.escape(match.group())
        self.change_style(token, style)
        self.output.append(value)

    def python_tokenizer(
        self,
        token,
        match,
        style,
    ):
        """
        Callback for python specific highlighting.
        """

        value = cgi.escape(match.group())
        if token == 'MULTILINESTRING':
            self.change_style(token, style)
            self.output.append(value)
            self.strMultilineString = match.group(1)
            return 'PYTHONMultilineString'
        elif token == 'ENDMULTILINESTRING':
            if match.group(1) == self.strMultilineString:
                self.output.append(value)
                self.strMultilineString = ''
                return 'PYTHON'
        if style and style[:5] == 'link:':
            self.change_style(None, None)
            (url, style) = style[5:].split(';', 1)
            if url == 'None' or url == '':
                self.output.append('<span style="%s">%s</span>'
                                   % (style, value))
            else:
                self.output.append('<a href="%s%s" style="%s">%s</a>'
                                   % (url, value, style, value))
        else:
            self.change_style(token, style)
            self.output.append(value)
        if token == 'GOTOHTML':
            return 'HTML'
        return None

    def html_tokenizer(
        self,
        token,
        match,
        style,
    ):
        """
        Callback for HTML specific highlighting.
        """

        value = cgi.escape(match.group())
        self.change_style(token, style)
        self.output.append(value)
        if token == 'GOTOPYTHON':
            return 'PYTHON'
        return None

    all_styles = {
        'C': (c_tokenizer, (
            ('COMMENT', re.compile(r'//.*\r?\n'),
             'color: green; font-style: italic'),
            ('MULTILINECOMMENT', re.compile(r'/\*.*?\*/', re.DOTALL),
             'color: green; font-style: italic'),
            ('PREPROCESSOR', re.compile(r'\s*#.*?[^\\]\s*\n',
             re.DOTALL), 'color: magenta; font-style: italic'),
            ('PUNC', re.compile(r'[-+*!&|^~/%\=<>\[\]{}(),.:]'),
             'font-weight: bold'),
            ('NUMBER',
             re.compile(r'0x[0-9a-fA-F]+|[+-]?\d+(\.\d+)?([eE][+-]\d+)?|\d+'),
             'color: red'),
            ('KEYWORD', re.compile(r'(sizeof|int|long|short|char|void|'
                                   + r'signed|unsigned|float|double|'
                                   + r'goto|break|return|continue|asm|'
                                   + r'case|default|if|else|switch|while|for|do|'
                                   + r'struct|union|enum|typedef|'
                                   + r'static|register|auto|volatile|extern|const)(?![a-zA-Z0-9_])'),
             'color:#185369; font-weight: bold'),
            ('CPPKEYWORD',
             re.compile(r'(class|private|protected|public|template|new|delete|'
                        + r'this|friend|using|inline|export|bool|throw|try|catch|'
                        + r'operator|typeid|virtual)(?![a-zA-Z0-9_])'),
             'color: blue; font-weight: bold'),
            ('STRING', re.compile(r'r?u?\'(.*?)(?<!\\)\'|"(.*?)(?<!\\)"'),
             'color: #FF9966'),
            ('IDENTIFIER', re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*'),
             None),
            ('WHITESPACE', re.compile(r'[   \r\n]+'), 'Keep'),
        )),
        'PYTHON': (python_tokenizer, (
            ('GOTOHTML', re.compile(r'\}\}'), 'color: red'),
            ('PUNC', re.compile(r'[-+*!|&^~/%\=<>\[\]{}(),.:]'),
             'font-weight: bold'),
            ('NUMBER',
             re.compile(r'0x[0-9a-fA-F]+|[+-]?\d+(\.\d+)?([eE][+-]\d+)?|\d+'
                        ), 'color: red'),
            ('KEYWORD',
             re.compile(r'(def|class|break|continue|del|exec|finally|pass|'
                        + r'print|raise|return|try|except|global|assert|lambda|'
                        + r'yield|for|while|if|elif|else|and|in|is|not|or|import|'
                        + r'from|True|False)(?![a-zA-Z0-9_])'),
             'color:#185369; font-weight: bold'),
            ('WEB2PY',
             re.compile(r'(request|response|session|cache|redirect|local_import|HTTP|TR|XML|URL|BEAUTIFY|A|BODY|BR|B|CAT|CENTER|CODE|COL|COLGROUP|DIV|EM|EMBED|FIELDSET|LEGEND|FORM|H1|H2|H3|H4|H5|H6|IFRAME|HEAD|HR|HTML|I|IMG|INPUT|LABEL|LI|LINK|MARKMIN|MENU|META|OBJECT|OL|ON|OPTION|P|PRE|SCRIPT|SELECT|SPAN|STYLE|TABLE|THEAD|TBODY|TFOOT|TAG|TD|TEXTAREA|TH|TITLE|TT|T|UL|XHTML|IS_SLUG|IS_STRONG|IS_LOWER|IS_UPPER|IS_ALPHANUMERIC|IS_DATETIME|IS_DATETIME_IN_RANGE|IS_DATE|IS_DATE_IN_RANGE|IS_DECIMAL_IN_RANGE|IS_EMAIL|IS_EXPR|IS_FLOAT_IN_RANGE|IS_IMAGE|IS_INT_IN_RANGE|IS_IN_SET|IS_IPV4|IS_LIST_OF|IS_LENGTH|IS_MATCH|IS_EQUAL_TO|IS_EMPTY_OR|IS_NULL_OR|IS_NOT_EMPTY|IS_TIME|IS_UPLOAD_FILENAME|IS_URL|CLEANUP|CRYPT|IS_IN_DB|IS_NOT_IN_DB|DAL|Field|SQLFORM|SQLTABLE|xmlescape|embed64)(?![a-zA-Z0-9_])'
                        ), 'link:%(link)s;text-decoration:None;color:#FF5C1F;'),
            ('MAGIC', re.compile(r'self|None'),
             'color:#185369; font-weight: bold'),
            ('MULTILINESTRING', re.compile(r'r?u?(\'\'\'|""")'),
             'color: #FF9966'),
            ('STRING', re.compile(r'r?u?\'(.*?)(?<!\\)\'|"(.*?)(?<!\\)"'
                                  ), 'color: #FF9966'),
            ('IDENTIFIER', re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*'),
             None),
            ('COMMENT', re.compile(r'\#.*\r?\n'),
             'color: green; font-style: italic'),
            ('WHITESPACE', re.compile(r'[   \r\n]+'), 'Keep'),
        )),
        'PYTHONMultilineString': (python_tokenizer,
                                  (('ENDMULTILINESTRING',
                                  re.compile(r'.*?("""|\'\'\')',
                                  re.DOTALL), 'color: darkred'), )),
        'HTML': (html_tokenizer, (
            ('GOTOPYTHON', re.compile(r'\{\{'), 'color: red'),
            ('COMMENT', re.compile(r'<!--[^>]*-->|<!>'),
             'color: green; font-style: italic'),
            ('XMLCRAP', re.compile(r'<![^>]*>'),
             'color: blue; font-style: italic'),
            ('SCRIPT', re.compile(r'<script .*?</script>', re.IGNORECASE
                                  + re.DOTALL), 'color: black'),
            ('TAG', re.compile(r'</?\s*[a-zA-Z0-9]+'),
             'color: darkred; font-weight: bold'),
            ('ENDTAG', re.compile(r'/?>'),
             'color: darkred; font-weight: bold'),
        )),
    }

    def highlight(self, data):
        """
        Syntax highlight some python code.
        Returns html version of code.
        """

        i = 0
        mode = self.mode
        while i < len(data):
            for (token, o_re, style) in Highlighter.all_styles[mode][1]:
                if not token in self.suppress_tokens:
                    match = o_re.match(data, i)
                    if match:
                        if style:
                            new_mode = \
                                Highlighter.all_styles[mode][0](self,
                                                                token, match, style
                                                                % dict(link=self.link))
                        else:
                            new_mode = \
                                Highlighter.all_styles[mode][0](self,
                                                                token, match, style)
                        if not new_mode is None:
                            mode = new_mode
                        i += max(1, len(match.group()))
                        break
            else:
                self.change_style(None, None)
                self.output.append(data[i])
                i += 1
        self.change_style(None, None)
        return ''.join(self.output).expandtabs(4)

    def change_style(self, token, style):
        """
        Generate output to change from existing style to another style only.
        """

        if token in self.styles:
            style = self.styles[token]
        if self.span_style != style:
            if style != 'Keep':
                if not self.span_style is None:
                    self.output.append('</span>')
                if not style is None:
                    self.output.append('<span style="%s">' % style)
                self.span_style = style


def highlight(
    code,
    language,
    link='/examples/globals/vars/',
    counter=1,
    styles=None,
    highlight_line=None,
    context_lines=None,
    attributes=None,
):
    styles = styles or {}
    attributes = attributes or {}
    if not 'CODE' in styles:
        code_style = """
        font-size: 11px;
        font-family: Bitstream Vera Sans Mono,monospace;
        background-color: transparent;
        margin: 0;
        padding: 5px;
        border: none;
        overflow: auto;
        white-space: pre !important;\n"""
    else:
        code_style = styles['CODE']
    if not 'LINENUMBERS' in styles:
        linenumbers_style = """
        font-size: 11px;
        font-family: Bitstream Vera Sans Mono,monospace;
        background-color: transparent;
        margin: 0;
        padding: 5px;
        border: none;
        color: #A0A0A0;\n"""
    else:
        linenumbers_style = styles['LINENUMBERS']
    if not 'LINEHIGHLIGHT' in styles:
        linehighlight_style = "background-color: #EBDDE2;"
    else:
        linehighlight_style = styles['LINEHIGHLIGHT']

    if language and language.upper() in ['PYTHON', 'C', 'CPP', 'HTML',
                                         'WEB2PY']:
        code = Highlighter(language, link, styles).highlight(code)
    else:
        code = cgi.escape(code)
    lines = code.split('\n')

    if counter is None:
        linenumbers = [''] * len(lines)
    elif isinstance(counter, str):
        linenumbers = [cgi.escape(counter)] * len(lines)
    else:
        linenumbers = [str(i + counter) + '.' for i in
                       xrange(len(lines))]

    if highlight_line:
        if counter and not isinstance(counter, str):
            lineno = highlight_line - counter
        else:
            lineno = highlight_line
        if lineno < len(lines):
            lines[lineno] = '<div style="%s">%s</div>' % (
                linehighlight_style, lines[lineno])
            linenumbers[lineno] = '<div style="%s">%s</div>' % (
                linehighlight_style, linenumbers[lineno])

        if context_lines:
            if lineno + context_lines < len(lines):
                del lines[lineno + context_lines:]
                del linenumbers[lineno + context_lines:]
            if lineno - context_lines > 0:
                del lines[0:lineno - context_lines]
                del linenumbers[0:lineno - context_lines]

    code = '<br/>'.join(lines)
    numbers = '<br/>'.join(linenumbers)

    items = attributes.items()
    fa = ' '.join([key[1:].lower() for (key, value) in items if key[:1]
                   == '_' and value is None] + ['%s="%s"'
                                                % (key[1:].lower(), str(value).replace('"', "'"))
                  for (key, value) in attributes.items() if key[:1]
                  == '_' and value])
    if fa:
        fa = ' ' + fa
    return '<table%s><tr valign="top"><td style="width:40px; text-align: right;"><pre style="%s">%s</pre></td><td><pre style="%s">%s</pre></td></tr></table>'\
        % (fa, linenumbers_style, numbers, code_style, code)


if __name__ == '__main__':
    import sys
    argfp = open(sys.argv[1])
    data = argfp.read()
    argfp.close()
    print '<html><body>' + highlight(data, sys.argv[2])\
        + '</body></html>'

########NEW FILE########
__FILENAME__ = html
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import cgi
import os
import re
import copy
import types
import urllib
import base64
import sanitizer
import itertools
import decoder
import copy_reg
import cPickle
import marshal

from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint

from storage import Storage
from utils import web2py_uuid, simple_hash, compare
from highlight import highlight

regex_crlf = re.compile('\r|\n')

join = ''.join

# name2codepoint is incomplete respect to xhtml (and xml): 'apos' is missing.
entitydefs = dict(map(lambda (
    k, v): (k, unichr(v).encode('utf-8')), name2codepoint.iteritems()))
entitydefs.setdefault('apos', u"'".encode('utf-8'))


__all__ = [
    'A',
    'B',
    'BEAUTIFY',
    'BODY',
    'BR',
    'BUTTON',
    'CENTER',
    'CAT',
    'CODE',
    'COL',
    'COLGROUP',
    'DIV',
    'EM',
    'EMBED',
    'FIELDSET',
    'FORM',
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
    'HEAD',
    'HR',
    'HTML',
    'I',
    'IFRAME',
    'IMG',
    'INPUT',
    'LABEL',
    'LEGEND',
    'LI',
    'LINK',
    'OL',
    'UL',
    'MARKMIN',
    'MENU',
    'META',
    'OBJECT',
    'ON',
    'OPTION',
    'P',
    'PRE',
    'SCRIPT',
    'OPTGROUP',
    'SELECT',
    'SPAN',
    'STRONG',
    'STYLE',
    'TABLE',
    'TAG',
    'TD',
    'TEXTAREA',
    'TH',
    'THEAD',
    'TBODY',
    'TFOOT',
    'TITLE',
    'TR',
    'TT',
    'URL',
    'XHTML',
    'XML',
    'xmlescape',
    'embed64',
]


def xmlescape(data, quote=True):
    """
    returns an escaped string of the provided data

    :param data: the data to be escaped
    :param quote: optional (default False)
    """

    # first try the xml function
    if hasattr(data, 'xml') and callable(data.xml):
        return data.xml()

    # otherwise, make it a string
    if not isinstance(data, (str, unicode)):
        data = str(data)
    elif isinstance(data, unicode):
        data = data.encode('utf8', 'xmlcharrefreplace')

    # ... and do the escaping
    data = cgi.escape(data, quote).replace("'", "&#x27;")
    return data

def call_as_list(f,*a,**b):
    if not isinstance(f, (list,tuple)):
        f = [f]
    for item in f:
        item(*a,**b)

def truncate_string(text, length, dots='...'):
    text = text.decode('utf-8')
    if len(text) > length:
        text = text[:length - len(dots)].encode('utf-8') + dots
    return text


def URL(
    a=None,
    c=None,
    f=None,
    r=None,
    args=None,
    vars=None,
    anchor='',
    extension=None,
    env=None,
    hmac_key=None,
    hash_vars=True,
    salt=None,
    user_signature=None,
    scheme=None,
    host=None,
    port=None,
    encode_embedded_slash=False,
    url_encode=True
):
    """
    generate a URL

    example::

        >>> str(URL(a='a', c='c', f='f', args=['x', 'y', 'z'],
        ...     vars={'p':1, 'q':2}, anchor='1'))
        '/a/c/f/x/y/z?p=1&q=2#1'

        >>> str(URL(a='a', c='c', f='f', args=['x', 'y', 'z'],
        ...     vars={'p':(1,3), 'q':2}, anchor='1'))
        '/a/c/f/x/y/z?p=1&p=3&q=2#1'

        >>> str(URL(a='a', c='c', f='f', args=['x', 'y', 'z'],
        ...     vars={'p':(3,1), 'q':2}, anchor='1'))
        '/a/c/f/x/y/z?p=3&p=1&q=2#1'

        >>> str(URL(a='a', c='c', f='f', anchor='1+2'))
        '/a/c/f#1%2B2'

        >>> str(URL(a='a', c='c', f='f', args=['x', 'y', 'z'],
        ...     vars={'p':(1,3), 'q':2}, anchor='1', hmac_key='key'))
        '/a/c/f/x/y/z?p=1&p=3&q=2&_signature=a32530f0d0caa80964bb92aad2bedf8a4486a31f#1'

        >>> str(URL(a='a', c='c', f='f', args=['w/x', 'y/z']))
        '/a/c/f/w/x/y/z'

        >>> str(URL(a='a', c='c', f='f', args=['w/x', 'y/z'], encode_embedded_slash=True))
        '/a/c/f/w%2Fx/y%2Fz'

        >>> str(URL(a='a', c='c', f='f', args=['%(id)d'], url_encode=False))
        '/a/c/f/%(id)d'

        >>> str(URL(a='a', c='c', f='f', args=['%(id)d'], url_encode=True))
        '/a/c/f/%25%28id%29d'

        >>> str(URL(a='a', c='c', f='f', vars={'id' : '%(id)d' }, url_encode=False))
        '/a/c/f?id=%(id)d'

        >>> str(URL(a='a', c='c', f='f', vars={'id' : '%(id)d' }, url_encode=True))
        '/a/c/f?id=%25%28id%29d'

        >>> str(URL(a='a', c='c', f='f', anchor='%(id)d', url_encode=False))
        '/a/c/f#%(id)d'

        >>> str(URL(a='a', c='c', f='f', anchor='%(id)d', url_encode=True))
        '/a/c/f#%25%28id%29d'

    generates a url '/a/c/f' corresponding to application a, controller c
    and function f. If r=request is passed, a, c, f are set, respectively,
    to r.application, r.controller, r.function.

    The more typical usage is:

    URL(r=request, f='index') that generates a url for the index function
    within the present application and controller.

    :param a: application (default to current if r is given)
    :param c: controller (default to current if r is given)
    :param f: function (default to current if r is given)
    :param r: request (optional)
    :param args: any arguments (optional)
    :param vars: any variables (optional)
    :param anchor: anchorname, without # (optional)
    :param hmac_key: key to use when generating hmac signature (optional)
    :param hash_vars: which of the vars to include in our hmac signature
        True (default) - hash all vars, False - hash none of the vars,
        iterable - hash only the included vars ['key1','key2']
    :param scheme: URI scheme (True, 'http' or 'https', etc); forces absolute URL (optional)
    :param host: string to force absolute URL with host (True means http_host)
    :param port: optional port number (forces absolute URL)

    :raises SyntaxError: when no application, controller or function is
        available
    :raises SyntaxError: when a CRLF is found in the generated url
    """

    from rewrite import url_out  # done here in case used not-in web2py

    if args in (None, []):
        args = []
    vars = vars or {}
    application = None
    controller = None
    function = None

    if not isinstance(args, (list, tuple)):
        args = [args]

    if not r:
        if a and not c and not f:
            (f, a, c) = (a, c, f)
        elif a and c and not f:
            (c, f, a) = (a, c, f)
        from globals import current
        if hasattr(current, 'request'):
            r = current.request

    if r:
        application = r.application
        controller = r.controller
        function = r.function
        env = r.env
        if extension is None and r.extension != 'html':
            extension = r.extension
    if a:
        application = a
    if c:
        controller = c
    if f:
        if not isinstance(f, str):
            if hasattr(f, '__name__'):
                function = f.__name__
            else:
                raise SyntaxError(
                    'when calling URL, function or function name required')
        elif '/' in f:
            if f.startswith("/"):
                f = f[1:]
            items = f.split('/')
            function = f = items[0]
            args = items[1:] + args
        else:
            function = f

        # if the url gets a static resource, don't force extention
        if controller == 'static':
            extension = None

        if '.' in function:
            function, extension = function.rsplit('.', 1)

    function2 = '%s.%s' % (function, extension or 'html')

    if not (application and controller and function):
        raise SyntaxError('not enough information to build the url (%s %s %s)' % (application, controller, function))

    if args:
        if url_encode:
            if encode_embedded_slash:
                other = '/' + '/'.join([urllib.quote(str(
                    x), '') for x in args])
            else:
                other = args and urllib.quote(
                    '/' + '/'.join([str(x) for x in args]))
        else:
            other = args and ('/' + '/'.join([str(x) for x in args]))
    else:
        other = ''

    if other.endswith('/'):
        other += '/'    # add trailing slash to make last trailing empty arg explicit

    list_vars = []
    for (key, vals) in sorted(vars.items()):
        if key == '_signature':
            continue
        if not isinstance(vals, (list, tuple)):
            vals = [vals]
        for val in vals:
            list_vars.append((key, val))

    if user_signature:
        from globals import current
        if current.session.auth:
            hmac_key = current.session.auth.hmac_key

    if hmac_key:
        # generate an hmac signature of the vars & args so can later
        # verify the user hasn't messed with anything

        h_args = '/%s/%s/%s%s' % (application, controller, function2, other)

        # how many of the vars should we include in our hash?
        if hash_vars is True:       # include them all
            h_vars = list_vars
        elif hash_vars is False:    # include none of them
            h_vars = ''
        else:                       # include just those specified
            if hash_vars and not isinstance(hash_vars, (list, tuple)):
                hash_vars = [hash_vars]
            h_vars = [(k, v) for (k, v) in list_vars if k in hash_vars]

        # re-assembling the same way during hash authentication
        message = h_args + '?' + urllib.urlencode(sorted(h_vars))
        sig = simple_hash(
            message, hmac_key or '', salt or '', digest_alg='sha1')
        # add the signature into vars
        list_vars.append(('_signature', sig))

    if list_vars:
        if url_encode:
            other += '?%s' % urllib.urlencode(list_vars)
        else:
            other += '?%s' % '&'.join(['%s=%s' % var[:2] for var in list_vars])
    if anchor:
        if url_encode:
            other += '#' + urllib.quote(str(anchor))
        else:
            other += '#' + (str(anchor))
    if extension:
        function += '.' + extension

    if regex_crlf.search(join([application, controller, function, other])):
        raise SyntaxError('CRLF Injection Detected')

    url = url_out(r, env, application, controller, function,
                  args, other, scheme, host, port)
    return url


def verifyURL(request, hmac_key=None, hash_vars=True, salt=None, user_signature=None):
    """
    Verifies that a request's args & vars have not been tampered with by the user

    :param request: web2py's request object
    :param hmac_key: the key to authenticate with, must be the same one previously
                    used when calling URL()
    :param hash_vars: which vars to include in our hashing. (Optional)
                    Only uses the 1st value currently
                    True (or undefined) means all, False none,
                    an iterable just the specified keys

    do not call directly. Use instead:

    URL.verify(hmac_key='...')

    the key has to match the one used to generate the URL.

        >>> r = Storage()
        >>> gv = Storage(p=(1,3),q=2,_signature='a32530f0d0caa80964bb92aad2bedf8a4486a31f')
        >>> r.update(dict(application='a', controller='c', function='f', extension='html'))
        >>> r['args'] = ['x', 'y', 'z']
        >>> r['get_vars'] = gv
        >>> verifyURL(r, 'key')
        True
        >>> verifyURL(r, 'kay')
        False
        >>> r.get_vars.p = (3, 1)
        >>> verifyURL(r, 'key')
        True
        >>> r.get_vars.p = (3, 2)
        >>> verifyURL(r, 'key')
        False

    """

    if not '_signature' in request.get_vars:
        return False  # no signature in the request URL

    # check if user_signature requires
    if user_signature:
        from globals import current
        if not current.session or not current.session.auth:
            return False
        hmac_key = current.session.auth.hmac_key
    if not hmac_key:
        return False

    # get our sig from request.get_vars for later comparison
    original_sig = request.get_vars._signature

    # now generate a new hmac for the remaining args & vars
    vars, args = request.get_vars, request.args

    # remove the signature var since it was not part of our signed message
    request.get_vars.pop('_signature')

    # join all the args & vars into one long string

    # always include all of the args
    other = args and urllib.quote('/' + '/'.join([str(x) for x in args])) or ''
    h_args = '/%s/%s/%s.%s%s' % (request.application,
                                 request.controller,
                                 request.function,
                                 request.extension,
                                 other)

    # but only include those vars specified (allows more flexibility for use with
    # forms or ajax)

    list_vars = []
    for (key, vals) in sorted(vars.items()):
        if not isinstance(vals, (list, tuple)):
            vals = [vals]
        for val in vals:
            list_vars.append((key, val))

    # which of the vars are to be included?
    if hash_vars is True:       # include them all
        h_vars = list_vars
    elif hash_vars is False:    # include none of them
        h_vars = ''
    else:                       # include just those specified
        # wrap in a try - if the desired vars have been removed it'll fail
        try:
            if hash_vars and not isinstance(hash_vars, (list, tuple)):
                hash_vars = [hash_vars]
            h_vars = [(k, v) for (k, v) in list_vars if k in hash_vars]
        except:
            # user has removed one of our vars! Immediate fail
            return False
    # build the full message string with both args & vars
    message = h_args + '?' + urllib.urlencode(sorted(h_vars))

    # hash with the hmac_key provided
    sig = simple_hash(message, str(hmac_key), salt or '', digest_alg='sha1')

    # put _signature back in get_vars just in case a second call to URL.verify is performed
    # (otherwise it'll immediately return false)
    request.get_vars['_signature'] = original_sig

    # return whether or not the signature in the request matched the one we just generated
    # (I.E. was the message the same as the one we originally signed)

    return compare(original_sig, sig)

URL.verify = verifyURL

ON = True


class XmlComponent(object):
    """
    Abstract root for all Html components
    """

    # TODO: move some DIV methods to here

    def xml(self):
        raise NotImplementedError

    def __mul__(self, n):
        return CAT(*[self for i in range(n)])

    def __add__(self, other):
        if isinstance(self, CAT):
            components = self.components
        else:
            components = [self]
        if isinstance(other, CAT):
            components += other.components
        else:
            components += [other]
        return CAT(*components)

    def add_class(self, name):
        """ add a class to _class attribute """
        c = self['_class']
        classes = (set(c.split()) if c else set()) | set(name.split())
        self['_class'] = ' '.join(classes) if classes else None
        return self

    def remove_class(self, name):
        """ remove a class from _class attribute """
        c = self['_class']
        classes = (set(c.split()) if c else set()) - set(name.split())
        self['_class'] = ' '.join(classes) if classes else None
        return self

class XML(XmlComponent):
    """
    use it to wrap a string that contains XML/HTML so that it will not be
    escaped by the template

    example:

    >>> XML('<h1>Hello</h1>').xml()
    '<h1>Hello</h1>'
    """

    def __init__(
        self,
        text,
        sanitize=False,
        permitted_tags=[
            'a',
            'b',
            'blockquote',
            'br/',
            'i',
            'li',
            'ol',
            'ul',
            'p',
            'cite',
            'code',
            'pre',
            'img/',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'table', 'tr', 'td', 'div',
            'strong','span',
        ],
        allowed_attributes={
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt'],
            'blockquote': ['type'],
            'td': ['colspan'],
        },
    ):
        """
        :param text: the XML text
        :param sanitize: sanitize text using the permitted tags and allowed
            attributes (default False)
        :param permitted_tags: list of permitted tags (default: simple list of
            tags)
        :param allowed_attributes: dictionary of allowed attributed (default
            for A, IMG and BlockQuote).
            The key is the tag; the value is a list of allowed attributes.
        """

        if sanitize:
            text = sanitizer.sanitize(text, permitted_tags,
                                      allowed_attributes)
        if isinstance(text, unicode):
            text = text.encode('utf8', 'xmlcharrefreplace')
        elif not isinstance(text, str):
            text = str(text)
        self.text = text

    def xml(self):
        return self.text

    def __str__(self):
        return self.text

    def __add__(self, other):
        return '%s%s' % (self, other)

    def __radd__(self, other):
        return '%s%s' % (other, self)

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))

#    why was this here? Break unpickling in sessions
#    def __getattr__(self, name):
#        return getattr(str(self), name)

    def __getitem__(self, i):
        return str(self)[i]

    def __getslice__(self, i, j):
        return str(self)[i:j]

    def __iter__(self):
        for c in str(self):
            yield c

    def __len__(self):
        return len(str(self))

    def flatten(self, render=None):
        """
        return the text stored by the XML object rendered by the render function
        """
        if render:
            return render(self.text, None, {})
        return self.text

    def elements(self, *args, **kargs):
        """
        to be considered experimental since the behavior of this method is questionable
        another options could be TAG(self.text).elements(*args,**kargs)
        """
        return []

### important to allow safe session.flash=T(....)


def XML_unpickle(data):
    return marshal.loads(data)


def XML_pickle(data):
    return XML_unpickle, (marshal.dumps(str(data)),)
copy_reg.pickle(XML, XML_pickle, XML_unpickle)


class DIV(XmlComponent):
    """
    HTML helper, for easy generating and manipulating a DOM structure.
    Little or no validation is done.

    Behaves like a dictionary regarding updating of attributes.
    Behaves like a list regarding inserting/appending components.

    example::

        >>> DIV('hello', 'world', _style='color:red;').xml()
        '<div style=\"color:red;\">helloworld</div>'

    all other HTML helpers are derived from DIV.

    _something=\"value\" attributes are transparently translated into
    something=\"value\" HTML attributes
    """

    # name of the tag, subclasses should update this
    # tags ending with a '/' denote classes that cannot
    # contain components
    tag = 'div'

    def __init__(self, *components, **attributes):
        """
        :param *components: any components that should be nested in this element
        :param **attributes: any attributes you want to give to this element

        :raises SyntaxError: when a stand alone tag receives components
        """

        if self.tag[-1:] == '/' and components:
            raise SyntaxError('<%s> tags cannot have components'
                              % self.tag)
        if len(components) == 1 and isinstance(components[0], (list, tuple)):
            self.components = list(components[0])
        else:
            self.components = list(components)
        self.attributes = attributes
        self._fixup()
        # converts special attributes in components attributes
        self.parent = None
        for c in self.components:
            self._setnode(c)
        self._postprocessing()

    def update(self, **kargs):
        """
        dictionary like updating of the tag attributes
        """

        for (key, value) in kargs.iteritems():
            self[key] = value
        return self

    def append(self, value):
        """
        list style appending of components

        >>> a=DIV()
        >>> a.append(SPAN('x'))
        >>> print a
        <div><span>x</span></div>
        """
        self._setnode(value)
        ret = self.components.append(value)
        self._fixup()
        return ret

    def insert(self, i, value):
        """
        list style inserting of components

        >>> a=DIV()
        >>> a.insert(0,SPAN('x'))
        >>> print a
        <div><span>x</span></div>
        """
        self._setnode(value)
        ret = self.components.insert(i, value)
        self._fixup()
        return ret

    def __getitem__(self, i):
        """
        gets attribute with name 'i' or component #i.
        If attribute 'i' is not found returns None

        :param i: index
           if i is a string: the name of the attribute
           otherwise references to number of the component
        """

        if isinstance(i, str):
            try:
                return self.attributes[i]
            except KeyError:
                return None
        else:
            return self.components[i]

    def __setitem__(self, i, value):
        """
        sets attribute with name 'i' or component #i.

        :param i: index
           if i is a string: the name of the attribute
           otherwise references to number of the component
        :param value: the new value
        """
        self._setnode(value)
        if isinstance(i, (str, unicode)):
            self.attributes[i] = value
        else:
            self.components[i] = value

    def __delitem__(self, i):
        """
        deletes attribute with name 'i' or component #i.

        :param i: index
           if i is a string: the name of the attribute
           otherwise references to number of the component
        """

        if isinstance(i, str):
            del self.attributes[i]
        else:
            del self.components[i]

    def __len__(self):
        """
        returns the number of included components
        """
        return len(self.components)

    def __nonzero__(self):
        """
        always return True
        """
        return True

    def _fixup(self):
        """
        Handling of provided components.

        Nothing to fixup yet. May be overridden by subclasses,
        eg for wrapping some components in another component or blocking them.
        """
        return

    def _wrap_components(self, allowed_parents,
                         wrap_parent=None,
                         wrap_lambda=None):
        """
        helper for _fixup. Checks if a component is in allowed_parents,
        otherwise wraps it in wrap_parent

        :param allowed_parents: (tuple) classes that the component should be an
            instance of
        :param wrap_parent: the class to wrap the component in, if needed
        :param wrap_lambda: lambda to use for wrapping, if needed

        """
        components = []
        for c in self.components:
            if isinstance(c, allowed_parents):
                pass
            elif wrap_lambda:
                c = wrap_lambda(c)
            else:
                c = wrap_parent(c)
            if isinstance(c, DIV):
                c.parent = self
            components.append(c)
        self.components = components

    def _postprocessing(self):
        """
        Handling of attributes (normally the ones not prefixed with '_').

        Nothing to postprocess yet. May be overridden by subclasses
        """
        return

    def _traverse(self, status, hideerror=False):
        # TODO: docstring
        newstatus = status
        for c in self.components:
            if hasattr(c, '_traverse') and callable(c._traverse):
                c.vars = self.vars
                c.request_vars = self.request_vars
                c.errors = self.errors
                c.latest = self.latest
                c.session = self.session
                c.formname = self.formname
                c['hideerror'] = hideerror or \
                        self.attributes.get('hideerror', False)
                newstatus = c._traverse(status, hideerror) and newstatus

        # for input, textarea, select, option
        # deal with 'value' and 'validation'

        name = self['_name']
        if newstatus:
            newstatus = self._validate()
            self._postprocessing()
        elif 'old_value' in self.attributes:
            self['value'] = self['old_value']
            self._postprocessing()
        elif name and name in self.vars:
            self['value'] = self.vars[name]
            self._postprocessing()
        if name:
            self.latest[name] = self['value']
        return newstatus

    def _validate(self):
        """
        nothing to validate yet. May be overridden by subclasses
        """
        return True

    def _setnode(self, value):
        if isinstance(value, DIV):
            value.parent = self

    def _xml(self):
        """
        helper for xml generation. Returns separately:
        - the component attributes
        - the generated xml of the inner components

        Component attributes start with an underscore ('_') and
        do not have a False or None value. The underscore is removed.
        A value of True is replaced with the attribute name.

        :returns: tuple: (attributes, components)
        """

        # get the attributes for this component
        # (they start with '_', others may have special meanings)
        attr = []
        for key, value in self.attributes.iteritems():
            if key[:1] != '_':
                continue
            name = key[1:]
            if value is True:
                value = name
            elif value is False or value is None:
                continue
            attr.append((name, value))
        data = self.attributes.get('data',{})
        for key, value in data.iteritems():
            name = 'data-' + key
            value = data[key]
            attr.append((name,value))
        attr.sort()
        fa = ''
        for name,value in attr:
            fa += ' %s="%s"' % (name, xmlescape(value, True))
        # get the xml for the inner components
        co = join([xmlescape(component) for component in
                   self.components])

        return (fa, co)

    def xml(self):
        """
        generates the xml for this component.
        """

        (fa, co) = self._xml()

        if not self.tag:
            return co

        if self.tag[-1:] == '/':
            # <tag [attributes] />
            return '<%s%s />' % (self.tag[:-1], fa)

        # else: <tag [attributes]>  inner components xml </tag>
        return '<%s%s>%s</%s>' % (self.tag, fa, co, self.tag)

    def __str__(self):
        """
        str(COMPONENT) returns equals COMPONENT.xml()
        """

        return self.xml()

    def flatten(self, render=None):
        """
        return the text stored by the DIV object rendered by the render function
        the render function must take text, tagname, and attributes
        render=None is equivalent to render=lambda text, tag, attr: text

        >>> markdown = lambda text,tag=None,attributes={}: \
                        {None: re.sub('\s+',' ',text), \
                         'h1':'#'+text+'\\n\\n', \
                         'p':text+'\\n'}.get(tag,text)
        >>> a=TAG('<h1>Header</h1><p>this is a     test</p>')
        >>> a.flatten(markdown)
        '#Header\\n\\nthis is a test\\n'
        """

        text = ''
        for c in self.components:
            if isinstance(c, XmlComponent):
                s = c.flatten(render)
            elif render:
                s = render(str(c))
            else:
                s = str(c)
            text += s
        if render:
            text = render(text, self.tag, self.attributes)
        return text

    regex_tag = re.compile('^[\w\-\:]+')
    regex_id = re.compile('#([\w\-]+)')
    regex_class = re.compile('\.([\w\-]+)')
    regex_attr = re.compile('\[([\w\-\:]+)=(.*?)\]')

    def elements(self, *args, **kargs):
        """
        find all component that match the supplied attribute dictionary,
        or None if nothing could be found

        All components of the components are searched.

        >>> a = DIV(DIV(SPAN('x'),3,DIV(SPAN('y'))))
        >>> for c in a.elements('span',first_only=True): c[0]='z'
        >>> print a
        <div><div><span>z</span>3<div><span>y</span></div></div></div>
        >>> for c in a.elements('span'): c[0]='z'
        >>> print a
        <div><div><span>z</span>3<div><span>z</span></div></div></div>

        It also supports a syntax compatible with jQuery

        >>> a=TAG('<div><span><a id="1-1" u:v=$>hello</a></span><p class="this is a test">world</p></div>')
        >>> for e in a.elements('div a#1-1, p.is'): print e.flatten()
        hello
        world
        >>> for e in a.elements('#1-1'): print e.flatten()
        hello
        >>> a.elements('a[u:v=$]')[0].xml()
        '<a id="1-1" u:v="$">hello</a>'

        >>> a=FORM( INPUT(_type='text'), SELECT(range(1)), TEXTAREA() )
        >>> for c in a.elements('input, select, textarea'): c['_disabled'] = 'disabled'
        >>> a.xml()
        '<form action="#" enctype="multipart/form-data" method="post"><input disabled="disabled" type="text" /><select disabled="disabled"><option value="0">0</option></select><textarea cols="40" disabled="disabled" rows="10"></textarea></form>'

        Elements that are matched can also be replaced or removed by specifying
        a "replace" argument (note, a list of the original matching elements
        is still returned as usual).

        >>> a = DIV(DIV(SPAN('x', _class='abc'), DIV(SPAN('y', _class='abc'), SPAN('z', _class='abc'))))
        >>> b = a.elements('span.abc', replace=P('x', _class='xyz'))
        >>> print a
        <div><div><p class="xyz">x</p><div><p class="xyz">x</p><p class="xyz">x</p></div></div></div>

        "replace" can be a callable, which will be passed the original element and
        should return a new element to replace it.

        >>> a = DIV(DIV(SPAN('x', _class='abc'), DIV(SPAN('y', _class='abc'), SPAN('z', _class='abc'))))
        >>> b = a.elements('span.abc', replace=lambda el: P(el[0], _class='xyz'))
        >>> print a
        <div><div><p class="xyz">x</p><div><p class="xyz">y</p><p class="xyz">z</p></div></div></div>

        If replace=None, matching elements will be removed completely.

        >>> a = DIV(DIV(SPAN('x', _class='abc'), DIV(SPAN('y', _class='abc'), SPAN('z', _class='abc'))))
        >>> b = a.elements('span', find='y', replace=None)
        >>> print a
        <div><div><span class="abc">x</span><div><span class="abc">z</span></div></div></div>

        If a "find_text" argument is specified, elements will be searched for text
        components that match find_text, and any matching text components will be
        replaced (find_text is ignored if "replace" is not also specified).
        Like the "find" argument, "find_text" can be a string or a compiled regex.

        >>> a = DIV(DIV(SPAN('x', _class='abc'), DIV(SPAN('y', _class='abc'), SPAN('z', _class='abc'))))
        >>> b = a.elements(find_text=re.compile('x|y|z'), replace='hello')
        >>> print a
        <div><div><span class="abc">hello</span><div><span class="abc">hello</span><span class="abc">hello</span></div></div></div>

        If other attributes are specified along with find_text, then only components
        that match the specified attributes will be searched for find_text.

        >>> a = DIV(DIV(SPAN('x', _class='abc'), DIV(SPAN('y', _class='efg'), SPAN('z', _class='abc'))))
        >>> b = a.elements('span.efg', find_text=re.compile('x|y|z'), replace='hello')
        >>> print a
        <div><div><span class="abc">x</span><div><span class="efg">hello</span><span class="abc">z</span></div></div></div>
        """
        if len(args) == 1:
            args = [a.strip() for a in args[0].split(',')]
        if len(args) > 1:
            subset = [self.elements(a, **kargs) for a in args]
            return reduce(lambda a, b: a + b, subset, [])
        elif len(args) == 1:
            items = args[0].split()
            if len(items) > 1:
                subset = [a.elements(' '.join(
                    items[1:]), **kargs) for a in self.elements(items[0])]
                return reduce(lambda a, b: a + b, subset, [])
            else:
                item = items[0]
                if '#' in item or '.' in item or '[' in item:
                    match_tag = self.regex_tag.search(item)
                    match_id = self.regex_id.search(item)
                    match_class = self.regex_class.search(item)
                    match_attr = self.regex_attr.finditer(item)
                    args = []
                    if match_tag:
                        args = [match_tag.group()]
                    if match_id:
                        kargs['_id'] = match_id.group(1)
                    if match_class:
                        kargs['_class'] = re.compile('(?<!\w)%s(?!\w)' %
                                                     match_class.group(1).replace('-', '\\-').replace(':', '\\:'))
                    for item in match_attr:
                        kargs['_' + item.group(1)] = item.group(2)
                    return self.elements(*args, **kargs)
        # make a copy of the components
        matches = []
        # check if the component has an attribute with the same
        # value as provided
        check = True
        tag = getattr(self, 'tag').replace('/', '')
        if args and tag not in args:
            check = False
        for (key, value) in kargs.iteritems():
            if key not in ['first_only', 'replace', 'find_text']:
                if isinstance(value, (str, int)):
                    if self[key] != str(value):
                        check = False
                elif key in self.attributes:
                    if not value.search(str(self[key])):
                        check = False
                else:
                    check = False
        if 'find' in kargs:
            find = kargs['find']
            is_regex = not isinstance(find, (str, int))
            for c in self.components:
                if (isinstance(c, str) and ((is_regex and find.search(c)) or
                   (str(find) in c))):
                    check = True
        # if found, return the component
        if check:
            matches.append(self)

        first_only = kargs.get('first_only', False)
        replace = kargs.get('replace', False)
        find_text = replace is not False and kargs.get('find_text', False)
        is_regex = not isinstance(find_text, (str, int, bool))
        find_components = not (check and first_only)

        def replace_component(i):
            if replace is None:
                del self[i]
            elif callable(replace):
                self[i] = replace(self[i])
            else:
                self[i] = replace
        # loop the components
        if find_text or find_components:
            for i, c in enumerate(self.components):
                if check and find_text and isinstance(c, str) and \
                        ((is_regex and find_text.search(c)) or (str(find_text) in c)):
                    replace_component(i)
                if find_components and isinstance(c, XmlComponent):
                    child_matches = c.elements(*args, **kargs)
                    if len(child_matches):
                        if not find_text and replace is not False and child_matches[0] is c:
                            replace_component(i)
                        if first_only:
                            return child_matches
                        matches.extend(child_matches)
        return matches

    def element(self, *args, **kargs):
        """
        find the first component that matches the supplied attribute dictionary,
        or None if nothing could be found

        Also the components of the components are searched.
        """
        kargs['first_only'] = True
        elements = self.elements(*args, **kargs)
        if not elements:
            # we found nothing
            return None
        return elements[0]

    def siblings(self, *args, **kargs):
        """
        find all sibling components that match the supplied argument list
        and attribute dictionary, or None if nothing could be found
        """
        sibs = [s for s in self.parent.components if not s == self]
        matches = []
        first_only = False
        if 'first_only' in kargs:
            first_only = kargs.pop('first_only')
        for c in sibs:
            try:
                check = True
                tag = getattr(c, 'tag').replace("/", "")
                if args and tag not in args:
                        check = False
                for (key, value) in kargs.iteritems():
                    if c[key] != value:
                            check = False
                if check:
                    matches.append(c)
                    if first_only:
                        break
            except:
                pass
        return matches

    def sibling(self, *args, **kargs):
        """
        find the first sibling component that match the supplied argument list
        and attribute dictionary, or None if nothing could be found
        """
        kargs['first_only'] = True
        sibs = self.siblings(*args, **kargs)
        if not sibs:
            return None
        return sibs[0]


class CAT(DIV):

    tag = ''


def TAG_unpickler(data):
    return cPickle.loads(data)


def TAG_pickler(data):
    d = DIV()
    d.__dict__ = data.__dict__
    marshal_dump = cPickle.dumps(d)
    return (TAG_unpickler, (marshal_dump,))


class __tag__(DIV):
    def __init__(self,name,*a,**b):
        DIV.__init__(self,*a,**b)
        self.tag = name

copy_reg.pickle(__tag__, TAG_pickler, TAG_unpickler)

class __TAG__(XmlComponent):

    """
    TAG factory example::

        >>> print TAG.first(TAG.second('test'), _key = 3)
        <first key=\"3\"><second>test</second></first>

    """

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __getattr__(self, name):
        if name[-1:] == '_':
            name = name[:-1] + '/'
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        return lambda *a,**b: __tag__(name,*a,**b)

    def __call__(self, html):
        return web2pyHTMLParser(decoder.decoder(html)).tree

TAG = __TAG__()


class HTML(DIV):
    """
    There are four predefined document type definitions.
    They can be specified in the 'doctype' parameter:

    -'strict' enables strict doctype
    -'transitional' enables transitional doctype (default)
    -'frameset' enables frameset doctype
    -'html5' enables HTML 5 doctype
    -any other string will be treated as user's own doctype

    'lang' parameter specifies the language of the document.
    Defaults to 'en'.

    See also :class:`DIV`
    """

    tag = 'html'

    strict = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">\n'
    transitional = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n'
    frameset = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">\n'
    html5 = '<!DOCTYPE HTML>\n'

    def xml(self):
        lang = self['lang']
        if not lang:
            lang = 'en'
        self.attributes['_lang'] = lang
        doctype = self['doctype']
        if doctype is None:
            doctype = self.transitional
        elif doctype == 'strict':
            doctype = self.strict
        elif doctype == 'transitional':
            doctype = self.transitional
        elif doctype == 'frameset':
            doctype = self.frameset
        elif doctype == 'html5':
            doctype = self.html5
        elif doctype == '':
            doctype = ''
        else:
            doctype = '%s\n' % doctype
        (fa, co) = self._xml()
        return '%s<%s%s>%s</%s>' % (doctype, self.tag, fa, co, self.tag)


class XHTML(DIV):
    """
    This is XHTML version of the HTML helper.

    There are three predefined document type definitions.
    They can be specified in the 'doctype' parameter:

    -'strict' enables strict doctype
    -'transitional' enables transitional doctype (default)
    -'frameset' enables frameset doctype
    -any other string will be treated as user's own doctype

    'lang' parameter specifies the language of the document and the xml document.
    Defaults to 'en'.

    'xmlns' parameter specifies the xml namespace.
    Defaults to 'http://www.w3.org/1999/xhtml'.

    See also :class:`DIV`
    """

    tag = 'html'

    strict = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'
    transitional = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
    frameset = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">\n'
    xmlns = 'http://www.w3.org/1999/xhtml'

    def xml(self):
        xmlns = self['xmlns']
        if xmlns:
            self.attributes['_xmlns'] = xmlns
        else:
            self.attributes['_xmlns'] = self.xmlns
        lang = self['lang']
        if not lang:
            lang = 'en'
        self.attributes['_lang'] = lang
        self.attributes['_xml:lang'] = lang
        doctype = self['doctype']
        if doctype:
            if doctype == 'strict':
                doctype = self.strict
            elif doctype == 'transitional':
                doctype = self.transitional
            elif doctype == 'frameset':
                doctype = self.frameset
            else:
                doctype = '%s\n' % doctype
        else:
            doctype = self.transitional
        (fa, co) = self._xml()
        return '%s<%s%s>%s</%s>' % (doctype, self.tag, fa, co, self.tag)


class HEAD(DIV):

    tag = 'head'


class TITLE(DIV):

    tag = 'title'


class META(DIV):

    tag = 'meta/'


class LINK(DIV):

    tag = 'link/'


class SCRIPT(DIV):

    tag = 'script'

    def xml(self):
        (fa, co) = self._xml()
        # no escaping of subcomponents
        co = '\n'.join([str(component) for component in
                       self.components])
        if co:
            # <script [attributes]><!--//--><![CDATA[//><!--
            # script body
            # //--><!]]></script>
            # return '<%s%s><!--//--><![CDATA[//><!--\n%s\n//--><!]]></%s>' % (self.tag, fa, co, self.tag)
            return '<%s%s><!--\n%s\n//--></%s>' % (self.tag, fa, co, self.tag)
        else:
            return DIV.xml(self)


class STYLE(DIV):

    tag = 'style'

    def xml(self):
        (fa, co) = self._xml()
        # no escaping of subcomponents
        co = '\n'.join([str(component) for component in
                       self.components])
        if co:
            # <style [attributes]><!--/*--><![CDATA[/*><!--*/
            # style body
            # /*]]>*/--></style>
            return '<%s%s><!--/*--><![CDATA[/*><!--*/\n%s\n/*]]>*/--></%s>' % (self.tag, fa, co, self.tag)
        else:
            return DIV.xml(self)


class IMG(DIV):

    tag = 'img/'


class SPAN(DIV):

    tag = 'span'


class BODY(DIV):

    tag = 'body'


class H1(DIV):

    tag = 'h1'


class H2(DIV):

    tag = 'h2'


class H3(DIV):

    tag = 'h3'


class H4(DIV):

    tag = 'h4'


class H5(DIV):

    tag = 'h5'


class H6(DIV):

    tag = 'h6'


class P(DIV):
    """
    Will replace ``\\n`` by ``<br />`` if the `cr2br` attribute is provided.

    see also :class:`DIV`
    """

    tag = 'p'

    def xml(self):
        text = DIV.xml(self)
        if self['cr2br']:
            text = text.replace('\n', '<br />')
        return text


class STRONG(DIV):

    tag = 'strong'


class B(DIV):

    tag = 'b'


class BR(DIV):

    tag = 'br/'


class HR(DIV):

    tag = 'hr/'


class A(DIV):

    tag = 'a'

    def xml(self):
        if not self.components and self['_href']:
            self.append(self['_href'])
        if not self['_disable_with']:
            self['_data-w2p_disable_with'] = 'default'
        if self['callback'] and not self['_id']:
            self['_id'] = web2py_uuid()        
        if self['delete']:
            self['_data-w2p_remove'] = self['delete']
        if self['target']:
            if self['target'] == '<self>':
                self['target'] = self['_id']
            self['_data-w2p_target'] = self['target']
        if self['component']:
            self['_data-w2p_method'] = 'GET'
            self['_href'] = self['component']
        elif self['callback']:
            self['_data-w2p_method'] = 'POST'
            self['_href'] = self['callback']
            if self['delete'] and not self['noconfirm']:
                if not self['confirm']:
                    self['_data-w2p_confirm'] = 'default'
                else:
                    self['_data-w2p_confirm'] = self['confirm']
        elif self['cid']:
            self['_data-w2p_method'] = 'GET'
            self['_data-w2p_target'] = self['cid']
            if self['pre_call']:
                self['_data-w2p_pre_call'] = self['pre_call']
        return DIV.xml(self)

class BUTTON(DIV):

    tag = 'button'


class EM(DIV):

    tag = 'em'


class EMBED(DIV):

    tag = 'embed/'


class TT(DIV):

    tag = 'tt'


class PRE(DIV):

    tag = 'pre'


class CENTER(DIV):

    tag = 'center'


class CODE(DIV):

    """
    displays code in HTML with syntax highlighting.

    :param attributes: optional attributes:

        - language: indicates the language, otherwise PYTHON is assumed
        - link: can provide a link
        - styles: for styles

    Example::

        {{=CODE(\"print 'hello world'\", language='python', link=None,
            counter=1, styles={}, highlight_line=None)}}


    supported languages are \"python\", \"html_plain\", \"c\", \"cpp\",
    \"web2py\", \"html\".
    The \"html\" language interprets {{ and }} tags as \"web2py\" code,
    \"html_plain\" doesn't.

    if a link='/examples/global/vars/' is provided web2py keywords are linked to
    the online docs.

    the counter is used for line numbering, counter can be None or a prompt
    string.
    """

    def xml(self):
        language = self['language'] or 'PYTHON'
        link = self['link']
        counter = self.attributes.get('counter', 1)
        highlight_line = self.attributes.get('highlight_line', None)
        context_lines = self.attributes.get('context_lines', None)
        styles = self['styles'] or {}
        return highlight(
            join(self.components),
            language=language,
            link=link,
            counter=counter,
            styles=styles,
            attributes=self.attributes,
            highlight_line=highlight_line,
            context_lines=context_lines,
        )


class LABEL(DIV):

    tag = 'label'


class LI(DIV):

    tag = 'li'


class UL(DIV):
    """
    UL Component.

    If subcomponents are not LI-components they will be wrapped in a LI

    see also :class:`DIV`
    """

    tag = 'ul'

    def _fixup(self):
        self._wrap_components(LI, LI)


class OL(UL):

    tag = 'ol'


class TD(DIV):

    tag = 'td'


class TH(DIV):

    tag = 'th'


class TR(DIV):
    """
    TR Component.

    If subcomponents are not TD/TH-components they will be wrapped in a TD

    see also :class:`DIV`
    """

    tag = 'tr'

    def _fixup(self):
        self._wrap_components((TD, TH), TD)


class THEAD(DIV):

    tag = 'thead'

    def _fixup(self):
        self._wrap_components(TR, TR)


class TBODY(DIV):

    tag = 'tbody'

    def _fixup(self):
        self._wrap_components(TR, TR)


class TFOOT(DIV):

    tag = 'tfoot'

    def _fixup(self):
        self._wrap_components(TR, TR)


class COL(DIV):

    tag = 'col'


class COLGROUP(DIV):

    tag = 'colgroup'


class TABLE(DIV):
    """
    TABLE Component.

    If subcomponents are not TR/TBODY/THEAD/TFOOT-components
    they will be wrapped in a TR

    see also :class:`DIV`
    """

    tag = 'table'

    def _fixup(self):
        self._wrap_components((TR, TBODY, THEAD, TFOOT, COL, COLGROUP), TR)


class I(DIV):

    tag = 'i'


class IFRAME(DIV):

    tag = 'iframe'


class INPUT(DIV):

    """
        INPUT Component

        examples::

            >>> INPUT(_type='text', _name='name', value='Max').xml()
            '<input name=\"name\" type=\"text\" value=\"Max\" />'

            >>> INPUT(_type='checkbox', _name='checkbox', value='on').xml()
            '<input checked=\"checked\" name=\"checkbox\" type=\"checkbox\" value=\"on\" />'

            >>> INPUT(_type='radio', _name='radio', _value='yes', value='yes').xml()
            '<input checked=\"checked\" name=\"radio\" type=\"radio\" value=\"yes\" />'

            >>> INPUT(_type='radio', _name='radio', _value='no', value='yes').xml()
            '<input name=\"radio\" type=\"radio\" value=\"no\" />'

        the input helper takes two special attributes value= and requires=.

        :param value: used to pass the initial value for the input field.
            value differs from _value because it works for checkboxes, radio,
            textarea and select/option too.

            - for a checkbox value should be '' or 'on'.
            - for a radio or select/option value should be the _value
                of the checked/selected item.

        :param requires: should be None, or a validator or a list of validators
            for the value of the field.
        """

    tag = 'input/'

    def _validate(self):

        # # this only changes value, not _value

        name = self['_name']
        if name is None or name == '':
            return True
        name = str(name)
        request_vars_get = self.request_vars.get
        if self['_type'] != 'checkbox':
            self['old_value'] = self['value'] or self['_value'] or ''
            value = request_vars_get(name, '')
            self['value'] = value if not hasattr(value,'file') else None
        else:
            self['old_value'] = self['value'] or False
            value = request_vars_get(name)
            if isinstance(value, (tuple, list)):
                self['value'] = self['_value'] in value
            else:
                self['value'] = self['_value'] == value
        requires = self['requires']
        if requires:
            if not isinstance(requires, (list, tuple)):
                requires = [requires]
            for validator in requires:
                (value, errors) = validator(value)
                if not errors is None:
                    self.vars[name] = value
                    self.errors[name] = errors
                    break
        if not name in self.errors:
            self.vars[name] = value
            return True
        return False

    def _postprocessing(self):
        t = self['_type']
        if not t:
            t = self['_type'] = 'text'
        t = t.lower()
        value = self['value']
        if self['_value'] is None or isinstance(self['_value'],cgi.FieldStorage):
            _value = None
        else:
            _value = str(self['_value'])
        if '_checked' in self.attributes and not 'value' in self.attributes:
            pass
        elif t == 'checkbox':
            if not _value:
                _value = self['_value'] = 'on'
            if not value:
                value = []
            elif value is True:
                value = [_value]
            elif not isinstance(value, (list, tuple)):
                value = str(value).split('|')
            self['_checked'] = _value in value and 'checked' or None
        elif t == 'radio':
            if str(value) == str(_value):
                self['_checked'] = 'checked'
            else:
                self['_checked'] = None
        elif not t == 'submit':
            if value is None:
                self['value'] = _value
            elif not isinstance(value, list):
                self['_value'] = value

    def xml(self):
        name = self.attributes.get('_name', None)
        if name and hasattr(self, 'errors') \
                and self.errors.get(name, None) \
                and self['hideerror'] != True:
            self['_class'] = (self['_class'] and self['_class']
                              + ' ' or '') + 'invalidinput'
            return DIV.xml(self) + DIV(
                DIV(
                    self.errors[name], _class='error',
                    errors=None, _id='%s__error' % name),
                _class='error_wrapper').xml()
        else:
            if self['_class'] and self['_class'].endswith('invalidinput'):
                self['_class'] = self['_class'][:-12]
                if self['_class'] == '':
                    self['_class'] = None
            return DIV.xml(self)


class TEXTAREA(INPUT):

    """
    example::

        TEXTAREA(_name='sometext', value='blah '*100, requires=IS_NOT_EMPTY())

    'blah blah blah ...' will be the content of the textarea field.
    """

    tag = 'textarea'

    def _postprocessing(self):
        if not '_rows' in self.attributes:
            self['_rows'] = 10
        if not '_cols' in self.attributes:
            self['_cols'] = 40
        if not self['value'] is None:
            self.components = [self['value']]
        elif self.components:
            self['value'] = self.components[0]


class OPTION(DIV):

    tag = 'option'

    def _fixup(self):
        if not '_value' in self.attributes:
            self.attributes['_value'] = str(self.components[0])


class OBJECT(DIV):

    tag = 'object'


class OPTGROUP(DIV):

    tag = 'optgroup'

    def _fixup(self):
        components = []
        for c in self.components:
            if isinstance(c, OPTION):
                components.append(c)
            else:
                components.append(OPTION(c, _value=str(c)))
        self.components = components


class SELECT(INPUT):

    """
    example::

        >>> from validators import IS_IN_SET
        >>> SELECT('yes', 'no', _name='selector', value='yes',
        ...    requires=IS_IN_SET(['yes', 'no'])).xml()
        '<select name=\"selector\"><option selected=\"selected\" value=\"yes\">yes</option><option value=\"no\">no</option></select>'

    """

    tag = 'select'

    def _fixup(self):
        components = []
        for c in self.components:
            if isinstance(c, (OPTION, OPTGROUP)):
                components.append(c)
            else:
                components.append(OPTION(c, _value=str(c)))
        self.components = components

    def _postprocessing(self):
        component_list = []
        for c in self.components:
            if isinstance(c, OPTGROUP):
                component_list.append(c.components)
            else:
                component_list.append([c])
        options = itertools.chain(*component_list)

        value = self['value']
        if not value is None:
            if not self['_multiple']:
                for c in options:  # my patch
                    if ((value is not None) and
                        (str(c['_value']) == str(value))):
                        c['_selected'] = 'selected'
                    else:
                        c['_selected'] = None
            else:
                if isinstance(value, (list, tuple)):
                    values = [str(item) for item in value]
                else:
                    values = [str(value)]
                for c in options:  # my patch
                    if ((value is not None) and
                        (str(c['_value']) in values)):
                        c['_selected'] = 'selected'
                    else:
                        c['_selected'] = None


class FIELDSET(DIV):

    tag = 'fieldset'


class LEGEND(DIV):

    tag = 'legend'


class FORM(DIV):

    """
    example::

        >>> from validators import IS_NOT_EMPTY
        >>> form=FORM(INPUT(_name=\"test\", requires=IS_NOT_EMPTY()))
        >>> form.xml()
        '<form action=\"#\" enctype=\"multipart/form-data\" method=\"post\"><input name=\"test\" type=\"text\" /></form>'

    a FORM is container for INPUT, TEXTAREA, SELECT and other helpers

    form has one important method::

        form.accepts(request.vars, session)

    if form is accepted (and all validators pass) form.vars contains the
    accepted vars, otherwise form.errors contains the errors.
    in case of errors the form is modified to present the errors to the user.
    """

    tag = 'form'

    def __init__(self, *components, **attributes):
        DIV.__init__(self, *components, **attributes)
        self.vars = Storage()
        self.errors = Storage()
        self.latest = Storage()
        self.accepted = None  # none for not submitted

    def assert_status(self, status, request_vars):
        return status

    def accepts(
        self,
        request_vars,
        session=None,
        formname='default',
        keepvalues=False,
        onvalidation=None,
        hideerror=False,
        **kwargs
    ):
        """
        kwargs is not used but allows to specify the same interface for FORM and SQLFORM
        """
        if request_vars.__class__.__name__ == 'Request':
            request_vars = request_vars.post_vars
        self.errors.clear()
        self.request_vars = Storage()
        self.request_vars.update(request_vars)
        self.session = session
        self.formname = formname
        self.keepvalues = keepvalues

        # if this tag is a form and we are in accepting mode (status=True)
        # check formname and formkey

        status = True
        changed = False
        request_vars = self.request_vars
        if session is not None:
            formkey = session.get('_formkey[%s]' % formname, None)
            # check if user tampering with form and void CSRF
            if not formkey or formkey != request_vars._formkey:
                status = False
        if formname != request_vars._formname:
            status = False
        if status and session:
            # check if editing a record that has been modified by the server
            if hasattr(self, 'record_hash') and self.record_hash != formkey:
                status = False
                self.record_changed = changed = True
        status = self._traverse(status, hideerror)
        status = self.assert_status(status, request_vars)
        if onvalidation:
            if isinstance(onvalidation, dict):
                onsuccess = onvalidation.get('onsuccess', None)
                onfailure = onvalidation.get('onfailure', None)
                onchange = onvalidation.get('onchange', None)
                if [k for k in onvalidation if not k in (
                        'onsuccess','onfailure','onchange')]:
                    raise RuntimeError('Invalid key in onvalidate dict')
                if onsuccess and status:
                    call_as_list(onsuccess,self)
                if onfailure and request_vars and not status:
                    call_as_list(onfailure,self)
                    status = len(self.errors) == 0
                if changed:
                    if onchange and self.record_changed and \
                            self.detect_record_change:
                        call_as_list(onchange,self)
            elif status:
                call_as_list(onvalidation, self)
        if self.errors:
            status = False
        if not session is None:
            if hasattr(self, 'record_hash'):
                formkey = self.record_hash
            else:
                formkey = web2py_uuid()
            self.formkey = session['_formkey[%s]' % formname] = formkey
        if status and not keepvalues:
            self._traverse(False, hideerror)
        self.accepted = status
        return status

    def _postprocessing(self):
        if not '_action' in self.attributes:
            self['_action'] = '#'
        if not '_method' in self.attributes:
            self['_method'] = 'post'
        if not '_enctype' in self.attributes:
            self['_enctype'] = 'multipart/form-data'

    def hidden_fields(self):
        c = []
        attr = self.attributes.get('hidden', {})
        if 'hidden' in self.attributes:
            c = [INPUT(_type='hidden', _name=key, _value=value)
                 for (key, value) in attr.iteritems()]
        if hasattr(self, 'formkey') and self.formkey:
            c.append(INPUT(_type='hidden', _name='_formkey',
                     _value=self.formkey))
        if hasattr(self, 'formname') and self.formname:
            c.append(INPUT(_type='hidden', _name='_formname',
                     _value=self.formname))
        return DIV(c, _style="display:none;")

    def xml(self):
        newform = FORM(*self.components, **self.attributes)
        hidden_fields = self.hidden_fields()
        if hidden_fields.components:
            newform.append(hidden_fields)
        return DIV.xml(newform)

    def validate(self, **kwargs):
        """
        This function validates the form,
        you can use it instead of directly form.accepts.

        Usage:
        In controller

        def action():
            form=FORM(INPUT(_name=\"test\", requires=IS_NOT_EMPTY()))
            form.validate() #you can pass some args here - see below
            return dict(form=form)

        This can receive a bunch of arguments

        onsuccess = 'flash' - will show message_onsuccess in response.flash
                    None - will do nothing
                    can be a function (lambda form: pass)
        onfailure = 'flash' - will show message_onfailure in response.flash
                    None - will do nothing
                    can be a function (lambda form: pass)
        onchange = 'flash' - will show message_onchange in response.flash
                    None - will do nothing
                    can be a function (lambda form: pass)

        message_onsuccess
        message_onfailure
        message_onchange
        next      = where to redirect in case of success
        any other kwargs will be passed for form.accepts(...)
        """
        from gluino import current, redirect
        kwargs['request_vars'] = kwargs.get(
            'request_vars', current.request.post_vars)
        kwargs['session'] = kwargs.get('session', current.session)
        kwargs['dbio'] = kwargs.get('dbio', False)
                                    # necessary for SQLHTML forms

        onsuccess = kwargs.get('onsuccess', 'flash')
        onfailure = kwargs.get('onfailure', 'flash')
        onchange = kwargs.get('onchange', 'flash')
        message_onsuccess = kwargs.get('message_onsuccess',
                                       current.T("Success!"))
        message_onfailure = kwargs.get('message_onfailure',
                                       current.T("Errors in form, please check it out."))
        message_onchange = kwargs.get('message_onchange',
                                      current.T("Form consecutive submissions not allowed. " +
                                                "Try re-submitting or refreshing the form page."))
        next = kwargs.get('next', None)
        for key in ('message_onsuccess', 'message_onfailure', 'onsuccess',
                    'onfailure', 'next', 'message_onchange', 'onchange'):
            if key in kwargs:
                del kwargs[key]

        if self.accepts(**kwargs):
            if onsuccess == 'flash':
                if next:
                    current.session.flash = message_onsuccess
                else:
                    current.response.flash = message_onsuccess
            elif callable(onsuccess):
                onsuccess(self)
            if next:
                if self.vars:
                    for key, value in self.vars.iteritems():
                        next = next.replace('[%s]' % key,
                                            urllib.quote(str(value)))
                    if not next.startswith('/'):
                        next = URL(next)
                redirect(next)
            return True
        elif self.errors:
            if onfailure == 'flash':
                current.response.flash = message_onfailure
            elif callable(onfailure):
                onfailure(self)
            return False
        elif hasattr(self, "record_changed"):
            if self.record_changed and self.detect_record_change:
                if onchange == 'flash':
                    current.response.flash = message_onchange
                elif callable(onchange):
                    onchange(self)
            return False

    def process(self, **kwargs):
        """
        Perform the .validate() method but returns the form

        Usage in controllers:
        # directly on return
        def action():
            #some code here
            return dict(form=FORM(...).process(...))

        You can use it with FORM, SQLFORM or FORM based plugins

        Examples:
        #response.flash messages
        def action():
            form = SQLFORM(db.table).process(message_onsuccess='Sucess!')
            retutn dict(form=form)

        # callback function
        # callback receives True or False as first arg, and a list of args.
        def my_callback(status, msg):
           response.flash = "Success! "+msg if status else "Errors occured"

        # after argument can be 'flash' to response.flash messages
        # or a function name to use as callback or None to do nothing.
        def action():
            return dict(form=SQLFORM(db.table).process(onsuccess=my_callback)
        """
        kwargs['dbio'] = kwargs.get('dbio', True)
                                    # necessary for SQLHTML forms
        self.validate(**kwargs)
        return self

    REDIRECT_JS = "window.location='%s';return false"

    def add_button(self, value, url, _class=None):
        submit = self.element('input[type=submit]')
        submit.parent.append(
            INPUT(_type="button", _value=value, _class=_class,
                  _onclick=self.REDIRECT_JS % url))

    @staticmethod
    def confirm(text='OK', buttons=None, hidden=None):
        if not buttons:
            buttons = {}
        if not hidden:
            hidden = {}
        inputs = [INPUT(_type='button',
                        _value=name,
                        _onclick=FORM.REDIRECT_JS % link)
                  for name, link in buttons.iteritems()]
        inputs += [INPUT(_type='hidden',
                         _name=name,
                         _value=value)
                   for name, value in hidden.iteritems()]
        form = FORM(INPUT(_type='submit', _value=text), *inputs)
        form.process()
        return form

    def as_dict(self, flat=False, sanitize=True):
        """EXPERIMENTAL

        Sanitize is naive. It should catch any unsafe value
        for client retrieval.
        """
        SERIALIZABLE = (int, float, bool, basestring, long,
                        set, list, dict, tuple, Storage, type(None))
        UNSAFE = ("PASSWORD", "CRYPT")
        d = self.__dict__

        def sanitizer(obj):
            if isinstance(obj, dict):
                for k in obj.keys():
                    if any([unsafe in str(k).upper() for
                           unsafe in UNSAFE]):
                       # erease unsafe pair
                       obj.pop(k)
            else:
                # not implemented
                pass
            return obj

        def flatten(obj):
            if isinstance(obj, (dict, Storage)):
                newobj = obj.copy()
            else:
                newobj = obj
            if sanitize:
                newobj = sanitizer(newobj)
            if flat:
                if type(obj) in SERIALIZABLE:
                    if isinstance(newobj, (dict, Storage)):
                        for k in newobj:
                            newk = flatten(k)
                            newobj[newk] = flatten(newobj[k])
                            if k != newk:
                                newobj.pop(k)
                        return newobj
                    elif isinstance(newobj, (list, tuple, set)):
                        return [flatten(item) for item in newobj]
                    else:
                        return newobj
                else: return str(newobj)
            else: return newobj
        return flatten(d)

    def as_json(self, sanitize=True):
        d = self.as_dict(flat=True, sanitize=sanitize)
        from serializers import json
        return json(d)

    def as_yaml(self, sanitize=True):
        d = self.as_dict(flat=True, sanitize=sanitize)
        from serializers import yaml
        return yaml(d)

    def as_xml(self, sanitize=True):
        d = self.as_dict(flat=True, sanitize=sanitize)
        from serializers import xml
        return xml(d)


class BEAUTIFY(DIV):

    """
    example::

        >>> BEAUTIFY(['a', 'b', {'hello': 'world'}]).xml()
        '<div><table><tr><td><div>a</div></td></tr><tr><td><div>b</div></td></tr><tr><td><div><table><tr><td style="font-weight:bold;vertical-align:top">hello</td><td valign="top">:</td><td><div>world</div></td></tr></table></div></td></tr></table></div>'

    turns any list, dictionary, etc into decent looking html.
    Two special attributes are
    :sorted: a function that takes the dict and returned sorted keys
    :keyfilter: a funciton that takes a key and returns its representation
                or None if the key is to be skipped. By default key[:1]=='_' is skipped.
    """

    tag = 'div'

    @staticmethod
    def no_underscore(key):
        if key[:1] == '_':
            return None
        return key

    def __init__(self, component, **attributes):
        self.components = [component]
        self.attributes = attributes
        sorter = attributes.get('sorted', sorted)
        keyfilter = attributes.get('keyfilter', BEAUTIFY.no_underscore)
        components = []
        attributes = copy.copy(self.attributes)
        level = attributes['level'] = attributes.get('level', 6) - 1
        if '_class' in attributes:
            attributes['_class'] += 'i'
        if level == 0:
            return
        for c in self.components:
            if hasattr(c, 'value') and not callable(c.value):
                if c.value:
                    components.append(c.value)
            if hasattr(c, 'xml') and callable(c.xml):
                components.append(c)
                continue
            elif hasattr(c, 'keys') and callable(c.keys):
                rows = []
                try:
                    keys = (sorter and sorter(c)) or c
                    for key in keys:
                        if isinstance(key, (str, unicode)) and keyfilter:
                            filtered_key = keyfilter(key)
                        else:
                            filtered_key = str(key)
                        if filtered_key is None:
                            continue
                        value = c[key]
                        if isinstance(value, types.LambdaType):
                            continue
                        rows.append(
                            TR(
                                TD(filtered_key, _style='font-weight:bold;vertical-align:top'),
                                TD(':', _valign='top'),
                                TD(BEAUTIFY(value, **attributes))))
                    components.append(TABLE(*rows, **attributes))
                    continue
                except:
                    pass
            if isinstance(c, str):
                components.append(str(c))
            elif isinstance(c, unicode):
                components.append(c.encode('utf8'))
            elif isinstance(c, (list, tuple)):
                items = [TR(TD(BEAUTIFY(item, **attributes)))
                         for item in c]
                components.append(TABLE(*items, **attributes))
            elif isinstance(c, cgi.FieldStorage):
                components.append('FieldStorage object')
            else:
                components.append(repr(c))
        self.components = components


class MENU(DIV):
    """
    Used to build menus

    Optional arguments
      _class: defaults to 'web2py-menu web2py-menu-vertical'
      ul_class: defaults to 'web2py-menu-vertical'
      li_class: defaults to 'web2py-menu-expand'
      li_first: defaults to 'web2py-menu-first'
      li_last: defaults to 'web2py-menu-last'

    Example:
        menu = MENU([['name', False, URL(...), [submenu]], ...])
        {{=menu}}
    """

    tag = 'ul'

    def __init__(self, data, **args):
        self.data = data
        self.attributes = args
        self.components = []
        if not '_class' in self.attributes:
            self['_class'] = 'web2py-menu web2py-menu-vertical'
        if not 'ul_class' in self.attributes:
            self['ul_class'] = 'web2py-menu-vertical'
        if not 'li_class' in self.attributes:
            self['li_class'] = 'web2py-menu-expand'
        if not 'li_first' in self.attributes:
            self['li_first'] = 'web2py-menu-first'
        if not 'li_last' in self.attributes:
            self['li_last'] = 'web2py-menu-last'
        if not 'li_active' in self.attributes:
            self['li_active'] = 'web2py-menu-active'
        if not 'mobile' in self.attributes:
            self['mobile'] = False

    def serialize(self, data, level=0):
        if level == 0:
            ul = UL(**self.attributes)
        else:
            ul = UL(_class=self['ul_class'])
        for item in data:
            if isinstance(item,LI):
                ul.append(item)
            else:
                (name, active, link) = item[:3]
                if isinstance(link, DIV):
                    li = LI(link)
                elif 'no_link_url' in self.attributes and self['no_link_url'] == link:
                    li = LI(DIV(name))
                elif isinstance(link,dict):
                    li = LI(A(name, **link))
                elif link:
                    li = LI(A(name, _href=link))
                elif not link and isinstance(name, A):
                    li = LI(name)
                else:
                    li = LI(A(name, _href='#',
                              _onclick='javascript:void(0);return false;'))
                if level == 0 and item == data[0]:
                    li['_class'] = self['li_first']
                elif level == 0 and item == data[-1]:
                    li['_class'] = self['li_last']
                if len(item) > 3 and item[3]:
                    li['_class'] = self['li_class']
                    li.append(self.serialize(item[3], level + 1))
                if active or ('active_url' in self.attributes and self['active_url'] == link):
                    if li['_class']:
                        li['_class'] = li['_class'] + ' ' + self['li_active']
                    else:
                        li['_class'] = self['li_active']
                if len(item) <= 4 or item[4] == True:
                    ul.append(li)
        return ul

    def serialize_mobile(self, data, select=None, prefix=''):
        if not select:
            select = SELECT(**self.attributes)
        for item in data:
            if len(item) <= 4 or item[4] == True:
                select.append(OPTION(CAT(prefix, item[0]),
                                     _value=item[2], _selected=item[1]))
                if len(item) > 3 and len(item[3]):
                    self.serialize_mobile(
                        item[3], select, prefix=CAT(prefix, item[0], '/'))
        select['_onchange'] = 'window.location=this.value'
        return select

    def xml(self):
        if self['mobile']:
            return self.serialize_mobile(self.data, 0).xml()
        else:
            return self.serialize(self.data, 0).xml()


def embed64(
    filename=None,
    file=None,
    data=None,
    extension='image/gif',
):
    """
    helper to encode the provided (binary) data into base64.

    :param filename: if provided, opens and reads this file in 'rb' mode
    :param file: if provided, reads this file
    :param data: if provided, uses the provided data
    """

    if filename and os.path.exists(file):
        fp = open(filename, 'rb')
        data = fp.read()
        fp.close()
    data = base64.b64encode(data)
    return 'data:%s;base64,%s' % (extension, data)


def test():
    """
    Example:

    >>> from validators import *
    >>> print DIV(A('click me', _href=URL(a='a', c='b', f='c')), BR(), HR(), DIV(SPAN(\"World\"), _class='unknown')).xml()
    <div><a data-w2p_disable_with="default" href="/a/b/c">click me</a><br /><hr /><div class=\"unknown\"><span>World</span></div></div>
    >>> print DIV(UL(\"doc\",\"cat\",\"mouse\")).xml()
    <div><ul><li>doc</li><li>cat</li><li>mouse</li></ul></div>
    >>> print DIV(UL(\"doc\", LI(\"cat\", _class='feline'), 18)).xml()
    <div><ul><li>doc</li><li class=\"feline\">cat</li><li>18</li></ul></div>
    >>> print TABLE(['a', 'b', 'c'], TR('d', 'e', 'f'), TR(TD(1), TD(2), TD(3))).xml()
    <table><tr><td>a</td><td>b</td><td>c</td></tr><tr><td>d</td><td>e</td><td>f</td></tr><tr><td>1</td><td>2</td><td>3</td></tr></table>
    >>> form=FORM(INPUT(_type='text', _name='myvar', requires=IS_EXPR('int(value)<10')))
    >>> print form.xml()
    <form action=\"#\" enctype=\"multipart/form-data\" method=\"post\"><input name=\"myvar\" type=\"text\" /></form>
    >>> print form.accepts({'myvar':'34'}, formname=None)
    False
    >>> print form.xml()
    <form action="#" enctype="multipart/form-data" method="post"><input class="invalidinput" name="myvar" type="text" value="34" /><div class="error_wrapper"><div class="error" id="myvar__error">invalid expression</div></div></form>
    >>> print form.accepts({'myvar':'4'}, formname=None, keepvalues=True)
    True
    >>> print form.xml()
    <form action=\"#\" enctype=\"multipart/form-data\" method=\"post\"><input name=\"myvar\" type=\"text\" value=\"4\" /></form>
    >>> form=FORM(SELECT('cat', 'dog', _name='myvar'))
    >>> print form.accepts({'myvar':'dog'}, formname=None, keepvalues=True)
    True
    >>> print form.xml()
    <form action=\"#\" enctype=\"multipart/form-data\" method=\"post\"><select name=\"myvar\"><option value=\"cat\">cat</option><option selected=\"selected\" value=\"dog\">dog</option></select></form>
    >>> form=FORM(INPUT(_type='text', _name='myvar', requires=IS_MATCH('^\w+$', 'only alphanumeric!')))
    >>> print form.accepts({'myvar':'as df'}, formname=None)
    False
    >>> print form.xml()
    <form action="#" enctype="multipart/form-data" method="post"><input class="invalidinput" name="myvar" type="text" value="as df" /><div class="error_wrapper"><div class="error" id="myvar__error">only alphanumeric!</div></div></form>
    >>> session={}
    >>> form=FORM(INPUT(value=\"Hello World\", _name=\"var\", requires=IS_MATCH('^\w+$')))
    >>> isinstance(form.as_dict(), dict)
    True
    >>> form.as_dict(flat=True).has_key("vars")
    True
    >>> isinstance(form.as_json(), basestring) and len(form.as_json(sanitize=False)) > 0
    True
    >>> if form.accepts({}, session,formname=None): print 'passed'
    >>> if form.accepts({'var':'test ', '_formkey': session['_formkey[None]']}, session, formname=None): print 'passed'
    """
    pass


class web2pyHTMLParser(HTMLParser):
    """
    obj = web2pyHTMLParser(text) parses and html/xml text into web2py helpers.
    obj.tree contains the root of the tree, and tree can be manipulated

    >>> str(web2pyHTMLParser('hello<div a="b" c=3>wor&lt;ld<span>xxx</span>y<script/>yy</div>zzz').tree)
    'hello<div a="b" c="3">wor&lt;ld<span>xxx</span>y<script></script>yy</div>zzz'
    >>> str(web2pyHTMLParser('<div>a<span>b</div>c').tree)
    '<div>a<span>b</span></div>c'
    >>> tree = web2pyHTMLParser('hello<div a="b">world</div>').tree
    >>> tree.element(_a='b')['_c']=5
    >>> str(tree)
    'hello<div a="b" c="5">world</div>'
    """
    def __init__(self, text, closed=('input', 'link')):
        HTMLParser.__init__(self)
        self.tree = self.parent = TAG['']()
        self.closed = closed
        self.tags = [x for x in __all__ if isinstance(eval(x), DIV)]
        self.last = None
        self.feed(text)

    def handle_starttag(self, tagname, attrs):
        if tagname.upper() in self.tags:
            tag = eval(tagname.upper())
        else:
            if tagname in self.closed:
                tagname += '/'
            tag = TAG[tagname]()
        for key, value in attrs:
            tag['_' + key] = value
        tag.parent = self.parent
        self.parent.append(tag)
        if not tag.tag.endswith('/'):
            self.parent = tag
        else:
            self.last = tag.tag[:-1]

    def handle_data(self, data):
        if not isinstance(data, unicode):
            try:
                data = data.decode('utf8')
            except:
                data = data.decode('latin1')
        self.parent.append(data.encode('utf8', 'xmlcharref'))

    def handle_charref(self, name):
        if name.startswith('x'):
            self.parent.append(unichr(int(name[1:], 16)).encode('utf8'))
        else:
            self.parent.append(unichr(int(name)).encode('utf8'))

    def handle_entityref(self, name):
        self.parent.append(entitydefs[name])

    def handle_endtag(self, tagname):
        # this deals with unbalanced tags
        if tagname == self.last:
            return
        while True:
            try:
                parent_tagname = self.parent.tag
                self.parent = self.parent.parent
            except:
                raise RuntimeError("unable to balance tag %s" % tagname)
            if parent_tagname[:len(tagname)] == tagname: break


def markdown_serializer(text, tag=None, attr=None):
    attr = attr or {}
    if tag is None:
        return re.sub('\s+', ' ', text)
    if tag == 'br':
        return '\n\n'
    if tag == 'h1':
        return '#' + text + '\n\n'
    if tag == 'h2':
        return '#' * 2 + text + '\n\n'
    if tag == 'h3':
        return '#' * 3 + text + '\n\n'
    if tag == 'h4':
        return '#' * 4 + text + '\n\n'
    if tag == 'p':
        return text + '\n\n'
    if tag == 'b' or tag == 'strong':
        return '**%s**' % text
    if tag == 'em' or tag == 'i':
        return '*%s*' % text
    if tag == 'tt' or tag == 'code':
        return '`%s`' % text
    if tag == 'a':
        return '[%s](%s)' % (text, attr.get('_href', ''))
    if tag == 'img':
        return '![%s](%s)' % (attr.get('_alt', ''), attr.get('_src', ''))
    return text


def markmin_serializer(text, tag=None, attr=None):
    attr = attr or {}
    # if tag is None: return re.sub('\s+',' ',text)
    if tag == 'br':
        return '\n\n'
    if tag == 'h1':
        return '# ' + text + '\n\n'
    if tag == 'h2':
        return '#' * 2 + ' ' + text + '\n\n'
    if tag == 'h3':
        return '#' * 3 + ' ' + text + '\n\n'
    if tag == 'h4':
        return '#' * 4 + ' ' + text + '\n\n'
    if tag == 'p':
        return text + '\n\n'
    if tag == 'li':
        return '\n- ' + text.replace('\n', ' ')
    if tag == 'tr':
        return text[3:].replace('\n', ' ') + '\n'
    if tag in ['table', 'blockquote']:
        return '\n-----\n' + text + '\n------\n'
    if tag in ['td', 'th']:
        return ' | ' + text
    if tag in ['b', 'strong', 'label']:
        return '**%s**' % text
    if tag in ['em', 'i']:
        return "''%s''" % text
    if tag in ['tt']:
        return '``%s``' % text.strip()
    if tag in ['code']:
        return '``\n%s``' % text
    if tag == 'a':
        return '[[%s %s]]' % (text, attr.get('_href', ''))
    if tag == 'img':
        return '[[%s %s left]]' % (attr.get('_alt', 'no title'), attr.get('_src', ''))
    return text


class MARKMIN(XmlComponent):
    """
    For documentation: http://web2py.com/examples/static/markmin.html
    """
    def __init__(self, text, extra=None, allowed=None, sep='p',
                 url=None, environment=None, latex='google',
                 autolinks='default',
                 protolinks='default',
                 class_prefix='',
                 id_prefix='markmin_'):
        self.text = text
        self.extra = extra or {}
        self.allowed = allowed or {}
        self.sep = sep
        self.url = URL if url == True else url
        self.environment = environment
        self.latex = latex
        self.autolinks = autolinks
        self.protolinks = protolinks
        self.class_prefix = class_prefix
        self.id_prefix = id_prefix

    def xml(self):
        """
        calls the gluino.contrib.markmin render function to convert the wiki syntax
        """
        from contrib.markmin.markmin2html import render
        return render(self.text, extra=self.extra,
                      allowed=self.allowed, sep=self.sep, latex=self.latex,
                      URL=self.url, environment=self.environment,
                      autolinks=self.autolinks, protolinks=self.protolinks,
                      class_prefix=self.class_prefix, id_prefix=self.id_prefix)

    def __str__(self):
        return self.xml()

    def flatten(self, render=None):
        """
        return the text stored by the MARKMIN object rendered by the render function
        """
        return self.text

    def elements(self, *args, **kargs):
        """
        to be considered experimental since the behavior of this method is questionable
        another options could be TAG(self.text).elements(*args,**kargs)
        """
        return [self.text]


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = http
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import re

__all__ = ['HTTP', 'redirect']

defined_status = {
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    422: 'UNPROCESSABLE ENTITY',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
}

regex_status = re.compile('^\d{3} \w+$')


class HTTP(Exception):

    def __init__(
        self,
        status,
        body='',
        cookies=None,
        **headers
    ):
        self.status = status
        self.body = body
        self.headers = headers
        self.cookies2headers(cookies)

    def cookies2headers(self, cookies):
        if cookies and len(cookies) > 0:
            self.headers['Set-Cookie'] = [
                str(cookie)[11:] for cookie in cookies.values()]

    def to(self, responder, env=None):
        env = env or {}
        status = self.status
        headers = self.headers
        if status in defined_status:
            status = '%d %s' % (status, defined_status[status])
        else:
            status = str(status)
            if not regex_status.match(status):
                status = '500 %s' % (defined_status[500])
        headers.setdefault('Content-Type', 'text/html; charset=UTF-8')
        body = self.body
        if status[:1] == '4':
            if not body:
                body = status
            if isinstance(body, str):
                headers['Content-Length'] = len(body)
        rheaders = []
        for k, v in headers.iteritems():
            if isinstance(v, list):
                rheaders += [(k, str(item)) for item in v]
            elif not v is None:
                rheaders.append((k, str(v)))
        responder(status, rheaders)
        if env.get('request_method', '') == 'HEAD':
            return ['']
        elif isinstance(body, str):
            return [body]
        elif hasattr(body, '__iter__'):
            return body
        else:
            return [str(body)]

    @property
    def message(self):
        """
        compose a message describing this exception

            "status defined_status [web2py_error]"

        message elements that are not defined are omitted
        """
        msg = '%(status)s'
        if self.status in defined_status:
            msg = '%(status)s %(defined_status)s'
        if 'web2py_error' in self.headers:
            msg += ' [%(web2py_error)s]'
        return msg % dict(
            status=self.status,
            defined_status=defined_status.get(self.status),
            web2py_error=self.headers.get('web2py_error'))

    def __str__(self):
        "stringify me"
        return self.message


def redirect(location='', how=303, client_side=False):
    if location:
        from gluino import current
        loc = location.replace('\r', '%0D').replace('\n', '%0A')
        if client_side and current.request.ajax:
            raise HTTP(200, **{'web2py-redirect-location': loc})
        else:
            raise HTTP(how,
                       'You are being redirected <a href="%s">here</a>' % loc,
                       Location=loc)
    else:
        from gluino import current
        if client_side and current.request.ajax:
            raise HTTP(200, **{'web2py-component-command': 'window.location.reload(true)'})

########NEW FILE########
__FILENAME__ = portalocker
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# portalocker.py
# Cross-platform (posix/nt) API for flock-style file locking.
#                  Requires python 1.5.2 or better.

"""
Cross-platform (posix/nt) API for flock-style file locking.

Synopsis:

   import portalocker
   file = open(\"somefile\", \"r+\")
   portalocker.lock(file, portalocker.LOCK_EX)
   file.seek(12)
   file.write(\"foo\")
   file.close()

If you know what you're doing, you may choose to

   portalocker.unlock(file)

before closing the file, but why?

Methods:

   lock( file, flags )
   unlock( file )

Constants:

   LOCK_EX
   LOCK_SH
   LOCK_NB

I learned the win32 technique for locking files from sample code
provided by John Nielsen <nielsenjf@my-deja.com> in the documentation
that accompanies the win32 modules.

Author: Jonathan Feinberg <jdf@pobox.com>
Version: $Id: portalocker.py,v 1.3 2001/05/29 18:47:55 Administrator Exp $
"""

import logging
import platform
logger = logging.getLogger("web2py")

os_locking = None
try:
    import google.appengine
    os_locking = 'gae'
except:
    try:
        import fcntl
        os_locking = 'posix'
    except:
        try:
            import win32con
            import win32file
            import pywintypes
            os_locking = 'windows'
        except:
            pass

if os_locking == 'windows':
    LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
    LOCK_SH = 0  # the default
    LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY

    # is there any reason not to reuse the following structure?

    __overlapped = pywintypes.OVERLAPPED()

    def lock(file, flags):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.LockFileEx(hfile, flags, 0, 0x7fff0000, __overlapped)

    def unlock(file):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.UnlockFileEx(hfile, 0, 0x7fff0000, __overlapped)


elif os_locking == 'posix':
    LOCK_EX = fcntl.LOCK_EX
    LOCK_SH = fcntl.LOCK_SH
    LOCK_NB = fcntl.LOCK_NB

    def lock(file, flags):
        fcntl.flock(file.fileno(), flags)

    def unlock(file):
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)


else:
    if platform.system() == 'Windows':
        logger.error('no file locking, you must install the win32 extensions from: http://sourceforge.net/projects/pywin32/files/')
    elif os_locking != 'gae':
        logger.debug('no file locking, this will cause problems')

    LOCK_EX = None
    LOCK_SH = None
    LOCK_NB = None

    def lock(file, flags):
        pass

    def unlock(file):
        pass


class LockedFile(object):
    def __init__(self, filename, mode='rb'):
        self.filename = filename
        self.mode = mode
        self.file = None
        if 'r' in mode:
            self.file = open(filename, mode)
            lock(self.file, LOCK_SH)
        elif 'w' in mode or 'a' in mode:
            self.file = open(filename, mode.replace('w', 'a'))
            lock(self.file, LOCK_EX)
            if not 'a' in mode:
                self.file.seek(0)
                self.file.truncate()
        else:
            raise RuntimeError("invalid LockedFile(...,mode)")

    def read(self, size=None):
        return self.file.read() if size is None else self.file.read(size)

    def readline(self):
        return self.file.readline()

    def readlines(self):
        return self.file.readlines()

    def write(self, data):
        self.file.write(data)
        self.file.flush()

    def close(self):
        if not self.file is None:
            unlock(self.file)
            self.file.close()
            self.file = None

    def __del__(self):
        if not self.file is None:
            self.close()


def read_locked(filename):
    fp = LockedFile(filename, 'r')
    data = fp.read()
    fp.close()
    return data


def write_locked(filename, data):
    fp = LockedFile(filename, 'w')
    data = fp.write(data)
    fp.close()

if __name__ == '__main__':
    f = LockedFile('test.txt', mode='wb')
    f.write('test ok')
    f.close()
    f = LockedFile('test.txt', mode='rb')
    sys.stdout.write(f.read()+'\n')
    f.close()

########NEW FILE########
__FILENAME__ = reserved_sql_keywords
# encoding utf-8

__author__ = "Thadeus Burgess <thadeusb@thadeusb.com>"

#    we classify as "non-reserved" those key words that are explicitly known
#    to the parser but are allowed as column or table names. Some key words
#    that are otherwise non-reserved cannot be used as function or data type n
#    ames and are in the nonreserved list. (Most of these words represent
#    built-in functions or data types with special syntax. The function
#    or type is still available but it cannot be redefined by the user.)
#    Labeled "reserved" are those tokens that are not allowed as column or
#    table names. Some reserved key words are allowable as names for
#    functions or data typesself.

# Note at the bottom of the list is a dict containing references to the
# tuples, and also if you add a list don't forget to remove its default
# set of COMMON.

# Keywords that are adapter specific. Such as a list of "postgresql"
# or "mysql" keywords

# These are keywords that are common to all SQL dialects, and should
# never be used as a table or column. Even if you use one of these
# the cursor will throw an OperationalError for the SQL syntax.
COMMON = set((
    'SELECT',
    'INSERT',
    'DELETE',
    'UPDATE',
    'DROP',
    'CREATE',
    'ALTER',

    'WHERE',
    'FROM',
    'INNER',
    'JOIN',
    'AND',
    'OR',
    'LIKE',
    'ON',
    'IN',
    'SET',

    'BY',
    'GROUP',
    'ORDER',
    'LEFT',
    'OUTER',

    'IF',
    'END',
    'THEN',
    'LOOP',
    'AS',
    'ELSE',
    'FOR',

    'CASE',
    'WHEN',
    'MIN',
    'MAX',
    'DISTINCT',
))


POSTGRESQL = set((
    'FALSE',
    'TRUE',
    'ALL',
    'ANALYSE',
    'ANALYZE',
    'AND',
    'ANY',
    'ARRAY',
    'AS',
    'ASC',
    'ASYMMETRIC',
    'AUTHORIZATION',
    'BETWEEN',
    'BIGINT',
    'BINARY',
    'BIT',
    'BOOLEAN',
    'BOTH',
    'CASE',
    'CAST',
    'CHAR',
    'CHARACTER',
    'CHECK',
    'COALESCE',
    'COLLATE',
    'COLUMN',
    'CONSTRAINT',
    'CREATE',
    'CROSS',
    'CURRENT_CATALOG',
    'CURRENT_DATE',
    'CURRENT_ROLE',
    'CURRENT_SCHEMA',
    'CURRENT_TIME',
    'CURRENT_TIMESTAMP',
    'CURRENT_USER',
    'DEC',
    'DECIMAL',
    'DEFAULT',
    'DEFERRABLE',
    'DESC',
    'DISTINCT',
    'DO',
    'ELSE',
    'END',
    'EXCEPT',
    'EXISTS',
    'EXTRACT',
    'FETCH',
    'FLOAT',
    'FOR',
    'FOREIGN',
    'FREEZE',
    'FROM',
    'FULL',
    'GRANT',
    'GREATEST',
    'GROUP',
    'HAVING',
    'ILIKE',
    'IN',
    'INITIALLY',
    'INNER',
    'INOUT',
    'INT',
    'INTEGER',
    'INTERSECT',
    'INTERVAL',
    'INTO',
    'IS',
    'ISNULL',
    'JOIN',
    'LEADING',
    'LEAST',
    'LEFT',
    'LIKE',
    'LIMIT',
    'LOCALTIME',
    'LOCALTIMESTAMP',
    'NATIONAL',
    'NATURAL',
    'NCHAR',
    'NEW',
    'NONE',
    'NOT',
    'NOTNULL',
    'NULL',
    'NULLIF',
    'NUMERIC',
    'OFF',
    'OFFSET',
    'OLD',
    'ON',
    'ONLY',
    'OR',
    'ORDER',
    'OUT',
    'OUTER',
    'OVERLAPS',
    'OVERLAY',
    'PLACING',
    'POSITION',
    'PRECISION',
    'PRIMARY',
    'REAL',
    'REFERENCES',
    'RETURNING',
    'RIGHT',
    'ROW',
    'SELECT',
    'SESSION_USER',
    'SETOF',
    'SIMILAR',
    'SMALLINT',
    'SOME',
    'SUBSTRING',
    'SYMMETRIC',
    'TABLE',
    'THEN',
    'TIME',
    'TIMESTAMP',
    'TO',
    'TRAILING',
    'TREAT',
    'TRIM',
    'UNION',
    'UNIQUE',
    'USER',
    'USING',
    'VALUES',
    'VARCHAR',
    'VARIADIC',
    'VERBOSE',
    'WHEN',
    'WHERE',
    'WITH',
    'XMLATTRIBUTES',
    'XMLCONCAT',
    'XMLELEMENT',
    'XMLFOREST',
    'XMLPARSE',
    'XMLPI',
    'XMLROOT',
    'XMLSERIALIZE',
))


POSTGRESQL_NONRESERVED = set((
    'A',
    'ABORT',
    'ABS',
    'ABSENT',
    'ABSOLUTE',
    'ACCESS',
    'ACCORDING',
    'ACTION',
    'ADA',
    'ADD',
    'ADMIN',
    'AFTER',
    'AGGREGATE',
    'ALIAS',
    'ALLOCATE',
    'ALSO',
    'ALTER',
    'ALWAYS',
    'ARE',
    'ARRAY_AGG',
    'ASENSITIVE',
    'ASSERTION',
    'ASSIGNMENT',
    'AT',
    'ATOMIC',
    'ATTRIBUTE',
    'ATTRIBUTES',
    'AVG',
    'BACKWARD',
    'BASE64',
    'BEFORE',
    'BEGIN',
    'BERNOULLI',
    'BIT_LENGTH',
    'BITVAR',
    'BLOB',
    'BOM',
    'BREADTH',
    'BY',
    'C',
    'CACHE',
    'CALL',
    'CALLED',
    'CARDINALITY',
    'CASCADE',
    'CASCADED',
    'CATALOG',
    'CATALOG_NAME',
    'CEIL',
    'CEILING',
    'CHAIN',
    'CHAR_LENGTH',
    'CHARACTER_LENGTH',
    'CHARACTER_SET_CATALOG',
    'CHARACTER_SET_NAME',
    'CHARACTER_SET_SCHEMA',
    'CHARACTERISTICS',
    'CHARACTERS',
    'CHECKED',
    'CHECKPOINT',
    'CLASS',
    'CLASS_ORIGIN',
    'CLOB',
    'CLOSE',
    'CLUSTER',
    'COBOL',
    'COLLATION',
    'COLLATION_CATALOG',
    'COLLATION_NAME',
    'COLLATION_SCHEMA',
    'COLLECT',
    'COLUMN_NAME',
    'COLUMNS',
    'COMMAND_FUNCTION',
    'COMMAND_FUNCTION_CODE',
    'COMMENT',
    'COMMIT',
    'COMMITTED',
    'COMPLETION',
    'CONCURRENTLY',
    'CONDITION',
    'CONDITION_NUMBER',
    'CONFIGURATION',
    'CONNECT',
    'CONNECTION',
    'CONNECTION_NAME',
    'CONSTRAINT_CATALOG',
    'CONSTRAINT_NAME',
    'CONSTRAINT_SCHEMA',
    'CONSTRAINTS',
    'CONSTRUCTOR',
    'CONTAINS',
    'CONTENT',
    'CONTINUE',
    'CONVERSION',
    'CONVERT',
    'COPY',
    'CORR',
    'CORRESPONDING',
    'COST',
    'COUNT',
    'COVAR_POP',
    'COVAR_SAMP',
    'CREATEDB',
    'CREATEROLE',
    'CREATEUSER',
    'CSV',
    'CUBE',
    'CUME_DIST',
    'CURRENT',
    'CURRENT_DEFAULT_TRANSFORM_GROUP',
    'CURRENT_PATH',
    'CURRENT_TRANSFORM_GROUP_FOR_TYPE',
    'CURSOR',
    'CURSOR_NAME',
    'CYCLE',
    'DATA',
    'DATABASE',
    'DATE',
    'DATETIME_INTERVAL_CODE',
    'DATETIME_INTERVAL_PRECISION',
    'DAY',
    'DEALLOCATE',
    'DECLARE',
    'DEFAULTS',
    'DEFERRED',
    'DEFINED',
    'DEFINER',
    'DEGREE',
    'DELETE',
    'DELIMITER',
    'DELIMITERS',
    'DENSE_RANK',
    'DEPTH',
    'DEREF',
    'DERIVED',
    'DESCRIBE',
    'DESCRIPTOR',
    'DESTROY',
    'DESTRUCTOR',
    'DETERMINISTIC',
    'DIAGNOSTICS',
    'DICTIONARY',
    'DISABLE',
    'DISCARD',
    'DISCONNECT',
    'DISPATCH',
    'DOCUMENT',
    'DOMAIN',
    'DOUBLE',
    'DROP',
    'DYNAMIC',
    'DYNAMIC_FUNCTION',
    'DYNAMIC_FUNCTION_CODE',
    'EACH',
    'ELEMENT',
    'EMPTY',
    'ENABLE',
    'ENCODING',
    'ENCRYPTED',
    'END-EXEC',
    'ENUM',
    'EQUALS',
    'ESCAPE',
    'EVERY',
    'EXCEPTION',
    'EXCLUDE',
    'EXCLUDING',
    'EXCLUSIVE',
    'EXEC',
    'EXECUTE',
    'EXISTING',
    'EXP',
    'EXPLAIN',
    'EXTERNAL',
    'FAMILY',
    'FILTER',
    'FINAL',
    'FIRST',
    'FIRST_VALUE',
    'FLAG',
    'FLOOR',
    'FOLLOWING',
    'FORCE',
    'FORTRAN',
    'FORWARD',
    'FOUND',
    'FREE',
    'FUNCTION',
    'FUSION',
    'G',
    'GENERAL',
    'GENERATED',
    'GET',
    'GLOBAL',
    'GO',
    'GOTO',
    'GRANTED',
    'GROUPING',
    'HANDLER',
    'HEADER',
    'HEX',
    'HIERARCHY',
    'HOLD',
    'HOST',
    'HOUR',
                             #    'ID',
    'IDENTITY',
    'IF',
    'IGNORE',
    'IMMEDIATE',
    'IMMUTABLE',
    'IMPLEMENTATION',
    'IMPLICIT',
    'INCLUDING',
    'INCREMENT',
    'INDENT',
    'INDEX',
    'INDEXES',
    'INDICATOR',
    'INFIX',
    'INHERIT',
    'INHERITS',
    'INITIALIZE',
    'INPUT',
    'INSENSITIVE',
    'INSERT',
    'INSTANCE',
    'INSTANTIABLE',
    'INSTEAD',
    'INTERSECTION',
    'INVOKER',
    'ISOLATION',
    'ITERATE',
    'K',
    'KEY',
    'KEY_MEMBER',
    'KEY_TYPE',
    'LAG',
    'LANCOMPILER',
    'LANGUAGE',
    'LARGE',
    'LAST',
    'LAST_VALUE',
    'LATERAL',
    'LC_COLLATE',
    'LC_CTYPE',
    'LEAD',
    'LENGTH',
    'LESS',
    'LEVEL',
    'LIKE_REGEX',
    'LISTEN',
    'LN',
    'LOAD',
    'LOCAL',
    'LOCATION',
    'LOCATOR',
    'LOCK',
    'LOGIN',
    'LOWER',
    'M',
    'MAP',
    'MAPPING',
    'MATCH',
    'MATCHED',
    'MAX',
    'MAX_CARDINALITY',
    'MAXVALUE',
    'MEMBER',
    'MERGE',
    'MESSAGE_LENGTH',
    'MESSAGE_OCTET_LENGTH',
    'MESSAGE_TEXT',
    'METHOD',
    'MIN',
    'MINUTE',
    'MINVALUE',
    'MOD',
    'MODE',
    'MODIFIES',
    'MODIFY',
    'MODULE',
    'MONTH',
    'MORE',
    'MOVE',
    'MULTISET',
    'MUMPS',
                             #    'NAME',
    'NAMES',
    'NAMESPACE',
    'NCLOB',
    'NESTING',
    'NEXT',
    'NFC',
    'NFD',
    'NFKC',
    'NFKD',
    'NIL',
    'NO',
    'NOCREATEDB',
    'NOCREATEROLE',
    'NOCREATEUSER',
    'NOINHERIT',
    'NOLOGIN',
    'NORMALIZE',
    'NORMALIZED',
    'NOSUPERUSER',
    'NOTHING',
    'NOTIFY',
    'NOWAIT',
    'NTH_VALUE',
    'NTILE',
    'NULLABLE',
    'NULLS',
    'NUMBER',
    'OBJECT',
    'OCCURRENCES_REGEX',
    'OCTET_LENGTH',
    'OCTETS',
    'OF',
    'OIDS',
    'OPEN',
    'OPERATION',
    'OPERATOR',
    'OPTION',
    'OPTIONS',
    'ORDERING',
    'ORDINALITY',
    'OTHERS',
    'OUTPUT',
    'OVER',
    'OVERRIDING',
    'OWNED',
    'OWNER',
    'P',
    'PAD',
    'PARAMETER',
    'PARAMETER_MODE',
    'PARAMETER_NAME',
    'PARAMETER_ORDINAL_POSITION',
    'PARAMETER_SPECIFIC_CATALOG',
    'PARAMETER_SPECIFIC_NAME',
    'PARAMETER_SPECIFIC_SCHEMA',
    'PARAMETERS',
    'PARSER',
    'PARTIAL',
    'PARTITION',
    'PASCAL',
    'PASSING',
                             #    'PASSWORD',
    'PATH',
    'PERCENT_RANK',
    'PERCENTILE_CONT',
    'PERCENTILE_DISC',
    'PLANS',
    'PLI',
    'POSITION_REGEX',
    'POSTFIX',
    'POWER',
    'PRECEDING',
    'PREFIX',
    'PREORDER',
    'PREPARE',
    'PREPARED',
    'PRESERVE',
    'PRIOR',
    'PRIVILEGES',
    'PROCEDURAL',
    'PROCEDURE',
    'PUBLIC',
    'QUOTE',
    'RANGE',
    'RANK',
    'READ',
    'READS',
    'REASSIGN',
    'RECHECK',
    'RECURSIVE',
    'REF',
    'REFERENCING',
    'REGR_AVGX',
    'REGR_AVGY',
    'REGR_COUNT',
    'REGR_INTERCEPT',
    'REGR_R2',
    'REGR_SLOPE',
    'REGR_SXX',
    'REGR_SXY',
    'REGR_SYY',
    'REINDEX',
    'RELATIVE',
    'RELEASE',
    'RENAME',
    'REPEATABLE',
    'REPLACE',
    'REPLICA',
    'RESET',
    'RESPECT',
    'RESTART',
    'RESTRICT',
    'RESULT',
    'RETURN',
    'RETURNED_CARDINALITY',
    'RETURNED_LENGTH',
    'RETURNED_OCTET_LENGTH',
    'RETURNED_SQLSTATE',
    'RETURNS',
    'REVOKE',
                             #    'ROLE',
    'ROLLBACK',
    'ROLLUP',
    'ROUTINE',
    'ROUTINE_CATALOG',
    'ROUTINE_NAME',
    'ROUTINE_SCHEMA',
    'ROW_COUNT',
    'ROW_NUMBER',
    'ROWS',
    'RULE',
    'SAVEPOINT',
    'SCALE',
    'SCHEMA',
    'SCHEMA_NAME',
    'SCOPE',
    'SCOPE_CATALOG',
    'SCOPE_NAME',
    'SCOPE_SCHEMA',
    'SCROLL',
    'SEARCH',
    'SECOND',
    'SECTION',
    'SECURITY',
    'SELF',
    'SENSITIVE',
    'SEQUENCE',
    'SERIALIZABLE',
    'SERVER',
    'SERVER_NAME',
    'SESSION',
    'SET',
    'SETS',
    'SHARE',
    'SHOW',
    'SIMPLE',
    'SIZE',
    'SOURCE',
    'SPACE',
    'SPECIFIC',
    'SPECIFIC_NAME',
    'SPECIFICTYPE',
    'SQL',
    'SQLCODE',
    'SQLERROR',
    'SQLEXCEPTION',
    'SQLSTATE',
    'SQLWARNING',
    'SQRT',
    'STABLE',
    'STANDALONE',
    'START',
    'STATE',
    'STATEMENT',
    'STATIC',
    'STATISTICS',
    'STDDEV_POP',
    'STDDEV_SAMP',
    'STDIN',
    'STDOUT',
    'STORAGE',
    'STRICT',
    'STRIP',
    'STRUCTURE',
    'STYLE',
    'SUBCLASS_ORIGIN',
    'SUBLIST',
    'SUBMULTISET',
    'SUBSTRING_REGEX',
    'SUM',
    'SUPERUSER',
    'SYSID',
    'SYSTEM',
    'SYSTEM_USER',
    'T',
                             #    'TABLE_NAME',
    'TABLESAMPLE',
    'TABLESPACE',
    'TEMP',
    'TEMPLATE',
    'TEMPORARY',
    'TERMINATE',
    'TEXT',
    'THAN',
    'TIES',
    'TIMEZONE_HOUR',
    'TIMEZONE_MINUTE',
    'TOP_LEVEL_COUNT',
    'TRANSACTION',
    'TRANSACTION_ACTIVE',
    'TRANSACTIONS_COMMITTED',
    'TRANSACTIONS_ROLLED_BACK',
    'TRANSFORM',
    'TRANSFORMS',
    'TRANSLATE',
    'TRANSLATE_REGEX',
    'TRANSLATION',
    'TRIGGER',
    'TRIGGER_CATALOG',
    'TRIGGER_NAME',
    'TRIGGER_SCHEMA',
    'TRIM_ARRAY',
    'TRUNCATE',
    'TRUSTED',
    'TYPE',
    'UESCAPE',
    'UNBOUNDED',
    'UNCOMMITTED',
    'UNDER',
    'UNENCRYPTED',
    'UNKNOWN',
    'UNLISTEN',
    'UNNAMED',
    'UNNEST',
    'UNTIL',
    'UNTYPED',
    'UPDATE',
    'UPPER',
    'URI',
    'USAGE',
    'USER_DEFINED_TYPE_CATALOG',
    'USER_DEFINED_TYPE_CODE',
    'USER_DEFINED_TYPE_NAME',
    'USER_DEFINED_TYPE_SCHEMA',
    'VACUUM',
    'VALID',
    'VALIDATOR',
    'VALUE',
    'VAR_POP',
    'VAR_SAMP',
    'VARBINARY',
    'VARIABLE',
    'VARYING',
    'VERSION',
    'VIEW',
    'VOLATILE',
    'WHENEVER',
    'WHITESPACE',
    'WIDTH_BUCKET',
    'WINDOW',
    'WITHIN',
    'WITHOUT',
    'WORK',
    'WRAPPER',
    'WRITE',
    'XML',
    'XMLAGG',
    'XMLBINARY',
    'XMLCAST',
    'XMLCOMMENT',
    'XMLDECLARATION',
    'XMLDOCUMENT',
    'XMLEXISTS',
    'XMLITERATE',
    'XMLNAMESPACES',
    'XMLQUERY',
    'XMLSCHEMA',
    'XMLTABLE',
    'XMLTEXT',
    'XMLVALIDATE',
    'YEAR',
    'YES',
    'ZONE',
                             ))

#Thanks villas
FIREBIRD = set((
    'ABS',
    'ACTIVE',
    'ADMIN',
    'AFTER',
    'ASCENDING',
    'AUTO',
    'AUTODDL',
    'BASED',
    'BASENAME',
    'BASE_NAME',
    'BEFORE',
    'BIT_LENGTH',
    'BLOB',
    'BLOBEDIT',
    'BOOLEAN',
    'BOTH',
    'BUFFER',
    'CACHE',
    'CHAR_LENGTH',
    'CHARACTER_LENGTH',
    'CHECK_POINT_LEN',
    'CHECK_POINT_LENGTH',
    'CLOSE',
    'COMMITTED',
    'COMPILETIME',
    'COMPUTED',
    'CONDITIONAL',
    'CONNECT',
    'CONTAINING',
    'CROSS',
    'CSTRING',
    'CURRENT_CONNECTION',
    'CURRENT_ROLE',
    'CURRENT_TRANSACTION',
    'CURRENT_USER',
    'DATABASE',
    'DB_KEY',
    'DEBUG',
    'DESCENDING',
    'DISCONNECT',
    'DISPLAY',
    'DO',
    'ECHO',
    'EDIT',
    'ENTRY_POINT',
    'EVENT',
    'EXIT',
    'EXTERN',
    'FALSE',
    'FETCH',
    'FILE',
    'FILTER',
    'FREE_IT',
    'FUNCTION',
    'GDSCODE',
    'GENERATOR',
    'GEN_ID',
    'GLOBAL',
    'GROUP_COMMIT_WAIT',
    'GROUP_COMMIT_WAIT_TIME',
    'HELP',
    'IF',
    'INACTIVE',
    'INDEX',
    'INIT',
    'INPUT_TYPE',
    'INSENSITIVE',
    'ISQL',
    'LC_MESSAGES',
    'LC_TYPE',
    'LEADING',
    'LENGTH',
    'LEV',
    'LOGFILE',
    'LOG_BUFFER_SIZE',
    'LOG_BUF_SIZE',
    'LONG',
    'LOWER',
    'MANUAL',
    'MAXIMUM',
    'MAXIMUM_SEGMENT',
    'MAX_SEGMENT',
    'MERGE',
    'MESSAGE',
    'MINIMUM',
    'MODULE_NAME',
    'NOAUTO',
    'NUM_LOG_BUFS',
    'NUM_LOG_BUFFERS',
    'OCTET_LENGTH',
    'OPEN',
    'OUTPUT_TYPE',
    'OVERFLOW',
    'PAGE',
    'PAGELENGTH',
    'PAGES',
    'PAGE_SIZE',
    'PARAMETER',
               #    'PASSWORD',
    'PLAN',
    'POST_EVENT',
    'QUIT',
    'RAW_PARTITIONS',
    'RDB$DB_KEY',
    'RECORD_VERSION',
    'RECREATE',
    'RECURSIVE',
    'RELEASE',
    'RESERV',
    'RESERVING',
    'RETAIN',
    'RETURN',
    'RETURNING_VALUES',
    'RETURNS',
               #    'ROLE',
    'ROW_COUNT',
    'ROWS',
    'RUNTIME',
    'SAVEPOINT',
    'SECOND',
    'SENSITIVE',
    'SHADOW',
    'SHARED',
    'SHELL',
    'SHOW',
    'SINGULAR',
    'SNAPSHOT',
    'SORT',
    'STABILITY',
    'START',
    'STARTING',
    'STARTS',
    'STATEMENT',
    'STATIC',
    'STATISTICS',
    'SUB_TYPE',
    'SUSPEND',
    'TERMINATOR',
    'TRAILING',
    'TRIGGER',
    'TRIM',
    'TRUE',
    'TYPE',
    'UNCOMMITTED',
    'UNKNOWN',
    'USING',
    'VARIABLE',
    'VERSION',
    'WAIT',
    'WEEKDAY',
    'WHILE',
    'YEARDAY',
               ))
FIREBIRD_NONRESERVED = set((
    'BACKUP',
    'BLOCK',
    'COALESCE',
    'COLLATION',
    'COMMENT',
    'DELETING',
    'DIFFERENCE',
    'IIF',
    'INSERTING',
    'LAST',
    'LEAVE',
    'LOCK',
    'NEXT',
    'NULLIF',
    'NULLS',
    'RESTART',
    'RETURNING',
    'SCALAR_ARRAY',
    'SEQUENCE',
    'STATEMENT',
    'UPDATING',
    'ABS',
    'ACCENT',
    'ACOS',
    'ALWAYS',
    'ASCII_CHAR',
    'ASCII_VAL',
    'ASIN',
    'ATAN',
    'ATAN2',
    'BACKUP',
    'BIN_AND',
    'BIN_OR',
    'BIN_SHL',
    'BIN_SHR',
    'BIN_XOR',
    'BLOCK',
    'CEIL',
    'CEILING',
    'COLLATION',
    'COMMENT',
    'COS',
    'COSH',
    'COT',
    'DATEADD',
    'DATEDIFF',
    'DECODE',
    'DIFFERENCE',
    'EXP',
    'FLOOR',
    'GEN_UUID',
    'GENERATED',
    'HASH',
    'IIF',
    'LIST',
    'LN',
    'LOG',
    'LOG10',
    'LPAD',
    'MATCHED',
    'MATCHING',
    'MAXVALUE',
    'MILLISECOND',
    'MINVALUE',
    'MOD',
    'NEXT',
    'OVERLAY',
    'PAD',
    'PI',
    'PLACING',
    'POWER',
    'PRESERVE',
    'RAND',
    'REPLACE',
    'RESTART',
    'RETURNING',
    'REVERSE',
    'ROUND',
    'RPAD',
    'SCALAR_ARRAY',
    'SEQUENCE',
    'SIGN',
    'SIN',
    'SINH',
    'SPACE',
    'SQRT',
    'TAN',
    'TANH',
    'TEMPORARY',
    'TRUNC',
    'WEEK',
))

# Thanks Jonathan Lundell
MYSQL = set((
    'ACCESSIBLE',
    'ADD',
    'ALL',
    'ALTER',
    'ANALYZE',
    'AND',
    'AS',
    'ASC',
    'ASENSITIVE',
    'BEFORE',
    'BETWEEN',
    'BIGINT',
    'BINARY',
    'BLOB',
    'BOTH',
    'BY',
    'CALL',
    'CASCADE',
    'CASE',
    'CHANGE',
    'CHAR',
    'CHARACTER',
    'CHECK',
    'COLLATE',
    'COLUMN',
    'CONDITION',
    'CONSTRAINT',
    'CONTINUE',
    'CONVERT',
    'CREATE',
    'CROSS',
    'CURRENT_DATE',
    'CURRENT_TIME',
    'CURRENT_TIMESTAMP',
    'CURRENT_USER',
    'CURSOR',
    'DATABASE',
    'DATABASES',
    'DAY_HOUR',
    'DAY_MICROSECOND',
    'DAY_MINUTE',
    'DAY_SECOND',
    'DEC',
    'DECIMAL',
    'DECLARE',
    'DEFAULT',
    'DELAYED',
    'DELETE',
    'DESC',
    'DESCRIBE',
    'DETERMINISTIC',
    'DISTINCT',
    'DISTINCTROW',
    'DIV',
    'DOUBLE',
    'DROP',
    'DUAL',
    'EACH',
    'ELSE',
    'ELSEIF',
    'ENCLOSED',
    'ESCAPED',
    'EXISTS',
    'EXIT',
    'EXPLAIN',
    'FALSE',
    'FETCH',
    'FLOAT',
    'FLOAT4',
    'FLOAT8',
    'FOR',
    'FORCE',
    'FOREIGN',
    'FROM',
    'FULLTEXT',
    'GRANT',
    'GROUP',
    'HAVING',
    'HIGH_PRIORITY',
    'HOUR_MICROSECOND',
    'HOUR_MINUTE',
    'HOUR_SECOND',
    'IF',
    'IGNORE',
    'IGNORE_SERVER_IDS',
    'IGNORE_SERVER_IDS',
    'IN',
    'INDEX',
    'INFILE',
    'INNER',
    'INOUT',
    'INSENSITIVE',
    'INSERT',
    'INT',
    'INT1',
    'INT2',
    'INT3',
    'INT4',
    'INT8',
    'INTEGER',
    'INTERVAL',
    'INTO',
    'IS',
    'ITERATE',
    'JOIN',
    'KEY',
    'KEYS',
    'KILL',
    'LEADING',
    'LEAVE',
    'LEFT',
    'LIKE',
    'LIMIT',
    'LINEAR',
    'LINES',
    'LOAD',
    'LOCALTIME',
    'LOCALTIMESTAMP',
    'LOCK',
    'LONG',
    'LONGBLOB',
    'LONGTEXT',
    'LOOP',
    'LOW_PRIORITY',
    'MASTER_HEARTBEAT_PERIOD',
    'MASTER_HEARTBEAT_PERIOD',
    'MASTER_SSL_VERIFY_SERVER_CERT',
    'MATCH',
    'MAXVALUE',
    'MAXVALUE',
    'MEDIUMBLOB',
    'MEDIUMINT',
    'MEDIUMTEXT',
    'MIDDLEINT',
    'MINUTE_MICROSECOND',
    'MINUTE_SECOND',
    'MOD',
    'MODIFIES',
    'NATURAL',
    'NO_WRITE_TO_BINLOG',
    'NOT',
    'NULL',
    'NUMERIC',
    'ON',
    'OPTIMIZE',
    'OPTION',
    'OPTIONALLY',
    'OR',
    'ORDER',
    'OUT',
    'OUTER',
    'OUTFILE',
    'PRECISION',
    'PRIMARY',
    'PROCEDURE',
    'PURGE',
    'RANGE',
    'READ',
    'READ_WRITE',
    'READS',
    'REAL',
    'REFERENCES',
    'REGEXP',
    'RELEASE',
    'RENAME',
    'REPEAT',
    'REPLACE',
    'REQUIRE',
    'RESIGNAL',
    'RESIGNAL',
    'RESTRICT',
    'RETURN',
    'REVOKE',
    'RIGHT',
    'RLIKE',
    'SCHEMA',
    'SCHEMAS',
    'SECOND_MICROSECOND',
    'SELECT',
    'SENSITIVE',
    'SEPARATOR',
    'SET',
    'SHOW',
    'SIGNAL',
    'SIGNAL',
    'SMALLINT',
    'SPATIAL',
    'SPECIFIC',
    'SQL',
    'SQL_BIG_RESULT',
    'SQL_CALC_FOUND_ROWS',
    'SQL_SMALL_RESULT',
    'SQLEXCEPTION',
    'SQLSTATE',
    'SQLWARNING',
    'SSL',
    'STARTING',
    'STRAIGHT_JOIN',
    'TABLE',
    'TERMINATED',
    'THEN',
    'TINYBLOB',
    'TINYINT',
    'TINYTEXT',
    'TO',
    'TRAILING',
    'TRIGGER',
    'TRUE',
    'UNDO',
    'UNION',
    'UNIQUE',
    'UNLOCK',
    'UNSIGNED',
    'UPDATE',
    'USAGE',
    'USE',
    'USING',
    'UTC_DATE',
    'UTC_TIME',
    'UTC_TIMESTAMP',
    'VALUES',
    'VARBINARY',
    'VARCHAR',
    'VARCHARACTER',
    'VARYING',
    'WHEN',
    'WHERE',
    'WHILE',
    'WITH',
    'WRITE',
    'XOR',
    'YEAR_MONTH',
    'ZEROFILL',
))

MSSQL = set((
    'ADD',
    'ALL',
    'ALTER',
    'AND',
    'ANY',
    'AS',
    'ASC',
    'AUTHORIZATION',
    'BACKUP',
    'BEGIN',
    'BETWEEN',
    'BREAK',
    'BROWSE',
    'BULK',
    'BY',
    'CASCADE',
    'CASE',
    'CHECK',
    'CHECKPOINT',
    'CLOSE',
    'CLUSTERED',
    'COALESCE',
    'COLLATE',
    'COLUMN',
    'COMMIT',
    'COMPUTE',
    'CONSTRAINT',
    'CONTAINS',
    'CONTAINSTABLE',
    'CONTINUE',
    'CONVERT',
    'CREATE',
    'CROSS',
    'CURRENT',
    'CURRENT_DATE',
    'CURRENT_TIME',
    'CURRENT_TIMESTAMP',
    'CURRENT_USER',
    'CURSOR',
    'DATABASE',
    'DBCC',
    'DEALLOCATE',
    'DECLARE',
    'DEFAULT',
    'DELETE',
    'DENY',
    'DESC',
    'DISK',
    'DISTINCT',
    'DISTRIBUTED',
    'DOUBLE',
    'DROP',
    'DUMMY',
    'DUMP',
    'ELSE',
    'END',
    'ERRLVL',
    'ESCAPE',
    'EXCEPT',
    'EXEC',
    'EXECUTE',
    'EXISTS',
    'EXIT',
    'FETCH',
    'FILE',
    'FILLFACTOR',
    'FOR',
    'FOREIGN',
    'FREETEXT',
    'FREETEXTTABLE',
    'FROM',
    'FULL',
    'FUNCTION',
    'GOTO',
    'GRANT',
    'GROUP',
    'HAVING',
    'HOLDLOCK',
    'IDENTITY',
    'IDENTITY_INSERT',
    'IDENTITYCOL',
    'IF',
    'IN',
    'INDEX',
    'INNER',
    'INSERT',
    'INTERSECT',
    'INTO',
    'IS',
    'JOIN',
    'KEY',
    'KILL',
    'LEFT',
    'LIKE',
    'LINENO',
    'LOAD',
    'NATIONAL ',
    'NOCHECK',
    'NONCLUSTERED',
    'NOT',
    'NULL',
    'NULLIF',
    'OF',
    'OFF',
    'OFFSETS',
    'ON',
    'OPEN',
    'OPENDATASOURCE',
    'OPENQUERY',
    'OPENROWSET',
    'OPENXML',
    'OPTION',
    'OR',
    'ORDER',
    'OUTER',
    'OVER',
    'PERCENT',
    'PLAN',
    'PRECISION',
    'PRIMARY',
    'PRINT',
    'PROC',
    'PROCEDURE',
    'PUBLIC',
    'RAISERROR',
    'READ',
    'READTEXT',
    'RECONFIGURE',
    'REFERENCES',
    'REPLICATION',
    'RESTORE',
    'RESTRICT',
    'RETURN',
    'REVOKE',
    'RIGHT',
    'ROLLBACK',
    'ROWCOUNT',
    'ROWGUIDCOL',
    'RULE',
    'SAVE',
    'SCHEMA',
    'SELECT',
    'SESSION_USER',
    'SET',
    'SETUSER',
    'SHUTDOWN',
    'SOME',
    'STATISTICS',
    'SYSTEM_USER',
    'TABLE',
    'TEXTSIZE',
    'THEN',
    'TO',
    'TOP',
    'TRAN',
    'TRANSACTION',
    'TRIGGER',
    'TRUNCATE',
    'TSEQUAL',
    'UNION',
    'UNIQUE',
    'UPDATE',
    'UPDATETEXT',
    'USE',
    'USER',
    'VALUES',
    'VARYING',
    'VIEW',
    'WAITFOR',
    'WHEN',
    'WHERE',
    'WHILE',
    'WITH',
    'WRITETEXT',
))

ORACLE = set((
    'ACCESS',
    'ADD',
    'ALL',
    'ALTER',
    'AND',
    'ANY',
    'AS',
    'ASC',
    'AUDIT',
    'BETWEEN',
    'BY',
    'CHAR',
    'CHECK',
    'CLUSTER',
    'COLUMN',
    'COMMENT',
    'COMPRESS',
    'CONNECT',
    'CREATE',
    'CURRENT',
    'DATE',
    'DECIMAL',
    'DEFAULT',
    'DELETE',
    'DESC',
    'DISTINCT',
    'DROP',
    'ELSE',
    'EXCLUSIVE',
    'EXISTS',
    'FILE',
    'FLOAT',
    'FOR',
    'FROM',
    'GRANT',
    'GROUP',
    'HAVING',
    'IDENTIFIED',
    'IMMEDIATE',
    'IN',
    'INCREMENT',
    'INDEX',
    'INITIAL',
    'INSERT',
    'INTEGER',
    'INTERSECT',
    'INTO',
    'IS',
    'LEVEL',
    'LIKE',
    'LOCK',
    'LONG',
    'MAXEXTENTS',
    'MINUS',
    'MLSLABEL',
    'MODE',
    'MODIFY',
    'NOAUDIT',
    'NOCOMPRESS',
    'NOT',
    'NOWAIT',
    'NULL',
    'NUMBER',
    'OF',
    'OFFLINE',
    'ON',
    'ONLINE',
    'OPTION',
    'OR',
    'ORDER',
    'PCTFREE',
    'PRIOR',
    'PRIVILEGES',
    'PUBLIC',
    'RAW',
    'RENAME',
    'RESOURCE',
    'REVOKE',
    'ROW',
    'ROWID',
    'ROWNUM',
    'ROWS',
    'SELECT',
    'SESSION',
    'SET',
    'SHARE',
    'SIZE',
    'SMALLINT',
    'START',
    'SUCCESSFUL',
    'SYNONYM',
    'SYSDATE',
    'TABLE',
    'THEN',
    'TO',
    'TRIGGER',
    'UID',
    'UNION',
    'UNIQUE',
    'UPDATE',
    'USER',
    'VALIDATE',
    'VALUES',
    'VARCHAR',
    'VARCHAR2',
    'VIEW',
    'WHENEVER',
    'WHERE',
    'WITH',
))

SQLITE = set((
    'ABORT',
    'ACTION',
    'ADD',
    'AFTER',
    'ALL',
    'ALTER',
    'ANALYZE',
    'AND',
    'AS',
    'ASC',
    'ATTACH',
    'AUTOINCREMENT',
    'BEFORE',
    'BEGIN',
    'BETWEEN',
    'BY',
    'CASCADE',
    'CASE',
    'CAST',
    'CHECK',
    'COLLATE',
    'COLUMN',
    'COMMIT',
    'CONFLICT',
    'CONSTRAINT',
    'CREATE',
    'CROSS',
    'CURRENT_DATE',
    'CURRENT_TIME',
    'CURRENT_TIMESTAMP',
    'DATABASE',
    'DEFAULT',
    'DEFERRABLE',
    'DEFERRED',
    'DELETE',
    'DESC',
    'DETACH',
    'DISTINCT',
    'DROP',
    'EACH',
    'ELSE',
    'END',
    'ESCAPE',
    'EXCEPT',
    'EXCLUSIVE',
    'EXISTS',
    'EXPLAIN',
    'FAIL',
    'FOR',
    'FOREIGN',
    'FROM',
    'FULL',
    'GLOB',
    'GROUP',
    'HAVING',
    'IF',
    'IGNORE',
    'IMMEDIATE',
    'IN',
    'INDEX',
    'INDEXED',
    'INITIALLY',
    'INNER',
    'INSERT',
    'INSTEAD',
    'INTERSECT',
    'INTO',
    'IS',
    'ISNULL',
    'JOIN',
    'KEY',
    'LEFT',
    'LIKE',
    'LIMIT',
    'MATCH',
    'NATURAL',
    'NO',
    'NOT',
    'NOTNULL',
    'NULL',
    'OF',
    'OFFSET',
    'ON',
    'OR',
    'ORDER',
    'OUTER',
    'PLAN',
    'PRAGMA',
    'PRIMARY',
    'QUERY',
    'RAISE',
    'REFERENCES',
    'REGEXP',
    'REINDEX',
    'RELEASE',
    'RENAME',
    'REPLACE',
    'RESTRICT',
    'RIGHT',
    'ROLLBACK',
    'ROW',
    'SAVEPOINT',
    'SELECT',
    'SET',
    'TABLE',
    'TEMP',
    'TEMPORARY',
    'THEN',
    'TO',
    'TRANSACTION',
    'TRIGGER',
    'UNION',
    'UNIQUE',
    'UPDATE',
    'USING',
    'VACUUM',
    'VALUES',
    'VIEW',
    'VIRTUAL',
    'WHEN',
    'WHERE',
))


MONGODB_NONRESERVED = set(('SAFE',))

# remove from here when you add a list.
JDBCSQLITE = SQLITE
DB2 = INFORMIX = INGRES = JDBCPOSTGRESQL = COMMON

ADAPTERS = {
    'sqlite': SQLITE,
    'mysql': MYSQL,
    'postgres': POSTGRESQL,
    'postgres_nonreserved': POSTGRESQL_NONRESERVED,
    'oracle': ORACLE,
    'mssql': MSSQL,
    'mssql2': MSSQL,
    'db2': DB2,
    'informix': INFORMIX,
    'firebird': FIREBIRD,
    'firebird_embedded': FIREBIRD,
    'firebird_nonreserved': FIREBIRD_NONRESERVED,
    'ingres': INGRES,
    'ingresu': INGRES,
    'jdbc:sqlite': JDBCSQLITE,
    'jdbc:postgres': JDBCPOSTGRESQL,
    'common': COMMON,
    'mongodb_nonreserved': MONGODB_NONRESERVED
}

ADAPTERS['all'] = reduce(lambda a, b: a.union(b), (
    x for x in ADAPTERS.values()))

########NEW FILE########
__FILENAME__ = sanitizer
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
::

    # from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496942
    # Title: Cross-site scripting (XSS) defense
    # Submitter: Josh Goldfoot (other recipes)
    # Last Updated: 2006/08/05
    # Version no: 1.0

"""


from htmllib import HTMLParser
from cgi import escape
from urlparse import urlparse
from formatter import AbstractFormatter
from htmlentitydefs import entitydefs
from xml.sax.saxutils import quoteattr

__all__ = ['sanitize']


def xssescape(text):
    """Gets rid of < and > and & and, for good measure, :"""

    return escape(text, quote=True).replace(':', '&#58;')


class XssCleaner(HTMLParser):

    def __init__(
        self,
        permitted_tags=[
            'a',
            'b',
            'blockquote',
            'br/',
            'i',
            'li',
            'ol',
            'ul',
            'p',
            'cite',
            'code',
            'pre',
            'img/',
        ],
        allowed_attributes={'a': ['href', 'title'], 'img': ['src', 'alt'
                                                            ], 'blockquote': ['type']},
        fmt=AbstractFormatter,
        strip_disallowed=False
    ):

        HTMLParser.__init__(self, fmt)
        self.result = ''
        self.open_tags = []
        self.permitted_tags = [i for i in permitted_tags if i[-1] != '/']
        self.requires_no_close = [i[:-1] for i in permitted_tags
                                  if i[-1] == '/']
        self.permitted_tags += self.requires_no_close
        self.allowed_attributes = allowed_attributes

        # The only schemes allowed in URLs (for href and src attributes).
        # Adding "javascript" or "vbscript" to this list would not be smart.

        self.allowed_schemes = ['http', 'https', 'ftp', 'mailto']

        #to strip or escape disallowed tags?
        self.strip_disallowed = strip_disallowed
        self.in_disallowed = False

    def handle_data(self, data):
        if data and not self.in_disallowed:
            self.result += xssescape(data)

    def handle_charref(self, ref):
        if self.in_disallowed:
            return
        elif len(ref) < 7 and ref.isdigit():
            self.result += '&#%s;' % ref
        else:
            self.result += xssescape('&#%s' % ref)

    def handle_entityref(self, ref):
        if self.in_disallowed:
            return
        elif ref in entitydefs:
            self.result += '&%s;' % ref
        else:
            self.result += xssescape('&%s' % ref)

    def handle_comment(self, comment):
        if self.in_disallowed:
            return
        elif comment:
            self.result += xssescape('<!--%s-->' % comment)

    def handle_starttag(
        self,
        tag,
        method,
        attrs,
    ):
        if tag not in self.permitted_tags:
            if self.strip_disallowed:
                self.in_disallowed = True
            else:
                self.result += xssescape('<%s>' % tag)
        else:
            bt = '<' + tag
            if tag in self.allowed_attributes:
                attrs = dict(attrs)
                self.allowed_attributes_here = [x for x in
                                                self.allowed_attributes[tag] if x in attrs
                                                and len(attrs[x]) > 0]
                for attribute in self.allowed_attributes_here:
                    if attribute in ['href', 'src', 'background']:
                        if self.url_is_acceptable(attrs[attribute]):
                            bt += ' %s="%s"' % (attribute,
                                                attrs[attribute])
                    else:
                        bt += ' %s=%s' % (xssescape(attribute),
                                          quoteattr(attrs[attribute]))
            if bt == '<a' or bt == '<img':
                return
            if tag in self.requires_no_close:
                bt += ' /'
            bt += '>'
            self.result += bt
            self.open_tags.insert(0, tag)

    def handle_endtag(self, tag, attrs):
        bracketed = '</%s>' % tag
        if tag not in self.permitted_tags:
            if self.strip_disallowed:
                self.in_disallowed = False
            else:
                self.result += xssescape(bracketed)
        elif tag in self.open_tags:
            self.result += bracketed
            self.open_tags.remove(tag)

    def unknown_starttag(self, tag, attributes):
        self.handle_starttag(tag, None, attributes)

    def unknown_endtag(self, tag):
        self.handle_endtag(tag, None)

    def url_is_acceptable(self, url):
        """
        Accepts relative, absolute, and mailto urls
        """

        parsed = urlparse(url)
        return (parsed[0] in self.allowed_schemes and '.' in parsed[1]) \
            or (parsed[0] in self.allowed_schemes and '@' in parsed[2]) \
            or (parsed[0] == '' and parsed[2].startswith('/'))

    def strip(self, rawstring, escape=True):
        """
        Returns the argument stripped of potentially harmful
        HTML or Javascript code

        @type escape: boolean
        @param escape: If True (default) it escapes the potentially harmful
          content, otherwise remove it
        """

        if not isinstance(rawstring, str):
            return str(rawstring)
        for tag in self.requires_no_close:
            rawstring = rawstring.replace("<%s/>" % tag, "<%s />" % tag)
        if not escape:
            self.strip_disallowed = True
        self.result = ''
        self.feed(rawstring)
        for endtag in self.open_tags:
            if endtag not in self.requires_no_close:
                self.result += '</%s>' % endtag
        return self.result

    def xtags(self):
        """
        Returns a printable string informing the user which tags are allowed
        """

        tg = ''
        for x in sorted(self.permitted_tags):
            tg += '<' + x
            if x in self.allowed_attributes:
                for y in self.allowed_attributes[x]:
                    tg += ' %s=""' % y
            tg += '> '
        return xssescape(tg.strip())


def sanitize(text, permitted_tags=[
        'a',
        'b',
        'blockquote',
        'br/',
        'i',
        'li',
        'ol',
        'ul',
        'p',
        'cite',
        'code',
        'pre',
        'img/',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'table', 'tbody', 'thead', 'tfoot', 'tr', 'td', 'div',
        'strong', 'span',
],
    allowed_attributes={
        'a': ['href', 'title'],
        'img': ['src', 'alt'],
        'blockquote': ['type'],
        'td': ['colspan'],
    },
        escape=True):
    if not isinstance(text, basestring):
        return str(text)
    return XssCleaner(permitted_tags=permitted_tags,
                      allowed_attributes=allowed_attributes).strip(text, escape)

########NEW FILE########
__FILENAME__ = serializers
"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""
import datetime
import decimal
from storage import Storage
from html import TAG, XmlComponent
from html import xmlescape

try:
    import simplejson as json_parser                # try external module
except ImportError:
    try:
        import json as json_parser                  # try stdlib (Python >= 2.6)
    except:
        import contrib.simplejson as json_parser    # fallback to pure-Python module

have_yaml = True
try:
    import yaml as yamlib
except ImportError:
    have_yaml = False

def cast_keys(o, cast=str, encoding="utf-8"):
    """ Builds a new object with <cast> type keys

    Arguments:
        o is the object input
        cast (defaults to str) is an object type or function
              which supports conversion such as:

              >>> converted = cast(o)

        encoding (defaults to utf-8) is the encoding for unicode
                 keys. This is not used for custom cast functions

    Use this funcion if you are in Python < 2.6.5
    This avoids syntax errors when unpacking dictionary arguments.
    """

    if isinstance(o, (dict, Storage)):
        if isinstance(o, dict):
            newobj = dict()
        else:
            newobj = Storage()

        for k, v in o.items():
            if (cast == str) and isinstance(k, unicode):
                key = k.encode(encoding)
            else:
                key = cast(k)
            if isinstance(v, (dict, Storage)):
                value = cast_keys(v, cast=cast, encoding=encoding)
            else:
                value = v
            newobj[key] = value
    else:
        raise TypeError("Cannot cast keys: %s is not supported" % \
                        type(o))
    return newobj

def loads_json(o, unicode_keys=True, **kwargs):
    # deserialize a json string
    result = json_parser.loads(o, **kwargs)
    if not unicode_keys:
        # filter non-str keys in dictionary objects
        result = cast_keys(result,
                           encoding=kwargs.get("encoding", "utf-8"))
    return result

def custom_json(o):
    if hasattr(o, 'custom_json') and callable(o.custom_json):
        return o.custom_json()
    if isinstance(o, (datetime.date,
                      datetime.datetime,
                      datetime.time)):
        return o.isoformat()[:19].replace('T', ' ')
    elif isinstance(o, (int, long)):
        return int(o)
    elif isinstance(o, decimal.Decimal):
        return str(o)
    elif type(o).__name__ == 'lazyT':
        return str(o)
    elif isinstance(o, XmlComponent):
        return str(o)
    elif hasattr(o, 'as_list') and callable(o.as_list):
        return o.as_list()
    elif hasattr(o, 'as_dict') and callable(o.as_dict):
        return o.as_dict()
    else:
        raise TypeError(repr(o) + " is not JSON serializable")


def xml_rec(value, key, quote=True):
    if hasattr(value, 'custom_xml') and callable(value.custom_xml):
        return value.custom_xml()
    elif isinstance(value, (dict, Storage)):
        return TAG[key](*[TAG[k](xml_rec(v, '', quote))
                          for k, v in value.items()])
    elif isinstance(value, list):
        return TAG[key](*[TAG.item(xml_rec(item, '', quote)) for item in value])
    elif hasattr(value, 'as_list') and callable(value.as_list):
        return str(xml_rec(value.as_list(), '', quote))
    elif hasattr(value, 'as_dict') and callable(value.as_dict):
        return str(xml_rec(value.as_dict(), '', quote))
    else:
        return xmlescape(value, quote)


def xml(value, encoding='UTF-8', key='document', quote=True):
    return ('<?xml version="1.0" encoding="%s"?>' % encoding) + str(xml_rec(value, key, quote))


def json(value, default=custom_json):
    # replace JavaScript incompatible spacing
    # http://timelessrepo.com/json-isnt-a-javascript-subset
    return json_parser.dumps(value,
        default=default).replace(ur'\u2028',
                                 '\\u2028').replace(ur'\2029',
                                                    '\\u2029')

def csv(value):
    return ''


def ics(events, title=None, link=None, timeshift=0, calname=True,
        **ignored):
    import datetime
    title = title or '(unknown)'
    if link and not callable(link):
        link = lambda item, prefix=link: prefix.replace(
            '[id]', str(item['id']))
    s = 'BEGIN:VCALENDAR'
    s += '\nVERSION:2.0'
    if not calname is False:
        s += '\nX-WR-CALNAME:%s' % (calname or title)
    s += '\nSUMMARY:%s' % title
    s += '\nPRODID:Generated by web2py'
    s += '\nCALSCALE:GREGORIAN'
    s += '\nMETHOD:PUBLISH'
    for item in events:
        s += '\nBEGIN:VEVENT'
        s += '\nUID:%s' % item['id']
        if link:
            s += '\nURL:%s' % link(item)
        shift = datetime.timedelta(seconds=3600 * timeshift)
        start = item['start_datetime'] + shift
        stop = item['stop_datetime'] + shift
        s += '\nDTSTART:%s' % start.strftime('%Y%m%dT%H%M%S')
        s += '\nDTEND:%s' % stop.strftime('%Y%m%dT%H%M%S')
        s += '\nSUMMARY:%s' % item['title']
        s += '\nEND:VEVENT'
    s += '\nEND:VCALENDAR'
    return s


def rss(feed):
    import contrib.rss2 as rss2
    if not 'entries' in feed and 'items' in feed:
        feed['entries'] = feed['items']
    now = datetime.datetime.now()
    rss = rss2.RSS2(title=str(feed.get('title', '(notitle)').encode('utf-8', 'replace')),
                    link=str(feed.get('link', None).encode('utf-8', 'replace')),
                    description=str(feed.get('description', '').encode('utf-8', 'replace')),
                    lastBuildDate=feed.get('created_on', now),
                    items=[rss2.RSSItem(
                           title=str(entry.get('title', '(notitle)').encode('utf-8', 'replace')),
                           link=str(entry.get('link', None).encode('utf-8', 'replace')),
                           description=str(entry.get('description', '').encode('utf-8', 'replace')),
                           pubDate=entry.get('created_on', now)
                           ) for entry in feed.get('entries', [])])
    return rss.to_xml(encoding='utf-8')


def yaml(data):
    if have_yaml:
        return yamlib.dump(data)
    else: raise ImportError("No YAML serializer available")

def loads_yaml(data):
    if have_yaml:
        return yamlib.load(data)
    else: raise ImportError("No YAML serializer available")

########NEW FILE########
__FILENAME__ = sqlhtml
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Holds:

- SQLFORM: provide a form for a table (with/without record)
- SQLTABLE: provides a table for a set of records
- form_factory: provides a SQLFORM for an non-db backed table

"""
try:
    from urlparse import parse_qs as psq
except ImportError:
    from cgi import parse_qs as psq
import os
import copy
from http import HTTP
from html import XmlComponent
from html import XML, SPAN, TAG, A, DIV, CAT, UL, LI, TEXTAREA, BR, IMG, SCRIPT
from html import FORM, INPUT, LABEL, OPTION, SELECT
from html import TABLE, THEAD, TBODY, TR, TD, TH, STYLE
from html import URL, truncate_string, FIELDSET
from dal import DAL, Field, Table, Row, CALLABLETYPES, smart_query, \
    bar_encode, Reference, REGEX_TABLE_DOT_FIELD
from storage import Storage
from utils import md5_hash
from validators import IS_EMPTY_OR, IS_NOT_EMPTY, IS_LIST_OF, IS_DATE, \
    IS_DATETIME, IS_INT_IN_RANGE, IS_FLOAT_IN_RANGE, IS_STRONG

import serializers
import datetime
import urllib
import re
import cStringIO
from globals import current
from http import redirect
import inspect

try:
    import settings
    is_gae = settings.global_settings.web2py_runtime_gae
except ImportError:
    is_gae = False



table_field = re.compile('[\w_]+\.[\w_]+')
widget_class = re.compile('^\w*')


def trap_class(_class=None, trap=True):
    return (trap and 'w2p_trap' or '') + (_class and ' ' + _class or '')


def represent(field, value, record):
    f = field.represent
    if not callable(f):
        return str(value)
    n = f.func_code.co_argcount - len(f.func_defaults or [])
    if getattr(f, 'im_self', None):
        n -= 1
    if n == 1:
        return f(value)
    elif n == 2:
        return f(value, record)
    else:
        raise RuntimeError("field representation must take 1 or 2 args")


def safe_int(x):
    try:
        return int(x)
    except ValueError:
        return 0


def safe_float(x):
    try:
        return float(x)
    except ValueError:
        return 0


def show_if(cond):
    if not cond:
        return None
    base = "%s_%s" % (cond.first.tablename, cond.first.name)
    if ((cond.op.__name__ == 'EQ' and cond.second == True) or
        (cond.op.__name__ == 'NE' and cond.second == False)):
        return base,":checked"
    if ((cond.op.__name__ == 'EQ' and cond.second == False) or
        (cond.op.__name__ == 'NE' and cond.second == True)):
        return base,":not(:checked)"
    if cond.op.__name__ == 'EQ':
        return base,"[value='%s']" % cond.second
    if cond.op.__name__ == 'NE':
        return base,"[value!='%s']" % cond.second
    if cond.op.__name__ == 'CONTAINS':
        return base,"[value~='%s']" % cond.second
    if cond.op.__name__ == 'BELONGS' and isinstance(cond.second,(list,tuple)):
        return base,','.join("[value='%s']" % (v) for v in cond.second)
    raise RuntimeError("Not Implemented Error")


class FormWidget(object):
    """
    helper for SQLFORM to generate form input fields
    (widget), related to the fieldtype
    """

    _class = 'generic-widget'

    @classmethod
    def _attributes(cls, field,
                    widget_attributes, **attributes):
        """
        helper to build a common set of attributes

        :param field: the field involved,
                      some attributes are derived from this
        :param widget_attributes:  widget related attributes
        :param attributes: any other supplied attributes
        """
        attr = dict(
            _id='%s_%s' % (field.tablename, field.name),
            _class=cls._class or
                widget_class.match(str(field.type)).group(),
            _name=field.name,
            requires=field.requires,
        )
        if getattr(field,'show_if',None):
            trigger, cond = show_if(field.show_if)
            attr['_data-show-trigger'] = trigger
            attr['_data-show-if'] = cond
        attr.update(widget_attributes)
        attr.update(attributes)
        return attr

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates the widget for the field.

        When serialized, will provide an INPUT tag:

        - id = tablename_fieldname
        - class = field.type
        - name = fieldname

        :param field: the field needing the widget
        :param value: value
        :param attributes: any other attributes to be applied
        """

        raise NotImplementedError


class StringWidget(FormWidget):
    _class = 'string'

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates an INPUT text tag.

        see also: :meth:`FormWidget.widget`
        """

        default = dict(
            _type='text',
            value=(not value is None and str(value)) or '',
        )
        attr = cls._attributes(field, default, **attributes)

        return INPUT(**attr)


class IntegerWidget(StringWidget):
    _class = 'integer'


class DoubleWidget(StringWidget):
    _class = 'double'


class DecimalWidget(StringWidget):
    _class = 'decimal'


class TimeWidget(StringWidget):
    _class = 'time'


class DateWidget(StringWidget):
    _class = 'date'

class DatetimeWidget(StringWidget):
    _class = 'datetime'

class TextWidget(FormWidget):
    _class = 'text'

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a TEXTAREA tag.

        see also: :meth:`FormWidget.widget`
        """

        default = dict(value=value)
        attr = cls._attributes(field, default, **attributes)
        return TEXTAREA(**attr)

class JSONWidget(FormWidget):
    _class = 'json'

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a TEXTAREA for JSON notation.

        see also: :meth:`FormWidget.widget`
        """
        if not isinstance(value, basestring):
            if value is not None:
                value = serializers.json(value)
        default = dict(value=value)
        attr = cls._attributes(field, default, **attributes)
        return TEXTAREA(**attr)

class BooleanWidget(FormWidget):
    _class = 'boolean'

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates an INPUT checkbox tag.

        see also: :meth:`FormWidget.widget`
        """

        default = dict(_type='checkbox', value=value)
        attr = cls._attributes(field, default,
                               **attributes)
        return INPUT(**attr)


class OptionsWidget(FormWidget):

    @staticmethod
    def has_options(field):
        """
        checks if the field has selectable options

        :param field: the field needing checking
        :returns: True if the field has options
        """

        return hasattr(field.requires, 'options')

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a SELECT tag, including OPTIONs (only 1 option allowed)

        see also: :meth:`FormWidget.widget`
        """
        default = dict(value=value)
        attr = cls._attributes(field, default,
                               **attributes)
        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires:
            if hasattr(requires[0], 'options'):
                options = requires[0].options()
            else:
                raise SyntaxError(
                    'widget cannot determine options of %s' % field)
        opts = [OPTION(v, _value=k) for (k, v) in options]
        return SELECT(*opts, **attr)


class ListWidget(StringWidget):

    @classmethod
    def widget(cls, field, value, **attributes):
        _id = '%s_%s' % (field.tablename, field.name)
        _name = field.name
        if field.type == 'list:integer':
            _class = 'integer'
        else:
            _class = 'string'
        requires = field.requires if isinstance(
            field.requires, (IS_NOT_EMPTY, IS_LIST_OF)) else None
        nvalue = value or ['']
        items = [LI(INPUT(_id=_id, _class=_class, _name=_name,
                          value=v, hideerror=k < len(nvalue) - 1,
                          requires=requires),
                    **attributes) for (k, v) in enumerate(nvalue)]
        attributes['_id'] = _id + '_grow_input'
        attributes['_style'] = 'list-style:none'
        attributes['_class'] = 'w2p_list'
        return TAG[''](UL(*items, **attributes))


class MultipleOptionsWidget(OptionsWidget):

    @classmethod
    def widget(cls, field, value, size=5, **attributes):
        """
        generates a SELECT tag, including OPTIONs (multiple options allowed)

        see also: :meth:`FormWidget.widget`

        :param size: optional param (default=5) to indicate how many rows must
            be shown
        """

        attributes.update(_size=size, _multiple=True)

        return OptionsWidget.widget(field, value, **attributes)


class RadioWidget(OptionsWidget):

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a TABLE tag, including INPUT radios (only 1 option allowed)

        see also: :meth:`FormWidget.widget`
        """

        if isinstance(value, (list,tuple)):
            value = str(value[0])
        else:
            value = str(value)


        attr = cls._attributes(field, {}, **attributes)
        attr['_class'] = attr.get('_class', 'web2py_radiowidget')

        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires:
            if hasattr(requires[0], 'options'):
                options = requires[0].options()
            else:
                raise SyntaxError('widget cannot determine options of %s'
                                  % field)
        options = [(k, v) for k, v in options if str(v)]
        opts = []
        cols = attributes.get('cols', 1)
        totals = len(options)
        mods = totals % cols
        rows = totals / cols
        if mods:
            rows += 1

        #widget style
        wrappers = dict(
            table=(TABLE, TR, TD),
            ul=(DIV, UL, LI),
            divs=(CAT, DIV, DIV)
        )
        parent, child, inner = wrappers[attributes.get('style', 'table')]

        for r_index in range(rows):
            tds = []
            for k, v in options[r_index * cols:(r_index + 1) * cols]:
                checked = {'_checked': 'checked'} if k == value else {}
                tds.append(inner(INPUT(_type='radio',
                                       _id='%s%s' % (field.name, k),
                                       _name=field.name,
                                       requires=attr.get('requires', None),
                                       hideerror=True, _value=k,
                                       value=value,
                                       **checked),
                                 LABEL(v, _for='%s%s' % (field.name, k))))
            opts.append(child(tds))

        if opts:
            opts[-1][0][0]['hideerror'] = False
        return parent(*opts, **attr)


class CheckboxesWidget(OptionsWidget):

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a TABLE tag, including INPUT checkboxes (multiple allowed)

        see also: :meth:`FormWidget.widget`
        """

        # was values = re.compile('[\w\-:]+').findall(str(value))
        if isinstance(value, (list, tuple)):
            values = [str(v) for v in value]
        else:
            values = [str(value)]

        attr = cls._attributes(field, {}, **attributes)
        attr['_class'] = attr.get('_class', 'web2py_checkboxeswidget')

        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires and hasattr(requires[0], 'options'):
            options = requires[0].options()
        else:
            raise SyntaxError('widget cannot determine options of %s'
                              % field)

        options = [(k, v) for k, v in options if k != '']
        opts = []
        cols = attributes.get('cols', 1)
        totals = len(options)
        mods = totals % cols
        rows = totals / cols
        if mods:
            rows += 1

        #widget style
        wrappers = dict(
            table=(TABLE, TR, TD),
            ul=(DIV, UL, LI),
            divs=(CAT, DIV, DIV)
        )
        parent, child, inner = wrappers[attributes.get('style', 'table')]

        for r_index in range(rows):
            tds = []
            for k, v in options[r_index * cols:(r_index + 1) * cols]:
                if k in values:
                    r_value = k
                else:
                    r_value = []
                tds.append(inner(INPUT(_type='checkbox',
                                       _id='%s%s' % (field.name, k),
                                       _name=field.name,
                                       requires=attr.get('requires', None),
                                       hideerror=True, _value=k,
                                       value=r_value),
                                 LABEL(v, _for='%s%s' % (field.name, k))))
            opts.append(child(tds))

        if opts:
            opts.append(
                INPUT(requires=attr.get('requires', None),
                      _style="display:none;",
                      _disabled="disabled",
                      _name=field.name,
                      hideerror=False))
        return parent(*opts, **attr)


class PasswordWidget(FormWidget):
    _class = 'password'

    DEFAULT_PASSWORD_DISPLAY = 8 * ('*')

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a INPUT password tag.
        If a value is present it will be shown as a number of '*', not related
        to the length of the actual value.

        see also: :meth:`FormWidget.widget`
        """
        # detect if attached a IS_STRONG with entropy
        default = dict(
            _type='password',
            _value=(value and cls.DEFAULT_PASSWORD_DISPLAY) or '',
        )
        attr = cls._attributes(field, default, **attributes)

        # deal with entropy check!
        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        is_strong = [r for r in requires if isinstance(r, IS_STRONG)]
        if is_strong:
            attr['_data-w2p_entropy'] = is_strong[0].entropy if is_strong[0].entropy else "null"
        # end entropy check
        output = INPUT(**attr)
        return output


class UploadWidget(FormWidget):
    _class = 'upload'

    DEFAULT_WIDTH = '150px'
    ID_DELETE_SUFFIX = '__delete'
    GENERIC_DESCRIPTION = 'file'
    DELETE_FILE = 'delete'

    @classmethod
    def widget(cls, field, value, download_url=None, **attributes):
        """
        generates a INPUT file tag.

        Optionally provides an A link to the file, including a checkbox so
        the file can be deleted.
        All is wrapped in a DIV.

        see also: :meth:`FormWidget.widget`

        :param download_url: Optional URL to link to the file (default = None)
        """

        default = dict(_type='file',)
        attr = cls._attributes(field, default, **attributes)

        inp = INPUT(**attr)

        if download_url and value:
            if callable(download_url):
                url = download_url(value)
            else:
                url = download_url + '/' + value
            (br, image) = ('', '')
            if UploadWidget.is_image(value):
                br = BR()
                image = IMG(_src=url, _width=cls.DEFAULT_WIDTH)

            requires = attr["requires"]
            if requires == [] or isinstance(requires, IS_EMPTY_OR):
                inp = DIV(inp,
                          SPAN('[',
                               A(current.T(
                                UploadWidget.GENERIC_DESCRIPTION), _href=url),
                               '|',
                               INPUT(_type='checkbox',
                                     _name=field.name + cls.ID_DELETE_SUFFIX,
                                     _id=field.name + cls.ID_DELETE_SUFFIX),
                               LABEL(current.T(cls.DELETE_FILE),
                                     _for=field.name + cls.ID_DELETE_SUFFIX,
                                     _style='display:inline'),
                               ']', _style='white-space:nowrap'),
                          br, image)
            else:
                inp = DIV(inp,
                          SPAN('[',
                               A(cls.GENERIC_DESCRIPTION, _href=url),
                               ']', _style='white-space:nowrap'),
                          br, image)
        return inp

    @classmethod
    def represent(cls, field, value, download_url=None):
        """
        how to represent the file:

        - with download url and if it is an image: <A href=...><IMG ...></A>
        - otherwise with download url: <A href=...>file</A>
        - otherwise: file

        :param field: the field
        :param value: the field value
        :param download_url: url for the file download (default = None)
        """

        inp = cls.GENERIC_DESCRIPTION

        if download_url and value:
            if callable(download_url):
                url = download_url(value)
            else:
                url = download_url + '/' + value
            if cls.is_image(value):
                inp = IMG(_src=url, _width=cls.DEFAULT_WIDTH)
            inp = A(inp, _href=url)

        return inp

    @staticmethod
    def is_image(value):
        """
        Tries to check if the filename provided references to an image

        Checking is based on filename extension. Currently recognized:
           gif, png, jp(e)g, bmp

        :param value: filename
        """

        extension = value.split('.')[-1].lower()
        if extension in ['gif', 'png', 'jpg', 'jpeg', 'bmp']:
            return True
        return False


class AutocompleteWidget(object):
    _class = 'string'

    def __init__(self, request, field, id_field=None, db=None,
                 orderby=None, limitby=(0, 10), distinct=False,
                 keyword='_autocomplete_%(tablename)s_%(fieldname)s',
                 min_length=2, help_fields=None, help_string=None):

        self.help_fields = help_fields or []
        self.help_string = help_string
        if self.help_fields and not self.help_string:
            self.help_string = ' '.join('%%(%s)s'%f.name
                                        for f in self.help_fields)

        self.request = request
        self.keyword = keyword % dict(tablename=field.tablename,
                                      fieldname=field.name)
        self.db = db or field._db
        self.orderby = orderby
        self.limitby = limitby
        self.distinct = distinct
        self.min_length = min_length
        self.fields = [field]
        if id_field:
            self.is_reference = True
            self.fields.append(id_field)
        else:
            self.is_reference = False
        if hasattr(request, 'application'):
            self.url = URL(args=request.args)
            self.callback()
        else:
            self.url = request

    def callback(self):
        if self.keyword in self.request.vars:
            field = self.fields[0]
            if is_gae:
                rows = self.db(field.__ge__(self.request.vars[self.keyword]) & field.__lt__(self.request.vars[self.keyword] + u'\ufffd')).select(orderby=self.orderby, limitby=self.limitby, *(self.fields+self.help_fields))
            else:
                rows = self.db(field.like(self.request.vars[self.keyword] + '%')).select(orderby=self.orderby, limitby=self.limitby, distinct=self.distinct, *(self.fields+self.help_fields))
            if rows:
                if self.is_reference:
                    id_field = self.fields[1]
                    if self.help_fields:
                        options = [OPTION(
                            self.help_string % dict([(h.name, s[h.name]) for h in self.fields[:1] + self.help_fields]),
                                   _value=s[id_field.name], _selected=(k == 0)) for k, s in enumerate(rows)]
                    else:
                        options = [OPTION(
                            s[field.name], _value=s[id_field.name],
                            _selected=(k == 0)) for k, s in enumerate(rows)]
                    raise HTTP(
                        200, SELECT(_id=self.keyword, _class='autocomplete',
                                    _size=len(rows), _multiple=(len(rows) == 1),
                                    *options).xml())
                else:
                    raise HTTP(
                        200, SELECT(_id=self.keyword, _class='autocomplete',
                                    _size=len(rows), _multiple=(len(rows) == 1),
                                    *[OPTION(s[field.name],
                                             _selected=(k == 0))
                                      for k, s in enumerate(rows)]).xml())
            else:
                raise HTTP(200, '')

    def __call__(self, field, value, **attributes):
        default = dict(
            _type='text',
            value=(not value is None and str(value)) or '',
        )
        attr = StringWidget._attributes(field, default, **attributes)
        div_id = self.keyword + '_div'
        attr['_autocomplete'] = 'off'
        if self.is_reference:
            key2 = self.keyword + '_aux'
            key3 = self.keyword + '_auto'
            attr['_class'] = 'string'
            name = attr['_name']
            if 'requires' in attr:
                del attr['requires']
            attr['_name'] = key2
            value = attr['value']
            record = self.db(
                self.fields[1] == value).select(self.fields[0]).first()
            attr['value'] = record and record[self.fields[0].name]
            attr['_onblur'] = "jQuery('#%(div_id)s').delay(1000).fadeOut('slow');" % \
                dict(div_id=div_id, u='F' + self.keyword)
            attr['_onkeyup'] = "jQuery('#%(key3)s').val('');var e=event.which?event.which:event.keyCode; function %(u)s(){jQuery('#%(id)s').val(jQuery('#%(key)s :selected').text());jQuery('#%(key3)s').val(jQuery('#%(key)s').val())}; if(e==39) %(u)s(); else if(e==40) {if(jQuery('#%(key)s option:selected').next().length)jQuery('#%(key)s option:selected').attr('selected',null).next().attr('selected','selected'); %(u)s();} else if(e==38) {if(jQuery('#%(key)s option:selected').prev().length)jQuery('#%(key)s option:selected').attr('selected',null).prev().attr('selected','selected'); %(u)s();} else if(jQuery('#%(id)s').val().length>=%(min_length)s) jQuery.get('%(url)s?%(key)s='+encodeURIComponent(jQuery('#%(id)s').val()),function(data){if(data=='')jQuery('#%(key3)s').val('');else{jQuery('#%(id)s').next('.error').hide();jQuery('#%(div_id)s').html(data).show().focus();jQuery('#%(div_id)s select').css('width',jQuery('#%(id)s').css('width'));jQuery('#%(key3)s').val(jQuery('#%(key)s').val());jQuery('#%(key)s').change(%(u)s);jQuery('#%(key)s').click(%(u)s);};}); else jQuery('#%(div_id)s').fadeOut('slow');" % \
                dict(url=self.url, min_length=self.min_length,
                     key=self.keyword, id=attr['_id'], key2=key2, key3=key3,
                     name=name, div_id=div_id, u='F' + self.keyword)
            if self.min_length == 0:
                attr['_onfocus'] = attr['_onkeyup']
            return TAG[''](INPUT(**attr), INPUT(_type='hidden', _id=key3, _value=value,
                                                _name=name, requires=field.requires),
                           DIV(_id=div_id, _style='position:absolute;'))
        else:
            attr['_name'] = field.name
            attr['_onblur'] = "jQuery('#%(div_id)s').delay(1000).fadeOut('slow');" % \
                dict(div_id=div_id, u='F' + self.keyword)
            attr['_onkeyup'] = "var e=event.which?event.which:event.keyCode; function %(u)s(){jQuery('#%(id)s').val(jQuery('#%(key)s').val())}; if(e==39) %(u)s(); else if(e==40) {if(jQuery('#%(key)s option:selected').next().length)jQuery('#%(key)s option:selected').attr('selected',null).next().attr('selected','selected'); %(u)s();} else if(e==38) {if(jQuery('#%(key)s option:selected').prev().length)jQuery('#%(key)s option:selected').attr('selected',null).prev().attr('selected','selected'); %(u)s();} else if(jQuery('#%(id)s').val().length>=%(min_length)s) jQuery.get('%(url)s?%(key)s='+encodeURIComponent(jQuery('#%(id)s').val()),function(data){jQuery('#%(id)s').next('.error').hide();jQuery('#%(div_id)s').html(data).show().focus();jQuery('#%(div_id)s select').css('width',jQuery('#%(id)s').css('width'));jQuery('#%(key)s').change(%(u)s);jQuery('#%(key)s').click(%(u)s);}); else jQuery('#%(div_id)s').fadeOut('slow');" % \
                dict(url=self.url, min_length=self.min_length,
                     key=self.keyword, id=attr['_id'], div_id=div_id, u='F' + self.keyword)
            if self.min_length == 0:
                attr['_onfocus'] = attr['_onkeyup']
            return TAG[''](INPUT(**attr), DIV(_id=div_id, _style='position:absolute;'))


def formstyle_table3cols(form, fields):
    ''' 3 column table - default '''
    table = TABLE()
    for id, label, controls, help in fields:
        _help = TD(help, _class='w2p_fc')
        _controls = TD(controls, _class='w2p_fw')
        _label = TD(label, _class='w2p_fl')
        table.append(TR(_label, _controls, _help, _id=id))
    return table


def formstyle_table2cols(form, fields):
    ''' 2 column table '''
    table = TABLE()
    for id, label, controls, help in fields:
        _help = TD(help, _class='w2p_fc', _width='50%')
        _controls = TD(controls, _class='w2p_fw', _colspan='2')
        _label = TD(label, _class='w2p_fl', _width='50%')
        table.append(TR(_label, _help, _id=id + '1', _class='even'))
        table.append(TR(_controls, _id=id + '2', _class='odd'))
    return table


def formstyle_divs(form, fields):
    ''' divs only '''
    table = FIELDSET()
    for id, label, controls, help in fields:
        _help = DIV(help, _class='w2p_fc')
        _controls = DIV(controls, _class='w2p_fw')
        _label = DIV(label, _class='w2p_fl')
        table.append(DIV(_label, _controls, _help, _id=id))
    return table


def formstyle_inline(form, fields):
    ''' divs only '''
    if len(fields) != 2:
        raise RuntimeError("Not possible")
    id, label, controls, help = fields[0]
    submit_button = fields[1][2]
    return CAT(DIV(controls, _style='display:inline'),
               submit_button)


def formstyle_ul(form, fields):
    ''' unordered list '''
    table = UL()
    for id, label, controls, help in fields:
        _help = DIV(help, _class='w2p_fc')
        _controls = DIV(controls, _class='w2p_fw')
        _label = DIV(label, _class='w2p_fl')
        table.append(LI(_label, _controls, _help, _id=id))
    return table


def formstyle_bootstrap(form, fields):
    ''' bootstrap format form layout '''
    form.add_class('form-horizontal')
    parent = FIELDSET()
    for id, label, controls, help in fields:
        # wrappers
        _help = SPAN(help, _class='help-block')
        # embed _help into _controls
        _controls = DIV(controls, _help, _class='controls')
        # submit unflag by default
        _submit = False

        if isinstance(controls, INPUT):
            controls.add_class('span4')
            if controls['_type'] == 'submit':
                # flag submit button
                _submit = True
                controls['_class'] = 'btn btn-primary'
            if controls['_type'] == 'file':
                controls['_class'] = 'input-file'

        # For password fields, which are wrapped in a CAT object.
        if isinstance(controls, CAT) and isinstance(controls[0], INPUT):
            controls[0].add_class('span4')

        if isinstance(controls, SELECT):
            controls.add_class('span4')

        if isinstance(controls, TEXTAREA):
            controls.add_class('span4')

        if isinstance(label, LABEL):
            label['_class'] = 'control-label'

        if _submit:
            # submit button has unwrapped label and controls, different class
            parent.append(DIV(label, controls, _class='form-actions', _id=id))
            # unflag submit (possible side effect)
            _submit = False
        else:
            # unwrapped label
            parent.append(DIV(label, _controls, _class='control-group', _id=id))
    return parent


class SQLFORM(FORM):

    """
    SQLFORM is used to map a table (and a current record) into an HTML form

    given a SQLTable stored in db.table

    generates an insert form::

        SQLFORM(db.table)

    generates an update form::

        record=db.table[some_id]
        SQLFORM(db.table, record)

    generates an update with a delete button::

        SQLFORM(db.table, record, deletable=True)

    if record is an int::

        record=db.table[record]

    optional arguments:

    :param fields: a list of fields that should be placed in the form,
        default is all.
    :param labels: a dictionary with labels for each field, keys are the field
        names.
    :param col3: a dictionary with content for an optional third column
            (right of each field). keys are field names.
    :param linkto: the URL of a controller/function to access referencedby
        records
            see controller appadmin.py for examples
    :param upload: the URL of a controller/function to download an uploaded file
            see controller appadmin.py for examples

    any named optional attribute is passed to the <form> tag
            for example _class, _id, _style, _action, _method, etc.

    """

    # usability improvements proposal by fpp - 4 May 2008 :
    # - correct labels (for points to field id, not field name)
    # - add label for delete checkbox
    # - add translatable label for record ID
    # - add third column to right of fields, populated from the col3 dict

    widgets = Storage(dict(
        string=StringWidget,
        text=TextWidget,
        json=JSONWidget,
        password=PasswordWidget,
        integer=IntegerWidget,
        double=DoubleWidget,
        decimal=DecimalWidget,
        time=TimeWidget,
        date=DateWidget,
        datetime=DatetimeWidget,
        upload=UploadWidget,
        boolean=BooleanWidget,
        blob=None,
        options=OptionsWidget,
        multiple=MultipleOptionsWidget,
        radio=RadioWidget,
        checkboxes=CheckboxesWidget,
        autocomplete=AutocompleteWidget,
        list=ListWidget,
    ))

    formstyles = Storage(dict(
        table3cols=formstyle_table3cols,
        table2cols=formstyle_table2cols,
        divs=formstyle_divs,
        ul=formstyle_ul,
        bootstrap=formstyle_bootstrap,
        inline=formstyle_inline,
    ))

    FIELDNAME_REQUEST_DELETE = 'delete_this_record'
    FIELDKEY_DELETE_RECORD = 'delete_record'
    ID_LABEL_SUFFIX = '__label'
    ID_ROW_SUFFIX = '__row'

    def assert_status(self, status, request_vars):
        if not status and self.record and self.errors:
            ### if there are errors in update mode
            # and some errors refers to an already uploaded file
            # delete error if
            # - user not trying to upload a new file
            # - there is existing file and user is not trying to delete it
            # this is because removing the file may not pass validation
            for key in self.errors.keys():
                if key in self.table \
                        and self.table[key].type == 'upload' \
                        and request_vars.get(key, None) in (None, '') \
                        and self.record[key] \
                        and not key + UploadWidget.ID_DELETE_SUFFIX in request_vars:
                    del self.errors[key]
            if not self.errors:
                status = True
        return status

    def __init__(
        self,
        table,
        record=None,
        deletable=False,
        linkto=None,
        upload=None,
        fields=None,
        labels=None,
        col3={},
        submit_button='Submit',
        delete_label='Check to delete',
        showid=True,
        readonly=False,
        comments=True,
        keepopts=[],
        ignore_rw=False,
        record_id=None,
        formstyle='table3cols',
        buttons=['submit'],
        separator=': ',
        **attributes
    ):
        """
        SQLFORM(db.table,
               record=None,
               fields=['name'],
               labels={'name': 'Your name'},
               linkto=URL(f='table/db/')
        """
        T = current.T

        self.ignore_rw = ignore_rw
        self.formstyle = formstyle
        self.readonly = readonly
        # Default dbio setting
        self.detect_record_change = None

        nbsp = XML('&nbsp;')  # Firefox2 does not display fields with blanks
        FORM.__init__(self, *[], **attributes)
        ofields = fields
        keyed = hasattr(table, '_primarykey')  # for backward compatibility

        # if no fields are provided, build it from the provided table
        # will only use writable or readable fields, unless forced to ignore
        if fields is None:
            fields = [f.name for f in table if
                      (ignore_rw or f.writable or f.readable) and
                      (readonly or not f.compute)]
        self.fields = fields

        # make sure we have an id
        if self.fields[0] != table.fields[0] and \
                isinstance(table, Table) and not keyed:
            self.fields.insert(0, table.fields[0])

        self.table = table

        # try to retrieve the indicated record using its id
        # otherwise ignore it
        if record and isinstance(record, (int, long, str, unicode)):
            if not str(record).isdigit():
                raise HTTP(404, "Object not found")
            record = table._db(table._id == record).select().first()
            if not record:
                raise HTTP(404, "Object not found")
        self.record = record

        self.record_id = record_id
        if keyed:
            self.record_id = dict([(k, record and str(record[k]) or None)
                                   for k in table._primarykey])
        self.field_parent = {}
        xfields = []
        self.fields = fields
        self.custom = Storage()
        self.custom.dspval = Storage()
        self.custom.inpval = Storage()
        self.custom.label = Storage()
        self.custom.comment = Storage()
        self.custom.widget = Storage()
        self.custom.linkto = Storage()

        # default id field name
        if not keyed:
            self.id_field_name = table._id.name
        else:
            self.id_field_name = table._primarykey[0]  # only works if one key

        sep = separator or ''

        for fieldname in self.fields:
            if fieldname.find('.') >= 0:
                continue

            field = self.table[fieldname]
            comment = None

            if comments:
                comment = col3.get(fieldname, field.comment)
            if comment is None:
                comment = ''
            self.custom.comment[fieldname] = comment

            if not labels is None and fieldname in labels:
                label = labels[fieldname]
            else:
                label = field.label
            self.custom.label[fieldname] = label

            field_id = '%s_%s' % (table._tablename, fieldname)

            label = LABEL(label, label and sep, _for=field_id,
                          _id=field_id + SQLFORM.ID_LABEL_SUFFIX)

            row_id = field_id + SQLFORM.ID_ROW_SUFFIX
            if field.type == 'id':
                self.custom.dspval.id = nbsp
                self.custom.inpval.id = ''
                widget = ''

                # store the id field name (for legacy databases)
                self.id_field_name = field.name

                if record:
                    if showid and field.name in record and field.readable:
                        v = record[field.name]
                        widget = SPAN(v, _id=field_id)
                        self.custom.dspval.id = str(v)
                        xfields.append((row_id, label, widget, comment))
                    self.record_id = str(record[field.name])
                self.custom.widget.id = widget
                continue

            if readonly and not ignore_rw and not field.readable:
                continue

            if record:
                default = record[fieldname]
            else:
                default = field.default
                if isinstance(default, CALLABLETYPES):
                    default = default()

            cond = readonly or \
                (not ignore_rw and not field.writable and field.readable)

            if default is not None and not cond:
                default = field.formatter(default)
            dspval = default
            inpval = default

            if cond:

                # ## if field.represent is available else
                # ## ignore blob and preview uploaded images
                # ## format everything else

                if field.represent:
                    inp = represent(field, default, record)
                elif field.type in ['blob']:
                    continue
                elif field.type == 'upload':
                    inp = UploadWidget.represent(field, default, upload)
                elif field.type == 'boolean':
                    inp = self.widgets.boolean.widget(
                        field, default, _disabled=True)
                else:
                    inp = field.formatter(default)
            elif field.type == 'upload':
                if field.widget:
                    inp = field.widget(field, default, upload)
                else:
                    inp = self.widgets.upload.widget(field, default, upload)
            elif field.widget:
                inp = field.widget(field, default)
            elif field.type == 'boolean':
                inp = self.widgets.boolean.widget(field, default)
                if default:
                    inpval = 'checked'
                else:
                    inpval = ''
            elif OptionsWidget.has_options(field):
                if not field.requires.multiple:
                    inp = self.widgets.options.widget(field, default)
                else:
                    inp = self.widgets.multiple.widget(field, default)
                if fieldname in keepopts:
                    inpval = TAG[''](*inp.components)
            elif field.type.startswith('list:'):
                inp = self.widgets.list.widget(field, default)
            elif field.type == 'text':
                inp = self.widgets.text.widget(field, default)
            elif field.type == 'password':
                inp = self.widgets.password.widget(field, default)
                if self.record:
                    dspval = PasswordWidget.DEFAULT_PASSWORD_DISPLAY
                else:
                    dspval = ''
            elif field.type == 'blob':
                continue
            else:
                field_type = widget_class.match(str(field.type)).group()
                field_type = field_type in self.widgets and field_type or 'string'
                inp = self.widgets[field_type].widget(field, default)

            xfields.append((row_id, label, inp, comment))
            self.custom.dspval[fieldname] = dspval if (dspval is not None) else nbsp
            self.custom.inpval[
                fieldname] = inpval if not inpval is None else ''
            self.custom.widget[fieldname] = inp

        # if a record is provided and found, as is linkto
        # build a link
        if record and linkto:
            db = linkto.split('/')[-1]
            for rfld in table._referenced_by:
                if keyed:
                    query = urllib.quote('%s.%s==%s' % (
                        db, rfld, record[rfld.type[10:].split('.')[1]]))
                else:
                    query = urllib.quote(
                        '%s.%s==%s' % (db, rfld, record[self.id_field_name]))
                lname = olname = '%s.%s' % (rfld.tablename, rfld.name)
                if ofields and not olname in ofields:
                    continue
                if labels and lname in labels:
                    lname = labels[lname]
                widget = A(lname,
                           _class='reference',
                           _href='%s/%s?query=%s' % (linkto, rfld.tablename, query))
                xfields.append(
                    (olname.replace('.', '__') + SQLFORM.ID_ROW_SUFFIX,
                     '', widget, col3.get(olname, '')))
                self.custom.linkto[olname.replace('.', '__')] = widget
#                 </block>

        # when deletable, add delete? checkbox
        self.custom.delete = self.custom.deletable = ''
        if record and deletable:
            #add secondary css class for cascade delete warning
            css = 'delete'
            for f in self.table.fields:
                on_del = self.table[f].ondelete
                if isinstance(on_del,str) and 'cascade' in on_del.lower():
                    css += ' cascade_delete'
                    break
            widget = INPUT(_type='checkbox',
                           _class=css,
                           _id=self.FIELDKEY_DELETE_RECORD,
                           _name=self.FIELDNAME_REQUEST_DELETE,
                           )
            xfields.append(
                (self.FIELDKEY_DELETE_RECORD + SQLFORM.ID_ROW_SUFFIX,
                 LABEL(
                        T(delete_label), separator,
                        _for=self.FIELDKEY_DELETE_RECORD,
                        _id=self.FIELDKEY_DELETE_RECORD + \
                            SQLFORM.ID_LABEL_SUFFIX),
                 widget,
                 col3.get(self.FIELDKEY_DELETE_RECORD, '')))
            self.custom.delete = self.custom.deletable = widget


        # when writable, add submit button
        self.custom.submit = ''
        if not readonly:
            if 'submit' in buttons:
                widget = self.custom.submit = INPUT(_type='submit',
                                                    _value=T(submit_button))
            elif buttons:
                widget = self.custom.submit = DIV(*buttons)
            if self.custom.submit:
                xfields.append(('submit_record' + SQLFORM.ID_ROW_SUFFIX,
                                '', widget, col3.get('submit_button', '')))

        # if a record is provided and found
        # make sure it's id is stored in the form
        if record:
            if not self['hidden']:
                self['hidden'] = {}
            if not keyed:
                self['hidden']['id'] = record[table._id.name]

        (begin, end) = self._xml()
        self.custom.begin = XML("<%s %s>" % (self.tag, begin))
        self.custom.end = XML("%s</%s>" % (end, self.tag))
        table = self.createform(xfields)
        self.components = [table]

    def createform(self, xfields):
        formstyle = self.formstyle
        if isinstance(formstyle, basestring):
            if formstyle in SQLFORM.formstyles:
                formstyle = SQLFORM.formstyles[formstyle]
            else:
                raise RuntimeError('formstyle not found')

        if callable(formstyle):
            # backward compatibility, 4 argument function is the old style
            args, varargs, keywords, defaults = inspect.getargspec(formstyle)
            if defaults and len(args) - len(defaults) == 4 or len(args) == 4:
                table = TABLE()
                for id, a, b, c in xfields:
                    newrows = formstyle(id, a, b, c)
                    self.field_parent[id] = getattr(b, 'parent', None) \
                        if isinstance(b,XmlComponent) else None
                    if type(newrows).__name__ != "tuple":
                        newrows = [newrows]
                    for newrow in newrows:
                        table.append(newrow)
            else:
                table = formstyle(self, xfields)
                for id, a, b, c in xfields:
                    self.field_parent[id] = getattr(b, 'parent', None) \
                        if isinstance(b,XmlComponent) else None
        else:
            raise RuntimeError('formstyle not supported')
        return table

    def accepts(
        self,
        request_vars,
        session=None,
        formname='%(tablename)s/%(record_id)s',
        keepvalues=None,
        onvalidation=None,
        dbio=True,
        hideerror=False,
        detect_record_change=False,
        **kwargs
    ):

        """
        similar FORM.accepts but also does insert, update or delete in DAL.
        but if detect_record_change == True than:
          form.record_changed = False (record is properly validated/submitted)
          form.record_changed = True (record cannot be submitted because changed)
        elseif detect_record_change == False than:
          form.record_changed = None
        """

        if keepvalues is None:
            keepvalues = True if self.record else False

        if self.readonly:
            return False

        if request_vars.__class__.__name__ == 'Request':
            request_vars = request_vars.post_vars

        keyed = hasattr(self.table, '_primarykey')

        # implement logic to detect whether record exist but has been modified
        # server side
        self.record_changed = None
        self.detect_record_change = detect_record_change
        if self.detect_record_change:
            if self.record:
                self.record_changed = False
                serialized = '|'.join(
                    str(self.record[k]) for k in self.table.fields())
                self.record_hash = md5_hash(serialized)

        # logic to deal with record_id for keyed tables
        if self.record:
            if keyed:
                formname_id = '.'.join(str(self.record[k])
                                       for k in self.table._primarykey
                                       if hasattr(self.record, k))
                record_id = dict((k, request_vars.get(k, None))
                                 for k in self.table._primarykey)
            else:
                (formname_id, record_id) = (self.record[self.id_field_name],
                                            request_vars.get('id', None))
            keepvalues = True
        else:
            if keyed:
                formname_id = 'create'
                record_id = dict([(k, None) for k in self.table._primarykey])
            else:
                (formname_id, record_id) = ('create', None)

        if not keyed and isinstance(record_id, (list, tuple)):
            record_id = record_id[0]

        if formname:
            formname = formname % dict(tablename=self.table._tablename,
                                       record_id=formname_id)

        # ## THIS IS FOR UNIQUE RECORDS, read IS_NOT_IN_DB

        for fieldname in self.fields:
            field = self.table[fieldname]
            requires = field.requires or []
            if not isinstance(requires, (list, tuple)):
                requires = [requires]
            [item.set_self_id(self.record_id) for item in requires
             if hasattr(item, 'set_self_id') and self.record_id]

        # ## END

        fields = {}
        for key in self.vars:
            fields[key] = self.vars[key]

        ret = FORM.accepts(
            self,
            request_vars,
            session,
            formname,
            keepvalues,
            onvalidation,
            hideerror=hideerror,
            **kwargs
        )

        self.deleted = \
            request_vars.get(self.FIELDNAME_REQUEST_DELETE, False)

        self.custom.end = TAG[''](self.hidden_fields(), self.custom.end)

        auch = record_id and self.errors and self.deleted

        if self.record_changed and self.detect_record_change:
            message_onchange = \
                kwargs.setdefault("message_onchange",
                                  current.T("A record change was detected. " +
                                            "Consecutive update self-submissions " +
                                            "are not allowed. Try re-submitting or " +
                                            "refreshing the form page."))
            if message_onchange is not None:
                current.response.flash = message_onchange
            return ret
        elif (not ret) and (not auch):
            # auch is true when user tries to delete a record
            # that does not pass validation, yet it should be deleted
            for fieldname in self.fields:
                field = self.table[fieldname]
                ### this is a workaround! widgets should always have default not None!
                if not field.widget and field.type.startswith('list:') and \
                        not OptionsWidget.has_options(field):
                    field.widget = self.widgets.list.widget
                if field.widget and fieldname in request_vars:
                    if fieldname in self.request_vars:
                        value = self.request_vars[fieldname]
                    elif self.record:
                        value = self.record[fieldname]
                    else:
                        value = self.table[fieldname].default
                    if field.type.startswith('list:') and isinstance(value, str):
                        value = [value]
                    row_id = '%s_%s%s' % (
                        self.table, fieldname, SQLFORM.ID_ROW_SUFFIX)
                    widget = field.widget(field, value)
                    parent = self.field_parent[row_id]
                    if parent:
                        parent.components = [widget]
                        if self.errors.get(fieldname):
                            parent._traverse(False, hideerror)
                    self.custom.widget[fieldname] = widget
            self.accepted = ret
            return ret

        if record_id and str(record_id) != str(self.record_id):
            raise SyntaxError('user is tampering with form\'s record_id: '
                              '%s != %s' % (record_id, self.record_id))

        if record_id and dbio and not keyed:
            self.vars.id = self.record[self.id_field_name]

        if self.deleted and self.custom.deletable:
            if dbio:
                if keyed:
                    qry = reduce(lambda x, y: x & y,
                                 [self.table[k] == record_id[k]
                                  for k in self.table._primarykey])
                else:
                    qry = self.table._id == self.record[self.id_field_name]
                self.table._db(qry).delete()
            self.errors.clear()
            for component in self.elements('input, select, textarea'):
                component['_disabled'] = True
            self.accepted = True
            return True

        for fieldname in self.fields:
            if not fieldname in self.table.fields:
                continue

            if not self.ignore_rw and not self.table[fieldname].writable:
                ### this happens because FORM has no knowledge of writable
                ### and thinks that a missing boolean field is a None
                if self.table[fieldname].type == 'boolean' and \
                        self.vars.get(fieldname, True) is None:
                    del self.vars[fieldname]
                continue

            field = self.table[fieldname]
            if field.type == 'id':
                continue
            if field.type == 'boolean':
                if self.vars.get(fieldname, False):
                    self.vars[fieldname] = fields[fieldname] = True
                else:
                    self.vars[fieldname] = fields[fieldname] = False
            elif field.type == 'password' and self.record\
                and request_vars.get(fieldname, None) == \
                    PasswordWidget.DEFAULT_PASSWORD_DISPLAY:
                continue  # do not update if password was not changed
            elif field.type == 'upload':
                f = self.vars[fieldname]
                fd = '%s__delete' % fieldname
                if f == '' or f is None:
                    if self.vars.get(fd, False):
                        f = self.table[fieldname].default or ''
                        fields[fieldname] = f
                    elif self.record:
                        if self.record[fieldname]:
                            fields[fieldname] = self.record[fieldname]
                        else:
                            f = self.table[fieldname].default or ''
                            fields[fieldname] = f
                    else:
                        f = self.table[fieldname].default or ''
                        fields[fieldname] = f
                    self.vars[fieldname] = fields[fieldname]
                    if not f:
                        continue
                    else:
                        f = os.path.join(
                            current.request.folder,
                            os.path.normpath(f))
                        source_file = open(f, 'rb')
                        original_filename = os.path.split(f)[1]
                elif hasattr(f, 'file'):
                    (source_file, original_filename) = (f.file, f.filename)
                elif isinstance(f, (str, unicode)):
                    ### do not know why this happens, it should not
                    (source_file, original_filename) = \
                        (cStringIO.StringIO(f), 'file.txt')
                else:
                    # this should never happen, why does it happen?
                    print 'f=',repr(f)
                    continue
                newfilename = field.store(source_file, original_filename,
                                          field.uploadfolder)
                # this line was for backward compatibility but problematic
                # self.vars['%s_newfilename' % fieldname] = newfilename
                fields[fieldname] = newfilename
                if isinstance(field.uploadfield, str):
                    fields[field.uploadfield] = source_file.read()
                # proposed by Hamdy (accept?) do we need fields at this point?
                self.vars[fieldname] = fields[fieldname]
                continue
            elif fieldname in self.vars:
                fields[fieldname] = self.vars[fieldname]
            elif field.default is None and field.type != 'blob':
                self.errors[fieldname] = 'no data'
                self.accepted = False
                return False
            value = fields.get(fieldname, None)
            if field.type == 'list:string':
                if not isinstance(value, (tuple, list)):
                    fields[fieldname] = value and [value] or []
            elif isinstance(field.type, str) and field.type.startswith('list:'):
                if not isinstance(value, list):
                    fields[fieldname] = [safe_int(
                        x) for x in (value and [value] or [])]
            elif field.type == 'integer':
                if not value is None:
                    fields[fieldname] = safe_int(value)
            elif field.type.startswith('reference'):
                if not value is None and isinstance(self.table, Table) and not keyed:
                    fields[fieldname] = safe_int(value)
            elif field.type == 'double':
                if not value is None:
                    fields[fieldname] = safe_float(value)

        for fieldname in self.vars:
            if fieldname != 'id' and fieldname in self.table.fields\
                and not fieldname in fields and not fieldname\
                    in request_vars:
                fields[fieldname] = self.vars[fieldname]

        if dbio:
            if 'delete_this_record' in fields:
                # this should never happen but seems to happen to some
                del fields['delete_this_record']
            for field in self.table:
                if not field.name in fields and field.writable is False \
                        and field.update is None and field.compute is None:
                    if record_id and self.record:
                        fields[field.name] = self.record[field.name]
                    elif not self.table[field.name].default is None:
                        fields[field.name] = self.table[field.name].default
            if keyed:
                if reduce(lambda x, y: x and y, record_id.values()):  # if record_id
                    if fields:
                        qry = reduce(lambda x, y: x & y,
                                     [self.table[k] == self.record[k] for k in self.table._primarykey])
                        self.table._db(qry).update(**fields)
                else:
                    pk = self.table.insert(**fields)
                    if pk:
                        self.vars.update(pk)
                    else:
                        ret = False
            else:
                if record_id:
                    self.vars.id = self.record[self.id_field_name]
                    if fields:
                        self.table._db(self.table._id == self.record[
                                       self.id_field_name]).update(**fields)
                else:
                    self.vars.id = self.table.insert(**fields)
        self.accepted = ret
        return ret

    AUTOTYPES = {
        type(''): ('string', None),
        type(True): ('boolean', None),
        type(1): ('integer', IS_INT_IN_RANGE(-1e12, +1e12)),
        type(1.0): ('double', IS_FLOAT_IN_RANGE()),
        type([]): ('list:string', None),
        type(datetime.date.today()): ('date', IS_DATE()),
        type(datetime.datetime.today()): ('datetime', IS_DATETIME())
    }

    @staticmethod
    def dictform(dictionary, **kwargs):
        fields = []
        for key, value in sorted(dictionary.items()):
            t, requires = SQLFORM.AUTOTYPES.get(type(value), (None, None))
            if t:
                fields.append(Field(key, t, requires=requires,
                                    default=value))
        return SQLFORM.factory(*fields, **kwargs)

    @staticmethod
    def smartdictform(session, name, filename=None, query=None, **kwargs):
        import os
        if query:
            session[name] = query.db(query).select().first().as_dict()
        elif os.path.exists(filename):
            env = {'datetime': datetime}
            session[name] = eval(open(filename).read(), {}, env)
        form = SQLFORM.dictform(session[name])
        if form.process().accepted:
            session[name].update(form.vars)
            if query:
                query.db(query).update(**form.vars)
            else:
                open(filename, 'w').write(repr(session[name]))
        return form

    @staticmethod
    def factory(*fields, **attributes):
        """
        generates a SQLFORM for the given fields.

        Internally will build a non-database based data model
        to hold the fields.
        """
        # Define a table name, this way it can be logical to our CSS.
        # And if you switch from using SQLFORM to SQLFORM.factory
        # your same css definitions will still apply.

        table_name = attributes.get('table_name', 'no_table')

        # So it won't interfere with SQLDB.define_table
        if 'table_name' in attributes:
            del attributes['table_name']

        return SQLFORM(DAL(None).define_table(table_name, *fields),
                       **attributes)

    @staticmethod
    def build_query(fields, keywords):
        request = current.request
        if isinstance(keywords, (tuple, list)):
            keywords = keywords[0]
            request.vars.keywords = keywords
        key = keywords.strip()
        if key and not ' ' in key and not '"' in key and not "'" in key:
            SEARCHABLE_TYPES = ('string', 'text', 'list:string')
            parts = [field.contains(
                key) for field in fields if field.type in SEARCHABLE_TYPES]
        else:
            parts = None
        if parts:
            return reduce(lambda a, b: a | b, parts)
        else:
            return smart_query(fields, key)

    @staticmethod
    def search_menu(fields,
                    search_options=None,
                    prefix='w2p'
                    ):
        T = current.T
        panel_id='%s_query_panel' % prefix
        fields_id='%s_query_fields' % prefix
        keywords_id='%s_keywords' % prefix
        field_id='%s_field' % prefix
        value_id='%s_value' % prefix
        search_options = search_options or {
            'string': ['=', '!=', '<', '>', '<=', '>=', 'starts with', 'contains', 'in', 'not in'],
            'text': ['=', '!=', '<', '>', '<=', '>=', 'starts with', 'contains', 'in', 'not in'],
            'date': ['=', '!=', '<', '>', '<=', '>='],
            'time': ['=', '!=', '<', '>', '<=', '>='],
            'datetime': ['=', '!=', '<', '>', '<=', '>='],
            'integer': ['=', '!=', '<', '>', '<=', '>=', 'in', 'not in'],
            'double': ['=', '!=', '<', '>', '<=', '>='],
            'id': ['=', '!=', '<', '>', '<=', '>=', 'in', 'not in'],
            'reference': ['=', '!='],
            'boolean': ['=', '!=']}
        if fields[0]._db._adapter.dbengine == 'google:datastore':
            search_options['string'] = ['=', '!=', '<', '>', '<=', '>=']
            search_options['text'] = ['=', '!=', '<', '>', '<=', '>=']
            search_options['list:string'] = ['contains']
            search_options['list:integer'] = ['contains']
            search_options['list:reference'] = ['contains']
        criteria = []
        selectfields = []
        for field in fields:
            name = str(field).replace('.', '-')
            # treat ftype 'decimal' as 'double'
            # (this fixes problems but needs refactoring!
            ftype = field.type.split(' ')[0]
            if ftype.startswith('decimal'): ftype = 'double'
            elif ftype=='bigint': ftype = 'integer'
            elif ftype.startswith('big-'): ftype = ftype[4:]
            # end
            options = search_options.get(ftype, None)
            if options:
                label = isinstance(
                    field.label, str) and T(field.label) or field.label
                selectfields.append(OPTION(label, _value=str(field)))
                operators = SELECT(*[OPTION(T(option), _value=option) for option in options])
                _id = "%s_%s" % (value_id,name)
                if field.type == 'boolean':
                    value_input = SQLFORM.widgets.boolean.widget(field,field.default,_id=_id)
                elif field.type == 'double':
                    value_input = SQLFORM.widgets.double.widget(field,field.default,_id=_id)
                elif field.type == 'time':
                    value_input = SQLFORM.widgets.time.widget(field,field.default,_id=_id)
                elif field.type == 'date':
                    value_input = SQLFORM.widgets.date.widget(field,field.default,_id=_id)
                elif field.type == 'datetime':
                    value_input = SQLFORM.widgets.datetime.widget(field,field.default,_id=_id)
                elif (field.type.startswith('reference ') or
                      field.type.startswith('list:reference ')) and \
                      hasattr(field.requires,'options'):
                    value_input = SELECT(
                        *[OPTION(v, _value=k)
                          for k,v in field.requires.options()],
                         **dict(_id=_id))
                elif field.type == 'integer' or \
                        field.type.startswith('reference ') or \
                        field.type.startswith('list:integer') or \
                        field.type.startswith('list:reference '):
                    value_input = SQLFORM.widgets.integer.widget(field,field.default,_id=_id)
                else:
                    value_input = INPUT(
                        _type='text', _id=_id, _class=field.type)

                new_button = INPUT(
                    _type="button", _value=T('New'), _class="btn",
                    _onclick="%s_build_query('new','%s')" % (prefix,field))
                and_button = INPUT(
                    _type="button", _value=T('And'), _class="btn",
                    _onclick="%s_build_query('and','%s')" % (prefix, field))
                or_button = INPUT(
                    _type="button", _value=T('Or'), _class="btn",
                    _onclick="%s_build_query('or','%s')" % (prefix, field))
                close_button = INPUT(
                    _type="button", _value=T('Close'), _class="btn",
                    _onclick="jQuery('#%s').slideUp()" % panel_id)

                criteria.append(DIV(
                    operators, value_input, new_button,
                    and_button, or_button, close_button,
                    _id='%s_%s' % (field_id, name),
                        _class='w2p_query_row hidden',
                        _style='display:inline'))

        criteria.insert(0, SELECT(
            _id=fields_id,
                _onchange="jQuery('.w2p_query_row').hide();jQuery('#%s_'+jQuery('#%s').val().replace('.','-')).show();" % (field_id,fields_id),
                _style='float:left',
                *selectfields))

        fadd = SCRIPT("""
        jQuery('#%(fields_id)s input,#%(fields_id)s select').css(
            'width','auto');
        jQuery(function(){web2py_ajax_fields('#%(fields_id)s');});
        function %(prefix)s_build_query(aggregator,a) {
          var b=a.replace('.','-');
          var option = jQuery('#%(field_id)s_'+b+' select').val();
          var value = jQuery('#%(value_id)s_'+b).val().replace('"','\\\\"');
          var s=a+' '+option+' "'+value+'"';
          var k=jQuery('#%(keywords_id)s');
          var v=k.val();
          if(aggregator=='new') k.val(s); else k.val((v?(v+' '+ aggregator +' '):'')+s);
        }
        """ % dict(
                prefix=prefix,fields_id=fields_id,keywords_id=keywords_id,
                field_id=field_id,value_id=value_id
                )
        )
        return CAT(
            DIV(_id=panel_id, _style="display:none;", *criteria), fadd)


    @staticmethod
    def grid(query,
             fields=None,
             field_id=None,
             left=None,
             headers={},
             orderby=None,
             groupby=None,
             searchable=True,
             sortable=True,
             paginate=20,
             deletable=True,
             editable=True,
             details=True,
             selectable=None,
             create=True,
             csv=True,
             links=None,
             links_in_grid=True,
             upload='<default>',
             args=[],
             user_signature=True,
             maxtextlengths={},
             maxtextlength=20,
             onvalidation=None,
             onfailure=None,
             oncreate=None,
             onupdate=None,
             ondelete=None,
             sorter_icons=(XML('&#x2191;'), XML('&#x2193;')),
             ui = 'web2py',
             showbuttontext=True,
             _class="web2py_grid",
             formname='web2py_grid',
             search_widget='default',
             ignore_rw = False,
             formstyle = 'table3cols',
             exportclasses = None,
             formargs={},
             createargs={},
             editargs={},
             viewargs={},
             selectable_submit_button='Submit',
             buttons_placement = 'right',
             links_placement = 'right',
             noconfirm=False,
             cache_count=None,
             client_side_delete=False,
             ):

        # jQuery UI ThemeRoller classes (empty if ui is disabled)
        if ui == 'jquery-ui':
            ui = dict(widget='ui-widget',
                      header='ui-widget-header',
                      content='ui-widget-content',
                      default='ui-state-default',
                      cornerall='ui-corner-all',
                      cornertop='ui-corner-top',
                      cornerbottom='ui-corner-bottom',
                      button='ui-button-text-icon-primary',
                      buttontext='ui-button-text',
                      buttonadd='ui-icon ui-icon-plusthick',
                      buttonback='ui-icon ui-icon-arrowreturnthick-1-w',
                      buttonexport='ui-icon ui-icon-transferthick-e-w',
                      buttondelete='ui-icon ui-icon-trash',
                      buttonedit='ui-icon ui-icon-pencil',
                      buttontable='ui-icon ui-icon-triangle-1-e',
                      buttonview='ui-icon ui-icon-zoomin',
                      )
        elif ui == 'web2py':
            ui = dict(widget='',
                      header='',
                      content='',
                      default='',
                      cornerall='',
                      cornertop='',
                      cornerbottom='',
                      button='button btn',
                      buttontext='buttontext button',
                      buttonadd='icon plus icon-plus',
                      buttonback='icon leftarrow icon-arrow-left',
                      buttonexport='icon downarrow icon-download',
                      buttondelete='icon trash icon-trash',
                      buttonedit='icon pen icon-pencil',
                      buttontable='icon rightarrow icon-arrow-right',
                      buttonview='icon magnifier icon-zoom-in',
                      )
        elif not isinstance(ui, dict):
            raise RuntimeError('SQLFORM.grid ui argument must be a dictionary')

        db = query._db
        T = current.T
        request = current.request
        session = current.session
        response = current.response
        logged = session.auth and session.auth.user
        wenabled = (not user_signature or logged)
        create = wenabled and create
        editable = wenabled and editable
        deletable = wenabled and deletable
        rows = None

        def fetch_count(dbset):
            ##FIXME for google:datastore cache_count is ignored
            ## if it's not an integer
            if cache_count is None or isinstance(cache_count, tuple):
                if groupby:
                    c = 'count(*)'
                    nrows = db.executesql(
                        'select count(*) from (%s);' %
                        dbset._select(c, left=left, cacheable=True,
                                      groupby=groupby, cache=cache_count)[:-1])[0][0]
                elif left:
                    c = 'count(*)'
                    nrows = dbset.select(c, left=left, cacheable=True, cache=cache_count).first()[c]
                elif dbset._db._adapter.dbengine=='google:datastore':
                    #if we don't set a limit, this can timeout for a large table
                    nrows = dbset.db._adapter.count(dbset.query, limit=1000)
                else:
                    nrows = dbset.count(cache=cache_count)
            elif isinstance(cache_count, (int, long)):
                    nrows = cache_count
            elif callable(cache_count):
                nrows = cache_count(dbset, request.vars)
            else:
                nrows = 0
            return nrows

        def url(**b):
            b['args'] = args + b.get('args', [])
            localvars = request.get_vars.copy()
            localvars.update(b.get('vars', {}))
            b['vars'] = localvars
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        def url2(**b):
            b['args'] = request.args + b.get('args', [])
            localvars = request.get_vars.copy()
            localvars.update(b.get('vars', {}))
            b['vars'] = localvars
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        referrer = session.get('_web2py_grid_referrer_' + formname, url())
        # if not user_signature every action is accessible
        # else forbid access unless
        # - url is based url
        # - url has valid signature (vars are not signed, only path_info)
        # = url does not contain 'create','delete','edit' (readonly)
        if user_signature:
            if not (
                '/'.join(str(a) for a in args) == '/'.join(request.args) or
                URL.verify(request,user_signature=user_signature,
                           hash_vars=False) or
                (request.args(len(args))=='view' and not logged)):
                session.flash = T('not authorized')
                redirect(referrer)

        def gridbutton(buttonclass='buttonadd', buttontext=T('Add'),
                       buttonurl=url(args=[]), callback=None,
                       delete=None, trap=True, noconfirm=None):
            if showbuttontext:
                return A(SPAN(_class=ui.get(buttonclass)),
                         SPAN(T(buttontext), _title=T(buttontext),
                              _class=ui.get('buttontext')),
                         _href=buttonurl,
                         callback=callback,
                         delete=delete,
                         noconfirm=noconfirm,
                         _class=trap_class(ui.get('button'), trap))
            else:
                return A(SPAN(_class=ui.get(buttonclass)),
                         _href=buttonurl,
                         callback=callback,
                         delete=delete,
                         noconfirm=noconfirm,
                         _title=T(buttontext),
                         _class=trap_class(ui.get('buttontext'), trap))

        dbset = db(query)
        tablenames = db._adapter.tables(dbset.query)
        if left is not None:
            if not isinstance(left, (list, tuple)):
                left = [left]
            for join in left:
                tablenames += db._adapter.tables(join)
        tables = [db[tablename] for tablename in tablenames]
        if fields:
            columns = [f for f in fields if f.tablename in tablenames]
        else:
            fields = []
            columns = []
            for table in tables:
                fields += [f for f in table]
                columns +=  [f for f in table]
                for k,f in table.iteritems():
                    if isinstance(f,Field.Virtual) and f.readable:
                        f.tablename = table._tablename
                        columns.append(f)
        if not field_id:
            field_id = tables[0]._id
        if not any(str(f)==str(field_id) for f in fields):
            fields = [f for f in fields]+[field_id]
        table = field_id.table
        tablename = table._tablename
        if upload == '<default>':
            upload = lambda filename: url(args=['download', filename])
            if request.args(-2) == 'download':
                stream = response.download(request, db)
                raise HTTP(200, stream, **response.headers)

        def buttons(edit=False, view=False, record=None):
            buttons = DIV(gridbutton('buttonback', 'Back', referrer),
                          _class='form_header row_buttons %(header)s %(cornertop)s' % ui)
            if edit and (not callable(edit) or edit(record)):
                args = ['edit', table._tablename, request.args[-1]]
                buttons.append(gridbutton('buttonedit', 'Edit',
                                          url(args=args)))
            if view:
                args = ['view', table._tablename, request.args[-1]]
                buttons.append(gridbutton('buttonview', 'View',
                                          url(args=args)))
            if record and links:
                for link in links:
                    if isinstance(link, dict):
                        buttons.append(link['body'](record))
                    elif link(record):
                        buttons.append(link(record))
            return buttons

        def linsert(lst, i, x):
            """
            a = [1,2]
            linsert(a, 1, [0,3])
            a = [1, 0, 3, 2]
            """
            lst[i:i] = x

        formfooter = DIV(
            _class='form_footer row_buttons %(header)s %(cornerbottom)s' % ui)

        create_form = update_form = view_form = search_form = None
        sqlformargs = dict(formargs)

        if create and request.args(-2) == 'new':
            table = db[request.args[-1]]
            sqlformargs.update(createargs)
            create_form = SQLFORM(
                table, ignore_rw=ignore_rw, formstyle=formstyle,
                _class='web2py_form',
                **sqlformargs)
            create_form.process(formname=formname,
                                next=referrer,
                                onvalidation=onvalidation,
                                onfailure=onfailure,
                                onsuccess=oncreate)
            res = DIV(buttons(), create_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res

        elif details and request.args(-3) == 'view':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(referrer)
            sqlformargs.update(viewargs)
            view_form = SQLFORM(
                table, record, upload=upload, ignore_rw=ignore_rw,
                formstyle=formstyle, readonly=True, _class='web2py_form',
                **sqlformargs)
            res = DIV(buttons(edit=editable, record=record), view_form,
                      formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res
        elif editable and request.args(-3) == 'edit':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(URL('error'))
            sqlformargs.update(editargs)
            deletable_ = deletable(record) if callable(deletable) else deletable
            update_form = SQLFORM(
                table,
                record, upload=upload, ignore_rw=ignore_rw,
                formstyle=formstyle, deletable=deletable_,
                _class='web2py_form',
                submit_button=T('Submit'),
                delete_label=T('Check to delete'),
                **sqlformargs)
            update_form.process(
                formname=formname,
                onvalidation=onvalidation,
                onfailure=onfailure,
                onsuccess=onupdate,
                next=referrer)
            res = DIV(buttons(view=details, record=record),
                      update_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            res.rows = None
            return res
        elif deletable and request.args(-3) == 'delete':
            table = db[request.args[-2]]
            if not callable(deletable):
                if ondelete:
                    ondelete(table, request.args[-1])
                db(table[table._id.name] == request.args[-1]).delete()
            else:
                record = table(request.args[-1]) or redirect(URL('error'))
                if deletable(record):
                    if ondelete:
                        ondelete(table, request.args[-1])
                    record.delete_record()
            redirect(referrer, client_side=client_side_delete)

        exportManager = dict(
            csv_with_hidden_cols=(ExporterCSV, 'CSV (hidden cols)'),
            csv=(ExporterCSV, 'CSV'),
            xml=(ExporterXML, 'XML'),
            html=(ExporterHTML, 'HTML'),
            json=(ExporterJSON, 'JSON'),
            tsv_with_hidden_cols=
                (ExporterTSV, 'TSV (Excel compatible, hidden cols)'),
            tsv=(ExporterTSV, 'TSV (Excel compatible)'))
        if not exportclasses is None:
            """
            remember: allow to set exportclasses=dict(csv=False) to disable the csv format
            """
            exportManager.update(exportclasses)

        export_type = request.vars._export_type
        if export_type:
            order = request.vars.order or ''
            if sortable:
                if order and not order == 'None':
                    if order[:1] == '~':
                        sign, rorder = '~', order[1:]
                    else:
                        sign, rorder = '', order
                    tablename, fieldname = rorder.split('.', 1)
                    orderby = db[tablename][fieldname]
                    if sign == '~':
                        orderby = ~orderby

            expcolumns = [str(f) for f in columns]
            if export_type.endswith('with_hidden_cols'):
                expcolumns = []
                for table in tables:
                    for field in table:
                        if field.readable and field.tablename in tablenames:
                            expcolumns.append(field)

            if export_type in exportManager and exportManager[export_type]:
                if request.vars.keywords:
                    try:
                        dbset = dbset(SQLFORM.build_query(
                            fields, request.vars.get('keywords', '')))
                        rows = dbset.select(cacheable=True, *expcolumns)
                    except Exception, e:
                        response.flash = T('Internal Error')
                        rows = []
                else:
                    rows = dbset.select(left=left, orderby=orderby,
                                    cacheable=True, *expcolumns)

                value = exportManager[export_type]
                clazz = value[0] if hasattr(value, '__getitem__') else value
                oExp = clazz(rows)
                filename = '.'.join(('rows', oExp.file_ext))
                response.headers['Content-Type'] = oExp.content_type
                response.headers['Content-Disposition'] = \
                    'attachment;filename=' + filename + ';'
                raise HTTP(200, oExp.export(), **response.headers)

        elif request.vars.records and not isinstance(
                request.vars.records, list):
            request.vars.records = [request.vars.records]
        elif not request.vars.records:
            request.vars.records = []

        session['_web2py_grid_referrer_' + formname] = \
            url2(vars=request.get_vars)
        console = DIV(_class='web2py_console %(header)s %(cornertop)s' % ui)
        error = None
        if create:
            add = gridbutton(
                buttonclass='buttonadd',
                buttontext=T('Add'),
                buttonurl=url(args=['new', tablename]))
            if not searchable:
                console.append(add)
        else:
            add = ''

        if searchable:
            sfields = reduce(lambda a, b: a + b,
                             [[f for f in t if f.readable] for t in tables])
            if isinstance(search_widget, dict):
                search_widget = search_widget[tablename]
            if search_widget == 'default':
                prefix = formname == 'web2py_grid' and 'w2p' or 'w2p_%s' % formname
                search_menu = SQLFORM.search_menu(sfields, prefix=prefix)
                spanel_id = '%s_query_fields' % prefix
                sfields_id = '%s_query_panel' % prefix
                skeywords_id = '%s_keywords' % prefix
                search_widget = lambda sfield, url: CAT(FORM(
                    INPUT(_name='keywords', _value=request.vars.keywords,
                          _id=skeywords_id,
                          _onfocus="jQuery('#%s').change();jQuery('#%s').slideDown();" % (spanel_id, sfields_id)),
                    INPUT(_type='submit', _value=T('Search'), _class="btn"),
                    INPUT(_type='submit', _value=T('Clear'), _class="btn",
                          _onclick="jQuery('#%s').val('');" % skeywords_id),
                    _method="GET", _action=url), search_menu)
            form = search_widget and search_widget(sfields, url()) or ''
            console.append(add)
            console.append(form)
            keywords = request.vars.get('keywords', '')
            try:
                if callable(searchable):
                    subquery = searchable(sfields, keywords)
                else:
                    subquery = SQLFORM.build_query(sfields, keywords)
            except RuntimeError:
                subquery = None
                error = T('Invalid query')
        else:
            subquery = None

        if subquery:
            dbset = dbset(subquery)
        try:
            nrows = fetch_count(dbset)
        except:
            nrows = 0
            error = T('Unsupported query')

        order = request.vars.order or ''
        if sortable:
            if order and not order == 'None':
                tablename, fieldname = order.split('~')[-1].split('.', 1)
                sort_field = db[tablename][fieldname]
                exception = sort_field.type in ('date', 'datetime', 'time')
                if exception:
                    orderby = (order[:1] == '~' and sort_field) or ~sort_field
                else:
                    orderby = (order[:1] == '~' and ~sort_field) or sort_field

        headcols = []
        if selectable:
            headcols.append(TH(_class=ui.get('default')))
        for field in columns:
            if not field.readable:
                continue
            key = str(field)
            header = headers.get(str(field), field.label or key)
            if sortable and not isinstance(field, Field.Virtual):
                if key == order:
                    key, marker = '~' + order, sorter_icons[0]
                elif key == order[1:]:
                    marker = sorter_icons[1]
                else:
                    marker = ''
                header = A(header, marker, _href=url(vars=dict(
                    keywords=request.vars.keywords or '',
                    order=key)), _class=trap_class())
            headcols.append(TH(header, _class=ui.get('default')))

        toadd = []
        if links and links_in_grid:
            for link in links:
                if isinstance(link, dict):
                    toadd.append(TH(link['header'], _class=ui.get('default')))
            if links_placement in ['right', 'both']:
                headcols.extend(toadd)
            if links_placement in ['left', 'both']:
                linsert(headcols, 0, toadd)

        # Include extra column for buttons if needed.
        include_buttons_column = (details or editable or deletable or
                                  (links and links_in_grid and
                                   not all([isinstance(link, dict) for link in links])))
        if include_buttons_column:
            if buttons_placement in ['right', 'both']:
                headcols.append(TH(_class=ui.get('default','')))
            if buttons_placement in ['left', 'both']:
                headcols.insert(0, TH(_class=ui.get('default','')))

        head = TR(*headcols, **dict(_class=ui.get('header')))

        cursor = True
        #figure out what page we are one to setup the limitby
        if paginate and dbset._db._adapter.dbengine=='google:datastore':
            cursor = request.vars.cursor or True
            limitby = (0, paginate)
            try: page = int(request.vars.page or 1)-1
            except ValueError: page = 0
        elif paginate and paginate<nrows:
            try: page = int(request.vars.page or 1)-1
            except ValueError: page = 0
            limitby = (paginate*page,paginate*(page+1))
        else:
            limitby = None

        try:
            table_fields = [f for f in fields if f.tablename in tablenames]
            if dbset._db._adapter.dbengine=='google:datastore':
                rows = dbset.select(left=left,orderby=orderby,
                                    groupby=groupby,limitby=limitby,
                                    reusecursor=cursor,
                                    cacheable=True,*table_fields)
                next_cursor = dbset._db.get('_lastcursor', None)
            else:
                rows = dbset.select(left=left,orderby=orderby,
                                    groupby=groupby,limitby=limitby,
                                    cacheable=True,*table_fields)
        except SyntaxError:
            rows = None
            next_cursor = None
            error = T("Query Not Supported")
        except Exception, e:
            rows = None
            next_cursor = None
            error = T("Query Not Supported: %s")%e

        message = error
        if not message and nrows:
            if dbset._db._adapter.dbengine=='google:datastore' and nrows>=1000:
                message = T('at least %(nrows)s records found') % dict(nrows=nrows)
            else:
                message = T('%(nrows)s records found') % dict(nrows=nrows)
        console.append(DIV(message or T('None'),_class='web2py_counter'))

        paginator = UL()
        if paginate and dbset._db._adapter.dbengine=='google:datastore':
            #this means we may have a large table with an unknown number of rows.
            try:
                page = int(request.vars.page or 1)-1
            except ValueError:
                page = 0
            paginator.append(LI('page %s'%(page+1)))
            if next_cursor:
                d = dict(page=page+2, cursor=next_cursor)
                if order: d['order']=order
                if request.vars.keywords: d['keywords']=request.vars.keywords
                paginator.append(LI(
                    A('next',_href=url(vars=d),_class=trap_class())))
        elif paginate and paginate<nrows:
            npages, reminder = divmod(nrows, paginate)
            if reminder:
                npages += 1
            try:
                page = int(request.vars.page or 1) - 1
            except ValueError:
                page = 0

            def self_link(name, p):
                d = dict(page=p + 1)
                if order:
                    d['order'] = order
                if request.vars.keywords:
                    d['keywords'] = request.vars.keywords
                return A(name, _href=url(vars=d), _class=trap_class())
            NPAGES = 5  # window is 2*NPAGES
            if page > NPAGES + 1:
                paginator.append(LI(self_link('<<', 0)))
            if page > NPAGES:
                paginator.append(LI(self_link('<', page - 1)))
            pages = range(max(0, page - NPAGES), min(page + NPAGES, npages))
            for p in pages:
                if p == page:
                    paginator.append(LI(A(p + 1, _onclick='return false'),
                                        _class=trap_class('current')))
                else:
                    paginator.append(LI(self_link(p + 1, p)))
            if page < npages - NPAGES:
                paginator.append(LI(self_link('>', page + 1)))
            if page < npages - NPAGES - 1:
                paginator.append(LI(self_link('>>', npages - 1)))
        else:
            limitby = None

        if rows:
            htmltable = TABLE(THEAD(head))
            tbody = TBODY()
            numrec = 0
            for row in rows:
                trcols = []
                id = row[field_id]
                if selectable:
                    trcols.append(
                        INPUT(_type="checkbox", _name="records", _value=id,
                                    value=request.vars.records))
                for field in columns:
                    if not field.readable:
                        continue
                    if field.type == 'blob':
                        continue
                    value = row[str(field)]
                    maxlength = maxtextlengths.get(str(field), maxtextlength)
                    if field.represent:
                        try:
                            value = field.represent(value, row)
                        except KeyError:
                            try:
                                value = field.represent(
                                    value, row[field.tablename])
                            except KeyError:
                                pass
                    elif field.type == 'boolean':
                        value = INPUT(_type="checkbox", _checked=value,
                                      _disabled=True)
                    elif field.type == 'upload':
                        if value:
                            if callable(upload):
                                value = A(
                                    T('file'), _href=upload(value))
                            elif upload:
                                value = A(T('file'),
                                          _href='%s/%s' % (upload, value))
                        else:
                            value = ''
                    if isinstance(value, str):
                        value = truncate_string(value, maxlength)
                    elif not isinstance(value, DIV):
                        value = field.formatter(value)
                    trcols.append(TD(value))
                row_buttons = TD(_class='row_buttons',_nowrap=True)
                if links and links_in_grid:
                    toadd = []
                    for link in links:
                        if isinstance(link, dict):
                            toadd.append(TD(link['body'](row)))
                        else:
                            if link(row):
                                row_buttons.append(link(row))
                    if links_placement in ['right', 'both']:
                        trcols.extend(toadd)
                    if links_placement in ['left', 'both']:
                        linsert(trcols, 0, toadd)

                if include_buttons_column:
                    if details and (not callable(details) or details(row)):
                        row_buttons.append(gridbutton(
                            'buttonview', 'View',
                            url(args=['view', tablename, id])))
                    if editable and (not callable(editable) or editable(row)):
                        row_buttons.append(gridbutton(
                            'buttonedit', 'Edit',
                            url(args=['edit', tablename, id])))
                    if deletable and (not callable(deletable) or deletable(row)):
                        row_buttons.append(gridbutton(
                            'buttondelete', 'Delete',
                            url(args=['delete', tablename, id]),
                            callback=url(args=['delete', tablename, id]),
                            noconfirm=noconfirm,
                            delete='tr'))
                    if buttons_placement in ['right', 'both']:
                        trcols.append(row_buttons)
                    if buttons_placement in ['left', 'both']:
                        trcols.insert(0, row_buttons)
                if numrec % 2 == 0:
                    classtr = 'even'
                else:
                    classtr = 'odd'
                numrec += 1
                if id:
                    rid = id
                    if callable(rid):  # can this ever be callable?
                        rid = rid(row)
                    tr = TR(*trcols, **dict(
                            _id=rid,
                            _class='%s %s' % (classtr, 'with_id')))
                else:
                    tr = TR(*trcols, **dict(_class=classtr))
                tbody.append(tr)
            htmltable.append(tbody)
            htmltable = DIV(
                htmltable, _class='web2py_htmltable',
                _style='width:100%;overflow-x:auto;-ms-overflow-x:scroll')
            if selectable:
                htmltable = FORM(htmltable, INPUT(
                        _type="submit", _value=T(selectable_submit_button)))
                if htmltable.process(formname=formname).accepted:
                    htmltable.vars.records = htmltable.vars.records or []
                    htmltable.vars.records = htmltable.vars.records if type(htmltable.vars.records) == list else [htmltable.vars.records]
                    records = [int(r) for r in htmltable.vars.records]
                    selectable(records)
                    redirect(referrer)
        else:
            htmltable = DIV(T('No records found'))

        if csv and nrows:
            export_links = []
            for k, v in sorted(exportManager.items()):
                if not v:
                    continue
                label = v[1] if hasattr(v, "__getitem__") else k
                link = url2(vars=dict(
                    order=request.vars.order or '',
                    _export_type=k,
                    keywords=request.vars.keywords or ''))
                export_links.append(A(T(label), _href=link))
            export_menu = \
                DIV(T('Export:'), _class="w2p_export_menu", *export_links)
        else:
            export_menu = None

        res = DIV(console, DIV(htmltable, _class="web2py_table"),
                  _class='%s %s' % (_class, ui.get('widget')))
        if paginator.components:
            res.append(
                DIV(paginator,
                    _class="web2py_paginator %(header)s %(cornerbottom)s" % ui))
        if export_menu:
            res.append(export_menu)
        res.create_form = create_form
        res.update_form = update_form
        res.view_form = view_form
        res.search_form = search_form
        res.rows = rows
        return res

    @staticmethod
    def smartgrid(table, constraints=None, linked_tables=None,
                  links=None, links_in_grid=True,
                  args=None, user_signature=True,
                  divider='>', breadcrumbs_class='',
                  **kwargs):
        """
        @auth.requires_login()
        def index():
            db.define_table('person',Field('name'),format='%(name)s')
            db.define_table('dog',
                Field('name'),Field('owner',db.person),format='%(name)s')
            db.define_table('comment',Field('body'),Field('dog',db.dog))
            if db(db.person).isempty():
                from gluino.contrib.populate import populate
                populate(db.person,300)
                populate(db.dog,300)
                populate(db.comment,1000)
                db.commit()
        form=SQLFORM.smartgrid(db[request.args(0) or 'person']) #***
        return dict(form=form)

        *** builds a complete interface to navigate all tables links
            to the request.args(0)
            table: pagination, search, view, edit, delete,
                   children, parent, etc.

        constraints is a dict {'table':query} that limits which
        records can be accessible
        links is a dict like
           {'tablename':[lambda row: A(....), ...]}
        that will add buttons when table tablename is displayed
        linked_tables is a optional list of tablenames of tables
        to be linked
        """
        request, T = current.request, current.T
        if args is None:
            args = []

        def url(**b):
            b['args'] = request.args[:nargs] + b.get('args', [])
            b['hash_vars'] = False
            b['user_signature'] = user_signature
            return URL(**b)

        db = table._db
        breadcrumbs = []
        if request.args(len(args)) != table._tablename:
            request.args[:] = args + [table._tablename]
        if links is None:
            links = {}
        if constraints is None:
            constraints = {}
        field = None
        name = None
        def format(table,row):
            if not row:
                return T('Unknown')
            elif isinstance(table._format,str):
                return table._format % row
            elif callable(table._format):
                return table._format(row)
            else:
                return '#'+str(row.id)
        try:
            nargs = len(args) + 1
            previous_tablename, previous_fieldname, previous_id = \
                table._tablename, None, None
            while len(request.args) > nargs:
                key = request.args(nargs)
                if '.' in key:
                    id = request.args(nargs + 1)
                    tablename, fieldname = key.split('.', 1)
                    table = db[tablename]
                    field = table[fieldname]
                    field.default = id
                    referee = field.type[10:]
                    if referee != previous_tablename:
                        raise HTTP(400)
                    cond = constraints.get(referee, None)
                    if cond:
                        record = db(
                            db[referee]._id == id)(cond).select().first()
                    else:
                        record = db[referee](id)
                    if previous_id:
                        if record[previous_fieldname] != int(previous_id):
                            raise HTTP(400)
                    previous_tablename, previous_fieldname, previous_id = \
                        tablename, fieldname, id
                    name = format(db[referee],record)
                    breadcrumbs.append(
                        LI(A(T(db[referee]._plural),
                             _class=trap_class(),
                             _href=url()),
                           SPAN(divider, _class='divider'),
                           _class='w2p_grid_breadcrumb_elem'))
                    if kwargs.get('details', True):
                        breadcrumbs.append(
                            LI(A(name, _class=trap_class(),
                                 _href=url(args=['view', referee, id])),
                               SPAN(divider, _class='divider'),
                               _class='w2p_grid_breadcrumb_elem'))
                    nargs += 2
                else:
                    break
            if nargs > len(args) + 1:
                query = (field == id)
                # cjk
                # if isinstance(linked_tables, dict):
                #     linked_tables = linked_tables.get(table._tablename, [])
                if linked_tables is None or referee in linked_tables:
                    field.represent = lambda id, r=None, referee=referee, rep=field.represent: A(callable(rep) and rep(id) or id, _class=trap_class(), _href=url(args=['view', referee, id]))
        except (KeyError, ValueError, TypeError):
            redirect(URL(args=table._tablename))
        if nargs == len(args) + 1:
            query = table._db._adapter.id_query(table)

        # filter out data info for displayed table
        if table._tablename in constraints:
            query = query & constraints[table._tablename]
        if isinstance(links, dict):
            links = links.get(table._tablename, [])
        for key in 'columns,orderby,searchable,sortable,paginate,deletable,editable,details,selectable,create,fields'.split(','):
            if isinstance(kwargs.get(key, None), dict):
                if table._tablename in kwargs[key]:
                    kwargs[key] = kwargs[key][table._tablename]
                else:
                    del kwargs[key]
        check = {}
        id_field_name = table._id.name
        for rfield in table._referenced_by:
            check[rfield.tablename] = \
                check.get(rfield.tablename, []) + [rfield.name]
        if isinstance(linked_tables, dict):
            for tbl in linked_tables.keys():
                tb = db[tbl]
                if isinstance(linked_tables[tbl], list):
                        if len(linked_tables[tbl]) > 1:
                            t = T('%s(%s)' %(tbl, fld))
                        else:
                            t = T(tb._plural)
                        for fld in linked_tables[tbl]:
                            if fld not in db[tbl].fields:
                                raise ValueError('Field %s not in table' %fld)
                            args0 = tbl + '.' + fld
                            links.append(
                                lambda row, t=t, nargs=nargs, args0=args0:
                                A(SPAN(t), _class=trap_class(), _href=url(
                                  args=[args0, row[id_field_name]])))
                else:
                    t = T(tb._plural)
                    fld = linked_tables[tbl]
                    if fld not in db[tbl].fields:
                        raise ValueError('Field %s not in table' %fld)
                    args0 = tbl + '.' + fld
                    links.append(
                        lambda row, t=t, nargs=nargs, args0=args0:
                        A(SPAN(t), _class=trap_class(), _href=url(
                          args=[args0, row[id_field_name]])))
        else:
            for tablename in sorted(check):
                linked_fieldnames = check[tablename]
                tb = db[tablename]
                multiple_links = len(linked_fieldnames) > 1
                for fieldname in linked_fieldnames:
                    if linked_tables is None or tablename in linked_tables:
                        t = T(tb._plural) if not multiple_links else \
                            T(tb._plural + '(' + fieldname + ')')
                        args0 = tablename + '.' + fieldname
                        links.append(
                            lambda row, t=t, nargs=nargs, args0=args0:
                            A(SPAN(t), _class=trap_class(), _href=url(
                              args=[args0, row[id_field_name]])))

        grid = SQLFORM.grid(query, args=request.args[:nargs], links=links,
                            links_in_grid=links_in_grid,
                            user_signature=user_signature, **kwargs)

        if isinstance(grid, DIV):
            header = table._plural
            next = grid.create_form or grid.update_form or grid.view_form
            breadcrumbs.append(LI(
                    A(T(header), _class=trap_class(),_href=url()),
                    SPAN(divider, _class='divider') if next else '',
                    _class='active w2p_grid_breadcrumb_elem'))
            if grid.create_form:
                header = T('New %(entity)s') % dict(entity=table._singular)
            elif grid.update_form:
                header = T('Edit %(entity)s') % dict(
                    entity=format(grid.update_form.table,
                                  grid.update_form.record))
            elif grid.view_form:
                header = T('View %(entity)s') % dict(
                    entity=format(grid.view_form.table,
                                  grid.view_form.record))
            if next:
                breadcrumbs.append(LI(
                            A(T(header), _class=trap_class(),_href=url()),
                            _class='active w2p_grid_breadcrumb_elem'))
            grid.insert(
                0, DIV(UL(*breadcrumbs, **{'_class': breadcrumbs_class}),
                       _class='web2py_breadcrumbs'))
        return grid


class SQLTABLE(TABLE):

    """
    given a Rows object, as returned by a db().select(), generates
    an html table with the rows.

    optional arguments:

    :param linkto: URL (or lambda to generate a URL) to edit individual records
    :param upload: URL to download uploaded files
    :param orderby: Add an orderby link to column headers.
    :param headers: dictionary of headers to headers redefinions
                    headers can also be a string to gerenare the headers from data
                    for now only headers="fieldname:capitalize",
                    headers="labels" and headers=None are supported
    :param truncate: length at which to truncate text in table cells.
        Defaults to 16 characters.
    :param columns: a list or dict contaning the names of the columns to be shown
        Defaults to all

    Optional names attributes for passed to the <table> tag

    The keys of headers and columns must be of the form "tablename.fieldname"

    Simple linkto example::

        rows = db.select(db.sometable.ALL)
        table = SQLTABLE(rows, linkto='someurl')

    This will link rows[id] to .../sometable/value_of_id


    More advanced linkto example::

        def mylink(field, type, ref):
            return URL(args=[field])

        rows = db.select(db.sometable.ALL)
        table = SQLTABLE(rows, linkto=mylink)

    This will link rows[id] to
        current_app/current_controlle/current_function/value_of_id

    New Implements: 24 June 2011:
    -----------------------------

    :param selectid: The id you want to select
    :param renderstyle: Boolean render the style with the table

    :param extracolumns = [{'label':A('Extra',_href='#'),
                    'class': '', #class name of the header
                    'width':'', #width in pixels or %
                    'content':lambda row, rc: A('Edit',_href='edit/%s'%row.id),
                    'selected': False #agregate class selected to this column
                    }]


    :param headers = {'table.id':{'label':'Id',
                           'class':'', #class name of the header
                           'width':'', #width in pixels or %
                           'truncate': 16, #truncate the content to...
                           'selected': False #agregate class selected to this column
                           },
               'table.myfield':{'label':'My field',
                                'class':'', #class name of the header
                                'width':'', #width in pixels or %
                                'truncate': 16, #truncate the content to...
                                'selected': False #agregate class selected to this column
                                },
               }

    table = SQLTABLE(rows, headers=headers, extracolumns=extracolumns)
`<

    """

    def __init__(
        self,
        sqlrows,
        linkto=None,
        upload=None,
        orderby=None,
        headers={},
        truncate=16,
        columns=None,
        th_link='',
        extracolumns=None,
        selectid=None,
        renderstyle=False,
        cid=None,
        **attributes
        ):

        TABLE.__init__(self, **attributes)

        self.components = []
        self.attributes = attributes
        self.sqlrows = sqlrows
        (components, row) = (self.components, [])
        if not sqlrows:
            return
        if not columns:
            columns = sqlrows.colnames
        if headers == 'fieldname:capitalize':
            headers = {}
            for c in columns:
                headers[c] = c.split('.')[-1].replace('_', ' ').title()
        elif headers == 'labels':
            headers = {}
            for c in columns:
                (t, f) = c.split('.')
                field = sqlrows.db[t][f]
                headers[c] = field.label
        if headers is None:
            headers = {}
        else:
            for c in columns:  # new implement dict
                if isinstance(headers.get(c, c), dict):
                    coldict = headers.get(c, c)
                    attrcol = dict()
                    if coldict['width'] != "":
                        attrcol.update(_width=coldict['width'])
                    if coldict['class'] != "":
                        attrcol.update(_class=coldict['class'])
                    row.append(TH(coldict['label'], **attrcol))
                elif orderby:
                    row.append(TH(A(headers.get(c, c),
                                    _href=th_link + '?orderby=' + c, cid=cid)))
                else:
                    row.append(TH(headers.get(c, c)))

            if extracolumns:  # new implement dict
                for c in extracolumns:
                    attrcol = dict()
                    if c['width'] != "":
                        attrcol.update(_width=c['width'])
                    if c['class'] != "":
                        attrcol.update(_class=c['class'])
                    row.append(TH(c['label'], **attrcol))

            components.append(THEAD(TR(*row)))

        tbody = []
        for (rc, record) in enumerate(sqlrows):
            row = []
            if rc % 2 == 0:
                _class = 'even'
            else:
                _class = 'odd'

            if not selectid is None:  # new implement
                if record.get('id') == selectid:
                    _class += ' rowselected'

            for colname in columns:
                if not table_field.match(colname):
                    if "_extra" in record and colname in record._extra:
                        r = record._extra[colname]
                        row.append(TD(r))
                        continue
                    else:
                        raise KeyError(
                            "Column %s not found (SQLTABLE)" % colname)
                (tablename, fieldname) = colname.split('.')
                try:
                    field = sqlrows.db[tablename][fieldname]
                except (KeyError, AttributeError):
                    field = None
                if tablename in record \
                        and isinstance(record, Row) \
                        and isinstance(record[tablename], Row):
                    r = record[tablename][fieldname]
                elif fieldname in record:
                    r = record[fieldname]
                else:
                    raise SyntaxError('something wrong in Rows object')
                r_old = r
                if not field or isinstance(field, (Field.Virtual, Field.Lazy)):
                    pass
                elif linkto and field.type == 'id':
                    try:
                        href = linkto(r, 'table', tablename)
                    except TypeError:
                        href = '%s/%s/%s' % (linkto, tablename, r_old)
                    r = A(r, _href=href)
                elif isinstance(field.type, str) and field.type.startswith('reference'):
                    if linkto:
                        ref = field.type[10:]
                        try:
                            href = linkto(r, 'reference', ref)
                        except TypeError:
                            href = '%s/%s/%s' % (linkto, ref, r_old)
                            if ref.find('.') >= 0:
                                tref, fref = ref.split('.')
                                if hasattr(sqlrows.db[tref], '_primarykey'):
                                    href = '%s/%s?%s' % (linkto, tref, urllib.urlencode({fref: r}))
                        r = A(represent(field, r, record), _href=str(href))
                    elif field.represent:
                        r = represent(field, r, record)
                elif linkto and hasattr(field._table, '_primarykey')\
                        and fieldname in field._table._primarykey:
                    # have to test this with multi-key tables
                    key = urllib.urlencode(dict([
                                ((tablename in record
                                      and isinstance(record, Row)
                                      and isinstance(record[tablename], Row)) and
                                 (k, record[tablename][k])) or (k, record[k])
                                    for k in field._table._primarykey]))
                    r = A(r, _href='%s/%s?%s' % (linkto, tablename, key))
                elif isinstance(field.type, str) and field.type.startswith('list:'):
                    r = represent(field, r or [], record)
                elif field.represent:
                    r = represent(field, r, record)
                elif field.type == 'blob' and r:
                    r = 'DATA'
                elif field.type == 'upload':
                    if upload and r:
                        r = A(current.T('file'), _href='%s/%s' % (upload, r))
                    elif r:
                        r = current.T('file')
                    else:
                        r = ''
                elif field.type in ['string', 'text']:
                    r = str(field.formatter(r))
                    if headers != {}:  # new implement dict
                        if isinstance(headers[colname], dict):
                            if isinstance(headers[colname]['truncate'], int):
                                r = truncate_string(
                                    r, headers[colname]['truncate'])
                    elif not truncate is None:
                        r = truncate_string(r, truncate)
                attrcol = dict()  # new implement dict
                if headers != {}:
                    if isinstance(headers[colname], dict):
                        colclass = headers[colname]['class']
                        if headers[colname]['selected']:
                            colclass = str(headers[colname]
                                           ['class'] + " colselected").strip()
                        if colclass != "":
                            attrcol.update(_class=colclass)

                row.append(TD(r, **attrcol))

            if extracolumns:  # new implement dict
                for c in extracolumns:
                    attrcol = dict()
                    colclass = c['class']
                    if c['selected']:
                        colclass = str(c['class'] + " colselected").strip()
                    if colclass != "":
                        attrcol.update(_class=colclass)
                    contentfunc = c['content']
                    row.append(TD(contentfunc(record, rc), **attrcol))

            tbody.append(TR(_class=_class, *row))

        if renderstyle:
            components.append(STYLE(self.style()))

        components.append(TBODY(*tbody))

    def style(self):

        css = '''
        table tbody tr.odd {
            background-color: #DFD;
        }
        table tbody tr.even {
            background-color: #EFE;
        }
        table tbody tr.rowselected {
            background-color: #FDD;
        }
        table tbody tr td.colselected {
            background-color: #FDD;
        }
        table tbody tr:hover {
            background: #DDF;
        }
        '''

        return css

form_factory = SQLFORM.factory  # for backward compatibility, deprecated


class ExportClass(object):
    label = None
    file_ext = None
    content_type = None

    def __init__(self, rows):
        self.rows = rows

    def represented(self):
        def none_exception(value):
            """
            returns a cleaned up value that can be used for csv export:
            - unicode text is encoded as such
            - None values are replaced with the given representation (default <NULL>)
            """
            if value is None:
                return '<NULL>'
            elif isinstance(value, unicode):
                return value.encode('utf8')
            elif isinstance(value, Reference):
                return int(value)
            elif hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            elif isinstance(value, (list, tuple)):  # for type='list:..'
                return bar_encode(value)
            return value

        represented = []
        for record in self.rows:
            row = []
            for col in self.rows.colnames:
                if not REGEX_TABLE_DOT_FIELD.match(col):
                    row.append(record._extra[col])
                else:
                    (t, f) = col.split('.')
                    field = self.rows.db[t][f]
                    if isinstance(record.get(t, None), (Row, dict)):
                        value = record[t][f]
                    else:
                        value = record[f]
                    if field.type == 'blob' and not value is None:
                        value = ''
                    elif field.represent:
                        value = field.represent(value, record)
                    row.append(none_exception(value))

            represented.append(row)
        return represented

    def export(self):
        raise NotImplementedError


class ExporterTSV(ExportClass):

    label = 'TSV'
    file_ext = "csv"
    content_type = "text/tab-separated-values"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):

        out = cStringIO.StringIO()
        final = cStringIO.StringIO()
        import csv
        writer = csv.writer(out, delimiter='\t')
        if self.rows:
            import codecs
            final.write(codecs.BOM_UTF16)
            writer.writerow(
                [unicode(col).encode("utf8") for col in self.rows.colnames])
            data = out.getvalue().decode("utf8")
            data = data.encode("utf-16")
            data = data[2:]
            final.write(data)
            out.truncate(0)
        records = self.represented()
        for row in records:
            writer.writerow(
                [str(col).decode('utf8').encode("utf-8") for col in row])
            data = out.getvalue().decode("utf8")
            data = data.encode("utf-16")
            data = data[2:]
            final.write(data)
            out.truncate(0)
        return str(final.getvalue())


class ExporterCSV(ExportClass):
    label = 'CSV'
    file_ext = "csv"
    content_type = "text/csv"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):
        if self.rows:
            return self.rows.as_csv()
        else:
            return ''

class ExporterHTML(ExportClass):
    label = 'HTML'
    file_ext = "html"
    content_type = "text/html"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):
        if self.rows:
            return self.rows.xml()
        else:
            return '<html>\n<body>\n<table>\n</table>\n</body>\n</html>'

class ExporterXML(ExportClass):
    label = 'XML'
    file_ext = "xml"
    content_type = "text/xml"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):
        if self.rows:
            return self.rows.as_xml()
        else:
            return '<rows></rows>'

class ExporterJSON(ExportClass):
    label = 'JSON'
    file_ext = "json"
    content_type = "application/json"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):
        if self.rows:
            return self.rows.as_json()
        else:
            return 'null'

########NEW FILE########
__FILENAME__ = storage
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Provides:

- List; like list but returns None instead of IndexOutOfBounds
- Storage; like dictionary allowing also for `obj.foo` for `obj['foo']`
"""

import cPickle
import portalocker

__all__ = ['List', 'Storage', 'Settings', 'Messages',
           'StorageList', 'load_storage', 'save_storage']

DEFAULT = lambda:0

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`, and setting obj.foo = None deletes item foo.

        >>> o = Storage(a=1)
        >>> print o.a
        1

        >>> o['a']
        1

        >>> o.a = 2
        >>> print o['a']
        2

        >>> del o.a
        >>> print o.a
        None
    """
    __slots__ = ()
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __getitem__ = dict.get
    __getattr__ = dict.get
    __repr__ = lambda self: '<Storage %s>' % dict.__repr__(self)
    # http://stackoverflow.com/questions/5247250/why-does-pickle-getstate-accept-as-a-return-value-the-very-instance-it-requi
    __getstate__ = lambda self: None
    __copy__ = lambda self: Storage(self)

    def getlist(self, key):
        """
        Return a Storage value as a list.

        If the value is a list it will be returned as-is.
        If object is None, an empty list will be returned.
        Otherwise, [value] will be returned.

        Example output for a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getlist('x')
        ['abc']
        >>> request.vars.getlist('y')
        ['abc', 'def']
        >>> request.vars.getlist('z')
        []
        """
        value = self.get(key, [])
        if value is None or isinstance(value, (list, tuple)):
            return value
        else:
            return [value]

    def getfirst(self, key, default=None):
        """
        Return the first or only value when given a request.vars-style key.

        If the value is a list, its first item will be returned;
        otherwise, the value will be returned as-is.

        Example output for a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getfirst('x')
        'abc'
        >>> request.vars.getfirst('y')
        'abc'
        >>> request.vars.getfirst('z')
        """
        values = self.getlist(key)
        return values[0] if values else default

    def getlast(self, key, default=None):
        """
        Returns the last or only single value when
        given a request.vars-style key.

        If the value is a list, the last item will be returned;
        otherwise, the value will be returned as-is.

        Simulated output with a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getlast('x')
        'abc'
        >>> request.vars.getlast('y')
        'def'
        >>> request.vars.getlast('z')
        """
        values = self.getlist(key)
        return values[-1] if values else default

PICKABLE = (str, int, long, float, bool, list, dict, tuple, set)


class StorageList(Storage):
    """
    like Storage but missing elements default to [] instead of None
    """
    def __getitem__(self, key):
        return self.__getattr__(key)

    def __getattr__(self, key):
        if key in self:
            return getattr(self, key)
        else:
            r = []
            setattr(self, key, r)
            return r


def load_storage(filename):
    fp = None
    try:
        fp = portalocker.LockedFile(filename, 'rb')
        storage = cPickle.load(fp)
    finally:
        if fp:
            fp.close()
    return Storage(storage)


def save_storage(storage, filename):
    fp = None
    try:
        fp = portalocker.LockedFile(filename, 'wb')
        cPickle.dump(dict(storage), fp)
    finally:
        if fp:
            fp.close()


class Settings(Storage):
    def __setattr__(self, key, value):
        if key != 'lock_keys' and self['lock_keys'] and key not in self:
            raise SyntaxError('setting key \'%s\' does not exist' % key)
        if key != 'lock_values' and self['lock_values']:
            raise SyntaxError('setting value cannot be changed: %s' % key)
        self[key] = value


class Messages(Settings):
    def __init__(self, T):
        Storage.__init__(self, T=T)

    def __getattr__(self, key):
        value = self[key]
        if isinstance(value, str):
            return str(self.T(value))
        return value

class FastStorage(dict):
    """
    Eventually this should replace class Storage but causes memory leak
    because of http://bugs.python.org/issue1469629

    >>> s = FastStorage()
    >>> s.a = 1
    >>> s.a
    1
    >>> s['a']
    1
    >>> s.b
    >>> s['b']
    >>> s['b']=2
    >>> s['b']
    2
    >>> s.b
    2
    >>> isinstance(s,dict)
    True
    >>> dict(s)
    {'a': 1, 'b': 2}
    >>> dict(FastStorage(s))
    {'a': 1, 'b': 2}
    >>> import pickle
    >>> s = pickle.loads(pickle.dumps(s))
    >>> dict(s)
    {'a': 1, 'b': 2}
    >>> del s.b
    >>> del s.a
    >>> s.a
    >>> s.b
    >>> s['a']
    >>> s['b']
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self

    def __getattr__(self, key):
        return getattr(self, key) if key in self else None

    def __getitem__(self, key):
        return dict.get(self, key, None)

    def copy(self):
        self.__dict__ = {}
        s = FastStorage(self)
        self.__dict__ = self
        return s

    def __repr__(self):
        return '<Storage %s>' % dict.__repr__(self)

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, sdict):
        dict.__init__(self, sdict)
        self.__dict__ = self

    def update(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class List(list):
    """
    Like a regular python list but a[i] if i is out of bounds return None
    instead of IndexOutOfBounds
    """

    def __call__(self, i, default=DEFAULT, cast=None, otherwise=None):
        """
        request.args(0,default=0,cast=int,otherwise='http://error_url')
        request.args(0,default=0,cast=int,otherwise=lambda:...)
        """
        n = len(self)
        if 0 <= i < n or -n <= i < 0:
            value = self[i]
        elif default is DEFAULT:
            value = None
        else:
            value, cast = default, False
        if cast:
            try:
                value = cast(value)
            except (ValueError, TypeError):
                from http import HTTP, redirect
                if otherwise is None:
                    raise HTTP(404)
                elif isinstance(otherwise, str):
                    redirect(otherwise)
                elif callable(otherwise):
                    return otherwise()
                else:
                    raise RuntimeError("invalid otherwise")
        return value


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework (Copyrighted, 2007-2011).
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Author: Thadeus Burgess

Contributors:

- Thank you to Massimo Di Pierro for creating the original gluon/template.py
- Thank you to Jonathan Lundell for extensively testing the regex on Jython.
- Thank you to Limodou (creater of uliweb) who inspired the block-element support for web2py.
"""

import os
import cgi
import logging
from re import compile, sub, escape, DOTALL
try:
    import cStringIO as StringIO
except:
    from io import StringIO

try:
    # have web2py
    from restricted import RestrictedError
    from globals import current
except ImportError:
    # do not have web2py
    current = None

    def RestrictedError(a, b, c):
        logging.error(str(a) + ':' + str(b) + ':' + str(c))
        return RuntimeError


class Node(object):
    """
    Basic Container Object
    """
    def __init__(self, value=None, pre_extend=False):
        self.value = value
        self.pre_extend = pre_extend

    def __str__(self):
        return str(self.value)


class SuperNode(Node):
    def __init__(self, name='', pre_extend=False):
        self.name = name
        self.value = None
        self.pre_extend = pre_extend

    def __str__(self):
        if self.value:
            return str(self.value)
        else:
            # raise SyntaxError("Undefined parent block ``%s``. \n" % self.name + "You must define a block before referencing it.\nMake sure you have not left out an ``{{end}}`` tag." )
            return ''

    def __repr__(self):
        return "%s->%s" % (self.name, self.value)


def output_aux(node, blocks):
    # If we have a block level
    #   If we can override this block.
    #     Override block from vars.
    #   Else we take the default
    # Else its just a string
    return (blocks[node.name].output(blocks)
            if node.name in blocks else
            node.output(blocks)) \
        if isinstance(node, BlockNode) \
        else str(node)


class BlockNode(Node):
    """
    Block Container.

    This Node can contain other Nodes and will render in a hierarchical order
    of when nodes were added.

    ie::

        {{ block test }}
            This is default block test
        {{ end }}
    """
    def __init__(self, name='', pre_extend=False, delimiters=('{{', '}}')):
        """
        name - Name of this Node.
        """
        self.nodes = []
        self.name = name
        self.pre_extend = pre_extend
        self.left, self.right = delimiters

    def __repr__(self):
        lines = ['%sblock %s%s' % (self.left, self.name, self.right)]
        lines += [str(node) for node in self.nodes]
        lines.append('%send%s' % (self.left, self.right))
        return ''.join(lines)

    def __str__(self):
        """
        Get this BlockNodes content, not including child Nodes
        """
        return ''.join(str(node) for node in self.nodes
                       if not isinstance(node, BlockNode))

    def append(self, node):
        """
        Add an element to the nodes.

        Keyword Arguments

        - node -- Node object or string to append.
        """
        if isinstance(node, str) or isinstance(node, Node):
            self.nodes.append(node)
        else:
            raise TypeError("Invalid type; must be instance of ``str`` or ``BlockNode``. %s" % node)

    def extend(self, other):
        """
        Extend the list of nodes with another BlockNode class.

        Keyword Arguments

        - other -- BlockNode or Content object to extend from.
        """
        if isinstance(other, BlockNode):
            self.nodes.extend(other.nodes)
        else:
            raise TypeError(
                "Invalid type; must be instance of ``BlockNode``. %s" % other)

    def output(self, blocks):
        """
        Merges all nodes into a single string.
        blocks -- Dictionary of blocks that are extending
        from this template.
        """
        return ''.join(output_aux(node, blocks) for node in self.nodes)


class Content(BlockNode):
    """
    Parent Container -- Used as the root level BlockNode.

    Contains functions that operate as such.
    """
    def __init__(self, name="ContentBlock", pre_extend=False):
        """
        Keyword Arguments

        name -- Unique name for this BlockNode
        """
        self.name = name
        self.nodes = []
        self.blocks = {}
        self.pre_extend = pre_extend

    def __str__(self):
        return ''.join(output_aux(node, self.blocks) for node in self.nodes)

    def _insert(self, other, index=0):
        """
        Inserts object at index.
        """
        if isinstance(other, (str, Node)):
            self.nodes.insert(index, other)
        else:
            raise TypeError(
                "Invalid type, must be instance of ``str`` or ``Node``.")

    def insert(self, other, index=0):
        """
        Inserts object at index.

        You may pass a list of objects and have them inserted.
        """
        if isinstance(other, (list, tuple)):
            # Must reverse so the order stays the same.
            other.reverse()
            for item in other:
                self._insert(item, index)
        else:
            self._insert(other, index)

    def append(self, node):
        """
        Adds a node to list. If it is a BlockNode then we assign a block for it.
        """
        if isinstance(node, (str, Node)):
            self.nodes.append(node)
            if isinstance(node, BlockNode):
                self.blocks[node.name] = node
        else:
            raise TypeError("Invalid type, must be instance of ``str`` or ``BlockNode``. %s" % node)

    def extend(self, other):
        """
        Extends the objects list of nodes with another objects nodes
        """
        if isinstance(other, BlockNode):
            self.nodes.extend(other.nodes)
            self.blocks.update(other.blocks)
        else:
            raise TypeError(
                "Invalid type; must be instance of ``BlockNode``. %s" % other)

    def clear_content(self):
        self.nodes = []


class TemplateParser(object):

    default_delimiters = ('{{', '}}')
    r_tag = compile(r'(\{\{.*?\}\})', DOTALL)

    r_multiline = compile(r'(""".*?""")|(\'\'\'.*?\'\'\')', DOTALL)

    # These are used for re-indentation.
    # Indent + 1
    re_block = compile('^(elif |else:|except:|except |finally:).*$', DOTALL)

    # Indent - 1
    re_unblock = compile('^(return|continue|break|raise)( .*)?$', DOTALL)
    # Indent - 1
    re_pass = compile('^pass( .*)?$', DOTALL)

    def __init__(self, text,
                 name="ParserContainer",
                 context=dict(),
                 path='views/',
                 writer='response.write',
                 lexers={},
                 delimiters=('{{', '}}'),
                 _super_nodes = [],
                 ):
        """
        text -- text to parse
        context -- context to parse in
        path -- folder path to templates
        writer -- string of writer class to use
        lexers -- dict of custom lexers to use.
        delimiters -- for example ('{{','}}')
        _super_nodes -- a list of nodes to check for inclusion
                        this should only be set by "self.extend"
                        It contains a list of SuperNodes from a child
                        template that need to be handled.
        """

        # Keep a root level name.
        self.name = name
        # Raw text to start parsing.
        self.text = text
        # Writer to use (refer to the default for an example).
        # This will end up as
        # "%s(%s, escape=False)" % (self.writer, value)
        self.writer = writer

        # Dictionary of custom name lexers to use.
        if isinstance(lexers, dict):
            self.lexers = lexers
        else:
            self.lexers = {}

        # Path of templates
        self.path = path
        # Context for templates.
        self.context = context

        # allow optional alternative delimiters
        self.delimiters = delimiters
        if delimiters != self.default_delimiters:
            escaped_delimiters = (escape(delimiters[0]),
                                  escape(delimiters[1]))
            self.r_tag = compile(r'(%s.*?%s)' % escaped_delimiters, DOTALL)
        elif hasattr(context.get('response', None), 'delimiters'):
            if context['response'].delimiters != self.default_delimiters:
                escaped_delimiters = (
                    escape(context['response'].delimiters[0]),
                    escape(context['response'].delimiters[1]))
                self.r_tag = compile(r'(%s.*?%s)' % escaped_delimiters,
                                     DOTALL)

        # Create a root level Content that everything will go into.
        self.content = Content(name=name)

        # Stack will hold our current stack of nodes.
        # As we descend into a node, it will be added to the stack
        # And when we leave, it will be removed from the stack.
        # self.content should stay on the stack at all times.
        self.stack = [self.content]

        # This variable will hold a reference to every super block
        # that we come across in this template.
        self.super_nodes = []

        # This variable will hold a reference to the child
        # super nodes that need handling.
        self.child_super_nodes = _super_nodes

        # This variable will hold a reference to every block
        # that we come across in this template
        self.blocks = {}

        # Begin parsing.
        self.parse(text)

    def to_string(self):
        """
        Return the parsed template with correct indentation.

        Used to make it easier to port to python3.
        """
        return self.reindent(str(self.content))

    def __str__(self):
        "Make sure str works exactly the same as python 3"
        return self.to_string()

    def __unicode__(self):
        "Make sure str works exactly the same as python 3"
        return self.to_string()

    def reindent(self, text):
        """
        Reindents a string of unindented python code.
        """

        # Get each of our lines into an array.
        lines = text.split('\n')

        # Our new lines
        new_lines = []

        # Keeps track of how many indents we have.
        # Used for when we need to drop a level of indentation
        # only to reindent on the next line.
        credit = 0

        # Current indentation
        k = 0

        #################
        # THINGS TO KNOW
        #################

        # k += 1 means indent
        # k -= 1 means unindent
        # credit = 1 means unindent on the next line.

        for raw_line in lines:
            line = raw_line.strip()

            # ignore empty lines
            if not line:
                continue

            # If we have a line that contains python code that
            # should be unindented for this line of code.
            # and then reindented for the next line.
            if TemplateParser.re_block.match(line):
                k = k + credit - 1

            # We obviously can't have a negative indentation
            k = max(k, 0)

            # Add the indentation!
            new_lines.append(' ' * (4 * k) + line)

            # Bank account back to 0 again :(
            credit = 0

            # If we are a pass block, we obviously de-dent.
            if TemplateParser.re_pass.match(line):
                k -= 1

            # If we are any of the following, de-dent.
            # However, we should stay on the same level
            # But the line right after us will be de-dented.
            # So we add one credit to keep us at the level
            # while moving back one indentation level.
            if TemplateParser.re_unblock.match(line):
                credit = 1
                k -= 1

            # If we are an if statement, a try, or a semi-colon we
            # probably need to indent the next line.
            if line.endswith(':') and not line.startswith('#'):
                k += 1

        # This must come before so that we can raise an error with the
        # right content.
        new_text = '\n'.join(new_lines)

        if k > 0:
            self._raise_error('missing "pass" in view', new_text)
        elif k < 0:
            self._raise_error('too many "pass" in view', new_text)

        return new_text

    def _raise_error(self, message='', text=None):
        """
        Raise an error using itself as the filename and textual content.
        """
        raise RestrictedError(self.name, text or self.text, message)

    def _get_file_text(self, filename):
        """
        Attempt to open ``filename`` and retrieve its text.

        This will use self.path to search for the file.
        """

        # If they didn't specify a filename, how can we find one!
        if not filename.strip():
            self._raise_error('Invalid template filename')

        # Allow Views to include other views dynamically
        context = self.context
        if current and not "response" in context:
            context["response"] = getattr(current, 'response', None)

        # Get the filename; filename looks like ``"template.html"``.
        # We need to eval to remove the quotes and get the string type.
        filename = eval(filename, context)

        # Get the path of the file on the system.
        filepath = self.path and os.path.join(self.path, filename) or filename

        # try to read the text.
        try:
            fileobj = open(filepath, 'rb')
            text = fileobj.read()
            fileobj.close()
        except IOError:
            self._raise_error('Unable to open included view file: ' + filepath)

        return text

    def include(self, content, filename):
        """
        Include ``filename`` here.
        """
        text = self._get_file_text(filename)

        t = TemplateParser(text,
                           name=filename,
                           context=self.context,
                           path=self.path,
                           writer=self.writer,
                           delimiters=self.delimiters)

        content.append(t.content)

    def extend(self, filename):
        """
        Extend ``filename``. Anything not declared in a block defined by the
        parent will be placed in the parent templates ``{{include}}`` block.
        """
        text = self._get_file_text(filename)

        # Create out nodes list to send to the parent
        super_nodes = []
        # We want to include any non-handled nodes.
        super_nodes.extend(self.child_super_nodes)
        # And our nodes as well.
        super_nodes.extend(self.super_nodes)

        t = TemplateParser(text,
                           name=filename,
                           context=self.context,
                           path=self.path,
                           writer=self.writer,
                           delimiters=self.delimiters,
                           _super_nodes=super_nodes)

        # Make a temporary buffer that is unique for parent
        # template.
        buf = BlockNode(
            name='__include__' + filename, delimiters=self.delimiters)
        pre = []

        # Iterate through each of our nodes
        for node in self.content.nodes:
            # If a node is a block
            if isinstance(node, BlockNode):
                # That happens to be in the parent template
                if node.name in t.content.blocks:
                    # Do not include it
                    continue

            if isinstance(node, Node):
                # Or if the node was before the extension
                # we should not include it
                if node.pre_extend:
                    pre.append(node)
                    continue

            # Otherwise, it should go int the
            # Parent templates {{include}} section.
                buf.append(node)
            else:
                buf.append(node)

        # Clear our current nodes. We will be replacing this with
        # the parent nodes.
        self.content.nodes = []

        t_content = t.content

        # Set our include, unique by filename
        t_content.blocks['__include__' + filename] = buf

        # Make sure our pre_extended nodes go first
        t_content.insert(pre)

        # Then we extend our blocks
        t_content.extend(self.content)

        # Work off the parent node.
        self.content = t_content

    def parse(self, text):

        # Basically, r_tag.split will split the text into
        # an array containing, 'non-tag', 'tag', 'non-tag', 'tag'
        # so if we alternate this variable, we know
        # what to look for. This is alternate to
        # line.startswith("{{")
        in_tag = False
        extend = None
        pre_extend = True

        # Use a list to store everything in
        # This is because later the code will "look ahead"
        # for missing strings or brackets.
        ij = self.r_tag.split(text)
        # j = current index
        # i = current item
        stack = self.stack
        for j in range(len(ij)):
            i = ij[j]

            if i:
                if not stack:
                    self._raise_error('The "end" tag is unmatched, please check if you have a starting "block" tag')

                # Our current element in the stack.
                top = stack[-1]

                if in_tag:
                    line = i

                    # Get rid of delimiters
                    line = line[len(self.delimiters[0]):-len(self.delimiters[1])].strip()

                    # This is bad juju, but let's do it anyway
                    if not line:
                        continue

                    # We do not want to replace the newlines in code,
                    # only in block comments.
                    def remove_newline(re_val):
                        # Take the entire match and replace newlines with
                        # escaped newlines.
                        return re_val.group(0).replace('\n', '\\n')

                    # Perform block comment escaping.
                    # This performs escaping ON anything
                    # in between """ and """
                    line = sub(TemplateParser.r_multiline,
                               remove_newline,
                               line)

                    if line.startswith('='):
                        # IE: {{=response.title}}
                        name, value = '=', line[1:].strip()
                    else:
                        v = line.split(' ', 1)
                        if len(v) == 1:
                            # Example
                            # {{ include }}
                            # {{ end }}
                            name = v[0]
                            value = ''
                        else:
                            # Example
                            # {{ block pie }}
                            # {{ include "layout.html" }}
                            # {{ for i in range(10): }}
                            name = v[0]
                            value = v[1]

                    # This will replace newlines in block comments
                    # with the newline character. This is so that they
                    # retain their formatting, but squish down to one
                    # line in the rendered template.

                    # First check if we have any custom lexers
                    if name in self.lexers:
                        # Pass the information to the lexer
                        # and allow it to inject in the environment

                        # You can define custom names such as
                        # '{{<<variable}}' which could potentially
                        # write unescaped version of the variable.
                        self.lexers[name](parser=self,
                                          value=value,
                                          top=top,
                                          stack=stack)

                    elif name == '=':
                        # So we have a variable to insert into
                        # the template
                        buf = "\n%s(%s)" % (self.writer, value)
                        top.append(Node(buf, pre_extend=pre_extend))

                    elif name == 'block' and not value.startswith('='):
                        # Make a new node with name.
                        node = BlockNode(name=value.strip(),
                                         pre_extend=pre_extend,
                                         delimiters=self.delimiters)

                        # Append this node to our active node
                        top.append(node)

                        # Make sure to add the node to the stack.
                        # so anything after this gets added
                        # to this node. This allows us to
                        # "nest" nodes.
                        stack.append(node)

                    elif name == 'end' and not value.startswith('='):
                        # We are done with this node.

                        # Save an instance of it
                        self.blocks[top.name] = top

                        # Pop it.
                        stack.pop()

                    elif name == 'super' and not value.startswith('='):
                        # Get our correct target name
                        # If they just called {{super}} without a name
                        # attempt to assume the top blocks name.
                        if value:
                            target_node = value
                        else:
                            target_node = top.name

                        # Create a SuperNode instance
                        node = SuperNode(name=target_node,
                                         pre_extend=pre_extend)

                        # Add this to our list to be taken care of
                        self.super_nodes.append(node)

                        # And put in in the tree
                        top.append(node)

                    elif name == 'include' and not value.startswith('='):
                        # If we know the target file to include
                        if value:
                            self.include(top, value)

                        # Otherwise, make a temporary include node
                        # That the child node will know to hook into.
                        else:
                            include_node = BlockNode(
                                name='__include__' + self.name,
                                pre_extend=pre_extend,
                                delimiters=self.delimiters)
                            top.append(include_node)

                    elif name == 'extend' and not value.startswith('='):
                        # We need to extend the following
                        # template.
                        extend = value
                        pre_extend = False

                    else:
                        # If we don't know where it belongs
                        # we just add it anyways without formatting.
                        if line and in_tag:

                            # Split on the newlines >.<
                            tokens = line.split('\n')

                            # We need to look for any instances of
                            # for i in range(10):
                            #   = i
                            # pass
                            # So we can properly put a response.write() in place.
                            continuation = False
                            len_parsed = 0
                            for k, token in enumerate(tokens):

                                token = tokens[k] = token.strip()
                                len_parsed += len(token)

                                if token.startswith('='):
                                    if token.endswith('\\'):
                                        continuation = True
                                        tokens[k] = "\n%s(%s" % (
                                            self.writer, token[1:].strip())
                                    else:
                                        tokens[k] = "\n%s(%s)" % (
                                            self.writer, token[1:].strip())
                                elif continuation:
                                    tokens[k] += ')'
                                    continuation = False

                            buf = "\n%s" % '\n'.join(tokens)
                            top.append(Node(buf, pre_extend=pre_extend))

                else:
                    # It is HTML so just include it.
                    buf = "\n%s(%r, escape=False)" % (self.writer, i)
                    top.append(Node(buf, pre_extend=pre_extend))

            # Remember: tag, not tag, tag, not tag
            in_tag = not in_tag

        # Make a list of items to remove from child
        to_rm = []

        # Go through each of the children nodes
        for node in self.child_super_nodes:
            # If we declared a block that this node wants to include
            if node.name in self.blocks:
                # Go ahead and include it!
                node.value = self.blocks[node.name]
                # Since we processed this child, we don't need to
                # pass it along to the parent
                to_rm.append(node)

        # Remove some of the processed nodes
        for node in to_rm:
            # Since this is a pointer, it works beautifully.
            # Sometimes I miss C-Style pointers... I want my asterisk...
            self.child_super_nodes.remove(node)

        # If we need to extend a template.
        if extend:
            self.extend(extend)

# We need this for integration with gluon


def parse_template(filename,
                   path='views/',
                   context=dict(),
                   lexers={},
                   delimiters=('{{', '}}')
                   ):
    """
    filename can be a view filename in the views folder or an input stream
    path is the path of a views folder
    context is a dictionary of symbols used to render the template
    """

    # First, if we have a str try to open the file
    if isinstance(filename, str):
        try:
            fp = open(os.path.join(path, filename), 'rb')
            text = fp.read()
            fp.close()
        except IOError:
            raise RestrictedError(filename, '', 'Unable to find the file')
    else:
        text = filename.read()

    # Use the file contents to get a parsed template and return it.
    return str(TemplateParser(text, context=context, path=path, lexers=lexers, delimiters=delimiters))


def get_parsed(text):
    """
    Returns the indented python code of text. Useful for unit testing.

    """
    return str(TemplateParser(text))


class DummyResponse():
    def __init__(self):
        self.body = StringIO.StringIO()

    def write(self, data, escape=True):
        if not escape:
            self.body.write(str(data))
        elif hasattr(data, 'xml') and callable(data.xml):
            self.body.write(data.xml())
        else:
            # make it a string
            if not isinstance(data, (str, unicode)):
                data = str(data)
            elif isinstance(data, unicode):
                data = data.encode('utf8', 'xmlcharrefreplace')
            data = cgi.escape(data, True).replace("'", "&#x27;")
            self.body.write(data)


class NOESCAPE():
    """
    A little helper to avoid escaping.
    """
    def __init__(self, text):
        self.text = text

    def xml(self):
        return self.text

# And this is a generic render function.
# Here for integration with gluino.


def render(content="hello world",
           stream=None,
           filename=None,
           path=None,
           context={},
           lexers={},
           delimiters=('{{', '}}'),
           writer='response.write'
           ):
    """
    >>> render()
    'hello world'
    >>> render(content='abc')
    'abc'
    >>> render(content='abc\\'')
    "abc'"
    >>> render(content='a"\\'bc')
    'a"\\'bc'
    >>> render(content='a\\nbc')
    'a\\nbc'
    >>> render(content='a"bcd"e')
    'a"bcd"e'
    >>> render(content="'''a\\nc'''")
    "'''a\\nc'''"
    >>> render(content="'''a\\'c'''")
    "'''a\'c'''"
    >>> render(content='{{for i in range(a):}}{{=i}}<br />{{pass}}', context=dict(a=5))
    '0<br />1<br />2<br />3<br />4<br />'
    >>> render(content='{%for i in range(a):%}{%=i%}<br />{%pass%}', context=dict(a=5),delimiters=('{%','%}'))
    '0<br />1<br />2<br />3<br />4<br />'
    >>> render(content="{{='''hello\\nworld'''}}")
    'hello\\nworld'
    >>> render(content='{{for i in range(3):\\n=i\\npass}}')
    '012'
    """
    # here to avoid circular Imports
    try:
        from globals import Response
    except ImportError:
        # Working standalone. Build a mock Response object.
        Response = DummyResponse

        # Add it to the context so we can use it.
        if not 'NOESCAPE' in context:
            context['NOESCAPE'] = NOESCAPE

    # save current response class
    if context and 'response' in context:
        old_response_body = context['response'].body
        context['response'].body = StringIO.StringIO()
    else:
        old_response_body = None
        context['response'] = Response()

    # If we don't have anything to render, why bother?
    if not content and not stream and not filename:
        raise SyntaxError("Must specify a stream or filename or content")

    # Here for legacy purposes, probably can be reduced to
    # something more simple.
    close_stream = False
    if not stream:
        if filename:
            stream = open(filename, 'rb')
            close_stream = True
        elif content:
            stream = StringIO.StringIO(content)

    # Execute the template.
    code = str(TemplateParser(stream.read(
    ), context=context, path=path, lexers=lexers, delimiters=delimiters, writer=writer))
    try:
        exec(code) in context
    except Exception:
        # for i,line in enumerate(code.split('\n')): print i,line
        raise

    if close_stream:
        stream.close()

    # Returned the rendered content.
    text = context['response'].body.getvalue()
    if old_response_body is not None:
        context['response'].body = old_response_body
    return text


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = utf8
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Created by Vladyslav Kozlovskyy (Ukraine) <dbdevelop©gmail.com>
       for Web2py project

Utilities and class for UTF8 strings managing
===========================================
"""
import __builtin__
__all__ = ['Utf8']

repr_escape_tab = {}
for i in range(1, 32):
    repr_escape_tab[i] = ur'\x%02x' % i
repr_escape_tab[7] = u'\\a'
repr_escape_tab[8] = u'\\b'
repr_escape_tab[9] = u'\\t'
repr_escape_tab[10] = u'\\n'
repr_escape_tab[11] = u'\\v'
repr_escape_tab[12] = u'\\f'
repr_escape_tab[13] = u'\\r'
repr_escape_tab[ord('\\')] = u'\\\\'
repr_escape_tab2 = repr_escape_tab.copy()
repr_escape_tab2[ord('\'')] = u"\\'"


def sort_key(s):
    """ Unicode Collation Algorithm (UCA) (http://www.unicode.org/reports/tr10/)
        is used for utf-8 and unicode strings sorting and for utf-8 strings
        comparison

        NOTE: pyuca is a very memory cost module! It loads the whole
              "allkey.txt" file (~2mb!) into the memory. But this
              functionality is needed only when sort_key() is called as a
              part of sort() function or when Utf8 strings are compared.

        So, it is a lazy "sort_key" function which (ONLY ONCE, ON ITS
        FIRST CALL) imports pyuca and replaces itself with a real
        sort_key() function
    """
    global sort_key
    try:
        from contrib.pyuca import unicode_collator
        unicode_sort_key = unicode_collator.sort_key
        sort_key = lambda s: unicode_sort_key(
            unicode(s, 'utf-8') if isinstance(s, str) else s)
    except:
        sort_key = lambda s: (
            unicode(s, 'utf-8') if isinstance(s, str) else s).lower()
    return sort_key(s)


def ord(char):
    """ returns unicode id for utf8 or unicode *char* character

        SUPPOSE that *char* is an utf-8 or unicode character only
    """
    if isinstance(char, unicode):
        return __builtin__.ord(char)
    return __builtin__.ord(unicode(char, 'utf-8'))


def chr(code):
    """ return utf8-character with *code* unicode id """
    return Utf8(unichr(code))


def size(string):
    """ return length of utf-8 string in bytes
        NOTE! The length of correspondent utf-8
              string is returned for unicode string
    """
    return Utf8(string).__size__()


def truncate(string, length, dots='...'):
    """ returns string of length < *length* or truncate
        string with adding *dots* suffix to the string's end

    args:
         length (int): max length of string
         dots (str or unicode): string suffix, when string is cutted

     returns:
         (utf8-str): original or cutted string
    """
    text = unicode(string, 'utf-8')
    dots = unicode(dots, 'utf-8') if isinstance(dots, str) else dots
    if len(text) > length:
        text = text[:length - len(dots)] + dots
    return str.__new__(Utf8, text.encode('utf-8'))


class Utf8(str):
    """
    Class for utf8 string storing and manipulations

    The base presupposition of this class usage is:
    "ALL strings in the application are either of
    utf-8 or unicode type, even when simple str
    type is used. UTF-8 is only a "packed" version
    of unicode, so Utf-8 and unicode strings are
    interchangeable."

    CAUTION! This class is slower than str/unicode!
    Do NOT use it inside intensive loops. Simply
    decode string(s) to unicode before loop and
    encode it back to utf-8 string(s) after
    intensive calculation.

    You can see the benefit of this class in doctests() below
    """
    def __new__(cls, content='', codepage='utf-8'):
        if isinstance(content, unicode):
            return str.__new__(cls, unicode.encode(content, 'utf-8'))
        elif codepage in ('utf-8', 'utf8') or isinstance(content, cls):
            return str.__new__(cls, content)
        else:
            return str.__new__(cls, unicode(content, codepage).encode('utf-8'))

    def __repr__(self):
        r''' # note that we use raw strings to avoid having to use double back slashes below
        NOTE! This function is a clone of web2py:gluino.languages.utf_repl() function

        utf8.__repr__() works same as str.repr() when processing ascii string
        >>> repr(Utf8('abc')) == repr(Utf8("abc")) == repr('abc') == repr("abc") == "'abc'"
        True
        >>> repr(Utf8('a"b"c')) == repr('a"b"c') == '\'a"b"c\''
        True
        >>> repr(Utf8("a'b'c")) == repr("a'b'c") == '"a\'b\'c"'
        True
        >>> repr(Utf8('a\'b"c')) == repr('a\'b"c') == repr(Utf8("a'b\"c")) == repr("a'b\"c") == '\'a\\\'b"c\''
        True
        >>> repr(Utf8('a\r\nb')) == repr('a\r\nb') == "'a\\r\\nb'" # Test for \r, \n
        True

        Unlike str.repr(), Utf8.__repr__() remains utf8 content when processing utf8 string
        >>> repr(Utf8('中文字')) == repr(Utf8("中文字")) == "'中文字'" != repr('中文字')
        True
        >>> repr(Utf8('中"文"字')) == "'中\"文\"字'" != repr('中"文"字')
        True
        >>> repr(Utf8("中'文'字")) == '"中\'文\'字"' != repr("中'文'字")
        True
        >>> repr(Utf8('中\'文"字')) == repr(Utf8("中'文\"字")) == '\'中\\\'文"字\'' != repr('中\'文"字') == repr("中'文\"字")
        True
        >>> repr(Utf8('中\r\n文')) == "'中\\r\\n文'" != repr('中\r\n文') # Test for \r, \n
        True
        '''
        if str.find(self, "'") >= 0 and str.find(self, '"') < 0:  # only single quote exists
            return '"' + unicode(self, 'utf-8').translate(repr_escape_tab).encode('utf-8') + '"'
        else:
            return "'" + unicode(self, 'utf-8').translate(repr_escape_tab2).encode('utf-8') + "'"

    def __size__(self):
        """ length of utf-8 string in bytes """
        return str.__len__(self)

    def __contains__(self, other):
        return str.__contains__(self, Utf8(other))

    def __getitem__(self, index):
        return str.__new__(Utf8, unicode(self, 'utf-8')[index].encode('utf-8'))

    def __getslice__(self, begin, end):
        return str.__new__(Utf8, unicode(self, 'utf-8')[begin:end].encode('utf-8'))

    def __add__(self, other):
        return str.__new__(Utf8, str.__add__(self, unicode.encode(other, 'utf-8')
                                             if isinstance(other, unicode) else other))

    def __len__(self):
        return len(unicode(self, 'utf-8'))

    def __mul__(self, integer):
        return str.__new__(Utf8, str.__mul__(self, integer))

    def __eq__(self, string):
        return str.__eq__(self, Utf8(string))

    def __ne__(self, string):
        return str.__ne__(self, Utf8(string))

    def capitalize(self):
        return str.__new__(Utf8, unicode(self, 'utf-8').capitalize().encode('utf-8'))

    def center(self, length):
        return str.__new__(Utf8, unicode(self, 'utf-8').center(length).encode('utf-8'))

    def upper(self):
        return str.__new__(Utf8, unicode(self, 'utf-8').upper().encode('utf-8'))

    def lower(self):
        return str.__new__(Utf8, unicode(self, 'utf-8').lower().encode('utf-8'))

    def title(self):
        return str.__new__(Utf8, unicode(self, 'utf-8').title().encode('utf-8'))

    def index(self, string):
        return unicode(self, 'utf-8').index(string if isinstance(string, unicode) else unicode(string, 'utf-8'))

    def isalnum(self):
        return unicode(self, 'utf-8').isalnum()

    def isalpha(self):
        return unicode(self, 'utf-8').isalpha()

    def isdigit(self):
        return unicode(self, 'utf-8').isdigit()

    def islower(self):
        return unicode(self, 'utf-8').islower()

    def isspace(self):
        return unicode(self, 'utf-8').isspace()

    def istitle(self):
        return unicode(self, 'utf-8').istitle()

    def isupper(self):
        return unicode(self, 'utf-8').isupper()

    def zfill(self, length):
        return str.__new__(Utf8, unicode(self, 'utf-8').zfill(length).encode('utf-8'))

    def join(self, iter):
        return str.__new__(Utf8, str.join(self, [Utf8(c) for c in
                                                 list(unicode(iter, 'utf-8') if
                                                      isinstance(iter, str) else
                                                      iter)]))

    def lstrip(self, chars=None):
        return str.__new__(Utf8, str.lstrip(self, None if chars is None else Utf8(chars)))

    def rstrip(self, chars=None):
        return str.__new__(Utf8, str.rstrip(self, None if chars is None else Utf8(chars)))

    def strip(self, chars=None):
        return str.__new__(Utf8, str.strip(self, None if chars is None else Utf8(chars)))

    def swapcase(self):
        return str.__new__(Utf8, unicode(self, 'utf-8').swapcase().encode('utf-8'))

    def count(self, sub, start=0, end=None):
        unistr = unicode(self, 'utf-8')
        return unistr.count(
            unicode(sub, 'utf-8') if isinstance(sub, str) else sub,
            start, len(unistr) if end is None else end)

    def decode(self, encoding='utf-8', errors='strict'):
        return str.decode(self, encoding, errors)

    def encode(self, encoding, errors='strict'):
        return unicode(self, 'utf-8').encode(encoding, errors)

    def expandtabs(self, tabsize=8):
        return str.__new__(Utf8, unicode(self, 'utf-8').expandtabs(tabsize).encode('utf-8'))

    def find(self, sub, start=None, end=None):
        return unicode(self, 'utf-8').find(unicode(sub, 'utf-8')
                                           if isinstance(sub, str) else sub, start, end)

    def ljust(self, width, fillchar=' '):
        return str.__new__(Utf8, unicode(self, 'utf-8').ljust(width, unicode(fillchar, 'utf-8')
                                                              if isinstance(fillchar, str) else fillchar).encode('utf-8'))

    def partition(self, sep):
        (head, sep, tail) = str.partition(self, Utf8(sep))
        return (str.__new__(Utf8, head),
                str.__new__(Utf8, sep),
                str.__new__(Utf8, tail))

    def replace(self, old, new, count=-1):
        return str.__new__(Utf8, str.replace(self, Utf8(old), Utf8(new), count))

    def rfind(self, sub, start=None, end=None):
        return unicode(self, 'utf-8').rfind(unicode(sub, 'utf-8')
                                            if isinstance(sub, str) else sub, start, end)

    def rindex(self, string):
        return unicode(self, 'utf-8').rindex(string if isinstance(string, unicode)
                                             else unicode(string, 'utf-8'))

    def rjust(self, width, fillchar=' '):
        return str.__new__(Utf8, unicode(self, 'utf-8').rjust(width, unicode(fillchar, 'utf-8')
                                                              if isinstance(fillchar, str) else fillchar).encode('utf-8'))

    def rpartition(self, sep):
        (head, sep, tail) = str.rpartition(self, Utf8(sep))
        return (str.__new__(Utf8, head),
                str.__new__(Utf8, sep),
                str.__new__(Utf8, tail))

    def rsplit(self, sep=None, maxsplit=-1):
        return [str.__new__(Utf8, part) for part in str.rsplit(self,
                                                               None if sep is None else Utf8(sep), maxsplit)]

    def split(self, sep=None, maxsplit=-1):
        return [str.__new__(Utf8, part) for part in str.split(self,
                                                              None if sep is None else Utf8(sep), maxsplit)]

    def splitlines(self, keepends=False):
        return [str.__new__(Utf8, part) for part in str.splitlines(self, keepends)]

    def startswith(self, prefix, start=0, end=None):
        unistr = unicode(self, 'utf-8')
        if isinstance(prefix, tuple):
            prefix = tuple(unicode(
                s, 'utf-8') if isinstance(s, str) else s for s in prefix)
        elif isinstance(prefix, str):
            prefix = unicode(prefix, 'utf-8')
        return unistr.startswith(prefix, start, len(unistr) if end is None else end)

    def translate(self, table, deletechars=''):
        if isinstance(table, dict):
            return str.__new__(Utf8, unicode(self, 'utf-8').translate(table).encode('utf-8'))
        else:
            return str.__new__(Utf8, str.translate(self, table, deletechars))

    def endswith(self, prefix, start=0, end=None):
        unistr = unicode(self, 'utf-8')
        if isinstance(prefix, tuple):
            prefix = tuple(unicode(
                s, 'utf-8') if isinstance(s, str) else s for s in prefix)
        elif isinstance(prefix, str):
            prefix = unicode(prefix, 'utf-8')
        return unistr.endswith(prefix, start, len(unistr) if end is None else end)
    if hasattr(str, 'format'):  # Python 2.5 hasn't got str.format() method
        def format(self, *args, **kwargs):
            args = [unicode(
                s, 'utf-8') if isinstance(s, str) else s for s in args]
            kwargs = dict((unicode(k, 'utf-8') if isinstance(k, str) else k,
                           unicode(v, 'utf-8') if isinstance(v, str) else v)
                          for k, v in kwargs.iteritems())
            return str.__new__(Utf8, unicode(self, 'utf-8').
                               format(*args, **kwargs).encode('utf-8'))

    def __mod__(self, right):
        if isinstance(right, tuple):
            right = tuple(unicode(v, 'utf-8') if isinstance(v, str) else v
                          for v in right)
        elif isinstance(right, dict):
            right = dict((unicode(k, 'utf-8') if isinstance(k, str) else k,
                          unicode(v, 'utf-8') if isinstance(v, str) else v)
                         for k, v in right.iteritems())
        elif isinstance(right, str):
            right = unicode(right, 'utf-8')
        return str.__new__(Utf8, unicode(self, 'utf-8').__mod__(right).encode('utf-8'))

    def __ge__(self, string):
        return sort_key(self) >= sort_key(string)

    def __gt__(self, string):
        return sort_key(self) > sort_key(string)

    def __le__(self, string):
        return sort_key(self) <= sort_key(string)

    def __lt__(self, string):
        return sort_key(self) < sort_key(string)


if __name__ == '__main__':
    def doctests():
        u"""
        doctests:
        >>> test_unicode=u'ПРоба Є PRobe'
        >>> test_unicode_word=u'ПРоба'
        >>> test_number_str='12345'
        >>> test_unicode
        u'\\u041f\\u0420\\u043e\\u0431\\u0430 \\u0404 PRobe'
        >>> print test_unicode
        ПРоба Є PRobe
        >>> test_word=test_unicode_word.encode('utf-8')
        >>> test_str=test_unicode.encode('utf-8')
        >>> s=Utf8(test_str)
        >>> s
        'ПРоба Є PRobe'
        >>> type(s)
        <class '__main__.Utf8'>
        >>> s == test_str
        True
        >>> len(test_str) # wrong length of utf8-string!
        19
        >>> len(test_unicode) # RIGHT!
        13
        >>> len(s) # RIGHT!
        13
        >>> size(test_str) # size of utf-8 string (in bytes) == len(str)
        19
        >>> size(test_unicode) # size of unicode string in bytes (packed to utf-8 string)
        19
        >>> size(s) # size of utf-8 string in bytes
        19
        >>> try: # utf-8 is a multibyte string. Convert it to unicode for use with builtin ord()
        ...     __builtin__.ord('б')  #  ascii string
        ... except Exception, e:
        ...     print 'Exception:', e
        Exception: ord() expected a character, but string of length 2 found
        >>> ord('б') # utf8.ord() is used(!!!)
        1073
        >>> ord(u'б') # utf8.ord() is used(!!!)
        1073
        >>> ord(s[3])  # utf8.ord() is used(!!!)
        1073
        >>> chr(ord(s[3])) # utf8.chr() and utf8.chr() is used(!!!)
        'б'
        >>> type(chr(1073))  # utf8.chr() is used(!!!)
        <class '__main__.Utf8'>
        >>> s=Utf8(test_unicode)
        >>> s
        'ПРоба Є PRobe'
        >>> s == test_str
        True
        >>> test_str == s
        True
        >>> s == test_unicode
        True
        >>> test_unicode == s
        True
        >>> print test_str.upper() # only ASCII characters uppered
        ПРоба Є PROBE
        >>> print test_unicode.upper() # unicode gives right result
        ПРОБА Є PROBE
        >>> s.upper() # utf8 class use unicode.upper()
        'ПРОБА Є PROBE'
        >>> type(s.upper())
        <class '__main__.Utf8'>
        >>> s.lower()
        'проба є probe'
        >>> type(s.lower())
        <class '__main__.Utf8'>
        >>> s.capitalize()
        'Проба є probe'
        >>> type(s.capitalize())
        <class '__main__.Utf8'>
        >>> len(s)
        13
        >>> len(test_unicode)
        13
        >>> s+'. Probe is проба'
        'ПРоба Є PRobe. Probe is проба'
        >>> type(s+'. Probe is проба')
        <class '__main__.Utf8'>
        >>> s+u'. Probe is проба'
        'ПРоба Є PRobe. Probe is проба'
        >>> type(s+u'. Probe is проба')
        <class '__main__.Utf8'>
        >>> s+s
        'ПРоба Є PRobeПРоба Є PRobe'
        >>> type(s+s)
        <class '__main__.Utf8'>
        >>> a=s
        >>> a+=s
        >>> a+=test_unicode
        >>> a+=test_str
        >>> a
        'ПРоба Є PRobeПРоба Є PRobeПРоба Є PRobeПРоба Є PRobe'
        >>> type(a)
        <class '__main__.Utf8'>
        >>> s*3
        'ПРоба Є PRobeПРоба Є PRobeПРоба Є PRobe'
        >>> type(s*3)
        <class '__main__.Utf8'>
        >>> a=Utf8("-проба-")
        >>> a*=10
        >>> a
        '-проба--проба--проба--проба--проба--проба--проба--проба--проба--проба-'
        >>> type(a)
        <class '__main__.Utf8'>
        >>> print "'"+test_str.center(17)+"'" # WRONG RESULT!
        'ПРоба Є PRobe'
        >>> s.center(17) # RIGHT!
        '  ПРоба Є PRobe  '
        >>> type(s.center(17))
        <class '__main__.Utf8'>
        >>> (test_word+test_number_str).isalnum() # WRONG RESULT! non ASCII chars are detected as non alpha
        False
        >>> Utf8(test_word+test_number_str).isalnum()
        True
        >>> s.isalnum()
        False
        >>> test_word.isalpha() # WRONG RESULT! Non ASCII characters are detected as non alpha
        False
        >>> Utf8(test_word).isalpha() # RIGHT!
        True
        >>> s.lower().islower()
        True
        >>> s.upper().isupper()
        True
        >>> print test_str.zfill(17) # WRONG RESULT!
        ПРоба Є PRobe
        >>> s.zfill(17) # RIGHT!
        '0000ПРоба Є PRobe'
        >>> type(s.zfill(17))
        <class '__main__.Utf8'>
        >>> s.istitle()
        False
        >>> s.title().istitle()
        True
        >>> Utf8('1234').isdigit()
        True
        >>> Utf8(' \t').isspace()
        True
        >>> s.join('•|•')
        '•ПРоба Є PRobe|ПРоба Є PRobe•'
        >>> s.join((str('(utf8 тест1)'), unicode('(unicode тест2)','utf-8'), '(ascii test3)'))
        '(utf8 тест1)ПРоба Є PRobe(unicode тест2)ПРоба Є PRobe(ascii test3)'
        >>> type(s)
        <class '__main__.Utf8'>
        >>> s==test_str
        True
        >>> s==test_unicode
        True
        >>> s.swapcase()
        'прОБА є prOBE'
        >>> type(s.swapcase())
        <class '__main__.Utf8'>
        >>> truncate(s, 10)
        'ПРоба Є...'
        >>> truncate(s, 20)
        'ПРоба Є PRobe'
        >>> truncate(s, 10, '•••') # utf-8 string as *dots*
        'ПРоба Є•••'
        >>> truncate(s, 10, u'®') # you can use unicode string as *dots*
        'ПРоба Є P®'
        >>> type(truncate(s, 10))
        <class '__main__.Utf8'>
        >>> Utf8(s.encode('koi8-u'), 'koi8-u')
        'ПРоба Є PRobe'
        >>> s.decode() # convert utf-8 string to unicode
        u'\\u041f\\u0420\\u043e\\u0431\\u0430 \\u0404 PRobe'
        >>> a='про\\tba'
        >>> str_tmp=a.expandtabs()
        >>> utf8_tmp=Utf8(a).expandtabs()
        >>> utf8_tmp.replace(' ','.') # RIGHT! (default tabsize is 8)
        'про.....ba'
        >>> utf8_tmp.index('b')
        8
        >>> print "'"+str_tmp.replace(' ','.')+"'" # WRONG STRING LENGTH!
        'про..ba'
        >>> str_tmp.index('b') # WRONG index of 'b' character
        8
        >>> print "'"+a.expandtabs(4).replace(' ','.')+"'" # WRONG RESULT!
        'про..ba'
        >>> Utf8(a).expandtabs(4).replace(' ','.') # RIGHT!
        'про.ba'
        >>> s.find('Є')
        6
        >>> s.find(u'Є')
        6
        >>> s.find(' ', 6)
        7
        >>> s.rfind(' ')
        7
        >>> s.partition('Є')
        ('ПРоба ', 'Є', ' PRobe')
        >>> s.partition(u'Є')
        ('ПРоба ', 'Є', ' PRobe')
        >>> (a,b,c) = s.partition('Є')
        >>> type(a), type(b), type(c)
        (<class '__main__.Utf8'>, <class '__main__.Utf8'>, <class '__main__.Utf8'>)
        >>> s.partition(' ')
        ('ПРоба', ' ', 'Є PRobe')
        >>> s.rpartition(' ')
        ('ПРоба Є', ' ', 'PRobe')
        >>> s.index('Є')
        6
        >>> s.rindex(u'Є')
        6
        >>> s.index(' ')
        5
        >>> s.rindex(' ')
        7
        >>> a=Utf8('а б ц д е а б ц д е а\\tб ц д е')
        >>> a.split()
        ['а', 'б', 'ц', 'д', 'е', 'а', 'б', 'ц', 'д',
            'е', 'а', 'б', 'ц', 'д', 'е']
        >>> a.rsplit()
        ['а', 'б', 'ц', 'д', 'е', 'а', 'б', 'ц', 'д',
            'е', 'а', 'б', 'ц', 'д', 'е']
        >>> a.expandtabs().split('б')
        ['а ', ' ц д е а ', ' ц д е а   ', ' ц д е']
        >>> a.expandtabs().rsplit('б')
        ['а ', ' ц д е а ', ' ц д е а   ', ' ц д е']
        >>> a.expandtabs().split(u'б', 1)
        ['а ', ' ц д е а б ц д е а   б ц д е']
        >>> a.expandtabs().rsplit(u'б', 1)
        ['а б ц д е а б ц д е а   ', ' ц д е']
        >>> a=Utf8("рядок1\\nрядок2\\nрядок3")
        >>> a.splitlines()
        ['рядок1', 'рядок2', 'рядок3']
        >>> a.splitlines(True)
        ['рядок1\\n', 'рядок2\\n', 'рядок3']
        >>> s[6]
        'Є'
        >>> s[0]
        'П'
        >>> s[-1]
        'e'
        >>> s[:10]
        'ПРоба Є PR'
        >>> s[2:-2:2]
        'оаЄPo'
        >>> s[::-1]
        'eboRP Є абоРП'
        >>> s.startswith('ПР')
        True
        >>> s.startswith(('ПР', u'об'),0)
        True
        >>> s.startswith(u'об', 2, 4)
        True
        >>> s.endswith('be')
        True
        >>> s.endswith(('be', 'PR', u'Є'))
        True
        >>> s.endswith('PR', 8, 10)
        True
        >>> s.endswith('Є', -7, -6)
        True
        >>> s.count(' ')
        2
        >>> s.count(' ',6)
        1
        >>> s.count(u'Є')
        1
        >>> s.count('Є', 0, 5)
        0
        >>> Utf8(
            "Parameters: '%(проба)s', %(probe)04d, %(проба2)s") % { u"проба": s,
        ...      "not used": "???", "probe":  2, "проба2": u"ПРоба Probe" }
        "Parameters: 'ПРоба Є PRobe', 0002, ПРоба Probe"
        >>> a=Utf8(u"Параметр: (%s)-(%s)-[%s]")
        >>> a%=(s, s[::-1], 1000)
        >>> a
        'Параметр: (ПРоба Є PRobe)-(eboRP Є абоРП)-[1000]'
        >>> if hasattr(Utf8,  'format'):
        ...     Utf8("Проба <{0}>, {1}, {param1}, {param2}").format(s, u"中文字",
        ...           param1="барабан", param2=1000) == 'Проба <ПРоба Є PRobe>, 中文字, барабан, 1000'
        ... else: # format() method is not used in python with version <2.6:
        ...     print True
        True
        >>> u'Б'<u'Ї' # WRONG ORDER!
        False
        >>> 'Б'<'Ї' # WRONG ORDER!
        False
        >>> Utf8('Б')<'Ї' # RIGHT!
        True
        >>> u'д'>u'ґ' # WRONG ORDER!
        False
        >>> Utf8('д')>Utf8('ґ') # RIGHT!
        True
        >>> u'є'<=u'ж' # WRONG ORDER!
        False
        >>> Utf8('є')<=u'ж' # RIGHT!
        True
        >>> Utf8('є')<=u'є'
        True
        >>> u'Ї'>=u'И' # WRONG ORDER!
        False
        >>> Utf8(u'Ї') >= u'И' # RIGHT
        True
        >>> Utf8('Є') >= 'Є'
        True
        >>> a="яжертиуіопшщїасдфгґхйклчєзьцвбнмюЯЖЕРТИУІОПШЩЇАСДФГҐХЙКЛЧЗЬЦВБНМЮЄ"  # str type
        >>> b=u"яжертиуіопшщїасдфгґхйклчєзьцвбнмюЯЖЕРТИУІОПШЩЇАСДФГҐХЙКЛЧЗЬЦВБНМЮЄ" # unicode type
        >>> c=Utf8("яжертиуіопшщїасдфгґхйклчєзьцвбнмюЯЖЕРТИУІОПШЩЇАСДФГҐХЙКЛЧЗЬЦВБНМЮЄ") # utf8 class
        >>> result = "".join(sorted(a))
        >>> result[0:20] # result is not utf8 string, because bytes, not utf8-characters were sorted
        '\\x80\\x81\\x82\\x83\\x84\\x84\\x85\\x86\\x86\\x87\\x87\\x88\\x89\\x8c\\x8e\\x8f\\x90\\x90\\x91\\x91'
        >>> try:
        ...   unicode(result, 'utf-8') # try to convert result (utf-8?) to unicode
        ... except Exception, e:
        ...    print 'Exception:', e
        Exception: 'utf8' codec can't decode byte 0x80 in position 0: unexpected code byte
        >>> try: # FAILED! (working with bytes, not with utf8-charactes)
        ...    "".join( sorted(a, key=sort_key) ) # utf8.sort_key may be used with utf8 or unicode strings only!
        ... except Exception, e:
        ...    print 'Exception:', e
        Exception: 'utf8' codec can't decode byte 0xd1 in position 0: unexpected end of data
        >>> print "".join( sorted(Utf8(a))) # converting *a* to unicode or utf8-string gives us correct result
        аАбБвВгГґҐдДеЕєЄжЖзЗиИіІїЇйЙкКлЛмМнНоОпПрРсСтТуУфФхХцЦчЧшШщЩьЬюЮяЯ
        >>> print u"".join( sorted(b) ) # WRONG ORDER! Default sort key is used
        ЄІЇАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЮЯабвгдежзийклмнопрстуфхцчшщьюяєіїҐґ
        >>> print u"".join( sorted(b, key=sort_key) ) # RIGHT ORDER! utf8.sort_key is used
        аАбБвВгГґҐдДеЕєЄжЖзЗиИіІїЇйЙкКлЛмМнНоОпПрРсСтТуУфФхХцЦчЧшШщЩьЬюЮяЯ
        >>> print "".join( sorted(c) ) # RIGHT ORDER! Utf8 "rich comparison" methods are used
        аАбБвВгГґҐдДеЕєЄжЖзЗиИіІїЇйЙкКлЛмМнНоОпПрРсСтТуУфФхХцЦчЧшШщЩьЬюЮяЯ
        >>> print "".join( sorted(c, key=sort_key) ) # RIGHT ORDER! utf8.sort_key is used
        аАбБвВгГґҐдДеЕєЄжЖзЗиИіІїЇйЙкКлЛмМнНоОпПрРсСтТуУфФхХцЦчЧшШщЩьЬюЮяЯ
        >>> Utf8().join(sorted(c.decode(), key=sort_key)) # convert to unicode for better performance
        'аАбБвВгГґҐдДеЕєЄжЖзЗиИіІїЇйЙкКлЛмМнНоОпПрРсСтТуУфФхХцЦчЧшШщЩьЬюЮяЯ'
        >>> for result in sorted(
            ["Іа", "Астро", u"гала", Utf8("Гоша"), "Єва", "шовк", "аякс", "Їжа",
        ...                       "ґанок", Utf8("Дар'я"), "білінг", "веб", u"Жужа", "проба", u"тест",
        ...                       "абетка", "яблуко", "Юляся", "Київ", "лимонад", "ложка", "Матриця",
        ...                      ], key=sort_key):
        ...     print result.ljust(20), type(result)
        абетка         <type 'str'>
        Астро           <type 'str'>
        аякс             <type 'str'>
        білінг         <type 'str'>
        веб               <type 'str'>
        гала                 <type 'unicode'>
        ґанок           <type 'str'>
        Гоша                 <class '__main__.Utf8'>
        Дар'я                <class '__main__.Utf8'>
        Єва               <type 'str'>
        Жужа                 <type 'unicode'>
        Іа                 <type 'str'>
        Їжа               <type 'str'>
        Київ             <type 'str'>
        лимонад       <type 'str'>
        ложка           <type 'str'>
        Матриця       <type 'str'>
        проба           <type 'str'>
        тест                 <type 'unicode'>
        шовк             <type 'str'>
        Юляся           <type 'str'>
        яблуко         <type 'str'>
        >>> a=Utf8("中文字")
        >>> L=list(a)
        >>> L
        ['中', '文', '字']
        >>> a="".join(L)
        >>> print a
        中文字
        >>> type(a)
        <type 'str'>
        >>> a="中文字"  # standard str type
        >>> L=list(a)
        >>> L
        ['\\xe4', '\\xb8', '\\xad', '\\xe6', '\\x96', '\\x87',
            '\\xe5', '\\xad', '\\x97']
        >>> from string import maketrans
        >>> str_tab=maketrans('PRobe','12345')
        >>> unicode_tab={ord(u'П'):ord(u'Ж'),
        ...              ord(u'Р')      : u'Ш',
        ...              ord(Utf8('о')) : None,  # utf8.ord() is used
        ...              ord('б')       : None,  # -//-//-
        ...              ord(u'а')      : u"中文字",
        ...              ord(u'Є')      : Utf8('•').decode(), # only unicode type is supported
        ...             }
        >>> s.translate(unicode_tab).translate(str_tab, deletechars=' ')
        'ЖШ中文字•12345'
        """
        import sys
        reload(sys)
        sys.setdefaultencoding("UTF-8")
        import doctest
        print "DOCTESTS STARTED..."
        doctest.testmod()
        print "DOCTESTS FINISHED"

    doctests()

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

This file specifically includes utilities for security.
"""

import threading
import struct
import hashlib
import hmac
import uuid
import random
import time
import os
import re
import sys
import logging
import socket
import base64
import zlib

python_version = sys.version_info[0]

if python_version == 2:
    import cPickle as pickle
else:
    import pickle


try:
    from Crypto.Cipher import AES
except ImportError:
    import contrib.aes as AES

try:
    from contrib.pbkdf2 import pbkdf2_hex
    HAVE_PBKDF2 = True
except ImportError:
    try:
        from .pbkdf2 import pbkdf2_hex
        HAVE_PBKDF2 = True
    except (ImportError, ValueError):
        HAVE_PBKDF2 = False

logger = logging.getLogger("web2py")

def AES_new(key, IV=None):
    """ Returns an AES cipher object and random IV if None specified """
    if IV is None:
        IV = fast_urandom16()

    return AES.new(key, AES.MODE_CBC, IV), IV


def compare(a, b):
    """ compares two strings and not vulnerable to timing attacks """
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


def md5_hash(text):
    """ Generate a md5 hash with the given text """
    return hashlib.md5(text).hexdigest()


def simple_hash(text, key='', salt='', digest_alg='md5'):
    """
    Generates hash with the given text using the specified
    digest hashing algorithm
    """
    if not digest_alg:
        raise RuntimeError("simple_hash with digest_alg=None")
    elif not isinstance(digest_alg, str):  # manual approach
        h = digest_alg(text + key + salt)
    elif digest_alg.startswith('pbkdf2'):  # latest and coolest!
        iterations, keylen, alg = digest_alg[7:-1].split(',')
        return pbkdf2_hex(text, salt, int(iterations),
                          int(keylen), get_digest(alg))
    elif key:  # use hmac
        digest_alg = get_digest(digest_alg)
        h = hmac.new(key + salt, text, digest_alg)
    else:  # compatible with third party systems
        h = hashlib.new(digest_alg)
        h.update(text + salt)
    return h.hexdigest()


def get_digest(value):
    """
    Returns a hashlib digest algorithm from a string
    """
    if not isinstance(value, str):
        return value
    value = value.lower()
    if value == "md5":
        return hashlib.md5
    elif value == "sha1":
        return hashlib.sha1
    elif value == "sha224":
        return hashlib.sha224
    elif value == "sha256":
        return hashlib.sha256
    elif value == "sha384":
        return hashlib.sha384
    elif value == "sha512":
        return hashlib.sha512
    else:
        raise ValueError("Invalid digest algorithm: %s" % value)

DIGEST_ALG_BY_SIZE = {
    128 / 4: 'md5',
    160 / 4: 'sha1',
    224 / 4: 'sha224',
    256 / 4: 'sha256',
    384 / 4: 'sha384',
    512 / 4: 'sha512',
}


def pad(s, n=32, padchar=' '):
    return s + (32 - len(s) % 32) * padchar


def secure_dumps(data, encryption_key, hash_key=None, compression_level=None):
    if not hash_key:
        hash_key = hashlib.sha1(encryption_key).hexdigest()
    dump = pickle.dumps(data)
    if compression_level:
        dump = zlib.compress(dump, compression_level)
    key = pad(encryption_key[:32])
    cipher, IV = AES_new(key)
    encrypted_data = base64.urlsafe_b64encode(IV + cipher.encrypt(pad(dump)))
    signature = hmac.new(hash_key, encrypted_data).hexdigest()
    return signature + ':' + encrypted_data


def secure_loads(data, encryption_key, hash_key=None, compression_level=None):
    if not ':' in data:
        return None
    if not hash_key:
        hash_key = hashlib.sha1(encryption_key).hexdigest()
    signature, encrypted_data = data.split(':', 1)
    actual_signature = hmac.new(hash_key, encrypted_data).hexdigest()
    if not compare(signature, actual_signature):
        return None
    key = pad(encryption_key[:32])
    encrypted_data = base64.urlsafe_b64decode(encrypted_data)
    IV, encrypted_data = encrypted_data[:16], encrypted_data[16:]
    cipher, _ = AES_new(key, IV=IV)
    try:
        data = cipher.decrypt(encrypted_data)
        data = data.rstrip(' ')
        if compression_level:
            data = zlib.decompress(data)
        return pickle.loads(data)
    except (TypeError, pickle.UnpicklingError):
        return None

### compute constant CTOKENS


def initialize_urandom():
    """
    This function and the web2py_uuid follow from the following discussion:
    http://groups.google.com/group/web2py-developers/browse_thread/thread/7fd5789a7da3f09

    At startup web2py compute a unique ID that identifies the machine by adding
    uuid.getnode() + int(time.time() * 1e3)

    This is a 48-bit number. It converts the number into 16 8-bit tokens.
    It uses this value to initialize the entropy source ('/dev/urandom') and to seed random.

    If os.random() is not supported, it falls back to using random and issues a warning.
    """
    node_id = uuid.getnode()
    microseconds = int(time.time() * 1e6)
    ctokens = [((node_id + microseconds) >> ((i % 6) * 8)) %
               256 for i in range(16)]
    random.seed(node_id + microseconds)
    try:
        os.urandom(1)
        have_urandom = True
        try:
            # try to add process-specific entropy
            frandom = open('/dev/urandom', 'wb')
            try:
                if python_version == 2:
                    frandom.write(''.join(chr(t) for t in ctokens)) # python 2
                else:
                    frandom.write(bytes([]).join(bytes([t]) for t in ctokens)) # python 3
            finally:
                frandom.close()
        except IOError:
            # works anyway
            pass
    except NotImplementedError:
        have_urandom = False
        logger.warning(
            """Cryptographically secure session management is not possible on your system because
your system does not provide a cryptographically secure entropy source.
This is not specific to web2py; consider deploying on a different operating system.""")
    if python_version == 2:
        packed = ''.join(chr(x) for x in ctokens) # python 2
    else:
        packed = bytes([]).join(bytes([x]) for x in ctokens) # python 3
    unpacked_ctokens = struct.unpack('=QQ', packed)
    return unpacked_ctokens, have_urandom
UNPACKED_CTOKENS, HAVE_URANDOM = initialize_urandom()


def fast_urandom16(urandom=[], locker=threading.RLock()):
    """
    this is 4x faster than calling os.urandom(16) and prevents
    the "too many files open" issue with concurrent access to os.urandom()
    """
    try:
        return urandom.pop()
    except IndexError:
        try:
            locker.acquire()
            ur = os.urandom(16 * 1024)
            urandom += [ur[i:i + 16] for i in xrange(16, 1024 * 16, 16)]
            return ur[0:16]
        finally:
            locker.release()


def web2py_uuid(ctokens=UNPACKED_CTOKENS):
    """
    This function follows from the following discussion:
    http://groups.google.com/group/web2py-developers/browse_thread/thread/7fd5789a7da3f09

    It works like uuid.uuid4 except that tries to use os.urandom() if possible
    and it XORs the output with the tokens uniquely associated with this machine.
    """
    rand_longs = (random.getrandbits(64), random.getrandbits(64))
    if HAVE_URANDOM:
        urand_longs = struct.unpack('=QQ', fast_urandom16())
        byte_s = struct.pack('=QQ',
                             rand_longs[0] ^ urand_longs[0] ^ ctokens[0],
                             rand_longs[1] ^ urand_longs[1] ^ ctokens[1])
    else:
        byte_s = struct.pack('=QQ',
                             rand_longs[0] ^ ctokens[0],
                             rand_longs[1] ^ ctokens[1])
    return str(uuid.UUID(bytes=byte_s, version=4))

REGEX_IPv4 = re.compile('(\d+)\.(\d+)\.(\d+)\.(\d+)')


def is_valid_ip_address(address):
    """
    >>> is_valid_ip_address('127.0')
    False
    >>> is_valid_ip_address('127.0.0.1')
    True
    >>> is_valid_ip_address('2001:660::1')
    True
    """
    # deal with special cases
    if address.lower() in ('127.0.0.1', 'localhost', '::1', '::ffff:127.0.0.1'):
        return True
    elif address.lower() in ('unknown', ''):
        return False
    elif address.count('.') == 3:  # assume IPv4
        if address.startswith('::ffff:'):
            address = address[7:]
        if hasattr(socket, 'inet_aton'):  # try validate using the OS
            try:
                socket.inet_aton(address)
                return True
            except socket.error:  # invalid address
                return False
        else:  # try validate using Regex
            match = REGEX_IPv4.match(address)
            if match and all(0 <= int(match.group(i)) < 256 for i in (1, 2, 3, 4)):
                return True
            return False
    elif hasattr(socket, 'inet_pton'):  # assume IPv6, try using the OS
        try:
            socket.inet_pton(socket.AF_INET6, address)
            return True
        except socket.error:  # invalid address
            return False
    else:  # do not know what to do? assume it is a valid address
        return True


def is_loopback_ip_address(ip=None, addrinfo=None):
    """
    Determines whether the address appears to be a loopback address.
    This assumes that the IP is valid.
    """
    if addrinfo: # see socket.getaddrinfo() for layout of addrinfo tuple
        if addrinfo[0] == socket.AF_INET or addrinfo[0] == socket.AF_INET6:
            ip = addrinfo[4]
    if not isinstance(ip, basestring):
        return False
    # IPv4 or IPv6-embedded IPv4 or IPv4-compatible IPv6
    if ip.count('.') == 3:  
        return ip.lower().startswith(('127', '::127', '0:0:0:0:0:0:127',
                                      '::ffff:127', '0:0:0:0:0:ffff:127'))
    return ip == '::1' or ip == '0:0:0:0:0:0:0:1'   # IPv6 loopback


def getipaddrinfo(host):
    """
    Filter out non-IP and bad IP addresses from getaddrinfo
    """
    try:
        return [addrinfo for addrinfo in socket.getaddrinfo(host, None)
                if (addrinfo[0] == socket.AF_INET or 
                    addrinfo[0] == socket.AF_INET6)
                and isinstance(addrinfo[4][0], basestring)]
    except socket.error:
        return []

########NEW FILE########
__FILENAME__ = validators
#!/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Thanks to ga2arch for help with IS_IN_DB and IS_NOT_IN_DB on GAE
"""

import os
import re
import datetime
import time
import cgi
import urllib
import struct
import decimal
import unicodedata
from cStringIO import StringIO
from utils import simple_hash, web2py_uuid, DIGEST_ALG_BY_SIZE
from dal import FieldVirtual, FieldMethod

JSONErrors = (NameError, TypeError, ValueError, AttributeError,
              KeyError)
try:
    import json as simplejson
except ImportError:
    from gluino.contrib import simplejson
    from gluino.contrib.simplejson.decoder import JSONDecodeError
    JSONErrors += (JSONDecodeError,)

__all__ = [
    'ANY_OF',
    'CLEANUP',
    'CRYPT',
    'IS_ALPHANUMERIC',
    'IS_DATE_IN_RANGE',
    'IS_DATE',
    'IS_DATETIME_IN_RANGE',
    'IS_DATETIME',
    'IS_DECIMAL_IN_RANGE',
    'IS_EMAIL',
    'IS_EMPTY_OR',
    'IS_EXPR',
    'IS_FLOAT_IN_RANGE',
    'IS_IMAGE',
    'IS_IN_DB',
    'IS_IN_SET',
    'IS_INT_IN_RANGE',
    'IS_IPV4',
    'IS_IPV6',
    'IS_IPADDRESS',
    'IS_LENGTH',
    'IS_LIST_OF',
    'IS_LOWER',
    'IS_MATCH',
    'IS_EQUAL_TO',
    'IS_NOT_EMPTY',
    'IS_NOT_IN_DB',
    'IS_NULL_OR',
    'IS_SLUG',
    'IS_STRONG',
    'IS_TIME',
    'IS_UPLOAD_FILENAME',
    'IS_UPPER',
    'IS_URL',
    'IS_JSON',
]

try:
    from globals import current
    have_current = True
except ImportError:
    have_current = False


def translate(text):
    if text is None:
        return None
    elif isinstance(text, (str, unicode)) and have_current:
        if hasattr(current, 'T'):
            return str(current.T(text))
    return str(text)


def options_sorter(x, y):
    return (str(x[1]).upper() > str(y[1]).upper() and 1) or -1


class Validator(object):
    """
    Root for all validators, mainly for documentation purposes.

    Validators are classes used to validate input fields (including forms
    generated from database tables).

    Here is an example of using a validator with a FORM::

        INPUT(_name='a', requires=IS_INT_IN_RANGE(0, 10))

    Here is an example of how to require a validator for a table field::

        db.define_table('person', SQLField('name'))
        db.person.name.requires=IS_NOT_EMPTY()

    Validators are always assigned using the requires attribute of a field. A
    field can have a single validator or multiple validators. Multiple
    validators are made part of a list::

        db.person.name.requires=[IS_NOT_EMPTY(), IS_NOT_IN_DB(db, 'person.id')]

    Validators are called by the function accepts on a FORM or other HTML
    helper object that contains a form. They are always called in the order in
    which they are listed.

    Built-in validators have constructors that take the optional argument error
    message which allows you to change the default error message.
    Here is an example of a validator on a database table::

        db.person.name.requires=IS_NOT_EMPTY(error_message=T('fill this'))

    where we have used the translation operator T to allow for
    internationalization.

    Notice that default error messages are not translated.
    """

    def formatter(self, value):
        """
        For some validators returns a formatted version (matching the validator)
        of value. Otherwise just returns the value.
        """
        return value

    def __call__(self, value):
        raise NotImplementedError
        return (value, None)


class IS_MATCH(Validator):
    """
    example::

        INPUT(_type='text', _name='name', requires=IS_MATCH('.+'))

    the argument of IS_MATCH is a regular expression::

        >>> IS_MATCH('.+')('hello')
        ('hello', None)

        >>> IS_MATCH('hell')('hello')
        ('hello', None)

        >>> IS_MATCH('hell.*', strict=False)('hello')
        ('hello', None)

        >>> IS_MATCH('hello')('shello')
        ('shello', 'invalid expression')

        >>> IS_MATCH('hello', search=True)('shello')
        ('shello', None)

        >>> IS_MATCH('hello', search=True, strict=False)('shellox')
        ('shellox', None)

        >>> IS_MATCH('.*hello.*', search=True, strict=False)('shellox')
        ('shellox', None)

        >>> IS_MATCH('.+')('')
        ('', 'invalid expression')
    """

    def __init__(self, expression, error_message='invalid expression',
                 strict=False, search=False, extract=False,
                 unicode=False):
        if strict or not search:
            if not expression.startswith('^'):
                expression = '^(%s)' % expression
        if strict:
            if not expression.endswith('$'):
                expression = '(%s)$' % expression
        if unicode:
            if not isinstance(expression,unicode):
                expression = expression.decode('utf8')
            self.regex = re.compile(expression,re.UNICODE)
        else:
            self.regex = re.compile(expression)
        self.error_message = error_message
        self.extract = extract
        self.unicode = unicode

    def __call__(self, value):
        if self.unicode and not isinstance(value,unicode):
            match = self.regex.search(str(value).decode('utf8'))
        else:
            match = self.regex.search(str(value))
        if match is not None:
            return (self.extract and match.group() or value, None)
        return (value, translate(self.error_message))


class IS_EQUAL_TO(Validator):
    """
    example::

        INPUT(_type='text', _name='password')
        INPUT(_type='text', _name='password2',
              requires=IS_EQUAL_TO(request.vars.password))

    the argument of IS_EQUAL_TO is a string

        >>> IS_EQUAL_TO('aaa')('aaa')
        ('aaa', None)

        >>> IS_EQUAL_TO('aaa')('aab')
        ('aab', 'no match')
    """

    def __init__(self, expression, error_message='no match'):
        self.expression = expression
        self.error_message = error_message

    def __call__(self, value):
        if value == self.expression:
            return (value, None)
        return (value, translate(self.error_message))


class IS_EXPR(Validator):
    """
    example::

        INPUT(_type='text', _name='name',
            requires=IS_EXPR('5 < int(value) < 10'))

    the argument of IS_EXPR must be python condition::

        >>> IS_EXPR('int(value) < 2')('1')
        ('1', None)

        >>> IS_EXPR('int(value) < 2')('2')
        ('2', 'invalid expression')
    """

    def __init__(self, expression, error_message='invalid expression', environment=None):
        self.expression = expression
        self.error_message = error_message
        self.environment = environment or {}

    def __call__(self, value):
        if callable(self.expression):
            return (value, self.expression(value))
        # for backward compatibility
        self.environment.update(value=value)
        exec '__ret__=' + self.expression in self.environment
        if self.environment['__ret__']:
            return (value, None)
        return (value, translate(self.error_message))


class IS_LENGTH(Validator):
    """
    Checks if length of field's value fits between given boundaries. Works
    for both text and file inputs.

    Arguments:

    maxsize: maximum allowed length / size
    minsize: minimum allowed length / size

    Examples::

        #Check if text string is shorter than 33 characters:
        INPUT(_type='text', _name='name', requires=IS_LENGTH(32))

        #Check if password string is longer than 5 characters:
        INPUT(_type='password', _name='name', requires=IS_LENGTH(minsize=6))

        #Check if uploaded file has size between 1KB and 1MB:
        INPUT(_type='file', _name='name', requires=IS_LENGTH(1048576, 1024))

        >>> IS_LENGTH()('')
        ('', None)
        >>> IS_LENGTH()('1234567890')
        ('1234567890', None)
        >>> IS_LENGTH(maxsize=5, minsize=0)('1234567890')  # too long
        ('1234567890', 'enter from 0 to 5 characters')
        >>> IS_LENGTH(maxsize=50, minsize=20)('1234567890')  # too short
        ('1234567890', 'enter from 20 to 50 characters')
    """

    def __init__(self, maxsize=255, minsize=0,
                 error_message='enter from %(min)g to %(max)g characters'):
        self.maxsize = maxsize
        self.minsize = minsize
        self.error_message = error_message

    def __call__(self, value):
        if value is None:
            length = 0
            if self.minsize <= length <= self.maxsize:
                return (value, None)
        elif isinstance(value, cgi.FieldStorage):
            if value.file:
                value.file.seek(0, os.SEEK_END)
                length = value.file.tell()
                value.file.seek(0, os.SEEK_SET)
            elif hasattr(value, 'value'):
                val = value.value
                if val:
                    length = len(val)
                else:
                    length = 0
            if self.minsize <= length <= self.maxsize:
                return (value, None)
        elif isinstance(value, str):
            try:
                lvalue = len(value.decode('utf8'))
            except:
                lvalue = len(value)
            if self.minsize <= lvalue <= self.maxsize:
                return (value, None)
        elif isinstance(value, unicode):
            if self.minsize <= len(value) <= self.maxsize:
                return (value.encode('utf8'), None)
        elif isinstance(value, (tuple, list)):
            if self.minsize <= len(value) <= self.maxsize:
                return (value, None)
        elif self.minsize <= len(str(value)) <= self.maxsize:
            return (str(value), None)
        return (value, translate(self.error_message)
                % dict(min=self.minsize, max=self.maxsize))

class IS_JSON(Validator):
    """
    example::
        INPUT(_type='text', _name='name',
            requires=IS_JSON(error_message="This is not a valid json input")

        >>> IS_JSON()('{"a": 100}')
        ({u'a': 100}, None)

        >>> IS_JSON()('spam1234')
        ('spam1234', 'invalid json')
    """

    def __init__(self, error_message='invalid json'):
        self.error_message = error_message

    def __call__(self, value):
        if value is None:
            return None
        try:
            return (simplejson.loads(value), None)
        except JSONErrors:
            return (value, translate(self.error_message))

    def formatter(self,value):
        if value is None:
            return None
        return simplejson.dumps(value)


class IS_IN_SET(Validator):
    """
    example::

        INPUT(_type='text', _name='name',
              requires=IS_IN_SET(['max', 'john'],zero=''))

    the argument of IS_IN_SET must be a list or set

        >>> IS_IN_SET(['max', 'john'])('max')
        ('max', None)
        >>> IS_IN_SET(['max', 'john'])('massimo')
        ('massimo', 'value not allowed')
        >>> IS_IN_SET(['max', 'john'], multiple=True)(('max', 'john'))
        (('max', 'john'), None)
        >>> IS_IN_SET(['max', 'john'], multiple=True)(('bill', 'john'))
        (('bill', 'john'), 'value not allowed')
        >>> IS_IN_SET(('id1','id2'), ['first label','second label'])('id1') # Traditional way
        ('id1', None)
        >>> IS_IN_SET({'id1':'first label', 'id2':'second label'})('id1')
        ('id1', None)
        >>> import itertools
        >>> IS_IN_SET(itertools.chain(['1','3','5'],['2','4','6']))('1')
        ('1', None)
        >>> IS_IN_SET([('id1','first label'), ('id2','second label')])('id1') # Redundant way
        ('id1', None)
    """

    def __init__(
        self,
        theset,
        labels=None,
        error_message='value not allowed',
        multiple=False,
        zero='',
        sort=False,
    ):
        self.multiple = multiple
        if isinstance(theset, dict):
            self.theset = [str(item) for item in theset]
            self.labels = theset.values()
        elif theset and isinstance(theset, (tuple, list)) \
                and isinstance(theset[0], (tuple, list)) and len(theset[0]) == 2:
            self.theset = [str(item) for item, label in theset]
            self.labels = [str(label) for item, label in theset]
        else:
            self.theset = [str(item) for item in theset]
            self.labels = labels
        self.error_message = error_message
        self.zero = zero
        self.sort = sort

    def options(self, zero=True):
        if not self.labels:
            items = [(k, k) for (i, k) in enumerate(self.theset)]
        else:
            items = [(k, self.labels[i]) for (i, k) in enumerate(self.theset)]
        if self.sort:
            items.sort(options_sorter)
        if zero and not self.zero is None and not self.multiple:
            items.insert(0, ('', self.zero))
        return items

    def __call__(self, value):
        if self.multiple:
            ### if below was values = re.compile("[\w\-:]+").findall(str(value))
            if not value:
                values = []
            elif isinstance(value, (tuple, list)):
                values = value
            else:
                values = [value]
        else:
            values = [value]
        thestrset = [str(x) for x in self.theset]
        failures = [x for x in values if not str(x) in thestrset]
        if failures and self.theset:
            if self.multiple and (value is None or value == ''):
                return ([], None)
            return (value, translate(self.error_message))
        if self.multiple:
            if isinstance(self.multiple, (tuple, list)) and \
                    not self.multiple[0] <= len(values) < self.multiple[1]:
                return (values, translate(self.error_message))
            return (values, None)
        return (value, None)


regex1 = re.compile('\w+\.\w+')
regex2 = re.compile('%\((?P<name>[^\)]+)\)s')


class IS_IN_DB(Validator):
    """
    example::

        INPUT(_type='text', _name='name',
              requires=IS_IN_DB(db, db.mytable.myfield, zero=''))

    used for reference fields, rendered as a dropbox
    """

    def __init__(
        self,
        dbset,
        field,
        label=None,
        error_message='value not in database',
        orderby=None,
        groupby=None,
        distinct=None,
        cache=None,
        multiple=False,
        zero='',
        sort=False,
        _and=None,
    ):
        from dal import Table
        if isinstance(field, Table):
            field = field._id

        if hasattr(dbset, 'define_table'):
            self.dbset = dbset()
        else:
            self.dbset = dbset
        (ktable, kfield) = str(field).split('.')
        if not label:
            label = '%%(%s)s' % kfield
        if isinstance(label, str):
            if regex1.match(str(label)):
                label = '%%(%s)s' % str(label).split('.')[-1]
            ks = regex2.findall(label)
            if not kfield in ks:
                ks += [kfield]
            fields = ks
        else:
            ks = [kfield]
            fields = 'all'
        self.fields = fields
        self.label = label
        self.ktable = ktable
        self.kfield = kfield
        self.ks = ks
        self.error_message = error_message
        self.theset = None
        self.orderby = orderby
        self.groupby = groupby
        self.distinct = distinct
        self.cache = cache
        self.multiple = multiple
        self.zero = zero
        self.sort = sort
        self._and = _and

    def set_self_id(self, id):
        if self._and:
            self._and.record_id = id

    def build_set(self):
        table = self.dbset.db[self.ktable]
        if self.fields == 'all':
            fields = [f for f in table]
        else:
            fields = [table[k] for k in self.fields]
        ignore = (FieldVirtual,FieldMethod)
        fields = filter(lambda f:not isinstance(f,ignore), fields)
        if self.dbset.db._dbname != 'gae':
            orderby = self.orderby or reduce(lambda a, b: a | b, fields)
            groupby = self.groupby
            distinct = self.distinct
            dd = dict(orderby=orderby, groupby=groupby,
                      distinct=distinct, cache=self.cache,
                      cacheable=True)
            records = self.dbset(table).select(*fields, **dd)
        else:
            orderby = self.orderby or \
                reduce(lambda a, b: a | b, (
                    f for f in fields if not f.name == 'id'))
            dd = dict(orderby=orderby, cache=self.cache, cacheable=True)
            records = self.dbset(table).select(table.ALL, **dd)
        self.theset = [str(r[self.kfield]) for r in records]
        if isinstance(self.label, str):
            self.labels = [self.label % r for r in records]
        else:
            self.labels = [self.label(r) for r in records]

    def options(self, zero=True):
        self.build_set()
        items = [(k, self.labels[i]) for (i, k) in enumerate(self.theset)]
        if self.sort:
            items.sort(options_sorter)
        if zero and not self.zero is None and not self.multiple:
            items.insert(0, ('', self.zero))
        return items

    def __call__(self, value):
        table = self.dbset.db[self.ktable]
        field = table[self.kfield]
        if self.multiple:
            if self._and:
                raise NotImplementedError
            if isinstance(value, list):
                values = value
            elif value:
                values = [value]
            else:
                values = []
            if isinstance(self.multiple, (tuple, list)) and \
                    not self.multiple[0] <= len(values) < self.multiple[1]:
                return (values, translate(self.error_message))
            if self.theset:
                if not [v for v in values if not v in self.theset]:
                    return (values, None)
            else:
                from dal import GoogleDatastoreAdapter

                def count(values, s=self.dbset, f=field):
                    return s(f.belongs(map(int, values))).count()
                if isinstance(self.dbset.db._adapter, GoogleDatastoreAdapter):
                    range_ids = range(0, len(values), 30)
                    total = sum(count(values[i:i + 30]) for i in range_ids)
                    if total == len(values):
                        return (values, None)
                elif count(values) == len(values):
                    return (values, None)
        elif self.theset:
            if str(value) in self.theset:
                if self._and:
                    return self._and(value)
                else:
                    return (value, None)
        else:
            if self.dbset(field == value).count():
                if self._and:
                    return self._and(value)
                else:
                    return (value, None)
        return (value, translate(self.error_message))


class IS_NOT_IN_DB(Validator):
    """
    example::

        INPUT(_type='text', _name='name', requires=IS_NOT_IN_DB(db, db.table))

    makes the field unique
    """

    def __init__(
        self,
        dbset,
        field,
        error_message='value already in database or empty',
        allowed_override=[],
        ignore_common_filters=False,
    ):

        from dal import Table
        if isinstance(field, Table):
            field = field._id

        if hasattr(dbset, 'define_table'):
            self.dbset = dbset()
        else:
            self.dbset = dbset
        self.field = field
        self.error_message = error_message
        self.record_id = 0
        self.allowed_override = allowed_override
        self.ignore_common_filters = ignore_common_filters

    def set_self_id(self, id):
        self.record_id = id

    def __call__(self, value):
        if isinstance(value,unicode):
            value = value.encode('utf8')
        else:
            value = str(value)
        if not value.strip():
            return (value, translate(self.error_message))
        if value in self.allowed_override:
            return (value, None)
        (tablename, fieldname) = str(self.field).split('.')
        table = self.dbset.db[tablename]
        field = table[fieldname]
        subset = self.dbset(field == value,
                            ignore_common_filters=self.ignore_common_filters)
        id = self.record_id
        if isinstance(id, dict):
            fields = [table[f] for f in id]
            row = subset.select(*fields, **dict(limitby=(0, 1), orderby_on_limitby=False)).first()
            if row and any(str(row[f]) != str(id[f]) for f in id):
                return (value, translate(self.error_message))
        else:
            row = subset.select(table._id, field, limitby=(0, 1), orderby_on_limitby=False).first()
            if row and str(row.id) != str(id):
                return (value, translate(self.error_message))
        return (value, None)


class IS_INT_IN_RANGE(Validator):
    """
    Determine that the argument is (or can be represented as) an int,
    and that it falls within the specified range. The range is interpreted
    in the Pythonic way, so the test is: min <= value < max.

    The minimum and maximum limits can be None, meaning no lower or upper limit,
    respectively.

    example::

        INPUT(_type='text', _name='name', requires=IS_INT_IN_RANGE(0, 10))

        >>> IS_INT_IN_RANGE(1,5)('4')
        (4, None)
        >>> IS_INT_IN_RANGE(1,5)(4)
        (4, None)
        >>> IS_INT_IN_RANGE(1,5)(1)
        (1, None)
        >>> IS_INT_IN_RANGE(1,5)(5)
        (5, 'enter an integer between 1 and 4')
        >>> IS_INT_IN_RANGE(1,5)(5)
        (5, 'enter an integer between 1 and 4')
        >>> IS_INT_IN_RANGE(1,5)(3.5)
        (3, 'enter an integer between 1 and 4')
        >>> IS_INT_IN_RANGE(None,5)('4')
        (4, None)
        >>> IS_INT_IN_RANGE(None,5)('6')
        (6, 'enter an integer less than or equal to 4')
        >>> IS_INT_IN_RANGE(1,None)('4')
        (4, None)
        >>> IS_INT_IN_RANGE(1,None)('0')
        (0, 'enter an integer greater than or equal to 1')
        >>> IS_INT_IN_RANGE()(6)
        (6, None)
        >>> IS_INT_IN_RANGE()('abc')
        ('abc', 'enter an integer')
    """

    def __init__(
        self,
        minimum=None,
        maximum=None,
        error_message=None,
    ):
        self.minimum = self.maximum = None
        if minimum is None:
            if maximum is None:
                self.error_message = translate(
                    error_message or 'enter an integer')
            else:
                self.maximum = int(maximum)
                if error_message is None:
                    error_message = \
                        'enter an integer less than or equal to %(max)g'
                self.error_message = translate(
                    error_message) % dict(max=self.maximum - 1)
        elif maximum is None:
            self.minimum = int(minimum)
            if error_message is None:
                error_message = \
                    'enter an integer greater than or equal to %(min)g'
            self.error_message = translate(
                error_message) % dict(min=self.minimum)
        else:
            self.minimum = int(minimum)
            self.maximum = int(maximum)
            if error_message is None:
                error_message = 'enter an integer between %(min)g and %(max)g'
            self.error_message = translate(error_message) \
                % dict(min=self.minimum, max=self.maximum - 1)

    def __call__(self, value):
        try:
            fvalue = float(value)
            value = int(value)
            if value != fvalue:
                return (value, self.error_message)
            if self.minimum is None:
                if self.maximum is None or value < self.maximum:
                    return (value, None)
            elif self.maximum is None:
                if value >= self.minimum:
                    return (value, None)
            elif self.minimum <= value < self.maximum:
                    return (value, None)
        except ValueError:
            pass
        return (value, self.error_message)


def str2dec(number):
    s = str(number)
    if not '.' in s:
        s += '.00'
    else:
        s += '0' * (2 - len(s.split('.')[1]))
    return s


class IS_FLOAT_IN_RANGE(Validator):
    """
    Determine that the argument is (or can be represented as) a float,
    and that it falls within the specified inclusive range.
    The comparison is made with native arithmetic.

    The minimum and maximum limits can be None, meaning no lower or upper limit,
    respectively.

    example::

        INPUT(_type='text', _name='name', requires=IS_FLOAT_IN_RANGE(0, 10))

        >>> IS_FLOAT_IN_RANGE(1,5)('4')
        (4.0, None)
        >>> IS_FLOAT_IN_RANGE(1,5)(4)
        (4.0, None)
        >>> IS_FLOAT_IN_RANGE(1,5)(1)
        (1.0, None)
        >>> IS_FLOAT_IN_RANGE(1,5)(5.25)
        (5.25, 'enter a number between 1 and 5')
        >>> IS_FLOAT_IN_RANGE(1,5)(6.0)
        (6.0, 'enter a number between 1 and 5')
        >>> IS_FLOAT_IN_RANGE(1,5)(3.5)
        (3.5, None)
        >>> IS_FLOAT_IN_RANGE(1,None)(3.5)
        (3.5, None)
        >>> IS_FLOAT_IN_RANGE(None,5)(3.5)
        (3.5, None)
        >>> IS_FLOAT_IN_RANGE(1,None)(0.5)
        (0.5, 'enter a number greater than or equal to 1')
        >>> IS_FLOAT_IN_RANGE(None,5)(6.5)
        (6.5, 'enter a number less than or equal to 5')
        >>> IS_FLOAT_IN_RANGE()(6.5)
        (6.5, None)
        >>> IS_FLOAT_IN_RANGE()('abc')
        ('abc', 'enter a number')
    """

    def __init__(
        self,
        minimum=None,
        maximum=None,
        error_message=None,
        dot='.'
    ):
        self.minimum = self.maximum = None
        self.dot = str(dot)
        if minimum is None:
            if maximum is None:
                if error_message is None:
                    error_message = 'enter a number'
            else:
                self.maximum = float(maximum)
                if error_message is None:
                    error_message = 'enter a number less than or equal to %(max)g'
        elif maximum is None:
            self.minimum = float(minimum)
            if error_message is None:
                error_message = 'enter a number greater than or equal to %(min)g'
        else:
            self.minimum = float(minimum)
            self.maximum = float(maximum)
            if error_message is None:
                error_message = 'enter a number between %(min)g and %(max)g'
        self.error_message = translate(error_message) \
            % dict(min=self.minimum, max=self.maximum)

    def __call__(self, value):
        try:
            if self.dot == '.':
                fvalue = float(value)
            else:
                fvalue = float(str(value).replace(self.dot, '.'))
            if self.minimum is None:
                if self.maximum is None or fvalue <= self.maximum:
                    return (fvalue, None)
            elif self.maximum is None:
                if fvalue >= self.minimum:
                    return (fvalue, None)
            elif self.minimum <= fvalue <= self.maximum:
                    return (fvalue, None)
        except (ValueError, TypeError):
            pass
        return (value, self.error_message)

    def formatter(self, value):
        if value is None:
            return None
        return str2dec(value).replace('.', self.dot)


class IS_DECIMAL_IN_RANGE(Validator):
    """
    Determine that the argument is (or can be represented as) a Python Decimal,
    and that it falls within the specified inclusive range.
    The comparison is made with Python Decimal arithmetic.

    The minimum and maximum limits can be None, meaning no lower or upper limit,
    respectively.

    example::

        INPUT(_type='text', _name='name', requires=IS_DECIMAL_IN_RANGE(0, 10))

        >>> IS_DECIMAL_IN_RANGE(1,5)('4')
        (Decimal('4'), None)
        >>> IS_DECIMAL_IN_RANGE(1,5)(4)
        (Decimal('4'), None)
        >>> IS_DECIMAL_IN_RANGE(1,5)(1)
        (Decimal('1'), None)
        >>> IS_DECIMAL_IN_RANGE(1,5)(5.25)
        (5.25, 'enter a number between 1 and 5')
        >>> IS_DECIMAL_IN_RANGE(5.25,6)(5.25)
        (Decimal('5.25'), None)
        >>> IS_DECIMAL_IN_RANGE(5.25,6)('5.25')
        (Decimal('5.25'), None)
        >>> IS_DECIMAL_IN_RANGE(1,5)(6.0)
        (6.0, 'enter a number between 1 and 5')
        >>> IS_DECIMAL_IN_RANGE(1,5)(3.5)
        (Decimal('3.5'), None)
        >>> IS_DECIMAL_IN_RANGE(1.5,5.5)(3.5)
        (Decimal('3.5'), None)
        >>> IS_DECIMAL_IN_RANGE(1.5,5.5)(6.5)
        (6.5, 'enter a number between 1.5 and 5.5')
        >>> IS_DECIMAL_IN_RANGE(1.5,None)(6.5)
        (Decimal('6.5'), None)
        >>> IS_DECIMAL_IN_RANGE(1.5,None)(0.5)
        (0.5, 'enter a number greater than or equal to 1.5')
        >>> IS_DECIMAL_IN_RANGE(None,5.5)(4.5)
        (Decimal('4.5'), None)
        >>> IS_DECIMAL_IN_RANGE(None,5.5)(6.5)
        (6.5, 'enter a number less than or equal to 5.5')
        >>> IS_DECIMAL_IN_RANGE()(6.5)
        (Decimal('6.5'), None)
        >>> IS_DECIMAL_IN_RANGE(0,99)(123.123)
        (123.123, 'enter a number between 0 and 99')
        >>> IS_DECIMAL_IN_RANGE(0,99)('123.123')
        ('123.123', 'enter a number between 0 and 99')
        >>> IS_DECIMAL_IN_RANGE(0,99)('12.34')
        (Decimal('12.34'), None)
        >>> IS_DECIMAL_IN_RANGE()('abc')
        ('abc', 'enter a decimal number')
    """

    def __init__(
        self,
        minimum=None,
        maximum=None,
        error_message=None,
        dot='.'
    ):
        self.minimum = self.maximum = None
        self.dot = str(dot)
        if minimum is None:
            if maximum is None:
                if error_message is None:
                    error_message = 'enter a decimal number'
            else:
                self.maximum = decimal.Decimal(str(maximum))
                if error_message is None:
                    error_message = 'enter a number less than or equal to %(max)g'
        elif maximum is None:
            self.minimum = decimal.Decimal(str(minimum))
            if error_message is None:
                error_message = 'enter a number greater than or equal to %(min)g'
        else:
            self.minimum = decimal.Decimal(str(minimum))
            self.maximum = decimal.Decimal(str(maximum))
            if error_message is None:
                error_message = 'enter a number between %(min)g and %(max)g'
        self.error_message = translate(error_message) \
            % dict(min=self.minimum, max=self.maximum)

    def __call__(self, value):
        try:
            if isinstance(value, decimal.Decimal):
                v = value
            else:
                v = decimal.Decimal(str(value).replace(self.dot, '.'))
            if self.minimum is None:
                if self.maximum is None or v <= self.maximum:
                    return (v, None)
            elif self.maximum is None:
                if v >= self.minimum:
                    return (v, None)
            elif self.minimum <= v <= self.maximum:
                    return (v, None)
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass
        return (value, self.error_message)

    def formatter(self, value):
        if value is None:
            return None
        return str2dec(value).replace('.', self.dot)


def is_empty(value, empty_regex=None):
    "test empty field"
    if isinstance(value, (str, unicode)):
        value = value.strip()
        if empty_regex is not None and empty_regex.match(value):
            value = ''
    if value is None or value == '' or value == []:
        return (value, True)
    return (value, False)


class IS_NOT_EMPTY(Validator):
    """
    example::

        INPUT(_type='text', _name='name', requires=IS_NOT_EMPTY())

        >>> IS_NOT_EMPTY()(1)
        (1, None)
        >>> IS_NOT_EMPTY()(0)
        (0, None)
        >>> IS_NOT_EMPTY()('x')
        ('x', None)
        >>> IS_NOT_EMPTY()(' x ')
        ('x', None)
        >>> IS_NOT_EMPTY()(None)
        (None, 'enter a value')
        >>> IS_NOT_EMPTY()('')
        ('', 'enter a value')
        >>> IS_NOT_EMPTY()('  ')
        ('', 'enter a value')
        >>> IS_NOT_EMPTY()(' \\n\\t')
        ('', 'enter a value')
        >>> IS_NOT_EMPTY()([])
        ([], 'enter a value')
        >>> IS_NOT_EMPTY(empty_regex='def')('def')
        ('', 'enter a value')
        >>> IS_NOT_EMPTY(empty_regex='de[fg]')('deg')
        ('', 'enter a value')
        >>> IS_NOT_EMPTY(empty_regex='def')('abc')
        ('abc', None)
    """

    def __init__(self, error_message='enter a value', empty_regex=None):
        self.error_message = error_message
        if empty_regex is not None:
            self.empty_regex = re.compile(empty_regex)
        else:
            self.empty_regex = None

    def __call__(self, value):
        value, empty = is_empty(value, empty_regex=self.empty_regex)
        if empty:
            return (value, translate(self.error_message))
        return (value, None)


class IS_ALPHANUMERIC(IS_MATCH):
    """
    example::

        INPUT(_type='text', _name='name', requires=IS_ALPHANUMERIC())

        >>> IS_ALPHANUMERIC()('1')
        ('1', None)
        >>> IS_ALPHANUMERIC()('')
        ('', None)
        >>> IS_ALPHANUMERIC()('A_a')
        ('A_a', None)
        >>> IS_ALPHANUMERIC()('!')
        ('!', 'enter only letters, numbers, and underscore')
    """

    def __init__(self, error_message='enter only letters, numbers, and underscore'):
        IS_MATCH.__init__(self, '^[\w]*$', error_message)


class IS_EMAIL(Validator):
    """
    Checks if field's value is a valid email address. Can be set to disallow
    or force addresses from certain domain(s).

    Email regex adapted from
    http://haacked.com/archive/2007/08/21/i-knew-how-to-validate-an-email-address-until-i.aspx,
    generally following the RFCs, except that we disallow quoted strings
    and permit underscores and leading numerics in subdomain labels

    Arguments:

    - banned: regex text for disallowed address domains
    - forced: regex text for required address domains

    Both arguments can also be custom objects with a match(value) method.

    Examples::

        #Check for valid email address:
        INPUT(_type='text', _name='name',
            requires=IS_EMAIL())

        #Check for valid email address that can't be from a .com domain:
        INPUT(_type='text', _name='name',
            requires=IS_EMAIL(banned='^.*\.com(|\..*)$'))

        #Check for valid email address that must be from a .edu domain:
        INPUT(_type='text', _name='name',
            requires=IS_EMAIL(forced='^.*\.edu(|\..*)$'))

        >>> IS_EMAIL()('a@b.com')
        ('a@b.com', None)
        >>> IS_EMAIL()('abc@def.com')
        ('abc@def.com', None)
        >>> IS_EMAIL()('abc@3def.com')
        ('abc@3def.com', None)
        >>> IS_EMAIL()('abc@def.us')
        ('abc@def.us', None)
        >>> IS_EMAIL()('abc@d_-f.us')
        ('abc@d_-f.us', None)
        >>> IS_EMAIL()('@def.com')           # missing name
        ('@def.com', 'enter a valid email address')
        >>> IS_EMAIL()('"abc@def".com')      # quoted name
        ('"abc@def".com', 'enter a valid email address')
        >>> IS_EMAIL()('abc+def.com')        # no @
        ('abc+def.com', 'enter a valid email address')
        >>> IS_EMAIL()('abc@def.x')          # one-char TLD
        ('abc@def.x', 'enter a valid email address')
        >>> IS_EMAIL()('abc@def.12')         # numeric TLD
        ('abc@def.12', 'enter a valid email address')
        >>> IS_EMAIL()('abc@def..com')       # double-dot in domain
        ('abc@def..com', 'enter a valid email address')
        >>> IS_EMAIL()('abc@.def.com')       # dot starts domain
        ('abc@.def.com', 'enter a valid email address')
        >>> IS_EMAIL()('abc@def.c_m')        # underscore in TLD
        ('abc@def.c_m', 'enter a valid email address')
        >>> IS_EMAIL()('NotAnEmail')         # missing @
        ('NotAnEmail', 'enter a valid email address')
        >>> IS_EMAIL()('abc@NotAnEmail')     # missing TLD
        ('abc@NotAnEmail', 'enter a valid email address')
        >>> IS_EMAIL()('customer/department@example.com')
        ('customer/department@example.com', None)
        >>> IS_EMAIL()('$A12345@example.com')
        ('$A12345@example.com', None)
        >>> IS_EMAIL()('!def!xyz%abc@example.com')
        ('!def!xyz%abc@example.com', None)
        >>> IS_EMAIL()('_Yosemite.Sam@example.com')
        ('_Yosemite.Sam@example.com', None)
        >>> IS_EMAIL()('~@example.com')
        ('~@example.com', None)
        >>> IS_EMAIL()('.wooly@example.com')       # dot starts name
        ('.wooly@example.com', 'enter a valid email address')
        >>> IS_EMAIL()('wo..oly@example.com')      # adjacent dots in name
        ('wo..oly@example.com', 'enter a valid email address')
        >>> IS_EMAIL()('pootietang.@example.com')  # dot ends name
        ('pootietang.@example.com', 'enter a valid email address')
        >>> IS_EMAIL()('.@example.com')            # name is bare dot
        ('.@example.com', 'enter a valid email address')
        >>> IS_EMAIL()('Ima.Fool@example.com')
        ('Ima.Fool@example.com', None)
        >>> IS_EMAIL()('Ima Fool@example.com')     # space in name
        ('Ima Fool@example.com', 'enter a valid email address')
        >>> IS_EMAIL()('localguy@localhost')       # localhost as domain
        ('localguy@localhost', None)

    """

    regex = re.compile('''
        ^(?!\.)                            # name may not begin with a dot
        (
          [-a-z0-9!\#$%&'*+/=?^_`{|}~]     # all legal characters except dot
          |
          (?<!\.)\.                        # single dots only
        )+
        (?<!\.)                            # name may not end with a dot
        @
        (
          localhost
          |
          (
            [a-z0-9]
                # [sub]domain begins with alphanumeric
            (
              [-\w]*                         # alphanumeric, underscore, dot, hyphen
              [a-z0-9]                       # ending alphanumeric
            )?
          \.                               # ending dot
          )+
          [a-z]{2,}                        # TLD alpha-only
       )$
    ''', re.VERBOSE | re.IGNORECASE)

    regex_proposed_but_failed = re.compile('^([\w\!\#$\%\&\'\*\+\-\/\=\?\^\`{\|\}\~]+\.)*[\w\!\#$\%\&\'\*\+\-\/\=\?\^\`{\|\}\~]+@((((([a-z0-9]{1}[a-z0-9\-]{0,62}[a-z0-9]{1})|[a-z])\.)+[a-z]{2,6})|(\d{1,3}\.){3}\d{1,3}(\:\d{1,5})?)$', re.VERBOSE | re.IGNORECASE)

    def __init__(self,
                 banned=None,
                 forced=None,
                 error_message='enter a valid email address'):
        if isinstance(banned, str):
            banned = re.compile(banned)
        if isinstance(forced, str):
            forced = re.compile(forced)
        self.banned = banned
        self.forced = forced
        self.error_message = error_message

    def __call__(self, value):
        match = self.regex.match(value)
        if match:
            domain = value.split('@')[1]
            if (not self.banned or not self.banned.match(domain)) \
                    and (not self.forced or self.forced.match(domain)):
                return (value, None)
        return (value, translate(self.error_message))


# URL scheme source:
# <http://en.wikipedia.org/wiki/URI_scheme> obtained on 2008-Nov-10

official_url_schemes = [
    'aaa',
    'aaas',
    'acap',
    'cap',
    'cid',
    'crid',
    'data',
    'dav',
    'dict',
    'dns',
    'fax',
    'file',
    'ftp',
    'go',
    'gopher',
    'h323',
    'http',
    'https',
    'icap',
    'im',
    'imap',
    'info',
    'ipp',
    'iris',
    'iris.beep',
    'iris.xpc',
    'iris.xpcs',
    'iris.lws',
    'ldap',
    'mailto',
    'mid',
    'modem',
    'msrp',
    'msrps',
    'mtqp',
    'mupdate',
    'news',
    'nfs',
    'nntp',
    'opaquelocktoken',
    'pop',
    'pres',
    'prospero',
    'rtsp',
    'service',
    'shttp',
    'sip',
    'sips',
    'snmp',
    'soap.beep',
    'soap.beeps',
    'tag',
    'tel',
    'telnet',
    'tftp',
    'thismessage',
    'tip',
    'tv',
    'urn',
    'vemmi',
    'wais',
    'xmlrpc.beep',
    'xmlrpc.beep',
    'xmpp',
    'z39.50r',
    'z39.50s',
]
unofficial_url_schemes = [
    'about',
    'adiumxtra',
    'aim',
    'afp',
    'aw',
    'callto',
    'chrome',
    'cvs',
    'ed2k',
    'feed',
    'fish',
    'gg',
    'gizmoproject',
    'iax2',
    'irc',
    'ircs',
    'itms',
    'jar',
    'javascript',
    'keyparc',
    'lastfm',
    'ldaps',
    'magnet',
    'mms',
    'msnim',
    'mvn',
    'notes',
    'nsfw',
    'psyc',
    'paparazzi:http',
    'rmi',
    'rsync',
    'secondlife',
    'sgn',
    'skype',
    'ssh',
    'sftp',
    'smb',
    'sms',
    'soldat',
    'steam',
    'svn',
    'teamspeak',
    'unreal',
    'ut2004',
    'ventrilo',
    'view-source',
    'webcal',
    'wyciwyg',
    'xfire',
    'xri',
    'ymsgr',
]
all_url_schemes = [None] + official_url_schemes + unofficial_url_schemes
http_schemes = [None, 'http', 'https']


# This regex comes from RFC 2396, Appendix B. It's used to split a URL into
# its component parts
# Here are the regex groups that it extracts:
#    scheme = group(2)
#    authority = group(4)
#    path = group(5)
#    query = group(7)
#    fragment = group(9)

url_split_regex = \
    re.compile('^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?')

# Defined in RFC 3490, Section 3.1, Requirement #1
# Use this regex to split the authority component of a unicode URL into
# its component labels
label_split_regex = re.compile(u'[\u002e\u3002\uff0e\uff61]')


def escape_unicode(string):
    '''
    Converts a unicode string into US-ASCII, using a simple conversion scheme.
    Each unicode character that does not have a US-ASCII equivalent is
    converted into a URL escaped form based on its hexadecimal value.
    For example, the unicode character '\u4e86' will become the string '%4e%86'

    :param string: unicode string, the unicode string to convert into an
        escaped US-ASCII form
    :returns: the US-ASCII escaped form of the inputted string
    :rtype: string

    @author: Jonathan Benn
    '''
    returnValue = StringIO()

    for character in string:
        code = ord(character)
        if code > 0x7F:
            hexCode = hex(code)
            returnValue.write('%' + hexCode[2:4] + '%' + hexCode[4:6])
        else:
            returnValue.write(character)

    return returnValue.getvalue()


def unicode_to_ascii_authority(authority):
    '''
    Follows the steps in RFC 3490, Section 4 to convert a unicode authority
    string into its ASCII equivalent.
    For example, u'www.Alliancefran\xe7aise.nu' will be converted into
    'www.xn--alliancefranaise-npb.nu'

    :param authority: unicode string, the URL authority component to convert,
                      e.g. u'www.Alliancefran\xe7aise.nu'
    :returns: the US-ASCII character equivalent to the inputed authority,
             e.g. 'www.xn--alliancefranaise-npb.nu'
    :rtype: string
    :raises Exception: if the function is not able to convert the inputed
        authority

    @author: Jonathan Benn
    '''
    #RFC 3490, Section 4, Step 1
    #The encodings.idna Python module assumes that AllowUnassigned == True

    #RFC 3490, Section 4, Step 2
    labels = label_split_regex.split(authority)

    #RFC 3490, Section 4, Step 3
    #The encodings.idna Python module assumes that UseSTD3ASCIIRules == False

    #RFC 3490, Section 4, Step 4
    #We use the ToASCII operation because we are about to put the authority
    #into an IDN-unaware slot
    asciiLabels = []
    try:
        import encodings.idna
        for label in labels:
            if label:
                asciiLabels.append(encodings.idna.ToASCII(label))
            else:
                 #encodings.idna.ToASCII does not accept an empty string, but
                 #it is necessary for us to allow for empty labels so that we
                 #don't modify the URL
                asciiLabels.append('')
    except:
        asciiLabels = [str(label) for label in labels]
    #RFC 3490, Section 4, Step 5
    return str(reduce(lambda x, y: x + unichr(0x002E) + y, asciiLabels))


def unicode_to_ascii_url(url, prepend_scheme):
    '''
    Converts the inputed unicode url into a US-ASCII equivalent. This function
    goes a little beyond RFC 3490, which is limited in scope to the domain name
    (authority) only. Here, the functionality is expanded to what was observed
    on Wikipedia on 2009-Jan-22:

       Component    Can Use Unicode?
       ---------    ----------------
       scheme       No
       authority    Yes
       path         Yes
       query        Yes
       fragment     No

    The authority component gets converted to punycode, but occurrences of
    unicode in other components get converted into a pair of URI escapes (we
    assume 4-byte unicode). E.g. the unicode character U+4E2D will be
    converted into '%4E%2D'. Testing with Firefox v3.0.5 has shown that it can
    understand this kind of URI encoding.

    :param url: unicode string, the URL to convert from unicode into US-ASCII
    :param prepend_scheme: string, a protocol scheme to prepend to the URL if
        we're having trouble parsing it.
        e.g. "http". Input None to disable this functionality
    :returns: a US-ASCII equivalent of the inputed url
    :rtype: string

    @author: Jonathan Benn
    '''
    #convert the authority component of the URL into an ASCII punycode string,
    #but encode the rest using the regular URI character encoding

    groups = url_split_regex.match(url).groups()
    #If no authority was found
    if not groups[3]:
        #Try appending a scheme to see if that fixes the problem
        scheme_to_prepend = prepend_scheme or 'http'
        groups = url_split_regex.match(
            unicode(scheme_to_prepend) + u'://' + url).groups()
    #if we still can't find the authority
    if not groups[3]:
        raise Exception('No authority component found, ' +
                        'could not decode unicode to US-ASCII')

    #We're here if we found an authority, let's rebuild the URL
    scheme = groups[1]
    authority = groups[3]
    path = groups[4] or ''
    query = groups[5] or ''
    fragment = groups[7] or ''

    if prepend_scheme:
        scheme = str(scheme) + '://'
    else:
        scheme = ''
    return scheme + unicode_to_ascii_authority(authority) +\
        escape_unicode(path) + escape_unicode(query) + str(fragment)


class IS_GENERIC_URL(Validator):
    """
    Rejects a URL string if any of the following is true:
       * The string is empty or None
       * The string uses characters that are not allowed in a URL
       * The URL scheme specified (if one is specified) is not valid

    Based on RFC 2396: http://www.faqs.org/rfcs/rfc2396.html

    This function only checks the URL's syntax. It does not check that the URL
    points to a real document, for example, or that it otherwise makes sense
    semantically. This function does automatically prepend 'http://' in front
    of a URL if and only if that's necessary to successfully parse the URL.
    Please note that a scheme will be prepended only for rare cases
    (e.g. 'google.ca:80')

    The list of allowed schemes is customizable with the allowed_schemes
    parameter. If you exclude None from the list, then abbreviated URLs
    (lacking a scheme such as 'http') will be rejected.

    The default prepended scheme is customizable with the prepend_scheme
    parameter. If you set prepend_scheme to None then prepending will be
    disabled. URLs that require prepending to parse will still be accepted,
    but the return value will not be modified.

    @author: Jonathan Benn

    >>> IS_GENERIC_URL()('http://user@abc.com')
    ('http://user@abc.com', None)

    """

    def __init__(
        self,
        error_message='enter a valid URL',
        allowed_schemes=None,
        prepend_scheme=None,
    ):
        """
        :param error_message: a string, the error message to give the end user
            if the URL does not validate
        :param allowed_schemes: a list containing strings or None. Each element
            is a scheme the inputed URL is allowed to use
        :param prepend_scheme: a string, this scheme is prepended if it's
            necessary to make the URL valid
        """

        self.error_message = error_message
        if allowed_schemes is None:
            self.allowed_schemes = all_url_schemes
        else:
            self.allowed_schemes = allowed_schemes
        self.prepend_scheme = prepend_scheme
        if self.prepend_scheme not in self.allowed_schemes:
            raise SyntaxError("prepend_scheme='%s' is not in allowed_schemes=%s"
                              % (self.prepend_scheme, self.allowed_schemes))

    GENERIC_URL = re.compile(r"%[^0-9A-Fa-f]{2}|%[^0-9A-Fa-f][0-9A-Fa-f]|%[0-9A-Fa-f][^0-9A-Fa-f]|%$|%[0-9A-Fa-f]$|%[^0-9A-Fa-f]$")
    GENERIC_URL_VALID = re.compile(r"[A-Za-z0-9;/?:@&=+$,\-_\.!~*'\(\)%#]+$")

    def __call__(self, value):
        """
        :param value: a string, the URL to validate
        :returns: a tuple, where tuple[0] is the inputed value (possible
            prepended with prepend_scheme), and tuple[1] is either
            None (success!) or the string error_message
        """
        try:
            # if the URL does not misuse the '%' character
            if not self.GENERIC_URL.search(value):
                # if the URL is only composed of valid characters
                if self.GENERIC_URL_VALID.match(value):
                    # Then split up the URL into its components and check on
                    # the scheme
                    scheme = url_split_regex.match(value).group(2)
                    # Clean up the scheme before we check it
                    if not scheme is None:
                        scheme = urllib.unquote(scheme).lower()
                    # If the scheme really exists
                    if scheme in self.allowed_schemes:
                        # Then the URL is valid
                        return (value, None)
                    else:
                        # else, for the possible case of abbreviated URLs with
                        # ports, check to see if adding a valid scheme fixes
                        # the problem (but only do this if it doesn't have
                        # one already!)
                        if value.find('://') < 0 and None in self.allowed_schemes:
                            schemeToUse = self.prepend_scheme or 'http'
                            prependTest = self.__call__(
                                schemeToUse + '://' + value)
                            # if the prepend test succeeded
                            if prependTest[1] is None:
                                # if prepending in the output is enabled
                                if self.prepend_scheme:
                                    return prependTest
                                else:
                                    # else return the original,
                                    #  non-prepended value
                                    return (value, None)
        except:
            pass
        # else the URL is not valid
        return (value, translate(self.error_message))

# Sources (obtained 2008-Nov-11):
#    http://en.wikipedia.org/wiki/Top-level_domain
#    http://www.iana.org/domains/root/db/

official_top_level_domains = [
    'ac',
    'ad',
    'ae',
    'aero',
    'af',
    'ag',
    'ai',
    'al',
    'am',
    'an',
    'ao',
    'aq',
    'ar',
    'arpa',
    'as',
    'asia',
    'at',
    'au',
    'aw',
    'ax',
    'az',
    'ba',
    'bb',
    'bd',
    'be',
    'bf',
    'bg',
    'bh',
    'bi',
    'biz',
    'bj',
    'bl',
    'bm',
    'bn',
    'bo',
    'br',
    'bs',
    'bt',
    'bv',
    'bw',
    'by',
    'bz',
    'ca',
    'cat',
    'cc',
    'cd',
    'cf',
    'cg',
    'ch',
    'ci',
    'ck',
    'cl',
    'cm',
    'cn',
    'co',
    'com',
    'coop',
    'cr',
    'cu',
    'cv',
    'cx',
    'cy',
    'cz',
    'de',
    'dj',
    'dk',
    'dm',
    'do',
    'dz',
    'ec',
    'edu',
    'ee',
    'eg',
    'eh',
    'er',
    'es',
    'et',
    'eu',
    'example',
    'fi',
    'fj',
    'fk',
    'fm',
    'fo',
    'fr',
    'ga',
    'gb',
    'gd',
    'ge',
    'gf',
    'gg',
    'gh',
    'gi',
    'gl',
    'gm',
    'gn',
    'gov',
    'gp',
    'gq',
    'gr',
    'gs',
    'gt',
    'gu',
    'gw',
    'gy',
    'hk',
    'hm',
    'hn',
    'hr',
    'ht',
    'hu',
    'id',
    'ie',
    'il',
    'im',
    'in',
    'info',
    'int',
    'invalid',
    'io',
    'iq',
    'ir',
    'is',
    'it',
    'je',
    'jm',
    'jo',
    'jobs',
    'jp',
    'ke',
    'kg',
    'kh',
    'ki',
    'km',
    'kn',
    'kp',
    'kr',
    'kw',
    'ky',
    'kz',
    'la',
    'lb',
    'lc',
    'li',
    'lk',
    'localhost',
    'lr',
    'ls',
    'lt',
    'lu',
    'lv',
    'ly',
    'ma',
    'mc',
    'md',
    'me',
    'mf',
    'mg',
    'mh',
    'mil',
    'mk',
    'ml',
    'mm',
    'mn',
    'mo',
    'mobi',
    'mp',
    'mq',
    'mr',
    'ms',
    'mt',
    'mu',
    'museum',
    'mv',
    'mw',
    'mx',
    'my',
    'mz',
    'na',
    'name',
    'nc',
    'ne',
    'net',
    'nf',
    'ng',
    'ni',
    'nl',
    'no',
    'np',
    'nr',
    'nu',
    'nz',
    'om',
    'org',
    'pa',
    'pe',
    'pf',
    'pg',
    'ph',
    'pk',
    'pl',
    'pm',
    'pn',
    'pr',
    'pro',
    'ps',
    'pt',
    'pw',
    'py',
    'qa',
    're',
    'ro',
    'rs',
    'ru',
    'rw',
    'sa',
    'sb',
    'sc',
    'sd',
    'se',
    'sg',
    'sh',
    'si',
    'sj',
    'sk',
    'sl',
    'sm',
    'sn',
    'so',
    'sr',
    'st',
    'su',
    'sv',
    'sy',
    'sz',
    'tc',
    'td',
    'tel',
    'test',
    'tf',
    'tg',
    'th',
    'tj',
    'tk',
    'tl',
    'tm',
    'tn',
    'to',
    'tp',
    'tr',
    'travel',
    'tt',
    'tv',
    'tw',
    'tz',
    'ua',
    'ug',
    'uk',
    'um',
    'us',
    'uy',
    'uz',
    'va',
    'vc',
    've',
    'vg',
    'vi',
    'vn',
    'vu',
    'wf',
    'ws',
    'xn--0zwm56d',
    'xn--11b5bs3a9aj6g',
    'xn--80akhbyknj4f',
    'xn--9t4b11yi5a',
    'xn--deba0ad',
    'xn--g6w251d',
    'xn--hgbk6aj7f53bba',
    'xn--hlcj6aya9esc7a',
    'xn--jxalpdlp',
    'xn--kgbechtv',
    'xn--p1ai',
    'xn--zckzah',
    'ye',
    'yt',
    'yu',
    'za',
    'zm',
    'zw',
]


class IS_HTTP_URL(Validator):
    """
    Rejects a URL string if any of the following is true:
       * The string is empty or None
       * The string uses characters that are not allowed in a URL
       * The string breaks any of the HTTP syntactic rules
       * The URL scheme specified (if one is specified) is not 'http' or 'https'
       * The top-level domain (if a host name is specified) does not exist

    Based on RFC 2616: http://www.faqs.org/rfcs/rfc2616.html

    This function only checks the URL's syntax. It does not check that the URL
    points to a real document, for example, or that it otherwise makes sense
    semantically. This function does automatically prepend 'http://' in front
    of a URL in the case of an abbreviated URL (e.g. 'google.ca').

    The list of allowed schemes is customizable with the allowed_schemes
    parameter. If you exclude None from the list, then abbreviated URLs
    (lacking a scheme such as 'http') will be rejected.

    The default prepended scheme is customizable with the prepend_scheme
    parameter. If you set prepend_scheme to None then prepending will be
    disabled. URLs that require prepending to parse will still be accepted,
    but the return value will not be modified.

    @author: Jonathan Benn

    >>> IS_HTTP_URL()('http://1.2.3.4')
    ('http://1.2.3.4', None)
    >>> IS_HTTP_URL()('http://abc.com')
    ('http://abc.com', None)
    >>> IS_HTTP_URL()('https://abc.com')
    ('https://abc.com', None)
    >>> IS_HTTP_URL()('httpx://abc.com')
    ('httpx://abc.com', 'enter a valid URL')
    >>> IS_HTTP_URL()('http://abc.com:80')
    ('http://abc.com:80', None)
    >>> IS_HTTP_URL()('http://user@abc.com')
    ('http://user@abc.com', None)
    >>> IS_HTTP_URL()('http://user@1.2.3.4')
    ('http://user@1.2.3.4', None)

    """

    GENERIC_VALID_IP = re.compile(
        "([\w.!~*'|;:&=+$,-]+@)?\d+\.\d+\.\d+\.\d+(:\d*)*$")
    GENERIC_VALID_DOMAIN = re.compile("([\w.!~*'|;:&=+$,-]+@)?(([A-Za-z0-9]+[A-Za-z0-9\-]*[A-Za-z0-9]+\.)*([A-Za-z0-9]+\.)*)*([A-Za-z]+[A-Za-z0-9\-]*[A-Za-z0-9]+)\.?(:\d*)*$")

    def __init__(
        self,
        error_message='enter a valid URL',
        allowed_schemes=None,
        prepend_scheme='http',
    ):
        """
        :param error_message: a string, the error message to give the end user
            if the URL does not validate
        :param allowed_schemes: a list containing strings or None. Each element
            is a scheme the inputed URL is allowed to use
        :param prepend_scheme: a string, this scheme is prepended if it's
            necessary to make the URL valid
        """

        self.error_message = error_message
        if allowed_schemes is None:
            self.allowed_schemes = http_schemes
        else:
            self.allowed_schemes = allowed_schemes
        self.prepend_scheme = prepend_scheme

        for i in self.allowed_schemes:
            if i not in http_schemes:
                raise SyntaxError("allowed_scheme value '%s' is not in %s" %
                                  (i, http_schemes))

        if self.prepend_scheme not in self.allowed_schemes:
            raise SyntaxError("prepend_scheme='%s' is not in allowed_schemes=%s" %
                              (self.prepend_scheme, self.allowed_schemes))

    def __call__(self, value):
        """
        :param value: a string, the URL to validate
        :returns: a tuple, where tuple[0] is the inputed value
            (possible prepended with prepend_scheme), and tuple[1] is either
            None (success!) or the string error_message
        """

        try:
            # if the URL passes generic validation
            x = IS_GENERIC_URL(error_message=self.error_message,
                               allowed_schemes=self.allowed_schemes,
                               prepend_scheme=self.prepend_scheme)
            if x(value)[1] is None:
                componentsMatch = url_split_regex.match(value)
                authority = componentsMatch.group(4)
                # if there is an authority component
                if authority:
                    # if authority is a valid IP address
                    if self.GENERIC_VALID_IP.match(authority):
                        # Then this HTTP URL is valid
                        return (value, None)
                    else:
                        # else if authority is a valid domain name
                        domainMatch = self.GENERIC_VALID_DOMAIN.match(
                            authority)
                        if domainMatch:
                            # if the top-level domain really exists
                            if domainMatch.group(5).lower()\
                                    in official_top_level_domains:
                                # Then this HTTP URL is valid
                                return (value, None)
                else:
                    # else this is a relative/abbreviated URL, which will parse
                    # into the URL's path component
                    path = componentsMatch.group(5)
                    # relative case: if this is a valid path (if it starts with
                    # a slash)
                    if path.startswith('/'):
                        # Then this HTTP URL is valid
                        return (value, None)
                    else:
                        # abbreviated case: if we haven't already, prepend a
                        # scheme and see if it fixes the problem
                        if value.find('://') < 0:
                            schemeToUse = self.prepend_scheme or 'http'
                            prependTest = self.__call__(schemeToUse
                                                        + '://' + value)
                            # if the prepend test succeeded
                            if prependTest[1] is None:
                                # if prepending in the output is enabled
                                if self.prepend_scheme:
                                    return prependTest
                                else:
                                    # else return the original, non-prepended
                                    # value
                                    return (value, None)
        except:
            pass
        # else the HTTP URL is not valid
        return (value, translate(self.error_message))


class IS_URL(Validator):
    """
    Rejects a URL string if any of the following is true:
       * The string is empty or None
       * The string uses characters that are not allowed in a URL
       * The string breaks any of the HTTP syntactic rules
       * The URL scheme specified (if one is specified) is not 'http' or 'https'
       * The top-level domain (if a host name is specified) does not exist

    (These rules are based on RFC 2616: http://www.faqs.org/rfcs/rfc2616.html)

    This function only checks the URL's syntax. It does not check that the URL
    points to a real document, for example, or that it otherwise makes sense
    semantically. This function does automatically prepend 'http://' in front
    of a URL in the case of an abbreviated URL (e.g. 'google.ca').

    If the parameter mode='generic' is used, then this function's behavior
    changes. It then rejects a URL string if any of the following is true:
       * The string is empty or None
       * The string uses characters that are not allowed in a URL
       * The URL scheme specified (if one is specified) is not valid

    (These rules are based on RFC 2396: http://www.faqs.org/rfcs/rfc2396.html)

    The list of allowed schemes is customizable with the allowed_schemes
    parameter. If you exclude None from the list, then abbreviated URLs
    (lacking a scheme such as 'http') will be rejected.

    The default prepended scheme is customizable with the prepend_scheme
    parameter. If you set prepend_scheme to None then prepending will be
    disabled. URLs that require prepending to parse will still be accepted,
    but the return value will not be modified.

    IS_URL is compatible with the Internationalized Domain Name (IDN) standard
    specified in RFC 3490 (http://tools.ietf.org/html/rfc3490). As a result,
    URLs can be regular strings or unicode strings.
    If the URL's domain component (e.g. google.ca) contains non-US-ASCII
    letters, then the domain will be converted into Punycode (defined in
    RFC 3492, http://tools.ietf.org/html/rfc3492). IS_URL goes a bit beyond
    the standards, and allows non-US-ASCII characters to be present in the path
    and query components of the URL as well. These non-US-ASCII characters will
    be escaped using the standard '%20' type syntax. e.g. the unicode
    character with hex code 0x4e86 will become '%4e%86'

    Code Examples::

        INPUT(_type='text', _name='name', requires=IS_URL())
        >>> IS_URL()('abc.com')
        ('http://abc.com', None)

        INPUT(_type='text', _name='name', requires=IS_URL(mode='generic'))
        >>> IS_URL(mode='generic')('abc.com')
        ('abc.com', None)

        INPUT(_type='text', _name='name',
            requires=IS_URL(allowed_schemes=['https'], prepend_scheme='https'))
        >>> IS_URL(allowed_schemes=['https'], prepend_scheme='https')('https://abc.com')
        ('https://abc.com', None)

        INPUT(_type='text', _name='name',
            requires=IS_URL(prepend_scheme='https'))
        >>> IS_URL(prepend_scheme='https')('abc.com')
        ('https://abc.com', None)

        INPUT(_type='text', _name='name',
            requires=IS_URL(mode='generic', allowed_schemes=['ftps', 'https'],
                prepend_scheme='https'))
        >>> IS_URL(mode='generic', allowed_schemes=['ftps', 'https'], prepend_scheme='https')('https://abc.com')
        ('https://abc.com', None)
        >>> IS_URL(mode='generic', allowed_schemes=['ftps', 'https', None], prepend_scheme='https')('abc.com')
        ('abc.com', None)

    @author: Jonathan Benn
    """

    def __init__(
        self,
        error_message='enter a valid URL',
        mode='http',
        allowed_schemes=None,
        prepend_scheme='http',
    ):
        """
        :param error_message: a string, the error message to give the end user
            if the URL does not validate
        :param allowed_schemes: a list containing strings or None. Each element
            is a scheme the inputed URL is allowed to use
        :param prepend_scheme: a string, this scheme is prepended if it's
            necessary to make the URL valid
        """

        self.error_message = error_message
        self.mode = mode.lower()
        if not self.mode in ['generic', 'http']:
            raise SyntaxError("invalid mode '%s' in IS_URL" % self.mode)
        self.allowed_schemes = allowed_schemes

        if self.allowed_schemes:
            if prepend_scheme not in self.allowed_schemes:
                raise SyntaxError("prepend_scheme='%s' is not in allowed_schemes=%s"
                                  % (prepend_scheme, self.allowed_schemes))

        # if allowed_schemes is None, then we will defer testing
        # prepend_scheme's validity to a sub-method

        self.prepend_scheme = prepend_scheme

    def __call__(self, value):
        """
        :param value: a unicode or regular string, the URL to validate
        :returns: a (string, string) tuple, where tuple[0] is the modified
            input value and tuple[1] is either None (success!) or the
            string error_message. The input value will never be modified in the
            case of an error. However, if there is success then the input URL
            may be modified to (1) prepend a scheme, and/or (2) convert a
            non-compliant unicode URL into a compliant US-ASCII version.
        """

        if self.mode == 'generic':
            subMethod = IS_GENERIC_URL(error_message=self.error_message,
                                       allowed_schemes=self.allowed_schemes,
                                       prepend_scheme=self.prepend_scheme)
        elif self.mode == 'http':
            subMethod = IS_HTTP_URL(error_message=self.error_message,
                                    allowed_schemes=self.allowed_schemes,
                                    prepend_scheme=self.prepend_scheme)
        else:
            raise SyntaxError("invalid mode '%s' in IS_URL" % self.mode)

        if type(value) != unicode:
            return subMethod(value)
        else:
            try:
                asciiValue = unicode_to_ascii_url(value, self.prepend_scheme)
            except Exception:
                #If we are not able to convert the unicode url into a
                # US-ASCII URL, then the URL is not valid
                return (value, translate(self.error_message))

            methodResult = subMethod(asciiValue)
            #if the validation of the US-ASCII version of the value failed
            if not methodResult[1] is None:
                # then return the original input value, not the US-ASCII version
                return (value, methodResult[1])
            else:
                return methodResult


regex_time = re.compile(
    '((?P<h>[0-9]+))([^0-9 ]+(?P<m>[0-9 ]+))?([^0-9ap ]+(?P<s>[0-9]*))?((?P<d>[ap]m))?')


class IS_TIME(Validator):
    """
    example::

        INPUT(_type='text', _name='name', requires=IS_TIME())

    understands the following formats
    hh:mm:ss [am/pm]
    hh:mm [am/pm]
    hh [am/pm]

    [am/pm] is optional, ':' can be replaced by any other non-space non-digit

        >>> IS_TIME()('21:30')
        (datetime.time(21, 30), None)
        >>> IS_TIME()('21-30')
        (datetime.time(21, 30), None)
        >>> IS_TIME()('21.30')
        (datetime.time(21, 30), None)
        >>> IS_TIME()('21:30:59')
        (datetime.time(21, 30, 59), None)
        >>> IS_TIME()('5:30')
        (datetime.time(5, 30), None)
        >>> IS_TIME()('5:30 am')
        (datetime.time(5, 30), None)
        >>> IS_TIME()('5:30 pm')
        (datetime.time(17, 30), None)
        >>> IS_TIME()('5:30 whatever')
        ('5:30 whatever', 'enter time as hh:mm:ss (seconds, am, pm optional)')
        >>> IS_TIME()('5:30 20')
        ('5:30 20', 'enter time as hh:mm:ss (seconds, am, pm optional)')
        >>> IS_TIME()('24:30')
        ('24:30', 'enter time as hh:mm:ss (seconds, am, pm optional)')
        >>> IS_TIME()('21:60')
        ('21:60', 'enter time as hh:mm:ss (seconds, am, pm optional)')
        >>> IS_TIME()('21:30::')
        ('21:30::', 'enter time as hh:mm:ss (seconds, am, pm optional)')
        >>> IS_TIME()('')
        ('', 'enter time as hh:mm:ss (seconds, am, pm optional)')
    """

    def __init__(self, error_message='enter time as hh:mm:ss (seconds, am, pm optional)'):
        self.error_message = error_message

    def __call__(self, value):
        try:
            ivalue = value
            value = regex_time.match(value.lower())
            (h, m, s) = (int(value.group('h')), 0, 0)
            if not value.group('m') is None:
                m = int(value.group('m'))
            if not value.group('s') is None:
                s = int(value.group('s'))
            if value.group('d') == 'pm' and 0 < h < 12:
                h = h + 12
            if not (h in range(24) and m in range(60) and s
                    in range(60)):
                raise ValueError('Hours or minutes or seconds are outside of allowed range')
            value = datetime.time(h, m, s)
            return (value, None)
        except AttributeError:
            pass
        except ValueError:
            pass
        return (ivalue, translate(self.error_message))

# A UTC class.
class UTC(datetime.tzinfo):
    """UTC"""
    ZERO = datetime.timedelta(0)
    def utcoffset(self, dt):
        return UTC.ZERO
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return UTC.ZERO
utc = UTC()

class IS_DATE(Validator):
    """
    example::

        INPUT(_type='text', _name='name', requires=IS_DATE())

    date has to be in the ISO8960 format YYYY-MM-DD
    """

    def __init__(self, format='%Y-%m-%d',
                 error_message='enter date as %(format)s',
                 timezone = None):
        """
        timezome must be None or a pytz.timezone("America/Chicago") object
        """
        self.format = translate(format)
        self.error_message = str(error_message)
        self.timezone = timezone
        self.extremes = {}

    def __call__(self, value):
        ovalue = value
        if isinstance(value, datetime.date):
            if self.timezone is not None:
                value = value - datetime.timedelta(seconds=self.timezone*3600)
            return (value, None)
        try:
            (y, m, d, hh, mm, ss, t0, t1, t2) = \
                time.strptime(value, str(self.format))
            value = datetime.date(y, m, d)
            if self.timezone is not None:
                value = self.timezone.localize(value).astimezone(utc)
            return (value, None)
        except:
            self.extremes.update(IS_DATETIME.nice(self.format))
            return (ovalue, translate(self.error_message) % self.extremes)

    def formatter(self, value):
        if value is None:
            return None
        format = self.format
        year = value.year
        y = '%.4i' % year
        format = format.replace('%y', y[-2:])
        format = format.replace('%Y', y)
        if year < 1900:
            year = 2000
        d = datetime.date(year, value.month, value.day)
        if self.timezone is not None:
            d = d.replace(tzinfo=utc).astimezone(self.timezone)
        return d.strftime(format)


class IS_DATETIME(Validator):
    """
    example::

        INPUT(_type='text', _name='name', requires=IS_DATETIME())

    datetime has to be in the ISO8960 format YYYY-MM-DD hh:mm:ss
    """

    isodatetime = '%Y-%m-%d %H:%M:%S'

    @staticmethod
    def nice(format):
        code = (('%Y', '1963'),
                ('%y', '63'),
                ('%d', '28'),
                ('%m', '08'),
                ('%b', 'Aug'),
                ('%B', 'August'),
                ('%H', '14'),
                ('%I', '02'),
                ('%p', 'PM'),
                ('%M', '30'),
                ('%S', '59'))
        for (a, b) in code:
            format = format.replace(a, b)
        return dict(format=format)

    def __init__(self, format='%Y-%m-%d %H:%M:%S',
                 error_message='enter date and time as %(format)s',
                 timezone=None):
        """
        timezome must be None or a pytz.timezone("America/Chicago") object
        """
        self.format = translate(format)
        self.error_message = str(error_message)
        self.extremes = {}
        self.timezone = timezone

    def __call__(self, value):
        ovalue = value
        if isinstance(value, datetime.datetime):
            return (value, None)
        try:
            (y, m, d, hh, mm, ss, t0, t1, t2) = \
                time.strptime(value, str(self.format))
            value = datetime.datetime(y, m, d, hh, mm, ss)
            if self.timezone is not None:
                value = self.timezone.localize(value).astimezone(utc)
            return (value, None)
        except:
            self.extremes.update(IS_DATETIME.nice(self.format))
            return (ovalue, translate(self.error_message) % self.extremes)

    def formatter(self, value):
        if value is None:
            return None
        format = self.format
        year = value.year
        y = '%.4i' % year
        format = format.replace('%y', y[-2:])
        format = format.replace('%Y', y)
        if year < 1900:
            year = 2000
        d = datetime.datetime(year, value.month, value.day,
                              value.hour, value.minute, value.second)
        if self.timezone is not None:
            d = d.replace(tzinfo=utc).astimezone(self.timezone)
        return d.strftime(format)


class IS_DATE_IN_RANGE(IS_DATE):
    """
    example::

        >>> v = IS_DATE_IN_RANGE(minimum=datetime.date(2008,1,1), \
                                 maximum=datetime.date(2009,12,31), \
                                 format="%m/%d/%Y",error_message="oops")

        >>> v('03/03/2008')
        (datetime.date(2008, 3, 3), None)

        >>> v('03/03/2010')
        ('03/03/2010', 'oops')

        >>> v(datetime.date(2008,3,3))
        (datetime.date(2008, 3, 3), None)

        >>> v(datetime.date(2010,3,3))
        (datetime.date(2010, 3, 3), 'oops')

    """
    def __init__(self,
                 minimum=None,
                 maximum=None,
                 format='%Y-%m-%d',
                 error_message=None,
                 timezone=None):
        self.minimum = minimum
        self.maximum = maximum
        if error_message is None:
            if minimum is None:
                error_message = "enter date on or before %(max)s"
            elif maximum is None:
                error_message = "enter date on or after %(min)s"
            else:
                error_message = "enter date in range %(min)s %(max)s"
        IS_DATE.__init__(self,
                         format=format,
                         error_message=error_message,
                         timezone=timezone)
        self.extremes = dict(min=minimum, max=maximum)

    def __call__(self, value):
        ovalue = value
        (value, msg) = IS_DATE.__call__(self, value)
        if msg is not None:
            return (value, msg)
        if self.minimum and self.minimum > value:
            return (ovalue, translate(self.error_message) % self.extremes)
        if self.maximum and value > self.maximum:
            return (ovalue, translate(self.error_message) % self.extremes)
        return (value, None)


class IS_DATETIME_IN_RANGE(IS_DATETIME):
    """
    example::

        >>> v = IS_DATETIME_IN_RANGE(\
                minimum=datetime.datetime(2008,1,1,12,20), \
                maximum=datetime.datetime(2009,12,31,12,20), \
                format="%m/%d/%Y %H:%M",error_message="oops")
        >>> v('03/03/2008 12:40')
        (datetime.datetime(2008, 3, 3, 12, 40), None)

        >>> v('03/03/2010 10:34')
        ('03/03/2010 10:34', 'oops')

        >>> v(datetime.datetime(2008,3,3,0,0))
        (datetime.datetime(2008, 3, 3, 0, 0), None)

        >>> v(datetime.datetime(2010,3,3,0,0))
        (datetime.datetime(2010, 3, 3, 0, 0), 'oops')
    """
    def __init__(self,
                 minimum=None,
                 maximum=None,
                 format='%Y-%m-%d %H:%M:%S',
                 error_message=None,
                 timezone=None):
        self.minimum = minimum
        self.maximum = maximum
        if error_message is None:
            if minimum is None:
                error_message = "enter date and time on or before %(max)s"
            elif maximum is None:
                error_message = "enter date and time on or after %(min)s"
            else:
                error_message = "enter date and time in range %(min)s %(max)s"
        IS_DATETIME.__init__(self,
                             format=format,
                             error_message=error_message,
                             timezone=timezone)
        self.extremes = dict(min=minimum, max=maximum)

    def __call__(self, value):
        ovalue = value
        (value, msg) = IS_DATETIME.__call__(self, value)
        if msg is not None:
            return (value, msg)
        if self.minimum and self.minimum > value:
            return (ovalue, translate(self.error_message) % self.extremes)
        if self.maximum and value > self.maximum:
            return (ovalue, translate(self.error_message) % self.extremes)
        return (value, None)


class IS_LIST_OF(Validator):

    def __init__(self, other=None, minimum=0, maximum=100,
                 error_message=None):
        self.other = other
        self.minimum = minimum
        self.maximum = maximum
        self.error_message = error_message or "enter between %(min)g and %(max)g values"

    def __call__(self, value):
        ivalue = value
        if not isinstance(value, list):
            ivalue = [ivalue]
        if not self.minimum is None and len(ivalue) < self.minimum:
            return (ivalue, translate(self.error_message) % dict(min=self.minimum, max=self.maximum))
        if not self.maximum is None and len(ivalue) > self.maximum:
            return (ivalue, translate(self.error_message) % dict(min=self.minimum, max=self.maximum))
        new_value = []
        if self.other:
            for item in ivalue:
                if item.strip():
                    (v, e) = self.other(item)
                    if e:
                        return (ivalue, e)
                    else:
                        new_value.append(v)
            ivalue = new_value
        return (ivalue, None)


class IS_LOWER(Validator):
    """
    convert to lower case

    >>> IS_LOWER()('ABC')
    ('abc', None)
    >>> IS_LOWER()('Ñ')
    ('\\xc3\\xb1', None)
    """

    def __call__(self, value):
        return (value.decode('utf8').lower().encode('utf8'), None)


class IS_UPPER(Validator):
    """
    convert to upper case

    >>> IS_UPPER()('abc')
    ('ABC', None)
    >>> IS_UPPER()('ñ')
    ('\\xc3\\x91', None)
    """

    def __call__(self, value):
        return (value.decode('utf8').upper().encode('utf8'), None)


def urlify(s, maxlen=80, keep_underscores=False):
    """
    Convert incoming string to a simplified ASCII subset.
    if (keep_underscores): underscores are retained in the string
    else: underscores are translated to hyphens (default)
    """
    if isinstance(s, str):
        s = s.decode('utf-8')             # to unicode
    s = s.lower()                         # to lowercase
    s = unicodedata.normalize('NFKD', s)  # normalize eg è => e, ñ => n
    s = s.encode('ascii', 'ignore')       # encode as ASCII
    s = re.sub('&\w+?;', '', s)           # strip html entities
    if keep_underscores:
        s = re.sub('\s+', '-', s)         # whitespace to hyphens
        s = re.sub('[^\w\-]', '', s)
                   # strip all but alphanumeric/underscore/hyphen
    else:
        s = re.sub('[\s_]+', '-', s)      # whitespace & underscores to hyphens
        s = re.sub('[^a-z0-9\-]', '', s)  # strip all but alphanumeric/hyphen
    s = re.sub('[-_][-_]+', '-', s)       # collapse strings of hyphens
    s = s.strip('-')                      # remove leading and trailing hyphens
    return s[:maxlen]                     # enforce maximum length


class IS_SLUG(Validator):
    """
    convert arbitrary text string to a slug

    >>> IS_SLUG()('abc123')
    ('abc123', None)
    >>> IS_SLUG()('ABC123')
    ('abc123', None)
    >>> IS_SLUG()('abc-123')
    ('abc-123', None)
    >>> IS_SLUG()('abc--123')
    ('abc-123', None)
    >>> IS_SLUG()('abc 123')
    ('abc-123', None)
    >>> IS_SLUG()('abc\t_123')
    ('abc-123', None)
    >>> IS_SLUG()('-abc-')
    ('abc', None)
    >>> IS_SLUG()('--a--b--_ -c--')
    ('a-b-c', None)
    >>> IS_SLUG()('abc&amp;123')
    ('abc123', None)
    >>> IS_SLUG()('abc&amp;123&amp;def')
    ('abc123def', None)
    >>> IS_SLUG()('ñ')
    ('n', None)
    >>> IS_SLUG(maxlen=4)('abc123')
    ('abc1', None)
    >>> IS_SLUG()('abc_123')
    ('abc-123', None)
    >>> IS_SLUG(keep_underscores=False)('abc_123')
    ('abc-123', None)
    >>> IS_SLUG(keep_underscores=True)('abc_123')
    ('abc_123', None)
    >>> IS_SLUG(check=False)('abc')
    ('abc', None)
    >>> IS_SLUG(check=True)('abc')
    ('abc', None)
    >>> IS_SLUG(check=False)('a bc')
    ('a-bc', None)
    >>> IS_SLUG(check=True)('a bc')
    ('a bc', 'must be slug')
    """

    @staticmethod
    def urlify(value, maxlen=80, keep_underscores=False):
        return urlify(value, maxlen, keep_underscores)

    def __init__(self, maxlen=80, check=False, error_message='must be slug', keep_underscores=False):
        self.maxlen = maxlen
        self.check = check
        self.error_message = error_message
        self.keep_underscores = keep_underscores

    def __call__(self, value):
        if self.check and value != urlify(value, self.maxlen, self.keep_underscores):
            return (value, translate(self.error_message))
        return (urlify(value, self.maxlen, self.keep_underscores), None)


class ANY_OF(Validator):
    """
    test if any of the validators in a list return successfully

    >>> ANY_OF([IS_EMAIL(),IS_ALPHANUMERIC()])('a@b.co')
    ('a@b.co', None)
    >>> ANY_OF([IS_EMAIL(),IS_ALPHANUMERIC()])('abco')
    ('abco', None)
    >>> ANY_OF([IS_EMAIL(),IS_ALPHANUMERIC()])('@ab.co')
    ('@ab.co', 'enter only letters, numbers, and underscore')
    >>> ANY_OF([IS_ALPHANUMERIC(),IS_EMAIL()])('@ab.co')
    ('@ab.co', 'enter a valid email address')
    """

    def __init__(self, subs):
        self.subs = subs

    def __call__(self, value):
        for validator in self.subs:
            value, error = validator(value)
            if error == None:
                break
        return value, error

    def formatter(self, value):
        # Use the formatter of the first subvalidator
        # that validates the value and has a formatter
        for validator in self.subs:
            if hasattr(validator, 'formatter') and validator(value)[1] != None:
                return validator.formatter(value)


class IS_EMPTY_OR(Validator):
    """
    dummy class for testing IS_EMPTY_OR

    >>> IS_EMPTY_OR(IS_EMAIL())('abc@def.com')
    ('abc@def.com', None)
    >>> IS_EMPTY_OR(IS_EMAIL())('   ')
    (None, None)
    >>> IS_EMPTY_OR(IS_EMAIL(), null='abc')('   ')
    ('abc', None)
    >>> IS_EMPTY_OR(IS_EMAIL(), null='abc', empty_regex='def')('def')
    ('abc', None)
    >>> IS_EMPTY_OR(IS_EMAIL())('abc')
    ('abc', 'enter a valid email address')
    >>> IS_EMPTY_OR(IS_EMAIL())(' abc ')
    ('abc', 'enter a valid email address')
    """

    def __init__(self, other, null=None, empty_regex=None):
        (self.other, self.null) = (other, null)
        if empty_regex is not None:
            self.empty_regex = re.compile(empty_regex)
        else:
            self.empty_regex = None
        if hasattr(other, 'multiple'):
            self.multiple = other.multiple
        if hasattr(other, 'options'):
            self.options = self._options

    def _options(self, zero=False):
        options = self.other.options(zero=zero)
        if (not options or options[0][0] != '') and not self.multiple:
            options.insert(0, ('', ''))
        return options

    def set_self_id(self, id):
        if isinstance(self.other, (list, tuple)):
            for item in self.other:
                if hasattr(item, 'set_self_id'):
                    item.set_self_id(id)
        else:
            if hasattr(self.other, 'set_self_id'):
                self.other.set_self_id(id)

    def __call__(self, value):
        value, empty = is_empty(value, empty_regex=self.empty_regex)
        if empty:
            return (self.null, None)
        if isinstance(self.other, (list, tuple)):
            error = None
            for item in self.other:
                value, error = item(value)
                if error:
                    break
            return value, error
        else:
            return self.other(value)

    def formatter(self, value):
        if hasattr(self.other, 'formatter'):
            return self.other.formatter(value)
        return value

IS_NULL_OR = IS_EMPTY_OR    # for backward compatibility


class CLEANUP(Validator):
    """
    example::

        INPUT(_type='text', _name='name', requires=CLEANUP())

    removes special characters on validation
    """
    REGEX_CLEANUP = re.compile('[^\x09\x0a\x0d\x20-\x7e]')

    def __init__(self, regex=None):
        self.regex = self.REGEX_CLEANUP if regex is None \
            else re.compile(regex)

    def __call__(self, value):
        v = self.regex.sub('', str(value).strip())
        return (v, None)


class LazyCrypt(object):
    """
    Stores a lazy password hash
    """
    def __init__(self, crypt, password):
        """
        crypt is an instance of the CRYPT validator,
        password is the password as inserted by the user
        """
        self.crypt = crypt
        self.password = password
        self.crypted = None

    def __str__(self):
        """
        Encrypted self.password and caches it in self.crypted.
        If self.crypt.salt the output is in the format <algorithm>$<salt>$<hash>

        Try get the digest_alg from the key (if it exists)
        else assume the default digest_alg. If not key at all, set key=''

        If a salt is specified use it, if salt is True, set salt to uuid
        (this should all be backward compatible)

        Options:
        key = 'uuid'
        key = 'md5:uuid'
        key = 'sha512:uuid'
        ...
        key = 'pbkdf2(1000,64,sha512):uuid' 1000 iterations and 64 chars length
        """
        if self.crypted:
            return self.crypted
        if self.crypt.key:
            if ':' in self.crypt.key:
                digest_alg, key = self.crypt.key.split(':', 1)
            else:
                digest_alg, key = self.crypt.digest_alg, self.crypt.key
        else:
            digest_alg, key = self.crypt.digest_alg, ''
        if self.crypt.salt:
            if self.crypt.salt == True:
                salt = str(web2py_uuid()).replace('-', '')[-16:]
            else:
                salt = self.crypt.salt
        else:
            salt = ''
        hashed = simple_hash(self.password, key, salt, digest_alg)
        self.crypted = '%s$%s$%s' % (digest_alg, salt, hashed)
        return self.crypted

    def __eq__(self, stored_password):
        """
        compares the current lazy crypted password with a stored password
        """

        # LazyCrypt objects comparison
        if isinstance(stored_password, self.__class__):
            return ((self is stored_password) or
                   ((self.crypt.key == stored_password.crypt.key) and
                   (self.password == stored_password.password)))

        if self.crypt.key:
            if ':' in self.crypt.key:
                key = self.crypt.key.split(':')[1]
            else:
                key = self.crypt.key
        else:
            key = ''
        if stored_password is None:
            return False
        elif stored_password.count('$') == 2:
            (digest_alg, salt, hash) = stored_password.split('$')
            h = simple_hash(self.password, key, salt, digest_alg)
            temp_pass = '%s$%s$%s' % (digest_alg, salt, h)
        else:  # no salting
            # guess digest_alg
            digest_alg = DIGEST_ALG_BY_SIZE.get(len(stored_password), None)
            if not digest_alg:
                return False
            else:
                temp_pass = simple_hash(self.password, key, '', digest_alg)
        return temp_pass == stored_password


class CRYPT(object):
    """
    example::

        INPUT(_type='text', _name='name', requires=CRYPT())

    encodes the value on validation with a digest.

    If no arguments are provided CRYPT uses the MD5 algorithm.
    If the key argument is provided the HMAC+MD5 algorithm is used.
    If the digest_alg is specified this is used to replace the
    MD5 with, for example, SHA512. The digest_alg can be
    the name of a hashlib algorithm as a string or the algorithm itself.

    min_length is the minimal password length (default 4) - IS_STRONG for serious security
    error_message is the message if password is too short

    Notice that an empty password is accepted but invalid. It will not allow login back.
    Stores junk as hashed password.

    Specify an algorithm or by default we will use sha512.

    Typical available algorithms:
      md5, sha1, sha224, sha256, sha384, sha512

    If salt, it hashes a password with a salt.
    If salt is True, this method will automatically generate one.
    Either case it returns an encrypted password string in the following format:

      <algorithm>$<salt>$<hash>

    Important: hashed password is returned as a LazyCrypt object and computed only if needed.
    The LasyCrypt object also knows how to compare itself with an existing salted password

    Supports standard algorithms

    >>> for alg in ('md5','sha1','sha256','sha384','sha512'):
    ...     print str(CRYPT(digest_alg=alg,salt=True)('test')[0])
    md5$...$...
    sha1$...$...
    sha256$...$...
    sha384$...$...
    sha512$...$...

    The syntax is always alg$salt$hash

    Supports for pbkdf2

    >>> alg = 'pbkdf2(1000,20,sha512)'
    >>> print str(CRYPT(digest_alg=alg,salt=True)('test')[0])
    pbkdf2(1000,20,sha512)$...$...

    An optional hmac_key can be specified and it is used as salt prefix

    >>> a = str(CRYPT(digest_alg='md5',key='mykey',salt=True)('test')[0])
    >>> print a
    md5$...$...

    Even if the algorithm changes the hash can still be validated

    >>> CRYPT(digest_alg='sha1',key='mykey',salt=True)('test')[0] == a
    True

    If no salt is specified CRYPT can guess the algorithms from length:

    >>> a = str(CRYPT(digest_alg='sha1',salt=False)('test')[0])
    >>> a
    'sha1$$a94a8fe5ccb19ba61c4c0873d391e987982fbbd3'
    >>> CRYPT(digest_alg='sha1',salt=False)('test')[0] == a
    True
    >>> CRYPT(digest_alg='sha1',salt=False)('test')[0] == a[6:]
    True
    >>> CRYPT(digest_alg='md5',salt=False)('test')[0] == a
    True
    >>> CRYPT(digest_alg='md5',salt=False)('test')[0] == a[6:]
    True
    """

    def __init__(self,
                 key=None,
                 digest_alg='pbkdf2(1000,20,sha512)',
                 min_length=0,
                 error_message='too short', salt=True):
        """
        important, digest_alg='md5' is not the default hashing algorithm for
        web2py. This is only an example of usage of this function.

        The actual hash algorithm is determined from the key which is
        generated by web2py in tools.py. This defaults to hmac+sha512.
        """
        self.key = key
        self.digest_alg = digest_alg
        self.min_length = min_length
        self.error_message = error_message
        self.salt = salt

    def __call__(self, value):
        if len(value) < self.min_length:
            return ('', translate(self.error_message))
        return (LazyCrypt(self, value), None)

#  entropy calculator for IS_STRONG
#
lowerset = frozenset(unicode('abcdefghijklmnopqrstuvwxyz'))
upperset = frozenset(unicode('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
numberset = frozenset(unicode('0123456789'))
sym1set = frozenset(unicode('!@#$%^&*()'))
sym2set = frozenset(unicode('~`-_=+[]{}\\|;:\'",.<>?/'))
otherset = frozenset(
    unicode('0123456789abcdefghijklmnopqrstuvwxyz'))  # anything else


def calc_entropy(string):
    " calculate a simple entropy for a given string "
    import math
    alphabet = 0    # alphabet size
    other = set()
    seen = set()
    lastset = None
    if isinstance(string, str):
        string = unicode(string, encoding='utf8')
    for c in string:
        # classify this character
        inset = otherset
        for cset in (lowerset, upperset, numberset, sym1set, sym2set):
            if c in cset:
                inset = cset
                break
        # calculate effect of character on alphabet size
        if inset not in seen:
            seen.add(inset)
            alphabet += len(inset)  # credit for a new character set
        elif c not in other:
            alphabet += 1   # credit for unique characters
            other.add(c)
        if inset is not lastset:
            alphabet += 1   # credit for set transitions
            lastset = cset
    entropy = len(
        string) * math.log(alphabet) / 0.6931471805599453  # math.log(2)
    return round(entropy, 2)


class IS_STRONG(object):
    """
    example::

        INPUT(_type='password', _name='passwd',
            requires=IS_STRONG(min=10, special=2, upper=2))

    enforces complexity requirements on a field

    >>> IS_STRONG(es=True)('Abcd1234')
    ('Abcd1234',
     'Must include at least 1 of the following: ~!@#$%^&*()_+-=?<>,.:;{}[]|')
    >>> IS_STRONG(es=True)('Abcd1234!')
    ('Abcd1234!', None)
    >>> IS_STRONG(es=True, entropy=1)('a')
    ('a', None)
    >>> IS_STRONG(es=True, entropy=1, min=2)('a')
    ('a', 'Minimum length is 2')
    >>> IS_STRONG(es=True, entropy=100)('abc123')
    ('abc123', 'Entropy (32.35) less than required (100)')
    >>> IS_STRONG(es=True, entropy=100)('and')
    ('and', 'Entropy (14.57) less than required (100)')
    >>> IS_STRONG(es=True, entropy=100)('aaa')
    ('aaa', 'Entropy (14.42) less than required (100)')
    >>> IS_STRONG(es=True, entropy=100)('a1d')
    ('a1d', 'Entropy (15.97) less than required (100)')
    >>> IS_STRONG(es=True, entropy=100)('añd')
    ('a\\xc3\\xb1d', 'Entropy (18.13) less than required (100)')

    """

    def __init__(self, min=None, max=None, upper=None, lower=None, number=None,
                 entropy=None,
                 special=None, specials=r'~!@#$%^&*()_+-=?<>,.:;{}[]|',
                 invalid=' "', error_message=None, es=False):
        self.entropy = entropy
        if entropy is None:
            # enforce default requirements
            self.min = 8 if min is None else min
            self.max = max  # was 20, but that doesn't make sense
            self.upper = 1 if upper is None else upper
            self.lower = 1 if lower is None else lower
            self.number = 1 if number is None else number
            self.special = 1 if special is None else special
        else:
            # by default, an entropy spec is exclusive
            self.min = min
            self.max = max
            self.upper = upper
            self.lower = lower
            self.number = number
            self.special = special
        self.specials = specials
        self.invalid = invalid
        self.error_message = error_message
        self.estring = es   # return error message as string (for doctest)

    def __call__(self, value):
        failures = []
        if value and len(value) == value.count('*') > 4:
            return (value, None)
        if self.entropy is not None:
            entropy = calc_entropy(value)
            if entropy < self.entropy:
                failures.append(translate("Entropy (%(have)s) less than required (%(need)s)")
                                % dict(have=entropy, need=self.entropy))
        if type(self.min) == int and self.min > 0:
            if not len(value) >= self.min:
                failures.append(translate("Minimum length is %s") % self.min)
        if type(self.max) == int and self.max > 0:
            if not len(value) <= self.max:
                failures.append(translate("Maximum length is %s") % self.max)
        if type(self.special) == int:
            all_special = [ch in value for ch in self.specials]
            if self.special > 0:
                if not all_special.count(True) >= self.special:
                    failures.append(translate("Must include at least %s of the following: %s")
                                    % (self.special, self.specials))
        if self.invalid:
            all_invalid = [ch in value for ch in self.invalid]
            if all_invalid.count(True) > 0:
                failures.append(translate("May not contain any of the following: %s")
                                % self.invalid)
        if type(self.upper) == int:
            all_upper = re.findall("[A-Z]", value)
            if self.upper > 0:
                if not len(all_upper) >= self.upper:
                    failures.append(translate("Must include at least %s upper case")
                                    % str(self.upper))
            else:
                if len(all_upper) > 0:
                    failures.append(
                        translate("May not include any upper case letters"))
        if type(self.lower) == int:
            all_lower = re.findall("[a-z]", value)
            if self.lower > 0:
                if not len(all_lower) >= self.lower:
                    failures.append(translate("Must include at least %s lower case")
                                    % str(self.lower))
            else:
                if len(all_lower) > 0:
                    failures.append(
                        translate("May not include any lower case letters"))
        if type(self.number) == int:
            all_number = re.findall("[0-9]", value)
            if self.number > 0:
                numbers = "number"
                if self.number > 1:
                    numbers = "numbers"
                if not len(all_number) >= self.number:
                    failures.append(translate("Must include at least %s %s")
                                    % (str(self.number), numbers))
            else:
                if len(all_number) > 0:
                    failures.append(translate("May not include any numbers"))
        if len(failures) == 0:
            return (value, None)
        if not self.error_message:
            if self.estring:
                return (value, '|'.join(failures))
            from html import XML
            return (value, XML('<br />'.join(failures)))
        else:
            return (value, translate(self.error_message))


class IS_IN_SUBSET(IS_IN_SET):

    REGEX_W = re.compile('\w+')

    def __init__(self, *a, **b):
        IS_IN_SET.__init__(self, *a, **b)

    def __call__(self, value):
        values = self.REGEX_W.findall(str(value))
        failures = [x for x in values if IS_IN_SET.__call__(self, x)[1]]
        if failures:
            return (value, translate(self.error_message))
        return (value, None)


class IS_IMAGE(Validator):
    """
    Checks if file uploaded through file input was saved in one of selected
    image formats and has dimensions (width and height) within given boundaries.

    Does *not* check for maximum file size (use IS_LENGTH for that). Returns
    validation failure if no data was uploaded.

    Supported file formats: BMP, GIF, JPEG, PNG.

    Code parts taken from
    http://mail.python.org/pipermail/python-list/2007-June/617126.html

    Arguments:

    extensions: iterable containing allowed *lowercase* image file extensions
    ('jpg' extension of uploaded file counts as 'jpeg')
    maxsize: iterable containing maximum width and height of the image
    minsize: iterable containing minimum width and height of the image

    Use (-1, -1) as minsize to pass image size check.

    Examples::

        #Check if uploaded file is in any of supported image formats:
        INPUT(_type='file', _name='name', requires=IS_IMAGE())

        #Check if uploaded file is either JPEG or PNG:
        INPUT(_type='file', _name='name',
            requires=IS_IMAGE(extensions=('jpeg', 'png')))

        #Check if uploaded file is PNG with maximum size of 200x200 pixels:
        INPUT(_type='file', _name='name',
            requires=IS_IMAGE(extensions=('png'), maxsize=(200, 200)))
    """

    def __init__(self,
                 extensions=('bmp', 'gif', 'jpeg', 'png'),
                 maxsize=(10000, 10000),
                 minsize=(0, 0),
                 error_message='invalid image'):

        self.extensions = extensions
        self.maxsize = maxsize
        self.minsize = minsize
        self.error_message = error_message

    def __call__(self, value):
        try:
            extension = value.filename.rfind('.')
            assert extension >= 0
            extension = value.filename[extension + 1:].lower()
            if extension == 'jpg':
                extension = 'jpeg'
            assert extension in self.extensions
            if extension == 'bmp':
                width, height = self.__bmp(value.file)
            elif extension == 'gif':
                width, height = self.__gif(value.file)
            elif extension == 'jpeg':
                width, height = self.__jpeg(value.file)
            elif extension == 'png':
                width, height = self.__png(value.file)
            else:
                width = -1
                height = -1
            assert self.minsize[0] <= width <= self.maxsize[0] \
                and self.minsize[1] <= height <= self.maxsize[1]
            value.file.seek(0)
            return (value, None)
        except:
            return (value, translate(self.error_message))

    def __bmp(self, stream):
        if stream.read(2) == 'BM':
            stream.read(16)
            return struct.unpack("<LL", stream.read(8))
        return (-1, -1)

    def __gif(self, stream):
        if stream.read(6) in ('GIF87a', 'GIF89a'):
            stream = stream.read(5)
            if len(stream) == 5:
                return tuple(struct.unpack("<HHB", stream)[:-1])
        return (-1, -1)

    def __jpeg(self, stream):
        if stream.read(2) == '\xFF\xD8':
            while True:
                (marker, code, length) = struct.unpack("!BBH", stream.read(4))
                if marker != 0xFF:
                    break
                elif code >= 0xC0 and code <= 0xC3:
                    return tuple(reversed(
                        struct.unpack("!xHH", stream.read(5))))
                else:
                    stream.read(length - 2)
        return (-1, -1)

    def __png(self, stream):
        if stream.read(8) == '\211PNG\r\n\032\n':
            stream.read(4)
            if stream.read(4) == "IHDR":
                return struct.unpack("!LL", stream.read(8))
        return (-1, -1)


class IS_UPLOAD_FILENAME(Validator):
    """
    Checks if name and extension of file uploaded through file input matches
    given criteria.

    Does *not* ensure the file type in any way. Returns validation failure
    if no data was uploaded.

    Arguments::

    filename: filename (before dot) regex
    extension: extension (after dot) regex
    lastdot: which dot should be used as a filename / extension separator:
             True means last dot, eg. file.png -> file / png
             False means first dot, eg. file.tar.gz -> file / tar.gz
    case: 0 - keep the case, 1 - transform the string into lowercase (default),
          2 - transform the string into uppercase

    If there is no dot present, extension checks will be done against empty
    string and filename checks against whole value.

    Examples::

        #Check if file has a pdf extension (case insensitive):
        INPUT(_type='file', _name='name',
            requires=IS_UPLOAD_FILENAME(extension='pdf'))

        #Check if file has a tar.gz extension and name starting with backup:
        INPUT(_type='file', _name='name',
            requires=IS_UPLOAD_FILENAME(filename='backup.*',
                extension='tar.gz', lastdot=False))

        #Check if file has no extension and name matching README
        #(case sensitive):
        INPUT(_type='file', _name='name',
            requires=IS_UPLOAD_FILENAME(filename='^README$',
                extension='^$', case=0))
    """

    def __init__(self, filename=None, extension=None, lastdot=True, case=1,
                 error_message='enter valid filename'):
        if isinstance(filename, str):
            filename = re.compile(filename)
        if isinstance(extension, str):
            extension = re.compile(extension)
        self.filename = filename
        self.extension = extension
        self.lastdot = lastdot
        self.case = case
        self.error_message = error_message

    def __call__(self, value):
        try:
            string = value.filename
        except:
            return (value, translate(self.error_message))
        if self.case == 1:
            string = string.lower()
        elif self.case == 2:
            string = string.upper()
        if self.lastdot:
            dot = string.rfind('.')
        else:
            dot = string.find('.')
        if dot == -1:
            dot = len(string)
        if self.filename and not self.filename.match(string[:dot]):
            return (value, translate(self.error_message))
        elif self.extension and not self.extension.match(string[dot + 1:]):
            return (value, translate(self.error_message))
        else:
            return (value, None)


class IS_IPV4(Validator):
    """
    Checks if field's value is an IP version 4 address in decimal form. Can
    be set to force addresses from certain range.

    IPv4 regex taken from: http://regexlib.com/REDetails.aspx?regexp_id=1411

    Arguments:

    minip: lowest allowed address; accepts:
           str, eg. 192.168.0.1
           list or tuple of octets, eg. [192, 168, 0, 1]
    maxip: highest allowed address; same as above
    invert: True to allow addresses only from outside of given range; note
            that range boundaries are not matched this way
    is_localhost: localhost address treatment:
                  None (default): indifferent
                  True (enforce): query address must match localhost address
                                  (127.0.0.1)
                  False (forbid): query address must not match localhost
                                  address
    is_private: same as above, except that query address is checked against
                two address ranges: 172.16.0.0 - 172.31.255.255 and
                192.168.0.0 - 192.168.255.255
    is_automatic: same as above, except that query address is checked against
                  one address range: 169.254.0.0 - 169.254.255.255

    Minip and maxip may also be lists or tuples of addresses in all above
    forms (str, int, list / tuple), allowing setup of multiple address ranges:

        minip = (minip1, minip2, ... minipN)
                   |       |           |
                   |       |           |
        maxip = (maxip1, maxip2, ... maxipN)

    Longer iterable will be truncated to match length of shorter one.

    Examples::

        #Check for valid IPv4 address:
        INPUT(_type='text', _name='name', requires=IS_IPV4())

        #Check for valid IPv4 address belonging to specific range:
        INPUT(_type='text', _name='name',
            requires=IS_IPV4(minip='100.200.0.0', maxip='100.200.255.255'))

        #Check for valid IPv4 address belonging to either 100.110.0.0 -
        #100.110.255.255 or 200.50.0.0 - 200.50.0.255 address range:
        INPUT(_type='text', _name='name',
            requires=IS_IPV4(minip=('100.110.0.0', '200.50.0.0'),
                             maxip=('100.110.255.255', '200.50.0.255')))

        #Check for valid IPv4 address belonging to private address space:
        INPUT(_type='text', _name='name', requires=IS_IPV4(is_private=True))

        #Check for valid IPv4 address that is not a localhost address:
        INPUT(_type='text', _name='name', requires=IS_IPV4(is_localhost=False))

    >>> IS_IPV4()('1.2.3.4')
    ('1.2.3.4', None)
    >>> IS_IPV4()('255.255.255.255')
    ('255.255.255.255', None)
    >>> IS_IPV4()('1.2.3.4 ')
    ('1.2.3.4 ', 'enter valid IPv4 address')
    >>> IS_IPV4()('1.2.3.4.5')
    ('1.2.3.4.5', 'enter valid IPv4 address')
    >>> IS_IPV4()('123.123')
    ('123.123', 'enter valid IPv4 address')
    >>> IS_IPV4()('1111.2.3.4')
    ('1111.2.3.4', 'enter valid IPv4 address')
    >>> IS_IPV4()('0111.2.3.4')
    ('0111.2.3.4', 'enter valid IPv4 address')
    >>> IS_IPV4()('256.2.3.4')
    ('256.2.3.4', 'enter valid IPv4 address')
    >>> IS_IPV4()('300.2.3.4')
    ('300.2.3.4', 'enter valid IPv4 address')
    >>> IS_IPV4(minip='1.2.3.4', maxip='1.2.3.4')('1.2.3.4')
    ('1.2.3.4', None)
    >>> IS_IPV4(minip='1.2.3.5', maxip='1.2.3.9', error_message='bad ip')('1.2.3.4')
    ('1.2.3.4', 'bad ip')
    >>> IS_IPV4(maxip='1.2.3.4', invert=True)('127.0.0.1')
    ('127.0.0.1', None)
    >>> IS_IPV4(maxip='1.2.3.4', invert=True)('1.2.3.4')
    ('1.2.3.4', 'enter valid IPv4 address')
    >>> IS_IPV4(is_localhost=True)('127.0.0.1')
    ('127.0.0.1', None)
    >>> IS_IPV4(is_localhost=True)('1.2.3.4')
    ('1.2.3.4', 'enter valid IPv4 address')
    >>> IS_IPV4(is_localhost=False)('127.0.0.1')
    ('127.0.0.1', 'enter valid IPv4 address')
    >>> IS_IPV4(maxip='100.0.0.0', is_localhost=True)('127.0.0.1')
    ('127.0.0.1', 'enter valid IPv4 address')
    """

    regex = re.compile(
        '^(([1-9]?\d|1\d\d|2[0-4]\d|25[0-5])\.){3}([1-9]?\d|1\d\d|2[0-4]\d|25[0-5])$')
    numbers = (16777216, 65536, 256, 1)
    localhost = 2130706433
    private = ((2886729728L, 2886795263L), (3232235520L, 3232301055L))
    automatic = (2851995648L, 2852061183L)

    def __init__(
        self,
        minip='0.0.0.0',
        maxip='255.255.255.255',
        invert=False,
        is_localhost=None,
        is_private=None,
        is_automatic=None,
            error_message='enter valid IPv4 address'):
        for n, value in enumerate((minip, maxip)):
            temp = []
            if isinstance(value, str):
                temp.append(value.split('.'))
            elif isinstance(value, (list, tuple)):
                if len(value) == len(filter(lambda item: isinstance(item, int), value)) == 4:
                    temp.append(value)
                else:
                    for item in value:
                        if isinstance(item, str):
                            temp.append(item.split('.'))
                        elif isinstance(item, (list, tuple)):
                            temp.append(item)
            numbers = []
            for item in temp:
                number = 0
                for i, j in zip(self.numbers, item):
                    number += i * int(j)
                numbers.append(number)
            if n == 0:
                self.minip = numbers
            else:
                self.maxip = numbers
        self.invert = invert
        self.is_localhost = is_localhost
        self.is_private = is_private
        self.is_automatic = is_automatic
        self.error_message = error_message

    def __call__(self, value):
        if self.regex.match(value):
            number = 0
            for i, j in zip(self.numbers, value.split('.')):
                number += i * int(j)
            ok = False
            for bottom, top in zip(self.minip, self.maxip):
                if self.invert != (bottom <= number <= top):
                    ok = True
            if not (self.is_localhost is None or self.is_localhost ==
                    (number == self.localhost)):
                    ok = False
            if not (self.is_private is None or self.is_private ==
                    (sum([number[0] <= number <= number[1] for number in self.private]) > 0)):
                    ok = False
            if not (self.is_automatic is None or self.is_automatic ==
                    (self.automatic[0] <= number <= self.automatic[1])):
                    ok = False
            if ok:
                return (value, None)
        return (value, translate(self.error_message))

class IS_IPV6(Validator):
    """
    Checks if field's value is an IP version 6 address. First attempts to
    use the ipaddress library and falls back to contrib/ipaddr.py from Google
    (https://code.google.com/p/ipaddr-py/)

    Arguments:
    is_private: None (default): indifferent
                True (enforce): address must be in fc00::/7 range
                False (forbid): address must NOT be in fc00::/7 range
    is_link_local: Same as above but uses fe80::/10 range
    is_reserved: Same as above but uses IETF reserved range
    is_mulicast: Same as above but uses ff00::/8 range
    is_routeable: Similar to above but enforces not private, link_local,
                  reserved or multicast
    is_6to4: Same as above but uses 2002::/16 range
    is_teredo: Same as above but uses 2001::/32 range
    subnets: value must be a member of at least one from list of subnets

    Examples:

        #Check for valid IPv6 address:
        INPUT(_type='text', _name='name', requires=IS_IPV6())

        #Check for valid IPv6 address is a link_local address:
        INPUT(_type='text', _name='name', requires=IS_IPV6(is_link_local=True))

        #Check for valid IPv6 address that is Internet routeable:
        INPUT(_type='text', _name='name', requires=IS_IPV6(is_routeable=True))

        #Check for valid IPv6 address in specified subnet:
        INPUT(_type='text', _name='name', requires=IS_IPV6(subnets=['2001::/32'])

    >>> IS_IPV6()('fe80::126c:8ffa:fe22:b3af')
    ('fe80::126c:8ffa:fe22:b3af', None)
    >>> IS_IPV6()('192.168.1.1')
    ('192.168.1.1', 'enter valid IPv6 address')
    >>> IS_IPV6(error_message='bad ip')('192.168.1.1')
    ('192.168.1.1', 'bad ip')
    >>> IS_IPV6(is_link_local=True)('fe80::126c:8ffa:fe22:b3af')
    ('fe80::126c:8ffa:fe22:b3af', None)
    >>> IS_IPV6(is_link_local=False)('fe80::126c:8ffa:fe22:b3af')
    ('fe80::126c:8ffa:fe22:b3af', 'enter valid IPv6 address')
    >>> IS_IPV6(is_link_local=True)('2001::126c:8ffa:fe22:b3af')
    ('2001::126c:8ffa:fe22:b3af', 'enter valid IPv6 address')
    >>> IS_IPV6(is_multicast=True)('2001::126c:8ffa:fe22:b3af')
    ('2001::126c:8ffa:fe22:b3af', 'enter valid IPv6 address')
    >>> IS_IPV6(is_multicast=True)('ff00::126c:8ffa:fe22:b3af')
    ('ff00::126c:8ffa:fe22:b3af', None)
    >>> IS_IPV6(is_routeable=True)('2001::126c:8ffa:fe22:b3af')
    ('2001::126c:8ffa:fe22:b3af', None)
    >>> IS_IPV6(is_routeable=True)('ff00::126c:8ffa:fe22:b3af')
    ('ff00::126c:8ffa:fe22:b3af', 'enter valid IPv6 address')
    >>> IS_IPV6(subnets='2001::/32')('2001::8ffa:fe22:b3af')
    ('2001::8ffa:fe22:b3af', None)
    >>> IS_IPV6(subnets='fb00::/8')('2001::8ffa:fe22:b3af')
    ('2001::8ffa:fe22:b3af', 'enter valid IPv6 address')
    >>> IS_IPV6(subnets=['fc00::/8','2001::/32'])('2001::8ffa:fe22:b3af')
    ('2001::8ffa:fe22:b3af', None)
    >>> IS_IPV6(subnets='invalidsubnet')('2001::8ffa:fe22:b3af')
    ('2001::8ffa:fe22:b3af', 'invalid subnet provided')
    
    """

    def __init__(
            self,
            is_private=None,
            is_link_local=None,
            is_reserved=None,
            is_multicast=None,
            is_routeable=None,
            is_6to4=None,
            is_teredo=None,
            subnets=None,
            error_message='enter valid IPv6 address'):
        self.is_private = is_private
        self.is_link_local = is_link_local
        self.is_reserved = is_reserved
        self.is_multicast = is_multicast
        self.is_routeable = is_routeable
        self.is_6to4 = is_6to4
        self.is_teredo = is_teredo
        self.subnets = subnets
        self.error_message = error_message

    def __call__(self, value):
        try:
            import ipaddress
        except ImportError:
            from contrib import ipaddr as ipaddress

        try:
            ip = ipaddress.IPv6Address(value)
            ok = True
        except ipaddress.AddressValueError:
            return (value, translate(self.error_message))

        if self.subnets:
            # iterate through self.subnets to see if value is a member
            ok = False
            if isinstance(self.subnets, str):
                self.subnets = [self.subnets]
            for network in self.subnets:
                try:
                    ipnet = ipaddress.IPv6Network(network)
                except (ipaddress.NetmaskValueError, ipaddress.AddressValueError):
                    return (value, translate('invalid subnet provided'))
                if ip in ipnet:
                    ok = True

        if self.is_routeable:
            self.is_private = False
            self.is_link_local = False
            self.is_reserved = False
            self.is_multicast = False

        if not (self.is_private is None or self.is_private ==
                ip.is_private):
            ok = False
        if not (self.is_link_local is None or self.is_link_local ==
                ip.is_link_local):
            ok = False
        if not (self.is_reserved is None or self.is_reserved ==
                ip.is_reserved):
            ok = False
        if not (self.is_multicast is None or self.is_multicast ==
                ip.is_multicast):
            ok = False
        if not (self.is_6to4 is None or self.is_6to4 ==
                ip.is_6to4):
            ok = False
        if not (self.is_teredo is None or self.is_teredo ==
                ip.is_teredo):
            ok = False

        if ok:
            return (value, None)

        return (value, translate(self.error_message))


class IS_IPADDRESS(Validator):
    """
    Checks if field's value is an IP Address (v4 or v6). Can be set to force
    addresses from within a specific range. Checks are done with the correct
    IS_IPV4 and IS_IPV6 validators.

    Uses ipaddress library if found, falls back to PEP-3144 ipaddr.py from
    Google (in contrib).

    Universal arguments:

    minip: lowest allowed address; accepts:
           str, eg. 192.168.0.1
           list or tuple of octets, eg. [192, 168, 0, 1]
    maxip: highest allowed address; same as above
    invert: True to allow addresses only from outside of given range; note
            that range boundaries are not matched this way

    IPv4 specific arguments:

    is_localhost: localhost address treatment:
                  None (default): indifferent
                  True (enforce): query address must match localhost address
                                  (127.0.0.1)
                  False (forbid): query address must not match localhost
                                  address
    is_private: same as above, except that query address is checked against
                two address ranges: 172.16.0.0 - 172.31.255.255 and
                192.168.0.0 - 192.168.255.255
    is_automatic: same as above, except that query address is checked against
                  one address range: 169.254.0.0 - 169.254.255.255
    is_ipv4: None (default): indifferent
             True (enforce): must be an IPv4 address
             False (forbid): must NOT be an IPv4 address

    IPv6 specific arguments:

    is_link_local: Same as above but uses fe80::/10 range
    is_reserved: Same as above but uses IETF reserved range
    is_mulicast: Same as above but uses ff00::/8 range
    is_routeable: Similar to above but enforces not private, link_local,
                  reserved or multicast
    is_6to4: Same as above but uses 2002::/16 range
    is_teredo: Same as above but uses 2001::/32 range
    subnets: value must be a member of at least one from list of subnets
    is_ipv6: None (default): indifferent
             True (enforce): must be an IPv6 address
             False (forbid): must NOT be an IPv6 address

    Minip and maxip may also be lists or tuples of addresses in all above
    forms (str, int, list / tuple), allowing setup of multiple address ranges:

        minip = (minip1, minip2, ... minipN)
                   |       |           |
                   |       |           |
        maxip = (maxip1, maxip2, ... maxipN)

    Longer iterable will be truncated to match length of shorter one.

    >>> IS_IPADDRESS()('192.168.1.5')
    ('192.168.1.5', None)
    >>> IS_IPADDRESS(is_ipv6=False)('192.168.1.5')
    ('192.168.1.5', None)
    >>> IS_IPADDRESS()('255.255.255.255')
    ('255.255.255.255', None)
    >>> IS_IPADDRESS()('192.168.1.5 ')
    ('192.168.1.5 ', 'enter valid IP address')
    >>> IS_IPADDRESS()('192.168.1.1.5')
    ('192.168.1.1.5', 'enter valid IP address')
    >>> IS_IPADDRESS()('123.123')
    ('123.123', 'enter valid IP address')
    >>> IS_IPADDRESS()('1111.2.3.4')
    ('1111.2.3.4', 'enter valid IP address')
    >>> IS_IPADDRESS()('0111.2.3.4')
    ('0111.2.3.4', 'enter valid IP address')
    >>> IS_IPADDRESS()('256.2.3.4')
    ('256.2.3.4', 'enter valid IP address')
    >>> IS_IPADDRESS()('300.2.3.4')
    ('300.2.3.4', 'enter valid IP address')
    >>> IS_IPADDRESS(minip='192.168.1.0', maxip='192.168.1.255')('192.168.1.100')
    ('192.168.1.100', None)
    >>> IS_IPADDRESS(minip='1.2.3.5', maxip='1.2.3.9', error_message='bad ip')('1.2.3.4')
    ('1.2.3.4', 'bad ip')
    >>> IS_IPADDRESS(maxip='1.2.3.4', invert=True)('127.0.0.1')
    ('127.0.0.1', None)
    >>> IS_IPADDRESS(maxip='192.168.1.4', invert=True)('192.168.1.4')
    ('192.168.1.4', 'enter valid IP address')
    >>> IS_IPADDRESS(is_localhost=True)('127.0.0.1')
    ('127.0.0.1', None)
    >>> IS_IPADDRESS(is_localhost=True)('192.168.1.10')
    ('192.168.1.10', 'enter valid IP address')
    >>> IS_IPADDRESS(is_localhost=False)('127.0.0.1')
    ('127.0.0.1', 'enter valid IP address')
    >>> IS_IPADDRESS(maxip='100.0.0.0', is_localhost=True)('127.0.0.1')
    ('127.0.0.1', 'enter valid IP address')

    >>> IS_IPADDRESS()('fe80::126c:8ffa:fe22:b3af')
    ('fe80::126c:8ffa:fe22:b3af', None)
    >>> IS_IPADDRESS(is_ipv4=False)('fe80::126c:8ffa:fe22:b3af')
    ('fe80::126c:8ffa:fe22:b3af', None)
    >>> IS_IPADDRESS()('fe80::126c:8ffa:fe22:b3af  ')
    ('fe80::126c:8ffa:fe22:b3af  ', 'enter valid IP address')
    >>> IS_IPADDRESS(is_ipv4=True)('fe80::126c:8ffa:fe22:b3af')
    ('fe80::126c:8ffa:fe22:b3af', 'enter valid IP address')
    >>> IS_IPADDRESS(is_ipv6=True)('192.168.1.1')
    ('192.168.1.1', 'enter valid IP address')
    >>> IS_IPADDRESS(is_ipv6=True, error_message='bad ip')('192.168.1.1')
    ('192.168.1.1', 'bad ip')
    >>> IS_IPADDRESS(is_link_local=True)('fe80::126c:8ffa:fe22:b3af')
    ('fe80::126c:8ffa:fe22:b3af', None)
    >>> IS_IPADDRESS(is_link_local=False)('fe80::126c:8ffa:fe22:b3af')
    ('fe80::126c:8ffa:fe22:b3af', 'enter valid IP address')
    >>> IS_IPADDRESS(is_link_local=True)('2001::126c:8ffa:fe22:b3af')
    ('2001::126c:8ffa:fe22:b3af', 'enter valid IP address')
    >>> IS_IPADDRESS(is_multicast=True)('2001::126c:8ffa:fe22:b3af')
    ('2001::126c:8ffa:fe22:b3af', 'enter valid IP address')
    >>> IS_IPADDRESS(is_multicast=True)('ff00::126c:8ffa:fe22:b3af')
    ('ff00::126c:8ffa:fe22:b3af', None)
    >>> IS_IPADDRESS(is_routeable=True)('2001::126c:8ffa:fe22:b3af')
    ('2001::126c:8ffa:fe22:b3af', None)
    >>> IS_IPADDRESS(is_routeable=True)('ff00::126c:8ffa:fe22:b3af')
    ('ff00::126c:8ffa:fe22:b3af', 'enter valid IP address')
    >>> IS_IPADDRESS(subnets='2001::/32')('2001::8ffa:fe22:b3af')
    ('2001::8ffa:fe22:b3af', None)
    >>> IS_IPADDRESS(subnets='fb00::/8')('2001::8ffa:fe22:b3af')
    ('2001::8ffa:fe22:b3af', 'enter valid IP address')
    >>> IS_IPADDRESS(subnets=['fc00::/8','2001::/32'])('2001::8ffa:fe22:b3af')
    ('2001::8ffa:fe22:b3af', None)
    >>> IS_IPADDRESS(subnets='invalidsubnet')('2001::8ffa:fe22:b3af')
    ('2001::8ffa:fe22:b3af', 'invalid subnet provided')
    """
    def __init__(
            self,
            minip='0.0.0.0',
            maxip='255.255.255.255',
            invert=False,
            is_localhost=None,
            is_private=None,
            is_automatic=None,
            is_ipv4=None,
            is_link_local=None,
            is_reserved=None,
            is_multicast=None,
            is_routeable=None,
            is_6to4=None,
            is_teredo=None,
            subnets=None,
            is_ipv6=None,
            error_message='enter valid IP address'):
        self.minip = minip,
        self.maxip = maxip,
        self.invert = invert
        self.is_localhost = is_localhost
        self.is_private = is_private
        self.is_automatic = is_automatic
        self.is_ipv4 = is_ipv4
        self.is_private = is_private
        self.is_link_local = is_link_local
        self.is_reserved = is_reserved
        self.is_multicast = is_multicast
        self.is_routeable = is_routeable
        self.is_6to4 = is_6to4
        self.is_teredo = is_teredo
        self.subnets = subnets
        self.is_ipv6 = is_ipv6
        self.error_message = error_message

    def __call__(self, value):
        try:
            import ipaddress
        except ImportError:
            from contrib import ipaddr as ipaddress

        try:
            ip = ipaddress.ip_address(value)
        except ValueError, e:
            return (value, translate(self.error_message))

        if self.is_ipv4 and isinstance(ip, ipaddress.IPv6Address):
            retval = (value, translate(self.error_message))
        elif self.is_ipv6 and isinstance(ip, ipaddress.IPv4Address):
            retval = (value, translate(self.error_message))
        elif self.is_ipv4 or isinstance(ip, ipaddress.IPv4Address):
            retval = IS_IPV4(
                minip=self.minip,
                maxip=self.maxip,
                invert=self.invert,
                is_localhost=self.is_localhost,
                is_private=self.is_private,
                is_automatic=self.is_automatic,
                error_message=self.error_message
                )(value)
        elif self.is_ipv6 or isinstance(ip, ipaddress.IPv6Address):
            retval = IS_IPV6(
                is_private=self.is_private,
                is_link_local=self.is_link_local,
                is_reserved=self.is_reserved,
                is_multicast=self.is_multicast,
                is_routeable=self.is_routeable,
                is_6to4=self.is_6to4,
                is_teredo=self.is_teredo,
                subnets=self.subnets,
                error_message=self.error_message
                )(value)
        else:
            retval = (value, translate(self.error_message))

        return retval


if __name__ == '__main__':
    import doctest
    doctest.testmod(
        optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)

########NEW FILE########
__FILENAME__ = wrapper
import traceback
from dal import *
from template import *
from html import *
from validators import *
from sqlhtml import *

class wrapper(object):
    debug = False
    response = None
    def __init__(self,view=None,dbs=[], debug = None, response = None):
        self.view = view
        self.dbs = dbs
        if not debug is None: self.debug = debug
        if not response is None: self.response = response
    def __call__(self,f):
        def g(*a,**b):
            g.__name__ = f.__name__
            try:
                for db in self.dbs: db._adapter.reconnect()
                r = f(*a,**b)
                if self.view:
                    r = render(filename=self.view,context=r)
                if self.response:
                    # used by pyramid
                    r = self.response(r)
            except HTTP, e:                
                raise NotImplementedError
            except Exception, e:
                print e
                for db in self.dbs: db._adapter.close('rollback')
                if self.debug:
                    return str(traceback.format_exc())
                raise e
            for db in self.dbs: db._adapter.close('rollback')
            if a and a[0].__class__.__name__=='MainHandler':
                # for tornado
                a[0].write(r)
            else:
                # for bottle, flask, pyramid
                return r
        return g
    
    @staticmethod
    def extract_vars(form):
        d = {}
        for key, value in form.items():
            if isinstance(value,list) and len(value)==1:
                value = value[0]
            if not key in d:
                d[key] = value
            elif isinstance(d[key],list):
                d[key].append(value)
            else:
                d[key]=[d[key],value]
        return d


########NEW FILE########
__FILENAME__ = pyramid_example
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.static import static_view
from pyramid.httpexceptions import HTTPFound
from gluino import wrapper, DAL, Field, SQLFORM, cache, IS_NOT_EMPTY
import time

# configure the gluino wrapper
wrapper.debug = True
wrapper.response = Response
wrapper.redirect = lambda status,url: HTTPFound(location=url)

# create database and table
db=DAL('sqlite://storage.sqlite')
db.define_table('person',Field('name',requires=IS_NOT_EMPTY()))

# define action
@wrapper(view='templates/index.html',dbs=[db])
def index(context, request):
    vars = wrapper.extract_vars(request.POST)
    form = SQLFORM(db.person)
    if form.accepts(vars):
        message = 'hello %s' % form.vars.name
    else:
        message = 'hello anonymous'
    people = db(db.person).select()
    now  = cache.ram('time',lambda:time.ctime(),10)
    return locals()

# start web server
if __name__=='__main__':
    config = Configurator()
    config.add_route('index', '/index')
    config.add_view(index, route_name='index')
    config.add_static_view(name='static', path='static')
    app = config.make_wsgi_app()
    server = make_server('0.0.0.0', 8080, app)
    server.serve_forever()


########NEW FILE########
__FILENAME__ = tornado_example
import tornado.ioloop
import tornado.web
from gluino import wrapper, DAL, Field, SQLFORM, cache, IS_NOT_EMPTY
import time

# configure the gluino wrapper                                               
wrapper.debug = True
wrapper.http = lambda code, message: tornado.web.HTTPError(code)
wrapper.redirect = lambda status, url: tornado.web.RequestHandler.redirect(url)

# create database and table
db=DAL('sqlite://storage.sqlite')
db.define_table('person',Field('name',requires=IS_NOT_EMPTY()))

# define action
def index(request):
    vars = wrapper.extract_vars(request.arguments)
    form = SQLFORM(db.person)
    if form.accepts(vars):
        message = 'hello %s' % form.vars.name
    else:
        message = 'hello anonymous'
    people = db(db.person).select()
    now  = cache.ram('time',lambda:time.ctime(),10)
    return locals()

class MainHandler(tornado.web.RequestHandler):
    @wrapper(view='templates/index.html',dbs=[db])
    def get(self): return index(self.request)
    def post(self): return self.get()

# configure routes
application = tornado.web.Application([
        (r"/index", MainHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static"}),
        ])

# start web server
if __name__ == "__main__":
    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = wsgiref_example
from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server
from gluino import wrapper, DAL, Field, SQLFORM, cache, IS_NOT_EMPTY
import time
import cgi
import traceback

# configure the gluino wrapper
wrapper.debug = True

# create database and table
db=DAL('sqlite://storage.sqlite')
db.define_table('person',Field('name',requires=IS_NOT_EMPTY()))

# define action
@wrapper(view='templates/index.html',dbs=[db])
def index(environ, vars):
    vars = wrapper.extract_vars(vars)
    form = SQLFORM(db.person)
    if form.accepts(vars):
        message = 'hello %s' % form.vars.name
    else:
        message = 'hello anonymous'
    people = db(db.person).select()
    now  = cache.ram('time',lambda:time.ctime(),10)
    return locals()

# A minimalist example dispatcher
# This is very naive ... bit gives the idea...
 
MAPS = {'/index':index}

def dispatcher(environ, start_response):    
    post = cgi.FieldStorage(
        fp=environ['wsgi.input'],environ=environ,keep_blank_values=True)
    vars = dict((k,post[k].value) for k in post)

    try:
        uri = environ['PATH_INFO']
        if uri.startswith('/static/'):
            body = open(uri[1:],'rb').read()
        else:
            action = MAPS.get(uri)
            if action:
                body = action(environ, vars)
            else:
                body = 'undefined action: ' + uri
        status = "200 OK"
    except:
        status = "500 INTERNAL ERROR"
        body = traceback.format_exc()
    headers = [('Content-Type', 'text/html'),
               ('Content-Length', str(len(body)))]
    start_response(status,headers)
    return body

# start the web server
if __name__=='__main__':
    httpd = make_server('', 8080, dispatcher)
    print "Serving on port 8080..."
    httpd.serve_forever()

########NEW FILE########
