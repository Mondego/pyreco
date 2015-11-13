__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "podbadge.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
__author__ = 'flaviocaetano'

########NEW FILE########
__FILENAME__ = settings
#coding: utf-8
# Django settings for podbadge project.

import os
PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    (u'Flávio Caetano', 'flavio@vieiracaetano.com'),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ''
    }
}

SHIELD_SERVICE = 'go-shields.herokuapp.com'
SHIELD_COLOR = 'D07D1D'

MANAGERS = ADMINS

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']

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
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static/')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths
    # os.path.join(PROJECT_ROOT, "static"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'b4bt)y3)6l%u2mma@fjl!&1jfx6k^7n%f&2fj5@4!1115(jr93'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
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

ROOT_URLCONF = 'podbadge.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'podbadge.wsgi.application'

TEMPLATE_DIRS = (os.path.join(
    os.path.dirname(__file__),
    '..',
    'templates').replace('\\', '/'),
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
    'podbadge'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['mail_admins', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.views.generic import RedirectView

# from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', RedirectView.as_view(
        url='http://fjcaetano.github.io/cocoapod-badges'
    )),

    url(r'^p', include('podbadge.views.platform')),
    url(r'^v', include('podbadge.views.version')),
)

########NEW FILE########
__FILENAME__ = helpers
__author__ = 'Flavio'

from django.conf import settings
from django.utils import simplejson

import urllib
import urllib2
import mimetypes


def prepare_shield(vendor, status):
    url = shield_url(vendor, clean_info(status))
    return fetch_shield(url)


def shield_url(vendor, status):

    return 'http://%(service)s/%(vendor)s-%(status)s-%(color)s.png' % {
        'service': settings.SHIELD_SERVICE,
        'color': settings.SHIELD_COLOR,
        'vendor': vendor,
        'status': status,
        }


def fetch_shield(url):
    contents = urllib2.urlopen(url).read()
    mimetype = mimetypes.guess_type(url)

    return contents, mimetype


def clean_info(info):
    clean = info.replace('-', '--').replace(' ', '_')
    return urllib.quote(clean)


def get_pod_info(podname):
    url = 'http://search.cocoapods.org/api/v1/pod/%s.json' % (podname, )

    response = urllib2.urlopen(url)
    return simplejson.loads(response.read())
########NEW FILE########
__FILENAME__ = platform
__author__ = 'Flavio'

from django.views.generic.base import View
from django.views.decorators.cache import never_cache
from django.http import HttpResponse

from podbadge.utils import helpers


class PlatformView(View):
    template_name = 'badge_platform.html'

    @never_cache
    def get(self, request, podname, retina=None):

        try:
            pod_info = helpers.get_pod_info(podname)

            platforms = pod_info.get('platforms', {'osx': '', 'ios': ''}).keys()

            platforms = '|'.join(platforms)
        except Exception:
            platforms = 'error'

        contents, mimetype = helpers.prepare_shield('platform', platforms)
        return HttpResponse(contents, mimetype=mimetype[0])

############
### URLS ###
############

from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^/(?P<podname>.*?)/badge(?:(?P<retina>@2x))?.(?:(png|svg))$', PlatformView.as_view()),
)
########NEW FILE########
__FILENAME__ = version
__author__ = 'Flavio'

from django.views.generic.base import View
from django.views.decorators.cache import never_cache
from django.http import HttpResponse

from podbadge.utils import helpers

import urllib2
import mimetypes

class VersionView( View ):
    template_name = 'badge_version.html'

    @never_cache
    def get(self, request, podname, version=None, retina=None):
        if not version:
            try:
                pod_info = helpers.get_pod_info(podname)

                version = pod_info['version']
            except Exception, e:
                version = 'error'

        contents, mimetype = helpers.prepare_shield('version', version)
        return HttpResponse(contents, mimetype=mimetype[0])

############
### URLS ###
############

from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^/(?P<podname>.*?)/(?P<version>.*?)/badge(?:(?P<retina>@2x))?.(?:(png|svg))$', VersionView.as_view()),
    url(r'^/(?P<podname>.*?)/badge(?:(?P<retina>@2x))?.(?:(png|svg))$', VersionView.as_view()),
)
########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for podbadge project.

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

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "podbadge.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "podbadge.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
