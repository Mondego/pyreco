__FILENAME__ = emitters
"""
This file is based on source code from django-piston, available at the following URL:
http://bitbucket.org/jespern/django-piston
"""

from __future__ import generators
from django.db.models.query import QuerySet
from django.db.models import Model, permalink
from django.utils import simplejson
from django.utils.xmlutils import SimplerXMLGenerator
from django.utils.encoding import smart_unicode
from django.core.urlresolvers import reverse, NoReverseMatch
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.core import serializers
from django.core.paginator import Page

import decimal, re, inspect
import copy

class Emitter(object):
    """
    Super emitter. All other emitters should subclass
    this one. It has the `construct` method which
    conveniently returns a serialized `dict`. This is
    usually the only method you want to use in your
    emitter. See below for examples.
    """

    EMITTERS = {}
    RESERVED_FIELDS = set([
        'read',
        'update',
        'create',
        'delete',
        'model',
        'anonymous',
        'allowed_methods',
        'fields',
        'exclude'
    ])

    def __init__(self, payload, typemapper, handler, fields=(), anonymous=True):

        self.typemapper = typemapper
        self.data = payload
        self.handler = handler
        self.fields = fields
        self.anonymous = anonymous

        if isinstance(self.data, Exception):
            raise

    def method_fields(self, handler, fields):

        if not handler:
            return {}

        ret = dict()
        for field in fields - Emitter.RESERVED_FIELDS:
            t = getattr(handler, str(field), None)

            if t and callable(t):
                ret[field] = t

        return ret

    def construct(self):
        """
        Recursively serialize a lot of types, and
        in cases where it doesn't recognize the type,
        it will fall back to Django's `smart_unicode`.

        Returns `dict`.
        """

        def _any(thing, fields=()):
            """
            Dispatch, all types are routed through here.
            """

            ret = None

            if isinstance(thing, QuerySet):
                ret = _qs(thing, fields=fields)
            elif isinstance(thing, Page):
                ret = _list(thing.object_list, fields=fields)
            elif isinstance(thing, (tuple, list)):
                ret = _list(thing, fields=fields)
            elif isinstance(thing, dict):
                ret = _dict(thing, fields=fields)
            elif isinstance(thing, decimal.Decimal):
                ret = str(thing)
            elif isinstance(thing, Model):
                ret = _model(thing, fields=fields)
            elif inspect.isfunction(thing):
                if not inspect.getargspec(thing)[0]:
                    ret = _any(thing())
            elif hasattr(thing, '__emittable__'):
                f = thing.__emittable__
                if inspect.ismethod(f) and len(inspect.getargspec(f)[0]) == 1:
                    ret = _any(f())
            elif repr(thing).startswith("<django.db.models.fields.related.RelatedManager"):
                ret = _any(thing.all())
            else:
                ret = smart_unicode(thing, strings_only=True)

            return ret

        def _fk(data, field):
            """
            Foreign keys.
            """

            return _any(getattr(data, field.name))

        def _related(data, fields=()):
            """
            Foreign keys.
            """

            return [ _model(m, fields) for m in data.iterator() ]

        def _m2m(data, field, fields=()):
            """
            Many to many (re-route to `_model`.)
            """

            return [ _model(m, fields) for m in getattr(data, field.name).iterator() ]

        def _model(data, fields=()):
            """
            Models. Will respect the `fields` and/or
            `exclude` on the handler (see `typemapper`.)
            """

            ret = { }
            handler = None

            # Does the model implement get_serialization_fields() or serialize_fields()?
            # We should only serialize these fields.
            if hasattr(data, 'get_serialization_fields'):
                fields = set(data.get_serialization_fields())
            if hasattr(data, 'serialize_fields'):
                fields = set(data.serialize_fields())

            # Is the model a Django user instance?
            # Ensure that only core (non-sensitive fields) are serialized
            if isinstance(data, User):
                fields = getattr(settings, 'DYNAMICRESPONSE_DJANGO_USER_FIELDS', ('id', 'email', 'first_name', 'last_name'))

            # Should we explicitly serialize specific fields?
            if fields:

                v = lambda f: getattr(data, f.attname)

                get_fields = set(fields)
                met_fields = self.method_fields(handler, get_fields)

                # Serialize normal fields
                for f in data._meta.local_fields:
                    if f.serialize and not any([ p in met_fields for p in [ f.attname, f.name ]]):
                        if not f.rel:
                            if f.attname in get_fields:
                                ret[f.attname] = _any(v(f))
                                get_fields.remove(f.attname)
                        else:
                            if f.attname[:-3] in get_fields:
                                ret[f.name] = _fk(data, f)
                                get_fields.remove(f.name)

                # Serialize many-to-many fields
                for mf in data._meta.many_to_many:
                    if mf.serialize and mf.attname not in met_fields:
                        if mf.attname in get_fields:
                            ret[mf.name] = _m2m(data, mf)
                            get_fields.remove(mf.name)

                # Try to get the remainder of fields
                for maybe_field in get_fields:
                    if isinstance(maybe_field, (list, tuple)):
                        model, fields = maybe_field
                        inst = getattr(data, model, None)

                        if inst:
                            if hasattr(inst, 'all'):
                                ret[model] = _related(inst, fields)
                            elif callable(inst):
                                if len(inspect.getargspec(inst)[0]) == 1:
                                    ret[model] = _any(inst(), fields)
                            else:
                                ret[model] = _model(inst, fields)

                    elif maybe_field in met_fields:
                        # Overriding normal field which has a "resource method"
                        # so you can alter the contents of certain fields without
                        # using different names.
                        ret[maybe_field] = _any(met_fields[maybe_field](data))

                    else:
                        maybe = getattr(data, maybe_field, None)
                        if maybe:
                            if callable(maybe):
                                if len(inspect.getargspec(maybe)[0]) == 1:
                                    ret[maybe_field] = _any(maybe())
                            else:
                                ret[maybe_field] = _any(maybe)
                        else:
                            ret[maybe_field] = _any(maybe)

            else:

                for f in data._meta.fields:
                    if not f.attname.startswith('_'):
                        ret[f.attname] = _any(getattr(data, f.attname))

                fields = dir(data.__class__) + ret.keys()
                add_ons = [k for k in dir(data) if k not in fields]

                for k in add_ons:
                    if not k.__str__().startswith('_'):
                        ret[k] = _any(getattr(data, k))

            return ret

        def _qs(data, fields=()):
            """
            Querysets.
            """

            return [ _any(v, fields) for v in data ]

        def _list(data, fields=()):
            """
            Lists.
            """

            return [ _any(v, fields) for v in data ]

        def _dict(data, fields=()):
            """
            Dictionaries.
            """

            return dict([ (k, _any(v, fields)) for k, v in data.iteritems() ])

        # Kickstart the seralizin'.
        return _any(self.data, self.fields)

    def in_typemapper(self, model, anonymous):
        for klass, (km, is_anon) in self.typemapper.iteritems():
            if model is km and is_anon is anonymous:
                return klass

    def render(self):
        """
        This super emitter does not implement `render`,
        this is a job for the specific emitter below.
        """
        raise NotImplementedError("Please implement render.")

class JSONEmitter(Emitter):
    """
    JSON emitter, understands timestamps.
    """

    def render(self):

        indent = 0
        if settings.DEBUG:
            indent = 4

        seria = simplejson.dumps(self.construct(), cls=DateTimeAwareJSONEncoder, ensure_ascii=False, indent=indent)
        return seria

########NEW FILE########
__FILENAME__ = json_response
from django.conf import settings
from django.http import HttpResponse

from dynamicresponse.emitters import JSONEmitter

class JsonResponse(HttpResponse):
    """
    Provides a JSON response to a client, performing automatic serialization.
    """
    
    def __init__(self, object=None, **kwargs):

        # Perform JSON serialization
        if object is not None:
            emitter = JSONEmitter(object, {}, None)
            content = emitter.render()
        else:
            content = ''

        # Status code for the response
        status_code = kwargs.get('status', 200)

        # Return response with correct payload/type
        super(JsonResponse, self).__init__(
            content,
            content_type='application/json; charset=%s' % settings.DEFAULT_CHARSET,
            status=status_code
        )

########NEW FILE########
__FILENAME__ = api
from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse, HttpResponseRedirect

