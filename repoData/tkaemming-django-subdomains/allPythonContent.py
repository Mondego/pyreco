__FILENAME__ = conf
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from subdomains import __version__

import django
from django.conf import settings

if not settings.configured:
    settings.configure()


extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
exclude_patterns = ['_build']

project = u'django-subdomains'
copyright = u'2012, ted kaemming'
version = release = '.'.join(map(str, __version__))

html_static_path = ['_static']
htmlhelp_basename = 'django-subdomainsdoc'

latex_elements = {}
latex_documents = [
  ('index', 'django-subdomains.tex', u'django-subdomains Documentation',
   u'ted kaemming', 'manual'),
]

man_pages = [
    ('index', 'django-subdomains', u'django-subdomains Documentation',
     [u'ted kaemming'], 1)
]

texinfo_documents = [
  ('index', 'django-subdomains', u'django-subdomains Documentation',
   u'ted kaemming', 'django-subdomains', 'One line description of project.',
   'Miscellaneous'),
]

intersphinx_mapping = {
    'python': ('http://docs.python.org/release/%s.%s' % sys.version_info[:2], None),
    'django': ('http://docs.djangoproject.com/en/%s.%s/' % django.VERSION[:2],
        'http://docs.djangoproject.com/en/%s.%s/_objects/' % django.VERSION[:2]),
}

autodoc_member_order = 'bysource'
autodoc_default_flags = ('members',)

########NEW FILE########
__FILENAME__ = requestfactory
"""
Backport of `django.test.client.RequestFactory` from Django 1.3 and above.
"""
import urllib
from cStringIO import StringIO
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import SimpleCookie
from django.utils.encoding import smart_str
from django.utils.http import urlencode
from django.test.client import (BOUNDARY, MULTIPART_CONTENT, CONTENT_TYPE_RE,
    FakePayload, encode_multipart)


