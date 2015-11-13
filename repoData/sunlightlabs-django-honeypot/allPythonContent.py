__FILENAME__ = decorators
import six

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps # Python <= 2.4

from django.conf import settings
from django.utils.safestring import mark_safe
from django.http import HttpResponseBadRequest
from django.template.loader import render_to_string

def honeypot_equals(val):
    """
        Default verifier used if HONEYPOT_VERIFIER is not specified.
        Ensures val == HONEYPOT_VALUE or HONEYPOT_VALUE() if it's a callable.
    """
    expected = getattr(settings, 'HONEYPOT_VALUE', '')
    if callable(expected):
        expected = expected()
    return val == expected

def verify_honeypot_value(request, field_name):
    """
        Verify that request.POST[field_name] is a valid honeypot.

        Ensures that the field exists and passes verification according to
        HONEYPOT_VERIFIER.
    """
    verifier = getattr(settings, 'HONEYPOT_VERIFIER', honeypot_equals)
    if request.method == 'POST':
        field = field_name or settings.HONEYPOT_FIELD_NAME
        if field not in request.POST or not verifier(request.POST[field]):
            resp = render_to_string('honeypot/honeypot_error.html',
                                    {'fieldname': field})
            return HttpResponseBadRequest(resp)

def check_honeypot(func=None, field_name=None):
    """
        Check request.POST for valid honeypot field.

        Takes an optional field_name that defaults to HONEYPOT_FIELD_NAME if
        not specified.
    """
    # hack to reverse arguments if called with str param
    if isinstance(func, six.string_types):
        func, field_name = field_name, func

    def decorated(func):
        def inner(request, *args, **kwargs):
            response = verify_honeypot_value(request, field_name)
            if response:
                return response
            else:
                return func(request, *args, **kwargs)
        return wraps(func)(inner)

    if func is None:
        def decorator(func):
            return decorated(func)
        return decorator
    return decorated(func)

########NEW FILE########
__FILENAME__ = middleware
import re
import itertools
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.conf import settings
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text
from honeypot.decorators import verify_honeypot_value

# these were moved out of Django 1.2 -- we're going to still use them
_POST_FORM_RE = re.compile(r'(<form\W[^>]*\bmethod\s*=\s*(\'|"|)POST(\'|"|)\b[^>]*>)',
                           re.IGNORECASE)
_HTML_TYPES = ('text/html', 'application/xhtml+xml')

class HoneypotViewMiddleware(object):
    """
        Middleware that verifies a valid honeypot on all non-ajax POSTs.
    """
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.is_ajax():
            return None
        return verify_honeypot_value(request, None)

class HoneypotResponseMiddleware(object):
    """
        Middleware that rewrites all POST forms to include honeypot field.

        Borrows heavily from pre-Django 1.2 django.contrib.csrf.middleware.CsrfResponseMiddleware.
    """
    def process_response(self, request, response):

        if response['Content-Type'].split(';')[0] in _HTML_TYPES:
             # ensure we don't add the 'id' attribute twice (HTML validity)
            def add_honeypot_field(match):
                """Returns the matched <form> tag plus the added <input> element"""
                value = getattr(settings, 'HONEYPOT_VALUE', '')
                if callable(value):
                    value = value()
                return mark_safe(match.group() +
                                 render_to_string('honeypot/honeypot_field.html',
                                                  {'fieldname': settings.HONEYPOT_FIELD_NAME,
                                                   'value': value}))

            # Modify any POST forms
            response.content = _POST_FORM_RE.sub(add_honeypot_field, force_text(response.content))
        return response

class HoneypotMiddleware(HoneypotViewMiddleware, HoneypotResponseMiddleware):
    """
        Combines HoneypotViewMiddleware and HoneypotResponseMiddleware.
    """
    pass

########NEW FILE########
__FILENAME__ = models
# needed to run tests

########NEW FILE########
__FILENAME__ = honeypot
from django import template
from django.conf import settings

register = template.Library()

