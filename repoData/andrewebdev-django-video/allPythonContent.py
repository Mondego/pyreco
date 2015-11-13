__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'


# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args += ['-c', options.config_file]

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.append('buildout:accept-buildout-test-releases=true')
args.append('bootstrap')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

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
# Django settings for videodemo project.

import os
from os.path import dirname

PROJECT_DIR = dirname(__file__)
BUILDOUT_DIR = dirname(dirname(dirname(__file__)))

projectdir = lambda p: os.path.join(PROJECT_DIR, p)
buildoutdir = lambda p: os.path.join(BUILDOUT_DIR, p)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': projectdir('dev.db'),                      # Or path to database file if using sqlite3.
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
MEDIA_ROOT = projectdir('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = projectdir('static')

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
SECRET_KEY = '*#wwjo1sqy97iq%^-*q=lcd-hijx@bl&*t&cfg-!knrr5)gd9x'

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

ROOT_URLCONF = 'videodemo.urls'

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
    'django.contrib.admin',
    'django.contrib.admindocs',
    'videostream',
    'oembed',
)


FFMPEG_BINARY_PATH = buildoutdir('parts/ffmpeg/bin/ffmpeg')
FLVTOOL_PATH = buildoutdir('bin/flvtool2')

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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    (r'^', include('videostream.urls')),

    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-

from django.contrib import admin

from videostream.models import *
from videostream.utils import encode_video_set

## Admin Actions
def encode_videos(modeladmin, request, queryset):
    """ Encode all selected videos """
    encode_video_set(queryset)
encode_videos.short_description = "Encode selected videos into Flash flv videos"

def mark_for_encoding(modeladmin, request, queryset):
    """ Mark selected videos for encoding """
    queryset.update(encode=True)
mark_for_encoding.short_description = "Mark videos for encoding"

def unmark_for_encoding(modeladmin, request, queryset):
    """ Unmark selected videos for encoding """
    queryset.update(encode=False)
unmark_for_encoding.short_description = "Unmark videos for encoding"

def enable_video_comments(modeladmin, request, queryset):
    """ Enable Comments on selected videos """
    queryset.update(allow_comments=True)
enable_video_comments.short_description = "Enable comments on selected videos"

def disable_video_comments(modeladmin, request, queryset):
    """ Disable comments on selected Videos """
    queryset.update(allow_comments=False)
disable_video_comments.short_description = "Disable comments on selected videos"

def publish_videos(modeladmin, request, queryset):
    """ Mark selected videos as public """
    queryset.update(is_public=True)
    # Quickly call the save() method for every video so that the dates are updated
    for video in queryset:
        video.save()
publish_videos.short_description = "Publish selected videos"

def unpublish_videos(modeladmin, request, queryset):
    """ Unmark selected videos as public """
    queryset.update(is_public=False)
unpublish_videos.short_description = "Unpublish selected Videos"

## Inline Model Classes
class HTML5VideoInline(admin.TabularInline):
    model = HTML5Video


## ModelAdmin Classes
class VideoCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ['title', 'slug']


class VideoAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)} 
    date_hierarchy = 'publish_date'
    list_display = ['title', 'slug', 'publish_date', 'is_public',
        'allow_comments', 'author']
    list_filter = ['created_date', 'publish_date', 'modified_date',
        'is_public', 'allow_comments']
    search_fields = ['title', 'description', 'tags']
    fieldsets = (
        ('Video Details', {'fields': [
            'title', 'slug', 'description', 'tags', 'categories', 'is_public',
            'allow_comments', 'publish_date', 'author',
        ]}),
    )
    actions = [publish_videos, unpublish_videos,
               enable_video_comments, disable_video_comments]


class FlashVideoAdmin(VideoAdmin):
    list_display = VideoAdmin.list_display + ['encode']
    list_filter = VideoAdmin.list_filter + ['encode']
    fieldsets = VideoAdmin.fieldsets + (
        ('Video Source', {'fields': [
            'original_file',
            'flv_file',
            'thumbnail', 
            'encode'
        ]}),
    )
    actions = VideoAdmin.actions + [mark_for_encoding,
                                    unmark_for_encoding, encode_videos]


class EmbedVideoAdmin(VideoAdmin):
    list_display = VideoAdmin.list_display + ['video_url']
    fieldsets = VideoAdmin.fieldsets + (
        ('Video Source', {'fields': [
            'video_url',
            'video_code',
        ]}),
    )


class BasicVideoAdmin(VideoAdmin):
    inlines = [HTML5VideoInline]


