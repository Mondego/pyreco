__FILENAME__ = local_settings
# Settings for devel server
import os
ROOT_PATH = os.path.dirname(__file__)
DEBUG = True
TEMPLATE_DEBUG = DEBUG
CACHE_BACKEND='file://%s/django_cache' % ROOT_PATH
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(ROOT_PATH, 'example.sqlite')
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''
MEDIA_ROOT = os.path.join(ROOT_PATH, 'media')
TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates'),
)
MEDIA_URL = '/media/'

SPRINGSTEEN_LOG_QUERIES = False
SPRINGSTEEN_LOG_DIR = os.path.join(ROOT_PATH,'logs')

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
__FILENAME__ = settings
# Django settings for example_project project.

BOSS_APP_ID = None # replace with your BOSS APP ID

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
SECRET_KEY = 'r(9(!$^-w7x1+n)%e=_3r39t7mv*ekca7)e=2&vunjm!07(6h^'

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
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'springsteen',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
)

try:
    from local_settings import *
except ImportError:
    pass

try:
    from boss_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^service/$', 'example_project.views.service'),
    (r'^service2/$', 'example_project.views.service2'),
    (r'^$', 'example_project.views.search'),
)

########NEW FILE########
__FILENAME__ = views
from springsteen.views import search as default_search
from springsteen.views import service
from springsteen.services import *
from django.utils import simplejson


def search(request, timeout=2000, max_count=20, extra_params={}):
    services = (GitHubService, DeliciousPopularService, Web)
    return default_search(request, timeout, max_count, services, extra_params)


def my_retrieve_func(query, start, count):
    def random_data(query):
        return {
            'title': "random %s" % query,
            'url': "http://example.com/%s/" % query,
            'abstract': '%s %s %s' % (query,query,query),
            }
    results = [ random_data(query) for x in range(count) ]
    dict = { 'total_results': 1000, 'results': results, }
    return simplejson.dumps(dict)

def service2(request):
    return service(request, retrieve_func=my_retrieve_func)

########NEW FILE########
__FILENAME__ = local_settings
# Settings for devel server
SPRINGSTEEN_LOG_QUERIES = False # True

import os
ROOT_PATH = os.path.dirname(__file__)
DEBUG = True
TEMPLATE_DEBUG = DEBUG
CACHE_BACKEND = "dummy:///"
DATABASE_ENGINE = None
DATABASE_NAME = None
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''
MEDIA_ROOT = os.path.join(ROOT_PATH, 'media')
TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates'),
)
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/admin_media/'

ROOT_URLCONF = 'urls'
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.doc.XViewMiddleware',
)
INSTALLED_APPS = (
    'springsteen',
)


########NEW FILE########
__FILENAME__ = main
import logging, os, sys
# Google App Engine imports.
from google.appengine.ext.webapp import util

# Remove the standard version of Django.
for k in [k for k in sys.modules if k.startswith('django')]:
    del sys.modules[k]

# Force sys.path to have our own directory first, in case we want to import
# from it.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
# Must set this env var *before* importing any part of Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django.core.handlers.wsgi
import django.core.signals
import django.db
import django.dispatch.dispatcher

def main():
    # Create a Django application for WSGI.
    application = django.core.handlers.wsgi.WSGIHandler()
    
    # Run the WSGI CGI handler with that application.
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()

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
__FILENAME__ = settings
# Django settings for example_project project.

BOSS_APP_ID = None # replace with your BOSS APP ID

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
SECRET_KEY = 'r(9(!$^-w7x1+n)%e=_3r39t7mv*ekca7)e=2&vunjm!07(6h^'

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
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'springsteen',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
)

try:
    from local_settings import *
except ImportError:
    pass

try:
    from boss_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'views.search'),
)

########NEW FILE########
__FILENAME__ = views
from springsteen.views import search as default_search
from springsteen.services import Web
from django.conf import settings


def search(request, timeout=2500, max_count=10):
    services = (Web,)
    return default_search(request, timeout, max_count, services)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = services
