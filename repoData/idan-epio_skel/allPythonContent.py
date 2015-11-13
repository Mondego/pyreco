__FILENAME__ = epio_flush_cache
from django.core.cache import cache

from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = 'Flushes the cache.'

    def handle_noargs(self, **options):
        cache.clear()
        print "Cache flushed."

########NEW FILE########
__FILENAME__ = epio_flush_redis
import redis
from bundle_config import config

from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = 'Flushes all keys in redis.'

    def handle_noargs(self, **options):
        r = redis.Redis(host=config['redis']['host'], port=int(config['redis']['port']), password=config['redis']['password'])
        r.flushall()
        print "All redis keys flushed."

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import local, env

def production():
    env['epioapp'] = # production epio instance name

def staging():
    env['epioapp'] = # staging epio instance

def epio(commandstring):
    local("epio {0} -a {1}".format(
        commandstring,
        env['epioapp']))

def deploy():
    """ An example deploy workflow """
    local("./manage.py collectstatic")
    epio('upload')
    epio('django syncdb')
    epio('django migrate')
    epio('django epio_flush_cache')


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
__FILENAME__ = base
from unipath import FSPath as Path

PROJECT_DIR = Path(__file__).absolute().ancestor(2)

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True

MEDIA_ROOT = PROJECT_DIR.child('media')
MEDIA_URL = '/media/'

STATIC_ROOT = PROJECT_DIR.child('static_root')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    str(PROJECT_DIR.child('static')),
)
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = # Put your secret key here. Django defaults to a 50-char string.

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
    PROJECT_DIR.child('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'epio_commands',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

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
__FILENAME__ = epio
from __future__ import absolute_import
from .base import *

from bundle_config import config
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config['postgres']['database'],
        'USER': config['postgres']['username'],
        'PASSWORD': config['postgres']['password'],
        'HOST': config['postgres']['host'],
    }
}

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '{host}:{port}'.format(
                host=config['redis']['host'],
                port=config['redis']['port']),
        'OPTIONS': {
            'PASSWORD': config['redis']['password'],
        },
        'VERSION': config['core']['version'],
    },
}
MEDIA_ROOT = config['core']['data_directory']

# CELERY SETTINGS
# ===============

# Uncomment if you're using Celery on ep.io.

# CELERY_RESULT_BACKEND = "redis"
# REDIS_HOST = config['redis']['host']
# REDIS_PORT = int(config['redis']['port'])
# REDIS_PASSWORD = config['redis']['password']
# REDIS_DB = int(config['redis']['database'])
# REDIS_CONNECT_RETRY = True

# BROKER_BACKEND = 'redis'
# BROKER_HOST = config['redis']['host']
# BROKER_PORT = int(config['redis']['port'])
# BROKER_PASSWORD = config['redis']['password']
# BROKER_VHOST = int(config['redis']['database'])

# import djcelery
# djcelery.setup_loader()

########NEW FILE########
__FILENAME__ = local
from __future__ import absolute_import
from .base import *

# Configure these however you like for local development.
# Don't forget to configure a database!

# DEBUG=True
# TEMPLATE_DEBUG=DEBUG

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#         'NAME': '',                      # Or path to database file if using sqlite3.
#         'USER': '',                      # Not used with sqlite3.
#         'PASSWORD': '',                  # Not used with sqlite3.
#         'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#         'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
#     }
# }
#
# CACHES = {
#     'default': {
#         'BACKEND': 'redis_cache.RedisCache',
#         'LOCATION': 'localhost:6379',
#     },
# }
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'epio_skel.views.home', name='home'),
    # url(r'^epio_skel/', include('epio_skel.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
