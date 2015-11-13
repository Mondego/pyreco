__FILENAME__ = predicate
import re

from django.db.models.query_utils import Q

LOOKUP_SEP = '__'

QUERY_TERMS = set([
    'exact', 'iexact', 'contains', 'icontains', 'gt', 'gte', 'lt', 'lte', 'in',
    'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'year',
    'month', 'day', 'week_day', 'isnull', 'search', 'regex', 'iregex',
])

def eval_wrapper(children):
    """
    generator to yield child nodes, or to wrap filter expressions
    """
    for child in children:
        if isinstance(child, P):
            yield child
        elif isinstance(child, tuple) and len(child) == 2:
            yield LookupExpression(child)

class P(Q):
    """
    A Django 'predicate' construct

    This is a variation on Q objects, but instead of being used to generate
    SQL, they are used to test a model instance against a set of conditions.
    """

    # allow the use of the 'in' operator for membership testing
    def __contains__(self, obj):
        return self.eval(obj)

    def eval(self, instance):
        """
        Returns true if the model instance matches this predicate
        """
        evaluators = {"AND": all, "OR": any}
        evaluator = evaluators[self.connector]
        return (evaluator(c.eval(instance) for c in eval_wrapper(self.children)))

    def to_identifier(self):
        s = ""
        for c in sorted(self.children):
            if isinstance(c, type(self)):
                s += c.to_identifier()
            else:
                s += ''.join([str(val) for val in c])
        return s.replace('_','')

class LookupExpression(object):
    """
    A thin wrapper around a filter expression tuple of (lookup-type, value) to
    provide an eval method
    """

    def __init__(self, expr):
        self.lookup, self.value = expr
        self.field = None

    def get_field(self, instance):
        lookup_type = 'exact' # Default lookup type
        parts = self.lookup.split(LOOKUP_SEP)
        num_parts = len(parts)
        if (len(parts) > 1 and parts[-1] in QUERY_TERMS):
            # Traverse the lookup query to distinguish related fields from
            # lookup types.
            lookup_model = instance
            for counter, field_name in enumerate(parts):
                try:
                    lookup_field = getattr(lookup_model, field_name)
                except AttributeError:
                    # Not a field. Bail out.
                    lookup_type = parts.pop()
                    return (lookup_model, lookup_field, lookup_type)
                # Unless we're at the end of the list of lookups, let's attempt
                # to continue traversing relations.
                if (counter + 1) < num_parts:
                    try:
                        dummy = lookup_model._meta.get_field(field_name).rel.to
                        lookup_model = lookup_field
                        # print lookup_model
                    except AttributeError:
                        # # Not a related field. Bail out.
                        lookup_type = parts.pop()
                        return (lookup_model, lookup_field, lookup_type)
        else:
            return (instance, getattr(instance, parts[0]), lookup_type)

    def eval(self, instance):
        """
        return true if the instance matches the expression
        """
        lookup_model, lookup_field, lookup_type = self.get_field(instance)
        comparison_func = getattr(self, '_' + lookup_type, None)
        if comparison_func:
            return comparison_func(lookup_model, lookup_field)
        raise ValueError("invalid lookup: {}".format(self.lookup))

    # Comparison functions

    def _exact(self, lookup_model, lookup_field):
        return lookup_field == self.value

    def _iexact(self, lookup_model, lookup_field):
        return lookup_field.lower() == self.value.lower()

    def _contains(self, lookup_model, lookup_field):
        return self.value in lookup_field

    def _icontains(self, lookup_model, lookup_field):
        return self.value.lower() in lookup_field.lower()

    def _gt(self, lookup_model, lookup_field):
        return lookup_field > self.value

    def _gte(self, lookup_model, lookup_field):
        return lookup_field >= self.value

    def _lt(self, lookup_model, lookup_field):
        return lookup_field < self.value

    def _lte(self, lookup_model, lookup_field):
        return lookup_field <= self.value

    def _startswith(self, lookup_model, lookup_field):
        return lookup_field.startswith(self.value)

    def _istartswith(self, lookup_model, lookup_field):
        return lookup_field.lower().startswith(self.value.lower())

    def _endswith(self, lookup_model, lookup_field):
        return lookup_field.endswith(self.value)

    def _iendswith(self, lookup_model, lookup_field):
        return lookup_field.lower().endswith(self.value.lower())

    def _in(self, lookup_model, lookup_field):
        return lookup_field in self.value

    def _range(self, lookup_model, lookup_field):
        # TODO could be more between like
        return self.value[0] < lookup_field < self.value[1]

    def _year(self, lookup_model, lookup_field):
        return lookup_field.year == self.value

    def _month(self, lookup_model, lookup_field):
        return lookup_field.month == self.value

    def _day(self, lookup_model, lookup_field):
        return lookup_field.day == self.value

    def _week_day(self, lookup_model, lookup_field):
        return lookup_field.weekday() == self.value

    def _isnull(self, lookup_model, lookup_field):
        if self.value:
            return lookup_field == None
        else:
            return lookup_field != None

    def _search(self, lookup_model, lookup_field):
        return self._contains(lookup_model, lookup_field)

    def _regex(self, lookup_model, lookup_field):
        """
        Note that for queries - this can be DB specific syntax
        here we just use Python
        """
        return bool(re.search(self.value, lookup_field))

    def _iregex(self, lookup_model, lookup_field):
        return bool(re.search(self.value, lookup_field, flags=re.I))



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
import datetime

