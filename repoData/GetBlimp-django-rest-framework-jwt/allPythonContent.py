__FILENAME__ = authentication
import jwt
from rest_framework import exceptions
from rest_framework.authentication import (BaseAuthentication,
                                           get_authorization_header)
from rest_framework_jwt.settings import api_settings

try:
    from django.contrib.auth import get_user_model
except ImportError:  # Django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


jwt_decode_handler = api_settings.JWT_DECODE_HANDLER


class JSONWebTokenAuthentication(BaseAuthentication):
    """
    Token based authentication using the JSON Web Token standard.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "JWT ".  For example:

        Authorization: JWT eyJhbGciOiAiSFMyNTYiLCAidHlwIj
    """
    www_authenticate_realm = 'api'

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'jwt':
            return None

        if len(auth) == 1:
            msg = 'Invalid JWT header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = ('Invalid JWT header. Credentials string '
                   'should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            payload = jwt_decode_handler(auth[1])
        except jwt.ExpiredSignature:
            msg = 'Signature has expired.'
            raise exceptions.AuthenticationFailed(msg)
        except jwt.DecodeError:
            msg = 'Error decoding signature.'
            raise exceptions.AuthenticationFailed(msg)

        user = self.authenticate_credentials(payload)

        return (user, auth[1])

    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        try:
            user_id = payload.get('user_id')

            if user_id:
                user = User.objects.get(pk=user_id, is_active=True)
            else:
                msg = 'Invalid payload'
                raise exceptions.AuthenticationFailed(msg)
        except User.DoesNotExist:
            msg = 'Invalid signature'
            raise exceptions.AuthenticationFailed(msg)

        return user

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return 'JWT realm="{0}"'.format(self.www_authenticate_realm)

########NEW FILE########
__FILENAME__ = models
# Just to keep things like ./manage.py test happy
########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

# https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/runtests/runtests.py
import os
import sys

# fix sys path so we don't need to setup PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
os.environ['DJANGO_SETTINGS_MODULE'] = 'rest_framework_jwt.runtests.settings'

import django
from django.conf import settings
from django.test.utils import get_runner


def main():
    TestRunner = get_runner(settings)

    test_runner = TestRunner()

    test_module_name = 'rest_framework_jwt.tests'

    if django.VERSION[0] == 1 and django.VERSION[1] < 6:
        test_module_name = 'tests'

    failures = test_runner.run_tests(
        [test_module_name], verbosity=1, interactive=True)

    sys.exit(failures)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = settings
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'r-4p2y=uc56fmqsncog%3h!7hc=y+g)xtz+9y(prx*1o9dpry0'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

# OAuth2 is optional and won't work if there is no provider & oauth2
try:
    import provider
except ImportError:
    pass
else:
    INSTALLED_APPS += (
        'provider',
        'provider.oauth2',
    )

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'urls'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':  'db.sqlite3',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

########NEW FILE########
__FILENAME__ = urls
"""
Blank URLConf just to keep runtests.py happy.
"""
from rest_framework.compat import patterns

urlpatterns = patterns('',)

########NEW FILE########
__FILENAME__ = serializers
from django.contrib.auth import authenticate
from rest_framework import serializers

from rest_framework_jwt.settings import api_settings


jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class JSONWebTokenSerializer(serializers.Serializer):
    """
    Serializer class used to validate a username and password.

    Returns a JSON Web Token that can be used to authenticate later calls.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if user:
                if not user.is_active:
                    msg = 'User account is disabled.'
                    raise serializers.ValidationError(msg)

                payload = jwt_payload_handler(user)

                return {
                    'token': jwt_encode_handler(payload)
                }
            else:
                msg = 'Unable to login with provided credentials.'
                raise serializers.ValidationError(msg)
        else:
            msg = 'Must include "username" and "password"'
            raise serializers.ValidationError(msg)

########NEW FILE########
__FILENAME__ = settings
import datetime

from django.conf import settings
from rest_framework.settings import APISettings


USER_SETTINGS = getattr(settings, 'JWT_AUTH', None)

DEFAULTS = {
    'JWT_ENCODE_HANDLER':
    'rest_framework_jwt.utils.jwt_encode_handler',

    'JWT_DECODE_HANDLER':
    'rest_framework_jwt.utils.jwt_decode_handler',

    'JWT_PAYLOAD_HANDLER':
    'rest_framework_jwt.utils.jwt_payload_handler',

    'JWT_SECRET_KEY': settings.SECRET_KEY,
    'JWT_ALGORITHM': 'HS256',
    'JWT_VERIFY': True,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_LEEWAY': 0,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=300)
}

# List of settings that may be in string import notation.
IMPORT_STRINGS = (
    'JWT_ENCODE_HANDLER',
    'JWT_DECODE_HANDLER',
    'JWT_PAYLOAD_HANDLER',
)

api_settings = APISettings(USER_SETTINGS, DEFAULTS, IMPORT_STRINGS)

########NEW FILE########
__FILENAME__ = test_authentication
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import TestCase
from django.utils import unittest

from rest_framework import permissions, status
from rest_framework.authentication import OAuth2Authentication
from rest_framework.compat import oauth2_provider, oauth2_provider_models
from rest_framework.compat import patterns
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.views import APIView

from rest_framework_jwt import utils
from rest_framework_jwt.authentication import JSONWebTokenAuthentication


DJANGO_OAUTH2_PROVIDER_NOT_INSTALLED = 'django-oauth2-provider not installed'

factory = APIRequestFactory()


class MockView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return HttpResponse({'a': 1, 'b': 2, 'c': 3})

    def post(self, request):
        return HttpResponse({'a': 1, 'b': 2, 'c': 3})


urlpatterns = patterns(
    '',
    (r'^jwt/$', MockView.as_view(
     authentication_classes=[JSONWebTokenAuthentication])),

    (r'^jwt-oauth2/$', MockView.as_view(
        authentication_classes=[
            JSONWebTokenAuthentication, OAuth2Authentication])),

    (r'^oauth2-jwt/$', MockView.as_view(
        authentication_classes=[
            OAuth2Authentication, JSONWebTokenAuthentication])),
)


class JSONWebTokenAuthenticationTests(TestCase):
    """JSON Web Token Authentication"""
    urls = 'rest_framework_jwt.tests.test_authentication'

    def setUp(self):
        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.username = 'jpueblo'
        self.email = 'jpueblo@example.com'
        self.user = User.objects.create_user(self.username, self.email)

    def test_post_form_passing_jwt_auth(self):
        """
        Ensure POSTing json over JWT auth with correct credentials
        passes and does not require CSRF
        """
        payload = utils.jwt_payload_handler(self.user)
        token = utils.jwt_encode_handler(payload)

        auth = 'JWT {0}'.format(token)
        response = self.csrf_client.post(
            '/jwt/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_json_passing_jwt_auth(self):
        """
        Ensure POSTing form over JWT auth with correct credentials
        passes and does not require CSRF
        """
        payload = utils.jwt_payload_handler(self.user)
        token = utils.jwt_encode_handler(payload)

        auth = 'JWT {0}'.format(token)
        response = self.csrf_client.post(
            '/jwt/', {'example': 'example'},
            HTTP_AUTHORIZATION=auth, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_form_failing_jwt_auth(self):
        """
        Ensure POSTing form over JWT auth without correct credentials fails
        """
        response = self.csrf_client.post('/jwt/', {'example': 'example'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_json_failing_jwt_auth(self):
        """
        Ensure POSTing json over JWT auth without correct credentials fails
        """
        response = self.csrf_client.post('/jwt/', {'example': 'example'},
                                         format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response['WWW-Authenticate'], 'JWT realm="api"')

    def test_post_no_jwt_header_failing_jwt_auth(self):
        """
        Ensure POSTing over JWT auth without credentials fails
        """
        auth = 'JWT'
        response = self.csrf_client.post(
            '/jwt/', {'example': 'example'},
            HTTP_AUTHORIZATION=auth, format='json')

        msg = 'Invalid JWT header. No credentials provided.'

        self.assertEqual(response.data['detail'], msg)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response['WWW-Authenticate'], 'JWT realm="api"')

    def test_post_invalid_jwt_header_failing_jwt_auth(self):
        """
        Ensure POSTing over JWT auth without correct credentials fails
        """
        auth = 'JWT abc abc'
        response = self.csrf_client.post(
            '/jwt/', {'example': 'example'},
            HTTP_AUTHORIZATION=auth, format='json')

        msg = ('Invalid JWT header. Credentials string '
               'should not contain spaces.')

        self.assertEqual(response.data['detail'], msg)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response['WWW-Authenticate'], 'JWT realm="api"')

    def test_post_expired_token_failing_jwt_auth(self):
        """
        Ensure POSTing over JWT auth with expired token fails
        """
        payload = utils.jwt_payload_handler(self.user)
        payload['exp'] = 1
        token = utils.jwt_encode_handler(payload)

        auth = 'JWT {0}'.format(token)
        response = self.csrf_client.post(
            '/jwt/', {'example': 'example'},
            HTTP_AUTHORIZATION=auth, format='json')

        msg = 'Signature has expired.'

        self.assertEqual(response.data['detail'], msg)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response['WWW-Authenticate'], 'JWT realm="api"')

    def test_post_invalid_token_failing_jwt_auth(self):
        """
        Ensure POSTing over JWT auth with invalid token fails
        """
        auth = 'JWT abc123'
        response = self.csrf_client.post(
            '/jwt/', {'example': 'example'},
            HTTP_AUTHORIZATION=auth, format='json')

        msg = 'Error decoding signature.'

        self.assertEqual(response.data['detail'], msg)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response['WWW-Authenticate'], 'JWT realm="api"')

    @unittest.skipUnless(oauth2_provider, DJANGO_OAUTH2_PROVIDER_NOT_INSTALLED)
    def test_post_passing_jwt_auth_with_oauth2_priority(self):
        """
        Ensure POSTing over JWT auth with correct credentials
        passes and does not require CSRF when OAuth2Authentication
        has priority on authentication_classes
        """
        payload = utils.jwt_payload_handler(self.user)
        token = utils.jwt_encode_handler(payload)

        auth = 'JWT {0}'.format(token)
        response = self.csrf_client.post(
            '/oauth2-jwt/', {'example': 'example'},
            HTTP_AUTHORIZATION=auth, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response)

    @unittest.skipUnless(oauth2_provider, DJANGO_OAUTH2_PROVIDER_NOT_INSTALLED)
    def test_post_passing_oauth2_with_jwt_auth_priority(self):
        """
        Ensure POSTing over OAuth2 with correct credentials
        passes and does not require CSRF when JSONWebTokenAuthentication
        has priority on authentication_classes
        """
        oauth2_client = oauth2_provider_models.Client.objects.create(
            user=self.user,
            client_type=0,
        )
        access_token = oauth2_provider_models.AccessToken.objects.create(
            user=self.user,
            client=oauth2_client,
        )

        auth = 'Bearer {0}'.format(access_token.token)
        response = self.csrf_client.post(
            '/jwt-oauth2/', {'example': 'example'},
            HTTP_AUTHORIZATION=auth, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response)

    def test_post_form_passing_jwt_invalid_payload(self):
        """
        Ensure POSTing json over JWT auth with invalid payload fails
        """
        payload = dict(email=None)
        token = utils.jwt_encode_handler(payload)

        auth = 'JWT {0}'.format(token)
        response = self.csrf_client.post(
            '/jwt/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)

        msg = 'Invalid payload'

        self.assertEqual(response.data['detail'], msg)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

########NEW FILE########
__FILENAME__ = test_serializers
from django.test import TestCase
from django.contrib.auth.models import User

from rest_framework_jwt.serializers import JSONWebTokenSerializer
from rest_framework_jwt import utils


class JSONWebTokenSerializerTests(TestCase):
    def setUp(self):
        self.email = 'jpueblo@example.com'
        self.username = 'jpueblo'
        self.password = 'password'
        self.user = User.objects.create_user(
            self.username, self.email, self.password)

        self.data = {
            'username': self.username,
            'password': self.password
        }

    def test_empty(self):
        serializer = JSONWebTokenSerializer()
        expected = {
            'username': ''
        }

        self.assertEqual(serializer.data, expected)

    def test_create(self):
        serializer = JSONWebTokenSerializer(data=self.data)
        is_valid = serializer.is_valid()

        token = serializer.object['token']
        decoded_payload = utils.jwt_decode_handler(token)

        self.assertTrue(is_valid)
        self.assertEqual(decoded_payload['username'], self.username)

    def test_invalid_credentials(self):
        self.data['password'] = 'wrong'
        serializer = JSONWebTokenSerializer(data=self.data)
        is_valid = serializer.is_valid()

        expected_error = {
            'non_field_errors': ['Unable to login with provided credentials.']
        }

        self.assertFalse(is_valid)
        self.assertEqual(serializer.errors, expected_error)

    def test_disabled_user(self):
        self.user.is_active = False
        self.user.save()

        serializer = JSONWebTokenSerializer(data=self.data)
        is_valid = serializer.is_valid()

        expected_error = {
            'non_field_errors': ['User account is disabled.']
        }

        self.assertFalse(is_valid)
        self.assertEqual(serializer.errors, expected_error)

    def test_required_fields(self):
        serializer = JSONWebTokenSerializer(data={})
        is_valid = serializer.is_valid()

        expected_error = {
            'username': ['This field is required.'],
            'password': ['This field is required.']
        }

        self.assertFalse(is_valid)
        self.assertEqual(serializer.errors, expected_error)

########NEW FILE########
__FILENAME__ = test_utils
import json
from jwt import base64url_decode

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework_jwt import utils


class UtilsTests(TestCase):
    def setUp(self):
        self.username = 'jpueblo'
        self.email = 'jpueblo@example.com'
        self.user = User.objects.create_user(self.username, self.email)

    def test_jwt_payload_handler(self):
        payload = utils.jwt_payload_handler(self.user)

        self.assertTrue(isinstance(payload, dict))
        self.assertEqual(payload['user_id'], self.user.id)
        self.assertEqual(payload['email'], self.email)
        self.assertEqual(payload['username'], self.username)
        self.assertTrue('exp' in payload)

    def test_jwt_encode(self):
        payload = utils.jwt_payload_handler(self.user)
        token = utils.jwt_encode_handler(payload)

        payload_data = base64url_decode(token.split('.')[1].encode('utf-8'))
        payload_from_token = json.loads(payload_data.decode('utf-8'))

        self.assertEqual(payload_from_token, payload)

    def test_jwt_decode(self):
        payload = utils.jwt_payload_handler(self.user)
        token = utils.jwt_encode_handler(payload)
        decoded_payload = utils.jwt_decode_handler(token)

        self.assertEqual(decoded_payload, payload)

########NEW FILE########
__FILENAME__ = test_views
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.compat import patterns
from rest_framework.test import APIClient

from rest_framework_jwt import utils


urlpatterns = patterns(
    '',
    (r'^auth-token/$', 'rest_framework_jwt.views.obtain_jwt_token'),
)


class ObtainJSONWebTokenTests(TestCase):
    urls = 'rest_framework_jwt.tests.test_views'

    def setUp(self):
        self.email = 'jpueblo@example.com'
        self.username = 'jpueblo'
        self.password = 'password'
        self.user = User.objects.create_user(
            self.username, self.email, self.password)

        self.data = {
            'username': self.username,
            'password': self.password
        }

    def test_jwt_login_json(self):
        """
        Ensure JWT login view using JSON POST works.
        """
        client = APIClient(enforce_csrf_checks=True)

        response = client.post('/auth-token/', self.data, format='json')

        decoded_payload = utils.jwt_decode_handler(response.data['token'])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(decoded_payload['username'], self.username)

    def test_jwt_login_json_bad_creds(self):
        """
        Ensure JWT login view using JSON POST fails
        if bad credentials are used.
        """
        client = APIClient(enforce_csrf_checks=True)

        self.data['password'] = 'wrong'
        response = client.post('/auth-token/', self.data, format='json')

        self.assertEqual(response.status_code, 400)

    def test_jwt_login_json_missing_fields(self):
        """
        Ensure JWT login view using JSON POST fails if missing fields.
        """
        client = APIClient(enforce_csrf_checks=True)

        response = client.post('/auth-token/',
                               {'username': self.username}, format='json')

        self.assertEqual(response.status_code, 400)

    def test_jwt_login_form(self):
        """
        Ensure JWT login view using form POST works.
        """
        client = APIClient(enforce_csrf_checks=True)

        response = client.post('/auth-token/', self.data)

        decoded_payload = utils.jwt_decode_handler(response.data['token'])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(decoded_payload['username'], self.username)

########NEW FILE########
__FILENAME__ = utils
import datetime
import jwt

from rest_framework_jwt.settings import api_settings


def jwt_payload_handler(user):
    return {
        'user_id': user.id,
        'email': user.email,
        'username': user.get_username(),
        'exp': datetime.datetime.utcnow() + api_settings.JWT_EXPIRATION_DELTA
    }


def jwt_encode_handler(payload):
    return jwt.encode(
        payload,
        api_settings.JWT_SECRET_KEY,
        api_settings.JWT_ALGORITHM
    ).decode('utf-8')


def jwt_decode_handler(token):
    return jwt.decode(
        token,
        api_settings.JWT_SECRET_KEY,
        api_settings.JWT_VERIFY,
        api_settings.JWT_VERIFY_EXPIRATION,
        api_settings.JWT_LEEWAY
    )

########NEW FILE########
__FILENAME__ = views
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import parsers
from rest_framework import renderers
from rest_framework.response import Response

from .serializers import JSONWebTokenSerializer


class ObtainJSONWebToken(APIView):
    """
    API View that receives a POST with a user's username and password.

    Returns a JSON Web Token that can be used for authenticated requests.
    """
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = JSONWebTokenSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.DATA)
        if serializer.is_valid():
            return Response({'token': serializer.object['token']})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


obtain_jwt_token = ObtainJSONWebToken.as_view()

########NEW FILE########
