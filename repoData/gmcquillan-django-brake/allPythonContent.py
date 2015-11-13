__FILENAME__ = cachebe
import hashlib

from django.core.cache import cache
from django.core.cache.backends.base import BaseCache

from brake.backends import BaseBackend


CACHE_PREFIX = 'rl:'
BASE_CACHE = BaseCache({})
IP_PREFIX = 'ip:'
KEY_TEMPLATE = 'func:%s:%s%s:%s%s'
PERIOD_PREFIX = 'period:'


class CacheBackend(BaseBackend):

    def get_ip(self, request):
        """This gets the IP we wish to use for ratelimiting.

        It defaults to 'REMOTE_ADDR'. It's recommended that you override
        this function if you're using loadbalancers or any kind of upstream
        proxy service to route requests to Django.
        """
        return request.META['REMOTE_ADDR']

    def _keys(self, func_name, request, ip=True, field=None, period=None):
        keys = []
        if ip:
            keys.append(KEY_TEMPLATE % (
                func_name, PERIOD_PREFIX, period,
                IP_PREFIX, self.get_ip(request)
            ))

        if field is not None:
            if not isinstance(field, (list, tuple)):
                field = [field]
            for f in field:
                val = getattr(request, request.method).get(f)
                # Convert value to hexdigest as cache backend doesn't allow
                # certain characters
                if val:
                    val = hashlib.sha1(val.encode('utf-8')).hexdigest()
                    keys.append('func:%s:%s%s:field:%s:%s' % (
                        func_name, PERIOD_PREFIX, period, f, val
                    ))

        return [
            BASE_CACHE.make_key(CACHE_PREFIX + k) for k in keys
        ]

    def count(self, func_name, request, ip=True, field=None, period=60):
        """Increment counters for all relevant cache_keys given a request."""
        counters = dict((key, 1) for key in self._keys(
            func_name, request, ip, field, period))
        counters.update(cache.get_many(counters.keys()))
        for key in counters:
            counters[key] += 1
        cache.set_many(counters, timeout=period)

    def limit(self, func_name, request,
            ip=True, field=None, count=5, period=None):
        """Return limit data about any keys relevant for requst."""
        counters = cache.get_many(
            self._keys(func_name, request, ip, field, period)
        )

        limits = []
        for counter in counters:
            ratelimited_by = 'field'
            if ':ip:' in counter:
                ratelimited_by = 'ip'

            if counters[counter] > count:
                limits.append({
                    'ratelimited_by': ratelimited_by,
                    'period': period,
                    'field': field,
                    'count': counters[counter],
                    'cache_key': counter,
                    'ip': self.get_ip(request)
                })

        return limits

########NEW FILE########
__FILENAME__ = decorators
import re
from functools import wraps

from django.conf import settings
from django.http import HttpResponse

class HttpResponseTooManyRequests(HttpResponse):
    status_code = getattr(settings, 'RATELIMIT_STATUS_CODE', 403)

def _method_match(request, method=None):
    if method is None:
        method = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD']
    if not isinstance(method, list):
        method = [method]
    return request.method in method


_PERIODS = {
    's': 1,
    'm': 60,
    'h': 60 * 60,
    'd': 24 * 60 * 60,
}

rate_re = re.compile('([\d]+)/([\d]*)([smhd])')


def _split_rate(rate):
    count, multi, period = rate_re.match(rate).groups()
    count = int(count)
    time = _PERIODS[period.lower()]
    if multi:
        time = time * int(multi)
    return count, time


def get_class_by_path(path):
    mod = __import__('.'.join(path.split('.')[:-1]))
    components = path.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)

    return mod

# Allows you to override the CacheBackend in your settings.py
_backend_class = getattr(
    settings,
    'RATELIMIT_CACHE_BACKEND',
    'brake.backends.cachebe.CacheBackend'
)
_backend = get_class_by_path(_backend_class)()


