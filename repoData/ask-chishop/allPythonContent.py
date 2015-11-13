__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser()
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=False,
                   help="Use Disribute rather than Setuptools.")

parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse(requirement)).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse(requirement)).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = default
# Django settings for djangopypi project.
import os

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

# Allow uploading a new distribution file for a project version
# if a file of that type already exists.
#
# The default on PyPI is to not allow this, but it can be real handy
# if you're sloppy.
DJANGOPYPI_ALLOW_VERSION_OVERWRITE = False
DJANGOPYPI_RELEASE_UPLOAD_TO = 'dists'

# change to False if you do not want Django's default server to serve static pages
LOCAL_DEVELOPMENT = True

REGISTRATION_OPEN = True
ACCOUNT_ACTIVATION_DAYS = 7
LOGIN_REDIRECT_URL = "/"

EMAIL_HOST = 'localhost'
DEFAULT_FROM_EMAIL = ''
SERVER_EMAIL = DEFAULT_FROM_EMAIL

MANAGERS = ADMINS

DATABASE_ENGINE = ''
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

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
here = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
MEDIA_ROOT = os.path.join(here, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'w_#0r2hh)=!zbynb*gg&969@)sy#^-^ia3m*+sd4@lst$zyaxu'

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

ROOT_URLCONF = 'chishop.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.markup',
    'django.contrib.admindocs',
    'registration',
    'djangopypi',
)

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
__FILENAME__ = production_example
from conf.default import *
import os

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
     ('chishop', 'example@example.org'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'postgresql_psycopg2'
DATABASE_NAME = 'chishop'
DATABASE_USER = 'chishop'
DATABASE_PASSWORD = 'chishop'
DATABASE_HOST = ''
DATABASE_PORT = ''

########NEW FILE########
__FILENAME__ = settings
from conf.default import *
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG
LOCAL_DEVELOPMENT = True

if LOCAL_DEVELOPMENT:
    import sys
    sys.path.append(os.path.dirname(__file__))

ADMINS = (
     ('chishop', 'example@example.org'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(here, 'devdatabase.db')
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url, include, handler404, handler500
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('')

# Serve static pages.
if settings.LOCAL_DEVELOPMENT:
    urlpatterns += patterns("django.views",
        url(r"^%s(?P<path>.*)$" % settings.MEDIA_URL[1:], "static.serve", {
            "document_root": settings.MEDIA_ROOT}))

urlpatterns += patterns("",
    # Admin interface
    url(r'^admin/doc/', include("django.contrib.admindocs.urls")),
    url(r'^admin/(.*)', admin.site.root),

    # Registration
    url(r'^accounts/', include('registration.backends.default.urls')),

    # The Chishop
    url(r'', include("djangopypi.urls"))
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from djangopypi.models import Project, Release, Classifier

admin.site.register(Project)
admin.site.register(Release)
admin.site.register(Classifier)

########NEW FILE########
__FILENAME__ = forms
import os
from django import forms
from django.conf import settings
from djangopypi.models import Project, Classifier, Release
from django.utils.translation import ugettext_lazy as _


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ['owner', 'classifiers']


class ReleaseForm(forms.ModelForm):
    class Meta:
        model = Release
        exclude = ['project']
########NEW FILE########
__FILENAME__ = http
from django.http import HttpResponse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict
from django.contrib.auth import authenticate


class HttpResponseNotImplemented(HttpResponse):
    status_code = 501


class HttpResponseUnauthorized(HttpResponse):
    status_code = 401

    def __init__(self, realm):
        HttpResponse.__init__(self)
        self['WWW-Authenticate'] = 'Basic realm="%s"' % realm


def parse_distutils_request(request):
    raw_post_data = request.raw_post_data
    sep = raw_post_data.splitlines()[1]
    items = raw_post_data.split(sep)
    post_data = {}
    files = {}
    for part in filter(lambda e: not e.isspace(), items):
        item = part.splitlines()
        if len(item) < 2:
            continue
        header = item[1].replace("Content-Disposition: form-data; ", "")
        kvpairs = header.split(";")
        headers = {}
        for kvpair in kvpairs:
            if not kvpair:
                continue
            key, value = kvpair.split("=")
            headers[key] = value.strip('"')
        if "name" not in headers:
            continue
        content = part[len("\n".join(item[0:2]))+2:len(part)-1]
        if "filename" in headers:
            file = SimpleUploadedFile(headers["filename"], content,
                    content_type="application/gzip")
            files["distribution"] = [file]
        elif headers["name"] in post_data:
            post_data[headers["name"]].append(content)
        else:
            # Distutils sends UNKNOWN for empty fields (e.g platform)
            # [russell.sim@gmail.com]
            if content == 'UNKNOWN':
                post_data[headers["name"]] = [None]
            else:
                post_data[headers["name"]] = [content]

    return MultiValueDict(post_data), MultiValueDict(files)


def login_basic_auth(request):
    authentication = request.META.get("HTTP_AUTHORIZATION")
    if not authentication:
        return
    (authmeth, auth) = authentication.split(' ', 1)
    if authmeth.lower() != "basic":
        return
    auth = auth.strip().decode("base64")
    username, password = auth.split(":", 1)
    return authenticate(username=username, password=password)

########NEW FILE########
__FILENAME__ = loadclassifiers
"""
Management command for loading all the known classifiers from the official
pypi, or from a file/url.

Note, pypi docs says to not add classifiers that are not used in submitted
projects. On the other hand it can be usefull to have a list of classifiers
to choose if you have to modify package data. Use it if you need it.
"""

from __future__ import with_statement
import urllib
import os.path

from django.core.management.base import BaseCommand
from djangopypi.models import Classifier

CLASSIFIERS_URL = "http://pypi.python.org/pypi?%3Aaction=list_classifiers"

class Command(BaseCommand):
    help = """Load all classifiers from pypi. If any arguments are given,
they will be used as paths or urls for classifiers instead of using the
official pypi list url"""

    def handle(self, *args, **options):
        args = args or [CLASSIFIERS_URL]

        cnt = 0
        for location in args:
            print "Loading %s" % location
            lines = self._get_lines(location)
            for name in lines:
                c, created = Classifier.objects.get_or_create(name=name)
                if created:
                    c.save()
                    cnt += 1

        print "Added %s new classifiers from %s source(s)" % (cnt, len(args))

    def _get_lines(self, location):
        """Return a list of lines for a lication that can be a file or
        a url. If path/url doesn't exist, returns an empty list"""
        try: # This is dirty, but OK I think. both net and file ops raise IOE
            if location.startswith(("http://", "https://")):
                fp = urllib.urlopen(location)
                return [e.strip() for e in fp.read().split('\n')
                        if e and not e.isspace()]
            else:
                fp = open(location)
                return [e.strip() for e in fp.readlines()
                        if e and not e.isspace()]
        except IOError:
            print "Couldn't load %s" % location
            return []

########NEW FILE########
__FILENAME__ = ppadd
"""
Management command for adding a package to the repository. Supposed to be the
equivelant of calling easy_install, but the install target is the chishop.
"""

from __future__ import with_statement
import os
import tempfile
import shutil
import urllib

import pkginfo

from django.core.files.base import File
from django.core.management.base import LabelCommand
from optparse import make_option
from contextlib import contextmanager
from urlparse import urlsplit
from setuptools.package_index import PackageIndex
from django.contrib.auth.models import User
from djangopypi.models import Project, Release, Classifier





@contextmanager
def tempdir():
    """Simple context that provides a temporary directory that is deleted
    when the context is exited."""
    d = tempfile.mkdtemp(".tmp", "djangopypi.")
    yield d
    shutil.rmtree(d)

class Command(LabelCommand):
    option_list = LabelCommand.option_list + (
            make_option("-o", "--owner", help="add packages as OWNER",
                        metavar="OWNER", default=None),
        )
    help = """Add one or more packages to the repository. Each argument can
be a package name or a URL to an archive or egg. Package names honour
the same rules as easy_install with regard to indicating versions etc.

If a version of the package exists, but is older than what we want to install,
the owner remains the same.

For new packages there needs to be an owner. If the --owner option is present
we use that value. If not, we try to match the maintainer of the package, form
the metadata, with a user in out database, based on the If it's a new package
and the maintainer emailmatches someone in our user list, we use that. If not,
the package can not be
added"""

    def __init__(self, *args, **kwargs):
        self.pypi = PackageIndex()
        LabelCommand.__init__(self, *args, **kwargs)

    def handle_label(self, label, **options):
        with tempdir() as tmp:
            path = self.pypi.download(label, tmp)
            if path:
                self._save_package(path, options["owner"])
            else:
                print "Could not add %s. Not found." % label

    def _save_package(self, path, ownerid):
        meta = self._get_meta(path)

        try:
            # can't use get_or_create as that demands there be an owner
            project = Project.objects.get(name=meta.name)
            isnewproject = False
        except Project.DoesNotExist:
            project = Project(name=meta.name)
            isnewproject = True

        release = project.get_release(meta.version)
        if not isnewproject and release and release.version == meta.version:
            print "%s-%s already added" % (meta.name, meta.version)
            return

        # algorithm as follows: If owner is given, try to grab user with that
        # username from db. If doesn't exist, bail. If no owner set look at
        # mail address from metadata and try to get that user. If it exists
        # use it. If not, bail.
        owner = None

        if ownerid:
            try:
                if "@" in ownerid:
                    owner = User.objects.get(email=ownerid)
                else:
                    owner = User.objects.get(username=ownerid)
            except User.DoesNotExist:
                pass
        else:
            try:
                owner = User.objects.get(email=meta.author_email)
            except User.DoesNotExist:
                pass

        if not owner:
            print "No owner defined. Use --owner to force one"
            return

        # at this point we have metadata and an owner, can safely add it.

        project.owner = owner
        # Some packages don't have proper licence, seems to be a problem
        # with setup.py upload. Use "UNKNOWN"
        project.license = meta.license or "Unknown"
        project.metadata_version = meta.metadata_version
        project.author = meta.author
        project.home_page = meta.home_page
        project.download_url = meta.download_url
        project.summary = meta.summary
        project.description = meta.description
        project.author_email = meta.author_email

        project.save()

        for classifier in meta.classifiers:
            project.classifiers.add(
                    Classifier.objects.get_or_create(name=classifier)[0])

        release = Release()
        release.version = meta.version
        release.project = project
        filename = os.path.basename(path)

        file = File(open(path, "rb"))
        release.distribution.save(filename, file)
        release.save()
        print "%s-%s added" % (meta.name, meta.version)

    def _get_meta(self, path):
        data = pkginfo.get_metadata(path)
        if data:
            return data
        else:
            print "Couldn't get metadata from %s. Not added to chishop" % os.path.basename(path)
            return None

########NEW FILE########
__FILENAME__ = models
import os
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

OS_NAMES = (
        ("aix", "AIX"),
        ("beos", "BeOS"),
        ("debian", "Debian Linux"),
        ("dos", "DOS"),
        ("freebsd", "FreeBSD"),
        ("hpux", "HP/UX"),
        ("mac", "Mac System x."),
        ("macos", "MacOS X"),
        ("mandrake", "Mandrake Linux"),
        ("netbsd", "NetBSD"),
        ("openbsd", "OpenBSD"),
        ("qnx", "QNX"),
        ("redhat", "RedHat Linux"),
        ("solaris", "SUN Solaris"),
        ("suse", "SuSE Linux"),
        ("yellowdog", "Yellow Dog Linux"),
)

ARCHITECTURES = (
    ("alpha", "Alpha"),
    ("hppa", "HPPA"),
    ("ix86", "Intel"),
    ("powerpc", "PowerPC"),
    ("sparc", "Sparc"),
    ("ultrasparc", "UltraSparc"),
)

UPLOAD_TO = getattr(settings,
    "DJANGOPYPI_RELEASE_UPLOAD_TO", 'dist')

class Classifier(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = _(u"classifier")
        verbose_name_plural = _(u"classifiers")

    def __unicode__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=255, unique=True)
    license = models.TextField(blank=True)
    metadata_version = models.CharField(max_length=64, default=1.0)
    author = models.CharField(max_length=128, blank=True)
    home_page = models.URLField(verify_exists=False, blank=True, null=True)
    download_url = models.CharField(max_length=200, blank=True, null=True)
    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    author_email = models.CharField(max_length=255, blank=True)
    classifiers = models.ManyToManyField(Classifier)
    owner = models.ForeignKey(User, related_name="projects")
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _(u"project")
        verbose_name_plural = _(u"projects")

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('djangopypi-show_links', (), {'dist_name': self.name})

    @models.permalink
    def get_pypi_absolute_url(self):
        return ('djangopypi-pypi_show_links', (), {'dist_name': self.name})

    def get_release(self, version):
        """Return the release object for version, or None"""
        try:
            return self.releases.get(version=version)
        except Release.DoesNotExist:
            return None

class Release(models.Model):
    version = models.CharField(max_length=32)
    distribution = models.FileField(upload_to=UPLOAD_TO)
    md5_digest = models.CharField(max_length=255, blank=True)
    platform = models.CharField(max_length=128, blank=True)
    signature = models.CharField(max_length=128, blank=True)
    filetype = models.CharField(max_length=255, blank=True)
    pyversion = models.CharField(max_length=32, blank=True)
    project = models.ForeignKey(Project, related_name="releases")
    upload_time = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _(u"release")
        verbose_name_plural = _(u"releases")
        unique_together = ("project", "version", "platform", "distribution", "pyversion")

    def __unicode__(self):
        return u"%s (%s)" % (self.release_name, self.platform)

    @property
    def type(self):
        dist_file_types = {
            'sdist':'Source',
            'bdist_dumb':'"dumb" binary',
            'bdist_rpm':'RPM',
            'bdist_wininst':'MS Windows installer',
            'bdist_egg':'Python Egg',
            'bdist_dmg':'OS X Disk Image'}
        return dist_file_types.get(self.filetype, self.filetype)

    @property
    def filename(self):
        return os.path.basename(self.distribution.name)

    @property
    def release_name(self):
        return u"%s-%s" % (self.project.name, self.version)

    @property
    def path(self):
        return self.distribution.name

    @models.permalink
    def get_absolute_url(self):
        return ('djangopypi-show_version', (), {'dist_name': self.project, 'version': self.version})

    def get_dl_url(self):
        return "%s#md5=%s" % (self.distribution.url, self.md5_digest)

########NEW FILE########
__FILENAME__ = safemarkup
from django import template
from django.conf import settings
from django.utils.encoding import smart_str, force_unicode
from django.utils.safestring import mark_safe

register = template.Library()


def saferst(value):
    try:
        from docutils.core import publish_parts
    except ImportError:
        return force_unicode(value)

    docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS",
                                 dict())
    
    try:
        parts = publish_parts(source=smart_str(value),
                              writer_name="html4css1",
                              settings_overrides=docutils_settings)
    except:
        return force_unicode(value)
    else:
        return mark_safe(force_unicode(parts["fragment"]))
saferst.is_safe = True
register.filter(saferst)


########NEW FILE########
__FILENAME__ = tests
import unittest
import StringIO
from djangopypi.views import parse_distutils_request, simple
from djangopypi.models import Project, Classifier
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpRequest

def create_post_data(action):
    data = {
            ":action": action,
            "metadata_version": "1.0",
            "name": "foo",
            "version": "0.1.0-pre2",
            "summary": "The quick brown fox jumps over the lazy dog.",
            "home_page": "http://example.com",
            "author": "Foo Bar Baz",
            "author_email": "foobarbaz@example.com",
            "license": "Apache",
            "keywords": "foo bar baz",
            "platform": "UNKNOWN",
            "classifiers": [
                "Development Status :: 3 - Alpha",
                "Environment :: Web Environment",
                "Framework :: Django",
                "Operating System :: OS Independent",
                "Intended Audience :: Developers",
                "Intended Audience :: System Administrators",
                "License :: OSI Approved :: BSD License",
                "Topic :: System :: Software Distribution",
                "Programming Language :: Python",
            ],
            "download_url": "",
            "provides": "",
            "requires": "",
            "obsoletes": "",
            "description": """
=========
FOOBARBAZ
=========

Introduction
------------
    ``foo`` :class:`bar`
    *baz*
    [foaoa]
            """,
    }
    return data

def create_request(data):
    boundary = '--------------GHSKFJDLGDS7543FJKLFHRE75642756743254'
    sep_boundary = '\n--' + boundary
    end_boundary = sep_boundary + '--'
    body = StringIO.StringIO()
    for key, value in data.items():
        # handle multiple entries for the same name
        if type(value) not in (type([]), type( () )):
            value = [value]
        for value in value:
            value = unicode(value).encode("utf-8")
            body.write(sep_boundary)
            body.write('\nContent-Disposition: form-data; name="%s"'%key)
            body.write("\n\n")
            body.write(value)
            if value and value[-1] == '\r':
                body.write('\n')  # write an extra newline (lurve Macs)
    body.write(end_boundary)
    body.write("\n")

    return body.getvalue()


class MockRequest(object):

    def __init__(self, raw_post_data):
        self.raw_post_data = raw_post_data
        self.META = {}


class TestParseWeirdPostData(unittest.TestCase):

    def test_weird_post_data(self):
        data = create_post_data("submit")
        raw_post_data = create_request(data)
        post, files = parse_distutils_request(MockRequest(raw_post_data))
        self.assertTrue(post)

        for key in post.keys():
            if isinstance(data[key], list):
                self.assertEquals(data[key], post.getlist(key))
            elif data[key] == "UNKNOWN":
                self.assertTrue(post[key] is None)
            else:
                self.assertEquals(post[key], data[key])



client = Client()

class TestSearch(unittest.TestCase):
    
    def setUp(self):
        dummy_user = User.objects.create(username='krill', password='12345',
                                 email='krill@opera.com')
        Project.objects.create(name='foo', license='Gnu',
                               summary="The quick brown fox jumps over the lazy dog.",
                               owner=dummy_user)        
        
    def test_search_for_package(self):        
        response = client.post(reverse('djangopypi-search'), {'search_term': 'foo'})
        self.assertTrue("The quick brown fox jumps over the lazy dog." in response.content)
        
class TestSimpleView(unittest.TestCase):
    
    def create_distutils_httprequest(self, user_data={}):
        self.post_data = create_post_data(action='user')        
        self.post_data.update(user_data)
        self.raw_post_data = create_request(self.post_data)
        request = HttpRequest()
        request.POST = self.post_data
        request.method = "POST"
        request.raw_post_data = self.raw_post_data
        return request      
        
    def test_user_registration(self):        
        request = self.create_distutils_httprequest({'name': 'peter_parker', 'email':'parker@dailybugle.com',
                                                    'password':'spiderman'})
        response = simple(request)
        self.assertEquals(200, response.status_code)
        
    def test_user_registration_with_wrong_data(self):
        request = self.create_distutils_httprequest({'name': 'peter_parker', 'email':'parker@dailybugle.com',
                                                     'password':'',})
        response = simple(request)
        self.assertEquals(400, response.status_code)
        
        
########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url, include

urlpatterns = patterns("djangopypi.views",
    # Simple PyPI
    url(r'^simple/$', "simple",
        name="djangopypi-simple"),

    url(r'^simple/(?P<dist_name>[\w\d_\.\-]+)/(?P<version>[\w\.\d\-_]+)/$',
        "show_version",
        name="djangopypi-show_version"),

    url(r'^simple/(?P<dist_name>[\w\d_\.\-]+)/$', "show_links",
        name="djangopypi-show_links"),

    url(r'^$', "simple", {'template_name': 'djangopypi/pypi.html'},
        name="djangopypi-pypi"),

    url(r'^(?P<dist_name>[\w\d_\.\-]+)/$', "show_links",
        {'template_name': 'djangopypi/pypi_show_links.html'},
        name="djangopypi-pypi_show_links"),
    
    url(r'^search','search',name='djangopypi-search')
)
########NEW FILE########
__FILENAME__ = utils
import sys
import traceback

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict


def transmute(f):
    if hasattr(f, "filename") and f.filename:
        v = SimpleUploadedFile(f.filename, f.value, f.type)
    else:
        v = f.value.decode("utf-8")
    return v


def decode_fs(fs):
    POST, FILES = {}, {}
    for k in fs.keys():
        v = transmute(fs[k])
        if isinstance(v, SimpleUploadedFile):
            FILES[k] = [v]
        else:
            # Distutils sends UNKNOWN for empty fields (e.g platform)
            # [russell.sim@gmail.com]
            if v == "UNKNOWN":
                v = None
            POST[k] = [v]
    return MultiValueDict(POST), MultiValueDict(FILES)


def debug(func):
    # @debug is handy when debugging distutils requests
    def _wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            traceback.print_exception(*sys.exc_info())
    return _wrapped
########NEW FILE########
__FILENAME__ = dists
import os

from django.conf import settings
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest)
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import login

from djangopypi.http import login_basic_auth, HttpResponseUnauthorized
from djangopypi.forms import ProjectForm, ReleaseForm
from djangopypi.models import Project, Release, Classifier, UPLOAD_TO

ALREADY_EXISTS_FMT = _(
    "A file named '%s' already exists for %s. Please create a new release.")


def submit_project_or_release(user, post_data, files):
    """Registers/updates a project or release"""
    try:
        project = Project.objects.get(name=post_data['name'])
        if project.owner != user:
            return HttpResponseForbidden(
                    "That project is owned by someone else!")
    except Project.DoesNotExist:
        project = None

    project_form = ProjectForm(post_data, instance=project)
    if project_form.is_valid():
        project = project_form.save(commit=False)
        project.owner = user
        project.save()
        for c in post_data.getlist('classifiers'):
            classifier, created = Classifier.objects.get_or_create(name=c)
            project.classifiers.add(classifier)
        if files:
            allow_overwrite = getattr(settings,
                "DJANGOPYPI_ALLOW_VERSION_OVERWRITE", False)
            try:
                release = Release.objects.get(version=post_data['version'],
                                              project=project,
                                              distribution=UPLOAD_TO + '/' +
                                              files['distribution']._name)
                if not allow_overwrite:
                    return HttpResponseForbidden(ALREADY_EXISTS_FMT % (
                                release.filename, release))
            except Release.DoesNotExist:
                release = None

            # If the old file already exists, django will append a _ after the
            # filename, however with .tar.gz files django does the "wrong"
            # thing and saves it as project-0.1.2.tar_.gz. So remove it before
            # django sees anything.
            release_form = ReleaseForm(post_data, files, instance=release)
            if release_form.is_valid():
                if release and os.path.exists(release.distribution.path):
                    os.remove(release.distribution.path)
                release = release_form.save(commit=False)
                release.project = project
                release.save()
            else:
                return HttpResponseBadRequest(
                        "ERRORS: %s" % release_form.errors)
    else:
        return HttpResponseBadRequest("ERRORS: %s" % project_form.errors)

    return HttpResponse()


def register_or_upload(request, post_data, files):
    user = login_basic_auth(request)
    if not user:
        return HttpResponseUnauthorized('pypi')

    login(request, user)
    if not request.user.is_authenticated():
        return HttpResponseForbidden(
                "Not logged in, or invalid username/password.")

    return submit_project_or_release(user, post_data, files)

########NEW FILE########
__FILENAME__ = search
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.db.models.query import Q

from djangopypi.models import Project


def _search_query(q):
    return Q(name__contains=q) | Q(summary__contains=q)


def search(request, template="djangopypi/search_results.html"):
    context = RequestContext(request, {"dists": None, "search_term": ""})

    if request.method == "POST":
        search_term = context["search_term"] = request.POST.get("search_term")
        if search_term:
            query = _search_query(search_term)
            context["dists"] = Project.objects.filter(query)

    if context["dists"] is None:
        context["dists"] = Project.objects.all()

    return render_to_response(template, context_instance=context)

########NEW FILE########
__FILENAME__ = users
from django.http import HttpResponse, HttpResponseBadRequest

from registration.forms import RegistrationForm
from registration.backends import get_backend

DEFAULT_BACKEND = "registration.backends.default.DefaultBackend"


def create_user(request, post_data, files, backend_name=DEFAULT_BACKEND):
    """Create new user from a distutil client request"""
    form = RegistrationForm({"username": post_data["name"],
                             "email": post_data["email"],
                             "password1": post_data["password"],
                             "password2": post_data["password"]})
    if not form.is_valid():
        # Dist Utils requires error msg in HTTP status: "HTTP/1.1 400 msg"
        # Which is HTTP/WSGI incompatible, so we're just returning a empty 400.
        return HttpResponseBadRequest()

    backend = get_backend(backend_name)
    if not backend.registration_allowed(request):
        return HttpResponseBadRequest()
    new_user = backend.register(request, **form.cleaned_data)
    return HttpResponse("OK\n", status=200, mimetype='text/plain')

########NEW FILE########