admin.site.register(VideoCategory, VideoCategoryAdmin)
admin.site.register(FlashVideo, FlashVideoAdmin)
admin.site.register(EmbedVideo, EmbedVideoAdmin)
admin.site.register(BasicVideo, BasicVideoAdmin)

########NEW FILE########
__FILENAME__ = feeds
# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence

from django.contrib.syndication.feeds import Feed
from django.conf import settings
from videostream.models import VideoStream

class LatestStream(Feed):
    title = getattr(settings, 'VIDEOSTREAM_FEED_TITLE', 'Video Feeds')
    description = getattr(settings, 'VIDEOSTREAM_FEED_DESCRIPTION', 'Video Feeds')
    link = getattr(settings, 'VIDEOSTREAM_FEED_LINK', '')

    def items(self):
        return VideoStream.objects.all().filter(is_public=True)[:5]

########NEW FILE########
__FILENAME__ = encode
# -*- coding: utf-8 -*-

import commands
import os

from django.core.management.base import NoArgsCommand

from videostream.utils import encode_video_set


class Command(NoArgsCommand):
    
    def handle_noargs(self, **options):
        """ Encode all pending streams """
        encode_video_set()

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from datetime import datetime

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


# use Django-tagging for tags. If Django-tagging cannot be found, create our own
# I did not author this little snippet, I found it somewhere on the web,
# and cannot remember where exactly it was.
try:
    from tagging.fields import TagField
    tagfield_help_text = 'Separate tags with spaces, put quotes around multiple-word tags.'
except ImportError:
    class TagField(models.CharField):
        def __init__(self, **kwargs):
            default_kwargs = {'max_length': 255, 'blank': True}
            default_kwargs.update(kwargs)
            super(TagField, self).__init__(**default_kwargs)
        def get_internal_type(self):
            return 'CharField'
    tagfield_help_text = 'Django-tagging was not found, tags will be treated as plain text.'
# End tagging snippet


class VideoCategory(models.Model):
    """ A model to help categorize videos """
    title = models.CharField(max_length=255)
    slug = models.SlugField(
        unique=True,
        help_text="A url friendly slug for the category",
    )
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Video Categories"

    def __unicode__(self):
        return "%s" % self.title

    @models.permalink
    def get_absolute_url(self):
        return ('videostream_category_detail', [self.slug])


class Video(models.Model):
    """
    This is our Base Video Class, with fields that will be available
    to all other Video models.
    """
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True,
        help_text="A url friendly slug for the video clip.")
    description = models.TextField(null=True, blank=True)

    tags = TagField(help_text=tagfield_help_text)
    categories = models.ManyToManyField(VideoCategory)
    allow_comments = models.BooleanField(default=False)

    ## TODO:
    ## In future we may want to allow for more control over publication
    is_public = models.BooleanField(default=False)

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    publish_date = models.DateTimeField(null=True, blank=True)

    author = models.ForeignKey(User, null=True, blank=True)
    
    class Meta:
        ordering = ('-publish_date', '-created_date')
        get_latest_by = 'publish_date'

    def __unicode__(self):
        return "%s" % self.title

    @models.permalink
    def get_absolute_url(self):
        return ('videostream_video_detail', (), { 
            'year': self.publish_date.strftime("%Y"),
            'month': self.publish_date.strftime("%b"),
            'day': self.publish_date.strftime("%d"), 
            'slug': self.slug 
        })

    def save(self, *args, **kwargs):
        self.modified_date = datetime.now()
        if self.publish_date == None and self.is_public:
            self.publish_date = datetime.now()
        super(Video, self).save(*args, **kwargs)


class BasicVideo(Video):
    """
    This is our basic HTML5 Video type. BasicVideo can have more than
    one HTML5 Video as a 'video type'. This allows us to create different
    video formats, one for each type format.
    """
    pass


class HTML5Video(models.Model):
    OGG = 0
    WEBM = 1
    MP4 = 2
    FLASH = 3
    VIDEO_TYPE = (
        (OGG, 'video/ogg'),
        (WEBM, 'video/webm'),
        (MP4, 'video/mp4'),
        (FLASH, 'video/flv'),
    )

    video_type = models.IntegerField(
        choices=VIDEO_TYPE,
        default=WEBM,
        help_text="The Video type"
    )
    video_file = models.FileField(
        upload_to="videos/html5/",
        help_text="The file you wish to upload. Make sure that it's the correct format.",
    )

    # Allow for multiple video types for a single video
    basic_video = models.ForeignKey(BasicVideo)

    class Meta:
        verbose_name = "Html 5 Video"
        verbose_name_plural = "Html 5 Videos"


