__FILENAME__ = get_dropbox_token
from django.core.management.base import NoArgsCommand
from dropbox import rest, session
from django_dropbox.settings import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TYPE

class Command(NoArgsCommand):

    def handle_noargs(self, *args, **options):
        sess = session.DropboxSession(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TYPE)
        request_token = sess.obtain_request_token()

        url = sess.build_authorize_url(request_token)
        print "Url:", url
        print "Please visit this website and press the 'Allow' button, then hit 'Enter' here."
        raw_input()
        
        # This will fail if the user didn't visit the above URL and hit 'Allow'
        access_token = sess.obtain_access_token(request_token)

        print "DROPBOX_ACCESS_TOKEN = '%s'" % access_token.key
        print "DROPBOX_ACCESS_TOKEN_SECRET = '%s'" % access_token.secret
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

CONSUMER_KEY = getattr(settings, 'DROPBOX_CONSUMER_KEY', None)
CONSUMER_SECRET = getattr(settings, 'DROPBOX_CONSUMER_SECRET', None)
ACCESS_TOKEN = getattr(settings, 'DROPBOX_ACCESS_TOKEN', None)
ACCESS_TOKEN_SECRET = getattr(settings, 'DROPBOX_ACCESS_TOKEN_SECRET', None)
CACHE_TIMEOUT = getattr(settings, 'DROPBOX_CACHE_TIMEOUT', 3600 * 24 * 365)   # One year

# ACCESS_TYPE should be 'dropbox' or 'app_folder' as configured for your app
ACCESS_TYPE = 'dropbox'


########NEW FILE########
__FILENAME__ = storage
import errno
import os.path
import re
import urlparse
import urllib
import itertools
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from dropbox.session import DropboxSession
from dropbox.client import DropboxClient
from dropbox.rest import ErrorResponse
from django.core.cache import cache
from django.core.files import File
from django.core.files.storage import Storage
from django.utils.encoding import filepath_to_uri

from .settings import (CONSUMER_KEY,
                       CONSUMER_SECRET,
                       ACCESS_TYPE,
                       ACCESS_TOKEN,
                       ACCESS_TOKEN_SECRET,
                       CACHE_TIMEOUT)


class DropboxStorage(Storage):
    """
    A storage class providing access to resources in a Dropbox Public folder.
    """

    def __init__(self, location='/Public'):
        session = DropboxSession(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TYPE, locale=None)
        session.set_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        self.client = DropboxClient(session)
        self.account_info = self.client.account_info()
        self.location = location
        self.base_url = 'http://dl.dropbox.com/u/{uid}/'.format(**self.account_info)

    def _get_abs_path(self, name):
        return os.path.realpath(os.path.join(self.location, name))

    def _open(self, name, mode='rb'):
        name = self._get_abs_path(name)
        remote_file = DropboxFile(name, self, mode=mode)
        return remote_file

    def _save(self, name, content):
        name = self._get_abs_path(name)
        directory = os.path.dirname(name)
        if not self.exists(directory) and directory:
             self.client.file_create_folder(directory)
        response = self.client.metadata(directory)
        if not response['is_dir']:
             raise IOError("%s exists and is not a directory." % directory)
        abs_name = os.path.realpath(os.path.join(self.location, name))
        self.client.put_file(abs_name, content)
        return name

    def delete(self, name):
        name = self._get_abs_path(name)
        self.client.file_delete(name)

    def exists(self, name):
        name = self._get_abs_path(name)
        try:
            metadata = self.client.metadata(name)
            if metadata.get('is_deleted'):
                return False
        except ErrorResponse as e:
            if e.status == 404: # not found
                return False
            raise e
        return True

    def listdir(self, path):
        path = self._get_abs_path(path)
        response = self.client.metadata(path)
        directories = []
        files = []
        for entry in response.get('contents', []):
            if entry['is_dir']:
                directories.append(os.path.basename(entry['path']))
            else:
                files.append(os.path.basename(entry['path']))
        return directories, files

    def size(self, name):
        cache_key = 'django-dropbox-size:%s' % filepath_to_uri(name)
        size = cache.get(cache_key)

        if not size:
            size = self.client.metadata(filepath_to_uri(name))['bytes']
            cache.set(cache_key, size, CACHE_TIMEOUT)

        return size

    def url(self, name):
        cache_key = 'django-dropbox-url:%s' % filepath_to_uri(name)
        url = cache.get(cache_key)

        if not url:
            url = self.client.share(filepath_to_uri(name), short_url=False)['url'] + '?dl=1'
            cache.set(cache_key, url, CACHE_TIMEOUT)

        return url

    def get_available_name(self, name):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        name = self._get_abs_path(name)
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        # If the filename already exists, add an underscore and a number (before
        # the file extension, if one exists) to the filename until the generated
        # filename doesn't exist.
        count = itertools.count(1)
        while self.exists(name):
            # file_ext includes the dot.
            name = os.path.join(dir_name, "%s_%s%s" % (file_root, count.next(), file_ext))

        return name