import operator
from urllib import urlopen
from threading import Thread
from django.utils import simplejson
from django.conf import settings
from springsteen.utils import cache_get, cache_put
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree



class Service(Thread):
    total_results = 0
    _results = []
    _topic = None
    # pruning_mechanisms = ['query', 'content']
    _prune_mechanism = 'query' 
    _qty = None

    def __init__(self, query, params={}):
        super(Service, self).__init__()
        self.query = self.rewrite_query(query)
        self.params = params.copy()
        if self._topic:
            self._topic = self._topic.lower()

    def rewrite_query(self, query):
        query = query.replace(' ','+')
        if self._topic and self._prune_mechanism == 'query' and not self._topic in query:
            query = "%s+%s" % (self._topic, query)
        return query

    def run(self):
        return False

    def filter_results(self):
        'Limits maximum results fetched from  a given source.'
        if self._topic and self._prune_mechanism == 'content':
            def test(result):
                if self._topic in result['title'].lower() or self._topic in result['text'].lower():
                    return True
                return False
            self._results = [ x for x in self._results if test(x) ]

        if self._qty:
            self._results = self._results[:self._qty]
            self.total_results = len(self._results)

    def count(self):
        return len(self._results)

    def results(self):
        return self._results

    def exhausted(self):
        'Return whether a service has no additional results for query.'
        start = self.params['start']
        count = self.params['count']
        return start+count >= self.total_results 

class CachableService(Service):
    _cache_duration = 60 * 30

    def make_cache_key(self):
        key = "%s,%s,%s" % (self.__class__, self.query, self.params)
        return key.replace(" ","")

    def retrieve_cache(self):
        "Need to overload to decode cached data properly."
        pass

    def store_cache(self, raw):
        cache_put(self.make_cache_key(), raw, self._cache_duration)

class HttpCachableService(CachableService):
    _source = 'web'

    def uri(self):
        'Return full uri for query.'
        return None

    def decode(self, results):
        pass

    def retrieve_cache(self):
        cached = cache_get(self.make_cache_key())
        if cached != None:
            self.decode(cached)

    def run(self):
        self.retrieve_cache()
        if not self._results:
            request = urlopen(self.uri())
            raw = request.read()
            self.store_cache(raw)
            self.decode(raw)
        self.filter_results()

    def results(self):
        for result in self._results:
            if result.has_key('source'):
                result['_source'] = result['source']
            result['source'] = self._source
        return self._results


class SpringsteenService(HttpCachableService):
    _uri = ""
    _source = 'springsteen'
    _use_start_param = True

    def uri(self):
        uri = "%s?query=%s" % (self._uri, self.query)
        if self._use_start_param and self.params.has_key('start'):
                uri = "%s&start=%s" % (uri, self.params['start'])
        return uri

    def decode(self, results):
        try:
            data = simplejson.loads(results)
            self._results = data['results']
            self.total_results = data['total_results']
        except ValueError:
            pass


class BossSearch(HttpCachableService):

    def uri(self):
        query = self.query.replace(' ','+')
        uri = "http://boss.yahooapis.com/ysearch/%s/v1/%s?appid=%s&format=json" \
            % (self._source, query, settings.BOSS_APP_ID)
        params = ["&%s=%s" % (p, self.params[p]) for p in self.params]
        return "%s%s" % (uri, "".join(params))

    def decode(self, results):
        results = simplejson.loads(results)
        self.total_results = int(results['ysearchresponse']['totalhits'])
        self._results = results['ysearchresponse']['resultset_%s' % self._source]


class Web(BossSearch):
    _source = "web"


class Images(BossSearch):
    _source = "images"


class News(BossSearch):
    _source = "news"


