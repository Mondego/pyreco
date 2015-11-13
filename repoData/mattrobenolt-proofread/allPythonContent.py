__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import sys
import os.path

CWD = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, CWD)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

SECRET_KEY = 'lol'
ROOT_URLCONF = 'tests.urls'
WSGI_APPLICATION = 'tests.wsgi.application'

INSTALLED_APPS = (
    'proofread.contrib.django_proofread',
)

TEMPLATE_DIRS = os.path.join(CWD, 'django_tests/templates/'),

PROOFREAD_SUCCESS = (
    '/',
    'thisisawesome/',
)

PROOFREAD_FAILURES = (
    '/lolidontexist',
    'idontexisteither'
)

PROOFREAD_ENDPOINTS = (
    ('/post/', 200, 'POST', {'a': 'yep'}),
    ('/post/', 405, 'GET'),
    ('/',)  # Redundant, but making sure the defaults get filled in properly
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.http import HttpResponse


def ok(request):
    return HttpResponse()


def post(request):
    if request.method == 'GET':
        return HttpResponse(status=405)
    # This is supposed to fail if 'a' wasn't posted
    return HttpResponse(request.POST['a'])


urlpatterns = patterns('',
    url(r'^$', ok),
    url(r'^thisisawesome/', ok),
    url(r'^post/', post),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for tests project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = base
"""
proofread.base
~~~~~~~~~~~~~~

:copyright: (c) 2013 by Matt Robenolt
:license: BSD, see LICENSE for more details.
"""

import uuid
import unittest


def make_test(path, status, method='GET', data=None):
    """ Generate a test method """
    def run(self):
        response = getattr(self.client, method.lower())(path, data or {})
        self.assertEqual(response.status_code, status)
    return run


class BuildTestCase(type):
    def __new__(cls, name, bases, attrs):
        endpoints = attrs.get('endpoints', [])
        status_code_text = attrs.get('status_code_text', {})

        for path, status, method, data in endpoints:
            if not path.startswith('/'):
                path = '/' + path
            status_text = status_code_text.get(status, 'UNKNOWN')

            test = make_test(path, status, method, data)
            test.__name__ = name
            if data:
                test.__doc__ = '%s %s %r => %d %s' % (method, path, data, status, status_text)
            else:
                test.__doc__ = '%s %s => %d %s' % (method, path, status, status_text)

            test_name = 'test_proofread_%s' % uuid.uuid4().hex[:6]
            attrs[test_name] = test
        return super(BuildTestCase, cls).__new__(cls, name, bases, attrs)


class BaseTestCase(unittest.TestCase):
    __metaclass__ = BuildTestCase

    endpoints = ()
    status_code_text = {}

########NEW FILE########
__FILENAME__ = proofread
"""
proofread.contrib.django_proofread.management.commands.proofread
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2013 by Matt Robenolt
:license: BSD, see LICENSE for more details.
"""


from django.core.management.base import NoArgsCommand
from django.core.management import call_command


class Command(NoArgsCommand):
    help = 'Run the proofread endpoint tests'

    def handle_noargs(self, **options):
        call_command('test', 'django_proofread.ProofreadTestCase', **options)

########NEW FILE########
__FILENAME__ = models
"""
proofread.contrib.django_proofread.models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2013 by Matt Robenolt
:license: BSD, see LICENSE for more details.
"""

########NEW FILE########
__FILENAME__ = tests
"""
proofread.contrib.django_proofread.tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2013 by Matt Robenolt
:license: BSD, see LICENSE for more details.
"""

from django.conf import settings
from django.test import TestCase
from django.core.handlers.wsgi import STATUS_CODE_TEXT
from proofread.base import BaseTestCase

ENDPOINTS = []
for endpoint in getattr(settings, 'PROOFREAD_ENDPOINTS', []):
    if len(endpoint) < 4:
        endpoint = endpoint + ('', 200, 'GET', None)[len(endpoint):]
    ENDPOINTS.append(endpoint)

for key, status in (('SUCCESS', 200), ('FAILURES', 404)):
    for endpoint in getattr(settings, 'PROOFREAD_%s' % key, ()):
        ENDPOINTS.append((endpoint, status, 'GET', None))

if not ENDPOINTS:
    import warnings
    warnings.warn("You haven't specified any urls for Proofread to test!")


class ProofreadTestCase(BaseTestCase, TestCase):
    status_code_text = STATUS_CODE_TEXT
    endpoints = ENDPOINTS

########NEW FILE########
