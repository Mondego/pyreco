__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import sys
sys.path.insert(0, '..')

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
# Django settings for ratelimitcache_demo project.

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
SECRET_KEY = 'w57fpw81*q*0200som1ru8_5%4vutoz7w**9-*gl+inqfpgpj$'

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

ROOT_URLCONF = 'demo.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

CACHE_BACKEND = 'locmem:///'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.http import HttpResponse
from pprint import pformat

import sys; sys.path.append('..')
from ratelimitcache import ratelimit, ratelimit_post

# Regular usage
@ratelimit(minutes=1, requests=10)
def index(request):
    return HttpResponse('Hello, World')


# Slightly weird usage so we can show debug information
class ratelimit_debug(ratelimit):
    def disallowed(self, request):
        return HttpResponse('RATE LIMIT EXCEEDED<br>%s' % pformat(
            self.get_counters(request)
        ))
limiter = ratelimit_debug(prefix = 'rl-debug')
@limiter
def debug(request):
    return HttpResponse(pformat(limiter.get_counters(request)))

# Weird again, this time demonstrating the ratelimit_post decorator
class ratelimit_debug_post(ratelimit_post):
    key_field = 'username'
    def disallowed(self, request):
        return HttpResponse('RATE LIMIT EXCEEDED<br>%s' % pformat(
            self.get_counters(request)
        ))
limiter_post = ratelimit_debug_post(prefix='rl-debug-post')
@limiter_post
def login(request):
    html = """
    <form action="/login/" method="post">
    <p><input type="text" name="username" value="%s"> <input type="submit"></p>
    </form>
    """ % request.POST.get('username', '')
    return HttpResponse(html + pformat(limiter_post.get_counters(request)))

urlpatterns = patterns('',
    (r'^$', index),
    (r'^debug/$', debug),
    (r'^login/$', login),
)

########NEW FILE########
__FILENAME__ = ratelimitcache
from django.http import HttpResponseForbidden
from django.core.cache import cache
from datetime import datetime, timedelta
import functools, sha

class ratelimit(object):
    "Instances of this class can be used as decorators"
    # This class is designed to be sub-classed
    minutes = 2 # The time period
    requests = 20 # Number of allowed requests in that time period
    
    prefix = 'rl-' # Prefix for memcache key
    
    def __init__(self, **options):
        for key, value in options.items():
            setattr(self, key, value)
    
    def __call__(self, fn):
        def wrapper(request, *args, **kwargs):
            return self.view_wrapper(request, fn, *args, **kwargs)
        functools.update_wrapper(wrapper, fn)
        return wrapper
    
    def view_wrapper(self, request, fn, *args, **kwargs):
        if not self.should_ratelimit(request):
            return fn(request, *args, **kwargs)
        
        counts = self.get_counters(request).values()
        
        # Increment rate limiting counter
        self.cache_incr(self.current_key(request))
        
        # Have they failed?
        if sum(counts) >= self.requests:
            return self.disallowed(request)
        
        return fn(request, *args, **kwargs)
    
    def cache_get_many(self, keys):
        return cache.get_many(keys)
    
    def cache_incr(self, key):
        # memcache is only backend that can increment atomically
        try:
            # add first, to ensure the key exists
            cache._cache.add(key, '0', time=self.expire_after())
            cache._cache.incr(key)
        except AttributeError:
            cache.set(key, cache.get(key, 0) + 1, self.expire_after())
    
    def should_ratelimit(self, request):
        return True
    
    def get_counters(self, request):
        return self.cache_get_many(self.keys_to_check(request))
    
    def keys_to_check(self, request):
        extra = self.key_extra(request)
        now = datetime.now()
        return [
            '%s%s-%s' % (
                self.prefix,
                extra,
                (now - timedelta(minutes = minute)).strftime('%Y%m%d%H%M')
            ) for minute in range(self.minutes + 1)
        ]
    
    def current_key(self, request):
        return '%s%s-%s' % (
            self.prefix,
            self.key_extra(request),
            datetime.now().strftime('%Y%m%d%H%M')
        )
    
    def key_extra(self, request):
        # By default, their IP address is used
        return request.META.get('REMOTE_ADDR', '')
    
    def disallowed(self, request):
        "Over-ride this method if you want to log incidents"
        return HttpResponseForbidden('Rate limit exceeded')
    
    def expire_after(self):
        "Used for setting the memcached cache expiry"
        return (self.minutes + 1) * 60

class ratelimit_post(ratelimit):
    "Rate limit POSTs - can be used to protect a login form"
    key_field = None # If provided, this POST var will affect the rate limit
    
    def should_ratelimit(self, request):
        return request.method == 'POST'
    
    def key_extra(self, request):
        # IP address and key_field (if it is set)
        extra = super(ratelimit_post, self).key_extra(request)
        if self.key_field:
            value = sha.new(request.POST.get(self.key_field, '')).hexdigest()
            extra += '-' + value
        return extra


########NEW FILE########
