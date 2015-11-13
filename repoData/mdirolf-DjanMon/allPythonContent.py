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
# Django settings for DjanMon project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = ''             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

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
SECRET_KEY = '-5x#-$^y4ys^#vm7#(bdyo5%*3qta*opfs6qz2i^1-y8%+q9%c'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
#    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'DjanMon.urls'

TEMPLATE_DIRS = (
    "templates"
)

INSTALLED_APPS = (
#    'django.contrib.auth',
    'django.contrib.contenttypes',
#    'django.contrib.sessions',
    'django.contrib.sites',
    'DjanMon.status',
)

STATIC_DOC_ROOT = 'static'

########NEW FILE########
__FILENAME__ = models
# from django.db import models

# We don't need models with MongoDB. If you really *want* models check out
# something like MongoKit (http://bitbucket.org/namlook/mongokit/) to add
# an ORM-ish layer on top of PyMongo.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
import datetime
import string
import random
import mimetypes
import cStringIO as StringIO

from PIL import Image
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from pymongo.connection import Connection
from pymongo import DESCENDING
import gridfs

db = Connection().sms
fs = gridfs.GridFS(db)
thumbs = gridfs.GridFS(db, collection='thumb')

page_size = 10

def _generate_filename(name):
    """Generate a unique filename to use for GridFS, using a given name.

    Just appends some random characters before the file extension and
    checks for uniqueness.
    """
    filename = name.rsplit(".", 1)
    filename[0] = "%s-%s" % (filename[0],
                             "".join(random.sample(string.letters + string.digits, 10)))
    filename = ".".join(filename)

    # Try again if this filename already exists
    if fs.exists(filename=filename):
    	return _generate_filename(name)
    else:
    	return filename

def index(request, page=0):
    if request.method == 'POST':
        if 'nickname' not in request.POST or 'text' not in request.POST:
            return HttpResponseRedirect("/")

        message = {"nickname": request.POST['nickname'],
                   "text": request.POST['text'],
                   "date": datetime.datetime.utcnow()}

        if "image" in request.FILES:
            filename = _generate_filename(request.FILES['image'].name)
            mimetype = request.FILES['image'].content_type

            # Only accept appropriate file extensions
            if not filename.endswith((".jpg", ".JPG", ".jpeg", ".JPEG", ".png",
                                      ".PNG", ".bmp", ".BMP", ".gif", ".GIF")):
                return HttpResponseRedirect("/")

            message["image"] = filename

            # Save fullsize image
            image = request.FILES['image'].read()
            fs.put(image, content_type=mimetype, filename=filename)

            # Save thumbnail
            image = Image.open(StringIO.StringIO(image))
            image.thumbnail((80, 60), Image.ANTIALIAS)
            data = StringIO.StringIO()
            image.save(data, image.format)
            thumbs.put(data.getvalue(), content_type=mimetype, filename=filename)
            data.close()

        db.messages.insert(message)
        return HttpResponseRedirect("/")
    else:
        page = int(page)

        previous = "hack"
        if page > 0:
            previous = page - 1

        next = "hack"
        if db.messages.count() > (page + 1) * page_size:
            next = page + 1

        messages = db.messages.find().sort("date", DESCENDING).limit(page_size).skip(page * page_size)
        return render_to_response('status/index.html', {'messages': messages,
                                                        'previous': previous,
                                                        'next': next})

def file(request, collection_or_filename, filename=None):
    if filename is not None:
        if collection_or_filename == "thumb":
            data = thumbs.get_last_version(filename)
        else:
            data = fs.get_last_version(filename)
    else:
        data = fs.get_last_version(collection_or_filename)
    mimetype = data.content_type or mimetypes.guess_type(filename or collection_or_filename)
    return HttpResponse(data, mimetype=mimetype)


########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       (r'^$', 'status.views.index'),
                       (r'^page/(?P<page>\d+)$', 'status.views.index'),
                       (r'^image/thumb/(?P<filename>.*)$', 'status.views.file',
                        {'collection_or_filename': 'thumb'}),
                       (r'^image/(?P<collection_or_filename>.*)$', 'status.views.file'),
                       (r'^static/(?P<path>.*)$', 'django.views.static.serve',
                        {'document_root': settings.STATIC_DOC_ROOT}),
                       )

########NEW FILE########