class RequestFactory(object):
    """
    Class that lets you create mock Request objects for use in testing.

    Usage:

    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})

    Once you have a request object you can pass it to any view function,
    just as if that view had been hooked up using a URLconf.
    """
    def __init__(self, **defaults):
        self.defaults = defaults
        self.cookies = SimpleCookie()
        self.errors = StringIO()

    def _base_environ(self, **request):
        """
        The base environment for a request.
        """
        environ = {
            'HTTP_COOKIE':       self.cookies.output(header='', sep='; '),
            'PATH_INFO':         '/',
            'QUERY_STRING':      '',
            'REMOTE_ADDR':       '127.0.0.1',
            'REQUEST_METHOD':    'GET',
            'SCRIPT_NAME':       '',
            'SERVER_NAME':       'testserver',
            'SERVER_PORT':       '80',
            'SERVER_PROTOCOL':   'HTTP/1.1',
            'wsgi.version':      (1, 0),
            'wsgi.url_scheme':   'http',
            'wsgi.errors':       self.errors,
            'wsgi.multiprocess': True,
            'wsgi.multithread':  False,
            'wsgi.run_once':     False,
        }
        environ.update(self.defaults)
        environ.update(request)
        return environ

    def request(self, **request):
        "Construct a generic request object."
        return WSGIRequest(self._base_environ(**request))

    def _get_path(self, parsed):
        # If there are parameters, add them
        if parsed[3]:
            return urllib.unquote(parsed[2] + ";" + parsed[3])
        else:
            return urllib.unquote(parsed[2])

    def get(self, path, data={}, **extra):
        "Construct a GET request"

        parsed = urlparse(path)
        r = {
            'CONTENT_TYPE':    'text/html; charset=utf-8',
            'PATH_INFO':       self._get_path(parsed),
            'QUERY_STRING':    urlencode(data, doseq=True) or parsed[4],
            'REQUEST_METHOD': 'GET',
            'wsgi.input':      FakePayload('')
        }
        r.update(extra)
        return self.request(**r)

    def post(self, path, data={}, content_type=MULTIPART_CONTENT,
             **extra):
        "Construct a POST request."

        if content_type is MULTIPART_CONTENT:
            post_data = encode_multipart(BOUNDARY, data)
        else:
            # Encode the content so that the byte representation is correct.
            match = CONTENT_TYPE_RE.match(content_type)
            if match:
                charset = match.group(1)
            else:
                charset = settings.DEFAULT_CHARSET
            post_data = smart_str(data, encoding=charset)

        parsed = urlparse(path)
        r = {
            'CONTENT_LENGTH': len(post_data),
            'CONTENT_TYPE':   content_type,
            'PATH_INFO':      self._get_path(parsed),
            'QUERY_STRING':   parsed[4],
            'REQUEST_METHOD': 'POST',
            'wsgi.input':     FakePayload(post_data),
        }
        r.update(extra)
        return self.request(**r)

    def head(self, path, data={}, **extra):
        "Construct a HEAD request."

        parsed = urlparse(path)
        r = {
            'CONTENT_TYPE':    'text/html; charset=utf-8',
            'PATH_INFO':       self._get_path(parsed),
            'QUERY_STRING':    urlencode(data, doseq=True) or parsed[4],
            'REQUEST_METHOD': 'HEAD',
            'wsgi.input':      FakePayload('')
        }
        r.update(extra)
        return self.request(**r)

    def options(self, path, data={}, **extra):
        "Constrict an OPTIONS request"

        parsed = urlparse(path)
        r = {
            'PATH_INFO':       self._get_path(parsed),
            'QUERY_STRING':    urlencode(data, doseq=True) or parsed[4],
            'REQUEST_METHOD': 'OPTIONS',
            'wsgi.input':      FakePayload('')
        }
        r.update(extra)
        return self.request(**r)

    def put(self, path, data={}, content_type=MULTIPART_CONTENT,
            **extra):
        "Construct a PUT request."

        if content_type is MULTIPART_CONTENT:
            post_data = encode_multipart(BOUNDARY, data)
        else:
            post_data = data

        # Make `data` into a querystring only if it's not already a string. If
        # it is a string, we'll assume that the caller has already encoded it.
        query_string = None
        if not isinstance(data, basestring):
            query_string = urlencode(data, doseq=True)

        parsed = urlparse(path)
        r = {
            'CONTENT_LENGTH': len(post_data),
            'CONTENT_TYPE':   content_type,
            'PATH_INFO':      self._get_path(parsed),
            'QUERY_STRING':   query_string or parsed[4],
            'REQUEST_METHOD': 'PUT',
            'wsgi.input':     FakePayload(post_data),
        }
        r.update(extra)
        return self.request(**r)

    def delete(self, path, data={}, **extra):
        "Construct a DELETE request."

        parsed = urlparse(path)
        r = {
            'PATH_INFO':       self._get_path(parsed),
            'QUERY_STRING':    urlencode(data, doseq=True) or parsed[4],
            'REQUEST_METHOD': 'DELETE',
            'wsgi.input':      FakePayload('')
        }
        r.update(extra)
        return self.request(**r)

########NEW FILE########
__FILENAME__ = template
# flake8: noqa
"""
Backport of `django.template.Library.simple_tag` from Django 1.4, as well as
it's dependencies.
"""
import re
import functools
from inspect import getargspec

from django.template import Node, TemplateSyntaxError

kwarg_re = re.compile(r"(?:(\w+)=)?(.+)")


class TagHelperNode(Node):
    """
    Base class for tag helper nodes such as SimpleNode, InclusionNode and
    AssignmentNode. Manages the positional and keyword arguments to be passed
    to the decorated function.
    """
    def __init__(self, takes_context, args, kwargs):
        self.takes_context = takes_context
        self.args = args
        self.kwargs = kwargs

    def get_resolved_arguments(self, context):
        resolved_args = [var.resolve(context) for var in self.args]
        if self.takes_context:
            resolved_args = [context] + resolved_args
        resolved_kwargs = dict((k, v.resolve(context))
            for k, v in self.kwargs.items())
        return resolved_args, resolved_kwargs


