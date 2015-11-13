__FILENAME__ = decorators
from datetime import datetime

from django.http import HttpResponse

from .signature import calculate_signature
from ..utils.decorators import wrap_object
from ..exceptions import HttpError


def auth_required(secret_key_func):
    """
    Requires that the user be authenticated either by a signature or by
    being actively logged in.
    """
    def actual_decorator(obj):

        def test_func(request, *args, **kwargs):
            secret_key = secret_key_func(request, *args, **kwargs)
            return validate_signature(request, secret_key) or request.user.is_authenticated()

        decorator = request_passes_test(test_func)
        return wrap_object(obj, decorator)

    return actual_decorator


def login_required(obj):
    """
    Requires that the user be logged in order to gain access to the resource
    at the specified the URI.
    """
    decorator = request_passes_test(lambda r, *args, **kwargs: r.user.is_authenticated())
    return wrap_object(obj, decorator)


def admin_required(obj):
    """
    Requires that the user be logged AND be set as a superuser
    """
    decorator = request_passes_test(lambda r, *args, **kwargs: r.user.is_superuser)
    return wrap_object(obj, decorator)


def signature_required(secret_key_func):
    """
    Requires that the request contain a valid signature to gain access
    to a specified resource.
    """
    def actual_decorator(obj):

        def test_func(request, *args, **kwargs):
            secret_key = secret_key_func(request, *args, **kwargs)
            return validate_signature(request, secret_key)

        decorator = request_passes_test(test_func)
        return wrap_object(obj, decorator)

    return actual_decorator


def request_passes_test(test_func, message=None, status=401):
    """
    Decorator for resources that checks that the request passes the given test.
    If the request fails the test a 401 (Unauthorized) response is returned,
    otherwise the view is executed normally. The test should be a callable that
    takes an HttpRequest object and any number of positional and keyword
    arguments as defined by the urlconf entry for the decorated resource.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not test_func(request, *args, **kwargs):
                raise HttpError(message=message, status=status)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def validate_signature(request, secret_key):
    """
    Validates the signature associated with the given request.
    """

    # Extract the request parameters according to the HTTP method
    data = request.GET.copy()
    if request.method != 'GET':
        message_body = getattr(request, request.method, {})
        data.update(message_body)

    # Make sure the request contains a signature
    if data.get('sig', False):
        sig = data['sig']
        del data['sig']
    else:
        return False

    # Make sure the request contains a timestamp
    if data.get('t', False):
        timestamp = int(data.get('t', False))
        del data['t']
    else:
        return False

    # Make sure the signature has not expired
    delta = datetime.utcnow() - datetime.utcfromtimestamp(timestamp)
    if delta.seconds > 5 * 60:  # If the signature is older than 5 minutes, it's invalid
        return False

    # Make sure the signature is valid
    return sig == calculate_signature(secret_key, data, timestamp)

########NEW FILE########
__FILENAME__ = signature
import time
import hmac
import hashlib


def calculate_signature(key, data, timestamp=None):
    """
    Calculates the signature for the given request data.
    """
    # Create a timestamp if one was not given
    if timestamp is None:
        timestamp = int(time.time())

    # Construct the message from the timestamp and the data in the request
    message = str(timestamp) + ''.join("%s%s" % (k,v) for k,v in sorted(data.items()))

    # Calculate the signature (HMAC SHA256) according to RFC 2104
    signature = hmac.HMAC(str(key), message, hashlib.sha256).hexdigest()

    return signature

########NEW FILE########
__FILENAME__ = exceptions
class HttpError(Exception):
    def __init__(self, message=None, status=500):
        super(HttpError, self).__init__(message)
        self.status = status

    def __repr__(self):
        return 'HttpError(%r, %r)' % (self.status, self.message)

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm as DjangoModelForm
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import NOT_PROVIDED


class ModelForm(DjangoModelForm):
    """
    Allows a model form to validate properly with default attributes missing.

    Django model forms expect all attributes for a given model to be present
    in a request. Since a typical request comes from an HTML form and the HTML
    for that form is typically generated by the form object (which sets all
    of the HTML form values to the defaults of the model), this is usually not
    an issue. However, with RESTful requests, we cannot assume that all
    attributes will be present in the request.

    This class allows the form to validate even if some (optional) attributes
    are not present in the original request. It does so by adding the default
    values (from the model) to the data from the request for each missing
    attribute. It must add these elements to the data object, as opposed to
    just passing it to the form's __init__ method as the 'initial' parameter
    since 'initial' is only used to render the HTML form and not for the
    validation of the data.

    UPDATE:
    This mixin has been updated to also populate form with values from an
    instance, if one has been provided.
    Note: this has not yet been tested, and likely does not work, on
    many-to-many relationships.
    """

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)

        # Make sure the data is editable and that we are not altering the
        # original object
        data = {}
        for k, v in self.data.items():
            data[k] = v
        self.data = data

        for field in self.instance.__class__._meta.fields:
            if field.name not in self.data.keys() or self.data.get(field.name) == None:
                inst_val = None
                if self.instance.id:
                    try:
                        inst_val = getattr(self.instance, field.name)
                        #Get the ID if this is a model object and
                        #we're dealing with a foreign key
                        #relationship.
                        inst_val = getattr(inst_val, 'id')
                    except (AttributeError, ObjectDoesNotExist):
                        pass
                    self.data[field.name] = inst_val
                elif field.default != NOT_PROVIDED:
                    self.data[field.name] = field.default

########NEW FILE########
__FILENAME__ = urlencode
from optparse import make_option
import calendar, datetime
import urllib

from django.core.management.base import BaseCommand
from ...auth.signature import calculate_signature


class Command(BaseCommand):
    help = """URL encode the given data.

