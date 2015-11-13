__FILENAME__ = models

########NEW FILE########
__FILENAME__ = s3
"""
    Two classes for media storage
"""

from storages.backends.s3boto import S3BotoStorage
from django.conf import settings

class FixedS3BotoStorage(S3BotoStorage):
    """
    fix the broken javascript admin resources with S3Boto on Django 1.4
    for more info see http://code.larlet.fr/django-storages/issue/121/s3boto-admin-prefix-issue-with-django-14
    """
    def url(self, name):
        url = super(FixedS3BotoStorage, self).url(name)
        if name.endswith('/') and not url.endswith('/'):
            url += '/'
        return url

class StaticStorage(FixedS3BotoStorage):
    """
    Storage for static files.
    The folder is defined in settings.STATIC_S3_PATH
    """

    def __init__(self, *args, **kwargs):
        kwargs['location'] = settings.STATIC_S3_PATH
        super(StaticStorage, self).__init__(*args, **kwargs)

class DefaultStorage(FixedS3BotoStorage):
    """
    Storage for uploaded media files.
    The folder is defined in settings.DEFAULT_S3_PATH
    """

    def __init__(self, *args, **kwargs):
        kwargs['location'] = settings.DEFAULT_S3_PATH
        super(DefaultStorage, self).__init__(*args, **kwargs)
########NEW FILE########
__FILENAME__ = testS3
"""
    Some tests to make sure that django-s3-folder-storage is storing uploaded
    files to S3 as expected.
    
    Designed to be run within a project to confirm that settings are correctly
    set up.
"""

import string
import random
import sys
import os

from django.test import TestCase
from django.core.files.base import ContentFile

from s3_folder_storage.s3 import DefaultStorage, StaticStorage

__all__ = (
    'ConfigurationTest',
)

class ConfigurationTest(TestCase):

    def setUp(self):
        """
            Generate a random string to test in the file content
        """
        chars = string.ascii_uppercase + string.digits
        self.file_text = ''.join(random.choice(chars) for x in range(6))
        self.file_text = "Dummy Test: %s" % self.file_text
        self.VERBOSE = False

    def testMediaUpload(self):
        """
            Upload a file and then confirm that it was uploaded
            for Media and Static files
        """
        self._testUpload(DefaultStorage(), 'media')
        self._testUpload(StaticStorage(), 'static')

    def _testUpload(self, storage, folder):
        
        # upload a file
        name = 's3dummyfile.txt'
        content = ContentFile(self.file_text)
        storage.save(name, content)
        
        if self.VERBOSE:
            print
            print "Write: %s/%s" % (folder, name)
            print "Content: '%s'" % self.file_text
        
        # confirm it was uploaded
        f = storage.open(name, 'r')
        file_text = f.read()
        self.assertEqual(file_text, self.file_text)

        if self.VERBOSE:
            print "Read: %s" % f.key.name
            print >> sys.stdout, "Content: '%s'" % file_text
        
        self.assertEqual(f.key.name, "%s/%s" % (folder, name))
        f.close()
        
        if self.VERBOSE:
            print "cleaning up: deleting file: %s" % f.key.name
        storage.bucket.delete_key(f.key)
        
        # # print >> sys.stdout, os.path.abspath(f)
        # print f.__dict__.keys()
        # print f.name
        # print f.key.__dict__.keys()
        # print "key: %s" % f.key
        # print "path: %s" % f.key.path
        # print "name: %s" % f.key.name
########NEW FILE########
__FILENAME__ = tests
import os
import sys
import django

BASE_PATH = os.path.dirname(__file__)

def main():
    """
    Standalone django model test with a 'memory-only-django-installation'.
    You can play with a django model without a complete django app installation.
    http://www.djangosnippets.org/snippets/1044/
    """
    sys.exc_clear()

    os.environ["DJANGO_SETTINGS_MODULE"] = "django.conf.global_settings"
    from django.conf import global_settings

    global_settings.INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.sessions',
        'django.contrib.contenttypes',
        's3_folder_storage',
    )
    if django.VERSION > (1,2):
        global_settings.DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_PATH, 'connpass.sqlite'),
                'USER': '',
                'PASSWORD': '',
                'HOST': '',
                'PORT': '',
            }
        }
    else:
        global_settings.DATABASE_ENGINE = "sqlite3"
        global_settings.DATABASE_NAME = ":memory:"

    global_settings.ROOT_URLCONF='beproud.django.authutils.tests.test_urls'
    global_settings.MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'beproud.django.authutils.middleware.AuthMiddleware',
    )
    
    # custom settings for tests
    
    global_settings.DEFAULT_FILE_STORAGE = 's3_folder_storage.s3.DefaultStorage'
    global_settings.DEFAULT_S3_PATH = "media"
    global_settings.STATICFILES_STORAGE = 's3_folder_storage.s3.StaticStorage'
    global_settings.STATIC_S3_PATH = "static"

    # requires some envifonment variables
    global_settings.AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', None)
    global_settings.AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
    global_settings.AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', None)

    global_settings.MEDIA_ROOT = '/%s/' % global_settings.DEFAULT_S3_PATH
    global_settings.MEDIA_URL = 'https://s3.amazonaws.com/%s/media/' % global_settings.AWS_STORAGE_BUCKET_NAME
    global_settings.STATIC_ROOT = "/%s/" % global_settings.STATIC_S3_PATH
    global_settings.STATIC_URL = 'https://s3.amazonaws.com/%s/static/' % global_settings.AWS_STORAGE_BUCKET_NAME
    global_settings.ADMIN_MEDIA_PREFIX = global_settings.STATIC_URL + 'admin/' 

    # global_settings.DEFAULT_FILE_STORAGE = 'backends.s3boto.S3BotoStorage'
    # global_settings.AWS_IS_GZIPPED = True
    global_settings.SECRET_KEY = "blahblah"

    from django.test.utils import get_runner
    test_runner = get_runner(global_settings)

    # import pdb; pdb.set_trace()
    
    if django.VERSION > (1,2):
        test_runner = test_runner()
        failures = test_runner.run_tests(['s3_folder_storage',])
    else:
        failures = test_runner(['s3_folder_storage',], verbosity=1)
    sys.exit(failures)

if __name__ == '__main__':
    main()
########NEW FILE########
