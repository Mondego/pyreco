__FILENAME__ = fabfile
# Common fabric tasks

import os.path
from fabric.api import *
from fabric.contrib.project import rsync_project

# if you rename the project directory, update this
PROJECT_NAME = 'project'


def _cd_project_root():
    assert hasattr(env, 'project_path')
    return cd(env.project_path)


def _activate():
    assert hasattr(env, 'virtualenv')
    if '/' in env.virtualenv:
        return prefix('source ' + env.virtualenv + '/bin/activate')
    else:
        return prefix('source ~/.bash_profile 2>/dev/null || ' +
            'source ~/.profile 2>/dev/null || true &&' +
            'workon ' + env.virtualenv)


def env(venv):
    """Virtual environment to use on the server"""
    env.virtualenv = venv


def server(server):
    """Server to use"""
    env.hosts = [server]


def path(path):
    """Project path on the server"""
    env.project_path = path

# Base commands


def rsync():
    """Sync remote files to the server using rsync."""
    assert hasattr(env, 'project_path')
    local_dir = os.path.dirname(__file__) + '/'
    rsync_project(remote_dir=env.project_path, local_dir=local_dir,
        exclude=['media/', 'static/', '*.pyc', '.git/', 'dev.db'])


def manage(cmd):
    """Run Django management command on the server"""
    with _activate():
        with _cd_project_root():
            run('python manage.py ' + cmd)


def git_pull(remote='origin'):
    """Pull newest version from the git repository"""
    assert hasattr(env, 'project_path')
    with _cd_project_root():
        run('git pull ' + remote)


def git_clone(origin):
    """Create a new project instance by cloning the source repository"""
    assert hasattr(env, 'project_path')
    run('git clone %s %s' % (origin, env.project_path))


def git_tag_now(prefix):
    """Tag the current branch HEAD with a timestamp"""
    import datetime
    assert hasattr(env, 'project_path')
    with _cd_project_root():
        run('git tag %s-%s' % (prefix,
            datetime.datetime.now().strftime('-%Y-%m-%d-%H-%M-%S')))

# High-level commands


def install_requirements(env='prod'):
    """Install required Python packages (from requirements/<env>.txt)"""
    with _activate():
        with _cd_project_root():
            run('pip install -r %s/requirements.txt' % env)


def collectstatic():
    """Collect static files using collectstatic."""
    manage('collectstatic --noinput')


def syncdb():
    """Execute initial syncdb"""
    manage('syncdb')


def migrate():
    """Execute any pending South migrations on the server."""
    manage('migrate')


def test():
    """Run Django tests"""
    assert hasattr(env, 'project_path')
    project_name = 'project'
    if project_name:
        manage('test --settings=%s.settings.test' % project_name)
    else:
        manage('test')


def update():
    """Do a complete project update.

    This combines:
        - installation of (newly) required Python packages via pip
        - collect new static files
        - upgrade locales,
        - db sync / migrations.
    """
    install_requirements()
    collectstatic()
    syncdb()
    migrate()


def setup(origin):
    """Create an initial deployment from the source git repository.

    This also sets up a sample settings/local.py which just pulls all
    the settings from dev.py
    """
    assert hasattr(env, 'project_path')
    assert hasattr(env, 'virtualenv')
    git_clone(origin)
    git_tag_now('initial-deploy')
    with prefix('source ~/.bash_profile 2>/dev/null || ' +
            'source ~/.profile 2>/dev/null || true'):
        run('mkvirtualenv --no-site-packages ' + env.virtualenv)
    project_name = 'project'
    if project_name:
        fname = project_name + '/settings/local.py'
        with _cd_project_root():
            run('test -f %(fname)s || echo "from .dev import *" > %(fname)s' %
                {'fname': fname})
    update()
    test()


def deploy():
    """Deploy a new version of the app from the tracked git branch."""
    assert hasattr(env, 'project_path')
    assert hasattr(env, 'virtualenv')
    git_pull()
    git_tag_now('deploy')
    update()
    test()


def runserver(host='0.0.0.0', port='8000'):
    """Run a development server on host:port (default 0.0.0.0:8000)"""
    manage('runserver %s:%s' % (host, port))

try:
    from local_fabfile import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

PROJECT_NAME = 'project'


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
        PROJECT_NAME + ".settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = base
# Django settings

import os.path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROJECT_NAME = os.path.basename(ROOT_DIR)


def ABS_PATH(*args):
    return os.path.join(ROOT_DIR, *args)


def ENV_SETTING(key, default):
    import os
    return os.environ.get(key, default)


ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

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

# If you set this to False, Django will treat all time values as local to
# the specified timezone.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ABS_PATH('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ABS_PATH('static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    ABS_PATH('staticfiles'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)


def ensure_secret_key_file():
    """Checks that secret.py exists in settings dir. If not, creates one
    with a random generated SECRET_KEY setting."""
    secret_path = os.path.join(ABS_PATH('settings'), 'secret.py')
    if not os.path.exists(secret_path):
        from django.utils.crypto import get_random_string
        secret_key = get_random_string(50,
            'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
        with open(secret_path, 'w') as f:
            f.write("SECRET_KEY = " + repr(secret_key) + "\n")

# Import the secret key
ensure_secret_key_file()
from secret import SECRET_KEY  # noqa

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
)

