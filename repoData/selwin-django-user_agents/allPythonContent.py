__FILENAME__ = middleware
from django.utils.functional import SimpleLazyObject

from .utils import get_user_agent


class UserAgentMiddleware(object):
    # A middleware that adds a "user_agent" object to request
    def process_request(self, request):
        request.user_agent = SimpleLazyObject(lambda: get_user_agent(request))

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = user_agents
from django import template

from ..utils import get_and_set_user_agent


register = template.Library()


@register.filter()
def is_mobile(request):
    return get_and_set_user_agent(request).is_mobile


@register.filter()
def is_pc(request):
    return get_and_set_user_agent(request).is_pc


@register.filter()
def is_tablet(request):
    return get_and_set_user_agent(request).is_tablet


@register.filter()
def is_bot(request):
    return get_and_set_user_agent(request).is_bot


@register.filter()
def is_touch_capable(request):
    return get_and_set_user_agent(request).is_touch_capable
########NEW FILE########
__FILENAME__ = settings
from os import path


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = ['django_user_agents']

MIDDLEWARE_CLASSES = (
    'django_user_agents.middleware.UserAgentMiddleware',
)

ROOT_URLCONF = 'django_user_agents.tests.urls'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 60,
    }
}

TEMPLATE_DIRS = (
    path.join(path.dirname(__file__), "templates"),
)
########NEW FILE########
__FILENAME__ = tests
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test.client import Client, RequestFactory
from django.utils import unittest

from user_agents.parsers import UserAgent
from django_user_agents.utils import get_cache_key, get_user_agent, get_and_set_user_agent
from django_user_agents.templatetags import user_agents


iphone_ua_string = 'Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B179 Safari/7534.48.3'
ipad_ua_string = 'Mozilla/5.0(iPad; U; CPU iPhone OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B314 Safari/531.21.10'
long_ua_string = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.3; .NET CLR 3.0.04506.30; .NET CLR 3.0.04506.648; .NET CLR 3.5.21022; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET4.0C; .NET4.0E)'


class MiddlewareTest(unittest.TestCase):

    def test_middleware_assigns_user_agent(self):
        client = Client(HTTP_USER_AGENT=ipad_ua_string)
        response = client.get(reverse('user_agent_test'))
        self.assertIsInstance(response.context['user_agent'], UserAgent)

    def test_cache_is_set(self):
        request = RequestFactory(HTTP_USER_AGENT=iphone_ua_string).get('')
        user_agent = get_user_agent(request)
        self.assertIsInstance(user_agent, UserAgent)
        self.assertIsInstance(cache.get(get_cache_key(iphone_ua_string)), UserAgent)

    def test_empty_user_agent_does_not_cause_error(self):
        request = RequestFactory().get('')
        user_agent = get_user_agent(request)
        self.assertIsInstance(user_agent, UserAgent)

    def test_get_and_set_user_agent(self):
        # Test that get_and_set_user_agent attaches ``user_agent`` to request
        request = RequestFactory().get('')
        get_and_set_user_agent(request)
        self.assertIsInstance(request.user_agent, UserAgent)

    def test_filters_can_be_loaded_in_template(self):
        client = Client(HTTP_USER_AGENT=ipad_ua_string)
        response = client.get(reverse('user_agent_test_filters'))
        self.assertEqual(response.status_code, 200)

    def test_filters(self):
        request = RequestFactory(HTTP_USER_AGENT=iphone_ua_string).get('')
        self.assertTrue(user_agents.is_mobile(request))
        self.assertTrue(user_agents.is_touch_capable(request))
        self.assertFalse(user_agents.is_tablet(request))
        self.assertFalse(user_agents.is_pc(request))
        self.assertFalse(user_agents.is_bot(request))

    def test_get_cache_key(self):
        self.assertEqual(get_cache_key(long_ua_string),
                         'c226ec488bae76c60dd68ad58f03d729')
        self.assertEqual(get_cache_key(iphone_ua_string),
                         '00705b9375a0e46e966515fe90f111da')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns('django_user_agents.tests.views',
    url(r'^user-agents/', 'test', name='user_agent_test'),
    url(r'^filters/', 'test_filters', name='user_agent_test_filters'),
)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render


def test(request):
    return render(request, "test.html", {'user_agent': request.user_agent})


def test_filters(request):
    return render(request, "test.html", {'request': request})
########NEW FILE########
__FILENAME__ = utils
from hashlib import md5

from django.core.cache import cache

from user_agents import parse


def get_cache_key(ua_string):
    # Some user agent strings are longer than 250 characters so we use its MD5
    return ''.join(['django_user_agents.', md5(ua_string).hexdigest()])


def get_user_agent(request):
    # Tries to get UserAgent objects from cache before constructing a UserAgent
    # from scratch because parsing regexes.yaml/json (ua-parser) is slow
    ua_string = request.META.get('HTTP_USER_AGENT', '')
    key = get_cache_key(ua_string)
    user_agent = cache.get(key)
    if user_agent is None:
        user_agent = parse(ua_string)
        cache.set(key, user_agent)
    return user_agent


def get_and_set_user_agent(request):
    # If request already has ``user_agent``, it will return that, otherwise
    # call get_user_agent and attach it to request so it can be reused
    if hasattr(request, 'user_agent'):
        return request.user_agent

    request.user_agent = get_user_agent(request)
    return request.user_agent

########NEW FILE########
