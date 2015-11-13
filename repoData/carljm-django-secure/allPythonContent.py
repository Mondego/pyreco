__FILENAME__ = csrf
from django.conf import settings

from .util import boolean_check



@boolean_check("CSRF_VIEW_MIDDLEWARE_NOT_INSTALLED")
def check_csrf_middleware():
    return ("django.middleware.csrf.CsrfViewMiddleware"
            in settings.MIDDLEWARE_CLASSES)

check_csrf_middleware.messages = {
    "CSRF_VIEW_MIDDLEWARE_NOT_INSTALLED": (
        "You don't appear to be using Django's built-in "
        "cross-site request forgery protection via the middleware "
        "('django.middleware.csrf.CsrfViewMiddleware' "
        "is not in your MIDDLEWARE_CLASSES). "
        "Enabling the middleware is the safest approach to ensure you "
        "don't leave any holes; see "
        "https://docs.djangoproject.com/en/dev/ref/contrib/csrf/."
        )
    }

########NEW FILE########
__FILENAME__ = djangosecure
from django.conf import settings

from ..conf import conf
from .util import boolean_check



@boolean_check("SECURITY_MIDDLEWARE_NOT_INSTALLED")
def check_security_middleware():
    return ("djangosecure.middleware.SecurityMiddleware" in
            settings.MIDDLEWARE_CLASSES)

check_security_middleware.messages = {
    "SECURITY_MIDDLEWARE_NOT_INSTALLED": (
        "You do not have 'djangosecure.middleware.SecurityMiddleware' "
        "in your MIDDLEWARE_CLASSES, so the SECURE_HSTS_SECONDS, "
        "SECURE_FRAME_DENY, SECURE_CONTENT_TYPE_NOSNIFF, "
        "SECURE_BROWSER_XSS_FILTER and SECURE_SSL_REDIRECT settings "
        "will have no effect.")
    }


@boolean_check("STRICT_TRANSPORT_SECURITY_NOT_ENABLED")
def check_sts():
    return bool(conf.SECURE_HSTS_SECONDS)

check_sts.messages = {
    "STRICT_TRANSPORT_SECURITY_NOT_ENABLED": (
        "You have not set a value for the SECURE_HSTS_SECONDS setting. "
        "If your entire site is served only over SSL, you may want to consider "
        "setting a value and enabling HTTP Strict Transport Security "
        "(see http://en.wikipedia.org/wiki/Strict_Transport_Security)."
        )
    }


@boolean_check("STRICT_TRANSPORT_SECURITY_NO_SUBDOMAINS")
def check_sts_include_subdomains():
    return bool(conf.SECURE_HSTS_INCLUDE_SUBDOMAINS)

check_sts_include_subdomains.messages = {
    "STRICT_TRANSPORT_SECURITY_NO_SUBDOMAINS": (
        "You have not set the SECURE_HSTS_INCLUDE_SUBDOMAINS setting to True. "
        "Without this, your site is potentially vulnerable to attack "
        "via an insecure connection to a subdomain."
        )
    }


@boolean_check("FRAME_DENY_NOT_ENABLED")
def check_frame_deny():
    return conf.SECURE_FRAME_DENY

check_frame_deny.messages = {
    "FRAME_DENY_NOT_ENABLED": (
        "Your SECURE_FRAME_DENY setting is not set to True, "
        "so your pages will not be served with an "
        "'x-frame-options: DENY' header. "
        "Unless there is a good reason for your site to be served in a frame, "
        "you should consider enabling this header "
        "to help prevent clickjacking attacks."
        )
    }


@boolean_check("CONTENT_TYPE_NOSNIFF_NOT_ENABLED")
def check_content_type_nosniff():
    return conf.SECURE_CONTENT_TYPE_NOSNIFF

check_content_type_nosniff.messages = {
    "CONTENT_TYPE_NOSNIFF_NOT_ENABLED": (
        "Your SECURE_CONTENT_TYPE_NOSNIFF setting is not set to True, "
        "so your pages will not be served with an "
        "'x-content-type-options: nosniff' header. "
        "You should consider enabling this header to prevent the "
        "browser from identifying content types incorrectly."
        )
    }


@boolean_check("BROWSER_XSS_FILTER_NOT_ENABLED")
def check_xss_filter():
    return conf.SECURE_BROWSER_XSS_FILTER

check_xss_filter.messages = {
    "BROWSER_XSS_FILTER_NOT_ENABLED": (
        "Your SECURE_BROWSER_XSS_FILTER setting is not set to True, "
        "so your pages will not be served with an "
        "'x-xss-protection: 1; mode=block' header. "
        "You should consider enabling this header to activate the "
        "browser's XSS filtering and help prevent XSS attacks."
        )
    }


