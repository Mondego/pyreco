__FILENAME__ = admin
from django.contrib import admin
from debug_logging.models import TestRun, DebugLogRecord


class TestRunAdmin(admin.ModelAdmin):
    pass
admin.site.register(TestRun, TestRunAdmin)


class DebugLogRecordAdmin(admin.ModelAdmin):
    pass
admin.site.register(DebugLogRecord, DebugLogRecordAdmin)

########NEW FILE########
__FILENAME__ = formatters
from logging import Formatter

from django.template import Context, Template


class DjangoTemplatedFormatter(Formatter):

    def __init__(self, fmt=None, datefmt=None):
        """
        Initialize the formatter either with the specified format string, or a
        default as described above. Allow for specialized date formatting with
        the optional datefmt argument (if omitted, you get the ISO8601 format).
        """
        self._fmt = fmt or "{{ message }}"
        self.datefmt = datefmt

    def format(self, record):
        """
        Format the specified record as text.

        The record's attribute dictionary is used as the context and the format
        provided on init is used as the template. Before formatting the
        dictionary, a couple of preparatory steps are carried out. The message
        attribute of the record is computed using LogRecord.getMessage(). If
        the formatting string contains "%(asctime)", formatTime() is called to
        format the event time. If there is exception information, it is
        formatted using formatException() and appended to the message.
        """
        record.message = record.getMessage()
        if "{{ asctime }}" in self._fmt:
            record.asctime = self.formatTime(record, self.datefmt)
        t = Template(self._fmt)
        s = t.render(Context(record.__dict__))
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        return s

########NEW FILE########
__FILENAME__ = handlers
import logging

from debug_logging.models import TestRun, DebugLogRecord


class DBHandler(logging.Handler):
    
    def emit(self, record):
        if type(record.msg) is dict:
            # Pull the project name, hostname, and revision out of the record
            filters = {}
            for key in ('project_name', 'hostname', 'revision'):
                if record.msg.has_key(key):
                    filters[key] = record.msg.pop(key)
            
            # Find the open test run for this project
            try:
                test_run = TestRun.objects.get(end__isnull=True, **filters)
            except TestRun.DoesNotExist:
                # Don't log this request if there isn't an open TestRun
                return
            record.msg['test_run'] = test_run
            
            instance = DebugLogRecord(**record.msg)
            instance.save()

########NEW FILE########
__FILENAME__ = log_urls
from __future__ import with_statement
import sys
from datetime import datetime
from optparse import  make_option

from django.test.client import Client
from django.core.management.base import BaseCommand, CommandError
from django.contrib.sitemaps import Sitemap

from debug_logging.settings import LOGGING_CONFIG
from debug_logging.handlers import DBHandler
from debug_logging.utils import import_from_string