def generic_tag_compiler(parser, token, params, varargs, varkw, defaults,
        name, takes_context, node_class):
    """
    Returns a template.Node subclass.
    """
    bits = token.split_contents()[1:]
    args, kwargs = parse_bits(parser, bits, params, varargs, varkw, defaults,
        takes_context, name)
    return node_class(takes_context, args, kwargs)


def simple_tag(register, function=None, takes_context=None, name=None):
    make_simple_tag = register.simple_tag

    def make_simple_tag(function):
        params, varargs, varkw, defaults = getargspec(function)

        class SimpleNode(TagHelperNode):
            def render(self, context):
                resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
                return function(*resolved_args, **resolved_kwargs)

        function_name = (name or getattr(function, '_decorated_function', function).__name__)
        compiled_tag = functools.partial(generic_tag_compiler,
            params=params, varargs=varargs, varkw=varkw,
            defaults=defaults, name=function_name,
            takes_context=takes_context, node_class=SimpleNode)
        compiled_tag.__doc__ = compiled_tag.__doc__
        register.tag(function_name, compiled_tag)
        return function

    if function is None:
        # @register.simple_tag(...)
        return make_simple_tag
    elif callable(function):
        # @register.simple_tag
        return make_simple_tag(function)

    return make_simple_tag


def parse_bits(parser, bits, params, varargs, varkw, defaults,
               takes_context, name):
    """
    Parses bits for template tag helpers (simple_tag, include_tag and
    assignment_tag), in particular by detecting syntax errors and by
    extracting positional and keyword arguments.
    """
    if takes_context:
        if params[0] == 'context':
            params = params[1:]
        else:
            raise TemplateSyntaxError(
                "'%s' is decorated with takes_context=True so it must "
                "have a first argument of 'context'" % name)
    args = []
    kwargs = {}
    unhandled_params = list(params)
    for bit in bits:
        # First we try to extract a potential kwarg from the bit
        kwarg = token_kwargs([bit], parser)
        if kwarg:
            # The kwarg was successfully extracted
            param, value = kwarg.items()[0]
            if param not in params and varkw is None:
                # An unexpected keyword argument was supplied
                raise TemplateSyntaxError(
                    "'%s' received unexpected keyword argument '%s'" %
                    (name, param))
            elif param in kwargs:
                # The keyword argument has already been supplied once
                raise TemplateSyntaxError(
                    "'%s' received multiple values for keyword argument '%s'" %
                    (name, param))
            else:
                # All good, record the keyword argument
                kwargs[str(param)] = value
                if param in unhandled_params:
                    # If using the keyword syntax for a positional arg, then
                    # consume it.
                    unhandled_params.remove(param)
        else:
            if kwargs:
                raise TemplateSyntaxError(
                    "'%s' received some positional argument(s) after some "
                    "keyword argument(s)" % name)
            else:
                # Record the positional argument
                args.append(parser.compile_filter(bit))
                try:
                    # Consume from the list of expected positional arguments
                    unhandled_params.pop(0)
                except IndexError:
                    if varargs is None:
                        raise TemplateSyntaxError(
                            "'%s' received too many positional arguments" %
                            name)
    if defaults is not None:
        # Consider the last n params handled, where n is the
        # number of defaults.
        unhandled_params = unhandled_params[:-len(defaults)]
    if unhandled_params:
        # Some positional arguments were not supplied
        raise TemplateSyntaxError(
            u"'%s' did not receive value(s) for the argument(s): %s" %
            (name, u", ".join([u"'%s'" % p for p in unhandled_params])))
    return args, kwargs


