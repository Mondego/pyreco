__FILENAME__ = example
from flask import request, url_for
from flask.ext.api import FlaskAPI, status, exceptions

app = FlaskAPI(__name__)


notes = {
    0: 'do the shopping',
    1: 'build the codez',
    2: 'paint the door',
}

def note_repr(key):
    return {
        'url': request.host_url.rstrip('/') + url_for('notes_detail', key=key),
        'text': notes[key]
    }


@app.route("/", methods=['GET', 'POST'])
def notes_list():
    """
    List or create notes.
    """
    if request.method == 'POST':
        note = str(request.data.get('text', ''))
        idx = max(notes.keys()) + 1
        notes[idx] = note
        return note_repr(idx), status.HTTP_201_CREATED

    # request.method == 'GET'
    return [note_repr(idx) for idx in sorted(notes.keys())]


@app.route("/<int:key>/", methods=['GET', 'PUT', 'DELETE'])
def notes_detail(key):
    """
    Retrieve, update or delete note instances.
    """
    if request.method == 'PUT':
        note = str(request.data.get('text', ''))
        notes[key] = note
        return note_repr(key)

    elif request.method == 'DELETE':
        notes.pop(key, None)
        return '', status.HTTP_204_NO_CONTENT

    # request.method == 'GET'
    if key not in notes:
        raise exceptions.NotFound()
    return note_repr(key)


if __name__ == "__main__":
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = app
# coding: utf8
from __future__ import unicode_literals
from flask import request, Flask, Blueprint
from flask._compat import reraise, string_types, text_type
from flask_api.exceptions import APIException
from flask_api.request import APIRequest
from flask_api.response import APIResponse
from flask_api.settings import APISettings
from itertools import chain
from werkzeug.exceptions import HTTPException
import re
import sys


api_resources = Blueprint(
    'flask-api', __name__,
    url_prefix='/flask-api',
    template_folder='templates', static_folder='static'
)


def urlize_quoted_links(content):
    return re.sub(r'"(https?://[^"]*)"', r'"<a href="\1">\1</a>"', content)


class FlaskAPI(Flask):
    request_class = APIRequest
    response_class = APIResponse

    def __init__(self, *args, **kwargs):
        super(FlaskAPI, self).__init__(*args, **kwargs)
        self.api_settings = APISettings(self.config)
        self.register_blueprint(api_resources)
        self.jinja_env.filters['urlize_quoted_links'] = urlize_quoted_links

    def preprocess_request(self):
        request.parser_classes = self.api_settings.DEFAULT_PARSERS
        request.renderer_classes = self.api_settings.DEFAULT_RENDERERS
        return super(FlaskAPI, self).preprocess_request()

    def make_response(self, rv):
        """
        We override this so that we can additionally handle
        list and dict types by default.
        """
        status_or_headers = headers = None
        if isinstance(rv, tuple):
            rv, status_or_headers, headers = rv + (None,) * (3 - len(rv))

        if rv is None and status_or_headers:
            raise ValueError('View function did not return a response')

        if isinstance(status_or_headers, (dict, list)):
            headers, status_or_headers = status_or_headers, None

        if not isinstance(rv, self.response_class):
            if isinstance(rv, (text_type, bytes, bytearray, list, dict)):
                rv = self.response_class(rv, headers=headers, status=status_or_headers)
                headers = status_or_headers = None
            else:
                rv = self.response_class.force_type(rv, request.environ)

        if status_or_headers is not None:
            if isinstance(status_or_headers, string_types):
                rv.status = status_or_headers
            else:
                rv.status_code = status_or_headers
        if headers:
            rv.headers.extend(headers)

        return rv

    def handle_user_exception(self, e):
        """
        We override the default behavior in order to deal with APIException.
        """
        exc_type, exc_value, tb = sys.exc_info()
        assert exc_value is e

        if isinstance(e, HTTPException) and not self.trap_http_exception(e):
            return self.handle_http_exception(e)

        if isinstance(e, APIException):
            return self.handle_api_exception(e)

        blueprint_handlers = ()
        handlers = self.error_handler_spec.get(request.blueprint)
        if handlers is not None:
            blueprint_handlers = handlers.get(None, ())
        app_handlers = self.error_handler_spec[None].get(None, ())
        for typecheck, handler in chain(blueprint_handlers, app_handlers):
            if isinstance(e, typecheck):
                return handler(e)

        reraise(exc_type, exc_value, tb)

    def handle_api_exception(self, exc):
        return APIResponse({'message': exc.detail}, status=exc.status_code)

    def create_url_adapter(self, request):
        """
        We need to override the default behavior slightly here,
        to ensure the any method-based routing takes account of
        any method overloading, so that eg PUT requests from the
        browsable API are routed to the correct view.
        """
        if request is not None:
            environ = request.environ.copy()
            environ['REQUEST_METHOD'] = request.method
            return self.url_map.bind_to_environ(environ,
                server_name=self.config['SERVER_NAME'])
        # We need at the very least the server name to be set for this
        # to work.
        if self.config['SERVER_NAME'] is not None:
            return self.url_map.bind(
                self.config['SERVER_NAME'],
                script_name=self.config['APPLICATION_ROOT'] or '/',
                url_scheme=self.config['PREFERRED_URL_SCHEME'])

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps
from flask import request


def set_parsers(*parsers):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if len(parsers) == 1 and isinstance(parsers[0], (list, tuple)):
                request.parser_classes = parsers[0]
            else:
                request.parser_classes = parsers
            return func(*args, **kwargs)
        return decorated_function
    return decorator


def set_renderers(*renderers):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if len(renderers) == 1 and isinstance(renderers[0], (list, tuple)):
                request.renderer_classes = renderers[0]
            else:
                request.renderer_classes = renderers
            return func(*args, **kwargs)
        return decorated_function
    return decorator

########NEW FILE########
__FILENAME__ = exceptions
from __future__ import unicode_literals
from flask_api import status


class APIException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = ''

    def __init__(self, detail=None):
        if detail is not None:
            self.detail = detail

    def __str__(self):
        return self.detail


class ParseError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = 'Malformed request.'