class APIMiddleware:
    """
    Detects API requests and provides support for Basic authentication.
    """

    api_accept_types = [
        'application/json',
    ]

    def process_request(self, request):

        # Check if request is API
        self._detect_api_request(request)

        # Should we authenticate based on headers?
        if self._should_authorize(request):
            if not self._perform_basic_auth(request):
                return self._require_authentication()

    def process_response(self, request, response):

        if not getattr(request, 'is_api', False):
            return response

        # Convert redirect from login_required to HTTP 401
        if isinstance(response, HttpResponseRedirect):
            redirect_url = response.get('Location', '')
            if redirect_url.startswith(settings.LOGIN_URL):
                return self._require_authentication()

        return response

    def _detect_api_request(self, request):
        """
        Detects API request based on the HTTP Accept header.
        If so, sets is_api on the request.
        """

        request.is_api = False
        request.accepts = []
        if 'HTTP_ACCEPT' in request.META:
            request.accepts = [a.split(';')[0] for a in request.META['HTTP_ACCEPT'].split(',')]

        for accept_type in request.accepts:
            if accept_type in self.api_accept_types:
                request.is_api = True

    def _get_auth_string(self, request):
        """
        Returns the authorization string set in the request header.
        """

        return request.META.get('Authorization', None) or request.META.get('HTTP_AUTHORIZATION', None)

    def _should_authorize(self, request):
        """
        Returns true if the request is an unauthenticated API request,
        already containing HTTP authorization headers.
        """

        if (not request.is_api) or (request.user.is_authenticated()):
            return False
        else:
            return self._get_auth_string(request) is not None

    def _perform_basic_auth(self, request):
        """"
        Logs in user specified with credentials provided by HTTP authentication.
        """

        # Get credentials from authorization header
        auth_string = self._get_auth_string(request)
        if not auth_string:
            return False

        # Try to parse the authorization method and credentials
        try:
            authmeth, auth = auth_string.split(' ', 1)
        except ValueError:
            authmeth, auth = '', None

        # We only support Basic authentication
        if not authmeth.lower() == 'basic':
            return False

        # Validate username and password
        auth = auth.strip().decode('base64')

        # Try the parse the credentials separated with a colon
        try:
            username, password = auth.split(':', 1)
        except ValueError:
            return False

        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            request.user = user
            return True
        else:
            return False

    def _require_authentication(self):
        """
        Returns a request for authentication.
        """

        response = HttpResponse(status=401)
        response['WWW-Authenticate'] = 'Basic realm="%s"' % getattr(settings, 'DYNAMICRESPONSE_BASIC_REALM_NAME', 'API')
        return response

########NEW FILE########
__FILENAME__ = dynamicformat
from django.http import HttpResponse, QueryDict
from django.utils import simplejson

from dynamicresponse.response import DynamicResponse

class DynamicFormatMiddleware:
    """
    Provides support for dynamic content negotiation, both in request and reponse.
    """

    def _flatten_dict(self, obj, prefix=''):
        """
        Converts a possibly nested dictionary to a flat dictionary.
        """

        encoded_dict = QueryDict('').copy()

        if hasattr(obj, 'items'):
            for key, value in obj.items():

                item_key = '%(prefix)s%(key)s' % { 'prefix': prefix, 'key': key }

                # Flatten lists for formsets and model choice fields
                if isinstance(value, list):
                    for i, item in enumerate(value):

                        if isinstance(item, dict):

                            # Flatten nested object to work with formsets
                            item_prefix = '%(key)s-%(index)d-' % { 'key': key, 'index': i }
                            encoded_dict.update(self._flatten_dict(item, prefix=item_prefix))

                            # ID for use with model multi choice fields
                            id_value = item.get('id', None)
                            if id_value:
                                encoded_dict.update({ key: id_value })

                        else:

                            # Value for use with model multi choice fields
                            encoded_dict.update({ key: item })

                # ID for use with model choice fields
                elif isinstance(value, dict):
                    encoded_dict[item_key] = value.get('id', value)

                # Keep JavaScript null as Python None
                elif value is None:
                    encoded_dict[item_key] = None

                # Other values are used directly
                else:
                    encoded_dict[item_key] = unicode(value)

        return encoded_dict

    def process_request(self, request):
        """"
        Parses the request, decoding JSON payloads to be compatible with forms.
        """

        # Does the request contain a JSON payload?
        content_type = request.META.get('CONTENT_TYPE', '')
        if content_type != '' and 'application/json' in content_type:

            # Ignore empty payloads (e.g. for deletes)
            content_length = 0
            if request.META.get('CONTENT_LENGTH', '') != '':
                content_length = int(request.META.get('CONTENT_LENGTH', 0))
            if content_length > 0:
                try:
                    # Replace request.POST with flattened dictionary from JSON
                    decoded_dict = simplejson.loads(request.raw_post_data)
                    request.POST = request.POST.copy()
                    request.POST = self._flatten_dict(decoded_dict)
                except:
                    return HttpResponse('Invalid JSON', status=400)

    def process_response(self, request, response):
        """
        Handles rendering dynamic responses.
        """

        # Cause dynamic responses to be rendered
        if isinstance(response, DynamicResponse):
            return response.render_response(request, response)

        return response

########NEW FILE########
__FILENAME__ = response
from django.conf import settings
from django.forms import Form, ModelForm
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from dynamicresponse.json_response import JsonResponse

CR_OK = ('OK', 200)
CR_INVALID_DATA = ('INVALID', 400)
CR_NOT_FOUND = ('NOT_FOUND', 404)
CR_CONFIRM = ('CONFIRM', 405)
CR_DELETED = ('DELETED', 204)
CR_REQUIRES_UPGRADE = ('REQUIRES_UPGRADE', 402)

class DynamicResponse(object):
    """
    Base class for dynamic responses.
    """

    def __init__(self, context={}, **kwargs):

        self.context = context
        self.status = context.get('status', CR_OK)
        for arg in kwargs:
            setattr(self, arg, kwargs[arg])

    def serialize(self):
        """
        Serializes the context as JSON, or returns a HTTP response with corresponding status.
        """

        key, status_code = self.status

        if status_code == CR_OK[1]:
            return JsonResponse(self.context)

        elif status_code == CR_INVALID_DATA[1]:

            # Output form errors when return status is invalid
            if hasattr(self, 'extra') and getattr(settings, 'DYNAMICRESPONSE_JSON_FORM_ERRORS', False):
                errors = {}

                for form in [value for key, value in self.extra.items() if isinstance(value, Form) or isinstance(value, ModelForm)]:
                    if not form.is_valid():

                        for key, val in form.errors.items():

                            # Flatten field errors
                            if isinstance(val, list):
                                val = ' '.join(val)

                            # Split general and field specific errors
                            if key == '__all__':
                                errors['general_errors'] = val
                            else:

                                # Field specific errors
                                if not 'field_errors' in errors:
                                    errors['field_errors'] = {}

                                errors['field_errors'][key] = val

                return JsonResponse(errors, status=status_code)

        # Return blank response for all other status codes
        return JsonResponse(status=status_code)

    def full_context(self):
        """
        Returns context and extra context combined into a single dictionary.
        """

        full_context = {}
        full_context.update(self.context)
        if hasattr(self, 'extra'):
            full_context.update(self.extra)
        return full_context

class SerializeOrRender(DynamicResponse):
    """
    For normal requests, the specified template is rendered.
    For API requests, the context is serialized and returned as JSON.
    """

    def __init__(self, template, context={}, **kwargs):

        super(SerializeOrRender, self).__init__(context, **kwargs)
        self.template = template

    def render_response(self, request, response):

        if request.is_api:
            res = self.serialize()
        else:
            res = render_to_response(self.template, self.full_context(), RequestContext(request))

        if hasattr(self, 'extra_headers'):
            for header in self.extra_headers:
                res[header] = self.extra_headers[header]

        return res

class SerializeOrRedirect(DynamicResponse):
    """
    For normal requests, the user is redirected to the specified location.
    For API requests, the context is serialized and returned as JSON.
    """

    def __init__(self, url, context={}, **kwargs):

        super(SerializeOrRedirect, self).__init__(context, **kwargs)
        self.url = url

    def render_response(self, request, response):

        if request.is_api:
            res = self.serialize()
        else:
            res = HttpResponseRedirect(self.url)

        if hasattr(self, 'extra_headers'):
            for header in self.extra_headers:
                res[header] = self.extra_headers[header]

        return res

class Serialize(DynamicResponse):
    """
    Serializes the context as JSON for both API and normal requests.
    Useful for AJAX-only type views.
    """

    def __init__(self, context={}, **kwargs):

        super(Serialize, self).__init__(context, **kwargs)

    def render_response(self, request, response):

        res = self.serialize()

        if hasattr(self, 'extra_headers'):
            for header in self.extra_headers:
                res[header] = self.extra_headers[header]

        return res

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from blog.models import BlogPost

admin.site.register(BlogPost)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from blog.models import BlogPost

class BlogPostForm(forms.ModelForm):
    """Creates/updates a blog post."""
    
    class Meta:
        model = BlogPost
        fields = ('title', 'text')

########NEW FILE########
__FILENAME__ = models
from django.db import models

class BlogPost(models.Model):
    """Simple blog post model for demo purposes."""
    
    title = models.CharField('Title', max_length=255)
    text = models.TextField('Text')
    
    class Meta:
        verbose_name='Blog post'
        verbose_name_plural='Blog posts'

    def __unicode__(self):        
        return self.title
        
    def serialize_fields(self):
        """Only these fields will be included in API responses."""
        
        return [
            'id',
            'title',
            'text'
        ]

