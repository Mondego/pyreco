__FILENAME__ = admin
from django.contrib import admin
from board.models import Service, Status, Event

class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(Service, ServiceAdmin)


class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'severity')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(Status, StatusAdmin)


class EventAdmin(admin.ModelAdmin):
    list_display = ('start', 'service', 'status', 'message')
    list_filter = ('service', 'status')

admin.site.register(Event, EventAdmin)




########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings
from django.contrib.sites.models import Site

def current_site(request):
    return {'current_site': Site.objects.get_current()}



########NEW FILE########
__FILENAME__ = feeds
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from board.models import Event

class EventFeed(Feed):
    description = "Latest status updates."
    link = '/'
    feed_type = Atom1Feed
    
    def title(self):
        return Site.objects.get_current().name

    def items(self):
        return Event.objects.order_by('-start')[:25]

    def item_title(self, item):
        if item.informational:
            status = 'Information'
        else:
            status = item.status.name
        return '%s: %s' % (item.service.name, status)

    def item_description(self, item):
        return item.message

    def item_link(self, item):
        return item.service.get_absolute_url()



########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Service'
        db.create_table('board_service', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('board', ['Service'])

        # Adding model 'Status'
        db.create_table('board_status', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('severity', self.gf('django.db.models.fields.IntegerField')()),
            ('image', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('board', ['Status'])

        # Adding model 'Event'
        db.create_table('board_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['board.Service'])),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['board.Status'])),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('start', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('informational', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('board', ['Event'])


    def backwards(self, orm):
        
        # Deleting model 'Service'
        db.delete_table('board_service')

        # Deleting model 'Status'
        db.delete_table('board_status')

        # Deleting model 'Event'
        db.delete_table('board_event')


    models = {
        'board.event': {
            'Meta': {'ordering': "('-start',)", 'object_name': 'Event'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'informational': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['board.Service']"}),
            'start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['board.Status']"})
        },
        'board.service': {
            'Meta': {'object_name': 'Service'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'board.status': {
            'Meta': {'object_name': 'Status'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'severity': ('django.db.models.fields.IntegerField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['board']

########NEW FILE########
__FILENAME__ = 0002_initial_statuses
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        orm.Status.objects.create(
            name="Down", 
            slug="down", 
            image="cross-circle", 
            severity=40,
            description="The service is currently down"
        )
        orm.Status.objects.create(
            name="Up", 
            slug="up", 
            image="tick-circle", 
            severity=10,
            description="The service is up"
        )
        orm.Status.objects.create(
            name="Warning", 
            slug="warning", 
            image="exclamation", 
            severity=30,
            description="The service is experiencing intermittent problems"
        )



    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'board.event': {
            'Meta': {'ordering': "('-start',)", 'object_name': 'Event'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'informational': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['board.Service']"}),
            'start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['board.Status']"})
        },
        'board.service': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Service'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'board.status': {
            'Meta': {'object_name': 'Status'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'severity': ('django.db.models.fields.IntegerField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['board']

########NEW FILE########
__FILENAME__ = models
from datetime import datetime, date, timedelta
from django.db import models

class Service(models.Model):
    """
    A service to track.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name
    
    @models.permalink
    def get_absolute_url(self):
        return ('service', [self.slug])

    def last_five_days(self):
        """
        Used on home page.
        """
        lowest = Status.objects.default()
        severity = lowest.severity
        
        yesterday = date.today() - timedelta(days=1)
        ago = yesterday - timedelta(days=5)
        
        events = self.events.filter(start__gt=ago, start__lt=yesterday)
        
        stats = {}
        
        for i in range(5):
            stats[yesterday.day] = {
                "image": lowest.image,
                "day": yesterday,
            }
            yesterday = yesterday - timedelta(days=1)
        
        for event in events:
            if event.status.severity > severity:
                if event.start.day in stats:
                    stats[event.start.day]["image"] = "information"
                    stats[event.start.day]["information"] = True

        results = []

        keys = stats.keys()
        keys.sort()
        keys.reverse()

        for k in keys:
            results.append(stats[k])
            
        return results
    


class StatusManager(models.Manager):
    def default(self):
        return self.get_query_set().filter(severity=10)[0]

class Status(models.Model):
    """
    A possible system status.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.CharField(max_length=255)
    SEVERITY_CHOICES = (
        (10, 'NORMAL'),
        (30, 'WARNING'),
        (40, 'ERROR'),
        (50, 'CRITICAL'),
    )
    severity = models.IntegerField(choices=SEVERITY_CHOICES)
    image = models.CharField(max_length=100)

    objects = StatusManager()

    class Meta:
        ordering = ('severity',)
        verbose_name_plural = 'statuses'

    def __unicode__(self):
        return self.name


class Event(models.Model):
    service = models.ForeignKey(Service, related_name='events')
    status = models.ForeignKey(Status, related_name='events')
    message = models.TextField()
    start = models.DateTimeField(default=datetime.now)
    informational = models.BooleanField(default=False)

    class Meta:
        ordering = ('-start',)
        get_latest_by = 'start'



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
from board.models import Service, Status
import datetime
from django.views.generic import ListView, DetailView

class BoardMixin(object):
    def get_context_data(self, **kwargs):
        context = super(BoardMixin, self).get_context_data(**kwargs)
        context['statuses'] = Status.objects.all()
        return context


def get_past_days(num):
    date = datetime.date.today()
    dates = []
    
    for i in range(1, num+1):
        dates.append(date - datetime.timedelta(days=i))
    
    return dates


class IndexView(BoardMixin, ListView):
    context_object_name = 'services'
    queryset = Service.objects.all()
    template_name = 'board/index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['default'] = Status.objects.default()
        context['past'] = get_past_days(5)
        return context


class ServiceView(BoardMixin, DetailView):
    model = Service


########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import local, env
import os
import random

def app(app):
    env['app'] = app

def setup():
    if not os.path.exists('settings/local.py'):
        with open('settings/local.py', 'w') as fp:
            secret_key = ''.join([
                random.choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
                for i in range(50)
            ])
            fp.write('SECRET_KEY = "%s"\n' % secret_key)

def deploy():
    setup()
    local("./manage.py collectstatic --noinput")
    local("./manage.py syncdb")
    local("./manage.py migrate")


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
__FILENAME__ = base
from unipath import FSPath as Path
PROJECT_DIR = Path(__file__).absolute().ancestor(2)

######################################
# Main
######################################

DEBUG = True
ROOT_URLCONF = 'urls'
SITE_ID = 1

######################################
# Apps
######################################

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
    'board',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

######################################
# Database
######################################

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'whiskerboard',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

######################################
# Localisation
######################################

TIME_ZONE = 'Europe/London'
LANGUAGE_CODE = 'en-gb'
USE_I18N = True
USE_L10N = True


######################################
# Logging
######################################

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

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


######################################
# Media/Static
######################################

MEDIA_ROOT = PROJECT_DIR.parent.child('data')
MEDIA_URL = '/media/'

STATIC_ROOT = PROJECT_DIR.child('static_root')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    str(PROJECT_DIR.child('static')),
)
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

######################################
# Templates
######################################

TEMPLATE_DEBUG = DEBUG

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    PROJECT_DIR.child('templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    'board.context_processors.current_site',
)


########NEW FILE########
__FILENAME__ = live
from __future__ import absolute_import
from .base import *
from .local import *

CACHE_BACKEND = 'redis_cache.cache://127.0.0.1:6379/?timeout=15'
DEBUG = False


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
from board.feeds import EventFeed
from board.views import IndexView, ServiceView

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^services/(?P<slug>[-\w]+)$', ServiceView.as_view(), name='service'),
    url(r'^feed$', EventFeed(), name='feed'),

    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