@boolean_check("SSL_REDIRECT_NOT_ENABLED")
def check_ssl_redirect():
    return conf.SECURE_SSL_REDIRECT

check_ssl_redirect.messages = {
    "SSL_REDIRECT_NOT_ENABLED": (
        "Your SECURE_SSL_REDIRECT setting is not set to True. "
        "Unless your site should be available over both SSL and non-SSL "
        "connections, you may want to either set this setting True "
        "or configure a loadbalancer or reverse-proxy server "
        "to redirect all connections to HTTPS."
        )
    }


@boolean_check("BAD_SECRET_KEY")
def check_secret_key():
    if getattr(settings, 'SECRET_KEY', None):
        return len(set(conf.SECRET_KEY)) >= 5
    else:
        return False

check_ssl_redirect.messages = {
    "BAD_SECRET_KEY": (
        "Your SECRET_KEY is either an empty string, non-existent, or has not "
        "enough characters. Please generate a long and random SECRET_KEY, "
        "otherwise many of Django's security-critical features will be "
        "vulnerable to attack."
        )
    }

########NEW FILE########
__FILENAME__ = run
from django.utils.importlib import import_module

from ..conf import conf



def get_check(func_path):
    mod_name, func_name = func_path.rsplit(".", 1)
    module = import_module(mod_name)
    return getattr(module, func_name)



def run_checks():
    warnings = set()

    for func_path in conf.SECURE_CHECKS:
        warnings.update(get_check(func_path)())

    return warnings

########NEW FILE########
__FILENAME__ = sessions
from django.conf import settings



def check_session_cookie_secure():
    ret = set()
    if not settings.SESSION_COOKIE_SECURE:
        if _session_app():
            ret.add("SESSION_COOKIE_NOT_SECURE_APP_INSTALLED")
        if _session_middleware():
            ret.add("SESSION_COOKIE_NOT_SECURE_MIDDLEWARE")
        if len(ret) > 1:
            ret = set(["SESSION_COOKIE_NOT_SECURE"])
    return ret

check_session_cookie_secure.messages = {
    "SESSION_COOKIE_NOT_SECURE_APP_INSTALLED":
        ("You have 'django.contrib.sessions' in your INSTALLED_APPS, "
         "but you have not set SESSION_COOKIE_SECURE to True."),
    "SESSION_COOKIE_NOT_SECURE_MIDDLEWARE":
        ("You have 'django.contrib.sessions.middleware.SessionMiddleware' "
         "in your MIDDLEWARE_CLASSES, but you have not set "
         "SESSION_COOKIE_SECURE to True."),
    "SESSION_COOKIE_NOT_SECURE":
        "SESSION_COOKIE_SECURE is not set to True."
    }

for k, v in check_session_cookie_secure.messages.items():
    check_session_cookie_secure.messages[k] = (
        v + "Using a secure-only session cookie makes it more difficult for "
        "network traffic sniffers to hijack user sessions.")



def check_session_cookie_httponly():
    ret = set()
    if not settings.SESSION_COOKIE_HTTPONLY:
        if _session_app():
            ret.add("SESSION_COOKIE_NOT_HTTPONLY_APP_INSTALLED")
        if _session_middleware():
            ret.add("SESSION_COOKIE_NOT_HTTPONLY_MIDDLEWARE")
        if len(ret) > 1:
            ret = set(["SESSION_COOKIE_NOT_HTTPONLY"])
    return ret

check_session_cookie_httponly.messages = {
    "SESSION_COOKIE_NOT_HTTPONLY_APP_INSTALLED":
        ("You have 'django.contrib.sessions' in your INSTALLED_APPS, "
         "but you have not set SESSION_COOKIE_HTTPONLY to True."),
    "SESSION_COOKIE_NOT_HTTPONLY_MIDDLEWARE":
        ("You have 'django.contrib.sessions.middleware.SessionMiddleware' "
         "in your MIDDLEWARE_CLASSES, but you have not set "
         "SESSION_COOKIE_HTTPONLY to True."),
    "SESSION_COOKIE_NOT_HTTPONLY":
        "SESSION_COOKIE_HTTPONLY is not set to True."
    }

for k, v in check_session_cookie_httponly.messages.items():
    check_session_cookie_httponly.messages[k] = (
        v + "Using a HttpOnly session cookie makes it more difficult for "
        "cross-site scripting attacks to hijack user sessions.")



def _session_middleware():
    return ("django.contrib.sessions.middleware.SessionMiddleware" in
            settings.MIDDLEWARE_CLASSES)



