__FILENAME__ = admin
from django.contrib import admin

from datatrans.models import KeyValue


class KeyValueAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'object_id', 'field',
                    'value', 'language', 'edited', 'fuzzy')
    ordering = ('digest', 'language')
    search_fields = ('content_type__app_label', 'content_type__model', 'value',)
    list_filter = ('content_type', 'language', 'edited', 'fuzzy')

admin.site.register(KeyValue, KeyValueAdmin)

########NEW FILE########
__FILENAME__ = deleteduplicates
from collections import defaultdict
from datatrans.models import KeyValue
from django.db import connection, transaction
from django.core.management.base import BaseCommand
from south.db import db


class Command(BaseCommand):
    help = 'Deletes duplicate KeyValues, only mysql is supported in a fast way'

    @transaction.commit_on_success
    def remove_duplicates_mysql(self):
        """
        Removes all the duplicates from the datatrans_keyvalue table. First we detect what the most horrible
        duplication count is of a KeyValue.  Then we iterate through the count and start deleting the newest duplicate
        row of a certain KeyValue.  Wow, confused?

        The majority of KeyValues have 1 duplication, but some have 2 duplications. This means that we have to execute
        the deletion query twice since it only deletes 1 duplication (the newest) each time
        """
        print '  Deleting duplicates from datatrans_keyvalue table'
        cursor = connection.cursor()
        cursor.execute("""
            select count(id)
            from datatrans_keyvalue
            group by digest, language, content_type_id, object_id, field
            having count(*) > 1
            order by count(id) desc
        """)
        row = cursor.fetchone()

        if row and row[0] > 0:
            count = row[0]
            print '   - Most horrible duplication count = ', count

            for i in range(count - 1):
                # Mysql doesn't allow to delete in a table while fetching values from it (makes sense).
                # Therefore we have to fetch the duplicate ids first into a python list.
                # Secondly we pass this list to the deletion query
                print '   - Deleting entries with %s duplicates' % (i + 1)
                cursor.execute("""
                        select max(id)
                        from datatrans_keyvalue
                        group by digest, language, content_type_id, object_id, field
                        having count(*) > 1
                    """)

                ids = [str(_row[0]) for _row in cursor.fetchall()]
                strids = ",".join(ids)

                cursor.execute("""
                    delete from datatrans_keyvalue
                    where id in (%s)
                """ % strids)
        else:
            print '   - No duplicates found'

    def remove_duplicates_default(self):
        """
        A cleaner implementation. But unfortunately way more slower slower
        """
        kv_map = defaultdict(lambda: [])
        deleted = 0

        for kv in KeyValue.objects.all():
            # For some reason a null object exists in the database
            if not kv.id:
                continue

            key = (kv.language, kv.digest, kv.content_type, kv.object_id, kv.field)
            kv_map[key].append(kv)

            for (kv.language, kv.digest, kv.content_type, kv.object_id, kv.field), kv_list in kv_map.items():
                if len(kv_list) == 1:
                    continue

                kv_list.sort(key=lambda kv: kv.id)

                for kv in kv_list[:-1]:
                    if kv.id:
                        print 'Deleting KeyValue ', kv.id, ", ", kv
                        deleted += 1
                        kv.delete()

        print 'Duplicates deleted:', deleted

    def print_db_info(self):
        from django.conf import settings
        conn = db._get_connection().connection
        dbinfo = settings.DATABASES[db.db_alias]
        print 'Database: ' + conn.get_host_info() + ":" + str(conn.port) + ", db: " + dbinfo['NAME']

    def handle(self, *args, **options):
        self.print_db_info()

        if db.backend_name == 'mysql':
            print 'Remove duplicates: mysql'
            self.remove_duplicates_mysql()
        else:
            #print 'Remove duplicates: default'
            #print 'Grab some coffee, this can take a while ...'
            #self.remove_duplicates_default()
            print 'Unfortunately this command only supports mysql, selected db: ', db.backend_name

########NEW FILE########
__FILENAME__ = middleware
from django.utils.cache import patch_vary_headers
from django.utils import translation


class MinimalLocaleMiddleware(object):
    """
    This is a minimal version of the LocaleMiddleware from Django.
    It only supports setting the current language from sessions.
    This allows the main site to be in one language while the site
    administrators can switch the language, so they don't experience
    problems while editing original database content when this is not
    in the main site's language.
    """

    def process_request(self, request):
        language = get_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = translation.get_language()
        translation.deactivate()
        return response


def get_language_from_request(request):
    from django.conf import settings
    supported = dict(settings.LANGUAGES)

    if hasattr(request, 'session'):
        lang_code = request.session.get('django_language', None)
        if lang_code in supported and lang_code is not None:
            return lang_code
    return settings.LANGUAGE_CODE

########NEW FILE########
__FILENAME__ = 0001a_remove_duplicates
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

from datatrans.models import KeyValue
from collections import defaultdict