class AuthenticationFailed(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = 'Incorrect authentication credentials.'


class NotAuthenticated(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = 'Authentication credentials were not provided.'


class PermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = 'You do not have permission to perform this action.'


class NotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = 'This resource does not exist.'

# class MethodNotAllowed(APIException):
#     status_code = status.HTTP_405_METHOD_NOT_ALLOWED
#     detail = 'Request method "%s" not allowed.'

#     def __init__(self, method, detail=None):
#         self.detail = (detail or self.detail) % method


class NotAcceptable(APIException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    detail = 'Could not satisfy the request Accept header.'


class UnsupportedMediaType(APIException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    detail = 'Unsupported media type in the request Content-Type header.'


class Throttled(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = 'Request was throttled.'

#     def __init__(self, wait=None, detail=None):
#         if wait is None:
#             self.detail = detail or self.detail
#             self.wait = None
#         else:
#             format = (detail or self.detail) + ' ' + self.extra_detail
#             self.detail = format % (wait, wait != 1 and 's' or '')
#             self.wait = math.ceil(wait)

########NEW FILE########
__FILENAME__ = mediatypes
# coding: utf8
from __future__ import unicode_literals


class MediaType(object):
    def __init__(self, media_type):
        self.main_type, self.sub_type, self.params = self._parse(media_type)

    @property
    def full_type(self):
        return self.main_type + '/' + self.sub_type

    @property
    def precedence(self):
        """
        Precedence is determined by how specific a media type is:

        3. 'type/subtype; param=val'
        2. 'type/subtype'
        1. 'type/*'
        0. '*/*'
        """
        if self.main_type == '*':
            return 0
        elif self.sub_type == '*':
            return 1
        elif not self.params or list(self.params.keys()) == ['q']:
            return 2
        return 3

    def satisfies(self, other):
        """
        Returns `True` if this media type is a superset of `other`.
        Some examples of cases where this holds true:

        'application/json; version=1.0' >= 'application/json; version=1.0'
        'application/json'              >= 'application/json; indent=4'
        'text/*'                        >= 'text/plain'
        '*/*'                           >= 'text/plain'
        """
        for key in self.params.keys():
            if key != 'q' and other.params.get(key, None) != self.params.get(key, None):
                return False

        if self.sub_type != '*' and other.sub_type != '*' and other.sub_type != self.sub_type:
            return False

        if self.main_type != '*' and other.main_type != '*' and other.main_type != self.main_type:
            return False

        return True

    def _parse(self, media_type):
        """
        Parse a media type string, like "application/json; indent=4" into a
        three-tuple, like: ('application', 'json', {'indent': 4})
        """
        full_type, sep, param_string = media_type.partition(';')
        params = {}
        for token in param_string.strip().split(','):
            key, sep, value = [s.strip() for s in token.partition('=')]
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            if key:
                params[key] = value
        main_type, sep, sub_type = [s.strip() for s in full_type.partition('/')]
        return (main_type, sub_type, params)

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, str(self))

    def __str__(self):
        """
        Return a canonical string representing the media type.
        Note that this ensures the params are sorted.
        """
        if self.params:
            params_str = ', '.join([
                '%s="%s"' % (key, val)
                for key, val in sorted(self.params.items())
            ])
            return self.full_type + '; ' + params_str
        return self.full_type

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        # Compare two MediaType instances, ignoring parameter ordering.
        return (
            self.full_type == other.full_type and
            self.params == other.params
        )


def parse_accept_header(accept):
    """
    Parses the value of a clients accept header, and returns a list of sets
    of media types it included, ordered by precedence.

    For example, 'application/json, application/xml, */*' would return:

    [
        set([<MediaType "application/xml">, <MediaType "application/json">]),
        set([<MediaType "*/*">])
    ]
    """
    ret = [set(), set(), set(), set()]
    for token in accept.split(','):
        media_type = MediaType(token.strip())
        ret[3 - media_type.precedence].add(media_type)
    return [media_types for media_types in ret if media_types]

########NEW FILE########
__FILENAME__ = negotiation
# coding: utf8
from __future__ import unicode_literals
from flask import request
from flask_api import exceptions
from flask_api.mediatypes import MediaType, parse_accept_header


class BaseNegotiation(object):
    def select_parser(self, parsers):
        msg = '`select_parser()` method must be implemented for class "%s"'
        raise NotImplementedError(msg % self.__class__.__name__)

    def select_renderer(self, renderers):
        msg = '`select_renderer()` method must be implemented for class "%s"'
        raise NotImplementedError(msg % self.__class__.__name__)


class DefaultNegotiation(BaseNegotiation):
    def select_parser(self, parsers):
        """
        Determine which parser to use for parsing the request body.
        Returns a two-tuple of (parser, content type).
        """
        content_type_header = request.content_type

        client_media_type = MediaType(content_type_header)
        for parser in parsers:
            server_media_type = MediaType(parser.media_type)
            if server_media_type.satisfies(client_media_type):
                return (parser, client_media_type)

        raise exceptions.UnsupportedMediaType()

    def select_renderer(self, renderers):
        """
        Determine which renderer to use for rendering the response body.
        Returns a two-tuple of (renderer, content type).
        """
        accept_header = request.headers.get('Accept', '*/*')

        for client_media_types in parse_accept_header(accept_header):
            for renderer in renderers:
                server_media_type = MediaType(renderer.media_type)
                for client_media_type in client_media_types:
                    if client_media_type.satisfies(server_media_type):
                        if server_media_type.precedence > client_media_type.precedence:
                            return (renderer, server_media_type)
                        else:
                            return (renderer, client_media_type)

        raise exceptions.NotAcceptable()

########NEW FILE########
__FILENAME__ = parsers
# coding: utf8
from __future__ import unicode_literals
from flask._compat import text_type
from flask_api import exceptions
from werkzeug.formparser import MultiPartParser as WerkzeugMultiPartParser
from werkzeug.formparser import default_stream_factory
from werkzeug.urls import url_decode_stream
import json


class BaseParser(object):
    media_type = None
    handles_file_uploads = False  # If set then 'request.files' will be populated.
    handles_form_data = False     # If set then 'request.form' will be populated.

    def parse(self, stream, media_type, **options):
        msg = '`parse()` method must be implemented for class "%s"'
        raise NotImplementedError(msg % self.__class__.__name__)


class JSONParser(BaseParser):
    media_type = 'application/json'

    def parse(self, stream, media_type, **options):
        data = stream.read().decode('utf-8')
        try:
            return json.loads(data)
        except ValueError as exc:
            msg = 'JSON parse error - %s' % text_type(exc)
            raise exceptions.ParseError(msg)


class MultiPartParser(BaseParser):
    media_type = 'multipart/form-data'
    handles_file_uploads = True
    handles_form_data = True

    def parse(self, stream, media_type, **options):
        multipart_parser = WerkzeugMultiPartParser(default_stream_factory)

        boundary = media_type.params.get('boundary')
        if boundary is None:
            msg = 'Multipart message missing boundary in Content-Type header'
            raise exceptions.ParseError(msg)
        boundary = boundary.encode('ascii')

        content_length = options.get('content_length')
        assert content_length is not None, 'MultiPartParser.parse() requires `content_length` argument'

        try:
            return multipart_parser.parse(stream, boundary, content_length)
        except ValueError as exc:
            msg = 'Multipart parse error - %s' % text_type(exc)
            raise exceptions.ParseError(msg)


class URLEncodedParser(BaseParser):
    media_type = 'application/x-www-form-urlencoded'
    handles_form_data = True

    def parse(self, stream, media_type, **options):
        return url_decode_stream(stream)

########NEW FILE########
__FILENAME__ = renderers
# coding: utf8
from __future__ import unicode_literals
from flask import request, render_template, current_app
from flask.json import JSONEncoder
from flask.globals import _request_ctx_stack
from flask_api.mediatypes import MediaType
import json
import re


def dedent(content):
    """
    Remove leading indent from a block of text.
    Used when generating descriptions from docstrings.

    Note that python's `textwrap.dedent` doesn't quite cut it,
    as it fails to dedent multiline docstrings that include
    unindented text on the initial line.
    """
    whitespace_counts = [len(line) - len(line.lstrip(' '))
                         for line in content.splitlines()[1:] if line.lstrip()]

    # unindent the content if needed
    if whitespace_counts:
        whitespace_pattern = '^' + (' ' * min(whitespace_counts))
        content = re.sub(re.compile(whitespace_pattern, re.MULTILINE), '', content)

    return content.strip()


def convert_to_title(name):
    return name.replace('-', ' ').replace('_', ' ').capitalize()


class BaseRenderer(object):
    media_type = None
    charset = 'utf-8'
    handles_empty_responses = False

    def render(self, data, media_type, **options):
        msg = '`render()` method must be implemented for class "%s"'
        raise NotImplementedError(msg % self.__class__.__name__)


class JSONRenderer(BaseRenderer):
    media_type = 'application/json'
    charset = None

    def render(self, data, media_type, **options):
        # Requested indentation may be set in the Accept header.
        try:
            indent = max(min(int(media_type.params['indent']), 8), 0)
        except (KeyError, ValueError, TypeError):
            indent = None
        # Indent may be set explicitly, eg when rendered by the browsable API.
        indent = options.get('indent', indent)
        return json.dumps(data, cls=JSONEncoder, ensure_ascii=False, indent=indent)


class HTMLRenderer(object):
    media_type = 'text/html'
    charset = 'utf-8'

    def render(self, data, media_type, **options):
        return data.encode(self.charset)


class BrowsableAPIRenderer(BaseRenderer):
    media_type = 'text/html'
    handles_empty_responses = True

    def render(self, data, media_type, **options):
        # Render the content as it would have been if the client
        # had requested 'Accept: */*'.
        available_renderers = [
            renderer for renderer in request.renderer_classes
            if not issubclass(renderer, BrowsableAPIRenderer)
        ]
        assert available_renderers, 'BrowsableAPIRenderer cannot be the only renderer'
        mock_renderer = available_renderers[0]()
        mock_media_type = MediaType(mock_renderer.media_type)
        if data == '' and not mock_renderer.handles_empty_responses:
            mock_content = None
        else:
            mock_content = mock_renderer.render(data, mock_media_type, indent=4)

        # Determine the allowed methods on this view.
        adapter = _request_ctx_stack.top.url_adapter
        allowed_methods = adapter.allowed_methods()

        endpoint = request.url_rule.endpoint
        view_name = str(endpoint)
        view_description = current_app.view_functions[endpoint].__doc__
        if view_description is not None:
            view_description = dedent(view_description)

        status = options['status']
        headers = options['headers']
        headers['Content-Type'] = str(mock_media_type)

        from flask_api import __version__

        context = {
            'status': status,
            'headers': headers,
            'content': mock_content,
            'allowed_methods': allowed_methods,
            'view_name': convert_to_title(view_name),
            'view_description': view_description,
            'version': __version__
        }
        return render_template('base.html', **context)

########NEW FILE########
__FILENAME__ = request
# coding: utf8
from __future__ import unicode_literals
from flask import Request
from flask_api.negotiation import DefaultNegotiation
from flask_api.settings import default_settings
from werkzeug.datastructures import MultiDict
from werkzeug.urls import url_decode_stream
from werkzeug.wsgi import get_content_length
from werkzeug._compat import to_unicode
import io


class APIRequest(Request):
    parser_classes = default_settings.DEFAULT_PARSERS
    renderer_classes = default_settings.DEFAULT_RENDERERS
    negotiator_class = DefaultNegotiation
    empty_data_class = MultiDict

    # Request parsing...

    @property
    def data(self):
        if not hasattr(self, '_data'):
            self._parse()
        return self._data

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._parse()
        return self._form

    @property
    def files(self):
        if not hasattr(self, '_files'):
            self._parse()
        return self._files

    def _parse(self):
        """
        Parse the body of the request, using whichever parser satifies the
        client 'Content-Type' header.
        """
        if not self.content_type or not self.content_length:
            self._set_empty_data()
            return

        negotiator = self.negotiator_class()
        parsers = [parser_cls() for parser_cls in self.parser_classes]
        options = self._get_parser_options()
        try:
            parser, media_type = negotiator.select_parser(parsers)
            ret = parser.parse(self.stream, media_type, **options)
        except:
            # Ensure that accessing `request.data` again does not reraise
            # the exception, so that eg exceptions can handle properly.
            self._set_empty_data()
            raise

        if parser.handles_file_uploads:
            assert isinstance(ret, tuple) and len(ret) == 2, 'Expected a two-tuple of (data, files)'
            self._data, self._files = ret
        else:
            self._data = ret
            self._files = self.empty_data_class()

        self._form = self._data if parser.handles_form_data else self.empty_data_class()

    def _get_parser_options(self):
        """
        Any additional information to pass to the parser.
        """
        return {'content_length': self.content_length}

    def _set_empty_data(self):
        """
        If the request does not contain data then return an empty representation.
        """
        self._data = self.empty_data_class()
        self._form = self.empty_data_class()
        self._files = self.empty_data_class()

    # Content negotiation...

    @property
    def accepted_renderer(self):
        if not hasattr(self, '_accepted_renderer'):
            self._perform_content_negotiation()
        return self._accepted_renderer

    @property
    def accepted_media_type(self):
        if not hasattr(self, '_accepted_media_type'):
            self._perform_content_negotiation()
        return self._accepted_media_type

    def _perform_content_negotiation(self):
        """
        Determine which of the available renderers should be used for
        rendering the response content, based on the client 'Accept' header.
        """
        negotiator = self.negotiator_class()
        renderers = [renderer() for renderer in self.renderer_classes]
        self._accepted_renderer, self._accepted_media_type = negotiator.select_renderer(renderers)

    # Method and content type overloading.

    @property
    def method(self):
        if not hasattr(self, '_method'):
            self._perform_method_overloading()
        return self._method

    @property
    def content_type(self):
        if not hasattr(self, '_content_type'):
            self._perform_method_overloading()
        return self._content_type

    @property
    def content_length(self):
        if not hasattr(self, '_content_length'):
            self._perform_method_overloading()
        return self._content_length

    @property
    def stream(self):
        if not hasattr(self, '_stream'):
            self._perform_method_overloading()
        return self._stream

    def _perform_method_overloading(self):
        """
        Perform method and content type overloading.

        Provides support for browser PUT, PATCH, DELETE & other requests,
        by specifing a '_method' form field.

        Also provides support for browser non-form requests (eg JSON),
        by specifing '_content' and '_content_type' form fields.
        """
        self._method = super(APIRequest, self).method
        self._stream = super(APIRequest, self).stream
        self._content_type = self.headers.get('Content-Type')
        self._content_length = get_content_length(self.environ)

        if (self._method == 'POST' and self._content_type == 'application/x-www-form-urlencoded'):
            # Read the request data, then push it back onto the stream again.
            body = self.get_data()
            data = url_decode_stream(io.BytesIO(body))
            self._stream = io.BytesIO(body)
            if '_method' in data:
                # Support browser forms with PUT, PATCH, DELETE & other methods.
                self._method = data['_method']
            if '_content' in data and '_content_type' in data:
                # Support browser forms with non-form data, such as JSON.
                body = data['_content'].encode('utf8')
                self._stream = io.BytesIO(body)
                self._content_type = data['_content_type']
                self._content_length = len(body)

    # Misc...

    @property
    def full_path(self):
        """
        Werzueg's full_path implementation always appends '?', even when the
        query string is empty.  Let's fix that.
        """
        if not self.query_string:
            return self.path
        return self.path + u'?' + to_unicode(self.query_string, self.url_charset)

    # @property
    # def auth(self):
    #     if not has_attribute(self, '_auth'):
    #         self._authenticate()
    #     return self._auth

    # def _authenticate(self):
    #     for authentication_class in self.authentication_classes:
    #         authenticator = authentication_class()
    #         try:
    #             auth = authenticator.authenticate(self)
    #         except exceptions.APIException:
    #             self._not_authenticated()
    #             raise

    #         if not auth is None:
    #             self._authenticator = authenticator
    #             self._auth = auth
    #             return

    #     self._not_authenticated()

    # def _not_authenticated(self):
    #     self._authenticator = None
    #     self._auth = None

########NEW FILE########
__FILENAME__ = response
# coding: utf8
from __future__ import unicode_literals
from flask import request, Response
from flask._compat import text_type, string_types


class APIResponse(Response):
    def __init__(self, content=None, *args, **kwargs):
        super(APIResponse, self).__init__(None, *args, **kwargs)

        media_type = None
        if isinstance(content, (list, dict, text_type, string_types)):
            renderer = request.accepted_renderer
            if content != '' or renderer.handles_empty_responses:
                media_type = request.accepted_media_type
                options = self.get_renderer_options()
                content = renderer.render(content, media_type, **options)
                if self.status_code == 204:
                    self.status_code = 200

        if isinstance(content, (text_type, bytes, bytearray)):
            self.set_data(content)
        else:
            self.response = content

        if media_type is not None:
            self.headers['Content-Type'] = str(media_type)

    def get_renderer_options(self):
        return {
            'status': self.status,
            'status_code': self.status_code,
            'headers': self.headers
        }

########NEW FILE########
__FILENAME__ = settings
from flask._compat import string_types
import importlib


def perform_imports(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if isinstance(val, string_types):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [perform_imports(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        # Nod to tastypie's use of importlib.
        parts = val.split('.')
        module_path, class_name = '.'.join(parts[:-1]), parts[-1]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except ImportError as exc:
        format = "Could not import '%s' for API setting '%s'. %s."
        msg = format % (val, setting_name, exc)
        raise ImportError(msg)


class APISettings(object):
    def __init__(self, user_config=None):
        self.user_config = user_config or {}

    @property
    def DEFAULT_PARSERS(self):
        default = [
            'flask_api.parsers.JSONParser',
            'flask_api.parsers.URLEncodedParser',
            'flask_api.parsers.MultiPartParser'
        ]
        val = self.user_config.get('DEFAULT_PARSERS', default)
        return perform_imports(val, 'DEFAULT_PARSERS')

    @property
    def DEFAULT_RENDERERS(self):
        default = [
            'flask_api.renderers.JSONRenderer',
            'flask_api.renderers.BrowsableAPIRenderer'
        ]
        val = self.user_config.get('DEFAULT_RENDERERS', default)
        return perform_imports(val, 'DEFAULT_RENDERERS')


default_settings = APISettings()

########NEW FILE########
__FILENAME__ = status
# coding: utf8
"""
Descriptive HTTP status codes, for code readability.

See RFC 2616 and RFC 6585.

RFC 2616: http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
RFC 6585: http://tools.ietf.org/html/rfc6585
"""
from __future__ import unicode_literals


def is_informational(code):
    return code >= 100 and code <= 199


def is_success(code):
    return code >= 200 and code <= 299


def is_redirect(code):
    return code >= 300 and code <= 399


def is_client_error(code):
    return code >= 400 and code <= 499


def is_server_error(code):
    return code >= 500 and code <= 599


HTTP_100_CONTINUE = 100
HTTP_101_SWITCHING_PROTOCOLS = 101
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_202_ACCEPTED = 202
HTTP_203_NON_AUTHORITATIVE_INFORMATION = 203
HTTP_204_NO_CONTENT = 204
HTTP_205_RESET_CONTENT = 205
HTTP_206_PARTIAL_CONTENT = 206
HTTP_300_MULTIPLE_CHOICES = 300
HTTP_301_MOVED_PERMANENTLY = 301
HTTP_302_FOUND = 302
HTTP_303_SEE_OTHER = 303
HTTP_304_NOT_MODIFIED = 304
HTTP_305_USE_PROXY = 305
HTTP_306_RESERVED = 306
HTTP_307_TEMPORARY_REDIRECT = 307
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_402_PAYMENT_REQUIRED = 402
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_405_METHOD_NOT_ALLOWED = 405
HTTP_406_NOT_ACCEPTABLE = 406
HTTP_407_PROXY_AUTHENTICATION_REQUIRED = 407
HTTP_408_REQUEST_TIMEOUT = 408
HTTP_409_CONFLICT = 409
HTTP_410_GONE = 410
HTTP_411_LENGTH_REQUIRED = 411
HTTP_412_PRECONDITION_FAILED = 412
HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_414_REQUEST_URI_TOO_LONG = 414
HTTP_415_UNSUPPORTED_MEDIA_TYPE = 415
HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE = 416
HTTP_417_EXPECTATION_FAILED = 417
HTTP_428_PRECONDITION_REQUIRED = 428
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE = 431
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_501_NOT_IMPLEMENTED = 501
HTTP_502_BAD_GATEWAY = 502
HTTP_503_SERVICE_UNAVAILABLE = 503
HTTP_504_GATEWAY_TIMEOUT = 504
HTTP_505_HTTP_VERSION_NOT_SUPPORTED = 505
HTTP_511_NETWORK_AUTHENTICATION_REQUIRED = 511

########NEW FILE########
__FILENAME__ = runtests
import unittest
import sys


if __name__ == '__main__':
    if len(sys.argv) > 1:
        unittest.main(module='flask_api.tests')
    else:
        argv = ['flask_api', 'discover', '-s', 'flask_api/tests']
        unittest.main(argv=argv)

########NEW FILE########
__FILENAME__ = test_app
# coding: utf8
from __future__ import unicode_literals
from flask import abort, make_response, request
from flask_api.decorators import set_renderers
from flask_api import exceptions, renderers, status, FlaskAPI
import json
import unittest


app = FlaskAPI(__name__)
app.config['TESTING'] = True


class JSONVersion1(renderers.JSONRenderer):
    media_type = 'application/json; api-version="1.0"'


class JSONVersion2(renderers.JSONRenderer):
    media_type = 'application/json; api-version="2.0"'


@app.route('/set_status_and_headers/')
def set_status_and_headers():
    headers = {'Location': 'http://example.com/456'}
    return {'example': 'content'}, status.HTTP_201_CREATED, headers


@app.route('/set_headers/')
def set_headers():
    headers = {'Location': 'http://example.com/456'}
    return {'example': 'content'}, headers


@app.route('/make_response_view/')
def make_response_view():
    response = make_response({'example': 'content'})
    response.headers['Location'] = 'http://example.com/456'
    return response


@app.route('/api_exception/')
def api_exception():
    raise exceptions.PermissionDenied()


@app.route('/abort_view/')
def abort_view():
    abort(status.HTTP_403_FORBIDDEN)


@app.route('/accepted_media_type/')
@set_renderers([JSONVersion2, JSONVersion1])
def accepted_media_type():
    return {'accepted_media_type': str(request.accepted_media_type)}


class AppTests(unittest.TestCase):
    def test_set_status_and_headers(self):
        with app.test_client() as client:
            response = client.get('/set_status_and_headers/')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.headers['Location'], 'http://example.com/456')
            self.assertEqual(response.content_type, 'application/json')
            expected = '{"example": "content"}'
            self.assertEqual(response.get_data().decode('utf8'), expected)

    def test_set_headers(self):
        with app.test_client() as client:
            response = client.get('/set_headers/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Location'], 'http://example.com/456')
            self.assertEqual(response.content_type, 'application/json')
            expected = '{"example": "content"}'
            self.assertEqual(response.get_data().decode('utf8'), expected)

    def test_make_response(self):
        with app.test_client() as client:
            response = client.get('/make_response_view/')
            self.assertEqual(response.content_type, 'application/json')
            self.assertEqual(response.headers['Location'], 'http://example.com/456')
            self.assertEqual(response.content_type, 'application/json')
            expected = '{"example": "content"}'
            self.assertEqual(response.get_data().decode('utf8'), expected)

    def test_api_exception(self):
        with app.test_client() as client:
            response = client.get('/api_exception/')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(response.content_type, 'application/json')
            expected = '{"message": "You do not have permission to perform this action."}'
            self.assertEqual(response.get_data().decode('utf8'), expected)

    def test_abort_view(self):
        with app.test_client() as client:
            response = client.get('/abort_view/')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_accepted_media_type_property(self):
        with app.test_client() as client:
            # Explicitly request the "api-version 1.0" renderer.
            headers = {'Accept': 'application/json; api-version="1.0"'}
            response = client.get('/accepted_media_type/', headers=headers)
            data = json.loads(response.get_data().decode('utf8'))
            expected = {'accepted_media_type': 'application/json; api-version="1.0"'}
            self.assertEqual(data, expected)

            # Request the default renderer, which is "api-version 2.0".
            headers = {'Accept': '*/*'}
            response = client.get('/accepted_media_type/', headers=headers)
            data = json.loads(response.get_data().decode('utf8'))
            expected = {'accepted_media_type': 'application/json; api-version="2.0"'}
            self.assertEqual(data, expected)

########NEW FILE########
__FILENAME__ = test_exceptions
# coding: utf8
from __future__ import unicode_literals
from flask_api import exceptions
from flask_api import status
import unittest


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    detail = 'Could not update the resource'


class TestExceptions(unittest.TestCase):
    def test_custom_exception(self):
        try:
            raise Conflict()
        except Conflict as exc:
            self.assertEqual(str(exc), 'Could not update the resource')
            self.assertEqual(exc.status_code, 409)

    def test_override_exception_detail(self):
        try:
            raise Conflict('A widget with this id already exists')
        except Conflict as exc:
            self.assertEqual(str(exc), 'A widget with this id already exists')
            self.assertEqual(exc.status_code, 409)

########NEW FILE########
__FILENAME__ = test_mediatypes
# coding: utf8
from __future__ import unicode_literals
from flask_api.mediatypes import MediaType, parse_accept_header
import unittest


class MediaTypeParsingTests(unittest.TestCase):
    def test_media_type_with_params(self):
        media = MediaType('application/xml; schema=foobar, q=0.5')
        self.assertEqual(str(media), 'application/xml; q="0.5", schema="foobar"')
        self.assertEqual(media.main_type, 'application')
        self.assertEqual(media.sub_type, 'xml')
        self.assertEqual(media.full_type, 'application/xml')
        self.assertEqual(media.params, {'schema': 'foobar', 'q': '0.5'})
        self.assertEqual(media.precedence, 3)
        self.assertEqual(repr(media), '<MediaType \'application/xml; q="0.5", schema="foobar"\'>')

    def test_media_type_with_q_params(self):
        media = MediaType('application/xml; q=0.5')
        self.assertEqual(str(media), 'application/xml; q="0.5"')
        self.assertEqual(media.main_type, 'application')
        self.assertEqual(media.sub_type, 'xml')
        self.assertEqual(media.full_type, 'application/xml')
        self.assertEqual(media.params, {'q': '0.5'})
        self.assertEqual(media.precedence, 2)

    def test_media_type_without_params(self):
        media = MediaType('application/xml')
        self.assertEqual(str(media), 'application/xml')
        self.assertEqual(media.main_type, 'application')
        self.assertEqual(media.sub_type, 'xml')
        self.assertEqual(media.full_type, 'application/xml')
        self.assertEqual(media.params, {})
        self.assertEqual(media.precedence, 2)

    def test_media_type_with_wildcard_sub_type(self):
        media = MediaType('application/*')
        self.assertEqual(str(media), 'application/*')
        self.assertEqual(media.main_type, 'application')
        self.assertEqual(media.sub_type, '*')
        self.assertEqual(media.full_type, 'application/*')
        self.assertEqual(media.params, {})
        self.assertEqual(media.precedence, 1)

    def test_media_type_with_wildcard_main_type(self):
        media = MediaType('*/*')
        self.assertEqual(str(media), '*/*')
        self.assertEqual(media.main_type, '*')
        self.assertEqual(media.sub_type, '*')
        self.assertEqual(media.full_type, '*/*')
        self.assertEqual(media.params, {})
        self.assertEqual(media.precedence, 0)


class MediaTypeMatchingTests(unittest.TestCase):
    def test_media_type_includes_params(self):
        media_type = MediaType('application/json')
        other = MediaType('application/json; version=1.0')
        self.assertTrue(media_type.satisfies(other))

    def test_media_type_missing_params(self):
        media_type = MediaType('application/json; version=1.0')
        other = MediaType('application/json')
        self.assertFalse(media_type.satisfies(other))

    def test_media_type_matching_params(self):
        media_type = MediaType('application/json; version=1.0')
        other = MediaType('application/json; version=1.0')
        self.assertTrue(media_type.satisfies(other))

    def test_media_type_non_matching_params(self):
        media_type = MediaType('application/json; version=1.0')
        other = MediaType('application/json; version=2.0')
        self.assertFalse(media_type.satisfies(other))

    def test_media_type_main_type_match(self):
        media_type = MediaType('image/*')
        other = MediaType('image/png')
        self.assertTrue(media_type.satisfies(other))

    def test_media_type_sub_type_mismatch(self):
        media_type = MediaType('image/jpeg')
        other = MediaType('image/png')
        self.assertFalse(media_type.satisfies(other))

    def test_media_type_wildcard_match(self):
        media_type = MediaType('*/*')
        other = MediaType('image/png')
        self.assertTrue(media_type.satisfies(other))

    def test_media_type_wildcard_mismatch(self):
        media_type = MediaType('image/*')
        other = MediaType('audio/*')
        self.assertFalse(media_type.satisfies(other))


class AcceptHeaderTests(unittest.TestCase):
    def test_parse_simple_accept_header(self):
        parsed = parse_accept_header('*/*, application/json')
        self.assertEqual(parsed, [
            set([MediaType('application/json')]),
            set([MediaType('*/*')])
        ])

    def test_parse_complex_accept_header(self):
        """
        The accept header should be parsed into a list of sets of MediaType.
        The list is an ordering of precedence.

        Note that we disregard 'q' values when determining precedence, and
        instead differentiate equal values by using the server preference.
        """
        header = 'application/xml; schema=foo, application/json; q=0.9, application/xml, */*'
        parsed = parse_accept_header(header)
        self.assertEqual(parsed, [
            set([MediaType('application/xml; schema=foo')]),
            set([MediaType('application/json; q=0.9'), MediaType('application/xml')]),
            set([MediaType('*/*')]),
        ])

########NEW FILE########
__FILENAME__ = test_negotiation
# coding: utf8
from __future__ import unicode_literals
import unittest
import flask_api
from flask_api import exceptions
from flask_api.negotiation import BaseNegotiation, DefaultNegotiation


app = flask_api.FlaskAPI(__name__)


class JSON(object):
    media_type = 'application/json'


class HTML(object):
    media_type = 'application/html'


class URLEncodedForm(object):
    media_type = 'application/x-www-form-urlencoded'


class TestRendererNegotiation(unittest.TestCase):
    def test_select_renderer_client_preference(self):
        negotiation = DefaultNegotiation()
        renderers = [JSON, HTML]
        headers = {'Accept': 'application/html'}
        with app.test_request_context(headers=headers):
            renderer, media_type = negotiation.select_renderer(renderers)
            self.assertEqual(renderer, HTML)
            self.assertEqual(str(media_type), 'application/html')

    def test_select_renderer_no_accept_header(self):
        negotiation = DefaultNegotiation()
        renderers = [JSON, HTML]
        with app.test_request_context():
            renderer, media_type = negotiation.select_renderer(renderers)
            self.assertEqual(renderer, JSON)
            self.assertEqual(str(media_type), 'application/json')

    def test_select_renderer_server_preference(self):
        negotiation = DefaultNegotiation()
        renderers = [JSON, HTML]
        headers = {'Accept': '*/*'}
        with app.test_request_context(headers=headers):
            renderer, media_type = negotiation.select_renderer(renderers)
            self.assertEqual(renderer, JSON)
            self.assertEqual(str(media_type), 'application/json')

    def test_select_renderer_failed(self):
        negotiation = DefaultNegotiation()
        renderers = [JSON, HTML]
        headers = {'Accept': 'application/xml'}
        with app.test_request_context(headers=headers):
            with self.assertRaises(exceptions.NotAcceptable):
                renderer, media_type = negotiation.select_renderer(renderers)

    def test_renderer_negotiation_not_implemented(self):
        negotiation = BaseNegotiation()
        with self.assertRaises(NotImplementedError) as context:
            negotiation.select_renderer([])
        msg = str(context.exception)
        expected = '`select_renderer()` method must be implemented for class "BaseNegotiation"'
        self.assertEqual(msg, expected)


class TestParserNegotiation(unittest.TestCase):
    def test_select_parser(self):
        negotiation = DefaultNegotiation()
        parsers = [JSON, URLEncodedForm]
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        with app.test_request_context(headers=headers):
            renderer, media_type = negotiation.select_parser(parsers)
            self.assertEqual(renderer, URLEncodedForm)
            self.assertEqual(str(media_type), 'application/x-www-form-urlencoded')

    def test_select_parser_failed(self):
        negotiation = DefaultNegotiation()
        parsers = [JSON, URLEncodedForm]
        headers = {'Content-Type': 'application/xml'}
        with app.test_request_context(headers=headers):
            with self.assertRaises(exceptions.UnsupportedMediaType):
                renderer, media_type = negotiation.select_parser(parsers)

    def test_parser_negotiation_not_implemented(self):
        negotiation = BaseNegotiation()
        with self.assertRaises(NotImplementedError) as context:
            negotiation.select_parser([])
        msg = str(context.exception)
        expected = '`select_parser()` method must be implemented for class "BaseNegotiation"'
        self.assertEqual(msg, expected)

########NEW FILE########
__FILENAME__ = test_parsers
# coding: utf8
from __future__ import unicode_literals
from flask import request
from flask_api import exceptions, parsers, status, mediatypes, FlaskAPI
from flask_api.decorators import set_parsers
import io
import json
import unittest


app = FlaskAPI(__name__)


@app.route('/', methods=['POST'])
def data():
    return {
        'data': request.data,
        'form': request.form,
        'files': dict([
            (key, {'name': val.filename, 'contents': val.read().decode('utf8')})
            for key, val in request.files.items()
        ])
    }


class ParserTests(unittest.TestCase):
    def test_valid_json(self):
        parser = parsers.JSONParser()
        stream = io.BytesIO(b'{"key": 1, "other": "two"}')
        data = parser.parse(stream, 'application/json')
        self.assertEqual(data, {"key": 1, "other": "two"})

    def test_invalid_json(self):
        parser = parsers.JSONParser()
        stream = io.BytesIO(b'{key: 1, "other": "two"}')
        with self.assertRaises(exceptions.ParseError) as context:
            parser.parse(stream, mediatypes.MediaType('application/json'))
        detail = str(context.exception)
        expected_py2 = 'JSON parse error - Expecting property name: line 1 column 1 (char 1)'
        expected_py3 = 'JSON parse error - Expecting property name enclosed in double quotes: line 1 column 2 (char 1)'
        self.assertIn(detail, (expected_py2, expected_py3))

    def test_invalid_multipart(self):
        parser = parsers.MultiPartParser()
        stream = io.BytesIO(b'invalid')
        media_type = mediatypes.MediaType('multipart/form-data; boundary="foo"')
        with self.assertRaises(exceptions.ParseError) as context:
            parser.parse(stream, media_type, content_length=len('invalid'))
        detail = str(context.exception)
        expected = 'Multipart parse error - Expected boundary at start of multipart data'
        self.assertEqual(detail, expected)

    def test_invalid_multipart_no_boundary(self):
        parser = parsers.MultiPartParser()
        stream = io.BytesIO(b'invalid')
        with self.assertRaises(exceptions.ParseError) as context:
            parser.parse(stream, mediatypes.MediaType('multipart/form-data'))
        detail = str(context.exception)
        expected = 'Multipart message missing boundary in Content-Type header'
        self.assertEqual(detail, expected)

    def test_renderer_negotiation_not_implemented(self):
        parser = parsers.BaseParser()
        with self.assertRaises(NotImplementedError) as context:
            parser.parse(None, None)
        msg = str(context.exception)
        expected = '`parse()` method must be implemented for class "BaseParser"'
        self.assertEqual(msg, expected)

    def test_accessing_json(self):
        with app.test_client() as client:
            data = json.dumps({'example': 'example'})
            response = client.post('/', data=data, content_type='application/json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/json')
            data = json.loads(response.get_data().decode('utf8'))
            expected = {
                "data": {"example": "example"},
                "form": {},
                "files": {}
            }
            self.assertEqual(data, expected)

    def test_accessing_url_encoded(self):
        with app.test_client() as client:
            data = {'example': 'example'}
            response = client.post('/', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/json')
            data = json.loads(response.get_data().decode('utf8'))
            expected = {
                "data": {"example": "example"},
                "form": {"example": "example"},
                "files": {}
            }
            self.assertEqual(data, expected)

    def test_accessing_multipart(self):
        with app.test_client() as client:
            data = {'example': 'example', 'upload': (io.BytesIO(b'file contents'), 'name.txt')}
            response = client.post('/', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/json')
            data = json.loads(response.get_data().decode('utf8'))
            expected = {
                "data": {"example": "example"},
                "form": {"example": "example"},
                "files": {"upload": {"name": "name.txt", "contents": "file contents"}}
            }
            self.assertEqual(data, expected)


class OverrideParserSettings(unittest.TestCase):
    def setUp(self):
        class CustomParser1(parsers.BaseParser):
            media_type = '*/*'

            def parse(self, stream, media_type, content_length=None):
                return 'custom parser 1'

        class CustomParser2(parsers.BaseParser):
            media_type = '*/*'

            def parse(self, stream, media_type, content_length=None):
                return 'custom parser 2'

        app = FlaskAPI(__name__)
        app.config['DEFAULT_PARSERS'] = [CustomParser1]

        @app.route('/custom_parser_1/', methods=['POST'])
        def custom_parser_1():
            return {'data': request.data}

        @app.route('/custom_parser_2/', methods=['POST'])
        @set_parsers([CustomParser2])
        def custom_parser_2():
            return {'data': request.data}

        @app.route('/custom_parser_2_as_args/', methods=['POST'])
        @set_parsers(CustomParser2, CustomParser1)
        def custom_parser_2_as_args():
            return {'data': request.data}

        self.app = app

    def test_overridden_parsers_with_settings(self):
        with self.app.test_client() as client:
            data = {'example': 'example'}
            response = client.post('/custom_parser_1/', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/json')
            data = json.loads(response.get_data().decode('utf8'))
            expected = {
                "data": "custom parser 1",
            }
            self.assertEqual(data, expected)

    def test_overridden_parsers_with_decorator(self):
        with self.app.test_client() as client:
            data = {'example': 'example'}
            response = client.post('/custom_parser_2/', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/json')
            data = json.loads(response.get_data().decode('utf8'))
            expected = {
                "data": "custom parser 2",
            }
            self.assertEqual(data, expected)

    def test_overridden_parsers_with_decorator_as_args(self):
        with self.app.test_client() as client:
            data = {'example': 'example'}
            response = client.post('/custom_parser_2_as_args/', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/json')
            data = json.loads(response.get_data().decode('utf8'))
            expected = {
                "data": "custom parser 2",
            }
            self.assertEqual(data, expected)

########NEW FILE########
__FILENAME__ = test_renderers
# coding: utf8
from __future__ import unicode_literals
from flask_api import renderers, status, FlaskAPI
from flask_api.decorators import set_renderers
from flask_api.mediatypes import MediaType
import unittest


class RendererTests(unittest.TestCase):
    def test_render_json(self):
        renderer = renderers.JSONRenderer()
        content = renderer.render({'example': 'example'}, MediaType('application/json'))
        expected = '{"example": "example"}'
        self.assertEqual(content, expected)

    def test_render_json_with_indent(self):
        renderer = renderers.JSONRenderer()
        content = renderer.render({'example': 'example'}, MediaType('application/json; indent=4'))
        expected = '{\n    "example": "example"\n}'
        self.assertEqual(content, expected)

    def test_renderer_negotiation_not_implemented(self):
        renderer = renderers.BaseRenderer()
        with self.assertRaises(NotImplementedError) as context:
            renderer.render(None, None)
        msg = str(context.exception)
        expected = '`render()` method must be implemented for class "BaseRenderer"'
        self.assertEqual(msg, expected)


class OverrideParserSettings(unittest.TestCase):
    def setUp(self):
        class CustomRenderer1(renderers.BaseRenderer):
            media_type = 'application/example1'

            def render(self, data, media_type, **options):
                return 'custom renderer 1'

        class CustomRenderer2(renderers.BaseRenderer):
            media_type = 'application/example2'

            def render(self, data, media_type, **options):
                return 'custom renderer 2'

        app = FlaskAPI(__name__)
        app.config['DEFAULT_RENDERERS'] = [CustomRenderer1]
        app.config['PROPAGATE_EXCEPTIONS'] = True

        @app.route('/custom_renderer_1/', methods=['GET'])
        def custom_renderer_1():
            return {'data': 'example'}

        @app.route('/custom_renderer_2/', methods=['GET'])
        @set_renderers([CustomRenderer2])
        def custom_renderer_2():
            return {'data': 'example'}

        @app.route('/custom_renderer_2_as_args/', methods=['GET'])
        @set_renderers(CustomRenderer2)
        def custom_renderer_2_as_args():
            return {'data': 'example'}

        self.app = app

    def test_overridden_parsers_with_settings(self):
        with self.app.test_client() as client:
            response = client.get('/custom_renderer_1/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/example1')
            data = response.get_data().decode('utf8')
            self.assertEqual(data, "custom renderer 1")

    def test_overridden_parsers_with_decorator(self):
        with self.app.test_client() as client:
            data = {'example': 'example'}
            response = client.get('/custom_renderer_2/', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/example2')
            data = response.get_data().decode('utf8')
            self.assertEqual(data, "custom renderer 2")

    def test_overridden_parsers_with_decorator_as_args(self):
        with self.app.test_client() as client:
            data = {'example': 'example'}
            response = client.get('/custom_renderer_2_as_args/', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.headers['Content-Type'], 'application/example2')
            data = response.get_data().decode('utf8')
            self.assertEqual(data, "custom renderer 2")

########NEW FILE########
__FILENAME__ = test_request
# coding: utf8
from __future__ import unicode_literals
from flask import request
from flask_api import exceptions
import flask_api
import io
import unittest

app = flask_api.FlaskAPI(__name__)


class MediaTypeParsingTests(unittest.TestCase):
    def test_json_request(self):
        kwargs = {
            'method': 'PUT',
            'input_stream': io.BytesIO(b'{"key": 1, "other": "two"}'),
            'content_type': 'application/json'
        }
        with app.test_request_context(**kwargs):
            self.assertEqual(request.data, {"key": 1, "other": "two"})

    def test_invalid_content_type_request(self):
        kwargs = {
            'method': 'PUT',
            'input_stream': io.BytesIO(b'Cannot parse this content type.'),
            'content_type': 'text/plain'
        }
        with app.test_request_context(**kwargs):
            with self.assertRaises(exceptions.UnsupportedMediaType):
                request.data

    def test_no_content_request(self):
        """
        Ensure that requests with no data do not populate the
        `.data`, `.form` or `.files` attributes.
        """
        with app.test_request_context(method='PUT'):
            self.assertFalse(request.data)

        with app.test_request_context(method='PUT'):
            self.assertFalse(request.form)

        with app.test_request_context(method='PUT'):
            self.assertFalse(request.files)

    def test_encode_request(self):
        """
        Ensure that `.full_path` is correctly decoded in python 3
        """
        with app.test_request_context(method='GET', path='/?a=b'):
            self.assertEqual(request.full_path, '/?a=b')

########NEW FILE########
__FILENAME__ = test_settings
# coding: utf8
from __future__ import unicode_literals
from flask_api.settings import APISettings
import unittest


class SettingsTests(unittest.TestCase):
    def test_bad_import(self):
        settings = APISettings({'DEFAULT_PARSERS': 'foobarz.FailedImport'})
        with self.assertRaises(ImportError) as context:
            settings.DEFAULT_PARSERS
        msg = str(context.exception)
        excepted_py2 = (
            "Could not import 'foobarz.FailedImport' for API setting "
            "'DEFAULT_PARSERS'. No module named foobarz."
        )
        excepted_py3 = (
            "Could not import 'foobarz.FailedImport' for API setting "
            "'DEFAULT_PARSERS'. No module named 'foobarz'."
        )
        self.assertIn(msg, (excepted_py2, excepted_py3))

########NEW FILE########
__FILENAME__ = test_status
# coding: utf8
from __future__ import unicode_literals
from flask_api import status
import unittest


class TestStatus(unittest.TestCase):
    def test_status_categories(self):
        self.assertFalse(status.is_informational(99))
        self.assertTrue(status.is_informational(100))
        self.assertTrue(status.is_informational(199))
        self.assertFalse(status.is_informational(200))

        self.assertFalse(status.is_success(199))
        self.assertTrue(status.is_success(200))
        self.assertTrue(status.is_success(299))
        self.assertFalse(status.is_success(300))

        self.assertFalse(status.is_redirect(299))
        self.assertTrue(status.is_redirect(300))
        self.assertTrue(status.is_redirect(399))
        self.assertFalse(status.is_redirect(400))

        self.assertFalse(status.is_client_error(399))
        self.assertTrue(status.is_client_error(400))
        self.assertTrue(status.is_client_error(499))
        self.assertFalse(status.is_client_error(500))

        self.assertFalse(status.is_server_error(499))
        self.assertTrue(status.is_server_error(500))
        self.assertTrue(status.is_server_error(599))
        self.assertFalse(status.is_server_error(600))

########NEW FILE########
