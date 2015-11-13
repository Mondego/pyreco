__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tztest.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for tztest project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'NAME': 'tztest',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'US/Pacific'

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
USE_TZ = False

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
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
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

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'm-62j3-svgu0w7_mx__msr(dvqb-6n*!it#$fl!_adyomu^xct'

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
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'tztest.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tztest.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    #'django.contrib.auth',
    #'django.contrib.contenttypes',
    #'django.contrib.sessions',
    #'django.contrib.sites',
    #'django.contrib.messages',
    #'django.contrib.staticfiles',
    'tztest.tztest',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

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
__FILENAME__ = main
"""Save and load some timestamps to Postgres using different
techniques and see if we get back the timestamps we want.
"""

from datetime import datetime
from pytz import timezone
from pytz import UTC

from tztest.tztest.models import Timestamp

from django.conf import settings

DJANGO_TZ = timezone(settings.TIME_ZONE)


class SaveMethod(object):
    """
    A way of saving a datetime to the database. The tz argument
    is the time zone to use and the style determines whether to
    save an 'aware' or 'naive' datetime.
    """
    def __init__(self, tz, style):
        assert style in ('aware', 'naive')
        self.tz = tz
        self.style = style

    def __unicode__(self):
        return u'{} {}'.format(self.style, self.tz.zone)

    def save(self, dt):
        dt = self.tz.normalize(dt)
        if self.style == 'naive':
            dt = dt.replace(tzinfo=None)
        return Timestamp.objects.create(timestamp=dt)


class LoadMethod(object):
    """
    A way of loading a datetime from the database. The tz argument is
    the time zone to localize to and the conversion argument
    determines whether to use the 'implicit' conversion of the Postgres
    connection (the normal Django way) or to use an 'explicit'
    conversion in an extra select.
    """
    def __init__(self, tz, conversion):
        assert conversion in ('implicit', 'explicit')
        self.tz = tz
        self.conversion = conversion

    def __unicode__(self):
        return u'{} {}'.format(self.conversion, self.tz.zone)

    def load(self, timestamp):
        """Return (stored_datetime, loaded_datetime).

        The stored_datetime is the timestamp actually stored in
        Postgres, which may or may not be the timestamp we saved. The
        loaded_datetime is the timestamp we end up with using this
        method.
        """
        select = {
            'timestamp_explicit':
            "timestamp at time zone '{}'".format(self.tz.zone),
            'timestamp_stored': "timestamp at time zone 'UTC'",
        }

        loaded_attr = ('timestamp' if self.conversion == 'implicit'
                       else 'timestamp_explicit')

        qs = Timestamp.objects.extra(select=select)

        timestamp = qs.get(pk=timestamp.pk)

        stored_datetime = UTC.localize(timestamp.timestamp_stored)
        loaded_datetime = self.tz.localize(getattr(timestamp, loaded_attr))

        return stored_datetime, loaded_datetime


class TestResult(object):
    """
    The result of a single roundtrip test.
    """
    def __init__(self, saved_dt, stored_dt, loaded_dt):
        self.stored_correctly = saved_dt == stored_dt
        self.loaded_correctly = saved_dt == loaded_dt

        self.stored_error = stored_dt - saved_dt
        self.loaded_error = loaded_dt - saved_dt

    def __unicode__(self):
        return u'{}/{}'.format(
            'OK' if self.stored_correctly else self.stored_error,
            'OK' if self.loaded_correctly else self.loaded_error)


class Test(object):
    """
    A pair of methods for saving and loading a timestamp to the database.
    """
    next_test_number = 1

    def __init__(self, save_method, load_method):
        self.test_number, Test.next_test_number = (
            self.next_test_number, self.next_test_number + 1)
        self.save_method = save_method
        self.load_method = load_method

    def __unicode__(self):
        return unicode(self.test_number)

    def make_roundtrip(self, saved_dt):
        return self.load_method.load(self.save_method.save(saved_dt))

    def run_test(self, saved_dt):
        return TestResult(saved_dt, *self.make_roundtrip(saved_dt))


