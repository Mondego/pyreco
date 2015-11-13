__FILENAME__ = defaults
from django.conf import settings

MAINTENANCE_MODE = getattr(settings, 'MAINTENANCE_MODE', False)
MAINTENANCE_IGNORE_URLS = getattr(settings, 'MAINTENANCE_IGNORE_URLS', ())
########NEW FILE########
__FILENAME__ = tests
import django
import os

TEST_ROOT = os.path.dirname(os.path.abspath(__file__))

if django.VERSION[:2] < (1, 3):
    DATABASE_ENGINE = 'sqlite3'           # 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
    DATABASE_NAME = 'testproject.db'             # Or path to database file if using sqlite3.
    DATABASE_USER = ''             # Not used with sqlite3.
    DATABASE_PASSWORD = ''         # Not used with sqlite3.
    DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
    DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

SITE_ID = 1

TEST_TEMPLATE_DIR = os.path.join(TEST_ROOT, os.pardir, os.pardir, 'tests', 'templates')

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'maintenancemode.middleware.MaintenanceModeMiddleware',
)

ROOT_URLCONF = 'maintenancemode.conf.urls.tests'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django_jenkins',
    'maintenancemode',
)

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pyflakes',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
)

########NEW FILE########
__FILENAME__ = defaults
__all__ = ['handler503']

handler503 = 'maintenancemode.views.defaults.temporary_unavailable'
########NEW FILE########
__FILENAME__ = tests
from django.conf.urls.defaults import *

urlpatterns = patterns('maintenancemode.views.tests',
    url(r'^$', 'index'),
    url(r'^ignored/$', 'index'),
)

########NEW FILE########
__FILENAME__ = http
from django.http import HttpResponse

class HttpResponseTemporaryUnavailable(HttpResponse):
    status_code = 503

########NEW FILE########
__FILENAME__ = middleware
import re
import django
from django.conf import settings
from django.core import urlresolvers


if django.VERSION[:2] <= (1, 3):
    from django.conf.urls import defaults as urls
else:
    from django.conf import urls

from maintenancemode.conf.settings.defaults import (MAINTENANCE_MODE,
                                                    MAINTENANCE_IGNORE_URLS)

urls.handler503 = 'maintenancemode.views.defaults.temporary_unavailable'
urls.__all__.append('handler503')

IGNORE_URLS = tuple([re.compile(url) for url in MAINTENANCE_IGNORE_URLS])


class MaintenanceModeMiddleware(object):
    def process_request(self, request):
        # Allow access if middleware is not activated
        if not MAINTENANCE_MODE:
            return None

        # Allow access if remote ip is in INTERNAL_IPS
        if request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS:
            return None

        # Allow access if the user doing the request is logged in and a
        # staff member.
        if hasattr(request, 'user') and request.user.is_staff:
            return None

        # Check if a path is explicitly excluded from maintenance mode
        for url in IGNORE_URLS:
            if url.match(request.path_info):
                return None

        # Otherwise show the user the 503 page
        resolver = urlresolvers.get_resolver(None)

        callback, param_dict = resolver._resolve_special('503')
        return callback(request, **param_dict)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = defaults
from django.template import RequestContext, loader

from maintenancemode import http

def temporary_unavailable(request, template_name='503.html'):
    """
    Default 503 handler, which looks for the requested URL in the redirects
    table, redirects if found, and displays 404 page if not redirected.

    Templates: `503.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/')
    """
    t = loader.get_template(template_name) # You need to create a 503.html template.
    context = RequestContext(request, {'request_path': request.path})
    return http.HttpResponseTemporaryUnavailable(t.render(context))

########NEW FILE########
__FILENAME__ = tests
from django.http import HttpResponse

def index(request):
    return HttpResponse('Rendered response page')
########NEW FILE########
