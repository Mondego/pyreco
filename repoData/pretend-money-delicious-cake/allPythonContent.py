__FILENAME__ = admin
from django.conf import settings
from django.contrib import admin


if 'django.contrib.auth' in settings.INSTALLED_APPS:
    from delicious_cake.models import ApiKey

    class ApiKeyInline(admin.StackedInline):
        model = ApiKey
        extra = 0

    admin.site.register(ApiKey)

########NEW FILE########
__FILENAME__ = authentication
import hmac
import time
import uuid
import base64

from django.conf import settings
from django.utils.http import same_origin
from django.contrib.auth import authenticate
from django.utils.translation import ugettext as _
from django.core.exceptions import ImproperlyConfigured
from django.middleware.csrf import _sanitize_token, constant_time_compare

from delicious_cake.http import HttpUnauthorized

try:
    from hashlib import sha1
except ImportError:
    import sha
    sha1 = sha.sha

try:
    import python_digest
except ImportError:
    python_digest = None

try:
    import oauth2
except ImportError:
    oauth2 = None

try:
    import oauth_provider
except ImportError:
    oauth_provider = None


class Authentication(object):
    """
    A simple base class to establish the protocol for auth.

    By default, this indicates the user is always authenticated.
    """
    def __init__(self, require_active=True):
        self.require_active = require_active

    def is_authenticated(self, request, **kwargs):
        """
        Identifies if the user is authenticated to continue or not.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        return True

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns a combination of IP address and hostname.
        """
        return "%s_%s" % (
            request.META.get('REMOTE_ADDR', 'noaddr'),
            request.META.get('REMOTE_HOST', 'nohost'))

    def check_active(self, user):
        """
        Ensures the user has an active account.

        Optimized for the ``django.contrib.auth.models.User`` case.
        """
        if not self.require_active:
            # Ignore & move on.
            return True

        return user.is_active


class BasicAuthentication(Authentication):
    """
    Handles HTTP Basic auth against a specific auth backend if provided,
    or against all configured authentication backends using the
    ``authenticate`` method from ``django.contrib.auth``.

    Optional keyword arguments:

    ``backend``
        If specified, use a specific ``django.contrib.auth`` backend instead
        of checking all backends specified in the ``AUTHENTICATION_BACKENDS``
        setting.
    ``realm``
        The realm to use in the ``HttpUnauthorized`` response.  Default:
        ``delicious-cake``.
    """
    def __init__(self, backend=None, realm='delicious-cake', **kwargs):
        super(BasicAuthentication, self).__init__(**kwargs)
        self.backend = backend
        self.realm = realm

    def _unauthorized(self):
        response = HttpUnauthorized()
        # FIXME: Sanitize realm.
        response['WWW-Authenticate'] = 'Basic Realm="%s"' % self.realm
        return response

    def is_authenticated(self, request, **kwargs):
        """
        Checks a user's basic auth credentials against the current
        Django auth backend.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        if not request.META.get('HTTP_AUTHORIZATION'):
            return self._unauthorized()

        try:
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split()
            if auth_type.lower() != 'basic':
                return self._unauthorized()
            user_pass = base64.b64decode(data)
        except:
            return self._unauthorized()

        bits = user_pass.split(':', 1)

        if len(bits) != 2:
            return self._unauthorized()

        if self.backend:
            user = self.backend.authenticate(
                username=bits[0], password=bits[1])
        else:
            user = authenticate(username=bits[0], password=bits[1])

        if user is None:
            return self._unauthorized()

        if not self.check_active(user):
            return False

        request.user = user
        return True

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns the user's basic auth username.
        """
        return request.META.get('REMOTE_USER', 'nouser')


class ApiKeyAuthentication(Authentication):
    """
    Handles API key auth, in which a user provides a username & API key.

    Uses the ``ApiKey`` model that ships with delicious-cake. If you wish to use
    a different model, override the ``get_key`` method to perform the key check
    as suits your needs.
    """
    def _unauthorized(self):
        return HttpUnauthorized()

    def extract_credentials(self, request):
        if request.META.get('HTTP_AUTHORIZATION') and request.META['HTTP_AUTHORIZATION'].lower().startswith('apikey '):
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split()

            if auth_type.lower() != 'apikey':
                raise ValueError("Incorrect authorization header.")

            username, api_key = data.split(':', 1)
        else:
            username = request.GET.get('username') or request.POST.get('username')
            api_key = request.GET.get('api_key') or request.POST.get('api_key')

        return username, api_key

    def is_authenticated(self, request, **kwargs):
        """
        Finds the user and checks their API key.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            username, api_key = self.extract_credentials(request)
        except ValueError:
            return self._unauthorized()

        if not username or not api_key:
            return self._unauthorized()

        try:
            user = User.objects.get_by_natural_key(username)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return self._unauthorized()

        if not self.check_active(user):
            return False

        request.user = user
        return self.get_key(user, api_key)

    def get_key(self, user, api_key):
        """
        Attempts to find the API key for the user. Uses ``ApiKey`` by default
        but can be overridden.
        """
        from delicious_cake.models import ApiKey

        try:
            ApiKey.objects.get(user=user, key=api_key)
        except ApiKey.DoesNotExist:
            return self._unauthorized()

        return True

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns the user's username.
        """
        username, api_key = self.extract_credentials(request)
        return username or 'nouser'


class SessionAuthentication(Authentication):
    """
    An authentication mechanism that piggy-backs on Django sessions.

    This is useful when the API is talking to Javascript on the same site.
    Relies on the user being logged in through the standard Django login
    setup.

    Requires a valid CSRF token.
    """
    def is_authenticated(self, request, **kwargs):
        """
        Checks to make sure the user is logged in & has a Django session.
        """
        # Cargo-culted from Django 1.3/1.4's ``django/middleware/csrf.py``.
        # We can't just use what's there, since the return values will be
        # wrong.
        # We also can't risk accessing ``request.POST``, which will break with
        # the serialized bodies.
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return request.user.is_authenticated()

        if getattr(request, '_dont_enforce_csrf_checks', False):
            return request.user.is_authenticated()

        csrf_token = _sanitize_token(request.COOKIES.get(settings.CSRF_COOKIE_NAME, ''))

        if request.is_secure():
            referer = request.META.get('HTTP_REFERER')

            if referer is None:
                return False

            good_referer = 'https://%s/' % request.get_host()

            if not same_origin(referer, good_referer):
                return False

        request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

        if not constant_time_compare(request_csrf_token, csrf_token):
            return False

        return request.user.is_authenticated()

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns the user's username.
        """
        return request.user.username


class DigestAuthentication(Authentication):
    """
    Handles HTTP Digest auth against a specific auth backend if provided,
    or against all configured authentication backends using the
    ``authenticate`` method from ``django.contrib.auth``. However, instead of
    the user's password, their API key should be used.

    Optional keyword arguments:

    ``backend``
        If specified, use a specific ``django.contrib.auth`` backend instead
        of checking all backends specified in the ``AUTHENTICATION_BACKENDS``
        setting.
    ``realm``
        The realm to use in the ``HttpUnauthorized`` response.  Default:
        ``delicious-cake``.
    """
    def __init__(self, backend=None, realm='delicious-cake', **kwargs):
        super(DigestAuthentication, self).__init__(**kwargs)
        self.backend = backend
        self.realm = realm

        if python_digest is None:
            raise ImproperlyConfigured("The 'python_digest' package could not be imported. It is required for use with the 'DigestAuthentication' class.")

    def _unauthorized(self):
        response = HttpUnauthorized()
        new_uuid = uuid.uuid4()
        opaque = hmac.new(str(new_uuid), digestmod=sha1).hexdigest()
        response['WWW-Authenticate'] = python_digest.build_digest_challenge(time.time(), getattr(settings, 'SECRET_KEY', ''), self.realm, opaque, False)
        return response

    def is_authenticated(self, request, **kwargs):
        """
        Finds the user and checks their API key.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        if not request.META.get('HTTP_AUTHORIZATION'):
            return self._unauthorized()

        try:
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split(' ', 1)

            if auth_type.lower() != 'digest':
                return self._unauthorized()
        except:
            return self._unauthorized()

        digest_response = python_digest.parse_digest_credentials(request.META['HTTP_AUTHORIZATION'])

        # FIXME: Should the nonce be per-user?
        if not python_digest.validate_nonce(digest_response.nonce, getattr(settings, 'SECRET_KEY', '')):
            return self._unauthorized()

        user = self.get_user(digest_response.username)
        api_key = self.get_key(user)

        if user is False or api_key is False:
            return self._unauthorized()

        expected = python_digest.calculate_request_digest(
            request.method,
            python_digest.calculate_partial_digest(digest_response.username, self.realm, api_key),
            digest_response)

        if not digest_response.response == expected:
            return self._unauthorized()

        if not self.check_active(user):
            return False

        request.user = user
        return True

    def get_user(self, username):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get_by_natural_key(username)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return False

        return user

    def get_key(self, user):
        """
        Attempts to find the API key for the user. Uses ``ApiKey`` by default
        but can be overridden.

        Note that this behaves differently than the ``ApiKeyAuthentication``
        method of the same name.
        """
        from delicious_cake.models import ApiKey

        try:
            key = ApiKey.objects.get(user=user)
        except ApiKey.DoesNotExist:
            return False

        return key.key

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns the user's username.
        """
        if hasattr(request, 'user'):
            try:
                return request.user.get_username()
            except AttributeError:
                pass
        return 'nouser'


class OAuthAuthentication(Authentication):
    """
    Handles OAuth, which checks a user's credentials against a separate service.
    Currently verifies against OAuth 1.0a services.

    This does *NOT* provide OAuth authentication in your API, strictly
    consumption.
    """
    def __init__(self, **kwargs):
        super(OAuthAuthentication, self).__init__(**kwargs)

        if oauth2 is None:
            raise ImproperlyConfigured("The 'python-oauth2' package could not be imported. It is required for use with the 'OAuthAuthentication' class.")

        if oauth_provider is None:
            raise ImproperlyConfigured("The 'django-oauth-plus' package could not be imported. It is required for use with the 'OAuthAuthentication' class.")

    def is_authenticated(self, request, **kwargs):
        from oauth_provider.store import store, InvalidTokenError

        if self.is_valid_request(request):
            oauth_request = oauth_provider.utils.get_oauth_request(request)
            consumer = store.get_consumer(request, oauth_request, oauth_request.get_parameter('oauth_consumer_key'))

            try:
                token = store.get_access_token(request, oauth_request, consumer, oauth_request.get_parameter('oauth_token'))
            except oauth_provider.store.InvalidTokenError:
                return oauth_provider.utils.send_oauth_error(oauth2.Error(_('Invalid access token: %s') % oauth_request.get_parameter('oauth_token')))

            try:
                self.validate_token(request, consumer, token)
            except oauth2.Error, e:
                return oauth_provider.utils.send_oauth_error(e)

            if consumer and token:
                if not self.check_active(token.user):
                    return False

                request.user = token.user
                return True

            return oauth_provider.utils.send_oauth_error(oauth2.Error(_('You are not allowed to access this resource.')))

        return oauth_provider.utils.send_oauth_error(oauth2.Error(_('Invalid request parameters.')))

    def is_in(self, params):
        """
        Checks to ensure that all the OAuth parameter names are in the
        provided ``params``.
        """
        from oauth_provider.consts import OAUTH_PARAMETERS_NAMES

        for param_name in OAUTH_PARAMETERS_NAMES:
            if param_name not in params:
                return False

        return True

    def is_valid_request(self, request):
        """
        Checks whether the required parameters are either in the HTTP
        ``Authorization`` header sent by some clients (the preferred method
        according to OAuth spec) or fall back to ``GET/POST``.
        """
        auth_params = request.META.get("HTTP_AUTHORIZATION", [])
        return self.is_in(auth_params) or self.is_in(request.REQUEST)

    def validate_token(self, request, consumer, token):
        oauth_server, oauth_request = oauth_provider.utils.initialize_server_request(request)
        return oauth_server.verify_request(oauth_request, consumer, token)


class MultiAuthentication(object):
    """
    An authentication backend that tries a number of backends in order.
    """
    def __init__(self, *backends, **kwargs):
        super(MultiAuthentication, self).__init__(**kwargs)
        self.backends = backends

    def is_authenticated(self, request, **kwargs):
        """
        Identifies if the user is authenticated to continue or not.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        unauthorized = False

        for backend in self.backends:
            check = backend.is_authenticated(request, **kwargs)

            if check:
                if isinstance(check, HttpUnauthorized):
                    unauthorized = unauthorized or check
                else:
                    request._authentication_backend = backend
                    return check

        return unauthorized

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns a combination of IP address and hostname.
        """
        try:
            return request._authentication_backend.get_identifier(request)
        except AttributeError:
            return 'nouser'

########NEW FILE########
__FILENAME__ = authorization
import operator

__all__ = ('Authorization', 'ReadOnlyAuthorization',)


class Authorization(object):
    """
    A base class that provides no permissions checking.
    """
    def __get__(self, instance, owner):
        """
        Makes ``Authorization`` a descriptor of ``ResourceOptions`` and creates
        a reference to the ``ResourceOptions`` object that may be used by
        methods of ``Authorization``.
        """
        self.resource_meta = instance
        return self

    def is_authorized(self, request, obj=None):
        """
        Checks if the user is authorized to perform the request. If ``object``
        is provided, it can do additional row-level checks.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        return True


class ReadOnlyAuthorization(Authorization):
    """
    Default Authentication class for ``Resource`` objects.

    Only allows GET requests.
    """

    def is_authorized(self, request, obj=None):
        """
        Allow any ``GET`` request.
        """
        if request.method == 'GET':
            return True
        else:
            return False


########NEW FILE########
__FILENAME__ = entities
try:
    from django.utils.copycompat import deepcopy
except ImportError:
    from copy import deepcopy

from delicious_cake import fields

__all__ = ('EntityMetaclass', 'Entity',)


class EntityMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['base_fields'] = {}
        declared_fields = {}

        try:
            parents = [b for b in bases if issubclass(b, Entity)]
            parents.reverse()

            for p in parents:
                parent_fields = getattr(p, 'base_fields', {})

                for field_name, field_object in parent_fields.items():
                    attrs['base_fields'][field_name] = deepcopy(field_object)
        except NameError:
            pass

        for field_name, obj in attrs.items():
            if isinstance(obj, fields.ApiField) and \
                    not field_name.startswith('_'):
                field = attrs.pop(field_name)
                field.field_name = field_name
                declared_fields[field_name] = field

        attrs['base_fields'].update(declared_fields)
        attrs['declared_fields'] = declared_fields

        new_class = super(
            EntityMetaclass, cls).__new__(cls, name, bases, attrs)

        for field_name, field_object in new_class.base_fields.items():
            if hasattr(field_object, 'contribute_to_class'):
                field_object.contribute_to_class(new_class, field_name)

        return new_class


class Entity(object):
    __metaclass__ = EntityMetaclass

    def __init__(self, obj):
        self.obj = obj
        self.fields = deepcopy(self.base_fields)

    def process(self, data):
        return data

    def full_process(self):
        processed_data = {}

        for field_name, field_object in self.fields.items():
            processed_field_data = field_object.process(self.obj)

            method = getattr(self, 'process_%s' % field_name, None)

            if method:
                if field_object.attribute is None:
                    processed_field_data = method(self.obj)
                else:
                    processed_field_data = method(processed_field_data)

            if processed_field_data is None and field_object.has_default:
                processed_field_data = field_object.default

            if processed_field_data is not None:
                processed_field_data = \
                    field_object.convert(processed_field_data)

            processed_data[field_name] = processed_field_data

        try:
            if 'resource_uri' not in processed_data:
                processed_data['resource_uri'] = self.get_resource_uri()
        except NotImplementedError:
            pass

        return self.process(processed_data)

    def get_resource_uri(self):
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = exceptions
from django.http import HttpResponse


class DeliciousCakeError(Exception):
    """A base exception for all delicious-cake related errors."""
    pass


class UnsupportedFormat(DeliciousCakeError):
    """
    Raised when an unsupported serialization format is requested.
    """
    pass


class UnsupportedSerializationFormat(UnsupportedFormat):
    pass


class UnsupportedDeserializationFormat(UnsupportedFormat):
    pass


