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
import os.path
import sys

# Experiments Settings
EXPERIMENTS_GOALS = (
    'page_goal',
    'js_goal',
    'cookie_goal',
)

EXPERIMENTS_AUTO_CREATE = True

EXPERIMENTS_SWITCH_AUTO_CREATE = True
EXPERIMENTS_SWITCH_AUTO_DELETE = True

EXPERIMENTS_SWITCH_LABEL = "Experiment: %s"

EXPERIMENTS_VERIFY_HUMAN = True #Careful with this setting, if it is toggled then participant counters will not increment accordingly

# Redis Settings
EXPERIMENTS_REDIS_HOST = 'localhost'
EXPERIMENTS_REDIS_PORT = 6379
EXPERIMENTS_REDIS_DB = 0


# Media Settings
STATIC_URL = '/static/'

# Other settings
# Django settings for example_project project.
NEXUS_MEDIA_PREFIX = '/nexus/media/'

DEBUG = True
TEMPLATE_DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

INTERNAL_IPS = ('127.0.0.1',)

MANAGERS = ADMINS

PROJECT_ROOT = os.path.dirname(__file__)

sys.path.insert(0, os.path.abspath(os.path.join(PROJECT_ROOT, '..')))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'experiments.db',                      # Or path to database file if using sqlite3.
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
TIME_ZONE = 'Europe/London'

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
ADMIN_MEDIA_PREFIX = '/admin/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'gfjo;2r3l;hjropjf30j3fl;m234nc9p;o2mnpfnpfj'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'experiments.middleware.ExperimentsMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'nexus',
    'experiments',
    'gargoyle',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
)

########NEW FILE########
__FILENAME__ = urls
from django.contrib import admin
from django.conf.urls.defaults import patterns, include, url
from django.views.generic import TemplateView

import nexus

admin.autodiscover()
nexus.autodiscover()

urlpatterns = patterns('',
    url(r'nexus/', include(nexus.site.urls)),
    url(r'experiments/', include('experiments.urls')),
    url(r'^$', TemplateView.as_view(template_name="test_page.html"), name="test_page"),
    url(r'^goal/$', TemplateView.as_view(template_name="goal.html"), name="goal"),
)


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from django import forms
from experiments.models import Experiment, Enrollment


class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'state')
    list_filter = ('name', 'start_date', 'state')
    search_fields = ('name', )

admin.site.register(Experiment, ExperimentAdmin)

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings
from itertools import chain
import re

CONTROL_GROUP = 'control'

VISIT_COUNT_GOAL = '_retention_visits'

BUILT_IN_GOALS = (
    VISIT_COUNT_GOAL,
)

USER_GOALS = getattr(settings, 'EXPERIMENTS_GOALS', [])
ALL_GOALS = tuple(chain(USER_GOALS, BUILT_IN_GOALS))

DO_NOT_AGGREGATE_GOALS = (
    VISIT_COUNT_GOAL,
)

VERIFY_HUMAN = getattr(settings, 'EXPERIMENTS_VERIFY_HUMAN', True)

SWITCH_AUTO_CREATE = getattr(settings, 'EXPERIMENTS_SWITCH_AUTO_CREATE', True)
SWITCH_LABEL = getattr(settings, 'EXPERIMENTS_SWITCH_LABEL', "Experiment: %s")
SWITCH_AUTO_DELETE = getattr(settings, 'EXPERIMENTS_SWITCH_AUTO_DELETE', True)

BOT_REGEX = re.compile("(Baidu|Gigabot|Googlebot|YandexBot|AhrefsBot|TVersity|libwww-perl|Yeti|lwp-trivial|msnbot|bingbot|facebookexternalhit|Twitterbot|Twitmunin|SiteUptime|TwitterFeed|Slurp|WordPress|ZIBB|ZyBorg)", re.IGNORECASE)

########NEW FILE########
__FILENAME__ = counters
from django.conf import settings

import redis
from redis.exceptions import ConnectionError, ResponseError

REDIS_HOST = getattr(settings, 'EXPERIMENTS_REDIS_HOST', 'localhost')
REDIS_PORT = getattr(settings, 'EXPERIMENTS_REDIS_PORT', 6379)
REDIS_PASSWORD = getattr(settings, 'EXPERIMENTS_REDIS_PASSWORD', None)
REDIS_EXPERIMENTS_DB = getattr(settings, 'EXPERIMENTS_REDIS_DB', 0)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_EXPERIMENTS_DB)

COUNTER_CACHE_KEY = 'experiments:participants:%s'
COUNTER_FREQ_CACHE_KEY = 'experiments:freq:%s'


def increment(key, participant_identifier, count=1):
    if count == 0:
        return

    try:
        cache_key = COUNTER_CACHE_KEY % key
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        new_value = r.hincrby(cache_key, participant_identifier, count)

        # Maintain histogram of per-user counts
        if new_value > count:
            r.hincrby(freq_cache_key, new_value - count, -1)
        r.hincrby(freq_cache_key, new_value, 1)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        pass


def clear(key, participant_identifier):
    try:
        # Remove the direct entry
        cache_key = COUNTER_CACHE_KEY % key
        pipe = r.pipeline()
        freq, _ = pipe.hget(cache_key, participant_identifier).hdel(cache_key, participant_identifier).execute()

        # Remove from the histogram
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        r.hincrby(freq_cache_key, freq, -1)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        pass


