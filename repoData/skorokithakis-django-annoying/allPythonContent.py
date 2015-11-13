__FILENAME__ = decorators
import importlib
from django.shortcuts import render_to_response
from django import forms
from django import VERSION as DJANGO_VERSION
from django.template import RequestContext
from django.db.models import signals as signalmodule
from django.http import HttpResponse
from django.conf import settings
# Try to be compatible with Django 1.5+.
try:
    import json
except ImportError:
    from django.utils import simplejson as json

import datetime
import os

__all__ = ['render_to', 'signals', 'ajax_request', 'autostrip']


try:
    from functools import wraps
except ImportError:
    def wraps(wrapped, assigned=('__module__', '__name__', '__doc__'),
              updated=('__dict__',)):
        def inner(wrapper):
            for attr in assigned:
                setattr(wrapper, attr, getattr(wrapped, attr))
            for attr in updated:
                getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
            return wrapper
        return inner


def render_to(template=None, content_type=None, mimetype=None):
    """
    Decorator for Django views that sends returned dict to render_to_response
    function.

    Template name can be decorator parameter or TEMPLATE item in returned
    dictionary.  RequestContext always added as context instance.
    If view doesn't return dict then decorator simply returns output.

    Parameters:
     - template: template name to use
     - content_type: content type to send in response headers
     - mimetype: content type to send in response headers (deprecated)

    Examples:
    # 1. Template name in decorator parameters

    @render_to('template.html')
    def foo(request):
        bar = Bar.object.all()
        return {'bar': bar}

    # equals to
    def foo(request):
        bar = Bar.object.all()
        return render_to_response('template.html',
                                  {'bar': bar},
                                  context_instance=RequestContext(request))


    # 2. Template name as TEMPLATE item value in return dictionary.
         if TEMPLATE is given then its value will have higher priority
         than render_to argument.

    @render_to()
    def foo(request, category):
        template_name = '%s.html' % category
        return {'bar': bar, 'TEMPLATE': template_name}

    #equals to
    def foo(request, category):
        template_name = '%s.html' % category
        return render_to_response(template_name,
                                  {'bar': bar},
                                  context_instance=RequestContext(request))

    """
    def renderer(function):
        @wraps(function)
        def wrapper(request, *args, **kwargs):
            output = function(request, *args, **kwargs)
            if not isinstance(output, dict):
                return output
            tmpl = output.pop('TEMPLATE', template)
            if tmpl is None:
                template_dir = os.path.join(*function.__module__.split('.')[:-1])
                tmpl = os.path.join(template_dir, function.func_name + ".html")
            # Explicit version check to avoid swallowing other exceptions
            if DJANGO_VERSION[0] >= 1 and DJANGO_VERSION[1] >= 5:
                return render_to_response(tmpl, output, \
                        context_instance=RequestContext(request),
                        content_type=content_type or mimetype)
            else:
                return render_to_response(tmpl, output, \
                        context_instance=RequestContext(request),
                        mimetype=content_type or mimetype)
        return wrapper
    return renderer


class Signals(object):
    '''
    Convenient wrapper for working with Django's signals (or any other
    implementation using same API).

    Example of usage::


       # connect to registered signal
       @signals.post_save(sender=YourModel)
       def sighandler(instance, **kwargs):
           pass

       # connect to any signal
       signals.register_signal(siginstance, signame) # and then as in example above

       or

       @signals(siginstance, sender=YourModel)
       def sighandler(instance, **kwargs):
           pass

    In any case defined function will remain as is, without any changes.

    (c) 2008 Alexander Solovyov, new BSD License
    '''
    def __init__(self):
        self._signals = {}

        # register all Django's default signals
        for k, v in signalmodule.__dict__.items():
            # that's hardcode, but IMHO it's better than isinstance
            if not k.startswith('__') and k != 'Signal':
                self.register_signal(v, k)

    def __getattr__(self, name):
        return self._connect(self._signals[name])

    def __call__(self, signal, **kwargs):
        def inner(func):
            signal.connect(func, **kwargs)
            return func
        return inner

    def _connect(self, signal):
        def wrapper(**kwargs):
            return self(signal, **kwargs)
        return wrapper

    def register_signal(self, signal, name):
        self._signals[name] = signal

signals = Signals()


