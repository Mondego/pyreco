__FILENAME__ = settings
"""
Django settings for example project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'bc(-+ke=d+ykea5@s(c_wcun!=db7j&4$5uqixfv5x0s9ygce^'

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
    'django.contrib.sites',
    'qrauth',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'example.urls'

WSGI_APPLICATION = 'example.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
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

# Settings for python manage.py collectstatic

STATIC_ROOT =  os.path.join(BASE_DIR, 'static')

# Setting for templates and apps templates not written by yourself

TEMPLATE_DIRS = (
     os.path.join(BASE_DIR, 'templates'),
)

#### django.contrib.sites requirements
SITE_ID = 1

#### Qrauth Example settings
AUTH_QR_CODE_EXPIRATION_TIME = 600 # Ten minutes

AUTH_QR_CODE_REDIRECT_URL = "/welcome-qrauth/"

AUTH_QR_CODE_REDIS_KWARGS = {
    "host": "127.0.0.1",
    "port": 6379,
    "db": 0,
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'example.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

# Django-qrauth url patterns
urlpatterns += patterns('',
    # .
    url(r'^qr/', include('qrauth.urls')),
    # .
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = qr
try:
    from PIL import Image, ImageDraw
except ImportError:
    import Image, ImageDraw

import qrcode.image.base
import qrcode.image.pil

class PilImage(qrcode.image.pil.PilImage):
    def __init__(self, border, width, box_size):
        if Image is None and ImageDraw is None:
            raise NotImplementedError("PIL not available")
        qrcode.image.base.BaseImage.__init__(self, border, width, box_size)
        self.kind = "PNG"

        pixelsize = (self.width + self.border * 2) * self.box_size
        self._img = Image.new("RGBA", (pixelsize, pixelsize))
        self._idr = ImageDraw.Draw(self._img)

def make_qr_code(string):
    return qrcode.make(string, box_size=10, border=1, image_factory=PilImage)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic.base import TemplateView

urlpatterns = patterns('qrauth.views',
    url(
        r'^pic/(?P<auth_code>[a-zA-Z\d]{50})/$',
        'qr_code_picture',
        name='auth_qr_code'
    ),
    url(
        r'^(?P<auth_code_hash>[a-f\d]{40})/$',
        'login_view',
        name='qr_code_login'
    ),
    url(
        r'invalid_code/$',
        TemplateView.as_view(
            template_name='qrauth/invalid_code.html'
        ),
        name='invalid_auth_code'
    ),
    url(
        r'^$',
        'qr_code_page',
        name='qr_code_page'
    ),
)

########NEW FILE########
__FILENAME__ = utils
import os
import string
import hashlib

from django.conf import settings

def generate_random_string(length,
                           stringset="".join(
                               [string.ascii_letters+string.digits]
                           )):
    """
    Returns a string with `length` characters chosen from `stringset`
    >>> len(generate_random_string(20) == 20 
    """
    return "".join([stringset[i%len(stringset)] \
        for i in [ord(x) for x in os.urandom(length)]])

def salted_hash(string):
    return hashlib.sha1(":)".join([
        string,
        settings.SECRET_KEY,
    ])).hexdigest()

########NEW FILE########
__FILENAME__ = views
# Create your views here.

import redis

from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, get_backends
from django.contrib.sites.models import get_current_site
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse

from django.contrib.auth.models import User

from django.conf import settings

from utils import generate_random_string, salted_hash
from qr import make_qr_code

AUTH_QR_CODE_EXPIRATION_TIME = getattr(
    settings,
    "AUTH_QR_CODE_EXPIRATION_TIME",
    300
)

AUTH_QR_CODE_REDIRECT_URL = getattr(
    settings,
    "AUTH_QR_CODE_REDIRECT_URL",
    "/"
)

AUTH_QR_CODE_REDIS_KWARGS = getattr(
    settings,
    "AUTH_QR_CODE_REDIS_KWARGS",
    {}
)

def uses_redis(func):
    def wrapper(*args, **kwargs):
        kwargs["r"] = redis.StrictRedis(**AUTH_QR_CODE_REDIS_KWARGS)
        return func(*args, **kwargs)

    return wrapper

@login_required
@uses_redis
def qr_code_page(request, r=None):
    auth_code = generate_random_string(50)
    auth_code_hash = salted_hash(auth_code)

    r.setex(
        "".join(["qrauth_", auth_code_hash]),
        AUTH_QR_CODE_EXPIRATION_TIME,
        request.user.id
    )

    return render_to_response("qrauth/page.html",
                              {"auth_code": auth_code},
                              context_instance=RequestContext(request))

@login_required
@uses_redis
def qr_code_picture(request, auth_code, r=None):
    auth_code_hash = salted_hash(auth_code)

    user_id = r.get("".join(["qrauth_", auth_code_hash]))

    if (user_id == None) or (user_id != str(request.user.id)):
        raise Http404("No such auth code")

    current_site = get_current_site(request)
    scheme = request.is_secure() and "https" or "http"

    login_link = "".join([
        scheme,
        "://",
        current_site.domain,
        reverse("qr_code_login", args=(auth_code_hash,)),
    ])

    img = make_qr_code(login_link)
    response = HttpResponse(content_type="image/png")
    img.save(response, "PNG")
    return response

@uses_redis
def login_view(request, auth_code_hash, r=None):
    redis_key = "".join(["qrauth_", auth_code_hash])

    user_id = r.get(redis_key)

    if user_id == None:
        return HttpResponseRedirect(reverse("invalid_auth_code"))

    r.delete(redis_key)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return HttpResponseRedirect(reverse("invalid_auth_code"))

    # In lieu of a call to authenticate()
    backend = get_backends()[0]
    user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
    login(request, user)

    return HttpResponseRedirect(AUTH_QR_CODE_REDIRECT_URL)

########NEW FILE########
