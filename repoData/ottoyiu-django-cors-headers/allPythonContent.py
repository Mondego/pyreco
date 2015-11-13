__FILENAME__ = defaults
from django.conf import settings

default_headers = (
    'x-requested-with',
    'content-type',
    'accept',
    'origin',
    'authorization',
    'x-csrftoken',
)
CORS_ALLOW_HEADERS = getattr(settings, 'CORS_ALLOW_HEADERS', default_headers)

default_methods = (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
)
CORS_ALLOW_METHODS = getattr(settings, 'CORS_ALLOW_METHODS', default_methods)

CORS_ALLOW_CREDENTIALS = getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)

CORS_PREFLIGHT_MAX_AGE = getattr(settings, 'CORS_PREFLIGHT_MAX_AGE', 86400)

CORS_ORIGIN_ALLOW_ALL = getattr(settings, 'CORS_ORIGIN_ALLOW_ALL', False)

CORS_ORIGIN_WHITELIST = getattr(settings, 'CORS_ORIGIN_WHITELIST', ())

CORS_ORIGIN_REGEX_WHITELIST = getattr(settings, 'CORS_ORIGIN_REGEX_WHITELIST', ())

CORS_EXPOSE_HEADERS = getattr(settings, 'CORS_EXPOSE_HEADERS', ())

CORS_URLS_REGEX = getattr(settings, 'CORS_URLS_REGEX', '^.*$')

########NEW FILE########
__FILENAME__ = middleware
import re
from django import http
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from corsheaders import defaults as settings


ACCESS_CONTROL_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
ACCESS_CONTROL_EXPOSE_HEADERS = 'Access-Control-Expose-Headers'
ACCESS_CONTROL_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'
ACCESS_CONTROL_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
ACCESS_CONTROL_ALLOW_METHODS = 'Access-Control-Allow-Methods'
ACCESS_CONTROL_MAX_AGE = 'Access-Control-Max-Age'