class TwitterSearchService(HttpCachableService):
    """
    Returns Twitter search results in SpringsteenService compatible format.

    This service is intentionally restricted to a maximum of ``_qty`` results,
    and will not be queried again throughout pagination.

    I've done it this way because old tweets are likely to have extremely
    low relevency, and I don't want to flood results with them.
    """

    _source = 'springsteen'
    _qty = 3

    def uri(self):
        return 'http://search.twitter.com/search.json?q=%s' % self.query

    def decode(self, results):
        def transform(result):
            return {
                'title':"Twitter: %s" % result['from_user'],
                'image':result['profile_image_url'],
                'url':"http://twitter.com/%s/" % result['from_user'],
                'text':result['text'],
                }

        data = simplejson.loads(results)
        self._results = [ transform(x) for x in data['results'] ]
        self.total_results = len(self._results)

class TwitterLinkSearchService(TwitterSearchService):
    'Returns only Tweets that contain a link.'

    def filter_results(self):
        self._results = [ x for x in self._results if 'http://' in x['text'] ]
        super(TwitterLinkSearchService, self).filter_results()
        

class MetawebService(HttpCachableService):
    _source = 'metaweb'
    _service = 'search'
    _params = ''
    _qty = 3

    def uri(self):
        params = (self._service, self.query, self._params)
        return 'http://www.freebase.com/api/service/%s?query=%s%s' % params
        
    def decode(self, results):
        self._results = simplejson.loads(results)['result']
        def convert(result):
            title = result['name']
            topics = result['type']
            id = result['id']
            aliases = result['alias']
            image = result['image']
            data =  {
                'title':title,
                'text':'',
                'url': u"http://www.freebase.com%s" % id,
                }
            if aliases:
                data['alias'] = aliases
            if topics:
                data['tags'] = [ x['name'] for x in topics ]
            if image:
                data['image'] = u"http://www.freebase.com/api/trans/image_thumb%s?maxheight=45&maxwidth=45&mode=fillcrop" % image['id']
            return data


        self._results = [ convert(x) for x in self._results ]


class DeliciousPopularService(HttpCachableService):
    _base = 'http://feeds.delicious.com/v2/json/popular/' #{tag}
    _qty = 5
    _source = 'delicious'

    def uri(self):
        uri = u"%s%s" % (self._base, self.query)
        if self._qty:
            uri = "%s?count=%s" % (uri, self._qty)
        return uri

    def decode(self, raw):
        def convert(result):
            return {
                'title':result['d'],
                'url':result['u'],
                'text':'',
                'tags':result['t'],
                'datetime':result['dt'],
                }

        results = simplejson.loads(raw)
        self._results = [ convert(x) for x in results ]
        self.total_results = len(self._results)


class DeliciousRecentService(DeliciousPopularService):
    _base = 'http://feeds.delicious.com/v2/json/tag/' # {tag[+tag+...+tag]}


class GitHubService(HttpCachableService):
    _source = 'github'
    _base = 'http://github.com/api/v1/json/search/'
    _qty = 5

    def uri(self):
        return u"%s%s" % (self._base, self.query)

    def decode(self, raw):
        def convert(result):
            score = result['score'] + result['followers']*0.01
            if result['fork'] is True:
                score += 0.05
            return {
                'title': u"%s's %s" % (result['username'],result['name']),
                'url':u"http://github.com/%s/%s/tree/master" % (result['username'],result['name']),
                'text':result['description'],
                'size':result['size'],
                'is_fork':result['fork'],
                'followers':result['followers'],
                'language':result['language'],
                'name':result['name'],
                'username':result['username'],
                'pushed':result['pushed'],
                'created':result['created'],
                'score':score,
                }
        json = simplejson.loads(raw)
        results = json['repositories']
        self._results = [ convert(x) for x in results ]
        self._results.sort(reverse=True,key=operator.itemgetter('score'))
        self.total_results = len(self._results)


