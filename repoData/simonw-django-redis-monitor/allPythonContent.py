__FILENAME__ = cursor_wrapper
from redis_monitor import get_instance
import time

class MonitoredCursorWrapper(object):
    def __init__(self, cursor, db):
        self.cursor = cursor
        self.db = db
        self.rm = get_instance('sqlops')
    
    def execute(self, sql, params=()):
        start = time.time()
        try:
            return self.cursor.execute(sql, params)
        finally:
            stop = time.time()
            duration_in_microseconds = int(1000000 * (stop - start))
            try:
                self.rm.record_hit_with_weight(duration_in_microseconds)
            except Exception, e:
                pass #logging.warn('RedisMonitor error: %s' % str(e))
    
    def executemany(self, sql, param_list):
        start = time.time()
        try:
            return self.cursor.executemany(sql, param_list)
        finally:
            stop = time.time()
            duration_in_microseconds = int(1000000 * (stop - start))
            try:
                self.rm.record_hits_with_total_weight(
                    len(param_list), duration_in_microseconds
                )
            except Exception, e:
                pass #logging.warn('RedisMonitor error: %s' % str(e))
    
    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)
    
    def __iter__(self):
        return iter(self.cursor)

########NEW FILE########
__FILENAME__ = middleware
from django.db.backends import BaseDatabaseWrapper
from django.conf import settings
from redis_monitor import get_instance
import time, logging

class RedisMonitorMiddleware(object):
    def process_request(self, request):
        if self.should_track_request(request):
            self.tracking = True
            self.start_time = time.time()
            self.rm = get_instance('requests')
        else:
            self.tracking = False
    
    def process_response(self, request, response):
        if getattr(self, 'tracking', False):
            duration = time.time() - self.start_time
            duration_in_microseconds = int(1000000 * duration)
            try:
                self.rm.record_hit_with_weight(duration_in_microseconds)
            except Exception, e:
                logging.warn('RedisMonitor error: %s' % str(e))
        return response
    
    def should_track_request(self, request):
        blacklist = getattr(settings, 'REDIS_MONITOR_REQUEST_BLACKLIST', [])
        for item in blacklist:
            if isinstance(item, basestring) and request.path == item:
                return False
            elif hasattr(item, 'match') and item.match(request.path):
                return False
        return True

########NEW FILE########
__FILENAME__ = base
from django.db.backends import *
from django.db.backends.mysql.base import DatabaseClient
from django.db.backends.mysql.base import DatabaseCreation
from django.db.backends.mysql.base import DatabaseIntrospection
from django.db.backends.mysql.base import DatabaseFeatures
from django.db.backends.mysql.base import DatabaseOperations
from django.db.backends.mysql.base import DatabaseWrapper \
    as OriginalDatabaseWrapper

from django_redis_monitor.cursor_wrapper import MonitoredCursorWrapper

class DatabaseWrapper(OriginalDatabaseWrapper):
    
    def _cursor(self):
        cursor = super(DatabaseWrapper, self)._cursor()
        return MonitoredCursorWrapper(cursor, self)

########NEW FILE########
__FILENAME__ = base
from django.db.backends import *
from django.db.backends.postgresql_psycopg2.base import DatabaseClient
from django.db.backends.postgresql_psycopg2.base import DatabaseCreation
from django.db.backends.postgresql_psycopg2.base import DatabaseIntrospection
from django.db.backends.postgresql_psycopg2.base import DatabaseFeatures
from django.db.backends.postgresql_psycopg2.base import DatabaseOperations
from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper \
    as OriginalDatabaseWrapper
from django.db.backends.postgresql_psycopg2.base import get_version

from django_redis_monitor.cursor_wrapper import MonitoredCursorWrapper

class DatabaseWrapper(OriginalDatabaseWrapper):
    
    def _cursor(self):
        cursor = super(DatabaseWrapper, self)._cursor()
        return MonitoredCursorWrapper(cursor, self)

########NEW FILE########
__FILENAME__ = redis_monitor
import datetime # we use utcnow to insulate against daylight savings errors
import redis

