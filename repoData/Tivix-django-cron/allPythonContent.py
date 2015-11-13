__FILENAME__ = admin
from django.contrib import admin

from django_cron.models import CronJobLog


class CronJobLogAdmin(admin.ModelAdmin):
    class Meta:
        model = CronJobLog

    search_fields = ('code', 'message')
    ordering = ('-start_time',)
    list_display = ('code', 'start_time', 'end_time', 'is_success')
    list_filter = ('code', 'start_time', 'is_success')

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser and obj is not None:
            names = [f.name for f in CronJobLog._meta.fields if f.name != 'id']
            return self.readonly_fields + tuple(names)
        return self.readonly_fields


admin.site.register(CronJobLog, CronJobLogAdmin)

########NEW FILE########
__FILENAME__ = cron
from django.conf import settings
from django_cron import CronJobBase, Schedule
from django_cron.models import CronJobLog
from django_cron.management.commands.runcrons import get_class

from django_common.helper import send_mail


class FailedRunsNotificationCronJob(CronJobBase):
    """
        Send email if cron failed to run X times in a row
    """
    RUN_EVERY_MINS = 30

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'django_cron.FailedRunsNotificationCronJob'

    def do(self):

        CRONS_TO_CHECK = map(lambda x: get_class(x), settings.CRON_CLASSES)
        EMAILS = [admin[1] for admin in settings.ADMINS]

        try:
            FAILED_RUNS_CRONJOB_EMAIL_PREFIX = settings.FAILED_RUNS_CRONJOB_EMAIL_PREFIX
        except:
            FAILED_RUNS_CRONJOB_EMAIL_PREFIX = ''

        for cron in CRONS_TO_CHECK:

            try:
                min_failures = cron.MIN_NUM_FAILURES
            except AttributeError:
                min_failures = 10

            failures = 0

            jobs = CronJobLog.objects.filter(code=cron.code).order_by('-end_time')[:min_failures]

            message = ''

            for job in jobs:
                if not job.is_success:
                    failures += 1
                    message += 'Job ran at %s : \n\n %s \n\n' % (job.start_time, job.message)

            if failures == min_failures:

                send_mail(
                    '%s%s failed %s times in a row!' % (FAILED_RUNS_CRONJOB_EMAIL_PREFIX, cron.code, \
                        min_failures), message,
                    settings.DEFAULT_FROM_EMAIL, EMAILS
                )

########NEW FILE########
__FILENAME__ = runcrons
import sys
from datetime import datetime
from optparse import make_option
import traceback

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache
from django_cron import CronJobManager
try:
    from django.utils import timezone
except ImportError:
    # timezone added in Django 1.4
    from django_cron import timezone
from django.db import close_connection


DEFAULT_LOCK_TIME = 24 * 60 * 60  # 24 hours


def get_class(kls):
    """
    TODO: move to django-common app.
    Converts a string to a class.
    Courtesy: http://stackoverflow.com/questions/452969/does-python-have-an-equivalent-to-java-class-forname/452981#452981
    """
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__(module)
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--force', action='store_true', help='Force cron runs'),
        make_option('--silent', action='store_true', help='Do not push any message on console'),
    )

    def handle(self, *args, **options):
        """
        Iterates over all the CRON_CLASSES (or if passed in as a commandline argument)
        and runs them.
        """
        if args:
            cron_class_names = args
        else:
            cron_class_names = getattr(settings, 'CRON_CLASSES', [])

        try:
            crons_to_run = map(lambda x: get_class(x), cron_class_names)
        except:
            error = traceback.format_exc()
            print('Make sure these are valid cron class names: %s\n%s' % (cron_class_names, error))
            sys.exit()

        for cron_class in crons_to_run:
            run_cron_with_cache_check(cron_class, force=options['force'],
                silent=options['silent'])
        close_connection()