class Command(BaseCommand):
    help = 'Hit a list of urls in sequence so that the requests will be logged'
    args = "url_list [url_list ...]"

    option_list = BaseCommand.option_list + (
        make_option('-s', '--manual-start',
            action='store_true',
            dest='manual_start',
            help='Manually start a TestRun without actually logging any urls.'
        ),
        make_option('-e', '--manual-end',
            action='store_true',
            dest='manual_end',
            help='End a TestRun that was started manually.'
        ),
        make_option('-n', '--name',
            action='store',
            dest='name',
            metavar='NAME',
            help='Add a name to the test run.'
        ),
        make_option('', '--sitemap',
            action='store',
            dest='sitemap',
            metavar='SITEMAP',
            help='Load urls from a django sitemap object or dict of sitemaps.'
        ),
        make_option('-d', '--description',
            action='store',
            dest='description',
            metavar='DESC',
            help='Add a description to the test run.'
        ),
        make_option('-u', '--username',
            action='store',
            dest='username',
            metavar='USERNAME',
            help='Run the test authenticated with the USERNAME provided.'
        ),
        make_option('-p', '--password',
            action='store',
            dest='password',
            metavar='PASSWORD',
            help='Run the test authenticated with the PASSWORD provided.'
        ),
    )

    def status_update(self, msg):
        if not self.quiet:
            print msg

    def status_ticker(self):
        if not self.quiet:
            sys.stdout.write('.')
            sys.stdout.flush()

    def handle(self, *url_lists, **options):
        from django.conf import settings
        from debug_logging.models import TestRun
        from debug_logging.utils import (get_project_name, get_hostname,
                                         get_revision)

        verbosity = int(options.get('verbosity', 1))
        self.quiet = verbosity < 1
        self.verbose = verbosity > 1

        # Dtermine if the DBHandler is used
        if True in [isinstance(handler, DBHandler) for handler in
                    LOGGING_CONFIG["LOGGING_HANDLERS"]]:
            self.has_dbhandler = True
        else:
            self.has_dbhandler = False

        # Check for a username without a password, or vice versa
        if options['username'] and not options['password']:
            raise CommandError('If a username is provided, a password must '
                               'also be provided.')
        if options['password'] and not options['username']:
            raise CommandError('If a password is provided, a username must '
                               'also be provided.')

        # Create a TestRun object to track this run
        filters = {}
        panels = settings.DEBUG_TOOLBAR_PANELS
        if 'debug_logging.panels.identity.IdentityLoggingPanel' in panels:
            filters['project_name'] = get_project_name()
            filters['hostname'] = get_hostname()
        if 'debug_logging.panels.revision.RevisionLoggingPanel' in panels:
            filters['revision'] = get_revision()

        if self.has_dbhandler:
            # Check to see if there is already a TestRun object open
            existing_runs = TestRun.objects.filter(end__isnull=True, **filters)
            if existing_runs:
                if options['manual_start']:
                    # If the --manual-start option was specified, error out
                    # because there is already an open TestRun
                    raise CommandError('There is already an open TestRun.')

                # Otherwise, close it so that we can open a new one
                for existing_run in existing_runs:
                    existing_run.end = datetime.now()
                    existing_run.save()

                if options['manual_end']:
                    # If the --manual-end option was specified, we can now exit
                    self.status_update('The TestRun was successfully closed.')
                    return
            if options['manual_end']:
                # The --manual-end option was specified, but there was no
                # existing run to close.
                raise CommandError('There is no open TestRun to end.')

            filters['start'] = datetime.now()
            test_run = TestRun(**filters)

            if options['name']:
                test_run.name = options['name']
            if options['description']:
                test_run.description = options['description']

            test_run.save()

            if options['manual_start']:
                # The TestRun was successfully created
                self.status_update('A new TestRun was successfully opened.')
                return

        urls = []
        for url_list in url_lists:
            with open(url_list) as f:
                urls.extend([l.strip() for l in f.readlines()
                             if not l.startswith('#')])

        if options['sitemap']:
            sitemaps = import_from_string(options['sitemap'])

            if isinstance(sitemaps, dict):
                for sitemap in sitemaps.values():
                    urls.extend(map(sitemap.location, sitemap.items()))
            elif isinstance(sitemaps, Sitemap):
                urls.extend(map(sitemaps.location, sitemaps.items()))
            else:
                raise CommandError(
                    'Sitemaps should be a Sitemap object or a dict, got %s '
                    'instead' % type(sitemaps)
                )

        self.status_update('Beginning debug logging run...')

        client = Client()

        if options['username'] and options['password']:
            client.login(username=options['username'],
                         password=options['password'])

        for url in urls:
            try:
                response = client.get(url, DJANGO_DEBUG_LOGGING=True)
            except KeyboardInterrupt as e:
                if self.has_dbhandler:
                    # Close out the log entry
                    test_run.end = datetime.now()
                    test_run.save()

                raise CommandError('Debug logging run cancelled.')
            except Exception as e:
                if self.verbose:
                    self.status_update('\nSkipped %s because of error: %s'
                                       % (url, e))
                continue
            if response and response.status_code == 200:
                self.status_ticker()
            else:
                if self.verbose:
                    try:
                        self.status_update('\nURL %s responded with code %s'
                                           % (url, response.status_code))
                    except NameError as e:
                        self.status_update('\nSkipped %s because of error: %s'
                                           % (url, e))

        if self.has_dbhandler:
            # Close out the log entry
            test_run.end = datetime.now()
            test_run.save()

        self.status_update('done!\n')

########NEW FILE########
__FILENAME__ = middleware
import logging

from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch

from debug_toolbar.toolbar.loader import DebugToolbar
from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_logging.settings import LOGGING_CONFIG

logger = logging.getLogger('debug.logger')
for HandlerClass in LOGGING_CONFIG["LOGGING_HANDLERS"]:
    logger.addHandler(HandlerClass)


