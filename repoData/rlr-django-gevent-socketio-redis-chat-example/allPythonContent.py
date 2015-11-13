__FILENAME__ = run_gevent
from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

from gevent import monkey
from socketio import SocketIOServer

class Command(BaseCommand):
    args = '<port_number>'
    help = 'Start the chat server. Takes an optional arg (port #).'

    def handle(self, *args, **options):
        """Run gevent socketio server."""
        try:
            port = int(args[0])
        except:
            port = 8000

        # Make blocking calls in socket lib non-blocking:
        monkey.patch_all()

        # Start up gevent-socketio stuff
        application = WSGIHandler()
        print 'Listening on http://127.0.0.1:%s and on port 843 (flash policy server)' % port
        SocketIOServer(('', port), application, resource='socket.io').serve_forever()

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
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('chatapp1.views',
    url(r'^$', 'chat', name='chatapp1'),
)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext

from gevent import Greenlet
from redis import Redis


def chat(request):
    """Render the chat page."""
    return render_to_response('chatapp1/chat.html', {}, RequestContext(request))


def socketio(request):
    """The socket.io view."""
    io = request.environ['socketio']
    redis_sub = redis_client().pubsub()
    user = username(request.user)

    # Subscribe to incoming pubsub messages from redis.
    def subscriber(io):
        redis_sub.subscribe(room_channel())
        redis_client().publish(room_channel(), user + ' connected.')
        while io.connected():
            for message in redis_sub.listen():
                if message['type'] == 'message':
                    io.send(message['data'])
    greenlet = Greenlet.spawn(subscriber, io)

    # Listen to incoming messages from client.
    while io.connected():
        message = io.recv()
        if message:
            redis_client().publish(room_channel(), user + ': ' + message[0])

    # Disconnected. Publish disconnect message and kill subscriber greenlet.
    redis_client().publish(room_channel(), user + ' disconnected')
    greenlet.throw(Greenlet.GreenletExit)

    return HttpResponse()


def redis_client():
    """Get a redis client."""
    return Redis(settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB,
                 socket_timeout=0.5)


def username(user):
    if user.is_authenticated():
        return user.username
    else:
        return 'guest-{n}'.format(n=redis_client().incr('chat:anonid'))


def room_channel(name='default'):
    """Get redis pubsub channel key for given chat room."""
    return 'chat:rooms:{n}'.format(n=name)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys
import imp

from django.core.management import execute_manager


try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

sys.path.insert(0, os.path.join(settings.ROOT, "apps"))

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for chatproject project.
import os


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)
ROOT_PACKAGE = os.path.basename(ROOT)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
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
TIME_ZONE = 'America/New_York'

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
MEDIA_ROOT = path('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

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
    path('static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '4r3*4_#s$5@m=d4x6wg_y9w^-e7w$o1n!q#m674kujubbr2sa2'

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
)

ROOT_URLCONF = '%s.urls' % ROOT_PACKAGE

TEMPLATE_DIRS = (
    path('templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'chatapp1',
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

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.simple import redirect_to


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', redirect_to, {'url': '/chatapp1'}, name='home.default'),
    url(r'chatapp1', include('chatapp1.urls')),
    url(r'^admin/', include(admin.site.urls)),

    # socket.io endpoint
    url(r'^socket\.io', 'chatapp1.views.socketio', name='chatapp1.socketio')
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