def ratelimit(
    ip=True, use_request_path=False, block=False, method=None, field=None, rate='5/m', increment=None
):
    def decorator(fn):
        count, period = _split_rate(rate)

        @wraps(fn)
        def _wrapped(request, *args, **kw):
            if use_request_path:
                func_name = request.path
            else:
                func_name = fn.__name__
            response = None
            if _method_match(request, method):
                limits = _backend.limit(
                    func_name, request, ip, field, count, period
                )
                if limits:
                    if block:
                        response = HttpResponseTooManyRequests()
                    request.limited = True
                    request.limits = limits

            if response is None:
                # If the response isn't HttpResponseTooManyRequests already, run
                # the actual function to get the result.
                response = fn(request, *args, **kw)

            if _method_match(request, method) and \
                    (increment is None or (callable(increment) and increment(
                        request, response
                    ))):
                _backend.count(func_name, request, ip, field, period)

            return response

        return _wrapped

    return decorator

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = custom_backend
from brake.backends import cachebe

class MyBrake(cachebe.CacheBackend):
    def get_ip(self, request):
        return request.META.get(
            'HTTP_TRUE_CLIENT_IP',
            request.META.get('REMOTE_ADDR')
        )

########NEW FILE########
__FILENAME__ = tests
from django.core.cache import cache
from django.http import HttpResponse
from django.utils import unittest

from brake.decorators import ratelimit


class MockRLKeys(object):
    pass


class RateLimitError(Exception):
    pass


class FakeRequest(object):
    """A simple request stub."""
    method = 'POST'
    META = {'REMOTE_ADDR': '127.0.0.1'}
    path = 'fake_login_path'

    def __init__(self, headers=None):
        if headers:
            self.META.update(headers)


class FakeClient(object):
    """An extremely light-weight test client."""

    def post(self, view_func, data, headers=None):
        request = FakeRequest(headers)
        if callable(view_func):
            request.POST = data

            return view_func(request)

        return request


class RateLimitTestCase(unittest.TestCase):
    """Adds assertFailsLogin and other helper methods."""

    @classmethod
    def setUpClass(cls):
        # Class Globals
        # Add any test function names here to get them automatically
        # populated in cache.
        cls.FUNCTIONS = (
            'fake_login',
            'fake_login_no_exception',
            'fake_login_path'
        )

        cls.PERIODS = (60, 3600, 86400)
        # Setup the keys used for the ip-specific counters.
        cls.IP_TEMPLATE = ':1:rl:func:%s:period:%d:ip:127.0.0.1'
        # Keys using this template are for form field-specific counters.
        cls.FIELD_TEMPLATE = ':1:rl:func:%s:period:%s:field:username:%s'
        # Sha1 hash of 'user' used in rate limit related tests:
        cls.USERNAME_SHA1_DIGEST = 'efe049ccead779e455e93893366c119d44ddd8b5'
        cls.KEYS = MockRLKeys()
        # Create all possible combinations of IP and user_hash memcached keys.
        for period in cls.PERIODS:
            setattr(
                cls.KEYS,
                'fake_login_field_%d' % (period),
                cls.FIELD_TEMPLATE % (
                    'fake_login',
                    period,
                    cls.USERNAME_SHA1_DIGEST
                )
            )
            for function in cls.FUNCTIONS:
                setattr(
                    cls.KEYS,
                    '%s_ip_%d' % (function, period),
                    cls.IP_TEMPLATE % (function, period)
                )

    def _make_rl_key(self, func_name, period, field_hash):
        """Makes a ratelimit-style memcached key."""
        return self.FIELD_TEMPLATE % (
            func_name, period, field_hash
        )

    def set_field_ratelimit_counts(self, func_name, period, field_hash, count):
        """Sets the ratelimit counters for a particular instance.

        Args:
            func_name: str, name of the function being ratelimited.
                e.g.: fake_login.
            period: int, period (in seconds).
            field_hash: str, hash of field value.
                e.g. username.

        """
        if func_name in self.FUNCTIONS and period in self.PERIODS:
            cache.set(
                self._make_rl_key(func_name, period, field_hash),
                count
            )

    def setUp(self):
        super(RateLimitTestCase, self).setUp()
        self.client = FakeClient()
        # We want fresh cache for ratelimit testing
        cache.clear()

    def tearDown(self):
        cache.clear()
        super(RateLimitTestCase, self).tearDown()


#
## Some default view mocks
###