def _session_app():
    return ("django.contrib.sessions" in settings.INSTALLED_APPS)

########NEW FILE########
__FILENAME__ = util
from django.utils.functional import wraps



def boolean_check(warning_code):
    def decorator(check_func):
        @wraps(check_func)
        def inner():
            if not check_func():
                return set([warning_code])
            return set()
        return inner
    return decorator

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured



class Configuration(object):
    def __init__(self, **kwargs):
        self.defaults = kwargs


    def __getattr__(self, k):
        try:
            return getattr(settings, k)
        except AttributeError:
            if k in self.defaults:
                return self.defaults[k]
            raise ImproperlyConfigured("django-secure requires %s setting." % k)


conf = Configuration(
    SECURE_HSTS_SECONDS=0,
    SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
    SECURE_FRAME_DENY=False,
    SECURE_CONTENT_TYPE_NOSNIFF=False,
    SECURE_BROWSER_XSS_FILTER=False,
    SECURE_SSL_REDIRECT=False,
    SECURE_SSL_HOST=None,
    SECURE_REDIRECT_EXEMPT=[],
    SECURE_PROXY_SSL_HEADER=None,
    SECURE_CHECKS=[
        "djangosecure.check.csrf.check_csrf_middleware",
        "djangosecure.check.sessions.check_session_cookie_secure",
        "djangosecure.check.sessions.check_session_cookie_httponly",
        "djangosecure.check.djangosecure.check_security_middleware",
        "djangosecure.check.djangosecure.check_sts",
        "djangosecure.check.djangosecure.check_sts_include_subdomains",
        "djangosecure.check.djangosecure.check_frame_deny",
        "djangosecure.check.djangosecure.check_content_type_nosniff",
        "djangosecure.check.djangosecure.check_xss_filter",
        "djangosecure.check.djangosecure.check_ssl_redirect",
        "djangosecure.check.djangosecure.check_secret_key",
        ]
    )

########NEW FILE########
__FILENAME__ = decorators
from django.utils.functional import wraps


def frame_deny_exempt(view):
    @wraps(view)
    def inner(*args, **kwargs):
        response = view(*args, **kwargs)
        response._frame_deny_exempt = True
        return response

    return inner

########NEW FILE########
__FILENAME__ = checksecure
import textwrap

from django.core.management.base import NoArgsCommand
from django.utils.termcolors import make_style

from ...check import get_check
from ...conf import conf


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        verbosity = int(options.get("verbosity"))

        self.style.SUCCESS = make_style(opts=('bold',), fg='green')

        warn_count = 0

        for func_path in conf.SECURE_CHECKS:
            func = get_check(func_path)

            if verbosity:
                self.stdout.write("Running %s... " % func_path)

            messages = []
            for warn_code in func():
                if verbosity:
                    msg = getattr(func, "messages", {}).get(
                        warn_code, warn_code)
                else:
                    msg = warn_code
                messages.append(msg)

            if verbosity:
                if messages:
                    self.stdout.write(self.style.ERROR("FAIL"))
                else:
                    self.stdout.write(self.style.SUCCESS("OK"))
                self.stdout.write("\n")

            for msg in messages:
                self.stderr.write(self.style.ERROR(textwrap.fill(msg)) + "\n")
                if verbosity:
                    self.stderr.write("\n")

            warn_count += len(messages)

        if verbosity and not warn_count:
            self.stdout.write(self.style.SUCCESS("\nAll clear!\n\n"))

########NEW FILE########
__FILENAME__ = middleware
import re

from django.http import HttpResponsePermanentRedirect

from .conf import conf


