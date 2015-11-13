__FILENAME__ = exceptions
class PipesBaseException(Exception):
    def __init__(self, code=None, reason=None, resp=None):
        self.code = code
        self.reason = reason
        self.resp = resp
    
    def __str__(self):
        if self.reason:
            return repr(self.reason)
        else:
            return repr(self.resp)

class ObjectNotSavedException(PipesBaseException):
    pass
class ResourceNotAvailableException(PipesBaseException):
    pass

########NEW FILE########
__FILENAME__ = main
from django.utils import simplejson
from django.core.cache import cache
from django.conf import settings

import urllib, urllib2, socket
from time import time

from exceptions import ObjectNotSavedException, ResourceNotAvailableException
from django_pipes import debug_stats

if hasattr(settings, "PIPES_CACHE_EXPIRY"):
    default_cache_expiry = settings.PIPES_CACHE_EXPIRY
else:
    default_cache_expiry = 60

# set default socket timeout; otherwise urllib2 requests could block forever.
if hasattr(settings, "PIPES_SOCKET_TIMEOUT"):
    socket.setdefaulttimeout(settings.PIPES_SOCKET_TIMEOUT)
else:
    socket.setdefaulttimeout(10)

class PipeResultSet(list):
    """all() and filter() on the PipeManager class return an instance of this class."""
    def __init__(self, pipe_cls, items):
        super(PipeResultSet, self).__init__(self)
        if isinstance(items, dict) and hasattr(pipe_cls, '__call__'):
            obj = pipe_cls.__call__()
            obj.items.update(_objectify_json(items))
            self.append(obj)
        elif isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and hasattr(pipe_cls, '__call__'):
                    # let's go ahead and create instances of the user-defined Pipe class
                    obj = pipe_cls.__call__()
                    obj.items.update(_objectify_json(item))
                    self.append(obj)
        else:
            self.append(items)

def _objectify_json(i):
    if isinstance(i, dict):
        transformed_dict = JSONDict()
        for key, val in i.iteritems():
            transformed_dict[key] = _objectify_json(val)
        return transformed_dict
    elif isinstance(i, list):
        for idx in range(len(i)):
            i[idx] = _objectify_json(i[idx])
    return i

def _log(msg):
    if settings.DEBUG:
        print msg

class JSONDict(dict):
    def __getattr__(self, attrname):
        if self.has_key(attrname):
            return self[attrname]
        else:
            raise AttributeError