########NEW FILE########
__FILENAME__ = runtests
# This file mainly exists to allow python setup.py test to work.
import os, sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, test_dir)

os.environ['DJANGO_SETTINGS_MODULE'] = 'myblog.settings'

from django.conf import settings
from django.test.utils import get_runner

def runtests():
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True)
    failures = test_runner.run_tests(['blog'])
    sys.exit(bool(failures))

if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = api
import unittest

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.test import TestCase
from mock import Mock

from dynamicresponse.middleware.api import APIMiddleware


class ApiTest(unittest.TestCase):
    """
    Test basic API middleware operations.
    """

    def setUp(self):
        self.api = APIMiddleware()
        self.request = HttpRequest()


    def testProcessRequestSetsIsApiFlag(self):
        self.api._detect_api_request = Mock()
        self.api._should_authorize = Mock() # Prevent execution
        self.api._perform_basic_auth = Mock() # Prevent execution
        self.api._require_authentication = Mock() # Prevent execution

        self.api.process_request(self.request)
        self.assertTrue(self.api._detect_api_request.called, '_detect_api_request function was not called, thus is_api is not set')

    def testProcessRequestReturns401IfInvalidRequest(self):
        self.api._detect_api_request = Mock() # Prevent execution
        self.api._should_authorize = Mock(return_value=False)
        self.api._perform_basic_auth = Mock(return_value=False)
        self.api._require_authentication = Mock(return_value='require_auth')

        self.assertTrue(self.api.process_request(self.request) is None)

        self.api._should_authorize = Mock(return_value=True)
        self.assertEqual(self.api.process_request(self.request), 'require_auth')

        self.api._perform_basic_auth = Mock(return_value=True)
        self.assertTrue(self.api.process_request(self.request) is None)

        self.api._should_authorize = Mock(return_value=False)
        self.assertTrue(self.api.process_request(self.request) is None)

    def testProcessResponseReturnsResponseAsIsUnlessItsARedirect(self):
        self.api._require_authentication = Mock(return_value='req_auth')
        self.request.is_api = False
        response = HttpResponse()

        result = self.api.process_response(self.request, response)
        self.assertTrue(result is response, 'process_response should return the same response object')

        self.request.is_api = True
        result = self.api.process_response(self.request, response)
        self.assertTrue(result is response, 'process_response should return the same response object')

        response = HttpResponseRedirect('/invalid/url')
        result = self.api.process_response(self.request, response)
        self.assertTrue(result is response, 'process_response should return the same response object')

        response = HttpResponseRedirect(settings.LOGIN_URL)
        result = self.api.process_response(self.request, response)
        self.assertEqual(result, 'req_auth')

    def testDetectApiRequestSetsApiTrueIfRequestAcceptsJson(self):
        self.request.is_api = False # Keeping pyLint happy
        self.api._detect_api_request(self.request)
        self.assertFalse(self.request.is_api)

        self.request.META['HTTP_ACCEPT'] = 'text/plain'
        self.api._detect_api_request(self.request)
        self.assertFalse(self.request.is_api)

        self.request.META['HTTP_ACCEPT'] = 'application/json'
        self.api._detect_api_request(self.request)
        self.assertTrue(self.request.is_api)

    def testGetAuthStringReturnsStringInAuthenticationHeader(self):
        no_auth = HttpRequest()
        auth1 = HttpRequest()
        auth2 = HttpRequest()

        auth1.META['Authorization'] = 'teststring'
        auth2.META['HTTP_AUTHORIZATION'] = 'teststring'

        self.assertTrue(self.api._get_auth_string(no_auth) is None)
        self.assertEqual(self.api._get_auth_string(auth1), 'teststring')
        self.assertEqual(self.api._get_auth_string(auth2), 'teststring')

    def testShouldAuthorizeReturnsTrueIfRequestNeedsAuthentication(self):
        self.api._get_auth_string = Mock(return_value="blabla")

        self.request.is_api = False
        self.request.user = Mock()
        self.request.user.is_authenticated = Mock(return_value=True)
        self.assertFalse(self.api._should_authorize(self.request))

        self.request.user.is_authenticated = Mock(return_value=False)
        self.assertFalse(self.api._should_authorize(self.request))

        self.request.is_api = True
        self.assertTrue(self.api._should_authorize(self.request))

        self.api._get_auth_string = Mock(return_value=None)
        self.assertFalse(self.api._should_authorize(self.request))

        self.request.user.is_authenticated = Mock(return_value=True)
        self.assertFalse(self.api._should_authorize(self.request))

    def testRequireAuthenticationReturnsValidHttpResponse(self):
        response = self.api._require_authentication()

        self.assertTrue(isinstance(response, HttpResponse), 'Response should be an instance of HttpResponse')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['WWW-Authenticate'], 'Basic realm="API"')

    def testInvalidBasicAuthStringResponse(self):
        """
        Ensure that invalid basic auth headers are treated correctly.
        """

        # Test missing "Basic" opening keyword
        request = HttpRequest()
        request.META['Authorization'] = 'invalid_basic_auth_string'

        self.assertFalse(self.api._perform_basic_auth(request))

        # Test wrong formatting of credentials
        request = HttpRequest()
        credentials = 'username password'.encode('base64') # Missing colon separator
        request.META['Authorization'] = 'Basic %s' % credentials

        self.assertFalse(self.api._perform_basic_auth(request))

class ApiLogInTests(TestCase):
    """
    Test log in of Django users via Basic auth.
    """

    fixtures = ['test_data']

    def setUp(self):
        self.api = APIMiddleware()

    def testBasicAuthentication(self):
        """
        Test that a user can log in with Basic auth.
        """

        request = HttpRequest()
        credentials = 'johndoe:foobar'.encode('base64')
        request.META['Authorization'] = 'Basic %s' % credentials

        self.assertTrue(self.api._perform_basic_auth(request))
        self.assertTrue(request.user.is_authenticated())
        self.assertEquals(request.user, User.objects.get(id=1))

########NEW FILE########
__FILENAME__ = dynamicformat
import unittest

from django.http import HttpRequest, HttpResponse, QueryDict
from django.utils.simplejson import loads, dumps
from mock import Mock

from dynamicresponse.middleware.dynamicformat import DynamicFormatMiddleware
from dynamicresponse.response import DynamicResponse


class DynamicFormatTest(unittest.TestCase):

    def setUp(self):
        self.dynamicformat = DynamicFormatMiddleware()
        self.request = HttpRequest()
        self.request._raw_post_data = dumps({
            "testint": 5,
            "teststring": "allihopa",
            "testobj": {
                "anotherint": 10,
                "anotherstring": "bengladesh",
                "testlist": [1, 2, 3, 4, 5]
            },
            "testlist": [1, 2, 3, 4, 5]
        })


    def testFlattenDict(self):
        self.assertTrue(isinstance(self.dynamicformat._flatten_dict(loads(self.request._raw_post_data)), QueryDict))

    def testProcessRequestFlattensPost(self):
        self.dynamicformat._flatten_dict = Mock()
        self.request.META['CONTENT_TYPE'] = 'application/json'
        self.request.META['CONTENT_LENGTH'] = 1

        self.dynamicformat.process_request(self.request)
        self.dynamicformat._flatten_dict.assert_called_once_with(loads(self.request._raw_post_data))

    def testProcessRequestDoesNotFlattenPostIfContentLengthIs0(self):
        self.dynamicformat._flatten_dict = Mock()
        self.request.META['CONTENT_TYPE'] = 'application/json'
        self.request.META['CONTENT_LENGTH'] = 0

        self.dynamicformat.process_request(self.request)
        self.assertFalse(self.dynamicformat._flatten_dict.called, '_flatted_dict was called when it shouldnt have been')

    def testProcessRequestReturnsHttpResponse400WhenPostDataConversionFails(self):
        def raiseException():
            raise

        self.dynamicformat._flatten_dict = Mock(side_effect=raiseException)
        self.request.META['CONTENT_TYPE'] = 'application/json'
        self.request.META['CONTENT_LENGTH'] = 1

        result = self.dynamicformat.process_request(self.request)
        self.assertTrue(isinstance(result, HttpResponse), 'should return instance of HttpResponse')
        self.assertEqual(result.status_code, 400)

    def testProcessResponseCallsRenderResponseOnDynamicResponseObjects(self):
        request = Mock()
        response = HttpResponse()

        self.assertTrue(self.dynamicformat.process_response(request, response) is response,
            'process_response should return the response object if not of instance DynamicResponse')

        response = {}
        self.assertTrue(self.dynamicformat.process_response(request, response) is response,
                        'process_response should return the response object if not of instance DynamicResponse')

        response = DynamicResponse()
        response.render_response = Mock()
        self.dynamicformat.process_response(request, response)
        self.assertTrue(response.render_response.called, 'render_response was not called')

########NEW FILE########
__FILENAME__ = json_response
from datetime import datetime
import unittest

from django.db import models
from django.http import HttpResponse
from django.utils import simplejson

from dynamicresponse.json_response import JsonResponse


