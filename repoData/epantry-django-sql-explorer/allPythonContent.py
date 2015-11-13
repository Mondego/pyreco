__FILENAME__ = actions
import tempfile
from zipfile import ZipFile
from datetime import date
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from collections import defaultdict
from explorer.utils import csv_report

_ = lambda x: x


def generate_report_action(description="Generate CSV file from SQL query",):

    def generate_report(modeladmin, request, queryset):
        results = [report for report in queryset if report.passes_blacklist()]
        queries = (len(results) > 0 and _package(results)) or defaultdict(int)
        response = HttpResponse(queries["data"], content_type=queries["content_type"])
        response['Content-Disposition'] = queries["filename"]
        response['Content-Length'] = queries["length"]
        return response
    
    generate_report.short_description = description
    return generate_report


def _package(queries):
    ret = {}
    is_one = len(queries) == 1
    name_root = lambda n: "attachment; filename=%s" % n
    ret["content_type"] = (is_one and 'text/csv') or 'application/zip'
    ret["filename"] = (is_one and name_root('%s.csv' % queries[0].title.replace(',', ''))) or name_root("Report_%s.zip" % date.today())
    ret["data"] = (is_one and csv_report(queries[0])) or _build_zip(queries)
    ret["length"] = (is_one and len(ret["data"]) or ret["data"].blksize)
    return ret


def _build_zip(queries):
    temp = tempfile.TemporaryFile()
    zip_file = ZipFile(temp, 'w')
    map(lambda r: zip_file.writestr('%s.csv' % r.title, csv_report(r) or "Error!"), queries)
    zip_file.close()
    ret = FileWrapper(temp)
    temp.seek(0)
    return ret

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from explorer.models import Query
from explorer.actions import generate_report_action


class QueryAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'created_by_user',)
    list_filter = ('title',)
    
    actions = [generate_report_action()]

admin.site.register(Query, QueryAdmin)

########NEW FILE########
__FILENAME__ = app_settings
from django.conf import settings

EXPLORER_SQL_BLACKLIST = getattr(settings, 'EXPLORER_SQL_BLACKLIST', ('ALTER', 'RENAME ', 'DROP', 'TRUNCATE', 'INSERT INTO', 'UPDATE', 'REPLACE', 'DELETE', 'ALTER', 'CREATE TABLE', 'SCHEMA', 'GRANT', 'OWNER TO'))

EXPLORER_SQL_WHITELIST = getattr(settings, 'EXPLORER_SQL_WHITELIST', ('CREATED', 'DELETED'))

EXPLORER_DEFAULT_ROWS = getattr(settings, 'EXPLORER_DEFAULT_ROWS', 100)

EXPLORER_SCHEMA_EXCLUDE_APPS = getattr(settings, 'EXPLORER_SCHEMA_EXCLUDE_APPS', ('django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.admin'))

EXPLORER_CONNECTION_NAME = getattr(settings, 'EXPLORER_CONNECTION_NAME', None)

EXPLORER_TRANSFORMS = getattr(settings, 'EXPLORER_TRANSFORMS', [])

EXPLORER_PERMISSION_VIEW = getattr(settings, 'EXPLORER_PERMISSION_VIEW', lambda u: u.is_staff)

EXPLORER_PERMISSION_CHANGE = getattr(settings, 'EXPLORER_PERMISSION_CHANGE', lambda u: u.is_staff)

EXPLORER_RECENT_QUERY_COUNT = getattr(settings, 'EXPLORER_RECENT_QUERY_COUNT', 10)
########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm, Field, ValidationError
from explorer.models import Query

_ = lambda x: x


class SqlField(Field):

    def validate(self, value):
        query = Query(sql=value)
        if not query.available_params():
            error = query.error_messages()
            if error:
                raise ValidationError(
                    _(error),
                    params={'value': value},
                    code="InvalidSql"
                )


