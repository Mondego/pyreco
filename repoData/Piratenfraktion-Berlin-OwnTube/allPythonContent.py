__FILENAME__ = admin
from livestream.models import Stream
from django.contrib import admin

admin.site.register(Stream)

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from livestream.models import Stream

import datetime

class UpcomingEvents(Feed):
    ''' This sub class of Django's Feed class handles the feed URL from urls.py
    in the owntube directory, it gets all upcoming
    streaming events and returns the data as required
    for the django feed class
    TO DO: 
    Making it possible to change the title and so on in a better way,
    maybe in the admin app?
    '''
    title = "Die kommenden Streams"
    link = "/stream/"
    description = "Hier kommen die Streams an"
	
    def items(self):
        return Stream.objects.filter(published=True,endDate__gt=datetime.datetime.now).order_by('-startDate')

    def item_title(self, item):
        return str(item.startDate) + ' ' + item.title

    def item_description(self, item):
        return item.description
    	
    def item_pubdate(self, item):
    	return item.created

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Stream'
        db.create_table('livestream_stream', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
            ('startDate', self.gf('django.db.models.fields.DateTimeField')()),
            ('endDate', self.gf('django.db.models.fields.DateTimeField')()),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('rtmpLink', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('audioOnlyLink', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('iframe', self.gf('django.db.models.fields.TextField')()),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('livestream', ['Stream'])


    def backwards(self, orm):
        # Deleting model 'Stream'
        db.delete_table('livestream_stream')


    models = {
        'livestream.stream': {
            'Meta': {'object_name': 'Stream'},
            'audioOnlyLink': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'endDate': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iframe': ('django.db.models.fields.TextField', [], {}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rtmpLink': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'startDate': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['livestream']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.safestring import mark_safe 

from autoslug import AutoSlugField

# Create your models here.

class Stream(models.Model):
    ''' This is the model for each live stream event nothing really special
    except for the iframe field maybe. It contains the loaded iframe for 
    each stream event and is marked as safe. Maybe we change this or add
    support for streams directly loaded into Projekktor'''
    title = models.CharField("Stream-Titel",max_length=200)
    slug = AutoSlugField(populate_from='title',unique=True)
    startDate = models.DateTimeField("Start der Veranstaltung")
    endDate = models.DateTimeField("Ende der Veranstaltung")
    description = models.TextField("Beschreibung")
    link = models.URLField("Link",blank=True,verify_exists=False)
    rtmpLink = models.URLField("RTMP Link",blank=True,verify_exists=False)
    audioOnlyLink = models.URLField("Audio-only Link",blank=True,verify_exists=False)
    iframe = models.TextField("iFrame des Streams")
    published = models.BooleanField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return self.title
    def get_absolute_url(self):
        return "/stream/%s/" % self.slug
    def display_iFrameSafeField(self): 
        return mark_safe(self.iframe)
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
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django import forms
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse

from livestream.models import Stream

import datetime


def current(request):
    ''' This view gets all streams that are scheduled to be live right now
    if there are no streams it redirects to the liste view. The upcoming_streams_list
    is used to show upcoming events in a side bar (see the template)'''
    stream_list = Stream.objects.filter(published=True,startDate__lt=datetime.datetime.now, endDate__gt=datetime.datetime.now).order_by('-startDate')
    upcoming_streams_list = Stream.objects.filter(published=True,endDate__gt=datetime.datetime.now).order_by('-startDate')[:5]
    if not stream_list:
        return redirect(list)
    else:
        return render_to_response('livestream/current.html', {'stream_list': stream_list, 'upcoming_streams_list': upcoming_streams_list},
                            context_instance=RequestContext(request))


def list(request):
    ''' This view shows gets all upcoming streaming events
    and forwards them to our template '''
    stream_list = Stream.objects.filter(published=True,endDate__gt=datetime.datetime.now).order_by('-startDate')
    return render_to_response('livestream/list.html', {'stream_list': stream_list},
                            context_instance=RequestContext(request))

def detail(request, slug):
    ''' This view shows the detail of a stream, it is used to
    show the user more information on one event but not
    for showing the player'''
    stream = get_object_or_404(Stream, slug=slug)
    upcoming_streams_list = Stream.objects.filter(published=True,endDate__gt=datetime.datetime.now).order_by('-startDate')[:5]
    return render_to_response('livestream/detail.html', {'stream': stream, 'upcoming_streams_list': upcoming_streams_list},
                            context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

import site
import owntube.settings as settings

if settings.VIRTUALENV:
    site.addsitedir(settings.VIRTUALENV)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "owntube.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings.example
# Django settings for owntube project.

DEBUG = False
TEMPLATE_DEBUG = DEBUG

# If you use an virtualenv (you schould) enter it here
VIRTUALENV = "/opt/owntube/lib/python2-6/sites-packages"

FORCE_SCRIPT_NAME = ''

# The guys who will get an email if something is wrong
ADMINS = (
    ('Philip Brechler', 'pbrechler@piratenfraktion-berlin.de'),
)

# Your database settings, sqlite is good for development and testing, not for deployment
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'owntube.sql',                      # Or path to database file if using sqlite3.
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
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'de-de'

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
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = '/opt/owntube/owntube/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = 'https://owntube.piratenfraktion-berlin.de/media/'

# Where do you want your upload cache to live (there should be some space left)
FILE_UPLOAD_TEMP_DIR = "/mnt/iscsi0/upload/"
# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/opt/owntube/owntube/static_files/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '/opt/owntube/owntube/owntube/static/',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'ThisOneIsNotUniqeSoPleaseChange'

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

ROOT_URLCONF = 'owntube.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'owntube.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/opt/owntube/owntube/templates"
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
    'django.contrib.markup',
    'taggit',
    'videoportal',
    'livestream',
    'static_pages',
    'djangotasks',
    'south',
    'taggit_templatetags',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
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
__FILENAME__ = compress
#!/usr/bin/env python
import os
import optparse
import subprocess
import sys

here = os.path.dirname(__file__)

def main():
    usage = "usage: %prog [file1..fileN]"
    description = """With no file paths given this script will automatically
compress all jQuery-based files of the admin app. Requires the Google Closure
Compiler library and Java version 6 or later."""
    parser = optparse.OptionParser(usage, description=description)
    parser.add_option("-c", dest="compiler", default="~/bin/compiler.jar",
                      help="path to Closure Compiler jar file")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose")
    (options, args) = parser.parse_args()

    compiler = os.path.expanduser(options.compiler)
    if not os.path.exists(compiler):
        sys.exit("Google Closure compiler jar file %s not found. Please use the -c option to specify the path." % compiler)

    if not args:
        if options.verbose:
            sys.stdout.write("No filenames given; defaulting to admin scripts\n")
        args = [os.path.join(here, f) for f in [
            "actions.js", "collapse.js", "inlines.js", "prepopulate.js"]]

    for arg in args:
        if not arg.endswith(".js"):
            arg = arg + ".js"
        to_compress = os.path.expanduser(arg)
        if os.path.exists(to_compress):
            to_compress_min = "%s.min.js" % "".join(arg.rsplit(".js"))
            cmd = "java -jar %s --js %s --js_output_file %s" % (compiler, to_compress, to_compress_min)
            if options.verbose:
                sys.stdout.write("Running: %s\n" % cmd)
            subprocess.call(cmd.split())
        else:
            sys.stdout.write("File %s not found. Sure it exists?\n" % to_compress)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from videoportal.feeds import *
from livestream.feeds import UpcomingEvents
from django.conf import settings

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'videoportal.views.list'),
    url(r'^videos/(?P<slug>[-\w]+)/$', 'videoportal.views.detail'),
    url(r'^tags/(?P<tag>[\w|\W]+)/$', 'videoportal.views.tag'),
    url(r'^collection/(?P<slug>[-\w]+)/$', 'videoportal.views.collection'),
    url(r'^json_tags/(?P<tag>[\w|\W]+)/$', 'videoportal.views.tag_json'),
    url(r'^videos/channel/(?P<slug>[-\w]+)/$', 'videoportal.views.channel_list'),
    url(r'^videos/iframe/(?P<slug>[-\w]+)/$', 'videoportal.views.iframe'),
    url(r'^search/', 'videoportal.views.search'),
    url(r'^json_search/', 'videoportal.views.search_json'),
    url(r'^submit/', 'videoportal.views.submit'),
    url(r'^encodingdone/', 'videoportal.views.encodingdone'),
    url(r'^status/', 'videoportal.views.status'),
    url(r'^contact/', 'static_pages.views.contact'),
    url(r'^about/', 'static_pages.views.about'),
    url(r'^stream/$', 'livestream.views.current'),
    url(r'^stream/list/$', 'livestream.views.list'),
    url(r'^stream/(?P<slug>[-\w]+)/$', 'livestream.views.detail'),
    url(r'^login/', 'django.contrib.auth.views.login'),
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    url(r'^feeds/latest/mp4', LatestMP4Videos()),
    url(r'^feeds/latest/webm', LatestWEBMVideos()),
    url(r'^feeds/latest/mp3', LatestMP3Audio()),
    url(r'^feeds/latest/ogg', LatestOGGAudio()),
    url(r'^feeds/stream/upcoming', UpcomingEvents()),
    url(r'^feeds/latest/torrent', TorrentFeed()),
    url(r'^feeds/(?P<channel_slug>[-\w]+)/mp4/$', ChannelFeedMP4()),
    url(r'^feeds/(?P<channel_slug>[-\w]+)/webm/$', ChannelFeedWEBM()),
    url(r'^feeds/(?P<channel_slug>[-\w]+)/ogg/$', ChannelFeedOGG()),
    url(r'^feeds/(?P<channel_slug>[-\w]+)/mp3/$', ChannelFeedMP3()),
    url(r'^feeds/(?P<channel_slug>[-\w]+)/torrent/$', ChannelFeedTorrent()),
    url(r'^feeds/collection/(?P<collection_slug>[-\w]+)/mp4/$', CollectionFeedMP4()),
    url(r'^feeds/collection/(?P<collection_slug>[-\w]+)/webm/$', CollectionFeedWEBM()),
    url(r'^feeds/collection/(?P<collection_slug>[-\w]+)/ogg/$', CollectionFeedOGG()),
    url(r'^feeds/collection/(?P<collection_slug>[-\w]+)/mp3/$', CollectionFeedMP3()),
    url(r'^feeds/collection/(?P<collection_slug>[-\w]+)/torrent/$', CollectionFeedTorrent()),
    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for owntube project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "owntube.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

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
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django import forms
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse

# All this views are just showing static pages not really usefull

def contact(request):
    return render_to_response('static_pages/contact.html',context_instance=RequestContext(request))
    
def about(request):
    return render_to_response('static_pages/about.html',context_instance=RequestContext(request))
########NEW FILE########
__FILENAME__ = admin
from videoportal.models import Video
from videoportal.models import Comment
from videoportal.models import Channel
from videoportal.models import Hotfolder
from videoportal.models import Collection

from django.contrib import admin

def make_published(modeladmin, request, queryset):
    queryset.update(published=True)
make_published.short_description = "Markierte Videos veroeffentlichen"

def make_torrent_done(modeladmin, request, queryset):
    queryset.update(torrentDone=True)
make_torrent_done.short_description = "Markierte Videos also mit Torrent markieren"

class VideoAdmin (admin.ModelAdmin):
    list_display = ['title','published','encodingDone', 'channel' ,'date']
    ordering = ['-date','-created']
    actions = [make_published,make_torrent_done]
    list_filter = ('kind', 'published', 'channel')
    fieldsets = (
        (None, {
            'fields': ('title', 'date', 'description', 'channel', 'linkURL', 'tags','published')
        }),
        ('Erweiterte Optionen', {
            'classes': ('collapse',),
            'fields': ('kind','user','torrentURL','mp4URL','webmURL','mp3URL','oggURL','videoThumbURL','audioThumbURL','duration','autoPublish','encodingDone','torrentDone')
        }),
    )
admin.site.register(Video,VideoAdmin)

def make_moderated(modeladmin,request, queryset):
    queryset.update(moderated=True)
make_moderated.short_description = "Markierte Kommentare zulassen"

class CommentAdmin (admin.ModelAdmin):
    list_display = ['comment','video','created','name','ip','moderated']
    ordering = ['-created']
    actions = [make_moderated]

admin.site.register(Comment,CommentAdmin)

class ChannelAdmin (admin.ModelAdmin):
    list_display = ['name','description','featured']
    ordering = ['-created']

admin.site.register(Channel,ChannelAdmin)

class HotfolderAdmin (admin.ModelAdmin):
    list_display = ['folderName','activated','autoPublish','kind','channel']
    ordering = ['-created']

admin.site.register(Hotfolder,HotfolderAdmin)

class CollectionAdmin(admin.ModelAdmin):
    list_display = ['title','date','channel']
    ordering = ['-date','-created']

admin.site.register(Collection,CollectionAdmin)

########NEW FILE########
__FILENAME__ = appsettings


# Should we use transloadit? Otherwise we will try ffmpeg
USE_TRANLOADIT = False

# Our transloadit auth key and secret
TRANSLOAD_AUTH_KEY = 'f8773dab00b4418d87163172f486a881'
TRANSLOAD_AUTH_SECRET = 'ae4f43f2be75a67a00334b0d578fc4a0037ee95f'
TRANSLOAD_TEMPLATE_VIDEO_ID = 'dd8ba41a71424910b9f8191021cb753f'
TRANSLOAD_TEMPLATE_AUDIO_ID = '2e3fb41355d84acf8a08eff53c8fe74c'
TRANSLOAD_TEMPLATE_VIDEO_AUDIO_ID = '52d9861b7683484d9eb8af5208c020e0'

# The URL Transloadit should notify if it was done (please remember the trailing slash)
TRANSLOAD_NOTIFY_URL = 'http://owntube.piratenfraktion-berlin.de/encodingdone/'

TRANSLOAD_MP4_ENCODE = 'encode_iphone'
TRANSLOAD_WEBM_ENCODE = 'encode_webm'
TRANSLOAD_MP3_ENCODE = 'encode_mp3'
TRANSLOAD_OGG_ENCODE = 'encode_ogg'
TRANSLOAD_THUMB_ENCODE = 'create_thumb'

ENCODING_OUTPUT_DIR = '/mnt/iscsi0/media/encoded/'
# How can we reach this files (public access is needed)
ENCODING_VIDEO_BASE_URL = 'http://owntube.piratenfraktion-berlin.de/media/encoded/'

USE_BITTORRENT = True
BITTORRENT_TRACKER_ANNOUNCE_URL = 'udp://tracker.publicbt.com:80'
BITTORRENT_TRACKER_BACKUP = 'udp://tracker.openbittorrent.com:80,udp://tracker.ccc.de:80,udp://tracker.istole.it:80'
BITTORRENT_FILES_DIR = '/opt/owntube/owntube/media/torrents/'
BITTORRENT_FILES_BASE_URL = 'http://owntube.piratenfraktion-berlin.de/media/torrents/'

# Base-Dir vor Hotfolders
HOTFOLDER_BASE_DIR = '/mnt/iscsi0/videostore/robotron/'
HOTFOLDER_MOVE_TO_DIR = '/opt/owntube/owntube/media/raw/'

########NEW FILE########
__FILENAME__ = bencode
# Written by Petru Paler, Uoti Urpala, Ross Cohen and John Hoffman
# see LICENSE.txt for license information

from types import IntType, LongType, StringType, ListType, TupleType, DictType
try:
    from types import BooleanType
except ImportError:
    BooleanType = None
try:
    from types import UnicodeType
except ImportError:
    UnicodeType = None

def decode_int(x, f):
    f += 1
    newf = x.index('e', f)
    try:
        n = int(x[f:newf])
    except:
        n = long(x[f:newf])
    if x[f] == '-':
        if x[f + 1] == '0':
            raise ValueError
    elif x[f] == '0' and newf != f+1:
        raise ValueError
    return (n, newf+1)
  
def decode_string(x, f):
    colon = x.index(':', f)
    try:
        n = int(x[f:colon])
    except (OverflowError, ValueError):
        n = long(x[f:colon])
    if x[f] == '0' and colon != f+1:
        raise ValueError
    colon += 1
    return (x[colon:colon+n], colon+n)

def decode_unicode(x, f):
    s, f = decode_string(x, f+1)
    return (s.decode('UTF-8'), f)

def decode_list(x, f):
    r, f = [], f+1
    while x[f] != 'e':
        v, f = decode_func[x[f]](x, f)
        r.append(v)
    return (r, f + 1)

def decode_dict(x, f):
    r, f = {}, f+1
    lastkey = None
    while x[f] != 'e':
        k, f = decode_string(x, f)
        if lastkey >= k:
            raise ValueError
        lastkey = k
        r[k], f = decode_func[x[f]](x, f)
    return (r, f + 1)

decode_func = {}
decode_func['l'] = decode_list
decode_func['d'] = decode_dict
decode_func['i'] = decode_int
decode_func['0'] = decode_string
decode_func['1'] = decode_string
decode_func['2'] = decode_string
decode_func['3'] = decode_string
decode_func['4'] = decode_string
decode_func['5'] = decode_string
decode_func['6'] = decode_string
decode_func['7'] = decode_string
decode_func['8'] = decode_string
decode_func['9'] = decode_string
#decode_func['u'] = decode_unicode
  
def bdecode(x, sloppy = 0):
    try:
        r, l = decode_func[x[0]](x, 0)
#    except (IndexError, KeyError):
    except (IndexError, KeyError, ValueError):
        raise ValueError, "bad bencoded data"
    if not sloppy and l != len(x):
        raise ValueError, "bad bencoded data"
    return r

def test_bdecode():
    try:
        bdecode('0:0:')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('ie')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('i341foo382e')
        assert 0
    except ValueError:
        pass
    assert bdecode('i4e') == 4L
    assert bdecode('i0e') == 0L
    assert bdecode('i123456789e') == 123456789L
    assert bdecode('i-10e') == -10L
    try:
        bdecode('i-0e')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('i123')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('i6easd')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('35208734823ljdahflajhdf')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('2:abfdjslhfld')
        assert 0
    except ValueError:
        pass
    assert bdecode('0:') == ''
    assert bdecode('3:abc') == 'abc'
    assert bdecode('10:1234567890') == '1234567890'
    try:
        bdecode('02:xy')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('l')
        assert 0
    except ValueError:
        pass
    assert bdecode('le') == []
    try:
        bdecode('leanfdldjfh')
        assert 0
    except ValueError:
        pass
    assert bdecode('l0:0:0:e') == ['', '', '']
    try:
        bdecode('relwjhrlewjh')
        assert 0
    except ValueError:
        pass
    assert bdecode('li1ei2ei3ee') == [1, 2, 3]
    assert bdecode('l3:asd2:xye') == ['asd', 'xy']
    assert bdecode('ll5:Alice3:Bobeli2ei3eee') == [['Alice', 'Bob'], [2, 3]]
    try:
        bdecode('d')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('defoobar')
        assert 0
    except ValueError:
        pass
    assert bdecode('de') == {}
    assert bdecode('d3:agei25e4:eyes4:bluee') == {'age': 25, 'eyes': 'blue'}
    assert bdecode('d8:spam.mp3d6:author5:Alice6:lengthi100000eee') == {'spam.mp3': {'author': 'Alice', 'length': 100000}}
    try:
        bdecode('d3:fooe')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('di1e0:e')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('d1:b0:1:a0:e')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('d1:a0:1:a0:e')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('i03e')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('l01:ae')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('9999:x')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('l0:')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('d0:0:')
        assert 0
    except ValueError:
        pass
    try:
        bdecode('d0:')
        assert 0
    except ValueError:
        pass

bencached_marker = []

class Bencached:
    def __init__(self, s):
        self.marker = bencached_marker
        self.bencoded = s

BencachedType = type(Bencached('')) # insufficient, but good as a filter

def encode_bencached(x, r):
    assert x.marker == bencached_marker
    r.append(x.bencoded)

def encode_int(x, r):
    r.extend(('i', str(x), 'e'))

def encode_bool(x, r):
    encode_int(int(x), r)

def encode_string(x, r):    
    r.extend((str(len(x)), ':', x))

def encode_unicode(x, r):
    #r.append('u')
    encode_string(x.encode('UTF-8'), r)

def encode_list(x, r):
    r.append('l')
    for e in x:
        encode_func[type(e)](e, r)
    r.append('e')

def encode_dict(x, r):
    r.append('d')
    ilist = x.items()
    ilist.sort()
    for k, v in ilist:
        r.extend((str(len(k)), ':', k))
        encode_func[type(v)](v, r)
    r.append('e')

encode_func = {}
encode_func[BencachedType] = encode_bencached
encode_func[IntType] = encode_int
encode_func[LongType] = encode_int
encode_func[StringType] = encode_string
encode_func[ListType] = encode_list
encode_func[TupleType] = encode_list
encode_func[DictType] = encode_dict
if BooleanType:
    encode_func[BooleanType] = encode_bool
if UnicodeType:
    encode_func[UnicodeType] = encode_unicode
    
def bencode(x):
    r = []
    try:
        encode_func[type(x)](x, r)
    except:
        print "*** error *** could not encode type %s (value: %s)" % (type(x), x)
        assert 0
    return ''.join(r)

def test_bencode():
    assert bencode(4) == 'i4e'
    assert bencode(0) == 'i0e'
    assert bencode(-10) == 'i-10e'
    assert bencode(12345678901234567890L) == 'i12345678901234567890e'
    assert bencode('') == '0:'
    assert bencode('abc') == '3:abc'
    assert bencode('1234567890') == '10:1234567890'
    assert bencode([]) == 'le'
    assert bencode([1, 2, 3]) == 'li1ei2ei3ee'
    assert bencode([['Alice', 'Bob'], [2, 3]]) == 'll5:Alice3:Bobeli2ei3eee'
    assert bencode({}) == 'de'
    assert bencode({'age': 25, 'eyes': 'blue'}) == 'd3:agei25e4:eyes4:bluee'
    assert bencode({'spam.mp3': {'author': 'Alice', 'length': 100000}}) == 'd8:spam.mp3d6:author5:Alice6:lengthi100000eee'
    try:
        bencode({1: 'foo'})
        assert 0
    except AssertionError:
        pass

  
try:
    import psyco
    psyco.bind(bdecode)
    psyco.bind(bencode)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = bitfield
# Written by Bram Cohen, Uoti Urpala, and John Hoffman
# see LICENSE.txt for license information

try:
    True
except:
    True = 1
    False = 0
    bool = lambda x: not not x

try:
    sum([1])
    negsum = lambda a: len(a) - sum(a)
except:
    negsum = lambda a: reduce(lambda x, y: x + (not y), a, 0)
    
def _int_to_booleans(x):
    r = []
    for i in range(8):
        r.append(bool(x & 0x80))
        x <<= 1
    return tuple(r)

lookup_table = []
reverse_lookup_table = {}
for i in xrange(256):
    x = _int_to_booleans(i)
    lookup_table.append(x)
    reverse_lookup_table[x] = chr(i)


class Bitfield:
    def __init__(self, length = None, bitstring = None, copyfrom = None):
        if copyfrom is not None:
            self.length = copyfrom.length
            self.array = copyfrom.array[:]
            self.numfalse = copyfrom.numfalse
            return
        if length is None:
            raise ValueError, "length must be provided unless copying from another array"
        self.length = length
        if bitstring is not None:
            extra = len(bitstring) * 8 - length
            if extra < 0 or extra >= 8:
                raise ValueError
            t = lookup_table
            r = []
            for c in bitstring:
                r.extend(t[ord(c)])
            if extra > 0:
                if r[-extra:] != [0] * extra:
                    raise ValueError
                del r[-extra:]
            self.array = r
            self.numfalse = negsum(r)
        else:
            self.array = [False] * length
            self.numfalse = length

    def __setitem__(self, index, val):
        val = bool(val)
        self.numfalse += self.array[index]-val
        self.array[index] = val

    def __getitem__(self, index):
        return self.array[index]

    def __len__(self):
        return self.length

    def tostring(self):
        booleans = self.array
        t = reverse_lookup_table
        s = len(booleans) % 8
        r = [ t[tuple(booleans[x:x+8])] for x in xrange(0, len(booleans)-s, 8) ]
        if s:
            r += t[tuple(booleans[-s:] + ([0] * (8-s)))]
        return ''.join(r)

    def complete(self):
        return not self.numfalse


def test_bitfield():
    try:
        x = Bitfield(7, 'ab')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(7, 'ab')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(9, 'abc')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(0, 'a')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(1, '')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(7, '')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(8, '')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(9, 'a')
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(7, chr(1))
        assert False
    except ValueError:
        pass
    try:
        x = Bitfield(9, chr(0) + chr(0x40))
        assert False
    except ValueError:
        pass
    assert Bitfield(0, '').tostring() == ''
    assert Bitfield(1, chr(0x80)).tostring() == chr(0x80)
    assert Bitfield(7, chr(0x02)).tostring() == chr(0x02)
    assert Bitfield(8, chr(0xFF)).tostring() == chr(0xFF)
    assert Bitfield(9, chr(0) + chr(0x80)).tostring() == chr(0) + chr(0x80)
    x = Bitfield(1)
    assert x.numfalse == 1
    x[0] = 1
    assert x.numfalse == 0
    x[0] = 1
    assert x.numfalse == 0
    assert x.tostring() == chr(0x80)
    x = Bitfield(7)
    assert len(x) == 7
    x[6] = 1
    assert x.numfalse == 6
    assert x.tostring() == chr(0x02)
    x = Bitfield(8)
    x[7] = 1
    assert x.tostring() == chr(1)
    x = Bitfield(9)
    x[8] = 1
    assert x.numfalse == 8
    assert x.tostring() == chr(0) + chr(0x80)
    x = Bitfield(8, chr(0xC4))
    assert len(x) == 8
    assert x.numfalse == 5
    assert x.tostring() == chr(0xC4)

########NEW FILE########
__FILENAME__ = btformats
# Written by Bram Cohen
# see LICENSE.txt for license information

from types import StringType, LongType, IntType, ListType, DictType
import re

reg = re.compile(r'^[^/\\.~][^/\\]*$')

ints = (LongType, IntType)

def check_info(info):
    if type(info) != DictType:
        raise ValueError, 'bad metainfo - not a dictionary'
    pieces = info.get('pieces')
    if type(pieces) != StringType or len(pieces) % 20 != 0:
        raise ValueError, 'bad metainfo - bad pieces key'
    piecelength = info.get('piece length')
    if type(piecelength) not in ints or piecelength <= 0:
        raise ValueError, 'bad metainfo - illegal piece length'
    name = info.get('name')
    if type(name) != StringType:
        raise ValueError, 'bad metainfo - bad name'
    if not reg.match(name):
        raise ValueError, 'name %s disallowed for security reasons' % name
    if info.has_key('files') == info.has_key('length'):
        raise ValueError, 'single/multiple file mix'
    if info.has_key('length'):
        length = info.get('length')
        if type(length) not in ints or length < 0:
            raise ValueError, 'bad metainfo - bad length'
    else:
        files = info.get('files')
        if type(files) != ListType:
            raise ValueError
        for f in files:
            if type(f) != DictType:
                raise ValueError, 'bad metainfo - bad file value'
            length = f.get('length')
            if type(length) not in ints or length < 0:
                raise ValueError, 'bad metainfo - bad length'
            path = f.get('path')
            if type(path) != ListType or path == []:
                raise ValueError, 'bad metainfo - bad path'
            for p in path:
                if type(p) != StringType:
                    raise ValueError, 'bad metainfo - bad path dir'
                if not reg.match(p):
                    raise ValueError, 'path %s disallowed for security reasons' % p
        for i in xrange(len(files)):
            for j in xrange(i):
                if files[i]['path'] == files[j]['path']:
                    raise ValueError, 'bad metainfo - duplicate path'

def check_message(message):
    if type(message) != DictType:
        raise ValueError
    check_info(message.get('info'))
    if type(message.get('announce')) != StringType:
        raise ValueError

def check_peers(message):
    if type(message) != DictType:
        raise ValueError
    if message.has_key('failure reason'):
        if type(message['failure reason']) != StringType:
            raise ValueError
        return
    peers = message.get('peers')
    if type(peers) == ListType:
        for p in peers:
            if type(p) != DictType:
                raise ValueError
            if type(p.get('ip')) != StringType:
                raise ValueError
            port = p.get('port')
            if type(port) not in ints or p <= 0:
                raise ValueError
            if p.has_key('peer id'):
                id = p['peer id']
                if type(id) != StringType or len(id) != 20:
                    raise ValueError
    elif type(peers) != StringType or len(peers) % 6 != 0:
        raise ValueError
    interval = message.get('interval', 1)
    if type(interval) not in ints or interval <= 0:
        raise ValueError
    minint = message.get('min interval', 1)
    if type(minint) not in ints or minint <= 0:
        raise ValueError
    if type(message.get('tracker id', '')) != StringType:
        raise ValueError
    npeers = message.get('num peers', 0)
    if type(npeers) not in ints or npeers < 0:
        raise ValueError
    dpeers = message.get('done peers', 0)
    if type(dpeers) not in ints or dpeers < 0:
        raise ValueError
    last = message.get('last', 0)
    if type(last) not in ints or last < 0:
        raise ValueError

########NEW FILE########
__FILENAME__ = Choker
# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange, shuffle
from BitTornado.clock import clock
try:
    True
except:
    True = 1
    False = 0

class Choker:
    def __init__(self, config, schedule, picker, done = lambda: False):
        self.config = config
        self.round_robin_period = config['round_robin_period']
        self.schedule = schedule
        self.picker = picker
        self.connections = []
        self.last_preferred = 0
        self.last_round_robin = clock()
        self.done = done
        self.super_seed = False
        self.paused = False
        schedule(self._round_robin, 5)

    def set_round_robin_period(self, x):
        self.round_robin_period = x

    def _round_robin(self):
        self.schedule(self._round_robin, 5)
        if self.super_seed:
            cons = range(len(self.connections))
            to_close = []
            count = self.config['min_uploads']-self.last_preferred
            if count > 0:   # optimization
                shuffle(cons)
            for c in cons:
                i = self.picker.next_have(self.connections[c], count > 0)
                if i is None:
                    continue
                if i < 0:
                    to_close.append(self.connections[c])
                    continue
                self.connections[c].send_have(i)
                count -= 1
            for c in to_close:
                c.close()
        if self.last_round_robin + self.round_robin_period < clock():
            self.last_round_robin = clock()
            for i in xrange(1, len(self.connections)):
                c = self.connections[i]
                u = c.get_upload()
                if u.is_choked() and u.is_interested():
                    self.connections = self.connections[i:] + self.connections[:i]
                    break
        self._rechoke()

    def _rechoke(self):
        preferred = []
        maxuploads = self.config['max_uploads']
        if self.paused:
            for c in self.connections:
                c.get_upload().choke()
            return
        if maxuploads > 1:
            for c in self.connections:
                u = c.get_upload()
                if not u.is_interested():
                    continue
                if self.done():
                    r = u.get_rate()
                else:
                    d = c.get_download()
                    r = d.get_rate()
                    if r < 1000 or d.is_snubbed():
                        continue
                preferred.append((-r, c))
            self.last_preferred = len(preferred)
            preferred.sort()
            del preferred[maxuploads-1:]
            preferred = [x[1] for x in preferred]
        count = len(preferred)
        hit = False
        to_unchoke = []
        for c in self.connections:
            u = c.get_upload()
            if c in preferred:
                to_unchoke.append(u)
            else:
                if count < maxuploads or not hit:
                    to_unchoke.append(u)
                    if u.is_interested():
                        count += 1
                        hit = True
                else:
                    u.choke()
        for u in to_unchoke:
            u.unchoke()

    def connection_made(self, connection, p = None):
        if p is None:
            p = randrange(-2, len(self.connections) + 1)
        self.connections.insert(max(p, 0), connection)
        self._rechoke()

    def connection_lost(self, connection):
        self.connections.remove(connection)
        self.picker.lost_peer(connection)
        if connection.get_upload().is_interested() and not connection.get_upload().is_choked():
            self._rechoke()

    def interested(self, connection):
        if not connection.get_upload().is_choked():
            self._rechoke()

    def not_interested(self, connection):
        if not connection.get_upload().is_choked():
            self._rechoke()

    def set_super_seed(self):
        while self.connections:             # close all connections
            self.connections[0].close()
        self.picker.set_superseed()
        self.super_seed = True

    def pause(self, flag):
        self.paused = flag
        self._rechoke()

########NEW FILE########
__FILENAME__ = Connecter
# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.bitfield import Bitfield
from BitTornado.clock import clock
from binascii import b2a_hex

try:
    True
except:
    True = 1
    False = 0

DEBUG = False

def toint(s):
    return long(b2a_hex(s), 16)

def tobinary(i):
    return (chr(i >> 24) + chr((i >> 16) & 0xFF) + 
        chr((i >> 8) & 0xFF) + chr(i & 0xFF))

CHOKE = chr(0)
UNCHOKE = chr(1)
INTERESTED = chr(2)
NOT_INTERESTED = chr(3)
# index
HAVE = chr(4)
# index, bitfield
BITFIELD = chr(5)
# index, begin, length
REQUEST = chr(6)
# index, begin, piece
PIECE = chr(7)
# index, begin, piece
CANCEL = chr(8)

class Connection:
    def __init__(self, connection, connecter):
        self.connection = connection
        self.connecter = connecter
        self.got_anything = False
        self.next_upload = None
        self.outqueue = []
        self.partial_message = None
        self.download = None
        self.upload = None
        self.send_choke_queued = False
        self.just_unchoked = None

    def get_ip(self, real=False):
        return self.connection.get_ip(real)

    def get_id(self):
        return self.connection.get_id()

    def get_readable_id(self):
        return self.connection.get_readable_id()

    def close(self):
        if DEBUG:
            print 'connection closed'
        self.connection.close()

    def is_locally_initiated(self):
        return self.connection.is_locally_initiated()

    def send_interested(self):
        self._send_message(INTERESTED)

    def send_not_interested(self):
        self._send_message(NOT_INTERESTED)

    def send_choke(self):
        if self.partial_message:
            self.send_choke_queued = True
        else:
            self._send_message(CHOKE)
            self.upload.choke_sent()
            self.just_unchoked = 0

    def send_unchoke(self):
        if self.send_choke_queued:
            self.send_choke_queued = False
            if DEBUG:
                print 'CHOKE SUPPRESSED'
        else:
            self._send_message(UNCHOKE)
            if (self.partial_message or self.just_unchoked is None
                or not self.upload.interested or self.download.active_requests):
                self.just_unchoked = 0
            else:
                self.just_unchoked = clock()

    def send_request(self, index, begin, length):
        self._send_message(REQUEST + tobinary(index) + 
            tobinary(begin) + tobinary(length))
        if DEBUG:
            print 'sent request: '+str(index)+': '+str(begin)+'-'+str(begin+length)

    def send_cancel(self, index, begin, length):
        self._send_message(CANCEL + tobinary(index) + 
            tobinary(begin) + tobinary(length))
        if DEBUG:
            print 'sent cancel: '+str(index)+': '+str(begin)+'-'+str(begin+length)

    def send_bitfield(self, bitfield):
        self._send_message(BITFIELD + bitfield)

    def send_have(self, index):
        self._send_message(HAVE + tobinary(index))

    def send_keepalive(self):
        self._send_message('')

    def _send_message(self, s):
        s = tobinary(len(s))+s
        if self.partial_message:
            self.outqueue.append(s)
        else:
            self.connection.send_message_raw(s)

    def send_partial(self, bytes):
        if self.connection.closed:
            return 0
        if self.partial_message is None:
            s = self.upload.get_upload_chunk()
            if s is None:
                return 0
            index, begin, piece = s
            self.partial_message = ''.join((
                            tobinary(len(piece) + 9), PIECE, 
                            tobinary(index), tobinary(begin), piece.tostring()))
            if DEBUG:
                print 'sending chunk: '+str(index)+': '+str(begin)+'-'+str(begin+len(piece))

        if bytes < len(self.partial_message):
            self.connection.send_message_raw(self.partial_message[:bytes])
            self.partial_message = self.partial_message[bytes:]
            return bytes

        q = [self.partial_message]
        self.partial_message = None
        if self.send_choke_queued:
            self.send_choke_queued = False
            self.outqueue.append(tobinary(1)+CHOKE)
            self.upload.choke_sent()
            self.just_unchoked = 0
        q.extend(self.outqueue)
        self.outqueue = []
        q = ''.join(q)
        self.connection.send_message_raw(q)
        return len(q)

    def get_upload(self):
        return self.upload

    def get_download(self):
        return self.download

    def set_download(self, download):
        self.download = download

    def backlogged(self):
        return not self.connection.is_flushed()

    def got_request(self, i, p, l):
        self.upload.got_request(i, p, l)
        if self.just_unchoked:
            self.connecter.ratelimiter.ping(clock() - self.just_unchoked)
            self.just_unchoked = 0
    



class Connecter:
    def __init__(self, make_upload, downloader, choker, numpieces, 
            totalup, config, ratelimiter, sched = None):
        self.downloader = downloader
        self.make_upload = make_upload
        self.choker = choker
        self.numpieces = numpieces
        self.config = config
        self.ratelimiter = ratelimiter
        self.rate_capped = False
        self.sched = sched
        self.totalup = totalup
        self.rate_capped = False
        self.connections = {}
        self.external_connection_made = 0

    def how_many_connections(self):
        return len(self.connections)

    def connection_made(self, connection):
        c = Connection(connection, self)
        self.connections[connection] = c
        c.upload = self.make_upload(c, self.ratelimiter, self.totalup)
        c.download = self.downloader.make_download(c)
        self.choker.connection_made(c)
        return c

    def connection_lost(self, connection):
        c = self.connections[connection]
        del self.connections[connection]
        if c.download:
            c.download.disconnected()
        self.choker.connection_lost(c)

    def connection_flushed(self, connection):
        conn = self.connections[connection]
        if conn.next_upload is None and (conn.partial_message is not None
               or conn.upload.buffer):
            self.ratelimiter.queue(conn)
            
    def got_piece(self, i):
        for co in self.connections.values():
            co.send_have(i)

    def got_message(self, connection, message):
        c = self.connections[connection]
        t = message[0]
        if t == BITFIELD and c.got_anything:
            connection.close()
            return
        c.got_anything = True
        if (t in [CHOKE, UNCHOKE, INTERESTED, NOT_INTERESTED] and 
                len(message) != 1):
            connection.close()
            return
        if t == CHOKE:
            c.download.got_choke()
        elif t == UNCHOKE:
            c.download.got_unchoke()
        elif t == INTERESTED:
            c.upload.got_interested()
        elif t == NOT_INTERESTED:
            c.upload.got_not_interested()
        elif t == HAVE:
            if len(message) != 5:
                connection.close()
                return
            i = toint(message[1:])
            if i >= self.numpieces:
                connection.close()
                return
            c.download.got_have(i)
        elif t == BITFIELD:
            try:
                b = Bitfield(self.numpieces, message[1:])
            except ValueError:
                connection.close()
                return
            c.download.got_have_bitfield(b)
        elif t == REQUEST:
            if len(message) != 13:
                connection.close()
                return
            i = toint(message[1:5])
            if i >= self.numpieces:
                connection.close()
                return
            c.got_request(i, toint(message[5:9]), 
                toint(message[9:]))
        elif t == CANCEL:
            if len(message) != 13:
                connection.close()
                return
            i = toint(message[1:5])
            if i >= self.numpieces:
                connection.close()
                return
            c.upload.got_cancel(i, toint(message[5:9]), 
                toint(message[9:]))
        elif t == PIECE:
            if len(message) <= 9:
                connection.close()
                return
            i = toint(message[1:5])
            if i >= self.numpieces:
                connection.close()
                return
            if c.download.got_piece(i, toint(message[5:9]), message[9:]):
                self.got_piece(i)
        else:
            connection.close()

########NEW FILE########
__FILENAME__ = Downloader
# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.CurrentRateMeasure import Measure
from BitTornado.bitfield import Bitfield
from random import shuffle
from BitTornado.clock import clock
try:
    True
except:
    True = 1
    False = 0

EXPIRE_TIME = 60 * 60

class PerIPStats: 	 
    def __init__(self, ip):
        self.numgood = 0
        self.bad = {}
        self.numconnections = 0
        self.lastdownload = None
        self.peerid = None

class BadDataGuard:
    def __init__(self, download):
        self.download = download
        self.ip = download.ip
        self.downloader = download.downloader
        self.stats = self.downloader.perip[self.ip]
        self.lastindex = None

    def failed(self, index, bump = False):
        self.stats.bad.setdefault(index, 0)
        self.downloader.gotbaddata[self.ip] = 1
        self.stats.bad[index] += 1
        if len(self.stats.bad) > 1:
            if self.download is not None:
                self.downloader.try_kick(self.download)
            elif self.stats.numconnections == 1 and self.stats.lastdownload is not None:
                self.downloader.try_kick(self.stats.lastdownload)
        if len(self.stats.bad) >= 3 and len(self.stats.bad) > int(self.stats.numgood/30):
            self.downloader.try_ban(self.ip)
        elif bump:
            self.downloader.picker.bump(index)

    def good(self, index):
        # lastindex is a hack to only increase numgood by one for each good
        # piece, however many chunks come from the connection(s) from this IP
        if index != self.lastindex:
            self.stats.numgood += 1
            self.lastindex = index

class SingleDownload:
    def __init__(self, downloader, connection):
        self.downloader = downloader
        self.connection = connection
        self.choked = True
        self.interested = False
        self.active_requests = []
        self.measure = Measure(downloader.max_rate_period)
        self.peermeasure = Measure(downloader.max_rate_period)
        self.have = Bitfield(downloader.numpieces)
        self.last = -1000
        self.last2 = -1000
        self.example_interest = None
        self.backlog = 2
        self.ip = connection.get_ip()
        self.guard = BadDataGuard(self)

    def _backlog(self, just_unchoked):
        self.backlog = min(
            2+int(4*self.measure.get_rate()/self.downloader.chunksize),
            (2*just_unchoked)+self.downloader.queue_limit() )
        if self.backlog > 50:
            self.backlog = max(50, self.backlog * 0.075)
        return self.backlog
    
    def disconnected(self):
        self.downloader.lost_peer(self)
        if self.have.complete():
            self.downloader.picker.lost_seed()
        else:
            for i in xrange(len(self.have)):
                if self.have[i]:
                    self.downloader.picker.lost_have(i)
        if self.have.complete() and self.downloader.storage.is_endgame():
            self.downloader.add_disconnected_seed(self.connection.get_readable_id())
        self._letgo()
        self.guard.download = None

    def _letgo(self):
        if self.downloader.queued_out.has_key(self):
            del self.downloader.queued_out[self]
        if not self.active_requests:
            return
        if self.downloader.endgamemode:
            self.active_requests = []
            return
        lost = {}
        for index, begin, length in self.active_requests:
            self.downloader.storage.request_lost(index, begin, length)
            lost[index] = 1
        lost = lost.keys()
        self.active_requests = []
        if self.downloader.paused:
            return
        ds = [d for d in self.downloader.downloads if not d.choked]
        shuffle(ds)
        for d in ds:
            d._request_more()
        for d in self.downloader.downloads:
            if d.choked and not d.interested:
                for l in lost:
                    if d.have[l] and self.downloader.storage.do_I_have_requests(l):
                        d.send_interested()
                        break

    def got_choke(self):
        if not self.choked:
            self.choked = True
            self._letgo()

    def got_unchoke(self):
        if self.choked:
            self.choked = False
            if self.interested:
                self._request_more(new_unchoke = True)
            self.last2 = clock()

    def is_choked(self):
        return self.choked

    def is_interested(self):
        return self.interested

    def send_interested(self):
        if not self.interested:
            self.interested = True
            self.connection.send_interested()

    def send_not_interested(self):
        if self.interested:
            self.interested = False
            self.connection.send_not_interested()

    def got_piece(self, index, begin, piece):
        length = len(piece)
        try:
            self.active_requests.remove((index, begin, length))
        except ValueError:
            self.downloader.discarded += length
            return False
        if self.downloader.endgamemode:
            self.downloader.all_requests.remove((index, begin, length))
        self.last = clock()
        self.last2 = clock()
        self.measure.update_rate(length)
        self.downloader.measurefunc(length)
        if not self.downloader.storage.piece_came_in(index, begin, piece, self.guard):
            self.downloader.piece_flunked(index)
            return False
        if self.downloader.storage.do_I_have(index):
            self.downloader.picker.complete(index)
        if self.downloader.endgamemode:
            for d in self.downloader.downloads:
                if d is not self:
                    if d.interested:
                        if d.choked:
                            assert not d.active_requests
                            d.fix_download_endgame()
                        else:
                            try:
                                d.active_requests.remove((index, begin, length))
                            except ValueError:
                                continue
                            d.connection.send_cancel(index, begin, length)
                            d.fix_download_endgame()
                    else:
                        assert not d.active_requests
        self._request_more()
        self.downloader.check_complete(index)
        return self.downloader.storage.do_I_have(index)

    def _request_more(self, new_unchoke = False):
        assert not self.choked
        if self.downloader.endgamemode:
            self.fix_download_endgame(new_unchoke)
            return
        if self.downloader.paused:
            return
        if len(self.active_requests) >= self._backlog(new_unchoke):
            if not (self.active_requests or self.backlog):
                self.downloader.queued_out[self] = 1
            return
        lost_interests = []
        while len(self.active_requests) < self.backlog:
            interest = self.downloader.picker.next(self.have,
                               self.downloader.storage.do_I_have_requests,
                               self.downloader.too_many_partials())
            if interest is None:
                break
            self.example_interest = interest
            self.send_interested()
            loop = True
            while len(self.active_requests) < self.backlog and loop:
                begin, length = self.downloader.storage.new_request(interest)
                self.downloader.picker.requested(interest)
                self.active_requests.append((interest, begin, length))
                self.connection.send_request(interest, begin, length)
                self.downloader.chunk_requested(length)
                if not self.downloader.storage.do_I_have_requests(interest):
                    loop = False
                    lost_interests.append(interest)
        if not self.active_requests:
            self.send_not_interested()
        if lost_interests:
            for d in self.downloader.downloads:
                if d.active_requests or not d.interested:
                    continue
                if d.example_interest is not None and self.downloader.storage.do_I_have_requests(d.example_interest):
                    continue
                for lost in lost_interests:
                    if d.have[lost]:
                        break
                else:
                    continue
                interest = self.downloader.picker.next(d.have,
                                   self.downloader.storage.do_I_have_requests,
                                   self.downloader.too_many_partials())
                if interest is None:
                    d.send_not_interested()
                else:
                    d.example_interest = interest
        if self.downloader.storage.is_endgame():
            self.downloader.start_endgame()


    def fix_download_endgame(self, new_unchoke = False):
        if self.downloader.paused:
            return
        if len(self.active_requests) >= self._backlog(new_unchoke):
            if not (self.active_requests or self.backlog) and not self.choked:
                self.downloader.queued_out[self] = 1
            return
        want = [a for a in self.downloader.all_requests if self.have[a[0]] and a not in self.active_requests]
        if not (self.active_requests or want):
            self.send_not_interested()
            return
        if want:
            self.send_interested()
        if self.choked:
            return
        shuffle(want)
        del want[self.backlog - len(self.active_requests):]
        self.active_requests.extend(want)
        for piece, begin, length in want:
            self.connection.send_request(piece, begin, length)
            self.downloader.chunk_requested(length)

    def got_have(self, index):
        if index == self.downloader.numpieces-1:
            self.downloader.totalmeasure.update_rate(self.downloader.storage.total_length-(self.downloader.numpieces-1)*self.downloader.storage.piece_length)
            self.peermeasure.update_rate(self.downloader.storage.total_length-(self.downloader.numpieces-1)*self.downloader.storage.piece_length)
        else:
            self.downloader.totalmeasure.update_rate(self.downloader.storage.piece_length)
            self.peermeasure.update_rate(self.downloader.storage.piece_length)
        if self.have[index]:
            return
        self.have[index] = True
        self.downloader.picker.got_have(index)
        if self.have.complete():
            self.downloader.picker.became_seed()
            if self.downloader.picker.am_I_complete():
                self.downloader.add_disconnected_seed(self.connection.get_readable_id())
                self.connection.close()
                return
        if self.downloader.endgamemode:
            self.fix_download_endgame()
        elif ( not self.downloader.paused
               and not self.downloader.picker.is_blocked(index)
               and self.downloader.storage.do_I_have_requests(index) ):
            if not self.choked:
                self._request_more()
            else:
                self.send_interested()

    def _check_interests(self):
        if self.interested or self.downloader.paused:
            return
        for i in xrange(len(self.have)):
            if ( self.have[i] and not self.downloader.picker.is_blocked(i)
                 and ( self.downloader.endgamemode
                       or self.downloader.storage.do_I_have_requests(i) ) ):
                self.send_interested()
                return

    def got_have_bitfield(self, have):
        if self.downloader.picker.am_I_complete() and have.complete():
            if self.downloader.super_seeding:
                self.connection.send_bitfield(have.tostring()) # be nice, show you're a seed too
            self.connection.close()
            self.downloader.add_disconnected_seed(self.connection.get_readable_id())
            return
        self.have = have
        if have.complete():
            self.downloader.picker.got_seed()
        else:
            for i in xrange(len(have)):
                if have[i]:
                    self.downloader.picker.got_have(i)
        if self.downloader.endgamemode and not self.downloader.paused:
            for piece, begin, length in self.downloader.all_requests:
                if self.have[piece]:
                    self.send_interested()
                    break
            return
        self._check_interests()

    def get_rate(self):
        return self.measure.get_rate()

    def is_snubbed(self):
        if not self.choked and clock() - self.last2 > self.downloader.snub_time:
            for index, begin, length in self.active_requests:
                self.connection.send_cancel(index, begin, length)
            self.got_choke()    # treat it just like a choke
        return clock() - self.last > self.downloader.snub_time


class Downloader:
    def __init__(self, storage, picker, backlog, max_rate_period,
                 numpieces, chunksize, measurefunc, snub_time,
                 kickbans_ok, kickfunc, banfunc):
        self.storage = storage
        self.picker = picker
        self.backlog = backlog
        self.max_rate_period = max_rate_period
        self.measurefunc = measurefunc
        self.totalmeasure = Measure(max_rate_period*storage.piece_length/storage.request_size)
        self.numpieces = numpieces
        self.chunksize = chunksize
        self.snub_time = snub_time
        self.kickfunc = kickfunc
        self.banfunc = banfunc
        self.disconnectedseeds = {}
        self.downloads = []
        self.perip = {}
        self.gotbaddata = {}
        self.kicked = {}
        self.banned = {}
        self.kickbans_ok = kickbans_ok
        self.kickbans_halted = False
        self.super_seeding = False
        self.endgamemode = False
        self.endgame_queued_pieces = []
        self.all_requests = []
        self.discarded = 0L
#        self.download_rate = 25000  # 25K/s test rate
        self.download_rate = 0
        self.bytes_requested = 0
        self.last_time = clock()
        self.queued_out = {}
        self.requeueing = False
        self.paused = False

    def set_download_rate(self, rate):
        self.download_rate = rate * 1000
        self.bytes_requested = 0

    def queue_limit(self):
        if not self.download_rate:
            return 10e10    # that's a big queue!
        t = clock()
        self.bytes_requested -= (t - self.last_time) * self.download_rate
        self.last_time = t
        if not self.requeueing and self.queued_out and self.bytes_requested < 0:
            self.requeueing = True
            q = self.queued_out.keys()
            shuffle(q)
            self.queued_out = {}
            for d in q:
                d._request_more()
            self.requeueing = False
        if -self.bytes_requested > 5*self.download_rate:
            self.bytes_requested = -5*self.download_rate
        return max(int(-self.bytes_requested/self.chunksize), 0)

    def chunk_requested(self, size):
        self.bytes_requested += size

    external_data_received = chunk_requested

    def make_download(self, connection):
        ip = connection.get_ip()
        if self.perip.has_key(ip):
            perip = self.perip[ip]
        else:
            perip = self.perip.setdefault(ip, PerIPStats(ip))
        perip.peerid = connection.get_readable_id()
        perip.numconnections += 1
        d = SingleDownload(self, connection)
        perip.lastdownload = d
        self.downloads.append(d)
        return d

    def piece_flunked(self, index):
        if self.paused:
            return
        if self.endgamemode:
            if self.downloads:
                while self.storage.do_I_have_requests(index):
                    nb, nl = self.storage.new_request(index)
                    self.all_requests.append((index, nb, nl))
                for d in self.downloads:
                    d.fix_download_endgame()
                return
            self._reset_endgame()
            return
        ds = [d for d in self.downloads if not d.choked]
        shuffle(ds)
        for d in ds:
            d._request_more()
        ds = [d for d in self.downloads if not d.interested and d.have[index]]
        for d in ds:
            d.example_interest = index
            d.send_interested()

    def has_downloaders(self):
        return len(self.downloads)

    def lost_peer(self, download):
        ip = download.ip
        self.perip[ip].numconnections -= 1
        if self.perip[ip].lastdownload == download:
            self.perip[ip].lastdownload = None
        self.downloads.remove(download)
        if self.endgamemode and not self.downloads: # all peers gone
            self._reset_endgame()

    def _reset_endgame(self):            
        self.storage.reset_endgame(self.all_requests)
        self.endgamemode = False
        self.all_requests = []
        self.endgame_queued_pieces = []


    def add_disconnected_seed(self, id):
#        if not self.disconnectedseeds.has_key(id):
#            self.picker.seed_seen_recently()
        self.disconnectedseeds[id]=clock()

#	def expire_disconnected_seeds(self):

    def num_disconnected_seeds(self):
        # first expire old ones
        expired = []
        for id, t in self.disconnectedseeds.items():
            if clock() - t > EXPIRE_TIME:     #Expire old seeds after so long
                expired.append(id)
        for id in expired:
#            self.picker.seed_disappeared()
            del self.disconnectedseeds[id]
        return len(self.disconnectedseeds)
        # if this isn't called by a stats-gathering function
        # it should be scheduled to run every minute or two.

    def _check_kicks_ok(self):
        if len(self.gotbaddata) > 10:
            self.kickbans_ok = False
            self.kickbans_halted = True
        return self.kickbans_ok and len(self.downloads) > 2

    def try_kick(self, download):
        if self._check_kicks_ok():
            download.guard.download = None
            ip = download.ip
            id = download.connection.get_readable_id()
            self.kicked[ip] = id
            self.perip[ip].peerid = id
            self.kickfunc(download.connection)
        
    def try_ban(self, ip):
        if self._check_kicks_ok():
            self.banfunc(ip)
            self.banned[ip] = self.perip[ip].peerid
            if self.kicked.has_key(ip):
                del self.kicked[ip]

    def set_super_seed(self):
        self.super_seeding = True

    def check_complete(self, index):
        if self.endgamemode and not self.all_requests:
            self.endgamemode = False
        if self.endgame_queued_pieces and not self.endgamemode:
            self.requeue_piece_download()
        if self.picker.am_I_complete():
            assert not self.all_requests
            assert not self.endgamemode
            for d in [i for i in self.downloads if i.have.complete()]:
                d.connection.send_have(index)   # be nice, tell the other seed you completed
                self.add_disconnected_seed(d.connection.get_readable_id())
                d.connection.close()
            return True
        return False

    def too_many_partials(self):
        return len(self.storage.dirty) > (len(self.downloads)/2)


    def cancel_piece_download(self, pieces):
        if self.endgamemode:
            if self.endgame_queued_pieces:
                for piece in pieces:
                    try:
                        self.endgame_queued_pieces.remove(piece)
                    except:
                        pass
            new_all_requests = []
            for index, nb, nl in self.all_requests:
                if index in pieces:
                    self.storage.request_lost(index, nb, nl)
                else:
                    new_all_requests.append((index, nb, nl))
            self.all_requests = new_all_requests

        for d in self.downloads:
            hit = False
            for index, nb, nl in d.active_requests:
                if index in pieces:
                    hit = True
                    d.connection.send_cancel(index, nb, nl)
                    if not self.endgamemode:
                        self.storage.request_lost(index, nb, nl)
            if hit:
                d.active_requests = [ r for r in d.active_requests
                                      if r[0] not in pieces ]
                d._request_more()
            if not self.endgamemode and d.choked:
                d._check_interests()

    def requeue_piece_download(self, pieces = []):
        if self.endgame_queued_pieces:
            for piece in pieces:
                if not piece in self.endgame_queued_pieces:
                    self.endgame_queued_pieces.append(piece)
            pieces = self.endgame_queued_pieces
        if self.endgamemode:
            if self.all_requests:
                self.endgame_queued_pieces = pieces
                return
            self.endgamemode = False
            self.endgame_queued_pieces = None
           
        ds = [d for d in self.downloads]
        shuffle(ds)
        for d in ds:
            if d.choked:
                d._check_interests()
            else:
                d._request_more()

    def start_endgame(self):
        assert not self.endgamemode
        self.endgamemode = True
        assert not self.all_requests
        for d in self.downloads:
            if d.active_requests:
                assert d.interested and not d.choked
            for request in d.active_requests:
                assert not request in self.all_requests
                self.all_requests.append(request)
        for d in self.downloads:
            d.fix_download_endgame()

    def pause(self, flag):
        self.paused = flag
        if flag:
            for d in self.downloads:
                for index, begin, length in d.active_requests:
                    d.connection.send_cancel(index, begin, length)
                d._letgo()
                d.send_not_interested()
            if self.endgamemode:
                self._reset_endgame()
        else:
            shuffle(self.downloads)
            for d in self.downloads:
                d._check_interests()
                if d.interested and not d.choked:
                    d._request_more()

########NEW FILE########
__FILENAME__ = DownloaderFeedback
# Written by Bram Cohen
# see LICENSE.txt for license information

from threading import Event

try:
    True
except:
    True = 1
    False = 0

class DownloaderFeedback:
    def __init__(self, choker, httpdl, add_task, upfunc, downfunc,
            ratemeasure, leftfunc, file_length, finflag, sp, statistics,
            statusfunc = None, interval = None):
        self.choker = choker
        self.httpdl = httpdl
        self.add_task = add_task
        self.upfunc = upfunc
        self.downfunc = downfunc
        self.ratemeasure = ratemeasure
        self.leftfunc = leftfunc
        self.file_length = file_length
        self.finflag = finflag
        self.sp = sp
        self.statistics = statistics
        self.lastids = []
        self.spewdata = None
        self.doneprocessing = Event()
        self.doneprocessing.set()
        if statusfunc:
            self.autodisplay(statusfunc, interval)
        

    def _rotate(self):
        cs = self.choker.connections
        for id in self.lastids:
            for i in xrange(len(cs)):
                if cs[i].get_id() == id:
                    return cs[i:] + cs[:i]
        return cs

    def spews(self):
        l = []
        cs = self._rotate()
        self.lastids = [c.get_id() for c in cs]
        for c in cs:
            a = {}
            a['id'] = c.get_readable_id()
            a['ip'] = c.get_ip()
            a['optimistic'] = (c is self.choker.connections[0])
            if c.is_locally_initiated():
                a['direction'] = 'L'
            else:
                a['direction'] = 'R'
            u = c.get_upload()
            a['uprate'] = int(u.measure.get_rate())
            a['uinterested'] = u.is_interested()
            a['uchoked'] = u.is_choked()
            d = c.get_download()
            a['downrate'] = int(d.measure.get_rate())
            a['dinterested'] = d.is_interested()
            a['dchoked'] = d.is_choked()
            a['snubbed'] = d.is_snubbed()
            a['utotal'] = d.connection.upload.measure.get_total()
            a['dtotal'] = d.connection.download.measure.get_total()
            if d.connection.download.have:
                a['completed'] = float(len(d.connection.download.have)-d.connection.download.have.numfalse)/float(len(d.connection.download.have))
            else:
                a['completed'] = 1.0
            a['speed'] = d.connection.download.peermeasure.get_rate()

            l.append(a)                                               

        for dl in self.httpdl.get_downloads():
            if dl.goodseed:
                a = {}
                a['id'] = 'http seed'
                a['ip'] = dl.baseurl
                a['optimistic'] = False
                a['direction'] = 'L'
                a['uprate'] = 0
                a['uinterested'] = False
                a['uchoked'] = False
                a['downrate'] = int(dl.measure.get_rate())
                a['dinterested'] = True
                a['dchoked'] = not dl.active
                a['snubbed'] = not dl.active
                a['utotal'] = None
                a['dtotal'] = dl.measure.get_total()
                a['completed'] = 1.0
                a['speed'] = None

                l.append(a)

        return l


    def gather(self, displayfunc = None):
        s = {'stats': self.statistics.update()}
        if self.sp.isSet():
            s['spew'] = self.spews()
        else:
            s['spew'] = None
        s['up'] = self.upfunc()
        if self.finflag.isSet():
            s['done'] = self.file_length
            return s
        s['down'] = self.downfunc()
        obtained, desired = self.leftfunc()
        s['done'] = obtained
        s['wanted'] = desired
        if desired > 0:
            s['frac'] = float(obtained)/desired
        else:
            s['frac'] = 1.0
        if desired == obtained:
            s['time'] = 0
        else:
            s['time'] = self.ratemeasure.get_time_left(desired-obtained)
        return s        


    def display(self, displayfunc):
        if not self.doneprocessing.isSet():
            return
        self.doneprocessing.clear()
        stats = self.gather()
        if self.finflag.isSet():
            displayfunc(dpflag = self.doneprocessing, 
                upRate = stats['up'], 
                statistics = stats['stats'], spew = stats['spew'])
        elif stats['time'] is not None:
            displayfunc(dpflag = self.doneprocessing, 
                fractionDone = stats['frac'], sizeDone = stats['done'], 
                downRate = stats['down'], upRate = stats['up'], 
                statistics = stats['stats'], spew = stats['spew'], 
                timeEst = stats['time'])
        else:
            displayfunc(dpflag = self.doneprocessing, 
                fractionDone = stats['frac'], sizeDone = stats['done'], 
                downRate = stats['down'], upRate = stats['up'], 
                statistics = stats['stats'], spew = stats['spew'])


    def autodisplay(self, displayfunc, interval):
        self.displayfunc = displayfunc
        self.interval = interval
        self._autodisplay()

    def _autodisplay(self):
        self.add_task(self._autodisplay, self.interval)
        self.display(self.displayfunc)

########NEW FILE########
__FILENAME__ = Encrypter
# Written by Bram Cohen
# see LICENSE.txt for license information

from cStringIO import StringIO
from binascii import b2a_hex
from socket import error as socketerror
from urllib import quote
try:
    True
except:
    True = 1
    False = 0

MAX_INCOMPLETE = 8

protocol_name = 'BitTorrent protocol'
option_pattern = chr(0)*8

def toint(s):
    return long(b2a_hex(s), 16)

def make_readable(s):
    if not s:
        return ''
    if quote(s).find('%') >= 0:
        return b2a_hex(s).upper()
    return '"'+s+'"'


class IncompleteCounter:
    def __init__(self):
        self.c = 0
    def increment(self):
        self.c += 1
    def decrement(self):
        self.c -= 1
    def toomany(self):
        return self.c >= MAX_INCOMPLETE
    
incompletecounter = IncompleteCounter()


# header, reserved, download id, my id, [length, message]

class Connection:
    def __init__(self, Encoder, connection, id, ext_handshake = False):
        self.Encoder = Encoder
        self.connection = connection
        self.connecter = Encoder.connecter
        self.id = id
        self.readable_id = make_readable(id)
        self.locally_initiated = (id != None)
        self.complete = False
        self.keepalive = lambda: None
        self.closed = False
        self.buffer = StringIO()
        if self.locally_initiated:
            incompletecounter.increment()
        if self.locally_initiated or ext_handshake:
            self.connection.write(chr(len(protocol_name)) + protocol_name + 
                option_pattern + self.Encoder.download_id)
        if ext_handshake:
            self.connection.write(self.Encoder.my_id)
            self.next_len, self.next_func = 20, self.read_peer_id
        else:
            self.next_len, self.next_func = 1, self.read_header_len
        self.Encoder.raw_server.add_task(self._auto_close, 15)

    def get_ip(self, real=False):
        return self.connection.get_ip(real)

    def get_id(self):
        return self.id

    def get_readable_id(self):
        return self.readable_id

    def is_locally_initiated(self):
        return self.locally_initiated

    def is_flushed(self):
        return self.connection.is_flushed()

    def read_header_len(self, s):
        if ord(s) != len(protocol_name):
            return None
        return len(protocol_name), self.read_header

    def read_header(self, s):
        if s != protocol_name:
            return None
        return 8, self.read_reserved

    def read_reserved(self, s):
        return 20, self.read_download_id

    def read_download_id(self, s):
        if s != self.Encoder.download_id:
            return None
        if not self.locally_initiated:
            self.Encoder.connecter.external_connection_made += 1
            self.connection.write(chr(len(protocol_name)) + protocol_name + 
                option_pattern + self.Encoder.download_id + self.Encoder.my_id)
        return 20, self.read_peer_id

    def read_peer_id(self, s):
        if not self.id:
            self.id = s
            self.readable_id = make_readable(s)
        else:
            if s != self.id:
                return None
        self.complete = self.Encoder.got_id(self)
        if not self.complete:
            return None
        if self.locally_initiated:
            self.connection.write(self.Encoder.my_id)
            incompletecounter.decrement()
        c = self.Encoder.connecter.connection_made(self)
        self.keepalive = c.send_keepalive
        return 4, self.read_len

    def read_len(self, s):
        l = toint(s)
        if l > self.Encoder.max_len:
            return None
        return l, self.read_message

    def read_message(self, s):
        if s != '':
            self.connecter.got_message(self, s)
        return 4, self.read_len

    def read_dead(self, s):
        return None

    def _auto_close(self):
        if not self.complete:
            self.close()

    def close(self):
        if not self.closed:
            self.connection.close()
            self.sever()

    def sever(self):
        self.closed = True
        del self.Encoder.connections[self.connection]
        if self.complete:
            self.connecter.connection_lost(self)
        elif self.locally_initiated:
            incompletecounter.decrement()

    def send_message_raw(self, message):
        if not self.closed:
            self.connection.write(message)

    def data_came_in(self, connection, s):
        self.Encoder.measurefunc(len(s))
        while 1:
            if self.closed:
                return
            i = self.next_len - self.buffer.tell()
            if i > len(s):
                self.buffer.write(s)
                return
            self.buffer.write(s[:i])
            s = s[i:]
            m = self.buffer.getvalue()
            self.buffer.reset()
            self.buffer.truncate()
            try:
                x = self.next_func(m)
            except:
                self.next_len, self.next_func = 1, self.read_dead
                raise
            if x is None:
                self.close()
                return
            self.next_len, self.next_func = x

    def connection_flushed(self, connection):
        if self.complete:
            self.connecter.connection_flushed(self)

    def connection_lost(self, connection):
        if self.Encoder.connections.has_key(connection):
            self.sever()


class Encoder:
    def __init__(self, connecter, raw_server, my_id, max_len,
            schedulefunc, keepalive_delay, download_id, 
            measurefunc, config):
        self.raw_server = raw_server
        self.connecter = connecter
        self.my_id = my_id
        self.max_len = max_len
        self.schedulefunc = schedulefunc
        self.keepalive_delay = keepalive_delay
        self.download_id = download_id
        self.measurefunc = measurefunc
        self.config = config
        self.connections = {}
        self.banned = {}
        self.to_connect = []
        self.paused = False
        if self.config['max_connections'] == 0:
            self.max_connections = 2 ** 30
        else:
            self.max_connections = self.config['max_connections']
        schedulefunc(self.send_keepalives, keepalive_delay)

    def send_keepalives(self):
        self.schedulefunc(self.send_keepalives, self.keepalive_delay)
        if self.paused:
            return
        for c in self.connections.values():
            c.keepalive()

    def start_connections(self, list):
        if not self.to_connect:
            self.raw_server.add_task(self._start_connection_from_queue)
        self.to_connect = list

    def _start_connection_from_queue(self):
        if self.connecter.external_connection_made:
            max_initiate = self.config['max_initiate']
        else:
            max_initiate = int(self.config['max_initiate']*1.5)
        cons = len(self.connections)
        if cons >= self.max_connections or cons >= max_initiate:
            delay = 60
        elif self.paused or incompletecounter.toomany():
            delay = 1
        else:
            delay = 0
            dns, id = self.to_connect.pop(0)
            self.start_connection(dns, id)
        if self.to_connect:
            self.raw_server.add_task(self._start_connection_from_queue, delay)

    def start_connection(self, dns, id):
        if ( self.paused
             or len(self.connections) >= self.max_connections
             or id == self.my_id
             or self.banned.has_key(dns[0]) ):
            return True
        for v in self.connections.values():
            if v is None:
                continue
            if id and v.id == id:
                return True
            ip = v.get_ip(True)
            if self.config['security'] and ip != 'unknown' and ip == dns[0]:
                return True
        try:
            c = self.raw_server.start_connection(dns)
            con = Connection(self, c, id)
            self.connections[c] = con
            c.set_handler(con)
        except socketerror:
            return False
        return True

    def _start_connection(self, dns, id):
        def foo(self=self, dns=dns, id=id):
            self.start_connection(dns, id)
       
        self.schedulefunc(foo, 0)

    def got_id(self, connection):
        if connection.id == self.my_id:
            self.connecter.external_connection_made -= 1
            return False
        ip = connection.get_ip(True)
        if self.config['security'] and self.banned.has_key(ip):
            return False
        for v in self.connections.values():
            if connection is not v:
                if connection.id == v.id:
                    return False
                if self.config['security'] and ip != 'unknown' and ip == v.get_ip(True):
                    v.close()
        return True

    def external_connection_made(self, connection):
        if self.paused or len(self.connections) >= self.max_connections:
            connection.close()
            return False
        con = Connection(self, connection, None)
        self.connections[connection] = con
        connection.set_handler(con)
        return True

    def externally_handshaked_connection_made(self, connection, options, already_read):
        if self.paused or len(self.connections) >= self.max_connections:
            connection.close()
            return False
        con = Connection(self, connection, None, True)
        self.connections[connection] = con
        connection.set_handler(con)
        if already_read:
            con.data_came_in(con, already_read)
        return True

    def close_all(self):
        for c in self.connections.values():
            c.close()
        self.connections = {}

    def ban(self, ip):
        self.banned[ip] = 1

    def pause(self, flag):
        self.paused = flag

########NEW FILE########
__FILENAME__ = fakeopen
# Written by Bram Cohen
# see LICENSE.txt for license information

class FakeHandle:
    def __init__(self, name, fakeopen):
        self.name = name
        self.fakeopen = fakeopen
        self.pos = 0
    
    def flush(self):
        pass
    
    def close(self):
        pass
    
    def seek(self, pos):
        self.pos = pos
    
    def read(self, amount = None):
        old = self.pos
        f = self.fakeopen.files[self.name]
        if self.pos >= len(f):
            return ''
        if amount is None:
            self.pos = len(f)
            return ''.join(f[old:])
        else:
            self.pos = min(len(f), old + amount)
            return ''.join(f[old:self.pos])
    
    def write(self, s):
        f = self.fakeopen.files[self.name]
        while len(f) < self.pos:
            f.append(chr(0))
        self.fakeopen.files[self.name][self.pos : self.pos + len(s)] = list(s)
        self.pos += len(s)

class FakeOpen:
    def __init__(self, initial = {}):
        self.files = {}
        for key, value in initial.items():
            self.files[key] = list(value)
    
    def open(self, filename, mode):
        """currently treats everything as rw - doesn't support append"""
        self.files.setdefault(filename, [])
        return FakeHandle(filename, self)

    def exists(self, file):
        return self.files.has_key(file)

    def getsize(self, file):
        return len(self.files[file])

def test_normal():
    f = FakeOpen({'f1': 'abcde'})
    assert f.exists('f1')
    assert not f.exists('f2')
    assert f.getsize('f1') == 5
    h = f.open('f1', 'rw')
    assert h.read(3) == 'abc'
    assert h.read(1) == 'd'
    assert h.read() == 'e'
    assert h.read(2) == ''
    h.write('fpq')
    h.seek(4)
    assert h.read(2) == 'ef'
    h.write('ghij')
    h.seek(0)
    assert h.read() == 'abcdefghij'
    h.seek(2)
    h.write('p')
    h.write('q')
    assert h.read(1) == 'e'
    h.seek(1)
    assert h.read(5) == 'bpqef'

    h2 = f.open('f2', 'rw')
    assert h2.read() == ''
    h2.write('mnop')
    h2.seek(1)
    assert h2.read() == 'nop'
    
    assert f.exists('f1')
    assert f.exists('f2')
    assert f.getsize('f1') == 10
    assert f.getsize('f2') == 4

########NEW FILE########
__FILENAME__ = FileSelector
# Written by John Hoffman
# see LICENSE.txt for license information

from random import shuffle
try:
    True
except:
    True = 1
    False = 0


class FileSelector:
    def __init__(self, files, piece_length, bufferdir,
                 storage, storagewrapper, sched, failfunc):
        self.files = files
        self.storage = storage
        self.storagewrapper = storagewrapper
        self.sched = sched
        self.failfunc = failfunc
        self.downloader = None
        self.picker = None

        storage.set_bufferdir(bufferdir)
        
        self.numfiles = len(files)
        self.priority = [1] * self.numfiles
        self.new_priority = None
        self.new_partials = None
        self.filepieces = []
        total = 0L
        for file, length in files:
            if not length:
                self.filepieces.append(())
            else:
                pieces = range( int(total/piece_length),
                                int((total+length-1)/piece_length)+1 )
                self.filepieces.append(tuple(pieces))
                total += length
        self.numpieces = int((total+piece_length-1)/piece_length)
        self.piece_priority = [1] * self.numpieces
        


    def init_priority(self, new_priority):
        try:
            assert len(new_priority) == self.numfiles
            for v in new_priority:
                assert type(v) in (type(0), type(0L))
                assert v >= -1
                assert v <= 2
        except:
#           print_exc()
            return False
        try:
            for f in xrange(self.numfiles):
                if new_priority[f] < 0:
                    self.storage.disable_file(f)
            self.new_priority = new_priority
        except (IOError, OSError), e:
            self.failfunc("can't open partial file for "
                          + self.files[f][0] + ': ' + str(e))
            return False
        return True

    '''
    d['priority'] = [file #1 priority [,file #2 priority...] ]
                    a list of download priorities for each file.
                    Priority may be -1, 0, 1, 2.  -1 = download disabled,
                    0 = highest, 1 = normal, 2 = lowest.
    Also see Storage.pickle and StorageWrapper.pickle for additional keys.
    '''
    def unpickle(self, d):
        if d.has_key('priority'):
            if not self.init_priority(d['priority']):
                return
        pieces = self.storage.unpickle(d)
        if not pieces:  # don't bother, nothing restoreable
            return
        new_piece_priority = self._get_piece_priority_list(self.new_priority)
        self.storagewrapper.reblock([i == -1 for i in new_piece_priority])
        self.new_partials = self.storagewrapper.unpickle(d, pieces)


    def tie_in(self, picker, cancelfunc, requestmorefunc):
        self.picker = picker
        self.cancelfunc = cancelfunc
        self.requestmorefunc = requestmorefunc

        if self.new_priority:
            self.priority = self.new_priority
            self.new_priority = None
            self.new_piece_priority = self._set_piece_priority(self.priority)

        if self.new_partials:
            shuffle(self.new_partials)
            for p in self.new_partials:
                self.picker.requested(p)
        self.new_partials = None
        

    def _set_files_disabled(self, old_priority, new_priority):
        old_disabled = [p == -1 for p in old_priority]
        new_disabled = [p == -1 for p in new_priority]
        data_to_update = []
        for f in xrange(self.numfiles):
            if new_disabled[f] != old_disabled[f]:
                data_to_update.extend(self.storage.get_piece_update_list(f))
        buffer = []
        for piece, start, length in data_to_update:
            if self.storagewrapper.has_data(piece):
                data = self.storagewrapper.read_raw(piece, start, length)
                if data is None:
                    return False
                buffer.append((piece, start, data))

        files_updated = False        
        try:
            for f in xrange(self.numfiles):
                if new_disabled[f] and not old_disabled[f]:
                    self.storage.disable_file(f)
                    files_updated = True
                if old_disabled[f] and not new_disabled[f]:
                    self.storage.enable_file(f)
                    files_updated = True
        except (IOError, OSError), e:
            if new_disabled[f]:
                msg = "can't open partial file for "
            else:
                msg = 'unable to open '
            self.failfunc(msg + self.files[f][0] + ': ' + str(e))
            return False
        if files_updated:
            self.storage.reset_file_status()

        changed_pieces = {}
        for piece, start, data in buffer:
            if not self.storagewrapper.write_raw(piece, start, data):
                return False
            data.release()
            changed_pieces[piece] = 1
        if not self.storagewrapper.doublecheck_data(changed_pieces):
            return False

        return True        


    def _get_piece_priority_list(self, file_priority_list):
        l = [-1] * self.numpieces
        for f in xrange(self.numfiles):
            if file_priority_list[f] == -1:
                continue
            for i in self.filepieces[f]:
                if l[i] == -1:
                    l[i] = file_priority_list[f]
                    continue
                l[i] = min(l[i], file_priority_list[f])
        return l
        

    def _set_piece_priority(self, new_priority):
        new_piece_priority = self._get_piece_priority_list(new_priority)
        pieces = range(self.numpieces)
        shuffle(pieces)
        new_blocked = []
        new_unblocked = []
        for piece in pieces:
            self.picker.set_priority(piece, new_piece_priority[piece])
            o = self.piece_priority[piece] == -1
            n = new_piece_priority[piece] == -1
            if n and not o:
                new_blocked.append(piece)
            if o and not n:
                new_unblocked.append(piece)
        if new_blocked:
            self.cancelfunc(new_blocked)
        self.storagewrapper.reblock([i == -1 for i in new_piece_priority])
        if new_unblocked:
            self.requestmorefunc(new_unblocked)

        return new_piece_priority        


    def set_priorities_now(self, new_priority = None):
        if not new_priority:
            new_priority = self.new_priority
            self.new_priority = None    # potential race condition
            if not new_priority:
                return
        old_priority = self.priority
        self.priority = new_priority
        if not self._set_files_disabled(old_priority, new_priority):
            return
        self.piece_priority = self._set_piece_priority(new_priority)

    def set_priorities(self, new_priority):
        self.new_priority = new_priority
        def s(self=self):
            self.set_priorities_now()
        self.sched(s)
        
    def set_priority(self, f, p):
        new_priority = self.get_priorities()
        new_priority[f] = p
        self.set_priorities(new_priority)

    def get_priorities(self):
        priority = self.new_priority
        if not priority:
            priority = self.priority    # potential race condition
        return [i for i in priority]

    def __setitem__(self, index, val):
        self.set_priority(index, val)

    def __getitem__(self, index):
        try:
            return self.new_priority[index]
        except:
            return self.priority[index]


    def finish(self):
        pass
#        for f in xrange(self.numfiles):
#            if self.priority[f] == -1:
#                self.storage.delete_file(f)

    def pickle(self):
        d = {'priority': self.priority}
        try:
            s = self.storage.pickle()
            sw = self.storagewrapper.pickle()
            for k in s.keys():
                d[k] = s[k]
            for k in sw.keys():
                d[k] = sw[k]
        except (IOError, OSError):
            pass
        return d

########NEW FILE########
__FILENAME__ = Filter
class Filter:
    def __init__(self, callback):
        self.callback = callback

    def check(self, ip, paramslist, headers):

        def params(key, default = None, l = paramslist):
            if l.has_key(key):
                return l[key][0]
            return default

        return None

########NEW FILE########
__FILENAME__ = HTTPDownloader
# Written by John Hoffman
# see LICENSE.txt for license information

from BitTornado.CurrentRateMeasure import Measure
from random import randint
from urlparse import urlparse
from httplib import HTTPConnection
from urllib import quote
from threading import Thread
from BitTornado.__init__ import product_name,version_short
try:
    True
except:
    True = 1
    False = 0

EXPIRE_TIME = 60 * 60

VERSION = product_name+'/'+version_short

class haveComplete:
    def complete(self):
        return True
    def __getitem__(self, x):
        return True
haveall = haveComplete()

class SingleDownload:
    def __init__(self, downloader, url):
        self.downloader = downloader
        self.baseurl = url
        try:
            (scheme, self.netloc, path, pars, query, fragment) = urlparse(url)
        except:
            self.downloader.errorfunc('cannot parse http seed address: '+url)
            return
        if scheme != 'http':
            self.downloader.errorfunc('http seed url not http: '+url)
            return
        try:
            self.connection = HTTPConnection(self.netloc)
        except:
            self.downloader.errorfunc('cannot connect to http seed: '+url)
            return
        self.seedurl = path
        if pars:
            self.seedurl += ';'+pars
        self.seedurl += '?'
        if query:
            self.seedurl += query+'&'
        self.seedurl += 'info_hash='+quote(self.downloader.infohash)

        self.measure = Measure(downloader.max_rate_period)
        self.index = None
        self.url = ''
        self.requests = []
        self.request_size = 0
        self.endflag = False
        self.error = None
        self.retry_period = 30
        self._retry_period = None
        self.errorcount = 0
        self.goodseed = False
        self.active = False
        self.cancelled = False
        self.resched(randint(2, 10))

    def resched(self, len = None):
        if len is None:
            len = self.retry_period
        if self.errorcount > 3:
            len = len * (self.errorcount - 2)
        self.downloader.rawserver.add_task(self.download, len)

    def _want(self, index):
        if self.endflag:
            return self.downloader.storage.do_I_have_requests(index)
        else:
            return self.downloader.storage.is_unstarted(index)

    def download(self):
        self.cancelled = False
        if self.downloader.picker.am_I_complete():
            self.downloader.downloads.remove(self)
            return
        self.index = self.downloader.picker.next(haveall, self._want)
        if ( self.index is None and not self.endflag
                     and not self.downloader.peerdownloader.has_downloaders() ):
            self.endflag = True
            self.index = self.downloader.picker.next(haveall, self._want)
        if self.index is None:
            self.endflag = True
            self.resched()
        else:
            self.url = ( self.seedurl+'&piece='+str(self.index) )
            self._get_requests()
            if self.request_size < self.downloader.storage._piecelen(self.index):
                self.url += '&ranges='+self._request_ranges()
            rq = Thread(target = self._request)
            rq.setDaemon(False)
            rq.start()
            self.active = True

    def _request(self):
        import encodings.ascii
        import encodings.punycode
        import encodings.idna
        
        self.error = None
        self.received_data = None
        try:
            self.connection.request('GET', self.url, None, 
                                {'User-Agent': VERSION})
            r = self.connection.getresponse()
            self.connection_status = r.status
            self.received_data = r.read()
        except Exception, e:
            self.error = 'error accessing http seed: '+str(e)
            try:
                self.connection.close()
            except:
                pass
            try:
                self.connection = HTTPConnection(self.netloc)
            except:
                self.connection = None  # will cause an exception and retry next cycle
        self.downloader.rawserver.add_task(self.request_finished)

    def request_finished(self):
        self.active = False
        if self.error is not None:
            if self.goodseed:
                self.downloader.errorfunc(self.error)
            self.errorcount += 1
        if self.received_data:
            self.errorcount = 0
            if not self._got_data():
                self.received_data = None
        if not self.received_data:
            self._release_requests()
            self.downloader.peerdownloader.piece_flunked(self.index)
        if self._retry_period:
            self.resched(self._retry_period)
            self._retry_period = None
            return
        self.resched()

    def _got_data(self):
        if self.connection_status == 503:   # seed is busy
            try:
                self.retry_period = max(int(self.received_data), 5)
            except:
                pass
            return False
        if self.connection_status != 200:
            self.errorcount += 1
            return False
        self._retry_period = 1
        if len(self.received_data) != self.request_size:
            if self.goodseed:
                self.downloader.errorfunc('corrupt data from http seed - redownloading')
            return False
        self.measure.update_rate(len(self.received_data))
        self.downloader.measurefunc(len(self.received_data))
        if self.cancelled:
            return False
        if not self._fulfill_requests():
            return False
        if not self.goodseed:
            self.goodseed = True
            self.downloader.seedsfound += 1
        if self.downloader.storage.do_I_have(self.index):
            self.downloader.picker.complete(self.index)
            self.downloader.peerdownloader.check_complete(self.index)
            self.downloader.gotpiecefunc(self.index)
        return True
    
    def _get_requests(self):
        self.requests = []
        self.request_size = 0L
        while self.downloader.storage.do_I_have_requests(self.index):
            r = self.downloader.storage.new_request(self.index)
            self.requests.append(r)
            self.request_size += r[1]
        self.requests.sort()

    def _fulfill_requests(self):
        start = 0L
        success = True
        while self.requests:
            begin, length = self.requests.pop(0)
            if not self.downloader.storage.piece_came_in(self.index, begin, 
                            self.received_data[start:start+length]):
                success = False
                break
            start += length
        return success

    def _release_requests(self):
        for begin, length in self.requests:
            self.downloader.storage.request_lost(self.index, begin, length)
        self.requests = []

    def _request_ranges(self):
        s = ''
        begin, length = self.requests[0]
        for begin1, length1 in self.requests[1:]:
            if begin + length == begin1:
                length += length1
                continue
            else:
                if s:
                    s += ','
                s += str(begin)+'-'+str(begin+length-1)
                begin, length = begin1, length1
        if s:
            s += ','
        s += str(begin)+'-'+str(begin+length-1)
        return s
        
    
class HTTPDownloader:
    def __init__(self, storage, picker, rawserver,
                 finflag, errorfunc, peerdownloader,
                 max_rate_period, infohash, measurefunc, gotpiecefunc):
        self.storage = storage
        self.picker = picker
        self.rawserver = rawserver
        self.finflag = finflag
        self.errorfunc = errorfunc
        self.peerdownloader = peerdownloader
        self.infohash = infohash
        self.max_rate_period = max_rate_period
        self.gotpiecefunc = gotpiecefunc
        self.measurefunc = measurefunc
        self.downloads = []
        self.seedsfound = 0

    def make_download(self, url):
        self.downloads.append(SingleDownload(self, url))
        return self.downloads[-1]

    def get_downloads(self):
        if self.finflag.isSet():
            return []
        return self.downloads

    def cancel_piece_download(self, pieces):
        for d in self.downloads:
            if d.active and d.index in pieces:
                d.cancelled = True

########NEW FILE########
__FILENAME__ = makemetafile
# Written by Bram Cohen
# multitracker extensions by John Hoffman
# see LICENSE.txt for license information

from os.path import getsize, split, join, abspath, isdir
from os import listdir
from sha import sha
from copy import copy
from BitTornado.bencode import bencode
from btformats import check_info
from threading import Event
from time import time
from traceback import print_exc
try:
    from sys import getfilesystemencoding
    ENCODING = getfilesystemencoding()
except:
    from sys import getdefaultencoding
    ENCODING = getdefaultencoding()

defaults = [
    ('announce_list', '', 
        'a list of announce URLs - explained below'), 
    ('httpseeds', '', 
        'a list of http seed URLs - explained below'), 
    ('piece_size_pow2', 0, 
        "which power of 2 to set the piece size to (0 = automatic)"), 
    ('comment', '', 
        "optional human-readable comment to put in .torrent"), 
    ('filesystem_encoding', '', 
        "optional specification for filesystem encoding " +
        "(set automatically in recent Python versions)"), 
    ('target', '', 
        "optional target file for the torrent")
    ]

default_piece_len_exp = 18

ignore = ['core', 'CVS']

def print_announcelist_details():
    print ('    announce_list = optional list of redundant/backup tracker URLs, in the format:')
    print ('           url[,url...][|url[,url...]...]')
    print ('                where URLs separated by commas are all tried first')
    print ('                before the next group of URLs separated by the pipe is checked.')
    print ("                If none is given, it is assumed you don't want one in the metafile.")
    print ('                If announce_list is given, clients which support it')
    print ('                will ignore the <announce> value.')
    print ('           Examples:')
    print ('                http://tracker1.com|http://tracker2.com|http://tracker3.com')
    print ('                     (tries trackers 1-3 in order)')
    print ('                http://tracker1.com,http://tracker2.com,http://tracker3.com')
    print ('                     (tries trackers 1-3 in a randomly selected order)')
    print ('                http://tracker1.com|http://backup1.com,http://backup2.com')
    print ('                     (tries tracker 1 first, then tries between the 2 backups randomly)')
    print ('')
    print ('    httpseeds = optional list of http-seed URLs, in the format:')
    print ('            url[|url...]')
    
def make_meta_file(file, url, params = {}, flag = Event(),
                   progress = lambda x: None, progress_percent = 1):
    if params.has_key('piece_size_pow2'):
        piece_len_exp = params['piece_size_pow2']
    else:
        piece_len_exp = default_piece_len_exp
    if params.has_key('target') and params['target'] != '':
        f = params['target']
    else:
        a, b = split(file)
        if b == '':
            f = a + '.torrent'
        else:
            f = join(a, b + '.torrent')
            
    if piece_len_exp == 0:  # automatic
        size = calcsize(file)
        if   size > 8L*1024*1024*1024:   # > 8 gig =
            piece_len_exp = 21          #   2 meg pieces
        elif size > 2*1024*1024*1024:   # > 2 gig =
            piece_len_exp = 20          #   1 meg pieces
        elif size > 512*1024*1024:      # > 512M =
            piece_len_exp = 19          #   512K pieces
        elif size > 64*1024*1024:       # > 64M =
            piece_len_exp = 18          #   256K pieces
        elif size > 16*1024*1024:       # > 16M =
            piece_len_exp = 17          #   128K pieces
        elif size > 4*1024*1024:        # > 4M =
            piece_len_exp = 16          #   64K pieces
        else:                           # < 4M =
            piece_len_exp = 15          #   32K pieces
    piece_length = 2 ** piece_len_exp

    encoding = None
    if params.has_key('filesystem_encoding'):
        encoding = params['filesystem_encoding']
    if not encoding:
        encoding = ENCODING
    if not encoding:
        encoding = 'ascii'
    
    info = makeinfo(file, piece_length, encoding, flag, progress, progress_percent)
    if flag.isSet():
        return
    check_info(info)
    h = open(f, 'wb')
    data = {'info': info, 'announce': url.strip(), 'creation date': long(time())}
    
    if params.has_key('comment') and params['comment']:
        data['comment'] = params['comment']
        
    if params.has_key('real_announce_list'):    # shortcut for progs calling in from outside
        data['announce-list'] = params['real_announce_list']
    elif params.has_key('announce_list') and params['announce_list']:
        l = []
        for tier in params['announce_list'].split('|'):
            l.append(tier.split(','))
        data['announce-list'] = l
        
    if params.has_key('real_httpseeds'):    # shortcut for progs calling in from outside
        data['httpseeds'] = params['real_httpseeds']
    elif params.has_key('httpseeds') and params['httpseeds']:
        data['httpseeds'] = params['httpseeds'].split('|')
        
    h.write(bencode(data))
    h.close()

def calcsize(file):
    if not isdir(file):
        return getsize(file)
    total = 0L
    for s in subfiles(abspath(file)):
        total += getsize(s[1])
    return total


def uniconvertl(l, e):
    r = []
    try:
        for s in l:
            r.append(uniconvert(s, e))
    except UnicodeError:
        raise UnicodeError('bad filename: '+join(l))
    return r

def uniconvert(s, e):
    try:
        s = unicode(s, e)
    except UnicodeError:
        raise UnicodeError('bad filename: '+s)
    return s.encode('utf-8')

def makeinfo(file, piece_length, encoding, flag, progress, progress_percent=1):
    file = abspath(file)
    if isdir(file):
        subs = subfiles(file)
        subs.sort()
        pieces = []
        sh = sha()
        done = 0L
        fs = []
        totalsize = 0.0
        totalhashed = 0L
        for p, f in subs:
            totalsize += getsize(f)

        for p, f in subs:
            pos = 0L
            size = getsize(f)
            fs.append({'length': size, 'path': uniconvertl(p, encoding)})
            h = open(f, 'rb')
            while pos < size:
                a = min(size - pos, piece_length - done)
                sh.update(h.read(a))
                if flag.isSet():
                    return
                done += a
                pos += a
                totalhashed += a
                
                if done == piece_length:
                    pieces.append(sh.digest())
                    done = 0
                    sh = sha()
                if progress_percent:
                    progress(totalhashed / totalsize)
                else:
                    progress(a)
            h.close()
        if done > 0:
            pieces.append(sh.digest())
        return {'pieces': ''.join(pieces), 
            'piece length': piece_length, 'files': fs, 
            'name': uniconvert(split(file)[1], encoding) }
    else:
        size = getsize(file)
        pieces = []
        p = 0L
        h = open(file, 'rb')
        while p < size:
            x = h.read(min(piece_length, size - p))
            if flag.isSet():
                return
            pieces.append(sha(x).digest())
            p += piece_length
            if p > size:
                p = size
            if progress_percent:
                progress(float(p) / size)
            else:
                progress(min(piece_length, size - p))
        h.close()
        return {'pieces': ''.join(pieces), 
            'piece length': piece_length, 'length': size, 
            'name': uniconvert(split(file)[1], encoding) }

def subfiles(d):
    r = []
    stack = [([], d)]
    while stack:
        p, n = stack.pop()
        if isdir(n):
            for s in listdir(n):
                if s not in ignore and s[:1] != '.':
                    stack.append((copy(p) + [s], join(n, s)))
        else:
            r.append((p, n))
    return r


def completedir(dir, url, params = {}, flag = Event(),
                vc = lambda x: None, fc = lambda x: None):
    files = listdir(dir)
    files.sort()
    ext = '.torrent'
    if params.has_key('target'):
        target = params['target']
    else:
        target = ''

    togen = []
    for f in files:
        if f[-len(ext):] != ext and (f + ext) not in files:
            togen.append(join(dir, f))
        
    total = 0
    for i in togen:
        total += calcsize(i)

    subtotal = [0]
    def callback(x, subtotal = subtotal, total = total, vc = vc):
        subtotal[0] += x
        vc(float(subtotal[0]) / total)
    for i in togen:
        fc(i)
        try:
            t = split(i)[-1]
            if t not in ignore and t[0] != '.':
                if target != '':
                    params['target'] = join(target, t+ext)
                make_meta_file(i, url, params, flag, progress = callback, progress_percent = 0)
        except ValueError:
            print_exc()

########NEW FILE########
__FILENAME__ = NatCheck
# Written by Bram Cohen
# see LICENSE.txt for license information

from cStringIO import StringIO
from socket import error as socketerror
from traceback import print_exc
try:
    True
except:
    True = 1
    False = 0

protocol_name = 'BitTorrent protocol'

# header, reserved, download id, my id, [length, message]

class NatCheck:
    def __init__(self, resultfunc, downloadid, peerid, ip, port, rawserver):
        self.resultfunc = resultfunc
        self.downloadid = downloadid
        self.peerid = peerid
        self.ip = ip
        self.port = port
        self.closed = False
        self.buffer = StringIO()
        self.next_len = 1
        self.next_func = self.read_header_len
        try:
            self.connection = rawserver.start_connection((ip, port), self)
            self.connection.write(chr(len(protocol_name)) + protocol_name +
                (chr(0) * 8) + downloadid)
        except socketerror:
            self.answer(False)
        except IOError:
            self.answer(False)

    def answer(self, result):
        self.closed = True
        try:
            self.connection.close()
        except AttributeError:
            pass
        self.resultfunc(result, self.downloadid, self.peerid, self.ip, self.port)

    def read_header_len(self, s):
        if ord(s) != len(protocol_name):
            return None
        return len(protocol_name), self.read_header

    def read_header(self, s):
        if s != protocol_name:
            return None
        return 8, self.read_reserved

    def read_reserved(self, s):
        return 20, self.read_download_id

    def read_download_id(self, s):
        if s != self.downloadid:
            return None
        return 20, self.read_peer_id

    def read_peer_id(self, s):
        if s != self.peerid:
            return None
        self.answer(True)
        return None

    def data_came_in(self, connection, s):
        while 1:
            if self.closed:
                return
            i = self.next_len - self.buffer.tell()
            if i > len(s):
                self.buffer.write(s)
                return
            self.buffer.write(s[:i])
            s = s[i:]
            m = self.buffer.getvalue()
            self.buffer.reset()
            self.buffer.truncate()
            x = self.next_func(m)
            if x is None:
                if not self.closed:
                    self.answer(False)
                return
            self.next_len, self.next_func = x

    def connection_lost(self, connection):
        if not self.closed:
            self.closed = True
            self.resultfunc(False, self.downloadid, self.peerid, self.ip, self.port)

    def connection_flushed(self, connection):
        pass

########NEW FILE########
__FILENAME__ = PiecePicker
# Written by Bram Cohen
# see LICENSE.txt for license information

from random import randrange, shuffle
from BitTornado.clock import clock
try:
    True
except:
    True = 1
    False = 0

class PiecePicker:
    def __init__(self, numpieces,
                 rarest_first_cutoff = 1, rarest_first_priority_cutoff = 3,
                 priority_step = 20):
        self.rarest_first_cutoff = rarest_first_cutoff
        self.rarest_first_priority_cutoff = rarest_first_priority_cutoff + priority_step
        self.priority_step = priority_step
        self.cutoff = rarest_first_priority_cutoff
        self.numpieces = numpieces
        self.started = []
        self.totalcount = 0
        self.numhaves = [0] * numpieces
        self.priority = [1] * numpieces
        self.removed_partials = {}
        self.crosscount = [numpieces]
        self.crosscount2 = [numpieces]
        self.has = [0] * numpieces
        self.numgot = 0
        self.done = False
        self.seed_connections = {}
        self.seed_time = None
        self.superseed = False
        self.seeds_connected = 0
        self._init_interests()

    def _init_interests(self):
        self.interests = [[] for x in xrange(self.priority_step)]
        self.level_in_interests = [self.priority_step] * self.numpieces
        interests = range(self.numpieces)
        shuffle(interests)
        self.pos_in_interests = [0] * self.numpieces
        for i in xrange(self.numpieces):
            self.pos_in_interests[interests[i]] = i
        self.interests.append(interests)


    def got_have(self, piece):
        self.totalcount+=1
        numint = self.numhaves[piece]
        self.numhaves[piece] += 1
        self.crosscount[numint] -= 1
        if numint+1==len(self.crosscount):
            self.crosscount.append(0)
        self.crosscount[numint+1] += 1
        if not self.done:
            numintplus = numint+self.has[piece]
            self.crosscount2[numintplus] -= 1
            if numintplus+1 == len(self.crosscount2):
                self.crosscount2.append(0)
            self.crosscount2[numintplus+1] += 1
            numint = self.level_in_interests[piece]
            self.level_in_interests[piece] += 1
        if self.superseed:
            self.seed_got_haves[piece] += 1
            numint = self.level_in_interests[piece]
            self.level_in_interests[piece] += 1
        elif self.has[piece] or self.priority[piece] == -1:
            return
        if numint == len(self.interests) - 1:
            self.interests.append([])
        self._shift_over(piece, self.interests[numint], self.interests[numint + 1])

    def lost_have(self, piece):
        self.totalcount-=1
        numint = self.numhaves[piece]
        self.numhaves[piece] -= 1
        self.crosscount[numint] -= 1
        self.crosscount[numint-1] += 1
        if not self.done:
            numintplus = numint+self.has[piece]
            self.crosscount2[numintplus] -= 1
            self.crosscount2[numintplus-1] += 1
            numint = self.level_in_interests[piece]
            self.level_in_interests[piece] -= 1
        if self.superseed:
            numint = self.level_in_interests[piece]
            self.level_in_interests[piece] -= 1
        elif self.has[piece] or self.priority[piece] == -1:
            return
        self._shift_over(piece, self.interests[numint], self.interests[numint - 1])

    def _shift_over(self, piece, l1, l2):
        assert self.superseed or (not self.has[piece] and self.priority[piece] >= 0)
        parray = self.pos_in_interests
        p = parray[piece]
        assert l1[p] == piece
        q = l1[-1]
        l1[p] = q
        parray[q] = p
        del l1[-1]
        newp = randrange(len(l2)+1)
        if newp == len(l2):
            parray[piece] = len(l2)
            l2.append(piece)
        else:
            old = l2[newp]
            parray[old] = len(l2)
            l2.append(old)
            l2[newp] = piece
            parray[piece] = newp


    def got_seed(self):
        self.seeds_connected += 1
        self.cutoff = max(self.rarest_first_priority_cutoff-self.seeds_connected, 0)

    def became_seed(self):
        self.got_seed()
        self.totalcount -= self.numpieces
        self.numhaves = [i-1 for i in self.numhaves]
        if self.superseed or not self.done:
            self.level_in_interests = [i-1 for i in self.level_in_interests]
            del self.interests[0]
        del self.crosscount[0]
        if not self.done:
            del self.crosscount2[0]

    def lost_seed(self):
        self.seeds_connected -= 1
        self.cutoff = max(self.rarest_first_priority_cutoff-self.seeds_connected, 0)


    def requested(self, piece):
        if piece not in self.started:
            self.started.append(piece)

    def _remove_from_interests(self, piece, keep_partial = False):
        l = self.interests[self.level_in_interests[piece]]
        p = self.pos_in_interests[piece]
        assert l[p] == piece
        q = l[-1]
        l[p] = q
        self.pos_in_interests[q] = p
        del l[-1]
        try:
            self.started.remove(piece)
            if keep_partial:
                self.removed_partials[piece] = 1
        except ValueError:
            pass

    def complete(self, piece):
        assert not self.has[piece]
        self.has[piece] = 1
        self.numgot += 1
        if self.numgot == self.numpieces:
            self.done = True
            self.crosscount2 = self.crosscount
        else:
            numhaves = self.numhaves[piece]
            self.crosscount2[numhaves] -= 1
            if numhaves+1 == len(self.crosscount2):
                self.crosscount2.append(0)
            self.crosscount2[numhaves+1] += 1
        self._remove_from_interests(piece)


    def next(self, haves, wantfunc, complete_first = False):
        cutoff = self.numgot < self.rarest_first_cutoff
        complete_first = (complete_first or cutoff) and not haves.complete()
        best = None
        bestnum = 2 ** 30
        for i in self.started:
            if haves[i] and wantfunc(i):
                if self.level_in_interests[i] < bestnum:
                    best = i
                    bestnum = self.level_in_interests[i]
        if best is not None:
            if complete_first or (cutoff and len(self.interests) > self.cutoff):
                return best
        if haves.complete():
            r = [ (0, min(bestnum, len(self.interests))) ]
        elif cutoff and len(self.interests) > self.cutoff:
            r = [ (self.cutoff, min(bestnum, len(self.interests))),
                      (0, self.cutoff) ]
        else:
            r = [ (0, min(bestnum, len(self.interests))) ]
        for lo, hi in r:
            for i in xrange(lo, hi):
                for j in self.interests[i]:
                    if haves[j] and wantfunc(j):
                        return j
        if best is not None:
            return best
        return None


    def am_I_complete(self):
        return self.done
    
    def bump(self, piece):
        l = self.interests[self.level_in_interests[piece]]
        pos = self.pos_in_interests[piece]
        del l[pos]
        l.append(piece)
        for i in range(pos, len(l)):
            self.pos_in_interests[l[i]] = i
        try:
            self.started.remove(piece)
        except:
            pass

    def set_priority(self, piece, p):
        if self.superseed:
            return False    # don't muck with this if you're a superseed
        oldp = self.priority[piece]
        if oldp == p:
            return False
        self.priority[piece] = p
        if p == -1:
            # when setting priority -1,
            # make sure to cancel any downloads for this piece
            if not self.has[piece]:
                self._remove_from_interests(piece, True)
            return True
        if oldp == -1:
            level = self.numhaves[piece] + (self.priority_step * p)
            self.level_in_interests[piece] = level
            if self.has[piece]:
                return True
            while len(self.interests) < level+1:
                self.interests.append([])
            l2 = self.interests[level]
            parray = self.pos_in_interests
            newp = randrange(len(l2)+1)
            if newp == len(l2):
                parray[piece] = len(l2)
                l2.append(piece)
            else:
                old = l2[newp]
                parray[old] = len(l2)
                l2.append(old)
                l2[newp] = piece
                parray[piece] = newp
            if self.removed_partials.has_key(piece):
                del self.removed_partials[piece]
                self.started.append(piece)
            # now go to downloader and try requesting more
            return True
        numint = self.level_in_interests[piece]
        newint = numint + ((p - oldp) * self.priority_step)
        self.level_in_interests[piece] = newint
        if self.has[piece]:
            return False
        while len(self.interests) < newint+1:
            self.interests.append([])
        self._shift_over(piece, self.interests[numint], self.interests[newint])
        return False

    def is_blocked(self, piece):
        return self.priority[piece] < 0


    def set_superseed(self):
        assert self.done
        self.superseed = True
        self.seed_got_haves = [0] * self.numpieces
        self._init_interests()  # assume everyone is disconnected

    def next_have(self, connection, looser_upload):
        if self.seed_time is None:
            self.seed_time = clock()
            return None
        if clock() < self.seed_time+10:  # wait 10 seconds after seeing the first peers
            return None                 # to give time to grab have lists
        if not connection.upload.super_seeding:
            return None
        if connection in self.seed_connections:
            if looser_upload:
                num = 1     # send a new have even if it hasn't spread that piece elsewhere
            else:
                num = 2
            if self.seed_got_haves[self.seed_connections[connection]] < num:
                return None
            if not connection.upload.was_ever_interested:   # it never downloaded it?
                connection.upload.skipped_count += 1
                if connection.upload.skipped_count >= 3:    # probably another stealthed seed
                    return -1                               # signal to close it
        for tier in self.interests:
            for piece in tier:
                if not connection.download.have[piece]:
                    seedint = self.level_in_interests[piece]
                    self.level_in_interests[piece] += 1  # tweak it up one, so you don't duplicate effort
                    if seedint == len(self.interests) - 1:
                        self.interests.append([])
                    self._shift_over(piece, 
                                self.interests[seedint], self.interests[seedint + 1])
                    self.seed_got_haves[piece] = 0       # reset this
                    self.seed_connections[connection] = piece
                    connection.upload.seed_have_list.append(piece)
                    return piece
        return -1       # something screwy; terminate connection

    def lost_peer(self, connection):
        try:
            del self.seed_connections[connection]
        except:
            pass

########NEW FILE########
__FILENAME__ = Rerequester
# Written by Bram Cohen
# modified for multitracker operation by John Hoffman
# see LICENSE.txt for license information

from BitTornado.zurllib import urlopen
from urllib import quote
from btformats import check_peers
from BitTornado.bencode import bdecode
from threading import Thread, Lock
from cStringIO import StringIO
from traceback import print_exc
from socket import error, gethostbyname
from random import shuffle
from sha import sha
from time import time
try:
    from os import getpid
except ImportError:
    def getpid():
        return 1
    
try:
    True
except:
    True = 1
    False = 0

mapbase64 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.-'
keys = {}
basekeydata = str(getpid()) + repr(time()) + 'tracker'

def add_key(tracker):
    key = ''
    for i in sha(basekeydata+tracker).digest()[-6:]:
        key += mapbase64[ord(i) & 0x3F]
    keys[tracker] = key

def get_key(tracker):
    try:
        return "&key="+keys[tracker]
    except:
        add_key(tracker)
        return "&key="+keys[tracker]

class fakeflag:
    def __init__(self, state=False):
        self.state = state
    def wait(self):
        pass
    def isSet(self):
        return self.state

class Rerequester:
    def __init__(self, trackerlist, interval, sched, howmany, minpeers, 
            connect, externalsched, amount_left, up, down, 
            port, ip, myid, infohash, timeout, errorfunc, excfunc, 
            maxpeers, doneflag, upratefunc, downratefunc, 
            unpauseflag = fakeflag(True)):

        self.excfunc = excfunc
        newtrackerlist = []        
        for tier in trackerlist:
            if len(tier) > 1:
                shuffle(tier)
            newtrackerlist += [tier]
        self.trackerlist = newtrackerlist
        self.lastsuccessful = ''
        self.rejectedmessage = 'rejected by tracker - '
        
        self.url = ('?info_hash=%s&peer_id=%s&port=%s' %
            (quote(infohash), quote(myid), str(port)))
        self.ip = ip
        self.interval = interval
        self.last = None
        self.trackerid = None
        self.announce_interval = 30 * 60
        self.sched = sched
        self.howmany = howmany
        self.minpeers = minpeers
        self.connect = connect
        self.externalsched = externalsched
        self.amount_left = amount_left
        self.up = up
        self.down = down
        self.timeout = timeout
        self.errorfunc = errorfunc
        self.maxpeers = maxpeers
        self.doneflag = doneflag
        self.upratefunc = upratefunc
        self.downratefunc = downratefunc
        self.unpauseflag = unpauseflag
        self.last_failed = True
        self.never_succeeded = True
        self.errorcodes = {}
        self.lock = SuccessLock()
        self.special = None
        self.stopped = False

    def start(self):
        self.sched(self.c, self.interval/2)
        self.d(0)

    def c(self):
        if self.stopped:
            return
        if not self.unpauseflag.isSet() and self.howmany() < self.minpeers:
            self.announce(3, self._c)
        else:
            self._c()

    def _c(self):
        self.sched(self.c, self.interval)

    def d(self, event = 3):
        if self.stopped:
            return
        if not self.unpauseflag.isSet():
            self._d()
            return
        self.announce(event, self._d)

    def _d(self):
        if self.never_succeeded:
            self.sched(self.d, 60)  # retry in 60 seconds
        else:
            self.sched(self.d, self.announce_interval)


    def announce(self, event = 3, callback = lambda: None, specialurl = None):

        if specialurl is not None:
            s = self.url+'&uploaded=0&downloaded=0&left=1'   # don't add to statistics
            if self.howmany() >= self.maxpeers:
                s += '&numwant=0'
            else:
                s += '&no_peer_id=1&compact=1'
            self.last_failed = True         # force true, so will display an error
            self.special = specialurl
            self.rerequest(s, callback)
            return
        
        else:
            s = ('%s&uploaded=%s&downloaded=%s&left=%s' %
                (self.url, str(self.up()), str(self.down()), 
                str(self.amount_left())))
        if self.last is not None:
            s += '&last=' + quote(str(self.last))
        if self.trackerid is not None:
            s += '&trackerid=' + quote(str(self.trackerid))
        if self.howmany() >= self.maxpeers:
            s += '&numwant=0'
        else:
            s += '&no_peer_id=1&compact=1'
        if event != 3:
            s += '&event=' + ['started', 'completed', 'stopped'][event]
        if event == 2:
            self.stopped = True
        self.rerequest(s, callback)


    def snoop(self, peers, callback = lambda: None):  # tracker call support
        self.rerequest(self.url
            +'&event=stopped&port=0&uploaded=0&downloaded=0&left=1&tracker=1&numwant='
            +str(peers), callback)


    def rerequest(self, s, callback):
        if not self.lock.isfinished():  # still waiting for prior cycle to complete??
            def retry(self = self, s = s, callback = callback):
                self.rerequest(s, callback)
            self.sched(retry, 5)         # retry in 5 seconds
            return
        self.lock.reset()
        rq = Thread(target = self._rerequest, args = [s, callback])
        rq.setDaemon(False)
        rq.start()

    def _rerequest(self, s, callback):
        try:
            def fail(self = self, callback = callback):
                self._fail(callback)
            if self.ip:
                try:
                    s += '&ip=' + gethostbyname(self.ip)
                except:
                    self.errorcodes['troublecode'] = 'unable to resolve: '+self.ip
                    self.externalsched(fail)
            self.errorcodes = {}
            if self.special is None:
                for t in range(len(self.trackerlist)):
                    for tr in range(len(self.trackerlist[t])):
                        tracker  = self.trackerlist[t][tr]
                        if self.rerequest_single(tracker, s, callback):
                            if not self.last_failed and tr != 0:
                                del self.trackerlist[t][tr]
                                self.trackerlist[t] = [tracker] + self.trackerlist[t]
                            return
            else:
                tracker = self.special
                self.special = None
                if self.rerequest_single(tracker, s, callback):
                    return
            # no success from any tracker
            self.externalsched(fail)
        except:
            self.exception(callback)


    def _fail(self, callback):
        if ( (self.upratefunc() < 100 and self.downratefunc() < 100)
             or not self.amount_left() ):
            for f in ['rejected', 'bad_data', 'troublecode']:
                if self.errorcodes.has_key(f):
                    r = self.errorcodes[f]
                    break
            else:
                r = 'Problem connecting to tracker - unspecified error'
            self.errorfunc(r)

        self.last_failed = True
        self.lock.give_up()
        self.externalsched(callback)


    def rerequest_single(self, t, s, callback):
        l = self.lock.set()
        rq = Thread(target = self._rerequest_single, args = [t, s+get_key(t), l, callback])
        rq.setDaemon(False)
        rq.start()
        self.lock.wait()
        if self.lock.success:
            self.lastsuccessful = t
            self.last_failed = False
            self.never_succeeded = False
            return True
        if not self.last_failed and self.lastsuccessful == t:
            # if the last tracker hit was successful, and you've just tried the tracker
            # you'd contacted before, don't go any further, just fail silently.
            self.last_failed = True
            self.externalsched(callback)
            self.lock.give_up()
            return True
        return False    # returns true if it wants rerequest() to exit


    def _rerequest_single(self, t, s, l, callback):
        try:        
            closer = [None]
            def timedout(self = self, l = l, closer = closer):
                if self.lock.trip(l):
                    self.errorcodes['troublecode'] = 'Problem connecting to tracker - timeout exceeded'
                    self.lock.unwait(l)
                try:
                    closer[0]()
                except:
                    pass
                    
            self.externalsched(timedout, self.timeout)

            err = None
            try:
                h = urlopen(t+s)
                closer[0] = h.close
                data = h.read()
            except (IOError, error), e:
                err = 'Problem connecting to tracker - ' + str(e)
            except:
                err = 'Problem connecting to tracker'
            try:
                h.close()
            except:
                pass
            if err:        
                if self.lock.trip(l):
                    self.errorcodes['troublecode'] = err
                    self.lock.unwait(l)
                return

            if not data:
                if self.lock.trip(l):
                    self.errorcodes['troublecode'] = 'no data from tracker'
                    self.lock.unwait(l)
                return
            
            try:
                r = bdecode(data, sloppy=1)
                check_peers(r)
            except ValueError, e:
                if self.lock.trip(l):
                    self.errorcodes['bad_data'] = 'bad data from tracker - ' + str(e)
                    self.lock.unwait(l)
                return
            
            if r.has_key('failure reason'):
                if self.lock.trip(l):
                    self.errorcodes['rejected'] = self.rejectedmessage + r['failure reason']
                    self.lock.unwait(l)
                return
                
            if self.lock.trip(l, True):     # success!
                self.lock.unwait(l)
            else:
                callback = lambda: None     # attempt timed out, don't do a callback

            # even if the attempt timed out, go ahead and process data
            def add(self = self, r = r, callback = callback):
                self.postrequest(r, callback)
            self.externalsched(add)
        except:
            self.exception(callback)


    def postrequest(self, r, callback):
        if r.has_key('warning message'):
            self.errorfunc('warning from tracker - ' + r['warning message'])
        self.announce_interval = r.get('interval', self.announce_interval)
        self.interval = r.get('min interval', self.interval)
        self.trackerid = r.get('tracker id', self.trackerid)
        self.last = r.get('last')
#        ps = len(r['peers']) + self.howmany()
        p = r['peers']
        peers = []
        if type(p) == type(''):
            for x in xrange(0, len(p), 6):
                ip = '.'.join([str(ord(i)) for i in p[x:x+4]])
                port = (ord(p[x+4]) << 8) | ord(p[x+5])
                peers.append(((ip, port), 0))
        else:
            for x in p:
                peers.append(((x['ip'].strip(), x['port']), x.get('peer id', 0)))
        ps = len(peers) + self.howmany()
        if ps < self.maxpeers:
            if self.doneflag.isSet():
                if r.get('num peers', 1000) - r.get('done peers', 0) > ps * 1.2:
                    self.last = None
            else:
                if r.get('num peers', 1000) > ps * 1.2:
                    self.last = None
        if peers:
            shuffle(peers)
            self.connect(peers)
        callback()

    def exception(self, callback):
        data = StringIO()
        print_exc(file = data)
        def r(s = data.getvalue(), callback = callback):
            if self.excfunc:
                self.excfunc(s)
            else:
                print s
            callback()
        self.externalsched(r)


class SuccessLock:
    def __init__(self):
        self.lock = Lock()
        self.pause = Lock()
        self.code = 0L
        self.success = False
        self.finished = True

    def reset(self):
        self.success = False
        self.finished = False

    def set(self):
        self.lock.acquire()
        if not self.pause.locked():
            self.pause.acquire()
        self.first = True
        self.code += 1L
        self.lock.release()
        return self.code

    def trip(self, code, s = False):
        self.lock.acquire()
        try:
            if code == self.code and not self.finished:
                r = self.first
                self.first = False
                if s:
                    self.finished = True
                    self.success = True
                return r
        finally:
            self.lock.release()

    def give_up(self):
        self.lock.acquire()
        self.success = False
        self.finished = True
        self.lock.release()

    def wait(self):
        self.pause.acquire()

    def unwait(self, code):
        if code == self.code and self.pause.locked():
            self.pause.release()

    def isfinished(self):
        self.lock.acquire()
        x = self.finished
        self.lock.release()
        return x    

########NEW FILE########
__FILENAME__ = Statistics
# Written by Edward Keyes
# see LICENSE.txt for license information

from threading import Event
try:
    True
except:
    True = 1
    False = 0

class Statistics_Response:
    pass    # empty class


class Statistics:
    def __init__(self, upmeasure, downmeasure, connecter, httpdl, 
                 ratelimiter, rerequest_lastfailed, fdatflag):
        self.upmeasure = upmeasure
        self.downmeasure = downmeasure
        self.connecter = connecter
        self.httpdl = httpdl
        self.ratelimiter = ratelimiter
        self.downloader = connecter.downloader
        self.picker = connecter.downloader.picker
        self.storage = connecter.downloader.storage
        self.torrentmeasure = connecter.downloader.totalmeasure
        self.rerequest_lastfailed = rerequest_lastfailed
        self.fdatflag = fdatflag
        self.fdatactive = False
        self.piecescomplete = None
        self.placesopen = None
        self.storage_totalpieces = len(self.storage.hashes)


    def set_dirstats(self, files, piece_length):
        self.piecescomplete = 0
        self.placesopen = 0
        self.filelistupdated = Event()
        self.filelistupdated.set()
        frange = xrange(len(files))
        self.filepieces = [[] for x in frange]
        self.filepieces2 = [[] for x in frange]
        self.fileamtdone = [0.0 for x in frange]
        self.filecomplete = [False for x in frange]
        self.fileinplace = [False for x in frange]
        start = 0L
        for i in frange:
            l = files[i][1]
            if l == 0:
                self.fileamtdone[i] = 1.0
                self.filecomplete[i] = True
                self.fileinplace[i] = True
            else:
                fp = self.filepieces[i]
                fp2 = self.filepieces2[i]
                for piece in range(int(start/piece_length), 
                                   int((start+l-1)/piece_length)+1):
                    fp.append(piece)
                    fp2.append(piece)
                start += l


    def update(self):
        s = Statistics_Response()
        s.upTotal = self.upmeasure.get_total()
        s.downTotal = self.downmeasure.get_total()
        s.last_failed = self.rerequest_lastfailed()
        s.external_connection_made = self.connecter.external_connection_made
        if s.downTotal > 0:
            s.shareRating = float(s.upTotal)/s.downTotal
        elif s.upTotal == 0:
            s.shareRating = 0.0
        else:
            s.shareRating = -1.0
        s.torrentRate = self.torrentmeasure.get_rate()
        s.torrentTotal = self.torrentmeasure.get_total()
        s.numSeeds = self.picker.seeds_connected
        s.numOldSeeds = self.downloader.num_disconnected_seeds()
        s.numPeers = len(self.downloader.downloads)-s.numSeeds
        s.numCopies = 0.0
        for i in self.picker.crosscount:
            if i==0:
                s.numCopies+=1
            else:
                s.numCopies+=1-float(i)/self.picker.numpieces
                break
        if self.picker.done:
            s.numCopies2 = s.numCopies + 1
        else:
            s.numCopies2 = 0.0
            for i in self.picker.crosscount2:
                if i==0:
                    s.numCopies2+=1
                else:
                    s.numCopies2+=1-float(i)/self.picker.numpieces
                    break
        s.discarded = self.downloader.discarded
        s.numSeeds += self.httpdl.seedsfound
        s.numOldSeeds += self.httpdl.seedsfound
        if s.numPeers == 0 or self.picker.numpieces == 0:
            s.percentDone = 0.0
        else:
            s.percentDone = 100.0*(float(self.picker.totalcount)/self.picker.numpieces)/s.numPeers

        s.backgroundallocating = self.storage.bgalloc_active
        s.storage_totalpieces = len(self.storage.hashes)
        s.storage_active = len(self.storage.stat_active)
        s.storage_new = len(self.storage.stat_new)
        s.storage_dirty = len(self.storage.dirty)
        numdownloaded = self.storage.stat_numdownloaded
        s.storage_justdownloaded = numdownloaded
        s.storage_numcomplete = self.storage.stat_numfound + numdownloaded
        s.storage_numflunked = self.storage.stat_numflunked
        s.storage_isendgame = self.downloader.endgamemode

        s.peers_kicked = self.downloader.kicked.items()
        s.peers_banned = self.downloader.banned.items()

        try:
            s.upRate = int(self.ratelimiter.upload_rate/1000)
            assert s.upRate < 5000
        except:
            s.upRate = 0
        s.upSlots = self.ratelimiter.slots

        if self.piecescomplete is None:     # not a multi-file torrent
            return s
        
        if self.fdatflag.isSet():
            if not self.fdatactive:
                self.fdatactive = True
        else:
            self.fdatactive = False

        if self.piecescomplete != self.picker.numgot:
            for i in xrange(len(self.filecomplete)):
                if self.filecomplete[i]:
                    continue
                oldlist = self.filepieces[i]
                newlist = [ piece
                            for piece in oldlist
                            if not self.storage.have[piece] ]
                if len(newlist) != len(oldlist):
                    self.filepieces[i] = newlist
                    self.fileamtdone[i] = (
                        (len(self.filepieces2[i])-len(newlist))
                         /float(len(self.filepieces2[i])) )
                    if not newlist:
                        self.filecomplete[i] = True
                    self.filelistupdated.set()

            self.piecescomplete = self.picker.numgot

        if ( self.filelistupdated.isSet()
                 or self.placesopen != len(self.storage.places) ):
            for i in xrange(len(self.filecomplete)):
                if not self.filecomplete[i] or self.fileinplace[i]:
                    continue
                while self.filepieces2[i]:
                    piece = self.filepieces2[i][-1]
                    if self.storage.places[piece] != piece:
                        break
                    del self.filepieces2[i][-1]
                if not self.filepieces2[i]:
                    self.fileinplace[i] = True
                    self.storage.set_file_readonly(i)
                    self.filelistupdated.set()

            self.placesopen = len(self.storage.places)

        s.fileamtdone = self.fileamtdone
        s.filecomplete = self.filecomplete
        s.fileinplace = self.fileinplace
        s.filelistupdated = self.filelistupdated

        return s


########NEW FILE########
__FILENAME__ = Storage
# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.piecebuffer import BufferPool
from threading import Lock
from time import strftime, localtime
import os
from os.path import exists, getsize, getmtime, basename
from traceback import print_exc
try:
    from os import fsync
except ImportError:
    fsync = lambda x: None
from bisect import bisect
    
try:
    True
except:
    True = 1
    False = 0

DEBUG = False

MAXREADSIZE = 32768
MAXLOCKSIZE = 1000000000L
MAXLOCKRANGE = 3999999999L   # only lock first 4 gig of file

_pool = BufferPool()
PieceBuffer = _pool.new

def dummy_status(fractionDone = None, activity = None):
    pass

class Storage:
    def __init__(self, files, piece_length, doneflag, config, 
                 disabled_files = None):
        # can raise IOError and ValueError
        self.files = files
        self.piece_length = piece_length
        self.doneflag = doneflag
        self.disabled = [False] * len(files)
        self.file_ranges = []
        self.disabled_ranges = []
        self.working_ranges = []
        numfiles = 0
        total = 0L
        so_far = 0L
        self.handles = {}
        self.whandles = {}
        self.tops = {}
        self.sizes = {}
        self.mtimes = {}
        if config.get('lock_files', True):
            self.lock_file, self.unlock_file = self._lock_file, self._unlock_file
        else:
            self.lock_file, self.unlock_file = lambda x1, x2: None, lambda x1, x2: None
        self.lock_while_reading = config.get('lock_while_reading', False)
        self.lock = Lock()

        if not disabled_files:
            disabled_files = [False] * len(files)

        for i in xrange(len(files)):
            file, length = files[i]
            if doneflag.isSet():    # bail out if doneflag is set
                return
            self.disabled_ranges.append(None)
            if length == 0:
                self.file_ranges.append(None)
                self.working_ranges.append([])
            else:
                range = (total, total + length, 0, file)
                self.file_ranges.append(range)
                self.working_ranges.append([range])
                numfiles += 1
                total += length
                if disabled_files[i]:
                    l = 0
                else:
                    if exists(file):
                        l = getsize(file)
                        if l > length:
                            h = open(file, 'rb+')
                            h.truncate(length)
                            h.flush()
                            h.close()
                            l = length
                    else:
                        l = 0
                        h = open(file, 'wb+')
                        h.flush()
                        h.close()
                    self.mtimes[file] = getmtime(file)
                self.tops[file] = l
                self.sizes[file] = length
                so_far += l

        self.total_length = total
        self._reset_ranges()

        self.max_files_open = config['max_files_open']
        if self.max_files_open > 0 and numfiles > self.max_files_open:
            self.handlebuffer = []
        else:
            self.handlebuffer = None


    if os.name == 'nt':
        def _lock_file(self, name, f):
            import msvcrt
            for p in range(0, min(self.sizes[name], MAXLOCKRANGE), MAXLOCKSIZE):
                f.seek(p)
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 
                               min(MAXLOCKSIZE, self.sizes[name]-p))

        def _unlock_file(self, name, f):
            import msvcrt
            for p in range(0, min(self.sizes[name], MAXLOCKRANGE), MAXLOCKSIZE):
                f.seek(p)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 
                               min(MAXLOCKSIZE, self.sizes[name]-p))

    elif os.name == 'posix':
        def _lock_file(self, name, f):
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

        def _unlock_file(self, name, f):
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    else:
        def _lock_file(self, name, f):
            pass
        def _unlock_file(self, name, f):
            pass


    def was_preallocated(self, pos, length):
        for file, begin, end in self._intervals(pos, length):
            if self.tops.get(file, 0) < end:
                return False
        return True


    def _sync(self, file):
        self._close(file)
        if self.handlebuffer:
            self.handlebuffer.remove(file)

    def sync(self):
        # may raise IOError or OSError
        for file in self.whandles.keys():
            self._sync(file)


    def set_readonly(self, f=None):
        if f is None:
            self.sync()
            return
        file = self.files[f][0]
        if self.whandles.has_key(file):
            self._sync(file)
            

    def get_total_length(self):
        return self.total_length


    def _open(self, file, mode):
        if self.mtimes.has_key(file):
            try:
                if self.handlebuffer is not None:
                    assert getsize(file) == self.tops[file]
                    newmtime = getmtime(file)
                    oldmtime = self.mtimes[file]
                    assert newmtime <= oldmtime+1
                    assert newmtime >= oldmtime-1
            except:
                if DEBUG:
                    print( file+' modified: '
                           +strftime('(%x %X)', localtime(self.mtimes[file]))
                           +strftime(' != (%x %X) ?', localtime(getmtime(file))) )
                raise IOError('modified during download')
        try:
            return open(file, mode)
        except:
            if DEBUG:
                print_exc()
            raise


    def _close(self, file):
        f = self.handles[file]
        del self.handles[file]
        if self.whandles.has_key(file):
            del self.whandles[file]
            f.flush()
            self.unlock_file(file, f)
            f.close()
            self.tops[file] = getsize(file)
            self.mtimes[file] = getmtime(file)
        else:
            if self.lock_while_reading:
                self.unlock_file(file, f)
            f.close()


    def _close_file(self, file):
        if not self.handles.has_key(file):
            return
        self._close(file)
        if self.handlebuffer:
            self.handlebuffer.remove(file)
        

    def _get_file_handle(self, file, for_write):
        if self.handles.has_key(file):
            if for_write and not self.whandles.has_key(file):
                self._close(file)
                try:
                    f = self._open(file, 'rb+')
                    self.handles[file] = f
                    self.whandles[file] = 1
                    self.lock_file(file, f)
                except (IOError, OSError), e:
                    if DEBUG:
                        print_exc()
                    raise IOError('unable to reopen '+file+': '+str(e))

            if self.handlebuffer:
                if self.handlebuffer[-1] != file:
                    self.handlebuffer.remove(file)
                    self.handlebuffer.append(file)
            elif self.handlebuffer is not None:
                self.handlebuffer.append(file)
        else:
            try:
                if for_write:
                    f = self._open(file, 'rb+')
                    self.handles[file] = f
                    self.whandles[file] = 1
                    self.lock_file(file, f)
                else:
                    f = self._open(file, 'rb')
                    self.handles[file] = f
                    if self.lock_while_reading:
                        self.lock_file(file, f)
            except (IOError, OSError), e:
                if DEBUG:
                    print_exc()
                raise IOError('unable to open '+file+': '+str(e))
            
            if self.handlebuffer is not None:
                self.handlebuffer.append(file)
                if len(self.handlebuffer) > self.max_files_open:
                    self._close(self.handlebuffer.pop(0))

        return self.handles[file]


    def _reset_ranges(self):
        self.ranges = []
        for l in self.working_ranges:
            self.ranges.extend(l)
            self.begins = [i[0] for i in self.ranges]

    def _intervals(self, pos, amount):
        r = []
        stop = pos + amount
        p = bisect(self.begins, pos) - 1
        while p < len(self.ranges):
            begin, end, offset, file = self.ranges[p]
            if begin >= stop:
                break
            r.append(( file, 
                       offset + max(pos, begin) - begin, 
                       offset + min(end, stop) - begin ))
            p += 1
        return r


    def read(self, pos, amount, flush_first = False):
        r = PieceBuffer()
        for file, pos, end in self._intervals(pos, amount):
            if DEBUG:
                print 'reading '+file+' from '+str(pos)+' to '+str(end)
            try:
                self.lock.acquire()
                h = self._get_file_handle(file, False)
                if flush_first and self.whandles.has_key(file):
                    h.flush()
                    fsync(h)
                h.seek(pos)
                while pos < end:
                    length = min(end-pos, MAXREADSIZE)
                    data = h.read(length)
                    if len(data) != length:
                        raise IOError('error reading data from '+ file)
                    r.append(data)
                    pos += length
                self.lock.release()
            except:
                self.lock.release()
                raise IOError('error reading data from '+ file)
        return r

    def write(self, pos, s):
        # might raise an IOError
        total = 0
        for file, begin, end in self._intervals(pos, len(s)):
            if DEBUG:
                print 'writing '+file+' from '+str(pos)+' to '+str(end)
            self.lock.acquire()
            h = self._get_file_handle(file, True)
            h.seek(begin)
            h.write(s[total: total + end - begin])
            self.lock.release()
            total += end - begin

    def top_off(self):
        for begin, end, offset, file in self.ranges:
            l = offset + end - begin
            if l > self.tops.get(file, 0):
                self.lock.acquire()
                h = self._get_file_handle(file, True)
                h.seek(l-1)
                h.write(chr(0xFF))
                self.lock.release()

    def flush(self):
        # may raise IOError or OSError
        for file in self.whandles.keys():
            self.lock.acquire()
            self.handles[file].flush()
            self.lock.release()

    def close(self):
        for file, f in self.handles.items():
            try:
                self.unlock_file(file, f)
            except:
                pass
            try:
                f.close()
            except:
                pass
        self.handles = {}
        self.whandles = {}
        self.handlebuffer = None


    def _get_disabled_ranges(self, f):
        if not self.file_ranges[f]:
            return ((), (), ())
        r = self.disabled_ranges[f]
        if r:
            return r
        start, end, offset, file = self.file_ranges[f]
        if DEBUG:
            print 'calculating disabled range for '+self.files[f][0]
            print 'bytes: '+str(start)+'-'+str(end)
            print 'file spans pieces '+str(int(start/self.piece_length))+'-'+str(int((end-1)/self.piece_length)+1)
        pieces = range(int(start/self.piece_length), 
                        int((end-1)/self.piece_length)+1)
        offset = 0
        disabled_files = []
        if len(pieces) == 1:
            if ( start % self.piece_length == 0
                 and end % self.piece_length == 0 ):   # happens to be a single,
                                                       # perfect piece
                working_range = [(start, end, offset, file)]
                update_pieces = []
            else:
                midfile = os.path.join(self.bufferdir, str(f))
                working_range = [(start, end, 0, midfile)]
                disabled_files.append((midfile, start, end))
                length = end - start
                self.sizes[midfile] = length
                piece = pieces[0]
                update_pieces = [(piece, start-(piece*self.piece_length), length)]
        else:
            update_pieces = []
            if start % self.piece_length != 0:  # doesn't begin on an even piece boundary
                end_b = pieces[1]*self.piece_length
                startfile = os.path.join(self.bufferdir, str(f)+'b')
                working_range_b = [ ( start, end_b, 0, startfile ) ]
                disabled_files.append((startfile, start, end_b))
                length = end_b - start
                self.sizes[startfile] = length
                offset = length
                piece = pieces.pop(0)
                update_pieces.append((piece, start-(piece*self.piece_length), length))
            else:
                working_range_b = []
            if f  != len(self.files)-1 and end % self.piece_length != 0:
                                                # doesn't end on an even piece boundary
                start_e = pieces[-1] * self.piece_length
                endfile = os.path.join(self.bufferdir, str(f)+'e')
                working_range_e = [ ( start_e, end, 0, endfile ) ]
                disabled_files.append((endfile, start_e, end))
                length = end - start_e
                self.sizes[endfile] = length
                piece = pieces.pop(-1)
                update_pieces.append((piece, 0, length))
            else:
                working_range_e = []
            if pieces:
                working_range_m = [ ( pieces[0]*self.piece_length,
                                      (pieces[-1]+1)*self.piece_length,
                                      offset, file ) ]
            else:
                working_range_m = []
            working_range = working_range_b + working_range_m + working_range_e

        if DEBUG:            
            print str(working_range)
            print str(update_pieces)
        r = (tuple(working_range), tuple(update_pieces), tuple(disabled_files))
        self.disabled_ranges[f] = r
        return r
        

    def set_bufferdir(self, dir):
        self.bufferdir = dir

    def enable_file(self, f):
        if not self.disabled[f]:
            return
        self.disabled[f] = False
        r = self.file_ranges[f]
        if not r:
            return
        file = r[3]
        if not exists(file):
            h = open(file, 'wb+')
            h.flush()
            h.close()
        if not self.tops.has_key(file):
            self.tops[file] = getsize(file)
        if not self.mtimes.has_key(file):
            self.mtimes[file] = getmtime(file)
        self.working_ranges[f] = [r]

    def disable_file(self, f):
        if self.disabled[f]:
            return
        self.disabled[f] = True
        r = self._get_disabled_ranges(f)
        if not r:
            return
        for file, begin, end in r[2]:
            if not os.path.isdir(self.bufferdir):
                os.makedirs(self.bufferdir)
            if not exists(file):
                h = open(file, 'wb+')
                h.flush()
                h.close()
            if not self.tops.has_key(file):
                self.tops[file] = getsize(file)
            if not self.mtimes.has_key(file):
                self.mtimes[file] = getmtime(file)
        self.working_ranges[f] = r[0]

    reset_file_status = _reset_ranges


    def get_piece_update_list(self, f):
        return self._get_disabled_ranges(f)[1]


    def delete_file(self, f):
        try:
            os.remove(self.files[f][0])
        except:
            pass


    '''
    Pickled data format:

    d['files'] = [ file #, size, mtime {, file #, size, mtime...} ]
                    file # in torrent, and the size and last modification
                    time for those files.  Missing files are either empty
                    or disabled.
    d['partial files'] = [ name, size, mtime... ]
                    Names, sizes and last modification times of files containing
                    partial piece data.  Filenames go by the following convention:
                    {file #, 0-based}{nothing, "b" or "e"}
                    eg: "0e" "3" "4b" "4e"
                    Where "b" specifies the partial data for the first piece in
                    the file, "e" the last piece, and no letter signifying that
                    the file is disabled but is smaller than one piece, and that
                    all the data is cached inside so adjacent files may be
                    verified.
    '''
    def pickle(self):
        files = []
        pfiles = []
        for i in xrange(len(self.files)):
            if not self.files[i][1]:    # length == 0
                continue
            if self.disabled[i]:
                for file, start, end in self._get_disabled_ranges(i)[2]:
                    pfiles.extend([basename(file), getsize(file), getmtime(file)])
                continue
            file = self.files[i][0]
            files.extend([i, getsize(file), getmtime(file)])
        return {'files': files, 'partial files': pfiles}


    def unpickle(self, data):
        # assume all previously-disabled files have already been disabled
        try:
            files = {}
            pfiles = {}
            l = data['files']
            assert len(l) % 3 == 0
            l = [l[x:x+3] for x in xrange(0, len(l), 3)]
            for f, size, mtime in l:
                files[f] = (size, mtime)
            l = data.get('partial files', [])
            assert len(l) % 3 == 0
            l = [l[x:x+3] for x in xrange(0, len(l), 3)]
            for file, size, mtime in l:
                pfiles[file] = (size, mtime)

            valid_pieces = {}
            for i in xrange(len(self.files)):
                if self.disabled[i]:
                    continue
                r = self.file_ranges[i]
                if not r:
                    continue
                start, end, offset, file = r
                if DEBUG:
                    print 'adding '+file
                for p in xrange( int(start/self.piece_length),
                                 int((end-1)/self.piece_length)+1 ):
                    valid_pieces[p] = 1

            if DEBUG:
                print valid_pieces.keys()
            
            def test(old, size, mtime):
                oldsize, oldmtime = old
                if size != oldsize:
                    return False
                if mtime > oldmtime+1:
                    return False
                if mtime < oldmtime-1:
                    return False
                return True

            for i in xrange(len(self.files)):
                if self.disabled[i]:
                    for file, start, end in self._get_disabled_ranges(i)[2]:
                        f1 = basename(file)
                        if ( not pfiles.has_key(f1)
                             or not test(pfiles[f1],getsize(file),getmtime(file)) ):
                            if DEBUG:
                                print 'removing '+file
                            for p in xrange( int(start/self.piece_length),
                                             int((end-1)/self.piece_length)+1 ):
                                if valid_pieces.has_key(p):
                                    del valid_pieces[p]
                    continue
                file, size = self.files[i]
                if not size:
                    continue
                if ( not files.has_key(i)
                     or not test(files[i], getsize(file), getmtime(file)) ):
                    start, end, offset, file = self.file_ranges[i]
                    if DEBUG:
                        print 'removing '+file
                    for p in xrange( int(start/self.piece_length),
                                     int((end-1)/self.piece_length)+1 ):
                        if valid_pieces.has_key(p):
                            del valid_pieces[p]
        except:
            if DEBUG:
                print_exc()
            return []

        if DEBUG:
            print valid_pieces.keys()                        
        return valid_pieces.keys()


########NEW FILE########
__FILENAME__ = StorageWrapper
# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.bitfield import Bitfield
from sha import sha
from BitTornado.clock import clock
from traceback import print_exc
from random import randrange
try:
    True
except:
    True = 1
    False = 0
from bisect import insort

DEBUG = False

STATS_INTERVAL = 0.2

def dummy_status(fractionDone = None, activity = None):
    pass

class Olist:
    def __init__(self, l = []):
        self.d = {}
        for i in l:
            self.d[i] = 1
    def __len__(self):
        return len(self.d)
    def includes(self, i):
        return self.d.has_key(i)
    def add(self, i):
        self.d[i] = 1
    def extend(self, l):
        for i in l:
            self.d[i] = 1
    def pop(self, n=0):
        # assert self.d
        k = self.d.keys()
        if n == 0:
            i = min(k)
        elif n == -1:
            i = max(k)
        else:
            k.sort()
            i = k[n]
        del self.d[i]
        return i
    def remove(self, i):
        if self.d.has_key(i):
            del self.d[i]

class fakeflag:
    def __init__(self, state=False):
        self.state = state
    def wait(self):
        pass
    def isSet(self):
        return self.state


class StorageWrapper:
    def __init__(self, storage, request_size, hashes, 
            piece_size, finished, failed, 
            statusfunc = dummy_status, flag = fakeflag(), check_hashes = True, 
            data_flunked = lambda x: None, backfunc = None, 
            config = {}, unpauseflag = fakeflag(True)):
        self.storage = storage
        self.request_size = long(request_size)
        self.hashes = hashes
        self.piece_size = long(piece_size)
        self.piece_length = long(piece_size)
        self.finished = finished
        self.failed = failed
        self.statusfunc = statusfunc
        self.flag = flag
        self.check_hashes = check_hashes
        self.data_flunked = data_flunked
        self.backfunc = backfunc
        self.config = config
        self.unpauseflag = unpauseflag
        
        self.alloc_type = config.get('alloc_type', 'normal')
        self.double_check = config.get('double_check', 0)
        self.triple_check = config.get('triple_check', 0)
        if self.triple_check:
            self.double_check = True
        self.bgalloc_enabled = False
        self.bgalloc_active = False
        self.total_length = storage.get_total_length()
        self.amount_left = self.total_length
        if self.total_length <= self.piece_size * (len(hashes) - 1):
            raise ValueError, 'bad data in responsefile - total too small'
        if self.total_length > self.piece_size * len(hashes):
            raise ValueError, 'bad data in responsefile - total too big'
        self.numactive = [0] * len(hashes)
        self.inactive_requests = [1] * len(hashes)
        self.amount_inactive = self.total_length
        self.amount_obtained = 0
        self.amount_desired = self.total_length
        self.have = Bitfield(len(hashes))
        self.have_cloaked_data = None
        self.blocked = [False] * len(hashes)
        self.blocked_holes = []
        self.blocked_movein = Olist()
        self.blocked_moveout = Olist()
        self.waschecked = [False] * len(hashes)
        self.places = {}
        self.holes = []
        self.stat_active = {}
        self.stat_new = {}
        self.dirty = {}
        self.stat_numflunked = 0
        self.stat_numdownloaded = 0
        self.stat_numfound = 0
        self.download_history = {}
        self.failed_pieces = {}
        self.out_of_place = 0
        self.write_buf_max = config['write_buffer_size']*1048576L
        self.write_buf_size = 0L
        self.write_buf = {}   # structure:  piece: [(start, data), ...]
        self.write_buf_list = []

        self.initialize_tasks = [
            ['checking existing data', 0, self.init_hashcheck, self.hashcheckfunc], 
            ['moving data', 1, self.init_movedata, self.movedatafunc], 
            ['allocating disk space', 1, self.init_alloc, self.allocfunc] ]

        self.backfunc(self._bgalloc, 0.1)
        self.backfunc(self._bgsync, max(self.config['auto_flush']*60, 60))

    def _bgsync(self):
        if self.config['auto_flush']:
            self.sync()
        self.backfunc(self._bgsync, max(self.config['auto_flush']*60, 60))


    def old_style_init(self):
        while self.initialize_tasks:
            msg, done, init, next = self.initialize_tasks.pop(0)
            if init():
                self.statusfunc(activity = msg, fractionDone = done)
                t = clock() + STATS_INTERVAL
                x = 0
                while x is not None:
                    if t < clock():
                        t = clock() + STATS_INTERVAL
                        self.statusfunc(fractionDone = x)
                    self.unpauseflag.wait()
                    if self.flag.isSet():
                        return False
                    x = next()

        self.statusfunc(fractionDone = 0)
        return True


    def initialize(self, donefunc, statusfunc = None):
        self.initialize_done = donefunc
        if statusfunc is None:
            statusfunc = self.statusfunc
        self.initialize_status = statusfunc
        self.initialize_next = None
            
        self.backfunc(self._initialize)

    def _initialize(self):
        if not self.unpauseflag.isSet():
            self.backfunc(self._initialize, 1)
            return
        
        if self.initialize_next:
            x = self.initialize_next()
            if x is None:
                self.initialize_next = None
            else:
                self.initialize_status(fractionDone = x)
        else:
            if not self.initialize_tasks:
                self.initialize_done()
                return
            msg, done, init, next = self.initialize_tasks.pop(0)
            if init():
                self.initialize_status(activity = msg, fractionDone = done)
                self.initialize_next = next

        self.backfunc(self._initialize)


    def init_hashcheck(self):
        if self.flag.isSet():
            return False
        self.check_list = []
        if not self.hashes or self.amount_left == 0:
            self.check_total = 0
            self.finished()
            return False

        self.check_targets = {}
        got = {}
        for p, v in self.places.items():
            assert not got.has_key(v)
            got[v] = 1
        for i in xrange(len(self.hashes)):
            if self.places.has_key(i):  # restored from pickled
                self.check_targets[self.hashes[i]] = []
                if self.places[i] == i:
                    continue
                else:
                    assert not got.has_key(i)
                    self.out_of_place += 1
            if got.has_key(i):
                continue
            if self._waspre(i):
                if self.blocked[i]:
                    self.places[i] = i
                else:
                    self.check_list.append(i)
                continue
            if not self.check_hashes:
                self.failed('told file complete on start-up, but data is missing')
                return False
            self.holes.append(i)
            if self.blocked[i] or self.check_targets.has_key(self.hashes[i]):
                self.check_targets[self.hashes[i]] = [] # in case of a hash collision, discard
            else:
                self.check_targets[self.hashes[i]] = [i]
        self.check_total = len(self.check_list)
        self.check_numchecked = 0.0
        self.lastlen = self._piecelen(len(self.hashes) - 1)
        self.numchecked = 0.0
        return self.check_total > 0

    def _markgot(self, piece, pos):
        if DEBUG:
            print str(piece)+' at '+str(pos)
        self.places[piece] = pos
        self.have[piece] = True
        len = self._piecelen(piece)
        self.amount_obtained += len
        self.amount_left -= len
        self.amount_inactive -= len
        self.inactive_requests[piece] = None
        self.waschecked[piece] = self.check_hashes
        self.stat_numfound += 1

    def hashcheckfunc(self):
        if self.flag.isSet():
            return None
        if not self.check_list:
            return None
        
        i = self.check_list.pop(0)
        if not self.check_hashes:
            self._markgot(i, i)
        else:
            d1 = self.read_raw(i, 0, self.lastlen)
            if d1 is None:
                return None
            sh = sha(d1[:])
            d1.release()
            sp = sh.digest()
            d2 = self.read_raw(i, self.lastlen, self._piecelen(i)-self.lastlen)
            if d2 is None:
                return None
            sh.update(d2[:])
            d2.release()
            s = sh.digest()
            if s == self.hashes[i]:
                self._markgot(i, i)
            elif (self.check_targets.get(s)
                   and self._piecelen(i) == self._piecelen(self.check_targets[s][-1])):
                self._markgot(self.check_targets[s].pop(), i)
                self.out_of_place += 1
            elif (not self.have[-1] and sp == self.hashes[-1]
                   and (i == len(self.hashes) - 1
                        or not self._waspre(len(self.hashes) - 1))):
                self._markgot(len(self.hashes) - 1, i)
                self.out_of_place += 1
            else:
                self.places[i] = i
        self.numchecked += 1
        if self.amount_left == 0:
            self.finished()
        return (self.numchecked / self.check_total)


    def init_movedata(self):
        if self.flag.isSet():
            return False
        if self.alloc_type != 'sparse':
            return False
        self.storage.top_off()  # sets file lengths to their final size
        self.movelist = []
        if self.out_of_place == 0:
            for i in self.holes:
                self.places[i] = i
            self.holes = []
            return False
        self.tomove = float(self.out_of_place)
        for i in xrange(len(self.hashes)):
            if not self.places.has_key(i):
                self.places[i] = i
            elif self.places[i] != i:
                self.movelist.append(i)
        self.holes = []
        return True

    def movedatafunc(self):
        if self.flag.isSet():
            return None
        if not self.movelist:
            return None
        i = self.movelist.pop(0)
        old = self.read_raw(self.places[i], 0, self._piecelen(i))
        if old is None:
            return None
        if not self.write_raw(i, 0, old):
            return None
        if self.double_check and self.have[i]:
            if self.triple_check:
                old.release()
                old = self.read_raw(i, 0, self._piecelen(i), 
                                            flush_first = True)
                if old is None:
                    return None
            if sha(old[:]).digest() != self.hashes[i]:
                self.failed('download corrupted; please restart and resume')
                return None
        old.release()

        self.places[i] = i
        self.tomove -= 1
        return (self.tomove / self.out_of_place)

        
    def init_alloc(self):
        if self.flag.isSet():
            return False
        if not self.holes:
            return False
        self.numholes = float(len(self.holes))
        self.alloc_buf = chr(0xFF) * self.piece_size
        if self.alloc_type == 'pre-allocate':
            self.bgalloc_enabled = True
            return True
        if self.alloc_type == 'background':
            self.bgalloc_enabled = True
        if self.blocked_moveout:
            return True
        return False


    def _allocfunc(self):
        while self.holes:
            n = self.holes.pop(0)
            if self.blocked[n]: # assume not self.blocked[index]
                if not self.blocked_movein:
                    self.blocked_holes.append(n)
                    continue
                if not self.places.has_key(n):
                    b = self.blocked_movein.pop(0)
                    oldpos = self._move_piece(b, n)
                    self.places[oldpos] = oldpos
                    return None
            if self.places.has_key(n):
                oldpos = self._move_piece(n, n)
                self.places[oldpos] = oldpos
                return None
            return n
        return None

    def allocfunc(self):
        if self.flag.isSet():
            return None
        
        if self.blocked_moveout:
            self.bgalloc_active = True
            n = self._allocfunc()
            if n is not None:
                if self.blocked_moveout.includes(n):
                    self.blocked_moveout.remove(n)
                    b = n
                else:
                    b = self.blocked_moveout.pop(0)
                oldpos = self._move_piece(b, n)
                self.places[oldpos] = oldpos
            return len(self.holes) / self.numholes

        if self.holes and self.bgalloc_enabled:
            self.bgalloc_active = True
            n = self._allocfunc()
            if n is not None:
                self.write_raw(n, 0, self.alloc_buf[:self._piecelen(n)])
                self.places[n] = n
            return len(self.holes) / self.numholes

        self.bgalloc_active = False
        return None

    def bgalloc(self):
        if self.bgalloc_enabled:
            if not self.holes and not self.blocked_moveout and self.backfunc:
                self.backfunc(self.storage.flush)
                # force a flush whenever the "finish allocation" button is hit
        self.bgalloc_enabled = True
        return False

    def _bgalloc(self):
        self.allocfunc()
        if self.config.get('alloc_rate', 0) < 0.1:
            self.config['alloc_rate'] = 0.1
        self.backfunc(self._bgalloc, 
              float(self.piece_size)/(self.config['alloc_rate']*1048576))


    def _waspre(self, piece):
        return self.storage.was_preallocated(piece * self.piece_size, self._piecelen(piece))

    def _piecelen(self, piece):
        if piece < len(self.hashes) - 1:
            return self.piece_size
        else:
            return self.total_length - (piece * self.piece_size)

    def get_amount_left(self):
        return self.amount_left

    def do_I_have_anything(self):
        return self.amount_left < self.total_length

    def _make_inactive(self, index):
        length = self._piecelen(index)
        l = []
        x = 0
        while x + self.request_size < length:
            l.append((x, self.request_size))
            x += self.request_size
        l.append((x, length - x))
        self.inactive_requests[index] = l

    def is_endgame(self):
        return not self.amount_inactive

    def reset_endgame(self, requestlist):
        for index, begin, length in requestlist:
            self.request_lost(index, begin, length)

    def get_have_list(self):
        return self.have.tostring()

    def get_have_list_cloaked(self):
        if self.have_cloaked_data is None:
            newhave = Bitfield(copyfrom = self.have)
            unhaves = []
            n = min(randrange(2, 5), len(self.hashes))    # between 2-4 unless torrent is small
            while len(unhaves) < n:
                unhave = randrange(min(32, len(self.hashes)))    # all in first 4 bytes
                if not unhave in unhaves:
                    unhaves.append(unhave)
                    newhave[unhave] = False
            self.have_cloaked_data = (newhave.tostring(), unhaves)
        return self.have_cloaked_data

    def do_I_have(self, index):
        return self.have[index]

    def do_I_have_requests(self, index):
        return not not self.inactive_requests[index]

    def is_unstarted(self, index):
        return (not self.have[index] and not self.numactive[index]
                 and not self.dirty.has_key(index))

    def get_hash(self, index):
        return self.hashes[index]

    def get_stats(self):
        return self.amount_obtained, self.amount_desired

    def new_request(self, index):
        # returns (begin, length)
        if self.inactive_requests[index] == 1:
            self._make_inactive(index)
        self.numactive[index] += 1
        self.stat_active[index] = 1
        if not self.dirty.has_key(index):
            self.stat_new[index] = 1
        rs = self.inactive_requests[index]
#        r = min(rs)
#        rs.remove(r)
        r = rs.pop(0)
        self.amount_inactive -= r[1]
        return r


    def write_raw(self, index, begin, data):
        try:
            self.storage.write(self.piece_size * index + begin, data)
            return True
        except IOError, e:
            self.failed('IO Error: ' + str(e))
            return False


    def _write_to_buffer(self, piece, start, data):
        if not self.write_buf_max:
            return self.write_raw(self.places[piece], start, data)
        self.write_buf_size += len(data)
        while self.write_buf_size > self.write_buf_max:
            old = self.write_buf_list.pop(0)
            if not self._flush_buffer(old, True):
                return False
        if self.write_buf.has_key(piece):
            self.write_buf_list.remove(piece)
        else:
            self.write_buf[piece] = []
        self.write_buf_list.append(piece)
        self.write_buf[piece].append((start, data))
        return True

    def _flush_buffer(self, piece, popped = False):
        if not self.write_buf.has_key(piece):
            return True
        if not popped:
            self.write_buf_list.remove(piece)
        l = self.write_buf[piece]
        del self.write_buf[piece]
        l.sort()
        for start, data in l:
            self.write_buf_size -= len(data)
            if not self.write_raw(self.places[piece], start, data):
                return False
        return True

    def sync(self):
        spots = {}
        for p in self.write_buf_list:
            spots[self.places[p]] = p
        l = spots.keys()
        l.sort()
        for i in l:
            try:
                self._flush_buffer(spots[i])
            except:
                pass
        try:
            self.storage.sync()
        except IOError, e:
            self.failed('IO Error: ' + str(e))
        except OSError, e:
            self.failed('OS Error: ' + str(e))


    def _move_piece(self, index, newpos):
        oldpos = self.places[index]
        if DEBUG:
            print 'moving '+str(index)+' from '+str(oldpos)+' to '+str(newpos)
        assert oldpos != index
        assert oldpos != newpos
        assert index == newpos or not self.places.has_key(newpos)
        old = self.read_raw(oldpos, 0, self._piecelen(index))
        if old is None:
            return -1
        if not self.write_raw(newpos, 0, old):
            return -1
        self.places[index] = newpos
        if self.have[index] and (
                self.triple_check or (self.double_check and index == newpos)):
            if self.triple_check:
                old.release()
                old = self.read_raw(newpos, 0, self._piecelen(index), 
                                    flush_first = True)
                if old is None:
                    return -1
            if sha(old[:]).digest() != self.hashes[index]:
                self.failed('download corrupted; please restart and resume')
                return -1
        old.release()

        if self.blocked[index]:
            self.blocked_moveout.remove(index)
            if self.blocked[newpos]:
                self.blocked_movein.remove(index)
            else:
                self.blocked_movein.add(index)
        else:
            self.blocked_movein.remove(index)
            if self.blocked[newpos]:
                self.blocked_moveout.add(index)
            else:
                self.blocked_moveout.remove(index)
                    
        return oldpos
            
    def _clear_space(self, index):
        h = self.holes.pop(0)
        n = h
        if self.blocked[n]: # assume not self.blocked[index]
            if not self.blocked_movein:
                self.blocked_holes.append(n)
                return True    # repeat
            if not self.places.has_key(n):
                b = self.blocked_movein.pop(0)
                oldpos = self._move_piece(b, n)
                if oldpos < 0:
                    return False
                n = oldpos
        if self.places.has_key(n):
            oldpos = self._move_piece(n, n)
            if oldpos < 0:
                return False
            n = oldpos
        if index == n or index in self.holes:
            if n == h:
                self.write_raw(n, 0, self.alloc_buf[:self._piecelen(n)])
            self.places[index] = n
            if self.blocked[n]:
                # because n may be a spot cleared 10 lines above, it's possible
                # for it to be blocked.  While that spot could be left cleared
                # and a new spot allocated, this condition might occur several
                # times in a row, resulting in a significant amount of disk I/O,
                # delaying the operation of the engine.  Rather than do this,
                # queue the piece to be moved out again, which will be performed
                # by the background allocator, with which data movement is
                # automatically limited.
                self.blocked_moveout.add(index)
            return False
        for p, v in self.places.items():
            if v == index:
                break
        else:
            self.failed('download corrupted; please restart and resume')
            return False
        self._move_piece(p, n)
        self.places[index] = index
        return False


    def piece_came_in(self, index, begin, piece, source = None):
        assert not self.have[index]
        
        if not self.places.has_key(index):
            while self._clear_space(index):
                pass
            if DEBUG:
                print 'new place for '+str(index)+' at '+str(self.places[index])
        if self.flag.isSet():
            return

        if self.failed_pieces.has_key(index):
            old = self.read_raw(self.places[index], begin, len(piece))
            if old is None:
                return True
            if old[:].tostring() != piece:
                try:
                    self.failed_pieces[index][self.download_history[index][begin]] = 1
                except:
                    self.failed_pieces[index][None] = 1
            old.release()
        self.download_history.setdefault(index, {})[begin] = source
        
        if not self._write_to_buffer(index, begin, piece):
            return True
        
        self.amount_obtained += len(piece)
        self.dirty.setdefault(index, []).append((begin, len(piece)))
        self.numactive[index] -= 1
        assert self.numactive[index] >= 0
        if not self.numactive[index]:
            del self.stat_active[index]
        if self.stat_new.has_key(index):
            del self.stat_new[index]

        if self.inactive_requests[index] or self.numactive[index]:
            return True
        
        del self.dirty[index]
        if not self._flush_buffer(index):
            return True
        length = self._piecelen(index)
        data = self.read_raw(self.places[index], 0, length, 
                                 flush_first = self.triple_check)
        if data is None:
            return True
        hash = sha(data[:]).digest()
        data.release()
        if hash != self.hashes[index]:

            self.amount_obtained -= length
            self.data_flunked(length, index)
            self.inactive_requests[index] = 1
            self.amount_inactive += length
            self.stat_numflunked += 1

            self.failed_pieces[index] = {}
            allsenders = {}
            for d in self.download_history[index].values():
                allsenders[d] = 1
            if len(allsenders) == 1:
                culprit = allsenders.keys()[0]
                if culprit is not None:
                    culprit.failed(index, bump = True)
                del self.failed_pieces[index] # found the culprit already
            
            return False

        self.have[index] = True
        self.inactive_requests[index] = None
        self.waschecked[index] = True
        self.amount_left -= length
        self.stat_numdownloaded += 1

        for d in self.download_history[index].values():
            if d is not None:
                d.good(index)
        del self.download_history[index]
        if self.failed_pieces.has_key(index):
            for d in self.failed_pieces[index].keys():
                if d is not None:
                    d.failed(index)
            del self.failed_pieces[index]

        if self.amount_left == 0:
            self.finished()
        return True


    def request_lost(self, index, begin, length):
        assert not (begin, length) in self.inactive_requests[index]
        insort(self.inactive_requests[index], (begin, length))
        self.amount_inactive += length
        self.numactive[index] -= 1
        if not self.numactive[index]:
            del self.stat_active[index]
            if self.stat_new.has_key(index):
                del self.stat_new[index]


    def get_piece(self, index, begin, length):
        if not self.have[index]:
            return None
        data = None
        if not self.waschecked[index]:
            data = self.read_raw(self.places[index], 0, self._piecelen(index))
            if data is None:
                return None
            if sha(data[:]).digest() != self.hashes[index]:
                self.failed('told file complete on start-up, but piece failed hash check')
                return None
            self.waschecked[index] = True
            if length == -1 and begin == 0:
                return data     # optimization
        if length == -1:
            if begin > self._piecelen(index):
                return None
            length = self._piecelen(index)-begin
            if begin == 0:
                return self.read_raw(self.places[index], 0, length)
        elif begin + length > self._piecelen(index):
            return None
        if data is not None:
            s = data[begin:begin+length]
            data.release()
            return s
        data = self.read_raw(self.places[index], begin, length)
        if data is None:
            return None
        s = data.getarray()
        data.release()
        return s

    def read_raw(self, piece, begin, length, flush_first = False):
        try:
            return self.storage.read(self.piece_size * piece + begin, 
                                                     length, flush_first)
        except IOError, e:
            self.failed('IO Error: ' + str(e))
            return None


    def set_file_readonly(self, n):
        try:
            self.storage.set_readonly(n)
        except IOError, e:
            self.failed('IO Error: ' + str(e))
        except OSError, e:
            self.failed('OS Error: ' + str(e))


    def has_data(self, index):
        return index not in self.holes and index not in self.blocked_holes

    def doublecheck_data(self, pieces_to_check):
        if not self.double_check:
            return
        sources = []
        for p, v in self.places.items():
            if pieces_to_check.has_key(v):
                sources.append(p)
        assert len(sources) == len(pieces_to_check)
        sources.sort()
        for index in sources:
            if self.have[index]:
                piece = self.read_raw(self.places[index], 0, self._piecelen(index), 
                                       flush_first = True)
                if piece is None:
                    return False
                if sha(piece[:]).digest() != self.hashes[index]:
                    self.failed('download corrupted; please restart and resume')
                    return False
                piece.release()
        return True


    def reblock(self, new_blocked):
        # assume downloads have already been canceled and chunks made inactive
        for i in xrange(len(new_blocked)):
            if new_blocked[i] and not self.blocked[i]:
                length = self._piecelen(i)
                self.amount_desired -= length
                if self.have[i]:
                    self.amount_obtained -= length
                    continue
                if self.inactive_requests[i] == 1:
                    self.amount_inactive -= length
                    continue
                inactive = 0
                for nb, nl in self.inactive_requests[i]:
                    inactive += nl
                self.amount_inactive -= inactive
                self.amount_obtained -= length - inactive
                
            if self.blocked[i] and not new_blocked[i]:
                length = self._piecelen(i)
                self.amount_desired += length
                if self.have[i]:
                    self.amount_obtained += length
                    continue
                if self.inactive_requests[i] == 1:
                    self.amount_inactive += length
                    continue
                inactive = 0
                for nb, nl in self.inactive_requests[i]:
                    inactive += nl
                self.amount_inactive += inactive
                self.amount_obtained += length - inactive

        self.blocked = new_blocked

        self.blocked_movein = Olist()
        self.blocked_moveout = Olist()
        for p, v in self.places.items():
            if p != v:
                if self.blocked[p] and not self.blocked[v]:
                    self.blocked_movein.add(p)
                elif self.blocked[v] and not self.blocked[p]:
                    self.blocked_moveout.add(p)

        self.holes.extend(self.blocked_holes)    # reset holes list
        self.holes.sort()
        self.blocked_holes = []


    '''
    Pickled data format:

    d['pieces'] = either a string containing a bitfield of complete pieces,
                    or the numeric value "1" signifying a seed.  If it is
                    a seed, d['places'] and d['partials'] should be empty
                    and needn't even exist.
    d['partials'] = [ piece, [ offset, length... ]... ]
                    a list of partial data that had been previously
                    downloaded, plus the given offsets.  Adjacent partials
                    are merged so as to save space, and so that if the
                    request size changes then new requests can be
                    calculated more efficiently.
    d['places'] = [ piece, place, {,piece, place ...} ]
                    the piece index, and the place it's stored.
                    If d['pieces'] specifies a complete piece or d['partials']
                    specifies a set of partials for a piece which has no
                    entry in d['places'], it can be assumed that
                    place[index] = index.  A place specified with no
                    corresponding data in d['pieces'] or d['partials']
                    indicates allocated space with no valid data, and is
                    reserved so it doesn't need to be hash-checked.
    '''
    def pickle(self):
        if self.have.complete():
            return {'pieces': 1}
        pieces = Bitfield(len(self.hashes))
        places = []
        partials = []
        for p in xrange(len(self.hashes)):
            if self.blocked[p] or not self.places.has_key(p):
                continue
            h = self.have[p]
            pieces[p] = h
            pp = self.dirty.get(p)
            if not h and not pp:  # no data
                places.extend([self.places[p], self.places[p]])
            elif self.places[p] != p:
                places.extend([p, self.places[p]])
            if h or not pp:
                continue
            pp.sort()
            r = []
            while len(pp) > 1:
                if pp[0][0]+pp[0][1] == pp[1][0]:
                    pp[0] = list(pp[0])
                    pp[0][1] += pp[1][1]
                    del pp[1]
                else:
                    r.extend(pp[0])
                    del pp[0]
            r.extend(pp[0])
            partials.extend([p, r])
        return {'pieces': pieces.tostring(), 'places': places, 'partials': partials}


    def unpickle(self, data, valid_places):
        got = {}
        places = {}
        dirty = {}
        download_history = {}
        stat_active = {}
        stat_numfound = self.stat_numfound
        amount_obtained = self.amount_obtained
        amount_inactive = self.amount_inactive
        amount_left = self.amount_left
        inactive_requests = [x for x in self.inactive_requests]
        restored_partials = []

        try:
            if data['pieces'] == 1:     # a seed
                assert not data.get('places', None)
                assert not data.get('partials', None)
                have = Bitfield(len(self.hashes))
                for i in xrange(len(self.hashes)):
                    have[i] = True
                assert have.complete()
                _places = []
                _partials = []
            else:
                have = Bitfield(len(self.hashes), data['pieces'])
                _places = data['places']
                assert len(_places) % 2 == 0
                _places = [_places[x:x+2] for x in xrange(0, len(_places), 2)]
                _partials = data['partials']
                assert len(_partials) % 2 == 0
                _partials = [_partials[x:x+2] for x in xrange(0, len(_partials), 2)]
                
            for index, place in _places:
                if place not in valid_places:
                    continue
                assert not got.has_key(index)
                assert not got.has_key(place)
                places[index] = place
                got[index] = 1
                got[place] = 1

            for index in xrange(len(self.hashes)):
                if have[index]:
                    if not places.has_key(index):
                        if index not in valid_places:
                            have[index] = False
                            continue
                        assert not got.has_key(index)
                        places[index] = index
                        got[index] = 1
                    length = self._piecelen(index)
                    amount_obtained += length
                    stat_numfound += 1
                    amount_inactive -= length
                    amount_left -= length
                    inactive_requests[index] = None

            for index, plist in _partials:
                assert not dirty.has_key(index)
                assert not have[index]
                if not places.has_key(index):
                    if index not in valid_places:
                        continue
                    assert not got.has_key(index)
                    places[index] = index
                    got[index] = 1
                assert len(plist) % 2 == 0
                plist = [plist[x:x+2] for x in xrange(0, len(plist), 2)]
                dirty[index] = plist
                stat_active[index] = 1
                download_history[index] = {}
                # invert given partials
                length = self._piecelen(index)
                l = []
                if plist[0][0] > 0:
                    l.append((0, plist[0][0]))
                for i in xrange(len(plist)-1):
                    end = plist[i][0]+plist[i][1]
                    assert not end > plist[i+1][0]
                    l.append((end, plist[i+1][0]-end))
                end = plist[-1][0]+plist[-1][1]
                assert not end > length
                if end < length:
                    l.append((end, length-end))
                # split them to request_size
                ll = []
                amount_obtained += length
                amount_inactive -= length
                for nb, nl in l:
                    while nl > 0:
                        r = min(nl, self.request_size)
                        ll.append((nb, r))
                        amount_inactive += r
                        amount_obtained -= r
                        nb += self.request_size
                        nl -= self.request_size
                inactive_requests[index] = ll
                restored_partials.append(index)

            assert amount_obtained + amount_inactive == self.amount_desired
        except:
#            print_exc()
            return []   # invalid data, discard everything

        self.have = have
        self.places = places
        self.dirty = dirty
        self.download_history = download_history
        self.stat_active = stat_active
        self.stat_numfound = stat_numfound
        self.amount_obtained = amount_obtained
        self.amount_inactive = amount_inactive
        self.amount_left = amount_left
        self.inactive_requests = inactive_requests
                
        return restored_partials
    

########NEW FILE########
__FILENAME__ = StreamCheck
# Written by Bram Cohen
# see LICENSE.txt for license information

from cStringIO import StringIO
from binascii import b2a_hex
from urllib import quote
import Connecter
try:
    True
except:
    True = 1
    False = 0

DEBUG = False


protocol_name = 'BitTorrent protocol'
option_pattern = chr(0)*8

def toint(s):
    return long(b2a_hex(s), 16)

def tohex(s):
    return b2a_hex(s).upper()

def make_readable(s):
    if not s:
        return ''
    if quote(s).find('%') >= 0:
        return tohex(s)
    return '"'+s+'"'

# header, reserved, download id, my id, [length, message]

streamno = 0


class StreamCheck:
    def __init__(self):
        global streamno
        self.no = streamno
        streamno += 1
        self.buffer = StringIO()
        self.next_len, self.next_func = 1, self.read_header_len

    def read_header_len(self, s):
        if ord(s) != len(protocol_name):
            print self.no, 'BAD HEADER LENGTH'
        return len(protocol_name), self.read_header

    def read_header(self, s):
        if s != protocol_name:
            print self.no, 'BAD HEADER'
        return 8, self.read_reserved

    def read_reserved(self, s):
        return 20, self.read_download_id

    def read_download_id(self, s):
        if DEBUG:
            print self.no, 'download ID ' + tohex(s)
        return 20, self.read_peer_id

    def read_peer_id(self, s):
        if DEBUG:
            print self.no, 'peer ID' + make_readable(s)
        return 4, self.read_len

    def read_len(self, s):
        l = toint(s)
        if l > 2 ** 23:
            print self.no, 'BAD LENGTH: '+str(l)+' ('+s+')'
        return l, self.read_message

    def read_message(self, s):
        if not s:
            return 4, self.read_len
        m = s[0]
        if ord(m) > 8:
            print self.no, 'BAD MESSAGE: '+str(ord(m))
        if m == Connecter.REQUEST:
            if len(s) != 13:
                print self.no, 'BAD REQUEST SIZE: '+str(len(s))
                return 4, self.read_len
            index = toint(s[1:5])
            begin = toint(s[5:9])
            length = toint(s[9:])
            print self.no, 'Request: '+str(index)+': '+str(begin)+'-'+str(begin)+'+'+str(length)
        elif m == Connecter.CANCEL:
            if len(s) != 13:
                print self.no, 'BAD CANCEL SIZE: '+str(len(s))
                return 4, self.read_len
            index = toint(s[1:5])
            begin = toint(s[5:9])
            length = toint(s[9:])
            print self.no, 'Cancel: '+str(index)+': '+str(begin)+'-'+str(begin)+'+'+str(length)
        elif m == Connecter.PIECE:
            index = toint(s[1:5])
            begin = toint(s[5:9])
            length = len(s)-9
            print self.no, 'Piece: '+str(index)+': '+str(begin)+'-'+str(begin)+'+'+str(length)
        else:
            print self.no, 'Message '+str(ord(m))+' (length '+str(len(s))+')'
        return 4, self.read_len

    def write(self, s):
        while 1:
            i = self.next_len - self.buffer.tell()
            if i > len(s):
                self.buffer.write(s)
                return
            self.buffer.write(s[:i])
            s = s[i:]
            m = self.buffer.getvalue()
            self.buffer.reset()
            self.buffer.truncate()
            x = self.next_func(m)
            self.next_len, self.next_func = x

########NEW FILE########
__FILENAME__ = T2T
# Written by John Hoffman
# see LICENSE.txt for license information

from Rerequester import Rerequester
from urllib import quote
from threading import Event
from random import randrange
import sys
import __init__
try:
    True
except:
    True = 1
    False = 0

DEBUG = True


def excfunc(x):
    print x

class T2TConnection:
    def __init__(self, myid, tracker, hash, interval, peers, timeout,
                     rawserver, disallow, isdisallowed):
        self.tracker = tracker
        self.interval = interval
        self.hash = hash
        self.operatinginterval = interval
        self.peers = peers
        self.rawserver = rawserver
        self.disallow = disallow
        self.isdisallowed = isdisallowed
        self.active = True
        self.busy = False
        self.errors = 0
        self.rejected = 0
        self.trackererror = False
        self.peerlists = []

        self.rerequester = Rerequester([[tracker]], interval,
            rawserver.add_task, lambda: 0, peers, self.addtolist, 
            rawserver.add_task, lambda: 1, 0, 0, 0, '',
            myid, hash, timeout, self.errorfunc, excfunc, peers, Event(),
            lambda: 0, lambda: 0)

        if self.isactive():
            rawserver.add_task(self.refresh, randrange(int(self.interval/10), self.interval))
                                        # stagger announces

    def isactive(self):
        if self.isdisallowed(self.tracker):    # whoops!
            self.deactivate()
        return self.active
            
    def deactivate(self):
        self.active = False

    def refresh(self):
        if not self.isactive():
            return
        self.lastsuccessful = True
        self.newpeerdata = []
        if DEBUG:
            print 'contacting %s for info_hash=%s' % (self.tracker, quote(self.hash))
        self.rerequester.snoop(self.peers, self.callback)

    def callback(self):
        self.busy = False
        if self.lastsuccessful:
            self.errors = 0
            self.rejected = 0
            if self.rerequester.announce_interval > (3*self.interval):
                # I think I'm stripping from a regular tracker; boost the number of peers requested
                self.peers = int(self.peers * (self.rerequester.announce_interval / self.interval))
            self.operatinginterval = self.rerequester.announce_interval
            if DEBUG:
                print ("%s with info_hash=%s returned %d peers" %
                        (self.tracker, quote(self.hash), len(self.newpeerdata)))
            self.peerlists.append(self.newpeerdata)
            self.peerlists = self.peerlists[-10:]  # keep up to the last 10 announces
        if self.isactive():
            self.rawserver.add_task(self.refresh, self.operatinginterval)

    def addtolist(self, peers):
        for peer in peers:
            self.newpeerdata.append((peer[1],peer[0][0],peer[0][1]))
        
    def errorfunc(self, r):
        self.lastsuccessful = False
        if DEBUG:
            print "%s with info_hash=%s gives error: '%s'" % (self.tracker, quote(self.hash), r)
        if r == self.rerequester.rejectedmessage + 'disallowed':   # whoops!
            if DEBUG:
                print ' -- disallowed - deactivating'
            self.deactivate()
            self.disallow(self.tracker)   # signal other torrents on this tracker
            return
        if r[:8].lower() == 'rejected': # tracker rejected this particular torrent
            self.rejected += 1
            if self.rejected == 3:     # rejected 3 times
                if DEBUG:
                    print ' -- rejected 3 times - deactivating'
                self.deactivate()
            return
        self.errors += 1
        if self.errors >= 3:                         # three or more errors in a row
            self.operatinginterval += self.interval  # lengthen the interval
            if DEBUG:
                print ' -- lengthening interval to '+str(self.operatinginterval)+' seconds'

    def harvest(self):
        x = []
        for list in self.peerlists:
            x += list
        self.peerlists = []
        return x


class T2TList:
    def __init__(self, enabled, trackerid, interval, maxpeers, timeout, rawserver):
        self.enabled = enabled
        self.trackerid = trackerid
        self.interval = interval
        self.maxpeers = maxpeers
        self.timeout = timeout
        self.rawserver = rawserver
        self.list = {}
        self.torrents = {}
        self.disallowed = {}
        self.oldtorrents = []

    def parse(self, allowed_list):
        if not self.enabled:
            return

        # step 1:  Create a new list with all tracker/torrent combinations in allowed_dir        
        newlist = {}
        for hash, data in allowed_list.items():
            if data.has_key('announce-list'):
                for tier in data['announce-list']:
                    for tracker in tier:
                        self.disallowed.setdefault(tracker, False)
                        newlist.setdefault(tracker, {})
                        newlist[tracker][hash] = None # placeholder
                            
        # step 2:  Go through and copy old data to the new list.
        # if the new list has no place for it, then it's old, so deactivate it
        for tracker, hashdata in self.list.items():
            for hash, t2t in hashdata.items():
                if not newlist.has_key(tracker) or not newlist[tracker].has_key(hash):
                    t2t.deactivate()                # this connection is no longer current
                    self.oldtorrents += [t2t]
                        # keep it referenced in case a thread comes along and tries to access.
                else:
                    newlist[tracker][hash] = t2t
            if not newlist.has_key(tracker):
                self.disallowed[tracker] = False    # reset when no torrents on it left

        self.list = newlist
        newtorrents = {}

        # step 3:  If there are any entries that haven't been initialized yet, do so.
        # At the same time, copy all entries onto the by-torrent list.
        for tracker, hashdata in newlist.items():
            for hash, t2t in hashdata.items():
                if t2t is None:
                    hashdata[hash] = T2TConnection(self.trackerid, tracker, hash,
                                        self.interval, self.maxpeers, self.timeout,
                                        self.rawserver, self._disallow, self._isdisallowed)
                newtorrents.setdefault(hash,[])
                newtorrents[hash] += [hashdata[hash]]
                
        self.torrents = newtorrents

        # structures:
        # list = {tracker: {hash: T2TConnection, ...}, ...}
        # torrents = {hash: [T2TConnection, ...]}
        # disallowed = {tracker: flag, ...}
        # oldtorrents = [T2TConnection, ...]

    def _disallow(self,tracker):
        self.disallowed[tracker] = True

    def _isdisallowed(self,tracker):
        return self.disallowed[tracker]

    def harvest(self,hash):
        harvest = []
        if self.enabled:
            for t2t in self.torrents[hash]:
                harvest += t2t.harvest()
        return harvest

########NEW FILE########
__FILENAME__ = track
# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.parseargs import parseargs, formatDefinitions
from BitTornado.RawServer import RawServer, autodetect_socket_style
from BitTornado.HTTPHandler import HTTPHandler, months
from BitTornado.parsedir import parsedir
from NatCheck import NatCheck
from T2T import T2TList
from BitTornado.subnetparse import IP_List, ipv6_to_ipv4, to_ipv4, is_valid_ip, is_ipv4
from BitTornado.iprangeparse import IP_List as IP_Range_List
from BitTornado.torrentlistparse import parsetorrentlist
from threading import Event, Thread
from BitTornado.bencode import bencode, bdecode, Bencached
from BitTornado.zurllib import urlopen
from urllib import quote, unquote
from Filter import Filter
from urlparse import urlparse
from os.path import exists
from cStringIO import StringIO
from traceback import print_exc
from time import time, gmtime, strftime, localtime
from BitTornado.clock import clock
from random import shuffle, seed
from types import StringType, IntType, LongType, DictType
from binascii import b2a_hex
import sys, os
import signal
import re
from BitTornado.__init__ import version, createPeerID
try:
    True
except:
    True = 1
    False = 0

defaults = [
    ('port', 80, "Port to listen on."),
    ('dfile', None, 'file to store recent downloader info in'),
    ('bind', '', 'comma-separated list of ips/hostnames to bind to locally'),
#    ('ipv6_enabled', autodetect_ipv6(),
    ('ipv6_enabled', 0,
         'allow the client to connect to peers via IPv6'),
    ('ipv6_binds_v4', autodetect_socket_style(),
        'set if an IPv6 server socket will also field IPv4 connections'),
    ('socket_timeout', 15, 'timeout for closing connections'),
    ('save_dfile_interval', 5 * 60, 'seconds between saving dfile'),
    ('timeout_downloaders_interval', 45 * 60, 'seconds between expiring downloaders'),
    ('reannounce_interval', 30 * 60, 'seconds downloaders should wait between reannouncements'),
    ('response_size', 50, 'number of peers to send in an info message'),
    ('timeout_check_interval', 5,
        'time to wait between checking if any connections have timed out'),
    ('nat_check', 3,
        "how many times to check if a downloader is behind a NAT (0 = don't check)"),
    ('log_nat_checks', 0,
        "whether to add entries to the log for nat-check results"),
    ('min_time_between_log_flushes', 3.0,
        'minimum time it must have been since the last flush to do another one'),
    ('min_time_between_cache_refreshes', 600.0,
        'minimum time in seconds before a cache is considered stale and is flushed'),
    ('allowed_dir', '', 'only allow downloads for .torrents in this dir'),
    ('allowed_list', '', 'only allow downloads for hashes in this list (hex format, one per line)'),
    ('allowed_controls', 0, 'allow special keys in torrents in the allowed_dir to affect tracker access'),
    ('multitracker_enabled', 0, 'whether to enable multitracker operation'),
    ('multitracker_allowed', 'autodetect', 'whether to allow incoming tracker announces (can be none, autodetect or all)'),
    ('multitracker_reannounce_interval', 2 * 60, 'seconds between outgoing tracker announces'),
    ('multitracker_maxpeers', 20, 'number of peers to get in a tracker announce'),
    ('aggregate_forward', '', 'format: <url>[,<password>] - if set, forwards all non-multitracker to this url with this optional password'),
    ('aggregator', '0', 'whether to act as a data aggregator rather than a tracker.  If enabled, may be 1, or <password>; ' +
             'if password is set, then an incoming password is required for access'),
    ('hupmonitor', 0, 'whether to reopen the log file upon receipt of HUP signal'),
    ('http_timeout', 60, 
        'number of seconds to wait before assuming that an http connection has timed out'),
    ('parse_dir_interval', 60, 'seconds between reloading of allowed_dir or allowed_file ' +
             'and allowed_ips and banned_ips lists'),
    ('show_infopage', 1, "whether to display an info page when the tracker's root dir is loaded"),
    ('infopage_redirect', '', 'a URL to redirect the info page to'),
    ('show_names', 1, 'whether to display names from allowed dir'),
    ('favicon', '', 'file containing x-icon data to return when browser requests favicon.ico'),
    ('allowed_ips', '', 'only allow connections from IPs specified in the given file; '+
             'file contains subnet data in the format: aa.bb.cc.dd/len'),
    ('banned_ips', '', "don't allow connections from IPs specified in the given file; "+
             'file contains IP range data in the format: xxx:xxx:ip1-ip2'),
    ('only_local_override_ip', 2, "ignore the ip GET parameter from machines which aren't on local network IPs " +
             "(0 = never, 1 = always, 2 = ignore if NAT checking is not enabled)"),
    ('logfile', '', 'file to write the tracker logs, use - for stdout (default)'),
    ('allow_get', 0, 'use with allowed_dir; adds a /file?hash={hash} url that allows users to download the torrent file'),
    ('keep_dead', 0, 'keep dead torrents after they expire (so they still show up on your /scrape and web page)'),
    ('scrape_allowed', 'full', 'scrape access allowed (can be none, specific or full)')
  ]

def statefiletemplate(x):
    if type(x) != DictType:
        raise ValueError
    for cname, cinfo in x.items():
        if cname == 'peers':
            for y in cinfo.values():      # The 'peers' key is a dictionary of SHA hashes (torrent ids)
                if type(y) != DictType:   # ... for the active torrents, and each is a dictionary
                    raise ValueError
                for id, info in y.items(): # ... of client ids interested in that torrent
                    if (len(id) != 20):
                        raise ValueError
                    if type(info) != DictType:  # ... each of which is also a dictionary
                        raise ValueError # ... which has an IP, a Port, and a Bytes Left count for that client for that torrent
                    if type(info.get('ip', '')) != StringType:
                        raise ValueError
                    port = info.get('port')
                    if type(port) not in (IntType,LongType) or port < 0:
                        raise ValueError
                    left = info.get('left')
                    if type(left) not in (IntType,LongType) or left < 0:
                        raise ValueError
        elif cname == 'completed':
            if (type(cinfo) != DictType): # The 'completed' key is a dictionary of SHA hashes (torrent ids)
                raise ValueError          # ... for keeping track of the total completions per torrent
            for y in cinfo.values():      # ... each torrent has an integer value
                if type(y) not in (IntType,LongType):
                    raise ValueError      # ... for the number of reported completions for that torrent
        elif cname == 'allowed':
            if (type(cinfo) != DictType): # a list of info_hashes and included data
                raise ValueError
            if x.has_key('allowed_dir_files'):
                adlist = [z[1] for z in x['allowed_dir_files'].values()]
                for y in cinfo.keys():        # and each should have a corresponding key here
                    if not y in adlist:
                        raise ValueError
        elif cname == 'allowed_dir_files':
            if (type(cinfo) != DictType): # a list of files, their attributes and info hashes
                raise ValueError
            dirkeys = {}
            for y in cinfo.values():      # each entry should have a corresponding info_hash
                if not y[1]:
                    continue
                if not x['allowed'].has_key(y[1]):
                    raise ValueError
                if dirkeys.has_key(y[1]): # and each should have a unique info_hash
                    raise ValueError
                dirkeys[y[1]] = 1
            

alas = 'your file may exist elsewhere in the universe\nbut alas, not here\n'

local_IPs = IP_List()
local_IPs.set_intranet_addresses()


def isotime(secs = None):
    if secs == None:
        secs = time()
    return strftime('%Y-%m-%d %H:%M UTC', gmtime(secs))

http_via_filter = re.compile(' for ([0-9.]+)\Z')

def _get_forwarded_ip(headers):
    if headers.has_key('http_x_forwarded_for'):
        header = headers['http_x_forwarded_for']
        try:
            x,y = header.split(',')
        except:
            return header
        if not local_IPs.includes(x):
            return x
        return y
    if headers.has_key('http_client_ip'):
        return headers['http_client_ip']
    if headers.has_key('http_via'):
        x = http_via_filter.search(headers['http_via'])
        try:
            return x.group(1)
        except:
            pass
    if headers.has_key('http_from'):
        return headers['http_from']
    return None

def get_forwarded_ip(headers):
    x = _get_forwarded_ip(headers)
    if not is_valid_ip(x) or local_IPs.includes(x):
        return None
    return x

def compact_peer_info(ip, port):
    try:
        s = ( ''.join([chr(int(i)) for i in ip.split('.')])
              + chr((port & 0xFF00) >> 8) + chr(port & 0xFF) )
        if len(s) != 6:
            raise ValueError
    except:
        s = ''  # not a valid IP, must be a domain name
    return s

class Tracker:
    def __init__(self, config, rawserver):
        self.config = config
        self.response_size = config['response_size']
        self.dfile = config['dfile']
        self.natcheck = config['nat_check']
        favicon = config['favicon']
        self.parse_dir_interval = config['parse_dir_interval']
        self.favicon = None
        if favicon:
            try:
                h = open(favicon,'r')
                self.favicon = h.read()
                h.close()
            except:
                print "**warning** specified favicon file -- %s -- does not exist." % favicon
        self.rawserver = rawserver
        self.cached = {}    # format: infohash: [[time1, l1, s1], [time2, l2, s2], [time3, l3, s3]]
        self.cached_t = {}  # format: infohash: [time, cache]
        self.times = {}
        self.state = {}
        self.seedcount = {}

        self.allowed_IPs = None
        self.banned_IPs = None
        if config['allowed_ips'] or config['banned_ips']:
            self.allowed_ip_mtime = 0
            self.banned_ip_mtime = 0
            self.read_ip_lists()
                
        self.only_local_override_ip = config['only_local_override_ip']
        if self.only_local_override_ip == 2:
            self.only_local_override_ip = not config['nat_check']

        if exists(self.dfile):
            try:
                h = open(self.dfile, 'rb')
                ds = h.read()
                h.close()
                tempstate = bdecode(ds)
                if not tempstate.has_key('peers'):
                    tempstate = {'peers': tempstate}
                statefiletemplate(tempstate)
                self.state = tempstate
            except:
                print '**warning** statefile '+self.dfile+' corrupt; resetting'
        self.downloads = self.state.setdefault('peers', {})
        self.completed = self.state.setdefault('completed', {})

        self.becache = {}   # format: infohash: [[l1, s1], [l2, s2], [l3, s3]]
        for infohash, ds in self.downloads.items():
            self.seedcount[infohash] = 0
            for x,y in ds.items():
                ip = y['ip']
                if ( (self.allowed_IPs and not self.allowed_IPs.includes(ip))
                     or (self.banned_IPs and self.banned_IPs.includes(ip)) ):
                    del ds[x]
                    continue
                if not y['left']:
                    self.seedcount[infohash] += 1
                if y.get('nat',-1):
                    continue
                gip = y.get('given_ip')
                if is_valid_ip(gip) and (
                    not self.only_local_override_ip or local_IPs.includes(ip) ):
                    ip = gip
                self.natcheckOK(infohash,x,ip,y['port'],y['left'])
            
        for x in self.downloads.keys():
            self.times[x] = {}
            for y in self.downloads[x].keys():
                self.times[x][y] = 0

        self.trackerid = createPeerID('-T-')
        seed(self.trackerid)
                
        self.reannounce_interval = config['reannounce_interval']
        self.save_dfile_interval = config['save_dfile_interval']
        self.show_names = config['show_names']
        rawserver.add_task(self.save_state, self.save_dfile_interval)
        self.prevtime = clock()
        self.timeout_downloaders_interval = config['timeout_downloaders_interval']
        rawserver.add_task(self.expire_downloaders, self.timeout_downloaders_interval)
        self.logfile = None
        self.log = None
        if (config['logfile']) and (config['logfile'] != '-'):
            try:
                self.logfile = config['logfile']
                self.log = open(self.logfile,'a')
                sys.stdout = self.log
                print "# Log Started: ", isotime()
            except:
                print "**warning** could not redirect stdout to log file: ", sys.exc_info()[0]

        if config['hupmonitor']:
            def huphandler(signum, frame, self = self):
                try:
                    self.log.close()
                    self.log = open(self.logfile,'a')
                    sys.stdout = self.log
                    print "# Log reopened: ", isotime()
                except:
                    print "**warning** could not reopen logfile"
             
            signal.signal(signal.SIGHUP, huphandler)            
                
        self.allow_get = config['allow_get']
        
        self.t2tlist = T2TList(config['multitracker_enabled'], self.trackerid,
                               config['multitracker_reannounce_interval'],
                               config['multitracker_maxpeers'], config['http_timeout'],
                               self.rawserver)

        if config['allowed_list']:
            if config['allowed_dir']:
                print '**warning** allowed_dir and allowed_list options cannot be used together'
                print '**warning** disregarding allowed_dir'
                config['allowed_dir'] = ''
            self.allowed = self.state.setdefault('allowed_list',{})
            self.allowed_list_mtime = 0
            self.parse_allowed()
            self.remove_from_state('allowed','allowed_dir_files')
            if config['multitracker_allowed'] == 'autodetect':
                config['multitracker_allowed'] = 'none'
            config['allowed_controls'] = 0

        elif config['allowed_dir']:
            self.allowed = self.state.setdefault('allowed',{})
            self.allowed_dir_files = self.state.setdefault('allowed_dir_files',{})
            self.allowed_dir_blocked = {}
            self.parse_allowed()
            self.remove_from_state('allowed_list')

        else:
            self.allowed = None
            self.remove_from_state('allowed','allowed_dir_files', 'allowed_list')
            if config['multitracker_allowed'] == 'autodetect':
                config['multitracker_allowed'] = 'none'
            config['allowed_controls'] = 0
                
        self.uq_broken = unquote('+') != ' '
        self.keep_dead = config['keep_dead']
        self.Filter = Filter(rawserver.add_task)
        
        aggregator = config['aggregator']
        if aggregator == '0':
            self.is_aggregator = False
            self.aggregator_key = None
        else:
            self.is_aggregator = True
            if aggregator == '1':
                self.aggregator_key = None
            else:
                self.aggregator_key = aggregator
            self.natcheck = False
                
        send = config['aggregate_forward']
        if not send:
            self.aggregate_forward = None
        else:
            try:
                self.aggregate_forward, self.aggregate_password = send.split(',')
            except:
                self.aggregate_forward = send
                self.aggregate_password = None

        self.cachetime = 0
        self.cachetimeupdate()

    def cachetimeupdate(self):
        self.cachetime += 1     # raw clock, but more efficient for cache
        self.rawserver.add_task(self.cachetimeupdate,1)

    def aggregate_senddata(self, query):
        url = self.aggregate_forward+'?'+query
        if self.aggregate_password is not None:
            url += '&password='+self.aggregate_password
        rq = Thread(target = self._aggregate_senddata, args = [url])
        rq.setDaemon(False)
        rq.start()

    def _aggregate_senddata(self, url):     # just send, don't attempt to error check,
        try:                                # discard any returned data
            h = urlopen(url)
            h.read()
            h.close()
        except:
            return


    def get_infopage(self):
        try:
            if not self.config['show_infopage']:
                return (404, 'Not Found', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, alas)
            red = self.config['infopage_redirect']
            if red:
                return (302, 'Found', {'Content-Type': 'text/html', 'Location': red},
                        '<A HREF="'+red+'">Click Here</A>')
            
            s = StringIO()
            s.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n' \
                '<html><head><title>BitTorrent download info</title>\n')
            if self.favicon is not None:
                s.write('<link rel="shortcut icon" href="/favicon.ico">\n')
            s.write('</head>\n<body>\n' \
                '<h3>BitTorrent download info</h3>\n'\
                '<ul>\n'
                '<li><strong>tracker version:</strong> %s</li>\n' \
                '<li><strong>server time:</strong> %s</li>\n' \
                '</ul>\n' % (version, isotime()))
            if self.config['allowed_dir']:
                if self.show_names:
                    names = [ (self.allowed[hash]['name'],hash)
                              for hash in self.allowed.keys() ]
                else:
                    names = [ (None,hash)
                              for hash in self.allowed.keys() ]
            else:
                names = [ (None,hash) for hash in self.downloads.keys() ]
            if not names:
                s.write('<p>not tracking any files yet...</p>\n')
            else:
                names.sort()
                tn = 0
                tc = 0
                td = 0
                tt = 0  # Total transferred
                ts = 0  # Total size
                nf = 0  # Number of files displayed
                if self.config['allowed_dir'] and self.show_names:
                    s.write('<table summary="files" border="1">\n' \
                        '<tr><th>info hash</th><th>torrent name</th><th align="right">size</th><th align="right">complete</th><th align="right">downloading</th><th align="right">downloaded</th><th align="right">transferred</th></tr>\n')
                else:
                    s.write('<table summary="files">\n' \
                        '<tr><th>info hash</th><th align="right">complete</th><th align="right">downloading</th><th align="right">downloaded</th></tr>\n')
                for name,hash in names:
                    l = self.downloads[hash]
                    n = self.completed.get(hash, 0)
                    tn = tn + n
                    c = self.seedcount[hash]
                    tc = tc + c
                    d = len(l) - c
                    td = td + d
                    if self.config['allowed_dir'] and self.show_names:
                        if self.allowed.has_key(hash):
                            nf = nf + 1
                            sz = self.allowed[hash]['length']  # size
                            ts = ts + sz
                            szt = sz * n   # Transferred for this torrent
                            tt = tt + szt
                            if self.allow_get == 1:
                                linkname = '<a href="/file?info_hash=' + quote(hash) + '">' + name + '</a>'
                            else:
                                linkname = name
                            s.write('<tr><td><code>%s</code></td><td>%s</td><td align="right">%s</td><td align="right">%i</td><td align="right">%i</td><td align="right">%i</td><td align="right">%s</td></tr>\n' \
                                % (b2a_hex(hash), linkname, size_format(sz), c, d, n, size_format(szt)))
                    else:
                        s.write('<tr><td><code>%s</code></td><td align="right"><code>%i</code></td><td align="right"><code>%i</code></td><td align="right"><code>%i</code></td></tr>\n' \
                            % (b2a_hex(hash), c, d, n))
                ttn = 0
                for i in self.completed.values():
                    ttn = ttn + i
                if self.config['allowed_dir'] and self.show_names:
                    s.write('<tr><td align="right" colspan="2">%i files</td><td align="right">%s</td><td align="right">%i</td><td align="right">%i</td><td align="right">%i/%i</td><td align="right">%s</td></tr>\n'
                            % (nf, size_format(ts), tc, td, tn, ttn, size_format(tt)))
                else:
                    s.write('<tr><td align="right">%i files</td><td align="right">%i</td><td align="right">%i</td><td align="right">%i/%i</td></tr>\n'
                            % (nf, tc, td, tn, ttn))
                s.write('</table>\n' \
                    '<ul>\n' \
                    '<li><em>info hash:</em> SHA1 hash of the "info" section of the metainfo (*.torrent)</li>\n' \
                    '<li><em>complete:</em> number of connected clients with the complete file</li>\n' \
                    '<li><em>downloading:</em> number of connected clients still downloading</li>\n' \
                    '<li><em>downloaded:</em> reported complete downloads (total: current/all)</li>\n' \
                    '<li><em>transferred:</em> torrent size * total downloaded (does not include partial transfers)</li>\n' \
                    '</ul>\n')

            s.write('</body>\n' \
                '</html>\n')
            return (200, 'OK', {'Content-Type': 'text/html; charset=iso-8859-1'}, s.getvalue())
        except:
            print_exc()
            return (500, 'Internal Server Error', {'Content-Type': 'text/html; charset=iso-8859-1'}, 'Server Error')


    def scrapedata(self, hash, return_name = True):
        l = self.downloads[hash]
        n = self.completed.get(hash, 0)
        c = self.seedcount[hash]
        d = len(l) - c
        f = {'complete': c, 'incomplete': d, 'downloaded': n}
        if return_name and self.show_names and self.config['allowed_dir']:
            f['name'] = self.allowed[hash]['name']
        return (f)

    def get_scrape(self, paramslist):
        fs = {}
        if paramslist.has_key('info_hash'):
            if self.config['scrape_allowed'] not in ['specific', 'full']:
                return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason':
                    'specific scrape function is not available with this tracker.'}))
            for hash in paramslist['info_hash']:
                if self.allowed is not None:
                    if self.allowed.has_key(hash):
                        fs[hash] = self.scrapedata(hash)
                else:
                    if self.downloads.has_key(hash):
                        fs[hash] = self.scrapedata(hash)
        else:
            if self.config['scrape_allowed'] != 'full':
                return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason':
                    'full scrape function is not available with this tracker.'}))
            if self.allowed is not None:
                keys = self.allowed.keys()
            else:
                keys = self.downloads.keys()
            for hash in keys:
                fs[hash] = self.scrapedata(hash)

        return (200, 'OK', {'Content-Type': 'text/plain'}, bencode({'files': fs}))


    def get_file(self, hash):
        if not self.allow_get:
            return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                'get function is not available with this tracker.')
        if not self.allowed.has_key(hash):
            return (404, 'Not Found', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, alas)
        fname = self.allowed[hash]['file']
        fpath = self.allowed[hash]['path']
        return (200, 'OK', {'Content-Type': 'application/x-bittorrent',
            'Content-Disposition': 'attachment; filename=' + fname},
            open(fpath, 'rb').read())


    def check_allowed(self, infohash, paramslist):
        if ( self.aggregator_key is not None
                and not ( paramslist.has_key('password')
                        and paramslist['password'][0] == self.aggregator_key ) ):
            return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                bencode({'failure reason':
                'Requested download is not authorized for use with this tracker.'}))

        if self.allowed is not None:
            if not self.allowed.has_key(infohash):
                return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason':
                    'Requested download is not authorized for use with this tracker.'}))
            if self.config['allowed_controls']:
                if self.allowed[infohash].has_key('failure reason'):
                    return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                        bencode({'failure reason': self.allowed[infohash]['failure reason']}))

        if paramslist.has_key('tracker'):
            if ( self.config['multitracker_allowed'] == 'none' or       # turned off
                          paramslist['peer_id'][0] == self.trackerid ): # oops! contacted myself
                return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason': 'disallowed'}))
            
            if ( self.config['multitracker_allowed'] == 'autodetect'
                        and not self.allowed[infohash].has_key('announce-list') ):
                return (200, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason':
                    'Requested download is not authorized for multitracker use.'}))

        return None


    def add_data(self, infohash, event, ip, paramslist):
        peers = self.downloads.setdefault(infohash, {})
        ts = self.times.setdefault(infohash, {})
        self.completed.setdefault(infohash, 0)
        self.seedcount.setdefault(infohash, 0)

        def params(key, default = None, l = paramslist):
            if l.has_key(key):
                return l[key][0]
            return default
        
        myid = params('peer_id','')
        if len(myid) != 20:
            raise ValueError, 'id not of length 20'
        if event not in ['started', 'completed', 'stopped', 'snooped', None]:
            raise ValueError, 'invalid event'
        port = long(params('port',''))
        if port < 0 or port > 65535:
            raise ValueError, 'invalid port'
        left = long(params('left',''))
        if left < 0:
            raise ValueError, 'invalid amount left'
        uploaded = long(params('uploaded',''))
        downloaded = long(params('downloaded',''))

        peer = peers.get(myid)
        islocal = local_IPs.includes(ip)
        mykey = params('key')
        if peer:
            auth = peer.get('key',-1) == mykey or peer.get('ip') == ip

        gip = params('ip')
        if is_valid_ip(gip) and (islocal or not self.only_local_override_ip):
            ip1 = gip
        else:
            ip1 = ip

        if params('numwant') is not None:
            rsize = min(int(params('numwant')),self.response_size)
        else:
            rsize = self.response_size

        if event == 'stopped':
            if peer:
                if auth:
                    self.delete_peer(infohash,myid)
        
        elif not peer:
            ts[myid] = clock()
            peer = {'ip': ip, 'port': port, 'left': left}
            if mykey:
                peer['key'] = mykey
            if gip:
                peer['given ip'] = gip
            if port:
                if not self.natcheck or islocal:
                    peer['nat'] = 0
                    self.natcheckOK(infohash,myid,ip1,port,left)
                else:
                    NatCheck(self.connectback_result,infohash,myid,ip1,port,self.rawserver)
            else:
                peer['nat'] = 2**30
            if event == 'completed':
                self.completed[infohash] += 1
            if not left:
                self.seedcount[infohash] += 1

            peers[myid] = peer

        else:
            if not auth:
                return rsize    # return w/o changing stats

            ts[myid] = clock()
            if not left and peer['left']:
                self.completed[infohash] += 1
                self.seedcount[infohash] += 1
                if not peer.get('nat', -1):
                    for bc in self.becache[infohash]:
                        bc[1][myid] = bc[0][myid]
                        del bc[0][myid]
            if peer['left']:
                peer['left'] = left

            if port:
                recheck = False
                if ip != peer['ip']:
                    peer['ip'] = ip
                    recheck = True
                if gip != peer.get('given ip'):
                    if gip:
                        peer['given ip'] = gip
                    elif peer.has_key('given ip'):
                        del peer['given ip']
                    recheck = True

                natted = peer.get('nat', -1)
                if recheck:
                    if natted == 0:
                        l = self.becache[infohash]
                        y = not peer['left']
                        for x in l:
                            del x[y][myid]
                        if not self.natcheck or islocal:
                            del peer['nat'] # restart NAT testing
                if natted and natted < self.natcheck:
                    recheck = True

                if recheck:
                    if not self.natcheck or islocal:
                        peer['nat'] = 0
                        self.natcheckOK(infohash,myid,ip1,port,left)
                    else:
                        NatCheck(self.connectback_result,infohash,myid,ip1,port,self.rawserver)

        return rsize


    def peerlist(self, infohash, stopped, tracker, is_seed, return_type, rsize):
        data = {}    # return data
        seeds = self.seedcount[infohash]
        data['complete'] = seeds
        data['incomplete'] = len(self.downloads[infohash]) - seeds
        
        if ( self.config['allowed_controls']
                and self.allowed[infohash].has_key('warning message') ):
            data['warning message'] = self.allowed[infohash]['warning message']

        if tracker:
            data['interval'] = self.config['multitracker_reannounce_interval']
            if not rsize:
                return data
            cache = self.cached_t.setdefault(infohash, None)
            if ( not cache or len(cache[1]) < rsize
                 or cache[0] + self.config['min_time_between_cache_refreshes'] < clock() ):
                bc = self.becache.setdefault(infohash,[[{}, {}], [{}, {}], [{}, {}]])
                cache = [ clock(), bc[0][0].values() + bc[0][1].values() ]
                self.cached_t[infohash] = cache
                shuffle(cache[1])
                cache = cache[1]

            data['peers'] = cache[-rsize:]
            del cache[-rsize:]
            return data

        data['interval'] = self.reannounce_interval
        if stopped or not rsize:     # save some bandwidth
            data['peers'] = []
            return data

        bc = self.becache.setdefault(infohash,[[{}, {}], [{}, {}], [{}, {}]])
        len_l = len(bc[0][0])
        len_s = len(bc[0][1])
        if not (len_l+len_s):   # caches are empty!
            data['peers'] = []
            return data
        l_get_size = int(float(rsize)*(len_l)/(len_l+len_s))
        cache = self.cached.setdefault(infohash,[None,None,None])[return_type]
        if cache and ( not cache[1]
                       or (is_seed and len(cache[1]) < rsize)
                       or len(cache[1]) < l_get_size
                       or cache[0]+self.config['min_time_between_cache_refreshes'] < self.cachetime ):
            cache = None
        if not cache:
            peers = self.downloads[infohash]
            vv = [[],[],[]]
            for key, ip, port in self.t2tlist.harvest(infohash):   # empty if disabled
                if not peers.has_key(key):
                    vv[0].append({'ip': ip, 'port': port, 'peer id': key})
                    vv[1].append({'ip': ip, 'port': port})
                    vv[2].append(compact_peer_info(ip, port))
            cache = [ self.cachetime,
                      bc[return_type][0].values()+vv[return_type],
                      bc[return_type][1].values() ]
            shuffle(cache[1])
            shuffle(cache[2])
            self.cached[infohash][return_type] = cache
            for rr in xrange(len(self.cached[infohash])):
                if rr != return_type:
                    try:
                        self.cached[infohash][rr][1].extend(vv[rr])
                    except:
                        pass
        if len(cache[1]) < l_get_size:
            peerdata = cache[1]
            if not is_seed:
                peerdata.extend(cache[2])
            cache[1] = []
            cache[2] = []
        else:
            if not is_seed:
                peerdata = cache[2][l_get_size-rsize:]
                del cache[2][l_get_size-rsize:]
                rsize -= len(peerdata)
            else:
                peerdata = []
            if rsize:
                peerdata.extend(cache[1][-rsize:])
                del cache[1][-rsize:]
        if return_type == 2:
            peerdata = ''.join(peerdata)
        data['peers'] = peerdata
        return data


    def get(self, connection, path, headers):
        real_ip = connection.get_ip()
        ip = real_ip
        if is_ipv4(ip):
            ipv4 = True
        else:
            try:
                ip = ipv6_to_ipv4(ip)
                ipv4 = True
            except ValueError:
                ipv4 = False

        if ( (self.allowed_IPs and not self.allowed_IPs.includes(ip))
             or (self.banned_IPs and self.banned_IPs.includes(ip)) ):
            return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                bencode({'failure reason':
                'your IP is not allowed on this tracker'}))

        nip = get_forwarded_ip(headers)
        if nip and not self.only_local_override_ip:
            ip = nip
            try:
                ip = to_ipv4(ip)
                ipv4 = True
            except ValueError:
                ipv4 = False

        paramslist = {}
        def params(key, default = None, l = paramslist):
            if l.has_key(key):
                return l[key][0]
            return default

        try:
            (scheme, netloc, path, pars, query, fragment) = urlparse(path)
            if self.uq_broken == 1:
                path = path.replace('+',' ')
                query = query.replace('+',' ')
            path = unquote(path)[1:]
            for s in query.split('&'):
                if s:
                    i = s.index('=')
                    kw = unquote(s[:i])
                    paramslist.setdefault(kw, [])
                    paramslist[kw] += [unquote(s[i+1:])]
                    
            if path == '' or path == 'index.html':
                return self.get_infopage()
            if (path == 'file'):
                return self.get_file(params('info_hash'))
            if path == 'favicon.ico' and self.favicon is not None:
                return (200, 'OK', {'Content-Type' : 'image/x-icon'}, self.favicon)

            # automated access from here on

            if path == 'scrape':
                return self.get_scrape(paramslist)
            
            if path != 'announce':
                return (404, 'Not Found', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, alas)

            # main tracker function

            filtered = self.Filter.check(real_ip, paramslist, headers)
            if filtered:
                return (400, 'Not Authorized', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'failure reason': filtered}))
            
            infohash = params('info_hash')
            if not infohash:
                raise ValueError, 'no info hash'

            notallowed = self.check_allowed(infohash, paramslist)
            if notallowed:
                return notallowed

            event = params('event')

            rsize = self.add_data(infohash, event, ip, paramslist)

        except ValueError, e:
            return (400, 'Bad Request', {'Content-Type': 'text/plain'}, 
                'you sent me garbage - ' + str(e))

        if self.aggregate_forward and not paramslist.has_key('tracker'):
            self.aggregate_senddata(query)

        if self.is_aggregator:      # don't return peer data here
            return (200, 'OK', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'},
                    bencode({'response': 'OK'}))

        if params('compact') and ipv4:
            return_type = 2
        elif params('no_peer_id'):
            return_type = 1
        else:
            return_type = 0
            
        data = self.peerlist(infohash, event=='stopped',
                             params('tracker'), not params('left'),
                             return_type, rsize)

        if paramslist.has_key('scrape'):
            data['scrape'] = self.scrapedata(infohash, False)
            
        return (200, 'OK', {'Content-Type': 'text/plain', 'Pragma': 'no-cache'}, bencode(data))


    def natcheckOK(self, infohash, peerid, ip, port, not_seed):
        bc = self.becache.setdefault(infohash,[[{}, {}], [{}, {}], [{}, {}]])
        bc[0][not not_seed][peerid] = Bencached(bencode({'ip': ip, 'port': port,
                                              'peer id': peerid}))
        bc[1][not not_seed][peerid] = Bencached(bencode({'ip': ip, 'port': port}))
        bc[2][not not_seed][peerid] = compact_peer_info(ip, port)


    def natchecklog(self, peerid, ip, port, result):
        year, month, day, hour, minute, second, a, b, c = localtime(time())
        print '%s - %s [%02d/%3s/%04d:%02d:%02d:%02d] "!natcheck-%s:%i" %i 0 - -' % (
            ip, quote(peerid), day, months[month], year, hour, minute, second,
            ip, port, result)

    def connectback_result(self, result, downloadid, peerid, ip, port):
        record = self.downloads.get(downloadid, {}).get(peerid)
        if ( record is None 
                 or (record['ip'] != ip and record.get('given ip') != ip)
                 or record['port'] != port ):
            if self.config['log_nat_checks']:
                self.natchecklog(peerid, ip, port, 404)
            return
        if self.config['log_nat_checks']:
            if result:
                x = 200
            else:
                x = 503
            self.natchecklog(peerid, ip, port, x)
        if not record.has_key('nat'):
            record['nat'] = int(not result)
            if result:
                self.natcheckOK(downloadid,peerid,ip,port,record['left'])
        elif result and record['nat']:
            record['nat'] = 0
            self.natcheckOK(downloadid,peerid,ip,port,record['left'])
        elif not result:
            record['nat'] += 1


    def remove_from_state(self, *l):
        for s in l:
            try:
                del self.state[s]
            except:
                pass

    def save_state(self):
        self.rawserver.add_task(self.save_state, self.save_dfile_interval)
        h = open(self.dfile, 'wb')
        h.write(bencode(self.state))
        h.close()


    def parse_allowed(self):
        self.rawserver.add_task(self.parse_allowed, self.parse_dir_interval)

        if self.config['allowed_dir']:
            r = parsedir( self.config['allowed_dir'], self.allowed,
                          self.allowed_dir_files, self.allowed_dir_blocked,
                          [".torrent"] )
            ( self.allowed, self.allowed_dir_files, self.allowed_dir_blocked,
                added, garbage2 ) = r
            
            self.state['allowed'] = self.allowed
            self.state['allowed_dir_files'] = self.allowed_dir_files

            self.t2tlist.parse(self.allowed)
            
        else:
            f = self.config['allowed_list']
            if self.allowed_list_mtime == os.path.getmtime(f):
                return
            try:
                r = parsetorrentlist(f, self.allowed)
                (self.allowed, added, garbage2) = r
                self.state['allowed_list'] = self.allowed
            except (IOError, OSError):
                print '**warning** unable to read allowed torrent list'
                return
            self.allowed_list_mtime = os.path.getmtime(f)

        for infohash in added.keys():
            self.downloads.setdefault(infohash, {})
            self.completed.setdefault(infohash, 0)
            self.seedcount.setdefault(infohash, 0)


    def read_ip_lists(self):
        self.rawserver.add_task(self.read_ip_lists,self.parse_dir_interval)
            
        f = self.config['allowed_ips']
        if f and self.allowed_ip_mtime != os.path.getmtime(f):
            self.allowed_IPs = IP_List()
            try:
                self.allowed_IPs.read_fieldlist(f)
                self.allowed_ip_mtime = os.path.getmtime(f)
            except (IOError, OSError):
                print '**warning** unable to read allowed_IP list'
                
        f = self.config['banned_ips']
        if f and self.banned_ip_mtime != os.path.getmtime(f):
            self.banned_IPs = IP_Range_List()
            try:
                self.banned_IPs.read_rangelist(f)
                self.banned_ip_mtime = os.path.getmtime(f)
            except (IOError, OSError):
                print '**warning** unable to read banned_IP list'
                

    def delete_peer(self, infohash, peerid):
        dls = self.downloads[infohash]
        peer = dls[peerid]
        if not peer['left']:
            self.seedcount[infohash] -= 1
        if not peer.get('nat',-1):
            l = self.becache[infohash]
            y = not peer['left']
            for x in l:
                del x[y][peerid]
        del self.times[infohash][peerid]
        del dls[peerid]

    def expire_downloaders(self):
        for x in self.times.keys():
            for myid, t in self.times[x].items():
                if t < self.prevtime:
                    self.delete_peer(x,myid)
        self.prevtime = clock()
        if (self.keep_dead != 1):
            for key, value in self.downloads.items():
                if len(value) == 0 and (
                        self.allowed is None or not self.allowed.has_key(key) ):
                    del self.times[key]
                    del self.downloads[key]
                    del self.seedcount[key]
        self.rawserver.add_task(self.expire_downloaders, self.timeout_downloaders_interval)


def track(args):
    if not args:
        print formatDefinitions(defaults, 80)
        return
    try:
        config, files = parseargs(args, defaults, 0, 0)
    except ValueError, e:
        print 'error: ' + str(e)
        print 'run with no arguments for parameter explanations'
        return
    r = RawServer(Event(), config['timeout_check_interval'],
                  config['socket_timeout'], ipv6_enable = config['ipv6_enabled'])
    t = Tracker(config, r)
    r.bind(config['port'], config['bind'],
           reuse = True, ipv6_socket_style = config['ipv6_binds_v4'])
    r.listen_forever(HTTPHandler(t.get, config['min_time_between_log_flushes']))
    t.save_state()
    print '# Shutting down: ' + isotime()

def size_format(s):
    if (s < 1024):
        r = str(s) + 'B'
    elif (s < 1048576):
        r = str(int(s/1024)) + 'KiB'
    elif (s < 1073741824L):
        r = str(int(s/1048576)) + 'MiB'
    elif (s < 1099511627776L):
        r = str(int((s/1073741824.0)*100.0)/100.0) + 'GiB'
    else:
        r = str(int((s/1099511627776.0)*100.0)/100.0) + 'TiB'
    return(r)


########NEW FILE########
__FILENAME__ = Uploader
# Written by Bram Cohen
# see LICENSE.txt for license information

from BitTornado.CurrentRateMeasure import Measure

try:
    True
except:
    True = 1
    False = 0

class Upload:
    def __init__(self, connection, ratelimiter, totalup, choker, storage, 
                 picker, config):
        self.connection = connection
        self.ratelimiter = ratelimiter
        self.totalup = totalup
        self.choker = choker
        self.storage = storage
        self.picker = picker
        self.config = config
        self.max_slice_length = config['max_slice_length']
        self.choked = True
        self.cleared = True
        self.interested = False
        self.super_seeding = False
        self.buffer = []
        self.measure = Measure(config['max_rate_period'], config['upload_rate_fudge'])
        self.was_ever_interested = False
        if storage.get_amount_left() == 0:
            if choker.super_seed:
                self.super_seeding = True   # flag, and don't send bitfield
                self.seed_have_list = []    # set from piecepicker
                self.skipped_count = 0
            else:
                if config['breakup_seed_bitfield']:
                    bitfield, msgs = storage.get_have_list_cloaked()
                    connection.send_bitfield(bitfield)
                    for have in msgs:
                        connection.send_have(have)
                else:
                    connection.send_bitfield(storage.get_have_list())
        else:
            if storage.do_I_have_anything():
                connection.send_bitfield(storage.get_have_list())
        self.piecedl = None
        self.piecebuf = None

    def got_not_interested(self):
        if self.interested:
            self.interested = False
            del self.buffer[:]
            self.piecedl = None
            if self.piecebuf:
                self.piecebuf.release()
            self.piecebuf = None
            self.choker.not_interested(self.connection)

    def got_interested(self):
        if not self.interested:
            self.interested = True
            self.was_ever_interested = True
            self.choker.interested(self.connection)

    def get_upload_chunk(self):
        if self.choked or not self.buffer:
            return None
        index, begin, length = self.buffer.pop(0)
        if self.config['buffer_reads']:
            if index != self.piecedl:
                if self.piecebuf:
                    self.piecebuf.release()
                self.piecedl = index
                self.piecebuf = self.storage.get_piece(index, 0, -1)
            try:
                piece = self.piecebuf[begin:begin+length]
                assert len(piece) == length
            except:     # fails if storage.get_piece returns None or if out of range
                self.connection.close()
                return None
        else:
            if self.piecebuf:
                self.piecebuf.release()
                self.piecedl = None
            piece = self.storage.get_piece(index, begin, length)
            if piece is None:
                self.connection.close()
                return None
        self.measure.update_rate(len(piece))
        self.totalup.update_rate(len(piece))
        return (index, begin, piece)

    def got_request(self, index, begin, length):
        if ((self.super_seeding and not index in self.seed_have_list)
                   or not self.interested or length > self.max_slice_length):
            self.connection.close()
            return
        if not self.cleared:
            self.buffer.append((index, begin, length))
        if not self.choked and self.connection.next_upload is None:
            self.ratelimiter.queue(self.connection)


    def got_cancel(self, index, begin, length):
        try:
            self.buffer.remove((index, begin, length))
        except ValueError:
            pass

    def choke(self):
        if not self.choked:
            self.choked = True
            self.connection.send_choke()
        self.piecedl = None
        if self.piecebuf:
            self.piecebuf.release()
            self.piecebuf = None

    def choke_sent(self):
        del self.buffer[:]
        self.cleared = True

    def unchoke(self):
        if self.choked:
            self.choked = False
            self.cleared = False
            self.connection.send_unchoke()
        
    def disconnected(self):
        if self.piecebuf:
            self.piecebuf.release()
            self.piecebuf = None

    def is_choked(self):
        return self.choked
        
    def is_interested(self):
        return self.interested

    def has_queries(self):
        return not self.choked and self.buffer

    def get_rate(self):
        return self.measure.get_rate()
    

########NEW FILE########
__FILENAME__ = clock
# Written by John Hoffman
# see LICENSE.txt for license information

import sys

from time import time

_MAXFORWARD = 100
_FUDGE = 1

class RelativeTime:
    def __init__(self):
        self.time = time()
        self.offset = 0

    def get_time(self):        
        t = time() + self.offset
        if t < self.time or t > self.time + _MAXFORWARD:
            self.time += _FUDGE
            self.offset += self.time - t
            return self.time
        self.time = t
        return t

if sys.platform != 'win32':
    _RTIME = RelativeTime()
    def clock():
        return _RTIME.get_time()
else:
    from time import clock
########NEW FILE########
__FILENAME__ = ConfigDir
#written by John Hoffman

from inifile import ini_write, ini_read
from bencode import bencode, bdecode
from types import IntType, LongType, StringType, FloatType
from CreateIcons import GetIcons, CreateIcon
from parseargs import defaultargs
from __init__ import product_name, version_short
import sys, os
from time import time, strftime

from binascii import b2a_hex as tohex, a2b_hex as unhex

try:
    True
except:
    True = 1
    False = 0

try:
    realpath = os.path.realpath
except:
    realpath = lambda x: x
OLDICONPATH = os.path.abspath(os.path.dirname(realpath(sys.argv[0])))

DIRNAME = '.'+product_name


def copyfile(oldpath, newpath): # simple file copy, all in RAM
    try:
        f = open(oldpath, 'rb')
        r = f.read()
        success = True
    except:
        success = False
    try:
        f.close()
    except:
        pass
    if not success:
        return False
    try:
        f = open(newpath, 'wb')
        f.write(r)
    except:
        success = False
    try:
        f.close()
    except:
        pass
    return success


class ConfigDir:

    ###### INITIALIZATION TASKS ######

    def __init__(self, config_type = None):
        self.config_type = config_type
        if config_type:
            config_ext = '.'+config_type
        else:
            config_ext = ''

        def check_sysvars(x):
            y = os.path.expandvars(x)
            if y != x and os.path.isdir(y):
                return y
            return None

        for d in ['${APPDATA}', '${HOME}', '${HOMEPATH}', '${USERPROFILE}']:
            dir_root = check_sysvars(d)
            if dir_root:
                break
        else:
            dir_root = os.path.expanduser('~')
            if not os.path.isdir(dir_root):
                dir_root = os.path.abspath(os.path.dirname(sys.argv[0]))

        dir_root = os.path.join(dir_root, DIRNAME)
        self.dir_root = dir_root

        if not os.path.isdir(self.dir_root):
            os.mkdir(self.dir_root, 0700)    # exception if failed

        self.dir_icons = os.path.join(dir_root, 'icons')
        if not os.path.isdir(self.dir_icons):
            os.mkdir(self.dir_icons)
        for icon in GetIcons():
            i = os.path.join(self.dir_icons, icon)
            if not os.path.exists(i):
                if not copyfile(os.path.join(OLDICONPATH, icon), i):
                    CreateIcon(icon, self.dir_icons)

        self.dir_torrentcache = os.path.join(dir_root, 'torrentcache')
        if not os.path.isdir(self.dir_torrentcache):
            os.mkdir(self.dir_torrentcache)

        self.dir_datacache = os.path.join(dir_root, 'datacache')
        if not os.path.isdir(self.dir_datacache):
            os.mkdir(self.dir_datacache)

        self.dir_piececache = os.path.join(dir_root, 'piececache')
        if not os.path.isdir(self.dir_piececache):
            os.mkdir(self.dir_piececache)

        self.configfile = os.path.join(dir_root, 'config'+config_ext+'.ini')
        self.statefile = os.path.join(dir_root, 'state'+config_ext)

        self.TorrentDataBuffer = {}


    ###### CONFIG HANDLING ######

    def setDefaults(self, defaults, ignore=[]):
        self.config = defaultargs(defaults)
        for k in ignore:
            if self.config.has_key(k):
                del self.config[k]

    def checkConfig(self):
        return os.path.exists(self.configfile)

    def loadConfig(self):
        try:
            r = ini_read(self.configfile)['']
        except:
            return self.config
        l = self.config.keys()
        for k, v in r.items():
            if self.config.has_key(k):
                t = type(self.config[k])
                try:
                    if t == StringType:
                        self.config[k] = v
                    elif t == IntType or t == LongType:
                        self.config[k] = long(v)
                    elif t == FloatType:
                        self.config[k] = float(v)
                    l.remove(k)
                except:
                    pass
        if l: # new default values since last save
            self.saveConfig()
        return self.config

    def saveConfig(self, new_config = None):
        if new_config:
            for k, v in new_config.items():
                if self.config.has_key(k):
                    self.config[k] = v
        try:
            ini_write(self.configfile, self.config, 
                       'Generated by '+product_name+'/'+version_short+'\n'
                       + strftime('%x %X'))
            return True
        except:
            return False

    def getConfig(self):
        return self.config


    ###### STATE HANDLING ######

    def getState(self):
        try:
            f = open(self.statefile, 'rb')
            r = f.read()
        except:
            r = None
        try:
            f.close()
        except:
            pass
        try:
            r = bdecode(r)
        except:
            r = None
        return r        

    def saveState(self, state):
        try:
            f = open(self.statefile, 'wb')
            f.write(bencode(state))
            success = True
        except:
            success = False
        try:
            f.close()
        except:
            pass
        return success


    ###### TORRENT HANDLING ######

    def getTorrents(self):
        d = {}
        for f in os.listdir(self.dir_torrentcache):
            f = os.path.basename(f)
            try:
                f, garbage = f.split('.')
            except:
                pass
            d[unhex(f)] = 1
        return d.keys()

    def getTorrentVariations(self, t):
        t = tohex(t)
        d = []
        for f in os.listdir(self.dir_torrentcache):
            f = os.path.basename(f)
            if f[:len(t)] == t:
                try:
                    garbage, ver = f.split('.')
                except:
                    ver = '0'
                d.append(int(ver))
        d.sort()
        return d

    def getTorrent(self, t, v = -1):
        t = tohex(t)
        if v == -1:
            v = max(self.getTorrentVariations(t))   # potential exception
        if v:
            t += '.'+str(v)
        try:
            f = open(os.path.join(self.dir_torrentcache, t), 'rb')
            r = bdecode(f.read())
        except:
            r = None
        try:
            f.close()
        except:
            pass
        return r

    def writeTorrent(self, data, t, v = -1):
        t = tohex(t)
        if v == -1:
            try:
                v = max(self.getTorrentVariations(t))+1
            except:
                v = 0
        if v:
            t += '.'+str(v)
        try:
            f = open(os.path.join(self.dir_torrentcache, t), 'wb')
            f.write(bencode(data))
        except:
            v = None
        try:
            f.close()
        except:
            pass
        return v


    ###### TORRENT DATA HANDLING ######

    def getTorrentData(self, t):
        if self.TorrentDataBuffer.has_key(t):
            return self.TorrentDataBuffer[t]
        t = os.path.join(self.dir_datacache, tohex(t))
        if not os.path.exists(t):
            return None
        try:
            f = open(t, 'rb')
            r = bdecode(f.read())
        except:
            r = None
        try:
            f.close()
        except:
            pass
        self.TorrentDataBuffer[t] = r
        return r

    def writeTorrentData(self, t, data):
        self.TorrentDataBuffer[t] = data
        try:
            f = open(os.path.join(self.dir_datacache, tohex(t)), 'wb')
            f.write(bencode(data))
            success = True
        except:
            success = False
        try:
            f.close()
        except:
            pass
        if not success:
            self.deleteTorrentData(t)
        return success

    def deleteTorrentData(self, t):
        try:
            os.remove(os.path.join(self.dir_datacache, tohex(t)))
        except:
            pass

    def getPieceDir(self, t):
        return os.path.join(self.dir_piececache, tohex(t))


    ###### EXPIRATION HANDLING ######

    def deleteOldCacheData(self, days, still_active = [], delete_torrents = False):
        if not days:
            return
        exptime = time() - (days*24*3600)
        names = {}
        times = {}

        for f in os.listdir(self.dir_torrentcache):
            p = os.path.join(self.dir_torrentcache, f)
            f = os.path.basename(f)
            try:
                f, garbage = f.split('.')
            except:
                pass
            try:
                f = unhex(f)
                assert len(f) == 20
            except:
                continue
            if delete_torrents:
                names.setdefault(f, []).append(p)
            try:
                t = os.path.getmtime(p)
            except:
                t = time()
            times.setdefault(f, []).append(t)
        
        for f in os.listdir(self.dir_datacache):
            p = os.path.join(self.dir_datacache, f)
            try:
                f = unhex(os.path.basename(f))
                assert len(f) == 20
            except:
                continue
            names.setdefault(f, []).append(p)
            try:
                t = os.path.getmtime(p)
            except:
                t = time()
            times.setdefault(f, []).append(t)

        for f in os.listdir(self.dir_piececache):
            p = os.path.join(self.dir_piececache, f)
            try:
                f = unhex(os.path.basename(f))
                assert len(f) == 20
            except:
                continue
            for f2 in os.listdir(p):
                p2 = os.path.join(p, f2)
                names.setdefault(f, []).append(p2)
                try:
                    t = os.path.getmtime(p2)
                except:
                    t = time()
                times.setdefault(f, []).append(t)
            names.setdefault(f, []).append(p)

        for k, v in times.items():
            if max(v) < exptime and not k in still_active:
                for f in names[k]:
                    try:
                        os.remove(f)
                    except:
                        try:
                            os.removedirs(f)
                        except:
                            pass


    def deleteOldTorrents(self, days, still_active = []):
        self.deleteOldCacheData(days, still_active, True)


    ###### OTHER ######

    def getIconDir(self):
        return self.dir_icons

########NEW FILE########
__FILENAME__ = ConfigReader
#written by John Hoffman

import sys
from wxPython.wx import *

from ConnChoice import connChoices
from download_bt1 import defaults
from ConfigDir import ConfigDir
import socket
from parseargs import defaultargs

try:
    True
except:
    True = 1
    False = 0
    
try:
    wxFULL_REPAINT_ON_RESIZE
except:
    wxFULL_REPAINT_ON_RESIZE = 0        # fix for wx pre-2.5

if (sys.platform == 'win32'):
    _FONT = 9
else:
    _FONT = 10

def HexToColor(s):
    r, g, b = s.split(' ')
    return wxColour(red = int(r, 16), green = int(g, 16), blue = int(b, 16))
    
def hex2(c):
    h = hex(c)[2:]
    if len(h) == 1:
        h = '0'+h
    return h
def ColorToHex(c):
    return hex2(c.Red()) + ' ' + hex2(c.Green()) + ' ' + hex2(c.Blue())

ratesettingslist = []
for x in connChoices:
    if not x.has_key('super-seed'):
        ratesettingslist.append(x['name'])


configFileDefaults = [
    #args only available for the gui client
    ('win32_taskbar_icon', 1, 
         "whether to iconize do system try or not on win32"), 
    ('gui_stretchwindow', 0, 
         "whether to stretch the download status window to fit the torrent name"), 
    ('gui_displaystats', 1, 
         "whether to display statistics on peers and seeds"), 
    ('gui_displaymiscstats', 1, 
         "whether to display miscellaneous other statistics"), 
    ('gui_ratesettingsdefault', ratesettingslist[0], 
         "the default setting for maximum upload rate and users"), 
    ('gui_ratesettingsmode', 'full', 
         "what rate setting controls to display; options are 'none', 'basic', and 'full'"), 
    ('gui_forcegreenonfirewall', 0, 
         "forces the status icon to be green even if the client seems to be firewalled"), 
    ('gui_default_savedir', '', 
         "default save directory"), 
    ('last_saved', '', # hidden; not set in config
         "where the last torrent was saved"), 
    ('gui_font', _FONT, 
         "the font size to use"), 
    ('gui_saveas_ask', -1, 
         "whether to ask where to download to (0 = never, 1 = always, -1 = automatic resume"), 
]

def setwxconfigfiledefaults():
    CHECKINGCOLOR = ColorToHex(wxSystemSettings_GetColour(wxSYS_COLOUR_3DSHADOW)) 	 
    DOWNLOADCOLOR = ColorToHex(wxSystemSettings_GetColour(wxSYS_COLOUR_ACTIVECAPTION))
    
    configFileDefaults.extend([
        ('gui_checkingcolor', CHECKINGCOLOR, 
            "progress bar checking color"), 
        ('gui_downloadcolor', DOWNLOADCOLOR, 
            "progress bar downloading color"), 
        ('gui_seedingcolor', '00 FF 00', 
            "progress bar seeding color"), 
    ])

defaultsToIgnore = ['responsefile', 'url', 'priority']


class configReader:

    def __init__(self):
        self.configfile = wxConfig("BitTorrent", style=wxCONFIG_USE_LOCAL_FILE)
        self.configMenuBox = None
        self.advancedMenuBox = None
        self._configReset = True         # run reset for the first time

        setwxconfigfiledefaults()

        defaults.extend(configFileDefaults)
        self.defaults = defaultargs(defaults)

        self.configDir = ConfigDir('gui')
        self.configDir.setDefaults(defaults, defaultsToIgnore)
        if self.configDir.checkConfig():
            self.config = self.configDir.loadConfig()
        else:
            self.config = self.configDir.getConfig()
            self.importOldGUIConfig()
            self.configDir.saveConfig()

        updated = False     # make all config default changes here

        if self.config['gui_ratesettingsdefault'] not in ratesettingslist:
            self.config['gui_ratesettingsdefault'] = (
                                self.defaults['gui_ratesettingsdefault'])
            updated = True
        if self.config['ipv6_enabled'] and (
                        sys.version_info < (2, 3) or not socket.has_ipv6):
            self.config['ipv6_enabled'] = 0
            updated = True
        for c in ['gui_checkingcolor', 'gui_downloadcolor', 'gui_seedingcolor']:
            try:
                HexToColor(self.config[c])
            except:
                self.config[c] = self.defaults[c]
                updated = True

        if updated:
            self.configDir.saveConfig()

        self.configDir.deleteOldCacheData(self.config['expire_cache_data'])


    def importOldGUIConfig(self):
        oldconfig = wxConfig("BitTorrent", style=wxCONFIG_USE_LOCAL_FILE)
        cont, s, i = oldconfig.GetFirstEntry()
        if not cont:
            oldconfig.DeleteAll()
            return False
        while cont:     # import old config data
            if self.config.has_key(s):
                t = oldconfig.GetEntryType(s)
                try:
                    if t == 1:
                        assert type(self.config[s]) == type('')
                        self.config[s] = oldconfig.Read(s)
                    elif t == 2 or t == 3:
                        assert type(self.config[s]) == type(1)
                        self.config[s] = int(oldconfig.ReadInt(s))
                    elif t == 4:
                        assert type(self.config[s]) == type(1.0)
                        self.config[s] = oldconfig.ReadFloat(s)
                except:
                    pass
            cont, s, i = oldconfig.GetNextEntry(i)

#        oldconfig.DeleteAll()
        return True


    def resetConfigDefaults(self):
        for p, v in self.defaults.items():
            if not p in defaultsToIgnore:
                self.config[p] = v
        self.configDir.saveConfig()

    def writeConfigFile(self):
        self.configDir.saveConfig()

    def WriteLastSaved(self, l):
        self.config['last_saved'] = l
        self.configDir.saveConfig()


    def getcheckingcolor(self):
        return HexToColor(self.config['gui_checkingcolor'])
    def getdownloadcolor(self):
        return HexToColor(self.config['gui_downloadcolor'])
    def getseedingcolor(self):
        return HexToColor(self.config['gui_seedingcolor'])

    def configReset(self):
        r = self._configReset
        self._configReset = False
        return r

    def getConfigDir(self):
        return self.configDir

    def getIconDir(self):
        return self.configDir.getIconDir()

    def getTorrentData(self, t):
        return self.configDir.getTorrentData(t)

    def setColorIcon(self, xxicon, xxiconptr, xxcolor):
        idata = wxMemoryDC()
        idata.SelectObject(xxicon)
        idata.SetBrush(wxBrush(xxcolor, wxSOLID))
        idata.DrawRectangle(0, 0, 16, 16)
        idata.SelectObject(wxNullBitmap)
        xxiconptr.Refresh()


    def getColorFromUser(self, parent, colInit):
        data = wxColourData()
        if colInit.Ok():
            data.SetColour(colInit)
        data.SetCustomColour(0, self.checkingcolor)
        data.SetCustomColour(1, self.downloadcolor)
        data.SetCustomColour(2, self.seedingcolor)
        dlg = wxColourDialog(parent, data)
        if not dlg.ShowModal():
            return colInit
        return dlg.GetColourData().GetColour()


    def configMenu(self, parent):
        self.parent = parent
        try:
            self.FONT = self.config['gui_font']
            self.default_font = wxFont(self.FONT, wxDEFAULT, wxNORMAL, wxNORMAL, False)
            self.checkingcolor = HexToColor(self.config['gui_checkingcolor'])
            self.downloadcolor = HexToColor(self.config['gui_downloadcolor'])
            self.seedingcolor = HexToColor(self.config['gui_seedingcolor'])
            
            if (self.configMenuBox is not None):
                try:
                    self.configMenuBox.Close()
                except wxPyDeadObjectError, e:
                    self.configMenuBox = None
    
            self.configMenuBox = wxFrame(None, -1, 'BitTorrent Preferences', size = (1, 1), 
                                style = wxDEFAULT_FRAME_STYLE|wxFULL_REPAINT_ON_RESIZE)
            if (sys.platform == 'win32'):
                self.icon = self.parent.icon
                self.configMenuBox.SetIcon(self.icon)
    
            panel = wxPanel(self.configMenuBox, -1)
            self.panel = panel
    
            def StaticText(text, font = self.FONT, underline = False, color = None, panel = panel):
                x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
                x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
                if color is not None:
                    x.SetForegroundColour(color)
                return x
    
            colsizer = wxFlexGridSizer(cols = 1, vgap = 8)
    
            self.gui_stretchwindow_checkbox = wxCheckBox(panel, -1, "Stretch window to fit torrent name *")
            self.gui_stretchwindow_checkbox.SetFont(self.default_font)
            self.gui_stretchwindow_checkbox.SetValue(self.config['gui_stretchwindow'])
    
            self.gui_displaystats_checkbox = wxCheckBox(panel, -1, "Display peer and seed statistics")
            self.gui_displaystats_checkbox.SetFont(self.default_font)
            self.gui_displaystats_checkbox.SetValue(self.config['gui_displaystats'])
    
            self.gui_displaymiscstats_checkbox = wxCheckBox(panel, -1, "Display miscellaneous other statistics")
            self.gui_displaymiscstats_checkbox.SetFont(self.default_font)
            self.gui_displaymiscstats_checkbox.SetValue(self.config['gui_displaymiscstats'])
    
            self.security_checkbox = wxCheckBox(panel, -1, "Don't allow multiple connections from the same IP")
            self.security_checkbox.SetFont(self.default_font)
            self.security_checkbox.SetValue(self.config['security'])
    
            self.autokick_checkbox = wxCheckBox(panel, -1, "Kick/ban clients that send you bad data *")
            self.autokick_checkbox.SetFont(self.default_font)
            self.autokick_checkbox.SetValue(self.config['auto_kick'])
    
            self.buffering_checkbox = wxCheckBox(panel, -1, "Enable read/write buffering *")
            self.buffering_checkbox.SetFont(self.default_font)
            self.buffering_checkbox.SetValue(self.config['buffer_reads'])
    
            self.breakup_checkbox = wxCheckBox(panel, -1, "Break-up seed bitfield to foil ISP manipulation")
            self.breakup_checkbox.SetFont(self.default_font)
            self.breakup_checkbox.SetValue(self.config['breakup_seed_bitfield'])

            self.autoflush_checkbox = wxCheckBox(panel, -1, "Flush data to disk every 5 minutes")
            self.autoflush_checkbox.SetFont(self.default_font)
            self.autoflush_checkbox.SetValue(self.config['auto_flush'])
    
            if sys.version_info >= (2, 3) and socket.has_ipv6:
                self.ipv6enabled_checkbox = wxCheckBox(panel, -1, "Initiate and receive connections via IPv6 *")
                self.ipv6enabled_checkbox.SetFont(self.default_font)
                self.ipv6enabled_checkbox.SetValue(self.config['ipv6_enabled'])
    
            self.gui_forcegreenonfirewall_checkbox = wxCheckBox(panel, -1, 
                                "Force icon to display green when firewalled")
            self.gui_forcegreenonfirewall_checkbox.SetFont(self.default_font)
            self.gui_forcegreenonfirewall_checkbox.SetValue(self.config['gui_forcegreenonfirewall'])
    
    
            self.minport_data = wxSpinCtrl(panel, -1, '', (-1, -1), (self.FONT*8, -1))
            self.minport_data.SetFont(self.default_font)
            self.minport_data.SetRange(1, 65535)
            self.minport_data.SetValue(self.config['minport'])
    
            self.maxport_data = wxSpinCtrl(panel, -1, '', (-1, -1), (self.FONT*8, -1))
            self.maxport_data.SetFont(self.default_font)
            self.maxport_data.SetRange(1, 65535)
            self.maxport_data.SetValue(self.config['maxport'])
            
            self.randomport_checkbox = wxCheckBox(panel, -1, "randomize")
            self.randomport_checkbox.SetFont(self.default_font)
            self.randomport_checkbox.SetValue(self.config['random_port'])
            
            self.gui_font_data = wxSpinCtrl(panel, -1, '', (-1, -1), (self.FONT*5, -1))
            self.gui_font_data.SetFont(self.default_font)
            self.gui_font_data.SetRange(8, 16)
            self.gui_font_data.SetValue(self.config['gui_font'])
    
            self.gui_ratesettingsdefault_data=wxChoice(panel, -1, choices = ratesettingslist)
            self.gui_ratesettingsdefault_data.SetFont(self.default_font)
            self.gui_ratesettingsdefault_data.SetStringSelection(self.config['gui_ratesettingsdefault'])
    
            self.maxdownload_data = wxSpinCtrl(panel, -1, '', (-1, -1), (self.FONT*7, -1))
            self.maxdownload_data.SetFont(self.default_font)
            self.maxdownload_data.SetRange(0, 5000)
            self.maxdownload_data.SetValue(self.config['max_download_rate'])
    
            self.gui_ratesettingsmode_data=wxRadioBox(panel, -1, 'Rate Settings Mode', 
                     choices = [ 'none', 'basic', 'full' ])
            self.gui_ratesettingsmode_data.SetFont(self.default_font)
            self.gui_ratesettingsmode_data.SetStringSelection(self.config['gui_ratesettingsmode'])
    
            if (sys.platform == 'win32'):
                self.win32_taskbar_icon_checkbox = wxCheckBox(panel, -1, "Minimize to system tray")
                self.win32_taskbar_icon_checkbox.SetFont(self.default_font)
                self.win32_taskbar_icon_checkbox.SetValue(self.config['win32_taskbar_icon'])
                
    #            self.upnp_checkbox = wxCheckBox(panel, -1, "Enable automatic UPnP port forwarding")
    #            self.upnp_checkbox.SetFont(self.default_font)
    #            self.upnp_checkbox.SetValue(self.config['upnp_nat_access'])
                self.upnp_data=wxChoice(panel, -1, 
                            choices = ['disabled', 'type 1 (fast)', 'type 2 (slow)'])
                self.upnp_data.SetFont(self.default_font)
                self.upnp_data.SetSelection(self.config['upnp_nat_access'])
    
            self.gui_default_savedir_ctrl = wxTextCtrl(parent = panel, id = -1, 
                                value = self.config['gui_default_savedir'], 
                                size = (26*self.FONT, -1), style = wxTE_PROCESS_TAB)
            self.gui_default_savedir_ctrl.SetFont(self.default_font)
    
            self.gui_savemode_data=wxRadioBox(panel, -1, 'Ask where to save: *', 
                     choices = [ 'always', 'never', 'auto-resume' ])
            self.gui_savemode_data.SetFont(self.default_font)
            self.gui_savemode_data.SetSelection(1-self.config['gui_saveas_ask'])
    
            self.checkingcolor_icon = wxEmptyBitmap(16, 16)
            self.checkingcolor_iconptr = wxStaticBitmap(panel, -1, self.checkingcolor_icon)
            self.setColorIcon(self.checkingcolor_icon, self.checkingcolor_iconptr, self.checkingcolor)
    
            self.downloadcolor_icon = wxEmptyBitmap(16, 16)
            self.downloadcolor_iconptr = wxStaticBitmap(panel, -1, self.downloadcolor_icon)
            self.setColorIcon(self.downloadcolor_icon, self.downloadcolor_iconptr, self.downloadcolor)
    
            self.seedingcolor_icon = wxEmptyBitmap(16, 16)
            self.seedingcolor_iconptr = wxStaticBitmap(panel, -1, self.seedingcolor_icon)
            self.setColorIcon(self.seedingcolor_icon, self.downloadcolor_iconptr, self.seedingcolor)
            
            rowsizer = wxFlexGridSizer(cols = 2, hgap = 20)
    
            block12sizer = wxFlexGridSizer(cols = 1, vgap = 7)
    
            block1sizer = wxFlexGridSizer(cols = 1, vgap = 2)
            if (sys.platform == 'win32'):
                block1sizer.Add(self.win32_taskbar_icon_checkbox)
    #            block1sizer.Add(self.upnp_checkbox)
            block1sizer.Add(self.gui_stretchwindow_checkbox)
            block1sizer.Add(self.gui_displaystats_checkbox)
            block1sizer.Add(self.gui_displaymiscstats_checkbox)
            block1sizer.Add(self.security_checkbox)
            block1sizer.Add(self.autokick_checkbox)
            block1sizer.Add(self.buffering_checkbox)
            block1sizer.Add(self.breakup_checkbox)
            block1sizer.Add(self.autoflush_checkbox)
            if sys.version_info >= (2, 3) and socket.has_ipv6:
                block1sizer.Add(self.ipv6enabled_checkbox)
            block1sizer.Add(self.gui_forcegreenonfirewall_checkbox)
    
            block12sizer.Add(block1sizer)
    
            colorsizer = wxStaticBoxSizer(wxStaticBox(panel, -1, "Gauge Colors:"), wxVERTICAL)
            colorsizer1 = wxFlexGridSizer(cols = 7)
            colorsizer1.Add(StaticText('           Checking: '), 1, wxALIGN_BOTTOM)
            colorsizer1.Add(self.checkingcolor_iconptr, 1, wxALIGN_BOTTOM)
            colorsizer1.Add(StaticText('   Downloading: '), 1, wxALIGN_BOTTOM)
            colorsizer1.Add(self.downloadcolor_iconptr, 1, wxALIGN_BOTTOM)
            colorsizer1.Add(StaticText('   Seeding: '), 1, wxALIGN_BOTTOM)
            colorsizer1.Add(self.seedingcolor_iconptr, 1, wxALIGN_BOTTOM)
            colorsizer1.Add(StaticText('  '))
            minsize = self.checkingcolor_iconptr.GetBestSize()
            minsize.SetHeight(minsize.GetHeight()+5)
            colorsizer1.SetMinSize(minsize)
            colorsizer.Add(colorsizer1)
           
            block12sizer.Add(colorsizer, 1, wxALIGN_LEFT)
    
            rowsizer.Add(block12sizer)
    
            block3sizer = wxFlexGridSizer(cols = 1)
    
            portsettingsSizer = wxStaticBoxSizer(wxStaticBox(panel, -1, "Port Range:*"), wxVERTICAL)
            portsettingsSizer1 = wxGridSizer(cols = 2, vgap = 1)
            portsettingsSizer1.Add(StaticText('From: '), 1, wxALIGN_CENTER_VERTICAL|wxALIGN_RIGHT)
            portsettingsSizer1.Add(self.minport_data, 1, wxALIGN_BOTTOM)
            portsettingsSizer1.Add(StaticText('To: '), 1, wxALIGN_CENTER_VERTICAL|wxALIGN_RIGHT)
            portsettingsSizer1.Add(self.maxport_data, 1, wxALIGN_BOTTOM)
            portsettingsSizer.Add(portsettingsSizer1)
            portsettingsSizer.Add(self.randomport_checkbox, 1, wxALIGN_CENTER)
            block3sizer.Add(portsettingsSizer, 1, wxALIGN_CENTER)
            block3sizer.Add(StaticText(' '))
            block3sizer.Add(self.gui_ratesettingsmode_data, 1, wxALIGN_CENTER)
            block3sizer.Add(StaticText(' '))
            ratesettingsSizer = wxFlexGridSizer(cols = 1, vgap = 2)
            ratesettingsSizer.Add(StaticText('Default Rate Setting: *'), 1, wxALIGN_CENTER)
            ratesettingsSizer.Add(self.gui_ratesettingsdefault_data, 1, wxALIGN_CENTER)
            block3sizer.Add(ratesettingsSizer, 1, wxALIGN_CENTER)
            if (sys.platform == 'win32'):
                block3sizer.Add(StaticText(' '))
                upnpSizer = wxFlexGridSizer(cols = 1, vgap = 2)
                upnpSizer.Add(StaticText('UPnP Port Forwarding: *'), 1, wxALIGN_CENTER)
                upnpSizer.Add(self.upnp_data, 1, wxALIGN_CENTER)
                block3sizer.Add(upnpSizer, 1, wxALIGN_CENTER)
            
            rowsizer.Add(block3sizer)
            colsizer.Add(rowsizer)
    
            block4sizer = wxFlexGridSizer(cols = 3, hgap = 15)        
            savepathsizer = wxFlexGridSizer(cols = 2, vgap = 1)
            savepathsizer.Add(StaticText('Default Save Path: *'))
            savepathsizer.Add(StaticText(' '))
            savepathsizer.Add(self.gui_default_savedir_ctrl, 1, wxEXPAND)
            savepathButton = wxButton(panel, -1, '...', size = (18, 18))
    #        savepathButton.SetFont(self.default_font)
            savepathsizer.Add(savepathButton, 0, wxALIGN_CENTER)
            savepathsizer.Add(self.gui_savemode_data, 0, wxALIGN_CENTER)
            block4sizer.Add(savepathsizer, -1, wxALIGN_BOTTOM)
    
            fontsizer = wxFlexGridSizer(cols = 1, vgap = 2)
            fontsizer.Add(StaticText(''))
            fontsizer.Add(StaticText('Font: *'), 1, wxALIGN_CENTER)
            fontsizer.Add(self.gui_font_data, 1, wxALIGN_CENTER)
            block4sizer.Add(fontsizer, 1, wxALIGN_CENTER_VERTICAL)
    
            dratesettingsSizer = wxFlexGridSizer(cols = 1, vgap = 2)
            dratesettingsSizer.Add(StaticText('Default Max'), 1, wxALIGN_CENTER)
            dratesettingsSizer.Add(StaticText('Download Rate'), 1, wxALIGN_CENTER)
            dratesettingsSizer.Add(StaticText('(kB/s): *'), 1, wxALIGN_CENTER)
            dratesettingsSizer.Add(self.maxdownload_data, 1, wxALIGN_CENTER)
            dratesettingsSizer.Add(StaticText('(0 = disabled)'), 1, wxALIGN_CENTER)
            
            block4sizer.Add(dratesettingsSizer, 1, wxALIGN_CENTER_VERTICAL)
    
            colsizer.Add(block4sizer, 0, wxALIGN_CENTER)
    #        colsizer.Add(StaticText(' '))
    
            savesizer = wxGridSizer(cols = 4, hgap = 10)
            saveButton = wxButton(panel, -1, 'Save')
    #        saveButton.SetFont(self.default_font)
            savesizer.Add(saveButton, 0, wxALIGN_CENTER)
    
            cancelButton = wxButton(panel, -1, 'Cancel')
    #        cancelButton.SetFont(self.default_font)
            savesizer.Add(cancelButton, 0, wxALIGN_CENTER)
    
            defaultsButton = wxButton(panel, -1, 'Revert to Defaults')
    #        defaultsButton.SetFont(self.default_font)
            savesizer.Add(defaultsButton, 0, wxALIGN_CENTER)
    
            advancedButton = wxButton(panel, -1, 'Advanced...')
    #        advancedButton.SetFont(self.default_font)
            savesizer.Add(advancedButton, 0, wxALIGN_CENTER)
            colsizer.Add(savesizer, 1, wxALIGN_CENTER)
    
            resizewarningtext=StaticText('* These settings will not take effect until the next time you start BitTorrent', self.FONT-2)
            colsizer.Add(resizewarningtext, 1, wxALIGN_CENTER)
    
            border = wxBoxSizer(wxHORIZONTAL)
            border.Add(colsizer, 1, wxEXPAND | wxALL, 4)
            
            panel.SetSizer(border)
            panel.SetAutoLayout(True)
    
            self.advancedConfig = {}
    
            def setDefaults(evt, self = self):
                try:
                    self.minport_data.SetValue(self.defaults['minport'])
                    self.maxport_data.SetValue(self.defaults['maxport'])
                    self.randomport_checkbox.SetValue(self.defaults['random_port'])
                    self.gui_stretchwindow_checkbox.SetValue(self.defaults['gui_stretchwindow'])
                    self.gui_displaystats_checkbox.SetValue(self.defaults['gui_displaystats'])
                    self.gui_displaymiscstats_checkbox.SetValue(self.defaults['gui_displaymiscstats'])
                    self.security_checkbox.SetValue(self.defaults['security'])
                    self.autokick_checkbox.SetValue(self.defaults['auto_kick'])
                    self.buffering_checkbox.SetValue(self.defaults['buffer_reads'])
                    self.breakup_checkbox.SetValue(self.defaults['breakup_seed_bitfield'])
                    self.autoflush_checkbox.SetValue(self.defaults['auto_flush'])
                    if sys.version_info >= (2, 3) and socket.has_ipv6:
                        self.ipv6enabled_checkbox.SetValue(self.defaults['ipv6_enabled'])
                    self.gui_forcegreenonfirewall_checkbox.SetValue(self.defaults['gui_forcegreenonfirewall'])
                    self.gui_font_data.SetValue(self.defaults['gui_font'])
                    self.gui_ratesettingsdefault_data.SetStringSelection(self.defaults['gui_ratesettingsdefault'])
                    self.maxdownload_data.SetValue(self.defaults['max_download_rate'])
                    self.gui_ratesettingsmode_data.SetStringSelection(self.defaults['gui_ratesettingsmode'])
                    self.gui_default_savedir_ctrl.SetValue(self.defaults['gui_default_savedir'])
                    self.gui_savemode_data.SetSelection(1-self.defaults['gui_saveas_ask'])
        
                    self.checkingcolor = HexToColor(self.defaults['gui_checkingcolor'])
                    self.setColorIcon(self.checkingcolor_icon, self.checkingcolor_iconptr, self.checkingcolor)
                    self.downloadcolor = HexToColor(self.defaults['gui_downloadcolor'])
                    self.setColorIcon(self.downloadcolor_icon, self.downloadcolor_iconptr, self.downloadcolor)
                    self.seedingcolor = HexToColor(self.defaults['gui_seedingcolor'])
                    self.setColorIcon(self.seedingcolor_icon, self.seedingcolor_iconptr, self.seedingcolor)
        
                    if (sys.platform == 'win32'):
                        self.win32_taskbar_icon_checkbox.SetValue(self.defaults['win32_taskbar_icon'])
        #                self.upnp_checkbox.SetValue(self.defaults['upnp_nat_access'])
                        self.upnp_data.SetSelection(self.defaults['upnp_nat_access'])
        
                    # reset advanced too
                    self.advancedConfig = {}
                    for key in ['ip', 'bind', 'min_peers', 'max_initiate', 'display_interval', 
                'alloc_type', 'alloc_rate', 'max_files_open', 'max_connections', 'super_seeder', 
                'ipv6_binds_v4', 'double_check', 'triple_check', 'lock_files', 'lock_while_reading', 
                'expire_cache_data']:
                        self.advancedConfig[key] = self.defaults[key]
                    self.CloseAdvanced()
                except:
                    self.parent.exception()
    
    
            def saveConfigs(evt, self = self):
                try:
                    self.config['gui_stretchwindow']=int(self.gui_stretchwindow_checkbox.GetValue())
                    self.config['gui_displaystats']=int(self.gui_displaystats_checkbox.GetValue())
                    self.config['gui_displaymiscstats']=int(self.gui_displaymiscstats_checkbox.GetValue())
                    self.config['security']=int(self.security_checkbox.GetValue())
                    self.config['auto_kick']=int(self.autokick_checkbox.GetValue())
                    buffering=int(self.buffering_checkbox.GetValue())
                    self.config['buffer_reads']=buffering
                    if buffering:
                        self.config['write_buffer_size']=self.defaults['write_buffer_size']
                    else:
                        self.config['write_buffer_size']=0
                    self.config['breakup_seed_bitfield']=int(self.breakup_checkbox.GetValue())
                    if self.autoflush_checkbox.GetValue():
                        self.config['auto_flush']=5
                    else:
                        self.config['auto_flush']=0
                    if sys.version_info >= (2, 3) and socket.has_ipv6:
                        self.config['ipv6_enabled']=int(self.ipv6enabled_checkbox.GetValue())
                    self.config['gui_forcegreenonfirewall']=int(self.gui_forcegreenonfirewall_checkbox.GetValue())
                    self.config['minport']=self.minport_data.GetValue()
                    self.config['maxport']=self.maxport_data.GetValue()
                    self.config['random_port']=int(self.randomport_checkbox.GetValue())
                    self.config['gui_font']=self.gui_font_data.GetValue()
                    self.config['gui_ratesettingsdefault']=self.gui_ratesettingsdefault_data.GetStringSelection()
                    self.config['max_download_rate']=self.maxdownload_data.GetValue()
                    self.config['gui_ratesettingsmode']=self.gui_ratesettingsmode_data.GetStringSelection()
                    self.config['gui_default_savedir']=self.gui_default_savedir_ctrl.GetValue()
                    self.config['gui_saveas_ask']=1-self.gui_savemode_data.GetSelection()
                    self.config['gui_checkingcolor']=ColorToHex(self.checkingcolor)
                    self.config['gui_downloadcolor']=ColorToHex(self.downloadcolor)
                    self.config['gui_seedingcolor']=ColorToHex(self.seedingcolor)
                    
                    if (sys.platform == 'win32'):
                        self.config['win32_taskbar_icon']=int(self.win32_taskbar_icon_checkbox.GetValue())
        #                self.config['upnp_nat_access']=int(self.upnp_checkbox.GetValue())
                        self.config['upnp_nat_access']=self.upnp_data.GetSelection()
        
                    if self.advancedConfig:
                        for key, val in self.advancedConfig.items():
                            self.config[key] = val
        
                    self.writeConfigFile()
                    self._configReset = True
                    self.Close()
                except:
                    self.parent.exception()
    
            def cancelConfigs(evt, self = self):
                self.Close()
    
            def savepath_set(evt, self = self):
                try:
                    d = self.gui_default_savedir_ctrl.GetValue()
                    if d == '':
                        d = self.config['last_saved']
                    dl = wxDirDialog(self.panel, 'Choose a default directory to save to', 
                        d, style = wxDD_DEFAULT_STYLE | wxDD_NEW_DIR_BUTTON)
                    if dl.ShowModal() == wxID_OK:
                        self.gui_default_savedir_ctrl.SetValue(dl.GetPath())
                except:
                    self.parent.exception()
    
            def checkingcoloricon_set(evt, self = self):
                try:
                    newcolor = self.getColorFromUser(self.panel, self.checkingcolor)
                    self.setColorIcon(self.checkingcolor_icon, self.checkingcolor_iconptr, newcolor)
                    self.checkingcolor = newcolor
                except:
                    self.parent.exception()
    
            def downloadcoloricon_set(evt, self = self):
                try:
                    newcolor = self.getColorFromUser(self.panel, self.downloadcolor)
                    self.setColorIcon(self.downloadcolor_icon, self.downloadcolor_iconptr, newcolor)
                    self.downloadcolor = newcolor
                except:
                    self.parent.exception()
    
            def seedingcoloricon_set(evt, self = self):
                try:
                    newcolor = self.getColorFromUser(self.panel, self.seedingcolor)
                    self.setColorIcon(self.seedingcolor_icon, self.seedingcolor_iconptr, newcolor)
                    self.seedingcolor = newcolor
                except:
                    self.parent.exception()

            EVT_BUTTON(self.configMenuBox, saveButton.GetId(), saveConfigs)
            EVT_BUTTON(self.configMenuBox, cancelButton.GetId(), cancelConfigs)
            EVT_BUTTON(self.configMenuBox, defaultsButton.GetId(), setDefaults)
            EVT_BUTTON(self.configMenuBox, advancedButton.GetId(), self.advancedMenu)
            EVT_BUTTON(self.configMenuBox, savepathButton.GetId(), savepath_set)
            EVT_LEFT_DOWN(self.checkingcolor_iconptr, checkingcoloricon_set)
            EVT_LEFT_DOWN(self.downloadcolor_iconptr, downloadcoloricon_set)
            EVT_LEFT_DOWN(self.seedingcolor_iconptr, seedingcoloricon_set)
    
            self.configMenuBox.Show()
            border.Fit(panel)
            self.configMenuBox.Fit()
        except:
            self.parent.exception()


    def Close(self):
        self.CloseAdvanced()
        if self.configMenuBox is not None:
            try:
                self.configMenuBox.Close()
            except wxPyDeadObjectError, e:
                pass
            self.configMenuBox = None

    def advancedMenu(self, event = None):
        try:
            if not self.advancedConfig:
                for key in ['ip', 'bind', 'min_peers', 'max_initiate', 'display_interval', 
            'alloc_type', 'alloc_rate', 'max_files_open', 'max_connections', 'super_seeder', 
            'ipv6_binds_v4', 'double_check', 'triple_check', 'lock_files', 'lock_while_reading', 
            'expire_cache_data']:
                    self.advancedConfig[key] = self.config[key]
    
            if (self.advancedMenuBox is not None):
                try:
                    self.advancedMenuBox.Close()
                except wxPyDeadObjectError, e:
                    self.advancedMenuBox = None
    
            self.advancedMenuBox = wxFrame(None, -1, 'BitTorrent Advanced Preferences', size = (1, 1), 
                                style = wxDEFAULT_FRAME_STYLE|wxFULL_REPAINT_ON_RESIZE)
            if (sys.platform == 'win32'):
                self.advancedMenuBox.SetIcon(self.icon)
    
            panel = wxPanel(self.advancedMenuBox, -1)
    #        self.panel = panel
    
            def StaticText(text, font = self.FONT, underline = False, color = None, panel = panel):
                x = wxStaticText(panel, -1, text, style = wxALIGN_LEFT)
                x.SetFont(wxFont(font, wxDEFAULT, wxNORMAL, wxNORMAL, underline))
                if color is not None:
                    x.SetForegroundColour(color)
                return x
    
            colsizer = wxFlexGridSizer(cols = 1, hgap = 13, vgap = 13)
            warningtext = StaticText('CHANGE THESE SETTINGS AT YOUR OWN RISK', self.FONT+4, True, 'Red')
            colsizer.Add(warningtext, 1, wxALIGN_CENTER)
    
            self.ip_data = wxTextCtrl(parent = panel, id = -1, 
                        value = self.advancedConfig['ip'], 
                        size = (self.FONT*13, int(self.FONT*2.2)), style = wxTE_PROCESS_TAB)
            self.ip_data.SetFont(self.default_font)
            
            self.bind_data = wxTextCtrl(parent = panel, id = -1, 
                        value = self.advancedConfig['bind'], 
                        size = (self.FONT*13, int(self.FONT*2.2)), style = wxTE_PROCESS_TAB)
            self.bind_data.SetFont(self.default_font)
            
            if sys.version_info >= (2, 3) and socket.has_ipv6:
                self.ipv6bindsv4_data=wxChoice(panel, -1, 
                                 choices = ['separate sockets', 'single socket'])
                self.ipv6bindsv4_data.SetFont(self.default_font)
                self.ipv6bindsv4_data.SetSelection(self.advancedConfig['ipv6_binds_v4'])
    
            self.minpeers_data = wxSpinCtrl(panel, -1, '', (-1, -1), (self.FONT*7, -1))
            self.minpeers_data.SetFont(self.default_font)
            self.minpeers_data.SetRange(10, 100)
            self.minpeers_data.SetValue(self.advancedConfig['min_peers'])
            # max_initiate = 2*minpeers
    
            self.displayinterval_data = wxSpinCtrl(panel, -1, '', (-1, -1), (self.FONT*7, -1))
            self.displayinterval_data.SetFont(self.default_font)
            self.displayinterval_data.SetRange(100, 2000)
            self.displayinterval_data.SetValue(int(self.advancedConfig['display_interval']*1000))
    
            self.alloctype_data = wxChoice(panel, -1, 
                             choices = ['normal', 'background', 'pre-allocate', 'sparse'])
            self.alloctype_data.SetFont(self.default_font)
            self.alloctype_data.SetStringSelection(self.advancedConfig['alloc_type'])
    
            self.allocrate_data = wxSpinCtrl(panel, -1, '', (-1, -1), (self.FONT*7, -1))
            self.allocrate_data.SetFont(self.default_font)
            self.allocrate_data.SetRange(1, 100)
            self.allocrate_data.SetValue(int(self.advancedConfig['alloc_rate']))
    
            self.locking_data = wxChoice(panel, -1, 
                               choices = ['no locking', 'lock while writing', 'lock always'])
            self.locking_data.SetFont(self.default_font)
            if self.advancedConfig['lock_files']:
                if self.advancedConfig['lock_while_reading']:
                    self.locking_data.SetSelection(2)
                else:
                    self.locking_data.SetSelection(1)
            else:
                self.locking_data.SetSelection(0)
    
            self.doublecheck_data = wxChoice(panel, -1, 
                               choices = ['no extra checking', 'double-check', 'triple-check'])
            self.doublecheck_data.SetFont(self.default_font)
            if self.advancedConfig['double_check']:
                if self.advancedConfig['triple_check']:
                    self.doublecheck_data.SetSelection(2)
                else:
                    self.doublecheck_data.SetSelection(1)
            else:
                self.doublecheck_data.SetSelection(0)
    
            self.maxfilesopen_choices = ['50', '100', '200', 'no limit ']
            self.maxfilesopen_data = wxChoice(panel, -1, choices = self.maxfilesopen_choices)
            self.maxfilesopen_data.SetFont(self.default_font)
            setval = self.advancedConfig['max_files_open']
            if setval == 0:
                setval = 'no limit '
            else:
                setval = str(setval)
            if not setval in self.maxfilesopen_choices:
                setval = self.maxfilesopen_choices[0]
            self.maxfilesopen_data.SetStringSelection(setval)
    
            self.maxconnections_choices = ['no limit ', '20', '30', '40', '50', '60', '100', '200']
            self.maxconnections_data = wxChoice(panel, -1, choices = self.maxconnections_choices)
            self.maxconnections_data.SetFont(self.default_font)
            setval = self.advancedConfig['max_connections']
            if setval == 0:
                setval = 'no limit '
            else:
                setval = str(setval)
            if not setval in self.maxconnections_choices:
                setval = self.maxconnections_choices[0]
            self.maxconnections_data.SetStringSelection(setval)
    
            self.superseeder_data = wxChoice(panel, -1, 
                             choices = ['normal', 'super-seed'])
            self.superseeder_data.SetFont(self.default_font)
            self.superseeder_data.SetSelection(self.advancedConfig['super_seeder'])
    
            self.expirecache_choices = ['never ', '3', '5', '7', '10', '15', '30', '60', '90']
            self.expirecache_data = wxChoice(panel, -1, choices = self.expirecache_choices)
            setval = self.advancedConfig['expire_cache_data']
            if setval == 0:
                setval = 'never '
            else:
                setval = str(setval)
            if not setval in self.expirecache_choices:
                setval = self.expirecache_choices[0]
            self.expirecache_data.SetFont(self.default_font)
            self.expirecache_data.SetStringSelection(setval)
           
    
            twocolsizer = wxFlexGridSizer(cols = 2, hgap = 20)
            datasizer = wxFlexGridSizer(cols = 2, vgap = 2)
            datasizer.Add(StaticText('Local IP: '), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.ip_data)
            datasizer.Add(StaticText('IP to bind to: '), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.bind_data)
            if sys.version_info >= (2, 3) and socket.has_ipv6:
                datasizer.Add(StaticText('IPv6 socket handling: '), 1, wxALIGN_CENTER_VERTICAL)
                datasizer.Add(self.ipv6bindsv4_data)
            datasizer.Add(StaticText('Minimum number of peers: '), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.minpeers_data)
            datasizer.Add(StaticText('Display interval (ms): '), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.displayinterval_data)
            datasizer.Add(StaticText('Disk allocation type:'), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.alloctype_data)
            datasizer.Add(StaticText('Allocation rate (MiB/s):'), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.allocrate_data)
            datasizer.Add(StaticText('File locking:'), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.locking_data)
            datasizer.Add(StaticText('Extra data checking:'), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.doublecheck_data)
            datasizer.Add(StaticText('Max files open:'), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.maxfilesopen_data)
            datasizer.Add(StaticText('Max peer connections:'), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.maxconnections_data)
            datasizer.Add(StaticText('Default seeding mode:'), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.superseeder_data)
            datasizer.Add(StaticText('Expire resume data(days):'), 1, wxALIGN_CENTER_VERTICAL)
            datasizer.Add(self.expirecache_data)
            
            twocolsizer.Add(datasizer)
    
            infosizer = wxFlexGridSizer(cols = 1)
            self.hinttext = StaticText('', self.FONT, False, 'Blue')
            infosizer.Add(self.hinttext, 1, wxALIGN_LEFT|wxALIGN_CENTER_VERTICAL)
            infosizer.SetMinSize((180, 100))
            twocolsizer.Add(infosizer, 1, wxEXPAND)
    
            colsizer.Add(twocolsizer)
    
            savesizer = wxGridSizer(cols = 3, hgap = 20)
            okButton = wxButton(panel, -1, 'OK')
    #        okButton.SetFont(self.default_font)
            savesizer.Add(okButton, 0, wxALIGN_CENTER)
    
            cancelButton = wxButton(panel, -1, 'Cancel')
    #        cancelButton.SetFont(self.default_font)
            savesizer.Add(cancelButton, 0, wxALIGN_CENTER)
    
            defaultsButton = wxButton(panel, -1, 'Revert to Defaults')
    #        defaultsButton.SetFont(self.default_font)
            savesizer.Add(defaultsButton, 0, wxALIGN_CENTER)
            colsizer.Add(savesizer, 1, wxALIGN_CENTER)
    
            resizewarningtext=StaticText('None of these settings will take effect until the next time you start BitTorrent', self.FONT-2)
            colsizer.Add(resizewarningtext, 1, wxALIGN_CENTER)
    
            border = wxBoxSizer(wxHORIZONTAL)
            border.Add(colsizer, 1, wxEXPAND | wxALL, 4)
            
            panel.SetSizer(border)
            panel.SetAutoLayout(True)
    
            def setDefaults(evt, self = self):
                try:
                    self.ip_data.SetValue(self.defaults['ip'])
                    self.bind_data.SetValue(self.defaults['bind'])
                    if sys.version_info >= (2, 3) and socket.has_ipv6:
                        self.ipv6bindsv4_data.SetSelection(self.defaults['ipv6_binds_v4'])
                    self.minpeers_data.SetValue(self.defaults['min_peers'])
                    self.displayinterval_data.SetValue(int(self.defaults['display_interval']*1000))
                    self.alloctype_data.SetStringSelection(self.defaults['alloc_type'])
                    self.allocrate_data.SetValue(int(self.defaults['alloc_rate']))
                    if self.defaults['lock_files']:
                        if self.defaults['lock_while_reading']:
                            self.locking_data.SetSelection(2)
                        else:
                            self.locking_data.SetSelection(1)
                    else:
                        self.locking_data.SetSelection(0)
                    if self.defaults['double_check']:
                        if self.defaults['triple_check']:
                            self.doublecheck_data.SetSelection(2)
                        else:
                            self.doublecheck_data.SetSelection(1)
                    else:
                        self.doublecheck_data.SetSelection(0)
                    setval = self.defaults['max_files_open']
                    if setval == 0:
                        setval = 'no limit '
                    else:
                        setval = str(setval)
                    if not setval in self.maxfilesopen_choices:
                        setval = self.maxfilesopen_choices[0]
                    self.maxfilesopen_data.SetStringSelection(setval)
                    setval = self.defaults['max_connections']
                    if setval == 0:
                        setval = 'no limit '
                    else:
                        setval = str(setval)
                    if not setval in self.maxconnections_choices:
                        setval = self.maxconnections_choices[0]
                    self.maxconnections_data.SetStringSelection(setval)
                    self.superseeder_data.SetSelection(int(self.defaults['super_seeder']))
                    setval = self.defaults['expire_cache_data']
                    if setval == 0:
                        setval = 'never '
                    else:
                        setval = str(setval)
                    if not setval in self.expirecache_choices:
                        setval = self.expirecache_choices[0]
                    self.expirecache_data.SetStringSelection(setval)
                except:
                    self.parent.exception()
    
            def saveConfigs(evt, self = self):
                try:
                    self.advancedConfig['ip'] = self.ip_data.GetValue()
                    self.advancedConfig['bind'] = self.bind_data.GetValue()
                    if sys.version_info >= (2, 3) and socket.has_ipv6:
                        self.advancedConfig['ipv6_binds_v4'] = self.ipv6bindsv4_data.GetSelection()
                    self.advancedConfig['min_peers'] = self.minpeers_data.GetValue()
                    self.advancedConfig['display_interval'] = float(self.displayinterval_data.GetValue())/1000
                    self.advancedConfig['alloc_type'] = self.alloctype_data.GetStringSelection()
                    self.advancedConfig['alloc_rate'] = float(self.allocrate_data.GetValue())
                    self.advancedConfig['lock_files'] = int(self.locking_data.GetSelection() >= 1)
                    self.advancedConfig['lock_while_reading'] = int(self.locking_data.GetSelection() > 1)
                    self.advancedConfig['double_check'] = int(self.doublecheck_data.GetSelection() >= 1)
                    self.advancedConfig['triple_check'] = int(self.doublecheck_data.GetSelection() > 1)
                    try:
                        self.advancedConfig['max_files_open'] = int(self.maxfilesopen_data.GetStringSelection())
                    except:       # if it ain't a number, it must be "no limit"
                        self.advancedConfig['max_files_open'] = 0
                    try:
                        self.advancedConfig['max_connections'] = int(self.maxconnections_data.GetStringSelection())
                        self.advancedConfig['max_initiate'] = min(
                            2*self.advancedConfig['min_peers'], self.advancedConfig['max_connections'])
                    except:       # if it ain't a number, it must be "no limit"
                        self.advancedConfig['max_connections'] = 0
                        self.advancedConfig['max_initiate'] = 2*self.advancedConfig['min_peers']
                    self.advancedConfig['super_seeder']=int(self.superseeder_data.GetSelection())
                    try:
                        self.advancedConfig['expire_cache_data'] = int(self.expirecache_data.GetStringSelection())
                    except:
                        self.advancedConfig['expire_cache_data'] = 0
                    self.advancedMenuBox.Close()
                except:
                    self.parent.exception()
    
            def cancelConfigs(evt, self = self):            
                self.advancedMenuBox.Close()
    
            def ip_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\nThe IP reported to the tracker.\n' +
                                      'unless the tracker is on the\n' +
                                      'same intranet as this client,\n' +
                                      'the tracker will autodetect the\n' +
                                      "client's IP and ignore this\n" +
                                      "value.")
    
            def bind_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\nThe IP the client will bind to.\n' +
                                      'Only useful if your machine is\n' +
                                      'directly handling multiple IPs.\n' +
                                      "If you don't know what this is,\n" +
                                      "leave it blank.")
    
            def ipv6bindsv4_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\nCertain operating systems will\n' +
                                      'open IPv4 protocol connections on\n' +
                                      'an IPv6 socket; others require you\n' +
                                      "to open two sockets on the same\n" +
                                      "port, one IPv4 and one IPv6.")
    
            def minpeers_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\nThe minimum number of peers the\n' +
                                      'client tries to stay connected\n' +
                                      'with.  Do not set this higher\n' +
                                      'unless you have a very fast\n' +
                                      "connection and a lot of system\n" +
                                      "resources.")
    
            def displayinterval_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\nHow often to update the\n' +
                                      'graphical display, in 1/1000s\n' +
                                      'of a second. Setting this too low\n' +
                                      "will strain your computer's\n" +
                                      "processor and video access.")
    
            def alloctype_hint(evt, self = self):
                self.hinttext.SetLabel('\n\nHow to allocate disk space.\n' +
                                      'normal allocates space as data is\n' +
                                      'received, background also adds\n' +
                                      "space in the background, pre-\n" +
                                      "allocate reserves up front, and\n" +
                                      'sparse is only for filesystems\n' +
                                      'that support it by default.')
    
            def allocrate_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\nAt what rate to allocate disk\n' +
                                      'space when allocating in the\n' +
                                      'background.  Set this too high on a\n' +
                                      "slow filesystem and your download\n" +
                                      "will slow to a crawl.")
    
            def locking_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\n\nFile locking prevents other\n' +
                                      'programs (including other instances\n' +
                                      'of BitTorrent) from accessing files\n' +
                                      "you are downloading.")
    
            def doublecheck_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\nHow much extra checking to do\n' +
                                      'making sure no data is corrupted.\n' +
                                      'Double-check mode uses more CPU,\n' +
                                      "while triple-check mode increases\n" +
                                      "disk accesses.")
    
            def maxfilesopen_hint(evt, self = self):
                self.hinttext.SetLabel('\n\n\nThe maximum number of files to\n' +
                                      'keep open at the same time.  Zero\n' +
                                      'means no limit.  Please note that\n' +
                                      "if this option is in effect,\n" +
                                      "files are not guaranteed to be\n" +
                                      "locked.")
    
            def maxconnections_hint(evt, self = self):
                self.hinttext.SetLabel('\n\nSome operating systems, most\n' +
                                      'notably Windows 9x/ME combined\n' +
                                      'with certain network drivers,\n' +
                                      "cannot handle more than a certain\n" +
                                      "number of open ports.  If the\n" +
                                      "client freezes, try setting this\n" +
                                      "to 60 or below.")
    
            def superseeder_hint(evt, self = self):
                self.hinttext.SetLabel('\n\nThe "super-seed" method allows\n' +
                                      'a single source to more efficiently\n' +
                                      'seed a large torrent, but is not\n' +
                                      "necessary in a well-seeded torrent,\n" +
                                      "and causes problems with statistics.\n" +
                                      "Unless you routinely seed torrents\n" +
                                      "you can enable this by selecting\n" +
                                      '"SUPER-SEED" for connection type.\n' +
                                      '(once enabled it does not turn off.)')
    
            def expirecache_hint(evt, self = self):
                self.hinttext.SetLabel('\n\nThe client stores temporary data\n' +
                                      'in order to handle downloading only\n' +
                                      'specific files from the torrent and\n' +
                                      "so it can resume downloads more\n" +
                                      "quickly.  This sets how long the\n" +
                                      "client will keep this data before\n" +
                                      "deleting it to free disk space.")
    
            EVT_BUTTON(self.advancedMenuBox, okButton.GetId(), saveConfigs)
            EVT_BUTTON(self.advancedMenuBox, cancelButton.GetId(), cancelConfigs)
            EVT_BUTTON(self.advancedMenuBox, defaultsButton.GetId(), setDefaults)
            EVT_ENTER_WINDOW(self.ip_data, ip_hint)
            EVT_ENTER_WINDOW(self.bind_data, bind_hint)
            if sys.version_info >= (2, 3) and socket.has_ipv6:
                EVT_ENTER_WINDOW(self.ipv6bindsv4_data, ipv6bindsv4_hint)
            EVT_ENTER_WINDOW(self.minpeers_data, minpeers_hint)
            EVT_ENTER_WINDOW(self.displayinterval_data, displayinterval_hint)
            EVT_ENTER_WINDOW(self.alloctype_data, alloctype_hint)
            EVT_ENTER_WINDOW(self.allocrate_data, allocrate_hint)
            EVT_ENTER_WINDOW(self.locking_data, locking_hint)
            EVT_ENTER_WINDOW(self.doublecheck_data, doublecheck_hint)
            EVT_ENTER_WINDOW(self.maxfilesopen_data, maxfilesopen_hint)
            EVT_ENTER_WINDOW(self.maxconnections_data, maxconnections_hint)
            EVT_ENTER_WINDOW(self.superseeder_data, superseeder_hint)
            EVT_ENTER_WINDOW(self.expirecache_data, expirecache_hint)
    
            self.advancedMenuBox.Show()
            border.Fit(panel)
            self.advancedMenuBox.Fit()
        except:
            self.parent.exception()


    def CloseAdvanced(self):
        if self.advancedMenuBox is not None:
            try:
                self.advancedMenuBox.Close()
            except wxPyDeadObjectError, e:
                self.advancedMenuBox = None


########NEW FILE########
__FILENAME__ = ConnChoice
connChoices=(
    {'name':'automatic',
     'rate':{'min':0, 'max':5000, 'def': 0},
     'conn':{'min':0, 'max':100,  'def': 0},
     'automatic':1},
    {'name':'unlimited',
     'rate':{'min':0, 'max':5000, 'def': 0, 'div': 50},
     'conn':{'min':4, 'max':100,  'def': 4}},
    {'name':'dialup/isdn',
     'rate':{'min':3,   'max':   8, 'def':  5},
     'conn':{'min':2, 'max':  3, 'def': 2},
     'initiate': 12},
    {'name':'dsl/cable slow',
     'rate':{'min':10,  'max':  48, 'def': 13},
     'conn':{'min':4, 'max': 20, 'def': 4}},
    {'name':'dsl/cable fast',
     'rate':{'min':20,  'max': 100, 'def': 40},
     'conn':{'min':4, 'max': 30, 'def': 6}},
    {'name':'T1',
     'rate':{'min':100, 'max': 300, 'def':150},
     'conn':{'min':4, 'max': 40, 'def':10}},
    {'name':'T3+',
     'rate':{'min':400, 'max':2000, 'def':500},
     'conn':{'min':4, 'max':100, 'def':20}},
    {'name':'seeder',
     'rate':{'min':0, 'max':5000, 'def':0, 'div': 50},
     'conn':{'min':1, 'max':100, 'def':1}},
    {'name':'SUPER-SEED', 'super-seed':1}
     )

connChoiceList = [x['name'] for x in connChoices]

########NEW FILE########
__FILENAME__ = CreateIcons
# Generated from bt_MakeCreateIcons - 05/10/04 22:15:33
# T-0.3.0 (BitTornado)

from binascii import a2b_base64
from zlib import decompress
from os.path import join

icons = {
    "icon_bt.ico":
        "eJyt1K+OFEEQx/FaQTh5GDRZhSQpiUHwCrxCBYXFrjyJLXeXEARPsZqUPMm+" +
        "AlmP+PGtngoLDji69zMz2zt/qqtr1mxHv7621d4+MnvK/jl66Bl2drV+e7Wz" +
        "S/v12A7rY4fDtuvOwfF4tOPXo52/fLLz+WwpWd6nqRXHKXux39sTrtnjNd7g" +
        "PW7wGSd860f880kffjvJ2QYS1Zcw4AjcoaA5yRFIFDQXOgKJguZmjkCioB4T" +
        "Y2CqxpTXA7sHEgVNEC8RSBQ0gfk7xtknCupgk3EEEgXlNgFHIFHQTMoRSBQ0" +
        "E+1ouicKmsk7AomCJiGOQKKgSZIjkChoEucIJAqaZDoCiYImwb4iydULmqQ7" +
        "AomC1kLcEQ/jSBQ0i+MIJAqaBXMEElVdi9siOgKJgmZhfWWlVjTddXW/FtsR" +
        "SBQ0BeAIJAqaonAEEgVNoTgCiYKmeByBREHaqiVWRtSRrAJzBBIFTdE5AomC" +
        "phBPpxPP57dVkDfrTl063nUVnWe383fZx9tb3uN+o7U+BLDtuvcQm8d/27Y/" +
        "jO3o5/ay+YPv/+f6y30e1OyB7QcsGWFj",
    "icon_done.ico":
        "eJyt1K2OVEEQhuEaQbJyMWgyCklSEoPgFvYWKigsduRKbLndhCC4itGk5Erm" +
        "Fsh4xMdbfSoMOGDpnuf89Jyf6uqaMdvRr69ttbdPzJ6xf4Eeeo6dXa3vXu/s" +
        "0n49tsP62OGw7bpzcDwe7fj1aOcvn+x8PltKlg9pasVxyl7u9/aUe/Z4gxu8" +
        "xy0+44Rv/Yp/vujDbxc520Ci+hYGHIF7FDQXOQKJguZGRyBR0DzMEUgU1GNi" +
        "DEzVmPJ6YfdAoqAJ4hUCiYImMH/HOPtEQR1sMo5AoqDcJuAIJAqaSTkCiYJm" +
        "oh1N90RBM3lHIFHQJMQRSBQ0SXIEEgVN4hyBREGTTEcgUdAk2FckuXpBk3RH" +
        "IFHQWoh74mEciYJmcRyBREGzYI5AoqprcVtERyBR0Cysr6zUiqa7rh7WYjsC" +
        "iYKmAByBREFTFI5AoqApFEcgUdAUjyOQKEhbtcTKiDqSVWCOQKKgKTpHIFHQ" +
        "FOLpdOL9fLcK8nY9qUvHu66i8+x2/i77eHfH77h/0VofAth23Xuoz/+2bX8Y" +
        "29HP7WXzB+f/5/7Lcx7V7JHtB9dPG3I=",
    "black.ico":
        "eJzt1zsOgkAYReFLLCztjJ2UlpLY485kOS7DpbgESwqTcQZDghjxZwAfyfl0" +
        "LIieGzUWSom/pan840rHnbSUtPHHX9Je9+tAh2ybNe8TZZ/vk8ajJ4zl6JVJ" +
        "+xFx+0R03Djx1/2B8bcT9L/bt0+4Wq+4se8e/VTfMvGqb4n3nYiIGz+lvt9s" +
        "9EpE2T4xJN4xNFYWU6t+JWXuXDFzTom7SodSyi/S+iwtwjlJ80KaNY/C34rW" +
        "aT8nvK5uhF7ohn7Yqfb87kffLAAAAAAAAAAAAAAAAAAAGMUNy7dADg==",
    "blue.ico":
        "eJzt10EOwUAYhuGv6cLSTux06QD2dTM9jmM4iiNYdiEZ81cIFTWddtDkfbQW" +
        "De8XogtS5h9FIf+81H4jLSSt/ekvaavrdaCDez4SZV+PpPHoicBy9ErSfkQ8" +
        "fCI6Hjgx6f7A+McJ+r/t95i46xMP7bf8Uz9o4k0/XMT338voP5shK0MkjXcM" +
        "YSqam6Qunatyf7Nk7iztaqk8SaujNLfzIM0qKX88ZX8rWmf7Nfa+W8N61rW+" +
        "7TR7fverHxYAAAAAAAAAAAAAAAAAAIziApVZ444=",
    "green.ico":
        "eJzt1zEOgjAAheFHGBzdjJuMHsAdbybxNB7Do3gERwaT2mJIBCOWlqok/yc4" +
        "EP1fNDIoZfZRFLLPa5120krS1p72kvZ6XAeGHLtHouzrkTQePOFZDl5J2g+I" +
        "+08Exz0nZt2PjH+coP/bvveEaY2L+/VN13/1PSbe9v0FfP+jTP6ziVmJkTQ+" +
        "MISZaO6SujSmyu3dkpmbdKil8iptLtLSnWdpUUn58yn3t6J39l/j3tc2XM91" +
        "Xd/tNHt296sfFgAAAAAAAAAAAAAAAAAATOIOVLEoDg==",
    "red.ico":
        "eJzt10EOwUAYhuGv6cLSTux06QD2dTOO4xiO4giWXUjG/BVCRTuddtDkfbQW" +
        "De8XogtS5h9FIf+81GEjLSSt/ekvaavbdaCVez0SZd+PpPHoicBy9ErSfkQ8" +
        "fCI6Hjgx6f7AeOcE/d/2QyceesaD+g1/1u+e+NwPF/H99zL6z2bIyhBJ4y1D" +
        "mIb6LqlK5/a5v1syd5F2lVSepdVJmtt5lGZ7KX8+ZX8rGmfzNfa+e8N61rW+" +
        "7dR7fverHxYAAAAAAAAAAAAAAAAAAIziCpgs444=",
    "white.ico":
        "eJzt1zsOgkAYReFLKCztjJ2ULsAed6bLcRnuwYTaJVhSmIwzGBLEiD8D+EjO" +
        "p2NB9NyosVBK/C3L5B+XOmykhaS1P/6StrpfBzoUp6J5nyj7fJ80Hj1hLEev" +
        "TNqPiNsnouPGib/uD4y/naD/3b59wtV6xY199+in+paJV31LvO9ERNz4KfX9" +
        "ZqNXIsr2iSHxjqGxspha9Sspc+f2qXNK3FXalVJ+kVZnaR7OUZrtpbR5FP5W" +
        "tE77OeF1dSP0Qjf0w06153c/+mYBAAAAAAAAAAAAAAAAAMAobj//I7s=",
    "yellow.ico":
        "eJzt1zsOgkAYReFLKCztjJ2ULsAedybLcRkuxSVYUpiM82M0ihGHgVFJzidY" +
        "ED03vgqlzN+KQv5+qf1GWkha+9Nf0lbX60AX556ORNnXI2k8eiKwHL2StB8R" +
        "D5+IjgdOTLo/MP5xgv5v+8ETd/3iYf2W/+oHTLzth4t4/3sZ/WszZGWIpPGO" +
        "IUxE8yupS+eq3H9smTtLu1oqT9LqKM3tPEizSsofT9nfitbZfow979awnnWt" +
        "bzvNnt/96osFAAAAAAAAAAAAAAAAAACjuABhjmIs",
    "black1.ico":
        "eJzt0zEOgkAUANEhFpZSGTstTWzkVt5Cj8ZROAIHMNGPWBCFDYgxMZkHn2Iz" +
        "G5YCyOLKc+K54XSANbCPiSV2tOt/qjgW3XtSnN41FH/Qv29Jx/P7qefp7W8P" +
        "4z85HQ+9JRG/7BpTft31DPUKyiVcFjEZzQ/TTtdzrWnKmCr6evv780qSJEmS" +
        "JEmSJEmSJEmSpPnunVFDcA==",
    "green1.ico":
        "eJzt0zEKwkAQRuEXLCyTSuy0DHgxb6F4shzFI+QAgpkkFoombowIwvt2Z4vh" +
        "X5gtFrJYRUGca/Y7WAFlVLTY0vf/1elxTwqP3xoKf5B/vjIenp+fOs+r/LWT" +
        "/uQ34aGpUqQnv+1ygDqHagnHRVRG+2H6unfrtZkq6hz5evP7eSVJkiRJkiRJ" +
        "kiRJkiRJ0nwNoWQ+AA==",
    "yellow1.ico":
        "eJzt0zEKwkAQRuEXLCxNJXZaCl7MW8Sj5SgeIQcQ4oS1UDTJxkhAeN/ubDH8" +
        "C7PFQhGrLIlzx/kEW+AYFS0OpP6/atuXPSk8fKsv/EX+/cpweH5+6jyf8kn+" +
        "k0fCfVPlyE/+2q2CZgP1Gi6rqILuw6R69uh1mTrqGvlmv/y8kiRJkiRJkiRJ" +
        "kiRJkiRpvjsp9L8k",
    "alloc.gif":
        "eJxz93SzsEw0YRBh+M4ABi0MS3ue///P8H8UjIIRBhR/sjAyMDAx6IAyAihP" +
        "MHAcYWDlkPHYsOBgM4ewVsyJDQsPNzEoebF8CHjo0smjH3dmRsDjI33C7Dw3" +
        "MiYuOtjNyDShRSNwyemJguJJKhaGS32nGka61Vg2NJyYKRd+bY+nwtMzjbqV" +
        "Qh84gxMCJgnlL4vJuqJyaa5NfFLNLsNVV2a7syacfVWkHd4bv7RN1ltM7ejm" +
        "tMtNZ19Oyb02p8C3aqr3dr2GbXl/7fZyOej5rW653WZ7MzzHZV+v7O2/EZM+" +
        "Pt45kbX6ScWHNWfOilo3n5thucXv8org1XF3DRQYrAEWiVY3"
}

def GetIcons():
    return icons.keys()

def CreateIcon(icon, savedir):
    try:
        f = open(join(savedir,icon),"wb")
        f.write(decompress(a2b_base64(icons[icon])))
        success = 1
    except:
        success = 0
    try:
        f.close()
    except:
        pass
    return success

########NEW FILE########
__FILENAME__ = CurrentRateMeasure
# Written by Bram Cohen
# see LICENSE.txt for license information

from clock import clock

class Measure:
    def __init__(self, max_rate_period, fudge = 1):
        self.max_rate_period = max_rate_period
        self.ratesince = clock() - fudge
        self.last = self.ratesince
        self.rate = 0.0
        self.total = 0L

    def update_rate(self, amount):
        self.total += amount
        t = clock()
        self.rate = (self.rate * (self.last - self.ratesince) + 
            amount) / (t - self.ratesince + 0.0001)
        self.last = t
        if self.ratesince < t - self.max_rate_period:
            self.ratesince = t - self.max_rate_period

    def get_rate(self):
        self.update_rate(0)
        return self.rate

    def get_rate_noupdate(self):
        return self.rate

    def time_until_rate(self, newrate):
        if self.rate <= newrate:
            return 0
        t = clock() - self.ratesince
        return ((self.rate * t) / newrate) - t

    def get_total(self):
        return self.total
########NEW FILE########
__FILENAME__ = download_bt1
# Written by Bram Cohen
# see LICENSE.txt for license information

from zurllib import urlopen
from urlparse import urlparse
from BT1.btformats import check_message
from BT1.Choker import Choker
from BT1.Storage import Storage
from BT1.StorageWrapper import StorageWrapper
from BT1.FileSelector import FileSelector
from BT1.Uploader import Upload
from BT1.Downloader import Downloader
from BT1.HTTPDownloader import HTTPDownloader
from BT1.Connecter import Connecter
from RateLimiter import RateLimiter
from BT1.Encrypter import Encoder
from RawServer import RawServer, autodetect_socket_style
from BT1.Rerequester import Rerequester
from BT1.DownloaderFeedback import DownloaderFeedback
from RateMeasure import RateMeasure
from CurrentRateMeasure import Measure
from BT1.PiecePicker import PiecePicker
from BT1.Statistics import Statistics
from ConfigDir import ConfigDir
from bencode import bencode, bdecode
from natpunch import UPnP_test
from sha import sha
from os import path, makedirs, listdir
from parseargs import parseargs, formatDefinitions, defaultargs
from socket import error as socketerror
from random import seed
from threading import Event
from clock import clock
from __init__ import createPeerID

try:
    True
except:
    True = 1
    False = 0

defaults = [
    ('max_uploads', 7,
        "the maximum number of uploads to allow at once."),
    ('keepalive_interval', 120.0,
        'number of seconds to pause between sending keepalives'),
    ('download_slice_size', 2 ** 14,
        "How many bytes to query for per request."),
    ('upload_unit_size', 1460,
        "when limiting upload rate, how many bytes to send at a time"),
    ('request_backlog', 10,
        "maximum number of requests to keep in a single pipe at once."),
    ('max_message_length', 2 ** 23,
        "maximum length prefix encoding you'll accept over the wire - larger values get the connection dropped."),
    ('ip', '',
        "ip to report you have to the tracker."),
    ('minport', 10000, 'minimum port to listen on, counts up if unavailable'),
    ('maxport', 60000, 'maximum port to listen on'),
    ('random_port', 1, 'whether to choose randomly inside the port range ' +
        'instead of counting up linearly'),
    ('responsefile', '',
        'file the server response was stored in, alternative to url'),
    ('url', '',
        'url to get file from, alternative to responsefile'),
    ('selector_enabled', 1,
        'whether to enable the file selector and fast resume function'),
    ('expire_cache_data', 10,
        'the number of days after which you wish to expire old cache data ' +
        '(0 = disabled)'),
    ('priority', '',
        'a list of file priorities separated by commas, must be one per file, ' +
        '0 = highest, 1 = normal, 2 = lowest, -1 = download disabled'),
    ('saveas', '',
        'local file name to save the file as, null indicates query user'),
    ('timeout', 300.0,
        'time to wait between closing sockets which nothing has been received on'),
    ('timeout_check_interval', 60.0,
        'time to wait between checking if any connections have timed out'),
    ('max_slice_length', 2 ** 17,
        "maximum length slice to send to peers, larger requests are ignored"),
    ('max_rate_period', 20.0,
        "maximum amount of time to guess the current rate estimate represents"),
    ('bind', '', 
        'comma-separated list of ips/hostnames to bind to locally'),
#    ('ipv6_enabled', autodetect_ipv6(),
    ('ipv6_enabled', 0,
         'allow the client to connect to peers via IPv6'),
    ('ipv6_binds_v4', autodetect_socket_style(),
        "set if an IPv6 server socket won't also field IPv4 connections"),
    ('upnp_nat_access', 1,
        'attempt to autoconfigure a UPnP router to forward a server port ' +
        '(0 = disabled, 1 = mode 1 [fast], 2 = mode 2 [slow])'),
    ('upload_rate_fudge', 5.0, 
        'time equivalent of writing to kernel-level TCP buffer, for rate adjustment'),
    ('tcp_ack_fudge', 0.03,
        'how much TCP ACK download overhead to add to upload rate calculations ' +
        '(0 = disabled)'),
    ('display_interval', .5,
        'time between updates of displayed information'),
    ('rerequest_interval', 5 * 60,
        'time to wait between requesting more peers'),
    ('min_peers', 20, 
        'minimum number of peers to not do rerequesting'),
    ('http_timeout', 60, 
        'number of seconds to wait before assuming that an http connection has timed out'),
    ('max_initiate', 40,
        'number of peers at which to stop initiating new connections'),
    ('check_hashes', 1,
        'whether to check hashes on disk'),
    ('max_upload_rate', 0,
        'maximum kB/s to upload at (0 = no limit, -1 = automatic)'),
    ('max_download_rate', 0,
        'maximum kB/s to download at (0 = no limit)'),
    ('alloc_type', 'normal',
        'allocation type (may be normal, background, pre-allocate or sparse)'),
    ('alloc_rate', 2.0,
        'rate (in MiB/s) to allocate space at using background allocation'),
    ('buffer_reads', 1,
        'whether to buffer disk reads'),
    ('write_buffer_size', 4,
        'the maximum amount of space to use for buffering disk writes ' +
        '(in megabytes, 0 = disabled)'),
    ('breakup_seed_bitfield', 1,
        'sends an incomplete bitfield and then fills with have messages, '
        'in order to get around stupid ISP manipulation'),
    ('snub_time', 30.0,
        "seconds to wait for data to come in over a connection before assuming it's semi-permanently choked"),
    ('spew', 0,
        "whether to display diagnostic info to stdout"),
    ('rarest_first_cutoff', 2,
        "number of downloads at which to switch from random to rarest first"),
    ('rarest_first_priority_cutoff', 5,
        'the number of peers which need to have a piece before other partials take priority over rarest first'),
    ('min_uploads', 4,
        "the number of uploads to fill out to with extra optimistic unchokes"),
    ('max_files_open', 50,
        'the maximum number of files to keep open at a time, 0 means no limit'),
    ('round_robin_period', 30,
        "the number of seconds between the client's switching upload targets"),
    ('super_seeder', 0,
        "whether to use special upload-efficiency-maximizing routines (only for dedicated seeds)"),
    ('security', 1,
        "whether to enable extra security features intended to prevent abuse"),
    ('max_connections', 0,
        "the absolute maximum number of peers to connect with (0 = no limit)"),
    ('auto_kick', 1,
        "whether to allow the client to automatically kick/ban peers that send bad data"),
    ('double_check', 1,
        "whether to double-check data being written to the disk for errors (may increase CPU load)"),
    ('triple_check', 0,
        "whether to thoroughly check data being written to the disk (may slow disk access)"),
    ('lock_files', 1,
        "whether to lock files the client is working with"),
    ('lock_while_reading', 0,
        "whether to lock access to files being read"),
    ('auto_flush', 0,
        "minutes between automatic flushes to disk (0 = disabled)"),
    ]

argslistheader = 'Arguments are:\n\n'


def _failfunc(x):
    print x

# old-style downloader
def download(params, filefunc, statusfunc, finfunc, errorfunc, doneflag, cols,
             pathFunc = None, presets = {}, exchandler = None,
             failed = _failfunc, paramfunc = None):

    try:
        config = parse_params(params, presets)
    except ValueError, e:
        failed('error: ' + str(e) + '\nrun with no args for parameter explanations')
        return
    if not config:
        errorfunc(get_usage())
        return
    
    myid = createPeerID()
    seed(myid)

    rawserver = RawServer(doneflag, config['timeout_check_interval'],
                          config['timeout'], ipv6_enable = config['ipv6_enabled'],
                          failfunc = failed, errorfunc = exchandler)

    upnp_type = UPnP_test(config['upnp_nat_access'])
    try:
        listen_port = rawserver.find_and_bind(config['minport'], config['maxport'],
                        config['bind'], ipv6_socket_style = config['ipv6_binds_v4'],
                        upnp = upnp_type, randomizer = config['random_port'])
    except socketerror, e:
        failed("Couldn't listen - " + str(e))
        return

    response = get_response(config['responsefile'], config['url'], failed)
    if not response:
        return

    infohash = sha(bencode(response['info'])).digest()

    d = BT1Download(statusfunc, finfunc, errorfunc, exchandler, doneflag,
                    config, response, infohash, myid, rawserver, listen_port)

    if not d.saveAs(filefunc):
        return

    if pathFunc:
        pathFunc(d.getFilename())

    hashcheck = d.initFiles(old_style = True)
    if not hashcheck:
        return
    if not hashcheck():
        return
    if not d.startEngine():
        return
    d.startRerequester()
    d.autoStats()

    statusfunc(activity = 'connecting to peers')

    if paramfunc:
        paramfunc({ 'max_upload_rate' : d.setUploadRate,  # change_max_upload_rate(<int KiB/sec>)
                    'max_uploads': d.setConns, # change_max_uploads(<int max uploads>)
                    'listen_port' : listen_port, # int
                    'peer_id' : myid, # string
                    'info_hash' : infohash, # string
                    'start_connection' : d._startConnection, # start_connection((<string ip>, <int port>), <peer id>)
                    })
        
    rawserver.listen_forever(d.getPortHandler())
    
    d.shutdown()


def parse_params(params, presets = {}):
    if not params:
        return None
    config, args = parseargs(params, defaults, 0, 1, presets = presets)
    if args:
        if config['responsefile'] or config['url']:
            raise ValueError, 'must have responsefile or url as arg or parameter, not both'
        if path.isfile(args[0]):
            config['responsefile'] = args[0]
        else:
            try:
                urlparse(args[0])
            except:
                raise ValueError, 'bad filename or url'
            config['url'] = args[0]
    elif (not config['responsefile']) == (not config['url']):
        raise ValueError, 'need responsefile or url, must have one, cannot have both'
    return config


def get_usage(defaults = defaults, cols = 100, presets = {}):
    return (argslistheader + formatDefinitions(defaults, cols, presets))


def get_response(file, url, errorfunc):
    try:
        if file:
            h = open(file, 'rb')
            try:
                line = h.read(10)   # quick test to see if responsefile contains a dict
                front, garbage = line.split(':', 1)
                assert front[0] == 'd'
                int(front[1:])
            except:
                errorfunc(file+' is not a valid responsefile')
                return None
            try:
                h.seek(0)
            except:
                try:
                    h.close()
                except:
                    pass
                h = open(file, 'rb')
        else:
            try:
                h = urlopen(url)
            except:
                errorfunc(url+' bad url')
                return None
        response = h.read()
    
    except IOError, e:
        errorfunc('problem getting response info - ' + str(e))
        return None
    try:    
        h.close()
    except:
        pass
    try:
        try:
            response = bdecode(response)
        except:
            errorfunc("warning: bad data in responsefile")
            response = bdecode(response, sloppy=1)
        check_message(response)
    except ValueError, e:
        errorfunc("got bad file info - " + str(e))
        return None

    return response


class BT1Download:    
    def __init__(self, statusfunc, finfunc, errorfunc, excfunc, doneflag, 
                 config, response, infohash, id, rawserver, port, 
                 appdataobj = None):
        self.statusfunc = statusfunc
        self.finfunc = finfunc
        self.errorfunc = errorfunc
        self.excfunc = excfunc
        self.doneflag = doneflag
        self.config = config
        self.response = response
        self.infohash = infohash
        self.myid = id
        self.rawserver = rawserver
        self.port = port
        
        self.info = self.response['info']
        self.pieces = [self.info['pieces'][x:x+20]
                       for x in xrange(0, len(self.info['pieces']), 20)]
        self.len_pieces = len(self.pieces)
        self.argslistheader = argslistheader
        self.unpauseflag = Event()
        self.unpauseflag.set()
        self.downloader = None
        self.storagewrapper = None
        self.fileselector = None
        self.super_seeding_active = False
        self.filedatflag = Event()
        self.spewflag = Event()
        self.superseedflag = Event()
        self.whenpaused = None
        self.finflag = Event()
        self.rerequest = None
        self.tcp_ack_fudge = config['tcp_ack_fudge']
        
        self.selector_enabled = config['selector_enabled']
        if appdataobj:
            self.appdataobj = appdataobj
        elif self.selector_enabled:
            self.appdataobj = ConfigDir()
            self.appdataobj.deleteOldCacheData( config['expire_cache_data'],
                                                [self.infohash] )

        self.excflag = self.rawserver.get_exception_flag()
        self.failed = False
        self.checking = False
        self.started = False

        self.picker = PiecePicker(self.len_pieces, config['rarest_first_cutoff'], 
                             config['rarest_first_priority_cutoff'])
        self.choker = Choker(config, rawserver.add_task, 
                             self.picker, self.finflag.isSet)


    def checkSaveLocation(self, loc):
        if self.info.has_key('length'):
            return path.exists(loc)
        for x in self.info['files']:
            if path.exists(path.join(loc, x['path'][0])):
                return True
        return False
                

    def saveAs(self, filefunc, pathfunc = None):
        try:
            def make(f, forcedir = False):
                if not forcedir:
                    f = path.split(f)[0]
                if f != '' and not path.exists(f):
                    makedirs(f)

            if self.info.has_key('length'):
                file_length = self.info['length']
                file = filefunc(self.info['name'], file_length, 
                                self.config['saveas'], False)
                if file is None:
                    return None
                make(file)
                files = [(file, file_length)]
            else:
                file_length = 0L
                for x in self.info['files']:
                    file_length += x['length']
                file = filefunc(self.info['name'], file_length, 
                                self.config['saveas'], True)
                if file is None:
                    return None

                # if this path exists, and no files from the info dict exist, we assume it's a new download and 
                # the user wants to create a new directory with the default name
                existing = 0
                if path.exists(file):
                    if not path.isdir(file):
                        self.errorfunc(file + 'is not a dir')
                        return None
                    if listdir(file):  # if it's not empty
                        for x in self.info['files']:
                            if path.exists(path.join(file, x['path'][0])):
                                existing = 1
                        if not existing:
                            file = path.join(file, self.info['name'])
                            if path.exists(file) and not path.isdir(file):
                                if file[-8:] == '.torrent':
                                    file = file[:-8]
                                if path.exists(file) and not path.isdir(file):
                                    self.errorfunc("Can't create dir - " + self.info['name'])
                                    return None
                make(file, True)

                # alert the UI to any possible change in path
                if pathfunc != None:
                    pathfunc(file)

                files = []
                for x in self.info['files']:
                    n = file
                    for i in x['path']:
                        n = path.join(n, i)
                    files.append((n, x['length']))
                    make(n)
        except OSError, e:
            self.errorfunc("Couldn't allocate dir - " + str(e))
            return None

        self.filename = file
        self.files = files
        self.datalength = file_length

        return file
    

    def getFilename(self):
        return self.filename


    def _finished(self):
        self.finflag.set()
        try:
            self.storage.set_readonly()
        except (IOError, OSError), e:
            self.errorfunc('trouble setting readonly at end - ' + str(e))
        if self.superseedflag.isSet():
            self._set_super_seed()
        self.choker.set_round_robin_period(
            max( self.config['round_robin_period'],
                 self.config['round_robin_period'] *
                                     self.info['piece length'] / 200000 ) )
        self.rerequest_complete()
        self.finfunc()

    def _data_flunked(self, amount, index):
        self.ratemeasure_datarejected(amount)
        if not self.doneflag.isSet():
            self.errorfunc('piece %d failed hash check, re-downloading it' % index)

    def _failed(self, reason):
        self.failed = True
        self.doneflag.set()
        if reason is not None:
            self.errorfunc(reason)
        

    def initFiles(self, old_style = False, statusfunc = None):
        if self.doneflag.isSet():
            return None
        if not statusfunc:
            statusfunc = self.statusfunc

        disabled_files = None
        if self.selector_enabled:
            self.priority = self.config['priority']
            if self.priority:
                try:
                    self.priority = self.priority.split(',')
                    assert len(self.priority) == len(self.files)
                    self.priority = [int(p) for p in self.priority]
                    for p in self.priority:
                        assert p >= -1
                        assert p <= 2
                except:
                    self.errorfunc('bad priority list given, ignored')
                    self.priority = None

            data = self.appdataobj.getTorrentData(self.infohash)
            try:
                d = data['resume data']['priority']
                assert len(d) == len(self.files)
                disabled_files = [x == -1 for x in d]
            except:
                try:
                    disabled_files = [x == -1 for x in self.priority]
                except:
                    pass

        try:
            try:
                self.storage = Storage(self.files, self.info['piece length'], 
                                       self.doneflag, self.config, disabled_files)
            except IOError, e:
                self.errorfunc('trouble accessing files - ' + str(e))
                return None
            if self.doneflag.isSet():
                return None

            self.storagewrapper = StorageWrapper(self.storage, self.config['download_slice_size'], 
                self.pieces, self.info['piece length'], self._finished, self._failed, 
                statusfunc, self.doneflag, self.config['check_hashes'], 
                self._data_flunked, self.rawserver.add_task, 
                self.config, self.unpauseflag)
            
        except ValueError, e:
            self._failed('bad data - ' + str(e))
        except IOError, e:
            self._failed('IOError - ' + str(e))
        if self.doneflag.isSet():
            return None

        if self.selector_enabled:
            self.fileselector = FileSelector(self.files, self.info['piece length'], 
                                             self.appdataobj.getPieceDir(self.infohash), 
                                             self.storage, self.storagewrapper, 
                                             self.rawserver.add_task, 
                                             self._failed)
            if data:
                data = data.get('resume data')
                if data:
                    self.fileselector.unpickle(data)
                
        self.checking = True
        if old_style:
            return self.storagewrapper.old_style_init()
        return self.storagewrapper.initialize


    def getCachedTorrentData(self):
        return self.appdataobj.getTorrentData(self.infohash)


    def _make_upload(self, connection, ratelimiter, totalup):
        return Upload(connection, ratelimiter, totalup, 
                      self.choker, self.storagewrapper, self.picker, 
                      self.config)

    def _kick_peer(self, connection):
        def k(connection = connection):
            connection.close()
        self.rawserver.add_task(k, 0)

    def _ban_peer(self, ip):
        self.encoder_ban(ip)

    def _received_raw_data(self, x):
        if self.tcp_ack_fudge:
            x = int(x*self.tcp_ack_fudge)
            self.ratelimiter.adjust_sent(x)
#            self.upmeasure.update_rate(x)

    def _received_data(self, x):
        self.downmeasure.update_rate(x)
        self.ratemeasure.data_came_in(x)

    def _received_http_data(self, x):
        self.downmeasure.update_rate(x)
        self.ratemeasure.data_came_in(x)
        self.downloader.external_data_received(x)

    def _cancelfunc(self, pieces):
        self.downloader.cancel_piece_download(pieces)
        self.httpdownloader.cancel_piece_download(pieces)
    def _reqmorefunc(self, pieces):
        self.downloader.requeue_piece_download(pieces)

    def startEngine(self, ratelimiter = None, statusfunc = None):
        if self.doneflag.isSet():
            return False
        if not statusfunc:
            statusfunc = self.statusfunc

        self.checking = False

        for i in xrange(self.len_pieces):
            if self.storagewrapper.do_I_have(i):
                self.picker.complete(i)
        self.upmeasure = Measure(self.config['max_rate_period'], 
                            self.config['upload_rate_fudge'])
        self.downmeasure = Measure(self.config['max_rate_period'])

        if ratelimiter:
            self.ratelimiter = ratelimiter
        else:
            self.ratelimiter = RateLimiter(self.rawserver.add_task, 
                                           self.config['upload_unit_size'], 
                                           self.setConns)
            self.ratelimiter.set_upload_rate(self.config['max_upload_rate'])
        
        self.ratemeasure = RateMeasure()
        self.ratemeasure_datarejected = self.ratemeasure.data_rejected

        self.downloader = Downloader(self.storagewrapper, self.picker, 
            self.config['request_backlog'], self.config['max_rate_period'], 
            self.len_pieces, self.config['download_slice_size'], 
            self._received_data, self.config['snub_time'], self.config['auto_kick'], 
            self._kick_peer, self._ban_peer)
        self.downloader.set_download_rate(self.config['max_download_rate'])
        self.connecter = Connecter(self._make_upload, self.downloader, self.choker, 
                            self.len_pieces, self.upmeasure, self.config, 
                            self.ratelimiter, self.rawserver.add_task)
        self.encoder = Encoder(self.connecter, self.rawserver, 
            self.myid, self.config['max_message_length'], self.rawserver.add_task, 
            self.config['keepalive_interval'], self.infohash, 
            self._received_raw_data, self.config)
        self.encoder_ban = self.encoder.ban

        self.httpdownloader = HTTPDownloader(self.storagewrapper, self.picker, 
            self.rawserver, self.finflag, self.errorfunc, self.downloader, 
            self.config['max_rate_period'], self.infohash, self._received_http_data, 
            self.connecter.got_piece)
        if self.response.has_key('httpseeds') and not self.finflag.isSet():
            for u in self.response['httpseeds']:
                self.httpdownloader.make_download(u)

        if self.selector_enabled:
            self.fileselector.tie_in(self.picker, self._cancelfunc, self._reqmorefunc)
            if self.priority:
                self.fileselector.set_priorities_now(self.priority)
            self.appdataobj.deleteTorrentData(self.infohash)
                                # erase old data once you've started modifying it
        self.started = True
        return True


    def rerequest_complete(self):
        if self.rerequest:
            self.rerequest.announce(1)

    def rerequest_stopped(self):
        if self.rerequest:
            self.rerequest.announce(2)

    def rerequest_lastfailed(self):
        if self.rerequest:
            return self.rerequest.last_failed
        return False

    def startRerequester(self):
        if self.response.has_key('announce-list'):
            trackerlist = self.response['announce-list']
        else:
            trackerlist = [[self.response['announce']]]

        self.rerequest = Rerequester(trackerlist, self.config['rerequest_interval'], 
            self.rawserver.add_task, self.connecter.how_many_connections, 
            self.config['min_peers'], self.encoder.start_connections, 
            self.rawserver.add_task, self.storagewrapper.get_amount_left, 
            self.upmeasure.get_total, self.downmeasure.get_total, self.port, self.config['ip'], 
            self.myid, self.infohash, self.config['http_timeout'], 
            self.errorfunc, self.excfunc, self.config['max_initiate'], 
            self.doneflag, self.upmeasure.get_rate, self.downmeasure.get_rate, 
            self.unpauseflag)

        self.rerequest.start()


    def _init_stats(self):
        self.statistics = Statistics(self.upmeasure, self.downmeasure, 
                    self.connecter, self.httpdownloader, self.ratelimiter, 
                    self.rerequest_lastfailed, self.filedatflag)
        if self.info.has_key('files'):
            self.statistics.set_dirstats(self.files, self.info['piece length'])
        if self.config['spew']:
            self.spewflag.set()

    def autoStats(self, displayfunc = None):
        if not displayfunc:
            displayfunc = self.statusfunc

        self._init_stats()
        DownloaderFeedback(self.choker, self.httpdownloader, self.rawserver.add_task, 
            self.upmeasure.get_rate, self.downmeasure.get_rate, 
            self.ratemeasure, self.storagewrapper.get_stats, 
            self.datalength, self.finflag, self.spewflag, self.statistics, 
            displayfunc, self.config['display_interval'])

    def startStats(self):
        self._init_stats()
        d = DownloaderFeedback(self.choker, self.httpdownloader, self.rawserver.add_task, 
            self.upmeasure.get_rate, self.downmeasure.get_rate, 
            self.ratemeasure, self.storagewrapper.get_stats, 
            self.datalength, self.finflag, self.spewflag, self.statistics)
        return d.gather


    def getPortHandler(self):
        return self.encoder


    def shutdown(self, torrentdata = {}):
        if self.checking or self.started:
            self.storagewrapper.sync()
            self.storage.close()
            self.rerequest_stopped()
        if self.fileselector and self.started:
            if not self.failed:
                self.fileselector.finish()
                torrentdata['resume data'] = self.fileselector.pickle()
            try:
                self.appdataobj.writeTorrentData(self.infohash, torrentdata)
            except:
                self.appdataobj.deleteTorrentData(self.infohash) # clear it
        return not self.failed and not self.excflag.isSet()
        # if returns false, you may wish to auto-restart the torrent


    def setUploadRate(self, rate):
        try:
            def s(self = self, rate = rate):
                self.config['max_upload_rate'] = rate
                self.ratelimiter.set_upload_rate(rate)
            self.rawserver.add_task(s)
        except AttributeError:
            pass

    def setConns(self, conns, conns2 = None):
        if not conns2:
            conns2 = conns
        try:
            def s(self = self, conns = conns, conns2 = conns2):
                self.config['min_uploads'] = conns
                self.config['max_uploads'] = conns2
                if (conns > 30):
                    self.config['max_initiate'] = conns + 10
            self.rawserver.add_task(s)
        except AttributeError:
            pass
        
    def setDownloadRate(self, rate):
        try:
            def s(self = self, rate = rate):
                self.config['max_download_rate'] = rate
                self.downloader.set_download_rate(rate)
            self.rawserver.add_task(s)
        except AttributeError:
            pass

    def startConnection(self, ip, port, id):
        self.encoder._start_connection((ip, port), id)
      
    def _startConnection(self, ipandport, id):
        self.encoder._start_connection(ipandport, id)
        
    def setInitiate(self, initiate):
        try:
            def s(self = self, initiate = initiate):
                self.config['max_initiate'] = initiate
            self.rawserver.add_task(s)
        except AttributeError:
            pass

    def getConfig(self):
        return self.config

    def getDefaults(self):
        return defaultargs(defaults)

    def getUsageText(self):
        return self.argslistheader

    def reannounce(self, special = None):
        try:
            def r(self = self, special = special):
                if special is None:
                    self.rerequest.announce()
                else:
                    self.rerequest.announce(specialurl = special)
            self.rawserver.add_task(r)
        except AttributeError:
            pass

    def getResponse(self):
        try:
            return self.response
        except:
            return None

#    def Pause(self):
#        try:
#            if self.storagewrapper:
#                self.rawserver.add_task(self._pausemaker, 0)
#        except:
#            return False
#        self.unpauseflag.clear()
#        return True
#
#    def _pausemaker(self):
#        self.whenpaused = clock()
#        self.unpauseflag.wait()   # sticks a monkey wrench in the main thread
#
#    def Unpause(self):
#        self.unpauseflag.set()
#        if self.whenpaused and clock()-self.whenpaused > 60:
#            def r(self = self):
#                self.rerequest.announce(3)      # rerequest automatically if paused for >60 seconds
#            self.rawserver.add_task(r)

    def Pause(self):
        if not self.storagewrapper:
            return False
        self.unpauseflag.clear()
        self.rawserver.add_task(self.onPause)
        return True

    def onPause(self):
        self.whenpaused = clock()
        if not self.downloader:
            return
        self.downloader.pause(True)
        self.encoder.pause(True)
        self.choker.pause(True)

    def Unpause(self):
        self.unpauseflag.set()
        self.rawserver.add_task(self.onUnpause)

    def onUnpause(self):
        if not self.downloader:
            return
        self.downloader.pause(False)
        self.encoder.pause(False)
        self.choker.pause(False)
        if self.rerequest and self.whenpaused and clock()-self.whenpaused > 60:
            self.rerequest.announce(3)      # rerequest automatically if paused for >60 seconds

    def set_super_seed(self):
        self.superseedflag.set()
        self.rawserver.add_task(self._set_super_seed)

    def _set_super_seed(self):
        if not self.super_seeding_active and self.finflag.isSet():
            self.super_seeding_active = True
            self.errorfunc('        ** SUPER-SEED OPERATION ACTIVE **\n' +
                           '  please set Max uploads so each peer gets 6-8 kB/s')
            def s(self = self):
                self.downloader.set_super_seed()
                self.choker.set_super_seed()
            self.rawserver.add_task(s)
            if self.finflag.isSet():        # mode started when already finished
                def r(self = self):
                    self.rerequest.announce(3)  # so after kicking everyone off, reannounce
                self.rawserver.add_task(r)

    def am_I_finished(self):
        return self.finflag.isSet()

    def get_transfer_stats(self):
        return self.upmeasure.get_total(), self.downmeasure.get_total()

########NEW FILE########
__FILENAME__ = HTTPHandler
# Written by Bram Cohen
# see LICENSE.txt for license information

from cStringIO import StringIO
from sys import stdout
import time
from clock import clock
from gzip import GzipFile
try:
    True
except:
    True = 1
    False = 0

DEBUG = False

weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

months = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

class HTTPConnection:
    def __init__(self, handler, connection):
        self.handler = handler
        self.connection = connection
        self.buf = ''
        self.closed = False
        self.done = False
        self.donereading = False
        self.next_func = self.read_type

    def get_ip(self):
        return self.connection.get_ip()

    def data_came_in(self, data):
        if self.donereading or self.next_func is None:
            return True
        self.buf += data
        while 1:
            try:
                i = self.buf.index('\n')
            except ValueError:
                return True
            val = self.buf[:i]
            self.buf = self.buf[i+1:]
            self.next_func = self.next_func(val)
            if self.donereading:
                return True
            if self.next_func is None or self.closed:
                return False

    def read_type(self, data):
        self.header = data.strip()
        words = data.split()
        if len(words) == 3:
            self.command, self.path, garbage = words
            self.pre1 = False
        elif len(words) == 2:
            self.command, self.path = words
            self.pre1 = True
            if self.command != 'GET':
                return None
        else:
            return None
        if self.command not in ('HEAD', 'GET'):
            return None
        self.headers = {}
        return self.read_header

    def read_header(self, data):
        data = data.strip()
        if data == '':
            self.donereading = True
            if self.headers.get('accept-encoding', '').find('gzip') > -1:
                self.encoding = 'gzip'
            else:
                self.encoding = 'identity'
            r = self.handler.getfunc(self, self.path, self.headers)
            if r is not None:
                self.answer(r)
            return None
        try:
            i = data.index(':')
        except ValueError:
            return None
        self.headers[data[:i].strip().lower()] = data[i+1:].strip()
        if DEBUG:
            print data[:i].strip() + ": " + data[i+1:].strip()
        return self.read_header

    def answer(self, (responsecode, responsestring, headers, data)):
        if self.closed:
            return
        if self.encoding == 'gzip':
            compressed = StringIO()
            gz = GzipFile(fileobj = compressed, mode = 'wb', compresslevel = 9)
            gz.write(data)
            gz.close()
            cdata = compressed.getvalue()
            if len(cdata) >= len(data):
                self.encoding = 'identity'
            else:
                if DEBUG:
                    print "Compressed: %i  Uncompressed: %i\n" % (len(cdata), len(data))
                data = cdata
                headers['Content-Encoding'] = 'gzip'

        # i'm abusing the identd field here, but this should be ok
        if self.encoding == 'identity':
            ident = '-'
        else:
            ident = self.encoding
        self.handler.log( self.connection.get_ip(), ident, '-',
                          self.header, responsecode, len(data),
                          self.headers.get('referer','-'),
                          self.headers.get('user-agent','-') )
        self.done = True
        r = StringIO()
        r.write('HTTP/1.0 ' + str(responsecode) + ' ' + 
            responsestring + '\r\n')
        if not self.pre1:
            headers['Content-Length'] = len(data)
            for key, value in headers.items():
                r.write(key + ': ' + str(value) + '\r\n')
            r.write('\r\n')
        if self.command != 'HEAD':
            r.write(data)
        self.connection.write(r.getvalue())
        if self.connection.is_flushed():
            self.connection.shutdown(1)

class HTTPHandler:
    def __init__(self, getfunc, minflush):
        self.connections = {}
        self.getfunc = getfunc
        self.minflush = minflush
        self.lastflush = clock()

    def external_connection_made(self, connection):
        self.connections[connection] = HTTPConnection(self, connection)

    def connection_flushed(self, connection):
        if self.connections[connection].done:
            connection.shutdown(1)

    def connection_lost(self, connection):
        ec = self.connections[connection]
        ec.closed = True
        del ec.connection
        del ec.next_func
        del self.connections[connection]

    def data_came_in(self, connection, data):
        c = self.connections[connection]
        if not c.data_came_in(data) and not c.closed:
            c.connection.shutdown(1)

    def log(self, ip, ident, username, header,
            responsecode, length, referrer, useragent):
        year, month, day, hour, minute, second, a, b, c = time.localtime(time.time())
        print '%s %s %s [%02d/%3s/%04d:%02d:%02d:%02d] "%s" %i %i "%s" "%s"' % (
            ip, ident, username, day, months[month], year, hour,
            minute, second, header, responsecode, length, referrer, useragent)
        t = clock()
        if t - self.lastflush > self.minflush:
            self.lastflush = t
            stdout.flush()

########NEW FILE########
__FILENAME__ = inifile
# Written by John Hoffman
# see LICENSE.txt for license information

'''
reads/writes a Windows-style INI file
format:

  aa = "bb"
  cc = 11

  [eee]
  ff = "gg"

decodes to:
d = { '': {'aa':'bb','cc':'11'}, 'eee': {'ff':'gg'} }

the encoder can also take this as input:

d = { 'aa': 'bb, 'cc': 11, 'eee': {'ff':'gg'} }

though it will only decode in the above format.  Keywords must be strings.
Values that are strings are written surrounded by quotes, and the decoding
routine automatically strips any.
Booleans are written as integers.  Anything else aside from string/int/float
may have unpredictable results.
'''

from traceback import print_exc
from types import DictType, StringType
try:
    from types import BooleanType
except ImportError:
    BooleanType = None

try:
    True
except:
    True = 1
    False = 0

DEBUG = False

def ini_write(f, d, comment=''):
    try:
        a = {'':{}}
        for k, v in d.items():
            assert type(k) == StringType
            k = k.lower()
            if type(v) == DictType:
                if DEBUG:
                    print 'new section:' +k
                if k:
                    assert not a.has_key(k)
                    a[k] = {}
                aa = a[k]
                for kk, vv in v:
                    assert type(kk) == StringType
                    kk = kk.lower()
                    assert not aa.has_key(kk)
                    if type(vv) == BooleanType:
                        vv = int(vv)
                    if type(vv) == StringType:
                        vv = '"'+vv+'"'
                    aa[kk] = str(vv)
                    if DEBUG:
                        print 'a['+k+']['+kk+'] = '+str(vv)
            else:
                aa = a['']
                assert not aa.has_key(k)
                if type(v) == BooleanType:
                    v = int(v)
                if type(v) == StringType:
                    v = '"'+v+'"'
                aa[k] = str(v)
                if DEBUG:
                    print 'a[\'\']['+k+'] = '+str(v)
        r = open(f, 'w')
        if comment:
            for c in comment.split('\n'):
                r.write('# '+c+'\n')
            r.write('\n')
        l = a.keys()
        l.sort()
        for k in l:
            if k:
                r.write('\n['+k+']\n')
            aa = a[k]
            ll = aa.keys()
            ll.sort()
            for kk in ll:
                r.write(kk+' = '+aa[kk]+'\n')
        success = True
    except:
        if DEBUG:
            print_exc()
        success = False
    try:
        r.close()
    except:
        pass
    return success


if DEBUG:
    def errfunc(lineno, line, err):
        print '('+str(lineno)+') '+err+': '+line
else:
    errfunc = lambda lineno, line, err: None

def ini_read(f, errfunc = errfunc):
    try:
        r = open(f, 'r')
        ll = r.readlines()
        d = {}
        dd = {'':d}
        for i in xrange(len(ll)):
            l = ll[i]
            l = l.strip()
            if not l:
                continue
            if l[0] == '#':
                continue
            if l[0] == '[':
                if l[-1] != ']':
                    errfunc(i, l, 'syntax error')
                    continue
                l1 = l[1:-1].strip().lower()
                if not l1:
                    errfunc(i, l, 'syntax error')
                    continue
                if dd.has_key(l1):
                    errfunc(i, l, 'duplicate section')
                    d = dd[l1]
                    continue
                d = {}
                dd[l1] = d
                continue
            try:
                k, v = l.split('=', 1)
            except:
                try:
                    k, v = l.split(':', 1)
                except:
                    errfunc(i, l, 'syntax error')
                    continue
            k = k.strip().lower()
            v = v.strip()
            if len(v) > 1 and ( (v[0] == '"' and v[-1] == '"') or
                                (v[0] == "'" and v[-1] == "'") ):
                v = v[1:-1]
            if not k:
                errfunc(i, l, 'syntax error')
                continue
            if d.has_key(k):
                errfunc(i, l, 'duplicate entry')
                continue
            d[k] = v
        if DEBUG:
            print dd
    except:
        if DEBUG:
            print_exc()
        dd = None
    try:
        r.close()
    except:
        pass
    return dd

########NEW FILE########
__FILENAME__ = iprangeparse
# Written by John Hoffman
# see LICENSE.txt for license information

from bisect import bisect, insort

try:
    True
except:
    True = 1
    False = 0
    bool = lambda x: not not x


def to_long_ipv4(ip):
    ip = ip.split('.')
    if len(ip) != 4:
        raise ValueError, "bad address"
    b = 0L
    for n in ip:
        b *= 256
        b += int(n)
    return b


def to_long_ipv6(ip):
    if not ip:
        raise ValueError, "bad address"
    if ip == '::':      # boundary handling
        ip = ''
    elif ip[:2] == '::':
        ip = ip[1:]
    elif ip[0] == ':':
        raise ValueError, "bad address"
    elif ip[-2:] == '::':
        ip = ip[:-1]
    elif ip[-1] == ':':
        raise ValueError, "bad address"

    b = []
    doublecolon = False
    for n in ip.split(':'):
        if n == '':     # double-colon
            if doublecolon:
                raise ValueError, "bad address"
            doublecolon = True
            b.append(None)
            continue
        if n.find('.') >= 0: # IPv4
            n = n.split('.')
            if len(n) != 4:
                raise ValueError, "bad address"
            for i in n:
                b.append(int(i))
            continue
        n = ('0'*(4-len(n))) + n
        b.append(int(n[:2], 16))
        b.append(int(n[2:], 16))
    bb = 0L
    for n in b:
        if n is None:
            for i in xrange(17-len(b)):
                bb *= 256
            continue
        bb *= 256
        bb += n
    return bb

ipv4addrmask = 65535L*256*256*256*256

class IP_List:
    def __init__(self):
        self.ipv4list = []  # starts of ranges
        self.ipv4dict = {}  # start: end of ranges
        self.ipv6list = []  # "
        self.ipv6dict = {}  # "

    def __nonzero__(self):
        return bool(self.ipv4list or self.ipv6list)


    def append(self, ip_beg, ip_end = None):
        if ip_end is None:
            ip_end = ip_beg
        else:
            assert ip_beg <= ip_end
        if ip_beg.find(':') < 0:        # IPv4
            ip_beg = to_long_ipv4(ip_beg)
            ip_end = to_long_ipv4(ip_end)
            l = self.ipv4list
            d = self.ipv4dict
        else:
            ip_beg = to_long_ipv6(ip_beg)
            ip_end = to_long_ipv6(ip_end)
            bb = ip_beg % (256*256*256*256)
            if bb == ipv4addrmask:
                ip_beg -= bb
                ip_end -= bb
                l = self.ipv4list
                d = self.ipv4dict
            else:
                l = self.ipv6list
                d = self.ipv6dict

        pos = bisect(l, ip_beg)-1
        done = pos < 0
        while not done:
            p = pos
            while p < len(l):
                range_beg = l[p]
                if range_beg > ip_end+1:
                    done = True
                    break
                range_end = d[range_beg]
                if range_end < ip_beg-1:
                    p += 1
                    if p == len(l):
                        done = True
                        break
                    continue
                # if neither of the above conditions is true, the ranges overlap
                ip_beg = min(ip_beg, range_beg)
                ip_end = max(ip_end, range_end)
                del l[p]
                del d[range_beg]
                break

        insort(l, ip_beg)
        d[ip_beg] = ip_end


    def includes(self, ip):
        if not (self.ipv4list or self.ipv6list):
            return False
        if ip.find(':') < 0:        # IPv4
            ip = to_long_ipv4(ip)
            l = self.ipv4list
            d = self.ipv4dict
        else:
            ip = to_long_ipv6(ip)
            bb = ip % (256*256*256*256)
            if bb == ipv4addrmask:
                ip -= bb
                l = self.ipv4list
                d = self.ipv4dict
            else:
                l = self.ipv6list
                d = self.ipv6dict
        for ip_beg in l[bisect(l, ip)-1:]:
            if ip == ip_beg:
                return True
            ip_end = d[ip_beg]
            if ip > ip_beg and ip <= ip_end:
                return True
        return False


    # reads a list from a file in the format 'whatever:whatever:ip-ip'
    # (not IPv6 compatible at all)
    def read_rangelist(self, file):
        f = open(file, 'r')
        while 1:
            line = f.readline()
            if not line:
                break
            line = line.strip()
            if not line or line[0] == '#':
                continue
            line = line.split(':')[-1]
            try:
                ip1, ip2 = line.split('-')
            except:
                ip1 = line
                ip2 = line
            try:
                self.append(ip1.strip(), ip2.strip())
            except:
                print '*** WARNING *** could not parse IP range: '+line
        f.close()

def is_ipv4(ip):
    return ip.find(':') < 0

def is_valid_ip(ip):
    try:
        if is_ipv4(ip):
            a = ip.split('.')
            assert len(a) == 4
            for i in a:
                chr(int(i))
            return True
        to_long_ipv6(ip)
        return True
    except:
        return False

########NEW FILE########
__FILENAME__ = launchmanycore
#!/usr/bin/env python

# Written by John Hoffman
# see LICENSE.txt for license information

from BitTornado import PSYCO
if PSYCO.psyco:
    try:
        import psyco
        assert psyco.__version__ >= 0x010100f0
        psyco.full()
    except:
        pass

from download_bt1 import BT1Download
from RawServer import RawServer 
from SocketHandler import UPnP_ERROR
from RateLimiter import RateLimiter
from ServerPortHandler import MultiHandler
from parsedir import parsedir
from natpunch import UPnP_test
from random import seed
from socket import error as socketerror
from threading import Event
import sys, os
from clock import clock
from __init__ import createPeerID, mapbase64
from cStringIO import StringIO
from traceback import print_exc

try:
    True
except:
    True = 1
    False = 0


def fmttime(n):
    try:
        n = int(n)  # n may be None or too large
        assert n < 5184000  # 60 days
    except:
        return 'downloading'
    m, s = divmod(n, 60)
    h, m = divmod(m, 60)
    return '%d:%02d:%02d' % (h, m, s)

class SingleDownload:
    def __init__(self, controller, hash, response, config, myid):       
        self.controller = controller
        self.hash = hash
        self.response = response
        self.config = config
        
        self.doneflag = Event()
        self.waiting = True
        self.checking = False
        self.working = False
        self.seed = False
        self.closed = False

        self.status_msg = ''
        self.status_err = ['']
        self.status_errtime = 0
        self.status_done = 0.0

        self.rawserver = controller.handler.newRawServer(hash, self.doneflag)

        d = BT1Download(self.display,
                        self.finished,
                        self.error, 
                        controller.exchandler,
                        self.doneflag,
                        config,
                        response, 
                        hash,
                        myid,
                        self.rawserver,
                        controller.listen_port)
        self.d = d

    def start(self):
        if not self.d.saveAs(self.saveAs):
            self._shutdown()
            return
        self._hashcheckfunc = self.d.initFiles()
        if not self._hashcheckfunc:
            self._shutdown()
            return
        self.controller.hashchecksched(self.hash)


    def saveAs(self, name, length, saveas, isdir):
        return self.controller.saveAs(self.hash, name, saveas, isdir)

    def hashcheck_start(self, donefunc):
        if self.is_dead():
            self._shutdown()
            return
        self.waiting = False
        self.checking = True
        self._hashcheckfunc(donefunc)

    def hashcheck_callback(self):
        self.checking = False
        if self.is_dead():
            self._shutdown()
            return
        if not self.d.startEngine(ratelimiter = self.controller.ratelimiter):
            self._shutdown()
            return
        self.d.startRerequester()
        self.statsfunc = self.d.startStats()
        self.rawserver.start_listening(self.d.getPortHandler())
        self.working = True

    def is_dead(self):
        return self.doneflag.isSet()

    def _shutdown(self):
        self.shutdown(False)

    def shutdown(self, quiet=True):
        if self.closed:
            return
        self.doneflag.set()
        self.rawserver.shutdown()
        if self.checking or self.working:
            self.d.shutdown()
        self.waiting = False
        self.checking = False
        self.working = False
        self.closed = True
        self.controller.was_stopped(self.hash)
        if not quiet:
            self.controller.died(self.hash)
            

    def display(self, activity = None, fractionDone = None):
        # really only used by StorageWrapper now
        if activity:
            self.status_msg = activity
        if fractionDone is not None:
            self.status_done = float(fractionDone)

    def finished(self):
        self.seed = True

    def error(self, msg):
        if self.doneflag.isSet():
            self._shutdown()
        self.status_err.append(msg)
        self.status_errtime = clock()


class LaunchMany:
    def __init__(self, config, Output):
        try:
            self.config = config
            self.Output = Output

            self.torrent_dir = config['torrent_dir']
            self.torrent_cache = {}
            self.file_cache = {}
            self.blocked_files = {}
            self.scan_period = config['parse_dir_interval']
            self.stats_period = config['display_interval']

            self.torrent_list = []
            self.downloads = {}
            self.counter = 0
            self.doneflag = Event()

            self.hashcheck_queue = []
            self.hashcheck_current = None
            
            self.rawserver = RawServer(self.doneflag,
                                       config['timeout_check_interval'],
                                       config['timeout'],
                                       ipv6_enable = config['ipv6_enabled'],
                                       failfunc = self.failed,
                                       errorfunc = self.exchandler)
            upnp_type = UPnP_test(config['upnp_nat_access'])
            while 1:
                try:
                    self.listen_port = self.rawserver.find_and_bind(
                                    config['minport'], config['maxport'], config['bind'], 
                                    ipv6_socket_style = config['ipv6_binds_v4'], 
                                    upnp = upnp_type, randomizer = config['random_port'])
                    break
                except socketerror, e:
                    if upnp_type and e == UPnP_ERROR:
                        self.Output.message('WARNING: COULD NOT FORWARD VIA UPnP')
                        upnp_type = 0
                        continue
                    self.failed("Couldn't listen - " + str(e))
                    return

            self.ratelimiter = RateLimiter(self.rawserver.add_task, 
                                           config['upload_unit_size'])
            self.ratelimiter.set_upload_rate(config['max_upload_rate'])

            self.handler = MultiHandler(self.rawserver, self.doneflag)
            seed(createPeerID())
            self.rawserver.add_task(self.scan, 0)
            self.rawserver.add_task(self.stats, 0)

            self.start()
        except:
            data = StringIO()
            print_exc(file = data)
            Output.exception(data.getvalue())

    def start(self):
        try:
            self.handler.listen_forever()
        except:
            data = StringIO()
            print_exc(file=data)
            self.Output.exception(data.getvalue())
        
        self.hashcheck_queue = []
        for hash in self.torrent_list:
            self.Output.message('dropped "'+self.torrent_cache[hash]['path']+'"')
            self.downloads[hash].shutdown()
                
        self.rawserver.shutdown()

    def scan(self):
        self.rawserver.add_task(self.scan, self.scan_period)
                                
        r = parsedir(self.torrent_dir, self.torrent_cache, 
                     self.file_cache, self.blocked_files, 
                     return_metainfo = True, errfunc = self.Output.message)

        ( self.torrent_cache, self.file_cache, self.blocked_files,
            added, removed ) = r

        for hash, data in removed.items():
            self.Output.message('dropped "'+data['path']+'"')
            self.remove(hash)
        for hash, data in added.items():
            self.Output.message('added "'+data['path']+'"')
            self.add(hash, data)

    def stats(self):
        self.rawserver.add_task(self.stats, self.stats_period)
        data = []
        for hash in self.torrent_list:
            cache = self.torrent_cache[hash]
            if self.config['display_path']:
                name = cache['path']
            else:
                name = cache['name']
            size = cache['length']
            d = self.downloads[hash]
            progress = '0.0%'
            peers = 0
            seeds = 0
            seedsmsg = "S"
            dist = 0.0
            uprate = 0.0
            dnrate = 0.0
            upamt = 0
            dnamt = 0
            t = 0
            if d.is_dead():
                status = 'stopped'
            elif d.waiting:
                status = 'waiting for hash check'
            elif d.checking:
                status = d.status_msg
                progress = '%.1f%%' % (d.status_done*100)
            else:
                stats = d.statsfunc()
                s = stats['stats']
                if d.seed:
                    status = 'seeding'
                    progress = '100.0%'
                    seeds = s.numOldSeeds
                    seedsmsg = "s"
                    dist = s.numCopies
                else:
                    if s.numSeeds + s.numPeers:
                        t = stats['time']
                        if t == 0:  # unlikely
                            t = 0.01
                        status = fmttime(t)
                    else:
                        t = -1
                        status = 'connecting to peers'
                    progress = '%.1f%%' % (int(stats['frac']*1000)/10.0)
                    seeds = s.numSeeds
                    dist = s.numCopies2
                    dnrate = stats['down']
                peers = s.numPeers
                uprate = stats['up']
                upamt = s.upTotal
                dnamt = s.downTotal
                   
            if d.is_dead() or d.status_errtime+300 > clock():
                msg = d.status_err[-1]
            else:
                msg = ''

            data.append(( name, status, progress, peers, seeds, seedsmsg, dist,
                          uprate, dnrate, upamt, dnamt, size, t, msg ))
        stop = self.Output.display(data)
        if stop:
            self.doneflag.set()

    def remove(self, hash):
        self.torrent_list.remove(hash)
        self.downloads[hash].shutdown()
        del self.downloads[hash]
        
    def add(self, hash, data):
        c = self.counter
        self.counter += 1
        x = ''
        for i in xrange(3):
            x = mapbase64[c & 0x3F]+x
            c >>= 6
        peer_id = createPeerID(x)
        d = SingleDownload(self, hash, data['metainfo'], self.config, peer_id)
        self.torrent_list.append(hash)
        self.downloads[hash] = d
        d.start()
        return d


    def saveAs(self, hash, name, saveas, isdir):
        x = self.torrent_cache[hash]
        style = self.config['saveas_style']
        if style == 1 or style == 3:
            if saveas:
                saveas = os.path.join(saveas, x['file'][:-1-len(x['type'])])
            else:
                saveas = x['path'][:-1-len(x['type'])]
            if style == 3:
                if not os.path.isdir(saveas):
                    try:
                        os.mkdir(saveas)
                    except:
                        raise OSError("couldn't create directory for "+x['path']
                                      +" ("+saveas+")")
                if not isdir:
                    saveas = os.path.join(saveas, name)
        else:
            if saveas:
                saveas = os.path.join(saveas, name)
            else:
                saveas = os.path.join(os.path.split(x['path'])[0], name)
                
        if isdir and not os.path.isdir(saveas):
            try:
                os.mkdir(saveas)
            except:
                raise OSError("couldn't create directory for "+x['path']
                                      +" ("+saveas+")")
        return saveas


    def hashchecksched(self, hash = None):
        if hash:
            self.hashcheck_queue.append(hash)
            # Check smallest torrents first
            self.hashcheck_queue.sort(lambda x, y: cmp(self.downloads[x].d.datalength, self.downloads[y].d.datalength))
        if not self.hashcheck_current:
            self._hashcheck_start()

    def _hashcheck_start(self):
        self.hashcheck_current = self.hashcheck_queue.pop(0)
        self.downloads[self.hashcheck_current].hashcheck_start(self.hashcheck_callback)

    def hashcheck_callback(self):
        self.downloads[self.hashcheck_current].hashcheck_callback()
        if self.hashcheck_queue:
            self._hashcheck_start()
        else:
            self.hashcheck_current = None

    def died(self, hash):
        if self.torrent_cache.has_key(hash):
            self.Output.message('DIED: "'+self.torrent_cache[hash]['path']+'"')
        
    def was_stopped(self, hash):
        try:
            self.hashcheck_queue.remove(hash)
        except:
            pass
        if self.hashcheck_current == hash:
            self.hashcheck_current = None
            if self.hashcheck_queue:
                self._hashcheck_start()

    def failed(self, s):
        self.Output.message('FAILURE: '+s)

    def exchandler(self, s):
        self.Output.exception(s)

########NEW FILE########
__FILENAME__ = natpunch
# Written by John Hoffman
# derived from NATPortMapping.py by Yejun Yang
# and from example code by Myers Carpenter
# see LICENSE.txt for license information

import socket
from traceback import print_exc
from subnetparse import IP_List
from clock import clock
from __init__ import createPeerID
try:
    True
except:
    True = 1
    False = 0

DEBUG = False

EXPIRE_CACHE = 30 # seconds
ID = "BT-"+createPeerID()[-4:]

try:
    import pythoncom, win32com.client
    _supported = 1
except ImportError:
    _supported = 0



class _UPnP1:   # derived from Myers Carpenter's code
                # seems to use the machine's local UPnP
                # system for its operation.  Runs fairly fast

    def __init__(self):
        self.map = None
        self.last_got_map = -10e10

    def _get_map(self):
        if self.last_got_map + EXPIRE_CACHE < clock():
            try:
                dispatcher = win32com.client.Dispatch("HNetCfg.NATUPnP")
                self.map = dispatcher.StaticPortMappingCollection
                self.last_got_map = clock()
            except:
                self.map = None
        return self.map

    def test(self):
        try:
            assert self._get_map()     # make sure a map was found
            success = True
        except:
            success = False
        return success


    def open(self, ip, p):
        map = self._get_map()
        try:
            map.Add(p, 'TCP', p, ip, True, ID)
            if DEBUG:
                print 'port opened: '+ip+':'+str(p)
            success = True
        except:
            if DEBUG:
                print "COULDN'T OPEN "+str(p)
                print_exc()
            success = False
        return success


    def close(self, p):
        map = self._get_map()
        try:
            map.Remove(p, 'TCP')
            success = True
            if DEBUG:
                print 'port closed: '+str(p)
        except:
            if DEBUG:
                print 'ERROR CLOSING '+str(p)
                print_exc()
            success = False
        return success


    def clean(self, retry = False):
        if not _supported:
            return
        try:
            map = self._get_map()
            ports_in_use = []
            for i in xrange(len(map)):
                try:
                    mapping = map[i]
                    port = mapping.ExternalPort
                    prot = str(mapping.Protocol).lower()
                    desc = str(mapping.Description).lower()
                except:
                    port = None
                if port and prot == 'tcp' and desc[:3] == 'bt-':
                    ports_in_use.append(port)
            success = True
            for port in ports_in_use:
                try:
                    map.Remove(port, 'TCP')
                except:
                    success = False
            if not success and not retry:
                self.clean(retry = True)
        except:
            pass


class _UPnP2:   # derived from Yejun Yang's code
                # apparently does a direct search for UPnP hardware
                # may work in some cases where _UPnP1 won't, but is slow
                # still need to implement "clean" method

    def __init__(self):
        self.services = None
        self.last_got_services = -10e10
                           
    def _get_services(self):
        if not self.services or self.last_got_services + EXPIRE_CACHE < clock():
            self.services = []
            try:
                f=win32com.client.Dispatch("UPnP.UPnPDeviceFinder")
                for t in ( "urn:schemas-upnp-org:service:WANIPConnection:1",
                           "urn:schemas-upnp-org:service:WANPPPConnection:1" ):
                    try:
                        conns = f.FindByType(t, 0)
                        for c in xrange(len(conns)):
                            try:
                                svcs = conns[c].Services
                                for s in xrange(len(svcs)):
                                    try:
                                        self.services.append(svcs[s])
                                    except:
                                        pass
                            except:
                                pass
                    except:
                        pass
            except:
                pass
            self.last_got_services = clock()
        return self.services

    def test(self):
        try:
            assert self._get_services()    # make sure some services can be found
            success = True
        except:
            success = False
        return success


    def open(self, ip, p):
        svcs = self._get_services()
        success = False
        for s in svcs:
            try:
                s.InvokeAction('AddPortMapping', ['', p, 'TCP', p, ip, True, ID, 0], '')
                success = True
            except:
                pass
        if DEBUG and not success:
            print "COULDN'T OPEN "+str(p)
            print_exc()
        return success


    def close(self, p):
        svcs = self._get_services()
        success = False
        for s in svcs:
            try:
                s.InvokeAction('DeletePortMapping', ['', p, 'TCP'], '')
                success = True
            except:
                pass
        if DEBUG and not success:
            print "COULDN'T OPEN "+str(p)
            print_exc()
        return success


class _UPnP:    # master holding class
    def __init__(self):
        self.upnp1 = _UPnP1()
        self.upnp2 = _UPnP2()
        self.upnplist = (None, self.upnp1, self.upnp2)
        self.upnp = None
        self.local_ip = None
        self.last_got_ip = -10e10
        
    def get_ip(self):
        if self.last_got_ip + EXPIRE_CACHE < clock():
            local_ips = IP_List()
            local_ips.set_intranet_addresses()
            try:
                for info in socket.getaddrinfo(socket.gethostname(), 0, socket.AF_INET):
                            # exception if socket library isn't recent
                    self.local_ip = info[4][0]
                    if local_ips.includes(self.local_ip):
                        self.last_got_ip = clock()
                        if DEBUG:
                            print 'Local IP found: '+self.local_ip
                        break
                else:
                    raise ValueError('couldn\'t find intranet IP')
            except:
                self.local_ip = None
                if DEBUG:
                    print 'Error finding local IP'
                    print_exc()
        return self.local_ip

    def test(self, upnp_type):
        if DEBUG:
            print 'testing UPnP type '+str(upnp_type)
        if not upnp_type or not _supported or self.get_ip() is None:
            if DEBUG:
                print 'not supported'
            return 0
        pythoncom.CoInitialize()                # leave initialized
        self.upnp = self.upnplist[upnp_type]    # cache this
        if self.upnp.test():
            if DEBUG:
                print 'ok'
            return upnp_type
        if DEBUG:
            print 'tested bad'
        return 0

    def open(self, p):
        assert self.upnp, "must run UPnP_test() with the desired UPnP access type first"
        return self.upnp.open(self.get_ip(), p)

    def close(self, p):
        assert self.upnp, "must run UPnP_test() with the desired UPnP access type first"
        return self.upnp.close(p)

    def clean(self):
        return self.upnp1.clean()

_upnp_ = _UPnP()

UPnP_test = _upnp_.test
UPnP_open_port = _upnp_.open
UPnP_close_port = _upnp_.close
UPnP_reset = _upnp_.clean


########NEW FILE########
__FILENAME__ = parseargs
# Written by Bill Bumgarner and Bram Cohen
# see LICENSE.txt for license information

from types import *
from cStringIO import StringIO


def splitLine(line, COLS=80, indent=10):
    indent = " " * indent
    width = COLS - (len(indent) + 1)
    if indent and width < 15:
        width = COLS - 2
        indent = " "
    s = StringIO()
    i = 0
    for word in line.split():
        if i == 0:
            s.write(indent+word)
            i = len(word)
            continue
        if i + len(word) >= width:
            s.write('\n'+indent+word)
            i = len(word)
            continue
        s.write(' '+word)
        i += len(word) + 1
    return s.getvalue()

def formatDefinitions(options, COLS, presets = {}):
    s = StringIO()
    for (longname, default, doc) in options:
        s.write('--' + longname + ' <arg>\n')
        default = presets.get(longname, default)
        if type(default) in (IntType, LongType):
            try:
                default = int(default)
            except:
                pass
        if default is not None:
            doc += ' (defaults to ' + repr(default) + ')'
        s.write(splitLine(doc, COLS, 10))
        s.write('\n\n')
    return s.getvalue()


def usage(string):
    raise ValueError(string)


def defaultargs(options):
    l = {}
    for (longname, default, doc) in options:
        if default is not None:
            l[longname] = default
    return l
        

def parseargs(argv, options, minargs = None, maxargs = None, presets = {}):
    config = {}
    longkeyed = {}
    for option in options:
        longname, default, doc = option
        longkeyed[longname] = option
        config[longname] = default
    for longname in presets.keys():        # presets after defaults but before arguments
        config[longname] = presets[longname]
    options = []
    args = []
    pos = 0
    while pos < len(argv):
        if argv[pos][:2] != '--':
            args.append(argv[pos])
            pos += 1
        else:
            if pos == len(argv) - 1:
                usage('parameter passed in at end with no value')
            key, value = argv[pos][2:], argv[pos+1]
            pos += 2
            if not longkeyed.has_key(key):
                usage('unknown key --' + key)
            longname, default, doc = longkeyed[key]
            try:
                t = type(config[longname])
                if t is NoneType or t is StringType:
                    config[longname] = value
                elif t in (IntType, LongType):
                    config[longname] = long(value)
                elif t is FloatType:
                    config[longname] = float(value)
                else:
                    assert 0
            except ValueError, e:
                usage('wrong format of --%s - %s' % (key, str(e)))
    for key, value in config.items():
        if value is None:
            usage("Option --%s is required." % key)
    if minargs is not None and len(args) < minargs:
        usage("Must supply at least %d args." % minargs)
    if maxargs is not None and len(args) > maxargs:
        usage("Too many args - %d max." % maxargs)
    return (config, args)

def test_parseargs():
    assert parseargs(('d', '--a', 'pq', 'e', '--b', '3', '--c', '4.5', 'f'), (('a', 'x', ''), ('b', 1, ''), ('c', 2.3, ''))) == ({'a': 'pq', 'b': 3, 'c': 4.5}, ['d', 'e', 'f'])
    assert parseargs([], [('a', 'x', '')]) == ({'a': 'x'}, [])
    assert parseargs(['--a', 'x', '--a', 'y'], [('a', '', '')]) == ({'a': 'y'}, [])
    try:
        parseargs([], [('a', 'x', '')])
    except ValueError:
        pass
    try:
        parseargs(['--a', 'x'], [])
    except ValueError:
        pass
    try:
        parseargs(['--a'], [('a', 'x', '')])
    except ValueError:
        pass
    try:
        parseargs([], [], 1, 2)
    except ValueError:
        pass
    assert parseargs(['x'], [], 1, 2) == ({}, ['x'])
    assert parseargs(['x', 'y'], [], 1, 2) == ({}, ['x', 'y'])
    try:
        parseargs(['x', 'y', 'z'], [], 1, 2)
    except ValueError:
        pass
    try:
        parseargs(['--a', '2.0'], [('a', 3, '')])
    except ValueError:
        pass
    try:
        parseargs(['--a', 'z'], [('a', 2.1, '')])
    except ValueError:
        pass


########NEW FILE########
__FILENAME__ = parsedir
# Written by John Hoffman and Uoti Urpala
# see LICENSE.txt for license information
from bencode import bencode, bdecode
from BT1.btformats import check_info
from sha import sha
import sys, os

try:
    True
except:
    True = 1
    False = 0

NOISY = False

def _errfunc(x):
    print ":: "+x

def parsedir(directory, parsed, files, blocked,
             exts = ['.torrent'], return_metainfo = False, errfunc = _errfunc):
    if NOISY:
        errfunc('checking dir')
    dirs_to_check = [directory]
    new_files = {}
    new_blocked = {}
    torrent_type = {}
    while dirs_to_check:    # first, recurse directories and gather torrents
        directory = dirs_to_check.pop()
        newtorrents = False
        for f in os.listdir(directory):
            newtorrent = None
            for ext in exts:
                if f.endswith(ext):
                    newtorrent = ext[1:]
                    break
            if newtorrent:
                newtorrents = True
                p = os.path.join(directory, f)
                new_files[p] = [(os.path.getmtime(p), os.path.getsize(p)), 0]
                torrent_type[p] = newtorrent
        if not newtorrents:
            for f in os.listdir(directory):
                p = os.path.join(directory, f)
                if os.path.isdir(p):
                    dirs_to_check.append(p)

    new_parsed = {}
    to_add = []
    added = {}
    removed = {}
    # files[path] = [(modification_time, size), hash], hash is 0 if the file
    # has not been successfully parsed
    for p, v in new_files.items():   # re-add old items and check for changes
        oldval = files.get(p)
        if not oldval:          # new file
            to_add.append(p)
            continue
        h = oldval[1]
        if oldval[0] == v[0]:   # file is unchanged from last parse
            if h:
                if blocked.has_key(p):  # parseable + blocked means duplicate
                    to_add.append(p)    # other duplicate may have gone away
                else:
                    new_parsed[h] = parsed[h]
                new_files[p] = oldval
            else:
                new_blocked[p] = 1  # same broken unparseable file
            continue
        if parsed.has_key(h) and not blocked.has_key(p):
            if NOISY:
                errfunc('removing '+p+' (will re-add)')
            removed[h] = parsed[h]
        to_add.append(p)

    to_add.sort()
    for p in to_add:                # then, parse new and changed torrents
        new_file = new_files[p]
        v, h = new_file
        if new_parsed.has_key(h): # duplicate
            if not blocked.has_key(p) or files[p][0] != v:
                errfunc('**warning** '+
                    p +' is a duplicate torrent for '+new_parsed[h]['path'])
            new_blocked[p] = 1
            continue
                
        if NOISY:
            errfunc('adding '+p)
        try:
            ff = open(p, 'rb')
            d = bdecode(ff.read())
            check_info(d['info'])
            h = sha(bencode(d['info'])).digest()
            new_file[1] = h
            if new_parsed.has_key(h):
                errfunc('**warning** '+
                    p +' is a duplicate torrent for '+new_parsed[h]['path'])
                new_blocked[p] = 1
                continue

            a = {}
            a['path'] = p
            f = os.path.basename(p)
            a['file'] = f
            a['type'] = torrent_type[p]
            i = d['info']
            l = 0
            nf = 0
            if i.has_key('length'):
                l = i.get('length', 0)
                nf = 1
            elif i.has_key('files'):
                for li in i['files']:
                    nf += 1
                    if li.has_key('length'):
                        l += li['length']
            a['numfiles'] = nf
            a['length'] = l
            a['name'] = i.get('name', f)
            def setkey(k, d = d, a = a):
                if d.has_key(k):
                    a[k] = d[k]
            setkey('failure reason')
            setkey('warning message')
            setkey('announce-list')
            if return_metainfo:
                a['metainfo'] = d
        except:
            errfunc('**warning** '+p+' has errors')
            new_blocked[p] = 1
            continue
        try:
            ff.close()
        except:
            pass
        if NOISY:
            errfunc('... successful')
        new_parsed[h] = a
        added[h] = a

    for p, v in files.items():       # and finally, mark removed torrents
        if not new_files.has_key(p) and not blocked.has_key(p):
            if NOISY:
                errfunc('removing '+p)
            removed[v[1]] = parsed[v[1]]

    if NOISY:
        errfunc('done checking')
    return (new_parsed, new_files, new_blocked, added, removed)


########NEW FILE########
__FILENAME__ = piecebuffer
# Written by John Hoffman
# see LICENSE.txt for license information

from array import array
from threading import Lock
# import inspect
try:
    True
except:
    True = 1
    False = 0
    
DEBUG = False

class SingleBuffer:
    def __init__(self, pool):
        self.pool = pool
        self.buf = array('c')

    def init(self):
        if DEBUG:
            print self.count
            '''
            for x in xrange(6,1,-1):
                try:
                    f = inspect.currentframe(x).f_code
                    print (f.co_filename,f.co_firstlineno,f.co_name)
                    del f
                except:
                    pass
            print ''
            '''
        self.length = 0

    def append(self, s):
        l = self.length+len(s)
        self.buf[self.length:l] = array('c', s)
        self.length = l

    def __len__(self):
        return self.length

    def __getslice__(self, a, b):
        if b > self.length:
            b = self.length
        if b < 0:
            b += self.length
        if a == 0 and b == self.length and len(self.buf) == b:
            return self.buf  # optimization
        return self.buf[a:b]

    def getarray(self):
        return self.buf[:self.length]

    def release(self):
        if DEBUG:
            print -self.count
        self.pool.release(self)


class BufferPool:
    def __init__(self):
        self.pool = []
        self.lock = Lock()
        if DEBUG:
            self.count = 0

    def new(self):
        self.lock.acquire()
        if self.pool:
            x = self.pool.pop()
        else:
            x = SingleBuffer(self)
            if DEBUG:
                self.count += 1
                x.count = self.count
        x.init()
        self.lock.release()
        return x

    def release(self, x):
        self.pool.append(x)


_pool = BufferPool()
PieceBuffer = _pool.new

########NEW FILE########
__FILENAME__ = PSYCO
# edit this file to enable/disable Psyco
# psyco = 1 -- enabled
# psyco = 0 -- disabled

psyco = 0

########NEW FILE########
__FILENAME__ = RateLimiter
# Written by Bram Cohen
# see LICENSE.txt for license information

from clock import clock
from CurrentRateMeasure import Measure
from math import sqrt

try:
    True
except:
    True = 1
    False = 0
try:
    sum([1])
except:
    sum = lambda a: reduce(lambda x, y: x+y, a, 0)

DEBUG = False

MAX_RATE_PERIOD = 20.0
MAX_RATE = 10e10
PING_BOUNDARY = 1.2
PING_SAMPLES = 7
PING_DISCARDS = 1
PING_THRESHHOLD = 5
PING_DELAY = 5  # cycles 'til first upward adjustment
PING_DELAY_NEXT = 2  # 'til next
ADJUST_UP = 1.05
ADJUST_DOWN = 0.95
UP_DELAY_FIRST = 5
UP_DELAY_NEXT = 2
SLOTS_STARTING = 6
SLOTS_FACTOR = 1.66/1000

class RateLimiter:
    def __init__(self, sched, unitsize, slotsfunc = lambda x: None):
        self.sched = sched
        self.last = None
        self.unitsize = unitsize
        self.slotsfunc = slotsfunc
        self.measure = Measure(MAX_RATE_PERIOD)
        self.autoadjust = False
        self.upload_rate = MAX_RATE * 1000
        self.slots = SLOTS_STARTING    # garbage if not automatic

    def set_upload_rate(self, rate):
        # rate = -1 # test automatic
        if rate < 0:
            if self.autoadjust:
                return
            self.autoadjust = True
            self.autoadjustup = 0
            self.pings = []
            rate = MAX_RATE
            self.slots = SLOTS_STARTING
            self.slotsfunc(self.slots)
        else:
            self.autoadjust = False
        if not rate:
            rate = MAX_RATE
        self.upload_rate = rate * 1000
        self.lasttime = clock()
        self.bytes_sent = 0

    def queue(self, conn):
        assert conn.next_upload is None
        if self.last is None:
            self.last = conn
            conn.next_upload = conn
            self.try_send(True)
        else:
            conn.next_upload = self.last.next_upload
            self.last.next_upload = conn
            self.last = conn

    def try_send(self, check_time = False):
        t = clock()
        self.bytes_sent -= (t - self.lasttime) * self.upload_rate
        self.lasttime = t
        if check_time:
            self.bytes_sent = max(self.bytes_sent, 0)
        cur = self.last.next_upload
        while self.bytes_sent <= 0:
            bytes = cur.send_partial(self.unitsize)
            self.bytes_sent += bytes
            self.measure.update_rate(bytes)
            if bytes == 0 or cur.backlogged():
                if self.last is cur:
                    self.last = None
                    cur.next_upload = None
                    break
                else:
                    self.last.next_upload = cur.next_upload
                    cur.next_upload = None
                    cur = self.last.next_upload
            else:
                self.last = cur
                cur = cur.next_upload
        else:
            self.sched(self.try_send, self.bytes_sent / self.upload_rate)

    def adjust_sent(self, bytes):
        self.bytes_sent = min(self.bytes_sent+bytes, self.upload_rate*3)
        self.measure.update_rate(bytes)


    def ping(self, delay):
        if DEBUG:
            print delay
        if not self.autoadjust:
            return
        self.pings.append(delay > PING_BOUNDARY)
        if len(self.pings) < PING_SAMPLES+PING_DISCARDS:
            return
        if DEBUG:
            print 'cycle'
        pings = sum(self.pings[PING_DISCARDS:])
        del self.pings[:]
        if pings >= PING_THRESHHOLD:   # assume flooded
            if self.upload_rate == MAX_RATE:
                self.upload_rate = self.measure.get_rate()*ADJUST_DOWN
            else:
                self.upload_rate = min(self.upload_rate, 
                                       self.measure.get_rate()*1.1)
            self.upload_rate = max(int(self.upload_rate*ADJUST_DOWN), 2)
            self.slots = int(sqrt(self.upload_rate*SLOTS_FACTOR))
            self.slotsfunc(self.slots)
            if DEBUG:
                print 'adjust down to '+str(self.upload_rate)
            self.lasttime = clock()
            self.bytes_sent = 0
            self.autoadjustup = UP_DELAY_FIRST
        else:   # not flooded
            if self.upload_rate == MAX_RATE:
                return
            self.autoadjustup -= 1
            if self.autoadjustup:
                return
            self.upload_rate = int(self.upload_rate*ADJUST_UP)
            self.slots = int(sqrt(self.upload_rate*SLOTS_FACTOR))
            self.slotsfunc(self.slots)
            if DEBUG:
                print 'adjust up to '+str(self.upload_rate)
            self.lasttime = clock()
            self.bytes_sent = 0
            self.autoadjustup = UP_DELAY_NEXT





########NEW FILE########
__FILENAME__ = RateMeasure
# Written by Bram Cohen
# see LICENSE.txt for license information

from clock import clock
try:
    True
except:
    True = 1
    False = 0

FACTOR = 0.999

class RateMeasure:
    def __init__(self):
        self.last = None
        self.time = 1.0
        self.got = 0.0
        self.remaining = None
        self.broke = False
        self.got_anything = False
        self.last_checked = None
        self.rate = 0

    def data_came_in(self, amount):
        if not self.got_anything:
            self.got_anything = True
            self.last = clock()
            return
        self.update(amount)

    def data_rejected(self, amount):
        pass

    def get_time_left(self, left):
        t = clock()
        if not self.got_anything:
            return None
        if t - self.last > 15:
            self.update(0)
        try:
            remaining = left/self.rate
            delta = max(remaining/20, 2)
            if self.remaining is None:
                self.remaining = remaining
            elif abs(self.remaining-remaining) > delta:
                self.remaining = remaining
            else:
                self.remaining -= t - self.last_checked
        except ZeroDivisionError:
            self.remaining = None
        if self.remaining is not None and self.remaining < 0.1:
            self.remaining = 0.1
        self.last_checked = t
        return self.remaining

    def update(self, amount):
        t = clock()
        t1 = int(t)
        l1 = int(self.last)
        for i in xrange(l1, t1):
            self.time *= FACTOR
            self.got *= FACTOR
        self.got += amount
        if t - self.last < 20:
            self.time += t - self.last
        self.last = t
        try:
            self.rate = self.got / self.time
        except ZeroDivisionError:
            pass

########NEW FILE########
__FILENAME__ = RawServer
# Written by Bram Cohen
# see LICENSE.txt for license information

from bisect import insort
from SocketHandler import SocketHandler
import socket
from cStringIO import StringIO
from traceback import print_exc
from select import error
from threading import Event
from clock import clock
import sys
try:
    True
except:
    True = 1
    False = 0


def autodetect_ipv6():
    try:
        assert sys.version_info >= (2, 3)
        assert socket.has_ipv6
        socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    except:
        return 0
    return 1

def autodetect_socket_style():
    if sys.platform.find('linux') < 0:
        return 1
    else:
        try:
            f = open('/proc/sys/net/ipv6/bindv6only', 'r')
            dual_socket_style = int(f.read())
            f.close()
            return int(not dual_socket_style)
        except:
            return 0


READSIZE = 100000

class RawServer:
    def __init__(self, doneflag, timeout_check_interval, timeout, noisy = True,
                 ipv6_enable = True, failfunc = lambda x: None, errorfunc = None,
                 sockethandler = None, excflag = Event()):
        self.timeout_check_interval = timeout_check_interval
        self.timeout = timeout
        self.servers = {}
        self.single_sockets = {}
        self.dead_from_write = []
        self.doneflag = doneflag
        self.noisy = noisy
        self.failfunc = failfunc
        self.errorfunc = errorfunc
        self.exccount = 0
        self.funcs = []
        self.externally_added = []
        self.finished = Event()
        self.tasks_to_kill = []
        self.excflag = excflag
        
        if sockethandler is None:
            sockethandler = SocketHandler(timeout, ipv6_enable, READSIZE)
        self.sockethandler = sockethandler
        self.add_task(self.scan_for_timeouts, timeout_check_interval)

    def get_exception_flag(self):
        return self.excflag

    def _add_task(self, func, delay, id = None):
        if delay < 0:
            delay = 0
        insort(self.funcs, (clock() + delay, func, id))

    def add_task(self, func, delay = 0, id = None):
        if delay < 0:
            delay = 0
        self.externally_added.append((func, delay, id))

    def scan_for_timeouts(self):
        self.add_task(self.scan_for_timeouts, self.timeout_check_interval)
        self.sockethandler.scan_for_timeouts()

    def bind(self, port, bind = '', reuse = False,
                        ipv6_socket_style = 1, upnp = False):
        self.sockethandler.bind(port, bind, reuse, ipv6_socket_style, upnp)

    def find_and_bind(self, minport, maxport, bind = '', reuse = False, 
                      ipv6_socket_style = 1, upnp = 0, randomizer = False):
        return self.sockethandler.find_and_bind(minport, maxport, bind, reuse, 
                                 ipv6_socket_style, upnp, randomizer)

    def start_connection_raw(self, dns, socktype, handler = None):
        return self.sockethandler.start_connection_raw(dns, socktype, handler)

    def start_connection(self, dns, handler = None, randomize = False):
        return self.sockethandler.start_connection(dns, handler, randomize)

    def get_stats(self):
        return self.sockethandler.get_stats()

    def pop_external(self):
        while self.externally_added:
            (a, b, c) = self.externally_added.pop(0)
            self._add_task(a, b, c)


    def listen_forever(self, handler):
        self.sockethandler.set_handler(handler)
        try:
            while not self.doneflag.isSet():
                try:
                    self.pop_external()
                    self._kill_tasks()
                    if self.funcs:
                        period = self.funcs[0][0] + 0.001 - clock()
                    else:
                        period = 2 ** 30
                    if period < 0:
                        period = 0
                    events = self.sockethandler.do_poll(period)
                    if self.doneflag.isSet():
                        return
                    while self.funcs and self.funcs[0][0] <= clock():
                        garbage1, func, id = self.funcs.pop(0)
                        if id in self.tasks_to_kill:
                            pass
                        try:
#                            print func.func_name
                            func()
                        except (SystemError, MemoryError), e:
                            self.failfunc(str(e))
                            return
                        except KeyboardInterrupt:
#                            self.exception(True)
                            return
                        except:
                            if self.noisy:
                                self.exception()
                    self.sockethandler.close_dead()
                    self.sockethandler.handle_events(events)
                    if self.doneflag.isSet():
                        return
                    self.sockethandler.close_dead()
                except (SystemError, MemoryError), e:
                    self.failfunc(str(e))
                    return
                except error:
                    if self.doneflag.isSet():
                        return
                except KeyboardInterrupt:
#                    self.exception(True)
                    return
                except:
                    self.exception()
                if self.exccount > 10:
                    return
        finally:
#            self.sockethandler.shutdown()
            self.finished.set()

    def is_finished(self):
        return self.finished.isSet()

    def wait_until_finished(self):
        self.finished.wait()

    def _kill_tasks(self):
        if self.tasks_to_kill:
            new_funcs = []
            for (t, func, id) in self.funcs:
                if id not in self.tasks_to_kill:
                    new_funcs.append((t, func, id))
            self.funcs = new_funcs
            self.tasks_to_kill = []

    def kill_tasks(self, id):
        self.tasks_to_kill.append(id)

    def exception(self, kbint = False):
        if not kbint:
            self.excflag.set()
        self.exccount += 1
        if self.errorfunc is None:
            print_exc()
        else:
            data = StringIO()
            print_exc(file = data)
#            print data.getvalue()   # report exception here too
            if not kbint:           # don't report here if it's a keyboard interrupt
                self.errorfunc(data.getvalue())

    def shutdown(self):
        self.sockethandler.shutdown()

########NEW FILE########
__FILENAME__ = selectpoll
# Written by Bram Cohen
# see LICENSE.txt for license information

from select import select
from time import sleep
from types import IntType
from bisect import bisect
POLLIN = 1
POLLOUT = 2
POLLERR = 8
POLLHUP = 16

class poll:
    def __init__(self):
        self.rlist = []
        self.wlist = []
        
    def register(self, f, t):
        if type(f) != IntType:
            f = f.fileno()
        if (t & POLLIN):
            insert(self.rlist, f)
        else:
            remove(self.rlist, f)
        if (t & POLLOUT):
            insert(self.wlist, f)
        else:
            remove(self.wlist, f)

    def unregister(self, f):
        if type(f) != IntType:
            f = f.fileno()
        remove(self.rlist, f)
        remove(self.wlist, f)

    def poll(self, timeout = None):
        if self.rlist or self.wlist:
            try:
                r, w, e = select(self.rlist, self.wlist, [], timeout)
            except ValueError:
                return None
        else:
            sleep(timeout)
            return []
        result = []
        for s in r:
            result.append((s, POLLIN))
        for s in w:
            result.append((s, POLLOUT))
        return result

def remove(list, item):
    i = bisect(list, item)
    if i > 0 and list[i-1] == item:
        del list[i-1]

def insert(list, item):
    i = bisect(list, item)
    if i == 0 or list[i-1] != item:
        list.insert(i, item)

def test_remove():
    x = [2, 4, 6]
    remove(x, 2)
    assert x == [4, 6]
    x = [2, 4, 6]
    remove(x, 4)
    assert x == [2, 6]
    x = [2, 4, 6]
    remove(x, 6)
    assert x == [2, 4]
    x = [2, 4, 6]
    remove(x, 5)
    assert x == [2, 4, 6]
    x = [2, 4, 6]
    remove(x, 1)
    assert x == [2, 4, 6]
    x = [2, 4, 6]
    remove(x, 7)
    assert x == [2, 4, 6]
    x = [2, 4, 6]
    remove(x, 5)
    assert x == [2, 4, 6]
    x = []
    remove(x, 3)
    assert x == []

def test_insert():
    x = [2, 4]
    insert(x, 1)
    assert x == [1, 2, 4]
    x = [2, 4]
    insert(x, 3)
    assert x == [2, 3, 4]
    x = [2, 4]
    insert(x, 5)
    assert x == [2, 4, 5]
    x = [2, 4]
    insert(x, 2)
    assert x == [2, 4]
    x = [2, 4]
    insert(x, 4)
    assert x == [2, 4]
    x = [2, 3, 4]
    insert(x, 3)
    assert x == [2, 3, 4]
    x = []
    insert(x, 3)
    assert x == [3]

########NEW FILE########
__FILENAME__ = ServerPortHandler
# Written by John Hoffman
# see LICENSE.txt for license information

from cStringIO import StringIO
#from RawServer import RawServer
try:
    True
except:
    True = 1
    False = 0

from BT1.Encrypter import protocol_name

default_task_id = []

class SingleRawServer:
    def __init__(self, info_hash, multihandler, doneflag, protocol):
        self.info_hash = info_hash
        self.doneflag = doneflag
        self.protocol = protocol
        self.multihandler = multihandler
        self.rawserver = multihandler.rawserver
        self.finished = False
        self.running = False
        self.handler = None
        self.taskqueue = []

    def shutdown(self):
        if not self.finished:
            self.multihandler.shutdown_torrent(self.info_hash)

    def _shutdown(self):
        if not self.finished:
            self.finished = True
            self.running = False
            self.rawserver.kill_tasks(self.info_hash)
            if self.handler:
                self.handler.close_all()

    def _external_connection_made(self, c, options, already_read):
        if self.running:
            c.set_handler(self.handler)
            self.handler.externally_handshaked_connection_made(
                c, options, already_read)

    ### RawServer functions ###

    def add_task(self, func, delay=0, id = default_task_id):
        if id is default_task_id:
            id = self.info_hash
        if not self.finished:
            self.rawserver.add_task(func, delay, id)

#    def bind(self, port, bind = '', reuse = False):
#        pass    # not handled here
        
    def start_connection(self, dns, handler = None):
        if not handler:
            handler = self.handler
        c = self.rawserver.start_connection(dns, handler)
        return c

#    def listen_forever(self, handler):
#        pass    # don't call with this
    
    def start_listening(self, handler):
        self.handler = handler
        self.running = True
        return self.shutdown    # obviously, doesn't listen forever

    def is_finished(self):
        return self.finished

    def get_exception_flag(self):
        return self.rawserver.get_exception_flag()


class NewSocketHandler:     # hand a new socket off where it belongs
    def __init__(self, multihandler, connection):
        self.multihandler = multihandler
        self.connection = connection
        connection.set_handler(self)
        self.closed = False
        self.buffer = StringIO()
        self.complete = False
        self.next_len, self.next_func = 1, self.read_header_len
        self.multihandler.rawserver.add_task(self._auto_close, 15)

    def _auto_close(self):
        if not self.complete:
            self.close()
        
    def close(self):
        if not self.closed:
            self.connection.close()
            self.closed = True

        
#   header format:
#        connection.write(chr(len(protocol_name)) + protocol_name + 
#            (chr(0) * 8) + self.encrypter.download_id + self.encrypter.my_id)

    # copied from Encrypter and modified
    
    def read_header_len(self, s):
        l = ord(s)
        return l, self.read_header

    def read_header(self, s):
        self.protocol = s
        return 8, self.read_reserved

    def read_reserved(self, s):
        self.options = s
        return 20, self.read_download_id

    def read_download_id(self, s):
        if self.multihandler.singlerawservers.has_key(s):
            if self.multihandler.singlerawservers[s].protocol == self.protocol:
                return True
        return None

    def data_came_in(self, garbage, s):
        while 1:
            if self.closed:
                return
            i = self.next_len - self.buffer.tell()
            if i > len(s):
                self.buffer.write(s)
                return
            self.buffer.write(s[:i])
            s = s[i:]
            m = self.buffer.getvalue()
            self.buffer.reset()
            self.buffer.truncate()
            try:
                x = self.next_func(m)
            except:
                self.next_len, self.next_func = 1, self.read_dead
                raise
            if x is None:
                self.close()
                return
            if x == True:       # ready to process
                self.multihandler.singlerawservers[m]._external_connection_made(
                        self.connection, self.options, s)
                self.complete = True
                return
            self.next_len, self.next_func = x

    def connection_flushed(self, ss):
        pass

    def connection_lost(self, ss):
        self.closed = True

class MultiHandler:
    def __init__(self, rawserver, doneflag):
        self.rawserver = rawserver
        self.masterdoneflag = doneflag
        self.singlerawservers = {}
        self.connections = {}
        self.taskqueues = {}

    def newRawServer(self, info_hash, doneflag, protocol=protocol_name):
        new = SingleRawServer(info_hash, self, doneflag, protocol)
        self.singlerawservers[info_hash] = new
        return new

    def shutdown_torrent(self, info_hash):
        self.singlerawservers[info_hash]._shutdown()
        del self.singlerawservers[info_hash]

    def listen_forever(self):
        self.rawserver.listen_forever(self)
        for srs in self.singlerawservers.values():
            srs.finished = True
            srs.running = False
            srs.doneflag.set()
        
    ### RawServer handler functions ###
    # be wary of name collisions

    def external_connection_made(self, ss):
        NewSocketHandler(self, ss)

########NEW FILE########
__FILENAME__ = SocketHandler
# Written by Bram Cohen
# see LICENSE.txt for license information

import socket
from errno import EWOULDBLOCK
try:
    from select import poll, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1000
except ImportError:
    from selectpoll import poll, POLLIN, POLLOUT, POLLERR, POLLHUP
    timemult = 1
from time import sleep
from clock import clock
import sys
from random import shuffle, randrange
from natpunch import UPnP_open_port, UPnP_close_port
# from BT1.StreamCheck import StreamCheck
# import inspect
try:
    True
except:
    True = 1
    False = 0

all = POLLIN | POLLOUT

UPnP_ERROR = "unable to forward port via UPnP"

class SingleSocket:
    def __init__(self, socket_handler, sock, handler, ip = None):
        self.socket_handler = socket_handler
        self.socket = sock
        self.handler = handler
        self.buffer = []
        self.last_hit = clock()
        self.fileno = sock.fileno()
        self.connected = False
        self.skipped = 0
#        self.check = StreamCheck()
        try:
            self.ip = self.socket.getpeername()[0]
        except:
            if ip is None:
                self.ip = 'unknown'
            else:
                self.ip = ip
        
    def get_ip(self, real=False):
        if real:
            try:
                self.ip = self.socket.getpeername()[0]
            except:
                pass
        return self.ip
        
    def close(self):
        '''
        for x in xrange(5,0,-1):
            try:
                f = inspect.currentframe(x).f_code
                print (f.co_filename,f.co_firstlineno,f.co_name)
                del f
            except:
                pass
        print ''
        '''
        assert self.socket
        self.connected = False
        sock = self.socket
        self.socket = None
        self.buffer = []
        del self.socket_handler.single_sockets[self.fileno]
        self.socket_handler.poll.unregister(sock)
        sock.close()

    def shutdown(self, val):
        self.socket.shutdown(val)

    def is_flushed(self):
        return not self.buffer

    def write(self, s):
#        self.check.write(s)
        assert self.socket is not None
        self.buffer.append(s)
        if len(self.buffer) == 1:
            self.try_write()

    def try_write(self):
        if self.connected:
            dead = False
            try:
                while self.buffer:
                    buf = self.buffer[0]
                    amount = self.socket.send(buf)
                    if amount == 0:
                        self.skipped += 1
                        break
                    self.skipped = 0
                    if amount != len(buf):
                        self.buffer[0] = buf[amount:]
                        break
                    del self.buffer[0]
            except socket.error, e:
                try:
                    dead = e[0] != EWOULDBLOCK
                except:
                    dead = True
                self.skipped += 1
            if self.skipped >= 3:
                dead = True
            if dead:
                self.socket_handler.dead_from_write.append(self)
                return
        if self.buffer:
            self.socket_handler.poll.register(self.socket, all)
        else:
            self.socket_handler.poll.register(self.socket, POLLIN)

    def set_handler(self, handler):
        self.handler = handler

class SocketHandler:
    def __init__(self, timeout, ipv6_enable, readsize = 100000):
        self.timeout = timeout
        self.ipv6_enable = ipv6_enable
        self.readsize = readsize
        self.poll = poll()
        # {socket: SingleSocket}
        self.single_sockets = {}
        self.dead_from_write = []
        self.max_connects = 1000
        self.port_forwarded = None
        self.servers = {}

    def scan_for_timeouts(self):
        t = clock() - self.timeout
        tokill = []
        for s in self.single_sockets.values():
            if s.last_hit < t:
                tokill.append(s)
        for k in tokill:
            if k.socket is not None:
                self._close_socket(k)

    def bind(self, port, bind = '', reuse = False, ipv6_socket_style = 1, upnp = 0):
        port = int(port)
        addrinfos = []
        self.servers = {}
        self.interfaces = []
        # if bind != "" thread it as a comma seperated list and bind to all
        # addresses (can be ips or hostnames) else bind to default ipv6 and
        # ipv4 address
        if bind:
            if self.ipv6_enable:
                socktype = socket.AF_UNSPEC
            else:
                socktype = socket.AF_INET
            bind = bind.split(',')
            for addr in bind:
                if sys.version_info < (2, 2):
                    addrinfos.append((socket.AF_INET, None, None, None, (addr, port)))
                else:
                    addrinfos.extend(socket.getaddrinfo(addr, port,
                                               socktype, socket.SOCK_STREAM))
        else:
            if self.ipv6_enable:
                addrinfos.append([socket.AF_INET6, None, None, None, ('', port)])
            if not addrinfos or ipv6_socket_style != 0:
                addrinfos.append([socket.AF_INET, None, None, None, ('', port)])
        for addrinfo in addrinfos:
            try:
                server = socket.socket(addrinfo[0], socket.SOCK_STREAM)
                if reuse:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.setblocking(0)
                server.bind(addrinfo[4])
                self.servers[server.fileno()] = server
                if bind:
                    self.interfaces.append(server.getsockname()[0])
                server.listen(64)
                self.poll.register(server, POLLIN)
            except socket.error, e:
                for server in self.servers.values():
                    try:
                        server.close()
                    except:
                        pass
                if self.ipv6_enable and ipv6_socket_style == 0 and self.servers:
                    raise socket.error('blocked port (may require ipv6_binds_v4 to be set)')
                raise socket.error(str(e))
        if not self.servers:
            raise socket.error('unable to open server port')
        if upnp:
            if not UPnP_open_port(port):
                for server in self.servers.values():
                    try:
                        server.close()
                    except:
                        pass
                    self.servers = None
                    self.interfaces = None
                raise socket.error(UPnP_ERROR)
            self.port_forwarded = port
        self.port = port

    def find_and_bind(self, minport, maxport, bind = '', reuse = False,
                      ipv6_socket_style = 1, upnp = 0, randomizer = False):
        e = 'maxport less than minport - no ports to check'
        if maxport-minport < 50 or not randomizer:
            portrange = range(minport, maxport+1)
            if randomizer:
                shuffle(portrange)
                portrange = portrange[:20]  # check a maximum of 20 ports
        else:
            portrange = []
            while len(portrange) < 20:
                listen_port = randrange(minport, maxport+1)
                if not listen_port in portrange:
                    portrange.append(listen_port)
        for listen_port in portrange:
            try:
                self.bind(listen_port, bind,
                               ipv6_socket_style = ipv6_socket_style, upnp = upnp)
                return listen_port
            except socket.error, e:
                pass
        raise socket.error(str(e))


    def set_handler(self, handler):
        self.handler = handler


    def start_connection_raw(self, dns, socktype = socket.AF_INET, handler = None):
        if handler is None:
            handler = self.handler
        sock = socket.socket(socktype, socket.SOCK_STREAM)
        sock.setblocking(0)
        try:
            sock.connect_ex(dns)
        except socket.error:
            raise
        except Exception, e:
            raise socket.error(str(e))
        self.poll.register(sock, POLLIN)
        s = SingleSocket(self, sock, handler, dns[0])
        self.single_sockets[sock.fileno()] = s
        return s


    def start_connection(self, dns, handler = None, randomize = False):
        if handler is None:
            handler = self.handler
        if sys.version_info < (2, 2):
            s = self.start_connection_raw(dns, socket.AF_INET, handler)
        else:
            if self.ipv6_enable:
                socktype = socket.AF_UNSPEC
            else:
                socktype = socket.AF_INET
            try:
                addrinfos = socket.getaddrinfo(dns[0], int(dns[1]),
                                               socktype, socket.SOCK_STREAM)
            except socket.error, e:
                raise
            except Exception, e:
                raise socket.error(str(e))
            if randomize:
                shuffle(addrinfos)
            for addrinfo in addrinfos:
                try:
                    s = self.start_connection_raw(addrinfo[4], addrinfo[0], handler)
                    break
                except:
                    pass
            else:
                raise socket.error('unable to connect')
        return s


    def _sleep(self):
        sleep(1)
        
    def handle_events(self, events):
        for sock, event in events:
            s = self.servers.get(sock)
            if s:
                if event & (POLLHUP | POLLERR) != 0:
                    self.poll.unregister(s)
                    s.close()
                    del self.servers[sock]
                    print "lost server socket"
                elif len(self.single_sockets) < self.max_connects:
                    try:
                        newsock, addr = s.accept()
                        newsock.setblocking(0)
                        nss = SingleSocket(self, newsock, self.handler)
                        self.single_sockets[newsock.fileno()] = nss
                        self.poll.register(newsock, POLLIN)
                        self.handler.external_connection_made(nss)
                    except socket.error:
                        self._sleep()
            else:
                s = self.single_sockets.get(sock)
                if not s:
                    continue
                s.connected = True
                if (event & (POLLHUP | POLLERR)):
                    self._close_socket(s)
                    continue
                if (event & POLLIN):
                    try:
                        s.last_hit = clock()
                        data = s.socket.recv(100000)
                        if not data:
                            self._close_socket(s)
                        else:
                            s.handler.data_came_in(s, data)
                    except socket.error, e:
                        code, msg = e
                        if code != EWOULDBLOCK:
                            self._close_socket(s)
                            continue
                if (event & POLLOUT) and s.socket and not s.is_flushed():
                    s.try_write()
                    if s.is_flushed():
                        s.handler.connection_flushed(s)

    def close_dead(self):
        while self.dead_from_write:
            old = self.dead_from_write
            self.dead_from_write = []
            for s in old:
                if s.socket:
                    self._close_socket(s)

    def _close_socket(self, s):
        s.close()
        s.handler.connection_lost(s)

    def do_poll(self, t):
        r = self.poll.poll(t*timemult)
        if r is None:
            connects = len(self.single_sockets)
            to_close = int(connects*0.05)+1 # close 5% of sockets
            self.max_connects = connects-to_close
            closelist = self.single_sockets.values()
            shuffle(closelist)
            closelist = closelist[:to_close]
            for sock in closelist:
                self._close_socket(sock)
            return []
        return r     

    def get_stats(self):
        return { 'interfaces': self.interfaces, 
                 'port': self.port, 
                 'upnp': self.port_forwarded is not None }


    def shutdown(self):
        for ss in self.single_sockets.values():
            try:
                ss.close()
            except:
                pass
        for server in self.servers.values():
            try:
                server.close()
            except:
                pass
        if self.port_forwarded is not None:
            UPnP_close_port(self.port_forwarded)


########NEW FILE########
__FILENAME__ = subnetparse
# Written by John Hoffman
# see LICENSE.txt for license information

from bisect import bisect, insort

try:
    True
except:
    True = 1
    False = 0
    bool = lambda x: not not x

hexbinmap = {
    '0': '0000',
    '1': '0001',
    '2': '0010',
    '3': '0011',
    '4': '0100',
    '5': '0101',
    '6': '0110',
    '7': '0111',
    '8': '1000',
    '9': '1001',
    'a': '1010',
    'b': '1011',
    'c': '1100',
    'd': '1101',
    'e': '1110',
    'f': '1111',
    'x': '0000',
}

chrbinmap = {}
for n in xrange(256):
    b = []
    nn = n
    for i in xrange(8):
        if nn & 0x80:
            b.append('1')
        else:
            b.append('0')
        nn <<= 1
    chrbinmap[n] = ''.join(b)


def to_bitfield_ipv4(ip):
    ip = ip.split('.')
    if len(ip) != 4:
        raise ValueError, "bad address"
    b = []
    for i in ip:
        b.append(chrbinmap[int(i)])
    return ''.join(b)

def to_bitfield_ipv6(ip):
    b = ''
    doublecolon = False

    if not ip:
        raise ValueError, "bad address"
    if ip == '::':      # boundary handling
        ip = ''
    elif ip[:2] == '::':
        ip = ip[1:]
    elif ip[0] == ':':
        raise ValueError, "bad address"
    elif ip[-2:] == '::':
        ip = ip[:-1]
    elif ip[-1] == ':':
        raise ValueError, "bad address"
    for n in ip.split(':'):
        if n == '':     # double-colon
            if doublecolon:
                raise ValueError, "bad address"
            doublecolon = True
            b += ':'
            continue
        if n.find('.') >= 0: # IPv4
            n = to_bitfield_ipv4(n)
            b += n + '0'*(32-len(n))
            continue
        n = ('x'*(4-len(n))) + n
        for i in n:
            b += hexbinmap[i]
    if doublecolon:
        pos = b.find(':')
        b = b[:pos]+('0'*(129-len(b)))+b[pos+1:]
    if len(b) != 128:   # always check size
        raise ValueError, "bad address"
    return b

ipv4addrmask = to_bitfield_ipv6('::ffff:0:0')[:96]

class IP_List:
    def __init__(self):
        self.ipv4list = []
        self.ipv6list = []

    def __nonzero__(self):
        return bool(self.ipv4list or self.ipv6list)


    def append(self, ip, depth = 256):
        if ip.find(':') < 0:        # IPv4
            insort(self.ipv4list, to_bitfield_ipv4(ip)[:depth])
        else:
            b = to_bitfield_ipv6(ip)
            if b.startswith(ipv4addrmask):
                insort(self.ipv4list, b[96:][:depth-96])
            else:
                insort(self.ipv6list, b[:depth])


    def includes(self, ip):
        if not (self.ipv4list or self.ipv6list):
            return False
        if ip.find(':') < 0:        # IPv4
            b = to_bitfield_ipv4(ip)
        else:
            b = to_bitfield_ipv6(ip)
            if b.startswith(ipv4addrmask):
                b = b[96:]
        if len(b) > 32:
            l = self.ipv6list
        else:
            l = self.ipv4list
        for map in l[bisect(l, b)-1:]:
            if b.startswith(map):
                return True
            if map > b:
                return False
        return False


    def read_fieldlist(self, file):   # reads a list from a file in the format 'ip/len <whatever>'
        f = open(file, 'r')
        while 1:
            line = f.readline()
            if not line:
                break
            line = line.strip().expandtabs()
            if not line or line[0] == '#':
                continue
            try:
                line, garbage = line.split(' ', 1)
            except:
                pass
            try:
                line, garbage = line.split('#', 1)
            except:
                pass
            try:
                ip, depth = line.split('/')
            except:
                ip = line
                depth = None
            try:
                if depth is not None:                
                    depth = int(depth)
                self.append(ip, depth)
            except:
                print '*** WARNING *** could not parse IP range: '+line
        f.close()


    def set_intranet_addresses(self):
        self.append('127.0.0.1', 8)
        self.append('10.0.0.0', 8)
        self.append('172.16.0.0', 12)
        self.append('192.168.0.0', 16)
        self.append('169.254.0.0', 16)
        self.append('::1')
        self.append('fe80::', 16)
        self.append('fec0::', 16)

    def set_ipv4_addresses(self):
        self.append('::ffff:0:0', 96)

def ipv6_to_ipv4(ip):
    ip = to_bitfield_ipv6(ip)
    if not ip.startswith(ipv4addrmask):
        raise ValueError, "not convertible to IPv4"
    ip = ip[-32:]
    x = ''
    for i in range(4):
        x += str(int(ip[:8], 2))
        if i < 3:
            x += '.'
        ip = ip[8:]
    return x

def to_ipv4(ip):
    if is_ipv4(ip):
        _valid_ipv4(ip)
        return ip
    return ipv6_to_ipv4(ip)

def is_ipv4(ip):
    return ip.find(':') < 0

def _valid_ipv4(ip):
    ip = ip.split('.')
    if len(ip) != 4:
        raise ValueError
    for i in ip:
        chr(int(i))

def is_valid_ip(ip):
    try:
        if not ip:
            return False
        if is_ipv4(ip):
            _valid_ipv4(ip)
            return True
        to_bitfield_ipv6(ip)
        return True
    except:
        return False

########NEW FILE########
__FILENAME__ = torrentlistparse
# Written by John Hoffman
# see LICENSE.txt for license information

from binascii import unhexlify

try:
    True
except:
    True = 1
    False = 0


# parses a list of torrent hashes, in the format of one hash per line in hex format

def parsetorrentlist(filename, parsed):
    new_parsed = {}
    added = {}
    removed = parsed
    f = open(filename, 'r')
    while 1:
        l = f.readline()
        if not l:
            break
        l = l.strip()
        try:
            if len(l) != 40:
                raise ValueError, 'bad line'
            h = unhexlify(l)
        except:
            print '*** WARNING *** could not parse line in torrent list: '+l
        if parsed.has_key(h):
            del removed[h]
        else:
            added[h] = True
        new_parsed[h] = True
    f.close()
    return (new_parsed, added, removed)


########NEW FILE########
__FILENAME__ = zurllib
# Written by John Hoffman
# see LICENSE.txt for license information

from httplib import HTTPConnection, HTTPSConnection, HTTPException
from urlparse import urlparse
from bencode import bdecode
from gzip import GzipFile
from StringIO import StringIO
from __init__ import product_name, version_short

VERSION = product_name+'/'+version_short
MAX_REDIRECTS = 10


class btHTTPcon(HTTPConnection): # attempt to add automatic connection timeout
    def connect(self):
        HTTPConnection.connect(self)
        try:
            self.sock.settimeout(30)
        except:
            pass

class btHTTPScon(HTTPSConnection): # attempt to add automatic connection timeout
    def connect(self):
        HTTPSConnection.connect(self)
        try:
            self.sock.settimeout(30)
        except:
            pass 

class urlopen:
    def __init__(self, url):
        self.tries = 0
        self._open(url.strip())
        self.error_return = None

    def _open(self, url):
        self.tries += 1
        if self.tries > MAX_REDIRECTS:
            raise IOError, ('http error', 500,
                            "Internal Server Error: Redirect Recursion")
        (scheme, netloc, path, pars, query, fragment) = urlparse(url)
        if scheme != 'http' and scheme != 'https':
            raise IOError, ('url error', 'unknown url type', scheme, url)
        url = path
        if pars:
            url += ';'+pars
        if query:
            url += '?'+query
#        if fragment:
        try:
            if scheme == 'http':
                self.connection = btHTTPcon(netloc)
            else:
                self.connection = btHTTPScon(netloc)
            self.connection.request('GET', url, None,
                                { 'User-Agent': VERSION,
                                  'Accept-Encoding': 'gzip' } )
            self.response = self.connection.getresponse()
        except HTTPException, e:
            raise IOError, ('http error', str(e))
        status = self.response.status
        if status in (301, 302):
            try:
                self.connection.close()
            except:
                pass
            self._open(self.response.getheader('Location'))
            return
        if status != 200:
            try:
                data = self._read()
                d = bdecode(data)
                if d.has_key('failure reason'):
                    self.error_return = data
                    return
            except:
                pass
            raise IOError, ('http error', status, self.response.reason)

    def read(self):
        if self.error_return:
            return self.error_return
        return self._read()

    def _read(self):
        data = self.response.read()
        if self.response.getheader('Content-Encoding', '').find('gzip') >= 0:
            try:
                compressed = StringIO(data)
                f = GzipFile(fileobj = compressed)
                data = f.read()
            except:
                raise IOError, ('http error', 'got corrupt response')
        return data

    def close(self):
        self.connection.close()

########NEW FILE########
__FILENAME__ = btmakemetafile
#!/usr/bin/env python

# Written by Bram Cohen
# multitracker extensions by John Hoffman
# see LICENSE.txt for license information

import sys
import md5
import zlib

from os.path import getsize, split, join, abspath, isdir, normpath
from os import listdir
from sha import sha
from copy import copy
from string import strip
from threading import Event
from time import time
from traceback import print_exc
try:
    from sys import getfilesystemencoding
    ENCODING = getfilesystemencoding()
except:
    from sys import getdefaultencoding
    ENCODING = getdefaultencoding()

from BitTornado.bencode import bencode
from BitTornado.BT1.btformats import check_info

defaults = [
    ('announce_list', '', 
        'a list of announce URLs - explained below'), 
    ('httpseeds', '',
        'a list of http seed URLs - explained below'),
    ('piece_size_pow2', 0, 
        "which power of 2 to set the piece size to (0 = automatic)"), 
    ('comment', '', 
        "optional human-readable comment to put in .torrent"), 
    ('filesystem_encoding', '',
        "optional specification for filesystem encoding " +
        "(set automatically in recent Python versions)"),
    ('target', '', 
        "optional target file for the torrent"),
    ('created by', '',
        "optional information on who made the torrent")
    ]

default_piece_len_exp = 18

ignore = ['core', 'CVS']

def print_announcelist_details():
    print ('    announce_list = optional list of redundant/backup tracker URLs, in the format:')
    print ('           url[,url...][|url[,url...]...]')
    print ('                where URLs separated by commas are all tried first')
    print ('                before the next group of URLs separated by the pipe is checked.')
    print ("                If none is given, it is assumed you don't want one in the metafile.")
    print ('                If announce_list is given, clients which support it')
    print ('                will ignore the <announce> value.')
    print ('           Examples:')
    print ('                http://tracker1.com|http://tracker2.com|http://tracker3.com')
    print ('                     (tries trackers 1-3 in order)')
    print ('                http://tracker1.com,http://tracker2.com,http://tracker3.com')
    print ('                     (tries trackers 1-3 in a randomly selected order)')
    print ('                http://tracker1.com|http://backup1.com,http://backup2.com')
    print ('                     (tries tracker 1 first, then tries between the 2 backups randomly)')
    print ('')
    print ('    httpseeds = optional list of http-seed URLs, in the format:')
    print ('            url[|url...]')

def make_meta_file(file, url, params = None, flag = Event(), 
                   progress = lambda x: None, progress_percent = 1, gethash = None):        
    if params is None:
        params = {}
    if 'piece_size_pow2' in params:
        piece_len_exp = params['piece_size_pow2']
    else:
        piece_len_exp = default_piece_len_exp
    if 'target' in params and params['target']:
        f = params['target']
    else:
        a, b = split(file)
        if b == '':
            f = a + '.torrent'
        else:
            f = join(a, b + '.torrent')
            
    if piece_len_exp == 0:  # automatic
        size = calcsize(file)
        if   size > 8L*1024*1024*1024:   # > 8 gig =
            piece_len_exp = 21          #   2 meg pieces
        elif size > 2*1024*1024*1024:   # > 2 gig =
            piece_len_exp = 20          #   1 meg pieces
        elif size > 512*1024*1024:      # > 512M =
            piece_len_exp = 19          #   512K pieces
        elif size > 64*1024*1024:       # > 64M =
            piece_len_exp = 18          #   256K pieces
        elif size > 16*1024*1024:       # > 16M =
            piece_len_exp = 17          #   128K pieces
        elif size > 4*1024*1024:        # > 4M =
            piece_len_exp = 16          #   64K pieces
        else:                           # < 4M =
            piece_len_exp = 15          #   32K pieces
    piece_length = 2 ** piece_len_exp
    
    encoding = None
    if 'filesystem_encoding' in params:
        encoding = params['filesystem_encoding']
    if not encoding:
        encoding = ENCODING
    if not encoding:
        encoding = 'ascii'
    
    info = makeinfo(file, piece_length, encoding, flag, progress, progress_percent, gethash = gethash)
    if flag.isSet():
        return
    check_info(info)
    h = open(f, 'wb')
    data = {'info': info, 'announce': strip(url), 'creation date': long(time())}
    
    if 'comment' in params and params['comment']:
        data['comment'] = params['comment']
    
    if 'created by' in params and params['created by']:
        data['created by'] = params['created by']
    
    if 'real_announce_list' in params:    # shortcut for progs calling in from outside
        data['announce-list'] = params['real_announce_list']
    elif 'announce_list' in params and params['announce_list']:
        l = []
        for tier in params['announce_list'].split('|'):
            l.append(tier.split(','))
        data['announce-list'] = l
        
    if 'real_httpseeds' in params:    # shortcut for progs calling in from outside
        data['httpseeds'] = params['real_httpseeds']
    elif 'httpseeds' in params and params['httpseeds']:
        data['httpseeds'] = params['httpseeds'].split('|')
    if 'url_list' in params and params['url_list']:
        data['url-list'] = params['url_list']
        
    h.write(bencode(data))
    h.close()

def calcsize(file):
    if not isdir(file):
        return getsize(file)
    total = 0L
    for s in subfiles(abspath(file)):
        total += getsize(s[1])
    return total


def uniconvertl(l, e):
    r = []
    try:
        for s in l:
            r.append(uniconvert(s, e))
    except UnicodeError:
        raise UnicodeError('bad filename: '+join(l))
    return r

def uniconvert(s, e):
    try:
        s = unicode(s,e)
    except UnicodeError:
        raise UnicodeError('bad filename: '+s)
    return s.encode('utf-8')

def makeinfo(file, piece_length, encoding, flag, progress, progress_percent=1, gethash = None):
    if gethash is None:
        gethash = {}
    
    if not 'md5' in gethash:
        gethash['md5'] = False
    if not 'crc32' in gethash:
        gethash['crc32'] = False
    if not 'sha1' in gethash:
        gethash['sha1'] = False
        
    file = abspath(file)
    if isdir(file):
        subs = subfiles(file)
        subs.sort()
        pieces = []
        sh = sha()
        done = 0L
        fs = []
        totalsize = 0.0
        totalhashed = 0L
        for p, f in subs:
            totalsize += getsize(f)

        for p, f in subs:
            pos = 0L
            size = getsize(f)
            h = open(f, 'rb')

            if gethash['md5']:
                hash_md5 = md5.new()
            if gethash['sha1']:
                hash_sha1 = sha()
            if gethash['crc32']:
                hash_crc32 = zlib.crc32('')
            
            while pos < size:
                a = min(size - pos, piece_length - done)
                
                readpiece = h.read(a)

                # See if the user cancelled
                if flag.isSet():
                    return
                
                sh.update(readpiece)

                # See if the user cancelled
                if flag.isSet():
                    return

                if gethash['md5']:                
                    # Update MD5
                    hash_md5.update(readpiece)
    
                    # See if the user cancelled
                    if flag.isSet():
                        return

                if gethash['crc32']:                
                    # Update CRC32
                    hash_crc32 = zlib.crc32(readpiece, hash_crc32)
    
                    # See if the user cancelled
                    if flag.isSet():
                        return
                
                if gethash['sha1']:                
                    # Update SHA1
                    hash_sha1.update(readpiece)
    
                    # See if the user cancelled
                    if flag.isSet():
                        return
                
                done += a
                pos += a
                totalhashed += a
                
                if done == piece_length:
                    pieces.append(sh.digest())
                    done = 0
                    sh = sha()
                if progress_percent:
                    progress(totalhashed / totalsize)
                else:
                    progress(a)
                    
            newdict = {'length': size,
                       'path': uniconvertl(p, encoding) }
            if gethash['md5']:
                newdict['md5sum'] = hash_md5.hexdigest()
            if gethash['crc32']:
                newdict['crc32'] = "%08X" % hash_crc32
            if gethash['sha1']:
                newdict['sha1'] = hash_sha1.digest()
                    
            fs.append(newdict)
                    
            h.close()
        if done > 0:
            pieces.append(sh.digest())
        return {'pieces': ''.join(pieces), 
                'piece length': piece_length,
                'files': fs, 
                'name': uniconvert(split(file)[1], encoding) }
    else:
        size = getsize(file)
        pieces = []
        p = 0L
        h = open(file, 'rb')
        
        if gethash['md5']:
            hash_md5 = md5.new()
        if gethash['crc32']:
            hash_crc32 = zlib.crc32('')
        if gethash['sha1']:
            hash_sha1 = sha()
        
        while p < size:
            x = h.read(min(piece_length, size - p))

            # See if the user cancelled
            if flag.isSet():
                return
            
            if gethash['md5']:
                # Update MD5
                hash_md5.update(x)
    
                # See if the user cancelled
                if flag.isSet():
                    return
            
            if gethash['crc32']:
                # Update CRC32
                hash_crc32 = zlib.crc32(x, hash_crc32)
    
                # See if the user cancelled
                if flag.isSet():
                    return
            
            if gethash['sha1']:
                # Update SHA-1
                hash_sha1.update(x)
    
                # See if the user cancelled
                if flag.isSet():
                    return
                
            pieces.append(sha(x).digest())

            # See if the user cancelled
            if flag.isSet():
                return

            p += piece_length
            if p > size:
                p = size
            if progress_percent:
                progress(float(p) / size)
            else:
                progress(min(piece_length, size - p))
        h.close()
        newdict = {'pieces': ''.join(pieces), 
                   'piece length': piece_length,
                   'length': size, 
                   'name': uniconvert(split(file)[1], encoding) }
        if gethash['md5']:
            newdict['md5sum'] = hash_md5.hexdigest()
        if gethash['crc32']:
            newdict['crc32'] = "%08X" % hash_crc32
        if gethash['sha1']:
            newdict['sha1'] = hash_sha1.digest()
                   
        return newdict

def subfiles(d):
    r = []
    stack = [([], d)]
    while stack:
        p, n = stack.pop()
        if isdir(n):
            for s in listdir(n):
                if s not in ignore and s[:1] != '.':
                    stack.append((copy(p) + [s], join(n, s)))
        else:
            r.append((p, n))
    return r

def completedir(dir, url, params = None, flag = Event(),
                vc = lambda x: None, fc = lambda x: None, getmd5 = False):
    if params is None:
        params = {}
    files = listdir(dir)
    files.sort()
    ext = '.torrent'
    if 'target' in params:
        target = params['target']
    else:
        target = ''

    togen = []
    for f in files:
        if f[-len(ext):] != ext and (f + ext) not in files:
            togen.append(join(dir, f))
        
    total = 0
    for i in togen:
        total += calcsize(i)

    subtotal = [0]
    def callback(x, subtotal = subtotal, total = total, vc = vc):
        subtotal[0] += x
        vc(float(subtotal[0]) / total)
    for i in togen:
        fc(i)
        try:
            t = split(i)[-1]
            if t not in ignore and t[0] != '.':
                if target != '':
                    params['target'] = join(target,t+ext)
                make_meta_file(i, url, params, flag, progress = callback, progress_percent = 0, getmd5 = getmd5)
        except ValueError:
            print_exc()

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.shortcuts import get_object_or_404

from videoportal.models import Video, Channel, Collection

import appsettings as settings

import os

class LatestMP4Videos(Feed):
    ''' This class (like the following) are handling the feed requests from urls.py.
    TODO:
    Better handling: We sould only use one Feed class and get the desired format with GET
    Dynamic Title for the Feed'''
    title = "OwnTube Latest Videos"
    link = "/"
    description = "The newest media from OwnTube"
    item_enclosure_mime_type = "video/mp4"
	
    def items(self):
        return Video.objects.filter(published=True).exclude(mp4URL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description
        
    def item_enclosure_url(self, item):
    	return item.mp4URL
    	
    def item_enclosure_length(self, item):
    	return item.mp4Size
    	
    def item_pubdate(self, item):
    	return item.created
    	
class LatestWEBMVideos(Feed):
    title = "OwnTube Latest Videos"
    link = "/"
    description = "The newest media from OwnTube"
    item_enclosure_mime_type = "video/webm"
	
    def items(self):
        return Video.objects.filter(published=True).exclude(webmURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description
        
    def item_enclosure_url(self, item):
    	return item.webmURL
    	
    def item_enclosure_length(self, item):
    	return item.webmSize
    	
    def item_pubdate(self, item):
    	return item.created
    	
class LatestMP3Audio(Feed):
    title = "OwnTube Latest Audio Files"
    link = "/"
    description = "The newest media from OwnTube"
    item_enclosure_mime_type = "audio/mp3"
	
    def items(self):
        return Video.objects.filter(published=True).exclude(mp3URL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description
        
    def item_enclosure_url(self, item):
    	return item.mp3URL
    	
    def item_enclosure_length(self, item):
    	return item.mp3Size
    	
    def item_pubdate(self, item):
    	return item.created
    	
class LatestOGGAudio(Feed):
    title = "OwnTube Latest Audio Files"
    link = "/"
    description = "The newest media from OwnTube"
    item_enclosure_mime_type = "audio/ogg"
	
    def items(self):
        return Video.objects.filter(published=True).exclude(oggURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description
        
    def item_enclosure_url(self, item):
    	return item.oggURL
    	
    def item_enclosure_length(self, item):
    	return item.oggSize
    	
    def item_pubdate(self, item):
    	return item.created

class TorrentFeed(Feed):
    title = "OwnTube TorrentFeed"
    link = "/"
    description = "Torrent files from OwnTube"
    item_enclosure_mime_type = "application/x-bittorrent"
	
    def items(self):
        return Video.objects.filter(published=True, torrentDone=True).exclude(torrentURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description
        
    def item_enclosure_url(self, item):
    	return item.torrentURL
    	
    def item_enclosure_length(self, item):
    	return os.path.getsize(settings.BITTORRENT_FILES_DIR + item.slug + '.torrent')
    	
    def item_pubdate(self, item):
    	return item.created

class ChannelFeedMP4(Feed):
    ''' This class (like the next one) gives the feeds for channels"'''
    
    def get_object(self, request, channel_slug):
        return get_object_or_404(Channel, slug=channel_slug)

    def title(self, obj):
        return "Piratenfraktion Berlin: %s" % obj.name

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "video/mp4"
    author_name = "Piratenfraktion Berlin"

    def items(self, obj):
        return Video.objects.filter(encodingDone=True, published=True, channel=obj ).exclude(mp4URL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.mp4URL

    def item_enclosure_length(self, item):
        return item.mp4Size

    def item_pubdate(self, item):
        return item.created

class ChannelFeedWEBM(Feed):

    def get_object(self, request, channel_slug):
        return get_object_or_404(Channel, slug=channel_slug)

    def title(self, obj):
        return "Piratenfraktion Berlin: %s" % obj.name

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "video/webm"
    author_name = "Piratenfraktion Berlin"

    def items(self, obj):
        return Video.objects.filter(encodingDone=True, published=True, channel=obj ).exclude(webmURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.webmURL

    def item_enclosure_length(self, item):
        return item.webmSize

    def item_pubdate(self, item):
        return item.created

class ChannelFeedMP3(Feed):

    def get_object(self, request, channel_slug):
        return get_object_or_404(Channel, slug=channel_slug)

    def title(self, obj):
        return "Piratenfraktion Berlin: %s" % obj.name

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "audio/mp3"
    author_name = "Piratenfraktion Berlin"

    def items(self, obj):
        return Video.objects.filter(encodingDone=True, published=True, channel=obj ).exclude(mp3URL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.mp3URL

    def item_enclosure_length(self, item):
        return item.mp3Size

    def item_pubdate(self, item):
        return item.created

class ChannelFeedOGG(Feed):

    def get_object(self, request, channel_slug):
        return get_object_or_404(Channel, slug=channel_slug)

    def title(self, obj):
        return "Piratenfraktion Berlin: %s" % obj.name

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "audio/ogg"
    author_name = "Piratenfraktion Berlin"

    def items(self, obj):
        return Video.objects.filter(encodingDone=True, published=True, channel=obj ).exclude(oggURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.oggURL

    def item_enclosure_length(self, item):
        return item.oggSize

    def item_pubdate(self, item):
        return item.created

class ChannelFeedTorrent(Feed):

    def get_object(self, request, channel_slug):
        return get_object_or_404(Channel, slug=channel_slug)

    def title(self, obj):
        return "OwnTube: Torrents for Channel %s" % obj.name

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "application/x-bittorrent"

    def items(self, obj):
        return Video.objects.filter(published=True, channel=obj, torrentDone=True ).exclude(torrentURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.torrentURL

    def item_enclosure_length(self, item):
        return os.path.getsize(settings.BITTORRENT_FILES_DIR + item.slug + '.torrent')

    def item_pubdate(self, item):
        return item.created

class CollectionFeedMP4(Feed):

    def get_object(self, request, collection_slug):
        return get_object_or_404(Collection, slug=collection_slug)

    def title(self, obj):
        return "OwnTube: Videos in Collection %s" % obj.title

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "video/mp4"

    def items(self, obj):
        return obj.videos.filter(encodingDone=True, published=True).exclude(mp4URL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.mp4URL

    def item_enclosure_length(self, item):
        return item.mp4Size

    def item_pubdate(self, item):
        return item.created

class CollectionFeedWEBM(Feed):

    def get_object(self, request, collection_slug):
        return get_object_or_404(Collection, slug=collection_slug)

    def title(self, obj):
        return "OwnTube: Videos in Collection %s" % obj.title

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "video/webm"

    def items(self, obj):
        return obj.videos.filter(encodingDone=True, published=True).exclude(webmURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.webmURL

    def item_enclosure_length(self, item):
        return item.webmSize

    def item_pubdate(self, item):
        return item.created

class CollectionFeedMP3(Feed):

    def get_object(self, request, collection_slug):
        return get_object_or_404(Collection, slug=collection_slug)

    def title(self, obj):
        return "OwnTube: Videos in Collection %s" % obj.title

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "audio/mp3"

    def items(self, obj):
        return obj.videos.filter(encodingDone=True, published=True).exclude(mp3URL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.mp3URL

    def item_enclosure_length(self, item):
        return item.mp3Size

    def item_pubdate(self, item):
        return item.created

class CollectionFeedOGG(Feed):

    def get_object(self, request, collection_slug):
        return get_object_or_404(Collection, slug=collection_slug)

    def title(self, obj):
        return "OwnTube: Videos in Collection %s" % obj.title

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "audio/ogg"

    def items(self, obj):
        return obj.videos.filter(encodingDone=True, published=True).exclude(oggURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.oggURL

    def item_enclosure_length(self, item):
        return item.oggSize

    def item_pubdate(self, item):
        return item.created

class CollectionFeedTorrent(Feed):

    def get_object(self, request, collection_slug):
        return get_object_or_404(Collection, slug=collection_slug)

    def title(self, obj):
        return "OwnTube: Videos in Collection %s" % obj.title

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return  obj.description

    item_enclosure_mime_type = "application/x-bittorrent"

    def items(self, obj):
        return obj.videos.filter(torrentDone=True, published=True).exclude(torrentURL='').order_by('-created')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_enclosure_url(self, item):
        return item.torrentURL

    def item_enclosure_length(self, item):
        return os.path.getsize(settings.BITTORRENT_FILES_DIR + item.slug + '.torrent')

    def item_pubdate(self, item):
        return item.created

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm
from django import forms

from videoportal.models import Video
from videoportal.models import Comment

class VideoForm(ModelForm):
    ''' Used for the uploading form '''

    class Meta:
        model = Video
        fields = ('title', 'date', 'description', 'channel', 
            'linkURL', 'kind', 'tags', 'originalFile')

class CommentForm(ModelForm):
    ''' Used for the comments '''
    class Meta:
        model = Comment
        exclude = ["ip","moderated","video"]

########NEW FILE########
__FILENAME__ = scanhotfolders
from django.core.management.base import BaseCommand, CommandError
from videoportal.models import *
import videoportal.appsettings as settings
import djangotasks
import datetime
import shutil
import os
import time

class Command(BaseCommand):
    args = ''
    help = 'Gets new videos out of hotfolders'
    def handle(self, *args, **options):
        now = time.time()
        five_minutes_ago = now - 60*2
        hotfolders = Hotfolder.objects.filter(activated=True)
        for folder in hotfolders:
            self.stdout.write('This is folder "%s"\n' % folder.folderName)
            os.chdir(settings.HOTFOLDER_BASE_DIR + folder.folderName)
            for file in os.listdir("."):
                st=os.stat(file)
                mtime=st.st_mtime
                if mtime < five_minutes_ago:
                    if file.endswith(".mov") or file.endswith(".mp4") or file.endswith(".avi") or file.endswith(".ogv") or file.endswith(".m4v") or file.endswith(".mp3") or file.endswith(".ogg"):
                        self.stdout.write('Using file %s\n' % file) 
                        video = Video(title=folder.defaultName,date=datetime.date.today(),description=folder.description,kind=folder.kind,channel=folder.channel,autoPublish=folder.autoPublish)
                        video.save()
                        shutil.copy(settings.HOTFOLDER_BASE_DIR + folder.folderName + '/' + file, settings.HOTFOLDER_MOVE_TO_DIR)
                        video.originalFile = settings.HOTFOLDER_MOVE_TO_DIR + file
                        video.save()
                        os.remove(settings.HOTFOLDER_BASE_DIR + folder.folderName + '/' + file)
                        djangotasks.register_task(video.encode_media, "Encode the files using ffmpeg")
                        encoding_task = djangotasks.task_for_object(video.encode_media)
                        djangotasks.run_task(encoding_task)
                        if settings.USE_BITTORRENT:
                            djangotasks.register_task(video.create_bittorrent, "Create Bittorrent file for video and serve via Bittorrent")
                            torrent_task = djangotasks.task_for_object(video.create_bittorrent)
                            djangotasks.run_task(torrent_task)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Video'
        db.create_table('videoportal_video', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('protocolURL', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('kind', self.gf('django.db.models.fields.IntegerField')(max_length=1)),
            ('torrentURL', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('mp4URL', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('mp4Size', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('webmURL', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('webmSize', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('mp3URL', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('mp3Size', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('oggURL', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('oggSize', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('videoThumbURL', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('duration', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=2, blank=True)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('encodingDone', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('assemblyid', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('originalFile', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('videoportal', ['Video'])

        # Adding model 'Comment'
        db.create_table('videoportal_comment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15, null=True, blank=True)),
            ('moderated', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('timecode', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=2, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(max_length=1000)),
            ('video', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['videoportal.Video'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('videoportal', ['Comment'])


    def backwards(self, orm):
        # Deleting model 'Video'
        db.delete_table('videoportal_video')

        # Deleting model 'Comment'
        db.delete_table('videoportal_comment')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'protocolURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0002_auto__add_channel__add_field_video_channel
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Channel'
        db.create_table('videoportal_channel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('videoportal', ['Channel'])

        # Adding M2M table for field videos on 'Channel'
        db.create_table('videoportal_channel_videos', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('channel', models.ForeignKey(orm['videoportal.channel'], null=False)),
            ('video', models.ForeignKey(orm['videoportal.video'], null=False))
        ))
        db.create_unique('videoportal_channel_videos', ['channel_id', 'video_id'])

        # Adding field 'Video.channel'
        db.add_column('videoportal_video', 'channel',
                      self.gf('django.db.models.fields.related.OneToOneField')(to=orm['videoportal.Channel'], unique=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'Channel'
        db.delete_table('videoportal_channel')

        # Removing M2M table for field videos on 'Channel'
        db.delete_table('videoportal_channel_videos')

        # Deleting field 'Video.channel'
        db.delete_column('videoportal_video', 'channel_id')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'contained_videos'", 'symmetrical': 'False', 'to': "orm['videoportal.Video']"})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'channel': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['videoportal.Channel']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'protocolURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_channel_slug
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Channel.slug'
        db.add_column('videoportal_channel', 'slug',
                      self.gf('autoslug.fields.AutoSlugField')(default=datetime.datetime(2012, 7, 17, 0, 0), unique=True, max_length=50, populate_from=None, unique_with=()),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Channel.slug'
        db.delete_column('videoportal_channel', 'slug')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'contained_videos'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['videoportal.Video']"})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'channel': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['videoportal.Channel']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'protocolURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_video_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Video.user'
        db.add_column('videoportal_video', 'user',
                      self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Video.user'
        db.delete_column('videoportal_video', 'user_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'contained_videos'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['videoportal.Video']"})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'channel': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['videoportal.Channel']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'protocolURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0005_auto__del_field_video_channel
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Video.channel'
        db.delete_column('videoportal_video', 'channel_id')


    def backwards(self, orm):
        # Adding field 'Video.channel'
        db.add_column('videoportal_video', 'channel',
                      self.gf('django.db.models.fields.related.OneToOneField')(to=orm['videoportal.Channel'], unique=True, null=True, blank=True),
                      keep_default=False)


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'contained_videos'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['videoportal.Video']"})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'protocolURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0006_auto__del_field_video_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Video.user'
        db.delete_column('videoportal_video', 'user_id')

        # Adding M2M table for field user on 'Video'
        db.create_table('videoportal_video_user', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('video', models.ForeignKey(orm['videoportal.video'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('videoportal_video_user', ['video_id', 'user_id'])


    def backwards(self, orm):
        # Adding field 'Video.user'
        db.add_column('videoportal_video', 'user',
                      self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, null=True, blank=True),
                      keep_default=False)

        # Removing M2M table for field user on 'Video'
        db.delete_table('videoportal_video_user')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'contained_videos'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['videoportal.Video']"})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'protocolURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0007_auto__add_field_video_channel
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Video.channel'
        db.add_column('videoportal_video', 'channel',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['videoportal.Channel'], null=True, blank=True),
                      keep_default=False)

        # Removing M2M table for field videos on 'Channel'
        db.delete_table('videoportal_channel_videos')


    def backwards(self, orm):
        # Deleting field 'Video.channel'
        db.delete_column('videoportal_video', 'channel_id')

        # Adding M2M table for field videos on 'Channel'
        db.create_table('videoportal_channel_videos', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('channel', models.ForeignKey(orm['videoportal.channel'], null=False)),
            ('video', models.ForeignKey(orm['videoportal.video'], null=False))
        ))
        db.create_unique('videoportal_channel_videos', ['channel_id', 'video_id'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'protocolURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0008_auto__add_field_video_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Video.user'
        db.add_column('videoportal_video', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)

        # Removing M2M table for field user on 'Video'
        db.delete_table('videoportal_video_user')


    def backwards(self, orm):
        # Deleting field 'Video.user'
        db.delete_column('videoportal_video', 'user_id')

        # Adding M2M table for field user on 'Video'
        db.create_table('videoportal_video_user', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('video', models.ForeignKey(orm['videoportal.video'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('videoportal_video_user', ['video_id', 'user_id'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'protocolURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0009_auto__del_field_video_protocolURL__add_field_video_linkURL__add_field_
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Video.protocolURL'
        db.delete_column('videoportal_video', 'protocolURL')

        # Adding field 'Video.linkURL'
        db.add_column('videoportal_video', 'linkURL',
                      self.gf('django.db.models.fields.URLField')(default='', max_length=200, blank=True),
                      keep_default=False)

        # Adding field 'Channel.description'
        db.add_column('videoportal_channel', 'description',
                      self.gf('django.db.models.fields.TextField')(max_length=1000, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Video.protocolURL'
        db.add_column('videoportal_video', 'protocolURL',
                      self.gf('django.db.models.fields.URLField')(default='', max_length=200, blank=True),
                      keep_default=False)

        # Deleting field 'Video.linkURL'
        db.delete_column('videoportal_video', 'linkURL')

        # Deleting field 'Channel.description'
        db.delete_column('videoportal_channel', 'description')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0010_auto__add_field_channel_featured
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Channel.featured'
        db.add_column('videoportal_channel', 'featured',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Channel.featured'
        db.delete_column('videoportal_channel', 'featured')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0011_auto__add_hotfolder
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Hotfolder'
        db.create_table('videoportal_hotfolder', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activated', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('channel', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['videoportal.Channel'])),
            ('folderName', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('defaultName', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=1000, null=True, blank=True)),
            ('autoPublish', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('kind', self.gf('django.db.models.fields.IntegerField')(max_length=1)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('videoportal', ['Hotfolder'])


    def backwards(self, orm):
        # Deleting model 'Hotfolder'
        db.delete_table('videoportal_hotfolder')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.hotfolder': {
            'Meta': {'object_name': 'Hotfolder'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'defaultName': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'folderName': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0012_auto__add_field_video_autoPublish
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Video.autoPublish'
        db.add_column('videoportal_video', 'autoPublish',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Video.autoPublish'
        db.delete_column('videoportal_video', 'autoPublish')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.hotfolder': {
            'Meta': {'object_name': 'Hotfolder'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'defaultName': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'folderName': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0013_auto__add_field_video_torrentDone
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Video.torrentDone'
        db.add_column('videoportal_video', 'torrentDone',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Video.torrentDone'
        db.delete_column('videoportal_video', 'torrentDone')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.hotfolder': {
            'Meta': {'object_name': 'Hotfolder'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'defaultName': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'folderName': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0014_auto__add_collection
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Collection'
        db.create_table('videoportal_collection', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=1000)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('videoportal', ['Collection'])

        # Adding M2M table for field videos on 'Collection'
        db.create_table('videoportal_collection_videos', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('collection', models.ForeignKey(orm['videoportal.collection'], null=False)),
            ('video', models.ForeignKey(orm['videoportal.video'], null=False))
        ))
        db.create_unique('videoportal_collection_videos', ['collection_id', 'video_id'])


    def backwards(self, orm):
        # Deleting model 'Collection'
        db.delete_table('videoportal_collection')

        # Removing M2M table for field videos on 'Collection'
        db.delete_table('videoportal_collection_videos')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.collection': {
            'Meta': {'object_name': 'Collection'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['videoportal.Video']", 'symmetrical': 'False'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.hotfolder': {
            'Meta': {'object_name': 'Hotfolder'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'defaultName': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'folderName': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0015_auto__add_field_collection_channel
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Collection.channel'
        db.add_column('videoportal_collection', 'channel',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['videoportal.Channel'], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Collection.channel'
        db.delete_column('videoportal_collection', 'channel_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.collection': {
            'Meta': {'object_name': 'Collection'},
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['videoportal.Video']", 'symmetrical': 'False'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.hotfolder': {
            'Meta': {'object_name': 'Hotfolder'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'defaultName': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'folderName': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0016_auto__add_field_collection_date
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Collection.date'
        db.add_column('videoportal_collection', 'date',
                      self.gf('django.db.models.fields.DateField')(null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Collection.date'
        db.delete_column('videoportal_collection', 'date')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.collection': {
            'Meta': {'object_name': 'Collection'},
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['videoportal.Video']", 'symmetrical': 'False'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.hotfolder': {
            'Meta': {'object_name': 'Hotfolder'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'defaultName': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'folderName': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0017_auto__chg_field_video_originalFile
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Video.originalFile'
        db.alter_column('videoportal_video', 'originalFile', self.gf('django.db.models.fields.files.FileField')(max_length=2048))

    def backwards(self, orm):

        # Changing field 'Video.originalFile'
        db.alter_column('videoportal_video', 'originalFile', self.gf('django.db.models.fields.files.FileField')(max_length=100))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.collection': {
            'Meta': {'object_name': 'Collection'},
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['videoportal.Video']", 'symmetrical': 'False'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.hotfolder': {
            'Meta': {'object_name': 'Hotfolder'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'defaultName': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'folderName': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '2048', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = 0018_auto__add_field_video_audioThumbURL
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Video.audioThumbURL'
        db.add_column('videoportal_video', 'audioThumbURL',
                      self.gf('django.db.models.fields.URLField')(default='', max_length=200, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Video.audioThumbURL'
        db.delete_column('videoportal_video', 'audioThumbURL')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        },
        'videoportal.channel': {
            'Meta': {'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'videoportal.collection': {
            'Meta': {'object_name': 'Collection'},
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['videoportal.Video']", 'symmetrical': 'False'})
        },
        'videoportal.comment': {
            'Meta': {'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'timecode': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Video']"})
        },
        'videoportal.hotfolder': {
            'Meta': {'object_name': 'Hotfolder'},
            'activated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'defaultName': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'folderName': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'videoportal.video': {
            'Meta': {'object_name': 'Video'},
            'assemblyid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'audioThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'autoPublish': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videoportal.Channel']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'encodingDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.IntegerField', [], {'max_length': '1'}),
            'linkURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'mp3Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp3URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'mp4Size': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'mp4URL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'oggSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'oggURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'originalFile': ('django.db.models.fields.files.FileField', [], {'max_length': '2048', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'torrentDone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'torrentURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'videoThumbURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'webmSize': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'webmURL': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['videoportal']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User

from autoslug import AutoSlugField
from taggit.managers import TaggableManager

import appsettings as settings

from pytranscode.ffmpeg import *
from pytranscode.presets import *
from pytranscode.runner import *

import os
import subprocess
import re
import decimal 
from mutagen import File

import urllib2
import datetime
import os
import re
from threading import Event

from BitTornadoABC.btmakemetafile import calcsize, make_meta_file, ignore

KIND_CHOICES = (
    (0, 'Video-only'),
    (1, 'Audio-only'),
    (2, 'Audio & Video'),
)

class Video(models.Model):
    ''' The model for our videos. It uses slugs (with DjangoAutoSlug) and tags (with Taggit)
    everything else is quite standard. The sizes fields are used in the feeds to make enclosures
    possible. The videoThumbURL is the URL for Projekktor's "poster" and assemblyid is just a storage
    for the result we get back from transloadit so that we know which video just triggered the "encoding_done"
    view. Why are there URL fields and not file fields? Because you maybe want to use external storage
    (like Amazon S3) to store your files '''

    created = models.DateTimeField(auto_now_add=True)
    channel = models.ForeignKey('videoportal.Channel',blank=True,null=True)
    date = models.DateField("Datum")
    description = models.TextField(u"Beschreibung")
    linkURL = models.URLField("Link",blank=True,verify_exists=False)
    modified = models.DateTimeField(auto_now=True)
    originalFile = models.FileField("Datei",upload_to="raw/%Y/%m/%d/", max_length=2048)
    tags = TaggableManager("Tags")
    title = models.CharField(u"Titel",max_length=200)

    assemblyid = models.CharField("Transloadit Result",max_length=100,blank=True)
    audioThumbURL = models.URLField("Audio Cover-URL",blank=True,verify_exists=False)
    autoPublish = models.BooleanField(default=True)
    duration = models.DecimalField(null=True, max_digits=10, decimal_places=2,blank=True)
    encodingDone = models.BooleanField()
    kind = models.IntegerField("Art",max_length=1, choices=KIND_CHOICES)
    mp4URL = models.URLField("MP4-URL",blank=True,verify_exists=False)
    mp4Size = models.BigIntegerField("MP4 Size in Bytes",null=True,blank=True)
    mp3URL = models.URLField("MP3-URL",blank=True,verify_exists=False)
    mp3Size = models.BigIntegerField("MP3 Size in Bytes",null=True,blank=True)
    oggURL = models.URLField("OGG-URL",blank=True,verify_exists=False)
    oggSize = models.BigIntegerField("OGG Size in Bytes",null=True,blank=True)
    published = models.BooleanField()
    slug = AutoSlugField(populate_from='title',unique=True)
    torrentURL = models.URLField("Torrent-URL",blank=True,verify_exists=False)
    torrentDone = models.BooleanField()
    user = models.ForeignKey(User, blank=True, null=True)
    videoThumbURL = models.URLField("Video Thumb-URL",blank=True,verify_exists=False)
    webmURL = models.URLField("WEBM-URL",blank=True,verify_exists=False)
    webmSize = models.BigIntegerField("WEBM Size in Bytes",null=True,blank=True)

    def __unicode__(self):
        return self.title
    def get_absolute_url(self):
        return "/videos/%s/" % self.slug
    def getClassName(self):
        return self.__class__.__name__

    def encode_media(self):
        ''' This is used to tell ffmpeg what to do '''
        kind = self.kind
        path = self.originalFile.path
        outputdir = settings.ENCODING_OUTPUT_DIR + self.slug
        if not os.path.exists(outputdir):
            os.makedirs(outputdir)
        outputdir = outputdir + '/'
        if ((kind == 0) or (kind == 2)):
            logfile = outputdir + 'encoding_mp4_log.txt'
            outfile_mp4 = outputdir + self.slug + '.mp4'
            # Create the command line
            cl_mp4 = ffmpeg(path, outfile_mp4, logfile, OWNTUBE_MP4_VIDEO, OWNTUBE_MP4_AUDIO).build_command_line()
            
            logfile = outputdir + 'encoding_webm_log.txt'
            outfile_webm = outputdir + self.slug + '.webm'
    
            cl_webm = ffmpeg(path, outfile_webm, logfile, OWNTUBE_WEBM_VIDEO, OWNTUBE_WEBM_AUDIO).build_command_line()
            
            self.mp4URL = settings.ENCODING_VIDEO_BASE_URL + self.slug + '/' + self.slug + '.mp4'
            self.webmURL = settings.ENCODING_VIDEO_BASE_URL + self.slug + '/' + self.slug + '.webm' 
            self.videoThumbURL = settings.ENCODING_VIDEO_BASE_URL + self.slug + '/' + self.slug + '.jpg'
            outcode = subprocess.Popen(cl_mp4, shell=True)
            
            while outcode.poll() == None:
                pass
    
            if outcode.poll() == 0:
                self.mp4Size = os.path.getsize(outfile_mp4)
                self.duration = getLength(outfile_mp4)
            else:
                raise StandardError('Encoding MP4 Failed')
            
            print(cl_mp4)
            print(cl_webm)    
            outcode = subprocess.Popen(cl_webm, shell=True)
            
            while outcode.poll() == None:
                pass
    
            if outcode.poll() == 0:
                self.wembSize = os.path.getsize(outfile_webm)
            else:
                raise StandardError('Encoding WEBM Failed')
    
            outcode = subprocess.Popen(['/usr/local/bin/ffmpeg -i '+ self.originalFile.path + ' -ss 5.0 -vframes 1 -f image2 ' + outputdir + self.slug + '.jpg'],shell = True)
            
            while outcode.poll() == None:
                pass
    
            if outcode.poll() == 0:
                pass 
            else:
                raise StandardError('Making Thumb Failed')
            
            
        if((kind == 1) or (kind == 2)):
            logfile = outputdir + 'encoding_mp3_log.txt'
            outfile_mp3 = outputdir + self.slug + '.mp3'
            # Create the command line
            cl_mp3 = ffmpeg(path, outfile_mp3, logfile, OWNTUBE_NULL_VIDEO , OWNTUBE_MP3_AUDIO).build_command_line()
            
            logfile = outputdir + 'encoding_ogg_log.txt'
            outfile_ogg = outputdir + self.slug + '.ogg'

            cl_ogg = ffmpeg(path, outfile_ogg, logfile, OWNTUBE_NULL_VIDEO, OWNTUBE_OGG_AUDIO).build_command_line()
            
            self.mp3URL = settings.ENCODING_VIDEO_BASE_URL + self.slug +  '/' + self.slug + '.mp3'
            self.oggURL = settings.ENCODING_VIDEO_BASE_URL + self.slug +  '/' + self.slug + '.ogg'
            
            outcode = subprocess.Popen(cl_mp3, shell=True)
            
            while outcode.poll() == None:
                pass
    
            if outcode.poll() == 0:
                self.mp3Size = os.path.getsize(outfile_mp3)
                self.duration = getLength(outfile_mp3)
            else:
                raise StandardError('Encoding MP3 Failed')
                
            outcode = subprocess.Popen(cl_ogg, shell=True)
            
            while outcode.poll() == None:
                pass
    
            if outcode.poll() == 0:
                self.oggSize = os.path.getsize(outfile_ogg)
            else:
                raise StandardError('Encoding OGG Failed')
                
        if (kind == 1):
            file = File(self.originalFile.path) # mutagen can automatically detect format and type of tags
            if file.tags and 'APIC:' in file.tags and file.tags['APIC:']:
                artwork = file.tags['APIC:'].data # access APIC frame and grab the image
                with open(outputdir + self.slug + '_cover.jpg', 'wb') as img:
                    img.write(artwork)

                self.audioThumbURL = settings.ENCODING_VIDEO_BASE_URL + self.slug + '/' + self.slug + '_cover.jpg'

        self.encodingDone = True
        self.torrentDone = settings.USE_BITTORRENT
        if settings.USE_BITTORRENT:
            self.torrentURL = settings.BITTORRENT_FILES_BASE_URL + self.slug + '.torrent'
            
        self.published = self.autoPublish
        self.save()
        
    def create_bittorrent(self):
        ''' This is where the bittorrent files are created and transmission is controlled'''
        flag = Event()
        make_meta_file(str(self.originalFile.path),
            settings.BITTORRENT_TRACKER_ANNOUNCE_URL,
            params = {'target' : settings.BITTORRENT_FILES_DIR
                                            + self.slug + '.torrent',
             'piece_size_pow2' : 18,
             'announce_list': settings.BITTORRENT_TRACKER_BACKUP,
             'url_list' : str(self.originalFile.url)},
             flag = flag,
             progress_percent=0)
        self.torrentURL = settings.BITTORRENT_FILES_BASE_URL + self.slug + '.torrent'
        self.torrentDone = True
        self.published = self.autoPublish
        self.save()
        
class Comment(models.Model):
    ''' The model for our comments, please note that (right now) OwnTube comments are moderated only'''
    name = models.CharField(u"Name",max_length=30)
    ip = models.IPAddressField("IP",blank=True,null=True)
    moderated = models.BooleanField()
    timecode = models.DecimalField(null=True, max_digits=10, decimal_places=2,blank=True)
    comment = models.TextField(u"Kommentar", max_length=1000)
    video = models.ForeignKey(Video)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return self.comment

class Channel(models.Model):
    ''' The model for our channels, all channels can hold videos but videos can only be part of one channel'''
    name = models.CharField(u"Name",max_length=30)
    slug = AutoSlugField(populate_from='name',unique=True)
    description = models.TextField(u"Beschreibung", max_length=1000, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    featured = models.BooleanField()
    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/videos/channel/%s/" % self.slug

class Hotfolder(models.Model):
    ''' This is used for hotfolder support. Files in one of these will be added to owntube automagicly using a cron job and a manage task '''
    activated = models.BooleanField()
    channel = models.ForeignKey(Channel)
    folderName = models.CharField(u"Ordnername",max_length=30)
    defaultName = models.CharField(u"Standard Titel",max_length=30, blank=True)
    description = models.TextField(u"Standardbeschreibung", max_length=1000, null=True, blank=True)
    autoPublish = models.BooleanField(u"Automatisch Veroeffentlichen")
    kind = models.IntegerField("Art",max_length=1, choices=KIND_CHOICES)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.folderName

class Collection(models.Model):
    title = models.CharField(u"Titel", max_length=40)
    description = models.TextField(u"Beschreibung", max_length=1000)
    slug = AutoSlugField(populate_from='title',unique=True)
    date = models.DateField("Datum",null=True)
    videos = models.ManyToManyField('videoportal.Video')
    channel = models.ForeignKey('videoportal.Channel',blank=True,null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return self.title
    def getClassName(self):
        return self.__class__.__name__
    def get_absolute_url(self):
        return "/collection/%s/" % self.slug

def getLength(filename):
    ''' Just a little helper to get the duration (in seconds) from a video file using ffmpeg '''
    process = subprocess.Popen(['/usr/local/bin/ffmpeg',  '-i', filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = process.communicate()
    matches = re.search(r"Duration:\s{1}(?P<hours>\d+?):(?P<minutes>\d+?):(?P<seconds>\d+\.\d+?),", stdout, re.DOTALL).groupdict()
    duration = decimal.Decimal(matches['hours'])*3600 + decimal.Decimal(matches['minutes'])*60 + decimal.Decimal(matches['seconds'])
    return duration

########NEW FILE########
__FILENAME__ = custom_filters
from django import template
import datetime

register = template.Library()

@register.filter(name='secondstohms')
def secondstohms(value):
    ''' This is used to have a nicer format for the video duration in the template'''
    if (value):
        return str(datetime.timedelta(seconds=int(value)))

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
# TO DO: CLEANING!!!
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django import forms
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.generic.list_detail import object_list
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core import serializers

from videoportal.models import Video, Comment, Channel, Collection
from videoportal.forms import VideoForm, CommentForm
from transloadit.client import Client
from taggit.models import Tag
import appsettings as settings

import djangotasks

import simplejson as json
import urllib2
import datetime
import os
import shutil
import re
from threading import Event
from traceback import print_exc
from sys import argv
from operator import attrgetter
import itertools

def list(request):
    ''' This view is the front page of OwnTube. It just gets the first 15 available video and
    forwards them to the template. We use Django's Paginator to have pagination '''
    queryset = itertools.chain(Video.objects.filter(encodingDone=True, published=True).order_by('-date','-modified'),Collection.objects.all().order_by('-created'))
    queryset_sorted = sorted(queryset, key=attrgetter('date', 'created'), reverse=True)
    paginator = Paginator(queryset_sorted,15)
    channel_list = Channel.objects.all()
    
    page = request.GET.get('page')
    try:
        videos = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        videos = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        videos = paginator.page(paginator.num_pages)
    return render_to_response('videos/index.html', {'latest_videos_list': videos, 'channel_list': channel_list},
                            context_instance=RequestContext(request))

def channel_list(request,slug):
    ''' This view is the view for the channels video list it works almost like the index view'''
    channel = get_object_or_404(Channel, slug=slug)
#    videos_list = Video.objects.filter(encodingDone=True, published=True, channel__slug=slug).order_by('-date','-modified')
    queryset = itertools.chain(Video.objects.filter(encodingDone=True, published=True, channel__slug=slug).order_by('-date','-modified'),Collection.objects.filter(channel__slug=slug).order_by('-created'))
    queryset_sorted = sorted(queryset, key=attrgetter('date', 'created'), reverse=True)
    paginator = Paginator(queryset_sorted,15)
    channel_list = Channel.objects.all()
    page = request.GET.get('page')
    try:
        videos = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        videos = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        videos = paginator.page(paginator.num_pages)
    return render_to_response('videos/channel.html', {'videos_list': videos, 'channel': channel, 'channel_list': channel_list},
                            context_instance=RequestContext(request))

def detail(request, slug):
    ''' Handles the detail view of a video (the player so to say) and handles the comments (this should become nicer with AJAX and stuff)'''
    if request.method == 'POST':
            comment = Comment(video=Video.objects.get(slug=slug),ip=request.META["REMOTE_ADDR"])
            video = get_object_or_404(Video, slug=slug)
            emptyform = CommentForm()
            form = CommentForm(request.POST, instance=comment)
            if form.is_valid():
                    comment = form.save(commit=False)
                    comment.save()
                    comments = Comment.objects.filter(moderated=True, video=video).order_by('-created')
                    message = "Ihr Kommentar muss noch freigeschaltet werden"
            
            return render_to_response('videos/detail.html', {'video': video, 'comment_form': emptyform, 'comments': comments, 'message': message}, context_instance=RequestContext(request))
                    
    else:
        video = get_object_or_404(Video, slug=slug)
        form = CommentForm()
        comments = Comment.objects.filter(moderated=True, video=video).order_by('-created')
        return render_to_response('videos/detail.html', {'video': video, 'comment_form': form, 'comments': comments},
                            context_instance=RequestContext(request))

def iframe(request, slug):
    ''' Returns an iframe for a video so that videos can be shared easily '''                         
    video = get_object_or_404(Video, slug=slug)
    return render_to_response('videos/iframe.html', {'video': video}, context_instance=RequestContext(request))


def tag(request, tag):
    ''' Gets all videos for a specified tag'''
    videolist = Video.objects.filter(encodingDone=True, published=True, tags__slug__in=[tag]).order_by('-date')
    tag_name = get_object_or_404(Tag, slug=tag)
    return render_to_response('videos/list.html', {'videos_list': videolist, 'tag':tag_name},
                            context_instance=RequestContext(request))

def collection(request, slug):
    ''' Gets all videos for a channel'''
    collection = get_object_or_404(Collection, slug=slug)
    videolist = collection.videos.filter(encodingDone=True, published=True)
    return render_to_response('videos/collection.html', {'videos_list': videolist, 'collection':collection},
                            context_instance=RequestContext(request))
                            
def search(request):
    ''' The search view for handling the search using Django's "Q"-class (see normlize_query and get_query)'''
    query_string = ''
    found_entries = None
    if ('q' in request.GET) and request.GET['q'].strip():
        query_string = request.GET['q']
        
        entry_query = get_query(query_string, ['title', 'description', 'tags__name'])
        
        found_entries = Video.objects.filter(entry_query).order_by('-date')

    return render_to_response('videos/search_results.html',
                          { 'query_string': query_string, 'videos_list': found_entries },
                          context_instance=RequestContext(request))

def search_json(request):
    ''' The search view for handling the search using Django's "Q"-class (see normlize_query and get_query)'''
    query_string = ''
    found_entries = None
    if ('q' in request.GET) and request.GET['q'].strip():
        query_string = request.GET['q']

        entry_query = get_query(query_string, ['title', 'description','tags__name'])

        found_entries = Video.objects.filter(entry_query).order_by('-date')

    data = serializers.serialize('json', found_entries)
    return HttpResponse(data, content_type = 'application/javascript; charset=utf8')
           
def tag_json(request, tag):
    videolist = Video.objects.filter(encodingDone=True, published=True, tags__name__in=[tag]).order_by('-date')
    data = serializers.serialize('json', videolist)
    return HttpResponse(data, content_type = 'application/javascript; charset=utf8')

@login_required(login_url='/login/')
def submit(request):
    ''' The view for uploading the videos. Only authenticated users can upload videos!
    If we use transloadit to encode the videos we use the more or less official python
    "API" to ask transloadit to transcode our files otherwise we use django tasks to make
    a new task task for encoding this video. If we use bittorrent to distribute our files
    we also use django tasks to make the .torrent files (this can take a few minutes for
    very large files '''
    if request.user.is_authenticated():
        if request.method == 'POST':
            form = VideoForm(request.POST, request.FILES or None)
            if form.is_valid():
                    cmodel = form.save()
                    if cmodel.originalFile:
                        if settings.USE_TRANLOADIT:
                            client = Client(settings.TRANSLOAD_AUTH_KEY, settings.TRANSLOAD_AUTH_SECRET)
                            params = None
                            if (cmodel.kind==0):
                                params = {
                                    'steps': {
                                        ':original': {
                                            'robot': '/http/import',
                                            'url': cmodel.originalFile.url,
                                        }
                                    },
                                    'template_id': settings.TRANSLOAD_TEMPLATE_VIDEO_ID,
                                    'notify_url': settings.TRANSLOAD_NOTIFY_URL
                                }
                            if (cmodel.kind==1):
                                params = {
                                    'steps': {
                                        ':original': {
                                            'robot': '/http/import',
                                            'url': cmodel.originalFile.url,
                                        }
                                    },
                                    'template_id': settings.TRANSLOAD_TEMPLATE_AUDIO_ID,
                                    'notify_url': settings.TRANSLOAD_NOTIFY_URL
                                }
                            if (cmodel.kind==2):
                                params = {
                                    'steps': {
                                        ':original': {
                                            'robot': '/http/import',
                                            'url': cmodel.originalFile.url,
                                        }
                                    },
                                    'template_id': settings.TRANSLOAD_TEMPLATE_VIDEO_AUDIO_ID,
                                    'notify_url': settings.TRANSLOAD_NOTIFY_URL
                                }
                            result = client.request(**params)
                            cmodel.assemblyid = result['assembly_id']
                            cmodel.published = cmodel.autoPublish
                            cmodel.encodingDone = False
                            cmodel.save()
                        else:
                            cmodel.save()
                            djangotasks.register_task(cmodel.encode_media, "Encode the files using ffmpeg")
                            encoding_task = djangotasks.task_for_object(cmodel.encode_media)
                            djangotasks.run_task(encoding_task)
                    if settings.USE_BITTORRENT:
                        djangotasks.register_task(cmodel.create_bittorrent, "Create Bittorrent file for video and serve it")
                        torrent_task = djangotasks.task_for_object(cmodel.create_bittorrent)
                        djangotasks.run_task(torrent_task)
                    cmodel.user = request.user
                    cmodel.save()
                    return redirect(list)
    
            return render_to_response('videos/submit.html',
                                    {'submit_form': form},
                                    context_instance=RequestContext(request))
        else:
            form = VideoForm()
            return render_to_response('videos/submit.html',
                                    {'submit_form': form},
                                    context_instance=RequestContext(request))
    else:
        return render_to_response('videos/nothing.html',
                            context_instance=RequestContext(request))

@login_required(login_url='/login/')
def status(request):
    if settings.USE_BITTORRENT:
        processing_videos = Video.objects.filter(Q(encodingDone=False) | Q(torrentDone=False))
    else:
        processing_videos = Video.objects.filter(encodingDone=False)
    running_tasks = []
    for video in processing_videos:
        tasks = djangotasks.models.Task.objects.filter(model="videoportal.video", object_id=video.pk)
        running_tasks.append(tasks)
    return render_to_response('videos/status.html',
                                    {'processing_videos': processing_videos, 'running_tasks': running_tasks},
                                    context_instance=RequestContext(request))

@csrf_exempt
def encodingdone(request):
    ''' This is a somewhat special view: It is called by transloadit to tell
    OwnTube that the encoding process is done. The view then parses the
    JSON data in the POST request send by transloadit and than get this information
    into our video model. Of course it can be possible for attackers to alter videos
    using for example curl but they would need to guess a assembly_id and these are 
    quite long hex strings. To improve the security we could also use the custom header
    option from transloadit but I think this wouldn't really help in a open source project'''
    if request.method == 'POST':
        data = json.loads(request.POST['transloadit'])
        try:
            video = Video.objects.get(assemblyid=data['assembly_id'])
            if (video.kind == 0):
                results = data['results']
                resultItem = results[settings.TRANSLOAD_MP4_ENCODE]
                resultFirst = resultItem[0]
                video.mp4URL = resultFirst['url']
                video.mp4Size = resultFirst['size']
                resultMeta = resultFirst['meta']
                video.duration = str(resultMeta['duration'])
                resultItem = results[settings.TRANSLOAD_WEBM_ENCODE]
                resultFirst = resultItem[0]
                video.webmURL = resultFirst['url']
                video.webmSize = resultFirst['size']
                resultItem = results[settings.TRANSLOAD_THUMB_ENCODE]
                resultFirst = resultItem[0]
                video.videoThumbURL = resultFirst['url']
            elif (video.kind == 1):
                results = data['results']
                resultItem = results[settings.TRANSLOAD_MP3_ENCODE]
                resultFirst = resultItem[0]
                video.mp3URL = resultFirst['url']
                video.mp3Size = resultFirst['size']
                resultMeta = resultFirst['meta']
                video.duration = str(resultMeta['duration'])
                resultItem = results[settings.TRANSLOAD_OGG_ENCODE]
                resultFirst = resultItem[0]
                video.oggURL = resultFirst['url']
                video.oggSize = resultFirst['size']
            elif (video.kind == 2):
                results = data['results']
                resultItem = results[settings.TRANSLOAD_MP4_ENCODE]
                resultFirst = resultItem[0]
                video.mp4URL = resultFirst['url']
                video.mp4Size = resultFirst['size']
                resultMeta = resultFirst['meta']
                video.duration = str(resultMeta['duration'])
                resultItem = results[settings.TRANSLOAD_WEBM_ENCODE]
                resultFirst = resultItem[0]
                video.webmURL = resultFirst['url']
                video.webmSize = resultFirst['size']
                resultItem = results[settings.TRANSLOAD_MP3_ENCODE]
                resultFirst = resultItem[0]
                video.mp3URL = resultFirst['url']
                video.mp3Size = resultFirst['size']
                resultItem = results[settings.TRANSLOAD_OGG_ENCODE]
                resultFirst = resultItem[0]
                video.oggURL = resultFirst['url']
                video.oggSize = resultFirst['size']
                resultItem = results[settings.TRANSLOAD_THUMB_ENCODE]
                resultFirst = resultItem[0]
                video.videoThumbURL = resultFirst['url']
            video.encodingDone = True
            video.save()
        except Video.DoesNotExist:
            raise Http404
        return HttpResponse("Video was updated")

    else:
        return render_to_response('videos/nothing.html',
                            context_instance=RequestContext(request))
    

def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:
        
        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
    
    '''
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] 

def get_query(query_string, search_fields):
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
    
    '''
    query = None # Query to search for every search term        
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query                      

########NEW FILE########
