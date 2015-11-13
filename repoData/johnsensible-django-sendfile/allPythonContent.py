__FILENAME__ = admin
from django.contrib import admin

from .models import Download

class DownloadAdmin(admin.ModelAdmin):
    list_display = ['title', 'file']

admin.site.register(Download, DownloadAdmin)


########NEW FILE########
__FILENAME__ = models
from django.db import models

from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.storage import FileSystemStorage

sendfile_storage = FileSystemStorage(location=settings.SENDFILE_ROOT)

class Download(models.Model):
    users = models.ManyToManyField(User, blank=True)
    is_public = models.BooleanField(default=True)
    title = models.CharField(max_length=255)
    # files stored in SENDFILE_ROOT directory (which should be protected)
    file = models.FileField(upload_to='download', storage=sendfile_storage)
    
    def is_user_allowed(self, user):
        return self.users.filter(pk=user.pk).exists()

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('download', [self.pk], {})

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
__FILENAME__ = urls
from django.conf.urls.defaults import *

from .views import download, download_list

urlpatterns = patterns('',
    url(r'^$', download_list),
    url(r'(?P<download_id>\d+)/$', download, name='download'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.template import RequestContext

from sendfile import sendfile

from .models import Download

def download(request, download_id):
    download = get_object_or_404(Download, pk=download_id)
    if download.is_public:
        return sendfile(request, download.file.path)
    return _auth_download(request, download)
    

@login_required
def _auth_download(request, download):
    if not download.is_user_allowed(request.user):
        return HttpResponseForbidden('Sorry, you cannot access this file')
    return sendfile(request, download.file.path)


def download_list(request):
    downloads = Download.objects.all()
    if request.user.is_authenticated():
        downloads = downloads.filter(Q(is_public=True) | Q(users=request.user))
    else:
        downloads = downloads.filter(is_public=True)
    return render_to_response('download/download_list.html',
                              {'download_list': downloads}, 
                              context_instance=RequestContext(request))

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
# Django settings for protected_downloads project.

import os.path

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'download.db'),
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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
SECRET_KEY = 'n309^dwk=@+g72ko--8vjyz&1v0u%xf#*0=wzr=2n#f3hb0a=l'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'protected_downloads.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'download',
    'sendfile',
)


# SENDFILE settings
SENDFILE_BACKEND = 'sendfile.backends.development'
#SENDFILE_BACKEND = 'sendfile.backends.xsendfile'
#SENDFILE_BACKEND = 'sendfile.backends.nginx'
SENDFILE_ROOT = os.path.join(PROJECT_ROOT, 'protected')
SENDFILE_URL = '/protected'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^', include('protected_downloads.download.urls')),
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = development
from django.views.static import serve

import os.path

def sendfile(request, filename, **kwargs):
    '''
    Send file using django dev static file server.

    DO NOT USE IN PRODUCTION
    this is only to be used when developing and is provided
    for convenience only
    '''
    dirname = os.path.dirname(filename)
    basename = os.path.basename(filename)
    return serve(request, basename, dirname)

########NEW FILE########
__FILENAME__ = mod_wsgi
from django.http import HttpResponse

from _internalredirect import _convert_file_to_url

def sendfile(request, filename, **kwargs):
    response = HttpResponse()
    response['Location'] = _convert_file_to_url(filename)
    # need to destroy get_host() to stop django
    # rewriting our location to include http, so that
    # mod_wsgi is able to do the internal redirect
    request.get_host = lambda: ''

    return response


########NEW FILE########
__FILENAME__ = nginx
from django.http import HttpResponse

from _internalredirect import _convert_file_to_url

def sendfile(request, filename, **kwargs):
    response = HttpResponse()
    url = _convert_file_to_url(filename)
    response['X-Accel-Redirect'] = url.encode('utf-8')

    return response

########NEW FILE########
__FILENAME__ = simple
import os
import stat
import re
from email.Utils import parsedate_tz, mktime_tz

from django.core.files.base import File
from django.http import HttpResponse, HttpResponseNotModified
from django.utils.http import http_date

def sendfile(request, filename, **kwargs):
    # Respect the If-Modified-Since header.
    statobj = os.stat(filename)

    if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'),
                              statobj[stat.ST_MTIME], statobj[stat.ST_SIZE]):
        return HttpResponseNotModified()
    
    
    response = HttpResponse(File(file(filename, 'rb')))

    response["Last-Modified"] = http_date(statobj[stat.ST_MTIME])
    return response
    
def was_modified_since(header=None, mtime=0, size=0):
    """
    Was something modified since the user last downloaded it?

    header
      This is the value of the If-Modified-Since header.  If this is None,
      I'll just return True.

    mtime
      This is the modification time of the item we're talking about.

    size
      This is the size of the item we're talking about.
    """
    try:
        if header is None:
            raise ValueError
        matches = re.match(r"^([^;]+)(; length=([0-9]+))?$", header,
                           re.IGNORECASE)
        header_date = parsedate_tz(matches.group(1))
        if header_date is None:
            raise ValueError
        header_mtime = mktime_tz(header_date)
        header_len = matches.group(3)
        if header_len and int(header_len) != size:
            raise ValueError
        if mtime > header_mtime:
            raise ValueError
    except (AttributeError, ValueError, OverflowError):
        return True
    return False


########NEW FILE########
__FILENAME__ = xsendfile
from django.http import HttpResponse

def sendfile(request, filename, **kwargs):
    response = HttpResponse()
    response['X-Sendfile'] = unicode(filename).encode('utf-8')

    return response


