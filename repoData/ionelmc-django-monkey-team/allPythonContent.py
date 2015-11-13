__FILENAME__ = admin
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url
from admin_utils import make_admin_class

make_admin_class("Setup", patterns("monkey_team.views",
    url(r'^$', 'setup', name='monkey_team_setup_changelist'),
    url(r'^monkey-team.user.js$', 'userscript', name='monkey_team_userscript'),
    url(r'^decode/$', 'decode', name='monkey_team_test'),
    url(r'^test/$', 'test', name='monkey_team_test'),
), "monkey_team")

make_admin_class("Decode", patterns("monkey_team.views",
    url(r'^$', 'decode', name='monkey_team_decode_changelist'),
), "monkey_team")

########NEW FILE########
__FILENAME__ = forms
from Crypto.Cipher import AES

from django import forms
from django.forms import ValidationError
from .utils import get_decode_key

class DecodeForm(forms.Form):
    optional_decode_key = forms.CharField(required=False)
    message = forms.CharField(widget=forms.Textarea, required=True)

    def clean_optional_decode_key(self):
        optional_decode_key = self.cleaned_data['optional_decode_key'].strip()
        if optional_decode_key:
            if len(optional_decode_key) != 64:
                raise ValidationError('Invalid length for decode key !')
            try:
                decode_key = optional_decode_key.decode('hex')
            except TypeError as e:
                raise ValidationError('Cannot convert to binary: %r' % e.msg)

            return decode_key

    def clean_message(self):
        message = self.cleaned_data['message']
        try:
            message = message.decode('base64')
        except TypeError as e:
            raise ValidationError('Cannot convert to binary: %r' % e.msg)

        if len(message) % 16:
            raise ValidationError('Wrong block size for message !')

        if len(message) <= 16:
            raise ValidationError('Message too short or missing IV !')

        return message

########NEW FILE########
__FILENAME__ = middleware
import sys
import os

from Crypto.Cipher import AES

from django.views.debug import technical_500_response
from django.template.loader import render_to_string
from django.conf import settings

from .utils import get_decode_key, get_client_key

BLOCK_SIZE = 16
MONKEY_FORCE_ACTIVE = getattr(settings, "MONKEY_FORCE_ACTIVE", False)
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s : s[0:-ord(s[-1])]

class MonkeyTeamMiddleware(object):

    @staticmethod
    def patch_response(request, response):
        iv = os.urandom(16)
        response.content = render_to_string("monkey_500.html", {
            'client_key': get_client_key(),
            'data': (
                iv + AES.new(
                    get_decode_key(),
                    AES.MODE_CBC,
                    iv,
                ).encrypt(
                    pad(response.content)
                )
            ).encode('base64'),
            'extra': ''#MonkeySetup.get_userscript_code(request),
        })

    def process_exception(self, request, exception):
        if not settings.DEBUG or MONKEY_FORCE_ACTIVE:
            exc_info = sys.exc_info()
            if exc_info:
                response = technical_500_response(request, *exc_info)
            else:
                response = technical_500_response(request, type(exception), exception, None)
            self.patch_response(request, response)
            return response
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test.client import Client
from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings

from monkey_team.views import TestException

class MonkeyTeamTestCase(TestCase):
    def setUp(self):
        self.user = User(
            username='test', email='test@example.com', is_active=True,
            is_staff=True, is_superuser=True,
        )
        self.user.set_password('test')
        self.user.save()
        self.client.login(username='test', password='test')

    def test_admin_not_broken(self):
        response = self.client.get('/admin/')
        self.assertContains(response, '/admin/password_change/')
        self.assertNotContains(response, "You don't have permission to edit anything")

    def test_admin_auth_not_broken(self):
        response = self.client.get('/admin/auth/')
        self.assertEqual(response.status_code, 200, response)

    def test_admin_auth_user_not_broken(self):
        response = self.client.get('/admin/auth/user/')
        self.assertEqual(response.status_code, 200, response)

    def test_admin_monkey_setup(self):
        response = self.client.get('/admin/monkey_team/')
        self.assertEqual(response.status_code, 200, response)
        response = self.client.get('/admin/monkey_team/setup/')
        self.assertEqual(response.status_code, 200, response)

    def test_admin_monkey_test(self):
        response = self.client.get('/admin/monkey_team/setup/test/')
        self.assertContains(response, "A team of highly trained monkeys has been dispatched to deal with this situation.", status_code=500)

    def test_admin_monkey_test_debug(self):
        settings.DEBUG = True
        self.assertRaises(TestException, self.client.get, '/admin/monkey_team/setup/test/')
        settings.DEBUG = False

    def test_admin_monkey_setup_debug(self):
        settings.DEBUG = True
        response = self.client.get('/admin/monkey_team/setup/')
        self.assertEqual(response.status_code, 200, response)
        self.assertContains(response, "Highly trained monkeys do not have")
        settings.DEBUG = False

    def test_admin_userscript_generate(self):
        response = self.client.get('/admin/monkey_team/setup/monkey-team.user.js')
        self.assertContains(response, "CLIENT_KEY")
        self.assertContains(response, "var CryptoJS=CryptoJS")