class DropboxFile(File):
    def __init__(self, name, storage, mode):
        self._storage = storage
        self._mode = mode
        self._is_dirty = False
        self.file = StringIO()
        self.start_range = 0
        self._name = name

    @property
    def size(self):
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self._name)
        return self._size

    def read(self, num_bytes=None):
        return self._storage.client.get_file(self._name).read()

    def write(self, content):
        if 'w' not in self._mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = StringIO(content)
        self._is_dirty = True

    def close(self):
        if self._is_dirty:
            self._storage.client.put_file(self._name, self.file.getvalue())
        self.file.close()
########NEW FILE########
__FILENAME__ = tests
#import os
from django.core.files.base import ContentFile
from django.test import TestCase
from django_dropbox.storage import DropboxStorage

class DropboxStorageTest(TestCase):

    def setUp(self):
        self.location = '/Public/testing'
        self.storage = DropboxStorage(location=self.location)
        self.storage.base_url = '/test_media_url/'

    def test_file_access_options(self):
        """
        Standard file access options are available, and work as expected.
        """
        self.assertFalse(self.storage.exists('storage_test'))
        f = self.storage.open('storage_test', 'w')
        f.write('storage contents')
        f.close()
        self.assertTrue(self.storage.exists('storage_test'))

        f = self.storage.open('storage_test', 'r')
        self.assertEqual(f.read(), 'storage contents')
        f.close()

        self.storage.delete('storage_test')
        self.assertFalse(self.storage.exists('storage_test'))

    def test_exists_folder(self):
        self.assertFalse(self.storage.exists('storage_test_exists'))
        self.storage.client.file_create_folder(self.location + '/storage_test_exists')
        self.assertTrue(self.storage.exists('storage_test_exists'))
        self.storage.delete('storage_test_exists')
        self.assertFalse(self.storage.exists('storage_test_exists'))

    def test_listdir(self):
        """
        File storage returns a tuple containing directories and files.
        """
        self.assertFalse(self.storage.exists('storage_test_1'))
        self.assertFalse(self.storage.exists('storage_test_2'))
        self.assertFalse(self.storage.exists('storage_dir_1'))

        f = self.storage.save('storage_test_1', ContentFile('custom content'))
        f = self.storage.save('storage_test_2', ContentFile('custom content'))
        self.storage.client.file_create_folder(self.location + '/storage_dir_1')

        dirs, files = self.storage.listdir(self.location)
        self.assertEqual(set(dirs), set([u'storage_dir_1']))
        self.assertEqual(set(files),
                         set([u'storage_test_1', u'storage_test_2']))

        self.storage.delete('storage_test_1')
        self.storage.delete('storage_test_2')
        self.storage.delete('storage_dir_1')

    def test_file_size(self):
        """
        File storage returns a url to access a given file from the Web.
        """
        self.assertFalse(self.storage.exists('storage_test_size'))
        f = self.storage.open('storage_test_size', 'w')
        f.write('these are 18 bytes')
        f.close()
        self.assertTrue(self.storage.exists('storage_test_size'))

        f = self.storage.open('storage_test_size', 'r')
        self.assertEqual(f.size, 18)
        f.close()

        self.storage.delete('storage_test_size')
        self.assertFalse(self.storage.exists('storage_test_size'))

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from dropbox_testing.models import Person

class PersonAdmin(admin.ModelAdmin):
    list_display = ('image',)
    
    def image(self, obj):
        if obj.photo:
            return '<img src="%s">' % obj.photo.url
        return ''
    image.allow_tags = True

admin.site.register(Person, PersonAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django_dropbox.storage import DropboxStorage

STORAGE = DropboxStorage()

class Person(models.Model):
     photo = models.ImageField(upload_to='photos', storage=STORAGE, null=True, blank=True)
     resume = models.FileField(upload_to='resumes', storage=STORAGE, null=True, blank=True)
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for django_dropbox_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sqlite',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

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

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
SECRET_KEY = 't_*)2-ihjb_+0-mv-m*hmca7fl&ag9g0(%$(hpdegao*^#%-di'

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
)

ROOT_URLCONF = 'django_dropbox_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django_dropbox',
    'dropbox_testing',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
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

try:
    from local_settings import *
except ImportError:
    raise ImportError('You must add local_settings.py file')
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'django_dropbox_project.views.home', name='home'),
    # url(r'^django_dropbox_project/', include('django_dropbox_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