class RedisMonitor(object):
    def __init__(self, prefix='', redis_obj=None, redis_host='localhost', 
            redis_port=6379, redis_db=0
        ):
        assert prefix and ' ' not in prefix, \
            'prefix (e.g. "rps") is required and must not contain spaces'
        self.prefix = prefix
        if redis_obj is None:
            redis_obj = redis.Redis(
                host=redis_host, port=redis_port, db=redis_db
            )
        self.r = redis_obj
    
    def _hash_and_slot(self, dt = None):
        dt = dt or datetime.datetime.utcnow()
        hash = dt.strftime('%Y%m%d:%H') # 20100709:12 = 12th hour of that day
        slot = '%02d:%d' % (  # 24:3 for seconds 30-39 in minute 24
            dt.minute, dt.second / 10
        )
        return ('%s:%s' % (self.prefix, hash), slot)
    
    def _calculate_start(self, hours, minutes, seconds, now = None):
        now = now or datetime.datetime.utcnow()
        delta = (60 * 60 * hours) + (60 * minutes) + seconds
        return now - datetime.timedelta(seconds = delta)
    
    def record_hit(self):
        self.record_hits(1)
    
    def record_hits(self, num_hits):
        hash, slot = self._hash_and_slot()
        self.r.hincrby(hash, slot, num_hits)
    
    def record_hit_with_weight(self, weight):
        self.record_hits_with_total_weight(1, weight)
    
    def record_hits_with_total_weight(self, num_hits, total_weight):
        hash, slot = self._hash_and_slot()
        self.r.hincrby(hash, slot, num_hits)
        self.r.hincrby(hash, slot + 'w', total_weight)
    
    def get_recent_hits(self, hours = 0, minutes = 0, seconds = 0):
        gathered = self.get_recent_hits_and_weights(hours, minutes, seconds)
        for date, hits, weight in gathered:
            yield date, hits
    
    def get_recent_hits_and_weights(
            self, hours = 0, minutes = 0, seconds = 0
        ):
        start = self._calculate_start(hours, minutes, seconds)
        start = start.replace(
            second = (start.second / 10) * 10, microsecond = 0
        )
        preloaded_hashes = {}
        gathered = []
        current = start
        now = datetime.datetime.utcnow().replace(
            second = (start.second / 10) * 10, microsecond = 0
        )
        while current < now:
            hash, slot = self._hash_and_slot(current)
            if hash not in preloaded_hashes:
                preloaded_hashes[hash] = self.r.hgetall(hash)
            hits = int(preloaded_hashes[hash].get(slot, 0))
            weight = int(preloaded_hashes[hash].get(slot + 'w', 0))
            gathered.append((current, hits, weight))
            current += datetime.timedelta(seconds = 10)
        return gathered
    
    def get_recent_hits_per_second(self, hours = 0, minutes = 0, seconds = 0):
        gathered = self.get_recent_hits(hours, minutes, seconds)
        for date, hits in gathered:
            yield date, hits / 10.0
    
    def get_recent_avg_weights(self, hours = 0, minutes = 0, seconds = 0):
        gathered = self.get_recent_hits_and_weights(hours, minutes, seconds)
        for date, hits, weight in gathered:
            if weight == 0 or hits == 0:
                yield date, 0
            else:
                yield date, float(weight) / hits

class RedisMonitorTotalsOnly(RedisMonitor):
    
    def record_hits_with_total_weight(self, num_hits, total_weight):
        hash = '%s:totals' % self.prefix
        self.r.hincrby(hash, 'hits', num_hits)
        self.r.hincrby(hash, 'weight', total_weight)
    
    def get_recent_hits_and_weights(self, *args, **kwargs):
        raise NotImplemented, 'REDIS_MONITOR_ONLY_TRACK_TOTALS mode'
    
    def get_totals(self):
        hash = '%s:totals' % self.prefix
        return self.r.hgetall(hash) or {}

