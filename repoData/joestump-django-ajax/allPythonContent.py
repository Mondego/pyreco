__FILENAME__ = decorators
from django.utils.translation import ugettext as _
from django.utils.log import getLogger
from django.http import Http404
from django.conf import settings
from decorator import decorator
from ajax.exceptions import AJAXError, PrimaryKeyMissing
from functools import wraps
from django.utils.decorators import available_attrs


logger = getLogger('django.request')


@decorator
def login_required(f, *args, **kwargs):
    if not args[0].user.is_authenticated():
        raise AJAXError(403, _('User must be authenticated.'))

    return f(*args, **kwargs)


@decorator
def require_pk(func, *args, **kwargs):
    if not hasattr(args[0], 'pk') or args[0].pk is None:
        raise PrimaryKeyMissing()

    return func(*args, **kwargs)


def allowed_methods(*args,**kwargs):
    request_method_list = args
    def decorator(func):
        @wraps(func, assigned=available_attrs(func))
        def inner(request, *args, **kwargs):
            if request.method not in request_method_list:
                raise AJAXError(403, _('Access denied.'))
            return func(request, *args, **kwargs)
        return inner
    return decorator        
    
@decorator
def json_response(f, *args, **kwargs):
    """Wrap a view in JSON.

    This decorator runs the given function and looks out for ajax.AJAXError's,
    which it encodes into a proper HttpResponse object. If an unknown error
    is thrown it's encoded as a 500.

    All errors are then packaged up with an appropriate Content-Type and a JSON
    body that you can inspect in JavaScript on the client. They look like:

    {
        "message": "Error message here.",
        "code": 500
    }

    Please keep in mind that raw exception messages could very well be exposed
    to the client if a non-AJAXError is thrown.
    """
    try:
        result = f(*args, **kwargs)
        if isinstance(result, AJAXError):
            raise result
    except AJAXError, e:
        result = e.get_response()

        request = args[0]
        logger.warn('AJAXError: %d %s - %s', e.code, request.path, e.msg,
            exc_info=True,
            extra={
                'status_code': e.code,
                'request': request
            }
        )
    except Http404, e:
        result = AJAXError(404, e.__str__()).get_response()
    except Exception, e:
        import sys
        exc_info = sys.exc_info()
        type, message, trace = exc_info
        if settings.DEBUG:
            import traceback
            tb = [{'file': l[0], 'line': l[1], 'in': l[2], 'code': l[3]} for
                l in traceback.extract_tb(trace)]
            result = AJAXError(500, message, traceback=tb).get_response()
        else:
            result = AJAXError(500, "Internal server error.").get_response()

        request = args[0]
        logger.error('Internal Server Error: %s' % request.path,
            exc_info=exc_info,
            extra={
                'status_code': 500,
                'request': request
            }
        )

    result['Content-Type'] = 'application/json'
    return result

########NEW FILE########
__FILENAME__ = encoders
from django.core import serializers
from ajax.exceptions import AlreadyRegistered, NotRegistered
from django.db.models.fields import FieldDoesNotExist
from django.db import models
from django.conf import settings
from django.utils.html import escape
from django.db.models.query import QuerySet
from django.utils.encoding import smart_str
import collections


# Used to change the field name for the Model's pk.
AJAX_PK_ATTR_NAME = getattr(settings, 'AJAX_PK_ATTR_NAME', 'pk')


def _fields_from_model(model):
    return [field.name for field in model.__class__._meta.fields]


