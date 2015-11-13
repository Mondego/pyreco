__FILENAME__ = models

########NEW FILE########
__FILENAME__ = storage
# -*- coding: utf-8 -*-

import os

from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import FileSystemStorage
from django.utils._os import safe_join
from django.utils.encoding import smart_str

from djcastor import utils


class CAStorage(FileSystemStorage):

    """
    A content-addressable storage backend for Django.

    Basic Usage
    -----------

        from django.db import models
        from djcastor import CAStorage

        class MyModel(models.Model):
            ...
            uploaded_file = models.FileField(storage=CAStorage())

    Extended Usage
    --------------

    There are several options you can pass to the `CAStorage` constructor. The
    first two are inherited from `django.core.files.storage.FileSystemStorage`:

    *   `location`: The absolute path to the directory that will hold uploaded
        files. If omitted, this will be set to the value of the `MEDIA_ROOT`
        setting.

    *   `base_url`: The URL that serves the files stored at this location. If
        omitted, this will be set to the value of the `MEDIA_URL` setting.

    `CAStorage` also adds two custom options:

    *   `keep_extension` (default `True`): Preserve the extension on uploaded
        files. This allows the webserver to guess their `Content-Type`.

    *   `sharding` (default `(2, 2)`): The width and depth to use when sharding
        digests, expressed as a two-tuple. `django-castor` shards files in the
        uploads directory based on their digests; this prevents filesystem
        issues when too many files are in a single directory. Sharding is based
        on two parameters: *width* and *depth*. The following examples show how
        these affect the sharding:

            >>> digest = '1f09d30c707d53f3d16c530dd73d70a6ce7596a9'

            >>> print shard(digest, width=2, depth=2)
            1f/09/1f09d30c707d53f3d16c530dd73d70a6ce7596a9

            >>> print shard(digest, width=2, depth=3)
            1f/09/d3/1f09d30c707d53f3d16c530dd73d70a6ce7596a9

            >>> print shard(digest, width=3, depth=2)
            1f0/9d3/1f09d30c707d53f3d16c530dd73d70a6ce7596a9

    """

    def __init__(self, location=None, base_url=None, keep_extension=True,
                 sharding=(2, 2)):
        # Avoid a confusing issue when you don't have a trailing slash: URLs
        # are generated which point to the parent. This is due to the behavior
        # of `urlparse.urljoin()`.
        if base_url is not None and not base_url.endswith('/'):
            base_url += '/'

        super(CAStorage, self).__init__(location=location, base_url=base_url)

        self.shard_width, self.shard_depth = sharding
        self.keep_extension = keep_extension

    @staticmethod
    def get_available_name(name):
        """Return the name as-is; in CAS, given names are ignored anyway."""

        return name

    def digest(self, content):
        if hasattr(content, 'temporary_file_path'):
            return utils.hash_filename(content.temporary_file_path())
        digest = utils.hash_chunks(content.chunks())
        content.seek(0)
        return digest

    def shard(self, hexdigest):
        return list(utils.shard(hexdigest, self.shard_width, self.shard_depth,
                                rest_only=False))

    def path(self, hexdigest):
        shards = self.shard(hexdigest)

        try:
            path = safe_join(self.location, *shards)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." %
                                      ('/'.join(shards),))

        return smart_str(os.path.normpath(path))

    def url(self, name):
        return super(CAStorage, self).url('/'.join(self.shard(name)))

    def delete(self, name, sure=False):
        if not sure:
            # Ignore automatic deletions; we don't know how many different
            # records point to one file.
            return

        path = name
        if os.path.sep not in path:
            path = self.path(name)
        utils.rm_file_and_empty_parents(path, root=self.location)

    def _save(self, name, content):
        digest = self.digest(content)
        if self.keep_extension:
            digest += os.path.splitext(name)[1]
        path = self.path(digest)
        if os.path.exists(path):
            return digest
        return super(CAStorage, self)._save(digest, content)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import hashlib
import os

from django.core.files import File
from django.core.files.uploadedfile import UploadedFile


def hash_filename(filename, digestmod=hashlib.sha1,
                  chunk_size=UploadedFile.DEFAULT_CHUNK_SIZE):

    """
    Return the hash of the contents of a filename, using chunks.

        >>> import os.path as p
        >>> filename = p.join(p.abspath(p.dirname(__file__)), 'models.py')
        >>> hash_filename(filename)
        'da39a3ee5e6b4b0d3255bfef95601890afd80709'

    """

    fileobj = File(open(filename))
    try:
        return hash_chunks(fileobj.chunks(chunk_size=chunk_size))
    finally:
        fileobj.close()