def token_kwargs(bits, parser, support_legacy=False):
    """
    A utility method for parsing token keyword arguments.

    :param bits: A list containing remainder of the token (split by spaces)
        that is to be checked for arguments. Valid arguments will be removed
        from this list.

    :param support_legacy: If set to true ``True``, the legacy format
        ``1 as foo`` will be accepted. Otherwise, only the standard ``foo=1``
        format is allowed.

    :returns: A dictionary of the arguments retrieved from the ``bits`` token
        list.

    There is no requirement for all remaining token ``bits`` to be keyword
    arguments, so the dictionary will be returned as soon as an invalid
    argument format is reached.
    """
    if not bits:
        return {}
    match = kwarg_re.match(bits[0])
    kwarg_format = match and match.group(1)
    if not kwarg_format:
        if not support_legacy:
            return {}
        if len(bits) < 3 or bits[1] != 'as':
            return {}

    kwargs = {}
    while bits:
        if kwarg_format:
            match = kwarg_re.match(bits[0])
            if not match or not match.group(1):
                return kwargs
            key, value = match.groups()
            del bits[:1]
        else:
            if len(bits) < 3 or bits[1] != 'as':
                return kwargs
            key, value = bits[2], bits[0]
            del bits[:3]
        kwargs[key] = parser.compile_filter(value)
        if bits and not kwarg_format:
            if bits[0] != 'and':
                return kwargs
            del bits[:1]
    return kwargs

########NEW FILE########
__FILENAME__ = tests
# flake8: noqa
"""
Backport of `django.test.utils.override_settings` from Django 1.3 and above.
"""
from functools import wraps

from django.conf import settings, UserSettingsHolder



class override_settings(object):
    """
    Acts as either a decorator, or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement. In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """
    def __init__(self, **kwargs):
        self.options = kwargs
        self.wrapped = settings._wrapped

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from django.test import TransactionTestCase
        if isinstance(test_func, type) and issubclass(test_func, TransactionTestCase):
            original_pre_setup = test_func._pre_setup
            original_post_teardown = test_func._post_teardown

            def _pre_setup(innerself):
                self.enable()
                original_pre_setup(innerself)
            def _post_teardown(innerself):
                original_post_teardown(innerself)
                self.disable()
            test_func._pre_setup = _pre_setup
            test_func._post_teardown = _post_teardown
            return test_func
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
        return inner

    def enable(self):
        override = UserSettingsHolder(settings._wrapped)
        for key, new_value in self.options.items():
            setattr(override, key, new_value)
        settings._wrapped = override
        # for key, new_value in self.options.items():
        #     setting_changed.send(sender=settings._wrapped.__class__,
        #                          setting=key, value=new_value)

    def disable(self):
        settings._wrapped = self.wrapped
        for key in self.options:
            new_value = getattr(settings, key, None)
            # setting_changed.send(sender=settings._wrapped.__class__,
            #                      setting=key, value=new_value)

########NEW FILE########
__FILENAME__ = middleware
import operator
import logging
import re

from django.conf import settings
from django.utils.cache import patch_vary_headers

from subdomains.utils import get_domain


logger = logging.getLogger(__name__)
lower = operator.methodcaller('lower')

UNSET = object()


class SubdomainMiddleware(object):
    """
    A middleware class that adds a ``subdomain`` attribute to the current request.
    """
    def get_domain_for_request(self, request):
        """
        Returns the domain that will be used to identify the subdomain part
        for this request.
        """
        return get_domain()

    def process_request(self, request):
        """
        Adds a ``subdomain`` attribute to the ``request`` parameter.
        """
        domain, host = map(lower,
            (self.get_domain_for_request(request), request.get_host()))

        pattern = r'^(?:(?P<subdomain>.*?)\.)?%s(?::.*)?$' % re.escape(domain)
        matches = re.match(pattern, host)

        if matches:
            request.subdomain = matches.group('subdomain')
        else:
            request.subdomain = None
            logger.warning('The host %s does not belong to the domain %s, '
                'unable to identify the subdomain for this request',
                request.get_host(), domain)


