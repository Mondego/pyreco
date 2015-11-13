__FILENAME__ = decorators
from commonware.response.decorators import (xframe_sameorigin,
                                            xframe_allow,
                                            xframe_deny,
                                            xrobots_exempt,
                                            xrobots_tag)

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings


class ScrubRequestOnException(object):
    """
    Hide sensitive information so they're not recorded in error logging.
    * passwords in request.POST
    * sessionid in request.COOKIES
    """

    def process_exception(self, request, exception):
        # Get a copy so it's mutable.
        request.POST = request.POST.copy()
        for key in request.POST:
            if 'password' in key.lower():
                request.POST[key] = '******'

        # Remove session id from cookies
        if settings.SESSION_COOKIE_NAME in request.COOKIES:
            request.COOKIES[settings.SESSION_COOKIE_NAME] = '******'
            # Clearing out all cookies in request.META. They will already
            # be sent with request.COOKIES.
            request.META['HTTP_COOKIE'] = '******'

########NEW FILE########
__FILENAME__ = tests
from django.db import DatabaseError

from nose.tools import eq_
from test_utils import RequestFactory

from commonware.exceptions.middleware import ScrubRequestOnException


def test_scrub_request():
    tests = (
        'password',
        'PASSWORD',
        'password2',
        'confirmpassword',
        'PaSsWorD',
    )

    e = DatabaseError()
    rf = RequestFactory()
    hpoe = ScrubRequestOnException()

    def hidden(password):
        sessionid = 'qwertyuiopasdfghjklzxcvbnm'
        rf.cookies['sessionid'] = sessionid
        post = rf.post('/foo', {password: 'foo'})
        eq_(post.POST[password], 'foo')
        eq_(post.COOKIES['sessionid'], sessionid)
        assert sessionid in post.META['HTTP_COOKIE']
        hpoe.process_exception(post, e)
        eq_(post.POST[password], '******')
        eq_(post.COOKIES['sessionid'], '******')
        eq_(post.META['HTTP_COOKIE'], '******')

    for pw in tests:
        yield hidden, pw

########NEW FILE########
__FILENAME__ = middleware
import threading

from django.utils import encoding


_local = threading.local()


def get_remote_addr():
    return getattr(_local, 'remote_addr', None)


def get_username():
    return getattr(_local, 'username', '<anon>')


class ThreadRequestMiddleware(object):
    """
    Store the current remote address in thread-local storage so our
    logging wrapper can access it.
    """

    def process_request(self, request):
        _local.remote_addr = request.META.get('REMOTE_ADDR', '')
        name = '<anon>'
        if hasattr(request, 'user') and request.user.is_authenticated():
            name = encoding.smart_str(request.user.username)
        _local.username = name

########NEW FILE########
__FILENAME__ = middleware
from commonware.exceptions.middleware import ScrubRequestOnException
from commonware.log.middleware import ThreadRequestMiddleware
from commonware.request.middleware import SetRemoteAddrFromForwardedFor
from commonware.response.middleware import (FrameOptionsHeader,
                                            ContentTypeOptionsHeader,
                                            RobotsTagHeader,
                                            StrictTransportMiddleware,
                                            XSSProtectionHeader)
from commonware.session.middleware import NoVarySessionMiddleware

########NEW FILE########
__FILENAME__ = middleware
import socket

from django.conf import settings

TYPES = (socket.AF_INET, socket.AF_INET6)


def is_valid(ip):
    for af in TYPES:
        try:
            socket.inet_pton(af, ip)
            return True
        except socket.error:
            pass
    return False


class SetRemoteAddrFromForwardedFor(object):
    """
    Replaces the Django 1.1 middleware to replace the remote IP with
    the value of the X-Forwarded-For header for use behind reverse proxy
    servers, like load balancers.
    """

    def process_request(self, request):
        ips = []

        if 'HTTP_X_FORWARDED_FOR' in request.META:
            xff = [i.strip() for i in
                   request.META['HTTP_X_FORWARDED_FOR'].split(',')]
            ips = [ip for ip in xff if is_valid(ip)]
        else:
            return

        ips.append(request.META['REMOTE_ADDR'])

        known = getattr(settings, 'KNOWN_PROXIES', [])
        ips.reverse()
        for ip in ips:
            request.META['REMOTE_ADDR'] = ip
            if not ip in known:
                break

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings

import mock
from nose.tools import eq_
from test_utils import RequestFactory

from commonware.request.middleware import (SetRemoteAddrFromForwardedFor,
                                           is_valid)


mw = SetRemoteAddrFromForwardedFor()


def get_req():
    req = RequestFactory().get('/')
    req.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4, 2.3.4.5'
    req.META['REMOTE_ADDR'] = '127.0.0.1'
    return req


def test_xff():
    req = get_req()
    mw.process_request(req)
    eq_('127.0.0.1', req.META['REMOTE_ADDR'])


@mock.patch.object(settings._wrapped, 'KNOWN_PROXIES', ['127.0.0.1'])
def test_xff_known():
    req = get_req()
    mw.process_request(req)
    eq_('2.3.4.5', req.META['REMOTE_ADDR'])

    req = get_req()
    del req.META['HTTP_X_FORWARDED_FOR']
    mw.process_request(req)
    eq_('127.0.0.1', req.META['REMOTE_ADDR'])


@mock.patch.object(settings._wrapped, 'KNOWN_PROXIES',
                   ['127.0.0.1', '2.3.4.5'])
def test_xff_multiknown():
    req = get_req()
    mw.process_request(req)
    eq_('1.2.3.4', req.META['REMOTE_ADDR'])


@mock.patch.object(settings._wrapped, 'KNOWN_PROXIES', ['127.0.0.1'])
def test_xff_bad_address():
    req = get_req()
    req.META['HTTP_X_FORWARDED_FOR'] += ',foobar'
    mw.process_request(req)
    eq_('2.3.4.5', req.META['REMOTE_ADDR'])


@mock.patch.object(settings._wrapped, 'KNOWN_PROXIES',
                   ['127.0.0.1', '2.3.4.5'])
def test_xff_all_known():
    """If all the remotes are known, use the last one."""
    req = get_req()
    req.META['HTTP_X_FORWARDED_FOR'] = '2.3.4.5'
    mw.process_request(req)
    eq_('2.3.4.5', req.META['REMOTE_ADDR'])


def test_is_valid():
    """IPv4 and IPv6 addresses are OK."""
    tests = (
        ('1.2.3.4', True),
        ('2.3.4.5', True),
        ('foobar', False),
        ('4.256.4.12', False),
        ('fe80::a00:27ff:fed5:56e0', True),
        ('fe80::a00:277ff:fed5:56e0', False),
        ('fe80::a00:27ff:ged5:56e0', False),
    )

    def _check(i, v):
        eq_(v, is_valid(i))

    for i, v in tests:
        yield _check, i, v

########NEW FILE########
__FILENAME__ = models
# Import monkeypatch code at startup.
from commonware.response.cookies.monkeypatch import patch_all


patch_all()

########NEW FILE########
__FILENAME__ = monkeypatch
"""Monkey-patch secure and httponly cookies into Django by default.

Enable this by adding ``commonware.response.cookies`` to your INSTALLED_APPS.

You can exempt every cookie by passing secure=False or httponly=False,
respectively:

    response.set_cookie('hello', value='world', secure=False, httponly=False)

To disable either of these patches, set COOKIES_SECURE = False or
COOKIES_HTTPONLY = False in settings.py.

Note: The httponly flag on cookies requires Python 2.6. Patches welcome.
"""

from functools import wraps
import os

from django.conf import settings
from django.http import HttpResponse


def set_cookie_secure(f):
    """
    Decorator for HttpResponse.set_cookie to enable httponly and secure
    for cookies by default.
    """
    @wraps(f)
    def wrapped(self, *args, **kwargs):
        # Default to secure=True unless:
        # - feature disabled or
        # - secure=* defined in set_cookie call or
        # - this is not an HTTPS request.
        if (getattr(settings, 'COOKIES_SECURE', True) and
                'secure' not in kwargs and
                os.environ.get('HTTPS', 'off') == 'on'):
            kwargs['secure'] = True

        # Set httponly flag unless feature disabled. Defaults to httponly=True
        # unless httponly=* was defined in set_cookie call.
        if (getattr(settings, 'COOKIES_HTTPONLY', True) and
                'httponly' not in kwargs):
            kwargs['httponly'] = True

        return f(self, *args, **kwargs)

    return wrapped


