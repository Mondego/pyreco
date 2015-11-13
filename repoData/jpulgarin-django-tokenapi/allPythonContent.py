__FILENAME__ = backends
from django.contrib.auth.backends import ModelBackend
from tokenapi.tokens import token_generator
from django.conf import settings

try:
    from django.contrib.auth import get_user_model
except ImportError: # Django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class TokenBackend(ModelBackend):
    def authenticate(self, pk, token):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

        TOKEN_CHECK_ACTIVE_USER = getattr(settings, "TOKEN_CHECK_ACTIVE_USER", False)

        if TOKEN_CHECK_ACTIVE_USER and not user.is_active:
            return None

        if token_generator.check_token(user,
            token):
            return user
        return None

########NEW FILE########
__FILENAME__ = decorators
from django.http import HttpResponseForbidden
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt

from functools import wraps

def token_required(view_func):
    """Decorator which ensures the user has provided a correct user and token pair."""

    @csrf_exempt
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = None
        token = None
        basic_auth = request.META.get('HTTP_AUTHORIZATION')

        if basic_auth:
            auth_method, auth_string = basic_auth.split(' ', 1)

            if auth_method.lower() == 'basic':
                auth_string = auth_string.strip().decode('base64')
                user, token = auth_string.split(':', 1)

        if not (user and token):
            user = request.REQUEST.get('user')
            token = request.REQUEST.get('token')

        if user and token:
            user = authenticate(pk=user, token=token)
            if user:
                login(request, user)
                return view_func(request, *args, **kwargs)

        return HttpResponseForbidden()
    return _wrapped_view

########NEW FILE########
__FILENAME__ = http
"""JSON helper functions"""
try:
    import simplejson as json
except ImportError:
    import json

from django.http import HttpResponse


def JsonResponse(data, dump=True, status=200):
    try:
        data['errors']
    except KeyError:
        data['success'] = True
    except TypeError:
        pass

    return HttpResponse(
        json.dumps(data) if dump else data,
        content_type='application/json',
        status=status,
    )


def JsonError(error_string, status=200):
    data = {
        'success': False,
        'errors': error_string,
    }
    return JSONResponse(data)


def JsonResponseBadRequest(error_string):
    return JsonError(error_string, status=400)


def JsonResponseUnauthorized(error_string):
    return JsonError(error_string, status=401)


def JsonResponseForbidden(error_string):
    return JsonError(error_string, status=403)


def JsonResponseNotFound(error_string):
    return JsonError(error_string, status=404)


def JsonResponseNotAllowed(error_string):
    return JsonError(error_string, status=405)


def JsonResponseNotAcceptable(error_string):
    return JsonError(error_string, status=406)


# For backwards compatability purposes
JSONResponse = JsonResponse
JSONError = JsonError

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
import json

from django.test import TestCase
from django.core.urlresolvers import reverse

try:
    from django.contrib.auth import get_user_model
except ImportError: # Django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from tokenapi.tokens import token_generator


class TokenManagementTestCase(TestCase):
    username = "jpulgarin"
    email = "jp@julianpulgarin.com"
    password = "GGGGGG"

    def setUp(self):
        self.user = User.objects.create_user(self.username, self.email, self.password)
        self.user.save()

        self.token = token_generator.make_token(self.user)

    def test_token_new_correct(self):
        response = self.client.post(reverse('api_token_new'), {
            'username': self.username,
            'password': self.password,
        })

        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['user'], self.user.pk)
        self.assertEqual(data['token'], self.token)

    def test_token_new_incorrect(self):
        credentials = ((
            self.username,
            "AAAAAA",
        ), (
            "j",
            self.password,
        ), (
            "j",
            "AAAAAA",
        ))

        for username, password in credentials:
            response = self.client.post(reverse('api_token_new'), {
                'username': username,
                'password': password,
            })

            data = json.loads(response.content)

            self.assertEqual(response.status_code, 200)
            self.assertFalse(data['success'])
            self.assertTrue(data['errors'])
            self.assertNotEqual(data.get('user'), self.user.pk)
            self.assertNotEqual(data.get('token'), self.token)

    def test_token_correct(self):
        response = self.client.post(reverse('api_token', kwargs={'token': self.token, 'user': self.user.pk}))

        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])

    def test_token_incorrect(self):
        incorrect_token = self.token[::-1]

        response = self.client.post(reverse('api_token', kwargs={'token': incorrect_token, 'user': self.user.pk}))

        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(data['success'])
        self.assertTrue(data['errors'])

