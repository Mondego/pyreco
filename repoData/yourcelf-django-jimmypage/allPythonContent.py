__FILENAME__ = cache
try:
    import hashlib
    md5 = hashlib.md5
except ImportError:
    # for Python << 2.5
    import md5 as md5_lib
    md5 = md5_lib.new()

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_save, pre_delete
from django.http import HttpResponse
from django.utils import translation
from django.utils.encoding import iri_to_uri
from django.utils.http import urlencode

__all__ = ('cache_page', 'clear_cache')

CACHE_PREFIX = getattr(settings, 'JIMMY_PAGE_CACHE_PREFIX', 'jp')
CACHE_SECONDS = getattr(settings, 'JIMMY_PAGE_CACHE_SECONDS', 0)
DISABLED = getattr(settings, 'JIMMY_PAGE_DISABLED', False)
EXPIRATION_WHITELIST = set(getattr(settings, 
    'JIMMY_PAGE_EXPIRATION_WHITELIST', 
    [
        "django_session",
        "django_admin_log",
        "registration_registrationprofile",
        "auth_message",
        "auth_user",
    ]))
DEBUG_CACHE = getattr(settings, 'JIMMY_PAGE_DEBUG_CACHE', False)
GLOBAL_GENERATION = CACHE_PREFIX + "_gen"

def clear_cache():
    debug("###### Incrementing Generation")
    try:
        cache.incr(GLOBAL_GENERATION)
    except ValueError:
        cache.set(GLOBAL_GENERATION, 1)

def expire_cache(sender, instance, **kwargs):
    table = instance._meta.db_table
    if table not in EXPIRATION_WHITELIST:
        clear_cache()
post_save.connect(expire_cache)
pre_delete.connect(expire_cache)

class cache_page(object):
    """
    Decorator to invoke cacheing for a view.  Can be used either this way::

        # uses default cache timeout
        @cache_page 
        def my_view(request, ...):
            ...

    or this way::

        # uses 60 seconds as cache timeout
        @cache_page(60) 
        def my_view(request, ...):
            ...

    """
    def __init__(self, arg=None):
        if callable(arg):
            # we are called with a function as argument; e.g., as a bare
            # decorator.  __call__ should be the new decorated function.
            self.time = CACHE_SECONDS
            self.call = self.decorate(arg)

        else:
            # we are called with an argument.  __call__ should return
            # a decorator for its argument.
            if arg is None:
                self.time = CACHE_SECONDS
            else:
                self.time = arg
            self.call = self.decorate

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def decorate(self, f):
        self.f = f
        return self.decorated

    def decorated(self, request, *args, **kwargs):
        debug("starting")
        try:
            if not settings.CACHES['default']['JOHNNY_CACHE']:
                raise KeyError
        except KeyError:
            raise ImproperlyConfigured('Not using johnny cache backend')
        if request_is_cacheable(request):
            key = get_cache_key(request)
            debug("Retrievable.")
            cached = cache.get(key)
            if cached is not None:
                debug("serving from cache")
                res = HttpResponse(cached)
                res["ETag"] = key
                return res

            debug("generating!")
            response = self.f(request, *args, **kwargs)
            if response_is_cacheable(request, response):
                debug("storing!")
                cache.set(key, response.content, self.time)
                response["ETag"] = key
            else:
                debug("Not storable.")
            return response 
        debug("Not retrievable.")
        debug("generating!")
        return self.f(request, *args, **kwargs)

def get_cache_key(request):
    user_id = "" 
    try:
        if request.user.is_authenticated():
            user_id = str(request.user.id)
    except AttributeError: # e.g. if auth is not installed
        pass
    
    key_parts = [
        CACHE_PREFIX,
        str(cache.get(GLOBAL_GENERATION)),
        iri_to_uri(request.path),
        urlencode(request.GET),
        translation.get_language(),
        user_id,
    ]
    suffix_function = getattr(settings, 'JIMMY_PAGE_SUFFIX_FUNCTION', None)
    if suffix_function and callable(suffix_function):
        part = suffix_function(request)
        if part:
            key_parts.append(part)
    key = "/".join(key_parts)

    debug(key)
    return md5(key).hexdigest()

def request_is_cacheable(request):
    return (not DISABLED) and \
            request.method == "GET" and \
            len(messages.get_messages(request)) == 0

def response_is_cacheable(request, response):
    return (not DISABLED) and \
        response.status_code == 200 and \
        response.get('Pragma', None) != "no-cache" and \
        response.get('Vary', None) != "Cookie" and \
        not request.META.get("CSRF_COOKIE_USED", None)

if DEBUG_CACHE:
    def debug(*args):
        print "JIMMYPAGE: " + " ".join([str(a) for a in args])
else:
    def debug(*args):
        pass


########NEW FILE########
__FILENAME__ = increment_cache
from django.core.management.base import BaseCommand
from jimmypage.cache import clear_cache

class Command(BaseCommand):
    help = "Increments the cache generation"
    def handle(self, *args, **options):
        clear_cache()
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
import unittest

from django.contrib.auth.models import User, AnonymousUser
from django.contrib import messages
from django.db import models
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

from jimmypage.cache import request_is_cacheable, response_is_cacheable, get_cache_key

class Model(models.Model):
    char = models.CharField(max_length=255, blank=True, null=True)

class CacheabilityTest(unittest.TestCase):
    def test_cacheable(self):
        req = HttpRequest()
        req.path = "/some/path"
        req.method = "GET"
        self.assertTrue(request_is_cacheable(req))

        req.user = AnonymousUser()
        self.assertTrue(request_is_cacheable(req))

        req.method = "POST"
        self.assertFalse(request_is_cacheable(req))

        req.method = "GET"
        self.assertTrue(request_is_cacheable(req))

        # TODO: ensure that messages works

        res = HttpResponse("fun times")
        self.assertTrue(response_is_cacheable(res))

        redirect = HttpResponseRedirect("someurl")
        self.assertFalse(response_is_cacheable(redirect))

        res['Pragma'] = "no-cache"
        self.assertFalse(response_is_cacheable(res))

    def test_key_uniqueness(self):
        req = HttpRequest()
        req.path = "/some/path"
        req.method = "GET"
        req.user = AnonymousUser()

        req2 = HttpRequest()
        req2.path = "/some/path"
        req2.method = "GET"
        req2.user = User.objects.create(username="a_user")

        req3 = HttpRequest()
        req3.path = "/some/other/path"
        req3.method = "GET"
        req3.user = AnonymousUser()

        self.assertNotEqual(get_cache_key(req), get_cache_key(req2))
        self.assertNotEqual(get_cache_key(req), get_cache_key(req3))

########NEW FILE########
__FILENAME__ = utils
import functools

from jimmypage.cache import clear_cache

def invalidate_cache(view):
    @functools.wraps(view)
    def _view(request, *args, **kwargs):
        clear_cache()
        return view(request, *args, **kwargs)
    return _view

########NEW FILE########