class PipeManager(object):
    """
    Manager class for pipes. Provides the same semantics as Django's ORM Manager class.
    Currently only all(), get() and filter() are implemented.
    
    get() & filter() accept:
        params - a dict of (key,value) pairs which are encoded into HTTP GET params 
                 and appended to the URI provided on the Pipe class.
        should_cache - should response be cached after fetching?
        cache_expiry - how long (in seconds) should response be cached?
                       Default is pipe.cache_expiry or settings.PIPES_CACHE_EXPIRY,
                       or 60 seconds.
    """
    def _set_pipe(self, pipe):
        self.pipe = pipe

    def filter(self, params, should_cache=None, cache_expiry=None, retries=None):
        if hasattr(self.pipe, 'uri'):
            
            # should cache or not?
            if should_cache is None:
                # no per-request caching specified; lets look for cache option on the Pipe class
                if hasattr(self.pipe, 'should_cache'):
                    should_cache = self.pipe.should_cache
                else:
                    should_cache = True
            
            # how many retries?
            if retries is None:
                # no per-request retries configured; lets look for retries option on the Pipe class
                if hasattr(self.pipe, 'retries'):
                    retries = self.pipe.retries
                else:
                    retries = 0
            
            url_string = self.pipe.uri
            if len(params)>0:
                url_string += "?%s" % urllib.urlencode(params)
            _log("Fetching: %s" % url_string)
            url_string = url_string.replace(" ",'')
            
            start = time()
            # Try the cache first
            resp = cache.get(url_string)
            if resp: 
                # Yay! found in cache!
                _log("Found in cache.")
                stop = time()
                debug_stats.record_query(url_string, found_in_cache=True, time=stop-start)
            else: 
                # Not found in cache
                _log("Not found in cache. Downloading...")
                
                attempts = 0
                while True:
                    try:
                        attempts += 1
                        respObj = urllib2.urlopen(url_string)
                        break
                    except urllib2.HTTPError, e:
                        stop = time()
                        debug_stats.record_query(url_string, failed=True, retries=attempts-1, time=stop-start)
                        raise ResourceNotAvailableException(code=e.code, resp=e.read())
                    except urllib2.URLError, e:
                        if attempts <= retries:
                            continue
                        else: 
                            stop = time()
                            debug_stats.record_query(url_string, failed=True, retries=attempts-1, time=stop-start)
                            raise ResourceNotAvailableException(reason=e.reason)
                        
                resp = respObj.read()
                if should_cache:
                    if cache_expiry is None:
                        if hasattr(self.pipe, 'cache_expiry'):
                            cache_expiry = self.pipe.cache_expiry
                        else:
                            cache_expiry = default_cache_expiry
                    cache.set(url_string, resp, cache_expiry)
                stop = time()
                debug_stats.record_query(url_string, retries=attempts-1, time=stop-start)

            resp_obj = simplejson.loads(resp)
            return PipeResultSet(self.pipe, resp_obj)
        else:
            return PipeResultSet(self.pipe, [])

    def get(self, params={}, should_cache=None, cache_expiry=None, retries=None):
        rs = self.filter(params, should_cache, cache_expiry, retries)
        if rs:
            return rs[0]
        else:
            return None

    def all(self, should_cache=None, cache_expiry=None, retries=None):
        return self.filter({}, should_cache, cache_expiry, retries)

    def _save(self, obj):
        "Makes a POST request to the given URI with the POST params set to the given object's attributes."
        if hasattr(self.pipe, 'uri'):
            url_string = self.pipe.uri
            post_params = urllib.urlencode(obj.items)
            _log("Posting to: %s" % url_string)
            try:
                resp = urllib2.urlopen(urllib2.Request(url_string, post_params))
            except urllib2.HTTPError, e:
                raise ObjectNotSavedException(code=e.code, resp=e.read())
            except urllib2.URLError, e:
                raise ObjectNotSavedException(reason=e.reason)
            else:
                resp_obj = simplejson.loads(resp.read())
                return resp_obj
        else:
            return None

class PipeBase(type):
    """Metaclass for all pipes"""
    def __new__(cls, name, bases, attrs):
        # If this isn't a subclass of Pipe, don't do anything special.
        try:
            if not filter(lambda b: issubclass(b, Pipe), bases):
                return super(PipeBase, cls).__new__(cls, name, bases, attrs)
        except NameError:
            # 'Pipe' isn't defined yet, meaning we're looking at our own
            # Pipe class, defined below.
            return super(PipeBase, cls).__new__(cls, name, bases, attrs)

        # Create the class.
        new_class = type.__new__(cls, name, bases, attrs)
        
        mgr = PipeManager()
        new_class.add_to_class('objects', mgr)
        mgr._set_pipe(new_class)
        
        return new_class

class Pipe(object):
    """Base class for all pipes. Users should typically subclass this class to create their pipe."""
    
    __metaclass__ = PipeBase
    uri = None
    
    def __init__(self, **kwargs):
        self.items = dict()
        if len(kwargs) > 0:
            self.items.update(kwargs)
    
    def add_to_class(cls, name, value):
        setattr(cls, name, value)
    add_to_class = classmethod(add_to_class)

    def __getattr__(self, attrname):
        if attrname == '__setstate__':
            # when you unpickle a Pipe object, __getattr__ gets called
            # before the constructor is called
            # this will result in a recursive loop since self.items won't be available yet.
            raise AttributeError
        elif self.items.has_key(attrname):
            return self.items[attrname]
        else:
            raise AttributeError
    
    def __setattr__(self, attrname, attrval):
        if attrname == 'items':
            # items is the only attribute which should be set as a regular instance attribute.
            object.__setattr__(self, attrname, attrval)
        else:
            # for all other attributes, just insert them into the items dict.
            self.items[attrname] = attrval

    def save(self):
        """
        Makes a POST request to the given URI with the POST params set to the class's attributes.
        Throws a ObjectNotSavedException if the request fails.
        """
        return self.objects._save(self)

########NEW FILE########
__FILENAME__ = stats_middleware
from django.conf import settings

import django_pipes as pipes