class AmazonProductService(HttpCachableService):
    _source = 'springsteen'
    _base_uri = 'http://ecs.amazonaws.com/onca/xml'
    _service = 'AWSECommerceService'
    _source = 'springsteen'
    _access_key=''
    _operation = 'ItemSearch'
    _search_index = 'Books'
    _search_type = 'Title'
    _qty = 2

    def uri(self):
        params = (self._base_uri, self._service,
                  self._access_key, self._operation,
                  self._search_index, self._search_type,
                  self.query)
        return "%s?Service=%s&AWSAccessKeyId=%s&Operation=%s&SearchIndex=%s&%s=%s" % params

    def decode(self, results):
        def tag(name):
            return '{http://webservices.amazon.com/AWSECommerceService/2005-10-05}%s' % name
        self._results = []
        elem = ElementTree.XML(results)
        for item in elem.find(tag('Items')).findall(tag('Item')):
            #asin = item.find(tag('ASIN')).text
            url = item.find(tag('DetailPageURL')).text
            attrs = item.find(tag('ItemAttributes'))
            authors = (attrs.findall(tag('Author')))
            author = ', '.join([x.text for x in authors])
            title = attrs.find(tag('Title')).text
            
            self._results.append({'title': "%s: %s" % (author, title),
                                  'text':'',
                                  'url':url})
        self._results = self._results[:self._qty]
        self.total_results = len(self._results)

########NEW FILE########
__FILENAME__ = springsteen
from django import template
register = template.Library()


def clean_url(word, length=75):
    parts = word.split('//')
    if len(parts) > 1:
        word = parts[1]
    if len(word) > length:
        return "%s..." % word[:length-3]
    return word

register.filter('clean_url', clean_url)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns(
    'springsteen.views',
    url(r'^search/$', 'search', name='search'),
)
                       

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
try:
    # Setup utilities for App Engine deployment
    import google.appengine.api

    def cache_get(key):
        return google.appengine.api.memcache.get(key)

    def cache_put(key, value, duration):
        google.appengine.api.memcache.set(key, value, duration)

    if getattr(settings, 'SPRINGSTEEN_LOG_QUERIES', False):
        from google.appengine.ext import db
        class QueryLog(db.Model):
            text = db.StringProperty()
            
        def log_query(msg):
            logged = QueryLog()
            logged.text = msg.lower()
            logged.put()

    else:
        def log_query(msg):
            pass


except ImportError:
    # Setup utilities for normal Django deployment
    import django.core.cache
    import logging, os

    def cache_get(key):
        return django.core.cache.cache.get(key)
    def cache_put(key, value, duration):
        django.core.cache.cache.set(key, value, duration)

    if getattr(settings, 'SPRINGSTEEN_LOG_QUERIES', False):
        def get_logger(name, file):
            logger = logging.getLogger(name)
            hdlr = logging.FileHandler(os.path.join(settings.SPRINGSTEEN_LOG_DIR, file))
            formatter = logging.Formatter('%(message)s') 
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr)
            logger.setLevel(logging.INFO)
            return logger

        QUERY_LOGGER = get_logger('findjango','queries.log')

        def log_query(msg):
            QUERY_LOGGER.info(msg.lower())
        
    else:
        def log_query(msg):
            pass



########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.http import HttpResponse
from springsteen.services import Web, Images, News
from django.utils import simplejson
from time import time
from django.conf import settings
import springsteen.utils

def multi_join(threads, timeout=None):
    'Join multiple threads with shared timeout.'
    for thread in threads:
        start = time()
        thread.join(timeout)
        if timeout is not None:
            timeout -= time() - start

def dummy_retrieve_func(query, start, count):
    """
    This is a dummy function for retrieving results.
    It should be replaced by a real function that
    return data in the same format.
    """
    data = {
        'total_results': 0,
        'results':[],
        }
    return simplejson.dumps(data)


def service(request, retrieve_func=dummy_retrieve_func, mimetype="application/json"):
    query = request.GET.get('query',None)
    if query:
        try:
            count = int(request.GET.get('count','10'))
        except ValueError:
            count = 10
        try:
            start = int(request.GET.get('start','0'))
        except ValueError:
            start = 0
        start = max(start, 0)
        return HttpResponse(retrieve_func(query, start,count), mimetype=mimetype)
    return HttpResponse('{"total_results":0, "results":[] }',
                        mimetype='application/json')