@ratelimit(field='username', method='POST', rate='5/m')
@ratelimit(field='username', method='POST', rate='10/h')
@ratelimit(field='username', method='POST', rate='20/d')
def fake_login(request):
    """Contrived version of a login form."""
    if getattr(request, 'limited', False):

        raise RateLimitError

    if request.method == 'POST':
        password = request.POST.get('password', 'fail')
        if password is not 'correct':

            return False

    return True


@ratelimit(field='username', method='POST', rate='10/m', block=True)
def fake_login_no_exception(request):
    """Fake view allows us to examine the response code."""
    return HttpResponse()

def fake_login_use_request_path(request):
    """Used to test use_request_path=True"""
    return HttpResponse()

class TestRateLimiting(RateLimitTestCase):

    def setUp(self):
        super(TestRateLimiting, self).setUp()
        self.good_payload = {'username': u'us\xe9r', 'password': 'correct'}
        self.bad_payload = {'username': u'us\xe9r'}

    def test_allow_some_failures(self):
        """Test to make sure that short-term thresholds ignore older ones."""

        self.assertFalse(self.client.post(fake_login, self.bad_payload))
        # We haven't gone over any threshold yet, so we should be able to
        # successfully login now.
        good_response = self.client.post(fake_login, self.good_payload)
        self.assertTrue(good_response)

    def test_fake_keys_work(self):
        """Ensure our ability to artificially set keys is accurate."""
        cache.set(self.KEYS.fake_login_ip_60, 4)
        cache.set(self.KEYS.fake_login_field_60, 4)
        cache.set(self.KEYS.fake_login_ip_3600, 4)
        cache.set(self.KEYS.fake_login_field_3600, 4)
        cache.set(self.KEYS.fake_login_ip_86400, 4)
        cache.set(self.KEYS.fake_login_field_86400, 4)

        self.client.post(fake_login, self.good_payload)

        self.assertEqual(cache.get(self.KEYS.fake_login_ip_60), 5)
        self.assertEqual(cache.get(self.KEYS.fake_login_field_60), 5)
        self.assertEqual(cache.get(self.KEYS.fake_login_ip_3600), 5)
        self.assertEqual(cache.get(self.KEYS.fake_login_field_3600), 5)
        self.assertEqual(cache.get(self.KEYS.fake_login_ip_86400), 5)
        self.assertEqual(cache.get(self.KEYS.fake_login_field_86400), 5)

    def test_ratelimit_by_ip_one_minute(self):
        """Block requests after 1 minute limit is exceeded."""
        # Set our counter as the threshold for our lowest period
        # We're only setting the counter for this remote IP
        cache.set(self.KEYS.fake_login_ip_60, 5)
        # Ensure that correct logins still go through.
        self.assertFalse(self.client.post(fake_login, self.bad_payload))
        # Now this most recent login has exceeded the threshold, we should get
        # an error:
        self.assertRaises(
            RateLimitError, self.client.post, fake_login, self.bad_payload
        )
        # With our configuration, even good requests will be rejected.
        self.assertRaises(
            RateLimitError, self.client.post, fake_login, self.good_payload
        )

    def test_ratelimit_by_field_one_minute(self):
        """Block requests after one minute limit is exceeded for a username."""
        cache.set(self.KEYS.fake_login_field_60, 5)
        self.assertFalse(self.client.post(fake_login, self.bad_payload))
        self.assertRaises(
            RateLimitError, self.client.post, fake_login, self.bad_payload
        )

    def test_ratelimit_one_hour(self):
        """Block requests after 1 hour limit is exceeded."""
        cache.set(self.KEYS.fake_login_ip_3600, 10)
        self.assertFalse(self.client.post(fake_login, self.bad_payload))
        self.assertRaises(
            RateLimitError, self.client.post, fake_login, self.bad_payload
        )

    def test_ratelimit_by_field_one_hour(self):
        """Block requests after 1 hour limit is exceeded for a username."""
        cache.set(self.KEYS.fake_login_field_3600, 10)
        self.assertFalse(self.client.post(fake_login, self.bad_payload))
        self.assertRaises(
            RateLimitError, self.client.post, fake_login, self.bad_payload
        )

    def test_ratelimit_one_day(self):
        """Block requests after 1 hour limit is exceeded."""
        cache.set(self.KEYS.fake_login_ip_86400, 20)
        self.assertFalse(self.client.post(fake_login, self.bad_payload))
        self.assertRaises(
            RateLimitError, self.client.post, fake_login, self.bad_payload
        )

    def test_ratelimit_by_field_one_day(self):
        """Block requests after 1 hour limit is exceeded for a username."""
        cache.set(self.KEYS.fake_login_field_86400, 20)
        self.assertFalse(self.client.post(fake_login, self.bad_payload))
        self.assertRaises(
            RateLimitError, self.client.post, fake_login, self.bad_payload
        )

    def test_smaller_periods_unaffected_by_larger_periods(self):
        """Ensure that counts above a smaller period's threshold."""
        # Here we set the cache way above the 1 minute threshold, but for the
        # hourly period.
        cache.set(self.KEYS.fake_login_ip_86400, 15)
        # We will not be limited because this doesn't put us over any threshold.
        self.assertTrue(self.client.post(fake_login, self.good_payload))

    def test_overridden_get_ip_works(self):
        """Test that our MyBrake Class defined in test_settings works."""
        cache.set(self.KEYS.fake_login_ip_60, 6)
        # Should trigger a ratelimit, but only from the HTTP_TRUE_CLIENT_IP
        # REMOTE_ADDR (the default) isn't in our cache at all.
        self.assertRaises(
            RateLimitError,
            self.client.post,
            fake_login,
            self.good_payload,
            headers={
                'HTTP_TRUE_CLIENT_IP': '127.0.0.1',
                'REMOTE_ADDR': '1.2.3.4'
            }
        )

    def test_status_code(self):
        """Test that our custom status code is returned."""
        cache.set(self.KEYS.fake_login_no_exception_ip_60, 20)
        result = self.client.post(fake_login_no_exception, self.bad_payload)
        # The default is 403, if we see 429, then we know our setting worked.
        self.assertEqual(result.status_code, 429)

    def test_use_request_path(self):
        """Test use_request_path=True = use request.path instead of view function name in cache key"""
        cache.set(self.KEYS.fake_login_path_ip_60, 6)
        rl = ratelimit(method='POST', use_request_path=True, rate='5/m', block=True)
        result = self.client.post(rl(fake_login_use_request_path), self.bad_payload)
        self.assertEqual(result.status_code, 429)

    def test_dont_use_request_path(self):
        """Test use_request_path=False for the same view function above"""
        cache.set(self.KEYS.fake_login_path_ip_60, 6)
        rl = ratelimit(method='POST', use_request_path=False, rate='5/m', block=True)
        result = self.client.post(rl(fake_login_use_request_path), self.bad_payload)
        self.assertEqual(result.status_code, 200)