class ModelWithSerializeFields(models.Model):
    title = models.CharField('Title', max_length=200)
    text = models.TextField('Text')
    _password = models.CharField('Password', max_length=100)

    def serialize_fields(self):
        return [
            'id',
            'title'
        ]

class ModelWithoutSerializeFields(models.Model):
    title = models.CharField('Title', max_length=200)
    text = models.TextField('Text')
    _password = models.CharField('Password', max_length=100)


class JsonResponseTest(unittest.TestCase):

    def setUp(self):
        self.testObj = { 'testval': 99, 'testStr': 'Ice Cone', 'today': datetime(2012, 5, 17) }
        self.jsonres = JsonResponse(self.testObj)

        self.modelWithSerializeFields = JsonResponse(ModelWithSerializeFields(title='Hadouken',
                                                                            text='is said repeatedly in Street Fighter',
                                                                            _password='is secret'))

        self.modelbaseWithoutSerializeFields = ModelWithoutSerializeFields(title='Hadouken',
                                                                        text='is said repeatedly in Street Fighter',
                                                                        _password='is secret')

        self.modelWithoutSerializeFields = JsonResponse(self.modelbaseWithoutSerializeFields)


    def testIsInstanceOfHttpResponse(self):
        self.assertTrue(isinstance(self.jsonres, HttpResponse), 'should be an instance of HttpResponse')
        self.assertTrue(isinstance(self.modelWithSerializeFields, HttpResponse), 'should be an instance of HttpResponse')
        self.assertTrue(isinstance(self.modelWithoutSerializeFields, HttpResponse), 'should be an instance of HttpResponse')

    def testSetsCorrectMimetype(self):
        self.assertEqual(self.jsonres['Content-Type'], 'application/json; charset=utf-8')
        self.assertEqual(self.modelWithSerializeFields['Content-Type'], 'application/json; charset=utf-8')
        self.assertEqual(self.modelWithoutSerializeFields['Content-Type'], 'application/json; charset=utf-8')

    def testDictContentConvertsToJson(self):
        result = simplejson.loads(self.jsonres.content)

        for key, value in result.items():
            self.assertEqual(self.testObj.get(key).__str__(), value.__str__())

    def testModelWithSerializeFieldsConvertsToJson(self):
        to_equal = { u'id': None, u'title': u'Hadouken' }
        result = simplejson.loads(self.modelWithSerializeFields.content)

        for key, value in result.items():
            self.assertEqual(to_equal.get(key).__str__(), value.__str__())

    def testModelWithoutSerializeFieldsConvertsToJson(self):
        to_equal = { u'text': u'is said repeatedly in Street Fighter', u'title': u'Hadouken', u'id': None }
        result = simplejson.loads(self.modelWithoutSerializeFields.content)

        for key, value in result.items():
            self.assertEqual(to_equal.get(key).__str__(), value.__str__())

    def testModelsWithDynamiclyAddedFieldsConvertsToJson(self):
        to_equal = { u'text': u'is said repeatedly in Street Fighter', u'title': u'Hadouken', u'id': None, u'dummy': u'blah' }

        self.modelbaseWithoutSerializeFields.dummy = "blah"
        self.modelbaseWithoutSerializeFields._dummy = "blah"
        result = simplejson.loads(JsonResponse(self.modelbaseWithoutSerializeFields).content)

        for key, value in result.items():
            self.assertEqual(to_equal.get(key).__str__(), value.__str__())

########NEW FILE########
__FILENAME__ = mock
# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2011 Michael Foord & the mock team
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 0.7.2
# http://www.voidspace.org.uk/python/mock/

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.


__all__ = (
    'Mock',
    'MagicMock',
    'mocksignature',
    'patch',
    'patch_object',
    'sentinel',
    'DEFAULT'
)

__version__ = '0.7.2'

__unittest = True


import sys
import warnings

try:
    import inspect
except ImportError:
    # for alternative platforms that
    # may not have inspect
    inspect = None

try:
    BaseException
except NameError:
    # Python 2.4 compatibility
    BaseException = Exception

try:
    from functools import wraps
except ImportError:
    # Python 2.4 compatibility
    def wraps(original):
        def inner(f):
            f.__name__ = original.__name__
            f.__doc__ = original.__doc__
            f.__module__ = original.__module__
            return f
        return inner

try:
    unicode
except NameError:
    # Python 3
    basestring = unicode = str

try:
    long
except NameError:
    # Python 3
    long = int

inPy3k = sys.version_info[0] == 3

if inPy3k:
    self = '__self__'
else:
    self = 'im_self'


# getsignature and mocksignature heavily "inspired" by
# the decorator module: http://pypi.python.org/pypi/decorator/
# by Michele Simionato

def _getsignature(func, skipfirst):
    if inspect is None:
        raise ImportError('inspect module not available')

    if inspect.isclass(func):
        func = func.__init__
        # will have a self arg
        skipfirst = True
    elif not (inspect.ismethod(func) or inspect.isfunction(func)):
        func = func.__call__

    regargs, varargs, varkwargs, defaults = inspect.getargspec(func)

    # instance methods need to lose the self argument
    if getattr(func, self, None) is not None:
        regargs = regargs[1:]

    _msg = "_mock_ is a reserved argument name, can't mock signatures using _mock_"
    assert '_mock_' not in regargs, _msg
    if varargs is not None:
        assert '_mock_' not in varargs, _msg
    if varkwargs is not None:
        assert '_mock_' not in varkwargs, _msg
    if skipfirst:
        regargs = regargs[1:]
    signature = inspect.formatargspec(regargs, varargs, varkwargs, defaults,
                                      formatvalue=lambda value: "")
    return signature[1:-1], func


def _copy_func_details(func, funcopy):
    funcopy.__name__ = func.__name__
    funcopy.__doc__ = func.__doc__
    funcopy.__dict__.update(func.__dict__)
    funcopy.__module__ = func.__module__
    if not inPy3k:
        funcopy.func_defaults = func.func_defaults
    else:
        funcopy.__defaults__ = func.__defaults__
        funcopy.__kwdefaults__ = func.__kwdefaults__


def mocksignature(func, mock=None, skipfirst=False):
    """
    mocksignature(func, mock=None, skipfirst=False)

    Create a new function with the same signature as `func` that delegates
    to `mock`. If `skipfirst` is True the first argument is skipped, useful
    for methods where `self` needs to be omitted from the new function.

    If you don't pass in a `mock` then one will be created for you.

    The mock is set as the `mock` attribute of the returned function for easy
    access.

    `mocksignature` can also be used with classes. It copies the signature of
    the `__init__` method.

    When used with callable objects (instances) it copies the signature of the
    `__call__` method.
    """
    if mock is None:
        mock = Mock()
    signature, func = _getsignature(func, skipfirst)
    src = "lambda %(signature)s: _mock_(%(signature)s)" % {
        'signature': signature
    }

    funcopy = eval(src, dict(_mock_=mock))
    _copy_func_details(func, funcopy)
    funcopy.mock = mock
    return funcopy


def _is_magic(name):
    return '__%s__' % name[2:-2] == name


class SentinelObject(object):
    "A unique, named, sentinel object."
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<SentinelObject "%s">' % self.name


class Sentinel(object):
    """Access attributes to return a named object, usable as a sentinel."""
    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        if name == '__bases__':
            # Without this help(mock) raises an exception
            raise AttributeError
        return self._sentinels.setdefault(name, SentinelObject(name))


sentinel = Sentinel()

DEFAULT = sentinel.DEFAULT


class OldStyleClass:
    pass
ClassType = type(OldStyleClass)


def _copy(value):
    if type(value) in (dict, list, tuple, set):
        return type(value)(value)
    return value


if inPy3k:
    class_types = type
else:
    class_types = (type, ClassType)