class ImmediateHttpResponse(DeliciousCakeError):
    """
    This exception is used to interrupt the flow of processing to immediately
    return a custom HttpResponse.

    Common uses include::

        * for authentication (like digest/OAuth)
        * for throttling

    """
    def __init__(self, response=None, response_cls=None, **response_kwargs):
        super(ImmediateHttpResponse, self).__init__(
            'ImmediateHttpResponse error')

        if response is None and response_cls is None:
            raise ValueError(
                "Must specify either 'response' or 'response_cls'")

        self.response = response
        self.response_cls = response_cls
        self.response_kwargs = response_kwargs


class BadRequest(DeliciousCakeError):
    """
    A generalized exception for indicating incorrect request parameters.

    Handled specially in that the message tossed by this exception will be
    presented to the end user.
    """
    pass


class ResourceEntityError(DeliciousCakeError):
    pass


class WrongNumberOfValues(DeliciousCakeError):
    pass


class ApiFieldError(DeliciousCakeError):
    """
    Raised when there is a configuration error with a ``ApiField``.
    """
    pass


class ValidationError(DeliciousCakeError):
    def __init__(self, form_errors):
        self.form_errors = form_errors

########NEW FILE########
__FILENAME__ = fields
import re
import datetime
from decimal import Decimal
from dateutil.parser import parse

from django.utils import datetime_safe
from django.utils.timezone import make_aware

from delicious_cake.utils import make_aware
from delicious_cake.exceptions import ApiFieldError


DATE_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}).*?$')
DATETIME_REGEX = re.compile(
    '^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(T|\s+)(?P<hour>\d{2})' \
        ':(?P<minute>\d{2}):(?P<second>\d{2}).*?$')


class ApiField(object):
    """The base implementation of an entity field."""
    processed_type = 'string'
    help_text = ''

    def __init__(self, attr=None, default=None, help_text=None):
        """
        Optionally accepts an ``attr``, which should be a string of
        either an instance attribute or callable off the object during
        ``process``. Defaults to ``None``, meaning data will be manually
        accessed.

        Optionally accepts a ``default``, which provides default data when the
        object being ``processed`` has no data on the field.
        Defaults to ``None``.

        Optionally accepts ``help_text``, which lets you provide a
        human-readable description of the field exposed at the schema level.
        Defaults to the per-Field definition.
        """

        self._attribute = attr
        self._field_name = None
        self._default = default

        if help_text:
            self.help_text = help_text

    def contribute_to_class(self, cls, name):
        pass

    def has_default(self):
        """Returns a boolean of whether this field has a default value."""
        return self._default is not None

    @property
    def default(self):
        """Returns the default value for the field."""
        if callable(self._default):
            return self._default()

        return self._default

    @property
    def attribute(self):
        return self._attribute

    @property
    def field_name(self):
        return self._field_name

    @field_name.setter
    def field_name(self, value):
        self._field_name = value

    def convert(self, value):
        """
        Handles conversion between the data found and the type of the field.

        Extending classes should override this method and provide correct
        data coercion.
        """
        return value

    def process(self, obj):
        """
        Takes data from the provided object and prepares it for the
        resource.
        """
        attrs = None

        if self._attribute is not None:
            attrs = self._attribute
        elif self._field_name is not None:
            attrs = self._field_name

        if attrs is not None:
            current_object = obj

            # Check for `__` in the field for looking through the relation.
            attrs = attrs.split('__')

            if isinstance(obj, dict):
                for attr in attrs:
                    current_object = current_object.get(attr, None)

                    if callable(current_object):
                        current_object = current_object()
            else:
                for attr in attrs:
                    current_object = getattr(current_object, attr, None)

                    if callable(current_object):
                        current_object = current_object()

            return current_object


class CharField(ApiField):
    """
    A text field of arbitrary length.
    """
    processed_type = 'string'
    help_text = 'Unicode string data. Ex: "Hello World"'

    def convert(self, value):
        if value is None:
            return None

        return unicode(value)


class FileField(ApiField):
    """
    A file-related field.
    """
    processed_type = 'string'
    help_text = 'A file URL as a string. Ex: ' \
        '"http://media.example.com/media/photos/my_photo.jpg"'

    def convert(self, value):
        if value is None:
            return None

        try:
            # Try to return the URL if it's a ``File``, falling back to the
            # string itself if it's been overridden or is a default.
            return getattr(value, 'url', value)
        except ValueError:
            return None


class IntegerField(ApiField):
    """
    An integer field.
    """
    processed_type = 'integer'
    help_text = 'Integer data. Ex: 2673'

    def convert(self, value):
        if value is None:
            return None

        return int(value)


class FloatField(ApiField):
    """
    A floating point field.
    """
    processed_type = 'float'
    help_text = 'Floating point numeric data. Ex: 26.73'

    def convert(self, value):
        if value is None:
            return None

        return float(value)


class DecimalField(ApiField):
    """
    A decimal field.
    """
    processed_type = 'decimal'
    help_text = 'Fixed precision numeric data. Ex: 26.73'

    def convert(self, value):
        if value is None:
            return None

        return Decimal(value)


class BooleanField(ApiField):
    """
    A boolean field.
    """
    processed_type = 'boolean'
    help_text = 'Boolean data. Ex: True'

    def convert(self, value):
        if value is None:
            return None

        return bool(value)


class ListField(ApiField):
    """
    A list field.
    """
    processed_type = 'list'
    help_text = "A list of data. Ex: ['abc', 26.73, 8]"

    def convert(self, value):
        if value is None:
            return None

        return list(value)


class DictField(ApiField):
    """
    A dictionary field.
    """
    processed_type = 'dict'
    help_text = "A dictionary of data. Ex: {'price': 26.73, 'name': 'Daniel'}"

    def convert(self, value):
        if value is None:
            return None

        return dict(value)


class DateField(ApiField):
    """
    A date field.
    """
    processed_type = 'date'
    help_text = 'A date as a string. Ex: "2010-11-10"'

    def convert(self, value):
        if isinstance(value, basestring):
            match = DATE_REGEX.search(value)

            if match:
                data = match.groupdict()
                return datetime_safe.date(
                    int(data['year']), int(data['month']), int(data['day']))
            else:
                raise ApiFieldError(
                    "Date provided to '%s' field doesn't appear to be a " \
                    "valid date string: '%s'" % (self._field_name, value))

        return datetime_safe.date(value.year, value.month, value.day)


class TimeField(ApiField):
    processed_type = 'time'
    help_text = 'A time as string. Ex: "20:05:23"'

    def convert(self, dt):
        try:
            if isinstance(dt, basestring):
                dt = parse(dt)
        except ValueError:
            raise ApiFieldError(
                    "Time provided to '%s' field doesn't appear to be a " \
                    "valid time string: '%s'" % (self._field_name, dt))
        else:
            return datetime.time(dt.hour, dt.minute, dt.second)


class DateTimeField(ApiField):
    processed_type = 'datetime'
    help_text = 'A date & time as a string. Ex: "2010-11-10T03:07:43"'

    def convert(self, value):
        if isinstance(value, basestring):
            match = DATETIME_REGEX.search(value)

            if match:
                data = match.groupdict()
                return make_aware(datetime_safe.datetime(
                    int(data['year']), int(data['month']),
                    int(data['day']), int(data['hour']),
                    int(data['minute']), int(data['second'])))
            else:
                raise ApiFieldError(
                    "Datetime provided to '%s' field doesn't appear to be a " \
                    "valid datetime string: '%s'" % (
                        self._field_name, value))

        return make_aware(datetime_safe.datetime(
            value.year, value.month, value.day,
            value.hour, value.minute, value.second))


class EntityField(ApiField):
    processed_type = 'dict'

    def __init__(self, entity_cls, *args, **kwargs):
        self.entity_cls = entity_cls
        super(EntityField, self).__init__(*args, **kwargs)

    def convert(self, value):
        if value is not None:
            return self.entity_cls(value).full_process()


class EntityListField(EntityField):
    processed_type = 'list'

    def convert(self, value):
        if value is not None:
            return [self.entity_cls(obj).full_process() for obj in value]

########NEW FILE########
__FILENAME__ = http
"""
The various HTTP responses for use in returning proper HTTP codes.
"""
from django.http import HttpResponse


class HttpCreated(HttpResponse):
    status_code = 201

    def __init__(self, *args, **kwargs):
        location = kwargs.pop('location', '')

        super(HttpCreated, self).__init__(*args, **kwargs)
        self['Location'] = location


class HttpAccepted(HttpResponse):
    status_code = 202


class HttpNoContent(HttpResponse):
    status_code = 204

    def __init__(self, *args, **kwargs):
        super(HttpNoContent, self).__init__(*args, **kwargs)
        del self['Content-Type']


class HttpMultipleChoices(HttpResponse):
    status_code = 300


class HttpSeeOther(HttpResponse):
    status_code = 303


class HttpNotModified(HttpResponse):
    status_code = 304


class HttpBadRequest(HttpResponse):
    status_code = 400


class HttpUnauthorized(HttpResponse):
    status_code = 401


class HttpForbidden(HttpResponse):
    status_code = 403


class HttpNotFound(HttpResponse):
    status_code = 404


class HttpMethodNotAllowed(HttpResponse):
    status_code = 405


class HttpNotAcceptable(HttpResponse):
    status_code = 406


class HttpConflict(HttpResponse):
    status_code = 409


class HttpGone(HttpResponse):
    status_code = 410


class HttpUnsupportedMediaType(HttpResponse):
    status_code = 415


class HttpTooManyRequests(HttpResponse):
    status_code = 429


class HttpApplicationError(HttpResponse):
    status_code = 500


class HttpNotImplemented(HttpResponse):
    status_code = 501

########NEW FILE########
__FILENAME__ = backfill_api_keys
from django.contrib.auth import get_user_model
from django.core.management.base import NoArgsCommand

from delicious_cake.models import ApiKey


class Command(NoArgsCommand):
    help = "Goes through all users and adds API keys for any that don't have one."

    def handle_noargs(self, **options):
        """Goes through all users and adds API keys for any that don't have one."""
        self.verbosity = int(options.get('verbosity', 1))

        for user in get_user_model().objects.all().iterator():
            try:
                api_key = ApiKey.objects.get(user=user)

                if not api_key.key:
                    # Autogenerate the key.
                    api_key.save()

                    if self.verbosity >= 1:
                        print u"Generated a new key for '%s'" % user.username
            except ApiKey.DoesNotExist:
                api_key = ApiKey.objects.create(user=user)

                if self.verbosity >= 1:
                    print u"Created a new key for '%s'" % user.username

########NEW FILE########
__FILENAME__ = models
import hmac
import time
import datetime

from django.db import models
from django.conf import settings

from delicious_cake.utils import now

try:
    from hashlib import sha1
except ImportError:
    import sha
    sha1 = sha.sha


class ApiAccess(models.Model):
    """A simple model for use with the ``CacheDBThrottle`` behaviors."""
    identifier = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True, default='')
    request_method = models.CharField(max_length=10, blank=True, default='')
    accessed = models.PositiveIntegerField()

    def __unicode__(self):
        return u"%s @ %s" % (self.identifier, self.accessed)

    def save(self, *args, **kwargs):
        self.accessed = int(time.time())
        return super(ApiAccess, self).save(*args, **kwargs)


if 'django.contrib.auth' in settings.INSTALLED_APPS:
    import uuid
    from django.conf import settings

    class ApiKey(models.Model):
        user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='api_key')
        key = models.CharField(
            max_length=255, blank=True, default='', db_index=True)
        created = models.DateTimeField(default=now)

        def __unicode__(self):
            return u"%s for %s" % (self.key, self.user)

        def save(self, *args, **kwargs):
            if not self.key:
                self.key = self.generate_key()

            return super(ApiKey, self).save(*args, **kwargs)

        def generate_key(self):
            # Get a random UUID.
            new_uuid = uuid.uuid4()
            # Hmac that beast.
            return hmac.new(str(new_uuid), digestmod=sha1).hexdigest()


    def create_api_key(sender, **kwargs):
        """
        A signal for hooking up automatic ``ApiKey`` creation.
        """
        if kwargs.get('created') is True:
            ApiKey.objects.create(user=kwargs.get('instance'))

########NEW FILE########
__FILENAME__ = options
from django.conf import settings

from delicious_cake.paginators import Paginator
from delicious_cake.throttle import BaseThrottle
from delicious_cake.serializers import Serializer
from delicious_cake.authorization import Authorization
from delicious_cake.authentication import Authentication

__all__ = ('DetailResourceOptions', 'ListResourceOptions',)


class DetailResourceOptions(object):
    include_entity = True

    entity_cls = None
    detail_entity_cls = None

    serializer = Serializer()
    default_format = 'application/json'

    authorization = Authorization()
    authentication = Authentication()

    throttle = BaseThrottle()

    def __new__(cls, name, meta=None):
        overrides = {}

        if meta is not None:
            for override_name in dir(meta):
                if not override_name.startswith('_'):
                    overrides[override_name] = getattr(meta, override_name)

        return object.__new__(type(name, (cls,), overrides))

    def _get_entity_cls(self, *entity_classes):
        entity_cls = None

        for entity_cls in entity_classes:
            if entity_cls is not None:
                break

        return entity_cls

    def get_detail_entity_cls(self):
        return self._get_entity_cls(self.entity_cls, self.detail_entity_cls)


class ListResourceOptions(DetailResourceOptions):
    collection_name = 'objects'

    list_entity_cls = None
    paginator_cls = Paginator

    max_limit = 100
    limit = getattr(settings, 'API_LIMIT_PER_PAGE', 20)

    def get_list_entity_cls(self):
        return self._get_entity_cls(
            self.entity_cls, self.list_entity_cls, self.detail_entity_cls)

########NEW FILE########
__FILENAME__ = paginators
from urllib import urlencode

from django.conf import settings

from delicious_cake.exceptions import BadRequest

__all__ = ('Paginator',)


