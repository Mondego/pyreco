__FILENAME__ = admin
from django.contrib import admin

from models import ErrorReport

class ErrorReportAdmin(admin.ModelAdmin):
    search_fields = ('message',
                     'url',
                     'user_agent',
                     'data')
    date_hierarchy = 'reported_at'
    list_display = ('reported_at', 
                    'message', 
                    'url', 
                    'line_number',
                    'user_agent',
                    'remote_addr')

admin.site.register(ErrorReport, ErrorReportAdmin)

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm

from models import ErrorReport

class ErrorReportForm(ModelForm):
    
    class Meta:
        fields = ('message', 'url', 'line_number',)
        model = ErrorReport

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ErrorReport'
        db.create_table('jhouston_errorreport', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('reported_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=255)),
            ('line_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('user_agent', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('remote_addr', self.gf('django.db.models.fields.IPAddressField')(max_length=15, blank=True)),
            ('data', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('jhouston', ['ErrorReport'])


    def backwards(self, orm):
        
        # Deleting model 'ErrorReport'
        db.delete_table('jhouston_errorreport')


    models = {
        'jhouston.errorreport': {
            'Meta': {'object_name': 'ErrorReport'},
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'remote_addr': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'blank': 'True'}),
            'reported_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255'}),
            'user_agent': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['jhouston']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_errorreport_url__chg_field_errorreport_user_agent
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'ErrorReport.url'
        db.alter_column('jhouston_errorreport', 'url', self.gf('django.db.models.fields.TextField')())

        # Changing field 'ErrorReport.user_agent'
        db.alter_column('jhouston_errorreport', 'user_agent', self.gf('django.db.models.fields.TextField')())


    def backwards(self, orm):
        
        # Changing field 'ErrorReport.url'
        db.alter_column('jhouston_errorreport', 'url', self.gf('django.db.models.fields.URLField')(max_length=255))

        # Changing field 'ErrorReport.user_agent'
        db.alter_column('jhouston_errorreport', 'user_agent', self.gf('django.db.models.fields.CharField')(max_length=255))


    models = {
        'jhouston.errorreport': {
            'Meta': {'object_name': 'ErrorReport'},
            'data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'remote_addr': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'blank': 'True'}),
            'reported_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {}),
            'user_agent': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['jhouston']

########NEW FILE########
__FILENAME__ = models
from django.db import models

class ErrorReport(models.Model):
    message = models.TextField(blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    # Ideally, URLField(max_length=1024) would be used.  However,
    # MySQL has a max_length limitation of 255 for URLField.
    url = models.TextField()
    line_number = models.PositiveIntegerField()
    user_agent = models.TextField()
    remote_addr = models.IPAddressField(blank=True)
    data = models.TextField(blank=True)

    

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
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^onerror/$', views.onerror)
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from forms import ErrorReportForm

@csrf_exempt
def onerror(request):
    if request.method != 'POST':
        ret = HttpResponse(content="Sorry, we accept POST only", status=400)
    else:
        form = ErrorReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.remote_addr = request.META['REMOTE_ADDR']
            report.user_agent = request.META['HTTP_USER_AGENT']
            report.save()
            ret = HttpResponse(content='Thanks for reporting', 
                               status=201)
        else:
            ret = HttpResponse(content=form._errors, status=400)
    return ret


########NEW FILE########
