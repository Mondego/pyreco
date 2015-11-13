__FILENAME__ = httmock
from functools import wraps
import datetime
from requests import cookies
import json
import re
import requests
from requests import structures
import sys
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

if sys.version_info >= (3, 0, 0):
    basestring = str


class Headers(object):
    def __init__(self, res):
        self.headers = res.headers

    def get_all(self, name, failobj=None):
        return self.getheaders(name)

    def getheaders(self, name):
        return [self.headers.get(name)]


def response(status_code=200, content='', headers=None, reason=None, elapsed=0,
             request=None):
    res = requests.Response()
    res.status_code = status_code
    if isinstance(content, dict):
        if sys.version_info[0] == 3:
            content = bytes(json.dumps(content), 'utf-8')
        else:
            content = json.dumps(content)
    res._content = content
    res._content_consumed = content
    res.headers = structures.CaseInsensitiveDict(headers or {})
    res.reason = reason
    res.elapsed = datetime.timedelta(elapsed)
    res.request = request
    if hasattr(request, 'url'):
        res.url = request.url
        if isinstance(request.url, bytes):
            res.url = request.url.decode('utf-8')
    if 'set-cookie' in res.headers:
        res.cookies.extract_cookies(cookies.MockResponse(Headers(res)),
                                    cookies.MockRequest(request))

    # normally this closes the underlying connection,
    #  but we have nothing to free.
    res.close = lambda *args, **kwargs: None

    return res


def all_requests(func):
    @wraps(func)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner


def urlmatch(scheme=None, netloc=None, path=None, method=None):
    def decorator(func):
        @wraps(func)
        def inner(self_or_url, url_or_request, *args, **kwargs):
            if isinstance(self_or_url, urlparse.SplitResult):
                url = self_or_url
                request = url_or_request
            else:
                url = url_or_request
                request = args[0]
            if scheme is not None and scheme != url.scheme:
                return
            if netloc is not None and not re.match(netloc, url.netloc):
                return
            if path is not None and not re.match(path, url.path):
                return
            if method is not None and method.upper() != request.method:
                return
            return func(self_or_url, url_or_request, *args, **kwargs)
        return inner
    return decorator


def first_of(handlers, *args, **kwargs):
    for handler in handlers:
        res = handler(*args, **kwargs)
        if res is not None:
            return res


class HTTMock(object):
    """
    Acts as a context manager to allow mocking
    """
    STATUS_CODE = 200

    def __init__(self, *handlers):
        self.handlers = handlers

    def __enter__(self):
        self._real_session_send = requests.Session.send

        def _fake_send(session, request, **kwargs):
            response = self.intercept(request)
            if isinstance(response, requests.Response):
                # this is pasted from requests to handle redirects properly:
                kwargs.setdefault('stream', session.stream)
                kwargs.setdefault('verify', session.verify)
                kwargs.setdefault('cert', session.cert)
                kwargs.setdefault('proxies', session.proxies)

                allow_redirects = kwargs.pop('allow_redirects', True)
                stream = kwargs.get('stream')
                timeout = kwargs.get('timeout')
                verify = kwargs.get('verify')
                cert = kwargs.get('cert')
                proxies = kwargs.get('proxies')

                gen = session.resolve_redirects(
                    response,
                    request,
                    stream=stream,
                    timeout=timeout,
                    verify=verify,
                    cert=cert,
                    proxies=proxies)

                history = [resp for resp in gen] if allow_redirects else []

                if history:
                    history.insert(0, response)
                    response = history.pop()
                    response.history = tuple(history)
                return response

            return self._real_session_send(session, request, **kwargs)
        requests.Session.send = _fake_send
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        requests.Session.send = self._real_session_send

    def intercept(self, request):
        url = urlparse.urlsplit(request.url)
        res = first_of(self.handlers, url, request)
        if isinstance(res, requests.Response):
            return res
        elif isinstance(res, dict):
            return response(res.get('status_code'),
                            res.get('content'),
                            res.get('headers'),
                            res.get('reason'),
                            res.get('elapsed', 0),
                            request)
        elif isinstance(res, basestring):
            return response(content=res)
        elif res is None:
            return None
        else:
            raise TypeError(
                "Dont know how to handle response of type {}".format(type(res)))


def with_httmock(*handlers):
    mock = HTTMock(*handlers)

    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            with mock:
                return func(*args, **kwargs)
        return inner
    return decorator

########NEW FILE########
__FILENAME__ = tests
import requests
import sys
import unittest

from httmock import all_requests, response, urlmatch, with_httmock, HTTMock


@urlmatch(scheme='swallow')
def unmatched_scheme(url, request):
    raise AssertionError('This is outrageous')


@urlmatch(path=r'^never$')
def unmatched_path(url, request):
    raise AssertionError('This is outrageous')


@urlmatch(method='post')
def unmatched_method(url, request):
    raise AssertionError('This is outrageous')


@urlmatch(netloc=r'(.*\.)?google\.com$', path=r'^/$')
def google_mock(url, request):
    return 'Hello from Google'


@urlmatch(scheme='http', netloc=r'(.*\.)?facebook\.com$')
def facebook_mock(url, request):
    return 'Hello from Facebook'


def any_mock(url, request):
    return 'Hello from %s' % (url.netloc,)


def example_400_response(url, response):
    r = requests.Response()
    r.status_code = 400
    r._content = 'Bad request.'
    return r


