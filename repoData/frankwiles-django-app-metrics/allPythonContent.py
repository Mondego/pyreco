__FILENAME__ = admin
from django.contrib import admin

from app_metrics.models import (Metric, MetricSet, MetricItem, MetricDay,
                                MetricWeek, MetricMonth, MetricYear
                                )


class MetricAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'slug', 'num')
    list_filter = ['metric__name']

    def slug(self, obj):
        return obj.metric.slug

admin.site.register(Metric)
admin.site.register(MetricSet)
admin.site.register(MetricDay, MetricAdmin)
admin.site.register(MetricWeek, MetricAdmin)
admin.site.register(MetricMonth, MetricAdmin)
admin.site.register(MetricYear, MetricAdmin)
admin.site.register(MetricItem, MetricAdmin)

########NEW FILE########
__FILENAME__ = composite
from django.conf import settings
from django.utils.importlib import import_module

DEFAULT_BACKENDS = getattr(settings, 'APP_METRICS_COMPOSITE_BACKENDS', [])


def metric(slug, num=1, **kwargs):
    _call_backends('metric', slug, num, **kwargs)


def timing(slug, seconds_taken, **kwargs):
    _call_backends('timing', slug, seconds_taken, **kwargs)


def gauge(slug, current_value, **kwargs):
    _call_backends('gauge', slug, current_value, **kwargs)


def _call_backends(method, slug, value, backends=DEFAULT_BACKENDS, **kwargs):
    for path in backends:
        backend = import_module(path)
        getattr(backend, method)(slug, value, **kwargs)

########NEW FILE########
__FILENAME__ = db
from app_metrics.tasks import db_metric_task, db_gauge_task


def metric(slug, num=1, **kwargs):
    """ Fire a celery task to record our metric in the database """
    db_metric_task.delay(slug, num, **kwargs)


def timing(slug, seconds_taken, **kwargs):
    # Unsupported, hence the noop.
    pass


def gauge(slug, current_value, **kwargs):
    """Fire a celery task to record the gauge's current value in the database."""
    db_gauge_task.delay(slug, current_value, **kwargs)

########NEW FILE########
__FILENAME__ = librato
from app_metrics.tasks import librato_metric_task


def _get_func(async):
    return librato_metric_task.delay if async else librato_metric_task


def metric(slug, num=1, async=True, **kwargs):
    _get_func(async)(slug, num, type="counter", **kwargs)


def timing(slug, seconds_taken, async=True, **kwargs):
    """not implemented"""


def gauge(slug, current_value, async=True, **kwargs):
    _get_func(async)(slug, current_value, type="gauge", **kwargs)

########NEW FILE########
__FILENAME__ = mixpanel
# Backend to handle sending app metrics directly to mixpanel.com
# See http://mixpanel.com/api/docs/ for more information on their API

from django.conf import settings
from app_metrics.tasks import mixpanel_metric_task
from app_metrics.tasks import _get_token


def metric(slug, num=1, properties=None):
    """
    Send metric directly to Mixpanel

    - slug here will be used as the Mixpanel "event" string
    - if num > 1, we will loop over this and send multiple
    - properties are a dictionary of additional information you
      may want to pass to Mixpanel.  For example you might use it like:

      metric("invite-friends",
             properties={"method": "email", "number-friends": "12", "ip": "123.123.123.123"})
    """
    token = _get_token()
    mixpanel_metric_task.delay(slug, num, properties)


def timing(slug, seconds_taken, **kwargs):
    # Unsupported, hence the noop.
    pass


def gauge(slug, current_value, **kwargs):
    # Unsupported, hence the noop.
    pass

########NEW FILE########
__FILENAME__ = redis
# Backend to store info in Redis
from django.conf import settings
from app_metrics.tasks import redis_metric_task, redis_gauge_task

def metric(slug, num=1, properties={}):
    redis_metric_task.delay(slug, num, **properties)

def timing(slug, seconds_taken, **kwargs):
    # No easy way to do this with redis, so this is a no-op
    pass

def gauge(slug, current_value, **kwargs):
    redis_gauge_task.delay(slug, current_value, **kwargs)


########NEW FILE########
__FILENAME__ = statsd
from django.conf import settings
from app_metrics.tasks import statsd_metric_task, statsd_timing_task, statsd_gauge_task


def metric(slug, num=1, **kwargs):
    """
    Send metric directly to statsd

    - ``slug`` will be used as the statsd "bucket" string
    - ``num`` increments the counter by that number
    """
    statsd_metric_task.delay(slug, num, **kwargs)


def timing(slug, seconds_taken, **kwargs):
    """
    Send timing directly to statsd

    - ``slug`` will be used as the statsd "bucket" string
    - ``seconds_taken`` stores the time taken as a float
    """
    statsd_timing_task.delay(slug, seconds_taken, **kwargs)


def gauge(slug, current_value, **kwargs):
    """
    Send timing directly to statsd

    - ``slug`` will be used as the statsd "bucket" string
    - ``current_value`` stores the current value of the gauge
    """
    statsd_gauge_task.delay(slug, current_value, **kwargs)

########NEW FILE########
__FILENAME__ = compat
from django.conf import settings
import django

__all__ = ['User', 'AUTH_USER_MODEL']

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


# Django 1.5+ compatibility
if django.VERSION >= (1, 5):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    username_field = User.USERNAME_FIELD
else:
    from django.contrib.auth.models import User
    username_field = 'username'

########NEW FILE########
__FILENAME__ = exceptions
class AppMetricsError(Exception):
    pass


class InvalidMetricsBackend(AppMetricsError):
    pass


class MetricError(AppMetricsError):
    pass


class TimerError(AppMetricsError):
    pass

########NEW FILE########
__FILENAME__ = metrics_aggregate
import datetime 
from django.core.management.base import NoArgsCommand 

from app_metrics.models import Metric, MetricItem, MetricDay, MetricWeek, MetricMonth, MetricYear 

from app_metrics.utils import week_for_date, month_for_date, year_for_date, get_backend 

class Command(NoArgsCommand): 
    help = "Aggregate Application Metrics" 

    requires_model_validation = True 

    def handle_noargs(self, **options): 
        """ Aggregate Application Metrics """ 

        backend = get_backend() 

        # If using Mixpanel this command is a NOOP
        if backend == 'app_metrics.backends.mixpanel': 
            print "Useless use of metrics_aggregate when using Mixpanel backend"
            return 

        # Aggregate Items
        items = MetricItem.objects.all() 

        for i in items: 
            # Daily Aggregation 
            day,create = MetricDay.objects.get_or_create(metric=i.metric, 
                                                         created=i.created)

            day.num = day.num + i.num
            day.save() 

            # Weekly Aggregation 
            week_date = week_for_date(i.created)
            week, create = MetricWeek.objects.get_or_create(metric=i.metric,
                                                            created=week_date)

            week.num = week.num + i.num 
            week.save() 

            # Monthly Aggregation 
            month_date = month_for_date(i.created) 
            month, create = MetricMonth.objects.get_or_create(metric=i.metric,
                                                              created=month_date)
            month.num = month.num + i.num 
            month.save() 

            # Yearly Aggregation 
            year_date = year_for_date(i.created) 
            year, create = MetricYear.objects.get_or_create(metric=i.metric,
                                                              created=year_date)
            year.num = year.num + i.num 
            year.save() 

        # Kill off our items 
        items.delete() 