class Mock(object):
    """
    Create a new ``Mock`` object. ``Mock`` takes several optional arguments
    that specify the behaviour of the Mock object:

    * ``spec``: This can be either a list of strings or an existing object (a
      class or instance) that acts as the specification for the mock object. If
      you pass in an object then a list of strings is formed by calling dir on
      the object (excluding unsupported magic attributes and methods). Accessing
      any attribute not in this list will raise an ``AttributeError``.

      If ``spec`` is an object (rather than a list of strings) then
      `mock.__class__` returns the class of the spec object. This allows mocks
      to pass `isinstance` tests.

    * ``spec_set``: A stricter variant of ``spec``. If used, attempting to *set*
      or get an attribute on the mock that isn't on the object passed as
      ``spec_set`` will raise an ``AttributeError``.

    * ``side_effect``: A function to be called whenever the Mock is called. See
      the :attr:`Mock.side_effect` attribute. Useful for raising exceptions or
      dynamically changing return values. The function is called with the same
      arguments as the mock, and unless it returns :data:`DEFAULT`, the return
      value of this function is used as the return value.

      Alternatively ``side_effect`` can be an exception class or instance. In
      this case the exception will be raised when the mock is called.

    * ``return_value``: The value returned when the mock is called. By default
      this is a new Mock (created on first access). See the
      :attr:`Mock.return_value` attribute.

    * ``wraps``: Item for the mock object to wrap. If ``wraps`` is not None
      then calling the Mock will pass the call through to the wrapped object
      (returning the real result and ignoring ``return_value``). Attribute
      access on the mock will return a Mock object that wraps the corresponding
      attribute of the wrapped object (so attempting to access an attribute that
      doesn't exist will raise an ``AttributeError``).

      If the mock has an explicit ``return_value`` set then calls are not passed
      to the wrapped object and the ``return_value`` is returned instead.

    * ``name``: If the mock has a name then it will be used in the repr of the
      mock. This can be useful for debugging. The name is propagated to child
      mocks.
    """
    def __new__(cls, *args, **kw):
        # every instance has its own class
        # so we can create magic methods on the
        # class without stomping on other mocks
        new = type(cls.__name__, (cls,), {'__doc__': cls.__doc__})
        return object.__new__(new)


    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT,
                    wraps=None, name=None, spec_set=None, parent=None):
        self._parent = parent
        self._name = name
        _spec_class = None
        if spec_set is not None:
            spec = spec_set
            spec_set = True

        if spec is not None and type(spec) is not list:
            if isinstance(spec, class_types):
                _spec_class = spec
            else:
                _spec_class = spec.__class__
            spec = dir(spec)

        self._spec_class = _spec_class
        self._spec_set = spec_set
        self._methods = spec
        self._children = {}
        self._return_value = return_value
        self.side_effect = side_effect
        self._wraps = wraps

        self.reset_mock()


    @property
    def __class__(self):
        if self._spec_class is None:
            return type(self)
        return self._spec_class


    def reset_mock(self):
        "Restore the mock object to its initial state."
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.call_args_list = []
        self.method_calls = []
        for child in self._children.values():
            child.reset_mock()
        if isinstance(self._return_value, Mock):
            if not self._return_value is self:
                self._return_value.reset_mock()


    def __get_return_value(self):
        if self._return_value is DEFAULT:
            self._return_value = self._get_child_mock()
        return self._return_value

    def __set_return_value(self, value):
        self._return_value = value

    __return_value_doc = "The value to be returned when the mock is called."
    return_value = property(__get_return_value, __set_return_value,
                            __return_value_doc)


    def __call__(self, *args, **kwargs):
        self.called = True
        self.call_count += 1
        self.call_args = callargs((args, kwargs))
        self.call_args_list.append(callargs((args, kwargs)))

        parent = self._parent
        name = self._name
        while parent is not None:
            parent.method_calls.append(callargs((name, args, kwargs)))
            if parent._parent is None:
                break
            name = parent._name + '.' + name
            parent = parent._parent

        ret_val = DEFAULT
        if self.side_effect is not None:
            if (isinstance(self.side_effect, BaseException) or
                isinstance(self.side_effect, class_types) and
                issubclass(self.side_effect, BaseException)):
                raise self.side_effect

            ret_val = self.side_effect(*args, **kwargs)
            if ret_val is DEFAULT:
                ret_val = self.return_value

        if self._wraps is not None and self._return_value is DEFAULT:
            return self._wraps(*args, **kwargs)
        if ret_val is DEFAULT:
            ret_val = self.return_value
        return ret_val


    def __getattr__(self, name):
        if name == '_methods':
            raise AttributeError(name)
        elif self._methods is not None:
            if name not in self._methods or name in _all_magics:
                raise AttributeError("Mock object has no attribute '%s'" % name)
        elif _is_magic(name):
            raise AttributeError(name)

        if name not in self._children:
            wraps = None
            if self._wraps is not None:
                wraps = getattr(self._wraps, name)
            self._children[name] = self._get_child_mock(parent=self, name=name, wraps=wraps)

        return self._children[name]


    def __repr__(self):
        if self._name is None and self._spec_class is None:
            return object.__repr__(self)

        name_string = ''
        spec_string = ''
        if self._name is not None:
            def get_name(name):
                if name is None:
                    return 'mock'
                return name
            parent = self._parent
            name = self._name
            while parent is not None:
                name = get_name(parent._name) + '.' + name
                parent = parent._parent
            name_string = ' name=%r' % name
        if self._spec_class is not None:
            spec_string = ' spec=%r'
            if self._spec_set:
                spec_string = ' spec_set=%r'
            spec_string = spec_string % self._spec_class.__name__
        return "<%s%s%s id='%s'>" % (type(self).__name__,
                                      name_string,
                                      spec_string,
                                      id(self))


    def __setattr__(self, name, value):
        if not 'method_calls' in self.__dict__:
            # allow all attribute setting until initialisation is complete
            return object.__setattr__(self, name, value)
        if (self._spec_set and self._methods is not None and name not in
            self._methods and name not in self.__dict__ and
            name != 'return_value'):
            raise AttributeError("Mock object has no attribute '%s'" % name)
        if name in _unsupported_magics:
            msg = 'Attempting to set unsupported magic method %r.' % name
            raise AttributeError(msg)
        elif name in _all_magics:
            if self._methods is not None and name not in self._methods:
                raise AttributeError("Mock object has no attribute '%s'" % name)

            if not isinstance(value, Mock):
                setattr(type(self), name, _get_method(name, value))
                original = value
                real = lambda *args, **kw: original(self, *args, **kw)
                value = mocksignature(value, real, skipfirst=True)
            else:
                setattr(type(self), name, value)
        return object.__setattr__(self, name, value)


    def __delattr__(self, name):
        if name in _all_magics and name in type(self).__dict__:
            delattr(type(self), name)
        return object.__delattr__(self, name)


    def assert_called_with(self, *args, **kwargs):
        """
        assert that the mock was called with the specified arguments.

        Raises an AssertionError if the args and keyword args passed in are
        different to the last call to the mock.
        """
        if self.call_args is None:
            raise AssertionError('Expected: %s\nNot called' % ((args, kwargs),))
        if not self.call_args == (args, kwargs):
            raise AssertionError(
                'Expected: %s\nCalled with: %s' % ((args, kwargs), self.call_args)
            )


    def assert_called_once_with(self, *args, **kwargs):
        """
        assert that the mock was called exactly once and with the specified
        arguments.
        """
        if not self.call_count == 1:
            msg = ("Expected to be called once. Called %s times." %
                   self.call_count)
            raise AssertionError(msg)
        return self.assert_called_with(*args, **kwargs)


    def _get_child_mock(self, **kw):
        klass = type(self).__mro__[1]
        return klass(**kw)



class callargs(tuple):
    """
    A tuple for holding the results of a call to a mock, either in the form
    `(args, kwargs)` or `(name, args, kwargs)`.

    If args or kwargs are empty then a callargs tuple will compare equal to
    a tuple without those values. This makes comparisons less verbose::

        callargs('name', (), {}) == ('name',)
        callargs('name', (1,), {}) == ('name', (1,))
        callargs((), {'a': 'b'}) == ({'a': 'b'},)
    """
    def __eq__(self, other):
        if len(self) == 3:
            if other[0] != self[0]:
                return False
            args_kwargs = self[1:]
            other_args_kwargs = other[1:]
        else:
            args_kwargs = tuple(self)
            other_args_kwargs = other

        if len(other_args_kwargs) == 0:
            other_args, other_kwargs = (), {}
        elif len(other_args_kwargs) == 1:
            if isinstance(other_args_kwargs[0], tuple):
                other_args = other_args_kwargs[0]
                other_kwargs = {}
            else:
                other_args = ()
                other_kwargs = other_args_kwargs[0]
        else:
            other_args, other_kwargs = other_args_kwargs

        return tuple(args_kwargs) == (other_args, other_kwargs)


def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