class MockTest(unittest.TestCase):

    def test_return_type(self):
        with HTTMock(any_mock):
            r = requests.get('http://domain.com/')
        self.assertTrue(isinstance(r, requests.Response))

    def test_scheme_fallback(self):
        with HTTMock(unmatched_scheme, any_mock):
            r = requests.get('http://example.com/')
        self.assertEqual(r.content, 'Hello from example.com')

    def test_path_fallback(self):
        with HTTMock(unmatched_path, any_mock):
            r = requests.get('http://example.com/')
        self.assertEqual(r.content, 'Hello from example.com')

    def test_method_fallback(self):
        with HTTMock(unmatched_method, any_mock):
            r = requests.get('http://example.com/')
        self.assertEqual(r.content, 'Hello from example.com')

    def test_netloc_fallback(self):
        with HTTMock(google_mock, facebook_mock):
            r = requests.get('http://google.com/')
        self.assertEqual(r.content, 'Hello from Google')
        with HTTMock(google_mock, facebook_mock):
            r = requests.get('http://facebook.com/')
        self.assertEqual(r.content, 'Hello from Facebook')

    def test_400_response(self):
        with HTTMock(example_400_response):
            r = requests.get('http://example.com/')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.content, 'Bad request.')

    def test_real_request_fallback(self):
        with HTTMock(any_mock):
            with HTTMock(google_mock, facebook_mock):
                r = requests.get('http://example.com/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, 'Hello from example.com')

    def test_invalid_intercept_response_raises_value_error(self):
        @all_requests
        def response_content(url, request):
            return -1
        with HTTMock(response_content):
            self.assertRaises(TypeError, requests.get, 'http://example.com/')


class DecoratorTest(unittest.TestCase):

    @with_httmock(any_mock)
    def test_decorator(self):
        r = requests.get('http://example.com/')
        self.assertEqual(r.content, 'Hello from example.com')

    @with_httmock(any_mock)
    def test_iter_lines(self):
        r = requests.get('http://example.com/')
        self.assertEqual(list(r.iter_lines()),
                         ['Hello from example.com'])


class AllRequestsDecoratorTest(unittest.TestCase):

    def test_all_requests_response(self):
        @all_requests
        def response_content(url, request):
            return {'status_code': 200, 'content': 'Oh hai'}
        with HTTMock(response_content):
            r = requests.get('https://foo_bar')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, 'Oh hai')

    def test_all_str_response(self):
        @all_requests
        def response_content(url, request):
            return 'Hello'
        with HTTMock(response_content):
            r = requests.get('https://foo_bar')
        self.assertEqual(r.content, 'Hello')


class AllRequestsMethodDecoratorTest(unittest.TestCase):
    @all_requests
    def response_content(self, url, request):
        return {'status_code': 200, 'content': 'Oh hai'}

    def test_all_requests_response(self):
        with HTTMock(self.response_content):
            r = requests.get('https://foo_bar')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, 'Oh hai')

    @all_requests
    def string_response_content(self, url, request):
        return 'Hello'

    def test_all_str_response(self):
        with HTTMock(self.string_response_content):
            r = requests.get('https://foo_bar')
        self.assertEqual(r.content, 'Hello')


class UrlMatchMethodDecoratorTest(unittest.TestCase):
    @urlmatch(netloc=r'(.*\.)?google\.com$', path=r'^/$')
    def google_mock(self, url, request):
        return 'Hello from Google'

    @urlmatch(scheme='http', netloc=r'(.*\.)?facebook\.com$')
    def facebook_mock(self, url, request):
        return 'Hello from Facebook'

    def test_netloc_fallback(self):
        with HTTMock(self.google_mock, facebook_mock):
            r = requests.get('http://google.com/')
        self.assertEqual(r.content, 'Hello from Google')
        with HTTMock(self.google_mock, facebook_mock):
            r = requests.get('http://facebook.com/')
        self.assertEqual(r.content, 'Hello from Facebook')


class ResponseTest(unittest.TestCase):

    content = {'name': 'foo', 'ipv4addr': '127.0.0.1'}

    def test_response_auto_json(self):
        r = response(0, self.content)
        if sys.version_info[0] == 2:
            self.assertTrue(isinstance(r.content, str))
        elif sys.version_info[0] == 3:
            self.assertTrue(isinstance(r.content, bytes))
        else:
            assert False, 'Could not determine Python version'
        self.assertEqual(r.json(), self.content)

    def test_response_status_code(self):
        r = response(200)
        self.assertEqual(r.status_code, 200)

    def test_response_headers(self):
        r = response(200, None, {'Content-Type': 'application/json'})
        self.assertEqual(r.headers['content-type'], 'application/json')

    def test_response_cookies(self):
        @all_requests
        def response_content(url, request):
            return response(200, 'Foo', {'Set-Cookie': 'foo=bar;'},
                            request=request)
        with HTTMock(response_content):
            r = requests.get('https://foo_bar')
        self.assertEqual(len(r.cookies), 1)
        self.assertTrue('foo' in r.cookies)
        self.assertEqual(r.cookies['foo'], 'bar')

    def test_python_version_encoding_differences(self):
        # Previous behavior would result in this test failing in Python3 due
        # to how requests checks for utf-8 JSON content in requests.utils with:
        #
        # TypeError: Can't convert 'bytes' object to str implicitly
        @all_requests
        def get_mock(url, request):
            return {'content': self.content,
                    'headers': {'content-type': 'application/json'},
                    'status_code': 200,
                    'elapsed': 5}

        with HTTMock(get_mock):
            response = requests.get('http://foo_bar')
            self.assertEqual(self.content, response.json())

    def test_mock_redirect(self):
        @urlmatch(netloc='example.com')
        def get_mock(url, request):
            return {'status_code': 302,
                    'headers': {'Location': 'http://google.com/'}}

        with HTTMock(get_mock, google_mock):
            response = requests.get('http://example.com/')
            self.assertEqual(len(response.history), 1)
            self.assertEqual(response.content, 'Hello from Google')

########NEW FILE########