########NEW FILE########
__FILENAME__ = metrics_send_mail
import datetime 
import string

from django.core.management.base import NoArgsCommand 
from django.conf import settings 
from django.db.models import Q
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from app_metrics.reports import generate_report
from app_metrics.models import MetricSet, Metric 
from app_metrics.utils import get_backend 

class Command(NoArgsCommand): 
    help = "Send Report E-mails" 
    requires_model_validation = True 
    can_import_settings = True 

    def handle_noargs(self, **options): 
        """ Send Report E-mails """ 

        from django.conf import settings
        translation.activate(settings.LANGUAGE_CODE)

        backend = get_backend() 

        # This command is a NOOP if using the Mixpanel backend 
        if backend == 'app_metrics.backends.mixpanel': 
            print "Useless use of metrics_send_email when using Mixpanel backend."
            return 

        # Determine if we should also send any weekly or monthly reports 
        today = datetime.date.today() 
        if today.weekday == 0: 
            send_weekly = True
        else: 
            send_weekly = False 

        if today.day == 1: 
            send_monthly = True 
        else: 
            send_monthly = False 

        qs = MetricSet.objects.filter(Q(no_email=False), Q(send_daily=True) | Q(send_monthly=send_monthly) | Q(send_weekly=send_weekly))

        if "mailer" in settings.INSTALLED_APPS: 
            from mailer import send_html_mail 
            USE_MAILER = True 
        else: 
            from django.core.mail import EmailMultiAlternatives
            USE_MAILER = False 

        for s in qs: 
            subject = _("%s Report") % s.name 

            recipient_list = s.email_recipients.values_list('email', flat=True)
            
            (message, message_html) = generate_report(s, html=True)

            if message == None:
                continue

            if USE_MAILER: 
                send_html_mail(subject=subject, 
                               message=message, 
                               message_html=message_html, 
                               from_email=settings.DEFAULT_FROM_EMAIL, 
                               recipient_list=recipient_list)
            else: 
                msg = EmailMultiAlternatives(subject=subject,
                                             body=message,
                                             from_email=settings.DEFAULT_FROM_EMAIL,
                                             to=recipient_list)
                msg.attach_alternative(message_html, "text/html")
                msg.send()

        translation.deactivate()


########NEW FILE########
__FILENAME__ = move_to_mixpanel
from django.core.management.base import NoArgsCommand

from app_metrics.models import MetricItem
from app_metrics.backends.mixpanel import metric
from app_metrics.utils import get_backend

class Command(NoArgsCommand):
    help = "Move MetricItems from the db backend to MixPanel"

    requires_model_validation = True

    def handle_noargs(self, **options):
        """ Move MetricItems from the db backend to MixPanel" """

        backend = get_backend()

        # If not using Mixpanel this command is a NOOP
        if backend != 'app_metrics.backends.mixpanel':
            print "You need to set the backend to MixPanel"
            return

        items = MetricItem.objects.all()

        for i in items:
            properties = {
                'time': i.created.strftime('%s'),
            }
            metric(i.metric.slug, num=i.num, properties=properties)

        # Kill off our items
        items.delete()

########NEW FILE########
__FILENAME__ = move_to_statsd
import sys
from django.core.management.base import NoArgsCommand
from app_metrics.models import MetricItem
from app_metrics.backends.statsd_backend import metric


