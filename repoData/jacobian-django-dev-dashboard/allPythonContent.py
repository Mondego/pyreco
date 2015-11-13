__FILENAME__ = admin
from __future__ import absolute_import

from django.contrib import admin
from .models import Category, Metric, Datum

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    list_editable = ('position',)
    ordering = ('position',)

admin.site.register(Category, CategoryAdmin)

class MetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'position', 'show_on_dashboard', 'show_sparkline', 'period')
    list_editable = ('show_on_dashboard', 'category', 'position', 'show_sparkline', 'period')
    ordering = ('category__position', 'position')
    prepopulated_fields = {'slug': ['name']}

for MC in Metric.__subclasses__():
    admin.site.register(MC, MetricAdmin)

admin.site.register(Datum,
    list_display = ('timestamp', 'metric', 'measurement'),
)

########NEW FILE########
__FILENAME__ = update_metrics
from __future__ import absolute_import, print_function

from django.core.management.base import NoArgsCommand
from ...models import Metric

class Command(NoArgsCommand):
    
    def handle_noargs(self, **options):
        verbose = int(options.get('verbosity', 0))
        for MC in Metric.__subclasses__():
            for metric in MC.objects.all():
                if verbose:
                    print("Updating %s ... " % metric.name.lower(), end="")
                datum = metric.data.create(measurement=metric.fetch())
                if verbose:
                    print(datum.measurement)
########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.utils.http import urlquote
from django.shortcuts import redirect