class SecurityMiddleware(object):
    def __init__(self):
        self.sts_seconds = conf.SECURE_HSTS_SECONDS
        self.sts_include_subdomains = conf.SECURE_HSTS_INCLUDE_SUBDOMAINS
        self.frame_deny = conf.SECURE_FRAME_DENY
        self.content_type_nosniff = conf.SECURE_CONTENT_TYPE_NOSNIFF
        self.xss_filter = conf.SECURE_BROWSER_XSS_FILTER
        self.redirect = conf.SECURE_SSL_REDIRECT
        self.redirect_host = conf.SECURE_SSL_HOST
        self.proxy_ssl_header = conf.SECURE_PROXY_SSL_HEADER
        self.redirect_exempt = [
            re.compile(r) for r in conf.SECURE_REDIRECT_EXEMPT]


    def process_request(self, request):
        if self.proxy_ssl_header and not request.is_secure():
            header, value = self.proxy_ssl_header
            if request.META.get(header, None) == value:
                # We're only patching the current request; its secure status
                # is not going to change.
                request.is_secure = lambda: True

        path = request.path.lstrip("/")
        if (self.redirect and
                not request.is_secure() and
                not any(pattern.search(path)
                        for pattern in self.redirect_exempt)):
            host = self.redirect_host or request.get_host()
            return HttpResponsePermanentRedirect(
                "https://%s%s" % (host, request.get_full_path()))


    def process_response(self, request, response):
        if (self.frame_deny and
                not getattr(response, "_frame_deny_exempt", False) and
                not 'x-frame-options' in response):
            response["x-frame-options"] = "DENY"

        if (self.sts_seconds and
                request.is_secure() and
                not 'strict-transport-security' in response):
            sts_header = ("max-age=%s" % self.sts_seconds)

            if self.sts_include_subdomains:
                sts_header = sts_header + "; includeSubDomains"

            response["strict-transport-security"] = sts_header

        if (self.content_type_nosniff and
                not 'x-content-type-options' in response):
            response["x-content-type-options"] = "nosniff"

        if self.xss_filter and not 'x-xss-protection' in response:
            response["x-xss-protection"] = "1; mode=block"

        return response

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.utils.six import StringIO



