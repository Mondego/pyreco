__FILENAME__ = settings
# Django settings for example project.
import os
from dj_settings_helpers import create_project_dir
project_dir = create_project_dir(os.path.join(os.path.dirname(__file__),
        '..', '..'))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': project_dir('project.db'),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

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

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'staticfiles.finders.FileSystemFinder',
    'staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '8d24sz0q0^mo3#uz_6!ne9@#!q*gvteao5b!_p6o940ar3-%=0'

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

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    project_dir('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    'abstract_templates',
    'jquery',
    'south',
    'timelinejs_static',

    'timelinejs',
    'example_usage',
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
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'example.views.home', name='home'),
    # url(r'^example/', include('example.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^$', TemplateView.as_view(template_name='index.html')),
    url(r'api/timelinejs/', include('timelinejs.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

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
import datetime
import json
import random

from django.test import TestCase
import factory

from timelinejs import models

seq = lambda s: factory.Sequence(lambda n: s.format(n))


def generate_random_start_date(*args):
    now = datetime.datetime.now()
    r = random.randint(-10, 10)
    return (now - datetime.timedelta(days=r)).date()


class AssetFactory(factory.Factory):
    FACTORY_FOR = models.Asset

    media = seq('media-{0}.png')
    credit = seq('credit-{0}')
    caption = seq('caption-{0}')


class TimelineFactory(factory.Factory):
    FACTORY_FOR = models.Timeline

    headline = seq('headline-{0}')
    start_date = factory.LazyAttribute(generate_random_start_date)
    text = seq('<p>Random Text{0}</p>')
    asset = factory.SubFactory(AssetFactory)


class TimelineEntryFactory(factory.Factory):
    FACTORY_FOR = models.TimelineEntry

    timeline = factory.SubFactory(TimelineFactory)
    start_date = factory.LazyAttribute(generate_random_start_date)
    headline = seq('timeline-entry-headline-{0}')
    text = seq('<p>Timeline Entry Text {0}</p>')
    asset = factory.SubFactory(AssetFactory)


def generate_random_asset(save=True):
    return AssetFactory.create() if save else AssetFactory.build()


def generate_random_timeline(save=True):
    return TimelineFactory.create() if save else TimelineFactory.build()


def generate_random_timeline_entry(timeline, save=True):
    return TimelineEntryFactory.create() if save else \
        TimelineFactory.build()


class AssetTestCase(TestCase):
    def test_unicode_shows_caption(self):
        asset = AssetFactory.build()
        self.assertEqual(asset.caption, str(asset))

    def test_to_json(self):
        """
        Verify that to_json returns appropriate JSON object
        """
        media = 'some-asset-%d.png' % random.randint(1000, 2000)
        credit = 'Some Random Credit %d' % random.randint(100, 200)
        caption = '<p>I\'m an HTML caption!</p>'
        m = models.Asset(media=media, credit=credit, caption=caption)

        expected = json.dumps({'media': media, 'credit': credit,
                'caption': caption})
        self.assertEqual(expected, m.to_json())


class TimelineEntryTestCase(TestCase):
    @property
    def timeline_entry_kwargs(self):
        return TimelineFactory.attributes()

    def test_unicode_shows_timeline_plus_headline(self):
        entry = TimelineEntryFactory.build()
        expected = '{0}: {1}'.format(entry.timeline, entry.headline)
        self.assertEqual(expected, str(entry))

    def test_to_json_dict(self):
        kwargs = self.timeline_entry_kwargs
        entry = models.TimelineEntry(**kwargs)
        expected = {
            'startDate': kwargs['start_date'].strftime('%Y,%m,%d'),
            'headline': kwargs['headline'],
            'text': kwargs['text'],
            'asset': kwargs['asset'].to_json_dict(),
        }
        self.assertEqual(expected, entry.to_json_dict())

    def test_to_json(self):
        kwargs = self.timeline_entry_kwargs
        entry = models.TimelineEntry(**kwargs)
        expected = json.dumps({
            'startDate': kwargs['start_date'].strftime('%Y,%m,%d'),
            'headline': kwargs['headline'],
            'text': kwargs['text'],
            'asset': kwargs['asset'].to_json_dict()
        })
        self.assertEqual(expected, entry.to_json())

    def test_can_convert_to_json_with_string_dates(self):
        kwargs = self.timeline_entry_kwargs
        kwargs['start_date'] = kwargs['start_date'].strftime('%Y-%m-%d')
        entry = models.TimelineEntry(**kwargs)
        entry.to_json()


class TimelineTestCase(TestCase):
    @property
    def timeline_kwargs(self):
        return TimelineFactory.attributes()

    def test_unicode_shows_headline(self):
        timeline = TimelineFactory.build()
        self.assertEqual(timeline.headline, str(timeline))

    def test_to_json(self):
        kwargs = self.timeline_kwargs
        timeline = models.Timeline(**kwargs)
        expected = json.dumps({'timeline': {
            'headline': kwargs['headline'],
            'type': 'default',
            'startDate': kwargs['start_date'].strftime('%Y,%m,%d'),
            'text': kwargs['text'],
            'asset': kwargs['asset'].to_json_dict(),
            'date': [],
        }})
        self.assertEqual(expected, timeline.to_json())

    def test_can_convert_to_json_with_string_dates(self):
        kwargs = self.timeline_kwargs
        kwargs['start_date'] = kwargs['start_date'].strftime('%Y-%m-%d')
        timeline = models.Timeline(**kwargs)
        timeline.to_json()

    def test_to_json_with_one_date(self):
        entry = TimelineEntryFactory.create()
        timeline = entry.timeline

        expected = [entry.to_json_dict()]
        actual = json.loads(timeline.to_json())['timeline']['date']
        self.assertEqual(expected, actual)

    def test_to_json_with_two_dates(self):
        timeline = TimelineFactory.create()
        entry_a = TimelineEntryFactory.create(timeline=timeline)
        entry_b = TimelineEntryFactory.create(timeline=timeline)

        expected = [entry_a.to_json_dict(), entry_b.to_json_dict()]
        actual = json.loads(timeline.to_json())['timeline']['date']
        self.assertEqual(expected, actual)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

# Ensure that the parent directory with tt_grid is on the sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from . import models


class TimelineEntryInline(admin.TabularInline):
    model = models.TimelineEntry


class TimelineAdmin(admin.ModelAdmin):
    inlines = [
        TimelineEntryInline,
    ]

    prepopulated_fields = {
        'slug': ('headline', ),
    }


admin.site.register(models.Asset)
admin.site.register(models.Timeline, TimelineAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Asset'
        db.create_table('timelinejs_asset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('media', self.gf('django.db.models.fields.TextField')()),
            ('credit', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('caption', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
        ))
        db.send_create_signal('timelinejs', ['Asset'])

        # Adding model 'Timeline'
        db.create_table('timelinejs_timeline', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('asset', self.gf('django.db.models.fields.related.ForeignKey')(related_name='timelines', to=orm['timelinejs.Asset'])),
        ))
        db.send_create_signal('timelinejs', ['Timeline'])

        # Adding model 'TimelineEntry'
        db.create_table('timelinejs_timelineentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('timeline', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entries', to=orm['timelinejs.Timeline'])),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('asset', self.gf('django.db.models.fields.related.ForeignKey')(related_name='timeline_entries', to=orm['timelinejs.Asset'])),
        ))
        db.send_create_signal('timelinejs', ['TimelineEntry'])


    def backwards(self, orm):
        # Deleting model 'Asset'
        db.delete_table('timelinejs_asset')

        # Deleting model 'Timeline'
        db.delete_table('timelinejs_timeline')

        # Deleting model 'TimelineEntry'
        db.delete_table('timelinejs_timelineentry')


    models = {
        'timelinejs.asset': {
            'Meta': {'object_name': 'Asset'},
            'caption': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'credit': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'media': ('django.db.models.fields.TextField', [], {})
        },
        'timelinejs.timeline': {
            'Meta': {'object_name': 'Timeline'},
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'timelines'", 'to': "orm['timelinejs.Asset']"}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'timelinejs.timelineentry': {
            'Meta': {'object_name': 'TimelineEntry'},
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'timeline_entries'", 'to': "orm['timelinejs.Asset']"}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'timeline': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['timelinejs.Timeline']"})
        }
    }

    complete_apps = ['timelinejs']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_timeline_slug
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Timeline.slug'
        db.add_column('timelinejs_timeline', 'slug',
                      self.gf('django.db.models.fields.SlugField')(default='', max_length=50),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Timeline.slug'
        db.delete_column('timelinejs_timeline', 'slug')


    models = {
        'timelinejs.asset': {
            'Meta': {'object_name': 'Asset'},
            'caption': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'credit': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'media': ('django.db.models.fields.TextField', [], {})
        },
        'timelinejs.timeline': {
            'Meta': {'object_name': 'Timeline'},
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'timelines'", 'to': "orm['timelinejs.Asset']"}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '50'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'timelinejs.timelineentry': {
            'Meta': {'object_name': 'TimelineEntry'},
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'timeline_entries'", 'to': "orm['timelinejs.Asset']"}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'timeline': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['timelinejs.Timeline']"})
        }
    }

    complete_apps = ['timelinejs']
