__FILENAME__ = decorators
import logging
from functools import wraps

from django import http
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.handlers.base import BaseHandler
from django.core.serializers.json import DjangoJSONEncoder
from django.core.signals import got_request_exception
from django.utils.importlib import import_module

import sys
if sys.version_info[0] == 3:
    unicode = str

from .exceptions import BadRequest

json = import_module(getattr(settings, 'JSON_MODULE', 'json'))
JSON = 'application/json'
logger = logging.getLogger('django.request')
logger.info('Using %s JSON module.', json.__name__)


def json_view(*decoargs, **decokwargs):
    """Ensure the response content is well-formed JSON.

    Views wrapped in @json_view can return JSON-serializable Python objects,
    like lists and dicts, and the decorator will serialize the output and set
    the correct Content-type.

    Views may also throw known exceptions, like Http404, PermissionDenied, etc,
    and @json_view will convert the response to a standard JSON error format,
    and set the status code and content type.

    If you return a two item tuple, the first is a JSON-serializable object and
    the second is an integer used for the HTTP status code, e.g.:

    >>> @json_view
    ... def example(request):
    ...    return {'foo': 'bar'}, 418

    By default all responses will get application/json as their content type.
    You can override it for non-error responses by giving the content_type
    keyword parameter to the decorator, e.g.:

    >>> @json_view(content_type="application/vnd.example-v1.0+json")
    ... def example2(request):
    ...     return {'foo': 'bar'}

    """

    content_type = decokwargs.get("content_type", JSON)

    def deco(f):
        @wraps(f)
        def _wrapped(request, *a, **kw):
            try:
                status = 200
                headers = {}
                ret = f(request, *a, **kw)

                if isinstance(ret, tuple):
                    if len(ret) == 3:
                        ret, status, headers = ret
                    else:
                        ret, status = ret

                # Some errors are not exceptions. :\
                if isinstance(ret, http.HttpResponseNotAllowed):
                    blob = json.dumps({
                        'error': 405,
                        'message': 'HTTP method not allowed.'
                    })
                    return http.HttpResponse(
                        blob, status=405, content_type=JSON)

                # Allow HttpResponses to go straight through.
                if isinstance(ret, http.HttpResponse):
                    return ret

                blob = json.dumps(ret, cls=DjangoJSONEncoder)
                response = http.HttpResponse(blob, status=status,
                                             content_type=content_type)
                for k in headers:
                    response[k] = headers[k]
                return response
            except http.Http404 as e:
                blob = json.dumps({
                    'error': 404,
                    'message': unicode(e),
                })
                logger.warning('Not found: %s', request.path,
                               extra={
                                   'status_code': 404,
                                   'request': request,
                               })
                return http.HttpResponseNotFound(blob, content_type=JSON)
            except PermissionDenied as e:
                logger.warning(
                    'Forbidden (Permission denied): %s', request.path,
                    extra={
                        'status_code': 403,
                        'request': request,
                    })
                blob = json.dumps({
                    'error': 403,
                    'message': unicode(e),
                })
                return http.HttpResponseForbidden(blob, content_type=JSON)
            except BadRequest as e:
                blob = json.dumps({
                    'error': 400,
                    'message': unicode(e),
                })
                return http.HttpResponseBadRequest(blob, content_type=JSON)
            except Exception as e:
                if settings.DEBUG:
                    exc_text = unicode(e)
                else:
                    exc_text = 'An error occurred'
                blob = json.dumps({
                    'error': 500,
                    'message': exc_text,
                })
                logger.exception(unicode(e))

                # Here we lie a little bit. Because we swallow the exception,
                # the BaseHandler doesn't get to send this signal. It sets the
                # sender argument to self.__class__, in case the BaseHandler
                # is subclassed.
                got_request_exception.send(sender=BaseHandler, request=request)
                return http.HttpResponseServerError(blob, content_type=JSON)
        return _wrapped
    if len(decoargs) == 1 and callable(decoargs[0]):
        return deco(decoargs[0])
    else:
        return deco

########NEW FILE########
__FILENAME__ = exceptions
class BadRequest(Exception):
    pass

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals
import json
import sys

from django import http
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.utils import timezone
from django.views.decorators.http import require_POST

import mock

from .decorators import json_view
from .exceptions import BadRequest


JSON = 'application/json'
rf = RequestFactory()


def eq_(a, b, msg=None):
    """From nose.tools.eq_."""
    assert a == b, msg or '%r != %r' % (a, b)

if sys.version < '3':
    def b(x):
        return x
else:
    import codecs

    def b(x):
        return codecs.latin_1_encode(x)[0]