class EmbedVideo(Video):
    video_url = models.URLField(null=True, blank=True)
    video_code = models.TextField(
        null=True,
        blank=True,
        help_text="Use the video embed code instead of the url if your frontend does not support embedding with the URL only."
    )


class FlashVideo(Video):
    """
    This model is what was once called "VideoStream". Since we want to support
    videos from other sources as well, this model was renamed to FlashVideo.
    """
    original_file = models.FileField(
        upload_to="videos/flash/source/",
        null=True,
        blank=True,
        help_text="Make sure that the video you are uploading has a audo bitrate of at least 16. The encoding wont function on a lower audio bitrate."
    )

    flv_file = models.FileField(
        upload_to="videos/flash/flv/",
        null=True,
        blank=True,
        help_text="If you already have an encoded flash video, upload it here (no encoding needed)."
    )

    thumbnail = models.ImageField(
        blank=True,
        null=True, 
        upload_to="videos/flash/thumbnails/",
        help_text="If you uploaded a flv clip that was already encoded, you will need to upload a thumbnail as well. If you are planning use django-video to encode, you dont have to upload a thumbnail, as django-video will create it for you"
    )

    # This option allows us to specify whether we need to encode the clip
    encode = models.BooleanField(
        default=False,
        help_text="Encode or Re-Encode the clip. If you only wanted to change some information on the item, and do not want to encode the clip again, make sure this option is not selected."
    )

    def get_player_size(self):
        """ this method returns the styles for the player size """
        size = getattr(settings, 'VIDEOSTREAM_SIZE', '320x240').split('x')
        return "width: %spx; height: %spx;" % (size[0], size[1])

########NEW FILE########
__FILENAME__ = videostream_tags
from django import template
from django.contrib.contenttypes.models import ContentType

from videostream.models import BasicVideo, EmbedVideo, FlashVideo


register = template.Library()


@register.inclusion_tag('videostream/include/render_video.html')
def render_video(video_instance, width=320, height=240):
    """
    This is a intelligent inclusion tag that will try do determine what kind
    of video ``video_instance`` is, and then render the correct HTML for this
    video.

    ``width`` and ``height`` refers to the width and height of the video.

    Example Usage:
        {% render_video video 640 480 %}

    """
    try:
        if video_instance.basicvideo:
            video_type = 'basicvideo'
    except:
        pass

    try:
        if video_instance.embedvideo:
            video_type = 'embedvideo'
    except:
        pass

    try:
        if video_instance.flashvideo:
            video_type = 'flashvideo'
    except:
        pass

    return locals() 

########NEW FILE########
__FILENAME__ = tests
from datetime import datetime

from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from videostream.models import (VideoCategory, Video, BasicVideo, HTML5Video,
    EmbedVideo, FlashVideo)


## Models (including basic urls for permalink lookups)
class VideoCategoryTestCase(TestCase):

    fixtures = ['videostream_test_fixtures.json']
    urls = 'videostream.urls'

    def test_model_exists(self):
        cat = VideoCategory.objects.create(
            title='test', slug='test', description='test category')

    def test_unicode(self):
        self.assertEqual('Category 1',
            VideoCategory.objects.get(id=1).__unicode__())

    def test_verbose_name_plural(self):
        self.assertEqual('Video Categories',
            VideoCategory._meta.verbose_name_plural)

    def test_categories_exist(self):
        self.assertEqual(2, VideoCategory.objects.all().count())

    def test_absolute_url(self):
        self.assertEqual('/category/category-1/',
            VideoCategory.objects.get(id=1).get_absolute_url())


class VideoTestCase(TestCase):

    fixtures = ['videostream_test_fixtures.json']
    urls = 'videostream.urls'

    def test_model(self):
        v = Video.objects.create(
            title='test video 1',
            slug='test-video-1',
            description='test video description',
            tags='tag1 tag2',
            author=User.objects.get(id=1),  # Use our default user
        )

    def test_unicode(self):
        self.assertEqual('Video 1', Video.objects.get(id=1).__unicode__())

    def test_visible_video_has_publish_date(self):
        v = Video.objects.get(id=1)
        self.assertIsNone(v.publish_date)

        v.is_public = True
        v.save()
        self.assertIsNotNone(v.publish_date)

    def test_video_has_categories(self):
        v = Video.objects.get(id=1)
        self.assertEqual(2, v.categories.all().count())

    def test_absolute_url(self):
        v = Video.objects.get(id=1)
        v.is_public = True
        v.save()

        now = datetime.now()
        expected_url = '/%s/%s/%s/%s/' % (
            now.strftime('%Y'), now.strftime('%b'), now.strftime('%d'),
            'video-1')

        self.assertEqual(expected_url, v.get_absolute_url())

    def test_is_parent_class(self):
        # Basically since this is a parent class all other videos that
        # inherrits from this class can also be found through this model
        # Since we have these other videos in the fixtures,
        # this test should pass
        self.assertEqual(3, Video.objects.all().count())