class CorsMiddleware(object):

    def process_request(self, request):
        '''
            If CORS preflight header, then create an empty body response (200 OK) and return it

            Django won't bother calling any other request view/exception middleware along with
            the requested view; it will call any response middlewares
        '''
        if (self.is_enabled(request) and
            request.method == 'OPTIONS' and
            'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META):
            response = http.HttpResponse()
            return response
        return None

    def process_response(self, request, response):
        '''
            Add the respective CORS headers
        '''
        origin = request.META.get('HTTP_ORIGIN')
        if self.is_enabled(request) and origin:
            # todo: check hostname from db instead
            url = urlparse(origin)

            if not settings.CORS_ORIGIN_ALLOW_ALL and self.origin_not_found_in_white_lists(origin, url):
                return response

            response[ACCESS_CONTROL_ALLOW_ORIGIN] = "*" if settings.CORS_ORIGIN_ALLOW_ALL else origin

            if len(settings.CORS_EXPOSE_HEADERS):
                response[ACCESS_CONTROL_EXPOSE_HEADERS] = ', '.join(settings.CORS_EXPOSE_HEADERS)

            if settings.CORS_ALLOW_CREDENTIALS:
                response[ACCESS_CONTROL_ALLOW_CREDENTIALS] = 'true'

            if request.method == 'OPTIONS':
                response[ACCESS_CONTROL_ALLOW_HEADERS] = ', '.join(settings.CORS_ALLOW_HEADERS)
                response[ACCESS_CONTROL_ALLOW_METHODS] = ', '.join(settings.CORS_ALLOW_METHODS)
                if settings.CORS_PREFLIGHT_MAX_AGE:
                    response[ACCESS_CONTROL_MAX_AGE] = settings.CORS_PREFLIGHT_MAX_AGE

        return response

    def origin_not_found_in_white_lists(self, origin, url):
        return url.netloc not in settings.CORS_ORIGIN_WHITELIST and not self.regex_domain_match(origin)

    def regex_domain_match(self, origin):
        for domain_pattern in settings.CORS_ORIGIN_REGEX_WHITELIST:
            if re.match(domain_pattern, origin):
                return origin

    def is_enabled(self, request):
        return re.match(settings.CORS_URLS_REGEX, request.path)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.http import HttpResponse
from django.test import TestCase
from corsheaders.middleware import CorsMiddleware
from corsheaders.middleware import ACCESS_CONTROL_ALLOW_ORIGIN
from corsheaders.middleware import ACCESS_CONTROL_EXPOSE_HEADERS
from corsheaders.middleware import ACCESS_CONTROL_ALLOW_CREDENTIALS
from corsheaders.middleware import ACCESS_CONTROL_ALLOW_HEADERS
from corsheaders.middleware import ACCESS_CONTROL_ALLOW_METHODS
from corsheaders.middleware import ACCESS_CONTROL_MAX_AGE
from corsheaders import defaults as settings
from mock import Mock
from mock import patch


class settings_override(object):
    def __init__(self, **kwargs):
        self.overrides = kwargs

    def __enter__(self):
        self.old = dict((key, getattr(settings, key)) for key in self.overrides)
        settings.__dict__.update(self.overrides)

    def __exit__(self, exc, value, tb):
        settings.__dict__.update(self.old)


class TestCorsMiddlewareProcessRequest(TestCase):

    def setUp(self):
        self.middleware = CorsMiddleware()

    def test_process_request(self):
        request = Mock(path='/')
        request.method = 'OPTIONS'
        request.META = {'HTTP_ACCESS_CONTROL_REQUEST_METHOD': 'value'}
        with settings_override(CORS_URLS_REGEX='^.*$'):
            response = self.middleware.process_request(request)
        self.assertIsInstance(response, HttpResponse)

    def test_process_request_empty_header(self):
        request = Mock(path='/')
        request.method = 'OPTIONS'
        request.META = {'HTTP_ACCESS_CONTROL_REQUEST_METHOD': ''}
        with settings_override(CORS_URLS_REGEX='^.*$'):
            response = self.middleware.process_request(request)
        self.assertIsInstance(response, HttpResponse)

    def test_process_request_no_header(self):
        request = Mock(path='/')
        request.method = 'OPTIONS'
        request.META = {}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

    def test_process_request_not_options(self):
        request = Mock(path='/')
        request.method = 'GET'
        request.META = {'HTTP_ACCESS_CONTROL_REQUEST_METHOD': 'value'}
        response = self.middleware.process_request(request)
        self.assertIsNone(response)


@patch('corsheaders.middleware.settings')
class TestCorsMiddlewareProcessResponse(TestCase):

    def setUp(self):
        self.middleware = CorsMiddleware()

    def assertAccessControlAllowOriginEquals(self, response, header):
        self.assertIn(ACCESS_CONTROL_ALLOW_ORIGIN, response, "Response %r does "
            "NOT have %r header" % (response, ACCESS_CONTROL_ALLOW_ORIGIN))
        self.assertEqual(response[ACCESS_CONTROL_ALLOW_ORIGIN], header)

    def test_process_response_no_origin(self, settings):
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request = Mock(path='/', META={})
        processed = self.middleware.process_response(request, response)
        self.assertNotIn(ACCESS_CONTROL_ALLOW_ORIGIN, processed)

    def test_process_response_not_in_whitelist(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = False
        settings.CORS_ORIGIN_WHITELIST = ['example.com']
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request = Mock(path='/', META={'HTTP_ORIGIN': 'http://foobar.it'})
        processed = self.middleware.process_response(request, response)
        self.assertNotIn(ACCESS_CONTROL_ALLOW_ORIGIN, processed)

    def test_process_response_in_whitelist(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = False
        settings.CORS_ORIGIN_WHITELIST = ['example.com', 'foobar.it']
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request = Mock(path='/', META={'HTTP_ORIGIN': 'http://foobar.it'})
        processed = self.middleware.process_response(request, response)
        self.assertAccessControlAllowOriginEquals(processed, 'http://foobar.it')

    def test_process_response_expose_headers(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = True
        settings.CORS_EXPOSE_HEADERS = ['accept', 'origin', 'content-type']
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request = Mock(path='/', META={'HTTP_ORIGIN': 'http://example.com'})
        processed = self.middleware.process_response(request, response)
        self.assertEqual(processed[ACCESS_CONTROL_EXPOSE_HEADERS],
            'accept, origin, content-type')

    def test_process_response_dont_expose_headers(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = True
        settings.CORS_EXPOSE_HEADERS = []
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request = Mock(path='/', META={'HTTP_ORIGIN': 'http://example.com'})
        processed = self.middleware.process_response(request, response)
        self.assertNotIn(ACCESS_CONTROL_EXPOSE_HEADERS, processed)

    def test_process_response_allow_credentials(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = True
        settings.CORS_ALLOW_CREDENTIALS = True
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request = Mock(path='/', META={'HTTP_ORIGIN': 'http://example.com'})
        processed = self.middleware.process_response(request, response)
        self.assertEqual(processed[ACCESS_CONTROL_ALLOW_CREDENTIALS], 'true')

    def test_process_response_dont_allow_credentials(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = True
        settings.CORS_ALLOW_CREDENTIALS = False
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request = Mock(path='/', META={'HTTP_ORIGIN': 'http://example.com'})
        processed = self.middleware.process_response(request, response)
        self.assertNotIn(ACCESS_CONTROL_ALLOW_CREDENTIALS, processed)

    def test_process_response_options_method(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = True
        settings.CORS_ALLOW_HEADERS = ['content-type', 'origin']
        settings.CORS_ALLOW_METHODS = ['GET', 'OPTIONS']
        settings.CORS_PREFLIGHT_MAX_AGE = 1002
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request_headers = {'HTTP_ORIGIN': 'http://example.com'}
        request = Mock(path='/', META=request_headers, method='OPTIONS')
        processed = self.middleware.process_response(request, response)
        self.assertEqual(processed[ACCESS_CONTROL_ALLOW_HEADERS],
            'content-type, origin')
        self.assertEqual(processed[ACCESS_CONTROL_ALLOW_METHODS], 'GET, OPTIONS')
        self.assertEqual(processed[ACCESS_CONTROL_MAX_AGE], '1002')

    def test_process_response_options_method_no_max_age(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = True
        settings.CORS_ALLOW_HEADERS = ['content-type', 'origin']
        settings.CORS_ALLOW_METHODS = ['GET', 'OPTIONS']
        settings.CORS_PREFLIGHT_MAX_AGE = 0
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request_headers = {'HTTP_ORIGIN': 'http://example.com'}
        request = Mock(path='/', META=request_headers, method='OPTIONS')
        processed = self.middleware.process_response(request, response)
        self.assertEqual(processed[ACCESS_CONTROL_ALLOW_HEADERS],
            'content-type, origin')
        self.assertEqual(processed[ACCESS_CONTROL_ALLOW_METHODS], 'GET, OPTIONS')
        self.assertNotIn(ACCESS_CONTROL_MAX_AGE, processed)

    def test_process_response_whitelist_with_port(self, settings):
        settings.CORS_ORIGIN_ALLOW_ALL = False
        settings.CORS_ALLOW_METHODS = ['OPTIONS']
        settings.CORS_ORIGIN_WHITELIST = ('localhost:9000',)
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request_headers = {'HTTP_ORIGIN': 'http://localhost:9000'}
        request = Mock(path='/', META=request_headers, method='OPTIONS')
        processed = self.middleware.process_response(request, response)
        self.assertEqual(processed.get(ACCESS_CONTROL_ALLOW_CREDENTIALS), 'true')

    def test_process_response_adds_origin_when_domain_found_in_origin_regex_whitelist(self, settings):
        settings.CORS_ORIGIN_REGEX_WHITELIST = ('^http?://(\w+\.)?google\.com$', )
        settings.CORS_ALLOW_CREDENTIALS = True
        settings.CORS_ORIGIN_ALLOW_ALL = False
        settings.CORS_ALLOW_METHODS = ['OPTIONS']
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request_headers = {'HTTP_ORIGIN': 'http://foo.google.com'}
        request = Mock(path='/', META=request_headers, method='OPTIONS')
        processed = self.middleware.process_response(request, response)
        self.assertEqual(processed.get(ACCESS_CONTROL_ALLOW_ORIGIN), 'http://foo.google.com')

    def test_process_response_will_not_add_origin_when_domain_not_found_in_origin_regex_whitelist(self, settings):
        settings.CORS_ORIGIN_REGEX_WHITELIST = ('^http?://(\w+\.)?yahoo\.com$', )
        settings.CORS_ALLOW_CREDENTIALS = True
        settings.CORS_ORIGIN_ALLOW_ALL = False
        settings.CORS_ALLOW_METHODS = ['OPTIONS']
        settings.CORS_URLS_REGEX = '^.*$'
        response = HttpResponse()
        request_headers = {'HTTP_ORIGIN': 'http://foo.google.com'}
        request = Mock(path='/', META=request_headers, method='OPTIONS')
        processed = self.middleware.process_response(request, response)
        self.assertEqual(processed.get(ACCESS_CONTROL_ALLOW_ORIGIN), None)

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
"""
"""
import sys


def run_tests():
    from django.conf import global_settings
    from django.conf import settings
    settings.configure(
        INSTALLED_APPS=[
            'corsheaders',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'TEST_NAME': ':memory:',
            },
        },
        MIDDLEWARE_CLASSES=global_settings.MIDDLEWARE_CLASSES + (
            'corsheaders.middleware.CorsMiddleware',),
    )

    from django.test.simple import DjangoTestSuiteRunner

    test_runner = DjangoTestSuiteRunner(verbosity=1)
    return test_runner.run_tests(['corsheaders'])


def main():
    failures = run_tests()
    sys.exit(failures)

if __name__ == '__main__':
    main()


########NEW FILE########
