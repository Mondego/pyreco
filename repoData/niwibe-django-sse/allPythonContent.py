__FILENAME__ = redisqueue
# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from redis import ConnectionPool as RedisConnectionPool
from redis import Redis

from redis.connection import UnixDomainSocketConnection, Connection
from redis.connection import DefaultParser

from .views import BaseSseView

import json


CONNECTION_KWARGS = getattr(settings, 'REDIS_SSEQUEUE_CONNECTION_SETTINGS', {})
DEFAULT_CHANNEL = getattr(settings, 'REDIS_SSEQUEUE_CHANEL_NAME', 'sse')


class ConnectionPoolManager(object):
    pools = {}

    @classmethod
    def key_for_kwargs(cls, kwargs):
        return ":".join([str(v) for v in kwargs.values()])

    @classmethod
    def connection_pool(cls, **kwargs):
        pool_key = cls.key_for_kwargs(kwargs)
        if pool_key in cls.pools:
            return cls.pools[pool_key]

        location = kwargs.get('location', None)
        if not location:
            raise ImproperlyConfigured("no `location` key on connection kwargs")

        params = {
            'connection_class': Connection,
            'db': kwargs.get('db', 0),
            'password': kwargs.get('password', None),
        }

        if location.startswith("unix:"):
            params['connection_class'] = UnixDomainSocketConnection
            params['path'] = location[5:]
        else:
            try:
                params['host'], params['port'] = location.split(":")
                params['port'] = int(params['port'])

            except ValueError:
                raise ImproperlyConfigured("Invalid `location` key syntax on connection kwargs")

        cls.pools[pool_key] = RedisConnectionPool(**params)
        return cls.pools[pool_key]


class RedisQueueView(BaseSseView):
    redis_channel = DEFAULT_CHANNEL

    def iterator(self):
        connection = _connect()
        pubsub = connection.pubsub()
        pubsub.subscribe(self.get_redis_channel())

        for message in pubsub.listen():
            if message['type'] == 'message':
                event, data = json.loads(message['data'].decode('utf-8'))
                self.sse.add_message(event, data)
                yield

    def get_redis_channel(self):
        return self.redis_channel


def _connect():
    pool = ConnectionPoolManager.connection_pool(**CONNECTION_KWARGS)
    return Redis(connection_pool=pool)


def send_event(event_name, data, channel=DEFAULT_CHANNEL):
    connection = _connect()
    connection.publish(channel, json.dumps([event_name, data]))


__all__ = ['send_event', 'RedisQueueView']

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

try:
    from django.http import StreamingHttpResponse as HttpResponse
except ImportError:
    from django.http import HttpResponse

from django.utils.decorators import method_decorator
from sse import Sse


class BaseSseView(View):
    """
    This is a base class for sse streaming.
    """

    def get_last_id(self):
        if "HTTP_LAST_EVENT_ID" in self.request.META:
            return self.request.META['HTTP_LAST_EVENT_ID']
        return None

    def _iterator(self):
        for subiterator in self.iterator():
            for bufferitem in self.sse:
                yield bufferitem

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        self.sse = Sse()

        self.request = request
        self.args = args
        self.kwargs = kwargs

        response = HttpResponse(self._iterator(), content_type="text/event-stream")
        response['Cache-Control'] = 'no-cache'
        response['Software'] = 'django-sse'
        return response

    def iterator(self):
        """
        This is a source of stream.
        Must use ``yield`` statement to flush
        content from sse object to the client.

        Example:

        def iterator(self):
            counter = 0
            while True:
                self.sse.add_message('foo', 'bar')
                self.sse.add_message('bar', 'foo')
                yield

        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = run_wsgi
# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()

#import sys
#sys.path.insert(0, '/home/niwi/devel/sse')


from gevent.pywsgi import WSGIServer
from wsgi import application

if __name__ == '__main__':
    server = WSGIServer(('0.0.0.0', 8888), application)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = settings
# Django settings for django_sse_example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

REDIS_SSEQUEUE_CONNECTION_SETTINGS = {
    'location': 'localhost:6379',
    'db': 0,
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
SECRET_KEY = 'fde@#9!6z@-4bb!-^=_x!eki8p%(f*bu9!jb=vj4#u$^&amp;a#e7$'

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

ROOT_URLCONF = 'django_sse_example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'django_sse_example.wsgi.application'

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
    'django_sse_example.web',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from .web.views import *
from django_sse.redisqueue import RedisQueueView

urlpatterns = patterns('',
    url(r'^home1/$', Home1.as_view(), name='home1'),
    url(r'^home2/$', Home2.as_view(), name='home2'),

    url(r'^events1/$', MySseEvents.as_view(), name='events1'),
    url(r'^events2/$', RedisQueueView.as_view(), name='events2'),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

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

from django.shortcuts import render_to_response
from django.views.generic import View
from django.template import RequestContext
from django.utils.timezone import now

from django_sse.views import BaseSseView

import time

class Home1(View):
    def get(self, request):
        return render_to_response('home.html', {},
            context_instance=RequestContext(request))


class Home2(View):
    def get(self, request):
        return render_to_response('home2.html', {},
            context_instance=RequestContext(request))


class MySseEvents(BaseSseView):
    def iterator(self):
        while True:
            self.sse.add_message("date", unicode(now()))
            time.sleep(1)
            yield

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for django_sse_example project.

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
import os, sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_sse_example.settings")
sys.path.insert(0, '..')
sys.path.insert(0, '../..')

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
import os, sys

sys.path.insert(0, '..')
#sys.path.insert(0, '/home/niwi/devel/sse')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_sse_example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
