__FILENAME__ = djqmethod
# -*- coding: utf-8 -*-

__version__ = '0.0.3'

from functools import partial

from django.db import models


def attr_error(obj, attr):
    return AttributeError("%r object has no attribute %r" % (str(type(obj)), attr))


class QueryMethod(object):

    # Make querymethod objects a little cheaper.
    __slots__ = ('function',)

    def __init__(self, function):
        self.function = function

    def for_query_set(self, qset):
        return partial(self.function, qset)

querymethod = QueryMethod


class QMethodLookupMixin(object):
    """Delegate missing attributes to querymethods on ``self.model``."""

    def __getattr__(self, attr):
        # Using `object.__getattribute__` avoids infinite loops if the 'model'
        # attribute does not exist.
        qmethod = getattr(object.__getattribute__(self, 'model'), attr, None)
        if isinstance(qmethod, QueryMethod):
            return qmethod.for_query_set(self)
        raise attr_error(self, attr)


class QMethodQuerySet(models.query.QuerySet, QMethodLookupMixin):
    pass


class Manager(models.Manager, QMethodLookupMixin):

    # If this is the default manager for a model, use this manager class for
    # relations (i.e. `group.people`, see README for details).
    use_for_related_fields = True

    def get_query_set(self, *args, **kwargs):
        return QMethodQuerySet(model=self.model, using=self._db)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import sys
sys.path.insert(0, '../../')
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.db import models
from djqmethod import Manager, querymethod


class SiteManager(CurrentSiteManager, Manager):
    pass


class Group(models.Model):
    pass


class Person(models.Model):

    group = models.ForeignKey(Group, related_name='people')
    age = models.PositiveIntegerField()
    site = models.ForeignKey(Site, related_name='people', null=True)

    objects = Manager()
    on_site = SiteManager()

    @querymethod
    def minors(query):
        return query.filter(age__lt=18)

    @querymethod
    def adults(query):
        return query.filter(age__gte=18)

    @querymethod
    def get_for_age(query, age):
        return query.get_or_create(age=age)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

import cPickle as pickle

from django.db import IntegrityError, models
from django.test import TestCase

from people.models import Group, Person


class SimpleTest(TestCase):

    fixtures = ['testing']

    def test_manager(self):
        self.failUnless(isinstance(
            Person.objects.minors(),
            models.query.QuerySet))

        self.failUnlessEqual(
            pks(Person.objects.minors()),
            pks(Person.objects.filter(age__lt=18)))

        self.failUnless(isinstance(
            Person.objects.adults(),
            models.query.QuerySet))

        self.failUnlessEqual(
            pks(Person.objects.adults()),
            pks(Person.objects.filter(age__gte=18)))

    def test_qset(self):
        self.failUnless(isinstance(
            Person.objects.all().minors(),
            models.query.QuerySet))

        self.failUnlessEqual(
            pks(Person.objects.all().minors()),
            pks(Person.objects.filter(age__lt=18)))

        self.failUnless(isinstance(
            Person.objects.all().adults(),
            models.query.QuerySet))

        self.failUnlessEqual(
            pks(Person.objects.all().adults()),
            pks(Person.objects.filter(age__gte=18)))


class RelationTest(TestCase):

    fixtures = ['testing']

    def test_querying(self):
        for group in Group.objects.all():
            self.failUnless(isinstance(
                group.people.all(),
                models.query.QuerySet))

            self.failUnless(isinstance(
                group.people.minors(),
                models.query.QuerySet))

            self.failUnlessEqual(
                pks(group.people.minors()),
                pks(group.people.filter(age__lt=18)))

            self.failUnless(isinstance(
                group.people.adults(),
                models.query.QuerySet))

            self.failUnlessEqual(
                pks(group.people.adults()),
                pks(group.people.filter(age__gte=18)))

    def test_creation(self):
        group = Group.objects.get(pk=1)
        person = group.people.create(age=32)
        assert person.group_id == group.pk

    def test_qmethods_get_the_original_object(self):
        group = Group.objects.get(pk=1)
        person, created = group.people.get_for_age(72)
        assert created
        assert person.age == 72
        assert person.group_id == group.pk

        # group_id cannot be NULL.
        with self.assertRaises(IntegrityError) as cm:
            Person.objects.get_for_age(22)
        assert "group_id" in cm.exception.message
        assert "NULL" in cm.exception.message


class PickleTest(TestCase):

    fixtures = ['testing']

    def assert_pickles(self, qset):
        self.failUnlessEqual(pks(qset),
                             pks(pickle.loads(pickle.dumps(qset))))

    def test(self):
        self.assert_pickles(Person.objects.minors())
        self.assert_pickles(Person.objects.all().minors())
        self.assert_pickles(Person.objects.minors().all())
        self.assert_pickles(Group.objects.all())
        self.assert_pickles(Group.objects.all()[0].people.all())
        self.assert_pickles(Group.objects.all()[0].people.minors())


def pks(qset):
    """Return the list of primary keys for the results of a QuerySet."""

    return sorted(tuple(qset.values_list('pk', flat=True)))

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Zachary Voase', 'z@zacharyvoase.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':  'django.db.backends.sqlite3',
        'NAME':  'dev.sqlite3',
        'USER':  '',
        'PASSWORD':  '',
        'HOST':  '',
        'PORT':  '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '8@+k3lm3=s+ml6_*(cnpbg1w=6k9xpk5f=irs+&j4_6i=62fy^'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.sites',
    'people',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^example/', include('example.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