from django.db import models

class TestObj(models.Model):
    char_value = models.CharField(max_length=100, default='')
    int_value = models.IntegerField(default=0)
    date_value = models.DateField(default=datetime.date.today)
    parent = models.ForeignKey('self', related_name='children', null=True)


########NEW FILE########
__FILENAME__ = tests
from datetime import date
from random import choice, random

from django.test import TestCase
from predicate import P

from models import TestObj

colors = """red
blue
yellow
green
orange
purple
violet
brown
black
white""".split('\n')

def make_test_objects():
    made = []

    for i in range(100):
        t = TestObj()
        t.char_value = ' '.join([choice(colors), choice(colors), choice(colors)])
        t.int_value = int(100 * random())
        if made:
            t.parent = choice(made)
        t.save()
        made.append(t)

class RelationshipFollowTest(TestCase):
    def setUp(self):
        make_test_objects()

    def test_follow_relationship(self):
        p1 = P(parent__int_value__gt=10)
        obj = TestObj.objects.filter(parent__int_value__gt=10)[0]
        self.assertTrue(p1.eval(obj))
        p2 = P(parent__parent__int_value__gt=10)
        obj = TestObj.objects.filter(parent__parent__int_value__gt=10)[0]
        self.assertTrue(p2.eval(obj))