def get(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        return r.hlen(cache_key)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return 0


def get_frequency(key, participant_identifier):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        freq = r.hget(cache_key, participant_identifier)
        return int(freq) if freq else 0
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return 0


def get_frequencies(key):
    try:
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        # In some cases when there are concurrent updates going on, there can
        # briefly be a negative result for some frequency count. We discard these
        # as they shouldn't really affect the result, and they are about to become
        # zero anyway.
        return dict((int(k), int(v)) for (k, v) in r.hgetall(freq_cache_key).items() if int(v) > 0)
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return tuple()


def reset(key):
    try:
        cache_key = COUNTER_CACHE_KEY % key
        r.delete(cache_key)
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % key
        r.delete(freq_cache_key)
        return True
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return False


def reset_pattern(pattern_key):
    #similar to above, but can pass pattern as arg instead
    try:
        cache_key = COUNTER_CACHE_KEY % pattern_key
        for key in r.keys(cache_key):
            r.delete(key)
        freq_cache_key = COUNTER_FREQ_CACHE_KEY % pattern_key
        for key in r.keys(freq_cache_key):
            r.delete(key)
        return True
    except (ConnectionError, ResponseError):
        # Handle Redis failures gracefully
        return False

########NEW FILE########
__FILENAME__ = dateutils
import calendar
from datetime import datetime

from django.conf import settings

USE_TZ = getattr(settings, 'USE_TZ', False)
if USE_TZ:
    from django.utils.timezone import now
else:
    now = datetime.now


def fix_awareness(value):
    tz_aware_value = value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None
    if USE_TZ and not tz_aware_value:
        from django.utils.timezone import get_current_timezone
        return value.replace(tzinfo=get_current_timezone())
    elif not USE_TZ and tz_aware_value:
        return value.replace(tzinfo=None)
    else:
        return value


def timestamp_from_datetime(dt):
    if dt is None:
        return None
    return calendar.timegm(dt.utctimetuple())


def datetime_from_timestamp(ts):
    if ts is None:
        return None
    return datetime.utcfromtimestamp(ts)

########NEW FILE########
__FILENAME__ = manager
from django.conf import settings
from experiments.models import Experiment
from modeldict import ModelDict

experiment_manager = ModelDict(Experiment, key='name', value='value', instances=True, auto_create=getattr(settings, 'EXPERIMENTS_AUTO_CREATE', True))

########NEW FILE########
__FILENAME__ = middleware
from experiments import record_goal

from urllib import unquote


class ExperimentsMiddleware(object):
    def process_response(self, request, response):
        experiments_goal = request.COOKIES.get('experiments_goal', None)
        if experiments_goal:
            for goal in unquote(experiments_goal).split(' '):  # multiple goals separated by space
                record_goal(goal, request)
            response.delete_cookie('experiments_goal')
        return response

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Experiment'
        db.create_table('experiments_experiment', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128, primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
            ('alternatives', self.gf('jsonfield.fields.JSONField')(default='{}', blank=True)),
            ('relevant_goals', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
            ('switch_key', self.gf('django.db.models.fields.CharField')(default='', max_length=50, null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, db_index=True, blank=True)),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('experiments', ['Experiment'])

        # Adding model 'Enrollment'
        db.create_table('experiments_enrollment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm["%s.%s" % (User._meta.app_label, User._meta.object_name)], null=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['experiments.Experiment'])),
            ('enrollment_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, db_index=True, blank=True)),
            ('alternative', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('goals', self.gf('jsonfield.fields.JSONField')(default='[]', blank=True)),
        ))
        db.send_create_signal('experiments', ['Enrollment'])

        # Adding unique constraint on 'Enrollment', fields ['user', 'experiment']
        db.create_unique('experiments_enrollment', ['user_id', 'experiment_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Enrollment', fields ['user', 'experiment']
        db.delete_unique('experiments_enrollment', ['user_id', 'experiment_id'])

        # Deleting model 'Experiment'
        db.delete_table('experiments_experiment')

        # Deleting model 'Enrollment'
        db.delete_table('experiments_enrollment')


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
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User.__name__ },
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'experiments.enrollment': {
            'Meta': {'unique_together': "(('user', 'experiment'),)", 'object_name': 'Enrollment'},
            'alternative': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'enrollment_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['experiments.Experiment']"}),
            'goals': ('jsonfield.fields.JSONField', [], {'default': "'[]'", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), 'null': 'True'})
        },
        'experiments.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'alternatives': ('jsonfield.fields.JSONField', [], {'default': "'{}'", 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'relevant_goals': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'switch_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['experiments']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_enrollment_goals_
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Enrollment.goals'
        db.alter_column('experiments_enrollment', 'goals', self.gf('jsonfield.fields.JSONField')(null=True, blank=True))

        # Adding field 'Experiment.relevant_chi2_goals'
        db.add_column('experiments_experiment', 'relevant_chi2_goals', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True), keep_default=False)

        # Adding field 'Experiment.relevant_mwu_goals'
        db.add_column('experiments_experiment', 'relevant_mwu_goals', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Changing field 'Enrollment.goals'
        db.alter_column('experiments_enrollment', 'goals', self.gf('jsonfield.fields.JSONField')(blank=True))

        # Deleting field 'Experiment.relevant_chi2_goals'
        db.delete_column('experiments_experiment', 'relevant_chi2_goals')

        # Deleting field 'Experiment.relevant_mwu_goals'
        db.delete_column('experiments_experiment', 'relevant_mwu_goals')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User.__name__ },
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'experiments.enrollment': {
            'Meta': {'unique_together': "(('user', 'experiment'),)", 'object_name': 'Enrollment'},
            'alternative': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'enrollment_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['experiments.Experiment']"}),
            'goals': ('jsonfield.fields.JSONField', [], {'default': "'{}'", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), 'null': 'True'})
        },
        'experiments.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'alternatives': ('jsonfield.fields.JSONField', [], {'default': "'{}'", 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'relevant_chi2_goals': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'relevant_mwu_goals': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'switch_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['experiments']

########NEW FILE########
__FILENAME__ = 0003_auto__del_field_enrollment_goals__add_field_enrollment_last_seen__chg_
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Enrollment.goals'
        db.delete_column('experiments_enrollment', 'goals')

        # Adding field 'Enrollment.last_seen'
        db.add_column('experiments_enrollment', 'last_seen', self.gf('django.db.models.fields.DateTimeField')(null=True), keep_default=False)

        # Changing field 'Enrollment.enrollment_date'
        db.alter_column('experiments_enrollment', 'enrollment_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True))


    def backwards(self, orm):
        
        # Adding field 'Enrollment.goals'
        db.add_column('experiments_enrollment', 'goals', self.gf('jsonfield.fields.JSONField')(default='{}', null=True, blank=True), keep_default=False)

        # Deleting field 'Enrollment.last_seen'
        db.delete_column('experiments_enrollment', 'last_seen')

        # Changing field 'Enrollment.enrollment_date'
        db.alter_column('experiments_enrollment', 'enrollment_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User.__name__ },
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'experiments.enrollment': {
            'Meta': {'unique_together': "(('user', 'experiment'),)", 'object_name': 'Enrollment'},
            'alternative': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'enrollment_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['experiments.Experiment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_seen': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s.%s']" % (User._meta.app_label, User._meta.object_name), 'null': 'True'})
        },
        'experiments.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'alternatives': ('jsonfield.fields.JSONField', [], {'default': "'{}'", 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'primary_key': 'True'}),
            'relevant_chi2_goals': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'relevant_mwu_goals': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'switch_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['experiments']

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings

from jsonfield import JSONField

from gargoyle.manager import gargoyle
from gargoyle.models import Switch

import random
import json

from experiments import counters, conf
from experiments.dateutils import now

PARTICIPANT_KEY = '%s:%s:participant'
GOAL_KEY = '%s:%s:%s:goal'

CONTROL_STATE = 0
ENABLED_STATE = 1
GARGOYLE_STATE = 2
TRACK_STATE = 3

STATES = (
    (CONTROL_STATE, 'Control'),
    (ENABLED_STATE, 'Enabled'),
    (GARGOYLE_STATE, 'Gargoyle'),
    (TRACK_STATE, 'Track'),
)


class Experiment(models.Model):
    name = models.CharField(primary_key=True, max_length=128)
    description = models.TextField(default="", blank=True, null=True)
    alternatives = JSONField(default={}, blank=True)
    relevant_chi2_goals = models.TextField(default="", null=True, blank=True)
    relevant_mwu_goals = models.TextField(default="", null=True, blank=True)
    switch_key = models.CharField(default="", max_length=50, null=True, blank=True)

    state = models.IntegerField(default=CONTROL_STATE, choices=STATES)

    start_date = models.DateTimeField(default=now, blank=True, null=True, db_index=True)
    end_date = models.DateTimeField(blank=True, null=True)

    def is_displaying_alternatives(self):
        if self.state == CONTROL_STATE:
            return False
        elif self.state == ENABLED_STATE:
            return True
        elif self.state == GARGOYLE_STATE:
            return True
        elif self.state == TRACK_STATE:
            return True
        else:
            raise Exception("Invalid experiment state %s!" % self.state)

    def is_accepting_new_users(self, request):
        if self.state == CONTROL_STATE:
            return False
        elif self.state == ENABLED_STATE:
            return True
        elif self.state == GARGOYLE_STATE:
            return gargoyle.is_active(self.switch_key, request)
        elif self.state == TRACK_STATE:
            return False
        else:
            raise Exception("Invalid experiment state %s!" % self.state)

    def ensure_alternative_exists(self, alternative, weight=None):
        if alternative not in self.alternatives:
            self.alternatives[alternative] = {}
            self.alternatives[alternative]['enabled'] = True
            self.save()
        if weight is not None and 'weight' not in self.alternatives[alternative]:
            self.alternatives[alternative]['weight'] = float(weight)
            self.save()

    def random_alternative(self):
        if all('weight' in alt for alt in self.alternatives.values()):
            return weighted_choice([(name, details['weight']) for name, details in self.alternatives.items()])
        else:
            return random.choice(self.alternatives.keys())

    def increment_participant_count(self, alternative_name, participant_identifier):
        # Increment experiment_name:alternative:participant counter
        counter_key = PARTICIPANT_KEY % (self.name, alternative_name)
        counters.increment(counter_key, participant_identifier)

    def increment_goal_count(self, alternative_name, goal_name, participant_identifier, count=1):
        # Increment experiment_name:alternative:participant counter
        counter_key = GOAL_KEY % (self.name, alternative_name, goal_name)
        counters.increment(counter_key, participant_identifier, count)

    def remove_participant(self, alternative_name, participant_identifier):
        # Remove participation record
        counter_key = PARTICIPANT_KEY % (self.name, alternative_name)
        counters.clear(counter_key, participant_identifier)

        # Remove goal records
        for goal_name in conf.ALL_GOALS:
            counter_key = GOAL_KEY % (self.name, alternative_name, goal_name)
            counters.clear(counter_key, participant_identifier)

    def participant_count(self, alternative):
        return counters.get(PARTICIPANT_KEY % (self.name, alternative))

    def goal_count(self, alternative, goal):
        return counters.get(GOAL_KEY % (self.name, alternative, goal))

    def participant_goal_frequencies(self, alternative, participant_identifier):
        for goal in conf.ALL_GOALS:
            yield goal, counters.get_frequency(GOAL_KEY % (self.name, alternative, goal), participant_identifier)

    def goal_distribution(self, alternative, goal):
        return counters.get_frequencies(GOAL_KEY % (self.name, alternative, goal))

    def __unicode__(self):
        return self.name

    def to_dict(self):
        data = {
            'name': self.name,
            'edit_url': reverse('experiments:results', kwargs={'name': self.name}),
            'start_date': self.start_date,
            'end_date': self.end_date,
            'state': self.state,
            'switch_key': self.switch_key,
            'description': self.description,
            'relevant_chi2_goals': self.relevant_chi2_goals,
            'relevant_mwu_goals': self.relevant_mwu_goals,
        }
        return data

    def to_dict_serialized(self):
        return json.dumps(self.to_dict(), cls=DjangoJSONEncoder)

    def save(self, *args, **kwargs):
        # Create new switch
        if self.switch_key and conf.SWITCH_AUTO_CREATE:
            try:
                Switch.objects.get(key=self.switch_key)
            except Switch.DoesNotExist:
                Switch.objects.create(key=self.switch_key, label=conf.SWITCH_LABEL % self.name, description=self.description)

        if not self.switch_key and self.state == 2:
            self.state = 0

        super(Experiment, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete existing switch
        if conf.SWITCH_AUTO_DELETE:
            try:
                Switch.objects.get(key=Experiment.objects.get(name=self.name).switch_key).delete()
            except Switch.DoesNotExist:
                pass

        counters.reset_pattern(self.name + "*")

        super(Experiment, self).delete(*args, **kwargs)


class Enrollment(models.Model):
    """ A participant in a split testing experiment """
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null=True)
    experiment = models.ForeignKey(Experiment)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True)
    alternative = models.CharField(max_length=50)

    class Meta:
        unique_together = ('user', 'experiment')

    def __unicode__(self):
        return u'%s - %s' % (self.user, self.experiment)

    def to_dict(self):
        data = {
            'user': self.user,
            'experiment': self.experiment,
            'enrollment_date': self.enrollment_date,
            'alternative': self.alternative,
            'goals': self.goals,
        }
        return data


def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        upto += w
        if upto >= r:
            return c



########NEW FILE########
__FILENAME__ = nexus_modules
try:
    from django.conf.urls import patterns, url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, url

from functools import wraps

from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import ValidationError

from experiments.models import Experiment, ENABLED_STATE, GARGOYLE_STATE
from experiments.significance import chi_square_p_value, mann_whitney
from experiments.dateutils import now
from experiments.utils import participant
from experiments import conf

import nexus
import json

MIN_ACTIONS_TO_SHOW = 3


def rate(a, b):
    if not b or a == None:
        return None
    return 100. * a / b


def improvement(a, b):
    if not b or not a:
        return None
    return (a - b) * 100. / b


def chi_squared_confidence(a_count, a_conversion, b_count, b_conversion):
    contingency_table = [[a_count - a_conversion, a_conversion],
                         [b_count - b_conversion, b_conversion]]

    chi_square, p_value = chi_square_p_value(contingency_table)
    if p_value is not None:
        return (1 - p_value) * 100
    else:
        return None


def average_actions(distribution):
    total_users = 0
    total_actions = 0
    for actions, frequency in distribution.items():
        total_users += frequency
        total_actions += actions * frequency
    if total_users:
        return total_actions / float(total_users)
    else:
        return 0


def fixup_distribution(distribution, count):
    zeros = count - sum(distribution.values())
    distribution[0] = zeros + distribution.get(0, 0)
    return distribution


def mann_whitney_confidence(a_distribution, b_distribution):
    p_value = mann_whitney(a_distribution, b_distribution)[1]
    if p_value is not None:
        return (1 - p_value * 2) * 100  # Two tailed probability
    else:
        return None


def points_with_surrounding_gaps(points):
    """
    This function makes sure that any gaps in the sequence provided have stopper points at their beginning
    and end so a graph will be drawn with correct 0 ranges. This is more efficient than filling in all points
    up to the maximum value. For example:

    input: [1,2,3,10,11,13]
    output [1,2,3,4,9,10,11,12,13]
    """
    points_with_gaps = []
    last_point = -1
    for point in points:
        if last_point + 1 == point:
            pass
        elif last_point + 2 == point:
            points_with_gaps.append(last_point + 1)
        else:
            points_with_gaps.append(last_point + 1)
            points_with_gaps.append(point - 1)
        points_with_gaps.append(point)
        last_point = point
    return points_with_gaps


def conversion_distributions_to_graph_table(conversion_distributions):
    ordered_distributions = list(conversion_distributions.items())
    total_entries = dict((name, float(sum(dist.values()) or 1)) for name, dist in ordered_distributions)
    graph_head = [['x'] + [name for name, dist in ordered_distributions]]

    points_in_any_distribution = sorted(set(k for name, dist in ordered_distributions for k in dist.keys()))
    points_with_gaps = points_with_surrounding_gaps(points_in_any_distribution)
    graph_body = [[point] + [dist.get(point, 0) / total_entries[name] for name, dist in ordered_distributions] for point in points_with_gaps]

    accumulator = [0] * len(ordered_distributions)
    for point in range(len(graph_body) - 1, -1, -1):
        accumulator = [graph_body[point][j + 1] + accumulator[j] for j in range(len(ordered_distributions))]
        graph_body[point][1:] = accumulator

    interesting_points = [point for point in points_in_any_distribution if max(dist.get(point, 0) for name, dist in ordered_distributions) >= MIN_ACTIONS_TO_SHOW]
    if len(interesting_points):
        highest_interesting_point = max(interesting_points)
    else:
        highest_interesting_point = 0
    graph_body = [g for g in graph_body if g[0] <= highest_interesting_point and g[0] != 0]

    graph_table = graph_head + graph_body
    return json.dumps(graph_table)


class ExperimentException(Exception):
    pass


def json_result(func):
    "Decorator to make JSON views simpler"

    def wrapper(self, request, *args, **kwargs):
        try:
            response = {
                "success": True,
                "data": func(self, request, *args, **kwargs)
            }
        except ExperimentException, exc:
            response = {
                "success": False,
                "data": exc.message
            }
        except Experiment.DoesNotExist:
            response = {
                "success": False,
                "data": "Experiment cannot be found"
            }
        except ValidationError, e:
            response = {
                "success": False,
                "data": u','.join(map(unicode, e.messages)),
            }
        except Exception:
            if settings.DEBUG:
                import traceback
                traceback.print_exc()
            raise
        return HttpResponse(json.dumps(response), mimetype="application/json")
    wrapper = wraps(func)(wrapper)
    return wrapper


class ExperimentsModule(nexus.NexusModule):
    home_url = 'index'
    name = 'experiments'

    def get_title(self):
        return 'Experiments'

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^$', self.as_view(self.index), name='index'),
            url(r'^add/$', self.as_view(self.add), name='add'),
            url(r'^update/$', self.as_view(self.update), name='update'),
            url(r'^delete/$', self.as_view(self.delete), name='delete'),
            url(r'^state/$', self.as_view(self.state), name='state'),
            url(r'^set_alternative/$', self.as_view(self.set_alternative), name='set_alternative'),
            url(r'^results/(?P<name>[a-zA-Z0-9-_]+)/$', self.as_view(self.results), name='results'),
        )
        return urlpatterns

    def render_on_dashboard(self, request):
        enabled_experiments_count = Experiment.objects.filter(state__in=[ENABLED_STATE, GARGOYLE_STATE]).count()
        enabled_experiments = list(Experiment.objects.filter(state__in=[ENABLED_STATE, GARGOYLE_STATE]).order_by("start_date")[:5])
        return self.render_to_string('nexus/experiments/dashboard.html', {
            'enabled_experiments': enabled_experiments,
            'enabled_experiments_count': enabled_experiments_count,
        }, request)

    def index(self, request):
        sort_by = request.GET.get('by', '-start_date')
        experiments = Experiment.objects.all().order_by(sort_by)

        return self.render_to_response("nexus/experiments/index.html", {
            "experiments": [e.to_dict() for e in experiments],
            "all_goals": json.dumps(conf.ALL_GOALS),
            "sorted_by": sort_by,
        }, request)

    def results(self, request, name):
        experiment = Experiment.objects.get(name=name)

        try:
            chi2_goals = experiment.relevant_chi2_goals.replace(" ", "").split(",")
        except AttributeError:
            chi2_goals = [u'']
        try:
            mwu_goals = experiment.relevant_mwu_goals.replace(" ", "").split(",")
        except AttributeError:
            mwu_goals = [u'']
        relevant_goals = set(chi2_goals + mwu_goals)

        alternatives = {}
        for alternative_name in experiment.alternatives.keys():
            alternatives[alternative_name] = experiment.participant_count(alternative_name)
        alternatives = sorted(alternatives.items())

        control_participants = experiment.participant_count(conf.CONTROL_GROUP)

        results = {}

        for goal in conf.ALL_GOALS:
            show_mwu = goal in mwu_goals

            alternatives_conversions = {}
            control_conversions = experiment.goal_count(conf.CONTROL_GROUP, goal)
            control_conversion_rate = rate(control_conversions, control_participants)

            if show_mwu:
                mwu_histogram = {}
                control_conversion_distribution = fixup_distribution(experiment.goal_distribution(conf.CONTROL_GROUP, goal), control_participants)
                control_average_goal_actions = average_actions(control_conversion_distribution)
                mwu_histogram['control'] = control_conversion_distribution
            else:
                control_average_goal_actions = None
            for alternative_name in experiment.alternatives.keys():
                if not alternative_name == conf.CONTROL_GROUP:
                    alternative_conversions = experiment.goal_count(alternative_name, goal)
                    alternative_participants = experiment.participant_count(alternative_name)
                    alternative_conversion_rate = rate(alternative_conversions, alternative_participants)
                    alternative_confidence = chi_squared_confidence(alternative_participants, alternative_conversions, control_participants, control_conversions)
                    if show_mwu:
                        alternative_conversion_distribution = fixup_distribution(experiment.goal_distribution(alternative_name, goal), alternative_participants)
                        alternative_average_goal_actions = average_actions(alternative_conversion_distribution)
                        alternative_distribution_confidence = mann_whitney_confidence(alternative_conversion_distribution, control_conversion_distribution)
                        mwu_histogram[alternative_name] = alternative_conversion_distribution
                    else:
                        alternative_average_goal_actions = None
                        alternative_distribution_confidence = None
                    alternative = {
                        'conversions': alternative_conversions,
                        'conversion_rate': alternative_conversion_rate,
                        'improvement': improvement(alternative_conversion_rate, control_conversion_rate),
                        'confidence': alternative_confidence,
                        'average_goal_actions': alternative_average_goal_actions,
                        'mann_whitney_confidence': alternative_distribution_confidence,
                    }
                    alternatives_conversions[alternative_name] = alternative

            control = {
                'conversions': control_conversions,
                'conversion_rate': control_conversion_rate,
                'average_goal_actions': control_average_goal_actions,
            }

            results[goal] = {
                "control": control,
                "alternatives": sorted(alternatives_conversions.items()),
                "relevant": goal in relevant_goals or relevant_goals == set([u'']),
                "mwu": goal in mwu_goals,
                "mwu_histogram": conversion_distributions_to_graph_table(mwu_histogram) if show_mwu else None
            }

        return self.render_to_response("nexus/experiments/results.html", {
            'experiment': experiment.to_dict(),
            'alternatives': alternatives,
            'control_participants': control_participants,
            'results': results,
            'column_count': len(alternatives_conversions) * 3 + 2,  # Horrible coupling with template design
            'user_alternative': participant(request).get_alternative(experiment.name),
        }, request)

    @json_result
    def state(self, request):
        if not request.user.has_perm('experiments.change_experiment'):
            raise ExperimentException("You do not have permission to do that!")

        experiment = Experiment.objects.get(name=request.POST.get("name"))
        try:
            state = int(request.POST.get("state"))
        except ValueError:
            raise ExperimentException("State must be integer")

        experiment.state = state

        if state == 0:
            experiment.end_date = now()
        else:
            experiment.end_date = None

        experiment.save()

        response = {
            "success": True,
            "experiment": experiment.to_dict_serialized(),
        }

        return response

    @json_result
    def add(self, request):
        if not request.user.has_perm('experiments.add_experiment'):
            raise ExperimentException("You do not have permission to do that!")

        name = request.POST.get("name")

        if not name:
            raise ExperimentException("Name cannot be empty")

        if len(name) > 128:
            raise ExperimentException("Name must be less than or equal to 128 characters in length")

        experiment, created = Experiment.objects.get_or_create(
            name=name,
            defaults=dict(
                switch_key=request.POST.get("switch_key"),
                description=request.POST.get("desc"),
                relevant_chi2_goals=request.POST.get("chi2_goals"),
                relevant_mwu_goals=request.POST.get("mwu_goals"),
            ),
        )

        if not created:
            raise ExperimentException("Experiment with name %s already exists" % name)

        response = {
            'success': True,
            'experiment': experiment.to_dict_serialized(),
        }

        return response

    @json_result
    def update(self, request):
        if not request.user.has_perm('experiments.change_experiment'):
            raise ExperimentException("You do not have permission to do that!")

        experiment = Experiment.objects.get(name=request.POST.get("curname"))

        experiment.switch_key = request.POST.get("switch_key")
        experiment.description = request.POST.get("desc")
        experiment.relevant_chi2_goals = request.POST.get("chi2_goals")
        experiment.relevant_mwu_goals = request.POST.get("mwu_goals")
        experiment.save()

        response = {
            'success': True,
            'experiment': experiment.to_dict_serialized()
        }

        return response

#    @permission_required(u'experiments.delete_experiment')
    @json_result
    def delete(self, request):
        if not request.user.has_perm('experiments.delete_experiment'):
            raise ExperimentException("You don't have permission to do that!")
        experiment = Experiment.objects.get(name=request.POST.get("name"))

        experiment.enrollment_set.all().delete()
        experiment.delete()
        return {'successful': True}

    @json_result
    def set_alternative(self, request):
        experiment_name = request.POST.get("experiment")
        alternative_name = request.POST.get("alternative")
        participant(request).set_alternative(experiment_name, alternative_name)
        return {
            'success': True,
            'alternative': participant(request).get_alternative(experiment_name)
        }

nexus.site.register(ExperimentsModule, 'experiments')

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


user_enrolled = django.dispatch.Signal(providing_args=['experiment', 'alternative', 'user', 'session'])

########NEW FILE########
__FILENAME__ = signal_handlers
from experiments.utils import participant


def transfer_enrollments_to_user(sender, request, user, **kwargs):
    anon_user = participant(session=request.session)
    authenticated_user = participant(user=user)
    authenticated_user.incorporate(anon_user)

########NEW FILE########
__FILENAME__ = significance
from experiments.stats import zprob, chisqprob


def mann_whitney(a_distribution, b_distribution, use_continuity=True):
    """Returns (u, p_value)"""
    MINIMUM_VALUES = 20

    all_values = sorted(set(a_distribution.keys() + b_distribution.keys()))

    count_so_far = 0
    a_rank_sum = 0
    b_rank_sum = 0
    a_count = 0
    b_count = 0

    variance_adjustment = 0

    for v in all_values:
        a_for_value = a_distribution.get(v, 0)
        b_for_value = b_distribution.get(v, 0)
        total_for_value = a_for_value + b_for_value
        average_rank = count_so_far + (1 + total_for_value) / 2.0

        a_rank_sum += average_rank * a_for_value
        b_rank_sum += average_rank * b_for_value
        a_count += a_for_value
        b_count += b_for_value
        count_so_far += total_for_value

        variance_adjustment += total_for_value ** 3 - total_for_value

    if a_count < MINIMUM_VALUES or b_count < MINIMUM_VALUES:
        return 0, None

    a_u = a_rank_sum - a_count * (a_count + 1) / 2.0
    b_u = b_rank_sum - b_count * (b_count + 1) / 2.0

    small_u = min(a_u, b_u)
    big_u = max(a_u, b_u)

    # These need adjusting for the huge number of ties we will have
    total_count = float(a_count + b_count)
    u_distribution_mean = a_count * b_count / 2.0
    u_distribution_sd = (
        (a_count * b_count / (total_count * (total_count - 1))) ** 0.5 *
        ((total_count ** 3 - total_count - variance_adjustment) / 12.0) ** 0.5)

    if u_distribution_sd == 0:
        return small_u, None

    if use_continuity:
        # normal approximation for prob calc with continuity correction
        z_score = abs((big_u - 0.5 - u_distribution_mean) / u_distribution_sd)
    else:
        # normal approximation for prob calc
        z_score = abs((big_u - u_distribution_mean) / u_distribution_sd)

    return small_u, 1 - zprob(z_score)


def chi_square_p_value(matrix):
    """
    Accepts a matrix (an array of arrays, where each child array represents a row)
    
    Example from http://math.hws.edu/javamath/ryan/ChiSquare.html:
    
    Suppose you conducted a drug trial on a group of animals and you
    hypothesized that the animals receiving the drug would survive better than
    those that did not receive the drug. You conduct the study and collect the
    following data:
    
    Ho: The survival of the animals is independent of drug treatment.
    
    Ha: The survival of the animals is associated with drug treatment.
    
    In that case, your matrix should be:
    [
     [ Survivors in Test, Dead in Test ],
     [ Survivors in Control, Dead in Control ]
    ]
    
    Code adapted from http://codecomments.wordpress.com/2008/02/13/computing-chi-squared-p-value-from-contingency-table-in-python/
    """
    num_rows = len(matrix)
    num_columns = len(matrix[0])

    # Sanity checking
    if num_rows == 0:
        return None
    for row in matrix:
        if len(row) != num_columns:
            return None

    row_sums = []
    # for each row
    for row in matrix:
        # add up all the values in the row
        row_sums.append(sum(row))

    column_sums = []
    # for each column i
    for i in range(num_columns):
        column_sum = 0.0
        # get the i'th value from each row
        for row in matrix:
            column_sum += row[i]
        column_sums.append(column_sum)

    # the total sum could be calculated from either the rows or the columns
    # coerce to float to make subsequent division generate float results
    grand_total = float(sum(row_sums))

    if grand_total <= 0:
        return None, None

    observed_test_statistic = 0.0
    for i in range(num_rows):
        for j in range(num_columns):
            expected_value = (row_sums[i] / grand_total) * (column_sums[j] / grand_total) * grand_total
            if expected_value <= 0:
                return None, None
            observed_value = matrix[i][j]
            observed_test_statistic += ((observed_value - expected_value) ** 2) / expected_value
            # See https://bitbucket.org/akoha/django-lean/issue/16/g_test-formula-is-incorrect
            #observed_test_statistic += 2 * (observed_value*log(observed_value/expected_value))

    degrees_freedom = (num_columns - 1) * (num_rows - 1)

    p_value = chisqprob(observed_test_statistic, degrees_freedom)

    return observed_test_statistic, p_value

########NEW FILE########
__FILENAME__ = stats
from math import fabs, exp, sqrt, log, pi


def flatten(iterable):
    for el in iterable:
        if isinstance(el, (list, tuple)):
            for sub_el in flatten(el):
                yield sub_el
        else:
            yield el


def mean(scores):
    scores = list(flatten(scores))
    try:
        return float(sum(scores)) / float(len(scores))
    except ZeroDivisionError:
        return float('NaN')


def isnan(value):
    try:
        from math import isnan
        return isnan(value)
    except ImportError:
        return isinstance(value, float) and value != value


def ss(inlist):
    """
    Squares each value in the passed list, adds up these squares and
    returns the result.
    
    Originally written by Gary Strangman.

    Usage:   lss(inlist)
    """
    ss = 0
    for item in inlist:
        ss = ss + item * item
    return ss


def var(inlist):
    """
    Returns the variance of the values in the passed list using N-1
    for the denominator (i.e., for estimating population variance).
    
    Originally written by Gary Strangman.
    
    Usage:   lvar(inlist)
    """
    n = len(inlist)
    if n <= 1:
        return 0.0
    mn = mean(inlist)
    deviations = [0] * len(inlist)
    for i in range(len(inlist)):
        deviations[i] = inlist[i] - mn
    return ss(deviations) / float(n - 1)


def stdev(inlist):
    """
    Returns the standard deviation of the values in the passed list
    using N-1 in the denominator (i.e., to estimate population stdev).
    
    Originally written by Gary Strangman.
    
    Usage:   lstdev(inlist)
    """
    return sqrt(var(inlist))


def gammln(xx):
    """
    Returns the gamma function of xx.
        Gamma(z) = Integral(0,infinity) of t^(z-1)exp(-t) dt.
    (Adapted from: Numerical Recipies in C.)
    
    Originally written by Gary Strangman.
    
    Usage:   lgammln(xx)
    """
    coeff = [76.18009173, -86.50532033, 24.01409822, -1.231739516,
             0.120858003e-2, -0.536382e-5]
    x = xx - 1.0
    tmp = x + 5.5
    tmp = tmp - (x + 0.5) * log(tmp)
    ser = 1.0
    for j in range(len(coeff)):
        x = x + 1
        ser = ser + coeff[j] / x
    return -tmp + log(2.50662827465 * ser)


def betacf(a, b, x):
    """
    This function evaluates the continued fraction form of the incomplete
    Beta function, betai.  (Adapted from: Numerical Recipies in C.)
    
    Originally written by Gary Strangman.
    
    Usage:   lbetacf(a,b,x)
    """
    ITMAX = 200
    EPS = 3.0e-7

    bm = az = am = 1.0
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    bz = 1.0 - qab * x / qap
    for i in range(ITMAX + 1):
        em = float(i + 1)
        tem = em + em
        d = em * (b - em) * x / ((qam + tem) * (a + tem))
        ap = az + d * am
        bp = bz + d * bm
        d = -(a + em) * (qab + em) * x / ((qap + tem) * (a + tem))
        app = ap + d * az
        bpp = bp + d * bz
        aold = az
        am = ap / bpp
        bm = bp / bpp
        az = app / bpp
        bz = 1.0
        if (abs(az - aold) < (EPS * abs(az))):
            return az
    print 'a or b too big, or ITMAX too small in Betacf.'


def betai(a, b, x):
    """
    Returns the incomplete beta function:
    
        I-sub-x(a,b) = 1/B(a,b)*(Integral(0,x) of t^(a-1)(1-t)^(b-1) dt)
    
    where a,b>0 and B(a,b) = G(a)*G(b)/(G(a+b)) where G(a) is the gamma
    function of a.  The continued fraction formulation is implemented here,
    using the betacf function.  (Adapted from: Numerical Recipies in C.)
    
    Originally written by Gary Strangman.
    
    Usage:   lbetai(a,b,x)
    """
    if (x < 0.0 or x > 1.0):
        raise ValueError, 'Bad x in lbetai'
    if (x == 0.0 or x == 1.0):
        bt = 0.0
    else:
        bt = exp(gammln(a + b) - gammln(a) - gammln(b) + a * log(x) + b *
                      log(1.0 - x))
    if (x < (a + 1.0) / (a + b + 2.0)):
        return bt * betacf(a, b, x) / float(a)
    else:
        return 1.0 - bt * betacf(b, a, 1.0 - x) / float(b)


def ttest_ind(a, b):
    """
    Calculates the t-obtained T-test on TWO INDEPENDENT samples of
    scores a, and b. Returns t-value, and prob.
    
    Originally written by Gary Strangman.
    
    Usage:   lttest_ind(a,b)
    Returns: t-value, two-tailed prob
    """
    x1, x2 = mean(a), mean(b)
    v1, v2 = stdev(a) ** 2, stdev(b) ** 2
    n1, n2 = len(a), len(b)
    df = n1 + n2 - 2
    try:
        svar = ((n1 - 1) * v1 + (n2 - 1) * v2) / float(df)
    except ZeroDivisionError:
        return float('nan'), float('nan')
    try:
        t = (x1 - x2) / sqrt(svar * (1.0 / n1 + 1.0 / n2))
    except ZeroDivisionError:
        t = 1.0
    prob = betai(0.5 * df, 0.5, df / (df + t * t))
    return t, prob


def zprob(z):
    """
    Returns the area under the normal curve 'to the left of' the given z value.
    Thus, 
        for z<0, zprob(z) = 1-tail probability
        for z>0, 1.0-zprob(z) = 1-tail probability
        for any z, 2.0*(1.0-zprob(abs(z))) = 2-tail probability
    Originally adapted from Gary Perlman code by Gary Strangman.

    Usage:   zprob(z)
    """
    Z_MAX = 6.0    # maximum meaningful z-value
    if z == 0.0:
        x = 0.0
    else:
        y = 0.5 * fabs(z)
        if y >= (Z_MAX * 0.5):
            x = 1.0
        elif (y < 1.0):
            w = y * y
            x = ((((((((0.000124818987 * w
                        - 0.001075204047) * w + 0.005198775019) * w
                      - 0.019198292004) * w + 0.059054035642) * w
                    - 0.151968751364) * w + 0.319152932694) * w
                  - 0.531923007300) * w + 0.797884560593) * y * 2.0
        else:
            y = y - 2.0
            x = (((((((((((((-0.000045255659 * y
                             + 0.000152529290) * y - 0.000019538132) * y
                           - 0.000676904986) * y + 0.001390604284) * y
                         - 0.000794620820) * y - 0.002034254874) * y
                       + 0.006549791214) * y - 0.010557625006) * y
                     + 0.011630447319) * y - 0.009279453341) * y
                   + 0.005353579108) * y - 0.002141268741) * y
                 + 0.000535310849) * y + 0.999936657524
    if z > 0.0:
        prob = ((x + 1.0) * 0.5)
    else:
        prob = ((1.0 - x) * 0.5)
    return prob


def chisqprob(chisq, df):
    """
    Returns the (1-tailed) probability value associated with the provided
    chi-square value and df.  
    
    Originally adapted from Gary Perlman code by Gary Strangman.
    
    Usage:   chisqprob(chisq,df)
    """
    BIG = 20.0

    def ex(x):
        BIG = 20.0
        if x < -BIG:
            return 0.0
        else:
            return exp(x)

    if chisq <= 0 or df < 1:
        return 1.0

    a = 0.5 * chisq
    if df % 2 == 0:
        even = 1
    else:
        even = 0
    if df > 1:
        y = ex(-a)
    if even:
        s = y
    else:
        s = 2.0 * zprob(-sqrt(chisq))
    if (df > 2):
        chisq = 0.5 * (df - 1.0)
        if even:
            z = 1.0
        else:
            z = 0.5
        if a > BIG:
            if even:
                e = 0.0
            else:
                e = log(sqrt(pi))
            c = log(a)
            while (z <= chisq):
                e = log(z) + e
                s = s + ex(c * z - a - e)
                z = z + 1.0
            return s
        else:
            if even:
                e = 1.0
            else:
                e = 1.0 / sqrt(pi) / sqrt(a)
            c = 0.0
            while (z <= chisq):
                e = e * (a / float(z))
                c = c + e
                z = z + 1.0
            return (c * y + s)
    else:
        return s

########NEW FILE########
__FILENAME__ = experiments
from __future__ import absolute_import

from django import template
from django.core.urlresolvers import reverse

from experiments.utils import participant
from experiments.manager import experiment_manager
from uuid import uuid4

register = template.Library()


@register.inclusion_tag('experiments/goal.html')
def experiment_goal(goal_name):
    return {'url': reverse('experiment_goal', kwargs={'goal_name': goal_name, 'cache_buster': uuid4()})}


class ExperimentNode(template.Node):
    def __init__(self, node_list, experiment_name, alternative, user_variable):
        self.node_list = node_list
        self.experiment_name = experiment_name
        self.alternative = alternative
        self.user_variable = user_variable

    def render(self, context):
        # Get User object
        if self.user_variable:
            auth_user = self.user_variable.resolve(context)
            user = participant(user=auth_user)
            gargoyle_key = auth_user
        else:
            request = context.get('request', None)
            user = participant(request)
            gargoyle_key = request

        # Should we render?
        if user.is_enrolled(self.experiment_name, self.alternative, gargoyle_key):
            response = self.node_list.render(context)
        else:
            response = ""

        return response


def _parse_token_contents(token_contents):
    (_, experiment_name, alternative), remaining_tokens = token_contents[:3], token_contents[3:]
    weight = None
    user_variable = None

    for offset, token in enumerate(remaining_tokens):
        if '=' in token:
            name, expression = token.split('=', 1)
            if name == 'weight':
                weight = expression
            elif name == 'user':
                user_variable = template.Variable(expression)
            else:
                raise ValueError()
        elif offset == 0:
            # Backwards compatibility, weight as positional argument
            weight = token
        else:
            raise ValueError()

    return experiment_name, alternative, weight, user_variable


@register.tag('experiment')
def experiment(parser, token):
    """
    Split Testing experiment tag has the following syntax :
    
    {% experiment <experiment_name> <alternative>  %}
    experiment content goes here
    {% endexperiment %}
    
    If the alternative name is neither 'test' nor 'control' an exception is raised
    during rendering.
    """
    try:
        token_contents = token.split_contents()
        experiment_name, alternative, weight, user_variable = _parse_token_contents(token_contents)

        node_list = parser.parse(('endexperiment', ))
        parser.delete_first_token()
    except ValueError:
        raise template.TemplateSyntaxError("Syntax should be like :"
                "{% experiment experiment_name alternative [weight=val] [user=val] %}")

    experiment = experiment_manager.get(experiment_name, None)
    if experiment:
        experiment.ensure_alternative_exists(alternative, weight)

    return ExperimentNode(node_list, experiment_name, alternative, user_variable)


@register.simple_tag(takes_context=True)
def visit(context):
    request = context.get('request', None)
    participant(request).visit()
    return ""

########NEW FILE########
__FILENAME__ = experiment_helpers
"""
experiments.templatetags.experiments_helpers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from django import template

register = template.Library()


def raw(parser, token):
    # Whatever is between {% raw %} and {% endraw %} will be preserved as
    # raw, unrendered template code.
    text = []
    parse_until = 'endraw'
    tag_mapping = {
        template.TOKEN_TEXT: ('', ''),
        template.TOKEN_VAR: ('{{', '}}'),
        template.TOKEN_BLOCK: ('{%', '%}'),
        template.TOKEN_COMMENT: ('{#', '#}'),
    }
    # By the time this template tag is called, the template system has already
    # lexed the template into tokens. Here, we loop over the tokens until
    # {% endraw %} and parse them to TextNodes. We have to add the start and
    # end bits (e.g. "{{" for variables) because those have already been
    # stripped off in a previous part of the template-parsing process.
    while parser.tokens:
        token = parser.next_token()
        if token.token_type == template.TOKEN_BLOCK and token.contents == parse_until:
            return template.TextNode(u''.join(text))
        start, end = tag_mapping[token.token_type]
        text.append(u'%s%s%s' % (start, token.contents, end))
    parser.unclosed_block_tag(parse_until)
raw = register.tag(raw)


def sort_by_key(field, currently):
    is_negative = currently.find('-') is 0
    current_field = currently.lstrip('-')

    if current_field == field and is_negative:
        return field
    elif current_field == field:
        return '-' + field
    else:
        return field

sort_by_key = register.filter(sort_by_key)

########NEW FILE########
__FILENAME__ = counter
from __future__ import absolute_import

from django.utils.unittest import TestCase

from experiments import counters

TEST_KEY = 'CounterTestCase'


class CounterTestCase(TestCase):
    def setUp(self):
        counters.reset(TEST_KEY)
        self.assertEqual(counters.get(TEST_KEY), 0)

    def tearDown(self):
        counters.reset(TEST_KEY)

    def test_add_item(self):
        counters.increment(TEST_KEY, 'fred')
        self.assertEqual(counters.get(TEST_KEY), 1)

    def test_add_multiple_items(self):
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'barney')
        counters.increment(TEST_KEY, 'george')
        counters.increment(TEST_KEY, 'george')
        self.assertEqual(counters.get(TEST_KEY), 3)

    def test_add_duplicate_item(self):
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'fred')
        self.assertEqual(counters.get(TEST_KEY), 1)

    def test_get_frequencies(self):
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'barney')
        counters.increment(TEST_KEY, 'george')
        counters.increment(TEST_KEY, 'roger')
        counters.increment(TEST_KEY, 'roger')
        counters.increment(TEST_KEY, 'roger')
        counters.increment(TEST_KEY, 'roger')
        self.assertEqual(counters.get_frequencies(TEST_KEY), {1: 3, 4: 1})

    def test_delete_key(self):
        counters.increment(TEST_KEY, 'fred')
        counters.reset(TEST_KEY)
        self.assertEqual(counters.get(TEST_KEY), 0)

    def test_clear_value(self):
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'fred')
        counters.increment(TEST_KEY, 'barney')
        counters.increment(TEST_KEY, 'barney')
        counters.clear(TEST_KEY, 'fred')

        self.assertEqual(counters.get(TEST_KEY), 1)
        self.assertEqual(counters.get_frequencies(TEST_KEY), {2: 1})

########NEW FILE########
__FILENAME__ = mannwhitney
from django.utils.unittest import TestCase

from experiments.significance import mann_whitney


# The hardcoded p and u values in these tests were calculated using scipy
class MannWhitneyTestCase(TestCase):
    longMessage = True

    def test_empty_sets(self):
        mann_whitney(dict(), dict())

    def test_identical_ranges(self):
        distribution = dict((x, 1) for x in range(50))
        self.assertUandPCorrect(distribution, distribution, 1250.0, 0.49862467827855483)

    def test_many_repeated_values(self):
        self.assertUandPCorrect({0: 100, 1: 50}, {0: 110, 1: 60}, 12500.0, 0.35672951675909859)

    def test_large_range(self):
        distribution_a = dict((x, 1) for x in range(10000))
        distribution_b = dict((x + 1, 1) for x in range(10000))
        self.assertUandPCorrect(distribution_a, distribution_b, 49990000.5, 0.49023014794874586)

    def test_very_different_sizes(self):
        distribution_a = dict((x, 1) for x in range(10000))
        distribution_b = dict((x, 1) for x in range(20))
        self.assertUandPCorrect(distribution_a, distribution_b, 200.0, 0)

    def assertUandPCorrect(self, distribution_a, distribution_b, u, p):
        our_u, our_p = mann_whitney(distribution_a, distribution_b)
        self.assertEqual(our_u, u, "U score incorrect")
        self.assertAlmostEqual(our_p, p, msg="p value incorrect")

########NEW FILE########
__FILENAME__ = signals
from django.test import TestCase

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from experiments.models import Experiment, ENABLED_STATE
from experiments.signals import user_enrolled
from experiments.utils import participant

EXPERIMENT_NAME = 'backgroundcolor'


class WatchSignal(object):
    def __init__(self, signal):
        self.signal = signal
        self.called = False

    def __enter__(self):
        self.signal.connect(self.signal_handler)
        return self

    def __exit__(self, *args):
        self.signal.disconnect(self.signal_handler)

    def signal_handler(self, *args, **kwargs):
        self.called = True


class SignalsTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment.objects.create(name=EXPERIMENT_NAME, state=ENABLED_STATE)
        self.user = User.objects.create(username='brian')

    def test_sends_enroll_signal(self):
        with WatchSignal(user_enrolled) as signal:
            participant(user=self.user).enroll(EXPERIMENT_NAME, ['red', 'blue'])
            self.assertTrue(signal.called)

    def test_does_not_send_enroll_signal_again(self):
        participant(user=self.user).enroll(EXPERIMENT_NAME, ['red', 'blue'])
        with WatchSignal(user_enrolled) as signal:
            participant(user=self.user).enroll(EXPERIMENT_NAME, ['red', 'blue'])
            self.assertFalse(signal.called)

########NEW FILE########
__FILENAME__ = stats
from django.utils.unittest import TestCase

from experiments import stats


class StatsTestCase(TestCase):
    def test_flatten(self):
        self.assertEqual(
            list(stats.flatten([1, [2, [3]], 4, 5])),
            [1, 2, 3, 4, 5]
            )

########NEW FILE########
__FILENAME__ = templatetags
from django.test import TestCase

from experiments.templatetags.experiments import _parse_token_contents


class ExperimentTemplateTagTestCase(TestCase):
    """These test cases are rather nastily coupled, and are mainly intended to check the token parsing code"""

    def test_returns_with_standard_values(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(experiment_name, 'backgroundcolor')
        self.assertEqual(alternative, 'blue')

    def test_handles_old_style_weight(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue', '10')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(weight, '10')

    def test_handles_labelled_weight(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue', 'weight=10')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(weight, '10')

    def test_handles_user(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue', 'user=commenter')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(user_resolvable.var, 'commenter')

    def test_handles_user_and_weight(self):
        token_contents = ('experiment', 'backgroundcolor', 'blue', 'user=commenter', 'weight=10')
        experiment_name, alternative, weight, user_resolvable = _parse_token_contents(token_contents)
        self.assertEqual(user_resolvable.var, 'commenter')
        self.assertEqual(weight, '10')

    def test_raises_on_insufficient_arguments(self):
        token_contents = ('experiment', 'backgroundcolor')
        self.assertRaises(ValueError, lambda: _parse_token_contents(token_contents))

########NEW FILE########
__FILENAME__ = webuser
from __future__ import absolute_import

from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession

from experiments.models import Experiment, ENABLED_STATE
from experiments.conf import CONTROL_GROUP, VISIT_COUNT_GOAL
from experiments.utils import participant

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

request_factory = RequestFactory()

TEST_ALTERNATIVE = 'blue'
TEST_GOAL = 'buy'
EXPERIMENT_NAME = 'backgroundcolor'


class WebUserTests(object):
    def setUp(self):
        self.experiment = Experiment(name=EXPERIMENT_NAME, state=ENABLED_STATE)
        self.experiment.save()
        self.request = request_factory.get('/')
        self.request.session = DatabaseSession()

    def tearDown(self):
        self.experiment.delete()

    def confirm_human(self, experiment_user):
        pass

    def participants(self, alternative):
        return self.experiment.participant_count(alternative)

    def enrollment_initially_none(self, ):
        experiment_user = participant(self.request)
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), None)

    def test_user_enrolls(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), TEST_ALTERNATIVE)

    def test_record_goal_increments_counts(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 0)
        experiment_user.goal(TEST_GOAL)
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 1)

    def test_can_record_goal_multiple_times(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        experiment_user.goal(TEST_GOAL)
        experiment_user.goal(TEST_GOAL)
        experiment_user.goal(TEST_GOAL)
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 1)

    def test_counts_increment_immediately_once_confirmed_human(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)

        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(self.participants(TEST_ALTERNATIVE), 1, "Did not count participant after confirm human")

    def test_visit_increases_goal(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        experiment_user.visit()

        self.assertEqual(self.experiment.goal_distribution(TEST_ALTERNATIVE, VISIT_COUNT_GOAL), {1: 1})

    def test_visit_twice_increases_once(self):
        experiment_user = participant(self.request)
        self.confirm_human(experiment_user)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)

        experiment_user.visit()
        experiment_user.visit()

        self.assertEqual(self.experiment.goal_distribution(TEST_ALTERNATIVE, VISIT_COUNT_GOAL), {1: 1})


class WebUserAnonymousTestCase(WebUserTests, TestCase):
    def setUp(self):
        super(WebUserAnonymousTestCase, self).setUp()
        self.request.user = AnonymousUser()

    def confirm_human(self, experiment_user):
        experiment_user.confirm_human()

    def test_confirm_human_increments_counts(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        experiment_user.goal(TEST_GOAL)

        self.assertEqual(self.participants(TEST_ALTERNATIVE), 0, "Counted participant before confirmed human")
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 0, "Counted goal before confirmed human")
        experiment_user.confirm_human()
        self.assertEqual(self.participants(TEST_ALTERNATIVE), 1, "Did not count participant after confirm human")
        self.assertEqual(self.experiment.goal_count(TEST_ALTERNATIVE, TEST_GOAL), 1, "Did not count goal after confirm human")


class WebUserAuthenticatedTestCase(WebUserTests, TestCase):
    def setUp(self):
        super(WebUserAuthenticatedTestCase, self).setUp()
        self.request.user = User(username='brian')
        self.request.user.save()


class BotTestCase(TestCase):
    def setUp(self):
        self.experiment = Experiment(name='backgroundcolor', state=ENABLED_STATE)
        self.experiment.save()
        self.request = request_factory.get('/', HTTP_USER_AGENT='GoogleBot/2.1')

    def test_user_does_not_enroll(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(self.experiment.participant_count(TEST_ALTERNATIVE), 0, "Bot counted towards results")

    def test_bot_in_control_group(self):
        experiment_user = participant(self.request)
        experiment_user.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
        self.assertEqual(experiment_user.get_alternative(EXPERIMENT_NAME), 'control', "Bot enrolled in a group")
        self.assertEqual(experiment_user.is_enrolled(self.experiment.name, TEST_ALTERNATIVE, self.request), False, "Bot in test alternative")
        self.assertEqual(experiment_user.is_enrolled(self.experiment.name, CONTROL_GROUP, self.request), True, "Bot not in control group")

    def tearDown(self):
        self.experiment.delete()

########NEW FILE########
__FILENAME__ = webuser_incorporate
from django.test import TestCase
from django.utils.unittest import TestSuite
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession

from experiments.utils import DummyUser, SessionUser, AuthenticatedUser
from experiments.models import Experiment, ENABLED_STATE

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

TEST_ALTERNATIVE = 'blue'
EXPERIMENT_NAME = 'backgroundcolor'


class WebUserIncorporateTestCase(object):
    def test_can_incorporate(self):
        self.incorporating.incorporate(self.incorporated)

    def test_incorporates_enrollment_from_other(self):
        if not self._has_data():
            return

        try:
            experiment = Experiment.objects.create(name=EXPERIMENT_NAME, state=ENABLED_STATE)
            self.incorporated.set_alternative(EXPERIMENT_NAME, TEST_ALTERNATIVE)
            self.incorporating.incorporate(self.incorporated)
            self.assertEqual(self.incorporating.get_alternative(EXPERIMENT_NAME), TEST_ALTERNATIVE)
        finally:
            experiment.delete()

    def _has_data(self):
        return not isinstance(self.incorporated, DummyUser) and not isinstance(self.incorporating, DummyUser)


def dummy(incorporating):
    return DummyUser()


def anonymous(incorporating):
    return SessionUser(session=DatabaseSession())


def authenticated(incorporating):
    return AuthenticatedUser(user=User.objects.create(username=['incorporating_user', 'incorporated_user'][incorporating]))

user_factories = (dummy, anonymous, authenticated)


def load_tests(loader, standard_tests, _):
    suite = TestSuite()
    suite.addTests(standard_tests)

    for incorporating in user_factories:
        for incorporated in user_factories:
            test_case = build_test_case(incorporating, incorporated)
            tests = loader.loadTestsFromTestCase(test_case)
            suite.addTests(tests)
    return suite


def build_test_case(incorporating, incorporated):
    class InstantiatedTestCase(WebUserIncorporateTestCase, TestCase):

        def setUp(self):
            super(InstantiatedTestCase, self).setUp()
            self.incorporating = incorporating(True)
            self.incorporated = incorporated(False)
    InstantiatedTestCase.__name__ = "WebUserIncorporateTestCase_into_%s_from_%s" % (incorporating.__name__, incorporated.__name__)
    return InstantiatedTestCase

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('experiments.views',
    url(r'^goal/(?P<goal_name>[^/]+)/(?P<cache_buster>[^/]+)?$', 'record_experiment_goal', name="experiment_goal"),
    url(r'^confirm_human/$', 'confirm_human', name="experiment_confirm_human"),
    url(r'^change_alternative/(?P<experiment_name>[a-zA-Z0-9-_]+)/(?P<alternative_name>[a-zA-Z0-9-_]+)/$', 'change_alternative', name="experiment_change_alternative"),
)

########NEW FILE########
__FILENAME__ = utils
from django.db import IntegrityError
from django.contrib.sessions.backends.base import SessionBase

from experiments.models import Enrollment
from experiments.manager import experiment_manager
from experiments.dateutils import now, fix_awareness, datetime_from_timestamp, timestamp_from_datetime
from experiments.signals import user_enrolled
from experiments import conf

from collections import namedtuple

import re
import warnings
import collections
import numbers
from datetime import timedelta


def record_goal(request, goal_name):
    _record_goal(goal_name, request)


def _record_goal(goal_name, request=None, session=None, user=None):
    warnings.warn('record_goal is deprecated. Please use participant().goal() instead.', DeprecationWarning)
    experiment_user = participant(request, session, user)
    experiment_user.goal(goal_name)


def participant(request=None, session=None, user=None):
    if request and hasattr(request, '_experiments_user'):
        return request._experiments_user
    else:
        result = _get_participant(request, session, user)
        if request:
            request._experiments_user = result
        return result


def _get_participant(request, session, user):
    if request and hasattr(request, 'user') and not user:
        user = request.user
    if request and hasattr(request, 'session') and not session:
        session = request.session

    if request and conf.BOT_REGEX.search(request.META.get("HTTP_USER_AGENT", "")):
        return DummyUser()
    elif user and user.is_authenticated():
        return AuthenticatedUser(user, request)
    elif session:
        return SessionUser(session, request)
    else:
        return DummyUser()

EnrollmentData = namedtuple('EnrollmentData', ['experiment', 'alternative', 'enrollment_date', 'last_seen'])


class WebUser(object):
    """Represents a user (either authenticated or session based) which can take part in experiments"""

    def enroll(self, experiment_name, alternatives):
        """Enroll this user in the experiment if they are not already part of it. Returns the selected alternative"""
        chosen_alternative = conf.CONTROL_GROUP

        experiment = experiment_manager.get(experiment_name, None)
        if experiment and experiment.is_displaying_alternatives():
            if isinstance(alternatives, collections.Mapping):
                if conf.CONTROL_GROUP not in alternatives:
                    experiment.ensure_alternative_exists(conf.CONTROL_GROUP, 1)
                for alternative, weight in alternatives.items():
                    experiment.ensure_alternative_exists(alternative, weight)
            else:
                alternatives_including_control = alternatives + [conf.CONTROL_GROUP]
                for alternative in alternatives_including_control:
                    experiment.ensure_alternative_exists(alternative)

            assigned_alternative = self._get_enrollment(experiment)
            if assigned_alternative:
                chosen_alternative = assigned_alternative
            elif experiment.is_accepting_new_users(self._gargoyle_key()):
                chosen_alternative = experiment.random_alternative()
                self._set_enrollment(experiment, chosen_alternative)

        return chosen_alternative

    def get_alternative(self, experiment_name):
        """Get the alternative this user is enrolled in. If not enrolled in the experiment returns 'control'"""
        experiment = experiment_manager.get(experiment_name, None)
        if experiment and experiment.is_displaying_alternatives():
            alternative = self._get_enrollment(experiment)
            if alternative is not None:
                return alternative
        return 'control'

    def set_alternative(self, experiment_name, alternative):
        """Explicitly set the alternative the user is enrolled in for the specified experiment.

        This allows you to change a user between alternatives. The user and goal counts for the new
        alternative will be increment, but those for the old one will not be decremented. The user will
        be enrolled in the experiment even if the experiment would not normally accept this user."""
        experiment = experiment_manager.get(experiment_name, None)
        if experiment:
            self._set_enrollment(experiment, alternative)

    def goal(self, goal_name, count=1):
        """Record that this user has performed a particular goal

        This will update the goal stats for all experiments the user is enrolled in."""
        for enrollment in self._get_all_enrollments():
            if enrollment.experiment.is_displaying_alternatives():
                self._experiment_goal(enrollment.experiment, enrollment.alternative, goal_name, count)

    def confirm_human(self):
        """Mark that this is a real human being (not a bot) and thus results should be counted"""
        pass

    def incorporate(self, other_user):
        """Incorporate all enrollments and goals performed by the other user

        If this user is not enrolled in a given experiment, the results for the
        other user are incorporated. For experiments this user is already
        enrolled in the results of the other user are discarded.

        This takes a relatively large amount of time for each experiment the other
        user is enrolled in."""
        for enrollment in other_user._get_all_enrollments():
            if not self._get_enrollment(enrollment.experiment):
                self._set_enrollment(enrollment.experiment, enrollment.alternative, enrollment.enrollment_date, enrollment.last_seen)
                goals = enrollment.experiment.participant_goal_frequencies(enrollment.alternative, other_user._participant_identifier())
                for goal_name, count in goals:
                    enrollment.experiment.increment_goal_count(enrollment.alternative, goal_name, self._participant_identifier(), count)
            other_user._cancel_enrollment(enrollment.experiment)

    def visit(self):
        """Record that the user has visited the site for the purposes of retention tracking"""
        for enrollment in self._get_all_enrollments():
            if enrollment.experiment.is_displaying_alternatives():
                if not enrollment.last_seen or now() - enrollment.last_seen >= timedelta(1):
                    self._experiment_goal(enrollment.experiment, enrollment.alternative, conf.VISIT_COUNT_GOAL, 1)
                    self._set_last_seen(enrollment.experiment, now())

    def _get_enrollment(self, experiment):
        """Get the name of the alternative this user is enrolled in for the specified experiment
        
        `experiment` is an instance of Experiment. If the user is not currently enrolled returns None."""
        raise NotImplementedError

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        """Explicitly set the alternative the user is enrolled in for the specified experiment.

        This allows you to change a user between alternatives. The user and goal counts for the new
        alternative will be increment, but those for the old one will not be decremented."""
        raise NotImplementedError

    def is_enrolled(self, experiment_name, alternative, request):
        """Enroll this user in the experiment if they are not already part of it. Returns the selected alternative"""
        """Test if the user is enrolled in the supplied alternative for the given experiment.

        The supplied alternative will be added to the list of possible alternatives for the
        experiment if it is not already there. If the user is not yet enrolled in the supplied
        experiment they will be enrolled, and an alternative chosen at random."""
        chosen_alternative = self.enroll(experiment_name, [alternative])
        return alternative == chosen_alternative

    def _participant_identifier(self):
        "Unique identifier for this user in the counter store"
        raise NotImplementedError

    def _get_all_enrollments(self):
        "Return experiment, alternative tuples for all experiments the user is enrolled in"
        raise NotImplementedError

    def _cancel_enrollment(self, experiment):
        "Remove the enrollment and any goals the user has against this experiment"
        raise NotImplementedError

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        "Record a goal against a particular experiment and alternative"
        raise NotImplementedError

    def _set_last_seen(self, experiment, last_seen):
        "Set the last time the user was seen associated with this experiment"
        raise NotImplementedError

    def _gargoyle_key(self):
        return None


class DummyUser(WebUser):
    def _get_enrollment(self, experiment):
        return None

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        user_enrolled.send(
            self,
            experiment=experiment.name, alternative=alternative,
            user=None, session=None)
        pass

    def is_enrolled(self, experiment_name, alternative, request):
        return alternative == conf.CONTROL_GROUP

    def incorporate(self, other_user):
        for enrollment in other_user._get_all_enrollments():
            other_user._cancel_enrollment(enrollment.experiment)

    def _participant_identifier(self):
        return ""

    def _get_all_enrollments(self):
        return []

    def _is_enrolled_in_experiment(self, experiment):
        return False

    def _cancel_enrollment(self, experiment):
        pass

    def _get_goal_counts(self, experiment, alternative):
        return {}

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        pass

    def _set_last_seen(self, experiment, last_seen):
        pass


class AuthenticatedUser(WebUser):
    def __init__(self, user, request=None):
        self._enrollment_cache = {}
        self.user = user
        self.request = request
        super(AuthenticatedUser, self).__init__()

    def _get_enrollment(self, experiment):
        if experiment.name not in self._enrollment_cache:
            try:
                self._enrollment_cache[experiment.name] = Enrollment.objects.get(user=self.user, experiment=experiment).alternative
            except Enrollment.DoesNotExist:
                self._enrollment_cache[experiment.name] = None
        return self._enrollment_cache[experiment.name]

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        if experiment.name in self._enrollment_cache:
            del self._enrollment_cache[experiment.name]

        try:
            enrollment, _ = Enrollment.objects.get_or_create(user=self.user, experiment=experiment, defaults={'alternative': alternative})
        except IntegrityError, exc:
            # Already registered (db race condition under high load)
            return
        # Update alternative if it doesn't match
        enrollment_changed = False
        if enrollment.alternative != alternative:
            enrollment.alternative = alternative
            enrollment_changed = True
        if enrollment_date:
            enrollment.enrollment_date = enrollment_date
            enrollment_changed = True
        if last_seen:
            enrollment.last_seen = last_seen
            enrollment_changed = True

        if enrollment_changed:
            enrollment.save()

        experiment.increment_participant_count(alternative, self._participant_identifier())

        user_enrolled.send(
            self,
            experiment=experiment.name, alternative=alternative,
            user=self.user, session=None)

    def _participant_identifier(self):
        return 'user:%d' % (self.user.pk, )

    def _get_all_enrollments(self):
        enrollments = Enrollment.objects.filter(user=self.user).select_related("experiment")
        if enrollments:
            for enrollment in enrollments:
                yield EnrollmentData(enrollment.experiment, enrollment.alternative, enrollment.enrollment_date, enrollment.last_seen)

    def _cancel_enrollment(self, experiment):
        try:
            enrollment = Enrollment.objects.get(user=self.user, experiment=experiment)
        except Enrollment.DoesNotExist:
            pass
        else:
            experiment.remove_participant(enrollment.alternative, self._participant_identifier())
            enrollment.delete()

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)

    def _set_last_seen(self, experiment, last_seen):
        Enrollment.objects.filter(user=self.user, experiment=experiment).update(last_seen=last_seen)

    def _gargoyle_key(self):
        return self.request or self.user


def _session_enrollment_latest_version(data):
    try:
        alternative, unused, enrollment_date, last_seen = data
        if isinstance(enrollment_date, numbers.Number):
            enrollment_date = datetime_from_timestamp(enrollment_date)
        if isinstance(last_seen, numbers.Number):
            last_seen = datetime_from_timestamp(last_seen)
        if last_seen:
            last_seen = fix_awareness(last_seen)
    except ValueError:  # Data from previous version
        alternative, unused = data
        enrollment_date = None
        last_seen = None
    return alternative, unused, enrollment_date, last_seen


class SessionUser(WebUser):
    def __init__(self, session, request=None):
        self.session = session
        self.request = request
        super(SessionUser, self).__init__()

    def _get_enrollment(self, experiment):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments and experiment.name in enrollments:
            alternative, _, _, _ = _session_enrollment_latest_version(enrollments[experiment.name])
            return alternative
        return None

    def _set_enrollment(self, experiment, alternative, enrollment_date=None, last_seen=None):
        enrollments = self.session.get('experiments_enrollments', {})
        enrollments[experiment.name] = (alternative, None, timestamp_from_datetime(enrollment_date or now()), timestamp_from_datetime(last_seen))
        self.session['experiments_enrollments'] = enrollments
        if self._is_verified_human():
            experiment.increment_participant_count(alternative, self._participant_identifier())
        user_enrolled.send(
            self,
            experiment=experiment.name, alternative=alternative,
            user=None, session=self.session)

    def confirm_human(self):
        if self.session.get('experiments_verified_human', False):
            return

        self.session['experiments_verified_human'] = True

        # Replay enrollments
        for enrollment in self._get_all_enrollments():
            enrollment.experiment.increment_participant_count(enrollment.alternative, self._participant_identifier())

        # Replay goals
        if 'experiments_goals' in self.session:
            try:
                for experiment_name, alternative, goal_name, count in self.session['experiments_goals']:
                    experiment = experiment_manager.get(experiment_name, None)
                    if experiment:
                        experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)
            except ValueError:
                pass  # Values from older version
            finally:
                del self.session['experiments_goals']

    def _participant_identifier(self):
        if 'experiments_session_key' not in self.session:
            if not self.session.session_key:
                self.session.save()  # Force session key
            self.session['experiments_session_key'] = self.session.session_key
        return 'session:%s' % (self.session['experiments_session_key'], )

    def _is_verified_human(self):
        if conf.VERIFY_HUMAN:
            return self.session.get('experiments_verified_human', False)
        else:
            return True

    def _get_all_enrollments(self):
        enrollments = self.session.get('experiments_enrollments', None)
        if enrollments:
            for experiment_name, data in enrollments.items():
                alternative, _, enrollment_date, last_seen = _session_enrollment_latest_version(data)
                experiment = experiment_manager.get(experiment_name, None)
                if experiment:
                    yield EnrollmentData(experiment, alternative, enrollment_date, last_seen)

    def _cancel_enrollment(self, experiment):
        alternative = self._get_enrollment(experiment)
        if alternative:
            experiment.remove_participant(alternative, self._participant_identifier())
            enrollments = self.session.get('experiments_enrollments', None)
            del enrollments[experiment.name]

    def _experiment_goal(self, experiment, alternative, goal_name, count):
        if self._is_verified_human():
            experiment.increment_goal_count(alternative, goal_name, self._participant_identifier(), count)
        else:
            goals = self.session.get('experiments_goals', [])
            goals.append((experiment.name, alternative, goal_name, count))
            self.session['experiments_goals'] = goals

    def _set_last_seen(self, experiment, last_seen):
        enrollments = self.session.get('experiments_enrollments', {})
        alternative, unused, enrollment_date, _ = _session_enrollment_latest_version(enrollments[experiment.name])
        enrollments[experiment.name] = (alternative, unused, timestamp_from_datetime(enrollment_date), timestamp_from_datetime(last_seen))
        self.session['experiments_enrollments'] = enrollments

    def _gargoyle_key(self):
        return self.request

__all__ = ['participant', 'record_goal']

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from experiments.utils import participant, record_goal
from experiments import record_goal
from experiments.models import Experiment

TRANSPARENT_1X1_PNG = \
("\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52"
 "\x00\x00\x00\x01\x00\x00\x00\x01\x08\x03\x00\x00\x00\x28\xcb\x34"
 "\xbb\x00\x00\x00\x19\x74\x45\x58\x74\x53\x6f\x66\x74\x77\x61\x72"
 "\x65\x00\x41\x64\x6f\x62\x65\x20\x49\x6d\x61\x67\x65\x52\x65\x61"
 "\x64\x79\x71\xc9\x65\x3c\x00\x00\x00\x06\x50\x4c\x54\x45\x00\x00"
 "\x00\x00\x00\x00\xa5\x67\xb9\xcf\x00\x00\x00\x01\x74\x52\x4e\x53"
 "\x00\x40\xe6\xd8\x66\x00\x00\x00\x0c\x49\x44\x41\x54\x78\xda\x62"
 "\x60\x00\x08\x30\x00\x00\x02\x00\x01\x4f\x6d\x59\xe1\x00\x00\x00"
 "\x00\x49\x45\x4e\x44\xae\x42\x60\x82\x00")


@never_cache
@require_POST
def confirm_human(request):
    experiment_user = participant(request)
    experiment_user.confirm_human()
    return HttpResponse(status=204)


@never_cache
def record_experiment_goal(request, goal_name, cache_buster=None):
    record_goal(goal_name, request)
    return HttpResponse(TRANSPARENT_1X1_PNG, mimetype="image/png")


def change_alternative(request, experiment_name, alternative_name):
    experiment = get_object_or_404(Experiment, name=experiment_name)
    if alternative_name not in experiment.alternatives.keys():
        return HttpResponseBadRequest()

    participant(request).set_alternative(experiment_name, alternative_name)
    return HttpResponse('OK')

########NEW FILE########
__FILENAME__ = testrunner
import os
import sys

from django.conf import settings


def runtests():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, test_dir)

    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=('django.contrib.auth',
                        'django.contrib.contenttypes',
                        'django.contrib.sessions',
                        'django.contrib.admin',
                        'gargoyle',
                        'experiments',),
        ROOT_URLCONF='experiments.urls',
    )

    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, failfast=False)
    failures = test_runner.run_tests(['experiments.tests', ])
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()

########NEW FILE########