def run_cron_with_cache_check(cron_class, force=False, silent=False):
    """
    Checks the cache and runs the cron or not.

    @cron_class - cron class to run.
    """
    if not cache.get(cron_class.__name__) or getattr(cron_class, 'ALLOW_PARALLEL_RUNS', False):
        timeout = DEFAULT_LOCK_TIME
        try:
            timeout = cron_class.DJANGO_CRON_LOCK_TIME if getattr(cron_class, 'DJANGO_CRON_LOCK_TIME', False) else settings.DJANGO_CRON_LOCK_TIME
        except:
            pass
        cache.set(cron_class.__name__, timezone.now(), timeout)
        instance = cron_class()
        CronJobManager.run(instance, force, silent)
        cache.delete(cron_class.__name__)
    else:
        if not silent:
            print("%s failed: lock has been found. Other cron started at %s" % \
                  (cron_class.__name__, cache.get(cron_class.__name__)))

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'CronJobLog'
        db.create_table('django_cron_cronjoblog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=64, db_index=True)),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('end_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('is_success', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('message', self.gf('django.db.models.fields.TextField')(max_length=1000, blank=True)),
        ))
        db.send_create_signal('django_cron', ['CronJobLog'])


    def backwards(self, orm):
        
        # Deleting model 'CronJobLog'
        db.delete_table('django_cron_cronjoblog')


    models = {
        'django_cron.cronjoblog': {
            'Meta': {'object_name': 'CronJobLog'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['django_cron']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_cronjoblog_ran_at_time
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'CronJobLog.ran_at_time'
        db.add_column('django_cron_cronjoblog', 'ran_at_time', self.gf('django.db.models.fields.TimeField')(db_index=True, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'CronJobLog.ran_at_time'
        db.delete_column('django_cron_cronjoblog', 'ran_at_time')


    models = {
        'django_cron.cronjoblog': {
            'Meta': {'object_name': 'CronJobLog'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'blank': 'True'}),
            'ran_at_time': ('django.db.models.fields.TimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['django_cron']

########NEW FILE########
__FILENAME__ = 0003_auto__add_index_cronjoblog_end_time__add_index_cronjoblog_ran_at_time_
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'CronJobLog', fields ['end_time']
        db.create_index(u'django_cron_cronjoblog', ['end_time'])

        # Adding index on 'CronJobLog', fields ['ran_at_time', 'is_success', 'code']
        db.create_index(u'django_cron_cronjoblog', ['ran_at_time', 'is_success', 'code'])

        # Adding index on 'CronJobLog', fields ['ran_at_time', 'start_time', 'code']
        db.create_index(u'django_cron_cronjoblog', ['ran_at_time', 'start_time', 'code'])

        # Adding index on 'CronJobLog', fields ['start_time', 'code']
        db.create_index(u'django_cron_cronjoblog', ['start_time', 'code'])


    def backwards(self, orm):
        # Removing index on 'CronJobLog', fields ['start_time', 'code']
        db.delete_index(u'django_cron_cronjoblog', ['start_time', 'code'])

        # Removing index on 'CronJobLog', fields ['ran_at_time', 'start_time', 'code']
        db.delete_index(u'django_cron_cronjoblog', ['ran_at_time', 'start_time', 'code'])

        # Removing index on 'CronJobLog', fields ['ran_at_time', 'is_success', 'code']
        db.delete_index(u'django_cron_cronjoblog', ['ran_at_time', 'is_success', 'code'])

        # Removing index on 'CronJobLog', fields ['end_time']
        db.delete_index(u'django_cron_cronjoblog', ['end_time'])


    models = {
        u'django_cron.cronjoblog': {
            'Meta': {'object_name': 'CronJobLog', 'index_together': "[('code', 'is_success', 'ran_at_time'), ('code', 'start_time', 'ran_at_time'), ('code', 'start_time')]"},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'blank': 'True'}),
            'ran_at_time': ('django.db.models.fields.TimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['django_cron']
########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models


class CronJobLog(models.Model):
    """
    Keeps track of the cron jobs that ran etc. and any error messages if they failed.
    """
    code = models.CharField(max_length=64, db_index=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    is_success = models.BooleanField(default=False)
    message = models.TextField(max_length=1000, blank=True)  # TODO: db_index=True

    """
    This field is used to mark jobs executed in exact time.
    Jobs that run every X minutes, have this field empty.
    """
    ran_at_time = models.TimeField(null=True, blank=True, db_index=True, editable=False)

    def __unicode__(self):
        return '%s (%s)' % (self.code, 'Success' if self.is_success else 'Fail')

    class Meta:
        index_together = [
            ('code', 'is_success', 'ran_at_time'),
            ('code', 'start_time', 'ran_at_time'),
            ('code', 'start_time')  # useful when finding latest run (order by start_time) of cron
        ]

########NEW FILE########
__FILENAME__ = tests
from django.utils import unittest


class SimpleTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_example(self):
        """Some test example"""
        pass

########NEW FILE########
__FILENAME__ = test_settings
import django

if django.VERSION[:2] >= (1, 3):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASE_ENGINE = 'sqlite3'

INSTALLED_APPS = [
    'django_cron',
]

SECRET_KEY = "wknfgl34qtnjo&Yk3jqfjtn2k3jtnk4wtnk"
########NEW FILE########
__FILENAME__ = timezone
"""Timezone helper functions.

This module uses pytz when it's available and fallbacks when it isn't.
"""

from datetime import datetime, timedelta, tzinfo
from threading import local
import time as _time

try:
    import pytz
except ImportError:
    pytz = None

from django.conf import settings

__all__ = [
    'utc', 'get_default_timezone', 'get_current_timezone',
    'activate', 'deactivate', 'override',
    'is_naive', 'is_aware', 'make_aware', 'make_naive',
]

settings.USE_TZ = False

# UTC and local time zones

ZERO = timedelta(0)

class UTC(tzinfo):
    """
    UTC implementation taken from Python's docs.

    Used only when pytz isn't available.
    """

    def __repr__(self):
        return "<UTC>"

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

class LocalTimezone(tzinfo):
    """
    Local time implementation taken from Python's docs.

    Used only when pytz isn't available, and most likely inaccurate. If you're
    having trouble with this class, don't waste your time, just install pytz.
    """

    def __init__(self):
        # This code is moved in __init__ to execute it as late as possible
        # See get_default_timezone().
        self.STDOFFSET = timedelta(seconds=-_time.timezone)
        if _time.daylight:
            self.DSTOFFSET = timedelta(seconds=-_time.altzone)
        else:
            self.DSTOFFSET = self.STDOFFSET
        self.DSTDIFF = self.DSTOFFSET - self.STDOFFSET
        tzinfo.__init__(self)

    def __repr__(self):
        return "<LocalTimezone>"

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self.DSTOFFSET
        else:
            return self.STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return self.DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0


utc = pytz.utc if pytz else UTC()
"""UTC time zone as a tzinfo instance."""

# In order to avoid accessing the settings at compile time,
# wrap the expression in a function and cache the result.
_localtime = None

def get_default_timezone():
    """
    Returns the default time zone as a tzinfo instance.

    This is the time zone defined by settings.TIME_ZONE.

    See also :func:`get_current_timezone`.
    """
    global _localtime
    if _localtime is None:
        if isinstance(settings.TIME_ZONE, basestring) and pytz is not None:
            _localtime = pytz.timezone(settings.TIME_ZONE)
        else:
            _localtime = LocalTimezone()
    return _localtime

# This function exists for consistency with get_current_timezone_name
def get_default_timezone_name():
    """
    Returns the name of the default time zone.
    """
    return _get_timezone_name(get_default_timezone())

_active = local()

def get_current_timezone():
    """
    Returns the currently active time zone as a tzinfo instance.
    """
    return getattr(_active, "value", get_default_timezone())

def get_current_timezone_name():
    """
    Returns the name of the currently active time zone.
    """
    return _get_timezone_name(get_current_timezone())

def _get_timezone_name(timezone):
    """
    Returns the name of ``timezone``.
    """
    try:
        # for pytz timezones
        return timezone.zone
    except AttributeError:
        # for regular tzinfo objects
        local_now = datetime.now(timezone)
        return timezone.tzname(local_now)

# Timezone selection functions.

# These functions don't change os.environ['TZ'] and call time.tzset()
# because it isn't thread safe.

def activate(timezone):
    """
    Sets the time zone for the current thread.

    The ``timezone`` argument must be an instance of a tzinfo subclass or a
    time zone name. If it is a time zone name, pytz is required.
    """
    if isinstance(timezone, tzinfo):
        _active.value = timezone
    elif isinstance(timezone, basestring) and pytz is not None:
        _active.value = pytz.timezone(timezone)
    else:
        raise ValueError("Invalid timezone: %r" % timezone)

def deactivate():
    """
    Unsets the time zone for the current thread.

    Django will then use the time zone defined by settings.TIME_ZONE.
    """
    if hasattr(_active, "value"):
        del _active.value

class override(object):
    """
    Temporarily set the time zone for the current thread.

    This is a context manager that uses ``~django.utils.timezone.activate()``
    to set the timezone on entry, and restores the previously active timezone
    on exit.

    The ``timezone`` argument must be an instance of a ``tzinfo`` subclass, a
    time zone name, or ``None``. If is it a time zone name, pytz is required.
    If it is ``None``, Django enables the default time zone.
    """
    def __init__(self, timezone):
        self.timezone = timezone
        self.old_timezone = getattr(_active, 'value', None)

    def __enter__(self):
        if self.timezone is None:
            deactivate()
        else:
            activate(self.timezone)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.old_timezone is not None:
            _active.value = self.old_timezone
        else:
            del _active.value


# Templates

def template_localtime(value, use_tz=None):
    """
    Checks if value is a datetime and converts it to local time if necessary.

    If use_tz is provided and is not None, that will force the value to
    be converted (or not), overriding the value of settings.USE_TZ.

    This function is designed for use by the template engine.
    """
    should_convert = (isinstance(value, datetime)
        and (settings.USE_TZ if use_tz is None else use_tz)
        and not is_naive(value)
        and getattr(value, 'convert_to_local_time', True))
    return localtime(value) if should_convert else value


# Utilities

def localtime(value, timezone=None):
    """
    Converts an aware datetime.datetime to local time.

    Local time is defined by the current time zone, unless another time zone
    is specified.
    """
    if timezone is None:
        timezone = get_current_timezone()
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # available for pytz time zones
        value = timezone.normalize(value)
    return value

def now():
    """
    Returns an aware or naive datetime.datetime, depending on settings.USE_TZ.
    """
    if settings.USE_TZ:
        # timeit shows that datetime.now(tz=utc) is 24% slower
        return datetime.utcnow().replace(tzinfo=utc)
    else:
        return datetime.now()

# By design, these four functions don't perform any checks on their arguments.
# The caller should ensure that they don't receive an invalid value like None.

def is_aware(value):
    """
    Determines if a given datetime.datetime is aware.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None

def is_naive(value):
    """
    Determines if a given datetime.datetime is naive.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is None or value.tzinfo.utcoffset(value) is None

def make_aware(value, timezone):
    """
    Makes a naive datetime.datetime in a given time zone aware.
    """
    if hasattr(timezone, 'localize'):
        # available for pytz time zones
        return timezone.localize(value, is_dst=None)
    else:
        # may be wrong around DST changes
        return value.replace(tzinfo=timezone)

def make_naive(value, timezone):
    """
    Makes an aware datetime.datetime naive in a given time zone.
    """
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # available for pytz time zones
        value = timezone.normalize(value)
    return value.replace(tzinfo=None)
########NEW FILE########