class SecurityMiddlewareTest(TestCase):
    @property
    def middleware(self):
        from djangosecure.middleware import SecurityMiddleware
        return SecurityMiddleware()


    @property
    def secure_request_kwargs(self):
        return {"wsgi.url_scheme": "https"}


    def response(self, *args, **kwargs):
        headers = kwargs.pop("headers", {})
        response = HttpResponse(*args, **kwargs)
        for k, v in headers.items():
            response[k] = v
        return response


    def process_response(self, *args, **kwargs):
        request_kwargs = {}
        if kwargs.pop("secure", False):
            request_kwargs.update(self.secure_request_kwargs)
        request = (kwargs.pop("request", None) or
                   self.request.get("/some/url", **request_kwargs))
        ret = self.middleware.process_request(request)
        if ret:
            return ret
        return self.middleware.process_response(
            request, self.response(*args, **kwargs))


    request = RequestFactory()


    def process_request(self, method, *args, **kwargs):
        if kwargs.pop("secure", False):
            kwargs.update(self.secure_request_kwargs)
        req = getattr(self.request, method.lower())(*args, **kwargs)
        return self.middleware.process_request(req)


    @override_settings(SECURE_FRAME_DENY=True)
    def test_frame_deny_on(self):
        """
        With SECURE_FRAME_DENY True, the middleware adds "x-frame-options:
        DENY" to the response.

        """
        self.assertEqual(self.process_response()["x-frame-options"], "DENY")


    @override_settings(SECURE_FRAME_DENY=True)
    def test_frame_deny_already_present(self):
        """
        The middleware will not override an "x-frame-options" header already
        present in the response.

        """
        response = self.process_response(
            headers={"x-frame-options": "SAMEORIGIN"})
        self.assertEqual(response["x-frame-options"], "SAMEORIGIN")


    @override_settings(SECURE_FRAME_DENY=True)
    def test_frame_deny_exempt(self):
        """
        If the response has the _frame_deny_exempt attribute set to True, the
        middleware does not add an "x-frame-options" header to the response.

        """
        response = HttpResponse()
        response._frame_deny_exempt = True
        response = self.middleware.process_response("not used", response)
        self.assertFalse("x-frame-options" in response)


    @override_settings(SECURE_FRAME_DENY=False)
    def test_frame_deny_off(self):
        """
        With SECURE_FRAME_DENY False, the middleware does not add an
        "x-frame-options" header to the response.

        """
        self.assertFalse("x-frame-options" in self.process_response())


    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_on(self):
        """
        With SECURE_HSTS_SECONDS=3600, the middleware adds
        "strict-transport-security: max-age=3600" to the response.

        """
        self.assertEqual(
            self.process_response(secure=True)["strict-transport-security"],
            "max-age=3600")


    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_already_present(self):
        """
        The middleware will not override a "strict-transport-security" header
        already present in the response.

        """
        response = self.process_response(
            secure=True,
            headers={"strict-transport-security": "max-age=7200"})
        self.assertEqual(response["strict-transport-security"], "max-age=7200")


    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_sts_only_if_secure(self):
        """
        The "strict-transport-security" header is not added to responses going
        over an insecure connection.

        """
        self.assertFalse(
            "strict-transport-security" in self.process_response(secure=False))


    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_sts_off(self):
        """
        With SECURE_HSTS_SECONDS of 0, the middleware does not add a
        "strict-transport-security" header to the response.

        """
        self.assertFalse(
            "strict-transport-security" in self.process_response(secure=True))


    @override_settings(
        SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_sts_include_subdomains(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        True, the middleware adds a "strict-transport-security" header with the
        "includeSubDomains" tag to the response.

        """
        response = self.process_response(secure=True)
        self.assertEqual(
            response["strict-transport-security"],
            "max-age=600; includeSubDomains",
            )


    @override_settings(
        SECURE_HSTS_SECONDS=600, SECURE_HSTS_INCLUDE_SUBDOMAINS=False)
    def test_sts_no_include_subdomains(self):
        """
        With SECURE_HSTS_SECONDS non-zero and SECURE_HSTS_INCLUDE_SUBDOMAINS
        False, the middleware adds a "strict-transport-security" header without
        the "includeSubDomains" tag to the response.

        """
        response = self.process_response(secure=True)
        self.assertEqual(response["strict-transport-security"], "max-age=600")


    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_content_type_on(self):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF set to True, the middleware adds
        "x-content-type-options: nosniff" header to the response.

        """
        self.assertEqual(
            self.process_response()["x-content-type-options"],
            "nosniff")


    @override_settings(SECURE_CONTENT_TYPE_NO_SNIFF=True)
    def test_content_type_already_present(self):
        """
        The middleware will not override an "x-content-type-options" header
        already present in the response.

        """
        response = self.process_response(
            secure=True,
            headers={"x-content-type-options": "foo"})
        self.assertEqual(response["x-content-type-options"], "foo")


    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_content_type_off(self):
        """
        With SECURE_CONTENT_TYPE_NOSNIFF False, the middleware does not add an
        "x-content-type-options" header to the response.

        """
        self.assertFalse("x-content-type-options" in self.process_response())


    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_xss_filter_on(self):
        """
        With SECURE_BROWSER_XSS_FILTER set to True, the middleware adds
        "s-xss-protection: 1; mode=block" header to the response.

        """
        self.assertEqual(
            self.process_response()["x-xss-protection"],
            "1; mode=block")


    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_xss_filter_already_present(self):
        """
        The middleware will not override an "x-xss-protection" header
        already present in the response.

        """
        response = self.process_response(
            secure=True,
            headers={"x-xss-protection": "foo"})
        self.assertEqual(response["x-xss-protection"], "foo")


    @override_settings(SECURE_BROWSER_XSS_FILTER=False)
    def test_xss_filter_off(self):
        """
        With SECURE_BROWSER_XSS_FILTER set to False, the middleware does not add an
        "x-xss-protection" header to the response.

        """
        self.assertFalse("x-xss-protection" in self.process_response())


    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_ssl_redirect_on(self):
        """
        With SECURE_SSL_REDIRECT True, the middleware redirects any non-secure
        requests to the https:// version of the same URL.

        """
        ret = self.process_request("get", "/some/url?query=string")
        self.assertEqual(ret.status_code, 301)
        self.assertEqual(
            ret["Location"], "https://testserver/some/url?query=string")


    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_no_redirect_ssl(self):
        """
        The middleware does not redirect secure requests.

        """
        ret = self.process_request("get", "/some/url", secure=True)
        self.assertEqual(ret, None)


    @override_settings(
        SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=["^insecure/"])
    def test_redirect_exempt(self):
        """
        The middleware does not redirect requests with URL path matching an
        exempt pattern.

        """
        ret = self.process_request("get", "/insecure/page")
        self.assertEqual(ret, None)


    @override_settings(
        SECURE_SSL_REDIRECT=True, SECURE_SSL_HOST="secure.example.com")
    def test_redirect_ssl_host(self):
        """
        The middleware redirects to SECURE_SSL_HOST if given.

        """
        ret = self.process_request("get", "/some/url")
        self.assertEqual(ret.status_code, 301)
        self.assertEqual(ret["Location"], "https://secure.example.com/some/url")


    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_ssl_redirect_off(self):
        """
        With SECURE_SSL_REDIRECT False, the middleware does no redirect.

        """
        ret = self.process_request("get", "/some/url")
        self.assertEqual(ret, None)



class ProxySecurityMiddlewareTest(SecurityMiddlewareTest):
    """
    Test that SecurityMiddleware behaves the same even if our "secure request"
    indicator is a proxy header.

    """
    def setUp(self):
        self.override = override_settings(
            SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTOCOL", "https"))

        self.override.enable()


    def tearDown(self):
        self.override.disable()


    @property
    def secure_request_kwargs(self):
        return {"HTTP_X_FORWARDED_PROTOCOL": "https"}


    def test_is_secure(self):
        """
        SecurityMiddleware patches request.is_secure() to report ``True`` even
        with a proxy-header secure request.

        """
        request = self.request.get("/some/url", **self.secure_request_kwargs)
        self.middleware.process_request(request)

        self.assertEqual(request.is_secure(), True)




class FrameDenyExemptTest(TestCase):
    def test_adds_exempt_attr(self):
        """
        Test that the decorator adds a _frame_deny_exempt attribute to the
        response. (We test above in the middleware tests that this attribute
        causes the X-Frame-Options header to not be added.)

        """
        from djangosecure.decorators import frame_deny_exempt

        @frame_deny_exempt
        def myview(request):
            return HttpResponse()

        self.assertEqual(myview("not used")._frame_deny_exempt, True)



def fake_test():
    return set(["SOME_WARNING"])

fake_test.messages = {
    "SOME_WARNING": "This is the warning message."
    }

def nomsg_test():
    return set(["OTHER WARNING"])

def passing_test():
    return []


class RunChecksTest(TestCase):
    @property
    def func(self):
        from djangosecure.check import run_checks
        return run_checks


    @override_settings(
        SECURE_CHECKS=[
            "djangosecure.tests.fake_test",
            "djangosecure.tests.nomsg_test"])
    def test_returns_warnings(self):
        self.assertEqual(self.func(), set(["SOME_WARNING", "OTHER WARNING"]))



class CheckSettingsCommandTest(TestCase):
    def call(self, **options):
        stdout = options.setdefault("stdout", StringIO())
        stderr = options.setdefault("stderr", StringIO())

        call_command("checksecure", **options)

        stderr.seek(0)
        stdout.seek(0)

        return stdout.read(), stderr.read()


    @override_settings(SECURE_CHECKS=["djangosecure.tests.fake_test"])
    def test_prints_messages(self):
        stdout, stderr = self.call()
        self.assertTrue("This is the warning message." in stderr)


    @override_settings(SECURE_CHECKS=["djangosecure.tests.nomsg_test"])
    def test_prints_code_if_no_message(self):
        stdout, stderr = self.call()
        self.assertTrue("OTHER WARNING" in stderr)


    @override_settings(SECURE_CHECKS=["djangosecure.tests.fake_test"])
    def test_prints_code_if_verbosity_0(self):
        stdout, stderr = self.call(verbosity=0)
        self.assertTrue("SOME_WARNING" in stderr)


    @override_settings(SECURE_CHECKS=["djangosecure.tests.fake_test"])
    def test_prints_check_names(self):
        stdout, stderr = self.call()
        self.assertTrue("djangosecure.tests.fake_test" in stdout)


    @override_settings(SECURE_CHECKS=["djangosecure.tests.fake_test"])
    def test_no_verbosity(self):
        stdout, stderr = self.call(verbosity=0)
        self.assertEqual(stdout, "")


    @override_settings(SECURE_CHECKS=["djangosecure.tests.passing_test"])
    def test_all_clear(self):
        stdout, stderr = self.call()
        self.assertTrue("All clear!" in stdout)



class CheckSessionCookieSecureTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.sessions import check_session_cookie_secure
        return check_session_cookie_secure


    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[])
    def test_session_cookie_secure_with_installed_app(self):
        """
        Warns if SESSION_COOKIE_SECURE is off and "django.contrib.sessions" is
        in INSTALLED_APPS.

        """
        self.assertEqual(
            self.func(), set(["SESSION_COOKIE_NOT_SECURE_APP_INSTALLED"]))


    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=[],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_with_middleware(self):
        """
        Warns if SESSION_COOKIE_SECURE is off and
        "django.contrib.sessions.middleware.SessionMiddleware" is in
        MIDDLEWARE_CLASSES.

        """
        self.assertEqual(
            self.func(), set(["SESSION_COOKIE_NOT_SECURE_MIDDLEWARE"]))


    @override_settings(
        SESSION_COOKIE_SECURE=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_both(self):
        """
        If SESSION_COOKIE_SECURE is off and we find both the session app and
        the middleware, we just provide one common warning.

        """
        self.assertEqual(
            self.func(), set(["SESSION_COOKIE_NOT_SECURE"]))


    @override_settings(
        SESSION_COOKIE_SECURE=True,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_secure_true(self):
        """
        If SESSION_COOKIE_SECURE is on, there's no warning about it.

        """
        self.assertEqual(self.func(), set())



class CheckSessionCookieHttpOnlyTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.sessions import check_session_cookie_httponly
        return check_session_cookie_httponly


    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[])
    def test_session_cookie_httponly_with_installed_app(self):
        """
        Warns if SESSION_COOKIE_HTTPONLY is off and "django.contrib.sessions"
        is in INSTALLED_APPS.

        """
        self.assertEqual(
            self.func(), set(["SESSION_COOKIE_NOT_HTTPONLY_APP_INSTALLED"]))


    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=[],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_with_middleware(self):
        """
        Warns if SESSION_COOKIE_HTTPONLY is off and
        "django.contrib.sessions.middleware.SessionMiddleware" is in
        MIDDLEWARE_CLASSES.

        """
        self.assertEqual(
            self.func(), set(["SESSION_COOKIE_NOT_HTTPONLY_MIDDLEWARE"]))


    @override_settings(
        SESSION_COOKIE_HTTPONLY=False,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_both(self):
        """
        If SESSION_COOKIE_HTTPONLY is off and we find both the session app and
        the middleware, we just provide one common warning.

        """
        self.assertTrue(
            self.func(), set(["SESSION_COOKIE_NOT_HTTPONLY"]))


    @override_settings(
        SESSION_COOKIE_HTTPONLY=True,
        INSTALLED_APPS=["django.contrib.sessions"],
        MIDDLEWARE_CLASSES=[
            "django.contrib.sessions.middleware.SessionMiddleware"])
    def test_session_cookie_httponly_true(self):
        """
        If SESSION_COOKIE_HTTPONLY is on, there's no warning about it.

        """
        self.assertEqual(self.func(), set())



class CheckCSRFMiddlewareTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.csrf import check_csrf_middleware
        return check_csrf_middleware


    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_no_csrf_middleware(self):
        self.assertEqual(
            self.func(), set(["CSRF_VIEW_MIDDLEWARE_NOT_INSTALLED"]))


    @override_settings(
        MIDDLEWARE_CLASSES=["django.middleware.csrf.CsrfViewMiddleware"])
    def test_with_csrf_middleware(self):
        self.assertEqual(self.func(), set())



class CheckSecurityMiddlewareTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.djangosecure import check_security_middleware
        return check_security_middleware


    @override_settings(MIDDLEWARE_CLASSES=[])
    def test_no_security_middleware(self):
        self.assertEqual(
            self.func(), set(["SECURITY_MIDDLEWARE_NOT_INSTALLED"]))


    @override_settings(
        MIDDLEWARE_CLASSES=["djangosecure.middleware.SecurityMiddleware"])
    def test_with_security_middleware(self):
        self.assertEqual(self.func(), set())



class CheckStrictTransportSecurityTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.djangosecure import check_sts
        return check_sts


    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_no_sts(self):
        self.assertEqual(
            self.func(), set(["STRICT_TRANSPORT_SECURITY_NOT_ENABLED"]))


    @override_settings(SECURE_HSTS_SECONDS=3600)
    def test_with_sts(self):
        self.assertEqual(self.func(), set())



class CheckStrictTransportSecuritySubdomainsTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.djangosecure import check_sts_include_subdomains
        return check_sts_include_subdomains


    @override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=False)
    def test_no_sts_subdomains(self):
        self.assertEqual(
            self.func(), set(["STRICT_TRANSPORT_SECURITY_NO_SUBDOMAINS"]))


    @override_settings(SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
    def test_with_sts_subdomains(self):
        self.assertEqual(self.func(), set())



class CheckFrameDenyTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.djangosecure import check_frame_deny
        return check_frame_deny


    @override_settings(SECURE_FRAME_DENY=False)
    def test_no_frame_deny(self):
        self.assertEqual(
            self.func(), set(["FRAME_DENY_NOT_ENABLED"]))


    @override_settings(SECURE_FRAME_DENY=True)
    def test_with_frame_deny(self):
        self.assertEqual(self.func(), set())



class CheckContentTypeNosniffTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.djangosecure import check_content_type_nosniff
        return check_content_type_nosniff


    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=False)
    def test_no_content_type_nosniff(self):
        self.assertEqual(
            self.func(), set(["CONTENT_TYPE_NOSNIFF_NOT_ENABLED"]))


    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_with_content_type_nosniff(self):
        self.assertEqual(self.func(), set())



class CheckXssFilterTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.djangosecure import check_xss_filter
        return check_xss_filter


    @override_settings(SECURE_BROWSER_XSS_FILTER=False)
    def test_no_xss_filter(self):
        self.assertEqual(
            self.func(), set(["BROWSER_XSS_FILTER_NOT_ENABLED"]))


    @override_settings(SECURE_BROWSER_XSS_FILTER=True)
    def test_with_xss_filter(self):
        self.assertEqual(self.func(), set())



class CheckSSLRedirectTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.djangosecure import check_ssl_redirect
        return check_ssl_redirect


    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_no_sts(self):
        self.assertEqual(
            self.func(), set(["SSL_REDIRECT_NOT_ENABLED"]))


    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_with_sts(self):
        self.assertEqual(self.func(), set())


class CheckSecretKeyTest(TestCase):
    @property
    def func(self):
        from djangosecure.check.djangosecure import check_secret_key
        return check_secret_key


    @override_settings(SECRET_KEY='awcetupav$#!^h9wTUAPCJWE&!T#``Ho;ta9w4tva')
    def test_okay_secret_key(self):
        self.assertEqual(self.func(), set())


    @override_settings(SECRET_KEY='')
    def test_empty_secret_key(self):
        self.assertEqual(self.func(), set(['BAD_SECRET_KEY']))


    @override_settings(SECRET_KEY=None)
    def test_missing_secret_key(self):
        del settings.SECRET_KEY
        self.assertEqual(self.func(), set(['BAD_SECRET_KEY']))


    @override_settings(SECRET_KEY=None)
    def test_none_secret_key(self):
        self.assertEqual(self.func(), set(['BAD_SECRET_KEY']))


    @override_settings(SECRET_KEY='bla bla')
    def test_low_entropy_secret_key(self):
        self.assertEqual(self.func(), set(['BAD_SECRET_KEY']))



class ConfTest(TestCase):
    def test_no_fallback(self):
        """
        Accessing a setting without a default value raises in
        ImproperlyConfigured.

        """
        from djangosecure.conf import conf

        self.assertRaises(ImproperlyConfigured, getattr, conf, "HAS_NO_DEFAULT")


    def test_defaults(self):
        from djangosecure.conf import conf

        self.assertEqual(
            conf.defaults,
            {
                "SECURE_CHECKS":[
                    "djangosecure.check.csrf.check_csrf_middleware",
                    "djangosecure.check.sessions.check_session_cookie_secure",
                    "djangosecure.check.sessions.check_session_cookie_httponly",
                    "djangosecure.check.djangosecure.check_security_middleware",
                    "djangosecure.check.djangosecure.check_sts",
                    "djangosecure.check.djangosecure.check_sts_include_subdomains",
                    "djangosecure.check.djangosecure.check_frame_deny",
                    "djangosecure.check.djangosecure.check_content_type_nosniff",
                    "djangosecure.check.djangosecure.check_xss_filter",
                    "djangosecure.check.djangosecure.check_ssl_redirect",
                    "djangosecure.check.djangosecure.check_secret_key",
                    ],
                "SECURE_HSTS_SECONDS": 0,
                "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
                "SECURE_FRAME_DENY": False,
                "SECURE_CONTENT_TYPE_NOSNIFF": False,
                "SECURE_BROWSER_XSS_FILTER": False,
                "SECURE_SSL_REDIRECT": False,
                "SECURE_SSL_HOST": None,
                "SECURE_REDIRECT_EXEMPT": [],
                "SECURE_PROXY_SSL_HEADER": None,
                }
            )

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-secure documentation build configuration file, created by
# sphinx-quickstart on Sun May 29 22:59:46 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-secure'
copyright = u'2011, Carl Meyer and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

from os.path import join, dirname
def get_version():
    fh = open(join(dirname(dirname(__file__)), "djangosecure", "__init__.py"))
    try:
        for line in fh.readlines():
            if line.startswith("__version__ ="):
                return line.split("=")[1].strip().strip('"')
    finally:
        fh.close()

# The full version, including alpha/beta/rc tags.
release = get_version()

# The short X.Y version.
version = ".".join(release.split(".")[:2])

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-securedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-secure.tex', u'django-secure Documentation',
   u'Carl Meyer and contributors', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-secure', u'django-secure Documentation',
     [u'Carl Meyer and contributors'], 1)
]

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import os, sys

from django.conf import settings


if not settings.configured:
    settings.configure(
        INSTALLED_APPS=["djangosecure"],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}})


def runtests(*test_args):
    if not test_args:
        test_args = ["djangosecure"]

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    try:
        from django.test.simple import DjangoTestSuiteRunner
        def run_tests(test_args, verbosity, interactive):
            runner = DjangoTestSuiteRunner(
                verbosity=verbosity, interactive=interactive, failfast=False)
            return runner.run_tests(test_args)
    except ImportError:
        # for Django versions that don't have DjangoTestSuiteRunner
        from django.test.simple import run_tests
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests()

########NEW FILE########
