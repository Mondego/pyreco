__FILENAME__ = socketserver
from optparse import make_option
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.importlib import import_module
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--port',
            action='store',
            dest='port',
            default=getattr(settings, 'SOCKJS_PORT', 9999),
            help='What port number to run the socket server on'),
        make_option(
            '--no-keep-alive',
            action='store_true',
            dest='no_keep_alive',
            default=False,
            help='Set no_keep_alive on the connection if your server needs it')
    )

    def handle(self, **options):
        if len(settings.SOCKJS_CLASSES) > 1:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "Multiple connections not yet supported"
            )

        module_name, cls_name = settings.SOCKJS_CLASSES[0].rsplit('.', 1)
        module = import_module(module_name)
        cls = getattr(module, cls_name)
        channel = getattr(settings, 'SOCKJS_CHANNEL', '/echo')
        if not channel.startswith('/'):
            channel = '/%s' % channel

        router = SockJSRouter(cls, channel)
        app_settings = {
            'debug': settings.DEBUG,
        }

        PORT = int(options['port'])
        app = web.Application(router.urls, **app_settings)
        app.listen(PORT, no_keep_alive=options['no_keep_alive'])
        print "Running sock app on port", PORT, "with channel", channel
        try:
            ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            # so you don't think you errored when ^C'ing out
            pass

########NEW FILE########
__FILENAME__ = models
# Hi! I'm a django app!

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models
from django.utils.timezone import utc

def now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)


class Message(models.Model):
    name = models.CharField(max_length=200)
    message = models.TextField()
    date = models.DateTimeField(default=now)

########NEW FILE########
__FILENAME__ = sockserver
import json
from sockjs.tornado import SockJSConnection
from .models import Message


class ChatConnection(SockJSConnection):
    _connected = set()

    def on_open(self, request):
        #print "OPEN"
        #print request.get_cookie('name')
        self._connected.add(self)
        for each in Message.objects.all().order_by('date')[:10]:
            self.send(self._package_message(each))

    def on_message(self, data):
        data = json.loads(data)
        #print "DATA", repr(data)
        msg = Message.objects.create(
            name=data['name'],
            message=data['message']
        )
        self.broadcast(self._connected, self._package_message(msg))

    def on_close(self):
        #print "CLOSE"
        self._connected.remove(self)

    def _package_message(self, m):
        return {'date': m.date.strftime('%H:%M:%S'),
                'message': m.message,
                'name': m.name}

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
from django.conf.urls import patterns, include, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.home, name='home'),
)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.shortcuts import render


def home(request):
    return render(request, 'chat/home.html', {
        'socket_port': settings.SOCKJS_PORT,
        'socket_channel': settings.SOCKJS_CHANNEL
    })

########NEW FILE########
__FILENAME__ = settings
# Django settings for project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'database.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
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
SECRET_KEY = 'i^4eorm*^ol6k#hg9tg*#1x+i!$t+hqg__7o^)fwa#lxw%q#kt'

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

ROOT_URLCONF = 'project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'project.wsgi.application'

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
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django_sockjs_tornado',
    'project.chat',
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



SOCKJS_PORT = 9999
SOCKJS_CHANNEL = 'echo'
SOCKJS_CLASSES = (
    'project.chat.sockserver.ChatConnection',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = patterns('',
    url(r'', include('project.chat.urls')),
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example_project project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