class TestTable(object):
    """
    A table showing the results of saving and loading different
    timestamps using different save and load methods.
    """
    def __init__(self):
        self.headers = ['#', 'Save As', 'Load As']
        self.rows = []

    def add_datetime(self, dt):
        """Add a test datetime to the table and update the results."""
        self.headers.append(DJANGO_TZ.normalize(dt))
        for row in self.rows:
            row.append(row[0].run_test(dt))

    def add_test(self, test):
        """Add a Test to the table and update the results."""
        row = [test, test.save_method, test.load_method]
        self.rows.append(row)
        for dt in self.headers[3:]:
            row.append(test.run_test(dt))

    def __unicode__(self):
        lines = []

        def add_row(row):
            cols = [
                u'{:>2}'.format(row[0]),
                u'{:^18}'.format(row[1]),
                u'{:^21}'.format(row[2]),
            ]
            cols.extend(u'{:^27}'.format(unicode(val)) for val in row[3:])
            lines.append(u'|'.join(cols))

        add_row(self.headers)
        lines.append('-' * len(lines[0]))
        map(add_row, self.rows)

        return u'\n'.join(lines)


datetimes = [
    # A timestamp that happens shortly before a US/Pacific
    # daylight savings time fall-back event.
    datetime(2002, 10, 27, 8, 30, 0, tzinfo=UTC),

    # A timestamp whose naive version, when interpreted as if
    # it was in US/Pacific, happens shortly after a daylight
    # savings time fall-forward event.
    datetime(2002, 4, 7, 2, 30, 0, tzinfo=UTC),
]

tests = [
    Test(SaveMethod(DJANGO_TZ, 'naive'), LoadMethod(DJANGO_TZ, 'implicit')),
    Test(SaveMethod(DJANGO_TZ, 'naive'), LoadMethod(DJANGO_TZ, 'explicit')),
    Test(SaveMethod(DJANGO_TZ, 'aware'), LoadMethod(DJANGO_TZ, 'implicit')),
    Test(SaveMethod(DJANGO_TZ, 'aware'), LoadMethod(DJANGO_TZ, 'explicit')),
    Test(SaveMethod(DJANGO_TZ, 'naive'), LoadMethod(UTC, 'explicit')),
    Test(SaveMethod(UTC, 'aware'),       LoadMethod(DJANGO_TZ, 'implicit')),
    Test(SaveMethod(UTC, 'naive'),       LoadMethod(UTC, 'implicit')),
    Test(SaveMethod(UTC, 'aware'),       LoadMethod(UTC, 'explicit')),
    Test(SaveMethod(DJANGO_TZ, 'aware'), LoadMethod(UTC, 'explicit')),
]


def generate_test_table():
    table = TestTable()

    for dt in datetimes:
        table.add_datetime(dt)

    for test in tests:
        table.add_test(test)

    return table

########NEW FILE########
__FILENAME__ = tztest_test
"""Print out a table of timestamps, some methods of saving and loading
them, and whether each method ended up storing and loaded the same
timestamps it started with. For each method and timestamp, the table
shows 'OK' if the stored/loaded timestamp is the same as the one
saved. Otherwise, the difference between the stored/loaded timestamp
is shown. Only the last two methods where all four such timestamps are
OK pass the test.
"""

from django.core.management.base import BaseCommand

from tztest.tztest.main import generate_test_table


class Command(BaseCommand):

    help = __doc__

    def handle(self, *args, **opts):
        print unicode(generate_test_table())

########NEW FILE########
__FILENAME__ = models
from django.db.models import DateTimeField
from django.db.models import Model


class Timestamp(Model):
    """
    A simple Django model for illustrating time zone issues.
    """
    timestamp = DateTimeField()

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

from tztest.tztest.main import generate_test_table


def home(request):
    table = generate_test_table()
    no_header = request.GET.get('noheader', False)
    return render(request, 'tztest/index.html',
                  {'table': table, 'no_header': no_header})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns(
    '',

    url(r'^$', 'tztest.tztest.views.home', name='home'),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for tztest project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "tztest.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tztest.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
