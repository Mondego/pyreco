__FILENAME__ = decorators
import functools


def mobile_template(template):
    """
    Mark a function as mobile-ready and pass a mobile template if MOBILE.

    @mobile_template('a/{mobile/}/b.html')
    def view(request, template=None):
        ...

    if request.MOBILE=True the template will be 'a/mobile/b.html'.
    if request.MOBILE=False the template will be 'a/b.html'.

    This function is useful if the mobile view uses the same context but a
    different template.
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(request, *args, **kw):
            fmt = {'mobile/': 'mobile/' if request.MOBILE else ''}
            kw['template'] = template.format(**fmt)
            return f(request, *args, **kw)
        return wrapper
    return decorator


def mobilized(normal_fn):
    """
    Replace a view function with a normal and mobile view.

    def view(request):
        ...

    @mobilized(view)
    def view(request):
        ...

    The second function is the mobile version of view. The original
    function is overwritten, and the decorator will choose the correct
    function based on request.MOBILE (set in middleware).
    """
    def decorator(mobile_fn):
        @functools.wraps(mobile_fn)
        def wrapper(request, *args, **kw):
            if request.MOBILE:
                return mobile_fn(request, *args, **kw)
            else:
                return normal_fn(request, *args, **kw)
        return wrapper
    return decorator


def not_mobilized(f):
    """
    Explicitly mark this function as not mobilized. If marked,
    Vary headers will not be sent.
    """
    @functools.wraps(f)
    def wrapper(request, *args, **kw):
        request.NO_MOBILE = True
        return f(request, *args, **kw)
    return wrapper

########NEW FILE########
__FILENAME__ = middleware
import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.cache import patch_vary_headers


# Mobile user agents.
USER_AGENTS = 'android|fennec|iemobile|iphone|opera (?:mini|mobi)'
USER_AGENTS = re.compile(getattr(settings, 'MOBILE_USER_AGENTS', USER_AGENTS))

# We set a cookie if you explicitly select mobile/no mobile.
COOKIE = getattr(settings, 'MOBILE_COOKIE', 'mobile')


# We do this in zeus for performance, so this exists for the devserver and
# to work out the logic.
class DetectMobileMiddleware(object):

    def process_request(self, request):
        ua = request.META.get('HTTP_USER_AGENT', '').lower()
        mc = request.COOKIES.get(COOKIE)
        if (USER_AGENTS.search(ua) and mc != 'off') or mc == 'on':
            request.META['HTTP_X_MOBILE'] = '1'

    def process_response(self, request, response):
        if not getattr(request, 'NO_MOBILE', False):
            patch_vary_headers(response, ['User-Agent'])
        return response


class XMobileMiddleware(object):

    def redirect(self, request, base):
        path = base.rstrip('/') + request.path
        if request.GET:
            path += '?' + request.GET.urlencode()
        response = HttpResponsePermanentRedirect(path)
        response['Vary'] = 'X-Mobile'
        return response

    def process_request(self, request):
        try:
            want_mobile = int(request.META.get('HTTP_X_MOBILE', 0))
        except Exception:
            want_mobile = False
        request.MOBILE = want_mobile

    def process_response(self, request, response):
        if not getattr(request, 'NO_MOBILE', False):
            patch_vary_headers(response, ['X-Mobile'])
        return response

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import unittest

from django import http, test
from django.utils import http as urllib

from mobility import decorators, middleware


FENNEC = ('Mozilla/5.0 (Android; Linux armv7l; rv:2.0b8) '
          'Gecko/20101221 Firefox/4.0b8 Fennec/4.0b3')
FIREFOX = 'Mozilla/5.0 (Windows NT 5.1; rv:2.0b9) Gecko/20100101 Firefox/4.0b9'


class TestDetectMobile(unittest.TestCase):

    def check(self, mobile, ua=None, cookie=None):
        d = {}
        if cookie:
            d['HTTP_COOKIE'] = 'mobile=%s' % cookie
        if ua:
            d['HTTP_USER_AGENT'] = ua
        request = test.RequestFactory().get('/', **d)
        response = middleware.DetectMobileMiddleware().process_request(request)
        assert response is None
        if mobile:
            self.assertEqual(request.META['HTTP_X_MOBILE'], '1')
        else:
            assert 'HTTP_X_MOBILE' not in request.META

    def test_mobile_ua(self):
        self.check(mobile=True, ua=FENNEC)

    def test_mobile_ua_and_cookie_on(self):
        self.check(mobile=True, ua=FENNEC, cookie='on')

    def test_mobile_ua_and_cookie_off(self):
        self.check(mobile=False, ua=FENNEC, cookie='off')

    def test_nonmobile_ua(self):
        self.check(mobile=False, ua=FIREFOX)

    def test_nonmobile_ua_and_cookie_on(self):
        self.check(mobile=True, ua=FIREFOX, cookie='on')

    def test_nonmobile_ua_and_cookie_off(self):
        self.check(mobile=False, ua=FIREFOX, cookie='off')

    def test_no_ua(self):
        self.check(mobile=False)

    def test_vary(self):
        request = test.RequestFactory().get('/')
        response = http.HttpResponse()
        r = middleware.DetectMobileMiddleware().process_response(request,
                                                                 response)
        assert r is response
        self.assertEqual(response['Vary'], 'User-Agent')


class TestXMobile(unittest.TestCase):

    def check(self, xmobile, mobile):
        request = test.RequestFactory().get('/')
        if xmobile:
            request.META['HTTP_X_MOBILE'] = xmobile
        middleware.XMobileMiddleware().process_request(request)
        self.assertEqual(request.MOBILE, mobile)

    def test_bad_xmobile(self):
        self.check(xmobile='xxx', mobile=False)

    def test_no_xmobile(self):
        self.check(xmobile=None, mobile=False)

    def test_xmobile_1(self):
        self.check(xmobile='1', mobile=True)

    def test_xmobile_0(self):
        self.check(xmobile='0', mobile=False)

    def test_vary(self):
        request = test.RequestFactory().get('/')
        response = http.HttpResponse()
        r = middleware.XMobileMiddleware().process_response(request, response)
        assert r is response
        self.assertEqual(response['Vary'], 'X-Mobile')

        response['Vary'] = 'User-Agent'
        middleware.XMobileMiddleware().process_response(request, response)
        self.assertEqual(response['Vary'], 'User-Agent, X-Mobile')


class TestMobilized(unittest.TestCase):

    def setUp(self):
        normal = lambda r: 'normal'
        mobile = lambda r: 'mobile'
        self.view = decorators.mobilized(normal)(mobile)
        self.request = test.RequestFactory().get('/')

    def test_call_normal(self):
        self.request.MOBILE = False
        self.assertEqual(self.view(self.request), 'normal')

    def test_call_mobile(self):
        self.request.MOBILE = True
        self.assertEqual(self.view(self.request), 'mobile')


class TestNotMobilized(unittest.TestCase):

    def setUp(self):
        self.view = lambda r: getattr(r, 'NO_MOBILE', False)
        self.request = test.RequestFactory().get('/')

    def test_call_normal(self):
        self.assertEqual(self.view(self.request), False)

    def test_call_nonmobile(self):
        view = decorators.not_mobilized(self.view)
        self.assertEqual(view(self.request), True)

    def test_vary_xmobile(self):
        request = test.RequestFactory().get('/')
        request.NO_MOBILE = True
        response = http.HttpResponse()

        r = middleware.XMobileMiddleware().process_response(request, response)
        self.assertEqual(response.get('Vary', None), None)

    def test_vary_detect_mobile(self):
        request = test.RequestFactory().get('/')
        request.NO_MOBILE = True
        response = http.HttpResponse()

        r = middleware.DetectMobileMiddleware().process_response(request,
                                                                 response)
        self.assertEqual(response.get('Vary', None), None)


class TestMobileTemplate(unittest.TestCase):

    def setUp(self):
        template = 'a/{mobile/}b.html'
        func = lambda request, template: template
        self.view = decorators.mobile_template(template)(func)
        self.request = test.RequestFactory().get('/')

    def test_normal_template(self):
        self.request.MOBILE = False
        self.assertEqual(self.view(self.request), 'a/b.html')

    def test_mobile_template(self):
        self.request.MOBILE = True
        self.assertEqual(self.view(self.request), 'a/mobile/b.html')

########NEW FILE########