########NEW FILE########
__FILENAME__ = tokens
"""django.contrib.auth.tokens, but without using last_login in hash"""

from datetime import date
from django.conf import settings
from django.utils.http import int_to_base36, base36_to_int

class TokenGenerator(object):
    """
    Strategy object used to generate and check tokens
    """

    TOKEN_TIMEOUT_DAYS = getattr(settings, "TOKEN_TIMEOUT_DAYS", 7)

    def make_token(self, user):
        """
        Returns a token for a given user
        """
        return self._make_token_with_timestamp(user, self._num_days(self._today()))

    def check_token(self, user, token):
        """
        Check that a token is correct for a given user.
        """
        # Parse the token
        try:
            ts_b36, hash = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if self._make_token_with_timestamp(user, ts) != token:
            return False

        # Check the timestamp is within limit
        if (self._num_days(self._today()) - ts) > self.TOKEN_TIMEOUT_DAYS:
            return False

        return True

    def _make_token_with_timestamp(self, user, timestamp):
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)

        # No longer using last login time
        from hashlib import sha1
        hash = sha1(settings.SECRET_KEY + unicode(user.id) +
            user.password + 
            unicode(timestamp)).hexdigest()[::2]
        return "%s-%s" % (ts_b36, hash)

    def _num_days(self, dt):
        return (dt - date(2001,1,1)).days

    def _today(self):
        # Used for mocking in tests
        return date.today()


token_generator = TokenGenerator()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns('tokenapi.views',
    url(r'^token/new.json$', 'token_new', name='api_token_new'),
    url(r'^token/(?P<token>.{24})/(?P<user>\d+).json$', 'token', name='api_token'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

try:
    from django.contrib.auth import get_user_model
except ImportError: # Django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from tokenapi.tokens import token_generator
from tokenapi.http import JsonResponse, JsonError, JsonResponseForbidden, JsonResponseUnauthorized


# Creates a token if the correct username and password is given
# token/new.json
# Required: username&password
# Returns: success&token&user
@csrf_exempt
def token_new(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if user:
                TOKEN_CHECK_ACTIVE_USER = getattr(settings, "TOKEN_CHECK_ACTIVE_USER", False)

                if TOKEN_CHECK_ACTIVE_USER and not user.is_active:
                    return JsonResponseForbidden("User account is disabled.")

                data = {
                    'token': token_generator.make_token(user),
                    'user': user.pk,
                }
                return JsonResponse(data)
            else:
                return JsonResponseUnauthorized("Unable to log you in, please try again.")
        else:
            return JsonError("Must include 'username' and 'password' as POST parameters.")
    else:
        return JsonError("Must access via a POST request.")

# Checks if a given token and user pair is valid
# token/:token/:user.json
# Required: user
# Returns: success
def token(request, token, user):
    try:
        user = User.objects.get(pk=user)
    except User.DoesNotExist:
        return JsonError("User does not exist.")

    TOKEN_CHECK_ACTIVE_USER = getattr(settings, "TOKEN_CHECK_ACTIVE_USER", False)

    if TOKEN_CHECK_ACTIVE_USER and not user.is_active:
        return JsonError("User account is disabled.")

    if token_generator.check_token(user, token):
        return JsonResponse({})
    else:
        return JsonError("Token did not match user.")

########NEW FILE########