def patch_all():
    HttpResponse.set_cookie = set_cookie_secure(HttpResponse.set_cookie)

########NEW FILE########
__FILENAME__ = tests
from django.http import HttpResponse
from mock import patch

from commonware.response.cookies.monkeypatch import patch_all


patch_all()


def test_insecure_response_cookies():
    """Ensure cookies are set as secure and httponly unless exempt."""

    # Not a secure request: Default to httponly=True, secure=False
    with patch.dict('os.environ', {'HTTPS': ''}):
        resp = HttpResponse()
        resp.set_cookie('hello', value='world')
        assert resp.cookies['hello']['httponly']
        assert not resp.cookies['hello']['secure']


def test_secure_response_cookies():

    # Secure request => automatically secure cookie, unless exempt.
    with patch.dict('os.environ', {'HTTPS': 'on'}):
        resp = HttpResponse()
        resp.set_cookie('default', value='foo')
        resp.set_cookie('not_secure', value='bar', secure=False)
        assert resp.cookies['default']['secure']
        assert not resp.cookies['not_secure']['secure']


def test_no_httponly_cookies():
    resp = HttpResponse()
    resp.set_cookie('default', value='foo')
    resp.set_cookie('js_ok', value='bar', httponly=False)
    assert resp.cookies['default']['httponly']
    assert not resp.cookies['js_ok']['httponly']

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps

from django.utils.decorators import available_attrs


def xframe_sameorigin(view_fn):
    @wraps(view_fn, assigned=available_attrs(view_fn))
    def _wrapped_view(request, *args, **kwargs):
        response = view_fn(request, *args, **kwargs)
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response
    return _wrapped_view


def xframe_allow(view_fn):
    @wraps(view_fn, assigned=available_attrs(view_fn))
    def _wrapped_view(request, *args, **kwargs):
        response = view_fn(request, *args, **kwargs)
        response.no_frame_options = True
        return response
    return _wrapped_view


def xframe_deny(view_fn):
    @wraps(view_fn, assigned=available_attrs(view_fn))
    def _wrapped_view(request, *args, **kwargs):
        response = view_fn(request, *args, **kwargs)
        response['X-Frame-Options'] = 'DENY'
        return response
    return _wrapped_view


def xrobots_exempt(view_fn):
    @wraps(view_fn, assigned=available_attrs(view_fn))
    def _wrapped_view(request, *args, **kwargs):
        response = view_fn(request, *args, **kwargs)
        response.no_robots_tag = True
        return response
    return _wrapped_view


def xrobots_tag(rule='noindex'):
    def decorator(view_fn):
        @wraps(view_fn, assigned=available_attrs(view_fn))
        def _wrapped_view(request, *args, **kwargs):
            response = view_fn(request, *args, **kwargs)
            response['X-Robots-Tag'] = rule
            return response
        return _wrapped_view
    return decorator

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings


class FrameOptionsHeader(object):
    """
    Set an X-Frame-Options header. Default to DENY. Set
    response['X-Frame-Options'] = 'SAMEORIGIN'
    to override.
    """

    def process_response(self, request, response):
        if hasattr(response, 'no_frame_options'):
            return response

        if not 'X-Frame-Options' in response:
            response['X-Frame-Options'] = 'DENY'

        return response


class RobotsTagHeader(object):
    """Set an X-Robots-Tag header.

    Default to noodp to avoid using directories for page titles. Set
    a value of response['X-Robots-Tag'] or use the relevant decorators
    to override.

    Change the default in settings by setting X_ROBOTS_DEFAULT = ''.
    """

    def process_response(self, request, response):
        if getattr(response, 'no_robots_tag', False):
            return response

        if not 'X-Robots-Tag' in response:
            default = getattr(settings, 'X_ROBOTS_DEFAULT', 'noodp')
            response['X-Robots-Tag'] = default

        return response