class SubdomainURLRoutingMiddleware(SubdomainMiddleware):
    """
    A middleware class that allows for subdomain-based URL routing.
    """
    def process_request(self, request):
        """
        Sets the current request's ``urlconf`` attribute to the urlconf
        associated with the subdomain, if it is listed in
        ``settings.SUBDOMAIN_URLCONFS``.
        """
        super(SubdomainURLRoutingMiddleware, self).process_request(request)

        subdomain = getattr(request, 'subdomain', UNSET)

        if subdomain is not UNSET:
            urlconf = settings.SUBDOMAIN_URLCONFS.get(subdomain)
            if urlconf is not None:
                logger.debug("Using urlconf %s for subdomain: %s",
                    repr(urlconf), repr(subdomain))
                request.urlconf = urlconf

    def process_response(self, request, response):
        """
        Forces the HTTP ``Vary`` header onto requests to avoid having responses
        cached across subdomains.
        """
        if getattr(settings, 'FORCE_VARY_ON_HOST', True):
            patch_vary_headers(response, ('Host',))

        return response

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = subdomainurls
from django.template import Library

from subdomains.compat.template import simple_tag
from subdomains.utils import reverse


register = Library()

UNSET = object()


@simple_tag(register, takes_context=True)
def url(context, view, subdomain=UNSET, *args, **kwargs):
    """
    Resolves a URL in a template, using subdomain-based URL resolution.

    If no subdomain is provided and a ``request`` is in the template context
    when rendering, the URL will be resolved relative to the current request's
    subdomain. If no ``request`` is provided, the URL will be resolved relative
    to current domain with the ``settings.ROOT_URLCONF``.

    Usage::

        {% load subdomainurls %}
        {% url 'view-name' subdomain='subdomain' %}

    .. note:: This tag uses the variable URL syntax introduced in Django
       1.3 as ``{% load url from future %}`` and was made the standard in Django
       1.5. If you are upgrading a legacy application from one of the previous
       template tag formats, make sure to quote your constant string URL names
       to avoid :exc:`~django.core.urlresolver.NoReverseMatch` errors during
       template rendering.

    """
    if subdomain is UNSET:
        request = context.get('request')
        if request is not None:
            subdomain = getattr(request, 'subdomain', None)
        else:
            subdomain = None
    elif subdomain is '':
        subdomain = None

    return reverse(view, subdomain=subdomain, args=args, kwargs=kwargs)

########NEW FILE########
__FILENAME__ = tests
import mock
import warnings

from django.contrib.sites.models import Site
from django.core.urlresolvers import NoReverseMatch, set_urlconf
from django.test import TestCase
from django.template import Context, Template

try:
    from django.test.client import RequestFactory
except ImportError:
    from subdomains.compat.requestfactory import RequestFactory  # noqa

try:
    from django.test.utils import override_settings
except ImportError:
    from subdomains.compat.tests import override_settings  # noqa

from subdomains.middleware import (SubdomainMiddleware,
    SubdomainURLRoutingMiddleware)
from subdomains.utils import reverse, urljoin


def prefix_values(dictionary, prefix):
    return dict((key, '%s.%s' % (prefix, value))
        for key, value in dictionary.iteritems())


class SubdomainTestMixin(object):
    DOMAIN = 'example.com'
    URL_MODULE_PATH = 'subdomains.tests.urls'

    def setUp(self):
        super(SubdomainTestMixin, self).setUp()
        self.site = Site.objects.get_current()
        self.site.domain = self.DOMAIN
        self.site.save()

    @override_settings(
        DEFAULT_URL_SCHEME='http',
        ROOT_URLCONF='%s.application' % URL_MODULE_PATH,
        SUBDOMAIN_URLCONFS=prefix_values({
            None: 'marketing',
            'api': 'api',
            'www': 'marketing',
        }, prefix=URL_MODULE_PATH),
        MIDDLEWARE_CLASSES=(
            'django.middleware.common.CommonMiddleware',
            'subdomains.middleware.SubdomainURLRoutingMiddleware',
        ))
    def run(self, *args, **kwargs):
        super(SubdomainTestMixin, self).run(*args, **kwargs)

    def get_path_to_urlconf(self, name):
        """
        Returns the full path to the given urlconf.
        """
        return '.'.join((self.URL_MODULE_PATH, name))

    def get_host_for_subdomain(self, subdomain=None):
        """
        Returns the hostname for the provided subdomain.
        """
        if subdomain is not None:
            host = '%s.%s' % (subdomain, self.site.domain)
        else:
            host = '%s' % self.site.domain
        return host


