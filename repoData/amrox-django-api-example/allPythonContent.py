__FILENAME__ = resources
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authentication import OAuthAuthentication
from tastypie.authorization import DjangoAuthorization

from django.contrib.auth.models import User
from tasks.models import Task

class UserResource(ModelResource):
    tasks = fields.ToManyField('api.resources.TaskResource', 'task_set', related_name='user')

    class Meta:
        queryset = User.objects.all()
        resource_name = 'users'
        excludes = ['email', 'password', 'is_active', 'is_staff', 'is_superuser']
        authentication = OAuthAuthentication()
        authorization = DjangoAuthorization()

    #def apply_authorization_limits(self, request, object_list):
    #    return object_list.filter(self=request.user)

class TaskResource(ModelResource):
    user = fields.ToOneField(UserResource, 'user', full=False)

    class Meta:
        queryset = Task.objects.all()
        resource_name = 'tasks'
        authentication = OAuthAuthentication()
        authorization = DjangoAuthorization()

    # Creating per-user resources:
    # http://django-tastypie.readthedocs.org/en/latest/cookbook.html#creating-per-user-resources

    def obj_create(self, bundle, request=None, **kwargs):
        return super(TaskResource, self).obj_create(bundle, request, user=request.user)

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)



########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

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
__FILENAME__ = middleware
#from django import http

# adapted from http://djangosnippets.org/snippets/2472/

class CloudMiddleware(object):
    def process_request(self, request):
        if 'HTTP_X_FORWARDED_PROTO' in request.META:
            if request.META['HTTP_X_FORWARDED_PROTO'] == 'https':
                request.is_secure = lambda: True
        return None




########NEW FILE########
__FILENAME__ = settings
import os
from settings_base import *

# (production, staging, development, local)
deploy_config = os.getenv('DEPLOY_CONFIG')

if deploy_config == 'production':
    from settings_production import *
else:
    from settings_local import *

########NEW FILE########
__FILENAME__ = settings_base
# Django settings for django_api_example project.

import os.path

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
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
SECRET_KEY = '+&4x8flqhd=#koe817n47ayb=7r%4g1#a&zg(lk6n(hs_qpyr!'

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
    'middleware.CloudMiddleware',
)

ROOT_URLCONF = 'django_api_example.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'oauth_provider',
    'tasks',
    'api'
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

# OAuth Settings

OAUTH_BLACKLISTED_HOSTNAMES = ['localhost', '127.0.0.1']
OAUTH_SIGNATURE_METHODS = ['hmac-sha1',]

########NEW FILE########
__FILENAME__ = settings_local
from settings_base import *
import posixpath

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '../data/db.sqlite',
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

STATIC_ROOT = os.path.join(PROJECT_ROOT, "static")
STATIC_URL = "/static/"
ADMIN_MEDIA_PREFIX = posixpath.join(STATIC_URL, "admin/")

DEBUG = True
TEMPLATE_DEBUG = DEBUG
SERVE_MEDIA = DEBUG

DEBUG_PROPAGATE_EXCEPTIONS = True

########NEW FILE########
__FILENAME__ = settings_production
from settings_base import *
import posixpath

# database settings are injected by heroku automatically

# Debug Media serving settings
#
# DON'T ACTUALLY SHIP WITH THESE SETTINGS
# 

STATIC_ROOT = os.path.join(PROJECT_ROOT, "static")
STATIC_URL = "/static/"
ADMIN_MEDIA_PREFIX = posixpath.join(STATIC_URL, "admin/")

DEBUG = False
SERVE_MEDIA = DEBUG

########NEW FILE########
__FILENAME__ = admin
from models import Task

from django.contrib import admin

admin.site.register(Task)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class Task(models.Model):
    """Models an individual task"""
    user = models.ForeignKey(User)
    text = models.TextField()
    complete = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=datetime.now())

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

from tastypie.api import Api
from api.resources import UserResource, TaskResource

v1_api = Api(api_name='v1')
v1_api.register(UserResource())
v1_api.register(TaskResource())

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'django_api_example.views.home', name='home'),
    # url(r'^django_api_example/', include('django_api_example.foo.urls')),

    url(r'^$', direct_to_template, {'template': 'index.html'}),
    url(r'^oauth/', include('oauth_provider.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include(v1_api.urls)),
)

########NEW FILE########
__FILENAME__ = client
"""
The MIT License

Copyright (c) 2012 Andy Mroczkowski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Example consumer. This is not recommended for production.
Instead, you'll want to create your own subclass of OAuthClient
or find one that works with your web framework.
"""

import oauth2 as oauth
import urllib
import urlparse

#############################################################################
# Get Access Token with xAuth
#############################################################################

# Basic Configuration.
# You'll probably need to change these.
consumer_key = 'consumer'
consumer_secret = 'secret'
host = 'django-api-example.herokuapp.com'
#host = 'localhost:8000'
username = 'test'
password = 'test'

access_token_url = 'http://%s/oauth/access_token/' % (host)

consumer = oauth.Consumer(consumer_key, consumer_secret)
client = oauth.Client(consumer)

# Set xAuth parameters
params = dict()
params['x_auth_username'] = username
params['x_auth_password'] = password
params['x_auth_mode'] = 'client_auth'

resp, token = client.request(access_token_url, method="POST",body=urllib.urlencode(params))

if resp.status / 100 != 2:
    print resp
    print token
    exit(1)
else:
    access_token = dict(urlparse.parse_qsl(token))
    print access_token

# Parse access token
token = oauth.Token(access_token['oauth_token'], access_token['oauth_token_secret'])

# and create a new client with that token
client = oauth.Client(consumer, token)

#############################################################################
# Access a protected URL using OAuth access token
#############################################################################


# Basic Configuration.
# You'll need to change these.
protected_url = 'http://%s/api/v1/tasks/' % (host)
protected_url_method = 'GET'

resp, content = client.request(protected_url, protected_url_method)
if resp.status / 100 != 2:
    print resp
print '%s %s ->\n %s' % (protected_url_method, protected_url, content)


########NEW FILE########
