__FILENAME__ = models
from django.db import models

########NEW FILE########
__FILENAME__ = views
import time
from simplejson import dumps
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext

# ZeroMQ Connection
from gevent import spawn
from gevent_zeromq import zmq

context = zmq.Context()
publisher = context.socket(zmq.PUB)
publisher.bind("tcp://127.0.0.1:5000")

ACTIVE_ROOMS = set([])

# Message Coroutines

def send_message(socket, room, text):
    socket.send_unicode("%s:%s" % (room, text))

def message_listener(socketio, room):
    # For too many threads spawning new connection will cause a
    # "too many mailboxes" error, but for small amounts of
    # threads this is fine.

    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://127.0.0.1:5000")

    # setsockopt doesn't like unicode
    subscriber.setsockopt(zmq.SUBSCRIBE, str(room))

    socketio.send({'message': 'connected: ' + room})

    while True:
        msg = subscriber.recv()
        if msg:
            socketio.send({'message': msg.split(":")[1]})

# Room Coroutines

def new_room(socket, room_name):
    socket.send("room:%s" % str(room_name))

def room_listener(socketio):
    # For too many threads spawning new connection will cause a
    # "too many mailboxes" error, but for small amounts of
    # threads this is fine.

    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://127.0.0.1:5000")
    subscriber.setsockopt(zmq.SUBSCRIBE, 'room')

    while True:
        msg = subscriber.recv()
        if msg:
            socketio.send({'room_name': msg.split(":")[1]})

        time.sleep(5)

def room(request, room_name=None, template_name='room.html'):
    context = {
        'room_name': room_name,
        'initial_rooms': dumps(list(ACTIVE_ROOMS)),
    }

    if room_name not in ACTIVE_ROOMS:
        spawn(new_room, publisher, room_name)
        ACTIVE_ROOMS.add(room_name)

    return render_to_response(template_name, context,
            context_instance=RequestContext(request))

def room_list(request, template_name='room_list.html'):
    context = {
        'initial_rooms': dumps(list(ACTIVE_ROOMS)),
    }

    return render_to_response(template_name, context,
            context_instance=RequestContext(request))

# SocketIO Handler

def socketio(request):
    socketio = request.environ['socketio']

    while True:
        message = socketio.recv()

        if len(message) == 1:
            action, arg = message[0].split(':')

            if action == 'subscribe':

                if arg == 'rooms':
                    spawn(room_listener, socketio)
                else:
                    spawn(message_listener, socketio, arg)

            elif action == 'message':
                room, text = arg.split(',')

                #timestamp = time.strftime("(%H.%M.%S)", time.localtime())
                ip_addr = request.META['REMOTE_ADDR']
                message = "(%s)  %s" % (ip_addr, text)
                spawn(send_message, publisher, room, message).join()

    return HttpResponse()



########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from django.core.management import execute_manager

import sys, os
import settings

sys.path.insert(0, os.path.join(settings.PROJECT_ROOT, "apps"))

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python

from gevent import monkey
monkey.patch_all()

import os
import sys

import django.core.handlers.wsgi
from socketio import SocketIOServer

import settings

PORT = 8080

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
application = django.core.handlers.wsgi.WSGIHandler()

sys.path.insert(0, os.path.join(settings.PROJECT_ROOT, "apps"))

if __name__ == '__main__':
    print('Listening on http://127.0.0.1:%s' % PORT)
    SocketIOServer(('', PORT), application, resource="socket.io").serve_forever()

########NEW FILE########
__FILENAME__ = settings
import os

PROJECT_ROOT = os.path.dirname(__file__)

LOGIN_URL = '/users/login/'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# You don't need a database to run this FYI
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'dev.db'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
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
    os.path.join(PROJECT_ROOT, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'krchb00kt9s@#)phw^g1%w32@ic7qs!_$7^)=l%!#b2qysr0+9'

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

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
        "django.contrib.auth.context_processors.auth",
        "django.core.context_processors.debug",
        "django.core.context_processors.i18n",
        "django.core.context_processors.media",
        "django.core.context_processors.request",
        "django.core.context_processors.static",
        "django.contrib.messages.context_processors.messages",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'django.contrib.admin',
    'chat',
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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

from chat.views import (
        room,
        room_list,
        socketio
)

urlpatterns = patterns('',

    # A list of chatrooms
    url(
        regex=r'^$',
        view=room_list,
        name='room_list'
    ),

    # A specific chatroom
    url(
        regex=r'^room/(?P<room_name>.*)$',
        view=room,
        name='room'
    ),

    # Socket IO hook
    url(
        regex=r'^socket\.io',
        view=socketio,
        name='socketio'
    ),
)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