class SubdomainMiddlewareTestCase(SubdomainTestMixin, TestCase):
    def setUp(self):
        super(SubdomainMiddlewareTestCase, self).setUp()
        self.middleware = SubdomainMiddleware()

    def test_subdomain_attribute(self):
        def subdomain(subdomain):
            """
            Returns the subdomain associated with the request by the middleware
            for the given subdomain.
            """
            host = self.get_host_for_subdomain(subdomain)
            request = RequestFactory().get('/', HTTP_HOST=host)
            self.middleware.process_request(request)
            return request.subdomain

        self.assertEqual(subdomain(None), None)
        self.assertEqual(subdomain('www'), 'www')
        self.assertEqual(subdomain('www.subdomain'), 'www.subdomain')
        self.assertEqual(subdomain('subdomain'), 'subdomain')
        self.assertEqual(subdomain('another.subdomain'), 'another.subdomain')

    def test_www_domain(self):
        def host(host):
            """
            Returns the subdomain for the provided HTTP Host.
            """
            request = RequestFactory().get('/', HTTP_HOST=host)
            self.middleware.process_request(request)
            return request.subdomain

        self.site.domain = 'www.%s' % self.DOMAIN
        self.site.save()

        with override_settings(REMOVE_WWW_FROM_DOMAIN=False):
            self.assertEqual(host('www.%s' % self.DOMAIN), None)

            # Squelch the subdomain warning for cleaner test output, since we
            # already know that this is an invalid subdomain.
            with warnings.catch_warnings(record=True) as warnlist:
                self.assertEqual(host('www.subdomain.%s' % self.DOMAIN), None)
                self.assertEqual(host('subdomain.%s' % self.DOMAIN), None)

            # Trick pyflakes into not warning us about variable usage.
            del warnlist

            self.assertEqual(host('subdomain.www.%s' % self.DOMAIN),
                'subdomain')
            self.assertEqual(host('www.subdomain.www.%s' % self.DOMAIN),
                'www.subdomain')

        with override_settings(REMOVE_WWW_FROM_DOMAIN=True):
            self.assertEqual(host('www.%s' % self.DOMAIN), 'www')
            self.assertEqual(host('subdomain.%s' % self.DOMAIN), 'subdomain')
            self.assertEqual(host('subdomain.www.%s' % self.DOMAIN),
                'subdomain.www')

    def test_case_insensitive_subdomain(self):
        host = 'WWW.%s' % self.DOMAIN
        request = RequestFactory().get('/', HTTP_HOST=host)
        self.middleware.process_request(request)
        self.assertEqual(request.subdomain, 'www')

        host = 'www.%s' % self.DOMAIN.upper()
        request = RequestFactory().get('/', HTTP_HOST=host)
        self.middleware.process_request(request)
        self.assertEqual(request.subdomain, 'www')


class SubdomainURLRoutingTestCase(SubdomainTestMixin, TestCase):
    def setUp(self):
        super(SubdomainURLRoutingTestCase, self).setUp()
        self.middleware = SubdomainURLRoutingMiddleware()

    def test_url_routing(self):
        def urlconf(subdomain):
            """
            Returns the URLconf associated with this request.
            """
            host = self.get_host_for_subdomain(subdomain)
            request = RequestFactory().get('/', HTTP_HOST=host)
            self.middleware.process_request(request)
            return getattr(request, 'urlconf', None)

        self.assertEqual(urlconf(None), self.get_path_to_urlconf('marketing'))
        self.assertEqual(urlconf('www'), self.get_path_to_urlconf('marketing'))
        self.assertEqual(urlconf('api'), self.get_path_to_urlconf('api'))

        # Falls through to the actual ROOT_URLCONF.
        self.assertEqual(urlconf('subdomain'), None)

    def test_appends_slash(self):
        for subdomain in (None, 'api', 'wildcard'):
            host = self.get_host_for_subdomain(subdomain)
            response = self.client.get('/example', HTTP_HOST=host)
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response['Location'], 'http://%s/example/' % host)