def get_instance(prefix):
    from django.conf import settings
    from django.core import signals
    host = getattr(settings, 'REDIS_MONITOR_HOST', 'localhost')
    port = getattr(settings, 'REDIS_MONITOR_PORT', 6379)
    db = getattr(settings, 'REDIS_MONITOR_DB', 0)
    only_track_totals = getattr(
        settings, 'REDIS_MONITOR_ONLY_TRACK_TOTALS', False
    )
    if only_track_totals:
        klass = RedisMonitorTotalsOnly
    else:
        klass = RedisMonitor
    obj = klass(prefix, redis_host=host, redis_port=port, redis_db=db)
    # Ensure we disconnect at the end of the request cycle
    signals.request_finished.connect(
        lambda **kwargs: obj.r.connection.disconnect()
    )
    return obj


########NEW FILE########
__FILENAME__ = base
from django.db.backends import *
from django.db.backends.sqlite3.base import DatabaseClient
from django.db.backends.sqlite3.base import DatabaseCreation
from django.db.backends.sqlite3.base import DatabaseIntrospection
from django.db.backends.sqlite3.base import DatabaseFeatures
from django.db.backends.sqlite3.base import DatabaseOperations
from django.db.backends.sqlite3.base import DatabaseWrapper \
    as OriginalDatabaseWrapper

from django_redis_monitor.cursor_wrapper import MonitoredCursorWrapper

class DatabaseWrapper(OriginalDatabaseWrapper):
    
    def _cursor(self):
        cursor = super(DatabaseWrapper, self)._cursor()
        return MonitoredCursorWrapper(cursor, self)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response as render
from django.http import HttpResponse
from django.conf import settings
from redis_monitor import get_instance

def monitor(request):
    requests = get_instance('requests')
    sqlops = get_instance('sqlops')
    if getattr(settings, 'REDIS_MONITOR_ONLY_TRACK_TOTALS', False):
        return render('django_redis_monitor/monitor_totals_only.html', {
            'requests': requests.get_totals(),
            'sqlops': sqlops.get_totals(),
        })
    else:
        return render('django_redis_monitor/monitor.html', {
            'requests': reversed(
                list(requests.get_recent_hits_per_second(minutes = 10))
            ),
            'sqlops': reversed(
                list(sqlops.get_recent_hits_per_second(minutes = 10))
            ),
        })

def nagios(request):
    if not getattr(settings, 'REDIS_MONITOR_ONLY_TRACK_TOTALS', False):
        return HttpResponse(
            'nagios only available in REDIS_MONITOR_ONLY_TRACK_TOTALS mode'
        )
    requests = get_instance('requests').get_totals()
    sqlops = get_instance('sqlops').get_totals()
    return render('django_redis_monitor/nagios.xml', {
        'db_count': sqlops.get('hits', 0),
        'db_total_ms': int(int(sqlops.get('weight', 0)) / 1000.0),
        'request_count': requests.get('hits', 0),
        'request_total_ms': int(int(requests.get('weight', 0)) / 1000.0),
    })

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
sys.path.append('../')

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
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASE_ENGINE = 'django_redis_monitor.sqlite3_backend'
DATABASE_NAME = 'data.db'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

TIME_ZONE = 'UTC'

LANGUAGE_CODE = 'en-us'
SITE_ID = 1

USE_I18N = True

MEDIA_ROOT = ''
MEDIA_URL = ''

ADMIN_MEDIA_PREFIX = '/media/'

SECRET_KEY = 'u3o25&^sgu79))-09v!ekid%1cbsa^h%75o3p%u_voh3&93vl1'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django_redis_monitor.middleware.RedisMonitorMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'redis_monitor_demo.urls'

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
    'django.contrib.flatpages',
    'django.contrib.admin',
    'django_redis_monitor', # For its templates directory
)

import re
REDIS_MONITOR_REQUEST_BLACKLIST = (
    '/favicon.ico',
    '/redis-monitor/',
    re.compile('^/static/'),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.http import HttpResponse
import time
from random import random

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', lambda request: time.sleep(random()) or HttpResponse('Hello!')),
    (r'^admin/(.*)', admin.site.root),
    ('^redis-monitor/$', 'django_redis_monitor.views.monitor'),
)

########NEW FILE########