class PipesStatsMiddleware:
    def process_response(self, request, response):
        if settings.DEBUG:
            
            queries = pipes.debug_stats.queries
            
            if len(queries) > 0:
                cached_queries = filter(lambda query: query['found_in_cache'], queries)
                failed_queries = filter(lambda query: query['failed'], queries)
                remote_queries = len(queries) - len(cached_queries) - len(failed_queries)
            
                print "\n================== Pipes Usage Summary ==========================="
                print "Total: %d   Found in cache: %d   Fetched from remote: %d   Failed: %d\n" % (
                        len(queries), len(cached_queries),
                        remote_queries, len(failed_queries)
                    )
                for idx, query in enumerate(queries):
                    if query['failed']:
                        status = "FAILED"
                    elif query['found_in_cache']:
                        status = "FETCHED FROM CACHE"
                    else:
                        status = "FETCHED FROM REMOTE"
                    print "%d) %s (%.3f ms) : %s : %d retries" % (
                            idx+1, 
                            status,
                            query['time'], 
                            query['url'], 
                            query['retries']
                    )
                print "====================================================================\n"
        
        return response

########NEW FILE########
__FILENAME__ = stats
try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

class PipesStats(local):
    'Collect per-request stats for pipes calls.'
    def __init__(self):
        self.queries = []
    
    def record_query(self, url, found_in_cache=False, failed=False, retries=0, time=None):
        self.queries.append({
            'url':url,
            'found_in_cache':found_in_cache,
            'failed':failed,
            'retries':retries,
            'time':time,
        })

    def reset(self):
        self.queries = []

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models
import django_pipes as pipes

# Create your models here.
class GoogleSearch(pipes.Pipe):
    uri = "http://ajax.googleapis.com/ajax/services/search/web"

    @staticmethod
    def fetch(q):
        resp = GoogleSearch.objects.get({'v':1.0, 'q':q})
        if resp and hasattr(resp, "responseData") and hasattr(resp.responseData, "results"):
            return resp.responseData.results

class TwitterSearch(pipes.Pipe):
    uri = "http://search.twitter.com/search.json"
    
    @staticmethod
    def fetch(q):
        resp = TwitterSearch.objects.get({'q':q})
        if resp and hasattr(resp, "results"):
            return resp.results

########NEW FILE########
__FILENAME__ = views
from pipes_sample.search.models import GoogleSearch, TwitterSearch
from django.shortcuts import render_to_response

def index(request):
    q = request.GET.get('q','Paris Hilton')
    results = GoogleSearch.fetch(q)
    ignored = TwitterSearch.fetch(q)
    return render_to_response("search.html", {'results':results,'q':q})

def twitter(request):
    q = request.GET.get('q','Barrack Obama')
    results = TwitterSearch.fetch(q)
    return render_to_response("twitter.html", {'results':results,'q':q})

########NEW FILE########
__FILENAME__ = settings
# Django settings for pipes_sample project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'rh0df(l@i)+eaact(%-!$)%co8gj1j7@$w!ymrp-%zwj1hn3ox'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django_pipes.middleware.PipesStatsMiddleware',
)

ROOT_URLCONF = 'pipes_sample.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/Users/harish/Code/Python/DjangoProjects/pipes_sample/templates",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django_pipes',
    'pipes_sample.search',
)

# "pipes"-specific settings
PIPES_SOCKET_TIMEOUT = 3
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('pipes_sample.search.views',
    (r'^$', 'index'),
    (r'^twitter/$', 'twitter'),
)

########NEW FILE########
__FILENAME__ = run_tests
#! /usr/bin/env python
if __name__ == "__main__":
    import os
    if "DJANGO_SETTINGS_MODULE" not in os.environ:
        print "Using pipes_sample as the test Django project..."
        os.environ['DJANGO_SETTINGS_MODULE'] = 'pipes_sample.settings'
    import nose
    nose.main()

########NEW FILE########
__FILENAME__ = testhttpserver
#! /usr/bin/env python

import time
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse

from django.utils import simplejson

class TestHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parts = urlparse(self.path)
        query = parts[2]
        params = [param.split("=") for param in parts[4].split("&")]
        if query == "/book/":
            if params and params[0][0] == "id":
                id = int(params[0][1])
                if id == 1:
                    title = "SICP"
                elif id == 2:
                    title = "jQuery programming"
                else:
                    title = "NA"
                self.wfile.write(
                    simplejson.dumps(
                        {'id':id,'title':title}
                    )
                )
            else:
                self.wfile.write("")
        elif query == "/timeout/":
            time.sleep(4)
            self.wfile.write("")
        else:
            self.wfile.write("")
    def do_POST(self):
        parts = urlparse(self.path)
        query = parts[2]
        self.wfile.write(simplejson.dumps("success"))