class DefaultEncoder(object):
    _mapping = {
        'IntegerField': int,
        'PositiveIntegerField': int,
        'AutoField': int,
        'FloatField': float,
    }

    def to_dict(self, record, expand=False, html_escape=False, fields=None):
        self.html_escape = html_escape
        if hasattr(record, '__exclude__') and callable(record.__exclude__):
            try:
                exclude = record.__exclude__()
                if fields is None:
                    fields = _fields_from_model(record)
                fields = set(fields) - set(exclude)
            except TypeError:
                pass
        data = serializers.serialize('python', [record], fields=fields)[0]

        if hasattr(record, 'extra_fields'):
            ret = record.extra_fields
        else:
            ret = {}

        ret.update(data['fields'])
        ret[AJAX_PK_ATTR_NAME] = data['pk']

        for field, val in ret.iteritems():
            try:
                f = record.__class__._meta.get_field(field)
                if expand and isinstance(f, models.ForeignKey):
                    try:
                        row = f.rel.to.objects.get(pk=val)
                        new_value = self.to_dict(row, False)
                    except f.rel.to.DoesNotExist:
                        new_value = None  # Changed this to None from {} -G
                else:
                    new_value = self._encode_value(f, val)

                ret[smart_str(field)] = new_value
            except FieldDoesNotExist, e:
                pass  # Assume extra fields are already safe.
                  
        if expand and hasattr(record, 'tags') and \
          record.tags.__class__.__name__.endswith('TaggableManager'):
          # Looks like this model is using taggit.
          ret['tags'] = [{'name': self._escape(t.name), 
          'slug': self._escape(t.slug)} for t in record.tags.all()]
          
        return ret

    __call__ = to_dict

    def _encode_value(self, field, value):
        if value is None:
            return value # Leave all None's as-is as they encode fine.

        try:
            return self._mapping[field.__class__.__name__](value)
        except KeyError:
            if isinstance(field, models.ForeignKey):
                f = field.rel.to._meta.get_field(field.rel.field_name)
                return self._encode_value(f, value)
            elif isinstance(field, models.BooleanField):
                # If someone could explain to me why the fuck the Python
                # serializer appears to serialize BooleanField to a string
                # with "True" or "False" in it, please let me know.
                return (value == "True" or (type(value) == bool and value))

        return self._escape(value)

    def _escape(self, value):
        if self.html_escape:
            return escape(value)
        return value


class HTMLEscapeEncoder(DefaultEncoder):
    """Encodes all values using Django's HTML escape function."""
    def _escape(self, value):
        return escape(value)


class ExcludeEncoder(DefaultEncoder):
    def __init__(self, exclude):
        self.exclude = exclude

    def __call__(self, record, html_escape=False):
        fields = set(_fields_from_model(record)) - set(self.exclude)
        return self.to_dict(record, html_escape=html_escape, fields=fields)


class IncludeEncoder(DefaultEncoder):
    def __init__(self, include):
        self.include = include

    def __call__(self, record, html_escape=False):
        return self.to_dict(record, html_escape=html_escape, fields=self.include)


class Encoders(object):
    def __init__(self):
        self._registry = {}

    def register(self, model, encoder):
        if model in self._registry:
            raise AlreadyRegistered()

        self._registry[model] = encoder

    def unregister(self, model):
        if model not in self._registry:
            raise NotRegistered()

        del self._registry[model]
    
    def get_encoder_from_record(self, record):
        if isinstance(record, models.Model) and \
            record.__class__ in self._registry:
            encoder = self._registry[record.__class__]
        else:
            encoder = DefaultEncoder()
        return encoder
        
    def encode(self, record, encoder=None, html_escape=False):
        if isinstance(record, collections.Iterable):
            ret = []
            for i in record:
                if not encoder:
                    encoder = self.get_encoder_from_record(i)
                ret.append(self.encode(i, html_escape=html_escape))
        else:
            if not encoder:
                encoder = self.get_encoder_from_record(record)
            ret = encoder(record, html_escape=html_escape)

        return ret


encoder = Encoders()

########NEW FILE########
__FILENAME__ = endpoints
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import smart_str
from django.utils.translation import ugettext_lazy as _
from ajax.decorators import require_pk
from ajax.exceptions import AJAXError, AlreadyRegistered, NotRegistered
from ajax.encoders import encoder
from ajax.signals import ajax_created, ajax_deleted, ajax_updated
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from ajax.views import EnvelopedResponse

try:
    from taggit.utils import parse_tags
except ImportError:
    def parse_tags(tagstring):
        raise AJAXError(500, 'Taggit required: http://bit.ly/RE0dr9')


class EmptyPageResult(object):
    def __init__(self):
        self.object_list = []