class JsonViewTests(TestCase):
    def test_object(self):
        data = {
            'foo': 'bar',
            'baz': 'qux',
            'quz': [{'foo': 'bar'}],
        }

        @json_view
        def temp(req):
            return data

        res = temp(rf.get('/'))
        eq_(200, res.status_code)
        eq_(data, json.loads(res.content.decode("utf-8")))
        eq_(JSON, res['content-type'])

    def test_list(self):
        data = ['foo', 'bar', 'baz']

        @json_view
        def temp(req):
            return data

        res = temp(rf.get('/'))
        eq_(200, res.status_code)
        eq_(data, json.loads(res.content.decode("utf-8")))
        eq_(JSON, res['content-type'])

    def test_404(self):
        @json_view
        def temp(req):
            raise http.Http404('foo')

        res = temp(rf.get('/'))
        eq_(404, res.status_code)
        eq_(JSON, res['content-type'])
        data = json.loads(res.content.decode("utf-8"))
        eq_(404, data['error'])
        eq_('foo', data['message'])

    def test_permission(self):
        @json_view
        def temp(req):
            raise PermissionDenied('bar')

        res = temp(rf.get('/'))
        eq_(403, res.status_code)
        eq_(JSON, res['content-type'])
        data = json.loads(res.content.decode("utf-8"))
        eq_(403, data['error'])
        eq_('bar', data['message'])

    def test_bad_request(self):
        @json_view
        def temp(req):
            raise BadRequest('baz')

        res = temp(rf.get('/'))
        eq_(400, res.status_code)
        eq_(JSON, res['content-type'])
        data = json.loads(res.content.decode("utf-8"))
        eq_(400, data['error'])
        eq_('baz', data['message'])

    def test_not_allowed(self):
        @json_view
        @require_POST
        def temp(req):
            return {}

        res = temp(rf.get('/'))
        eq_(405, res.status_code)
        eq_(JSON, res['content-type'])
        data = json.loads(res.content.decode("utf-8"))
        eq_(405, data['error'])

    @override_settings(DEBUG=True)
    def test_server_error_debug(self):
        @json_view
        def temp(req):
            raise TypeError('fail')

        res = temp(rf.get('/'))
        eq_(500, res.status_code)
        eq_(JSON, res['content-type'])
        data = json.loads(res.content.decode("utf-8"))
        eq_(500, data['error'])
        eq_('fail', data['message'])

    @override_settings(DEBUG=False)
    def test_server_error_no_debug(self):
        @json_view
        def temp(req):
            raise TypeError('fail')

        res = temp(rf.get('/'))
        eq_(500, res.status_code)
        eq_(JSON, res['content-type'])
        data = json.loads(res.content.decode('utf-8'))
        eq_(500, data['error'])
        eq_('An error occurred', data['message'])

    def test_http_status(self):
        @json_view
        def temp(req):
            return {}, 402
        res = temp(rf.get('/'))
        eq_(402, res.status_code)
        eq_(JSON, res['content-type'])
        data = json.loads(res.content.decode("utf-8"))
        eq_({}, data)

    def test_headers(self):
        @json_view
        def temp(req):
            return {}, 302, {'X-Foo': 'Bar'}
        res = temp(rf.get('/'))
        eq_(302, res.status_code)
        eq_(JSON, res['content-type'])
        eq_('Bar', res['X-Foo'])
        data = json.loads(res.content.decode("utf-8"))
        eq_({}, data)

    def test_signal_sent(self):
        from . import decorators

        @json_view
        def temp(req):
            [][0]  # sic.

        with mock.patch.object(decorators, 'got_request_exception') as s:
            res = temp(rf.get('/'))

        assert s.send.called
        eq_(JSON, res['content-type'])

    def test_unicode_error(self):
        @json_view
        def temp(req):
            raise http.Http404('page \xe7\xe9 not found')

        res = temp(rf.get('/\xe7\xe9'))
        eq_(404, res.status_code)
        data = json.loads(res.content.decode("utf-8"))
        assert '\xe7\xe9' in data['message']

    def test_override_content_type(self):
        testtype = "application/vnd.helloworld+json"
        data = {"foo": "bar"}

        @json_view(content_type=testtype)
        def temp(req):
            return data

        res = temp(rf.get('/'))
        eq_(200, res.status_code)
        eq_(data, json.loads(res.content.decode("utf-8")))
        eq_(testtype, res['content-type'])

    def test_passthrough_response(self):
        """Allow HttpResponse objects through untouched."""
        payload = json.dumps({'foo': 'bar'}).encode('utf-8')

        @json_view
        def temp(req):
            return http.HttpResponse(payload, content_type='text/plain')

        res = temp(rf.get('/'))
        eq_(200, res.status_code)
        eq_(payload, res.content)
        eq_('text/plain', res['content-type'])

    def test_datetime(self):
        now = timezone.now()

        @json_view
        def temp(req):
            return {"datetime": now}

        res = temp(rf.get('/'))
        eq_(200, res.status_code)
        payload = json.dumps({"datetime": now}, cls=DjangoJSONEncoder)
        eq_(b(payload), res.content)

########NEW FILE########
__FILENAME__ = test_settings
INSTALLED_APPS = ('jsonview',)

SECRET_KEY = 'foo'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    },
}

########NEW FILE########