def hash_chunks(iterator, digestmod=hashlib.sha1):

    """
    Hash the contents of a string-yielding iterator.

        >>> import hashlib
        >>> digest = hashlib.sha1('abc').hexdigest()
        >>> strings = iter(['a', 'b', 'c'])
        >>> hash_chunks(strings, digestmod=hashlib.sha1) == digest
        True

    """

    digest = digestmod()
    for chunk in iterator:
        digest.update(chunk)
    return digest.hexdigest()


def shard(string, width, depth, rest_only=False):

    """
    Shard the given string by a width and depth. Returns a generator.

    A width and depth of 2 indicates that there should be 2 shards of length 2.

        >>> digest = '1f09d30c707d53f3d16c530dd73d70a6ce7596a9'
        >>> list(shard(digest, 2, 2))
        ['1f', '09', '1f09d30c707d53f3d16c530dd73d70a6ce7596a9']

    A width of 5 and depth of 1 will result in only one shard of length 5.

        >>> list(shard(digest, 5, 1))
        ['1f09d', '1f09d30c707d53f3d16c530dd73d70a6ce7596a9']

    A width of 1 and depth of 5 will give 5 shards of length 1.

        >>> list(shard(digest, 1, 5))
        ['1', 'f', '0', '9', 'd', '1f09d30c707d53f3d16c530dd73d70a6ce7596a9']

    If the `rest_only` parameter is true, only the remainder of the sharded
    string will be used as the last element:

        >>> list(shard(digest, 2, 2, rest_only=True))
        ['1f', '09', 'd30c707d53f3d16c530dd73d70a6ce7596a9']

    """

    for i in xrange(depth):
        yield string[(width * i):(width * (i + 1))]

    if rest_only:
        yield string[(width * depth):]
    else:
        yield string


def rm_file_and_empty_parents(filename, root=None):
    """Delete a file, keep removing empty parent dirs up to `root`."""

    if root:
        root_stat = os.stat(root)

    os.unlink(filename)
    directory = os.path.dirname(filename)
    while not (root and os.path.samestat(root_stat, os.stat(directory))):
        if os.listdir(directory):
            break
        os.rmdir(directory)
        directory = os.path.dirname(directory)

########NEW FILE########
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
MEDIA_ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

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
    'uploads',
)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from django.db import models

from djcastor import CAStorage


class Upload(models.Model):
    
    file = models.FileField(upload_to='uploads', storage=CAStorage())
    created = models.DateTimeField(auto_now_add=True)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from StringIO import StringIO
import hashlib
import os
import shutil

from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.conf import settings
from django.test import TestCase

from uploads.models import Upload


class ReadTest(TestCase):

    fixtures = ['testing']

    def test(self):
        upload = Upload.objects.get(pk=1)
        self.assertEqual(upload.file.read(), "Hello, World!\n")


class MemoryWriteTest(TestCase):

    def test(self):
        text = "Spam Spam Spam.\n"
        digest = hashlib.sha1(text).hexdigest()
        io = StringIO(text)

        new_upload = Upload(file=InMemoryUploadedFile(
            io, 'file', 'spam.txt', 'text/plain', len(text), 'utf-8'))
        new_upload.save()

        # Upload has been saved to the database.
        self.assert_(new_upload.pk)

        # Upload contains correct content.
        self.assertEqual(new_upload.file.read(), text)

        # Filename is the hash of the file contents.
        self.assert_(new_upload.file.name.startswith(digest))

    def tearDown(self):
        # Remove the upload in `MEDIA_ROOT`.
        directory = os.path.join(settings.MEDIA_ROOT, '8f')
        if os.path.exists(directory):
            shutil.rmtree(directory)


class FileWriteTest(TestCase):

    def setUp(self):
        self.text = "Spam Spam Spam Spam.\n"
        self.digest = hashlib.sha1(self.text).hexdigest()
        self.tempfile = TemporaryUploadedFile('spam4.txt', 'text/plain',
                                              len(self.text), 'utf-8')
        self.tempfile.file.write(self.text)
        self.tempfile.file.seek(0)

    def test(self):
        new_upload = Upload(file=self.tempfile)
        new_upload.save()

        # Upload has been saved to the database.
        self.assert_(new_upload.pk)

        # Upload contains correct content.
        self.assertEqual(new_upload.file.read(), self.text)

        # Filename is the hash of the file contents.
        self.assert_(new_upload.file.name.startswith(self.digest))

    def tearDown(self):
        self.tempfile.close()  # Also deletes the temp file.

        # Remove the upload in `MEDIA_ROOT`.
        directory = os.path.join(settings.MEDIA_ROOT, '24')
        if os.path.exists(directory):
            shutil.rmtree(directory)

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