class ModelEndpoint(object):
    _value_map = {
        'false': False,
        'true': True,
        'null': None
    }

    immutable_fields = []  # List of model fields that are not writable.

    def __init__(self, application, model, method, **kwargs):
        self.application = application
        self.model = model
        self.fields = [f.name for f in self.model._meta.fields]
        self.method = method
        self.pk = kwargs.get('pk', None)
        self.options = kwargs

    def create(self, request):
        record = self.model(**self._extract_data(request))
        if self.can_create(request.user, record):
            record = self._save(record)
            try:
                tags = self._extract_tags(request)
                record.tags.set(*tags)
            except KeyError:
                pass

            ajax_created.send(sender=record.__class__, instance=record)
            return encoder.encode(record)
        else:
            raise AJAXError(403, _("Access to endpoint is forbidden"))

    def tags(self, request):
        cmd = self.options.get('taggit_command', None)
        if not cmd:
            raise AJAXError(400, _("Invalid or missing taggit command."))

        record = self._get_record()
        if cmd == 'similar':
            result = record.tags.similar_objects()
        else:
            try:
                tags = self._extract_tags(request)
                getattr(record.tags, cmd)(*tags)
            except KeyError:
                pass  # No tags to set/manipulate in this request.
            result = record.tags.all()

        return encoder.encode(result)

    def get_queryset(self, request, **kwargs):
        return self.model.objects.none()

    def list(self, request):
        """
        List objects of a model. By default will show page 1 with 20 objects on it. 
        
        **Usage**::
        
            params = {"items_per_page":10,"page":2} //all params are optional
            $.post("/ajax/{app}/{model}/list.json"),params)
        
        """

        max_items_per_page = getattr(self, 'max_per_page',
                                      getattr(settings, 'AJAX_MAX_PER_PAGE', 100))
        requested_items_per_page = request.POST.get("items_per_page", 20)
        items_per_page = min(max_items_per_page, requested_items_per_page)
        current_page = request.POST.get("current_page", 1)

        if not self.can_list(request.user):
            raise AJAXError(403, _("Access to this endpoint is forbidden"))

        objects = self.get_queryset(request)

        paginator = Paginator(objects, items_per_page)

        try:
            page = paginator.page(current_page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), return empty list.
            page = EmptyPageResult()

        data = [encoder.encode(record) for record in page.object_list]
        return EnvelopedResponse(data=data, metadata={'total': paginator.count})


    def _set_tags(self, request, record):
        tags = self._extract_tags(request)
        if tags:
            record.tags.set(*tags) 

    def _save(self, record):
        try:
            record.full_clean()
            record.save()
            return record
        except ValidationError, e:
            raise AJAXError(400, _("Could not save model."),
                errors=e.message_dict)

    @require_pk
    def update(self, request):
        record = self._get_record()
        modified = self._get_record()
        for key, val in self._extract_data(request).iteritems():
            setattr(modified, key, val)
        if self.can_update(request.user, record, modified=modified):

            self._save(modified)

            try:
                tags = self._extract_tags(request)
                if tags:
                    modified.tags.set(*tags)
                else:
                    # If tags were in the request and set to nothing, we will
                    # clear them all out.
                    modified.tags.clear()
            except KeyError:
                pass

            ajax_updated.send(sender=record.__class__, instance=record)
            return encoder.encode(modified)
        else:
            raise AJAXError(403, _("Access to endpoint is forbidden"))

    @require_pk
    def delete(self, request):
        record = self._get_record()
        if self.can_delete(request.user, record):
            record.delete()
            ajax_deleted.send(sender=record.__class__, instance=record)
            return {'pk': int(self.pk)}
        else:
            raise AJAXError(403, _("Access to endpoint is forbidden"))

    @require_pk
    def get(self, request):
        record = self._get_record()
        if self.can_get(request.user, record):
            return encoder.encode(record)
        else:
            raise AJAXError(403, _("Access to endpoint is forbidden"))

    def _extract_tags(self, request):
        # We let this throw a KeyError so that calling functions will know if
        # there were NO tags in the request or if there were, but that the
        # call had an empty tags list in it.
        raw_tags = request.POST['tags']
        tags = []
        if raw_tags:
            try:
                tags = [t for t in parse_tags(raw_tags) if len(t)]
            except Exception, e:
                pass

        return tags

    def _extract_data(self, request):
        """Extract data from POST.

        Handles extracting a vanilla Python dict of values that are present
        in the given model. This also handles instances of ``ForeignKey`` and
        will convert those to the appropriate object instances from the
        database. In other words, it will see that user is a ``ForeignKey`` to
        Django's ``User`` class, assume the value is an appropriate pk, and
        load up that record.
        """
        data = {}
        for field, val in request.POST.iteritems():
            if field in self.immutable_fields:
                continue  # Ignore immutable fields silently.

            if field in self.fields:
                field_obj = self.model._meta.get_field(field)
                val = self._extract_value(val)
                if isinstance(field_obj, models.ForeignKey):
                    if field_obj.null and not val:
                        clean_value = None
                    else:
                        clean_value = field_obj.rel.to.objects.get(pk=val)
                else:
                    clean_value = val
                data[smart_str(field)] = clean_value

        return data

    def _extract_value(self, value):
        """If the value is true/false/null replace with Python equivalent."""
        return ModelEndpoint._value_map.get(smart_str(value).lower(), value)

    def _get_record(self):
        """Fetch a given record.

        Handles fetching a record from the database along with throwing an
        appropriate instance of ``AJAXError`.
        """
        if not self.pk:
            raise AJAXError(400, _('Invalid request for record.'))

        try:
            return self.model.objects.get(pk=self.pk)
        except self.model.DoesNotExist:
            raise AJAXError(404, _('%s with id of "%s" not found.') % (
                self.model.__name__, self.pk))

    def can_get(self, user, record):
        return True

    def _user_is_active_or_staff(self, user, record, **kwargs):
        return ((user.is_authenticated() and user.is_active) or user.is_staff)

    can_create = _user_is_active_or_staff
    can_update = _user_is_active_or_staff
    can_delete = _user_is_active_or_staff
    can_list = lambda *args, **kwargs: False

    def authenticate(self, request, application, method):
        """Authenticate the AJAX request.

        By default any request to fetch a model is allowed for any user,
        including anonymous users. All other methods minimally require that
        the user is already logged in.

        Most likely you will want to lock down who can edit and delete various
        models. To do this, just override this method in your child class.
        """
        if request.user.is_authenticated():
            return True

        return False