########NEW FILE########
__FILENAME__ = _internalredirect
from django.conf import settings
import os.path

def _convert_file_to_url(filename):
    relpath = os.path.relpath(filename, settings.SENDFILE_ROOT)
    
    url = [settings.SENDFILE_URL]

    while relpath:
        relpath, head = os.path.split(relpath)
        url.insert(1, head)

    return u'/'.join(url)


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# coding=utf-8

from django.conf import settings
from django.test import TestCase
from django.http import HttpResponse, Http404, HttpRequest
import os.path
from tempfile import mkdtemp
import shutil
from sendfile import sendfile as real_sendfile, _get_sendfile


def sendfile(request, filename, **kwargs):
    # just a simple response with the filename
    # as content - so we can test without a backend active
    return HttpResponse(filename)


class TempFileTestCase(TestCase):

    def setUp(self):
        super(TempFileTestCase, self).setUp()
        self.TEMP_FILE_ROOT = mkdtemp()
    
    def tearDown(self):
        super(TempFileTestCase, self).tearDown()
        if os.path.exists(self.TEMP_FILE_ROOT):
            shutil.rmtree(self.TEMP_FILE_ROOT)

    def ensure_file(self, filename):
        path = os.path.join(self.TEMP_FILE_ROOT, filename)
        if not os.path.exists(path):
            open(path, 'w').close()
        return path


class TestSendfile(TempFileTestCase):

    def setUp(self):
        super(TestSendfile, self).setUp()
        # set ourselves to be the sendfile backend
        settings.SENDFILE_BACKEND = 'sendfile.tests'
        _get_sendfile.clear()
    
    def _get_readme(self):
        return self.ensure_file('testfile.txt')

    def test_404(self):
        try:
            real_sendfile(HttpRequest(), 'fhdsjfhjk.txt')
        except Http404:
            pass

    def test_sendfile(self):
        response = real_sendfile(HttpRequest(), self._get_readme())
        self.assertTrue(response is not None)
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(self._get_readme(), response.content)

    def test_set_mimetype(self):
        response = real_sendfile(HttpRequest(), self._get_readme(), mimetype='text/plain')
        self.assertTrue(response is not None)
        self.assertEqual('text/plain', response['Content-Type'])

    def test_set_encoding(self):
        response = real_sendfile(HttpRequest(), self._get_readme(), encoding='utf8')
        self.assertTrue(response is not None)
        self.assertEqual('utf8', response['Content-Encoding'])

    def test_attachment(self):
        response = real_sendfile(HttpRequest(), self._get_readme(), attachment=True)
        self.assertTrue(response is not None)
        self.assertEqual('attachment; filename="testfile.txt"', response['Content-Disposition'])

    def test_attachment_filename_false(self):
        response = real_sendfile(HttpRequest(), self._get_readme(), attachment=True, attachment_filename=False)
        self.assertTrue(response is not None)
        self.assertEqual('attachment', response['Content-Disposition'])

    def test_attachment_filename(self):
        response = real_sendfile(HttpRequest(), self._get_readme(), attachment=True, attachment_filename='tests.txt')
        self.assertTrue(response is not None)
        self.assertEqual('attachment; filename="tests.txt"', response['Content-Disposition'])

    def test_attachment_filename_unicode(self):
        response = real_sendfile(HttpRequest(), self._get_readme(), attachment=True, attachment_filename='test’s.txt')
        self.assertTrue(response is not None)
        self.assertEqual('attachment; filename="test\'s.txt"; filename*=UTF-8\'\'test%E2%80%99s.txt', response['Content-Disposition'])


class TestXSendfileBackend(TempFileTestCase):

    def setUp(self):
        super(TestXSendfileBackend, self).setUp()
        settings.SENDFILE_BACKEND = 'sendfile.backends.xsendfile'
        _get_sendfile.clear()

    def test_correct_file_in_xsendfile_header(self):
        filepath = self.ensure_file('readme.txt')
        response = real_sendfile(HttpRequest(), filepath)
        self.assertTrue(response is not None)
        self.assertEqual(filepath, response['X-Sendfile'])

    def test_xsendfile_header_containing_unicode(self):
        filepath = self.ensure_file(u'péter_là_gueule.txt')
        response = real_sendfile(HttpRequest(), filepath)
        self.assertTrue(response is not None)
        self.assertEqual(filepath, response['X-Sendfile'].decode('utf-8'))


class TestNginxBackend(TempFileTestCase):

    def setUp(self):
        super(TestNginxBackend, self).setUp()
        settings.SENDFILE_BACKEND = 'sendfile.backends.nginx'
        settings.SENDFILE_ROOT = self.TEMP_FILE_ROOT
        settings.SENDFILE_URL = '/private'
        _get_sendfile.clear()

    def test_correct_url_in_xaccelredirect_header(self):
        filepath = self.ensure_file('readme.txt')
        response = real_sendfile(HttpRequest(), filepath)
        self.assertTrue(response is not None)
        self.assertEqual('/private/readme.txt', response['X-Accel-Redirect'])

    def test_xaccelredirect_header_containing_unicode(self):
        filepath = self.ensure_file(u'péter_là_gueule.txt')
        response = real_sendfile(HttpRequest(), filepath)
        self.assertTrue(response is not None)
        self.assertEqual(u'/private/péter_là_gueule.txt', response['X-Accel-Redirect'].decode('utf-8'))

########NEW FILE########