class DebugLoggingMiddleware(DebugToolbarMiddleware):
    """
    Extends the Debug Toolbar middleware with some extras for logging stats.
    """

    def _logging_enabled(self, request):
        return request.META.get('DJANGO_DEBUG_LOGGING', False)

    def _show_toolbar(self, request):
        if self._logging_enabled(request):
            # If logging is enabled, don't show the toolbar
            return False
        return super(DebugLoggingMiddleware, self)._show_toolbar(request)

    def process_request(self, request):
        if self._logging_enabled(request):
            request.debug_logging = LOGGING_CONFIG
            request.debug_logging['ENABLED'] = True
        response = super(DebugLoggingMiddleware, self).process_request(request)

        if self._logging_enabled(request):
            # If the debug-logging frontend is in use, add it to the blacklist
            blacklist = request.debug_logging['BLACKLIST']
            try:
                debug_logging_prefix = reverse('debug_logging_index')
                blacklist.append(debug_logging_prefix)
            except NoReverseMatch:
                pass

            # Don't log requests to urls in the blacklist
            for blacklist_url in blacklist:
                if request.path.startswith(blacklist_url):
                    return response

            # Add an attribute to the request to track stats, and log the
            # request path
            request.debug_logging_stats = {'request_path': request.path}

            self.debug_toolbars[request] = DebugToolbar(request)
            for panel in self.debug_toolbars[request].panels:
                panel.process_request(request)

        return response

    def process_response(self, request, response):
        response = super(DebugLoggingMiddleware, self).process_response(
            request, response)

        if response.status_code == 200:
            if self._logging_enabled(request) and \
              hasattr(request, 'debug_logging_stats'):
                # If logging is enabled, log the stats to the selected handler
                logger.debug(request.debug_logging_stats)

        return response

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'DebugLogRecord'
        db.create_table('debug_logging_debuglogrecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('project_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('request_path', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('revision', self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True)),
            ('settings_pickled', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('timer_utime', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('timer_stime', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('timer_cputime', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('timer_total', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('timer_vcsw', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('timer_ivcsw', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('sql_num_queries', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('sql_time', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('sql_queries_pickled', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('cache_num_calls', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cache_time', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('cache_hits', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cache_misses', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cache_sets', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cache_gets', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cache_get_many', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cache_deletes', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('cache_calls_pickled', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('debug_logging', ['DebugLogRecord'])


    def backwards(self, orm):
        
        # Deleting model 'DebugLogRecord'
        db.delete_table('debug_logging_debuglogrecord')


    models = {
        'debug_logging.debuglogrecord': {
            'Meta': {'object_name': 'DebugLogRecord'},
            'cache_calls_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'cache_deletes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_get_many': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_gets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_num_calls': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_sets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'request_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'settings_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_num_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sql_queries_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_cputime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_ivcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timer_stime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_total': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_utime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_vcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['debug_logging']

########NEW FILE########
__FILENAME__ = 0002_add_test_run_model
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'TestRun'
        db.create_table('debug_logging_testrun', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('end', self.gf('django.db.models.fields.DateTimeField')()),
            ('project_name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('revision', self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True)),
            ('avg_time', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('total_time', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('avg_cpu_time', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('total_cpu_time', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('avg_sql_time', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('total_sql_time', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('avg_sql_queries', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('total_sql_queries', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('max_sql_queries', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('avg_cache_hits', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('total_cache_hits', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('avg_cache_misses', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('total_cache_misses', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('debug_logging', ['TestRun'])

        # Adding field 'DebugLogRecord.test_run'
        db.add_column('debug_logging_debuglogrecord', 'test_run', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['debug_logging.TestRun'], null=True, blank=True), keep_default=False)

        # Changing field 'DebugLogRecord.hostname'
        db.alter_column('debug_logging_debuglogrecord', 'hostname', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'DebugLogRecord.project_name'
        db.alter_column('debug_logging_debuglogrecord', 'project_name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))


    def backwards(self, orm):

        raise RuntimeError("Cannot reverse this migration. 'DebugLogRecord.hostname' and 'DebugLogRecord.project_name' were made nullable.")


    models = {
        'debug_logging.debuglogrecord': {
            'Meta': {'object_name': 'DebugLogRecord'},
            'cache_calls_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'cache_deletes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_get_many': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_gets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_num_calls': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_sets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'request_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'settings_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_num_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sql_queries_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'test_run': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['debug_logging.TestRun']", 'null': 'True', 'blank': 'True'}),
            'timer_cputime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_ivcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timer_stime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_total': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_utime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_vcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'debug_logging.testrun': {
            'Meta': {'object_name': 'TestRun'},
            'avg_cache_hits': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cache_misses': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_queries': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'total_cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['debug_logging']

########NEW FILE########
__FILENAME__ = 0003_move_project_name_hostname_revision
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        """
        This is just a very basic data migration that groups all existing log
        records under one TestRun.
        """
        from django.db.models import Max, Min
        
        records = orm.DebugLogRecord.objects.all()[:1]
        if records:
            hostname = records[0].hostname
            project_name = records[0].project_name
            revision = records[0].revision
        else:
            # There are no records
            return
        
        times = orm.DebugLogRecord.objects.aggregate(Max('timestamp'), Min('timestamp'))
        start = times['timestamp__min']
        end = times['timestamp__max']
        
        test_run = orm.TestRun.objects.create(
            start=start,
            end=end,
            project_name=project_name,
            hostname=hostname,
            revision=revision,
        )
        
        for record in orm.DebugLogRecord.objects.all():
            record.test_run = test_run
            record.save()


    def backwards(self, orm):
        raise RuntimeError("Cannot reverse this migration.")


    models = {
        'debug_logging.debuglogrecord': {
            'Meta': {'object_name': 'DebugLogRecord'},
            'cache_calls_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'cache_deletes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_get_many': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_gets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_num_calls': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_sets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'request_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'settings_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_num_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sql_queries_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'test_run': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['debug_logging.TestRun']", 'null': 'True', 'blank': 'True'}),
            'timer_cputime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_ivcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timer_stime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_total': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_utime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_vcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'debug_logging.testrun': {
            'Meta': {'object_name': 'TestRun'},
            'avg_cache_hits': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cache_misses': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_queries': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'total_cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['debug_logging']

########NEW FILE########
__FILENAME__ = 0004_remove_project_name_hostname_revision
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'DebugLogRecord.hostname'
        db.delete_column('debug_logging_debuglogrecord', 'hostname')

        # Deleting field 'DebugLogRecord.revision'
        db.delete_column('debug_logging_debuglogrecord', 'revision')

        # Deleting field 'DebugLogRecord.project_name'
        db.delete_column('debug_logging_debuglogrecord', 'project_name')

        # Changing field 'DebugLogRecord.test_run'
        db.alter_column('debug_logging_debuglogrecord', 'test_run_id', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['debug_logging.TestRun']))


    def backwards(self, orm):
        
        # Adding field 'DebugLogRecord.hostname'
        db.add_column('debug_logging_debuglogrecord', 'hostname', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True), keep_default=False)

        # Adding field 'DebugLogRecord.revision'
        db.add_column('debug_logging_debuglogrecord', 'revision', self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True), keep_default=False)

        # Adding field 'DebugLogRecord.project_name'
        db.add_column('debug_logging_debuglogrecord', 'project_name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True), keep_default=False)

        # Changing field 'DebugLogRecord.test_run'
        db.alter_column('debug_logging_debuglogrecord', 'test_run_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['debug_logging.TestRun'], null=True))


    models = {
        'debug_logging.debuglogrecord': {
            'Meta': {'object_name': 'DebugLogRecord'},
            'cache_calls_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'cache_deletes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_get_many': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_gets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_num_calls': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_sets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'request_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'settings_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_num_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sql_queries_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'test_run': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['debug_logging.TestRun']"}),
            'timer_cputime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_ivcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timer_stime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_total': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_utime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_vcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'debug_logging.testrun': {
            'Meta': {'object_name': 'TestRun'},
            'avg_cache_hits': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cache_misses': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_queries': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'total_cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['debug_logging']

########NEW FILE########
__FILENAME__ = 0005_rename_picklefields
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Rename the columns that will be converted to picklefields
        db.rename_column('debug_logging_debuglogrecord', 'settings_pickled', 'settings')
        db.rename_column('debug_logging_debuglogrecord', 'sql_queries_pickled', 'sql_queries')
        db.rename_column('debug_logging_debuglogrecord', 'cache_calls_pickled', 'cache_calls')


    def backwards(self, orm):
        # Rename the columns that were converted to picklefields
        db.rename_column('debug_logging_debuglogrecord', 'settings', 'settings_pickled')
        db.rename_column('debug_logging_debuglogrecord', 'sql_queries', 'sql_queries_pickled')
        db.rename_column('debug_logging_debuglogrecord', 'cache_calls', 'cache_calls_pickled')


    models = {
        'debug_logging.debuglogrecord': {
            'Meta': {'object_name': 'DebugLogRecord'},
            'cache_calls_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'cache_deletes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_get_many': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_gets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_num_calls': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_sets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'request_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'settings_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_num_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sql_queries_pickled': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'test_run': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['debug_logging.TestRun']"}),
            'timer_cputime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_ivcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timer_stime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_total': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_utime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_vcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'debug_logging.testrun': {
            'Meta': {'object_name': 'TestRun'},
            'avg_cache_hits': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cache_misses': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_queries': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'total_cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['debug_logging']

########NEW FILE########
__FILENAME__ = 0006_auto__change_test_run_end
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'TestRun.end'
        db.alter_column('debug_logging_testrun', 'end', self.gf('django.db.models.fields.DateTimeField')(null=True))


    def backwards(self, orm):
        
        # User chose to not deal with backwards NULL issues for 'TestRun.end'
        raise RuntimeError("Cannot reverse this migration. 'TestRun.end' and its values cannot be restored.")


    models = {
        'debug_logging.debuglogrecord': {
            'Meta': {'object_name': 'DebugLogRecord'},
            'cache_calls': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'cache_deletes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_get_many': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_gets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_num_calls': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_sets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'request_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'settings': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'sql_num_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sql_queries': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'test_run': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['debug_logging.TestRun']"}),
            'timer_cputime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_ivcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timer_stime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_total': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_utime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_vcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'debug_logging.testrun': {
            'Meta': {'object_name': 'TestRun'},
            'avg_cache_hits': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cache_misses': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_queries': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'total_cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['debug_logging']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_testrun_name__add_field_testrun_description
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'TestRun.name'
        db.add_column('debug_logging_testrun', 'name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True), keep_default=False)

        # Adding field 'TestRun.description'
        db.add_column('debug_logging_testrun', 'description', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'TestRun.name'
        db.delete_column('debug_logging_testrun', 'name')

        # Deleting field 'TestRun.description'
        db.delete_column('debug_logging_testrun', 'description')


    models = {
        'debug_logging.debuglogrecord': {
            'Meta': {'object_name': 'DebugLogRecord'},
            'cache_calls': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'cache_deletes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_get_many': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_gets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_num_calls': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_sets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'request_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'settings': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'sql_num_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sql_queries': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'test_run': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['debug_logging.TestRun']"}),
            'timer_cputime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_ivcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timer_stime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_total': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_utime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_vcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'debug_logging.testrun': {
            'Meta': {'object_name': 'TestRun'},
            'avg_cache_hits': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cache_misses': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_queries': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'total_cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['debug_logging']

########NEW FILE########
__FILENAME__ = 0008_auto__add_field_testrun_total_requests
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'TestRun.total_requests'
        db.add_column('debug_logging_testrun', 'total_requests', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'TestRun.total_requests'
        db.delete_column('debug_logging_testrun', 'total_requests')


    models = {
        'debug_logging.debuglogrecord': {
            'Meta': {'object_name': 'DebugLogRecord'},
            'cache_calls': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'cache_deletes': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_get_many': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_gets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_num_calls': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_sets': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'cache_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'request_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'settings': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'sql_num_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sql_queries': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'test_run': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'records'", 'to': "orm['debug_logging.TestRun']"}),
            'timer_cputime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_ivcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timer_stime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_total': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_utime': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'timer_vcsw': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'debug_logging.testrun': {
            'Meta': {'object_name': 'TestRun'},
            'avg_cache_hits': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cache_misses': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_queries': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'avg_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'project_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'revision': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'total_cache_hits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cache_misses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_cpu_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_requests': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_queries': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_sql_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'total_time': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['debug_logging']

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models
from django.template.defaultfilters import date as date_filter

from picklefield.fields import PickledObjectField


class TestRun(models.Model):
    """Captures overall statistics about a single test run."""
    start = models.DateTimeField()
    end = models.DateTimeField(blank=True, null=True)

    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    project_name = models.CharField(max_length=255, blank=True, null=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    revision = models.CharField(max_length=40, blank=True, null=True)

    # Some of these fields aren't used yet, since they are not represented in
    # the UI.  Once they are added to the UI, they'll be added to the
    # set_aggregates method below.
    total_requests = models.IntegerField(blank=True, null=True)
    avg_time = models.FloatField(blank=True, null=True)
    total_time = models.FloatField(blank=True, null=True)
    avg_cpu_time = models.FloatField(blank=True, null=True)
    total_cpu_time = models.FloatField(blank=True, null=True)

    avg_sql_time = models.FloatField(blank=True, null=True)
    total_sql_time = models.FloatField(blank=True, null=True)
    avg_sql_queries = models.FloatField(blank=True, null=True)
    total_sql_queries = models.IntegerField(blank=True, null=True)
    max_sql_queries = models.IntegerField(blank=True, null=True)

    avg_cache_hits = models.FloatField(blank=True, null=True)
    total_cache_hits = models.IntegerField(blank=True, null=True)
    avg_cache_misses = models.FloatField(blank=True, null=True)
    total_cache_misses = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        date_format = 'n/j/Y g:i a'
        if self.name:
            return '%s (%s)' % (name, date_filter(self.start, date_format))
        return date_filter(self.start, date_format)

    def get_absolute_url(self):
        return reverse('debug_logging_run_detail', args=[self.id])

    def set_aggregates(self, force=False):
        """
        Sets any aggregates that haven't been generated yet, or recalculates
        them if the force option is indicated.
        """
        aggregates = {}
        
        if not self.avg_time or force:
            aggregates["avg_time"] = models.Avg('timer_total')
        if not self.avg_cpu_time or force:
            aggregates["avg_cpu_time"] = models.Avg('timer_cputime')
        if not self.avg_sql_time or force:
            aggregates["avg_sql_time"] = models.Avg('sql_time')
        if not self.avg_sql_queries or force:
            aggregates["avg_sql_queries"] = models.Avg('sql_num_queries')
        if not self.total_sql_queries or force:
            aggregates["total_sql_queries"] = models.Sum('sql_num_queries')
        if not self.max_sql_queries or force:
            aggregates["max_sql_queries"] = models.Max('sql_num_queries')
        if not self.total_requests or force:
            aggregates["total_requests"] = models.Count('pk')
        
        if aggregates:
            aggregated = self.records.aggregate(**aggregates)
            
            for key, value in aggregated.items():
                setattr(self, key, value)


class DebugLogRecord(models.Model):
    """Captures statistics for individual requests."""
    timestamp = models.DateTimeField(auto_now_add=True)
    test_run = models.ForeignKey(TestRun, related_name='records')

    request_path = models.CharField(max_length=255)
    settings = PickledObjectField(compress=True, blank=True, null=True)

    # Timer stats
    timer_utime = models.FloatField(blank=True, null=True)
    timer_stime = models.FloatField(blank=True, null=True)
    timer_cputime = models.FloatField(blank=True, null=True)
    timer_total = models.FloatField(blank=True, null=True)
    timer_vcsw = models.IntegerField(blank=True, null=True)
    timer_ivcsw = models.IntegerField(blank=True, null=True)

    # Sql stats
    sql_num_queries = models.IntegerField(blank=True, null=True)
    sql_time = models.FloatField(blank=True, null=True)
    sql_queries = PickledObjectField(compress=True, blank=True, null=True)

    # Cache stats
    cache_num_calls = models.IntegerField(blank=True, null=True)
    cache_time = models.FloatField(blank=True, null=True)
    cache_hits = models.IntegerField(blank=True, null=True)
    cache_misses = models.IntegerField(blank=True, null=True)
    cache_sets = models.IntegerField(blank=True, null=True)
    cache_gets = models.IntegerField(blank=True, null=True)
    cache_get_many = models.IntegerField(blank=True, null=True)
    cache_deletes = models.IntegerField(blank=True, null=True)
    cache_calls = PickledObjectField(compress=True, blank=True, null=True)

    def __unicode__(self):
        return u'DebugLogRecord from %s' % self.timestamp

########NEW FILE########
__FILENAME__ = cache
from debug_toolbar.panels.cache import CacheDebugPanel, CacheStatTracker

from debug_logging.settings import LOGGING_CONFIG


class CacheLoggingPanel(CacheDebugPanel):
    """Extends the Cache debug panel to enable logging."""

    def process_response(self, request, response):
        super(CacheLoggingPanel, self).process_response(request, response)
        if getattr(request, 'debug_logging', {}).get('ENABLED', False):
            # Logging is enabled, so log the cache data

            stats = {}

            stats['cache_num_calls'] = len(self.cache.calls)
            stats['cache_time'] = self.cache.total_time
            stats['cache_hits'] = self.cache.hits
            stats['cache_misses'] = self.cache.misses
            stats['cache_sets'] = self.cache.sets
            stats['cache_gets'] = self.cache.gets
            stats['cache_get_many'] = self.cache.get_many
            stats['cache_deletes'] = self.cache.deletes

            if LOGGING_CONFIG['CACHE_EXTRA']:
                stats['cache_calls'] = self.cache.calls

            request.debug_logging_stats.update(stats)

########NEW FILE########
__FILENAME__ = identity
from django.utils.translation import ugettext_lazy as _

from debug_logging.utils import get_project_name, get_hostname
from debug_toolbar.panels import DebugPanel


class IdentityLoggingPanel(DebugPanel):
    """
    A panel to display the current site name and hostname, to identify the
    current environment for logging.
    """
    name = 'Identity'
    has_content = False

    def nav_title(self):
        return _('Identity')

    def nav_subtitle(self):
        project_name, hostname = self.identify()
        if project_name and hostname:
            return '%s on %s' % (project_name, hostname)

    def process_response(self, request, response):
        if getattr(request, 'debug_logging', {}).get('ENABLED', False):
            project_name, hostname = self.identify()
            # Logging is enabled, so log the revision
            request.debug_logging_stats.update({
                'project_name': project_name,
                'hostname': hostname,
            })

    def identify(self):
        return get_project_name(), get_hostname()

########NEW FILE########
__FILENAME__ = revision
from django.utils.translation import ugettext_lazy as _
from debug_logging.utils import get_revision
from debug_toolbar.panels import DebugPanel


class RevisionLoggingPanel(DebugPanel):
    """
    A panel to display the current source code revision. Currently only
    supports git.
    """
    name = 'Revision'
    has_content = False

    def nav_title(self):
        return _('Revision')

    def nav_subtitle(self):
        return self.get_revision() or 'Revision unavailable'

    def process_response(self, request, response):
        if getattr(request, 'debug_logging', {}).get('ENABLED', False):
            # Logging is enabled, so log the revision
            request.debug_logging_stats.update({
                'revision': self.get_revision()
            })

    def get_revision(self):
        return get_revision()

########NEW FILE########
__FILENAME__ = settings_vars
from django.views.debug import get_safe_settings
from debug_toolbar.panels.settings_vars import SettingsVarsDebugPanel


class SettingsVarsLoggingPanel(SettingsVarsDebugPanel):
    """Extends the Settings debug panel to enable logging."""

    def process_response(self, request, response):
        super(SettingsVarsLoggingPanel, self).process_response(request, response)
        if getattr(request, 'debug_logging', {}).get('ENABLED', False):
            # Logging is enabled, so log the settings

            safe_settings = get_safe_settings()
            log_settings = {}
            for k, v in safe_settings.items():
                if request.debug_logging['LOGGED_SETTINGS_RE'].search(k):
                    log_settings[k] = v

            request.debug_logging_stats['settings'] = log_settings

########NEW FILE########
__FILENAME__ = sql
from django.db.backends import BaseDatabaseWrapper
from debug_toolbar.panels.sql import SQLDebugPanel
from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_toolbar.utils.tracking import replace_call


# Warning, ugly hackery ahead. Place an alias to the logging class in the
# panels dict.
@replace_call(BaseDatabaseWrapper.cursor)
def cursor(func, self):
    djdt = DebugToolbarMiddleware.get_current()
    if djdt:
        djdt._panels[SQLDebugPanel] = djdt.get_panel(SQLLoggingPanel)
    return func(self)


class SQLLoggingPanel(SQLDebugPanel):
    """Extends the SQL debug panel to enable logging."""

    def process_response(self, request, response):
        super(SQLLoggingPanel, self).process_response(request, response)
        if getattr(request, 'debug_logging', {}).get('ENABLED', False):
            # Call the nav_subtitle method so that the query data is captured
            self.nav_subtitle()

            for alias, query in self._queries:
                query['alias'] = alias

            stats = {}

            queries = [q for a, q in self._queries]

            if request.debug_logging['SQL_EXTRA']:
                stats['sql_queries'] = queries

            stats['sql_time'] = self._sql_time
            stats['sql_num_queries'] = len(queries)
            request.debug_logging_stats.update(stats)

########NEW FILE########
__FILENAME__ = timer
from django.conf import settings
from debug_toolbar.panels.timer import TimerDebugPanel


class TimerLoggingPanel(TimerDebugPanel):
    """Extends the Timer debug panel to enable logging."""

    def get_stats(self):
        """
        Taken from the beginning of TimerDebugPanel's 'content' method.
        """
        utime = 1000 * self._elapsed_ru('ru_utime')
        stime = 1000 * self._elapsed_ru('ru_stime')
        vcsw = self._elapsed_ru('ru_nvcsw')
        ivcsw = self._elapsed_ru('ru_nivcsw')
        minflt = self._elapsed_ru('ru_minflt')
        majflt = self._elapsed_ru('ru_majflt')

        return utime, stime, vcsw, ivcsw, minflt, majflt

    def process_response(self, request, response):
        super(TimerLoggingPanel, self).process_response(request, response)

        if getattr(request, 'debug_logging', {}).get('ENABLED', False):
            utime, stime, vcsw, ivcsw, minflt, majflt = self.get_stats()
            stats = {
                'timer_utime': utime,
                'timer_stime': stime,
                'timer_cputime': (utime + stime),
                'timer_total': self.total_time,
                'timer_vcsw': vcsw,
                'timer_ivcsw': ivcsw,
            }
            request.debug_logging_stats.update(stats)

########NEW FILE########
__FILENAME__ = settings
import re
from logging import Handler

from django.conf import settings
from django.utils.importlib import import_module

from debug_logging.utils import import_from_string


DEFAULT_LOGGED_SETTINGS = [
    'CACHE_BACKEND', 'CACHE_MIDDLEWARE_KEY_PREFIX', 'CACHE_MIDDLEWARE_SECONDS',
    'DATABASES', 'DEBUG', 'DEBUG_LOGGING_CONFIG', 'DEBUG_TOOLBAR_CONFIG',
    'DEBUG_TOOLBAR_PANELS', 'INSTALLED_APPS', 'INTERNAL_IPS',
    'MIDDLEWARE_CLASSES', 'TEMPLATE_CONTEXT_PROCESSORS', 'TEMPLATE_DEBUG',
    'USE_I18N', 'USE_L10N'
]


DEFAULT_CONFIG = {
    'SQL_EXTRA': False,
    'CACHE_EXTRA': False,
    'BLACKLIST': [],
    'LOGGING_HANDLERS': ('debug_logging.handlers.DBHandler',),
    'LOGGED_SETTINGS': DEFAULT_LOGGED_SETTINGS,
}

# Cache of the logging config.
_logging_config = None


def _get_logging_config():
    """
    Extend the default config with the values provided in settings.py, and then
    conduct some post-processing.
    """
    global _logging_config
    if _logging_config is None:
        _logging_config = dict(DEFAULT_CONFIG,
                               **getattr(settings, 'DEBUG_LOGGING_CONFIG', {}))

        # Instantiate the handlers
        handlers = []
        for handler in _logging_config['LOGGING_HANDLERS']:
            if isinstance(handler, Handler):
                handlers.append(handler())
            elif isinstance(handler, basestring):
                handlers.append(import_from_string(handler)())
        _logging_config['LOGGING_HANDLERS'] = handlers

        # Compile a regex for logged settings
        _logging_config['LOGGED_SETTINGS_RE'] = re.compile(
            '|'.join(_logging_config['LOGGED_SETTINGS'])
        )

    return _logging_config


LOGGING_CONFIG = _get_logging_config()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('debug_logging.views',
    url(r'^$', 'index', name='debug_logging_index'),
    url(r'^delete$', 'delete_runs', name='debug_logging_delete_runs'),
    url(r'^run/(\d+)/$', 'run_detail', name='debug_logging_run_detail'),
    url(r'^record/(\d+)/$', 'record_detail', name='debug_logging_record_detail'),
)

########NEW FILE########
__FILENAME__ = utils
import os.path
import platform
import subprocess

from django.conf import settings
from django.utils.importlib import import_module


def get_project_name():
    return settings.SETTINGS_MODULE.split('.')[0]


def get_hostname():
    return platform.node()


def get_revision():
    vcs = getattr(settings, 'DEBUG_TOOLBAR_CONFIG', {}).get('VCS', None)
    if vcs == 'git':
        module = import_module(settings.SETTINGS_MODULE)
        path = os.path.realpath(os.path.dirname(module.__file__))
        cmd = 'cd %s && git rev-parse --verify --short HEAD' % path
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        proc_stdout, proc_stderr = proc.communicate()
        return proc_stdout


def import_from_string(path):
    i = path.rfind('.')
    module, attr = path[:i], path[i + 1:]
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured(
            'Error importing module %s: "%s"' % (module, e)
        )
    try:
        instance = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured(
            'Module "%s" does not define a "%s" attribute' % (module, attr)
        )
    return instance

########NEW FILE########
__FILENAME__ = views
from django.core.paginator import Paginator

from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext

from debug_logging.models import DebugLogRecord, TestRun

RECORDS_PER_PAGE = 50


def _get_all_test_runs():
    return TestRun.objects.all()


def index(request):
    return render_to_response("debug_logging/index.html", {
        'all_test_runs': _get_all_test_runs(),
    }, context_instance=RequestContext(request))

def delete_runs(request):
    if request.method == "POST":
        runs = map(int, request.POST.getlist("run_id"))
        
        TestRun.objects.filter(pk__in = runs).delete()

    return redirect("debug_logging_index")

def run_detail(request, run_id):
    test_run = get_object_or_404(TestRun, id=run_id)
    
    sort = request.GET.get('sort')
    
    if sort == 'response_time':
        order_by = '-timer_total'
    elif sort == 'sql_queries':
        order_by = '-sql_num_queries'
    elif sort == 'sql_time':
        order_by = '-sql_time'
    else:
        order_by = '-timestamp'
    
    test_run.set_aggregates()
    
    p = Paginator(test_run.records.order_by(order_by), RECORDS_PER_PAGE)
    try:
        page_num = int(request.GET.get('p', 1))
    except ValueError:
        page_num = 1
    page = p.page(page_num)
    
    return render_to_response("debug_logging/run_detail.html", {
        'page': page,
        'test_run': test_run,
        'all_test_runs': _get_all_test_runs(),
    }, context_instance=RequestContext(request))


def record_detail(request, record_id):
    record = get_object_or_404(DebugLogRecord, pk=record_id)
    return render_to_response("debug_logging/record_detail.html", {
        'test_run': record.test_run,
        'record': record,
        'all_test_runs': _get_all_test_runs(),
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-debug-logging documentation build configuration file, created by
# sphinx-quickstart on Wed Nov 30 09:06:54 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

DOCS_BASE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(DOCS_BASE, '..')))

import debug_logging

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-debug-logging'
copyright = u'2011, Lincoln Loop'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = debug_logging.get_version(short=True)
# The full version, including alpha/beta/rc tags.
release = debug_logging.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-debug-loggingdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-debug-logging.tex', u'django-debug-logging Documentation',
   u'Lincoln Loop', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-debug-logging', u'django-debug-logging Documentation',
     [u'Lincoln Loop'], 1)
]

########NEW FILE########