class Command(NoArgsCommand):
    help = "Move MetricItems from the db backend to statsd"
    requires_model_validation = True

    def handle_noargs(self, **options):
        """Move MetricItems from the db backend to statsd"""
        backend = get_backend()

        # If not using statsd, this command is a NOOP.
        if backend != 'app_metrics.backends.statsd_backend':
            sys.exit(1, "You need to set the backend to 'statsd_backend'")

        items = MetricItem.objects.all()

        for i in items:
            metric(i.metric.slug, num=i.num)

        # Kill off our items
        items.delete()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from app_metrics.compat import AUTH_USER_MODEL


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Metric'
        db.create_table('app_metrics_metric', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=60)),
        ))
        db.send_create_signal('app_metrics', ['Metric'])

        # Adding model 'MetricSet'
        db.create_table('app_metrics_metricset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('no_email', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('send_daily', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('send_weekly', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('send_monthly', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('app_metrics', ['MetricSet'])

        # Adding M2M table for field metrics on 'MetricSet'
        db.create_table('app_metrics_metricset_metrics', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('metricset', models.ForeignKey(orm['app_metrics.metricset'], null=False)),
            ('metric', models.ForeignKey(orm['app_metrics.metric'], null=False))
        ))
        db.create_unique('app_metrics_metricset_metrics', ['metricset_id', 'metric_id'])

        # Adding M2M table for field email_recipients on 'MetricSet'
        db.create_table('app_metrics_metricset_email_recipients', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('metricset', models.ForeignKey(orm['app_metrics.metricset'], null=False)),
            ('user', models.ForeignKey(orm[AUTH_USER_MODEL], null=False))
        ))
        db.create_unique('app_metrics_metricset_email_recipients', ['metricset_id', 'user_id'])

        # Adding model 'MetricItem'
        db.create_table('app_metrics_metricitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('metric', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['app_metrics.Metric'])),
            ('num', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('created', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
        ))
        db.send_create_signal('app_metrics', ['MetricItem'])

        # Adding model 'MetricDay'
        db.create_table('app_metrics_metricday', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('metric', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['app_metrics.Metric'])),
            ('num', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('created', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
        ))
        db.send_create_signal('app_metrics', ['MetricDay'])

        # Adding model 'MetricWeek'
        db.create_table('app_metrics_metricweek', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('metric', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['app_metrics.Metric'])),
            ('num', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('created', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
        ))
        db.send_create_signal('app_metrics', ['MetricWeek'])

        # Adding model 'MetricMonth'
        db.create_table('app_metrics_metricmonth', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('metric', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['app_metrics.Metric'])),
            ('num', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('created', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
        ))
        db.send_create_signal('app_metrics', ['MetricMonth'])

        # Adding model 'MetricYear'
        db.create_table('app_metrics_metricyear', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('metric', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['app_metrics.Metric'])),
            ('num', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('created', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
        ))
        db.send_create_signal('app_metrics', ['MetricYear'])

    def backwards(self, orm):
        # Deleting model 'Metric'
        db.delete_table('app_metrics_metric')

        # Deleting model 'MetricSet'
        db.delete_table('app_metrics_metricset')

        # Removing M2M table for field metrics on 'MetricSet'
        db.delete_table('app_metrics_metricset_metrics')

        # Removing M2M table for field email_recipients on 'MetricSet'
        db.delete_table('app_metrics_metricset_email_recipients')

        # Deleting model 'MetricItem'
        db.delete_table('app_metrics_metricitem')

        # Deleting model 'MetricDay'
        db.delete_table('app_metrics_metricday')

        # Deleting model 'MetricWeek'
        db.delete_table('app_metrics_metricweek')

        # Deleting model 'MetricMonth'
        db.delete_table('app_metrics_metricmonth')

        # Deleting model 'MetricYear'
        db.delete_table('app_metrics_metricyear')

    models = {
        'app_metrics.metric': {
            'Meta': {'object_name': 'Metric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '60'})
        },
        'app_metrics.metricday': {
            'Meta': {'object_name': 'MetricDay'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricitem': {
            'Meta': {'object_name': 'MetricItem'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'app_metrics.metricmonth': {
            'Meta': {'object_name': 'MetricMonth'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricset': {
            'Meta': {'object_name': 'MetricSet'},
            'email_recipients': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm[AUTH_USER_MODEL]", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metrics': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['app_metrics.Metric']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'no_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_daily': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'send_monthly': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_weekly': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'app_metrics.metricweek': {
            'Meta': {'object_name': 'MetricWeek'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricyear': {
            'Meta': {'object_name': 'MetricYear'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
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
        AUTH_USER_MODEL: {
            'Meta': {'object_name': AUTH_USER_MODEL.split('.')[-1]},
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
        }
    }

    complete_apps = ['app_metrics']

########NEW FILE########
__FILENAME__ = 0002_alter_created_to_datetime
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from app_metrics.compat import AUTH_USER_MODEL


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'MetricItem.created'
        db.alter_column('app_metrics_metricitem', 'created', self.gf('django.db.models.fields.DateTimeField')())
    def backwards(self, orm):

        # Changing field 'MetricItem.created'
        db.alter_column('app_metrics_metricitem', 'created', self.gf('django.db.models.fields.DateField')())
    models = {
        'app_metrics.metric': {
            'Meta': {'object_name': 'Metric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '60'})
        },
        'app_metrics.metricday': {
            'Meta': {'object_name': 'MetricDay'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricitem': {
            'Meta': {'object_name': 'MetricItem'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'app_metrics.metricmonth': {
            'Meta': {'object_name': 'MetricMonth'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricset': {
            'Meta': {'object_name': 'MetricSet'},
            'email_recipients': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm[AUTH_USER_MODEL]", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metrics': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['app_metrics.Metric']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'no_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_daily': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'send_monthly': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_weekly': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'app_metrics.metricweek': {
            'Meta': {'object_name': 'MetricWeek'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricyear': {
            'Meta': {'object_name': 'MetricYear'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
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
        AUTH_USER_MODEL: {
            'Meta': {'object_name': AUTH_USER_MODEL.split('.')[-1]},
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
        }
    }

    complete_apps = ['app_metrics']

########NEW FILE########
__FILENAME__ = 0003_auto__add_gauge
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from app_metrics.compat import AUTH_USER_MODEL


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Gauge'
        db.create_table('app_metrics_gauge', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=60)),
            ('current_value', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=15, decimal_places=6)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('app_metrics', ['Gauge'])


    def backwards(self, orm):
        # Deleting model 'Gauge'
        db.delete_table('app_metrics_gauge')


    models = {
        'app_metrics.gauge': {
            'Meta': {'object_name': 'Gauge'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'current_value': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '15', 'decimal_places': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '60'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'app_metrics.metric': {
            'Meta': {'object_name': 'Metric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '60'})
        },
        'app_metrics.metricday': {
            'Meta': {'object_name': 'MetricDay'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricitem': {
            'Meta': {'object_name': 'MetricItem'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        'app_metrics.metricmonth': {
            'Meta': {'object_name': 'MetricMonth'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricset': {
            'Meta': {'object_name': 'MetricSet'},
            'email_recipients': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm[AUTH_USER_MODEL]", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metrics': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['app_metrics.Metric']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'no_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_daily': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'send_monthly': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_weekly': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'app_metrics.metricweek': {
            'Meta': {'object_name': 'MetricWeek'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
        'app_metrics.metricyear': {
            'Meta': {'object_name': 'MetricYear'},
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metric': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['app_metrics.Metric']"}),
            'num': ('django.db.models.fields.BigIntegerField', [], {'default': '0'})
        },
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
        AUTH_USER_MODEL: {
            'Meta': {'object_name': AUTH_USER_MODEL.split('.')[-1]},
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
        }
    }

    complete_apps = ['app_metrics']

########NEW FILE########
__FILENAME__ = models
import datetime

from django.db import models, IntegrityError
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from app_metrics.compat import User


class Metric(models.Model):
    """ The type of metric we want to store """
    name = models.CharField(_('name'), max_length=50)
    slug = models.SlugField(_('slug'), unique=True, max_length=60, db_index=True)

    class Meta:
        verbose_name = _('metric')
        verbose_name_plural = _('metrics')

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id and not self.slug:
            self.slug = slugify(self.name)
            i = 0
            while True:
                try:
                    return super(Metric, self).save(*args, **kwargs)
                except IntegrityError:
                    i += 1
                    self.slug = "%s_%d" % (self.slug, i)
        else:
            return super(Metric, self).save(*args, **kwargs)


class MetricSet(models.Model):
    """ A set of metrics that should be sent via email to certain users """
    name = models.CharField(_('name'), max_length=50)
    metrics = models.ManyToManyField(Metric, verbose_name=_('metrics'))
    email_recipients = models.ManyToManyField(User, verbose_name=_('email recipients'))
    no_email = models.BooleanField(_('no e-mail'), default=False)
    send_daily = models.BooleanField(_('send daily'), default=True)
    send_weekly = models.BooleanField(_('send weekly'), default=False)
    send_monthly = models.BooleanField(_('send monthly'), default=False)

    class Meta:
        verbose_name = _('metric set')
        verbose_name_plural = _('metric sets')

    def __unicode__(self):
        return self.name


class MetricItem(models.Model):
    """ Individual metric items """
    metric = models.ForeignKey(Metric, verbose_name=_('metric'))
    num = models.IntegerField(_('number'), default=1)
    created = models.DateTimeField(_('created'), default=datetime.datetime.now)

    class Meta:
        verbose_name = _('metric item')
        verbose_name_plural = _('metric items')

    def __unicode__(self):
        return _("'%(name)s' of %(num)d on %(created)s") % {
            'name': self.metric.name,
            'num': self.num,
            'created': self.created
        }


class MetricDay(models.Model):
    """ Aggregation of Metrics on a per day basis """
    metric = models.ForeignKey(Metric, verbose_name=_('metric'))
    num = models.BigIntegerField(_('number'), default=0)
    created = models.DateField(_('created'), default=datetime.date.today)

    class Meta:
        verbose_name = _('day metric')
        verbose_name_plural = _('day metrics')

    def __unicode__(self):
        return _("'%(name)s' for '%(created)s'") % {
            'name': self.metric.name,
            'created': self.created
        }


class MetricWeek(models.Model):
    """ Aggregation of Metrics on a weekly basis """
    metric = models.ForeignKey(Metric, verbose_name=_('metric'))
    num = models.BigIntegerField(_('number'), default=0)
    created = models.DateField(_('created'), default=datetime.date.today)

    class Meta:
        verbose_name = _('week metric')
        verbose_name_plural = _('week metrics')

    def __unicode__(self):
        return _("'%(name)s' for week %(week)s of %(year)s") % {
            'name': self.metric.name,
            'week': self.created.strftime("%U"),
            'year': self.created.strftime("%Y")
        }


class MetricMonth(models.Model):
    """ Aggregation of Metrics on monthly basis """
    metric = models.ForeignKey(Metric, verbose_name=('metric'))
    num = models.BigIntegerField(_('number'), default=0)
    created = models.DateField(_('created'), default=datetime.date.today)

    class Meta:
        verbose_name = _('month metric')
        verbose_name_plural = _('month metrics')

    def __unicode__(self):
        return _("'%(name)s' for %(month)s %(year)s") % {
            'name': self.metric.name,
            'month': self.created.strftime("%B"),
            'year': self.created.strftime("%Y")
        }


class MetricYear(models.Model):
    """ Aggregation of Metrics on a yearly basis """
    metric = models.ForeignKey(Metric, verbose_name=_('metric'))
    num = models.BigIntegerField(_('number'), default=0)
    created = models.DateField(_('created'), default=datetime.date.today)

    class Meta:
        verbose_name = _('year metric')
        verbose_name_plural = _('year metrics')

    def __unicode__(self):
        return _("'%(name)s' for %(year)s") % {
            'name': self.metric.name,
            'year': self.created.strftime("%Y")
        }


class Gauge(models.Model):
    """
    A representation of the current state of some data.
    """
    name = models.CharField(_('name'), max_length=50)
    slug = models.SlugField(_('slug'), unique=True, max_length=60)
    current_value = models.DecimalField(_('current value'), max_digits=15, decimal_places=6, default='0.00')
    created = models.DateTimeField(_('created'), default=datetime.datetime.now)
    updated = models.DateTimeField(_('updated'), default=datetime.datetime.now)

    class Meta:
        verbose_name = _('gauge')
        verbose_name_plural = _('gauges')

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id and not self.slug:
            self.slug = slugify(self.name)

        self.updated = datetime.datetime.now()
        return super(Gauge, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = reports
import datetime

from django.template.loader import render_to_string

from app_metrics.models import *
from app_metrics.trending import trending_for_metric

from django.conf import settings

def generate_report(metric_set=None, html=False):
    """ Generate a Metric Set Report """

    # Get trending data for each metric
    metric_trends = []
    for m in metric_set.metrics.all():
        data = {'metric': m}
        data['trends'] = trending_for_metric(m)
        metric_trends.append(data)

    send_zero_activity = getattr(settings, 'APP_METRICS_SEND_ZERO_ACTIVITY', True)

    if not send_zero_activity:
        activity_today = False
        for trend in metric_trends:
            if trend['trends']['current_day'] > 0:
                activity_today = True
                continue
        if not activity_today:
            return None, None


    message = render_to_string('app_metrics/email.txt', {
                            'metric_set': metric_set,
                            'metrics': metric_trends,
                            'today': datetime.date.today(),
                })

    if html:
        message_html = render_to_string('app_metrics/email.html', {
                            'metric_set': metric_set,
                            'metrics': metric_trends,
                            'today': datetime.date.today(),
                })

        return message, message_html

    else:
        return message

########NEW FILE########
__FILENAME__ = tasks
import base64
import json
import urllib
import urllib2
import datetime

try:
    from celery.task import task
except ImportError:
    from celery.decorators import task

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from app_metrics.models import Metric, MetricItem, Gauge

# For statsd support
try:
    # Not required. If we do this once at the top of the module, we save
    # ourselves the pain of importing every time the task fires.
    import statsd
except ImportError:
    statsd = None

# For redis support
try:
    import redis
except:
    redis = None

# For librato support
try:
    import librato
    from librato.metrics import Gauge as LibratoGauge
    from librato.metrics import Counter as LibratoCounter
except ImportError:
    librato = None


class MixPanelTrackError(Exception):
    pass

# DB Tasks

@task
def db_metric_task(slug, num=1, **kwargs):
    met = Metric.objects.get(slug=slug)
    MetricItem.objects.create(metric=met, num=num)


@task
def db_gauge_task(slug, current_value, **kwargs):
    gauge, created = Gauge.objects.get_or_create(slug=slug, defaults={
        'name': slug,
        'current_value': current_value,
    })

    if not created:
        gauge.current_value = current_value
        gauge.save()


def _get_token():
    token = getattr(settings, 'APP_METRICS_MIXPANEL_TOKEN', None)

    if not token:
        raise ImproperlyConfigured("You must define APP_METRICS_MIXPANEL_TOKEN when using the mixpanel backend.")
    else:
        return token

# Mixpanel tasks

@task
def mixpanel_metric_task(slug, num, properties=None, **kwargs):
    token = _get_token()
    if properties is None:
        properties = dict()

    if "token" not in properties:
        properties["token"] = token

    url = getattr(settings, 'APP_METRICS_MIXPANEL_API_URL', "http://api.mixpanel.com/track/")

    params = {"event": slug, "properties": properties}
    b64_data = base64.b64encode(json.dumps(params))

    data = urllib.urlencode({"data": b64_data})
    req = urllib2.Request(url, data)
    for i in range(num):
        response = urllib2.urlopen(req)
        if response.read() == '0':
            raise MixPanelTrackError(u'MixPanel returned 0')


# Statsd tasks

def get_statsd_conn():
    if statsd is None:
        raise ImproperlyConfigured("You must install 'python-statsd' in order to use this backend.")

    conn = statsd.Connection(
        host=getattr(settings, 'APP_METRICS_STATSD_HOST', 'localhost'),
        port=int(getattr(settings, 'APP_METRICS_STATSD_PORT', 8125)),
        sample_rate=float(getattr(settings, 'APP_METRICS_STATSD_SAMPLE_RATE', 1)),
    )
    return conn


@task
def statsd_metric_task(slug, num=1, **kwargs):
    conn = get_statsd_conn()
    counter = statsd.Counter(slug, connection=conn)
    counter += num


@task
def statsd_timing_task(slug, seconds_taken=1.0, **kwargs):
    conn = get_statsd_conn()

    # You might be wondering "Why not use ``timer.start/.stop`` here?"
    # The problem is that this is a task, likely running out of process
    # & perhaps with network overhead. We'll measure the timing elsewhere,
    # in-process, to be as accurate as possible, then use the out-of-process
    # task for talking to the statsd backend.
    timer = statsd.Timer(slug, connection=conn)
    timer.send('total', seconds_taken)


@task
def statsd_gauge_task(slug, current_value, **kwargs):
    conn = get_statsd_conn()
    gauge = statsd.Gauge(slug, connection=conn)
    # We send nothing here, since we only have one name/slug to work with here.
    gauge.send('', current_value)

# Redis tasks

def get_redis_conn():
    if redis is None:
        raise ImproperlyConfigured("You must install 'redis' in order to use this backend.")
    conn = redis.StrictRedis(
        host=getattr(settings, 'APP_METRICS_REDIS_HOST', 'localhost'),
        port=getattr(settings, 'APP_METRICS_REDIS_PORT', 6379),
        db=getattr(settings, 'APP_METRICS_REDIS_DB', 0),
    )
    return conn


@task
def redis_metric_task(slug, num=1, **kwargs):
    # Record a metric in redis. We prefix our key here with 'm' for Metric
    # and build keys for each day, week, month, and year
    r = get_redis_conn()

    # Build keys
    now = datetime.datetime.now()
    day_key = "m:%s:%s" % (slug, now.strftime("%Y-%m-%d"))
    week_key = "m:%s:w:%s" % (slug, now.strftime("%U"))
    month_key = "m:%s:m:%s" % (slug, now.strftime("%Y-%m"))
    year_key = "m:%s:y:%s" % (slug, now.strftime("%Y"))

    # Increment keys
    r.incrby(day_key, num)
    r.incrby(week_key, num)
    r.incrby(month_key, num)
    r.incrby(year_key, num)


@task
def redis_gauge_task(slug, current_value, **kwargs):
    # We prefix our keys with a 'g' here for Gauge to avoid issues
    # of having a gauge and metric of the same name
    r = get_redis_conn()
    r.set("g:%s" % slug, current_value)

# Librato tasks

@task
def librato_metric_task(name, num, **kwargs):
    api = librato.connect(settings.APP_METRICS_LIBRATO_USER,
                          settings.APP_METRICS_LIBRATO_TOKEN)
    api.submit(name, num, **kwargs)

########NEW FILE########
__FILENAME__ = base_tests
import datetime
from decimal import Decimal
import mock

from django.test import TestCase
from django.core import management
from django.conf import settings
from django.core import mail
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured

from app_metrics.exceptions import TimerError
from app_metrics.models import Metric, MetricItem, MetricDay, MetricWeek, MetricMonth, MetricYear, Gauge
from app_metrics.utils import *
from app_metrics.trending import _trending_for_current_day, _trending_for_yesterday, _trending_for_week, _trending_for_month, _trending_for_year

class MetricCreationTests(TestCase):

    def test_auto_slug_creation(self):
        new_metric = Metric.objects.create(name='foo bar')
        self.assertEqual(new_metric.name, 'foo bar')
        self.assertEqual(new_metric.slug, 'foo-bar')

        new_metric2 = Metric.objects.create(name='foo bar')
        self.assertEqual(new_metric2.name, 'foo bar')
        self.assertEqual(new_metric2.slug, 'foo-bar_1')

    def test_metric(self):
        new_metric = create_metric(name='Test Metric Class',
                                   slug='test_metric')

        metric('test_metric')
        metric('test_metric')
        metric('test_metric')

        current_count = MetricItem.objects.filter(metric=new_metric)

        self.assertEqual(len(current_count), 3)
        self.assertEqual(current_count[0].num, 1)
        self.assertEqual(current_count[1].num, 1)
        self.assertEqual(current_count[2].num, 1)

    def test_get_or_create_metric(self):
        new_metric = get_or_create_metric(name='Test Metric Class',
                                          slug='test_metric')

        metric('test_metric')
        metric('test_metric')
        metric('test_metric')

        new_metric = get_or_create_metric(name='Test Metric Class',
                                          slug='test_metric')

        current_count = MetricItem.objects.filter(metric=new_metric)
        self.assertEqual(len(current_count), 3)
        self.assertEqual(current_count[0].num, 1)
        self.assertEqual(current_count[1].num, 1)
        self.assertEqual(current_count[2].num, 1)

class MetricAggregationTests(TestCase):

    def setUp(self):
        self.metric1 = create_metric(name='Test Aggregation1', slug='test_agg1')
        self.metric2 = create_metric(name='Test Aggregation2', slug='test_agg2')

        metric('test_agg1')
        metric('test_agg1')

        metric('test_agg2')
        metric('test_agg2')
        metric('test_agg2')

    def test_daily_aggregation(self):
        management.call_command('metrics_aggregate')

        day1 = MetricDay.objects.get(metric=self.metric1)
        day2 = MetricDay.objects.get(metric=self.metric2)
        self.assertEqual(day1.num, 2)
        self.assertEqual(day2.num, 3)

    def test_weekly_aggregation(self):
        management.call_command('metrics_aggregate')

        week1 = MetricWeek.objects.get(metric=self.metric1)
        week2 = MetricWeek.objects.get(metric=self.metric2)
        self.assertEqual(week1.num, 2)
        self.assertEqual(week2.num, 3)

    def test_monthly_aggregation(self):
        management.call_command('metrics_aggregate')

        month1 = MetricMonth.objects.get(metric=self.metric1)
        month2 = MetricMonth.objects.get(metric=self.metric2)
        self.assertEqual(month1.num, 2)
        self.assertEqual(month2.num, 3)

    def test_yearly_aggregation(self):
        management.call_command('metrics_aggregate')

        year1 = MetricYear.objects.get(metric=self.metric1)
        year2 = MetricYear.objects.get(metric=self.metric2)
        self.assertEqual(year1.num, 2)
        self.assertEqual(year2.num, 3)

class DisabledTests(TestCase):
    """ Test disabling collection """

    def setUp(self):
        super(DisabledTests, self).setUp()
        self.old_disabled = getattr(settings, 'APP_METRICS_DISABLED', False)
        settings.APP_METRICS_DISABLED = True
        self.metric1 = create_metric(name='Test Disable', slug='test_disable')

    def test_disabled(self):
        self.assertEqual(MetricItem.objects.filter(metric__slug='test_disable').count(), 0)
        settings.APP_METRICS_DISABLED = True
        metric('test_disable')
        self.assertEqual(MetricItem.objects.filter(metric__slug='test_disable').count(), 0)
        self.assertTrue(collection_disabled())

    def tearDown(self):
        settings.APP_METRICS_DISABLED = self.old_disabled
        super(DisabledTests, self).tearDown()

class TrendingTests(TestCase):
    """ Test that our trending logic works """

    def setUp(self):
        self.metric1 = create_metric(name='Test Trending1', slug='test_trend1')
        self.metric2 = create_metric(name='Test Trending2', slug='test_trend2')

    def test_trending_for_current_day(self):
        """ Test current day trending counter """
        metric('test_trend1')
        metric('test_trend1')
        management.call_command('metrics_aggregate')
        metric('test_trend1')
        metric('test_trend1')

        count = _trending_for_current_day(self.metric1)
        self.assertEqual(count, 4)

    def test_trending_for_yesterday(self):
        """ Test yesterday trending """
        today = datetime.date.today()
        yesterday_date = today - datetime.timedelta(days=1)
        previous_week_date = today - datetime.timedelta(weeks=1)
        previous_month_date = get_previous_month(today)

        MetricDay.objects.create(metric=self.metric1, num=5, created=yesterday_date)
        MetricDay.objects.create(metric=self.metric1, num=4, created=previous_week_date)
        MetricDay.objects.create(metric=self.metric1, num=3, created=previous_month_date)

        data = _trending_for_yesterday(self.metric1)
        self.assertEqual(data['yesterday'], 5)
        self.assertEqual(data['previous_week'], 4)
        self.assertEqual(data['previous_month'], 3)

    def test_trending_for_week(self):
        """ Test weekly trending data """
        this_week_date = week_for_date(datetime.date.today())
        previous_week_date = this_week_date - datetime.timedelta(weeks=1)
        previous_month_date = get_previous_month(this_week_date)
        previous_year_date = get_previous_year(this_week_date)

        MetricWeek.objects.create(metric=self.metric1, num=5, created=this_week_date)
        MetricWeek.objects.create(metric=self.metric1, num=4, created=previous_week_date)
        MetricWeek.objects.create(metric=self.metric1, num=3, created=previous_month_date)
        MetricWeek.objects.create(metric=self.metric1, num=2, created=previous_year_date)

        data = _trending_for_week(self.metric1)
        self.assertEqual(data['week'], 5)
        self.assertEqual(data['previous_week'], 4)
        self.assertEqual(data['previous_month_week'], 3)
        self.assertEqual(data['previous_year_week'], 2)

    def test_trending_for_month(self):
        """ Test monthly trending data """
        this_month_date = month_for_date(datetime.date.today())
        previous_month_date = get_previous_month(this_month_date)
        previous_month_year_date = get_previous_year(this_month_date)

        MetricMonth.objects.create(metric=self.metric1, num=5, created=this_month_date)
        MetricMonth.objects.create(metric=self.metric1, num=4, created=previous_month_date)
        MetricMonth.objects.create(metric=self.metric1, num=3, created=previous_month_year_date)

        data = _trending_for_month(self.metric1)
        self.assertEqual(data['month'], 5)
        self.assertEqual(data['previous_month'], 4)
        self.assertEqual(data['previous_month_year'], 3)

    def test_trending_for_year(self):
        """ Test yearly trending data """
        this_year_date = year_for_date(datetime.date.today())
        previous_year_date = get_previous_year(this_year_date)

        MetricYear.objects.create(metric=self.metric1, num=5, created=this_year_date)
        MetricYear.objects.create(metric=self.metric1, num=4, created=previous_year_date)

        data = _trending_for_year(self.metric1)
        self.assertEqual(data['year'], 5)
        self.assertEqual(data['previous_year'], 4)

    def test_missing_trending(self):
        this_week_date = week_for_date(datetime.date.today())
        previous_week_date = this_week_date - datetime.timedelta(weeks=1)
        previous_month_date = get_previous_month(this_week_date)
        previous_year_date = get_previous_year(this_week_date)

        MetricWeek.objects.create(metric=self.metric1, num=5, created=this_week_date)
        MetricWeek.objects.create(metric=self.metric1, num=4, created=previous_week_date)
        MetricWeek.objects.create(metric=self.metric1, num=3, created=previous_month_date)

        data = _trending_for_week(self.metric1)
        self.assertEqual(data['week'], 5)
        self.assertEqual(data['previous_week'], 4)
        self.assertEqual(data['previous_month_week'], 3)
        self.assertEqual(data['previous_year_week'], 0)

class EmailTests(TestCase):
    """ Test that our emails send properly """
    def setUp(self):
        self.user1 = User.objects.create_user('user1', 'user1@example.com', 'user1pass')
        self.user2 = User.objects.create_user('user2', 'user2@example.com', 'user2pass')
        self.metric1 = create_metric(name='Test Trending1', slug='test_trend1')
        self.metric2 = create_metric(name='Test Trending2', slug='test_trend2')
        self.set = create_metric_set(name="Fake Report",
                                     metrics=[self.metric1, self.metric2],
                                     email_recipients=[self.user1, self.user2])

    def test_email(self):
        """ Test email sending """
        metric('test_trend1')
        metric('test_trend1')
        metric('test_trend1')
        metric('test_trend2')
        metric('test_trend2')

        management.call_command('metrics_aggregate')
        management.call_command('metrics_send_mail')

        self.assertEqual(len(mail.outbox), 1)


class GaugeTests(TestCase):
    def setUp(self):
        self.gauge = Gauge.objects.create(
            name='Testing',
        )

    def test_existing_gauge(self):
        self.assertEqual(Gauge.objects.all().count(), 1)
        self.assertEqual(Gauge.objects.get(slug='testing').current_value, Decimal('0.00'))
        gauge('testing', '10.5')

        # We should not have created a new gauge
        self.assertEqual(Gauge.objects.all().count(), 1)
        self.assertEqual(Gauge.objects.get(slug='testing').current_value, Decimal('10.5'))

        # Test updating
        gauge('testing', '11.1')
        self.assertEqual(Gauge.objects.get(slug='testing').current_value, Decimal('11.1'))

    def test_new_gauge(self):
        gauge('test_trend1', Decimal('12.373'))
        self.assertEqual(Gauge.objects.all().count(), 2)
        self.assertTrue('test_trend1' in list(Gauge.objects.all().values_list('slug', flat=True)))
        self.assertEqual(Gauge.objects.get(slug='test_trend1').current_value, Decimal('12.373'))


class TimerTests(TestCase):
    def setUp(self):
        super(TimerTests, self).setUp()
        self.timer = Timer()

    def test_start(self):
        with mock.patch('time.time') as mock_time:
            mock_time.return_value = '12345.0'
            self.timer.start()

        self.assertEqual(self.timer._start, '12345.0')

        self.assertRaises(TimerError, self.timer.start)

    def test_stop(self):
        self.assertRaises(TimerError, self.timer.stop)

        with mock.patch('time.time') as mock_time:
            mock_time.return_value = 12345.0
            self.timer.start()

        with mock.patch('time.time') as mock_time:
            mock_time.return_value = 12347.2
            self.timer.stop()

        self.assertAlmostEqual(self.timer._elapsed, 2.2)
        self.assertEqual(self.timer._start, None)

    def test_elapsed(self):
        self.assertRaises(TimerError, self.timer.elapsed)

        self.timer._elapsed = 2.2
        self.assertEqual(self.timer.elapsed(), 2.2)

    # The ``Timer.store()`` is tested as part of the statsd backend tests.

class MixpanelCommandTest1(TestCase):
    """ Test out our management command noops """

    def setUp(self):
        new_metric = Metric.objects.create(name='foo bar')
        i = MetricItem.objects.create(metric=new_metric)
        self.old_backend = settings.APP_METRICS_BACKEND
        settings.APP_METRICS_BACKEND = 'app_metrics.backends.db'

    def test_mixpanel_noop(self):
        self.assertEqual(1, MetricItem.objects.all().count())
        management.call_command('move_to_mixpanel')
        self.assertEqual(1, MetricItem.objects.all().count())

    def tearDown(self):
        settings.APP_METRICS_BACKEND = self.old_backend

class MixpanelCommandTest2(TestCase):
    """ Test out our management command works """

    def setUp(self):
        new_metric = Metric.objects.create(name='foo bar')
        i = MetricItem.objects.create(metric=new_metric)
        self.old_backend = settings.APP_METRICS_BACKEND
        settings.APP_METRICS_BACKEND = 'app_metrics.backends.mixpanel'

    def test_mixpanel_op(self):
        self.assertEqual(1, MetricItem.objects.all().count())
        self.assertRaises(ImproperlyConfigured, management.call_command, 'move_to_mixpanel')

    def tearDown(self):
        settings.APP_METRICS_BACKEND = self.old_backend

########NEW FILE########
__FILENAME__ = librato_tests

########NEW FILE########
__FILENAME__ = mixpanel_tests
from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from app_metrics.utils import *

class MixpanelMetricConfigTests(TestCase):

    def setUp(self):
        self.old_backend = settings.APP_METRICS_BACKEND
        settings.APP_METRICS_BACKEND = 'app_metrics.backends.mixpanel'

    def test_metric(self):
        self.assertRaises(ImproperlyConfigured, metric, 'test_metric')

    def tearDown(self):
        settings.APP_METRICS_BACKEND = self.old_backend

class MixpanelCreationTests(TestCase):

    def setUp(self):
        self.old_backend = settings.APP_METRICS_BACKEND
        self.old_token = settings.APP_METRICS_MIXPANEL_TOKEN
        settings.APP_METRICS_BACKEND = 'app_metrics.backends.mixpanel'
        settings.APP_METRICS_MIXPANEL_TOKEN = 'foobar'

    def test_metric(self):
        metric('testing')

    def tearDown(self):
        settings.APP_METRICS_BACKEND = self.old_backend
        settings.APP_METRICS_MIXPANEL_TOKEN = self.old_token

########NEW FILE########
__FILENAME__ = redis_tests
import mock
from django.test import TestCase
from django.conf import settings
from app_metrics.utils import metric, gauge

class RedisTests(TestCase):
    def setUp(self):
        super(RedisTests, self).setUp()
        self.old_backend = getattr(settings, 'APP_METRICS_BACKEND', None)
        settings.APP_METRICS_BACKEND = 'app_metrics.backends.redis'

    def tearDown(self):
        settings.APP_METRICS_BACKEND = self.old_backend
        super(RedisTests, self).tearDown()

    def test_metric(self):
        with mock.patch('redis.client.StrictRedis') as mock_client:
            instance = mock_client.return_value
            instance._send.return_value = 1

            metric('foo')
            mock_client._send.asert_called_with(mock.ANY, {'slug':'foo', 'num':'1'})

    def test_gauge(self):
        with mock.patch('redis.client.StrictRedis') as mock_client:
            instance = mock_client.return_value
            instance._send.return_value = 1

            gauge('testing', 10.5)
            mock_client._send.asert_called_with(mock.ANY, {'slug':'testing', 'current_value':'10.5'})


########NEW FILE########
__FILENAME__ = settings
import os

import django

BASE_PATH = os.path.dirname(__file__)

if django.VERSION[:2] >= (1, 3):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASE_ENGINE = 'sqlite3'
    DATABASE_NAME = ':memory:'

SITE_ID = 1

DEBUG = True

TEST_RUNNER = 'django_coverage.coverage_runner.CoverageRunner'

COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$',
    'common.views.test', '__init__', 'django',
    'migrations', 'djcelery'
]

COVERAGE_REPORT_HTML_OUTPUT_DIR = os.path.join(BASE_PATH, 'coverage')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'app_metrics',
    'app_metrics.tests',
    'djcelery',
    'django_coverage'
]

ROOT_URLCONF = 'app_metrics.tests.urls'

CELERY_ALWAYS_EAGER = True

APP_METRICS_BACKEND = 'app_metrics.backends.db'
APP_METRICS_MIXPANEL_TOKEN = None
APP_METRICS_DISABLED = False

SECRET_KEY = "herp-derp"

########NEW FILE########
__FILENAME__ = statsd_tests
from decimal import Decimal
import mock
import time
from django.test import TestCase
from django.conf import settings
from app_metrics.utils import metric, timing, gauge


class StatsdCreationTests(TestCase):
    def setUp(self):
        super(StatsdCreationTests, self).setUp()
        self.old_backend = getattr(settings, 'APP_METRICS_BACKEND', None)
        settings.APP_METRICS_BACKEND = 'app_metrics.backends.statsd'

    def test_metric(self):
        with mock.patch('statsd.Client') as mock_client:
            instance = mock_client.return_value
            instance._send.return_value = 1

            metric('testing')
            mock_client._send.assert_called_with(mock.ANY, {'testing': '1|c'})

            metric('testing', 2)
            mock_client._send.assert_called_with(mock.ANY, {'testing': '2|c'})

            metric('another', 4)
            mock_client._send.assert_called_with(mock.ANY, {'another': '4|c'})

    def test_timing(self):
        with mock.patch('statsd.Client') as mock_client:
            instance = mock_client.return_value
            instance._send.return_value = 1

            with timing('testing'):
                time.sleep(0.025)

            mock_client._send.assert_called_with(mock.ANY, {'testing.total': mock.ANY})

    def test_gauge(self):
        with mock.patch('statsd.Client') as mock_client:
            instance = mock_client.return_value
            instance._send.return_value = 1

            gauge('testing', 10.5)
            mock_client._send.assert_called_with(mock.ANY, {'testing': '10.5|g'})

            gauge('testing', Decimal('6.576'))
            mock_client._send.assert_called_with(mock.ANY, {'testing': '6.576|g'})

            gauge('another', 1)
            mock_client._send.assert_called_with(mock.ANY, {'another': '1|g'})

    def tearDown(self):
        settings.APP_METRICS_BACKEND = self.old_backend
        super(StatsdCreationTests, self).tearDown()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
        (r'^admin/', include(admin.site.urls)),
        (r'^admin/metrics/', include('app_metrics.urls')),
)

########NEW FILE########
__FILENAME__ = trending
import datetime

from django.core.exceptions import ObjectDoesNotExist

from app_metrics.models import Metric, MetricItem, MetricDay, MetricWeek, MetricMonth, MetricYear
from app_metrics.utils import week_for_date, month_for_date, year_for_date, get_previous_month, get_previous_year

class InvalidMetric(Exception): pass

def trending_for_metric(metric=None, date=None):
    """ Build a dictionary of trending values for a given metric """

    if not isinstance(metric, Metric):
        raise InvalidMetric('No Metric instance passed to trending_for_metric()')
    if not date:
        date = datetime.date.today()

    data = {}

    # Get current day values so far
    if date == datetime.date.today():
        data['current_day'] = _trending_for_current_day(metric)

    data['yesterday']   = _trending_for_yesterday(metric)
    data['week']        = _trending_for_week(metric)
    data['month']       = _trending_for_month(metric)
    data['year']        = _trending_for_year(metric)

    return data

def _trending_for_current_day(metric=None):
    date = datetime.date.today()
    unaggregated_values = MetricItem.objects.filter(metric=metric)
    aggregated_values = MetricDay.objects.filter(metric=metric, created=date)
    count = 0

    for u in unaggregated_values:
        count = count + u.num

    for a in aggregated_values:
        count = count + a.num

    return count

def _trending_for_yesterday(metric=None):
    today = datetime.date.today()
    yesterday_date = today - datetime.timedelta(days=1)
    previous_week_date = today - datetime.timedelta(weeks=1)
    previous_month_date = get_previous_month(today)

    data = {
            'yesterday': 0,
            'previous_week': 0,
            'previous_month': 0,
    }

    try:
        yesterday = MetricDay.objects.get(metric=metric, created=yesterday_date)
        data['yesterday'] = yesterday.num
    except ObjectDoesNotExist:
        pass

    try: 
        previous_week = MetricDay.objects.get(metric=metric, created=previous_week_date)
        data['previous_week'] = previous_week.num
    except ObjectDoesNotExist:
        pass

    try:
        previous_month = MetricDay.objects.get(metric=metric, created=previous_month_date)
        data['previous_month'] = previous_month.num
    except ObjectDoesNotExist:
        pass

    return data

def _trending_for_week(metric=None):
    this_week_date = week_for_date(datetime.date.today())
    previous_week_date = this_week_date - datetime.timedelta(weeks=1)
    previous_month_week_date = get_previous_month(this_week_date)
    previous_year_week_date = get_previous_year(this_week_date)

    data = {
            'week': 0,
            'previous_week': 0,
            'previous_month_week': 0,
            'previous_year_week': 0,
    }

    try:
        week = MetricWeek.objects.get(metric=metric, created=this_week_date)
        data['week'] = week.num
    except ObjectDoesNotExist:
        pass

    try:
        previous_week = MetricWeek.objects.get(metric=metric, created=previous_week_date)
        data['previous_week'] = previous_week.num
    except ObjectDoesNotExist:
        pass

    try:
        previous_month_week = MetricWeek.objects.get(metric=metric, created=previous_month_week_date)
        data['previous_month_week'] = previous_month_week.num
    except ObjectDoesNotExist:
        pass

    try:
        previous_year_week = MetricWeek.objects.get(metric=metric, created=previous_year_week_date)
        data['previous_year_week'] = previous_year_week.num
    except ObjectDoesNotExist:
        pass

    return data

def _trending_for_month(metric=None):
    this_month_date = month_for_date(datetime.date.today())
    previous_month_date = get_previous_month(this_month_date)
    previous_month_year_date = get_previous_year(this_month_date)

    data = {
            'month': 0,
            'previous_month': 0,
            'previous_month_year': 0
    }

    try:
        month = MetricMonth.objects.get(metric=metric, created=this_month_date)
        data['month'] = month.num
    except ObjectDoesNotExist:
        pass

    try:
        previous_month = MetricMonth.objects.get(metric=metric, created=previous_month_date)
        data['previous_month'] = previous_month.num
    except ObjectDoesNotExist:
        pass

    try:
        previous_month_year = MetricMonth.objects.get(metric=metric, created=previous_month_year_date)
        data['previous_month_year'] = previous_month_year.num
    except ObjectDoesNotExist:
        pass

    return data

def _trending_for_year(metric=None):
    this_year_date = year_for_date(datetime.date.today())
    previous_year_date = get_previous_year(this_year_date)

    data = {
            'year': 0,
            'previous_year': 0,
    }

    try:
        year = MetricYear.objects.get(metric=metric, created=this_year_date)
        data['year'] = year.num
    except ObjectDoesNotExist:
        pass

    try:
        previous_year = MetricYear.objects.get(metric=metric, created=previous_year_date)
        data['previous_year'] = previous_year.num
    except ObjectDoesNotExist:
        pass

    return data

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *

from app_metrics.views import *

urlpatterns = patterns('',
        url(
            regex   = r'^reports/$',
            view    = metric_report_view,
            name    = 'app_metrics_reports',
            ),
    )

########NEW FILE########
__FILENAME__ = utils
from contextlib import contextmanager
import datetime
import time
from django.conf import settings
from django.utils.importlib import import_module

from app_metrics.exceptions import InvalidMetricsBackend, TimerError
from app_metrics.models import Metric, MetricSet


def collection_disabled():
    return getattr(settings, 'APP_METRICS_DISABLED', False)


def get_backend():
    return getattr(settings, 'APP_METRICS_BACKEND', 'app_metrics.backends.db')


def get_composite_backends():
    return getattr(settings, 'APP_METRICS_COMPOSITE_BACKENDS', ())


def should_create_models(backend=None):
    if backend is None:
        backend = get_backend()

    if backend == 'app_metrics.backends.composite':
        backends = get_composite_backends()
        for b in backends:
            if b == 'app_metrics.backends.db':
                return True
    else:
        return backend == 'app_metrics.backends.db'


def create_metric_set(name=None, metrics=None, email_recipients=None,
        no_email=False, send_daily=True, send_weekly=False,
        send_monthly=False):
    """ Create a metric set """

    # This should be a NOOP for the non-database-backed backends
    if not should_create_models():
        return

    try:
        metric_set = MetricSet(
                            name=name,
                            no_email=no_email,
                            send_daily=send_daily,
                            send_weekly=send_weekly,
                            send_monthly=send_monthly)
        metric_set.save()

        for m in metrics:
            metric_set.metrics.add(m)

        for e in email_recipients:
            metric_set.email_recipients.add(e)

    except:
        return False

    return metric_set

def create_metric(name, slug):
    """ Create a new type of metric to track """

    # This should be a NOOP for the non-database-backed backends
    if not should_create_models():
        return

    # See if this metric already exists
    existing = Metric.objects.filter(name=name, slug=slug)

    if existing:
        return False
    else:
        new_metric = Metric(name=name, slug=slug)
        new_metric.save()
        return new_metric

def get_or_create_metric(name, slug):
    """
    Returns the metric with the given name and slug, creating
    it if necessary
    """

    # This should be a NOOP for the non-database-backed backends
    if not should_create_models():
        return

    metric, created = Metric.objects.get_or_create(slug=slug, defaults={'name': name})
    return metric


def import_backend():
    backend_string = get_backend()

    # Attempt to import the backend
    try:
        backend = import_module(backend_string)
    except Exception, e:
        raise InvalidMetricsBackend("Could not load '%s' as a backend: %s" %
                                    (backend_string, e))

    return backend


def metric(slug, num=1, **kwargs):
    """ Increment a metric """
    if collection_disabled():
        return

    backend = import_backend()

    try:
        backend.metric(slug, num, **kwargs)
    except Metric.DoesNotExist:
        create_metric(slug=slug, name='Autocreated Metric')


class Timer(object):
    """
    An object for manually controlling timing. Useful in situations where the
    ``timing`` context manager will not work.

    Usage::

        timer = Timer()
        timer.start()

        # Do some stuff.

        timer.stop()

        # Returns a float of how many seconds the logic took.
        timer.elapsed()

        # Stores the float of how many seconds the logic took.
        timer.store()

    """
    def __init__(self):
        self._start = None
        self._elapsed = None

    def timestamp(self):
        return time.time()

    def start(self):
        if self._start is not None:
            raise TimerError("You have already called '.start()' on this instance.")

        self._start = time.time()

    def stop(self):
        if self._start is None:
            raise TimerError("You must call '.start()' before calling '.stop()'.")

        self._elapsed = time.time() - self._start
        self._start = None

    def elapsed(self):
        if self._elapsed is None:
            raise TimerError("You must call '.stop()' before trying to get the elapsed time.")

        return self._elapsed

    def store(self, slug):
        if collection_disabled():
            return
        backend = import_backend()
        backend.timing(slug, self.elapsed())


@contextmanager
def timing(slug):
    """
    A context manager to recording how long some logic takes & sends it off to
    the backend.

    Usage::

        with timing('create_event'):
            # Your code here.
            # For example, create the event & all the related data.
            event = Event.objects.create(
                title='Coffee break',
                location='LPT',
                when=datetime.datetime(2012, 5, 4, 14, 0, 0)
            )
    """
    timer = Timer()
    timer.start()
    yield
    timer.stop()
    timer.store(slug)


def gauge(slug, current_value, **kwargs):
    """Update a gauge."""
    if collection_disabled():
        return
    backend = import_backend()
    backend.gauge(slug, current_value, **kwargs)


def week_for_date(date):
    return date - datetime.timedelta(days=date.weekday())

def month_for_date(month):
    return month - datetime.timedelta(days=month.day-1)

def year_for_date(year):
    return datetime.date(year.year, 01, 01)

def get_previous_month(date):
    if date.month == 1:
        month_change = 12
    else:
        month_change = date.month - 1
    new = date

    return new.replace(month=month_change)

def get_previous_year(date):
    new = date
    return new.replace(year=new.year-1)


########NEW FILE########
__FILENAME__ = views

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext

@login_required
def metric_report_view(request):
    return render_to_response('app_metrics/reports.html', {}, context_instance=RequestContext(request))




########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-app-metrics documentation build configuration file, created by
# sphinx-quickstart on Mon Nov 28 13:08:26 2011.
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

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
# extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-app-metrics'
copyright = u'2011, Frank Wiles'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.8.0'
# The full version, including alpha/beta/rc tags.
release = '0.8.0'

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
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    html_theme = 'default'
else:
    html_theme = 'sphinxdoc'

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
htmlhelp_basename = 'django-app-metricsdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-app-metrics.tex', u'django-app-metrics Documentation',
   u'Frank Wiles', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-app-metrics', u'django-app-metrics Documentation',
     [u'Frank Wiles'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-app-metrics', u'django-app-metrics Documentation',
   u'Frank Wiles', 'django-app-metrics', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