Returns a URL encoded string for the given set of data. If a secret key is
specified, the secure signature is also calculated and added to the result."""

    args = "secret_key [key=value key=value ...]"

    option_list = BaseCommand.option_list + (
        make_option('--secret-key',
            dest='secret-key',
            action='store',
            help='Calculate the secure signature with the secret key'),
        )

    def handle(self, *data, **options):
        # Convert the data from a list of key, value pairs to a dict
        data = dict(item.split('=') for item in data)

        # Get the secret key if one was provided
        secret_key = options.get('secret-key', None)

        if secret_key:
            # If the timestamp was specified, use it and remove it from the data
            # before calculating the signature, otherwise, the time use will be
            # now in UTC time.
            timestamp = data.pop('t', None)
            if timestamp:
                timestamp = int(timestamp)
            else:
                dt = datetime.datetime.utcnow()
                timestamp = calendar.timegm(dt.timetuple())
            signature = calculate_signature(secret_key, data, timestamp)
            data['t'] = timestamp
            data['sig'] = signature

        print urllib.urlencode(data)

########NEW FILE########
__FILENAME__ = models
# Just here to make sure that Django stays happy

########NEW FILE########
__FILENAME__ = resource
from django.http import HttpResponse
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

from .exceptions import HttpError


class Resource(View):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        # Technically, the HTTP spec does not preclude any HTTP request from
        # containing data in the message body, so load the data into the POST
        # dict if there is any present
        method = request.method
        request.method = 'POST'
        request._load_post_and_files()

        # Now that message body has been loaded, check for a method override
        method_override = None
        if request.GET and request.GET.get('_method', None):
            request.GET._mutable = True
            method_override = request.GET.pop('_method')[0].upper()
            request.GET._mutable = False
        elif request.POST and request.POST.get('_method', None):
            request.POST._mutable = True
            method_override = request.POST.pop('_method')[0].upper()
            request.POST._mutable = False

        # Set the HTTP method on the request according to the override first
        # if one exists, and if not, set it back to the original method used
        request.method = method_override or method

        # Add a dict to hold the message body data to the request based on the
        # HTTP method used (or the method override if one was provided)
        if request.method not in ['POST', 'GET']:
            setattr(request, request.method, request.POST)

        # Check for an HttpError when executing the view. If one was returned,
        # get the message and status code and return it, otherwise, let any
        # other type of exception bubble up or return the response if no error
        # occurred.
        try:
            response = super(Resource, self).dispatch(request, *args, **kwargs)
        except HttpError, e:
            response = HttpResponse(status=e.status)

        return response

########NEW FILE########
__FILENAME__ = response
import collections
import mimetypes

import mimeparse

from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponse

from .utils.decorators import wrap_object
from .exceptions import HttpError
from .utils.serializers import to_json, to_html, to_text


DEFAULT_MIMETYPES = {
    'application/json': to_json,
    'text/html': to_html,
    'text/plain': to_text
}


class RESTfulResponse(collections.MutableMapping, collections.Callable):
    """
    Can be used as a decorator or an instance to properly formatted content

    This class provides content negotiation for RESTful requests. The content-
    type of a response is determined by the ACCEPT header of the reqeust or by
    an overriding file extension in the URL (e.g., path/to/some/resource.xml)
    will return the response formatted as XML.

    This class creates an instance that can be used directly to transform a
    python dict into a properly formatted response via the render_to_response
    method or it can be used as a decorator for class-based views or for an
    individual method within a class-based view. If a requested mimetype is
    not found amongst the supported mimetypes, the content-type of the response
    will default to 'application/json'.

    This class is inspired by an excellent blog post from James Bennett. See
    http://www.b-list.org/weblog/2008/nov/29/multiresponse/ for more
    information.
    """
    def __init__(self, mimetype_mapping=None):
        self._mimetypes = {}
        if mimetype_mapping:
            self._mimetypes.update(mimetype_mapping)

    def __len__(self):
        return len(self.keys())

    def __iter__(self):
        for key in self.keys():
            yield key

    def __getitem__(self, mimetype):
        if mimetype in self._mimetypes:
            return self._mimetypes[mimetype]
        else:
            return DEFAULT_MIMETYPES[mimetype]

    def __setitem__(self, mimetype, func_or_templ):
        self._mimetypes[mimetype] = func_or_templ

    def __delitem__(self, mimetype):
        del self._mimetypes[mimetype]

    def keys(self):
        return list(set(self._mimetypes.keys()) | set(DEFAULT_MIMETYPES.keys()))

    def __call__(self, view_obj):
        def decorator(view_func):
            def wrapper(request, *args, **kwargs):
                try:
                    results = view_func(request, *args, **kwargs)
                except HttpError, e:
                    results = (
                        e.message and {'error': e.message} or None,
                        e.status
                    )

                # TODO: What should be done about a resource that returns a normal
                #       Django HttpResponse? Right now, if an HttpResponse is
                #       returned, it is allowed to propogate. In other words, it
                #       acts just as it would if content negotiation wasn't being
                #       used. Another option would be to extract the content and
                #       status code from the HttpResponse object and pass those
                #       into the render_to_response method.
                if isinstance(results, HttpResponse):
                    return results

                # Get the status code, if one was provided
                if isinstance(results, collections.Sequence) and len(results) == 2:
                    try:
                        data, status_code = results[0], int(results[1])
                    except Exception:
                        data, status_code = results, 200
                else:
                    data, status_code = results, 200

                response = self.render_to_response(request, data, status_code, kwargs.get('_format', None))
                return response
            return wrapper
        return wrap_object(view_obj, decorator)

    def render_to_response(self, request, data=None, status=200, format=None):
        format = request.REQUEST.get('_format', None) or format
        mimetype = mimeparse.best_match(self.keys(), request.META.get('HTTP_ACCEPT', ''))
        mimetype = mimetypes.guess_type('placeholder_filename.%s' % format)[0] or mimetype
        content_type = '%s; charset=%s' % (mimetype, settings.DEFAULT_CHARSET)

        templ_or_func = self.get(mimetype)

        # If a template or function isn't found, return a 415 (unsupportted media type) response
        if not templ_or_func:
            return HttpResponse(status=415)

        if data is None:
            response = HttpResponse()
        elif isinstance(templ_or_func, str):
            response = render_to_response(templ_or_func, {'context': data})
        else:
            response = HttpResponse(templ_or_func(data))

        response['Content-Type'] = content_type
        response.status_code = status
        return response

########NEW FILE########
__FILENAME__ = decorators
import inspect
from functools import update_wrapper

from django.utils.decorators import method_decorator, available_attrs


def wrap_object(obj, decorator):
    """
    Decorates the given object with the decorator function.

    If obj is a method, the method is decorated with the decorator function
    and returned. If obj is a class (i.e., a class based view), the methods
    in the class corresponding to HTTP methods will be decorated and the
    resultant class object will be returned.
    """
    actual_decorator = method_decorator(decorator)

    if inspect.isfunction(obj):
        wrapped_obj = actual_decorator(obj)
        update_wrapper(wrapped_obj, obj, assigned=available_attrs(obj))
    elif inspect.isclass(obj):
        for method_name in obj.http_method_names:
            if hasattr(obj, method_name):
                method = getattr(obj, method_name)
                wrapped_method = actual_decorator(method)
                update_wrapper(wrapped_method, method, assigned=available_attrs(method))
                setattr(obj, method_name, wrapped_method)
        wrapped_obj = obj
    else:
        raise TypeError("received an object of type '{0}' expected 'function' or 'classobj'.".format(type(obj)))

    return wrapped_obj

########NEW FILE########
__FILENAME__ = serializers
from decimal import Decimal
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.query import QuerySet
from django.template import Template, Context

import logging
logger = logging.getLogger(__name__)

try:
    from pygments import highlight
    from pygments.lexers import JSONLexer
    from pygments.formatters import HtmlFormatter
    PYGMENTS_INSTALLED = True
except Exception, e:
    logging.info("Install pygments for syntax highlighting")
    PYGMENTS_INSTALLED = False

try:
    import simplejson as json
except ImportError:
    logging.info('Install simplejson for better performance')
    import json


class DecimalEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return DjangoJSONEncoder.default(self, obj)


def to_json(content, indent=None):
    """
    Serializes a python object as JSON

    This method uses the DJangoJSONEncoder to to ensure that python objects
    such as Decimal objects are properly serialized. It can also serialize
    Django QuerySet objects.
    """
    if isinstance(content, QuerySet):
        json_serializer = serializers.get_serializer('json')()
        serialized_content = json_serializer.serialize(content, ensure_ascii=False, indent=indent)
    else:
        try:
            serialized_content = json.dumps(content, cls=DecimalEncoder, ensure_ascii=False, indent=indent)
        except TypeError:
            # Fix for Django 1.5
            serialized_content = json.dumps(content, ensure_ascii=False, indent=indent)
    return serialized_content


def to_html(data):
    """
    Serializes a python object as HTML

    This method uses the to_json method to turn the given data object into
    formatted JSON that is displayed in an HTML page. If pygments in installed,
    syntax highlighting will also be applied to the JSON.
    """
    base_html_template = Template('''
        <html>
            <head>
                {% if style %}
                <style type="text/css">
                    {{ style }}
                </style>
                {% endif %}
            </head>
            <body>
                {% if style %}
                    {{ body|safe }}
                {% else %}
                    <pre></code>{{ body }}</code></pre>
                {% endif %}
            </body>
        </html>
        ''')

    code = to_json(data, indent=4)
    if PYGMENTS_INSTALLED:
        c = Context({
            'body': highlight(code, JSONLexer(), HtmlFormatter()),
            'style': HtmlFormatter().get_style_defs('.highlight')
        })
        html = base_html_template.render(c)
    else:
        c = Context({'body': code})
        html = base_html_template.render(c)
    return html

def to_text(data):
    """
    Serializes a python object as plain text

    If the data can be serialized as JSON, this method will use the to_json
    method to format the data, otherwise the data is returned as is.
    """
    try:
        serialized_content = to_json(data, indent=4)
    except Exception, e:
        serialized_content = data
    return serialized_content




########NEW FILE########