class FormEndpoint(object):
    """AJAX endpoint for processing Django forms.

    The models and forms are processed in pretty much the same manner, only a
    form class is used rather than a model class.
    """
    def create(self, request):
        form = self.model(request.POST)
        if form.is_valid():
            model = form.save()
            if hasattr(model, 'save'):
                # This is a model form so we save it and return the model.
                model.save()
                return encoder.encode(model)
            else:
                return model  # Assume this is a dict to encode.
        else:
            return encoder.encode(form.errors)

    def update(self, request):
        raise AJAXError(404, _("Endpoint does not exist."))

    delete = update
    get = update


class Endpoints(object):
    def __init__(self):
        self._registry = {}

    def register(self, model, endpoint):
        if model in self._registry:
            raise AlreadyRegistered()

        self._registry[model] = endpoint

    def unregister(self, model):
        if model not in self._registry:
            raise NotRegistered()

        del self._registry[model]

    def load(self, model_name, application, method, **kwargs):
        for model in self._registry:
            if model.__name__.lower() == model_name:
                return self._registry[model](application, model, method,
                    **kwargs)

        raise NotRegistered()

########NEW FILE########
__FILENAME__ = exceptions
try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django.utils.encoding import smart_str
from django.http import HttpResponse, HttpResponseNotFound, \
    HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseServerError, \
    HttpResponseBadRequest


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class PrimaryKeyMissing(Exception):
    pass