class QueryForm(ModelForm):

    sql = SqlField()

    def clean(self):
        if self.instance and self.data.get('created_by_user', None):
            self.cleaned_data['created_by_user'] = self.instance.created_by_user
        return super(QueryForm, self).clean()

    class Meta:
        model = Query
        fields = ['title', 'sql', 'description', 'created_by_user']
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Query'
        db.create_table(u'explorer_query', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('sql', self.gf('django.db.models.fields.TextField')()),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'explorer', ['Query'])


    def backwards(self, orm):
        # Deleting model 'Query'
        db.delete_table(u'explorer_query')


    models = {
        u'explorer.query': {
            'Meta': {'ordering': "['title']", 'object_name': 'Query'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sql': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['explorer']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_query_last_run_date
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Query.last_run_date'
        db.add_column(u'explorer_query', 'last_run_date',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, default=datetime.datetime(2014, 3, 15, 0, 0), blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Query.last_run_date'
        db.delete_column(u'explorer_query', 'last_run_date')


    models = {
        u'explorer.query': {
            'Meta': {'ordering': "['title']", 'object_name': 'Query'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sql': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['explorer']
########NEW FILE########
__FILENAME__ = 0003_auto__del_field_query_created_by__add_field_query_created_by_user
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings


user_model = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Query.created_by'
        db.delete_column(u'explorer_query', 'created_by')

        # Adding field 'Query.created_by_user'
        db.add_column(u'explorer_query', 'created_by_user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_model], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Query.created_by'
        db.add_column(u'explorer_query', 'created_by',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Query.created_by_user'
        db.delete_column(u'explorer_query', 'created_by_user_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        user_model: {
            'Meta': {'object_name': user_model.split(".")[1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'explorer.query': {
            'Meta': {'ordering': "['title']", 'object_name': 'Query'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sql': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['explorer']
########NEW FILE########
__FILENAME__ = 0004_auto__add_querylog
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings


user_model = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'QueryLog'
        db.create_table(u'explorer_querylog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sql', self.gf('django.db.models.fields.TextField')()),
            ('query', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['explorer.Query'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('is_playground', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('run_by_user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_model], null=True, blank=True)),
            ('run_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'explorer', ['QueryLog'])


    def backwards(self, orm):
        # Deleting model 'QueryLog'
        db.delete_table(u'explorer_querylog')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        user_model: {
            'Meta': {'object_name': user_model.split(".")[1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'explorer.query': {
            'Meta': {'ordering': "['title']", 'object_name': 'Query'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sql': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'explorer.querylog': {
            'Meta': {'object_name': 'QueryLog'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_playground': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'query': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['explorer.Query']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'run_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'run_by_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'sql': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['explorer']
########NEW FILE########
__FILENAME__ = models
from explorer.utils import passes_blacklist, write_csv, swap_params, execute_query, execute_and_fetch_query, extract_params, shared_dict_update
from django.db import models, DatabaseError
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

MSG_FAILED_BLACKLIST = "Query failed the SQL blacklist."


class Query(models.Model):
    title = models.CharField(max_length=255)
    sql = models.TextField()
    description = models.TextField(null=True, blank=True)
    created_by_user = models.ForeignKey(get_user_model(), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_run_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        verbose_name_plural = 'Queries'

    def __unicode__(self):
        return unicode(self.title)

    def passes_blacklist(self, params=None):
        return passes_blacklist(self.final_sql(params=params))

    def final_sql(self, params=None):
        return swap_params(self.sql, params)

    def error_messages(self):
        if not self.passes_blacklist():
            return MSG_FAILED_BLACKLIST
        try:
            execute_query(self.final_sql())
            return None
        except DatabaseError, e:
            return str(e)

    def headers_and_data(self, params=None):
        if not self.passes_blacklist(params):
            return [], [], None, MSG_FAILED_BLACKLIST
        try:
            return execute_and_fetch_query(self.final_sql(params))
        except (DatabaseError, Warning), e:
            return [], [], None, str(e)

    def available_params(self, param_values=None):
        p = extract_params(self.sql)
        if param_values:
            shared_dict_update(p, param_values)
        return p

    def get_absolute_url(self):
        return reverse("query_detail", kwargs={'query_id': self.id})

    def log(self, user):
        log_entry = QueryLog(sql=self.sql, query_id=self.id, run_by_user=user, is_playground=not bool(self.id))
        log_entry.save()


class QueryLog(models.Model):

    sql = models.TextField()
    query = models.ForeignKey(Query, null=True, blank=True, on_delete=models.SET_NULL)
    is_playground = models.BooleanField(default=False)
    run_by_user = models.ForeignKey(get_user_model(), null=True, blank=True)
    run_at = models.DateTimeField(auto_now_add=True)
########NEW FILE########
__FILENAME__ = factories
import factory
from explorer import models


class SimpleQueryFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Query

    title = "My simple query"
    sql = "SELECT 1+1 AS TWO"  # same result in postgres and sqlite
    description = "Doin' math"
    created_by_user_id = 1
########NEW FILE########
__FILENAME__ = test_actions
from django.test import TestCase
from explorer.actions import generate_report_action
from explorer.tests.factories import SimpleQueryFactory
from explorer.utils import csv_report
import StringIO
from zipfile import ZipFile


class testSqlQueryActions(TestCase):

    def test_simple_query_runs(self):

        expected_csv = 'two\r\n2\r\n'

        r = SimpleQueryFactory()
        result = csv_report(r)

        self.assertIsNotNone(result, "Query '%s' returned None." % r.title)
        self.assertEqual(result.lower(), expected_csv)

    def test_single_query_is_csv_file(self):
        expected_csv = 'two\r\n2\r\n'

        r = SimpleQueryFactory()
        fn = generate_report_action()
        result = fn(None, None, [r, ])
        self.assertEqual(result.content.lower(), expected_csv)

    def test_multiple_queries_are_zip_file(self):

        expected_csv = 'two\r\n2\r\n'

        q = SimpleQueryFactory()
        q2 = SimpleQueryFactory()
        fn = generate_report_action()
        res = fn(None, None, [q, q2])
        z = ZipFile(StringIO.StringIO(res.content))
        got_csv = z.read(z.namelist()[0])

        self.assertEqual(len(z.namelist()), 2)
        self.assertEqual(z.namelist()[0], '%s.csv' % q.title)
        self.assertEqual(got_csv.lower(), expected_csv)

    # if commas are not removed from the filename, then Chrome throws "duplicate headers received from server"
    def test_packaging_removes_commas_from_file_name(self):

        expected = 'attachment; filename=query for x y.csv'
        q = SimpleQueryFactory(title='query for x, y')
        fn = generate_report_action()
        res = fn(None, None, [q])
        self.assertEqual(res['Content-Disposition'], expected)

########NEW FILE########
__FILENAME__ = test_forms
from django.test import TestCase
from django.forms.models import model_to_dict
from explorer.tests.factories import SimpleQueryFactory
from explorer.forms import QueryForm


class TestFormValidation(TestCase):

    def test_form_is_valid_with_valid_sql(self):
        q = SimpleQueryFactory(sql="select 1;", created_by_user_id=None)
        form = QueryForm(model_to_dict(q))
        self.assertTrue(form.is_valid())

    def test_form_is_not_valid_with_invalid_sql(self):
        q = SimpleQueryFactory(sql="select a;", created_by_user_id=None)
        form = QueryForm(model_to_dict(q))
        self.assertFalse(form.is_valid())

    def test_form_is_always_valid_with_params(self):
        q = SimpleQueryFactory(sql="select $$a$$;", created_by_user_id=None)
        q.params = {}
        form = QueryForm(model_to_dict(q))
        self.assertTrue(form.is_valid())
########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase
from explorer.tests.factories import SimpleQueryFactory
from explorer.tests.utils import AssertMethodIsCalled
from explorer.models import MSG_FAILED_BLACKLIST, QueryLog, Query


class TestQueryModel(TestCase):

    def test_blacklist_check_runs_before_execution(self):
        q = SimpleQueryFactory(sql='select 1;')
        with AssertMethodIsCalled(q, "passes_blacklist"):
            headers, data, duration, error = q.headers_and_data()

    def test_blacklist_prevents_bad_sql_from_executing(self):
        q = SimpleQueryFactory(sql='select 1 "delete";')
        headers, data, duration, error = q.headers_and_data()
        self.assertEqual(error, MSG_FAILED_BLACKLIST)

    def test_blacklist_prevents_bad_sql_with_params_from_executing(self):
        q = SimpleQueryFactory(sql="select '$$foo$$';")
        headers, data, duration, error = q.headers_and_data(params={"foo": "'; delete from *; select'"})
        self.assertEqual(error, MSG_FAILED_BLACKLIST)

    def test_params_get_merged(self):
        q = SimpleQueryFactory(sql="select '$$foo$$';")
        params = {'foo': 'bar', 'mux': 'qux'}
        self.assertEqual(q.available_params(params), {'foo': 'bar'})

    def test_query_log(self):
        self.assertEqual(0, QueryLog.objects.count())
        q = SimpleQueryFactory()
        q.log(None)
        self.assertEqual(1, QueryLog.objects.count())
        log = QueryLog.objects.first()
        self.assertEqual(log.run_by_user, None)
        self.assertEqual(log.query, q)
        self.assertFalse(log.is_playground)

    def test_playground_query_log(self):
        query = Query(sql='select 1;', title="Playground")
        query.log(None)
        log = QueryLog.objects.first()
        self.assertTrue(log.is_playground)
########NEW FILE########
__FILENAME__ = test_utils
from django.test import TestCase
from explorer.actions import generate_report_action
from explorer.tests.factories import SimpleQueryFactory
from explorer import app_settings
from explorer.utils import passes_blacklist, schema_info, param, swap_params, extract_params,\
    shared_dict_update, EXPLORER_PARAM_TOKEN, transform_row, get_transforms


class TestSqlBlacklist(TestCase):

    def setUp(self):
        self.orig = app_settings.EXPLORER_SQL_BLACKLIST

    def tearDown(self):
        app_settings.EXPLORER_SQL_BLACKLIST = self.orig

    def test_overriding_blacklist(self):
        app_settings.EXPLORER_SQL_BLACKLIST = []
        r = SimpleQueryFactory(sql="SELECT 1+1 AS \"DELETE\";")
        fn = generate_report_action()
        result = fn(None, None, [r, ])
        self.assertEqual(result.content, 'DELETE\r\n2\r\n')

    def test_default_blacklist_prevents_deletes(self):
        r = SimpleQueryFactory(sql="SELECT 1+1 AS \"DELETE\";")
        fn = generate_report_action()
        result = fn(None, None, [r, ])
        self.assertEqual(result.content, '0')

    def test_queries_deleting_stuff_are_not_ok(self):
        sql = "'distraction'; deLeTe from table; SELECT 1+1 AS TWO; drop view foo;"
        self.assertFalse(passes_blacklist(sql))

    def test_queries_dropping_views_is_not_ok_and_not_case_sensitive(self):
        sql = "SELECT 1+1 AS TWO; drop ViEw foo;"
        self.assertFalse(passes_blacklist(sql))


class TestSchemaInfo(TestCase):

    def test_schema_info_returns_valid_data(self):
        res = schema_info()
        tables = [a[1] for a in res]
        self.assertIn('explorer_query', tables)

    def test_app_exclusion_list(self):
        app_settings.EXPLORER_SCHEMA_EXCLUDE_APPS = ('explorer',)
        res = schema_info()
        app_settings.EXPLORER_SCHEMA_EXCLUDE_APPS = ('',)
        tables = [a[1] for a in res]
        self.assertNotIn('explorer_query', tables)


class TestParams(TestCase):

    def test_swappable_params_are_built_correctly(self):
        expected = EXPLORER_PARAM_TOKEN + 'foo' + EXPLORER_PARAM_TOKEN
        self.assertEqual(expected, param('foo'))

    def test_params_get_swapped(self):
        sql = 'please swap $$this$$ and $$that$$'
        expected = 'please swap here and there'
        params = {'this': 'here', 'that': 'there'}
        got = swap_params(sql, params)
        self.assertEqual(got, expected)

    def test_empty_params_does_nothing(self):
        sql = 'please swap $$this$$ and $$that$$'
        params = None
        got = swap_params(sql, params)
        self.assertEqual(got, sql)

    def test_non_string_param_gets_swapper(self):
        sql = 'please swap $$this$$'
        expected = 'please swap 1'
        params = {'this': 1}
        got = swap_params(sql, params)
        self.assertEqual(got, expected)

    def test_extracting_params(self):
        sql = 'please swap $$this$$'
        expected = {'this': ''}
        self.assertEqual(extract_params(sql), expected)

    def test_shared_dict_update(self):
        source = {'foo': 1, 'bar': 2}
        target = {'bar': None}  # ha ha!
        self.assertEqual({'bar': 2}, shared_dict_update(target, source))


class TestTransforms(TestCase):

    def test_transforms_are_identified_in_headers(self):
        headers = ['foo']
        transforms = [('foo', 'http://www.%s.com')]
        got = get_transforms(headers, transforms)
        self.assertEqual([(0, 'http://www.%s.com')], got)

    def test_transform_alters_row(self):
        headers = ['foo', 'bar']
        transforms = get_transforms(headers, [('bar', 'http://www.{0}.com')])
        row = [1, 2]
        got = transform_row(transforms, row)
        self.assertEqual([1, 'http://www.2.com'], got)

    def test_multiple_transforms(self):
        headers = ['foo', 'bar']
        transforms = get_transforms(headers, [('foo', '<a href="{0}">{0}</a>'),
                                              ('bar', 'x: {0}')])
        rows = [[1, 2], ['a', 'b']]
        got = [transform_row(transforms, row) for row in rows]
        expected = [
            ['<a href="1">1</a>', 'x: 2'],
            ['<a href="a">a</a>', 'x: b']
        ]
        self.assertEqual(expected, got)

########NEW FILE########
__FILENAME__ = test_views
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from explorer.tests.factories import SimpleQueryFactory
from explorer.models import Query, QueryLog
from explorer import app_settings
import time

class TestQueryListView(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')

    def test_admin_required(self):
        self.client.logout()
        resp = self.client.get(reverse("explorer_index"))
        self.assertTemplateUsed(resp, 'admin/login.html')


class TestQueryCreateView(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.user = User.objects.create_user('user', 'user@user.com', 'pwd')

    def test_change_permission_required(self):
        self.client.login(username='user', password='pwd')
        resp = self.client.get(reverse("query_create"))
        self.assertTemplateUsed(resp, 'admin/login.html')

    def test_renders_with_title(self):
        self.client.login(username='admin', password='pwd')
        resp = self.client.get(reverse("query_create"))
        self.assertTemplateUsed(resp, 'explorer/query.html')
        self.assertContains(resp, "New Query")


class TestQueryDetailView(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')

    def test_query_with_bad_sql_renders_error(self):
        query = SimpleQueryFactory(sql="error")
        resp = self.client.get(reverse("query_detail", kwargs={'query_id': query.id}))
        self.assertTemplateUsed(resp, 'explorer/query.html')
        self.assertContains(resp, "syntax error")

    def test_query_with_bad_sql_renders_error_on_save(self):
        query = SimpleQueryFactory(sql="select 1;")
        resp = self.client.post(reverse("query_detail", kwargs={'query_id': query.id}), data={'sql': 'error'})
        self.assertTemplateUsed(resp, 'explorer/query.html')
        self.assertContains(resp, "syntax error")

    def test_posting_query_saves_correctly(self):
        expected = 'select 2;'
        query = SimpleQueryFactory(sql="select 1;")
        data = model_to_dict(query)
        data['sql'] = expected
        self.client.post(reverse("query_detail", kwargs={'query_id': query.id}), data)
        self.assertEqual(Query.objects.get(pk=query.id).sql, expected)

    def test_change_permission_required_to_save_query(self):

        old = app_settings.EXPLORER_PERMISSION_CHANGE
        app_settings.EXPLORER_PERMISSION_CHANGE = lambda u: False

        query = SimpleQueryFactory()
        expected = query.sql
        resp = self.client.get(reverse("query_detail", kwargs={'query_id': query.id}))
        self.assertTemplateUsed(resp, 'explorer/query.html')

        self.client.post(reverse("query_detail", kwargs={'query_id': query.id}), {'sql': 'select 1;'})
        self.assertEqual(Query.objects.get(pk=query.id).sql, expected)

        app_settings.EXPLORER_PERMISSION_CHANGE = old

    def test_modified_date_gets_updated_after_viewing_query(self):
        query = SimpleQueryFactory()
        old = query.last_run_date
        time.sleep(0.1)
        self.client.get(reverse("query_detail", kwargs={'query_id': query.id}))
        self.assertNotEqual(old, Query.objects.get(pk=query.id).last_run_date)

    def test_admin_required(self):
        self.client.logout()
        query = SimpleQueryFactory(sql="before")
        resp = self.client.get(reverse("query_detail", kwargs={'query_id': query.id}))
        self.assertTemplateUsed(resp, 'admin/login.html')


class TestDownloadView(TestCase):
    def setUp(self):
        self.query = SimpleQueryFactory(sql="select 1;")
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')

    def test_download_query(self):
        resp = self.client.get(reverse("query_download", kwargs={'query_id': self.query.id}))
        self.assertEqual(resp['content-type'], 'text/csv')

    def test_admin_required(self):
        self.client.logout()
        resp = self.client.get(reverse("query_download", kwargs={'query_id': self.query.id}))
        self.assertTemplateUsed(resp, 'admin/login.html')

    def test_params_in_download(self):
        q = SimpleQueryFactory(sql="select '$$foo$$';")
        url = '%s?params=%s' % (reverse("query_download", kwargs={'query_id': q.id}), '{"foo":123}')
        resp = self.client.get(url)
        self.assertContains(resp, "'123'")



class TestQueryPlayground(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')

    def test_empty_playground_renders(self):
        resp = self.client.get(reverse("explorer_playground"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'explorer/play.html')

    def test_playground_renders_with_query_sql(self):
        query = SimpleQueryFactory(sql="select 1;")
        resp = self.client.get('%s?query_id=%s' % (reverse("explorer_playground"), query.id))
        self.assertTemplateUsed(resp, 'explorer/play.html')
        self.assertContains(resp, 'select 1;')

    def test_playground_renders_with_posted_sql(self):
        resp = self.client.post(reverse("explorer_playground"), {'sql': 'select 1;'})
        self.assertTemplateUsed(resp, 'explorer/play.html')
        self.assertContains(resp, 'select 1;')

    def test_query_with_no_resultset_doesnt_throw_error(self):
        query = SimpleQueryFactory(sql="")
        resp = self.client.get('%s?query_id=%s' % (reverse("explorer_playground"), query.id))
        self.assertTemplateUsed(resp, 'explorer/play.html')

    def test_admin_required(self):
        self.client.logout()
        resp = self.client.get(reverse("explorer_playground"))
        self.assertTemplateUsed(resp, 'admin/login.html')


class TestCSVFromSQL(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')

    def test_admin_required(self):
        self.client.logout()
        resp = self.client.post(reverse("generate_csv"), {})
        self.assertTemplateUsed(resp, 'admin/login.html')

    def test_downloading_from_playground(self):
        sql = "select 1;"
        resp = self.client.post(reverse("generate_csv"), {'sql': sql})
        self.assertEqual(resp['content-type'], 'text/csv')


class TestSchemaView(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')

    def test_returns_schema_contents(self):
        resp = self.client.get(reverse("explorer_schema"))
        self.assertContains(resp, "explorer_query")
        self.assertTemplateUsed(resp, 'explorer/schema.html')

    def test_admin_required(self):
        self.client.logout()
        resp = self.client.get(reverse("explorer_schema"))
        self.assertTemplateUsed(resp, 'admin/login.html')


class TestParamsInViews(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')
        self.query = SimpleQueryFactory(sql="select $$swap$$;")

    def test_retrieving_query_works_with_params(self):
        resp = self.client.get(reverse("query_detail", kwargs={'query_id': self.query.id}) + '?params={"swap":123}')
        self.assertContains(resp, "123")

    def test_saving_non_executing_query_with__wrong_url_params_works(self):
        q = SimpleQueryFactory(sql="select $$swap$$;")
        data = model_to_dict(q)
        url = '%s?params=%s' % (reverse("query_detail", kwargs={'query_id': q.id}), '{"foo":123}')
        resp = self.client.post(url, data)
        self.assertContains(resp, 'saved')

    def test_users_without_change_permissions_can_use_params(self):

        old = app_settings.EXPLORER_PERMISSION_CHANGE
        app_settings.EXPLORER_PERMISSION_CHANGE = lambda u: False

        resp = self.client.get(reverse("query_detail", kwargs={'query_id': self.query.id}) + '?params={"swap":123}')
        self.assertContains(resp, "123")

        app_settings.EXPLORER_PERMISSION_CHANGE = old


class TestCreatedBy(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.user2 = User.objects.create_superuser('admin2', 'admin2@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')
        self.query = SimpleQueryFactory.build()
        self.data = model_to_dict(self.query)
        self.data["created_by_user"] = 2

    def test_query_update_doesnt_change_created_user(self):
        self.query.save()
        self.client.post(reverse("query_detail", kwargs={'query_id': self.query.id}), self.data)
        q = Query.objects.get(id=self.query.id)
        self.assertEqual(q.created_by_user_id, 1)


    def test_new_query_gets_created_by_logged_in_user(self):
        self.client.post(reverse("query_create"), self.data)
        q = Query.objects.first()
        self.assertEqual(q.created_by_user_id, 1)


class TestQueryLog(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'admin@admin.com', 'pwd')
        self.client.login(username='admin', password='pwd')

    def test_playground_saves_query_to_log(self):
        self.client.post(reverse("explorer_playground"), {'sql': 'select 1;'})
        log = QueryLog.objects.first()
        self.assertTrue(log.is_playground)
        self.assertEqual(log.sql, 'select 1;')

    # Since it will be saved on the initial query creation, no need to log it
    def test_creating_query_does_not_save_to_log(self):
        query = SimpleQueryFactory()
        self.client.post(reverse("query_create"), model_to_dict(query))
        self.assertEqual(0, QueryLog.objects.count())

    def test_changing_query_saves_to_log(self):
        query = SimpleQueryFactory()
        data = model_to_dict(query)
        data['sql'] = 'select 12345;'
        self.client.post(reverse("query_detail", kwargs={'query_id': query.id}), data)
        self.assertEqual(1, QueryLog.objects.count())

    def test_unchanged_query_doesnt_save_to_log(self):
        query = SimpleQueryFactory()
        self.client.post(reverse("query_detail", kwargs={'query_id': query.id}), model_to_dict(query))
        self.assertEqual(0, QueryLog.objects.count())

    def test_retrieving_query_doesnt_save_to_log(self):
        query = SimpleQueryFactory()
        self.client.get(reverse("query_detail", kwargs={'query_id': query.id}))
        self.assertEqual(0, QueryLog.objects.count())

    def test_query_gets_logged_and_appears_on_log_page(self):
        query = SimpleQueryFactory()
        data = model_to_dict(query)
        data['sql'] = 'select 12345;'
        self.client.post(reverse("query_detail", kwargs={'query_id': query.id}), data)
        resp = self.client.get(reverse("explorer_logs"))
        self.assertContains(resp, 'select 12345;')

########NEW FILE########
__FILENAME__ = utils
## Testing helpers (from http://stackoverflow.com/a/3829849/221390
class AssertMethodIsCalled(object):
    def __init__(self, obj, method):
        self.obj = obj
        self.method = method

    def called(self, *args, **kwargs):
        self.method_called = True
        self.orig_method(*args, **kwargs)

    def __enter__(self):
        self.orig_method = getattr(self.obj, self.method)
        setattr(self.obj, self.method, self.called)
        self.method_called = False

    def __exit__(self, exc_type, exc_value, traceback):
        assert getattr(self.obj, self.method) == self.called, "method %s was modified during assertMethodIsCalled" % self.method

        setattr(self.obj, self.method, self.orig_method)

        # If an exception was thrown within the block, we've already failed.
        if traceback is None:
            assert self.method_called, "method %s of %s was not called" % (self.method, self.obj)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from explorer.views import QueryView, CreateQueryView, PlayQueryView, DeleteQueryView, ListQueryView, ListQueryLogView

urlpatterns = patterns('',
    url(r'(?P<query_id>\d+)/$', QueryView.as_view(), name='query_detail'),
    url(r'(?P<query_id>\d+)/download$', 'explorer.views.download_query', name='query_download'),
    url(r'(?P<pk>\d+)/delete$', DeleteQueryView.as_view(), name='query_delete'),
    url(r'new/$', CreateQueryView.as_view(), name='query_create'),
    url(r'play/$', PlayQueryView.as_view(), name='explorer_playground'),
    url(r'csv$', 'explorer.views.csv_from_sql', name='generate_csv'),
    url(r'schema/$', 'explorer.views.schema', name='explorer_schema'),
    url(r'logs/$', ListQueryLogView.as_view(), name='explorer_logs'),
    url(r'$', ListQueryView.as_view(), name='explorer_index'),
)
########NEW FILE########
__FILENAME__ = utils
import functools
import csv
import cStringIO
import json
import re
from time import time
from explorer import app_settings
from django.db import connections, connection, models, transaction, DatabaseError
from django.http import HttpResponse

EXPLORER_PARAM_TOKEN = "$$"

## SQL Specific Things

def passes_blacklist(sql):
    clean = functools.reduce(lambda sql, term: sql.upper().replace(term, ""), app_settings.EXPLORER_SQL_WHITELIST, sql)
    return not any(write_word in clean.upper() for write_word in app_settings.EXPLORER_SQL_BLACKLIST)


def execute_query(sql):
    conn = connections[app_settings.EXPLORER_CONNECTION_NAME] if app_settings.EXPLORER_CONNECTION_NAME else connection
    cursor = conn.cursor()
    start_time = time()

    sid = transaction.savepoint()
    try:
        cursor.execute(sql)
        transaction.savepoint_commit(sid)
    except DatabaseError:
        transaction.savepoint_rollback(sid)
        raise

    end_time = time()
    duration = (end_time - start_time) * 1000
    return cursor, duration


def execute_and_fetch_query(sql):
    cursor, duration = execute_query(sql)
    headers = [d[0] for d in cursor.description] if cursor.description else ['--']
    transforms = get_transforms(headers, app_settings.EXPLORER_TRANSFORMS)
    data = [transform_row(transforms, r) for r in cursor.fetchall()]
    return headers, data, duration, None


def get_transforms(headers, transforms):
    relevant_transforms = []
    for field, template in transforms:
        try:
            relevant_transforms.append((headers.index(field), template))
        except ValueError:
            pass
    return relevant_transforms


def transform_row(transforms, row):
    row = [x.encode('utf-8') if type(x) is unicode else x for x in list(row)]
    for i, t in transforms:
        row[i] = t.format(str(row[i]))
    return row


# returns schema information via django app inspection (sorted alphabetically by db table name):
# [
#     ("package.name -> ModelClass", "db_table_name",
#         [
#             ("db_column_name", "DjangoFieldType"),
#             (...),
#         ]
#     )
# ]
def schema_info():
    ret = []
    apps = [a for a in models.get_apps() if a.__package__ not in app_settings.EXPLORER_SCHEMA_EXCLUDE_APPS]
    for app in apps:
        for model in models.get_models(app):
            friendly_model = "%s -> %s" % (app.__package__, model._meta.object_name)
            ret.append((
                          friendly_model,
                          model._meta.db_table,
                          [_format_field(f) for f in model._meta.fields]
                      ))

            #Do the same thing for many_to_many fields. These don't show up in the field list of the model
            #because they are stored as separate "through" relations and have their own tables
            ret += [(
                       friendly_model,
                       m2m.rel.through._meta.db_table,
                       [_format_field(f) for f in m2m.rel.through._meta.fields]
                    ) for m2m in model._meta.many_to_many]

    return sorted(ret, key=lambda t: t[1])  # sort by table name


def _format_field(field):
    return (field.get_attname_column()[1], field.get_internal_type())



def param(name):
    return "%s%s%s" % (EXPLORER_PARAM_TOKEN, name, EXPLORER_PARAM_TOKEN)


def swap_params(sql, params):
    p = params.items() if params else {}
    for k, v in p:
        sql = sql.replace(param(k), str(v))
    return sql


def extract_params(text):
    regex = re.compile("\$\$([a-zA-Z0-9_|-]+)\$\$")
    params = re.findall(regex, text)
    return dict(zip(params, ['' for i in range(len(params))]))


def write_csv(headers, data):
    csv_data = cStringIO.StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(headers)
    map(lambda row: writer.writerow(row), data)
    return csv_data.getvalue()


def build_download_response(query, request):
    data = csv_report(query, url_get_params(request))
    response = HttpResponse(data, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % query.title.replace(',', '')
    response['Content-Length'] = len(data)
    return response


def csv_report(query, params=None):
    headers, data, duration, error = query.headers_and_data(params)
    if error:
        return error
    return write_csv(headers, data)


## Helpers
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.views import login
from django.contrib.auth import REDIRECT_FIELD_NAME
def safe_admin_login_prompt(request):
    defaults = {
        'template_name': 'admin/login.html',
        'authentication_form': AdminAuthenticationForm,
        'extra_context': {
            'title': 'Log in',
            'app_path': request.get_full_path(),
            REDIRECT_FIELD_NAME: request.get_full_path(),
        },
    }
    return login(request, **defaults)


def shared_dict_update(target, source):
    for k_d1 in target:
        if k_d1 in source:
            target[k_d1] = source[k_d1]
    return target


def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except ValueError:
        return default


def safe_json(val):
    try:
        return json.loads(val)
    except ValueError:
        return None


def get_int_from_request(request, name, default):
    val = request.GET.get(name, default)
    return safe_cast(val, int, default) if val else None


def get_json_from_request(request, name):
    val = request.GET.get(name, None)
    return safe_json(val) if val else None


def url_get_rows(request):
    return get_int_from_request(request, 'rows', app_settings.EXPLORER_DEFAULT_ROWS)


def url_get_query_id(request):
    return get_int_from_request(request, 'query_id', None)


def url_get_params(request):
    return get_json_from_request(request, 'params')




########NEW FILE########
__FILENAME__ = views
from django.http.response import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.base import View
from django.views.generic import ListView
from django.views.generic.edit import CreateView, DeleteView
from django.views.decorators.http import require_POST, require_GET
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse_lazy

from explorer.models import Query, QueryLog
from explorer.app_settings import EXPLORER_PERMISSION_VIEW, EXPLORER_PERMISSION_CHANGE, EXPLORER_RECENT_QUERY_COUNT
from explorer.forms import QueryForm
from explorer.utils import url_get_rows, url_get_query_id, schema_info, url_get_params, safe_admin_login_prompt, build_download_response


def view_permission(f):
    def wrap(request, *args, **kwargs):
        if not EXPLORER_PERMISSION_VIEW(request.user):
            return safe_admin_login_prompt(request)
        return f(request, *args, **kwargs)
    return wrap


def change_permission(f):
    def wrap(request, *args, **kwargs):
        if not EXPLORER_PERMISSION_CHANGE(request.user):
            return safe_admin_login_prompt(request)
        return f(request, *args, **kwargs)
    return wrap


class ExplorerContextMixin(object):

    def gen_ctx(self):
        return {'can_view': EXPLORER_PERMISSION_VIEW(self.request.user),
                'can_change': EXPLORER_PERMISSION_CHANGE(self.request.user)}

    def get_context_data(self, **kwargs):
        ctx = super(ExplorerContextMixin, self).get_context_data(**kwargs)
        ctx.update(self.gen_ctx())
        return ctx

    def render_template(self, template, ctx):
        ctx.update(self.gen_ctx())
        return render_to_response(template, ctx)


@view_permission
@require_GET
def download_query(request, query_id):
    query = get_object_or_404(Query, pk=query_id)
    return build_download_response(query, request)


@change_permission
@require_POST
def csv_from_sql(request):
    sql = request.POST.get('sql', None)
    if not sql:
        return PlayQueryView.render(request)
    return build_download_response(Query(sql=sql, title="Playground"), request)


@change_permission
@require_GET
def schema(request):
    return render_to_response('explorer/schema.html', {'schema': schema_info()})


class ListQueryView(ExplorerContextMixin, ListView):

    @method_decorator(view_permission)
    def dispatch(self, *args, **kwargs):
        return super(ListQueryView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        recent_queries = Query.objects.all().order_by('-last_run_date')[:EXPLORER_RECENT_QUERY_COUNT]
        context = super(ListQueryView, self).get_context_data(**kwargs)
        context['recent_queries'] = recent_queries
        return context

    model = Query


class ListQueryLogView(ExplorerContextMixin, ListView):

    @method_decorator(view_permission)
    def dispatch(self, *args, **kwargs):
        return super(ListQueryLogView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        recent_logs = QueryLog.objects.all().order_by('-run_at')[:100]
        context = super(ListQueryLogView, self).get_context_data(**kwargs)
        context['recent_logs'] = recent_logs
        return context

    model = QueryLog


class CreateQueryView(ExplorerContextMixin, CreateView):

    @method_decorator(change_permission)
    def dispatch(self, *args, **kwargs):
        return super(CreateQueryView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by_user = self.request.user
        return super(CreateQueryView, self).form_valid(form)

    form_class = QueryForm
    template_name = 'explorer/query.html'


class DeleteQueryView(ExplorerContextMixin, DeleteView):

    @method_decorator(change_permission)
    def dispatch(self, *args, **kwargs):
        return super(DeleteQueryView, self).dispatch(*args, **kwargs)

    model = Query
    success_url = reverse_lazy("explorer_index")


class PlayQueryView(ExplorerContextMixin, View):

    @method_decorator(change_permission)
    def dispatch(self, *args, **kwargs):
        return super(PlayQueryView, self).dispatch(*args, **kwargs)

    def get(self, request):
        if not url_get_query_id(request):
            return self.render(request)
        query = get_object_or_404(Query, pk=url_get_query_id(request))
        return self.render_with_sql(request, query)

    def post(self, request):
        sql = request.POST.get('sql', None)
        if not sql:
            return PlayQueryView.render(request)
        query = Query(sql=sql, title="Playground")
        query.log(request.user)
        return self.render_with_sql(request, query)

    def render(self, request):
        c = RequestContext(request, {'title': 'Playground'})
        return self.render_template('explorer/play.html', c)

    def render_with_sql(self, request, query):
        return self.render_template('explorer/play.html', query_viewmodel(request, query, title="Playground"))


class QueryView(ExplorerContextMixin, View):

    @method_decorator(view_permission)
    def dispatch(self, *args, **kwargs):
        return super(QueryView, self).dispatch(*args, **kwargs)

    def get(self, request, query_id):
        query, form = QueryView.get_instance_and_form(request, query_id)
        query.save()  # updates the modified date
        vm = query_viewmodel(request, query, form=form, message=None)
        return self.render_template('explorer/query.html', vm)

    def post(self, request, query_id):
        if not EXPLORER_PERMISSION_CHANGE(request.user):
            return HttpResponseRedirect(
                reverse_lazy('query_detail', kwargs={'query_id': query_id})
            )

        query, form = QueryView.get_instance_and_form(request, query_id)
        success = form.save() if form.is_valid() else None
        if form.has_changed():
            query.log(request.user)
        vm = query_viewmodel(request, query, form=form, message="Query saved." if success else None)
        return self.render_template('explorer/query.html', vm)

    @staticmethod
    def get_instance_and_form(request, query_id):
        query = get_object_or_404(Query, pk=query_id)
        form = QueryForm(request.POST if len(request.POST) else None, instance=query)
        return query, form


def query_viewmodel(request, query, title=None, form=None, message=None):
    rows = url_get_rows(request)
    params = url_get_params(request)
    headers, data, duration, error = query.headers_and_data(params)
    return RequestContext(request, {
            'error': error,
            'params': query.available_params(param_values=params),
            'title': title,
            'query': query,
            'form': form,
            'message': message,
            'data': data[:rows],
            'headers': headers,
            'duration': duration,
            'rows': rows,
            'total_rows': len(data)})
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
from django.core import management
if __name__ == "__main__":
    management.execute_from_command_line()
########NEW FILE########
__FILENAME__ = test_settings
SECRET_KEY = 'shhh'
SITE_ID = 1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

ROOT_URLCONF = 'explorer.urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.static",
    "django.core.context_processors.request",
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'explorer',
    'south'
)

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
)

STATIC_URL = '/static/'
########NEW FILE########