class CanonicalDomainMiddleware(object):
    """
    Force-redirect to settings.CANONICAL_HOSTNAME if that's not the domain
    being accessed. If the setting isn't set, do nothing.
    """
    def __init__(self):
        try:
            self.canonical_hostname = settings.CANONICAL_HOSTNAME
        except AttributeError:
            raise MiddlewareNotUsed("settings.CANONICAL_HOSTNAME is undefined")

    def process_request(self, request):
        if request.get_host() == self.canonical_hostname:
            return

        # Domains didn't match, so do some fixups.
        new_url = [
            'https' if request.is_secure() else 'http',
            '://',
            self.canonical_hostname,
            urlquote(request.path),
            '?%s' % request.GET.urlencode() if request.GET else ''
        ]
        return redirect(''.join(new_url), permanent=True)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'TracTicketMetric'
        db.create_table('dashboard_tracticketmetric', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('query', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('dashboard', ['TracTicketMetric'])

        # Adding model 'Datum'
        db.create_table('dashboard_datum', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('measurement', self.gf('django.db.models.fields.BigIntegerField')()),
        ))
        db.send_create_signal('dashboard', ['Datum'])


    def backwards(self, orm):
        
        # Deleting model 'TracTicketMetric'
        db.delete_table('dashboard_tracticketmetric')

        # Deleting model 'Datum'
        db.delete_table('dashboard_datum')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0002_add_show_flag
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'TracTicketMetric.show_on_dashboard'
        db.add_column('dashboard_tracticketmetric', 'show_on_dashboard', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'TracTicketMetric.show_on_dashboard'
        db.delete_column('dashboard_tracticketmetric', 'show_on_dashboard')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0003_add_sparkline_flag
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'TracTicketMetric.show_sparkline'
        db.add_column('dashboard_tracticketmetric', 'show_sparkline', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'TracTicketMetric.show_sparkline'
        db.delete_column('dashboard_tracticketmetric', 'show_sparkline')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0004_add_rss_metric
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'RSSFeedMetric'
        db.create_table('dashboard_rssfeedmetric', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('show_on_dashboard', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('show_sparkline', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('feed_url', self.gf('django.db.models.fields.URLField')(max_length=1000)),
            ('link_url', self.gf('django.db.models.fields.URLField')(max_length=1000)),
        ))
        db.send_create_signal('dashboard', ['RSSFeedMetric'])


    def backwards(self, orm):
        
        # Deleting model 'RSSFeedMetric'
        db.delete_table('dashboard_rssfeedmetric')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.rssfeedmetric': {
            'Meta': {'object_name': 'RSSFeedMetric'},
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0005_add_period_field
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'RSSFeedMetric.period'
        db.add_column('dashboard_rssfeedmetric', 'period', self.gf('django.db.models.fields.CharField')(default='instant', max_length=15), keep_default=False)

        # Adding field 'TracTicketMetric.period'
        db.add_column('dashboard_tracticketmetric', 'period', self.gf('django.db.models.fields.CharField')(default='instant', max_length=15), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'RSSFeedMetric.period'
        db.delete_column('dashboard_rssfeedmetric', 'period')

        # Deleting field 'TracTicketMetric.period'
        db.delete_column('dashboard_tracticketmetric', 'period')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.rssfeedmetric': {
            'Meta': {'object_name': 'RSSFeedMetric'},
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0006_add_units
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'RSSFeedMetric.unit'
        db.add_column('dashboard_rssfeedmetric', 'unit', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True), keep_default=False)

        # Adding field 'RSSFeedMetric.unit_plural'
        db.add_column('dashboard_rssfeedmetric', 'unit_plural', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True), keep_default=False)

        # Adding field 'TracTicketMetric.unit'
        db.add_column('dashboard_tracticketmetric', 'unit', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True), keep_default=False)

        # Adding field 'TracTicketMetric.unit_plural'
        db.add_column('dashboard_tracticketmetric', 'unit_plural', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'RSSFeedMetric.unit'
        db.delete_column('dashboard_rssfeedmetric', 'unit')

        # Deleting field 'RSSFeedMetric.unit_plural'
        db.delete_column('dashboard_rssfeedmetric', 'unit_plural')

        # Deleting field 'TracTicketMetric.unit'
        db.delete_column('dashboard_tracticketmetric', 'unit')

        # Deleting field 'TracTicketMetric.unit_plural'
        db.delete_column('dashboard_tracticketmetric', 'unit_plural')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.rssfeedmetric': {
            'Meta': {'object_name': 'RSSFeedMetric'},
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'unit': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'unit': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0007_set_units
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        orm.TracTicketMetric.objects.all().update(unit="ticket", unit_plural="tickets")
        orm.RSSFeedMetric.objects.all().update(unit="commit", unit_plural="commits")

    def backwards(self, orm):
        pass

    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.rssfeedmetric': {
            'Meta': {'object_name': 'RSSFeedMetric'},
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'unit': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'unit': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0008_add_githubitemcountmetric
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'GithubItemCountMetric'
        db.create_table('dashboard_githubitemcountmetric', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('show_on_dashboard', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('show_sparkline', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('period', self.gf('django.db.models.fields.CharField')(default='instant', max_length=15)),
            ('unit', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('unit_plural', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('api_url', self.gf('django.db.models.fields.URLField')(max_length=1000)),
            ('link_url', self.gf('django.db.models.fields.URLField')(max_length=1000)),
        ))
        db.send_create_signal('dashboard', ['GithubItemCountMetric'])

    def backwards(self, orm):
        # Deleting model 'GithubItemCountMetric'
        db.delete_table('dashboard_githubitemcountmetric')

    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.githubitemcountmetric': {
            'Meta': {'object_name': 'GithubItemCountMetric'},
            'api_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.rssfeedmetric': {
            'Meta': {'object_name': 'RSSFeedMetric'},
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['dashboard']
########NEW FILE########
__FILENAME__ = 0009_add_jenkinsfailuresmetric
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'JenkinsFailuresMetric'
        db.create_table('dashboard_jenkinsfailuresmetric', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('show_on_dashboard', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('show_sparkline', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('period', self.gf('django.db.models.fields.CharField')(default='instant', max_length=15)),
            ('unit', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('unit_plural', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('jenkins_root_url', self.gf('django.db.models.fields.URLField')(max_length=1000)),
            ('build_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('is_success_cnt', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_percentage', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('dashboard', ['JenkinsFailuresMetric'])

    def backwards(self, orm):
        # Deleting model 'JenkinsFailuresMetric'
        db.delete_table('dashboard_jenkinsfailuresmetric')

    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.githubitemcountmetric': {
            'Meta': {'object_name': 'GithubItemCountMetric'},
            'api_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.jenkinsfailuresmetric': {
            'Meta': {'object_name': 'JenkinsFailuresMetric'},
            'build_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_percentage': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_success_cnt': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'jenkins_root_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.rssfeedmetric': {
            'Meta': {'object_name': 'RSSFeedMetric'},
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['dashboard']
########NEW FILE########
__FILENAME__ = 0010_add_categories
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Category'
        db.create_table('dashboard_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('position', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1)),
        ))
        db.send_create_signal('dashboard', ['Category'])

        # Adding field 'JenkinsFailuresMetric.category'
        db.add_column('dashboard_jenkinsfailuresmetric', 'category',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dashboard.Category'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'JenkinsFailuresMetric.position'
        db.add_column('dashboard_jenkinsfailuresmetric', 'position',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1),
                      keep_default=False)

        # Adding field 'GithubItemCountMetric.category'
        db.add_column('dashboard_githubitemcountmetric', 'category',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dashboard.Category'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'GithubItemCountMetric.position'
        db.add_column('dashboard_githubitemcountmetric', 'position',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1),
                      keep_default=False)

        # Adding field 'RSSFeedMetric.category'
        db.add_column('dashboard_rssfeedmetric', 'category',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dashboard.Category'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'RSSFeedMetric.position'
        db.add_column('dashboard_rssfeedmetric', 'position',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1),
                      keep_default=False)

        # Adding field 'TracTicketMetric.category'
        db.add_column('dashboard_tracticketmetric', 'category',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dashboard.Category'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'TracTicketMetric.position'
        db.add_column('dashboard_tracticketmetric', 'position',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=1),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting model 'Category'
        db.delete_table('dashboard_category')

        # Deleting field 'JenkinsFailuresMetric.category'
        db.delete_column('dashboard_jenkinsfailuresmetric', 'category_id')

        # Deleting field 'JenkinsFailuresMetric.position'
        db.delete_column('dashboard_jenkinsfailuresmetric', 'position')

        # Deleting field 'GithubItemCountMetric.category'
        db.delete_column('dashboard_githubitemcountmetric', 'category_id')

        # Deleting field 'GithubItemCountMetric.position'
        db.delete_column('dashboard_githubitemcountmetric', 'position')

        # Deleting field 'RSSFeedMetric.category'
        db.delete_column('dashboard_rssfeedmetric', 'category_id')

        # Deleting field 'RSSFeedMetric.position'
        db.delete_column('dashboard_rssfeedmetric', 'position')

        # Deleting field 'TracTicketMetric.category'
        db.delete_column('dashboard_tracticketmetric', 'category_id')

        # Deleting field 'TracTicketMetric.position'
        db.delete_column('dashboard_tracticketmetric', 'position')

    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.category': {
            'Meta': {'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'})
        },
        'dashboard.datum': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Datum'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'measurement': ('django.db.models.fields.BigIntegerField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        'dashboard.githubitemcountmetric': {
            'Meta': {'object_name': 'GithubItemCountMetric'},
            'api_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dashboard.Category']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.jenkinsfailuresmetric': {
            'Meta': {'object_name': 'JenkinsFailuresMetric'},
            'build_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dashboard.Category']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_percentage': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_success_cnt': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'jenkins_root_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.rssfeedmetric': {
            'Meta': {'object_name': 'RSSFeedMetric'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dashboard.Category']", 'null': 'True', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_url': ('django.db.models.fields.URLField', [], {'max_length': '1000'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dashboard.tracticketmetric': {
            'Meta': {'object_name': 'TracTicketMetric'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dashboard.Category']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'period': ('django.db.models.fields.CharField', [], {'default': "'instant'", 'max_length': '15'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'query': ('django.db.models.fields.TextField', [], {}),
            'show_on_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'show_sparkline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit_plural': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['dashboard']
########NEW FILE########
__FILENAME__ = models
import ast
import datetime
import xmlrpclib
import feedparser
import calendar
import requests
from django.conf import settings
from django.contrib.contenttypes.generic import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models, connections

METRIC_PERIOD_INSTANT = 'instant'
METRIC_PERIOD_DAILY = 'daily'
METRIC_PERIOD_WEEKLY = 'weekly'
METRIC_PERIOD_CHOICES = (
    (METRIC_PERIOD_INSTANT, 'Instant'),
    (METRIC_PERIOD_DAILY, 'Daily'),
    (METRIC_PERIOD_WEEKLY, 'Weekly'),
)

class Category(models.Model):
    name = models.CharField(max_length=300)
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name_plural = 'categories'

    def __unicode__(self):
        return self.name

class Metric(models.Model):
    name = models.CharField(max_length=300)
    slug = models.SlugField()
    category = models.ForeignKey(Category, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    position = models.PositiveSmallIntegerField(default=1)
    data = GenericRelation('Datum')
    show_on_dashboard = models.BooleanField(default=True)
    show_sparkline = models.BooleanField(default=True)
    period = models.CharField(max_length=15, choices=METRIC_PERIOD_CHOICES,
                              default=METRIC_PERIOD_INSTANT)
    unit = models.CharField(max_length=100)
    unit_plural = models.CharField(max_length=100)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ("metric-detail", [self.slug])

    @property
    def display_position(self):
        cat_position = -1 if self.category is None else self.category.position
        return cat_position, self.position

    def gather_data(self, since):
        """
        Gather all the data from this metric since a given date.

        Returns a list of (timestamp, value) tuples. The timestamp is a Unix
        timestamp, coverted from localtime to UTC.
        """
        if self.period == METRIC_PERIOD_INSTANT:
            return self._gather_data_instant(since)
        elif self.period == METRIC_PERIOD_DAILY:
            return self._gather_data_periodic(since, 'day')
        elif self.period == METRIC_PERIOD_WEEKLY:
            return self._gather_data_periodic(since, 'week')
        else:
            raise ValueError("Unknown period: %s", self.period)

    def _gather_data_instant(self, since):
        """
        Gather data from an "instant" metric.

        Instant metrics change every time we measure them, so they're easy:
        just return every single measurement.
        """
        data = self.data.filter(timestamp__gt=since) \
                        .order_by('timestamp') \
                        .values_list('timestamp', 'measurement')
        return [(calendar.timegm(t.timetuple()), m) for (t, m) in data]

    def _gather_data_periodic(self, since, period):
        """
        Gather data from "periodic" merics.

        Period metrics are reset every day/week/month and count up as the period
        goes on. Think "commits today" or "new tickets this week".

        XXX I'm not completely sure how to deal with this since time zones wreak
        havoc, so there's right now a hard-coded offset which doesn't really
        scale but works for now.
        """
        OFFSET = "2 hours" # HACK!
        ctid = ContentType.objects.get_for_model(self).id

        c = connections['default'].cursor()
        c.execute('''SELECT
                        DATE_TRUNC(%s, timestamp - INTERVAL %s),
                        MAX(measurement)
                     FROM dashboard_datum
                     WHERE content_type_id = %s
                       AND object_id = %s
                       AND timestamp >= %s
                     GROUP BY 1;''', [period, OFFSET, ctid, self.id, since])
        return [(calendar.timegm(t.timetuple()), float(m)) for (t, m) in c.fetchall()]

class TracTicketMetric(Metric):
    query = models.TextField()

    def __unicode__(self):
        return self.name

    def fetch(self):
        s = xmlrpclib.ServerProxy(settings.TRAC_RPC_URL)
        return len(s.ticket.query(self.query + "&max=0"))

    def link(self):
        return "%squery?%s&desc=1&order=changetime" % (settings.TRAC_URL, self.query)

class RSSFeedMetric(Metric):
    feed_url = models.URLField(max_length=1000)
    link_url = models.URLField(max_length=1000)

    def fetch(self):
        return len(feedparser.parse(self.feed_url).entries)

    def link(self):
        return self.link_url

class GithubItemCountMetric(Metric):
    """Example: https://api.github.com/repos/django/django/pulls?state=open"""
    api_url = models.URLField(max_length=1000)
    link_url = models.URLField(max_length=1000)

    def fetch(self):
        """
        Request the specified GitHub API URL with 100 items per page. Loop over
        the pages until no page left. Return total item count.
        """
        count = 0
        page = 1
        while True:
            r = requests.get(self.api_url, params={
                'page': page, 'per_page': 100
            })
            c = len(r.json)
            count += c
            page += 1
            if c < 100:
                break
        return count

    def link(self):
        return self.link_url

class JenkinsFailuresMetric(Metric):
    """
    Track failures of a job/build. Uses the Python flavor of the Jenkins REST
    API.
    """
    jenkins_root_url = models.URLField(
        verbose_name='Jenkins instance root URL',
        max_length=1000,
        help_text='E.g. http://ci.djangoproject.com/',
    )
    build_name = models.CharField(
        max_length=100,
        help_text='E.g. Django Python3',
    )
    is_success_cnt = models.BooleanField(
        verbose_name='Should the metric be a value representing success ratio?',
        help_text='E.g. if there are 50 tests of which 30 are failing the value of this metric will be 20 (or 40%.)',
    )
    is_percentage = models.BooleanField(
        verbose_name='Should the metric be a percentage value?',
        help_text='E.g. if there are 50 tests of which 30 are failing the value of this metric will be 60%.',
    )

    def urljoin(self, *parts):
        return '/'.join(p.strip('/') for p in parts)

    def _fetch(self):
        """
        Actually get the values we are interested in by using the Jenkins REST
        API (https://wiki.jenkins-ci.org/display/JENKINS/Remote+access+API)
        """
        api_url = self.urljoin(self.link(), 'api/python')
        job_desc = requests.get(api_url)
        job_dict = ast.literal_eval(job_desc.text)
        build_ptr_dict = job_dict['lastCompletedBuild']
        build_url = self.urljoin(build_ptr_dict['url'], 'api/python')
        build_desc = requests.get(build_url)
        build_dict = ast.literal_eval(build_desc.text)
        return (build_dict['actions'][4]['failCount'], build_dict['actions'][4]['totalCount'])

    def _calculate(self, failures, total):
        """Calculate the metric value."""
        if self.is_success_cnt:
            value = total - failures
        else:
            value = failures
        if self.is_percentage:
            if not total:
                return 0
            value = (value * 100)/total
        return value

    def fetch(self):
        failures, total = self._fetch()
        return self._calculate(failures, total)

    def link(self):
        return self.urljoin(self.jenkins_root_url, 'job', self.build_name)

class Datum(models.Model):
    metric = GenericForeignKey()
    content_type = models.ForeignKey(ContentType, related_name='+')
    object_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField(default=datetime.datetime.now)
    measurement = models.BigIntegerField()

    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'
        verbose_name_plural = 'data'

    def __unicode__(self):
        return "%s at %s: %s" % (self.metric, self.timestamp, self.measurement)

########NEW FILE########
__FILENAME__ = base
import os
from unipath import FSPath as Path

PROJECT_DIR = Path(__file__).absolute().ancestor(3)

#
# My settings
#

TRAC_CREDS = os.environ['TRAC_CREDS']  # Set to "user:pass" for Trac.
TRAC_RPC_URL = "https://%s@code.djangoproject.com/login/rpc" % TRAC_CREDS
TRAC_URL = "https://code.djangoproject.com/"

#
# Django settings follow...
#

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True

MEDIA_ROOT = PROJECT_DIR.child('media')
MEDIA_URL = '/media/'

STATIC_ROOT = PROJECT_DIR.child('static_root')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    str(PROJECT_DIR.child('static')),
)
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = "c55c3faa-6c32-11e0-818b-c7ea0e354dc2"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    PROJECT_DIR.child('templates'),
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'south',
    'dashboard',
]

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
__FILENAME__ = heroku
import os
import urlparse
from .base import *

# Heroku needs Gunicorn specifically.
INSTALLED_APPS += ['gunicorn']

SECRET_KEY = os.environ['SECRET_KEY']

#
# Now lock this sucker down.
#
INSTALLED_APPS += ['djangosecure']
MIDDLEWARE_CLASSES.insert(0, 'djangosecure.middleware.SecurityMiddleware')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_FRAME_DENY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# The header Heroku uses to indicate SSL:
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Canoncalize on "dashboard.djangoproject.com"
MIDDLEWARE_CLASSES.insert(0, 'dashboard.middleware.CanonicalDomainMiddleware')
CANONICAL_HOSTNAME = 'dashboard.djangoproject.com'

#
# Store files on S3, pulling config from os.environ.
#
DEFAULT_FILE_STORAGE = STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
AWS_S3_SECURE_URLS = True
AWS_QUERYSTRING_AUTH = False

#
# Pull the various config info from Heroku.
# Heroku adds some of this automatically if we're using a simple settings.py,
# but we're not and it's just as well -- I like doing this by hand.
#

# Make sure urlparse understands custom config schemes.
urlparse.uses_netloc.append('postgres')
urlparse.uses_netloc.append('redis')

# Grab database info
db_url = urlparse.urlparse(os.environ['DATABASE_URL'])
DATABASES = {
    'default': {
        'ENGINE':  'django.db.backends.postgresql_psycopg2',
        'NAME':     db_url.path[1:],
        'USER':     db_url.username,
        'PASSWORD': db_url.password,
        'HOST':     db_url.hostname,
        'PORT':     db_url.port,
    }
}

# Now do redis and the cache.
redis_url = urlparse.urlparse(os.environ['REDISTOGO_URL'])
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '{0}:{1}'.format(redis_url.hostname, redis_url.port),
        'OPTIONS': {
            'DB': 0,
            'PASSWORD': redis_url.password,
        },
        'VERSION': os.environ.get('CACHE_VERSION', 0),
    },
}

# Use Sentry for debugging if available.
if 'SENTRY_DSN' in os.environ:
    INSTALLED_APPS += ["raven.contrib.django"]

########NEW FILE########
__FILENAME__ = local
from __future__ import absolute_import
from .base import *

DEBUG = TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'djdash',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
}

try:
    import debug_toolbar
except ImportError:
    pass
else:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE_CLASSES += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import
import datetime
import operator
from django import http
from django.conf import settings
from django.shortcuts import render
from django.utils import simplejson
from django.forms.models import model_to_dict
from django.views.decorators.cache import cache_page
from .models import Metric

TEN_MINUTES = 60 * 10

@cache_page(TEN_MINUTES)
def index(request):
    metrics = []
    for MC in Metric.__subclasses__():
        metrics.extend(MC.objects.filter(show_on_dashboard=True))
    metrics = sorted(metrics, key=operator.attrgetter('display_position'))

    data = []
    for metric in metrics:
        latest = metric.data.latest()
        data.append({'metric': metric, 'latest': latest})
    return render(request, 'dashboard/index.html', {'data': data})

@cache_page(TEN_MINUTES)
def metric_detail(request, metric_slug):
    metric = _find_metric(metric_slug)
    return render(request, 'dashboard/detail.html', {
        'metric': metric,
        'latest': metric.data.latest(),
    })

@cache_page(TEN_MINUTES)
def metric_json(request, metric_slug):
    metric = _find_metric(metric_slug)

    try:
        daysback = int(request.GET['days'])
    except (TypeError, KeyError, ValueError):
        daysback = 30
    d = datetime.datetime.now() - datetime.timedelta(days=daysback)

    doc = model_to_dict(metric)
    doc['data'] = metric.gather_data(since=d)

    return http.HttpResponse(
        simplejson.dumps(doc, indent = 2 if settings.DEBUG else None),
        content_type = "application/json",
    )

def _find_metric(slug):
    for MC in Metric.__subclasses__():
        try:
            return MC.objects.get(slug=slug)
        except MC.DoesNotExist:
            continue
    raise http.Http404()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dashboard.settings.local")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url('^$',                       'dashboard.views.index',            name="dashboard-index"),
    url('^metric/([\w-]+)/$',       'dashboard.views.metric_detail',    name="metric-detail"),
    url('^metric/([\w-]+).json$',   'dashboard.views.metric_json',      name="metric-json"),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