########NEW FILE########
__FILENAME__ = utils
from decorators import _backend

"""Access limits and increment counts without using a decorator."""

def get_limits(request, label, field, periods):
    limits = []
    count = 10
    for period in periods:
        limits.extend(_backend.limit(
            label,
            request,
            field=field,
            count=count,
            period=period
        ))
        count += 10

    return limits

def inc_counts(request, label, field, periods):
    for period in periods:
        _backend.count(label, request, field=field, period=period)

########NEW FILE########
__FILENAME__ = test_settings
DATABASES = {'default':{
    'NAME':':memory:',
    'ENGINE':'django.db.backends.sqlite3'
}}

# install the bare minimum for
# testing django-brake
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'brake',
)


# This is where our ratelimiting information is stored.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

RATELIMIT_CACHE_BACKEND = 'brake.tests.custom_backend.MyBrake'
RATELIMIT_STATUS_CODE = 429 # The HTTP Response code to return.

# point to ourselves as the root urlconf, define no patterns (see below)
ROOT_URLCONF = 'test_settings'

# set this to turn off an annoying "you're doing it wrong" message
SECRET_KEY = 'HAHAHA ratelimits!'

# turn this file into a pseudo-urls.py.
from django.conf.urls import patterns

urlpatterns = patterns('',)

########NEW FILE########