class AJAXError(Exception):
    RESPONSES = {
        400: HttpResponseBadRequest,
        403: HttpResponseForbidden,
        404: HttpResponseNotFound,
        405: HttpResponseNotAllowed,
        500: HttpResponseServerError,
    }

    def __init__(self, code, msg, **kwargs):
        self.code = code
        self.msg = msg
        self.extra = kwargs  # Any kwargs will be appended to the output.

    def get_response(self):
        try:
            msg = smart_str(self.msg.decode())
        except (AttributeError,):
            msg = smart_str(self.msg)
        error = {
            'success': False,
            'data': {
                'code': self.code,
                'message': msg
            }
        }
        error.update(self.extra)

        response = self.RESPONSES[self.code]()
        response.content = json.dumps(error, separators=(',', ':'))
        return response

########NEW FILE########
__FILENAME__ = DebugToolbar
try:
    import json
except ImportError:
    from django.utils import simplejson as json

from debug_toolbar.middleware import DebugToolbarMiddleware, add_content_handler
from django.core.serializers.json import DjangoJSONEncoder


class AJAXDebugToolbarJSONEncoder(DjangoJSONEncoder):
    pass


class AJAXDebugToolbarMiddleware(DebugToolbarMiddleware):
    """
    Replaces django-debug-toolbar's default DebugToolbarMiddleware.

    This middleware overrides the DebugToolbarMiddleware.process_response() to
    return the toolbar data in the AJAX response if the request was an AJAX
    request. This allows for debugging via the browser console using data from 
    the django-debug-toolbar panels.
    """
    def _append_json(self, response, toolbar):
        payload = json.loads(response.content)
        payload['debug_toolbar'] = {
            'sql': toolbar.stats['sql'],
            'timer': toolbar.stats['timer']
        }
        try:
            response.content = json.dumps(payload, indent=4,
                cls=AJAXDebugToolbarJSONEncoder)
        except:
            pass
        return response


add_content_handler('_append_json', ['application/json', 'text/javascript'])

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

ajax_created = django.dispatch.Signal(providing_args=['instance'])
ajax_deleted = django.dispatch.Signal(providing_args=['instance'])
ajax_updated = django.dispatch.Signal(providing_args=['instance'])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.views.static import serve
import os

JAVASCRIPT_PATH = "%s/js" % os.path.dirname(__file__)

urlpatterns = patterns('ajax.views',
    (r'^(?P<application>\w+)/(?P<model>\w+).json', 'endpoint_loader'), 
    (r'^(?P<application>\w+)/(?P<model>\w+)/(?P<method>\w+).json', 'endpoint_loader'), 
    (r'^(?P<application>\w+)/(?P<model>\w+)/(?P<pk>\d+)/(?P<method>\w+)/?(?P<taggit_command>(add|remove|set|clear|similar))?.json$', 'endpoint_loader'),
    (r'^js/(?P<path>.*)$', serve,
        {'document_root': JAVASCRIPT_PATH}),
)

########NEW FILE########
__FILENAME__ = views
try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from django.utils.importlib import import_module
from django.utils.log import getLogger
from django.core.serializers.json import DjangoJSONEncoder
from ajax.exceptions import AJAXError, NotRegistered
from ajax.decorators import json_response
import ajax


logger = getLogger('django.request')


class EnvelopedResponse(object):
    """
    Object used to contain metadata about the request that will be added to
    the wrapping json structure (aka the envelope).

    :param: data - The object representation that you want to return
    :param: metadata - dict of information which will be merged with the
                       envelope.
    """
    def __init__(self, data, metadata):
        self.data = data
        self.metadata = metadata