class ComparisonFunctionsTest(TestCase):

    def setUp(self):
        self.testobj = TestObj(
                char_value="hello world",
                int_value=50,
                date_value=date.today())

    def test_exact(self):
        self.assertTrue(P(char_value__exact='hello world').eval(self.testobj))
        self.assertTrue(P(char_value='hello world').eval(self.testobj))
        self.assertFalse(P(char_value='Hello world').eval(self.testobj))
        self.assertFalse(P(char_value='hello worl').eval(self.testobj))

    def test_iexact(self):
        self.assertTrue(P(char_value__iexact='heLLo World').eval(self.testobj))
        self.assertFalse(P(char_value__iexact='hello worl').eval(self.testobj))

    def test_contains(self):
        self.assertTrue(P(char_value__contains='hello').eval(self.testobj))
        self.assertFalse(P(char_value__contains='foobar').eval(self.testobj))

    def test_icontains(self):
        self.assertTrue(P(char_value__icontains='heLLo').eval(self.testobj))

    def test_gt(self):
        self.assertTrue(P(int_value__gt=20).eval(self.testobj))
        self.assertFalse(P(int_value__gt=80).eval(self.testobj))
        self.assertTrue(P(int_value__gt=20.0).eval(self.testobj))
        self.assertFalse(P(int_value__gt=80.0).eval(self.testobj))
        self.assertFalse(P(int_value__gt=50).eval(self.testobj))

    def test_gte(self):
        self.assertTrue(P(int_value__gte=20).eval(self.testobj))
        self.assertTrue(P(int_value__gte=50).eval(self.testobj))

    def test_lt(self):
        self.assertFalse(P(int_value__lt=20).eval(self.testobj))
        self.assertTrue(P(int_value__lt=80).eval(self.testobj))
        self.assertFalse(P(int_value__lt=20.0).eval(self.testobj))
        self.assertTrue(P(int_value__lt=80.0).eval(self.testobj))
        self.assertFalse(P(int_value__lt=50).eval(self.testobj))

    def test_lte(self):
        self.assertFalse(P(int_value__lte=20).eval(self.testobj))
        self.assertTrue(P(int_value__lte=50).eval(self.testobj))

    def test_startswith(self):
        self.assertTrue(P(char_value__startswith='hello').eval(self.testobj))
        self.assertFalse(P(char_value__startswith='world').eval(self.testobj))
        self.assertFalse(P(char_value__startswith='Hello').eval(self.testobj))

    def test_istartswith(self):
        self.assertTrue(P(char_value__istartswith='heLLo').eval(self.testobj))
        self.assertFalse(P(char_value__startswith='world').eval(self.testobj))

    def test_endswith(self):
        self.assertFalse(P(char_value__endswith='hello').eval(self.testobj))
        self.assertTrue(P(char_value__endswith='world').eval(self.testobj))
        self.assertFalse(P(char_value__endswith='World').eval(self.testobj))

    def test_iendswith(self):
        self.assertFalse(P(char_value__iendswith='hello').eval(self.testobj))
        self.assertTrue(P(char_value__iendswith='World').eval(self.testobj))

    def test_dates(self):
        today = date.today()
        self.assertTrue(P(date_value__year=today.year).eval(self.testobj))
        self.assertTrue(P(date_value__month=today.month).eval(self.testobj))
        self.assertTrue(P(date_value__day=today.day).eval(self.testobj))
        self.assertTrue(P(date_value__week_day=today.weekday()).eval(self.testobj))

        self.assertFalse(P(date_value__year=today.year + 1).eval(self.testobj))
        self.assertFalse(P(date_value__month=today.month + 1).eval(self.testobj))
        self.assertFalse(P(date_value__day=today.day + 1).eval(self.testobj))
        self.assertFalse(P(date_value__week_day=today.weekday() + 1).eval(self.testobj))

    def test_null(self):
        self.assertTrue(P(parent__isnull=True).eval(self.testobj))
        self.assertFalse(P(parent__isnull=False).eval(self.testobj))

    def test_regex(self):
        self.assertTrue(P(char_value__regex='hel*o').eval(self.testobj))
        self.assertFalse(P(char_value__regex='Hel*o').eval(self.testobj))

    def test_iregex(self):
        self.assertTrue(P(char_value__iregex='Hel*o').eval(self.testobj))

    def test_in_operator(self):
        p = P(int_value__lte=50)
        p2 = P(int_value__lt=10)
        self.assertTrue(self.testobj in p)
        self.assertFalse(self.testobj in p2)


class GroupTest(TestCase):

    def setUp(self):
        self.testobj = TestObj(
                char_value="hello world",
                int_value=50,
                date_value=date.today())

    def test_and(self):
        p1 = P(char_value__contains='hello')
        p2 = P(int_value=50)
        p3 = P(int_value__lt=20)
        pand1 = p1 & p2
        pand2 = p2 & p3
        self.assertTrue(pand1.eval(self.testobj))
        self.assertFalse(pand2.eval(self.testobj))

    def test_or(self):
        p1 = P(char_value__contains='hello', int_value=50)
        p2 = P(int_value__gt=80)
        p3 = P(int_value__lt=20)
        por1 = p1 | p2
        por2 = p2 | p3
        self.assertTrue(por1.eval(self.testobj))
        self.assertFalse(por2.eval(self.testobj))


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for testproject project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

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
SECRET_KEY = '#0&k@ztj55vtu(7pr1x2#n1)g9msz$ebqj1o_b2@+qw!+2^(zu'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'testproject.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'testproject.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
        # 'django_nose',
        'testapp',
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
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testproject.views.home', name='home'),
    # url(r'^testproject/', include('testproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
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