class SubdomainURLReverseTestCase(SubdomainTestMixin, TestCase):
    def test_url_join(self):
        self.assertEqual(urljoin(self.DOMAIN), 'http://%s' % self.DOMAIN)
        self.assertEqual(urljoin(self.DOMAIN, scheme='https'),
            'https://%s' % self.DOMAIN)

        with override_settings(DEFAULT_URL_SCHEME='https'):
            self.assertEqual(urljoin(self.DOMAIN), 'https://%s' % self.DOMAIN)

        self.assertEqual(urljoin(self.DOMAIN, path='/example/'),
            'http://%s/example/' % self.DOMAIN)

    def test_implicit_reverse(self):
        # Uses settings.SUBDOMAIN_URLCONFS[None], if it exists.
        # Otherwise would perform the same behavior as `test_wildcard_reverse`.
        self.assertEqual(reverse('home'), 'http://%s/' % self.DOMAIN)

    def test_explicit_reverse(self):
        # Uses explicitly provided settings.SUBDOMAIN_URLCONF[subdomain]
        self.assertEqual(reverse('home', subdomain='api'),
            'http://api.%s/' % self.DOMAIN)
        self.assertEqual(reverse('view', subdomain='api'),
            'http://api.%s/view/' % self.DOMAIN)

    def test_wildcard_reverse(self):
        # Falls through to settings.ROOT_URLCONF
        subdomain = 'wildcard'
        self.assertEqual(reverse('home', subdomain),
            'http://%s.%s/' % (subdomain, self.DOMAIN))
        self.assertEqual(reverse('view', subdomain),
            'http://%s.%s/view/' % (subdomain, self.DOMAIN))

    def test_reverse_subdomain_mismatch(self):
        self.assertRaises(NoReverseMatch, lambda: reverse('view'))

    def test_reverse_invalid_urlconf_argument(self):
        self.assertRaises(TypeError,
            lambda: reverse('home',
                urlconf=self.get_path_to_urlconf('marketing')))

    def test_using_not_default_urlconf(self):
        # Ensure that changing the currently active URLconf to something other
        # than the default still resolves wildcard subdomains correctly.
        set_urlconf(self.get_path_to_urlconf('api'))

        subdomain = 'wildcard'

        # This will raise NoReverseMatch if we're using the wrong URLconf for
        # the provided subdomain.
        self.assertEqual(reverse('application', subdomain=subdomain),
            'http://%s.%s/application/' % (subdomain, self.DOMAIN))


class SubdomainTemplateTagTestCase(SubdomainTestMixin, TestCase):
    def make_template(self, template):
        return Template('{% load subdomainurls %}' + template)

    def test_without_subdomain(self):
        defaults = {'view': 'home'}
        template = self.make_template('{% url view %}')

        context = Context(defaults)
        rendered = template.render(context).strip()
        self.assertEqual(rendered, 'http://%s/' % self.DOMAIN)

    def test_with_subdomain(self):
        defaults = {'view': 'home'}
        template = self.make_template('{% url view subdomain=subdomain %}')

        for subdomain in ('www', 'api', 'wildcard'):
            context = Context(dict(defaults, subdomain=subdomain))
            rendered = template.render(context).strip()
            self.assertEqual(rendered,
                'http://%s.%s/' % (subdomain, self.DOMAIN))

    def test_no_reverse(self):
        template = self.make_template('{% url view subdomain=subdomain %}')

        context = Context({'view': '__invalid__'})
        self.assertRaises(NoReverseMatch, lambda: template.render(context))

    def test_implied_subdomain_from_request(self):
        template = self.make_template('{% url view %}')
        defaults = {'view': 'home'}

        request = mock.Mock()
        request.subdomain = None

        context = Context(dict(defaults, request=request))
        rendered = template.render(context).strip()
        self.assertEqual(rendered, 'http://%s/' % self.DOMAIN)

        for subdomain in ('www', 'api', 'wildcard'):
            request = mock.Mock()
            request.subdomain = subdomain

            context = Context(dict(defaults, request=request))
            rendered = template.render(context).strip()
            self.assertEqual(rendered,
                'http://%s.%s/' % (subdomain, self.DOMAIN))

