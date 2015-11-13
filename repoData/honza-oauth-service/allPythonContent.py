__FILENAME__ = admin
from django.contrib import admin
from models import User, UserProfile


admin.site.register(User)
admin.site.register(UserProfile)

########NEW FILE########
__FILENAME__ = api
import json

from functools import wraps
from django.http import HttpResponse, HttpResponseForbidden
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings

import oauth2 as oauth

from models import User


CONSUMERS = getattr(settings, 'CONSUMERS', {})


server = oauth.Server(signature_methods={
    'HMAC-SHA1': oauth.SignatureMethod_HMAC_SHA1()
})


def get_consumer(consumer_key):
    """
    Extract consumer information from settings
    """
    try:
        obj = CONSUMERS[consumer_key]
    except KeyError:
        return None

    if obj['active']:
        return oauth.Consumer(consumer_key, obj['secret'])

    return None


def get_user_by_token(token):
    """
    Look up user by ``token``.  Implement a real method.
    """
    try:
        return User.objects.get(token=token)
    except User.DoesNotExist:
        return None


def _check_request(request):
    """
    Verify that the flask ``request`` is properly signed and the user making it
    is authorized to proceed.
    """
    auth_header = {}
    parameters = {}

    if 'Authorization' in request.META:
        auth_header = {'Authorization': request.META['Authorization']}
    elif 'HTTP_AUTHORIZATION' in request.META:
        auth_header =  {'Authorization': request.META['HTTP_AUTHORIZATION']}

    if request.method == "POST" and \
        (request.META.get('CONTENT_TYPE') == "application/x-www-form-urlencoded" \
            or request.META.get('SERVER_NAME') == 'testserver'):
        parameters = dict(request.REQUEST.items())

    r = oauth.Request.from_request(request.method,
            request.build_absolute_uri(),
            headers=auth_header, parameters=parameters,
            query_string=request.META.get('QUERY_STRING', ''))

    access_token = r.get_parameter('oauth_token')
    consumer_key = r.get_parameter('oauth_consumer_key')

    frontend_consumer = get_consumer(consumer_key)

    user = get_user_by_token(access_token)

    if not user:
        return False, None

    token = oauth.Token(user.token, user.secret)


    try:
        server.verify_request(r, frontend_consumer, token)
        return True, user
    except:
        return False, None


def oauth_protected(f):
    """
    Flask view decorator.  Make sure that incoming OAuth request is valid.
    """
    @wraps(f)
    def decorated_view(request, *args, **kwargs):
        allowed, user = _check_request(request)
        if allowed:
            return f(request, user, *args, **kwargs)
        else:
            raise HttpResponseForbidden()
    return decorated_view


class JsonResponse(HttpResponse):
    """
    HttpResponse descendant, which return response with ``application/json`` mimetype.
    """
    def __init__(self, data):
        content = json.dumps(data, cls=DjangoJSONEncoder)
        super(JsonResponse, self).__init__(content=content,
                mimetype='application/json')