class StrictTransportMiddleware(object):
    """
    Set the Strict-Transport-Security header on responses. Use the
    STS_MAX_AGE setting to control the max-age value. (Default: 1 year.)
    Use the STS_SUBDOMAINS boolean to add includeSubdomains.
    (Default: False.)
    """

    def process_response(self, request, response):
        if request.is_secure():
            age = getattr(settings, 'STS_MAX_AGE', 31536000)  # 365 days.
            subdomains = getattr(settings, 'STS_SUBDOMAINS', False)
            val = 'max-age=%d' % age
            if subdomains:
                val += '; includeSubDomains'
            response['Strict-Transport-Security'] = val
        return response


class XSSProtectionHeader(object):
    """
    Set the X-XSS-Protection header on responses. Defaults to
    '1; mode=block'. Set response['X-XSS-Protection'] = '0' (disable)
    or '1' (rewrite mode) to override.
    """

    def process_response(self, request, response):
        if not 'X-XSS-Protection' in response:
            response['X-XSS-Protection'] = '1; mode=block'
        return response


class ContentTypeOptionsHeader(object):
    """
    Set the X-Content-Type-Options header on responses. Defaults
    to 'nosniff'. Set response['X-Content-Type-Options'] = ''
    to override.
    """

    def process_response(self, request, response):
        if not 'X-Content-Type-Options' in response:
            response['X-Content-Type-Options'] = 'nosniff'
        return response

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.http import HttpResponse
from django.test.client import RequestFactory

import mock
from nose.tools import eq_

from commonware.response import decorators, middleware


view_fn = lambda *a: HttpResponse()


def _wrapped_resp(decorator, fn, mw_cls=None):
    req = RequestFactory().get('/')
    _wrapped = decorator(fn)
    resp = _wrapped(req)
    if mw_cls is not None:
        mw = mw_cls()
        resp = mw.process_response(req, resp)
    return resp


def _make_resp(mw_cls, secure=False):
    mw = mw_cls()
    req = RequestFactory().get('/')
    if secure:
        req.is_secure = lambda: True
    resp = mw.process_response(req, HttpResponse())
    return resp


def test_sts_middleware():
    resp = _make_resp(middleware.StrictTransportMiddleware)
    assert 'Strict-Transport-Security' not in resp
    resp = _make_resp(middleware.StrictTransportMiddleware, secure=True)
    assert 'Strict-Transport-Security' in resp
    eq_('max-age=31536000', resp['Strict-Transport-Security'])


@mock.patch.object(settings._wrapped, 'STS_SUBDOMAINS', True)
def test_sts_middleware_subdomains():
    resp = _make_resp(middleware.StrictTransportMiddleware, secure=True)
    assert 'Strict-Transport-Security' in resp
    assert resp['Strict-Transport-Security'].endswith('includeSubDomains')


def test_xframe_middleware():
    resp = _make_resp(middleware.FrameOptionsHeader)
    assert 'X-Frame-Options' in resp
    eq_('DENY', resp['X-Frame-Options'])


def test_xframe_middleware_no_overwrite():
    mw = middleware.FrameOptionsHeader()
    resp = HttpResponse()
    resp['X-Frame-Options'] = 'SAMEORIGIN'
    resp = mw.process_response({}, resp)
    eq_('SAMEORIGIN', resp['X-Frame-Options'])


def test_xframe_sameorigin_decorator():
    resp = _wrapped_resp(decorators.xframe_sameorigin, view_fn,
                         middleware.FrameOptionsHeader)
    assert 'X-Frame-Options' in resp
    eq_('SAMEORIGIN', resp['X-Frame-Options'])


def test_xframe_deny_middleware():
    resp = _wrapped_resp(decorators.xframe_deny, view_fn)
    assert 'X-Frame-Options' in resp
    eq_('DENY', resp['X-Frame-Options'])


def test_xframe_middleware_disable():
    resp = _wrapped_resp(decorators.xframe_allow, view_fn,
                         middleware.FrameOptionsHeader)
    assert not 'X-Frame-Options' in resp