@register.inclusion_tag('honeypot/honeypot_field.html')
def render_honeypot_field(field_name=None):
    """
        Renders honeypot field named field_name (defaults to HONEYPOT_FIELD_NAME).
    """
    if not field_name:
        field_name = settings.HONEYPOT_FIELD_NAME
    value = getattr(settings, 'HONEYPOT_VALUE', '')
    if callable(value):
        value = value()
    return {'fieldname': field_name, 'value': value}

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.template import Template, Context
from django.template.loader import render_to_string
from django.conf import settings
from honeypot.middleware import HoneypotViewMiddleware, HoneypotResponseMiddleware
from honeypot.decorators import verify_honeypot_value, check_honeypot


def _get_GET_request():
    return HttpRequest()

def _get_POST_request():
    req = HttpRequest()
    req.method = "POST"
    return req

def view_func(request):
    return HttpResponse()

class HoneypotTestCase(TestCase):
    def setUp(self):
        # delattrs here are a required hack until django #10130 is closed
        if hasattr(settings, 'HONEYPOT_VALUE'):
            delattr(settings._wrapped, 'HONEYPOT_VALUE')
        if hasattr(settings, 'HONEYPOT_VERIFIER'):
            delattr(settings._wrapped, 'HONEYPOT_VERIFIER')
        settings.HONEYPOT_FIELD_NAME = 'honeypot'

class VerifyHoneypotValue(HoneypotTestCase):

    def test_no_call_on_get(self):
        """ test that verify_honeypot_value is not called when request.method == GET """
        request = _get_GET_request()
        resp = verify_honeypot_value(request, None)
        self.assertEquals(resp, None)

    def test_verifier_false(self):
        """ test that verify_honeypot_value fails when HONEYPOT_VERIFIER returns False """
        request = _get_POST_request()
        request.POST[settings.HONEYPOT_FIELD_NAME] = ''
        settings.HONEYPOT_VERIFIER = lambda x: False
        resp = verify_honeypot_value(request, None)
        self.assertEquals(resp.__class__, HttpResponseBadRequest)

    def test_field_missing(self):
        """ test that verify_honeypot_value succeeds when HONEYPOT_FIELD_NAME is missing from request.POST """
        request = _get_POST_request()
        resp = verify_honeypot_value(request, None)
        self.assertEquals(resp.__class__, HttpResponseBadRequest)

    def test_field_blank(self):
        """ test that verify_honeypot_value succeeds when HONEYPOT_VALUE is blank """
        request = _get_POST_request()
        request.POST[settings.HONEYPOT_FIELD_NAME] = ''
        resp = verify_honeypot_value(request, None)
        self.assertEquals(resp, None)

    def test_honeypot_value_string(self):
        """ test that verify_honeypot_value succeeds when HONEYPOT_VALUE is a string """
        request = _get_POST_request()
        settings.HONEYPOT_VALUE = '(test string)'
        request.POST[settings.HONEYPOT_FIELD_NAME] = settings.HONEYPOT_VALUE
        resp = verify_honeypot_value(request, None)
        self.assertEquals(resp, None)

    def test_honeypot_value_callable(self):
        """ test that verify_honeypot_value succeeds when HONEYPOT_VALUE is a callable """
        request = _get_POST_request()
        settings.HONEYPOT_VALUE = lambda: '(test string)'
        request.POST[settings.HONEYPOT_FIELD_NAME] = settings.HONEYPOT_VALUE()
        resp = verify_honeypot_value(request, None)
        self.assertEquals(resp, None)


class CheckHoneypotDecorator(HoneypotTestCase):

    def test_default_decorator(self):
        """ test that @check_honeypot works and defaults to HONEYPOT_FIELD_NAME """
        new_view_func = check_honeypot(view_func)
        request = _get_POST_request()
        resp = new_view_func(request)
        self.assertEquals(resp.__class__, HttpResponseBadRequest)

    def test_decorator_argument(self):
        """ test that check_honeypot(view, 'fieldname') works """
        new_view_func = check_honeypot(view_func, 'fieldname')
        request = _get_POST_request()
        resp = new_view_func(request)
        self.assertEquals(resp.__class__, HttpResponseBadRequest)

    def test_decorator_py24_syntax(self):
        """ test that @check_honeypot syntax works """
        @check_honeypot('field')
        def new_view_func(request):
            return HttpResponse()
        request = _get_POST_request()
        resp = new_view_func(request)
        self.assertEquals(resp.__class__, HttpResponseBadRequest)