class Migration(DataMigration):

    depends_on = (
        ("datatrans", "0001_initial"),
    )

    def forwards(self, orm):
        "Write your forwards methods here."

        kv_map = defaultdict(lambda: [])

        for kv in orm.KeyValue.objects.all():
            key = (kv.language, kv.digest)
            kv_map[key].append(kv)

        for (language, digest), kv_list in kv_map.items():
            if len(kv_list) == 1:
                continue

            kv_list.sort(key=lambda kv: kv.id)

            for kv in kv_list[:-1]:
                print 'Deleting KeyValue', kv.id
                kv.delete()


    def backwards(self, orm):
        "Write your backwards methods here."

    models = {
        'datatrans.keyvalue': {
            'Meta': {'object_name': 'KeyValue'},
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'fuzzy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['datatrans']


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'KeyValue'
        db.create_table('datatrans_keyvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('digest', self.gf('django.db.models.fields.CharField')(max_length=40, db_index=True)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=5, db_index=True)),
            ('value', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('edited', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('fuzzy', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('datatrans', ['KeyValue'])


    def backwards(self, orm):
        
        # Deleting model 'KeyValue'
        db.delete_table('datatrans_keyvalue')


    models = {
        'datatrans.keyvalue': {
            'Meta': {'object_name': 'KeyValue'},
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'fuzzy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['datatrans']

########NEW FILE########
__FILENAME__ = 0002_add_unique_together
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    depends_on = (
        ("datatrans", "0001a_remove_duplicates"),
    )

    def forwards(self, orm):
        
        # Adding unique constraint on 'KeyValue', fields ['language', 'digest']
        db.create_unique('datatrans_keyvalue', ['language', 'digest'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'KeyValue', fields ['language', 'digest']
        db.delete_unique('datatrans_keyvalue', ['language', 'digest'])


    models = {
        'datatrans.keyvalue': {
            'Meta': {'unique_together': "(('digest', 'language'),)", 'object_name': 'KeyValue'},
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'fuzzy': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['datatrans']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_keyvalue_content_type__add_field_keyvalue_object_id__a
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'KeyValue', fields ['language', 'digest']
        try:
            db.delete_unique('datatrans_keyvalue', ['language', 'digest'])
        except ValueError:
            print "  WARNING: current index didn't exist"

        # Adding field 'KeyValue.content_type'
        db.add_column('datatrans_keyvalue', 'content_type', self.gf('django.db.models.fields.related.ForeignKey')(default=None, null=True, to=orm['contenttypes.ContentType']), keep_default=False)

        # Adding field 'KeyValue.object_id'
        db.add_column('datatrans_keyvalue', 'object_id', self.gf('django.db.models.fields.PositiveIntegerField')(default=None, null=True), keep_default=False)

        # Adding field 'KeyValue.field'
        db.add_column('datatrans_keyvalue', 'field', self.gf('django.db.models.fields.TextField')(default=""), keep_default=False)

    def backwards(self, orm):
        
        # Deleting field 'KeyValue.content_type'
        db.delete_column('datatrans_keyvalue', 'content_type_id')

        # Deleting field 'KeyValue.object_id'
        db.delete_column('datatrans_keyvalue', 'object_id')

        # Deleting field 'KeyValue.field'
        db.delete_column('datatrans_keyvalue', 'field')

        # Adding unique constraint on 'KeyValue', fields ['language', 'digest']
        db.create_unique('datatrans_keyvalue', ['language', 'digest'])

    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatrans.keyvalue': {
            'Meta': {'object_name': 'KeyValue'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'field': ('django.db.models.fields.TextField', [], {}),
            'fuzzy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['datatrans']

########NEW FILE########
__FILENAME__ = 0003_auto__add_modelwordcount__add_fieldwordcount__add_unique_fieldwordcoun
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ModelWordCount'
        db.create_table('datatrans_modelwordcount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('total_words', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('valid', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], unique=True)),
        ))
        db.send_create_signal('datatrans', ['ModelWordCount'])

        # Adding model 'FieldWordCount'
        db.create_table('datatrans_fieldwordcount', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('total_words', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('valid', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('field', self.gf('django.db.models.fields.CharField')(max_length=64, db_index=True)),
        ))
        db.send_create_signal('datatrans', ['FieldWordCount'])

        # Adding unique constraint on 'FieldWordCount', fields ['content_type', 'field']
        db.create_unique('datatrans_fieldwordcount', ['content_type_id', 'field'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'FieldWordCount', fields ['content_type', 'field']
        db.delete_unique('datatrans_fieldwordcount', ['content_type_id', 'field'])

        # Deleting model 'ModelWordCount'
        db.delete_table('datatrans_modelwordcount')

        # Deleting model 'FieldWordCount'
        db.delete_table('datatrans_fieldwordcount')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatrans.fieldwordcount': {
            'Meta': {'unique_together': "(('content_type', 'field'),)", 'object_name': 'FieldWordCount'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'field': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'total_words': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'datatrans.keyvalue': {
            'Meta': {'unique_together': "(('digest', 'language'),)", 'object_name': 'KeyValue'},
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'fuzzy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'datatrans.modelwordcount': {
            'Meta': {'object_name': 'ModelWordCount'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'total_words': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['datatrans']

########NEW FILE########
__FILENAME__ = 0004_add_object_links
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.contrib.contenttypes.models import ContentType

from datatrans.models import make_digest, KeyValue
from datatrans.utils import get_registry
from collections import defaultdict

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."

        registry = get_registry()
        counts = defaultdict(lambda: [])

        for modelclass, fields in registry.items():
            ct = ContentType.objects.get_for_model(modelclass)
            for object in modelclass.objects.all():
                for field in fields.keys():
                    value = object.__dict__[field]
                    counts[value].append((object, field))
                    digest = make_digest(value)

                    done = {}

                    for kv in KeyValue.objects.filter(digest=digest).all():
                        if kv.object_id is None:
                            kv.content_object = object
                            kv.field = field
                            kv.save()
                        else:
                            if not kv.language in done:
                                KeyValue.objects.get_or_create(
                                    digest = kv.digest,
                                    language = kv.language,
                                    object_id = object.id,
                                    content_type_id = ct.id,
                                    field = field,
                                    defaults = { 'value': kv.value,
                                                 'edited': kv.edited,
                                                 'fuzzy': kv.fuzzy,
                                               }
                                )
                                done[kv.language] = 1

        # for value, uses in counts.items():
        #     if len(uses) > 1:
        #         print value, uses


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatrans.keyvalue': {
            'Meta': {'object_name': 'KeyValue'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'field': ('django.db.models.fields.TextField', [], {}),
            'fuzzy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['datatrans']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_keyvalue_updated
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'KeyValue.updated'
        db.add_column('datatrans_keyvalue', 'updated',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now=True, blank=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'KeyValue.updated'
        db.delete_column('datatrans_keyvalue', 'updated')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatrans.fieldwordcount': {
            'Meta': {'unique_together': "(('content_type', 'field'),)", 'object_name': 'FieldWordCount'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'field': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'total_words': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'datatrans.keyvalue': {
            'Meta': {'unique_together': "(('digest', 'language'),)", 'object_name': 'KeyValue'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'field': ('django.db.models.fields.TextField', [], {}),
            'fuzzy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'datatrans.modelwordcount': {
            'Meta': {'object_name': 'ModelWordCount'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'total_words': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['datatrans']
########NEW FILE########
__FILENAME__ = 0006_auto__chg_field_keyvalue_field__del_unique_keyvalue_language_digest__a
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'KeyValue', fields ['language', 'digest']
        try:
            db.delete_unique('datatrans_keyvalue', ['language', 'digest'])
        except ValueError:
            print "  WARNING: current index didn't exist"

        # Changing field 'KeyValue.field'
        db.alter_column('datatrans_keyvalue', 'field', self.gf('django.db.models.fields.CharField')(max_length=255))
        # Adding unique constraint on 'KeyValue', fields ['field', 'digest', 'content_type', 'language', 'object_id']
        db.create_unique('datatrans_keyvalue', ['field', 'digest', 'content_type_id', 'language', 'object_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'KeyValue', fields ['field', 'digest', 'content_type', 'language', 'object_id']
        db.delete_unique('datatrans_keyvalue', ['field', 'digest', 'content_type_id', 'language', 'object_id'])


        # Changing field 'KeyValue.field'
        db.alter_column('datatrans_keyvalue', 'field', self.gf('django.db.models.fields.TextField')())
        # Adding unique constraint on 'KeyValue', fields ['language', 'digest']
        db.create_unique('datatrans_keyvalue', ['language', 'digest'])

    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatrans.fieldwordcount': {
            'Meta': {'unique_together': "(('content_type', 'field'),)", 'object_name': 'FieldWordCount'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'field': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'total_words': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'datatrans.keyvalue': {
            'Meta': {'unique_together': "(('language', 'content_type', 'field', 'object_id', 'digest'),)", 'object_name': 'KeyValue'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'field': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'fuzzy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'datatrans.modelwordcount': {
            'Meta': {'object_name': 'ModelWordCount'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'total_words': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['datatrans']
########NEW FILE########
__FILENAME__ = models
import datetime
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import signals
from django.db.models.query import QuerySet
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from hashlib import sha1


def make_digest(key):
    """Get the SHA1 hexdigest of the given key"""
    return sha1(key.encode('utf-8')).hexdigest()


def _get_cache_keys(self):
    """Get all the cache keys for the given object"""
    kv_id_fields = ('language', 'digest', 'content_type_id', 'object_id', 'field')
    values = tuple(getattr(self, attr) for attr in kv_id_fields)
    return ('datatrans_%s_%s_%s_%s_%s' % values,
            'datatrans_%s' % self.id)

# cache for an hour
CACHE_DURATION = getattr(settings, 'DATATRANS_CACHE_DURATION', 60 * 60)


class KeyValueManager(models.Manager):
    def get_query_set(self):
        return KeyValueQuerySet(self.model)

    def get_keyvalue(self, key, language, obj, field):
        key = key or ''
        digest = make_digest(key)
        content_type = ContentType.objects.get_for_model(obj.__class__)
        object_id = obj.id
        keyvalue, created = self.get_or_create(digest=digest,
                                               language=language,
                                               content_type_id=content_type.id,
                                               object_id=obj.id,
                                               field=field,
                                               defaults={'value': key})
        return keyvalue

    def lookup(self, key, language, obj, field):
        kv = self.get_keyvalue(key, language, obj, field)
        if kv.edited:
            return kv.value
        else:
            return key

    def for_model(self, model, fields, modelfield=None):
        """
        Get KeyValues for a model. The fields argument is a list of model
        fields.
        If modelfield is specified, only KeyValue entries for that field will
        be returned.
        """
        field_names = [f.name for f in fields] if modelfield is None else [modelfield]
        ct = ContentType.objects.get_for_model(model)
        return self.filter(field__in=field_names, content_type__id=ct.id)

    def contribute_to_class(self, model, name):
        signals.post_save.connect(self._post_save, sender=model)
        signals.post_delete.connect(self._post_delete, sender=model)
        setattr(model, '_get_cache_keys', _get_cache_keys)
        setattr(model, 'cache_keys', property(_get_cache_keys))
        return super(KeyValueManager, self).contribute_to_class(model, name)

    def _invalidate_cache(self, instance):
        """
        Explicitly set a None value instead of just deleting so we don't have
        any race conditions where.
        """
        for key in instance.cache_keys:
            cache.set(key, None, 5)

    def _post_save(self, instance, **kwargs):
        """
        Refresh the cache when saving
        """
        for key in instance.cache_keys:
            cache.set(key, instance, CACHE_DURATION)

    def _post_delete(self, instance, **kwargs):
        self._invalidate_cache(instance)


class KeyValueQuerySet(QuerySet):
    def iterator(self):
        superiter = super(KeyValueQuerySet, self).iterator()
        while True:
            obj = superiter.next()
            # Use cache.add instead of cache.set to prevent race conditions
            for key in obj.cache_keys:
                cache.add(key, obj, CACHE_DURATION)
            yield obj

    def get(self, *args, **kwargs):
        """
        Checks the cache to see if there's a cached entry for this pk. If not,
        fetches using super then stores the result in cache.

        Most of the logic here was gathered from a careful reading of
        ``django.db.models.sql.query.add_filter``
        """
        if self.query.where:
            # If there is any other ``where`` filter on this QuerySet just call
            # super. There will be a where clause if this QuerySet has already
            # been filtered/cloned.
            return super(KeyValueQuerySet, self).get(*args, **kwargs)

        kv_id_fields = ('language', 'digest', 'content_type', 'object_id', 'field')

        # Punt on anything more complicated than get by pk/id only...
        if len(kwargs) == 1:
            k = kwargs.keys()[0]
            if k in ('pk', 'pk__exact', 'id', 'id__exact'):
                obj = cache.get('datatrans_%s' % kwargs.values()[0])
                if obj is not None:
                    return obj
        elif set(kv_id_fields) <= set(kwargs.keys()):
            values = tuple(kwargs[attr] for attr in kv_id_fields)
            obj = cache.get('datatrans_%s_%s_%s_%s_%s' % values)

            if obj is not None:
                return obj

        # Calls self.iterator to fetch objects, storing object in cache.
        return super(KeyValueQuerySet, self).get(*args, **kwargs)


class KeyValue(models.Model):
    """
    The datatrans magic is stored in this model. It stores the localized fields of models.
    """
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True, default=None)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    field = models.CharField(max_length=255)
    language = models.CharField(max_length=5, db_index=True, choices=settings.LANGUAGES)

    value = models.TextField(blank=True)
    edited = models.BooleanField(blank=True, default=False)
    fuzzy = models.BooleanField(blank=True, default=False)

    digest = models.CharField(max_length=40, db_index=True)
    updated = models.DateTimeField(auto_now=True, default=datetime.datetime.now)

    objects = KeyValueManager()

    def __unicode__(self):
        return u'%s: %s' % (self.language, self.value)

    class Meta:
        #unique_together = ('digest', 'language')
        unique_together = ('language', 'content_type', 'field', 'object_id', 'digest')


class WordCount(models.Model):
    """
    It all happens here
    """
    class Meta:
        abstract = True

    total_words = models.IntegerField(default=0)
    valid = models.BooleanField()


class ModelWordCount(WordCount):
    """
    Caches the total number of localized words for a model
    """
    content_type = models.ForeignKey(ContentType, db_index=True, unique=True)


class FieldWordCount(WordCount):
    """
    Caches the total number of localized words for a model field.
    """
    class Meta:
        unique_together = ('content_type', 'field')

    content_type = models.ForeignKey(ContentType, db_index=True)
    field = models.CharField(max_length=64, db_index=True)



########NEW FILE########
__FILENAME__ = tests
import sys

from django.core.cache import cache
from django.test import TestCase
from django.utils import translation
from django.contrib.contenttypes.models import ContentType

from datatrans.models import KeyValue, make_digest


if len(sys.argv) > 1 and sys.argv[1] == 'test':
    # We need a model to translate. This is a bit hacky, see
    # http://code.djangoproject.com/ticket/7835
    from django.db import models

    class ModelToTranslate(models.Model):
        message = models.TextField()


class DatatransTests(TestCase):
    def setUp(self):
        self.nl = 'nl'
        self.en = 'en'
        self.message_en = 'Message in English'
        self.message_nl = 'Bericht in het Nederlands'
        self.field = 'message'
        self.instance = ModelToTranslate.objects.create(message=self.message_en)

    def test_default_values(self):
        value = KeyValue.objects.lookup(self.message_en, self.nl, self.instance, self.field)
        self.assertEqual(value, self.message_en)

        kv = KeyValue.objects.get_keyvalue(self.message_en, self.nl, self.instance, self.field)
        kv.value = self.message_nl
        kv.save()

        value = KeyValue.objects.lookup(self.message_en, self.nl, self.instance, self.field)
        self.assertEqual(value, self.message_en)

        kv.edited = True
        kv.save()

        value = KeyValue.objects.lookup(self.message_en, self.nl, self.instance, self.field)
        self.assertEqual(value, self.message_nl)

    def test_cache(self):
        digest = make_digest(self.message_en)
        type_id = ContentType.objects.get_for_model(self.instance.__class__).id
        cache_key = 'datatrans_%s_%s_%s_%s_%s' % (self.nl,
                                                  digest,
                                                  type_id,
                                                  self.instance.id,
                                                  self.field)

        self.assertEqual(cache.get(cache_key), None)

        translation.activate(self.nl)

        kv = KeyValue.objects.get_keyvalue(self.message_en, self.nl, self.instance, self.field)
        self.assertEqual(cache.get(cache_key).value, self.message_en)
        kv.value = self.message_nl
        kv.save()
        kv = KeyValue.objects.get_keyvalue(self.message_en, self.nl, self.instance, self.field)
        self.assertEqual(cache.get(cache_key).value, self.message_nl)
        kv.value = '%s2' % self.message_nl
        kv.save()
        self.assertEqual(cache.get(cache_key).value, '%s2' % self.message_nl)
        kv.delete()
        self.assertEqual(cache.get(cache_key), None)

    def test_fuzzy(self):
        kv = KeyValue.objects.get_keyvalue(self.message_en, self.nl, self.instance, self.field)
        kv.value = self.message_nl
        kv.edited = True
        kv.fuzzy = True
        kv.save()

        value = KeyValue.objects.lookup(self.message_en, self.nl, self.instance, self.field)
        self.assertEqual(value, self.message_nl)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from datatrans import views

urlpatterns = patterns('',
    url(r'^$', views.model_list, name='datatrans_model_list'),
    url(r'^model/(?P<slug>.*)/(?P<language>.*)/(?P<object_id>.*)/$', views.object_detail, name='datatrans_object_detail'),
    url(r'^model/(?P<slug>.*)/(?P<language>.*)/$', views.model_detail, name='datatrans_model_detail'),
    url(r'^make/messages/$', views.make_messages, name='datatrans_make_messages'),
    url(r'^obsoletes/$', views.obsolete_list, name='datatrans_obsolete_list'),
)

########NEW FILE########
__FILENAME__ = utils
# -*- encoding: utf-8 -*-
import operator

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import models
from django.utils import translation
from django.utils.datastructures import SortedDict
from django.contrib.contenttypes.models import ContentType

from datatrans.models import KeyValue, make_digest, ModelWordCount, FieldWordCount


"""
REGISTRY is a dict containing the registered models and their translation
fields as a dict.
Example:

>>> from blog.models import Entry
>>> from datatrans.utils import *
>>> class EntryTranslation(object):
...     fields = ('title', 'body',)
...
>>> register(Entry, EntryTranslation)
>>> REGISTRY
{<class 'blog.models.Entry'>: {'body': <django.db.models.fields.TextField object at 0x911368c>,
                               'title': <django.db.models.fields.CharField object at 0x911346c>}}
"""
REGISTRY = SortedDict()
META = SortedDict()


def get_registry():
    return REGISTRY


def get_meta():
    return META


def count_words():
    return sum(count_model_words(model) for model in REGISTRY)


def count_model_words(model):
    """
    Returns word count for the given model and language.
    """
    ct = ContentType.objects.get_for_model(model)
    model_wc, created = ModelWordCount.objects.get_or_create(
        content_type=ct
    )
    if not model_wc.valid:
        total_words = 0

        for field in REGISTRY[model]:
            field_wc, created = FieldWordCount.objects.get_or_create(
                content_type=ct, field=field
            )
            if not field_wc.valid:
                field_wc.total_words = _count_field_words(model, field_wc.field)
                field_wc.valid = True
                field_wc.save()

            total_words += field_wc.total_words

        model_wc.total_words = total_words
        model_wc.valid = True
        model_wc.save()

    return model_wc.total_words


def _count_field_words(model, fieldname):
    """
    Return word count for the given model and field.
    """
    total = 0

    for instance in model.objects.all():
        words = _count_words(instance.__dict__[fieldname])
        total += words
    return total


def _count_words(text):
    """
    Count words in a piece of text.
    """
    return len(text.split()) if text else 0


def get_default_language():
    """
    Get the source language code if specified, or else just the default
    language code.
    """
    lang = getattr(settings, 'SOURCE_LANGUAGE_CODE', settings.LANGUAGE_CODE)
    default = [l[0] for l in settings.LANGUAGES if l[0] == lang]
    if len(default) == 0:
        # when not found, take first part ('en' instead of 'en-us')
        lang = lang.split('-')[0]
        default = [l[0] for l in settings.LANGUAGES if l[0] == lang]
    if len(default) == 0:
        raise ImproperlyConfigured("The [SOURCE_]LANGUAGE_CODE '%s' is not found in your LANGUAGES setting." % lang)
    return default[0]


def get_current_language():
    """
    Get the current language
    """
    lang = translation.get_language()
    current = [l[0] for l in settings.LANGUAGES if l[0] == lang]
    if len(current) == 0:
        lang = lang.split('-')[0]
        current = [l[0] for l in settings.LANGUAGES if l[0] == lang]
    if len(current) == 0:
        # Fallback to default language code
        return get_default_language()
    
    return current[0]


class FieldDescriptor(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, instance, owner):
        lang_code = get_current_language()
        key = instance.__dict__[self.name]
        if not key:
            return u''
        if instance.id is None:
            return key
        return KeyValue.objects.lookup(key, lang_code, instance, self.name)

    def __set__(self, instance, value):
        lang_code = get_current_language()
        default_lang = get_default_language()

        if lang_code == default_lang or not self.name in instance.__dict__ or instance.id is None:
            instance.__dict__[self.name] = value
        else:
            original = instance.__dict__[self.name]
            if original == u'':
                instance.__dict__[self.name] = value
                original = value

            kv = KeyValue.objects.get_keyvalue(original, lang_code, instance, self.name)
            kv.value = value
            kv.edited = True
            kv.save()

        return None


def _pre_save(sender, instance, **kwargs):
    setattr(instance, 'datatrans_old_language', get_current_language())
    default_lang = get_default_language()
    translation.activate(default_lang)

    # When we edit a registered model, update the original translations and mark them as unedited (to do)
    if instance.pk is not None:
        try:
            # Just because instance.pk is set, it does not mean that the instance
            # is saved. Most typical/important ex: loading fixtures
            original = sender.objects.get(pk=instance.pk)
        except ObjectDoesNotExist:
            return None

        ct = ContentType.objects.get_for_model(sender)
        register = get_registry()
        fields = register[sender].values()
        for field in fields:
            old_digest = make_digest(original.__dict__[field.name] or '')
            new_digest = make_digest(instance.__dict__[field.name] or '')
            # If changed, update keyvalues
            if old_digest != new_digest:
                # Check if the new value already exists, if not, create a new one. The old one will be obsoleted.
                old_query = KeyValue.objects.filter(digest=old_digest,
                                                    content_type__id=ct.id,
                                                    object_id=original.id,
                                                    field=field.name)
                new_query = KeyValue.objects.filter(digest=new_digest,
                                                    content_type__id=ct.id,
                                                    object_id=original.id,
                                                    field=field.name)

                old_count = old_query.count()
                new_count = new_query.count()
                _invalidate_word_count(sender, field, instance)
                if old_count != new_count or new_count == 0:
                    for kv in old_query:
                        if new_query.filter(language=kv.language).count() > 0:
                            continue
                        new_value = instance.__dict__[field.name] if kv.language == default_lang else kv.value
                        new_kv = KeyValue(digest=new_digest,
                                          content_type_id=ct.id,
                                          object_id=original.id,
                                          field=field.name,
                                          language=kv.language,
                                          edited=kv.edited,
                                          fuzzy=True,
                                          value=new_value)
                        new_kv.save()


def _post_save(sender, instance, created, **kwargs):
    translation.activate(getattr(instance, 'datatrans_old_language',
                                 get_default_language()))


def _datatrans_filter(self, language=None, mode='and', **kwargs):
    """
    This filter allows you to search model instances on the
    translated contents of a given field.

    :param language: Language code (one of the keys of settings.LANGUAGES).
                     Specifies which language to perform the query in.
    :type language: str

    :param mode: Determines how to combine multiple filter arguments. Mode
                 'or' is fully supported. Mode 'and' only accepts one filter argument.
    :type mode: str, one of ('and', 'or')

    :param <field_name>__<selector>: Indicates which field to search, and
                                     which method (icontains, exact, ...) to use.
                                     If the value of this parameter is an iterable, we will
                                     add multiple filters.
    :type <field_name>__<selector>: str

    :return: Queryset with the matching instances.
    :rtype: :class:`django.db.models.query.QuerySet`

    Search for jobs whose Dutch function name contains 'ontwikkelaar':

    >>> Job.objects.datatrans_filter(function__icontains='ontwikkelaar', language='nl')
    ...

    Search for jobs whose Dutch description contains both 'slim' and 'efficiënt':

    >>> Job.objects.datatrans_filter(description__icontains=['slim', 'efficiënt'],
                                     mode='and', language='nl')
    ...
    """
    assert mode in ('and', 'or')

    if mode == 'and' and len(kwargs) > 1:
        raise NotImplementedError("No support for multiple field name in 'and' mode.")

    if language is None:
        language = translation.get_language()

    registry = get_registry()
    ct = ContentType.objects.get_for_model(self.model)
    q_objects = []

    for key, value in kwargs.items():
        if '__' in key:
            field, method = key.split('__', 1)
        else:
            field, method = key, 'exact'

        if field not in registry[self.model].keys():
            raise ValueError("Field '" + field + "' of " + self.model.__name__ +
                            " has not been registered for translation.")

        def add_filters(field, method, value):
            filters = { 'field' : field, 'value__' + method : value }
            q_objects.append(models.Q(**filters))

        try:
            # Add multiple filters if value is iterable.
            map(lambda v: add_filters(field, method, v), value)
        except TypeError:
            # Iteration failed, therefore value contains single object.
            add_filters(field, method, value)

    query = KeyValue.objects.filter(content_type__id=ct.id, language=language)

    if q_objects:
        op = operator.or_ if mode == 'or' else operator.and_
        query = query.filter(reduce(op, q_objects))

    object_ids = set(i for i , in query.values_list('object_id'))

    return self.filter(id__in=object_ids)


def _invalidate_word_count(model, field, instance):
    content_type = ContentType.objects.get_for_model(model)

    try:
        model_wc = ModelWordCount.objects.get(content_type=content_type)
    except ModelWordCount.DoesNotExist:
        pass
    else:
        model_wc.valid = False
        model_wc.save()

    try:
        field_wc = FieldWordCount.objects.get(
            content_type=content_type, field=field.name
        )
    except FieldWordCount.DoesNotExist:
        pass
    else:
        field_wc.valid = False
        field_wc.save()


def register(model, modeltranslation):
    """
    modeltranslation must be a class with the following attribute:

    fields = ('field1', 'field2', ...)

    For example:

    class BlogPostTranslation(object):
        fields = ('title', 'content',)

    """

    if not model in REGISTRY:
        # create a fields dict (models apparently lack this?!)
        fields = dict([(f.name, f) for f in model._meta._fields() if f.name in modeltranslation.fields])

        REGISTRY[model] = fields
        META[model] = modeltranslation

        models.signals.pre_save.connect(_pre_save, sender=model)
        models.signals.post_save.connect(_post_save, sender=model)

        for field in fields.values():
            setattr(model, field.name, FieldDescriptor(field.name))

        # Set new filter method in model manager.
        model.objects.__class__.datatrans_filter = _datatrans_filter


def make_messages(build_digest_list=False):
    """
    This function loops over all the registered models and, when necessary,
    creates KeyValue entries for the fields specified.

    When build_digest_list is True, a list of digests will be created
    for all the translatable data. When it is False, it will return
    the number of processed objects.
    """
    object_count = 0
    digest_list = []

    for model in REGISTRY:
        fields = REGISTRY[model].values()
        objects = model.objects.all()
        for object in objects:
            for field in fields:
                for lang_code, lang_human in settings.LANGUAGES:
                    value = object.__dict__[field.name]
                    if build_digest_list:
                        digest_list.append(make_digest(value))
                    KeyValue.objects.lookup(value, lang_code, object, field.name)
            object_count += 1

    if build_digest_list:
        return digest_list
    else:
        return object_count


def find_obsoletes():
    digest_list = make_messages(build_digest_list=True)
    obsoletes = KeyValue.objects.exclude(digest__in=digest_list)
    return obsoletes

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.template.context import RequestContext
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.contrib.contenttypes.models import ContentType

from datatrans import utils
from datatrans.models import KeyValue
from datatrans.utils import count_model_words

def can_translate(user):
    if not user.is_authenticated():
        return False
    elif user.is_superuser:
        return True
    else:
        group_name = getattr(settings, 'DATATRANS_GROUP_NAME', None)
        if group_name:
            from django.contrib.auth.models import Group
            translators = Group.objects.get(name=group_name)
            return translators in user.groups.all()
        else:
            return user.is_staff


def _get_model_slug(model):
    ct = ContentType.objects.get_for_model(model)
    return u'%s.%s' % (ct.app_label, ct.model)


def _get_model_entry(slug):
    app_label, model_slug = slug.split('.')
    ct = ContentType.objects.get(app_label=app_label, model=model_slug)
    model_class = ct.model_class()
    registry = utils.get_registry()
    if not model_class in registry:
        raise Http404(u'No registered model found for given query.')
    return model_class


def _get_model_stats(model, filter=lambda x: x):
    default_lang = utils.get_default_language()
    registry = utils.get_registry()
    keyvalues = filter(KeyValue.objects.for_model(model, registry[model].values()).exclude(language=default_lang))
    total = keyvalues.count()
    done = keyvalues.filter(edited=True, fuzzy=False).count()
    return (done * 100 / total if total > 0 else 0, done, total)


@user_passes_test(can_translate, settings.LOGIN_URL)
def model_list(request):
    """
    Shows an overview of models to translate, along with the fields, languages
    and progress information.
    The context structure is defined as follows:

    context = {'models': [{'languages': [('nl', 'NL', (<percent_done>, <todo>, <total>)), ('fr', 'FR', (<percent_done>, <todo>, <total>))],
                           'field_names': [u'description'],
                           'stats': (75, 15, 20),
                           'slug': u'flags_app.flag',
                           'model_name': u'flag'}]}
    """
    registry = utils.get_registry()

    default_lang = utils.get_default_language()
    languages = [l for l in settings.LANGUAGES if l[0] != default_lang]

    models = [{'slug': _get_model_slug(model),
               'model_name': u'%s' % model._meta.verbose_name,
               'field_names': [u'%s' % f.verbose_name for f in registry[model].values()],
               'stats': _get_model_stats(model),
               'words': count_model_words(model),
               'languages': [
                    (
                        l[0],
                        l[1],
                        _get_model_stats(
                            model,
                            filter=lambda x: x.filter(language=l[0])
                        ),
                    )
                    for l in languages
                ],
               } for model in registry]

    total_words = sum(m['words'] for m in models)
    context = {'models': models, 'words': total_words}

    return render_to_response('datatrans/model_list.html',
                              context,
                              context_instance=RequestContext(request))


def commit_translations(request):
    translations = [
        (KeyValue.objects.get(pk=int(k.split('_')[1])), v)
        for k, v in request.POST.items() if 'translation_' in k]
    for keyvalue, translation in translations:
        empty = 'empty_%d' % keyvalue.pk in request.POST
        ignore = 'ignore_%d' % keyvalue.pk in request.POST
        if translation != '' or empty or ignore:
            if keyvalue.value != translation:
                if not ignore:
                    keyvalue.value = translation
                keyvalue.fuzzy = False
            if ignore:
                keyvalue.fuzzy = False
            keyvalue.edited = True
            keyvalue.save()


def get_context_object(model, fields, language, default_lang, object):
    object_item = {}
    object_item['name'] = unicode(object)
    object_item['id'] = object.id
    object_item['fields'] = object_fields = []
    for field in fields.values():
        key = model.objects.filter(pk=object.pk).values(field.name)[0][field.name]
        original = KeyValue.objects.get_keyvalue(key, default_lang, object, field.name)
        translation = KeyValue.objects.get_keyvalue(key, language, object, field.name)
        object_fields.append({
            'name': field.name,
            'verbose_name': unicode(field.verbose_name),
            'original': original,
            'translation': translation
        })
    return object_item


def needs_translation(model, fields, language, object):
    for field in fields.values():
        key = model.objects.filter(pk=object.pk).values(field.name)[0][field.name]
        translation = KeyValue.objects.get_keyvalue(key, language)
        if not translation.edited:
            return True
    return False


def editor(request, model, language, objects):
    registry = utils.get_registry()
    fields = registry[model]

    default_lang = utils.get_default_language()
    model_name = u'%s' % model._meta.verbose_name

    first_unedited_translation = None
    object_list = []
    for object in objects:
        context_object = get_context_object(
            model, fields, language, default_lang, object)
        object_list.append(context_object)

        if first_unedited_translation is None:
            for field in context_object['fields']:
                tr = field['translation']
                if not tr.edited:
                    first_unedited_translation = tr
                    break

    context = {'model': model_name,
               'objects': object_list,
               'original_language': default_lang,
               'other_language': language,
               'progress': _get_model_stats(
                   model, lambda x: x.filter(language=language)),
               'first_unedited': first_unedited_translation}

    return render_to_response(
        'datatrans/model_detail.html', context,
        context_instance=RequestContext(request))


def selector(request, model, language, objects):
    fields = utils.get_registry()[model]
    for object in objects:
        if needs_translation(model, fields, language, object):
            object.todo = True
    context = {
        'model': model.__name__,
        'objects': objects
    }
    return render_to_response(
        'datatrans/object_list.html', context,
        context_instance=RequestContext(request))


@user_passes_test(can_translate, settings.LOGIN_URL)
def object_detail(request, slug, language, object_id):
    if request.method == 'POST':
        commit_translations(request)
        return HttpResponseRedirect('.')

    model = _get_model_entry(slug)
    objects = model.objects.filter(id=int(object_id))

    return editor(request, model, language, objects)


@user_passes_test(can_translate, settings.LOGIN_URL)
def model_detail(request, slug, language):
    '''
    The context structure is defined as follows:

    context = {'model': '<name of model>',
               'objects': [{'name': '<name of object>',
                            'fields': [{
                                'name': '<name of field>',
                                'original': '<kv>',
                                'translation': '<kv>'
                            ]}],
             }
    '''

    if request.method == 'POST':
        commit_translations(request)
        return HttpResponseRedirect('.')

    model = _get_model_entry(slug)
    meta = utils.get_meta()[model]
    objects = model.objects.all()
    if getattr(meta, 'one_form_per_object', False):
        return selector(request, model, language, objects)
    else:
        return editor(request, model, language, objects)


@user_passes_test(can_translate, settings.LOGIN_URL)
def make_messages(request):
    utils.make_messages()
    return HttpResponseRedirect(reverse('datatrans_model_list'))


@user_passes_test(can_translate, settings.LOGIN_URL)
def obsolete_list(request):
    from django.db.models import Q

    default_lang = utils.get_default_language()
    all_obsoletes = utils.find_obsoletes().order_by('digest')
    obsoletes = all_obsoletes.filter(Q(edited=True) | Q(language=default_lang))

    if request.method == 'POST':
        all_obsoletes.delete()
        return HttpResponseRedirect(reverse('datatrans_obsolete_list'))

    context = {'obsoletes': obsoletes}
    return render_to_response('datatrans/obsolete_list.html', context, context_instance=RequestContext(request))

########NEW FILE########
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
__FILENAME__ = runtests
#This file mainly exists to allow python setup.py test to work.

import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'test_project.settings'

test_dir = os.path.dirname(__file__)
sys.path.insert(0, test_dir)

from django.test.utils import get_runner
from django.conf import settings

def runtests():
    test_runner = get_runner(settings)
    failures = test_runner().run_tests([])
    sys.exit(failures)

if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.
import os
PROJECT_DIR = os.path.dirname(__file__)


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

#DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = PROJECT_DIR + '/test_settings.db'    # Or path to database file if using sqlite3.
#DATABASE_NAME = 'datatrans'    # Or path to database file if using sqlite3.
DATABASE_USER = 'postgres'             # Not used with sqlite3.
DATABASE_PASSWORD = 'postgres'         # Not used with sqlite3.
DATABASE_HOST = 'localhost'             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = '5432'             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'
LANGUAGES = (('en', 'English'),
             ('ro', 'Romanian'),
             ('hu', 'Hungarian'))

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

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
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '^!e2_=825c67y=x_w&&ks@sr-k)+k@4ksfxj=9e8*uusp(8-u3'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

CACHE_BACKEND = 'locmem://'

ROOT_URLCONF = 'test_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_DIR, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'datatrans',
    'test_project.testapp'
)

try:
    import test_extensions
except ImportError:
    pass
else:
    INSTALLED_APPS += ('test_extensions',)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from testapp.models import Option

class OptionAdmin(admin.ModelAdmin):
    pass

admin.site.register(Option, OptionAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from datatrans.utils import register

# Create your models here.
class Option(models.Model):
    name = models.CharField(_(u'name'), max_length=64)

    class Meta:
        verbose_name = _(u'option')
        verbose_name_plural = _(u'options')

    def __unicode__(self):
        return u'%s' % self.name

# register translations
class OptionTranslation(object):
    fields = ('name',)

register(Option, OptionTranslation)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.conf import settings
try:
    from django.db import DEFAULT_DB_ALIAS
except ImportError:
    pass
from django.utils import translation

from datatrans.models import KeyValue
from datatrans.utils import get_default_language

from test_project.testapp.models import Option
from test_project.testapp.utils import test_concurrently


if hasattr(settings, 'DATABASES'):
    DATABASE_ENGINE = settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']
else:
    DATABASE_ENGINE = settings.DATABASE_ENGINE
USING_POSTGRESQL = DATABASE_ENGINE.startswith('postgresql') or \
    DATABASE_ENGINE.startswith('django.db.backends.postgresql')

class PostgresRegressionTest(TestCase):
    if USING_POSTGRESQL:
        def test_concurrent_inserts_with_same_value_break_pre_save(self):
            @test_concurrently(2)
            def add_new_records():
                value = "test string that does not already exist in db"
                option = Option(name=value)
                option.save()
                count_kv = KeyValue.objects.filter(language=get_default_language(),
                                                   value=value).count()
                self.assertEqual(count_kv, 1,
                                 u"Got %d KeyValues after concurrent insert instead of 1." % count_kv)
            add_new_records()

class RegressionTests(TestCase):
    def test_access_before_save_breaks_pre_save(self):
        translation.activate('en')
        value_en = "test1_en"
        option = Option(name=value_en)
        self.assertEqual(option.name, value_en)
        option.save()

        translation.activate('ro')
        self.assertEqual(option.name, value_en)
        value_ro = "test1_ro"
        option.name = value_ro
        self.assertEqual(option.name, value_ro)
        option.save()
        self.assertEqual(option.name, value_ro)

        translation.activate('en')
        value_en = "test2_en"
        option.name = value_en
        self.assertEqual(option.name, value_en) # this access causes the creation of a new KeyValue for 'en', which
                                                # causes the pre_save handler to skip creation of a new KeyValue for 'ro' language
                                                # and causes the last assertEqual to fail
        option.save()
        self.assertEqual(option.name, value_en)

        translation.activate('ro')
        self.assertEqual(option.name, value_ro)

########NEW FILE########
__FILENAME__ = utils
def test_concurrently(times):
    """
    Add this decorator to small pieces of code that you want to test
    concurrently to make sure they don't raise exceptions when run at the
    same time.  E.g., some Django views that do a SELECT and then a subsequent
    INSERT might fail when the INSERT assumes that the data has not changed
    since the SELECT.
    """
    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []
            import threading
            def call_test_func():
                try:
                    test_func(*args, **kwargs)
                except Exception, e:
                    exceptions.append(e)
                    raise
            threads = []
            for i in range(times):
                threads.append(threading.Thread(target=call_test_func))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                raise Exception('test_concurrently intercepted %s exceptions: %s' % (len(exceptions), exceptions))
        return wrapper
    return test_concurrently_decorator

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from datatrans import urls

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^test_project/', include('test_project.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
     (r'^admin/', include(admin.site.urls)),
     (r'^trans/', include(urls)),
)

########NEW FILE########
