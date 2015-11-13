__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "salmon.settings.local")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = authentication
import base64
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.utils.crypto import constant_time_compare
from rest_framework import authentication
from rest_framework import exceptions

class SettingsAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        has_api_key = hasattr(settings, 'API_KEY')
        using_basic_auth = 'HTTP_AUTHORIZATION' in request.META
        if using_basic_auth and has_api_key:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2 and auth[0].lower() == "basic":
                key = base64.b64decode(auth[1]).split(':')[0]
                if constant_time_compare(settings.API_KEY, key):
                    request._salmon_allowed = True
                    return (AnonymousUser, None)
                else:
                    raise exceptions.AuthenticationFailed('No such user')
        return None



########NEW FILE########
__FILENAME__ = graph
from datetime import datetime
import os
import whisper

from django.conf import settings


class WhisperDatabase(object):
    def __init__(self, name):
        self.name = name
        self.path = self.get_db_path(name)
        if not os.path.exists(self.path):
            self._create()

    def get_db_path(self, name):
        return os.path.join(settings.SALMON_WHISPER_DB_PATH, name)

    def _create(self):
        """Create the Whisper file on disk"""
        if not os.path.exists(settings.SALMON_WHISPER_DB_PATH):
            os.makedirs(settings.SALMON_WHISPER_DB_PATH)
        archives = [whisper.parseRetentionDef(retentionDef)
                    for retentionDef in settings.ARCHIVES.split(",")]
        whisper.create(self.path, archives,
                       xFilesFactor=settings.XFILEFACTOR,
                       aggregationMethod=settings.AGGREGATION_METHOD)

    def update(self, timestamp, value):
        self._update([(timestamp.strftime("%s"), value)])

    def _update(self, datapoints):
        """
        This method store in the datapoints in the current database.

            :datapoints: is a list of tupple with the epoch timestamp and value
                 [(1368977629,10)]
        """
        if len(datapoints) == 1:
            timestamp, value = datapoints[0]
            whisper.update(self.path, value, timestamp)
        else:
            whisper.update_many(self.path, datapoints)

    def fetch(self, from_time, until_time=None):
        """
        This method fetch data from the database according to the period
        given

        fetch(path, fromTime, untilTime=None)

        fromTime is an datetime
        untilTime is also an datetime, but defaults to now.

        Returns a tuple of (timeInfo, valueList)
        where timeInfo is itself a tuple of (fromTime, untilTime, step)

        Returns None if no data can be returned
        """
        until_time = until_time or datetime.now()
        time_info, values = whisper.fetch(self.path,
                                          from_time.strftime('%s'),
                                          until_time.strftime('%s'))
        # build up a list of (timestamp, value)
        start_time, end_time, step = time_info
        current = start_time
        times = []
        while current <= end_time:
            times.append(current)
            current += step
        return zip(times, values)

