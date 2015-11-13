__FILENAME__ = context_processors
from django.conf import settings


def readonly(request):
    return {
        'SITE_READ_ONLY': getattr(settings, 'SITE_READ_ONLY', False),
    }

########NEW FILE########
__FILENAME__ = exceptions
from django.db.utils import DatabaseError


class DatabaseWriteDenied(DatabaseError):
    pass

########NEW FILE########
__FILENAME__ = middleware
from .exceptions import DatabaseWriteDenied
from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri


class HttpResponseReload(HttpResponse):
    """
    Reload page and stay on the same page from where request was made.
    """
    status_code = 302
    
    def __init__(self, request):
        HttpResponse.__init__(self)
        referer = request.META.get('HTTP_REFERER')
        self['Location'] = iri_to_uri(referer or "/")


class DatabaseReadOnlyMiddleware(object):
    def process_exception(self, request, exception):
        # Only process DatabaseWriteDenied exceptions
        if not isinstance(exception, DatabaseWriteDenied):
            return None
        
        # Handle the exception
        if request.method == 'POST':
            if getattr(settings, 'DB_READ_ONLY_MIDDLEWARE_MESSAGE', False):
                from django.contrib import messages
                messages.error(request, 'The site is currently in read-only '
                    'mode. Please try editing later.')
            
            # Try to redirect to this page's GET version
            return HttpResponseReload(request)
        else:
            # We can't do anything about this error
            return HttpResponse('The site is currently in read-only mode. '
                'Please try again later.')

########NEW FILE########
__FILENAME__ = tests
"""
Tests? What Tests?
"""

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
from os.path import dirname, abspath, join

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',

        # Uncomment below to run tests with mysql
        #DATABASE_ENGINE='django.db.backends.mysql',
        #DATABASE_NAME='readonly_test',
        #DATABASE_USER='readonly_test',
        #DATABASE_HOST='/var/mysql/mysql.sock',
        INSTALLED_APPS=[
            'readonly',
        ],
        ROOT_URLCONF='',
        DEBUG=False,
        SITE_READ_ONLY=True,
    )

from django.test.simple import run_tests


def runtests(*test_args):
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    if not test_args:
        test_args = ['readonly']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=0, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