@json_response
def endpoint_loader(request, application, model, **kwargs):
    """Load an AJAX endpoint.

    This will load either an ad-hoc endpoint or it will load up a model
    endpoint depending on what it finds. It first attempts to load ``model``
    as if it were an ad-hoc endpoint. Alternatively, it will attempt to see if
    there is a ``ModelEndpoint`` for the given ``model``.
    """
    if request.method != "POST":
        raise AJAXError(400, _('Invalid HTTP method used.'))

    try:
        module = import_module('%s.endpoints' % application)
    except ImportError, e:
        if settings.DEBUG:
            raise e
        else:
            raise AJAXError(404, _('AJAX endpoint does not exist.'))

    if hasattr(module, model):
        # This is an ad-hoc endpoint
        endpoint = getattr(module, model)
    else:
        # This is a model endpoint
        method = kwargs.get('method', 'create').lower()
        try:
            del kwargs['method']
        except:
            pass

        try:
            model_endpoint = ajax.endpoint.load(model, application, method,
                **kwargs)
            if not model_endpoint.authenticate(request, application, method):
                raise AJAXError(403, _('User is not authorized.'))

            endpoint = getattr(model_endpoint, method, False)

            if not endpoint:
                raise AJAXError(404, _('Invalid method.'))
        except NotRegistered:
            raise AJAXError(500, _('Invalid model.'))

    data = endpoint(request)
    if isinstance(data, HttpResponse):
        return data

    if isinstance(data, EnvelopedResponse):
        envelope = data.metadata
        payload = data.data
    else:
        envelope = {}
        payload = data

    envelope.update({
        'success': True,
        'data': payload,
    })

    return HttpResponse(json.dumps(envelope, cls=DjangoJSONEncoder,
        separators=(',', ':')))

########NEW FILE########
__FILENAME__ = endpoints
from ajax import endpoint
from ajax.decorators import login_required
from ajax.endpoints import ModelEndpoint
from .models import Widget, Category


@login_required
def echo(request):
    """For testing purposes only."""
    return request.POST


class WidgetEndpoint(ModelEndpoint):
    model = Widget
    max_per_page = 100
    can_list = lambda *args, **kwargs: True

    def get_queryset(self, request):
        return Widget.objects.all()

class CategoryEndpoint(ModelEndpoint):
    model = Category


endpoint.register(Widget, WidgetEndpoint)
endpoint.register(Category, CategoryEndpoint)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Category(models.Model):
    title = models.CharField(max_length=100)

class Widget(models.Model):
    category = models.ForeignKey(Category, null=True, blank=True)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200, null=True, blank=True)
    active = models.BooleanField()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.contrib.auth.models import User
import json
from ajax.exceptions import AJAXError
from .models import Widget, Category
from .endpoints import WidgetEndpoint, CategoryEndpoint


class BaseTest(TestCase):
    fixtures = ['users.json', 'categories.json', 'widgets.json']

    def setUp(self):
        self.login('jstump')

    def login(self, username, password='testing'):
        user = User.objects.get(username=username)
        login_successful = self.client.login(username=user.username,
            password=password)
        self.assertTrue(login_successful)

    def post(self, uri, data={}, debug=False, status_code=200):
        """Send an AJAX request.

        This handles sending the AJAX request via the built-in Django test
        client and then decodes the response.

        ``status_code`` lets you define what you expect the status code
        to be which will be tested before returning the response object
        and the decoded JSON content.

        ``debug`` if set to True will spit out the response and content.
        """
        response = self.client.post(uri, data)
        if debug:
            print response.__class__.__name__
            print response

        self.assertEquals(status_code, response.status_code)

        return response, json.loads(response.content)


class EncodeTests(BaseTest):
    def test_encode(self):
        from ajax.encoders import encoder
        widget = Widget.objects.get(pk=1)
        self.assertEquals(widget.title,'Iorem lipsum color bit amit')
        encoded = encoder.encode(widget)
        for k in ('title','active','description'):
            self.assertEquals(encoded[k],getattr(widget,k))
        widgets = Widget.objects.all()
        all_encoded = encoder.encode(widgets)
        for encoded in all_encoded:
            widget = Widget.objects.get(pk=encoded['pk'])
            for k in ('title','active','description'):
                self.assertEquals(encoded[k],getattr(widget,k))
        

class EndpointTests(BaseTest):
    def test_echo(self):
        """Test the ad-hoc echo endpoint."""
        resp, content = self.post('/ajax/example/echo.json',
            {'name': 'Joe Stump', 'age': 31})
        self.assertEquals('Joe Stump', content['data']['name'])
        self.assertEquals('31', content['data']['age'])

    def test_empty_foreign_key(self):
        """Test that nullable ForeignKey fields can be set to null"""
        resp, content = self.post('/ajax/example/widget/3/update.json',
            {'category': ''})
        self.assertEquals(None, content['data']['category'])
        self.assertEquals(None, Widget.objects.get(pk=3).category)

    def test_false_foreign_key(self):
        """Test that nullable ForeignKey fields can be set to null by setting it to false"""
        resp, content = self.post('/ajax/example/widget/6/update.json',
            {'category': False})
        self.assertEquals(None, content['data']['category'])
        self.assertEquals(None, Widget.objects.get(pk=6).category)

    def test_logged_out_user_fails(self):
        """Make sure @login_required rejects requests to echo."""
        self.client.logout()
        resp, content = self.post('/ajax/example/echo.json', {},
            status_code=403)