def fetch_results_batch(query, timeout, services, params):
    "Perform a batch of requests and aggregate results."
    threads = [ x(query, params) for x in services ]
    for thread in threads:
        thread.start()
    multi_join(threads, timeout=timeout)
    total_results = 0
    results = []
    unexhausted_services = []
    for thread in threads:
        if not thread.exhausted():
            unexhausted_services.append(thread.__class__)
        results = results + thread.results()
        total_results = total_results + thread.total_results

    return results, total_results, unexhausted_services


def search(request, timeout=2500, max_count=10, services=(), \
               extra_params={}, reranking_func=None, extra_context={},\
               render=True):
    """
    timeout:      a global timeout for all requested services
    max_count:    used to prevent resource draining URL hacking
    services:     services to query with search terms
    extra_params: overrides and extra parameters for searches
    reranking_func: function for reranking all results
    extra_context: extra stuff passed to the template for rendering
    """
    query = request.GET.get('query',None)
    results = []
    total_results = 0
    try:
        count = int(request.GET.get('count','%s' % max_count))
    except ValueError:
        count = 10
    count = min(count, max_count)
    try:
        start = int(request.GET.get('start','0'))
    except ValueError:
        start = 0
    start = max(start, 0)

    if query:
        # log the query
        springsteen.utils.log_query(query)

        # because we are aggregating distributed resources,
        # we don't know how many results they will return,
        # so finding the 30th result (for example) has potential
        # to be rather complex
        #
        # instead we must build up results from 0th to nth result
        # due to the caching of service results, this ideally
        # still only requires one series of requests if the
        # user is paginating through results (as opposed to jumping
        # to a high page, for example)
        batch_start = 0
        batch_count = count
        batch_i = 0
        batch_result_count = 0
        batches = []
        max_batches = getattr(settings, 'SPRINGSTEEN_MAX_BATCHES', 3)
        while batch_result_count < start+count and \
                len(services) > 0 and \
                batch_i < max_batches:
            params = {'count':batch_count, 'start':batch_start}
            params.update(extra_params)
            batch, total_results, services = fetch_results_batch(query, timeout, services, params)
            batch_result_count = batch_result_count + len(batch)
            batches.append(batch)
            
            batch_start = batch_start + batch_count
            batch_i = batch_i + 1


        # hook for providing custom ranking for results
        # we have to rerank each batch individually to
        # preserve ordering (otherwise you might have results
        # from the first batch pushed into the second batch,
        # and thus have results occur on multiple pages.
        if reranking_func:
            reranked_batches = []
            for batch in batches:
                reranked = reranking_func(query, batch)
                reranked_batches.append(reranked)
            batches = reranked_batches

        for batch in batches:
            results = results + batch
    
        # remove duplicate results
        new_results = []
        seen = {}
        for result in results:
            url = result['url']
            if not seen.has_key(url):
                new_results.append(result)
                seen[url] = True
        results = new_results
        results = results[start:start+count]

    if render:
        range = ( start+1, min(start+count,total_results) )
        next_start = start + count
        previous_start = start - count
        has_next = range[1] < total_results
        has_previous = range[0] > 1
        context = {
            'query': query,
            'count': count,
            'start': start,
            'range': range,
            'has_next': has_next,
            'has_previous': has_previous,
            'next_start': next_start,
            'previous_start': previous_start,
            'results': results,
            'total_results': total_results,
            }
        context.update(extra_context)
        return render_to_response("springsteen/results.html",context)
    else:
        return {'total_results': total_results,
                'results': results,
                'start': start,
                'count': count }


def web(request, timeout=2500, max_count=10, extra_params={}):
    services = (Web,)
    return search(request,timeout,max_count,services,extra_params)


def images(request, timeout=2500, max_count=10, extra_params={}):
    services = (Images,)
    return search(request,timeout,max_count,services,extra_params)


def news(request, timeout=2500, max_count=10, extra_params={}):
    services = (News,)
    return search(request,timeout,max_count,services,extra_params)

########NEW FILE########