########NEW FILE########
__FILENAME__ = start
"""
sentry.management.commands.start
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
from django.core.management import call_command
from django.core.management.base import NoArgsCommand

from optparse import make_option
import sys

from salmon.core.server import SalmonHTTPServer


class Command(NoArgsCommand):
    help = 'Starts the web service'

    option_list = NoArgsCommand.option_list + (
        make_option('--debug',
            action='store_true',
            dest='debug',
            default=False),
        make_option('--noupgrade',
            action='store_false',
            dest='upgrade',
            default=True),
        make_option('--workers', '-w',
            dest='workers',
            type=int,
            default=None),
    )

    def handle(self, address=None, upgrade=True, **options):

        if address:
            if ':' in address:
                host, port = address.split(':', 1)
                port = int(port)
            else:
                host = address
                port = None
        else:
            host, port = None, None

        if upgrade:
            # Ensure we perform an upgrade before starting any service
            print "Performing upgrade before service startup..."
            call_command('migrate', verbosity=0)


        server = SalmonHTTPServer(
            debug=options.get('debug'),
            host=host,
            port=port,
            workers=options.get('workers'),
        )

        # remove command line arguments to avoid optparse failures with service code
        # that calls call_command which reparses the command line, and if --noupgrade is supplied
        # a parse error is thrown
        sys.argv = sys.argv[:1]

        print "Running web service"
        server.run()

########NEW FILE########
__FILENAME__ = upgrade
from django.core.management import call_command
from django.core.management.base import BaseCommand
from optparse import make_option


class Command(BaseCommand):
    help = 'Performs any pending database migrations and upgrades'

    option_list = BaseCommand.option_list + (
        make_option('--noinput',
            action='store_true',
            dest='noinput',
            default=False,
            help='Tells Django to NOT prompt the user for input of any kind.',
        ),
    )

    def handle(self, **options):
        call_command('syncdb', migrate=True,
                     interactive=(not options['noinput']))

########NEW FILE########
__FILENAME__ = permissions
from rest_framework import permissions

class SalmonPermission(permissions.IsAdminUser):
    """
    Check for the token the SettingsAuthenicator sets on the request
    or if the user is an admin
    """

    def has_permission(self, request, view):
        if getattr(request, '_salmon_allowed', False):
            return True
        return super(SalmonPermission, self).has_permission(request, view)

########NEW FILE########
__FILENAME__ = runner
import base64
import os
import sys
from optparse import OptionParser
from logan.runner import run_app, parse_args, configure_app as logan_configure
from salmon.settings import base as base_settings

KEY_LENGTH = 40


def generate_settings():
    """
    This command is run when ``default_path`` doesn't exist, or ``init`` is
    run and returns a string representing the default data to put into their
    settings file.
    """
    conf_file = os.path.join(os.path.dirname(base_settings.__file__),
                             'example', 'conf.py')
    conf_template = open(conf_file).read()
    default_url = 'http://salmon.example.com'
    site_url = raw_input("What will be the URL for Salmon? [{0}]".format(
        default_url))
    site_url = site_url or default_url
    secret_key = base64.b64encode(os.urandom(KEY_LENGTH))
    api_key = base64.b64encode(os.urandom(KEY_LENGTH))
    output = conf_template.format(api_key=api_key, secret_key=secret_key,
                                  site_url=site_url)
    return output


def main():
    run_app(
        project='salmon',
        default_config_path='~/.salmon/conf.py',
        default_settings='salmon.settings.base',
        settings_initializer=generate_settings,
        settings_envvar='SALMON_CONF',
    )


# used for wsgi initialization
def configure_app(**kwargs):
    """Builds up the settings using the same method as logan"""
    sys_args = sys.argv
    args, command, command_args = parse_args(sys_args[1:])
    parser = OptionParser()
    parser.add_option('--config', metavar='CONFIG')
    (options, logan_args) = parser.parse_args(args)
    config_path = options.config
    logan_configure(config_path=config_path, **kwargs)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = server
import os
import subprocess
from django.conf import settings


# Borrowed liberally from Sentry
# https://github.com/getsentry/sentry/blob/3cc971a843efcab317f8acac0a98f1851e8f838d/src/sentry/services/http.py
class SalmonHTTPServer(object):

    def __init__(self, host=None, port=None, debug=False, workers=None):

        self.host = host or settings.WEB_HOST
        self.port = port or settings.WEB_PORT
        self.workers = workers

        options = settings.WEB_OPTIONS or {}
        gunicorn_args = [
            '--bind={0}:{1}'.format(self.host, self.port),
            '--timeout={0}'.format(options.get('timeout', 30)),
            '--name={0}'.format(options.get('name', 'Salmon')),
            '--workers={0}'.format(options.get('workers', 4)),
            '--worker-class={0}'.format(options.get('worker', 'gevent'))
        ]

        for bool_arg in ['debug', 'daemon']:
            if options.get(bool_arg):
                gunicorn_args.append('--{0}'.format(options[bool_arg]))

        if workers:
            '--workers={0}'.format(workers)

        self.gunicorn_args = gunicorn_args

    def run(self):
        command = [os.path.join(settings.PYTHON_BIN, 'gunicorn'),
                   'salmon.wsgi:application']
        subprocess.call(command + self.gunicorn_args)

########NEW FILE########
__FILENAME__ = test_authentication
import base64
from django.conf import settings
from django.utils import unittest
from django.test.client import RequestFactory
from django.test.utils import override_settings

from rest_framework import exceptions

from salmon.core.authentication import SettingsAuthentication


class TestAuthentication(unittest.TestCase):
    def setUp(self):
        self.req_factory = RequestFactory()

    @override_settings(API_KEY='test')
    def test_valid_auth(self):
        http_auth = 'Basic {0}'.format(
            base64.encodestring(settings.API_KEY))
        request = self.req_factory.post('/api/v1/metric/', {},
                                        HTTP_AUTHORIZATION=http_auth)
        auth = SettingsAuthentication()
        auth_resp = auth.authenticate(request)
        self.assertFalse(auth_resp is None, "Authentication failed")

    @override_settings(API_KEY='test')
    def test_invalid_auth(self):
        http_auth = 'Basic {0}'.format(
            base64.encodestring('wrongkey'))
        request = self.req_factory.post('/api/v1/metric/', {},
                               HTTP_AUTHORIZATION=http_auth)
        auth = SettingsAuthentication()
        self.assertRaises(exceptions.AuthenticationFailed, auth.authenticate,
                          request)

    @override_settings(API_KEY='test')
    def test_no_auth(self):
        request = self.req_factory.post('/api/v1/metric/', {})
        auth = SettingsAuthentication()
        auth_resp = auth.authenticate(request)
        self.assertTrue(auth_resp is None, "Authentication succeeded")


########NEW FILE########
__FILENAME__ = test_graph
import os

from django.conf import settings

from salmon.core import graph
from salmon.core.tests import BaseTestCase


class WhisperDatabaseTest(BaseTestCase):

    def test_database_creation(self):
        """
        Tests that the whisper database get created if does not exist.
        """
        not_existing_wsp = "doesnotexist.wsp"
        path = os.path.join(settings.SALMON_WHISPER_DB_PATH, not_existing_wsp)
        self.assertEqual(os.path.exists(path), False)
        graph.WhisperDatabase(path)
        self.assertEqual(os.path.exists(path), True)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from . import models

class MetricAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('source',)
    list_display = ('name', 'source', 'last_updated', 'value_display',
                    'alert_triggered', 'display_as', 'is_counter', 'transform',
                    'alert_operator', 'alert_value')
    list_editable = ('display_as', 'is_counter',
                     'alert_operator', 'alert_value')


    def __init__(self, *args, **kwargs):
        super(MetricAdmin, self).__init__(*args, **kwargs)
        # Don't link to detail pages
        self.list_display_links = (None, )

    def has_add_permission(self, request):
        """Hides the add metric link in admin"""
        return False

    def value_display(self, obj):
        return obj.get_value_display()
    value_display.admin_order_field = 'latest_value'


class MetricGroupAdmin(MetricAdmin):
    list_filter = ('display_as', 'is_counter')
    list_display = ('name', 'display_as', 'is_counter', 'transform',
                    'alert_operator', 'alert_value')


    def get_queryset(self, request):
        """Shows one entry per distinct metric name"""
        queryset = super(MetricGroupAdmin, self).get_queryset(request)
        # poor-man's DISTINCT ON for Sqlite3
        qs_values = queryset.values('id', 'name')
        # 2.7+ only :(
        # = {metric['name']: metric['id'] for metric in qs_values}
        distinct_names = {}
        for metric in qs_values:
            distinct_names[metric['name']] = metric['id']
        queryset = self.model.objects.filter(id__in=distinct_names.values())
        return queryset

    def save_model(self, request, obj, form, change):
        """Updates all metrics with the same name"""
        like_metrics = self.model.objects.filter(name=obj.name)
        # 2.7+ only :(
        # = {key: form.cleaned_data[key] for key in form.changed_data}
        updates = {}
        for key in form.changed_data:
            updates[key] = form.cleaned_data[key]
        like_metrics.update(**updates)



admin.site.register(models.Metric, MetricAdmin)
admin.site.register(models.MetricGroup, MetricGroupAdmin)
admin.site.register(models.Source)

########NEW FILE########
__FILENAME__ = forms
from django import forms


class FilterHistory(forms.Form):
    from_date = forms.DateTimeField(required=False)
    to_date = forms.DateTimeField(required=False)

########NEW FILE########
__FILENAME__ = generate_sample_data
from optparse import make_option

from django.core.management.base import BaseCommand

from salmon.metrics.tests import generate_sample_data


class Command(BaseCommand):
    help = "Generate sample data"
    option_list = BaseCommand.option_list + (
        make_option('--point_number',
                    action='store_true',
                    dest='point_numbers',
                    default=200,
                    help='Number of results you want to create.'),
        make_option('--interval',
                    action='store_true',
                    dest='interval',
                    default=5,
                    help='Interval in minutes between each result'))

    def handle(self, *args, **options):
        self.stdout.write("Generating sample data ....")
        self.stdout.write("This operation will take few seconds.")
        generate_sample_data(options["point_numbers"], options["interval"])
        self.stdout.write("Done!")

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Source'
        db.create_table(u'metrics_source', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'metrics', ['Source'])

        # Adding model 'Metric'
        db.create_table(u'metrics_metric', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('source', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['metrics.Source'], null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('latest_value', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('alert_operator', self.gf('django.db.models.fields.CharField')(max_length=2, blank=True)),
            ('alert_value', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('alert_triggered', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('display_as', self.gf('django.db.models.fields.CharField')(default='float', max_length=20)),
        ))
        db.send_create_signal(u'metrics', ['Metric'])

        # Adding unique constraint on 'Metric', fields ['source', 'name']
        db.create_unique(u'metrics_metric', ['source_id', 'name'])


    def backwards(self, orm):
        # Removing unique constraint on 'Metric', fields ['source', 'name']
        db.delete_unique(u'metrics_metric', ['source_id', 'name'])

        # Deleting model 'Source'
        db.delete_table(u'metrics_source')

        # Deleting model 'Metric'
        db.delete_table(u'metrics_metric')


    models = {
        u'metrics.metric': {
            'Meta': {'unique_together': "(('source', 'name'),)", 'object_name': 'Metric'},
            'alert_operator': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'alert_triggered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'alert_value': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'display_as': ('django.db.models.fields.CharField', [], {'default': "'float'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'latest_value': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['metrics.Source']", 'null': 'True'})
        },
        u'metrics.source': {
            'Meta': {'object_name': 'Source'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['metrics']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_metric_is_counter
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Metric.is_counter'
        db.add_column(u'metrics_metric', 'is_counter',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Metric.is_counter'
        db.delete_column(u'metrics_metric', 'is_counter')


    models = {
        u'metrics.metric': {
            'Meta': {'unique_together': "(('source', 'name'),)", 'object_name': 'Metric'},
            'alert_operator': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'alert_triggered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'alert_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'display_as': ('django.db.models.fields.CharField', [], {'default': "'float'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_counter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'latest_value': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['metrics.Source']", 'null': 'True'})
        },
        u'metrics.source': {
            'Meta': {'object_name': 'Source'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['metrics']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_metric_transform
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Metric.transform'
        db.add_column(u'metrics_metric', 'transform',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=20, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Metric.transform'
        db.delete_column(u'metrics_metric', 'transform')


    models = {
        u'metrics.metric': {
            'Meta': {'unique_together': "(('source', 'name'),)", 'object_name': 'Metric'},
            'alert_operator': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'alert_triggered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'alert_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'display_as': ('django.db.models.fields.CharField', [], {'default': "'float'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_counter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'latest_value': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['metrics.Source']", 'null': 'True'}),
            'transform': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        },
        u'metrics.source': {
            'Meta': {'object_name': 'Source'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['metrics']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_metric__previous_counter_value
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Metric._previous_counter_value'
        db.add_column(u'metrics_metric', '_previous_counter_value',
                      self.gf('django.db.models.fields.FloatField')(null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Metric._previous_counter_value'
        db.delete_column(u'metrics_metric', '_previous_counter_value')


    models = {
        u'metrics.metric': {
            'Meta': {'unique_together': "(('source', 'name'),)", 'object_name': 'Metric'},
            '_previous_counter_value': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'alert_operator': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'alert_triggered': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'alert_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'display_as': ('django.db.models.fields.CharField', [], {'default': "'float'", 'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_counter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'latest_value': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['metrics.Source']", 'null': 'True'}),
            'transform': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        },
        u'metrics.source': {
            'Meta': {'object_name': 'Source'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['metrics']
########NEW FILE########
__FILENAME__ = models
import logging
import operator
import time
from django.db import models
from django.core.urlresolvers import reverse
from django.utils.text import get_valid_filename
from django.template import defaultfilters
from salmon.core import graph

from . import utils

logger = logging.getLogger(__name__)


class Source(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("history", kwargs={"name": self.name})


class Metric(models.Model):
    OPERATOR_CHOICES = (
        ('lt', 'value < alert'),
        ('le', 'value <= alert'),
        ('eq', 'value == alert'),
        ('ne', 'value != alert'),
        ('ge', 'value >= alert'),
        ('gt', 'value > alert'),
    )
    DISPLAY_CHOICES = (
        ('float', 'Number'),
        ('boolean', 'True/False'),
        ('byte', 'Bytes'),
        ('percentage', 'Percentage'),
        ('second', 'Seconds'),
    )
    source = models.ForeignKey(Source, null=True)
    name = models.CharField(max_length=255)
    latest_value = models.FloatField(null=True)
    _previous_counter_value = models.FloatField(null=True)
    last_updated = models.DateTimeField(null=True)
    is_counter = models.BooleanField(default=False)
    transform = models.CharField(max_length=20, blank=True)
    alert_operator = models.CharField(max_length=2, choices=OPERATOR_CHOICES,
                                      blank=True)
    alert_value = models.FloatField(null=True, blank=True)
    alert_triggered = models.BooleanField(default=False)
    display_as = models.CharField(max_length=20, choices=DISPLAY_CHOICES,
                                  default='float')

    class Meta:
        unique_together = ('source', 'name')

    def __init__(self, *args, **kwargs):
        super(Metric, self).__init__(*args, **kwargs)
        self._reset_changes()

    def _reset_changes(self):
        """Stores current values for comparison later"""
        self._original = {}
        if self.last_updated is not None:
            self._original['last_updated'] = self.last_updated

    @property
    def whisper_filename(self):
        """Build a file path to the Whisper database"""
        source_name = self.source_id and self.source.name or ''
        return get_valid_filename("{0}__{1}.wsp".format(source_name,
                                                        self.name))

    def add_latest_to_archive(self):
        """Adds value to whisper DB"""
        archive = self.get_or_create_archive()
        archive.update(self.last_updated, self.latest_value)

    def get_or_create_archive(self):
        """
        Gets a Whisper DB instance.
        Creates it if it doesn't exist.
        """
        return graph.WhisperDatabase(self.whisper_filename)

    def load_archive(self, from_date, to_date=None):
        """Loads in historical data from Whisper database"""
        return self.get_or_create_archive().fetch(from_date, to_date)

    def in_alert_state(self):
        oper = getattr(operator, self.alert_operator)
        return bool(oper(self.latest_value, self.alert_value))

    def get_value_display(self):
        """Human friendly value output"""
        if self.display_as == 'percentage':
            return '{0}%'.format(self.latest_value)
        if self.display_as == 'boolean':
            return bool(self.latest_value)
        if self.display_as == 'byte':
            return defaultfilters.filesizeformat(self.latest_value)
        if self.display_as == 'second':
            return time.strftime('%H:%M:%S', time.gmtime(self.latest_value))
        return self.latest_value

    def time_between_updates(self):
        """Time between current `last_updated` and previous `last_updated`"""
        if 'last_updated' not in self._original:
            return 0
        last_update = self._original['last_updated']
        this_update = self.last_updated
        return this_update - last_update

    def do_transform(self):
        """Apply the transformation (if it exists) to the latest_value"""
        if not self.transform:
            return
        try:
            self.latest_value = utils.Transform(
                expr=self.transform, value=self.latest_value,
                timedelta=self.time_between_updates().total_seconds()).result()
        except (TypeError, ValueError):
            logger.warn("Invalid transformation '%s' for metric %s",
                        self.transfrom, self.pk)
        self.transform = ''

    def do_counter_conversion(self):
        """Update latest value to the diff between it and the previous value"""
        if self.is_counter:
            if self._previous_counter_value is None:
                prev_value = self.latest_value
            else:
                prev_value = self._previous_counter_value
            self._previous_counter_value = self.latest_value
            self.latest_value = self.latest_value - prev_value

    def check_alarm(self):
        if self.alert_operator and self.alert_value:
            self.alert_triggered = self.in_alert_state()

    def save(self, *args, **kwargs):
        self.do_transform()
        self.do_counter_conversion()
        self.check_alarm()
        obj = super(Metric, self).save(*args, **kwargs)
        self._reset_changes()
        return obj


class MetricGroup(Metric):
    """Used to edit all metrics with the same name in the admin"""
    class Meta:
        proxy = True

########NEW FILE########
__FILENAME__ = serializers
import logging
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.timezone import now
from rest_framework import serializers

from . import models

logger = logging.getLogger(__name__)


class MetricSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source='source.name', required=False)
    value = serializers.FloatField(source='latest_value')
    timestamp = serializers.DateTimeField(source='last_updated',
                                          required=False)

    class Meta:
        model = models.Metric
        fields = ('source', 'name', 'value', 'timestamp')

    def validate_source(self, attrs, source):
        if source in attrs:
            try:
                reverse("history", args=[attrs[source]])
            except NoReverseMatch:
                raise serializers.ValidationError("Source is invalid.")
        return attrs

    def restore_object(self, attrs, instance=None):
        kwargs = {'name': attrs['name']}
        if 'source.name' in attrs:
            source, created = models.Source.objects.get_or_create(
                name=attrs['source.name'])
            if created:
                logger.debug('Created source: %s', source.name)
            kwargs['source_id'] = source.pk
        try:
            instance = self.opts.model.objects.get(**kwargs)
        except self.opts.model.DoesNotExist:
            instance = self.opts.model(**kwargs)
        instance.latest_value = attrs['latest_value']
        instance.last_updated = attrs.get('timestamp', now())
        return instance

    def save_object(self, obj, **kwargs):
        if 'force_insert' in kwargs:
            del(kwargs['force_insert'])
        super(MetricSerializer, self).save_object(obj, **kwargs)
        obj.add_latest_to_archive()

########NEW FILE########
__FILENAME__ = metrics
from django.template import Context, Library, loader

register = Library()

@register.simple_tag
def display_result(metric):
    template_base = 'metrics/includes/{0}_field.html'
    display_template = template_base.format(metric.display_as)
    default_template = template_base.format('default')
    template = loader.select_template([display_template, default_template])
    return template.render(Context({'metric': metric}))

########NEW FILE########
__FILENAME__ = test_models
import datetime
import random
import shutil
from tempfile import mkdtemp

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from salmon.core.tests import BaseTestCase
from salmon.metrics import models

INTERVAL_MIN = 5


class TestModels(BaseTestCase):

    def test_no_alert(self):
        metric = models.Metric(latest_value=10, alert_operator='lt',
                               alert_value=11)
        self.assertTrue(metric.in_alert_state())

    def test_yes_alert(self):
        metric = models.Metric(latest_value=10, alert_operator='lt',
                               alert_value=8)
        self.assertFalse(metric.in_alert_state())

    def test_counter(self):
        first_value = 20
        second_value = 30
        third_value = 70
        metric = models.Metric(name='a', is_counter=True,
                               latest_value=first_value)
        metric.save()
        metric.latest_value = second_value
        metric.save()
        self.assertEqual(metric.latest_value, second_value - first_value)
        metric.latest_value = third_value
        metric.save()
        self.assertEqual(metric.latest_value, third_value - second_value)


    def test_archive(self):
        iters = 5
        start = (datetime.datetime.now() -
                 datetime.timedelta(minutes=iters * INTERVAL_MIN))
        metric = models.Metric(name='a', latest_value=0, last_updated=start)
        for i in range(iters):
            metric.latest_value = random.randint(1, 100)
            metric.last_updated = (
                start + datetime.timedelta(minutes=i * INTERVAL_MIN))
            metric.add_latest_to_archive()

        self.assertEqual(len(metric.load_archive(start)), iters)

########NEW FILE########
__FILENAME__ = test_serializers
from django.test import TestCase

from salmon.metrics.serializers import MetricSerializer
from salmon.metrics import models

class TestSerializer(TestCase):

    def test_single(self):
        data = {'source': 'test.example.com',
                'name': 'load',
                'value': 0.1}
        serializer = MetricSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        metric = models.Metric.objects.get(pk=serializer.object.pk)
        self.assertEqual(data['source'], metric.source.name)
        self.assertEqual(data['name'], metric.name)
        self.assertEqual(data['value'], metric.latest_value)
        self.assertFalse(metric.last_updated is None)


    def test_multi(self):
        data = [
            {'source': 'test.example.com', 'name': 'load', 'value': 0.1},
            {'source': 'multi.example.com', 'name': 'cpu', 'value': 55.5},
        ]
        serializer = MetricSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        for item in data:
            source = models.Source.objects.get(name=item['source'])
            self.assertEqual(source.metric_set.count(), 1)

    def test_invalid(self):
        data = {'source': 'test.example.com',
                'name': 'load'}
        serializer = MetricSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_invalid_source(self):
        data = {'source': 'test.example.com:8000',
                'name': 'load', 'value': 0.1}
        serializer = MetricSerializer(data=data)
        self.assertFalse(serializer.is_valid())

########NEW FILE########
__FILENAME__ = test_utils
from django.utils import unittest

from salmon.metrics.utils import Transform

class TransformTests(unittest.TestCase):
    def test_valid(self):
        result = Transform(expr='x+5*2.5', value=8.0, timedelta=0).result()
        self.assertEqual(result, 8.0+5*2.5)

    def test_bad_variable(self):
        trans = Transform(expr='b+5*2.5', value=8.0, timedelta=0)
        self.assertRaises(ValueError, trans.result)

    def test_invalid_command(self):
        trans = Transform(expr='5**99999', value=8.0, timedelta=0)
        self.assertRaises(TypeError, trans.result)

########NEW FILE########
__FILENAME__ = test_views
from django.utils.timezone import now
from django.core.urlresolvers import reverse

from salmon.core.tests import BaseTestCase
from salmon.metrics import models


class MonitorUrlTest(BaseTestCase):

    def setUp(self):
        self.source = models.Source.objects.create(name='source')
        models.Metric.objects.create(source=self.source, name='a',
                                     latest_value=1.0, last_updated=now())

    def test_dashboard_get(self):
        url = reverse("dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_history_get(self):
        url = self.source.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["graphs"]), 1)

########NEW FILE########
__FILENAME__ = utils
import ast
import operator as op


class Transform(object):
    "Parse and evaluate un-trusted expression from string"
    # Lots of help from http://stackoverflow.com/a/9558001/116042
    # supported operators
    operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                 ast.Div: op.truediv}

    def __init__(self, expr, value, timedelta):
        self.expr = expr
        self.value = value
        self.timedelta = timedelta

    def replace_variable(self, variable):
        """Substitute variables with numeric values"""
        if variable == 'x':
            return self.value
        if variable == 't':
            return self.timedelta
        raise ValueError("Invalid variable %s", variable)

    def result(self):
        """Evaluate expression and return result"""
        # Module(body=[Expr(value=...)])
        return self.eval_(ast.parse(self.expr).body[0].value)

    def eval_(self, node):
        if isinstance(node, ast.Name):
            # <variable>
            return self.replace_variable(node.id)
        if isinstance(node, ast.Num):
            # <number>
            return node.n
        if isinstance(node, ast.operator) and type(node) in self.operators:
            # <operator>
            return self.operators[type(node)]
        if isinstance(node, ast.BinOp):
            # <left> <operator> <right>
            return self.eval_(node.op)(self.eval_(node.left),
                                       self.eval_(node.right))
        raise TypeError(node)


########NEW FILE########
__FILENAME__ = views
import datetime
import json
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.utils.datastructures import SortedDict
from django.utils.timezone import now

from rest_framework.generics import CreateAPIView
from rest_framework.authentication import SessionAuthentication

from salmon.core import authentication, permissions
from . import forms, models, serializers


class CreateMetricView(CreateAPIView):
    """Saves a new metric value (or values)"""
    authentication_classes = (authentication.SettingsAuthentication,
                              SessionAuthentication)
    permission_classes = (permissions.SalmonPermission,)
    model = models.Metric
    serializer_class = serializers.MetricSerializer

    def get_serializer(self, instance=None, data=None, files=None,
                       many=False, partial=False):
        if isinstance(data, list):
            many = True
        return super(CreateMetricView, self).get_serializer(instance, data,
                                                            files, many,
                                                            partial)


def dashboard(request):
    """Shows the latest results for each source"""
    sources = (models.Source.objects.all().prefetch_related('metric_set')
                                          .order_by('name'))
    metrics = SortedDict([(src, src.metric_set.all()) for src in sources])
    no_source_metrics = models.Metric.objects.filter(source__isnull=True)
    if no_source_metrics:
        metrics[''] = no_source_metrics

    if request.META.get('HTTP_X_PJAX', False):
        parent_template = 'pjax.html'
    else:
        parent_template = 'base.html'
    return render(request, 'metrics/dashboard.html', {
        'source_metrics': metrics,
        'parent_template': parent_template
    })

def history(request, name):
    source = get_object_or_404(models.Source, name=name)
    from_date = now() - datetime.timedelta(hours=12)
    to_date = now()

    initial = {
        "from_date": from_date,
        "to_date": to_date
    }
    if "from_date" in request.GET or "to_date" in request.GET:
        data = request.GET.copy()
        if not request.GET.get("from_date"):
            data.setlist("from_date", [from_date])
        if not request.GET.get("to_date"):
            data.setlist("to_date", [to_date])
        form = forms.FilterHistory(data, initial=initial)
        if form.is_valid():
            from_date = form.cleaned_data["from_date"] or from_date
            to_date = form.cleaned_data["to_date"] or to_date
    else:
        form = forms.FilterHistory(initial=initial)
    graphs = []

    for metric in source.metric_set.all().order_by('name'):
        history = metric.load_archive(
            from_date=from_date,
            to_date=to_date)
        # javascript uses milliseconds since epoch
        js_data = map(lambda x: (x[0] * 1000, x[1]), history)
        graphs.append({
            'name': metric.name,
            'data': json.dumps(js_data),
            'type': 'float',
        })
    if request.META.get('HTTP_X_PJAX', False):
        parent_template = 'pjax.html'
    else:
        parent_template = 'base.html'
    return render(request, 'metrics/history.html', {
        'form': form,
        'source': source,
        'graphs': graphs,
        'parent_template': parent_template,
        'refresh_interval_history': settings.REFRESH_INTERVAL_HISTORY,
    })


########NEW FILE########
__FILENAME__ = base
"""Base settings shared by all environments"""
# Import global settings to make it easier to extend settings.
from django.conf.global_settings import *   # pylint: disable=W0614,W0401

#==============================================================================
# Generic Django project settings
#==============================================================================

DEBUG = False
TEMPLATE_DEBUG = DEBUG

SITE_ID = 1
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
TIME_ZONE = 'UTC'
USE_TZ = True
USE_I18N = True
USE_L10N = True
LANGUAGE_CODE = 'en'
LANGUAGES = (
    ('en', 'English'),
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '+$l@=0=6ystdflyqticq8hsa_4t#ofipjbknb%8kn5s7www=04'

INSTALLED_APPS = (
    'salmon.core',
    'salmon.metrics',

    'gunicorn',
    'south',
    'rest_framework',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
)

#==============================================================================
# Calculation of directories relative to the project module location
#==============================================================================

import os
import sys
import salmon as project_module

PROJECT_DIR = os.path.dirname(os.path.realpath(project_module.__file__))

PYTHON_BIN = os.path.dirname(sys.executable)
ve_path = os.path.dirname(os.path.dirname(os.path.dirname(PROJECT_DIR)))
# Assume that the presence of 'activate_this.py' in the python bin/
# directory means that we're running in a virtual environment.
if os.path.exists(os.path.join(PYTHON_BIN, 'activate_this.py')):
    # We're running with a virtualenv python executable.
    VAR_ROOT = os.path.join(os.path.dirname(PYTHON_BIN), 'var')
elif ve_path and os.path.exists(os.path.join(ve_path, 'bin',
                                             'activate_this.py')):
    # We're running in [virtualenv_root]/src/[project_name].
    VAR_ROOT = os.path.join(ve_path, 'var')
else:
    # Set the variable root to a path in the project which is
    # ignored by the repository.
    VAR_ROOT = os.path.join(PROJECT_DIR, 'var')

if not os.path.exists(VAR_ROOT):
    os.mkdir(VAR_ROOT)

#==============================================================================
# Project URLS and media settings
#==============================================================================

ROOT_URLCONF = 'salmon.urls'

LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'
LOGIN_REDIRECT_URL = '/'

STATIC_URL = '/static/'
MEDIA_URL = '/uploads/'

STATIC_ROOT = os.path.join(VAR_ROOT, 'static')
MEDIA_ROOT = os.path.join(VAR_ROOT, 'uploads')

STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static'),
)

ALLOWED_HOSTS = ['*']
WSGI_APPLICATION = 'salmon.wsgi.application'

#==============================================================================
# Database
#==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(VAR_ROOT, 'salmon.db'),
    }
}

#==============================================================================
# Templates
#==============================================================================

TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS += (
)

#==============================================================================
# Middleware
#==============================================================================

MIDDLEWARE_CLASSES += (
)

#==============================================================================
# Auth / security
#==============================================================================

AUTHENTICATION_BACKENDS += (
)

#==============================================================================
# Miscellaneous project settings
#==============================================================================

SALMON_URL = "http://salmon.example.com"

# Tip: Execute run_checks via ssh by using:
# SALT_COMMAND = 'ssh example.com "sudo su - salmon  -s /bin/bash -c \'salt {args} \'\"'

# work-around for https://github.com/saltstack/salt/issues/4454
SALT_COMMAND = '/usr/bin/python /usr/bin/salt -t 1 -C {args}'

# ALERT_EMAILS is a list of emails, they are notified for each
# `result.failed` unless specified otherwise in the checks.yaml
ALERT_EMAILS = None

# Time (in minutes) to keep old results in the Django database
EXPIRE_RESULTS = 60

# Interval in millisecond between each refresh of the history pages
REFRESH_INTERVAL_HISTORY = 60 * 1000

# Web Service
WEB_HOST = 'localhost'
WEB_PORT = 9000
WEB_OPTIONS = {
    'workers': 3,
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['mail_admins'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ["null"],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security.*': {
            'handlers': ["mail_admins"],
            'level': 'ERROR',
            'propagate': False,
        },
        'salmon.*': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },

    }
}

#==============================================================================
# Third party app settings
#==============================================================================

########NEW FILE########
__FILENAME__ = conf
import os
SECRET_KEY = "{secret_key}"

SALMON_URL = "{site_url}"

API_KEY = "{api_key}"

# https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
# from urlparse import urlparse
# ALLOWED_HOSTS = [urlparse(SALMON_URL).hostname]

SALMON_WHISPER_DB_PATH = os.path.expanduser('~/.salmon/whisper')

# ==============================================================
# whisper
# ==============================================================
XFILEFACTOR = 0.5
AGGREGATION_METHOD = "average"
ARCHIVES = "5m:1d,30m:7d,1d:1y"


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.contrib import admin

from salmon.metrics import views as metrics_views

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    url(r'^$', metrics_views.dashboard, name="dashboard"),
    url(r'^(?P<name>[-\w\._]*)/$', metrics_views.history, name="history"),
    url(r'^api/v1/metric/$', metrics_views.CreateMetricView.as_view()),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for salmon project.

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

from salmon.core.runner import configure_app, generate_settings
configure_app(
        project='salmon',
        default_config_path='~/.salmon/conf.py',
        default_settings='salmon.settings.base',
        settings_initializer=generate_settings,
        settings_envvar='SALMON_CONF',
    )

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
from dj_static import Cling

application = Cling(get_wsgi_application())

########NEW FILE########