########NEW FILE########
__FILENAME__ = api
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url  # noqa

from subdomains.tests.urls.default import urlpatterns as default_patterns
from subdomains.tests.views import view


urlpatterns = default_patterns + patterns('',
    url(regex=r'^$', view=view, name='home'),
    url(regex=r'^view/$', view=view, name='view'),
)

########NEW FILE########
__FILENAME__ = application
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url  # noqa

from subdomains.tests.urls.default import urlpatterns as default_patterns
from subdomains.tests.views import view


urlpatterns = default_patterns + patterns('',
    url(regex=r'^view/$', view=view, name='view'),
    url(regex=r'^application/$', view=view, name='application'),
)

########NEW FILE########
__FILENAME__ = default
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url  # noqa

from subdomains.tests.views import view


urlpatterns = patterns('',
    url(regex=r'^$', view=view, name='home'),
    url(regex=r'^example/$', view=view, name='example'),
)

########NEW FILE########
__FILENAME__ = marketing
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url  # noqa

from subdomains.tests.urls.default import urlpatterns as default_patterns


urlpatterns = default_patterns

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse


def view(request):
    return HttpResponse()

########NEW FILE########
__FILENAME__ = utils
import functools
try:
    from urlparse import urlunparse
except ImportError:
    from urllib.parse import urlunparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse as simple_reverse


def current_site_domain():
    domain = Site.objects.get_current().domain

    prefix = 'www.'
    if getattr(settings, 'REMOVE_WWW_FROM_DOMAIN', False) \
            and domain.startswith(prefix):
        domain = domain.replace(prefix, '', 1)

    return domain

get_domain = current_site_domain


def urljoin(domain, path=None, scheme=None):
    """
    Joins a domain, path and scheme part together, returning a full URL.

    :param domain: the domain, e.g. ``example.com``
    :param path: the path part of the URL, e.g. ``/example/``
    :param scheme: the scheme part of the URL, e.g. ``http``, defaulting to the
        value of ``settings.DEFAULT_URL_SCHEME``
    :returns: a full URL
    """
    if scheme is None:
        scheme = getattr(settings, 'DEFAULT_URL_SCHEME', 'http')

    return urlunparse((scheme, domain, path or '', None, None, None))


def reverse(viewname, subdomain=None, scheme=None, args=None, kwargs=None,
        current_app=None):
    """
    Reverses a URL from the given parameters, in a similar fashion to
    :meth:`django.core.urlresolvers.reverse`.

    :param viewname: the name of URL
    :param subdomain: the subdomain to use for URL reversing
    :param scheme: the scheme to use when generating the full URL
    :param args: positional arguments used for URL reversing
    :param kwargs: named arguments used for URL reversing
    :param current_app: hint for the currently executing application
    """
    urlconf = settings.SUBDOMAIN_URLCONFS.get(subdomain, settings.ROOT_URLCONF)

    domain = get_domain()
    if subdomain is not None:
        domain = '%s.%s' % (subdomain, domain)

    path = simple_reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs,
        current_app=current_app)
    return urljoin(domain, path, scheme=scheme)


#: :func:`reverse` bound to insecure (non-HTTPS) URLs scheme
insecure_reverse = functools.partial(reverse, scheme='http')

#: :func:`reverse` bound to secure (HTTPS) URLs scheme
secure_reverse = functools.partial(reverse, scheme='https')

#: :func:`reverse` bound to be relative to the current scheme
relative_reverse = functools.partial(reverse, scheme='')

########NEW FILE########