def test_xssprotection_middleware():
    resp = _make_resp(middleware.XSSProtectionHeader)
    assert 'X-XSS-Protection' in resp
    eq_('1; mode=block', resp['X-XSS-Protection'])


def test_xssprotection_middleware_no_overwrite():
    mw = middleware.XSSProtectionHeader()
    resp = HttpResponse()
    resp['X-XSS-Protection'] = '1'
    resp = mw.process_response({}, resp)
    eq_('1', resp['X-XSS-Protection'])


def test_contenttypeoptions_middleware():
    resp = _make_resp(middleware.ContentTypeOptionsHeader)
    assert 'X-Content-Type-Options' in resp
    eq_('nosniff', resp['X-Content-Type-Options'])


def test_contenttypeoptions_middleware_no_overwrite():
    mw = middleware.ContentTypeOptionsHeader()
    resp = HttpResponse()
    resp['X-Content-Type-Options'] = ''
    resp = mw.process_response({}, resp)
    eq_('', resp['X-Content-Type-Options'])


def test_xrobotstag_middleware():
    resp = _make_resp(middleware.RobotsTagHeader)
    assert 'X-Robots-Tag' in resp
    eq_('noodp', resp['X-Robots-Tag'])


def test_xrobotstag_middleware_no_overwrite():
    mw = middleware.RobotsTagHeader()
    resp = HttpResponse()
    resp['X-Robots-Tag'] = 'bananas'
    resp = mw.process_response({}, resp)
    eq_('bananas', resp['X-Robots-Tag'])


def test_xrobots_exempt():
    resp = _wrapped_resp(decorators.xrobots_exempt, view_fn,
                         middleware.RobotsTagHeader)
    assert 'X-Robots-Tag' not in resp


def test_xrobots_tag_decorator():
    value = 'noindex,nofollow'
    resp = _wrapped_resp(decorators.xrobots_tag(value), view_fn,
                         middleware.RobotsTagHeader)
    assert 'X-Robots-Tag' in resp
    eq_(value, resp['X-Robots-Tag'])

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware


class NoVarySessionMiddleware(SessionMiddleware):
    """
    SessionMiddleware sets Vary: Cookie anytime request.session is accessed.
    request.session is accessed indirectly anytime request.user is touched.
    We always touch request.user to see if the user is authenticated, so every
    request would be sending vary, so we'd get no caching.

    We skip the cache in Zeus if someone has a session cookie, so varying on
    Cookie at this level only hurts us.
    """

    def process_response(self, request, response):
        # Let SessionMiddleware do its processing but prevent it from changing
        # the Vary header.

        # If we're in read-only mode, die early.
        if getattr(settings, 'READ_ONLY', False):
            return response

        vary = response.get('Vary', None)
        new_response = (super(NoVarySessionMiddleware, self)
                        .process_response(request, response))
        if vary:
            new_response['Vary'] = vary
        else:
            del new_response['Vary']
        return new_response

########NEW FILE########
__FILENAME__ = settings
import os

# Make filepaths relative to settings.
ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

JINJA_CONFIG = {}

STS_SUBDOMAINS = False

KNOWN_PROXIES = []

########NEW FILE########
__FILENAME__ = fabfile
"""
Creating standalone Django apps is a PITA because you're not in a project, so
you don't have a settings.py file.  I can never remember to define
DJANGO_SETTINGS_MODULE, so I run these commands which get the right env
automatically.
"""
import functools
import os

from fabric.api import local as _local


NAME = os.path.basename(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.dirname(__file__))

os.environ['DJANGO_SETTINGS_MODULE'] = '%s-project.settings' % NAME
os.environ['PYTHONPATH'] = os.pathsep.join([ROOT,
                                            os.path.join(ROOT, 'examples')])

_local = functools.partial(_local, capture=False)


def shell():
    """Open a Django shell."""
    _local('django-admin.py shell')


def test():
    """Run the tests."""
    _local('nosetests -s')


def coverage():
    """Run the tests with a coverage report."""
    _local('nosetests -s --with-coverage --cover-package=commonware')

########NEW FILE########
