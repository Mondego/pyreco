__FILENAME__ = middleware
import django
# Django 1.5 add support for custom auth user model
if django.VERSION >= (1, 5):
    from django.contrib.auth import get_user_model
    User = get_user_model()
else:
    try:
        from django.contrib.auth.models import User
    except ImportError:
        raise ImportError(u'User model is not to be found.')
from django.conf import settings
from django.contrib.auth import login

from tempus.middleware import BaseTempusMiddleware


class AutoLoginMiddleware(BaseTempusMiddleware):
    def _get_user(self, request):
        user_pk = request.tempus
        if user_pk:
            # Only change user if necessary. We strip the token in any case.
            # The AnonymousUser class has no 'pk' attribute (#18093)
            if getattr(request.user, 'pk', request.user.id) == user_pk:
                return None
            try:
                return User.objects.get(pk=user_pk)
            except (ValueError, User.DoesNotExist):
                return None

    def success_func(self, request):
        user = self._get_user(request)
        if user:
            user.backend = settings.AUTHENTICATION_BACKENDS[0]
            login(request, user)

########NEW FILE########
__FILENAME__ = middleware
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.cache import add_never_cache_headers
from django.core.signing import BadSignature
from django.core.signing import SignatureExpired

from urlobject import URLObject

from .utils import tempus_loads


class BaseTempusMiddleware(object):
    max_age = None
    param_name = 'tempus'

    def process_request(self, request):
        token = request.GET.get(self.param_name)
        if not token:
            return

        redirect_url = URLObject(request.get_full_path())
        redirect_url = redirect_url.del_query_param(self.param_name)

        response = redirect(unicode(redirect_url))
        try:
            token_data = tempus_loads(token, max_age=self.max_age)
            tempus = getattr(request, 'tempus', None)
            if tempus:
                current_tempus = tempus.copy()
                current_tempus.update(token_data)
                request.tempus = current_tempus
            else:
                request.tempus = token_data
        except SignatureExpired:
            value = self.__process_func(request, 'expired_func')
            if value:
                return value
        except BadSignature:
            value = self.__process_func(request, 'unsuccess_func')
            if value:
                return value
        else:
            value = self.__process_func(request, 'success_func')
            if value:
                return value

        add_never_cache_headers(response)
        return response

    def __process_func(self, request, func_name):
        func_name = getattr(self, func_name, None)
        if func_name:
            value = func_name(request)
            if isinstance(value, HttpResponse):
                return value

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tempus_tag
from django import template

from tempus.utils import tempus_dumps


register = template.Library()


@register.simple_tag
def tempus(data, param_name='tempus', salt='tempus'):
    encrypted_data = tempus_dumps(data, salt=salt)
    return '%s=%s' % (param_name, encrypted_data)

########NEW FILE########
__FILENAME__ = middleware
from __future__ import unicode_literals

from django.test import Client
from django.test import TestCase
from django.contrib.auth.models import User

from tempus.utils import tempus_dumps


class TestAutoLogin(TestCase):
    def setUp(self):
        self.csrf_client = Client(enforce_csrf_checks=True)

        self.username = 'john'
        self.email = 'lennon@thebeatles.com'
        self.password = 'password'
        self.user = User.objects.create_user(self.username,
                                             self.email,
                                             self.password)
        self.token_data = tempus_dumps(self.user.pk)

    def test_redirect(self):
        response = self.client.get('/user/',
                                   {'tempus': self.token_data})
        self.assertRedirects(response, '/user/')

    def test_login_user(self):
        response = self.client.get('/user/',
                                   {'tempus': self.token_data},
                                   follow=True)
        self.assertEqual(response.content, b'john')

    def test_bad_token(self):
        response = self.client.get('/user/',
                                   {'tempus': 'WRONGTOKEN'},
                                   follow=True)
        self.assertEqual(response.content, b'anonymous')

    def test_no_token(self):
        response = self.client.get('/user/')
        self.assertEqual(response.content, b'anonymous')


class TestPromo(TestCase):
    def setUp(self):
        self.csrf_client = Client(enforce_csrf_checks=True)
        promo_data = {'discount': 5}
        self.token_data = tempus_dumps(promo_data)

    def test_redirect(self):
        response = self.client.get('/promo/',
                                   {'promo': self.token_data})
        self.assertRedirects(response, '/promo/')

    def test_promotion(self):
        response = self.client.get('/promo/',
                                   {'promo': self.token_data},
                                   follow=True)
        self.assertEqual(response.content, b'20')

    def test_bad_token(self):
        response = self.client.get('/promo/',
                                   {'promo': 'WRONGTOKEN'},
                                   follow=True)
        self.assertEqual(response.content, b'25')

    def test_no_token(self):
        response = self.client.get('/promo/')
        self.assertEqual(response.content, b'25')

########NEW FILE########
__FILENAME__ = settings
from __future__ import unicode_literals

CACHES = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'tempus'
)

ROOT_URLCONF = 'tempus.tests.urls'

SECRET_KEY = 'tempusfugit'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'tempus.contrib.auto_login.middleware.AutoLoginMiddleware',
    'tempus.tests.utils.PromoMiddleware'
)

########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals

from django.conf.urls import patterns

from .views import promo
from .views import show_user


urlpatterns = patterns('', (r'^user/$', show_user), (r'^promo/$', promo))

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.template import RequestContext
from django.template import Template


template_user = Template(
    '{% if user.is_authenticated %}{{ user }}'
    '{% elif user.is_anonymous %}anonymous'
    '{% else %}no user'
    '{% endif %}'
)

template_promo = Template(
    '{{ price }}'
)


def show_user(request):
    context = RequestContext(request)
    return HttpResponse(template_user.render(context),
                        content_type='text/plain')


def promo(request):
    price = 25
    discount = request.tempus.get('discount', 0)
    price -= discount
    context = RequestContext(request, {'price': price})
    return HttpResponse(template_promo.render(context),
                        content_type='text/plain')

########NEW FILE########
__FILENAME__ = utils
from django.core import signing


def tempus_dumps(data, salt='tempus', compress=True, *args, **kwargs):
    encrypted_data = signing.dumps(
        data, salt=salt, compress=compress, *args, **kwargs)
    return encrypted_data


def tempus_loads(encrypted_data, salt='tempus', max_age=None, *args, **kwargs):
    data = signing.loads(
        encrypted_data, salt=salt, max_age=max_age, *args, **kwargs)
    return data

########NEW FILE########
