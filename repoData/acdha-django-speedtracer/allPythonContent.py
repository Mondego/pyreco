__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for example_project project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dev.db',
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
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '##g-qj0@4-@spjqp!#w2#(h^oag^9#wr3kzdji8m(ychwplvea'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'speedtracer.middleware.SpeedTracerMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.flatpages',

    'speedtracer',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = middleware
# encoding: utf-8

import os
import re
import inspect
import time
import uuid
import sys

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.utils import simplejson


class SpeedTracerMiddleware(object):
    """
    Record server-side performance data for Google Chrome's SpeedTracer

    Getting started:

    1. Download and install Speed Tracer:
        http://code.google.com/webtoolkit/speedtracer/get-started.html
    2. Add this middleware to your MIDDLEWARE_CLASSES
    3. Reload your page
    4. Open SpeedTracer and expand the "Server Trace" in the page's detailed
       report which should look something like http://flic.kr/p/8kwEw3

    NOTE: Trace data is store in the Django cache. Yours must be functional.
    """

    #: Traces will be stored in the cache with keys using this prefix:
    CACHE_PREFIX = getattr(settings, "SPEEDTRACER_CACHE_PREFIX", 'speedtracer-%s')

    #: Help debug SpeedTracerMiddleware:
    DEBUG = getattr(settings, 'SPEEDTRACER_DEBUG', False)

    #: Trace into Django code:
    TRACE_DJANGO = getattr(settings, 'SPEEDTRACER_TRACE_DJANGO', False)

    #: Trace data will be retrieved from here:
    TRACE_URL = getattr(settings, "SPEEDTRACER_API_URL", '/__speedtracer__/')

    def __init__(self):
        self.traces = []
        self.call_stack = []

        file_filter = getattr(settings, "SPEEDTRACER_FILE_FILTER_RE", None)
        if isinstance(file_filter, basestring):
            file_filter = re.compile(file_filter)
        elif file_filter is None:
            # We'll build a list of installed app modules from INSTALLED_APPS
            app_dirs = set()
            for app in settings.INSTALLED_APPS:
                try:
                    if app.startswith("django.") and not self.TRACE_DJANGO:
                        continue

                    for k, v in sys.modules.items():
                        if k.startswith(app):
                            app_dirs.add(*sys.modules[app].__path__)
                except KeyError:
                    print >>sys.stderr, "Can't get path for app: %s" % app

            app_dir_re = "(%s)" % "|".join(map(re.escape, app_dirs))

            print  >> sys.stderr, "Autogenerated settings.SPEEDTRACER_FILE_FILTER_RE: %s" % app_dir_re

            file_filter = re.compile(app_dir_re)

        self.file_filter = file_filter

    def trace_callback(self, frame, event, arg):
        if not event in ('call', 'return'):
            return

        if not self.file_filter.match(frame.f_code.co_filename):
            return # No trace

        if self.DEBUG:
            print "%s: %s %s[%s]" % (
                event,
                frame.f_code.co_name,
                frame.f_code.co_filename,
                frame.f_lineno,
            )

        if event == 'call':
            code = frame.f_code

            class_name = module_name = ""

            module = inspect.getmodule(code)
            if module:
                module_name = module.__name__

            try:
                class_name = frame.f_locals['self'].__class__.__name__
            except (KeyError, AttributeError):
                pass

            new_record = {
                'operation':  {
                    'sourceCodeLocation':  {
                        'className'  :  frame.f_code.co_filename,
                        'methodName' :  frame.f_code.co_name,
                        'lineNumber' :  frame.f_lineno,
                    },
                    'type':  'METHOD',
                    'label':  '.'.join(filter(None, (module_name, class_name, frame.f_code.co_name))),
                },
                'children':  [],
                'range': {"start_time": time.time() },
            }

            new_record['id'] = id(new_record)

            self.call_stack.append(new_record)

            return self.trace_callback

        elif event == 'return':
            end_time = time.time()

            if not self.call_stack:
                print >>sys.stderr, "Return without stack?"
                return

            current_frame = self.call_stack.pop()

            current_frame['range'] = self._build_range(current_frame['range']["start_time"], end_time)

            if not self.call_stack:
                self.traces.append(current_frame)
            else:
                self.call_stack[-1]['children'].append(current_frame)

            return

    def process_request(self, request):
        if request.path.endswith("symbolmanifest.json"):
            raise Http404

        if not request.path.startswith(self.TRACE_URL):
            request._speedtracer_start_time = time.time()
            sys.settrace(self.trace_callback)
            return

        trace_id = self.CACHE_PREFIX % request.path[len(self.TRACE_URL):]

        data = cache.get(trace_id, {})

        return HttpResponse(simplejson.dumps(data), mimetype="application/json; charset=UTF-8")

    def process_response(self, request, response):
        sys.settrace(None)

        try:
            start_time = request._speedtracer_start_time
        except AttributeError:
            return response

        end_time = time.time()

        trace_id = uuid.uuid4()

        data = {
            'trace':  {
                'id':  str(trace_id),
                'application': 'Django SpeedTracer',
                'date':  time.time(),
                'range': self._build_range(start_time, end_time),
                'frameStack':  {
                    'id': 0,
                    'range': self._build_range(start_time, end_time),
                    'operation':  {
                        'type':  'HTTP',
                        'label':  "%s %s" % (request.method, request.path)
                    },
                    'children': self.traces,
                }
            }
        }

        cache.set(self.CACHE_PREFIX % trace_id, data, getattr(settings, "SPEEDTRACER_TRACE_TTL", 3600))

        response['X-TraceUrl'] = "%s%s" % (self.TRACE_URL, trace_id)

        return response

    def _build_range(self, start_time, end_time):
        return {
            "start": start_time,
            "end": end_time,
            "duration": end_time - start_time,
        }

########NEW FILE########
