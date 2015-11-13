__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
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

from django.db import models
from djqmixin import Manager, QMixin


class AgeMixin(QMixin):
    def minors(self):
        return self.filter(age__lt=18)
    
    def adults(self):
        return self.filter(age__gte=18)



class Group(models.Model):
    pass


class Person(models.Model):
    
    group = models.ForeignKey(Group, related_name='people')
    age = models.PositiveIntegerField()
    
    objects = Manager.include(AgeMixin)()

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from django.db import models
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
    
    def test(self):
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


def pks(qset):
    """Return the list of primary keys for the results of a QuerySet."""
    
    return sorted(tuple(qset.values_list('pk', flat=True)))

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Zachary Voase', 'zacharyvoase@me.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'dev.sqlite3'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

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