class BasicVideoTestCase(TestCase):

    fixtures = ['videostream_test_fixtures.json']

    def test_model_exists(self):
        v = BasicVideo()  # No need to test other fields since it inherrits

    def test_has_html5videos(self):
        v = BasicVideo.objects.get(id=1)
        self.assertEqual(3, v.html5video_set.all().count())


class HTML5VideoTestCase(TestCase):

    fixtures = ['videostream_test_fixtures.json']

    def test_model(self):
        v = HTML5Video(video_type=1, video_file='test.ogg')

    def test_html5videos_exists(self):
        self.assertEqual(3, HTML5Video.objects.all().count())


class EmbedVideoTestCase(TestCase):

    fixtures = ['videostream_test_fixtures.json']

    def test_model(self):
        v = EmbedVideo.objects.create(
            video_url='http://test.example.com/video/',
            video_code='[video code]'
        )


class FlashVideoTestCase(TestCase):

    fixtures = ['videostream_test_fixtures.json']

    def test_model(self):
        v = FlashVideo(
            original_file='original.mp4',
            flv_file='video.flv',
            thumbnail='thumb.png',
            encode=False
        )

    def test_get_player_size(self):
        self.assertEqual('width: 320px; height: 240px;',
            FlashVideo.objects.get(id=1).get_player_size())


class VideoStreamViewsTestCase(TestCase):

    fixtures = ['videostream_test_fixtures.json']
    urls = 'videostream.urls'

    def setUp(self):
        now = datetime.now()
        self.day = now.strftime('%d')
        self.month = now.strftime('%b')
        self.year = now.strftime('%Y')

        for v in Video.objects.all():
            v.is_public = True
            v.save()

    def test_category_list_view(self):
        c = Client()
        response = c.get('/categories/')
        self.assertEqual(200, response.status_code)
        self.assertIn('object_list', response.context)
        self.assertEqual(2, response.context['object_list'].count())

    def test_category_detail_view(self):
        c = Client()
        response = c.get('/category/category-1/')
        self.assertEqual(200, response.status_code)
        self.assertIn('category', response.context)

    def test_archive_year_view(self):
        c = Client()
        response = c.get('/%s/' % self.year)
        self.assertEqual(200, response.status_code)
        self.assertIn('date_list', response.context)
        self.assertEqual(1, len(response.context['date_list']))

    def test_archive_month_view(self):
        c = Client()
        response = c.get('/%s/%s/' % (self.year, self.month))
        self.assertEqual(200, response.status_code)
        self.assertIn('object_list', response.context)
        self.assertEqual(3, response.context['object_list'].count())

    def test_archive_day_view(self):
        c = Client()
        response = c.get('/%s/%s/%s/' % (self.year, self.month, self.day))
        self.assertEqual(200, response.status_code)
        self.assertIn('object_list', response.context)
        self.assertEqual(3, response.context['object_list'].count())

    def test_video_detail_view(self):
        c = Client()
        response = c.get('/%s/%s/%s/%s/' % (
            self.year, self.month, self.day, 'video-1'))
        self.assertEqual(200, response.status_code)
        self.assertIn('video', response.context)
        self.assertEqual('Video 1', response.context['video'].title)


########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

from django.conf.urls import *
from django.views.generic import DetailView, ListView
from django.views.generic.dates import *

from videostream.models import VideoCategory, Video
#from videostream.feeds import LatestStream


urlpatterns = patterns('',

    url(r'^category/(?P<slug>[-\w]+)/$', DetailView.as_view(
            model=VideoCategory, context_object_name='category'
        ), name='videostream_category_detail'),

    url(r'^categories/$', ListView.as_view(
            model=VideoCategory,
        ), name='videostream_category_list'),


    ## Date Based Views
    url(r'^latest/$', ArchiveIndexView.as_view(
            queryset=Video.objects.filter(is_public=True),
            date_field='publish_date',
        ), name='videostream_video_archive'),

    url(r'^(?P<year>\d{4})/(?P<month>\w+)/(?P<day>\d{1,2})/(?P<slug>[-\w]+)/$', 
        DateDetailView.as_view(
            queryset=Video.objects.filter(is_public=True),
            date_field='publish_date',
        ),
        name='videostream_video_detail'),

    url(r'^(?P<year>\d{4})/(?P<month>\w+)/(?P<day>\d{1,2})/$',
        DayArchiveView.as_view(
            queryset=Video.objects.filter(is_public=True),
            date_field='publish_date',
        ), name='videostream_video_day'),

    url(r'^(?P<year>\d{4})/(?P<month>\w+)/$',
        MonthArchiveView.as_view(
            queryset=Video.objects.filter(is_public=True),
            date_field='publish_date',
        ), name='videostream_video_month'),

    url(r'^(?P<year>\d{4})/$', YearArchiveView.as_view(
            queryset=Video.objects.filter(is_public=True),
            date_field='publish_date',
        ), name='videostream_video_year'),

)

