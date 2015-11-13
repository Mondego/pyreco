__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import LiveServerTestCase
from subprocess import Popen, PIPE
import os.path
import sys

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.views import serve
from django.utils.http import http_date
from django.conf import settings

__all__ = ['CasperTestCase']


def staticfiles_handler_serve(self, request):
    import time
    resp = serve(request, self.file_path(request.path), insecure=True)
    if resp.status_code == 200:
        resp["Expires"] = http_date(time.time() + 24 * 3600)
    return resp


class CasperTestCase(LiveServerTestCase):
    """LiveServerTestCase subclass that can invoke CasperJS tests."""

    use_phantom_disk_cache = False
    load_images = False
    no_colors = True

    def __init__(self, *args, **kwargs):
        super(CasperTestCase, self).__init__(*args, **kwargs)
        if self.use_phantom_disk_cache:
            StaticFilesHandler.serve = staticfiles_handler_serve

    def casper(self, test_filename, **kwargs):
        """CasperJS test invoker.

        Takes a test filename (.js) and optional arguments to pass to the
        casper test.

        Returns True if the test(s) passed, and False if any test failed.

        Since CasperJS startup/shutdown is quite slow, it is recommended
        to bundle all the tests from a test case in a single casper file
        and invoke it only once.
        """

        kwargs.update({
            'load-images': 'yes' if self.load_images else 'no',
            'disk-cache': 'yes' if self.use_phantom_disk_cache else 'no',
            'ignore-ssl-errors': 'yes',
            'url-base': self.live_server_url,
            'log-level': 'debug' if settings.DEBUG else 'error',
        })

        cn = settings.SESSION_COOKIE_NAME
        if cn in self.client.cookies:
            kwargs['cookie-' + cn] = self.client.cookies[cn].value

        cmd = ['casperjs', 'test']

        if self.no_colors:
            cmd.append('--no-colors')

        if settings.DEBUG:
            cmd.append('--verbose')

        cmd.extend([('--%s=%s' % i) for i in kwargs.iteritems()])
        cmd.append(test_filename)

        p = Popen(cmd, stdout=PIPE, stderr=PIPE,
            cwd=os.path.dirname(test_filename))  # flake8: noqa
        out, err = p.communicate()
        if p.returncode != 0:
            sys.stdout.write(out)
            sys.stderr.write(err)
        return p.returncode == 0

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
# nothing to be done here, move along

########NEW FILE########
__FILENAME__ = tests
from casper.tests import CasperTestCase
import os.path

from django.contrib.auth.models import User


class CasperTestTestCase(CasperTestCase):
    """
    Yo dawg, I heard you like tests, so I put tests in your tests
    so you can test while you test.
    """

    def test_that_casper_integration_works(self):
        self.assertTrue(self.casper(
            os.path.join(os.path.dirname(__file__),
                'casper-tests/test.js')))  # flake8: noqa

    def test_that_casper_integration_works_when_test_fails(self):
        self.assertFalse(self.casper(
            os.path.join(os.path.dirname(__file__),
                'casper-tests/failing-test.js')))  # flake8: noqa

    def test_that_casper_can_reuse_session_cookie(self):
        u = User.objects.create_user(username='foo', password='bar')
        self.client.login(username='foo', password='bar')
        self.assertTrue(self.casper(
            os.path.join(os.path.dirname(__file__),
                'casper-tests/session.js')))  # flake8: noqa

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render


def index(request):
    return render(request, 'index.html', {
        'authenticated': request.user.is_authenticated()
    })

########NEW FILE########
__FILENAME__ = settings
# Django settings for testproject project.

import os.path
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.abspath(os.path.join(ROOT_DIR, '..')))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

ALLOWED_HOSTS = []
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1

USE_I18N = True
USE_L10N = True
USE_TZ = True
MEDIA_ROOT = ''
MEDIA_URL = ''
STATIC_ROOT = ''
STATIC_URL = '/static/'
STATICFILES_DIRS = ()
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
SECRET_KEY = 'nd&dz8k$757ngw(d(11ro-9@!_thx=@*7w1#&!u12t2%78a2dr'
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
ROOT_URLCONF = 'testproject.urls'
WSGI_APPLICATION = 'testproject.wsgi.application'
TEMPLATE_DIRS = ()
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'casper',
    'testapp'
)
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
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'testapp.views.index', name='index')  # flake8: noqa
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for testproject project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "testproject.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