class _patch(object):
    def __init__(self, target, attribute, new, spec, create,
                    mocksignature, spec_set):
        self.target = target
        self.attribute = attribute
        self.new = new
        self.spec = spec
        self.create = create
        self.has_local = False
        self.mocksignature = mocksignature
        self.spec_set = spec_set


    def copy(self):
        return _patch(self.target, self.attribute, self.new, self.spec,
                        self.create, self.mocksignature, self.spec_set)


    def __call__(self, func):
        if isinstance(func, class_types):
            return self.decorate_class(func)
        else:
            return self.decorate_callable(func)


    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if attr.startswith("test") and hasattr(attr_value, "__call__"):
                setattr(klass, attr, self.copy()(attr_value))
        return klass


    def decorate_callable(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        @wraps(func)
        def patched(*args, **keywargs):
            # don't use a with here (backwards compatability with 2.5)
            extra_args = []
            for patching in patched.patchings:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.append(arg)
            args += tuple(extra_args)
            try:
                return func(*args, **keywargs)
            finally:
                for patching in reversed(getattr(patched, 'patchings', [])):
                    patching.__exit__()

        patched.patchings = [self]
        if hasattr(func, 'func_code'):
            # not in Python 3
            patched.compat_co_firstlineno = getattr(func, "compat_co_firstlineno",
                                                    func.func_code.co_firstlineno)
        return patched


    def get_original(self):
        target = self.target
        name = self.attribute

        original = DEFAULT
        local = False

        try:
            original = target.__dict__[name]
        except (AttributeError, KeyError):
            original = getattr(target, name, DEFAULT)
        else:
            local = True

        if not self.create and original is DEFAULT:
            raise AttributeError("%s does not have the attribute %r" % (target, name))
        return original, local


    def __enter__(self):
        """Perform the patch."""
        new, spec, spec_set = self.new, self.spec, self.spec_set
        original, local = self.get_original()
        if new is DEFAULT:
            # XXXX what if original is DEFAULT - shouldn't use it as a spec
            inherit = False
            if spec_set == True:
                spec_set = original
                if isinstance(spec_set, class_types):
                    inherit = True
            elif spec == True:
                # set spec to the object we are replacing
                spec = original
                if isinstance(spec, class_types):
                    inherit = True
            new = Mock(spec=spec, spec_set=spec_set)
            if inherit:
                new.return_value = Mock(spec=spec, spec_set=spec_set)
        new_attr = new
        if self.mocksignature:
            new_attr = mocksignature(original, new)

        self.temp_original = original
        self.is_local = local
        setattr(self.target, self.attribute, new_attr)
        return new


    def __exit__(self, *_):
        """Undo the patch."""
        if self.is_local and self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
            if not self.create and not hasattr(self.target, self.attribute):
                # needed for proxy objects like django settings
                setattr(self.target, self.attribute, self.temp_original)

        del self.temp_original
        del self.is_local

    start = __enter__
    stop = __exit__


def _patch_object(target, attribute, new=DEFAULT, spec=None, create=False,
                  mocksignature=False, spec_set=None):
    """
    patch.object(target, attribute, new=DEFAULT, spec=None, create=False,
                 mocksignature=False, spec_set=None)

    patch the named member (`attribute`) on an object (`target`) with a mock
    object.

    Arguments new, spec, create, mocksignature and spec_set have the same
    meaning as for patch.
    """
    return _patch(target, attribute, new, spec, create, mocksignature,
                  spec_set)


def patch_object(*args, **kwargs):
    "A deprecated form of patch.object(...)"
    warnings.warn(('Please use patch.object instead.'), DeprecationWarning, 2)
    return _patch_object(*args, **kwargs)


def patch(target, new=DEFAULT, spec=None, create=False,
            mocksignature=False, spec_set=None):
    """
    ``patch`` acts as a function decorator, class decorator or a context
    manager. Inside the body of the function or with statement, the ``target``
    (specified in the form `'PackageName.ModuleName.ClassName'`) is patched
    with a ``new`` object. When the function/with statement exits the patch is
    undone.

    The ``target`` is imported and the specified attribute patched with the new
    object, so it must be importable from the environment you are calling the
    decorator from.

    If ``new`` is omitted, then a new ``Mock`` is created and passed in as an
    extra argument to the decorated function.

    The ``spec`` and ``spec_set`` keyword arguments are passed to the ``Mock``
    if patch is creating one for you.

    In addition you can pass ``spec=True`` or ``spec_set=True``, which causes
    patch to pass in the object being mocked as the spec/spec_set object.

    If ``mocksignature`` is True then the patch will be done with a function
    created by mocking the one being replaced. If the object being replaced is
    a class then the signature of `__init__` will be copied. If the object
    being replaced is a callable object then the signature of `__call__` will
    be copied.

    By default ``patch`` will fail to replace attributes that don't exist. If
    you pass in 'create=True' and the attribute doesn't exist, patch will
    create the attribute for you when the patched function is called, and
    delete it again afterwards. This is useful for writing tests against
    attributes that your production code creates at runtime. It is off by by
    default because it can be dangerous. With it switched on you can write
    passing tests against APIs that don't actually exist!

    Patch can be used as a TestCase class decorator. It works by
    decorating each test method in the class. This reduces the boilerplate
    code when your test methods share a common patchings set.

    Patch can be used with the with statement, if this is available in your
    version of Python. Here the patching applies to the indented block after
    the with statement. If you use "as" then the patched object will be bound
    to the name after the "as"; very useful if `patch` is creating a mock
    object for you.

    `patch.dict(...)` and `patch.object(...)` are available for alternate
    use-cases.
    """
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: %r" %
                        (target,))
    target = _importer(target)
    return _patch(target, attribute, new, spec, create, mocksignature, spec_set)


class _patch_dict(object):
    """
    Patch a dictionary and restore the dictionary to its original state after
    the test.

    `in_dict` can be a dictionary or a mapping like container. If it is a
    mapping then it must at least support getting, setting and deleting items
    plus iterating over keys.

    `in_dict` can also be a string specifying the name of the dictionary, which
    will then be fetched by importing it.

    `values` can be a dictionary of values to set in the dictionary. `values`
    can also be an iterable of ``(key, value)`` pairs.

    If `clear` is True then the dictionary will be cleared before the new
    values are set.
    """

    def __init__(self, in_dict, values=(), clear=False):
        if isinstance(in_dict, basestring):
            in_dict = _importer(in_dict)
        self.in_dict = in_dict
        # support any argument supported by dict(...) constructor
        self.values = dict(values)
        self.clear = clear
        self._original = None


    def __call__(self, f):
        if isinstance(f, class_types):
            return self.decorate_class(f)
        @wraps(f)
        def _inner(*args, **kw):
            self._patch_dict()
            try:
                return f(*args, **kw)
            finally:
                self._unpatch_dict()

        return _inner


    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if attr.startswith("test") and hasattr(attr_value, "__call__"):
                decorator = _patch_dict(self.in_dict, self.values, self.clear)
                decorated = decorator(attr_value)
                setattr(klass, attr, decorated)
        return klass


    def __enter__(self):
        """Patch the dict."""
        self._patch_dict()


    def _patch_dict(self):
        """Unpatch the dict."""
        values = self.values
        in_dict = self.in_dict
        clear = self.clear

        try:
            original = in_dict.copy()
        except AttributeError:
            # dict like object with no copy method
            # must support iteration over keys
            original = {}
            for key in in_dict:
                original[key] = in_dict[key]
        self._original = original

        if clear:
            _clear_dict(in_dict)

        try:
            in_dict.update(values)
        except AttributeError:
            # dict like object with no update method
            for key in values:
                in_dict[key] = values[key]


    def _unpatch_dict(self):
        in_dict = self.in_dict
        original = self._original

        _clear_dict(in_dict)

        try:
            in_dict.update(original)
        except AttributeError:
            for key in original:
                in_dict[key] = original[key]


    def __exit__(self, *args):
        self._unpatch_dict()
        return False

    start = __enter__
    stop = __exit__


def _clear_dict(in_dict):
    try:
        in_dict.clear()
    except AttributeError:
        keys = list(in_dict)
        for key in keys:
            del in_dict[key]


patch.object = _patch_object
patch.dict = _patch_dict


magic_methods = (
    "lt le gt ge eq ne "
    "getitem setitem delitem "
    "len contains iter "
    "hash str sizeof "
    "enter exit "
    "divmod neg pos abs invert "
    "complex int float index "
    "trunc floor ceil "
)

numerics = "add sub mul div truediv floordiv mod lshift rshift and xor or pow "
inplace = ' '.join('i%s' % n for n in numerics.split())
right = ' '.join('r%s' % n for n in numerics.split())
extra = ''
if inPy3k:
    extra = 'bool next '
else:
    extra = 'unicode long nonzero oct hex '
# __truediv__ and __rtruediv__ not available in Python 3 either

# not including __prepare__, __instancecheck__, __subclasscheck__
# (as they are metaclass methods)
# __del__ is not supported at all as it causes problems if it exists

_non_defaults = set('__%s__' % method for method in [
    'cmp', 'getslice', 'setslice', 'coerce', 'subclasses',
    'dir', 'format', 'get', 'set', 'delete', 'reversed',
    'missing', 'reduce', 'reduce_ex', 'getinitargs',
    'getnewargs', 'getstate', 'setstate', 'getformat',
    'setformat', 'repr'
])


def _get_method(name, func):
    "Turns a callable object (like a mock) into a real function"
    def method(self, *args, **kw):
        return func(self, *args, **kw)
    method.__name__ = name
    return method


_magics = set(
    '__%s__' % method for method in
    ' '.join([magic_methods, numerics, inplace, right, extra]).split()
)

_all_magics = _magics | _non_defaults

_unsupported_magics = set([
    '__getattr__', '__setattr__',
    '__init__', '__new__', '__prepare__'
    '__instancecheck__', '__subclasscheck__',
    '__del__'
])

_calculate_return_value = {
    '__hash__': lambda self: object.__hash__(self),
    '__str__': lambda self: object.__str__(self),
    '__sizeof__': lambda self: object.__sizeof__(self),
    '__unicode__': lambda self: unicode(object.__str__(self)),
}