def date_time_handler(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        raise TypeError("%r is not JSON serializable" % obj)

FORMAT_TYPES = {
    'application/json': lambda response: json.dumps(response, default=date_time_handler),
    'text/json':        lambda response: json.dumps(response, default=date_time_handler),
}

try:
    import yaml
except ImportError:
    pass
else:
    FORMAT_TYPES.update({
        'application/yaml': yaml.dump,
        'text/yaml':        yaml.dump,
    })


def ajax_request(func):
    """
    If view returned serializable dict, returns response in a format requested
    by HTTP_ACCEPT header. Defaults to JSON if none requested or match.

    Currently supports JSON or YAML (if installed), but can easily be extended.

    example:

        @ajax_request
        def my_view(request):
            news = News.objects.all()
            news_titles = [entry.title for entry in news]
            return {'news_titles': news_titles}
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        for accepted_type in request.META.get('HTTP_ACCEPT', '').split(','):
            if accepted_type in FORMAT_TYPES.keys():
                format_type = accepted_type
                break
        else:
            format_type = 'application/json'
        response = func(request, *args, **kwargs)
        if not isinstance(response, HttpResponse):
            if hasattr(settings, 'FORMAT_TYPES'):
                format_type_handler = settings.FORMAT_TYPES[format_type]
                if hasattr(format_type_handler, '__call__'):
                    data = format_type_handler(response)
                elif isinstance(format_type_handler, basestring):
                    mod_name, func_name = format_type_handler.rsplit('.', 1)
                    module = __import__(mod_name, fromlist=[func_name])
                    function = getattr(module, func_name)
                    data = function(response)
            else:
                data = FORMAT_TYPES[format_type](response)
            response = HttpResponse(data, content_type=format_type)
            response['content-length'] = len(data)
        return response
    return wrapper


def autostrip(cls):
    """
    strip text fields before validation

    example:
    class PersonForm(forms.Form):
        name = forms.CharField(min_length=2, max_length=10)
        email = forms.EmailField()

    PersonForm = autostrip(PersonForm)

    #or you can use @autostrip in python >= 2.6

    Author: nail.xx
    """
    fields = [(key, value) for key, value in cls.base_fields.iteritems() if isinstance(value, forms.CharField)]
    for field_name, field_object in fields:
        def get_clean_func(original_clean):
            return lambda value: original_clean(value and value.strip())
        clean_func = get_clean_func(getattr(field_object, 'clean'))
        setattr(field_object, 'clean', clean_func)
    return cls

########NEW FILE########
__FILENAME__ = exceptions
class Redirect(Exception):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


########NEW FILE########
__FILENAME__ = fields
from django.db import models
from django.db.models import OneToOneField
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.related import SingleRelatedObjectDescriptor

# South support.
try:
    from south.modelsinspector import add_introspection_rules
    SOUTH = True
except ImportError:
    SOUTH = False

# Try to be compatible with Django 1.5+.
try:
    import json
except ImportError:
    from django.utils import simplejson as json


class AutoSingleRelatedObjectDescriptor(SingleRelatedObjectDescriptor):
    def __get__(self, instance, instance_type=None):
        try:
            return super(AutoSingleRelatedObjectDescriptor, self).__get__(instance, instance_type)
        except self.related.model.DoesNotExist:
            obj = self.related.model(**{self.related.field.name: instance})
            obj.save()
            # Don't return obj directly, otherwise it won't be added
            # to Django's cache, and the first 2 calls to obj.relobj
            # will return 2 different in-memory objects
            return super(AutoSingleRelatedObjectDescriptor, self).__get__(instance, instance_type)


class AutoOneToOneField(OneToOneField):
    '''
    OneToOneField creates related object on first call if it doesnt exist yet.
    Use it instead of original OneToOne field.

    example:

        class MyProfile(models.Model):
            user = AutoOneToOneField(User, primary_key=True)
            home_page = models.URLField(max_length=255, blank=True)
            icq = models.IntegerField(max_length=255, null=True)
    '''
    def contribute_to_related_class(self, cls, related):
        setattr(cls, related.get_accessor_name(), AutoSingleRelatedObjectDescriptor(related))

if SOUTH:
    add_introspection_rules([
        (
            (AutoOneToOneField,),
            [],
            {
                "to": ["rel.to", {}],
                "to_field": ["rel.field_name", {"default_attr": "rel.to._meta.pk.name"}],
                "related_name": ["rel.related_name", {"default": None}],
                "db_index": ["db_index", {"default": True}],
            },
        )
    ],
    ["^annoying\.fields\.AutoOneToOneField"])


class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    Django snippet #1478

    example:
        class Page(models.Model):
            data = JSONField(blank=True, null=True)


        page = Page.objects.get(pk=5)
        page.data = {'title': 'test', 'type': 3}
        page.save()
    """

    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                return json.loads(value)
        except ValueError:
            pass
        return value

    def get_db_prep_save(self, value, *args, **kwargs):
        if value == "":
            return None
        if isinstance(value, dict) or isinstance(value, list):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

    def value_from_object(self, obj):
        value = super(JSONField, self).value_from_object(obj)
        if self.null and value is None:
            return None
        return json.dumps(value)

if SOUTH:
    add_introspection_rules([], ["^annoying.fields.JSONField"])

########NEW FILE########
__FILENAME__ = functions
from django.shortcuts import _get_queryset
from django.conf import settings


def get_object_or_None(klass, *args, **kwargs):
    """
    Uses get() to return an object or None if the object does not exist.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.

    Note: Like with get(), a MultipleObjectsReturned will be raised if more than one
    object is found.
    """
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None



def get_config(key, default=None):
    """
    Get settings from django.conf if exists,
    return default value otherwise

    example:

    ADMIN_EMAIL = get_config('ADMIN_EMAIL', 'default@email.com')
    """
    return getattr(settings, key, default)

########NEW FILE########
__FILENAME__ = middlewares
import re

from django.conf import settings
from django.views.static import serve
from django.shortcuts import redirect

from .exceptions import Redirect


class StaticServe(object):
    """
    Django middleware for serving static files instead of using urls.py
    """
    regex = re.compile(r'^%s(?P<path>.*)$' % settings.MEDIA_URL)

    def process_request(self, request):
        if settings.DEBUG:
            match = self.regex.search(request.path)
            if match:
                return serve(request, match.group(1), settings.MEDIA_ROOT)


class RedirectMiddleware(object):
    """
    You must add this middleware to MIDDLEWARE_CLASSES list,
    to make work Redirect exception. All arguments passed to
    Redirect will be passed to django built in redirect function.
    """
    def process_exception(self, request, exception):
        if not isinstance(exception, Redirect):
            return
        return redirect(*exception.args, **exception.kwargs)

########NEW FILE########
__FILENAME__ = models
"""Mandatory models.py for tests to work"""

########NEW FILE########
__FILENAME__ = annoying
import django
from django import template

from smart_if import smart_if


register = template.Library()


try:
    if int(django.get_version()[-5:]) < 11806:
        register.tag('if', smart_if)
except ValueError:
    pass

########NEW FILE########
__FILENAME__ = smart_if
from django import template

__author__ = "SmileyChris"

#==============================================================================
# Calculation objects
#==============================================================================

class BaseCalc(object):
    def __init__(self, var1, var2=None, negate=False):
        self.var1 = var1
        self.var2 = var2
        self.negate = negate

    def resolve(self, context):
        try:
            var1, var2 = self.resolve_vars(context)
            outcome = self.calculate(var1, var2)
        except:
            outcome = False
        if self.negate:
            return not outcome
        return outcome

    def resolve_vars(self, context):
        var2 = self.var2 and self.var2.resolve(context)
        return self.var1.resolve(context), var2

    def calculate(self, var1, var2):
        raise NotImplementedError()


class Or(BaseCalc):
    def calculate(self, var1, var2):
        return var1 or var2


class And(BaseCalc):
    def calculate(self, var1, var2):
        return var1 and var2


class Equals(BaseCalc):
    def calculate(self, var1, var2):
        return var1 == var2


class Greater(BaseCalc):
    def calculate(self, var1, var2):
        return var1 > var2


class GreaterOrEqual(BaseCalc):
    def calculate(self, var1, var2):
        return var1 >= var2


class In(BaseCalc):
    def calculate(self, var1, var2):
        return var1 in var2


OPERATORS = {
    '=': (Equals, True),
    '==': (Equals, True),
    '!=': (Equals, False),
    '>': (Greater, True),
    '>=': (GreaterOrEqual, True),
    '<=': (Greater, False),
    '<': (GreaterOrEqual, False),
    'or': (Or, True),
    'and': (And, True),
    'in': (In, True),
}
BOOL_OPERATORS = ('or', 'and')


class IfParser(object):
    error_class = ValueError

    def __init__(self, tokens):
        self.tokens = tokens

    def _get_tokens(self):
        return self._tokens

    def _set_tokens(self, tokens):
        self._tokens = tokens
        self.len = len(tokens)
        self.pos = 0

    tokens = property(_get_tokens, _set_tokens)

    def parse(self):
        if self.at_end():
            raise self.error_class('No variables provided.')
        var1 = self.get_bool_var()
        while not self.at_end():
            op, negate = self.get_operator()
            var2 = self.get_bool_var()
            var1 = op(var1, var2, negate=negate)
        return var1

    def get_token(self, eof_message=None, lookahead=False):
        negate = True
        token = None
        pos = self.pos
        while token is None or token == 'not':
            if pos >= self.len:
                if eof_message is None:
                    raise self.error_class()
                raise self.error_class(eof_message)
            token = self.tokens[pos]
            negate = not negate
            pos += 1
        if not lookahead:
            self.pos = pos
        return token, negate

    def at_end(self):
        return self.pos >= self.len

    def create_var(self, value):
        return TestVar(value)

    def get_bool_var(self):
        """
        Returns either a variable by itself or a non-boolean operation (such as
        ``x == 0`` or ``x < 0``).

        This is needed to keep correct precedence for boolean operations (i.e.
        ``x or x == 0`` should be ``x or (x == 0)``, not ``(x or x) == 0``).
        """
        var = self.get_var()
        if not self.at_end():
            op_token = self.get_token(lookahead=True)[0]
            if isinstance(op_token, basestring) and (op_token not in
                                                     BOOL_OPERATORS):
                op, negate = self.get_operator()
                return op(var, self.get_var(), negate=negate)
        return var

    def get_var(self):
        token, negate = self.get_token('Reached end of statement, still '
                                       'expecting a variable.')
        if isinstance(token, basestring) and token in OPERATORS:
            raise self.error_class('Expected variable, got operator (%s).' %
                                   token)
        var = self.create_var(token)
        if negate:
            return Or(var, negate=True)
        return var

    def get_operator(self):
        token, negate = self.get_token('Reached end of statement, still '
                                       'expecting an operator.')
        if not isinstance(token, basestring) or token not in OPERATORS:
            raise self.error_class('%s is not a valid operator.' % token)
        if self.at_end():
            raise self.error_class('No variable provided after "%s".' % token)
        op, true = OPERATORS[token]
        if not true:
            negate = not negate
        return op, negate


#==============================================================================
# Actual templatetag code.
#==============================================================================

class TemplateIfParser(IfParser):
    error_class = template.TemplateSyntaxError

    def __init__(self, parser, *args, **kwargs):
        self.template_parser = parser
        return super(TemplateIfParser, self).__init__(*args, **kwargs)

    def create_var(self, value):
        return self.template_parser.compile_filter(value)


class SmartIfNode(template.Node):
    def __init__(self, var, nodelist_true, nodelist_false=None):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.var = var

    def render(self, context):
        if self.var.resolve(context):
            return self.nodelist_true.render(context)
        if self.nodelist_false:
            return self.nodelist_false.render(context)
        return ''

    def __repr__(self):
        return "<Smart If node>"

    def __iter__(self):
        for node in self.nodelist_true:
            yield node
        if self.nodelist_false:
            for node in self.nodelist_false:
                yield node

    def get_nodes_by_type(self, nodetype):
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        nodes.extend(self.nodelist_true.get_nodes_by_type(nodetype))
        if self.nodelist_false:
            nodes.extend(self.nodelist_false.get_nodes_by_type(nodetype))
        return nodes


def smart_if(parser, token):
    """
    A smarter {% if %} tag for django templates.

    While retaining current Django functionality, it also handles equality,
    greater than and less than operators. Some common case examples::

        {% if articles|length >= 5 %}...{% endif %}
        {% if "ifnotequal tag" != "beautiful" %}...{% endif %}

    Arguments and operators _must_ have a space between them, so
    ``{% if 1>2 %}`` is not a valid smart if tag.

    All supported operators are: ``or``, ``and``, ``in``, ``=`` (or ``==``),
    ``!=``, ``>``, ``>=``, ``<`` and ``<=``.
    """
    bits = token.split_contents()[1:]
    var = TemplateIfParser(parser, bits).parse()
    nodelist_true = parser.parse(('else', 'endif'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endif',))
        parser.delete_first_token()
    else:
        nodelist_false = None
    return SmartIfNode(var, nodelist_true, nodelist_false)


########NEW FILE########
__FILENAME__ = decorators
"""Tests for django-annoying's decorators"""

from django.test import TestCase

try:
    import json
except ImportError:
    from django.utils import simplejson as json

class AJAXRequestTestCase(TestCase):
    """Test cases for ajax_request"""
    urls = 'annoying.tests.urls'

    def setUp(self):
        self.RESPONSE_JSON = json.loads('{"int": 1, "list": [2, 3, 4], "bool": true, "date": "2013-12-25T15:16:00", "string": "barry", "dict": {"foo": "bar", "bar": "bob"}}')

    def test_defaults(self):
        response = self.client.get('/ajax-request/')
        self.assertEquals(json.loads(response.content), self.RESPONSE_JSON)
        self.assertTrue('application/json' in response['content-type'])

    def test_valid_header(self):
        response = self.client.get('/ajax-request/', HTTP_ACCEPT='text/json')
        self.assertEquals(json.loads(response.content), self.RESPONSE_JSON)
        self.assertTrue('text/json' in response['content-type'])

    def test_invalid_header(self):
        response = self.client.get('/ajax-request/', HTTP_ACCEPT='foo/bar')
        self.assertEquals(json.loads(response.content), self.RESPONSE_JSON)
        self.assertTrue('application/json' in response['content-type'])

    def test_httpresponse_check(self):
        response = self.client.get('/ajax-request-httpresponse/')
        self.assertEquals(response.content, "Data")
        self.assertTrue('text/html' in response['content-type'])


class RenderToTestCase(TestCase):
    """Test cases for render_to"""
    urls = 'annoying.tests.urls'

    def test_content_type_kwarg(self):
        response = self.client.get('/render-to-content-type-kwarg/')
        self.assertTrue('text/plain' in response['content-type'])

    def test_mimetype_kwarg(self):
        response = self.client.get('/render-to-mimetype-kwarg/')
        self.assertTrue('text/plain' in response['content-type'])

    def test_content_type_positional(self):
        response = self.client.get('/render-to-content-type-positional/')
        self.assertTrue('text/plain' in response['content-type'])

########NEW FILE########
__FILENAME__ = urls
"""URLs for django-annoying's tests"""
from __future__ import absolute_import

from django.conf.urls import patterns
from . import views

urlpatterns = patterns('',
    (r'^ajax-request/$', views.ajax_request_view),
    (r'^ajax-request-httpresponse/$', views.ajax_request_httpresponse_view),
    (r'^render-to-content-type-kwarg/$', views.render_to_content_type_kwarg),
    (r'^render-to-mimetype-kwarg/$', views.render_to_mimetype_kwarg),
    (r'^render-to-content-type-positional/$', views.render_to_content_type_positional),
)

########NEW FILE########
__FILENAME__ = views
"""Views for django-annoying's tests"""
from __future__ import absolute_import

from django.http import HttpResponse

from ..decorators import ajax_request, render_to

import datetime

@ajax_request
def ajax_request_view(request):
    return {
        'bool': True,
        'int': 1,
        'list': [2, 3, 4],
        'dict': {
            'foo': 'bar',
            'bar': 'bob',
        },
        'string': 'barry',
        'date': datetime.datetime(2013, 12, 25, 15, 16),
    }

@ajax_request
def ajax_request_httpresponse_view(request):
    return HttpResponse("Data")


@render_to('test.txt', content_type='text/plain')
def render_to_content_type_kwarg(request):
    return {}


@render_to('test.txt', mimetype='text/plain')
def render_to_mimetype_kwarg(request):
    return {}


@render_to('test.txt', 'text/plain')
def render_to_content_type_positional(request):
    return {}

########NEW FILE########
__FILENAME__ = utils
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri


class HttpResponseReload(HttpResponse):
    """
    Reload page and stay on the same page from where request was made.

    example:

    def simple_view(request):
        if request.POST:
            form = CommentForm(request.POST):
            if form.is_valid():
                form.save()
                return HttpResponseReload(request)
        else:
            form = CommentForm()
        return render_to_response('some_template.html', {'form': form})
    """
    status_code = 302

    def __init__(self, request):
        HttpResponse.__init__(self)
        referer = request.META.get('HTTP_REFERER')
        self['Location'] = iri_to_uri(referer or "/")

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
import sys
from os import path as osp

this = osp.splitext(osp.basename(__file__))[0]
BASE_DIR = osp.dirname(__file__)

from django.conf import settings
SETTINGS = dict(
    DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'test.db'}},
    DEBUG=True,
    TEMPLATE_DEBUG=True,
    ROOT_URLCONF=this,
    INSTALLED_APPS=('django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'annoying'),
    TEMPLATE_DIRS=(osp.join(BASE_DIR, 'annoying', 'tests', 'templates'),),
)

if not settings.configured:
    settings.configure(**SETTINGS)

from django.db import models
from django.conf.urls import patterns

urlpatterns = patterns('',)

if __name__ == '__main__':
    # override get_app to work with us
    get_app_orig = models.get_app
    def get_app(app_label, *a, **kw):
        if app_label == this:
            return sys.modules[__name__]
        return get_app_orig(app_label, *a, **kw)
    models.get_app = get_app

    models.loading.cache.app_store[type(this + '.models', (), {'__file__':__file__})] = this

    from django.core import management
    management.execute_from_command_line(["test.py", "test", "annoying"])

########NEW FILE########