class MockRequest(object):
    def __init__(self, **kwargs):
        self.POST = kwargs
        self.user = None


class ModelEndpointTests(BaseTest):
    def setUp(self):
        self.list_endpoint = WidgetEndpoint('example', Widget, 'list')
        self.category_endpoint = CategoryEndpoint('example', Category, 'list')

    def test_list_returns_all_items(self):
        results = self.list_endpoint.list(MockRequest())
        self.assertEqual(len(results.data), Widget.objects.count())

    def test_list_obeys_endpoint_pagination_amount(self):
        self.list_endpoint.max_per_page = 1
        results = self.list_endpoint.list(MockRequest())
        self.assertEqual(len(results.data), 1)

    def test_list__ajaxerror_if_can_list_isnt_set(self):
        self.assertRaises(AJAXError, self.category_endpoint.list, MockRequest())

    def test_out_of_range_returns_empty_list(self):
        results = self.list_endpoint.list(MockRequest(current_page=99))
        self.assertEqual(len(results.data), 0)

    def test_request_doesnt_override_max_per_page(self):
        self.list_endpoint.max_per_page = 1
        results = self.list_endpoint.list(MockRequest(items_per_page=2))
        self.assertEqual(len(results.data), 1)

    def test_list_has_permission__default_empty(self):
        Category.objects.create(title='test')

        self.category_endpoint.can_list = lambda *args, **kwargs: True

        results = self.category_endpoint.list(MockRequest())
        self.assertEqual(0, len(results.data))

    def test_list_has_total(self):
        self.category_endpoint.can_list = lambda *args, **kwargs: True

        results = self.list_endpoint.list(MockRequest())
        self.assertEqual(6, results.metadata['total'])

class ModelEndpointPostTests(TestCase):
    """
    Integration test for full urls->views->endpoint->encoder (and back) cycle.
    """
    def setUp(self):
        for title in ['first', 'second', 'third']:
            Widget.objects.create(title=title)
        u = User(email='test@example.org', username='test')
        u.set_password('password')
        u.save()

    def test_can_request_list_with_total(self):
        self.client.login(username='test', password='password')

        resp = self.client.post('/ajax/example/widget/list.json')
        content = json.loads(resp.content)
        self.assertTrue('total' in content.keys())
        self.assertEquals(content['total'], 3)
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import sys
sys.path.insert(0, '../')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Joe Stump', 'joe@joestump.net'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'example.sqlite3',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# A boolean that specifies if datetimes will be timezone-aware by default or
# not. If this is set to True, Django will use timezone-aware datetimes
# internally. Otherwise, Django will use naive datetimes in local time.
USE_TZ = True

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

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

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '(l*w&8lg1co#vw#3$1#i^!!!tvhiw061%@jm*_-#_o@jv-y^#d'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'tests.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jenkins',
    'ajax',
    'example',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# Only run Jenkins report generation on these apps.
PROJECT_APPS = ('example',)

# Which Jenkins reports/tasks to run.
JENKINS_TASKS = ('django_jenkins.tasks.run_pylint',
                 'django_jenkins.tasks.run_pep8',
                 'django_jenkins.tasks.run_pyflakes',
                 'django_jenkins.tasks.with_coverage',
                 'django_jenkins.tasks.django_tests',)

# The test runner for the Jenkins command.
JENKINS_TEST_RUNNER = 'django_jenkins.runner.CITestSuiteRunner'

# django-ajax specific settings
MAX_PER_PAGE = 20

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url


urlpatterns = patterns('',
    url(r'^ajax/', include('ajax.urls')),
)

########NEW FILE########