_return_values = {
    '__int__': 1,
    '__contains__': False,
    '__len__': 0,
    '__iter__': iter([]),
    '__exit__': False,
    '__complex__': 1j,
    '__float__': 1.0,
    '__bool__': True,
    '__nonzero__': True,
    '__oct__': '1',
    '__hex__': '0x1',
    '__long__': long(1),
    '__index__': 1,
}


def _get_eq(self):
    def __eq__(other):
        ret_val = self.__eq__._return_value
        if ret_val is not DEFAULT:
            return ret_val
        return self is other
    return __eq__

def _get_ne(self):
    def __ne__(other):
        if self.__ne__._return_value is not DEFAULT:
            return DEFAULT
        return self is not other
    return __ne__

_side_effect_methods = {
    '__eq__': _get_eq,
    '__ne__': _get_ne,
}



def _set_return_value(mock, method, name):
    return_value = DEFAULT
    if name in _return_values:
        return_value = _return_values[name]
    elif name in _calculate_return_value:
        try:
            return_value = _calculate_return_value[name](mock)
        except AttributeError:
            return_value = AttributeError(name)
    elif name in _side_effect_methods:
        side_effect = _side_effect_methods[name](mock)
        method.side_effect = side_effect
    if return_value is not DEFAULT:
        method.return_value = return_value


class MagicMock(Mock):
    """
    MagicMock is a subclass of :Mock with default implementations
    of most of the magic methods. You can use MagicMock without having to
    configure the magic methods yourself.

    If you use the ``spec`` or ``spec_set`` arguments then *only* magic
    methods that exist in the spec will be created.

    Attributes and the return value of a `MagicMock` will also be `MagicMocks`.
    """
    def __init__(self, *args, **kw):
        Mock.__init__(self, *args, **kw)

        these_magics = _magics
        if self._methods is not None:
            these_magics = _magics.intersection(self._methods)

        for entry in these_magics:
            # could specify parent?
            m = Mock()
            setattr(self, entry, m)
            _set_return_value(self, m, entry)

########NEW FILE########
__FILENAME__ = response
import unittest

from django.conf import settings
from django.forms import Form
from django.template.base import TemplateDoesNotExist
from django.utils import simplejson
from mock import Mock

from dynamicresponse.response import *

class ConstantTest(unittest.TestCase):

    def test_constants(self):
        self.assertEqual(CR_OK, ('OK', 200))
        self.assertEqual(CR_INVALID_DATA, ('INVALID', 400))
        self.assertEqual(CR_NOT_FOUND, ('NOT_FOUND', 404))
        self.assertEqual(CR_CONFIRM, ('CONFIRM', 405))
        self.assertEqual(CR_DELETED, ('DELETED', 204))
        self.assertEqual(CR_REQUIRES_UPGRADE, ('REQUIRES_UPGRADE', 402))


class DynamicResponseTest(unittest.TestCase):

    def testSerializeReturnsJsonResponseWhenStatusIs200(self):
        dynRes = DynamicResponse()
        serialize_result = dynRes.serialize()

        self.assertTrue(isinstance(serialize_result, JsonResponse), 'Serialized result should be an instance of JsonResponse')
        self.assertTrue(isinstance(serialize_result, HttpResponse), 'Serialized result should be an instance of HttpResponse')
        self.assertEqual(serialize_result.status_code, 200)

    def testSerializeReturnsHttpResponseWhenStatusIs400AndSettingsSpecifyErrorReportingAndNoErrors(self):
        dynRes = DynamicResponse(status=CR_INVALID_DATA)
        settings.DYNAMICRESPONSE_JSON_FORM_ERRORS = True
        serialize_result = dynRes.serialize()

        self.assertTrue(isinstance(serialize_result, HttpResponse), 'Serialized result should be a HttpResponse with correct setting and status: 400')
        self.assertEqual(serialize_result.status_code, 400)

    def testJsonResponseWithStatus400ReturnErrorsWhenSettingsSpecifyErrorReporting(self):
        settings.DYNAMICRESPONSE_JSON_FORM_ERRORS = True
        simple_form = Form()
        simple_form.is_valid = Mock(return_value=False)
        simple_form.errors[u'SimpleError'] = u'This was a very simple error, shame on you'
        simple_form.errors[u'Error2'] = u'This was a bit more serious'

        should_equal = simplejson.dumps({'field_errors': simple_form.errors}, indent=0)

        dynRes = DynamicResponse({}, extra={ 'form': simple_form }, status=CR_INVALID_DATA)
        serialized_result = dynRes.serialize()

        self.assertTrue(isinstance(serialized_result, JsonResponse))
        self.assertEqual(should_equal, serialized_result.content, 'Correct error message is not returned from JsonResponse')

    def testFullContextReturnsContextMergedWithExtraContext(self):
        testContext = {"testNum": 5, "word": "bird", "beach": 10}
        testExtraContext = {"extra": True, "blue?": False}
        dynResNoExtra = DynamicResponse(testContext)
        dynResWithExtra = DynamicResponse(testContext, extra=testExtraContext)

        for key, value in dynResNoExtra.full_context().items():
            self.assertEqual(testContext[key], value)

        for key, value in dynResWithExtra.full_context().items():
            self.assertTrue(testContext.get(key) == value or testExtraContext.get(key) == value,
                            'full_context apperantly did not merge context and extra_context')


class SerializeOrRenderTest(unittest.TestCase):

    def setUp(self):
        self.sor = SerializeOrRender("invalidtemplate")
        self.sor.serialize = Mock(return_value=HttpResponse())

        self.request = Mock()


    def testIsInstanceOfDynamicResponse(self):
        self.assertTrue(isinstance(self.sor, DynamicResponse), 'Should be an instance of DynamicResponse')

    def testRenderResponseCallsSerializeIfRequestIsApiIsTrue(self):
        self.request.is_api = True

        result = self.sor.render_response(self.request, "unused_variable")

        self.assertTrue(self.sor.serialize.called, 'serialize was not called')
        self.assertTrue(isinstance(result, HttpResponse), 'should return an instance of HttpResponse')

    def testRenderResponseCallsDjangoRenderToResponseIfRequestIsApiIsFalse(self):
        self.request.is_api = False
        tried_rendering_template = False

        try:
            self.sor.render_response(self.request, "unused_variable")
        except TemplateDoesNotExist, templatestr:
            self.assertTrue(templatestr.__str__() == "invalidtemplate")
            tried_rendering_template = True

        self.assertTrue(tried_rendering_template, 'render_to_response was not called')

    def testRenderResponseAttachesSelfsExtraHeadersToReturnElement(self):
        self.sor.extra_headers = { 'testh': 1, 'testh2': 2, 'testh3': 3 }
        result = self.sor.render_response(self.request, "unused_variable")

        for header in self.sor.extra_headers:
            self.assertTrue(result.has_header(header), 'apperently did not merge extra_headers with headers')


class SerializeOrRedirectTest(unittest.TestCase):

    def setUp(self):
        self.sor = SerializeOrRedirect("invalidurl")
        self.sor.serialize = Mock(return_value=HttpResponse())

        self.request = Mock()


    def testIsInstanceOfDynamicResponse(self):
        self.assertTrue(isinstance(self.sor, DynamicResponse), 'Should be an instance of DynamicResponse')

    def testRenderResponseCallsSerializeIfRequestIsApiIsTrue(self):
        self.request.is_api = True

        result = self.sor.render_response(self.request, "unused_variable")

        self.assertTrue(self.sor.serialize.called, 'serialize was not called')
        self.assertTrue(isinstance(result, HttpResponse), 'should return an instance of HttpResponse')

    def testRenderResponseReturnsHttpResponseRedirectIfRequestIsApiIsFalse(self):
        self.request.is_api = False

        result = self.sor.render_response(self.request, "unused_variable")

        self.assertTrue(isinstance(result, HttpResponseRedirect), 'should return an instance of HttpResponseRedirect')

    def testRenderResponseAttachesSelfsExtraHeadersToReturnElement(self):
        self.sor.extra_headers = { 'testh': 1, 'testh2': 2, 'testh3': 3 }
        result = self.sor.render_response(self.request, "unused_variable")

        for header in self.sor.extra_headers:
            self.assertTrue(result.has_header(header), 'apperently did not merge extra_headers with headers')


class SerializeTest(unittest.TestCase):

    def setUp(self):
        self.ser = Serialize()
        self.ser.serialize = Mock(return_value=HttpResponse())

        self.request = Mock()


    def testIsInstanceOfDynamicResponse(self):
        self.assertTrue(isinstance(self.ser, DynamicResponse), 'Should be an instance of DynamicResponse')

    def testRenderResponseCallsSerialize(self):
        result = self.ser.render_response(self.request, "unused_variable")

        self.assertTrue(self.ser.serialize.called, 'serialize was not called')
        self.assertTrue(isinstance(result, HttpResponse), 'should return an instance of HttpResponse')

    def testRenderResponseAttachesSelfsExtraHeadersToReturnElement(self):
        self.ser.extra_headers = { 'testh': 1, 'testh2': 2, 'testh3': 3 }
        result = self.ser.render_response(self.request, "unused_variable")

        for header in self.ser.extra_headers:
            self.assertTrue(result.has_header(header), 'extra_headers has apparently not been merged with headers')