class Paginator(object):
    """
    Limits result sets down to sane amounts for passing to the client.

    This is used in place of Django's ``Paginator`` due to the way pagination
    works. ``limit`` & ``offset`` (delicious-cake) are used in place of
    ``page`` (Django) so none of the page-related calculations are necessary.

    This implementation also provides additional details like the
    ``total_count`` of resources seen and convenience links to the
    ``previous``/``next`` pages of data as available.
    """
    def __init__(self, request_data, objects, resource_uri=None, limit=None,
                 offset=0, max_limit=100, collection_name='objects'):
        """
        Instantiates the ``Paginator`` and allows for some configuration.

        The ``request_data`` argument ought to be a dictionary-like object.
        May provide ``limit`` and/or ``offset`` to override the defaults.
        Commonly provided ``request.GET``. Required.

        The ``objects`` should be a list-like object of ``Resources``.
        This is typically a ``QuerySet`` but can be anything that
        implements slicing. Required.

        Optionally accepts a ``limit`` argument, which specifies how many
        items to show at a time. Defaults to ``None``, which is no limit.

        Optionally accepts an ``offset`` argument, which specifies where in
        the ``objects`` to start displaying results from. Defaults to 0.

        Optionally accepts a ``max_limit`` argument, which the upper bound
        limit. Defaults to ``1000``. If you set it to 0 or ``None``, no upper
        bound will be enforced.
        """
        self.request_data = request_data
        self.objects = objects
        self.limit = limit
        self.max_limit = max_limit
        self.offset = offset
        self.resource_uri = resource_uri
        self.collection_name = collection_name

    def get_limit(self):
        """
        Determines the proper maximum number of results to return.

        In order of importance, it will use:

            * The user-requested ``limit`` from the GET parameters, if specified.
            * The object-level ``limit`` if specified.
            * ``settings.API_LIMIT_PER_PAGE`` if specified.

        Default is 20 per page.
        """

        limit = self.request_data.get('limit', self.limit)
        if limit is None:
            limit = getattr(settings, 'API_LIMIT_PER_PAGE', 20)

        try:
            limit = int(limit)
        except ValueError:
            raise BadRequest(
                "Invalid limit '%s' provided. Please provide a positive integer." % limit)

        if limit < 0:
            raise BadRequest("Invalid limit '%s' provided. Please provide a positive integer >= 0." % limit)

        if self.max_limit and (not limit or limit > self.max_limit):
            # If it's more than the max, we're only going to return the max.
            # This is to prevent excessive DB (or other) load.
            return self.max_limit

        return limit

    def get_offset(self):
        """
        Determines the proper starting offset of results to return.

        It attempst to use the user-provided ``offset`` from the GET parameters,
        if specified. Otherwise, it falls back to the object-level ``offset``.

        Default is 0.
        """
        offset = self.offset

        if 'offset' in self.request_data:
            offset = self.request_data['offset']

        try:
            offset = int(offset)
        except ValueError:
            raise BadRequest("Invalid offset '%s' provided. Please provide an integer." % offset)

        if offset < 0:
            raise BadRequest("Invalid offset '%s' provided. Please provide a positive integer >= 0." % offset)

        return offset

    def get_slice(self, limit, offset):
        """
        Slices the result set to the specified ``limit`` & ``offset``.
        """
        if limit == 0:
            return self.objects[offset:]

        return self.objects[offset:offset + limit]

    def get_count(self):
        """
        Returns a count of the total number of objects seen.
        """
        try:
            return self.objects.count()
        except (AttributeError, TypeError):
            # If it's not a QuerySet (or it's ilk), fallback to ``len``.
            return len(self.objects)

    def get_previous(self, limit, offset):
        """
        If a previous page is available, will generate a URL to request that
        page. If not available, this returns ``None``.
        """
        if offset - limit < 0:
            return None

        return self._generate_uri(limit, offset - limit)

    def get_next(self, limit, offset, count):
        """
        If a next page is available, will generate a URL to request that
        page. If not available, this returns ``None``.
        """
        if offset + limit >= count:
            return None

        return self._generate_uri(limit, offset + limit)

    def _generate_uri(self, limit, offset):
        if self.resource_uri is None:
            return None

        try:
            # QueryDict has a urlencode method that can handle multiple values for the same key
            request_params = self.request_data.copy()
            if 'limit' in request_params:
                del request_params['limit']
            if 'offset' in request_params:
                del request_params['offset']
            request_params.update({'limit': limit, 'offset': offset})
            encoded_params = request_params.urlencode()
        except AttributeError:
            request_params = {}

            for k, v in self.request_data.items():
                if isinstance(v, unicode):
                    request_params[k] = v.encode('utf-8')
                else:
                    request_params[k] = v

            if 'limit' in request_params:
                del request_params['limit']
            if 'offset' in request_params:
                del request_params['offset']

            request_params.update({'limit': limit, 'offset': offset})
            encoded_params = urlencode(request_params)

        return '%s?%s' % (self.resource_uri, encoded_params,)

    def page(self):
        """
        Generates all pertinent data about the requested page.

        Handles getting the correct ``limit`` & ``offset``, then slices off
        the correct set of results and returns all pertinent metadata.
        """
        limit = self.get_limit()
        offset = self.get_offset()
        count = self.get_count()
        objects = self.get_slice(limit, offset)
        meta = {
            'offset': offset,
            'limit': limit,
            'total_count': count}

        if limit:
            meta['previous'] = self.get_previous(limit, offset)
            meta['next'] = self.get_next(limit, offset, count)

        return {
            self.collection_name: objects, 'meta': meta}

########NEW FILE########
__FILENAME__ = resources
import sys
import logging
import traceback
import collections

import django
from django.conf import settings

from django.db import models
from django.views.generic import View
from django import http as django_http
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from delicious_cake import http as cake_http
from delicious_cake.response import ResourceResponse
from delicious_cake.utils import (
    determine_format, build_content_type, is_valid_jsonp_callback_value,)
from delicious_cake.options import DetailResourceOptions, ListResourceOptions

from delicious_cake.exceptions import (
    ImmediateHttpResponse, BadRequest,
    UnsupportedSerializationFormat, UnsupportedDeserializationFormat,
    WrongNumberOfValues, ResourceEntityError, ValidationError,)

__all__ = ('Resource', 'DetailResource', 'ListResource', 'MultipartResource',)


log = logging.getLogger('django.request.delicious_cake')

NOT_FOUND_EXCEPTIONS = (ObjectDoesNotExist, django_http.Http404,)


class BaseResourceMetaClass(type):
    def __new__(cls, name, bases, attrs):
        new_class = super(BaseResourceMetaClass, cls).__new__(
            cls, name, bases, attrs)

        opts = getattr(new_class, 'Meta', None)
        new_class._meta = cls.options_cls(name, opts)

        return new_class


class DetailResourceMetaClass(BaseResourceMetaClass):
    options_cls = DetailResourceOptions


class ListResourceMetaClass(BaseResourceMetaClass):
    options_cls = ListResourceOptions