########NEW FILE########
__FILENAME__ = utils
import hashlib
import os
from django.conf import settings
from django.template import RequestContext
from django.template.loader import render_to_string

def get_client_key():
    return hashlib.sha1(
        "monkey-team-match-id-%s" % settings.SECRET_KEY
    ).hexdigest()

def get_decode_key():
    return hashlib.sha256(
        "monkey-team-decode-key-%s" % settings.SECRET_KEY
    ).digest()

def get_decode_key_hex():
    return get_decode_key().encode('hex').strip()

def get_userscript_code(request):
    return render_to_string("monkey-team.user.js", {
        'client_key': get_client_key(),
        'decode_key': get_decode_key_hex(),
        'lib_code': file(os.path.join(os.path.dirname(__file__), 'aes.js')).read(),
        'site_name': request.get_host(),
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = views
from Crypto.Cipher import AES

from django.conf import settings
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render

from .utils import get_client_key, get_userscript_code, get_decode_key
from .forms import DecodeForm

class TestException(Exception):
    pass

def userscript(request):
    response = HttpResponse(
        get_userscript_code(request),
        mimetype='application/javascript'
    )
    response['Content-Disposition'] = 'attachment; filename="monkey-team-%s.user.js"' % get_client_key()
    return response

def test(_request):
    raise TestException("Relax, it's just a test ...")

def setup(request):
    return render(request, "monkey_setup.html", {
        'userscript_url': reverse('admin:monkey_team_userscript'),
        'test_url': reverse('admin:monkey_team_test'),
        'warn_middleware': 'monkey_team.middleware.MonkeyTeamMiddleware' not in settings.MIDDLEWARE_CLASSES,
        'warn_debug': settings.DEBUG,
    })

def decode(request):
    if request.method == "POST":
        form = DecodeForm(request.POST)
        if form.is_valid():
            message = form.cleaned_data['message']
            optional_decode_key = form.cleaned_data['optional_decode_key']
            decode_key = optional_decode_key or get_decode_key()
            return HttpResponse(
                AES.new(
                    decode_key,
                    AES.MODE_CBC,
                    message[:16],
                ).decrypt(
                    message[16:]
                )
            )
    else:
        form = DecodeForm()
    return render(request, "monkey_decode.html", {
        "form": form
    })
########NEW FILE########
__FILENAME__ = settings
import os
TEMPLATE_DEBUG = DEBUG = False
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(os.path.dirname(__file__), 'database.sqlite')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_NAME
    },
}
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'monkey_team',
)
SITE_ID = 1
ROOT_URLCONF = 'test_project.urls'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'monkey_team.middleware.MonkeyTeamMiddleware',
)
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
TEMPLATE_DIRS = os.path.join(os.path.dirname(__file__), 'templates'),
SECRET_KEY = "DON'T MATTER"
STATIC_URL = "/static/"
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s: %(levelname)s/%(processName)s/%(process)s] %(name)s - %(message)s \t\t\t in %(funcName)s@%(pathname)s:%(lineno)d'
        },
    },
    'handlers': {
        'console': {
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': 'ext://sys.stderr'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level':'DEBUG',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': True,
    }
}
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, handler404, handler500, include, url
except ImportError:
    from django.conf.urls.defaults import patterns, handler404, handler500, include, url
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
