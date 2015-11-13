__FILENAME__ = cache
from django.core.cache import get_cache
from django.core.cache.backends.base import InvalidCacheBackendError

try:
    cache = get_cache('debug-panel')
except InvalidCacheBackendError:
    from django.core.cache import cache
########NEW FILE########
__FILENAME__ = middleware
"""
Debug Panel middleware
"""
import threading
import time

from django.core.urlresolvers import reverse, resolve, Resolver404
from django.conf import settings
from debug_panel.cache import cache
import debug_toolbar.middleware

# the urls patterns that concern only the debug_panel application
import debug_panel.urls

def show_toolbar(request):
    """
    Default function to determine whether to show the toolbar on a given page.
    """
    if request.META.get('REMOTE_ADDR', None) not in settings.INTERNAL_IPS:
        return False

    return bool(settings.DEBUG)


debug_toolbar.middleware.show_toolbar = show_toolbar


class DebugPanelMiddleware(debug_toolbar.middleware.DebugToolbarMiddleware):
    """
    Middleware to set up Debug Panel on incoming request and render toolbar
    on outgoing response.
    """

    def process_request(self, request):
        """
        Try to match the request with an URL from debug_panel application.

        If it matches, that means we are serving a view from debug_panel,
        and we can skip the debug_toolbar middleware.

        Otherwise we fallback to the default debug_toolbar middleware.
        """

        try:
            res = resolve(request.path, urlconf=debug_panel.urls)
        except Resolver404:
            return super(DebugPanelMiddleware, self).process_request(request)

        return res.func(request, *res.args, **res.kwargs)


    def process_response(self, request, response):
        """
        Store the DebugToolbarMiddleware rendered toolbar into a cache store.

        The data stored in the cache are then reachable from an URL that is appened
        to the HTTP response header under the 'X-debug-data-url' key.
        """
        toolbar = self.__class__.debug_toolbars.get(threading.current_thread().ident, None)

        response = super(DebugPanelMiddleware, self).process_response(request, response)

        if toolbar:
            cache_key = "%f" % time.time()
            cache.set(cache_key, toolbar.render_toolbar())

            response['X-debug-data-url'] = request.build_absolute_uri(
                reverse('debug_data', urlconf=debug_panel.urls, kwargs={'cache_key': cache_key}))

        return response

########NEW FILE########
__FILENAME__ = urls
"""
URLpatterns for the debug panel.

These should not be loaded explicitly; It is used internally by the
debug-panel application.
"""
try:
    from django.conf.urls import patterns, url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, url

_PREFIX = '__debug__'

urlpatterns = patterns('debug_panel.views',
    url(r'^%s/data/(?P<cache_key>\d+\.\d+)/$' % _PREFIX, 'debug_data', name='debug_data'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from debug_panel.cache import cache
from django.shortcuts import render_to_response
from django.views.decorators.clickjacking import xframe_options_exempt

@xframe_options_exempt
def debug_data(request, cache_key):
    html = cache.get(cache_key)

    if html is None:
        return render_to_response('debug-data-unavailable.html')

    return HttpResponse(html, content_type="text/html; charset=utf-8")

########NEW FILE########
__FILENAME__ = settings
"""Django settings for tests."""

DEBUG = True
# Quick-start development settings - unsuitable for production

SECRET_KEY = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

INTERNAL_IPS = ['127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'debug_toolbar',
    'debug_panel',
    'tests',
]

MEDIA_URL = '/media/'   # Avoids https://code.djangoproject.com/ticket/21451

MIDDLEWARE_CLASSES = [
    'debug_panel.middleware.DebugPanelMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tests.urls'

STATIC_URL = '/static/'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

DEBUG_TOOLBAR_PATCH_SETTINGS = True

########NEW FILE########
__FILENAME__ = test
from __future__ import absolute_import, unicode_literals

import threading

from urlparse import urlparse

from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings

from debug_panel.middleware import DebugPanelMiddleware


rf = RequestFactory()
debug_url_header_key = 'X-debug-data-url'


@override_settings(DEBUG=True)
class DebugPanelTestCase(TestCase):
    def setUp(self):
        request = rf.get('/')
        response = HttpResponse()

        self.middleware = DebugPanelMiddleware()
        self.request = request
        self.response = response


    def _get_toolbar(self):
        return DebugPanelMiddleware.debug_toolbars[threading.current_thread().ident]

    def _set_toolbar(self, toolbar):
        DebugPanelMiddleware.debug_toolbars[threading.current_thread().ident] = toolbar

    def assertValidDebugHeader(self, response):
        self.assertIn(debug_url_header_key, response)


    def assertNoDebugHeader(self, response):
        self.assertNotIn(debug_url_header_key, response)


    def test_appends_header(self):
        self.middleware.process_request(self.request)
        self.middleware.process_response(self.request, self.response)

        self.assertValidDebugHeader(self.response)


    def test_appends_header_on_ajax_request(self):
        self.request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'

        self.middleware.process_request(self.request)
        self.middleware.process_response(self.request, self.response)

        self.assertValidDebugHeader(self.response)


    def test_debug_url_is_fully_qualified(self):
        """
        since the debug url might be resolved from a different hostname,
        inside a chrome devkit panel for example, the url must be fully
        qualified.
        """
        self.middleware.process_request(self.request)
        self.middleware.process_response(self.request, self.response)

        debug_url = self.response[debug_url_header_key]
        self.assertTrue(debug_url.startswith('http://testserver/'))


    def test_debug_view_render_toolbar(self):
        self.middleware.process_request(self.request)

        # store the toolbar before it's deleted by the middleware
        toolbar = self._get_toolbar()
        self.middleware.process_response(self.request, self.response)

        debug_url = self.response[debug_url_header_key]
        response = self.client.get(urlparse(debug_url).path)
        self.assertEqual(response.status_code, 200)

        # the toolbar must be set in DebugPanelMiddleware to be rendered
        self._set_toolbar(toolbar)
        self.assertEqual(response.content, toolbar.render_toolbar())


    def test_debug_view_frame_friendly(self):
        """
        Clickjacking protection must be disable for the debug view
        since it must be callable inside iframe.
        """
        self.middleware.process_request(self.request)
        self.middleware.process_response(self.request, self.response)

        debug_url = self.response[debug_url_header_key]
        response = self.client.get(urlparse(debug_url).path)

        self.assertNotIn('X-Frame-Options', response)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import include, patterns, url

urlpatterns = patterns('',
)

########NEW FILE########