########NEW FILE########
__FILENAME__ = models
import json

from dateutil.parser import parse
from django.db import models


class Asset(models.Model):
    media = models.TextField()
    credit = models.TextField(blank=True, default='')
    caption = models.TextField(blank=True, default='')

    def __unicode__(self):
        return self.caption

    def to_json_dict(self):
        return {
            'media': self.media,
            'credit': self.credit,
            'caption': self.caption,
        }

    def to_json(self):
        return json.dumps(self.to_json_dict())


class Timeline(models.Model):
    headline = models.CharField(max_length=255)
    start_date = models.DateField()
    slug = models.SlugField(default='')
    text = models.TextField()
    asset = models.ForeignKey(Asset, related_name='timelines')

    def __unicode__(self):
        return self.headline

    def to_json(self):
        if type(self.start_date) is str:
            self.start_date = parse(self.start_date)
        return json.dumps({"timeline": {
            'headline': self.headline,
            'type': 'default',
            'startDate': self.start_date.strftime('%Y,%m,%d'),
            'text': self.text,
            'asset': self.asset.to_json_dict(),
            'date': [a.to_json_dict() for a in self.entries.all()],
        }})


class TimelineEntry(models.Model):
    timeline = models.ForeignKey(Timeline, related_name='entries')
    start_date = models.DateField()
    headline = models.CharField(max_length=255)
    text = models.TextField()
    asset = models.ForeignKey(Asset, related_name='timeline_entries')

    def __unicode__(self):
        return "%s: %s" % (self.timeline, self.headline)

    def to_json_dict(self):
        if type(self.start_date) is str:
            self.start_date = parse(self.start_date)
        return {
            'startDate': self.start_date.strftime('%Y,%m,%d'),
            'headline': self.headline,
            'text': self.text,
            'asset': self.asset.to_json_dict(),
        }

    def to_json(self):
        return json.dumps(self.to_json_dict())

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    # Support Django 1.3
    from django.conf.urls.defaults import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+).json$', views.TimelineJsonView.as_view(),
            name='timelinejs_json'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.views.generic.detail import BaseDetailView

from . import models


class TimelineJsonView(BaseDetailView):
    model = models.Timeline

    def render_to_response(self, context):
        return HttpResponse(self.object.to_json(), status=200,
                content_type="application/json")

########NEW FILE########