ROOT_URLCONF = PROJECT_NAME + '.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or
    # "C:/www/django/templates". Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    ABS_PATH('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'south'
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
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler'
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
__FILENAME__ = dev
from .base import *
import dj_database_url

DEBUG = (ENV_SETTING('DEBUG', 'true') == 'true')
TEMPLATE_DEBUG = (ENV_SETTING('TEMPLATE_DEBUG', 'true') == 'true')
COMPRESS_ENABLED = (ENV_SETTING('COMPRESS_ENABLED', 'true') == 'true')

DATABASES = {'default': dj_database_url.config(
    default='sqlite:////' + ROOT_DIR + '/dev.db')}

EMAIL_BACKEND = ENV_SETTING('EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend')

# Disable caching while in development
CACHES = {
    'default': {
        'BACKEND': ENV_SETTING('CACHE_BACKEND',
            'django.core.cache.backends.dummy.DummyCache')
    }
}

# Add SQL statement logging in development
if (ENV_SETTING('SQL_DEBUG', 'false') == 'true'):
    LOGGING['loggers']['django.db'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': False
    }

# set up Django Debug Toolbar if installed
try:
    import debug_toolbar  # noqa
    MIDDLEWARE_CLASSES += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )
    INSTALLED_APPS += (
        'debug_toolbar',
    )
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TOOLBAR_CALLBACK': lambda *args, **kwargs: True
    }
except ImportError:
    pass


# Set up django-extensions if installed
try:
    import django_extensions  # noqa
    INSTALLED_APPS += ('django_extensions',)
except ImportError:
    pass


# Enable django-compressor if it's installed
if COMPRESS_ENABLED:
    try:
        import compressor  # noqa
        INSTALLED_APPS += ('compressor',)
        STATICFILES_FINDERS += ('compressor.finders.CompressorFinder',)
    except ImportError:
        pass

########NEW FILE########
__FILENAME__ = prod
from .base import *

DEBUG = (ENV_SETTING('DEBUG', 'true') == 'true')
TEMPLATE_DEBUG = (ENV_SETTING('TEMPLATE_DEBUG', 'true') == 'true')
COMPRESS_ENABLED = (ENV_SETTING('COMPRESS_ENABLED', 'true') == 'true')

# Uncomment to precompress files during deployment (also update Makefile)
# COMPRESS_OFFLINE = True

# Try to use DATABASE_URL environment variable if possible, otherwise fall back
# to hardcoded values
try:
    import dj_database_url
    DATABASES = {'default': dj_database_url.config()}
except ImportError:
    DATABASES = {}

if not DATABASES or 'default' not in DATABASES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.',
            'NAME': '',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }
    }

# Memcached is better choice, if you can set it up; if not, this is a good
# alternative.
CACHES = {
    'default': {
        'BACKEND': ENV_SETTING('CACHE_BACKEND',
            'django.core.cache.backends.locmem.LocMemCache')
    }
}

# Enable Raven if it's installed
try:
    import raven.contrib.django.raven_compat  # noqa
    INSTALLED_APPS += ('raven.contrib.django.raven_compat',)

    # Raven will try to use SENTRY_DSN from environment if possible (eg. on
    # Heroku). If you need to set it manually, uncomment and set SENTRY_DSN
    # setting here.
    # SENTRY_DSN = ''
except ImportError:
    pass

# Enable gunicorn if it's installed
try:
    import gunicorn  # noqa
    INSTALLED_APPS += (
        'gunicorn',
    )
except ImportError:
    pass

# Enable django-compressor if it's installed
if COMPRESS_ENABLED:
    try:
        import compressor  # noqa
        INSTALLED_APPS += ('compressor',)
        STATICFILES_FINDERS += ('compressor.finders.CompressorFinder',)
    except ImportError:
        pass

########NEW FILE########
__FILENAME__ = test
# Settings file optimized for test running. Sets up in-memory database,
# Nose test runner and disables South for the tests

from .base import *

# Use in-memory SQLIte3 database for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# No need to use South in testing
SOUTH_TESTS_MIGRATE = False
SKIP_SOUTH_TESTS = True

# Disable cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

try:
    import django_nose  # noqa
    import os.path
    INSTALLED_APPS += (
        'django_nose',
    )
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    PROJECT_APPS = [app for app in INSTALLED_APPS
            if os.path.exists(os.path.join(ROOT_DIR, '..', app))]
    if PROJECT_APPS:
        NOSE_ARGS = ['--cover-package=' + ','.join(PROJECT_APPS)]
except ImportError:
    pass


PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'myapp.views.home', name='home'),
    # url(r'^myapp/', include('myapp.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
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
from os import environ
from os.path import basename, dirname

settings_module = basename(dirname(__file__)) + '.settings'
environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