########NEW FILE########
__FILENAME__ = views
# encoding=utf-8
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson

from blog.models import BlogPost

class ViewTests(TestCase):
    """
    Test the views as regular Django views.
    """

    def setUp(self):

        # Create an initial object to test with
        post = BlogPost(title=u'Hello Wørld', text=u'Hello World, this is dynamicresponse. ÆØÅæøå.')
        post.save()

        self.post = post

    def testListPosts(self):
        """
        Test the list_posts view.
        """

        response = self.client.get(reverse('list_posts'))

        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/list_posts.html')
        self.assertTrue(self.post in response.context['posts'])

    def testCreatePost(self):
        """
        Test the post view, creating a new entry.
        """

        response = self.client.get(reverse('create_post'))

        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/post.html')
        self.assertTrue('form' in response.context)

        # Create a new post
        response = self.client.post(reverse('create_post'), {
            'title': u'Hello Mr. ÆØÅæøå',
            'text': u'How nice to finally meet you.',
        })

        self.assertRedirects(response, reverse('list_posts'))

        # Check the newly created object
        self.assertTrue(BlogPost.objects.filter(id=2).exists())

        new_post = BlogPost.objects.get(id=2)
        self.assertEquals(new_post.title, u'Hello Mr. ÆØÅæøå')
        self.assertEquals(new_post.text, u'How nice to finally meet you.')

    def testPostDetailAndEdit(self):
        """
        Test the post view with existing post, updating it.
        """

        response = self.client.get(reverse('post', kwargs={'post_id': self.post.id}))

        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/post.html')
        self.assertEquals(self.post, response.context['post'])
        self.assertTrue('form' in response.context)

        # Edit post with invalid data
        response = self.client.post(reverse('post', kwargs={'post_id': self.post.id}), {})
        self.assertEquals(response.status_code, 200)
        self.assertTrue('form' in response.context)
        self.assertFalse(response.context['form'].is_valid())

        # Edit post with valid data
        response = self.client.post(reverse('post', kwargs={'post_id': self.post.id}), {
            'title': u'Brand new title',
            'text': u'Now with more swag. Før real.',
        })

        self.assertRedirects(response, reverse('list_posts'))

        # Check the newly edited object
        new_post = BlogPost.objects.get(id=self.post.id)
        self.assertEquals(new_post.title, u'Brand new title')
        self.assertEquals(new_post.text, u'Now with more swag. Før real.')

    def testPostDelete(self):
        """
        Test the delete_post view.
        """

        response = self.client.get(reverse('delete_post', kwargs={'post_id': self.post.id}))

        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/delete_post.html')
        self.assertEquals(self.post, response.context['post'])

        # Delete the post
        post_id = self.post.id

        response = self.client.post(reverse('delete_post', kwargs={'post_id': post_id}))
        self.assertRedirects(response, reverse('list_posts'))

        with self.assertRaises(BlogPost.DoesNotExist):
            BlogPost.objects.get(id=post_id)

class ViewJSONTests(TestCase):
    """
    Test all the views with JSON input and ouput.
    """

    def setUp(self):

        # Headers for GET requests
        self.extra_headers = {
            'HTTP_ACCEPT': 'application/json'
        }

        # Create an initial object to test with
        post = BlogPost(title=u'Hello Wørld', text=u'Hello World, this is dynamicresponse. ÆØÅæøå.')
        post.save()

        self.post = post

    def testListPosts(self):
        """
        Test the list_posts view.
        """

        response = self.client.get(reverse('list_posts'), **self.extra_headers)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json; charset=utf-8')

        # Load JSON and check dictionary
        data = simplejson.loads(response.content)
        self.assertTrue('posts' in data)
        self.assertEquals(data['posts'][0]['id'], 1)

    def testCreatePost(self):
        """
        Test the post view, creating a new entry.
        """

        response = self.client.get(reverse('create_post'), **self.extra_headers)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json; charset=utf-8')

        data_json = u"""
            {
                "title": "Hello Mr. ÆØÅæøå",
                "text": "Lorem ipsum dolor sit amet"
            }
        """

        # Create a new post
        response = self.client.post(reverse('create_post'), data_json, content_type='application/json', **self.extra_headers)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json; charset=utf-8')

        # Check the newly created object
        self.assertTrue(BlogPost.objects.filter(id=2).exists())

        new_post = BlogPost.objects.get(id=2)
        self.assertEquals(new_post.title, u'Hello Mr. ÆØÅæøå')
        self.assertEquals(new_post.text, u'Lorem ipsum dolor sit amet')

    def testPostDetailAndEdit(self):
        """
        Test the post view with existing post, updating it.
        """

        response = self.client.get(reverse('post', kwargs={'post_id': self.post.id}), **self.extra_headers)

        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json; charset=utf-8')

        # Load JSON and check dictionary
        data = simplejson.loads(response.content)
        self.assertTrue('post' in data)
        self.assertEquals(data['post']['id'], 1)

        # Edit post with invalid data
        data_json_invalid = u"""
            {
                "foo": "bar"
            }
        """

        # Without JSON error output
        response = self.client.post(reverse('post', kwargs={'post_id': self.post.id}), data_json_invalid, content_type='application/json', **self.extra_headers)

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response['Content-Type'], 'application/json; charset=utf-8')

        # With JSON error output
        settings.DYNAMICRESPONSE_JSON_FORM_ERRORS = True
        response = self.client.post(reverse('post', kwargs={'post_id': self.post.id}), data_json_invalid, content_type='application/json', **self.extra_headers)

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response['Content-Type'], 'application/json; charset=utf-8')

        # Edit post with valid data
        data_json_valid = u"""
            {
                "title": "Brand new title",
                "text": "This is now edited."
            }
        """

        response = self.client.post(reverse('post', kwargs={'post_id': self.post.id}), data_json_valid, content_type='application/json', **self.extra_headers)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json; charset=utf-8')

        # Check the newly edited object
        new_post = BlogPost.objects.get(id=self.post.id)
        self.assertEquals(new_post.title, u'Brand new title')
        self.assertEquals(new_post.text, u'This is now edited.')

    def testPostDelete(self):
        """
        Test the delete_post view.
        """

        response = self.client.get(reverse('delete_post', kwargs={'post_id': self.post.id}), **self.extra_headers)
        self.assertEquals(response.status_code, 405)

        # Delete the post
        post_id = self.post.id

        response = self.client.post(reverse('delete_post', kwargs={'post_id': post_id}), content_type='application/json', **self.extra_headers)
        self.assertEquals(response.status_code, 204)

        with self.assertRaises(BlogPost.DoesNotExist):
            BlogPost.objects.get(id=post_id)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('myblog.blog.views',
    url(r'^$', 'list_posts', name='list_posts'),
    url(r'^create/$', 'post', name='create_post'),
    url(r'^(?P<post_id>\d+)/$', 'post', name='post'),
    url(r'^(?P<post_id>\d+)/delete/$', 'delete_post', name='delete_post'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from dynamicresponse.response import *

from forms import BlogPostForm
from models import BlogPost

def list_posts(request):
    """
    Lists all blog post.
    """
    
    posts = BlogPost.objects.all()
    return SerializeOrRender('blog/list_posts.html', { 'posts': posts })

def post(request, post_id=None):
    """
    Displays, creates or updates a blog post.
    """
    
    post = None
    if post_id:
        post = get_object_or_404(BlogPost.objects.all(), pk=post_id)
    
    if request.method == 'POST':
        
        form = BlogPostForm(request.POST, instance=post)
        
        if form.is_valid():
            post = form.save()
            return SerializeOrRedirect(reverse('list_posts'), { 'post': post })
            
        else:
            
            return SerializeOrRender('blog/post.html', { 'post': post }, extra = { 'form': form }, status=CR_INVALID_DATA)    
        
    else:
        
        form = BlogPostForm(instance=post)
    
    return SerializeOrRender('blog/post.html', { 'post': post }, extra={ 'form': form })

def delete_post(request, post_id):
    """
    Deletes the blog post.
    """
    
    post = get_object_or_404(BlogPost.objects.all(), pk=post_id)
    
    if request.method == 'POST':
        
        post.delete()
        return SerializeOrRedirect(reverse('list_posts'), {}, status=CR_DELETED)
    
    return SerializeOrRender('blog/delete_post.html', { 'post': post }, status=CR_CONFIRM)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for blog project.
import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'myblog.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'yfn#e4l95-!35ox47c4t+gu*eandf1gvmhf96wxc4f%1=b#vcc'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'dynamicresponse.middleware.api.APIMiddleware',
    'dynamicresponse.middleware.dynamicformat.DynamicFormatMiddleware',
)

ROOT_URLCONF = 'myblog.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'myblog.blog',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^', include('myblog.blog.urls')),
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