# feeds = {
#     'latest':  LatestStream,        
# }

# urlpatterns += patterns('django.contrib.syndication.views',
#     (r'^feeds/(?P<url>.*)/$', 'feed', {'feed_dict': feeds}),
# )

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import commands
import os

from django.conf import settings

from videostream.models import FlashVideo


# This allows the developer to override the binary path for ffmpeg
FFMPEG_BINARY_PATH = getattr(settings, 'FFMPEG_BINARY_PATH', 'ffmpeg')
FLVTOOL_PATH = getattr(settings, 'FLVTOOL_PATH', 'flvtool2')


def encode_video(flashvideo):
    """
    Encode a single Video where ``flashvideo`` is an instance of
    videostream.models.FlashVideo
    """
    MEDIA_ROOT = getattr(settings, 'MEDIA_ROOT')
    VIDEOSTREAM_SIZE = getattr(settings, 'VIDEOSTREAM_SIZE', '320x240')
    VIDEOSTREAM_THUMBNAIL_SIZE = getattr(settings,
        'VIDEOSTREAM_THUMBNAIL_SIZE', '320x240')

    flvfilename = "%s.flv" % flashvideo.slug
    infile = "%s/%s" % (MEDIA_ROOT, flashvideo.original_file)
    outfile = "%s/videos/flash/flv/%s" % (MEDIA_ROOT, flvfilename)
    thumbnailfilename = "%s/videos/flash/thumbnails/%s.png" % (
        MEDIA_ROOT, flashvideo.slug)

    # Final Results
    flvurl = "videos/flash/flv/%s" % flvfilename
    thumburl = "videos/flash/thumbnails/%s.png" % flashvideo.slug

    # Check if flv and thumbnail folder exists and create if not
    if not(os.access("%s/videos/flash/flv/" % MEDIA_ROOT, os.F_OK)):
        os.makedirs("%s/videos/flash/flv" % MEDIA_ROOT)

    if not(os.access("%s/videos/flash/thumbnails/" % MEDIA_ROOT, os.F_OK)):
        os.makedirs("%s/videos/flash/thumbnails" % MEDIA_ROOT)

    # ffmpeg command to create flv video
    ffmpeg = "%s -y -i %s -acodec libmp3lame -ar 22050 -ab 32000 -f flv -s %s %s" % (
        FFMPEG_BINARY_PATH, infile, VIDEOSTREAM_SIZE, outfile)

    # ffmpeg command to create the video thumbnail
    getThumb = "%s -y -i %s -vframes 1 -ss 00:00:02 -an -vcodec png -f rawvideo -s %s %s" % (
        FFMPEG_BINARY_PATH, infile, VIDEOSTREAM_THUMBNAIL_SIZE, thumbnailfilename)

    # flvtool command to get the metadata
    flvtool = "%s -U %s" % (FLVTOOL_PATH, outfile)

    # Lets do the conversion
    ffmpegresult = commands.getoutput(ffmpeg)
    print 80*"~"
    print ffmpegresult

    if os.access(outfile, os.F_OK): # outfile exists

        # There was a error cause the outfile size is zero
        if (os.stat(outfile).st_size==0): 
            # We remove the file so that it does not cause confusion
            os.remove(outfile)

        else:
            # there does not seem to be errors, follow the rest of the procedures
            flvtoolresult = commands.getoutput(flvtool)
            print flvtoolresult

            thumbresult = commands.getoutput(getThumb)
            print thumbresult

            flashvideo.encode = False
            flashvideo.flv_file = flvurl
            flashvideo.thumbnail = thumburl

    print 80*"~"
    flashvideo.save()


def encode_video_set(queryset=None):

    if not queryset:
        queryset = FlashVideo.objects.filter(encode=True)

    for flashvideo in queryset:
        encode_video(flashvideo)


########NEW FILE########