class RenderHoneypotField(HoneypotTestCase):

    def _assert_rendered_field(self, template, fieldname, value=''):
        correct = render_to_string('honeypot/honeypot_field.html', 
                                   {'fieldname':fieldname, 'value': value})
        rendered = template.render(Context())
        self.assertEquals(rendered, correct)

    def test_default_templatetag(self):
        """ test that {% render_honeypot_field %} works and defaults to HONEYPOT_FIELD_NAME """
        template = Template('{% load honeypot %}{% render_honeypot_field %}')
        self._assert_rendered_field(template, settings.HONEYPOT_FIELD_NAME, '')

    def test_templatetag_honeypot_value(self):
        """ test that {% render_honeypot_field %} uses settings.HONEYPOT_VALUE """
        template = Template('{% load honeypot %}{% render_honeypot_field %}')
        settings.HONEYPOT_VALUE = '(leave blank)'
        self._assert_rendered_field(template, settings.HONEYPOT_FIELD_NAME, settings.HONEYPOT_VALUE)

    def test_templatetag_argument(self):
        """ test that {% render_honeypot_field 'fieldname' %} works """
        template = Template('{% load honeypot %}{% render_honeypot_field "fieldname" %}')
        self._assert_rendered_field(template, 'fieldname', '')

class HoneypotMiddleware(HoneypotTestCase):

    _response_body = '<form method="POST"></form>'

    def test_view_middleware_invalid(self):
        """ don't call view when HONEYPOT_VERIFIER returns False """
        request = _get_POST_request()
        retval = HoneypotViewMiddleware().process_view(request, view_func, (), {})
        self.assertEquals(retval.__class__, HttpResponseBadRequest)

    def test_view_middleware_valid(self):
        """ call view when HONEYPOT_VERIFIER returns True """
        request = _get_POST_request()
        request.POST[settings.HONEYPOT_FIELD_NAME] = ''
        retval = HoneypotViewMiddleware().process_view(request, view_func, (), {})
        self.assertEquals(retval, None)

    def test_response_middleware_rewrite(self):
        """ ensure POST forms are rewritten """
        request = _get_POST_request()
        request.POST[settings.HONEYPOT_FIELD_NAME] = ''
        response = HttpResponse(self._response_body)
        HoneypotResponseMiddleware().process_response(request, response)
        self.assertNotContains(response, self._response_body)
        self.assertContains(response, 'name="%s"' % settings.HONEYPOT_FIELD_NAME)

    def test_response_middleware_contenttype_exclusion(self):
        """ ensure POST forms are not rewritten for non-html content types """
        request = _get_POST_request()
        request.POST[settings.HONEYPOT_FIELD_NAME] = ''
        response = HttpResponse(self._response_body, content_type='text/javascript')
        HoneypotResponseMiddleware().process_response(request, response)
        self.assertContains(response, self._response_body)

    def test_response_middleware_unicode(self):
        """ ensure that POST form rewriting works with unicode templates """
        request = _get_GET_request()
        unicode_body = u'\u2603'+self._response_body    # add unicode snowman
        response = HttpResponse(unicode_body)
        HoneypotResponseMiddleware().process_response(request, response)
        self.assertNotContains(response, unicode_body)
        self.assertContains(response, 'name="%s"' % settings.HONEYPOT_FIELD_NAME)

########NEW FILE########
__FILENAME__ = test_settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}
INSTALLED_APPS = ('honeypot',)
SECRET_KEY = 'honeyisfrombees'

########NEW FILE########