HTTPServer(('localhost',9090), TestHTTPRequestHandler).serve_forever()

########NEW FILE########
__FILENAME__ = test_pipes
import django_pipes as pipes
from django.core.cache import cache


# models
class Book(pipes.Pipe):
    uri = "http://localhost:9090/book/"

class Nada(pipes.Pipe):
    "This resource does not exist on the server."
    uri = "http://localhost:9091/nonexistent/"

class TimesOut(pipes.Pipe):
    uri = "http://localhost:9090/timeout/"

class BookNotCached(pipes.Pipe):
    uri = "http://localhost:9090/book/"
    should_cache = False # default = True

class Flaky(pipes.Pipe):
    uri = "http://localhost:9091/nonexistent/"
    retries = 1

# tests
def test_two_pipes_of_same_kind_with_different_params():
    "Two pipes of the same kind but filtered by different params should give back different result sets."
    b1 = Book.objects.get({'id':1})
    b2 = Book.objects.get({'id':2})
    assert b1.id != b2.id

def test_POST_request():
    b1 = Book(id=1, title="Python in a nutshell")
    r = b1.save()
    assert r == "success"

def test_fetch_nonexistent_resource():
    try:
        nada = Nada.objects.get({'id':1})
    except pipes.ResourceNotAvailableException, e:
        assert True
    else:
        assert False

def test_fetch_timeout():
    try:
        TimesOut.objects.all()
    except pipes.ResourceNotAvailableException, e:
        import socket
        assert hasattr(e, 'reason') and type(e.reason) == socket.timeout
    else:
        assert False

def test_pipes_debug_stats():
    # clean up stuff from previous tests
    pipes.debug_stats.reset()
    cache.delete("http://localhost:9090/book/?id=1")
    
    b1 = Book.objects.get({'id':1})
    queries = pipes.debug_stats.queries
    assert len(queries) == 1
    query1 = queries[0]
    assert query1['url'] == "http://localhost:9090/book/?id=1"
    assert query1['found_in_cache'] == False

    b1 = Book.objects.get({'id':1})
    assert len(queries) == 2
    query2 = queries[1]
    assert query2['url'] == "http://localhost:9090/book/?id=1"
    assert query2['found_in_cache'] == True

def test_pipe_level_caching_option():
    "if the pipe-level caching option is set to False, then it should override the default value of True"
    # clean up
    pipes.debug_stats.reset()
    cache.delete("http://localhost:9090/book/?id=1")
    
    # fetch the book with id = 1
    b1 = BookNotCached.objects.get({'id':1})
    queries = pipes.debug_stats.queries
    query1 = queries[0]
    assert query1['found_in_cache'] == False
    
    # fetch the book with id = 1 again; should not be fetched from cache
    b2 = BookNotCached.objects.get({'id':1})
    query2 = queries[1]
    assert query2['found_in_cache'] == False

def test_request_level_caching_option():
    "if caching is defined at request-level, it should override global default or pipe-level caching if any"

    # clean up stuff from previous tests
    pipes.debug_stats.reset()
    cache.delete("http://localhost:9090/book/?id=1")

    # override global default
    b1 = Book.objects.get({'id':1}, should_cache=False)
    b1 = Book.objects.get({'id':1}, should_cache=False)
    queries = pipes.debug_stats.queries
    assert queries[1]['found_in_cache'] == False
    
    # override pipes-level default
    nb1 = BookNotCached.objects.get({'id':1}, should_cache=True)
    nb1 = BookNotCached.objects.get({'id':1})
    assert queries[3]['found_in_cache'] == True

def test_retries():
    "if fetching fails, should retry."
    
    pipes.debug_stats.reset()
    queries = pipes.debug_stats.queries
    
    # override global default
    try:
        f = Flaky.objects.all()
    except pipes.ResourceNotAvailableException, e:
        assert queries[0]['retries'] == 1

    # override pipes-level default
    try:
        f = Flaky.objects.all(retries=2)
    except pipes.ResourceNotAvailableException, e:
        assert queries[1]['retries'] == 2

########NEW FILE########