def jsonify(func):
    """
    If view returned serializable dict, returns JsonResponse with this dict
    as content.

    example:

        @ajax_request
        def my_view(request):
            return {'news_titles': 2}
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        response = func(request, *args, **kwargs)
        if isinstance(response, dict):
            return JsonResponse(response)
        else:
            return response
    return wrapper

########NEW FILE########
__FILENAME__ = models
from django.db import models
from uuid import uuid4
import hashlib


def get_rand_hash():
    uid = uuid4()
    return hashlib.sha1(str(uid)).hexdigest()


class User(models.Model):
    username = models.CharField(max_length=200, unique=True)
    password = models.CharField(max_length=200)
    token = models.CharField(max_length=200, default=get_rand_hash)
    secret = models.CharField(max_length=200, default=get_rand_hash)

    def __unicode__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    favorite_color = models.CharField(max_length=20,
            help_text="English or hex")

    def __unicode__(self):
        return "User Profile for %s" % self.user.username

########NEW FILE########
__FILENAME__ = settings
import os

# Django settings for data project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

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
SECRET_KEY = '6(^ekkhk_z&amp;675na=rg5r3xl#+9c8y+==*-u%jh@@ut7g9jl7m'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'data.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'data.wsgi.application'

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
    'django.contrib.admin',
    'data'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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


FRONTEND_KEY = os.environ.get('FRONTEND_KEY', None)
FRONTEND_SECRET = os.environ.get('FRONTEND_SECRET', None)


assert FRONTEND_KEY and FRONTEND_SECRET


CONSUMERS = {
    FRONTEND_KEY: {
        'name': 'Front end',
        'active': True,
        'secret': FRONTEND_SECRET
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'data.views.index'),
    url(r'^authenticate$', 'data.views.authenticate'),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseNotAllowed, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from api import oauth_protected, jsonify
from models import User


@oauth_protected
@jsonify
def index(request, user):
    return {
        'favorite_color': user.userprofile.favorite_color
    }


@csrf_exempt
@jsonify
def authenticate(request):
    if request.method != 'POST':
        raise HttpResponseNotAllowed()

    username = request.POST.get('username')
    password = request.POST.get('password')

    try:
        user = User.objects.get(username=username, password=password)
    except User.DoesNotExist:
        raise HttpResponseForbidden()

    return {
        'token': user.token,
        'secret': user.secret
    }

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for data project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = fabfile
from uuid import uuid4 as _uid
import hashlib
import random


try:
    random = random.SystemRandom()
except:
    pass


allowed_chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'


def _get_random_string(length=12, allowed_chars=allowed_chars):
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def _get_rand_hash():
    uid = _uid()
    return hashlib.sha1(str(uid)).hexdigest()


def secret():
    """
    Generate a Flask/Django session secret
    """
    print _get_random_string(50)


def oauth():
    """
    Generate two OAuth safe sha1 hashes
    """
    print _get_rand_hash()
    print _get_rand_hash()

########NEW FILE########
__FILENAME__ = api
import os
import json
import requests
from oauth_hook import OAuthHook

FRONTEND_KEY = os.environ.get('FRONTEND_KEY', None)
FRONTEND_SECRET = os.environ.get('FRONTEND_SECRET', None)
DATA_HOST = "http://127.0.0.1:8000"


assert FRONTEND_KEY and FRONTEND_SECRET


def make_request(user, url):
    OAuthHook.consumer_key = FRONTEND_KEY
    OAuthHook.consumer_secret = FRONTEND_SECRET
    hook = OAuthHook(access_token=user['access_token'],
            access_token_secret=user['access_token_secret'], header_auth=True)
    client = requests.session(hooks={'pre_request': hook})

    response = client.get(DATA_HOST + url)

    if response.status_code != 200:
        return None

    return json.loads(response.content)


def authenticate(username, password):
    credentials = {
        'username': username,
        'password': password
    }
    response = requests.post(DATA_HOST + "/authenticate",  credentials)

    if response.status_code == 200:
        data = json.loads(response.content)
        return data['token'], data['secret']
    else:
        return None, None

# API methods ----------------------------------------------------------------


def get_color(user):
    return make_request(user, "/")

########NEW FILE########
__FILENAME__ = app
from flask import Flask, request, session, redirect, url_for
from api import get_color, authenticate


app = Flask(__name__)
app.secret_key = "2@-s4=@i!7xnc(ee8#x4!$$k^evqin19ehszf14178&_!$gq5k"


@app.route('/')
def index():
    if "token" not in session:
        return redirect(url_for('login'))

    user = {
        'access_token': session.get('token'),
        'access_token_secret': session.get('secret')
    }

    data = get_color(user)

    if not data:
        return ('Forbidden', 403)

    return """
    <html>
    <head>
    <style>
        body {
            background: %s;
        }
    </style>
    </head>
    <body>
    <h1>Hello there</h1>
    <p>Your favorite color is %s.  We've also colored the background as such.</p>
    <p><a href="/logout">Logout</a></p>
    </body>
    </html>
    """ % (data['favorite_color'], data['favorite_color'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        token, secret = authenticate(request.form['username'],
            request.form['password'])
        if token and secret:
            session['token'] = token
            session['secret'] = secret
        return redirect(url_for('index'))
    return """
        <form action="" method="post">
            <p>Username: <input type="text" name="username"></p>
            <p>Password: <input type="password" name="password"></p>
            <p><input type="submit" value="Login"></p>
        </form>
        <p><a href="/logout">Logout</a></p>
    """


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(port=4444, debug=True)

########NEW FILE########
