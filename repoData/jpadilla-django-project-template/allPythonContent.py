__FILENAME__ = fabfile
from fabric.api import *

# current_git_branch = local('git symbolic-ref HEAD', capture=True).split('/')[-1]


# === Environments ===
def development():
    env.env = 'development'
    env.settings = '{{ project_name }}.settings.development'


def staging():
    env.env = 'staging'
    env.settings = '{{ project_name }}.settings.staging'
    env.remote = ''
    env.heroku_app = ''


def production():
    env.env = 'production'
    env.settings = '{{ project_name }}.settings.production'
    env.remote = ''
    env.heroku_app = ''


# Default Environment
development()


# === Deployment ===
def deploy():
    local('git push {remote}'.format(**env))


# === Static assets stuff ===
def collectstatic():
    # brunchbuild()
    local('python manage.py collectstatic --noinput -i app -i config.coffee \
            -i node_modules -i package.json --settings={settings}'.format(**env))
    # if env.env != 'development':
    #     commit_id = local('git rev-parse HEAD', capture=True)
    #     _config_set(key='HEAD_COMMIT_ID', value=commit_id)


def brunchwatch(app_name='core'):
    local('cd {{ project_name }}/%s/static/ && brunch w' % app_name)


def brunchbuild(app_name='core'):
    with settings(warn_only=True):
        local('rm -r {{ project_name }}/%s/static/public/' % app_name)
    local('cd {{ project_name }}/%s/static/ && brunch b -m' % app_name)


# === DB ===
def resetdb():
    if env.env == 'development':
        with settings(warn_only=True):
            local('rm dev.sqlite3')
        local('python manage.py syncdb --settings={settings}'.format(**env))
        local('python manage.py migrate --settings={settings}'.format(**env))
    else:

        if raw_input('\nDo you really want to RESET DATABASE of {heroku_app}? YES or [NO]: '.format(**env)) == 'YES':
            local('heroku run python manage.py syncdb --noinput --settings={settings} --app {heroku_app}'.format(**env))
            local('heroku run python manage.py migrate --settings={settings} --app {heroku_app}'.format(**env))
        else:
            print '\nRESET DATABASE aborted'


def schemamigration(app_names='core'):
    local('python manage.py schemamigration {app_names} --auto --settings={settings}'.format(app_names, **env))


def migrate():
    if env.env == 'development':
        local('python manage.py migrate --settings={settings}'.format(**env))
    else:

        if raw_input('\nDo you really want to MIGRATE DATABASE of {heroku_app}? YES or [NO]: '.format(**env)) == 'YES':
            local('heroku run python manage.py migrate --settings={settings} --app {heroku_app}'.format(**env))
        else:
            print '\nMIGRATE DATABASE aborted'


def updatedb():
    schemamigration()
    migrate()


# === Heroku ===
def ps():
    local('heroku ps --app {heroku_app}'.format(**env))


def restart():
    if raw_input('\nDo you really want to RESTART (web/worker) {heroku_app}? YES or [NO]: '.format(**env)) == 'YES':
        local('heroku ps:restart web --app {heroku_app}'.format(**env))
    else:
        print '\nRESTART aborted'


def tail():
    local('heroku logs --tail --app {heroku_app}'.format(**env))


def shell():
    local('heroku run bash --app {heroku_app}'.format(**env))


def config():
    local('heroku config --app {heroku_app}'.format(**env))


def _config_set(key=None, value=None):
    if key and value:
        local('heroku config:set {}={} --app {heroku_app}'.format(key, value, **env))
    else:
        print '\nErr!'

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    ENVIRONMENT = os.getenv('ENVIRONMENT')

    if ENVIRONMENT == 'STAGING':
        settings = 'staging'
    elif ENVIRONMENT == 'PRODUCTION':
        settings = 'production'
    else:
        settings = 'development'

    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
        "{{ project_name }}.settings.{settings}".format(settings=settings))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = common
import os

#==============================================================================
# Generic Django project settings
#==============================================================================

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

SITE_ID = 1

TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGE_CODE = 'en-us'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '{{ secret_key }}'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    # 'django.contrib.admindocs',

    'south',
    'gunicorn',
    'django_extensions',

    # '{{ project_name }}.core'
)

#==============================================================================
# Calculation of directories relative to the project module location
#==============================================================================

ENVIRONMENT = os.getenv('ENVIRONMENT', 'DEVELOPMENT')

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PROJECT_NAME = PROJECT_PATH.split('/')[-1]


#==============================================================================
# Project URLS and media settings
#==============================================================================

ROOT_URLCONF = '{{ project_name }}.urls'

MEDIA_ROOT = ''
MEDIA_URL = ''

STATIC_ROOT = ''
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

#==============================================================================
# Templates
#==============================================================================

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

#==============================================================================
# Middleware
#==============================================================================

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

#==============================================================================
# Auth / security
#==============================================================================

#==============================================================================
# Miscellaneous project settings
#==============================================================================

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = '{{ project_name }}.wsgi.application'

#==============================================================================
# Third party app settings
#==============================================================================


#==============================================================================
# Logging
#==============================================================================

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
__FILENAME__ = development
import os

from {{ project_name }}.settings.common import *

#==============================================================================
# Generic Django project settings
#==============================================================================

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dev.sqlite3',
    }
}

########NEW FILE########
__FILENAME__ = production
import dj_database_url

from {{ project_name }}.settings.common import *

#==============================================================================
# Generic Django project settings
#==============================================================================

DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': dj_database_url.config()
}

########NEW FILE########
__FILENAME__ = staging
import dj_database_url

from {{ project_name }}.settings.common import *

#==============================================================================
# Generic Django project settings
#==============================================================================

DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': dj_database_url.config()
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', '{{ project_name }}.views.home', name='home'),
    # url(r'^{{ project_name }}/', include('{{ project_name }}.foo.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for {{ project_name }} project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)
########NEW FILE########