class Resource(View):
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        try:
            method = request.method.lower()

            if method in self.http_method_names and hasattr(self, method):
                handler = getattr(
                    self, 'dispatch_%s' % method, self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            self.is_authenticated(request)
            self.is_authorized(request)
            self.throttle_check(request)

            self.request = request
            self.args = args
            self.kwargs = kwargs

            try:
                response = self.dispatch_any(request, handler, *args, **kwargs)
            except ValidationError, e:
                # Catch ValidationError here for non-resources can throw them.
                self.raise_validation_error(request, e.form_errors)

        except ImmediateHttpResponse, e:
            if e.response is not None:
                response = e.response
            else:
                desired_format = self.determine_format(request)

                response_kwargs = e.response_kwargs
                response_kwargs['content_type'] = response_kwargs.get(
                    'content_type', build_content_type(desired_format))

                response = e.response_cls(**response_kwargs)
        except Exception, e:
            response = self.handle_exception(request, e)

        self.log_throttled_access(request)

        if not isinstance(response, cake_http.HttpResponse):
            return cake_http.HttpNoContent()

        return response

    def is_authenticated(self, request):
        auth_result = self._meta.authentication.is_authenticated(request)

        if isinstance(auth_result, cake_http.HttpResponse):
            raise ImmediateHttpResponse(response=auth_result)

        if auth_result is False:
            self.raise_authorization_error()

    def is_authorized(self, request, obj=None):
        auth_result = self._meta.authorization.is_authorized(request, obj)

        if isinstance(auth_result, cake_http.HttpResponse):
            raise ImmediateHttpResponse(response=auth_result)

        if auth_result is False:
            self.raise_authorization_error()

    def throttle_check(self, request):
        identifier = self._meta.authentication.get_identifier(request)

        if self._meta.throttle.should_be_throttled(identifier):
            raise ImmediateHttpResponse(
                response_cls=cake_http.HttpTooManyRequests)

    def log_throttled_access(self, request):
        request_method = request.method.lower()
        self._meta.throttle.accessed(
            self._meta.authentication.get_identifier(request),
            url=request.get_full_path(), request_method=request_method)
            
    def dispatch_any(self, request, handler, *args, **kwargs):
        """
        Hook for custom exception handling
        """
        return handler(request, *args, **kwargs)

    def dispatch_get(self, request, *args, **kwargs):
        raise NotImplementedError

    def dispatch_head(self, request, *args, **kwargs):
        raise NotImplementedError

    def dispatch_post(self, request, *args, **kwargs):
        return self.dispatch_creation(self.post, request, *args, **kwargs)

    def dispatch_put(self, request, *args, **kwargs):
        raise NotImplementedError

    def dispatch_delete(self, request, *args, **kwargs):
        raise NotImplementedError

    def dispatch_options(self, request, *args, **kwargs):
        return self.options(request, *args, **kwargs)

    def dispatch_method(self, method, request,
                        wrap_response=True, *args, **kwargs):
        self.process_body(request)
        resource_resp = method(request, *args, **kwargs)

        self.raise_if_http_response(resource_resp)

        if wrap_response and resource_resp is not None and \
                not isinstance(resource_resp, ResourceResponse):
            resource_resp = ResourceResponse(resource_resp)

        return resource_resp

    def dispatch_creation(self, method, request, *args, **kwargs):
        # Expected to be in the form of one of the following:
        # 0.  None
        # 1.  ResourceResponse
        # 2.  ResourceResponse, created (bool)
        # 3.  Object
        # 4.  Object, created (bool)
        ret = self.dispatch_method(
            method, request, wrap_response=False, *args, **kwargs)
        created = False

        if isinstance(ret, ResourceResponse):
            resp = ret
        elif isinstance(ret, collections.Iterable):
            if len(ret) == 2:
                resp = ret[0]

                if resp is not None:
                    created = ret[1]
                    if not isinstance(resp, ResourceResponse):
                        resp = ResourceResponse(resp)
            else:
                raise WrongNumberOfValues('Must return 1 or 2 values')
        elif ret is not None:
            resp = ResourceResponse(ret)
        else:
            resp = None

        if resp is not None:
            return self.create_http_response(request, resp, created=created)

    def options(self, request, *args, **kwargs):
        """
        Handles responding to requests for the OPTIONS HTTP verb.
        """
        response = cake_http.HttpResponse()
        response['Allow'] = ', '.join(self.allowed_methods)
        response['Content-Length'] = '0'
        return response

    @property
    def allowed_methods(self):
        return [m for m in self.http_method_names if hasattr(self, m)]

    def raise_if_http_response(self, potential_response):
        if isinstance(potential_response, cake_http.HttpResponse):
            raise ImmediateHttpResponse(response=potential_response)

    def handle_exception(self, request, exception):
        desired_format = self.determine_format(request)
        content_type = build_content_type(desired_format)

        if isinstance(exception, NOT_FOUND_EXCEPTIONS):
            response = cake_http.HttpNotFound(content_type=content_type)
        elif isinstance(exception, UnsupportedSerializationFormat):
            response = cake_http.HttpNotAcceptable(content_type=content_type)
        elif isinstance(exception, UnsupportedDeserializationFormat):
            response = cake_http.HttpUnsupportedMediaType(
                content_type=content_type)
        elif isinstance(exception, MultipleObjectsReturned):
            response = cake_http.HttpMultipleChoices(content_type=content_type)
        elif isinstance(exception, BadRequest):
            response = cake_http.HttpBadRequest(exception.message)
        else:
            if settings.DEBUG:
                data = {
                    'error_message': unicode(exception),
                    'traceback': '\n'.join(
                        traceback.format_exception(*(sys.exc_info())))}
            else:
                data = {
                    'error_message': getattr(
                        settings, 'DELICIOUS_CAKE_CANNED_ERROR',
                        'Sorry, this request could not be processed.  ' \
                        'Please try again later.')}

            response = cake_http.HttpApplicationError(
                content=self.serialize(request, data, desired_format),
                content_type=content_type, status=500)

        if settings.DEBUG or response.status_code == 500:
            log.error('Server Error: %s' % request.path,
                exc_info=sys.exc_info(), extra={'request': request})

            # SEND ERROR NOTIFICATIONS HERE!

        return response

    def process_body(self, request):
        # Deprecated, use request.body going forward
        if request.raw_post_data:
            request.DATA = self.deserialize(
                request, request.raw_post_data,
                format=request.META.get('CONTENT_TYPE', 'application/json'))
        else:
            request.DATA = {}

    def determine_format(self, request):
        return determine_format(
            request, self._meta.serializer,
            default_format=self._meta.default_format)

    def serialize(self, request, data, format, options={}):
        options = options or {}

        if 'text/javascript' in format:
            # get JSONP callback name. default to "callback"
            callback = request.GET.get('callback', 'callback')

            if not is_valid_jsonp_callback_value(callback):
                raise BadRequest('JSONP callback name is invalid.')

            options['callback'] = callback
        return self._meta.serializer.serialize(data, format, options)

    def deserialize(self, request, data, format):
        return self._meta.serializer.deserialize(data, format)

    def raise_validation_error(self, request, errors):
        self.raise_coded_error(request, 'VALIDATION_ERROR', errors)

    def raise_coded_error(self, request, code, errors, errors_extra=None,
                          response_cls=cake_http.HttpBadRequest):
        errors = {'code': code, 'errors': errors}

        if errors_extra is not None:
            errors.update(errors_extra)

        self.raise_http_error(request, errors, response_cls=response_cls)

    def raise_http_error(self, request, error,
                         response_cls=cake_http.HttpBadRequest):
        if request:
            desired_format = self.determine_format(request)
        else:
            desired_format = self._meta.default_format

        response = response_cls(
            content_type=build_content_type(desired_format),
            content=self.serialize(request, error, desired_format))

        raise ImmediateHttpResponse(response=response)

    def raise_authorization_error(self):
        raise ImmediateHttpResponse(response_cls=cake_http.HttpUnauthorized)

    def _get_include_entity(self, resource_response, force_include_entity):
        if force_include_entity:
            return True
        elif resource_response.include_entity is not None:
            return resource_response.include_entity

        return self._meta.include_entity

    def get_http_response_details(self, resource_response, entity,
                                  include_entity, default_response_cls,
                                  default_response_kwargs):
        response_cls = resource_response.get_response_cls()

        if response_cls is not None:
            response_kwargs = resource_response.get_response_kwargs(entity)
        else:
            if default_response_cls is not None:
                response_cls = default_response_cls
                response_kwargs = default_response_kwargs
            else:
                response_kwargs = {}
                response_cls = cake_http.HttpResponse \
                    if include_entity else cake_http.HttpNoContent

        return response_cls, response_kwargs

    def _process_http_response(self, request, http_response, obj):
        if hasattr(self, 'process_http_response'):
            self.process_http_response(http_response, obj)

        method_response_processor = getattr(
            self, 'process_http_response_%s' % request.method.lower(), None)

        if method_response_processor is not None:
            method_response_processor(http_response, obj)

    def create_http_response(self, request, resource_response,
                             created=False, force_include_entity=None,
                             default_response_cls=None,
                             **default_response_kwargs):
        if resource_response is None:
            return

        include_entity = self._get_include_entity(
            resource_response, force_include_entity)

        entity_cls = resource_response.get_entity_cls(
            self._meta.get_detail_entity_cls())

        if resource_response.obj is None:
            if created or include_entity:
                raise ResourceEntityError(
                    "'ResourceResponse.obj' must not be None if 'created'" \
                    " or 'include_entity' is True")
            entity = None
        else:
            if entity_cls is None:
                raise ResourceEntityError(
                    "Must specify 'entity_cls' or 'detail_entity_cls' if" \
                    " 'created' or 'include_entity' is True")

            entity = entity_cls(resource_response.obj)

        if created:
            http_response_cls = cake_http.HttpCreated
            http_response_kwargs = {'location': entity.get_resource_uri()}
        else:
            http_response_cls, http_response_kwargs = \
                self.get_http_response_details(
                    resource_response, entity, include_entity,
                    default_response_cls, default_response_kwargs)

        desired_format = self.determine_format(request)

        content = '' if entity is None or include_entity is False else \
            self.serialize(request, entity.full_process(), desired_format)

        http_response = http_response_cls(
            content=content, content_type=build_content_type(desired_format),
            **http_response_kwargs)

        self._process_http_response(request, http_response, entity)

        return http_response

    def head_impl(self, request, *args, **kwargs):
        if hasattr(self, 'get'):
            return self.get(request, *args, **kwargs)


class DetailResource(Resource):
    __metaclass__ = DetailResourceMetaClass

    def dispatch_get(self, request, *args, **kwargs):
        return self.create_http_response(request,
            self.dispatch_method(self.get, request, *args, **kwargs),
            force_include_entity=True)

    def dispatch_head(self, request, *args, **kwargs):
        return self.create_http_response(request,
            self.dispatch_method(self.head, request, *args, **kwargs),
            default_response_cls=cake_http.HttpResponse,
            force_include_entity=False)

    def dispatch_put(self, request, *args, **kwargs):
        return self.dispatch_creation(self.put, request, *args, **kwargs)

    def dispatch_delete(self, request, *args, **kwargs):
        return self.create_http_response(request,
            self.dispatch_method(self.delete, request, *args, **kwargs))


class ListResource(Resource):
    __metaclass__ = ListResourceMetaClass

    def dispatch_get(self, request, *args, **kwargs):
        return self.create_http_list_response(
            request, self.dispatch_method(self.get, request, *args, **kwargs),
            paginated=True, force_include_entity=True)

    def dispatch_head(self, request, *args, **kwargs):
        return self.create_http_list_response(request,
            self.dispatch_method(self.head, request, *args, **kwargs),
            paginated=True, force_include_entity=False,
            default_response_cls=cake_http.HttpResponse)

    def dispatch_put(self, request, *args, **kwargs):
        return self.create_http_list_response(request,
            self.dispatch_method(self.put, request, *args, **kwargs))

    def dispatch_delete(self, request, *args, **kwargs):
        return self.create_http_list_response(request,
            self.dispatch_method(self.delete, request, *args, **kwargs))

    def create_http_list_response(self, request, resource_response,
                                  paginated=False, force_include_entity=None,
                                  default_response_cls=None,
                                  **default_response_kwargs):
        if resource_response is None:
            return

        include_entity = self._get_include_entity(
            resource_response, force_include_entity)

        entity_cls = resource_response.get_entity_cls(
            self._meta.get_detail_entity_cls())

        if entity_cls is None and include_entity:
            raise ResourceEntityError(
                "Must specify 'entity_cls', 'list_entity_cls', or " \
                "'detail_entity_cls' if 'include_entity' is True")

        obj = resource_response.obj

        if obj is None:
            entities = []
        elif not isinstance(obj, collections.Iterable):
            entities = [obj]
        else:
            entities = obj

        if paginated:
            paginator = self._meta.paginator_cls(
                request.GET, entities, resource_uri=self.get_resource_uri(),
                limit=self._meta.limit, max_limit=self._meta.max_limit,
                collection_name=self._meta.collection_name)

            page = paginator.page()
            entities = page[self._meta.collection_name]
        else:
            page = {}
            page[self._meta.collection_name] = entities

        http_response_cls, http_response_kwargs = \
            self.get_http_response_details(
                resource_response, entities, include_entity,
                default_response_cls, default_response_kwargs)

        desired_format = self.determine_format(request)

        if include_entity:
            entities = [entity_cls(obj).full_process() for obj in entities]
            page[self._meta.collection_name] = entities
            content = self.serialize(request, page, desired_format)
        else:
            content = ''
            entities = None

        http_response = http_response_cls(
            content=content, content_type=build_content_type(desired_format),
            **http_response_kwargs)

        self._process_http_response(request, http_response, entities)

        return http_response

    def get_resource_uri(self):
        raise NotImplementedError


class MultipartResource(DetailResource):
    def convert_post_to_VERB(self, request, verb):
        if request.method == verb:
            if hasattr(request, '_post'):
                del(request._post)
                del(request._files)

            try:
                request.method = 'POST'
                request._load_post_and_files()
                request.method = verb
            except AttributeError:
                request.META['REQUEST_METHOD'] = 'POST'
                request._load_post_and_files()
                request.META['REQUEST_METHOD'] = verb

            setattr(request, verb, request.POST)

    def convert_post_to_put(self, request):
        return self.convert_post_to_VERB(request, verb='PUT')

    def deserialize(self, request, data, format=None):
        self.convert_post_to_put(request)

        if not format:
            format = request.META.get('CONTENT_TYPE', 'application/json')

        if format == 'application/x-www-form-urlencoded':
            return request.POST

        if format.startswith('multipart'):
            data = request.POST.copy()
            data.update(request.FILES)

            return data

        return super(MultipartResource, self).deserialize(
            request, data, format)

########NEW FILE########
__FILENAME__ = response
from delicious_cake import http as cake_http

__all__ = ('ResourceResponse',)


class ResourceResponse(object):
    def __init__(self, obj=None, entity_cls=None, include_entity=None,
                 response_cls=None, response_kwargs=None):
        self.obj = obj

        self.entity_cls = entity_cls
        self.include_entity = include_entity

        self.response_cls = response_cls
        self.response_kwargs = response_kwargs

    def get_entity_cls(self, default=None):
        return self.entity_cls if self.entity_cls is not None else default

    def get_response_cls(self, default=None):
        return self.response_cls if self.response_cls is not None else default

    def get_response_kwargs(self, obj):
        ret = {}

        if self.response_kwargs is not None:
            for key in self.response_kwargs.keys():
                val = self.response_kwargs[key]

                if callable(val):
                    val = val(obj)

                ret[key] = val

        return ret

########NEW FILE########
__FILENAME__ = serializers
import datetime
from StringIO import StringIO

import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers import json
from django.utils import simplejson
from django.utils.encoding import force_unicode

from delicious_cake.exceptions import (
    BadRequest, UnsupportedFormat, UnsupportedSerializationFormat,
    UnsupportedDeserializationFormat,)

from delicious_cake.utils import (
    format_datetime, format_date, format_time, make_naive)

try:
    import lxml
    from lxml.etree import parse as parse_xml
    from lxml.etree import Element, tostring
except ImportError:
    lxml = None
try:
    import yaml
    from django.core.serializers import pyyaml
except ImportError:
    yaml = None
try:
    import biplist
except ImportError:
    biplist = None


# Ugh & blah.
# So doing a regular dump is generally fine, since DeliciousCake doesn't usually
# serialize advanced types. *HOWEVER*, it will dump out Python Unicode strings
# as a custom YAML tag, which of course ``yaml.safe_load`` can't handle.
if yaml is not None:
    from yaml.constructor import SafeConstructor
    from yaml.loader import Reader, Scanner, Parser, Composer, Resolver

    class DeliciousCakeConstructor(SafeConstructor):
        def construct_yaml_unicode_dammit(self, node):
            value = self.construct_scalar(node)
            try:
                return value.encode('ascii')
            except UnicodeEncodeError:
                return value

    DeliciousCakeConstructor.add_constructor(u'tag:yaml.org,2002:python/unicode', DeliciousCakeConstructor.construct_yaml_unicode_dammit)

    class DeliciousCakeLoader(Reader, Scanner, Parser, Composer, DeliciousCakeConstructor, Resolver):
        def __init__(self, stream):
            Reader.__init__(self, stream)
            Scanner.__init__(self)
            Parser.__init__(self)
            Composer.__init__(self)
            DeliciousCakeConstructor.__init__(self)
            Resolver.__init__(self)


class Serializer(object):
    """
    A swappable class for serialization.

    This handles most types of data as well as the following output formats::

        * json
        * jsonp
        * xml
        * yaml
        * html
        * plist (see http://explorapp.com/biplist/)

    It was designed to make changing behavior easy, either by overridding the
    various format methods (i.e. ``to_json``), by changing the
    ``formats/content_types`` options or by altering the other hook methods.
    """
    formats = ['json', 'jsonp', 'xml', 'yaml', 'html', 'plist']
    content_types = {
        'json': 'application/json',
        'jsonp': 'text/javascript',
        'xml': 'application/xml',
        'yaml': 'text/yaml',
        'html': 'text/html',
        'plist': 'application/x-plist',
    }

    def __init__(self, formats=None, content_types=None, datetime_formatting=None):
        self.supported_formats = []
        self.datetime_formatting = getattr(settings, 'DELICIOUS_CAKE_DATETIME_FORMATTING', 'iso-8601')

        if formats is not None:
            self.formats = formats

        if content_types is not None:
            self.content_types = content_types

        if datetime_formatting is not None:
            self.datetime_formatting = datetime_formatting

        for format in self.formats:
            try:
                self.supported_formats.append(self.content_types[format])
            except KeyError:
                raise UnsupportedFormat("Content type for specified type '%s' not found. Please provide it at either the class level or via the arguments." % format)

    def get_mime_for_format(self, format):
        """
        Given a format, attempts to determine the correct MIME type.

        If not available on the current ``Serializer``, returns
        ``application/json`` by default.
        """
        try:
            return self.content_types[format]
        except KeyError:
            return 'application/json'

    def format_datetime(self, data):
        """
        A hook to control how datetimes are formatted.

        Can be overridden at the ``Serializer`` level (``datetime_formatting``)
        or globally (via ``settings.DELICIOUS_CAKE_DATETIME_FORMATTING``).

        Default is ``iso-8601``, which looks like "2010-12-16T03:02:14".
        """
        data = make_naive(data)
        if self.datetime_formatting == 'rfc-2822':
            return format_datetime(data)

        return data.isoformat()

    def format_date(self, data):
        """
        A hook to control how dates are formatted.

        Can be overridden at the ``Serializer`` level (``datetime_formatting``)
        or globally (via ``settings.DELICIOUS_CAKE_DATETIME_FORMATTING``).

        Default is ``iso-8601``, which looks like "2010-12-16".
        """
        if self.datetime_formatting == 'rfc-2822':
            return format_date(data)

        return data.isoformat()

    def format_time(self, data):
        """
        A hook to control how times are formatted.

        Can be overridden at the ``Serializer`` level (``datetime_formatting``)
        or globally (via ``settings.DELICIOUS_CAKE_DATETIME_FORMATTING``).

        Default is ``iso-8601``, which looks like "03:02:14".
        """
        if self.datetime_formatting == 'rfc-2822':
            return format_time(data)

        return data.isoformat()

    def serialize(self, bundle, format, options={}):
        """
        Given some data and a format, calls the correct method to serialize
        the data and returns the result.
        """
        desired_format = None

        for short_format, long_format in self.content_types.items():
            if format == long_format:
                if hasattr(self, "to_%s" % short_format):
                    desired_format = short_format
                    break

        if desired_format is None:
            raise UnsupportedSerializationFormat("The format indicated '%s' had no available serialization method. Please check your ``formats`` and ``content_types`` on your Serializer." % format)

        try:
            serialized = \
                getattr(self, "to_%s" % desired_format)(bundle, options)
        except UnsupportedSerializationFormat, e:
            raise
        except Exception, e:
            raise BadRequest()

        return serialized

    def deserialize(self, content, format):
        """
        Given some data and a format, calls the correct method to deserialize
        the data and returns the result.
        """
        desired_format = None

        format = format.split(';')[0]

        for short_format, long_format in self.content_types.items():
            if format == long_format:
                if hasattr(self, "from_%s" % short_format):
                    desired_format = short_format
                    break

        if desired_format is None:
            raise UnsupportedDeserializationFormat("The format indicated '%s' had no available deserialization method. Please check your ``formats`` and ``content_types`` on your Serializer." % format)

        try:
            deserialized = getattr(self, "from_%s" % desired_format)(content)
        except UnsupportedDeserializationFormat, e:
            raise
        except Exception, e:
            raise BadRequest()

        return deserialized

    def to_simple(self, data, options):
        """
        For a piece of data, attempts to recognize it and provide a simplified
        form of something complex.

        This brings complex Python data structures down to native types of the
        serialization format(s).
        """
        if isinstance(data, (list, tuple)):
            return [self.to_simple(item, options) for item in data]
        if isinstance(data, dict):
            return dict((key, self.to_simple(val, options)) for (key, val) in data.iteritems())
        elif isinstance(data, datetime.datetime):
            return self.format_datetime(data)
        elif isinstance(data, datetime.date):
            return self.format_date(data)
        elif isinstance(data, datetime.time):
            return self.format_time(data)
        elif isinstance(data, bool):
            return data
        elif type(data) in (long, int, float):
            return data
        elif data is None:
            return None
        else:
            return force_unicode(data)

    def to_etree(self, data, options=None, name=None, depth=0):
        """
        Given some data, converts that data to an ``etree.Element`` suitable
        for use in the XML output.
        """
        if isinstance(data, (list, tuple)):
            element = Element(name or 'objects')
            if name:
                element = Element(name)
                element.set('type', 'list')
            else:
                element = Element('objects')
            for item in data:
                element.append(self.to_etree(item, options, depth=depth + 1))
        elif isinstance(data, dict):
            if depth == 0:
                element = Element(name or 'response')
            else:
                element = Element(name or 'object')
                element.set('type', 'hash')
            for (key, value) in data.iteritems():
                element.append(self.to_etree(value, options, name=key, depth=depth + 1))
        else:
            element = Element(name or 'value')
            simple_data = self.to_simple(data, options)
            data_type = get_type_string(simple_data)

            if data_type != 'string':
                element.set('type', get_type_string(simple_data))

            if data_type != 'null':
                if isinstance(simple_data, unicode):
                    element.text = simple_data
                else:
                    element.text = force_unicode(simple_data)

        return element

    def from_etree(self, data):
        """
        Not the smartest deserializer on the planet. At the request level,
        it first tries to output the deserialized subelement called "object"
        or "objects" and falls back to deserializing based on hinted types in
        the XML element attribute "type".
        """
        if data.tag == 'request':
            # if "object" or "objects" exists, return deserialized forms.
            elements = data.getchildren()
            for element in elements:
                if element.tag in ('object', 'objects'):
                    return self.from_etree(element)
            return dict((element.tag, self.from_etree(element)) for element in elements)
        elif data.tag == 'object' or data.get('type') == 'hash':
            return dict((element.tag, self.from_etree(element)) for element in data.getchildren())
        elif data.tag == 'objects' or data.get('type') == 'list':
            return [self.from_etree(element) for element in data.getchildren()]
        else:
            type_string = data.get('type')
            if type_string in ('string', None):
                return data.text
            elif type_string == 'integer':
                return int(data.text)
            elif type_string == 'float':
                return float(data.text)
            elif type_string == 'boolean':
                if data.text == 'True':
                    return True
                else:
                    return False
            else:
                return None

    def to_json(self, data, options=None):
        """
        Given some Python data, produces JSON output.
        """
        options = options or {}
        data = self.to_simple(data, options)

        sort_keys = settings.DEBUG

        if django.get_version() >= '1.5':
            return json.json.dumps(data, cls=json.DjangoJSONEncoder, sort_keys=sort_keys, ensure_ascii=False)
        else:
            return simplejson.dumps(data, cls=json.DjangoJSONEncoder, sort_keys=sort_keys, ensure_ascii=False)

    def from_json(self, content):
        """
        Given some JSON data, returns a Python dictionary of the decoded data.
        """
        return simplejson.loads(content)

    def to_jsonp(self, data, options=None):
        """
        Given some Python data, produces JSON output wrapped in the provided
        callback.

        Due to a difference between JSON and Javascript, two
        newline characters, \u2028 and \u2029, need to be escaped.
        See http://timelessrepo.com/json-isnt-a-javascript-subset for
        details.
        """
        options = options or {}
        json = self.to_json(data, options)
        json = json.replace(u'\u2028', u'\\u2028').replace(u'\u2029', u'\\u2029')
        return u'%s(%s)' % (options['callback'], json)

    def to_xml(self, data, options=None):
        """
        Given some Python data, produces XML output.
        """
        options = options or {}

        if lxml is None:
            raise UnsupportedSerializationFormat("Usage of the XML aspects requires lxml.")

        return tostring(self.to_etree(data, options), xml_declaration=True, encoding='utf-8')

    def from_xml(self, content):
        """
        Given some XML data, returns a Python dictionary of the decoded data.
        """
        if lxml is None:
            raise UnsupportedDeserializationFormat("Usage of the XML aspects requires lxml.")

        return self.from_etree(parse_xml(StringIO(content)).getroot())

    def to_yaml(self, data, options=None):
        """
        Given some Python data, produces YAML output.
        """
        options = options or {}

        if yaml is None:
            raise UnsupportedSerializationFormat("Usage of the YAML aspects requires yaml.")

        return yaml.dump(self.to_simple(data, options))

    def from_yaml(self, content):
        """
        Given some YAML data, returns a Python dictionary of the decoded data.
        """
        if yaml is None:
            raise UnsupportedDeserializationFormat("Usage of the YAML aspects requires yaml.")

        return yaml.load(content, Loader=DeliciousCakeLoader)

    def to_plist(self, data, options=None):
        """
        Given some Python data, produces binary plist output.
        """
        options = options or {}

        if biplist is None:
            raise UnsupportedSerializationFormat("Usage of the plist aspects requires biplist.")

        return biplist.writePlistToString(self.to_simple(data, options))

    def from_plist(self, content):
        """
        Given some binary plist data, returns a Python dictionary of the decoded data.
        """
        if biplist is None:
            raise UnsupportedDeserializationFormat("Usage of the plist aspects requires biplist.")

        return biplist.readPlistFromString(content)

    def to_html(self, data, options=None):
        """
        Reserved for future usage.

        The desire is to provide HTML output of a resource, making an API
        available to a browser. This is on the TODO list but not currently
        implemented.
        """
        options = options or {}
        return 'Sorry, not implemented yet. Please append "?format=json" to your URL.'

    def from_html(self, content):
        """
        Reserved for future usage.

        The desire is to handle form-based (maybe Javascript?) input, making an
        API available to a browser. This is on the TODO list but not currently
        implemented.
        """
        pass


def get_type_string(data):
    """
    Translates a Python data type into a string format.
    """
    data_type = type(data)

    if data_type in (int, long):
        return 'integer'
    elif data_type == float:
        return 'float'
    elif data_type == bool:
        return 'boolean'
    elif data_type in (list, tuple):
        return 'list'
    elif data_type == dict:
        return 'hash'
    elif data is None:
        return 'null'
    elif isinstance(data, basestring):
        return 'string'

########NEW FILE########
__FILENAME__ = test
import time
from urlparse import urlparse

from django.conf import settings
from django.test import TestCase
from django.test.client import FakePayload, Client
from delicious_cake.serializers import Serializer


class TestApiClient(object):
    def __init__(self, serializer=None):
        """
        Sets up a fresh ``TestApiClient`` instance.

        If you are employing a custom serializer, you can pass the class to the
        ``serializer=`` kwarg.
        """
        self.client = Client()
        self.serializer = serializer

        if not self.serializer:
            self.serializer = Serializer()

    def get_content_type(self, short_format):
        """
        Given a short name (such as ``json`` or ``xml``), returns the full content-type
        for it (``application/json`` or ``application/xml`` in this case).
        """
        return self.serializer.content_types.get(short_format, 'json')

    def get(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``GET`` request to the provided URI.

        Optionally accepts a ``data`` kwarg, which in the case of ``GET``, lets you
        send along ``GET`` parameters. This is useful when testing filtering or other
        things that read off the ``GET`` params. Example::

            from delicious_cake.test import TestApiClient
            client = TestApiClient()

            response = client.get('/api/v1/entry/1/', data={'format': 'json', 'title__startswith': 'a', 'limit': 20, 'offset': 60})

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['HTTP_ACCEPT'] = content_type

        # GET & DELETE are the only times we don't serialize the data.
        if data is not None:
            kwargs['data'] = data

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.get(uri, **kwargs)

    def head(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``GET`` request to the provided URI.

        Optionally accepts a ``data`` kwarg, which in the case of ``GET``, lets you
        send along ``GET`` parameters. This is useful when testing filtering or other
        things that read off the ``GET`` params. Example::

            from delicious_cake.test import TestApiClient
            client = TestApiClient()

            response = client.get('/api/v1/entry/1/', data={'format': 'json', 'title__startswith': 'a', 'limit': 20, 'offset': 60})

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['HTTP_ACCEPT'] = content_type

        # GET & DELETE are the only times we don't serialize the data.
        if data is not None:
            kwargs['data'] = data

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.head(uri, **kwargs)

    def post(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``POST`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``POST`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from delicious_cake.test import TestApiClient
            client = TestApiClient()

            response = client.post('/api/v1/entry/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['content_type'] = content_type

        if data is not None:
            kwargs['data'] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.post(uri, **kwargs)

    def put(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``PUT`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``PUT`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from delicious_cake.test import TestApiClient
            client = TestApiClient()

            response = client.put('/api/v1/entry/1/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['content_type'] = content_type

        if data is not None:
            kwargs['data'] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.put(uri, **kwargs)

    def patch(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``PATCH`` request to the provided URI.

        Optionally accepts a ``data`` kwarg. **Unlike** ``GET``, in ``PATCH`` the
        ``data`` gets serialized & sent as the body instead of becoming part of the URI.
        Example::

            from delicious_cake.test import TestApiClient
            client = TestApiClient()

            response = client.patch('/api/v1/entry/1/', data={
                'created': '2012-05-01T20:02:36',
                'slug': 'another-post',
                'title': 'Another Post',
                'user': '/api/v1/user/1/',
            })

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['content_type'] = content_type

        if data is not None:
            kwargs['data'] = self.serializer.serialize(data, format=content_type)

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        # This hurts because Django doesn't support PATCH natively.
        parsed = urlparse(uri)
        r = {
            'CONTENT_LENGTH': len(kwargs['data']),
            'CONTENT_TYPE': content_type,
            'PATH_INFO': self.client._get_path(parsed),
            'QUERY_STRING': parsed[4],
            'REQUEST_METHOD': 'PATCH',
            'wsgi.input': FakePayload(kwargs['data']),
        }
        r.update(kwargs)
        return self.client.request(**r)

    def delete(self, uri, format='json', data=None, authentication=None, **kwargs):
        """
        Performs a simulated ``DELETE`` request to the provided URI.

        Optionally accepts a ``data`` kwarg, which in the case of ``DELETE``, lets you
        send along ``DELETE`` parameters. This is useful when testing filtering or other
        things that read off the ``DELETE`` params. Example::

            from delicious_cake.test import TestApiClient
            client = TestApiClient()

            response = client.delete('/api/v1/entry/1/', data={'format': 'json'})

        Optionally accepts an ``authentication`` kwarg, which should be an HTTP header
        with the correct authentication data already setup.

        All other ``**kwargs`` passed in get passed through to the Django
        ``TestClient``. See https://docs.djangoproject.com/en/dev/topics/testing/#module-django.test.client
        for details.
        """
        content_type = self.get_content_type(format)
        kwargs['content_type'] = content_type

        # GET & DELETE are the only times we don't serialize the data.
        if data is not None:
            kwargs['data'] = data

        if authentication is not None:
            kwargs['HTTP_AUTHORIZATION'] = authentication

        return self.client.delete(uri, **kwargs)


class ResourceTestCase(TestCase):
    """
    A useful base class for the start of testing Delicious Cake APIs.
    """
    def setUp(self):
        super(ResourceTestCase, self).setUp()
        self.serializer = Serializer()
        self.api_client = TestApiClient()

    def get_credentials(self):
        """
        A convenience method for the user as a way to shorten up the
        often repetitious calls to create the same authentication.

        Raises ``NotImplementedError`` by default.

        Usage::

            class MyResourceTestCase(ResourceTestCase):
                def get_credentials(self):
                    return self.create_basic('daniel', 'pass')

                # Then the usual tests...

        """
        raise NotImplementedError("You must return the class for your Resource to test.")

    def create_basic(self, username, password):
        """
        Creates & returns the HTTP ``Authorization`` header for use with BASIC
        Auth.
        """
        import base64
        return 'Basic %s' % base64.b64encode(':'.join([username, password]))

    def create_apikey(self, username, api_key):
        """
        Creates & returns the HTTP ``Authorization`` header for use with
        ``ApiKeyAuthentication``.
        """
        return 'ApiKey %s:%s' % (username, api_key)

    def create_digest(self, username, api_key, method, uri):
        """
        Creates & returns the HTTP ``Authorization`` header for use with Digest
        Auth.
        """
        from delicious_cake.authentication import (
            hmac, sha1, uuid, python_digest,)

        new_uuid = uuid.uuid4()
        opaque = hmac.new(str(new_uuid), digestmod=sha1).hexdigest()

        return python_digest.build_authorization_request(
            username, method.upper(), uri, 1, # nonce_count
            digest_challenge=python_digest.build_digest_challenge(
                time.time(), getattr(settings, 'SECRET_KEY', ''),
                'delicious-cake', opaque, False), password=api_key)

    def create_oauth(self, user):
        """
        Creates & returns the HTTP ``Authorization`` header for use with Oauth.
        """
        from oauth_provider.models import Consumer, Token, Resource

        # Necessary setup for ``oauth_provider``.
        resource, _ = Resource.objects.get_or_create(url='test', defaults={
            'name': 'Test Resource'
        })
        consumer, _ = Consumer.objects.get_or_create(key='123', defaults={
            'name': 'Test',
            'description': 'Testing...'
        })
        token, _ = Token.objects.get_or_create(key='foo', token_type=Token.ACCESS, defaults={
            'consumer': consumer,
            'resource': resource,
            'secret': '',
            'user': user,
        })

        # Then generate the header.
        oauth_data = {
            'oauth_consumer_key': '123',
            'oauth_nonce': 'abc',
            'oauth_signature': '&',
            'oauth_signature_method': 'PLAINTEXT',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': 'foo',
        }
        return 'OAuth %s' % ','.join([key + '=' + value for key, value in oauth_data.items()])

    def assertHttpOK(self, resp):
        """
        Ensures the response is returning a HTTP 200.
        """
        return self.assertEqual(resp.status_code, 200)

    def assertHttpCreated(self, resp):
        """
        Ensures the response is returning a HTTP 201.
        """
        return self.assertEqual(resp.status_code, 201)

    def assertHttpAccepted(self, resp):
        """
        Ensures the response is returning a HTTP 202.
        """
        return self.assertEqual(resp.status_code, 202)

    def assertHttpNoContent(self, resp):
        """
        Ensures the response is returning HTTP 204.
        """
        return self.assertEqual(resp.status_code, 204)

    def assertHttpMultipleChoices(self, resp):
        """
        Ensures the response is returning a HTTP 300.
        """
        return self.assertEqual(resp.status_code, 300)

    def assertHttpSeeOther(self, resp):
        """
        Ensures the response is returning a HTTP 303.
        """
        return self.assertEqual(resp.status_code, 303)

    def assertHttpNotModified(self, resp):
        """
        Ensures the response is returning a HTTP 304.
        """
        return self.assertEqual(resp.status_code, 304)

    def assertHttpBadRequest(self, resp):
        """
        Ensures the response is returning a HTTP 400.
        """
        return self.assertEqual(resp.status_code, 400)

    def assertHttpUnauthorized(self, resp):
        """
        Ensures the response is returning a HTTP 401.
        """
        return self.assertEqual(resp.status_code, 401)

    def assertHttpForbidden(self, resp):
        """
        Ensures the response is returning a HTTP 403.
        """
        return self.assertEqual(resp.status_code, 403)

    def assertHttpNotFound(self, resp):
        """
        Ensures the response is returning a HTTP 404.
        """
        return self.assertEqual(resp.status_code, 404)

    def assertHttpMethodNotAllowed(self, resp):
        """
        Ensures the response is returning a HTTP 405.
        """
        return self.assertEqual(resp.status_code, 405)

    def assertHttpConflict(self, resp):
        """
        Ensures the response is returning a HTTP 409.
        """
        return self.assertEqual(resp.status_code, 409)

    def assertHttpGone(self, resp):
        """
        Ensures the response is returning a HTTP 410.
        """
        return self.assertEqual(resp.status_code, 410)

    def assertHttpTooManyRequests(self, resp):
        """
        Ensures the response is returning a HTTP 429.
        """
        return self.assertEqual(resp.status_code, 429)

    def assertHttpApplicationError(self, resp):
        """
        Ensures the response is returning a HTTP 500.
        """
        return self.assertEqual(resp.status_code, 500)

    def assertHttpNotImplemented(self, resp):
        """
        Ensures the response is returning a HTTP 501.
        """
        return self.assertEqual(resp.status_code, 501)

    def assertValidJSON(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid JSON &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_json(data)

    def assertValidXML(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid XML &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_xml(data)

    def assertValidYAML(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid YAML &
        can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_yaml(data)

    def assertValidPlist(self, data):
        """
        Given the provided ``data`` as a string, ensures that it is valid
        binary plist & can be loaded properly.
        """
        # Just try the load. If it throws an exception, the test case will fail.
        self.serializer.from_plist(data)

    def assertValidJSONResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/json``)
        * The content is valid JSON
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp['Content-Type'].startswith('application/json'))
        self.assertValidJSON(resp.content)

    def assertValidXMLResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/xml``)
        * The content is valid XML
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp['Content-Type'].startswith('application/xml'))
        self.assertValidXML(resp.content)

    def assertValidYAMLResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``text/yaml``)
        * The content is valid YAML
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp['Content-Type'].startswith('text/yaml'))
        self.assertValidYAML(resp.content)

    def assertValidPlistResponse(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, assert that
        you get back:

        * An HTTP 200
        * The correct content-type (``application/x-plist``)
        * The content is valid binary plist data
        """
        self.assertHttpOK(resp)
        self.assertTrue(resp['Content-Type'].startswith('application/x-plist'))
        self.assertValidPlist(resp.content)

    def deserialize(self, resp):
        """
        Given a ``HttpResponse`` coming back from using the ``client``, this method
        checks the ``Content-Type`` header & attempts to deserialize the data based on
        that.

        It returns a Python datastructure (typically a ``dict``) of the serialized data.
        """
        return self.serializer.deserialize(resp.content, format=resp['Content-Type'])

    def serialize(self, data, format='application/json'):
        """
        Given a Python datastructure (typically a ``dict``) & a desired content-type,
        this method will return a serialized string of that data.
        """
        return self.serializer.serialize(data, format=format)

    def assertKeys(self, data, expected):
        """
        This method ensures that the keys of the ``data`` match up to the keys of
        ``expected``.

        It covers the (extremely) common case where you want to make sure the keys of
        a response match up to what is expected. This is typically less fragile than
        testing the full structure, which can be prone to data changes.
        """
        self.assertEqual(sorted(data.keys()), sorted(expected))

########NEW FILE########
__FILENAME__ = throttle
import time
from django.core.cache import cache


class BaseThrottle(object):
    """
    A simplified, swappable base class for throttling.

    Does nothing save for simulating the throttling API and implementing
    some common bits for the subclasses.

    Accepts a number of optional kwargs::

        * ``throttle_at`` - the number of requests at which the user should
          be throttled. Default is 150 requests.
        * ``timeframe`` - the length of time (in seconds) in which the user
          make up to the ``throttle_at`` requests. Default is 3600 seconds (
          1 hour).
        * ``expiration`` - the length of time to retain the times the user
          has accessed the api in the cache. Default is 604800 (1 week).
    """
    def __init__(self, throttle_at=150, timeframe=3600, expiration=None):
        self.throttle_at = throttle_at
        # In seconds, please.
        self.timeframe = timeframe

        if expiration is None:
            # Expire in a week.
            expiration = 604800

        self.expiration = int(expiration)

    def convert_identifier_to_key(self, identifier):
        """
        Takes an identifier (like a username or IP address) and converts it
        into a key usable by the cache system.
        """
        bits = []

        for char in identifier:
            if char.isalnum() or char in ['_', '.', '-']:
                bits.append(char)

        safe_string = ''.join(bits)
        return "%s_accesses" % safe_string

    def should_be_throttled(self, identifier, **kwargs):
        """
        Returns whether or not the user has exceeded their throttle limit.

        Always returns ``False``, as this implementation does not actually
        throttle the user.
        """
        return False

    def accessed(self, identifier, **kwargs):
        """
        Handles recording the user's access.

        Does nothing in this implementation.
        """
        pass


class CacheThrottle(BaseThrottle):
    """
    A throttling mechanism that uses just the cache.
    """
    def should_be_throttled(self, identifier, **kwargs):
        """
        Returns whether or not the user has exceeded their throttle limit.

        Maintains a list of timestamps when the user accessed the api within
        the cache.

        Returns ``False`` if the user should NOT be throttled or ``True`` if
        the user should be throttled.
        """
        key = self.convert_identifier_to_key(identifier)

        # Make sure something is there.
        cache.add(key, [])

        # Weed out anything older than the timeframe.
        minimum_time = int(time.time()) - int(self.timeframe)
        times_accessed = [
            access for access in cache.get(key) if access >= minimum_time]
        cache.set(key, times_accessed, self.expiration)

        if len(times_accessed) >= int(self.throttle_at):
            # Throttle them.
            return True

        # Let them through.
        return False

    def accessed(self, identifier, **kwargs):
        """
        Handles recording the user's access.

        Stores the current timestamp in the "accesses" list within the cache.
        """
        key = self.convert_identifier_to_key(identifier)
        times_accessed = cache.get(key, [])
        times_accessed.append(int(time.time()))
        cache.set(key, times_accessed, self.expiration)


class CacheDBThrottle(CacheThrottle):
    """
    A throttling mechanism that uses the cache for actual throttling but
    writes-through to the database.

    This is useful for tracking/aggregating usage through time, to possibly
    build a statistics interface or a billing mechanism.
    """
    def accessed(self, identifier, **kwargs):
        """
        Handles recording the user's access.

        Does everything the ``CacheThrottle`` class does, plus logs the
        access within the database using the ``ApiAccess`` model.
        """
        # Do the import here, instead of top-level, so that the model is
        # only required when using this throttling mechanism.
        from delicious_cake.models import ApiAccess
        super(CacheDBThrottle, self).accessed(identifier, **kwargs)
        # Write out the access to the DB for logging purposes.
        ApiAccess.objects.create(
            identifier=identifier,
            url=kwargs.get('url', ''),
            request_method=kwargs.get('request_method', ''))

########NEW FILE########
__FILENAME__ = formatting
import email
import datetime
import time
from django.utils import dateformat
from delicious_cake.utils.timezone import make_aware, make_naive, aware_datetime

# Try to use dateutil for maximum date-parsing niceness. Fall back to
# hard-coded RFC2822 parsing if that's not possible.
try:
    from dateutil.parser import parse as mk_datetime
except ImportError:
    def mk_datetime(string):
        return make_aware(
            datetime.datetime.fromtimestamp(
                time.mktime(email.utils.parsedate(string))))

__all__ = ('format_datetime', 'format_date', 'format_time',)


def format_datetime(dt):
    """
    RFC 2822 datetime formatter
    """
    return dateformat.format(make_naive(dt), 'r')


def format_date(d):
    """
    RFC 2822 date formatter
    """
    # workaround because Django's dateformat utility requires a datetime
    # object (not just date)
    dt = aware_datetime(d.year, d.month, d.day, 0, 0, 0)
    return dateformat.format(dt, 'j M Y')


def format_time(t):
    """
    RFC 2822 time formatter
    """
    # again, workaround dateformat input requirement
    dt = aware_datetime(2000, 1, 1, t.hour, t.minute, t.second)
    return dateformat.format(dt, 'H:i:s O')

########NEW FILE########
__FILENAME__ = mime
import mimeparse

__all__ = ('determine_format', 'build_content_type',)


def determine_format(request, serializer, default_format='application/json'):
    """
    Tries to "smartly" determine which output format is desired.

    First attempts to find a ``format`` override from the request and supplies
    that if found.

    If no request format was demanded, it falls back to ``mimeparse`` and the
    ``Accepts`` header, allowing specification that way.

    If still no format is found, returns the ``default_format`` (which defaults
    to ``application/json`` if not provided).
    """
    # First, check if they forced the format.
    if request.GET.get('format'):
        if request.GET['format'] in serializer.formats:
            return serializer.get_mime_for_format(request.GET['format'])

    # Try to fallback on the Accepts header.
    if request.META.get('HTTP_ACCEPT', '*/*') != '*/*':
        formats = list(serializer.supported_formats) or []
        # Reverse the list, because mimeparse is weird like that. See also
        # https://github.com/toastdriven/django-tastypie/issues#issue/12 for
        # more information.
        formats.reverse()
        best_format = mimeparse.best_match(
            formats, request.META['HTTP_ACCEPT'])

        if best_format:
            return best_format

    # No valid 'Accept' header/formats. Sane default.
    return default_format


def build_content_type(fmt, encoding='utf-8'):
    """
    Appends character encoding to the provided format if not already present.
    """
    if 'charset' in fmt:
        return fmt

    return "%s; charset=%s" % (fmt, encoding)

########NEW FILE########
__FILENAME__ = timezone
import datetime
from django.conf import settings

__all__ = ('make_aware', 'make_naive', 'now', 'aware_date', 'aware_datetime',)


try:
    from django.utils import timezone

    def make_aware(value):
        if getattr(settings, "USE_TZ", False) and timezone.is_naive(value):
            default_tz = timezone.get_default_timezone()
            value = timezone.make_aware(value, default_tz)
        return value

    def make_naive(value):
        if getattr(settings, "USE_TZ", False) and timezone.is_aware(value):
            default_tz = timezone.get_default_timezone()
            value = timezone.make_naive(value, default_tz)
        return value

    def now():
        localtime = getattr(timezone, "template_localtime", timezone.localtime)
        return localtime(timezone.now())

except ImportError:
    now = datetime.datetime.now
    make_aware = make_naive = lambda x: x

def aware_date(*args, **kwargs):
    return make_aware(datetime.date(*args, **kwargs))

def aware_datetime(*args, **kwargs):
    return make_aware(datetime.datetime(*args, **kwargs))

########NEW FILE########
__FILENAME__ = validate_jsonp
# -*- coding: utf-8 -*-

# Placed into the Public Domain by tav <tav@espians.com>

"""Validate Javascript Identifiers for use as JSON-P callback parameters."""

import re
from unicodedata import category

__all__ = ('is_valid_jsonp_callback_value',)


# ------------------------------------------------------------------------------
# javascript identifier unicode categories and "exceptional" chars
# ------------------------------------------------------------------------------

valid_jsid_categories_start = frozenset([
    'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl'
    ])

valid_jsid_categories = frozenset([
    'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl', 'Mn', 'Mc', 'Nd', 'Pc'
    ])

valid_jsid_chars = ('$', '_')

# ------------------------------------------------------------------------------
# regex to find array[index] patterns
# ------------------------------------------------------------------------------

array_index_regex = re.compile(r'\[[0-9]+\]$')

has_valid_array_index = array_index_regex.search
replace_array_index = array_index_regex.sub

# ------------------------------------------------------------------------------
# javascript reserved words -- including keywords and null/boolean literals
# ------------------------------------------------------------------------------

is_reserved_js_word = frozenset([

    'abstract', 'boolean', 'break', 'byte', 'case', 'catch', 'char', 'class',
    'const', 'continue', 'debugger', 'default', 'delete', 'do', 'double',
    'else', 'enum', 'export', 'extends', 'false', 'final', 'finally', 'float',
    'for', 'function', 'goto', 'if', 'implements', 'import', 'in', 'instanceof',
    'int', 'interface', 'long', 'native', 'new', 'null', 'package', 'private',
    'protected', 'public', 'return', 'short', 'static', 'super', 'switch',
    'synchronized', 'this', 'throw', 'throws', 'transient', 'true', 'try',
    'typeof', 'var', 'void', 'volatile', 'while', 'with',

    # potentially reserved in a future version of the ES5 standard
    # 'let', 'yield'

    ]).__contains__

# ------------------------------------------------------------------------------
# the core validation functions
# ------------------------------------------------------------------------------

def is_valid_javascript_identifier(identifier, escape=r'\u', ucd_cat=category):
    """Return whether the given ``id`` is a valid Javascript identifier."""

    if not identifier:
        return False

    if not isinstance(identifier, unicode):
        try:
            identifier = unicode(identifier, 'utf-8')
        except UnicodeDecodeError:
            return False

    if escape in identifier:

        new = []; add_char = new.append
        split_id = identifier.split(escape)
        add_char(split_id.pop(0))

        for segment in split_id:
            if len(segment) < 4:
                return False
            try:
                add_char(unichr(int('0x' + segment[:4], 16)))
            except Exception:
                return False
            add_char(segment[4:])

        identifier = u''.join(new)

    if is_reserved_js_word(identifier):
        return False

    first_char = identifier[0]

    if not ((first_char in valid_jsid_chars) or
            (ucd_cat(first_char) in valid_jsid_categories_start)):
        return False

    for char in identifier[1:]:
        if not ((char in valid_jsid_chars) or
                (ucd_cat(char) in valid_jsid_categories)):
            return False

    return True


def is_valid_jsonp_callback_value(value):
    """Return whether the given ``value`` can be used as a JSON-P callback."""

    for identifier in value.split(u'.'):
        while '[' in identifier:
            if not has_valid_array_index(identifier):
                return False
            identifier = replace_array_index(u'', identifier)
        if not is_valid_javascript_identifier(identifier):
            return False

    return True

# ------------------------------------------------------------------------------
# test
# ------------------------------------------------------------------------------

def test():
    """
    The function ``is_valid_javascript_identifier`` validates a given identifier
    according to the latest draft of the ECMAScript 5 Specification:

      >>> is_valid_javascript_identifier('hello')
      True

      >>> is_valid_javascript_identifier('alert()')
      False

      >>> is_valid_javascript_identifier('a-b')
      False

      >>> is_valid_javascript_identifier('23foo')
      False

      >>> is_valid_javascript_identifier('foo23')
      True

      >>> is_valid_javascript_identifier('$210')
      True

      >>> is_valid_javascript_identifier(u'Stra\u00dfe')
      True

      >>> is_valid_javascript_identifier(r'\u0062') # u'b'
      True

      >>> is_valid_javascript_identifier(r'\u62')
      False

      >>> is_valid_javascript_identifier(r'\u0020')
      False

      >>> is_valid_javascript_identifier('_bar')
      True

      >>> is_valid_javascript_identifier('some_var')
      True

      >>> is_valid_javascript_identifier('$')
      True

    But ``is_valid_jsonp_callback_value`` is the function you want to use for
    validating JSON-P callback parameter values:

      >>> is_valid_jsonp_callback_value('somevar')
      True

      >>> is_valid_jsonp_callback_value('function')
      False

      >>> is_valid_jsonp_callback_value(' somevar')
      False

    It supports the possibility of '.' being present in the callback name, e.g.

      >>> is_valid_jsonp_callback_value('$.ajaxHandler')
      True

      >>> is_valid_jsonp_callback_value('$.23')
      False

    As well as the pattern of providing an array index lookup, e.g.

      >>> is_valid_jsonp_callback_value('array_of_functions[42]')
      True

      >>> is_valid_jsonp_callback_value('array_of_functions[42][1]')
      True

      >>> is_valid_jsonp_callback_value('$.ajaxHandler[42][1].foo')
      True

      >>> is_valid_jsonp_callback_value('array_of_functions[42]foo[1]')
      False

      >>> is_valid_jsonp_callback_value('array_of_functions[]')
      False

      >>> is_valid_jsonp_callback_value('array_of_functions["key"]')
      False

    Enjoy!

    """

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = entities
from django.db import models

from delicious_cake import fields
from delicious_cake.entities import Entity

from cake.models import Cake

__all__ = ('CakeListEntity', 'CakeDetailEntity', 'CakePointListEntity',)


class CakeEntity(Entity):
    @models.permalink
    def get_resource_uri(self):
        return ('cake-detail', (self.obj.pk,))


class CakeListEntity(CakeEntity):
    CAKE_TYPE_CHOICES_LOOKUP = dict(Cake.CAKE_TYPE_CHOICES)

    resource_id = fields.IntegerField(attr='pk')
    cake_type = fields.CharField()

    def process_cake_type(self, cake_type):
        return self.CAKE_TYPE_CHOICES_LOOKUP.get(cake_type, 'Unknown')


class PointEntity(Entity):
    x = fields.IntegerField()
    y = fields.IntegerField()


class CakePointListEntity(CakeListEntity):
    point = fields.EntityField(entity_cls=PointEntity)
    points = fields.EntityListField(entity_cls=PointEntity)


class CakeDetailEntity(CakeListEntity):
    message = fields.CharField()


########NEW FILE########
__FILENAME__ = forms
from django import forms

from cake.models import Cake


class CakeForm(forms.ModelForm):
    id = forms.IntegerField(required=False)
    message = forms.CharField(max_length=128)
    cake_type = forms.TypedChoiceField(
        choices=Cake.CAKE_TYPE_CHOICES, coerce=int)

    class Meta(object):
        model = Cake

########NEW FILE########
__FILENAME__ = models
from collections import namedtuple

from django.db import models
from django.utils.timezone import now


__all__ = ('Cake',)


Point = namedtuple('Point', ['x', 'y', 'parrot'])


class Cake(models.Model):
    CAKE_TYPE_BIRTHDAY = 1
    CAKE_TYPE_GRADUATION = 2
    CAKE_TYPE_SCHADENFREUDE = 3

    CAKE_TYPE_CHOICES = (
        (CAKE_TYPE_BIRTHDAY, u'Birthday Cake',),
        (CAKE_TYPE_GRADUATION, u'Graduation Cake',),
        (CAKE_TYPE_SCHADENFREUDE, u'Shameful Pride Cake',),)

    point = Point(x=42, y=7, parrot=u'Norwegian Blue')

    points = [Point(x=42, y=7, parrot=u'Norwegian Blue'),
              Point(x=8, y=8, parrot=u'Hegemony')]

    message = models.CharField(max_length=128)
    cake_type = models.PositiveSmallIntegerField(db_index=True)

########NEW FILE########
__FILENAME__ = resources
from collections import namedtuple

from django.db import models
from django.shortcuts import get_object_or_404

from delicious_cake import http
from delicious_cake.resources import (
    ListResource, DetailResource, ResourceResponse, MultipartResource,)
from delicious_cake.exceptions import ValidationError

from cake.models import Cake
from cake.forms import CakeForm
from cake.entities import CakeListEntity, CakeDetailEntity, CakePointListEntity

__all__ = ('CakeDetailResource', 'CakeListResource', 'CakeListResourceExtra',
           'CakePointListResource')


class CakeListResource(ListResource):
    '''A simple list view'''
    def get(self, request, *args, **kwargs):
        return Cake.objects.all()

    def head(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        cake_form = CakeForm(request.DATA)

        if not cake_form.is_valid():
            raise ValidationError(cake_form.errors)

        # Return the newly created instance and indicate that 
        # HTTP 201 CREATED should be used in the response.

        # return object, created (boolean)
        return cake_form.save(), True

    def delete(self, request, *args, **kwargs):
        Cake.objects.all().delete()

    # Used to get the base uri when paginating.   
    @models.permalink
    def get_resource_uri(self):
        return ('cake-list',)

    class Meta(object):
        # See delicious_cake/options.py for more 'Resource' options.

        # 'Entity' classes are used to pre-process objects before 
        # serialization.        

        # The 'list_entity_cls' will be used to pre-process the returned 
        # objects when viewed as a list.
        list_entity_cls = CakeListEntity

        # The 'detail_entity_cls' will be used to pre-process the returned 
        # objects when returned individually.        
        detail_entity_cls = CakeDetailEntity

        # If the same representation of the object is used in both list and 
        # details views the 'entity_cls' option can be used
        # (e.g.  entity_cls = CakeDetailEntity) 


class CakeDetailResource(DetailResource):
    '''A simple detail view'''
    def get(self, request, *args, **kwargs):
        return get_object_or_404(Cake, pk=kwargs['pk'])

    def put(self, request, *args, **kwargs):
        pk = kwargs['pk']

        try:
            created = False
            instance = Cake.objects.get(pk=pk)
        except Cake.DoesNotExist:
            created = True
            instance = Cake(id=pk)

        cake_form = CakeForm(request.DATA, instance=instance)

        if not cake_form.is_valid():
            raise ValidationError(cake_form.errors)

        # Return the newly created instance and indicate that 
        # HTTP 201 CREATED should be used in the response.
        # OR
        # Return the updated instance with HTTP 200 OK
        return cake_form.save(), created

    def delete(self, request, *args, **kwargs):
        get_object_or_404(Cake, pk=kwargs['pk']).delete()

    def head(self, request, *args, **kwargs):
        return self.get(self, request, *args, **kwargs)

    class Meta(object):
        detail_entity_cls = CakeDetailEntity


class CakeListResourceExtra(ListResource):
    # Add a response header to all responses.
    def process_http_response(self, http_response, entities):
        http_response['X-The-Cake-Is-A-Lie'] = False

    # Add a response header to all GET responses.
    def process_http_response_get(self, http_response, entities):
        http_response['X-Cake-Count'] = len(entities)

    def get(self, request, *args, **kwargs):
        # Tell the resource to use the 'CakeDetailEntity' instead of the 
        # default ('CakeListEntity' in this case) by specifying 'entity_cls'.
        return ResourceResponse(
           Cake.objects.all(), entity_cls=CakeDetailEntity)

    def post(self, request, *args, **kwargs):
        cake_form = CakeForm(request.DATA)

        if not cake_form.is_valid():
            raise ValidationError(cake_form.errors)

        cake = cake_form.save()

        # You can return 'ResourceResponse's if you need to 
        # use a custom 'HttpResponse' class or pass in specific parameters to 
        # the 'HttpResponse' class's constructor.  

        # For example, in this method we want to return an HTTP 201 (CREATED) 
        # response, with the newly created cake's uri in 'Location' header.  
        # To do this we set the 'response_cls' argument to 'http.HttpCreated' 
        # and add a 'location' key to 'response_kwargs' dict.  

        # This is equilivant to returning "cake_form.save(), created"

        # In this case, the value passed into the location parameter of our 
        # 'HttpCreated' response will be  a callable.  When invoked it will be 
        # passed one parameter, the entity created from our cake object.

        # And, just for fun, let's set 'include_entity' to False.

        # So again, we'll return HTTP 201 (CREATED), with a Location header,
        # the X-The-Cake-Is-A-Lie header, and no entity body.

        return ResourceResponse(
            include_entity=False,
            response_cls=http.HttpAccepted,
            response_kwargs={
                'location': lambda entity: entity.get_resource_uri()})

    @models.permalink
    def get_resource_uri(self):
        return ('cake-list-extra',)

    class Meta(object):
        entity_cls = CakeListEntity


class CakePointListResource(ListResource):
    def get(self, request, *args, **kwargs):
        return Cake.objects.all()

    @models.permalink
    def get_resource_uri(self):
        return ('cake-list-point',)

    class Meta(object):
        entity_cls = CakePointListEntity


class CakeUploadResource(MultipartResource):
    def post(self, request, *args, **kwargs):
        cake_form = CakeForm(request.DATA)

        if not cake_form.is_valid():
            raise ValidationError(cake_form.errors)

        cake = cake_form.save()

        return cake, True

    @models.permalink
    def get_resource_uri(self):
        return ('cake-upload',)

    class Meta(object):
        entity_cls = CakeListEntity

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from .resources import (
    CakeListResource, CakeDetailResource, CakeListResourceExtra,
    CakeUploadResource, CakePointListResource,)


urlpatterns = patterns('',
    url(r'^cake/(?P<pk>\d+)/$', CakeDetailResource.as_view(),
        name='cake-detail'),
    url(r'^cake/$', CakeListResource.as_view(), name='cake-list'),
    url(r'^cake/extra/$', CakeListResourceExtra.as_view(),
        name='cake-list-extra'),
    url(r'^cake/point/$', CakePointListResource.as_view(),
        name='cake-list-point'),
    url(r'^cake/upload/$', CakeUploadResource.as_view(),
        name='cake-upload'),)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import os

ADMINS = (
    ('test@example.com', 'Mr. Test'),)

BASE_PATH = os.path.abspath(os.path.dirname(__file__))

MEDIA_ROOT = os.path.normpath(os.path.join(BASE_PATH, 'media'))

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'delicious_cake.db'
TEST_DATABASE_NAME = 'delicious-cake-test.db'

# for forwards compatibility
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.%s' % DATABASE_ENGINE,
        'NAME': DATABASE_NAME,
        'TEST_NAME': TEST_DATABASE_NAME}}


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'delicious_cake',
    'cake',)

DEBUG = True
TEMPLATE_DEBUG = DEBUG
CACHE_BACKEND = 'locmem://'
SECRET_KEY = 'verysecret'

# to make sure timezones are handled correctly in Django>=1.4
USE_TZ = True

ROOT_URLCONF = 'cake.urls'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = cake
import datetime

from django.db import models

from delicious_cake import fields
from delicious_cake.entities import Entity

from core.models import Cake

__all__ = ('CakeListEntity', 'CakeDetailEntity')


class CakeEntity(Entity):
    @models.permalink
    def get_resource_uri(self):
        return ('simple-detail', (self.obj.pk,))


class CakeDeleteEntity(Entity):
    message = fields.CharField()

    def process_message(self, processed_data):
        return u'DELETED:  %s' % processed_data['cake']


class CakeListEntity(CakeEntity):
    CAKE_TYPE_CHOICES_LOOKUP = dict(Cake.CAKE_TYPE_CHOICES)

    resource_id = fields.IntegerField(attr='pk')
    cake_type = fields.CharField(attr='cake_type')

    def process_cake_type(self, cake_type):
        return self.CAKE_TYPE_CHOICES_LOOKUP.get(cake_type, 'Unknown')


class CakeDetailEntity(CakeListEntity):
    message = fields.CharField()

########NEW FILE########
__FILENAME__ = forms
from django import forms

from core.models import Cake


class CakeForm(forms.Form):
    message = forms.CharField(max_length=128)
    cake_type = forms.TypedChoiceField(
        choices=Cake.CAKE_TYPE_CHOICES, coerce=int)


class CakeUploadForm(forms.Form):
    cake_pattern = forms.FileField()

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.timezone import now

class TimeClass(object):
    @property
    def time(self):
        return now()


class Cake(models.Model):
    CAKE_TYPE_BIRTHDAY = 1
    CAKE_TYPE_GRADUATION = 2
    CAKE_TYPE_SCHADENFREUDE = 3

    CAKE_TYPE_CHOICES = (
        (CAKE_TYPE_BIRTHDAY, u'Birthday Cake',),
        (CAKE_TYPE_GRADUATION, u'Graduation Cake',),
        (CAKE_TYPE_SCHADENFREUDE, u'Shameful Pride Cake',),)

    message = models.CharField(max_length=128)
    cake_type = models.PositiveSmallIntegerField(db_index=True)

    def __init__(self, *args, **kwargs):
        self.nested_time = TimeClass()
        super(Cake, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = resource_base
import collections

from django.shortcuts import get_object_or_404

from delicious_cake.resources import (
    ListResource, DetailResource, ResourceResponse,)

from core.models import Cake
from core.forms import CakeForm

__all__ = ('BaseResourceMixin', 'BaseDetailResource', 'BaseListResource',)


class BaseResourceMixin(object):
    def get_obj(self, request, *args, **kwargs):
        return get_object_or_404(Cake, pk=kwargs['pk'])

    def _update_obj(self, obj, data, custom_pk=None):
        if custom_pk is not None:
            obj.pk = custom_pk

        obj.message = data['message']
        obj.cake_type = data['cake_type']

        obj.save()

        return obj

    def update_obj(self, obj, request, custom_pk=None, *args, **kwargs):
        cake_form = CakeForm(request.DATA)

        if cake_form.is_valid():
            return self._update_obj(
                obj, cake_form.cleaned_data, custom_pk=custom_pk)
        else:
            self.raise_validation_error(request, cake_form.errors)

    def _create_obj(self, request, *args, **kwargs):
        cake = Cake()
        self.update_obj(cake, request, *args, **kwargs)

        return cake

    def create_obj(self, request, *args, **kwargs):
        cake = Cake()
        self.update_obj(cake, request, *args, **kwargs)

        return cake


class BaseDetailResource(DetailResource, BaseResourceMixin):
    def _get(self, request, *args, **kwargs):
        return self.get_obj(request, *args, **kwargs)

    def _post(self, request, *args, **kwargs):
        cake = self.create_obj(request, *args, **kwargs)
        return cake, True

    def _put(self, request, *args, **kwargs):
        pk = kwargs['pk']

        try:
            cake = Cake.objects.get(pk=pk)
            self.update_obj(cake, request, *args, **kwargs)
            created = False
        except Cake.DoesNotExist:
            created = True
            cake = self.create_obj(request, custom_pk=pk, *args, **kwargs)

        return cake, created

    def _delete(self, request, *args, **kwargs):
        cake = get_object_or_404(Cake, pk=kwargs['pk'])
        cake.delete()
        return cake

    def _head(self, request, *args, **kwargs):
        return self._get(request, *args, **kwargs)


class BaseListResource(ListResource, BaseResourceMixin):
    def _get(self, request, *args, **kwargs):
        return Cake.objects.all()

    def _head(self, request, *args, **kwargs):
        return self._get(request, *args, **kwargs)

    def _put(self, request, *args, **kwargs):
        data = request.DATA

        if not isinstance(data, list):
            self.raise_http_error(request, 'Must be a list')

        cake_forms = []

        for cake in data:
            cake_form = CakeForm(cake)

            if not cake_form.is_valid():
                self.raise_http_error(request, 'Invalid Cake')

            cake_forms.append(cake_form)

        # Delete Old List
        Cake.objects.all().delete()

        # Create New List
        cakes = [self._update_obj(Cake(), cake_form.cleaned_data) \
                    for cake_form in cake_forms]

        return cakes

    def _post(self, request, *args, **kwargs):
        cake = self.create_obj(request, *args, **kwargs)
        return cake, True

    def _delete(self, request, *args, **kwargs):
        Cake.objects.all().delete()

########NEW FILE########
__FILENAME__ = resource_custom_create
from django.db import models

from delicious_cake.http import HttpCreated
from delicious_cake.response import ResourceResponse

from core.entities import CakeDetailEntity, CakeListEntity
from core.resources import BaseListResource, BaseDetailResource

__all__ = ('CustomCreateListResource',)


class CustomCreateListResource(BaseDetailResource):
    def post(self, request, *args, **kwargs):
        cake = self.create_obj(request, *args, **kwargs)

        return ResourceResponse(
            cake, response_cls=HttpCreated,
            response_kwargs={
                'location': lambda entity: entity.get_resource_uri()})

    class Meta(object):
        detail_entity_cls = CakeDetailEntity

########NEW FILE########
__FILENAME__ = resource_custom_entity
from django.db import models

from delicious_cake.response import ResourceResponse

from core.entities import CakeDetailEntity, CakeListEntity
from core.resources import BaseListResource, BaseDetailResource

__all__ = ('CustomEntityDetailResource', 'CustomEntityListResource',)


class CustomEntityDetailResource(BaseDetailResource):
    def get(self, request, *args, **kwargs):
        return ResourceResponse(
            self._get(request, *args, **kwargs), entity_cls=CakeDetailEntity)

    def head(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        cake, created = self._post(request, *args, **kwargs)
        return ResourceResponse(cake, entity_cls=CakeDetailEntity), created

    def put(self, request, *args, **kwargs):
        cake, created = self._put(request, *args, **kwargs)
        return ResourceResponse(cake, entity_cls=CakeDetailEntity), created

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    class Meta(object):
        include_entity = True


class CustomEntityListResource(BaseListResource):
    def get(self, request, *args, **kwargs):
        return ResourceResponse(
            self._get(request, *args, **kwargs), entity_cls=CakeListEntity)

    def head(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return ResourceResponse(
            self.create_obj(
                request, *args, **kwargs), entity_cls=CakeDetailEntity), True

    def put(self, request, *args, **kwargs):
        return ResourceResponse(
            self._put(request, *args, **kwargs), entity_cls=CakeDetailEntity)

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    @models.permalink
    def get_resource_uri(self):
        return ('custom-entity-list',)

    class Meta(object):
        include_entity = True

########NEW FILE########
__FILENAME__ = resource_empty
from delicious_cake.response import ResourceResponse

from core.entities import CakeListEntity, CakeDetailEntity
from core.resources import BaseDetailResource, BaseListResource

__all__ = ('EmptyDetailResource', 'EmptyListResource',)


class EmptyDetailResource(BaseDetailResource):
    def get(self, request, *args, **kwargs):
        self._get(request, *args, **kwargs)

    def head(self, request, *args, **kwargs):
        self._head(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._post(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        self._put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    class Meta(object):
        include_entity = False


class EmptyListResource(BaseListResource):
    def get(self, request, *args, **kwargs):
        self._get(request, *args, **kwargs)

    def head(self, request, *args, **kwargs):
        self._head(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._post(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        self._put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    class Meta(object):
        include_entity = False

########NEW FILE########
__FILENAME__ = resource_simple
from django.db import models

import delicious_cake.http as cake_http

from delicious_cake.response import ResourceResponse

from delicious_cake.throttle import CacheDBThrottle
from delicious_cake.authentication import (
    BasicAuthentication, MultiAuthentication, ApiKeyAuthentication,)

from core.entities import CakeDetailEntity, CakeListEntity
from core.resources import BaseListResource, BaseDetailResource

__all__ = ('SimpleDetailResource', 'SimpleListResource',
           'BareSimpleListResource', 'BareSimpleDetailResource',
           'ForcedSimpleDetailResource', 'ForcedSimpleListResource',)


class SimpleDetailResource(BaseDetailResource):
    def get(self, request, *args, **kwargs):
        return ResourceResponse(self._get(request, *args, **kwargs))

    def head(self, request, *args, **kwargs):
        return ResourceResponse(self._head(request, *args, **kwargs))

    def post(self, request, *args, **kwargs):
        cake, created = self._post(request, *args, **kwargs)
        return ResourceResponse(cake), created

    def put(self, request, *args, **kwargs):
        cake, created = self._put(request, *args, **kwargs)
        return ResourceResponse(cake), created

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    class Meta(object):
        include_entity = True
        detail_entity_cls = CakeDetailEntity


class SimpleListResource(BaseListResource):
    def get(self, request, *args, **kwargs):
        return ResourceResponse(self._get(request, *args, **kwargs))

    def head(self, request, *args, **kwargs):
        return ResourceResponse(self._head(request, *args, **kwargs))

    def post(self, request, *args, **kwargs):
        return ResourceResponse(
            self.create_obj(request, *args, **kwargs)), True

    def put(self, request, *args, **kwargs):
        return ResourceResponse(self._put(request, *args, **kwargs))

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    @models.permalink
    def get_resource_uri(self):
        return ('simple-list',)

    class Meta(object):
        include_entity = True
        list_entity_cls = CakeListEntity
        detail_entity_cls = CakeDetailEntity

#        authentication = MultiAuthentication(
#            BasicAuthentication(), ApiKeyAuthentication())
#        throttle = CacheDBThrottle(throttle_at=1, timeframe=5)

class ForcedSimpleDetailResource(BaseDetailResource):
    def get(self, request, *args, **kwargs):
        return ResourceResponse(
            self._get(request, *args, **kwargs), include_entity=True)

    def head(self, request, *args, **kwargs):
        return ResourceResponse(
            self._head(request, *args, **kwargs), include_entity=True)

    def post(self, request, *args, **kwargs):
        cake, created = self._post(request, *args, **kwargs)
        return ResourceResponse(cake, include_entity=True), created

    def put(self, request, *args, **kwargs):
        cake, created = self._put(request, *args, **kwargs)
        return ResourceResponse(cake, include_entity=True), created

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    class Meta(object):
        include_entity = False
        detail_entity_cls = CakeDetailEntity


class ForcedSimpleListResource(BaseListResource):
    def get(self, request, *args, **kwargs):
        return ResourceResponse(
            self._get(request, *args, **kwargs), include_entity=True)

    def head(self, request, *args, **kwargs):
        return ResourceResponse(
            self._head(request, *args, **kwargs), include_entity=True)

    def post(self, request, *args, **kwargs):
        return ResourceResponse(
            self.create_obj(
                request, *args, **kwargs), include_entity=True), True

    def put(self, request, *args, **kwargs):
        return ResourceResponse(
            self._put(request, *args, **kwargs), include_entity=True)

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    @models.permalink
    def get_resource_uri(self):
        return ('forced-simple-list',)

    class Meta(object):
        include_entity = False
        list_entity_cls = CakeListEntity
        detail_entity_cls = CakeDetailEntity


class BareSimpleDetailResource(BaseDetailResource):
    def get(self, request, *args, **kwargs):
        return self._get(request, *args, **kwargs)

    def head(self, request, *args, **kwargs):
        return self._head(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._post(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self._put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    class Meta(object):
        include_entity = True
        detail_entity_cls = CakeDetailEntity


class BareSimpleListResource(BaseListResource):
    def get(self, request, *args, **kwargs):
        return self._get(request, *args, **kwargs)

    def head(self, request, *args, **kwargs):
        return self._head(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create_obj(request, *args, **kwargs), True

    def put(self, request, *args, **kwargs):
        self._put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self._delete(request, *args, **kwargs)

    @models.permalink
    def get_resource_uri(self):
        return ('bare-simple-list',)

    class Meta(object):
        include_entity = True
        list_entity_cls = CakeListEntity
        detail_entity_cls = CakeDetailEntity

########NEW FILE########
__FILENAME__ = resource_unimplemented
from core.entities import CakeListEntity, CakeDetailEntity
from core.resources import BaseDetailResource, BaseListResource

__all__ = ('UnimplementedDetailResource', 'UnimplementedListResource',)


class UnimplementedDetailResource(BaseDetailResource):
    class Meta(object):
        include_entity = False
        entity_cls = CakeDetailEntity


class UnimplementedListResource(BaseListResource):
    class Meta(object):
        include_entity = False
        entity_cls = CakeListEntity

########NEW FILE########
__FILENAME__ = resource_upload
from delicious_cake import fields
from delicious_cake.entities import Entity
from delicious_cake.resources import MultipartResource
from delicious_cake.response import ResourceResponse

from core.forms import CakeUploadForm

__all__ = ('CakeUploadResource',)


class CakeUploadResource(MultipartResource):
    def _put_post(self, request, *args, **kwargs):
        cake_form = CakeUploadForm(files=request.FILES)

        if not cake_form.is_valid():
            self.raise_validation_error(request, cake_form.errors)

    def post(self, request, *args, **kwargs):
        return self._put_post(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self._put_post(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = test_resource_base
from django.http import HttpRequest

from delicious_cake.resources import Resource
from delicious_cake.test import ResourceTestCase

from core.models import Cake
from core.entities import CakeListEntity, CakeDetailEntity

from core.resources import (
    UnimplementedListResource, UnimplementedDetailResource,
    SimpleListResource,)

__all__ = ('BaseResourceTestCase',)


BIRTHDAY_MESSAGE = u"You're another year closer to death!"


class BaseResourceTestCase(ResourceTestCase):
    fixtures = ['test_data.json']

    def test_determine_format(self):
        request = HttpRequest()
        resource = UnimplementedDetailResource()

        # Default.
        self.assertEqual(
            resource.determine_format(request), 'application/json')

        # Test forcing the ``format`` parameter.
        request.GET = {'format': 'json'}
        self.assertEqual(
            resource.determine_format(request), 'application/json')

        request.GET = {'format': 'jsonp'}
        self.assertEqual(resource.determine_format(request), 'text/javascript')

        request.GET = {'format': 'xml'}
        self.assertEqual(resource.determine_format(request), 'application/xml')

        request.GET = {'format': 'yaml'}
        self.assertEqual(resource.determine_format(request), 'text/yaml')

        request.GET = {'format': 'foo'}
        self.assertEqual(
            resource.determine_format(request), 'application/json')

        # Test the ``Accept`` header.
        request.META = {'HTTP_ACCEPT': 'application/json'}
        self.assertEqual(
            resource.determine_format(request), 'application/json')

        request.META = {'HTTP_ACCEPT': 'text/javascript'}
        self.assertEqual(resource.determine_format(request), 'text/javascript')

        request.META = {'HTTP_ACCEPT': 'application/xml'}
        self.assertEqual(resource.determine_format(request), 'application/xml')

        request.META = {'HTTP_ACCEPT': 'text/yaml'}
        self.assertEqual(resource.determine_format(request), 'text/yaml')

        request.META = {'HTTP_ACCEPT': 'text/html'}
        self.assertEqual(resource.determine_format(request), 'text/html')

        request.META = {
            'HTTP_ACCEPT': 'application/json,application/xml;q=0.9,*/*;q=0.8'}
        self.assertEqual(
            resource.determine_format(request), 'application/json')

        request.META = {
            'HTTP_ACCEPT': \
                'text/plain,application/xml,application/json;q=0.9,*/*;q=0.8'}
        self.assertEqual(resource.determine_format(request), 'application/xml')

    def test_jsonp_validation(self):
        resp = self.api_client.get('/simple/1/?format=jsonp&callback=()')

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content, 'JSONP callback name is invalid.')

        # valid JSONP callback should work
        resp = self.api_client.get(
            '/simple/1/?format=jsonp&callback=myCallback')

        self.assertEqual(resp.status_code, 200)

    def test_get_entity_cls(self):
        simple_list_resource = SimpleListResource()
        un_list_resource = UnimplementedListResource()
        un_detail_resource = UnimplementedDetailResource()

        self.assertEqual(
            CakeListEntity, simple_list_resource._meta.get_list_entity_cls())
        self.assertEqual(
            CakeDetailEntity,
            simple_list_resource._meta.get_detail_entity_cls())

        self.assertEqual(
            CakeDetailEntity, un_detail_resource._meta.get_detail_entity_cls())

        self.assertEqual(
            CakeListEntity, un_list_resource._meta.get_list_entity_cls())
        self.assertEqual(
            CakeListEntity, un_list_resource._meta.get_detail_entity_cls())


########NEW FILE########
__FILENAME__ = test_resource_empty
from delicious_cake.test import ResourceTestCase

from core.models import Cake

__all__ = ('EmptyResourceTestCase',)


BIRTHDAY_MESSAGE = u"You're another year closer to death!"


class EmptyResourceTestCase(ResourceTestCase):
    fixtures = ['test_data.json']

    def test_empty_detail_resource(self):
        # Test GET
        response = self.api_client.get('/empty/1/')
        self.assertHttpNoContent(response)

        # Test GET 404
        response = self.api_client.get('/empty/404/')
        self.assertHttpNotFound(response)

        # Test HEAD
        response = self.api_client.head('/empty/1/')
        self.assertHttpNoContent(response)

        #### POST ####
        response = self.api_client.post('/empty/2/', data={
            'cake_type': Cake.CAKE_TYPE_BIRTHDAY, 'message': BIRTHDAY_MESSAGE})
        self.assertHttpNoContent(response)

        # Test Bad POST
        response = self.api_client.post('/empty/2/', data={
            'ct': Cake.CAKE_TYPE_BIRTHDAY, 'm': BIRTHDAY_MESSAGE})
        self.assertHttpBadRequest(response)

        # Test PUT update
        cake = Cake.objects.get(pk=3)
        self.assertEquals(cake.message, u'Cake 3')

        response = self.api_client.put('/empty/3/', data={
            'cake_type': Cake.CAKE_TYPE_BIRTHDAY, 'message': BIRTHDAY_MESSAGE})

        cake = Cake.objects.get(pk=3)

        self.assertEquals(cake.message, BIRTHDAY_MESSAGE)

        # Test PUT create
        response = self.api_client.put('/empty/100000/', data={
            'cake_type': Cake.CAKE_TYPE_BIRTHDAY, 'message': BIRTHDAY_MESSAGE})
        self.assertHttpNoContent(response)

        response = self.api_client.get('/empty/100000/')
        self.assertHttpNoContent(response)

        # Test Bad PUT
        response = self.api_client.post('/empty/2/', data={
            'ct': Cake.CAKE_TYPE_BIRTHDAY, 'm': BIRTHDAY_MESSAGE})
        self.assertHttpBadRequest(response)

        # Test DELETE
        response = self.api_client.delete('/empty/100000/')
        self.assertHttpNoContent(response)

        # Test DELETE with 404
        response = self.api_client.delete('/empty/100000/')
        self.assertHttpNotFound(response)

    def test_empty_list_resource(self):
        # Test GET
        response = self.api_client.get('/empty/')
        self.assertHttpNoContent(response)

        # Test HEAD
        response = self.api_client.head('/empty/')
        self.assertHttpNoContent(response)

        # Test POST
        response = self.api_client.post('/empty/', data={
            'cake_type': Cake.CAKE_TYPE_BIRTHDAY, 'message': BIRTHDAY_MESSAGE})

        self.assertHttpNoContent(response)
        self.assertEqual(51, Cake.objects.all().count())

        # Test PUT
        data = [
            {'cake_type': Cake.CAKE_TYPE_BIRTHDAY,
                'message': BIRTHDAY_MESSAGE},
            {'cake_type': Cake.CAKE_TYPE_GRADUATION,
                'message': BIRTHDAY_MESSAGE},
            {'cake_type': Cake.CAKE_TYPE_SCHADENFREUDE,
                'message': BIRTHDAY_MESSAGE}]

        response = self.api_client.put('/empty/', data=data)

        self.assertHttpNoContent(response)
        self.assertEqual(3, Cake.objects.all().count())

        # Test Delete
        response = self.api_client.delete('/empty/')

        self.assertHttpNoContent(response)
        self.assertEqual(0, Cake.objects.all().count())

########NEW FILE########
__FILENAME__ = test_resource_simple
from delicious_cake.test import ResourceTestCase

from core.models import Cake

__all__ = ('SimpleResourceTestCase',)


BIRTHDAY_MESSAGE = u"You're another year closer to death!"


class SimpleResourceTestCase(ResourceTestCase):
    fixtures = ['test_data.json']

    simple_detail_get_entity = {
        'resource_uri': u'/simple/1/',
        'message': u'Cake 1',
        'cake_type': u'Birthday Cake',
        'resource_id': 1}

    def _test_detail_resource(self, resource):
        # Test GET
        response = self.api_client.get('/%s/1/' % resource)
        self.assertHttpOK(response)

        self.assertEqual(
            self.simple_detail_get_entity, self.deserialize(response))

        # Test GET 404
        response = self.api_client.get('/%s/404/' % resource)
        self.assertHttpNotFound(response)

        # Test HEAD
        response = self.api_client.head('/%s/1/' % resource)
        self.assertHttpOK(response)

        #### POST ####
        response = self.api_client.post('/%s/2/' % resource, data={
            'cake_type': Cake.CAKE_TYPE_BIRTHDAY, 'message': BIRTHDAY_MESSAGE})
        self.assertHttpCreated(response)

        entity = self.deserialize(response)

        self.assertEqual(BIRTHDAY_MESSAGE, entity['message'])

        self.assertTrue(
            response['Location'].endswith(entity['resource_uri']))

        # Test Bad POST
        response = self.api_client.post('/%s/2/' % resource, data={
            'ct': Cake.CAKE_TYPE_BIRTHDAY, 'm': BIRTHDAY_MESSAGE})
        self.assertHttpBadRequest(response)

        # Test PUT update
        cake = Cake.objects.get(pk=3)
        self.assertEquals(cake.message, u'Cake 3')

        response = self.api_client.put('/%s/3/' % resource, data={
            'cake_type': Cake.CAKE_TYPE_BIRTHDAY, 'message': BIRTHDAY_MESSAGE})

        cake = Cake.objects.get(pk=3)

        self.assertEquals(cake.message, BIRTHDAY_MESSAGE)

        # Test PUT create
        response = self.api_client.put('/%s/100000/' % resource, data={
            'cake_type': Cake.CAKE_TYPE_BIRTHDAY, 'message': BIRTHDAY_MESSAGE})

        self.assertHttpCreated(response)

        response = self.api_client.get('/%s/100000/' % resource)
        self.assertHttpOK(response)

        # Test Bad PUT
        response = self.api_client.post('/%s/2/' % resource, data={
            'ct': Cake.CAKE_TYPE_BIRTHDAY, 'm': BIRTHDAY_MESSAGE})
        self.assertHttpBadRequest(response)

        # Test DELETE
        response = self.api_client.delete('/%s/100000/' % resource)
        self.assertHttpNoContent(response)

        # Test DELETE with 404
        response = self.api_client.delete('/%s/100000/' % resource)
        self.assertHttpNotFound(response)

        # Test DELETE with entity in response

    def _test_list_resource(self, resource):
        # Test GET
        response = self.api_client.get('/%s/' % resource)

        self.assertHttpOK(response)
        self.assertEqual(20, len(self.deserialize(response)['objects']))

        # Test HEAD
        response = self.api_client.head('/%s/' % resource)
        self.assertHttpOK(response)

        # Test POST
        response = self.api_client.post('/%s/' % resource, data={
            'cake_type': Cake.CAKE_TYPE_BIRTHDAY, 'message': BIRTHDAY_MESSAGE})

        self.assertHttpCreated(response)

        # Test PUT
        data = [
            {'cake_type': Cake.CAKE_TYPE_BIRTHDAY,
                'message': BIRTHDAY_MESSAGE},
            {'cake_type': Cake.CAKE_TYPE_GRADUATION,
                'message': BIRTHDAY_MESSAGE},
            {'cake_type': Cake.CAKE_TYPE_SCHADENFREUDE,
                'message': BIRTHDAY_MESSAGE}]

        response = self.api_client.put('/%s/' % resource, data=data)

        self.assertHttpOK(response)

        response = self.api_client.get('/%s/' % resource)

        self.assertHttpOK(response)
        self.assertEqual(3, len(self.deserialize(response)['objects']))

        # Test Delete
        response = self.api_client.delete('/%s/' % resource)
        self.assertHttpNoContent(response)

        response = self.api_client.get('/%s/' % resource)

        self.assertHttpOK(response)
        self.assertEqual(0, len(self.deserialize(response)['objects']))

    def test_simple_detail_resource(self):
        self._test_detail_resource('simple')

    def test_simple_list_resource(self):
        self._test_list_resource('simple')

    def test_forced_simple_detail_resource(self):
        self._test_detail_resource('forced/simple')

    def test_forced_simple_list_resource(self):
        self._test_list_resource('forced/simple')

    def test_bare_simple_detail_resource(self):
        self._test_detail_resource('bare/simple')

    def test_bare_simple_list_resource(self):
        self._test_list_resource('bare/simple')

    def test_custom_simple_detail_resource(self):
        self._test_detail_resource('custom/simple')

    def test_custom_simple_list_resource(self):
        self._test_list_resource('custom/simple')

########NEW FILE########
__FILENAME__ = test_resource_unimplemented
from delicious_cake.test import ResourceTestCase

__all__ = ('UnimplementedResourceTestCase',)


HTTP_METHODS = ['get', 'head', 'post', 'put', 'delete', 'options']


class UnimplementedResourceTestCase(ResourceTestCase):
    def _test_unimplemented_resource(self, uri):
        for method in HTTP_METHODS:
            method_attr = getattr(self.client, method)
            response = method_attr(uri)

            if method is not 'options':
                self.assertHttpMethodNotAllowed(response)
            else:
                self.assertHttpOK(response)

    def test_unimplemented_list_resource(self):
        self._test_unimplemented_resource('/unimplemented/')

    def test_unimplemented_detail_resource(self):
        self._test_unimplemented_resource('/unimplemented/1/')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from .resources import *


urlpatterns = patterns('',
    url(r'^simple/(?P<pk>\d+)/$', SimpleDetailResource.as_view(),
        name='simple-detail'),
    url(r'^simple/$', SimpleListResource.as_view(),
        name='simple-list'),

    url(r'^forced/simple/(?P<pk>\d+)/$', ForcedSimpleDetailResource.as_view(),
        name='forced-simple-detail'),
    url(r'^forced/simple/$', ForcedSimpleListResource.as_view(),
        name='forced-simple-list'),

    url(r'^bare/simple/(?P<pk>\d+)/$', ForcedSimpleDetailResource.as_view(),
        name='bare-simple-detail'),
    url(r'^bare/simple/$', ForcedSimpleListResource.as_view(),
        name='bare-simple-list'),

    url(r'^custom/simple/(?P<pk>\d+)/$',
        CustomEntityDetailResource.as_view(),
        name='custom-entity-detail'),
    url(r'^custom/simple/$', CustomEntityListResource.as_view(),
        name='custom-entity-list'),

    url(r'^unimplemented/(?P<pk>\d+)/$', UnimplementedDetailResource.as_view(),
        name='unimplemented-detail'),
    url(r'^unimplemented/$', UnimplementedListResource.as_view(),
        name='unimplemented-list'),

    url(r'^empty/(?P<pk>\d+)/$', EmptyDetailResource.as_view(),
        name='empty-detail'),
    url(r'^empty/$', EmptyListResource.as_view(), name='empty-list'),

    url(r'^custom/create/$', CustomCreateListResource.as_view(),
        name='custom-create-detail'),

    url(r'^upload/$', CakeUploadResource.as_view(),
        name='upload-resource'),)

########NEW FILE########
__FILENAME__ = manage_core
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_core")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import os

ADMINS = (
    ('test@example.com', 'Mr. Test'),)

BASE_PATH = os.path.abspath(os.path.dirname(__file__))

MEDIA_ROOT = os.path.normpath(os.path.join(BASE_PATH, 'media'))

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'delicious_cake.db'
TEST_DATABASE_NAME = 'delicious-cake-test.db'

# for forwards compatibility
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.%s' % DATABASE_ENGINE,
        'NAME': DATABASE_NAME,
        'TEST_NAME': TEST_DATABASE_NAME}}


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'delicious_cake']

DEBUG = True
TEMPLATE_DEBUG = DEBUG
CACHE_BACKEND = 'locmem://'
SECRET_KEY = 'verysecret'

# to make sure timezones are handled correctly in Django>=1.4
USE_TZ = True

########NEW FILE########
__FILENAME__ = settings_core
from settings import *

INSTALLED_APPS.append('core')

ROOT_URLCONF = 'core.urls'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
