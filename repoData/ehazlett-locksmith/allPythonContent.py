__FILENAME__ = forms
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django import forms
from django.contrib.auth.models import User
from accounts.models import UserProfile

class AccountForm(forms.ModelForm):
    # override the default fields to force them to be required
    # (the django User model doesn't require them)
    def __init__(self, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

class UserProfileForm(forms.ModelForm):
    # override the default fields to force them to be required
    # (the django User model doesn't require them)
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['encryption_key_timeout'].required = True
    class Meta:
        model = UserProfile
        fields = ('encryption_key_timeout',)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table('accounts_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
            ('encryption_key_timeout', self.gf('django.db.models.fields.IntegerField')(default=3600, null=True, blank=True)),
        ))
        db.send_create_signal('accounts', ['UserProfile'])


    def backwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table('accounts_userprofile')


    models = {
        'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'encryption_key_timeout': ('django.db.models.fields.IntegerField', [], {'default': '3600', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_userprofile_is_pro
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserProfile.is_pro'
        db.add_column('accounts_userprofile', 'is_pro',
                      self.gf('django.db.models.fields.NullBooleanField')(default=False, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserProfile.is_pro'
        db.delete_column('accounts_userprofile', 'is_pro')


    models = {
        'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'encryption_key_timeout': ('django.db.models.fields.IntegerField', [], {'default': '3600', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_pro': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_userprofile_pro_join_date
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserProfile.pro_join_date'
        db.add_column('accounts_userprofile', 'pro_join_date',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserProfile.pro_join_date'
        db.delete_column('accounts_userprofile', 'pro_join_date')


    models = {
        'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'encryption_key_timeout': ('django.db.models.fields.IntegerField', [], {'default': '3600', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_pro': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'pro_join_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_userprofile_customer_id
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserProfile.customer_id'
        db.add_column('accounts_userprofile', 'customer_id',
                      self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserProfile.customer_id'
        db.delete_column('accounts_userprofile', 'customer_id')


    models = {
        'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'customer_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'encryption_key_timeout': ('django.db.models.fields.IntegerField', [], {'default': '3600', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_pro': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'pro_join_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = 0005_auto__chg_field_userprofile_customer_id
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'UserProfile.customer_id'
        db.alter_column('accounts_userprofile', 'customer_id', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

    def backwards(self, orm):

        # Changing field 'UserProfile.customer_id'
        db.alter_column('accounts_userprofile', 'customer_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True))

    models = {
        'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'encryption_key_timeout': ('django.db.models.fields.IntegerField', [], {'default': '3600', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_pro': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'pro_join_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_userprofile_activation_code
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserProfile.activation_code'
        db.add_column('accounts_userprofile', 'activation_code',
                      self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserProfile.activation_code'
        db.delete_column('accounts_userprofile', 'activation_code')


    models = {
        'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'activation_code': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'customer_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'encryption_key_timeout': ('django.db.models.fields.IntegerField', [], {'default': '3600', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_pro': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'pro_join_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = models
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from uuid import uuid4
from tastypie.models import create_api_key

class UserProfile(models.Model):
    """
    User profile

    """
    user = models.ForeignKey(User, unique=True)
    encryption_key_timeout = models.IntegerField(default=3600, blank=True,
        null=True)
    is_pro = models.NullBooleanField(default=False, null=True, blank=True)
    pro_join_date = models.DateTimeField(null=True, blank=True)
    customer_id = models.CharField(max_length=64, null=True, blank=True)
    activation_code = models.CharField(max_length=64, null=True, blank=True)

    def __unicode__(self):
        return self.user.username

# create user profile upon save
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        profile, created = UserProfile.objects.get_or_create(user=instance)

models.signals.post_save.connect(create_api_key, sender=User)


########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.contrib.auth.models import User

class AccountsTest(TestCase):
    def setUp(self):
        self._username = 'testuser'
        self._password = 'test1234'
        self.user = User(username=self._username)
        self.user.set_password(self._password)
        self.user.save()
        
    def test_login(self):
        self.client.login(username=self._username, password=self._password)
        resp = self.client.get('/')
        self.assertEqual(resp.context['user'].username, self._username)

    def test_logout(self):
        self.test_login()
        self.client.logout()
        resp = self.client.get('/')
        self.assertNotEqual(resp.context['user'].username, self._username)


########NEW FILE########
__FILENAME__ = urls
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, url

urlpatterns = patterns('accounts.views',
    url(r'^login/$', 'login', name='accounts.login'),
    url(r'^logout/$', 'logout', name='accounts.logout'),
    url(r'^details/$', 'details', name='accounts.details'),
    url(r'^signup/$', 'signup', name='accounts.signup'),
    url(r'^confirm/(?P<code>[\W,\w]+)/$', 'confirm', name='accounts.confirm'),
    url(r'^activate/$', 'activate', name='accounts.activate'),
    url(r'^hook/$', 'hook', name='accounts.hook'),
)

########NEW FILE########
__FILENAME__ = views
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import (authenticate, login as login_user,
    logout as logout_user)
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _
from accounts.forms import AccountForm, UserProfileForm
from accounts.models import UserProfile
from datetime import datetime
from utils import billing
import random
import string
try:
    import simplejson as json
except ImportError:
    import json

@require_http_methods(["GET", "POST"])
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login_user(request, user)
                return redirect(reverse('index'))
            else:
                messages.error(request, _('Your account is disabled.  Make sure you have activated your account.'))
        else:
            messages.error(request, _('Invalid username/password'))
    return render_to_response('accounts/login.html',
        context_instance=RequestContext(request))

def logout(request):
    logout_user(request)
    return redirect(reverse('index'))

@login_required
def details(request):
    ctx = {}
    form = AccountForm(instance=request.user)
    pform = UserProfileForm(instance=request.user.get_profile())
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=request.user)
        pform = UserProfileForm(request.POST,
            instance=request.user.get_profile())
        if form.is_valid() and pform.is_valid():
            form.save()
            pform.save()
            messages.info(request, _('Account updated.'))
    ctx['form'] = form
    ctx['pform'] = pform
    return render_to_response('accounts/details.html', ctx,
        context_instance=RequestContext(request))

def confirm(request, code=None):
    up = UserProfile.objects.get(activation_code=code)
    user = up.user
    user.is_active = True
    user.save()
    messages.success(request, _('Thanks!  You may now login.'))
    return redirect(reverse('accounts.login'))

def signup(request):
    ctx = {}
    if not settings.SIGNUP_ENABLED:
        messages.warning(request, _('Signup is not enabled at this time.'))
        return redirect(reverse('index'))
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        user = User(first_name=first_name, last_name=last_name,
            email=email)
        user.username = username
        user.set_password(password)
        user.is_active = False
        user.save()
        # generate code
        code = ''.join(random.sample(string.letters+string.digits, 16))
        up = user.get_profile()
        up.activation_code = code
        up.save()
        # send welcome
        tmpl = """Thanks for signing up!

Please activate your account by clicking the following link:

http://{0}{1}

Please feel free to request features, submit bug reports, check the wiki, etc.
at https://github.com/ehazlett/locksmith/wiki

If you have any questions please feel free to contact us at support@vitasso.com.

Thanks!
Locksmith Team
""".format(request.get_host(), reverse('accounts.confirm', args=[code]))
        send_mail(_('Welcome to Locksmith!'), tmpl, settings.ADMIN_EMAIL,
            [user.email], fail_silently=True)
        messages.success(request, _('Thanks!  Please check your email to activate.'))
        return redirect(reverse('index'))
    return render_to_response('accounts/signup.html', ctx,
        context_instance=RequestContext(request))

@login_required
def activate(request):
    ctx = {}
    if request.method == 'POST':
        token = request.POST.get('token')
        try:
            customer = billing.create_customer(token, settings.ACCOUNT_PLAN,
                request.user.email)
            up = request.user.get_profile()
            up.customer_id = customer.id
            up.save()
            messages.success(request, _('Thanks for supporting!  Please let us know if you have any questions.'))
            return redirect(reverse('index'))
        except Exception, e:
            messages.error(request, '{0}:{1}'.format(
                _('Error processing payment'), e))
    return render_to_response('accounts/activate.html', ctx,
        context_instance=RequestContext(request))

@csrf_exempt
def hook(request):
    event = json.loads(request.body)
    print(event)
    event_type = event.get('type')
    # subscription payment success
    if event_type == 'invoice.payment_succeeded':
        customer = event.get('data', {}).get('object', {}).get('customer')
        up = UserProfile.objects.get(customer_id=customer)
        if settings.DEBUG or event.get('livemode'):
            up.is_pro = True
            up.pro_join_date = datetime.now()
            up.save()
    # subscription ended
    if event_type == 'customer.subscription.deleted' or \
        event_type == 'charge.refunded' or event_type == 'charge.failed' or \
        event_type == 'customer.subscription.deleted' or \
        event_type == 'invoice.payment_failed':
        customer = event.get('data', {}).get('object', {}).get('customer')
        up = UserProfile.objects.get(customer_id=customer)
        if settings.DEBUG or event.get('livemode'):
            up.is_pro = False
            up.save()
    return HttpResponse(status=200)

########NEW FILE########
__FILENAME__ = admin
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from accounts.models import UserProfile

admin.site.unregister(User)

class UserProfileInline(admin.StackedInline):
    model = UserProfile

class UserProfileAdmin(UserAdmin):
    inlines = (UserProfileInline,)

admin.site.register(User, UserProfileAdmin)

########NEW FILE########
__FILENAME__ = api_v1
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from tastypie.resources import ModelResource
from tastypie.authorization import (DjangoAuthorization, Authorization)
from tastypie.authentication import ApiKeyAuthentication, Authentication
from tastypie.utils import trailing_slash
from tastypie.bundle import Bundle
from tastypie import fields
from django.core.urlresolvers import reverse
from django.conf.urls.defaults import *
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as login_user
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from vault.models import CredentialGroup, Credential
from tastypie.models import ApiKey
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from utils.encryption import (decrypt, set_user_encryption_key,
    get_user_encryption_key)
import simplejson as json
import os

# set csrf exempt to allow mobile login
@csrf_exempt
def api_login(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    if not username:
        # attempt to parse a json string
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
    user = authenticate(username=username, password=password)
    code = 200
    if user is not None:
        login_user(request, user)
        ur = UserResource()
        user_data = ur.obj_get(request, username=user.username)
        bundle = ur.build_bundle(obj=user_data, request=request)
        data = ur.serialize(None, ur.full_dehydrate(bundle),
            'application/json')
    else:
        data = json.dumps({'error': 'Access denied'})
        code = 403
    return HttpResponse(data, status=code,
        content_type='application/json')

class AppAuthentication(Authentication):
    def is_authenticated(self, request, **kwargs):
        # session based
        if request.user.is_authenticated():
            return True
        else: # check api_key
            if request.META.has_key('HTTP_AUTHORIZATION'):
                auth_header = request.META.get('HTTP_AUTHORIZATION')
                key = request.META.get('HTTP_ENCRYPTION_KEY')
                try:
                    username, api_key = auth_header.split()[-1].split(':')
                    # check auth
                    user = User.objects.get(username=username)
                    if user and user.api_key.key == api_key:
                        # set encryption key
                        set_user_encryption_key(user.username, key)
                        # auth successful ; set request.user to user for
                        # later user (authorization, filtering, etc.)
                        request.user = user
                        return True
                except:
                    # invalid auth header
                    pass
        return False

class CredentialGroupAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        return object_list.filter(Q(owner=bundle.request.user) | \
            Q(members__in=bundle.request.user))

    def read_detail(self, object_list, bundle):
        return object_list.filter(Q(owner=bundle.request.user) | \
            Q(members__in=[bundle.request.user]))

    def create_list(self, object_list, bundle):
        return object_list

    def create_detail(self, object_list, bundle):
        return bundle.obj.owner == bundle.request.user

    def update_list(self, object_list, bundle):
        allowed = []

        # Since they may not all be saved, iterate over them.
        for obj in object_list:
            if obj.owner == bundle.request.user:
                allowed.append(obj)
        return allowed

    def update_detail(self, object_list, bundle):
        return bundle.obj.owner == bundle.request.user

    def delete_list(self, object_list, bundle):
        return bundle.obj.owner == bundle.request.user

    def delete_detail(self, object_list, bundle):
        return bundle.obj.owner == bundle.request.user

class CredentialAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        return object_list.filter(groups__owner=bundle.request.user)

    def read_detail(self, object_list, bundle):
        return object_list.filter(groups__owner=bundle.request.user)

    def create_list(self, object_list, bundle):
        return object_list

    def create_detail(self, object_list, bundle):
        return object_list.filter(groups__owner=bundle.request.user)

    def update_list(self, object_list, bundle):
        allowed = []

        # Since they may not all be saved, iterate over them.
        for obj in object_list:
            for g in obj.groups:
                if g.owner == bundle.request.user:
                    allowed.append(obj)
        return allowed

    def update_detail(self, object_list, bundle):
        return object_list.filter(groups__owner=bundle.request.user)

    def delete_list(self, object_list, bundle):
        return object_list.filter(groups__owner=bundle.request.user)

    def delete_detail(self, object_list, bundle):
        return object_list.filter(groups__owner=bundle.request.user)

class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        excludes = ('id', 'password', 'is_staff', 'is_superuser')
        list_allowed_methods = ['get']
        authentication = AppAuthentication()
        authorization = Authorization()
        resource_name = 'accounts'

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<username>[\w\d_.-]+)/$" % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]

    def get_object_list(self, request):
        return super(UserResource, self).get_object_list(request).filter(
            username=request.user.username)

    # only let non-admin users see their own account
    def apply_authorization_limits(self, request, object_list):
        if not request.user.is_superuser:
            object_list = object_list.filter(username=request.user.username)
        return object_list

    # this is broken in tastypie 0.9.13
    ## build custom resource_uri (instead of /resource/<pk>/)
    #def get_resource_uri(self, bundle_or_obj, url_name='api_dispatch_list'):
    #    kwargs = {
    #        'resource_name': self._meta.resource_name,
    #    }
    #    if isinstance(bundle_or_obj, Bundle):
    #        kwargs['pk'] = bundle_or_obj.obj.username
    #    else:
    #        kwargs['pk'] = bundle_or_obj.id
    #    if self._meta.api_name is not None:
    #        kwargs['api_name'] = self._meta.api_name
    #    return self._build_reverse_url('api_dispatch_detail', kwargs = kwargs)

    def dehydrate(self, bundle):
        # add api_key
        bundle.data['api_key'] = bundle.obj.api_key.key
        return bundle

class CredentialGroupResource(ModelResource):
    class Meta:
        queryset = CredentialGroup.objects.all()
        excludes = ('id', )
        #list_allowed_methods = ['get']
        authentication = AppAuthentication()
        authorization = CredentialGroupAuthorization()
        resource_name = 'credentialgroups'
        filtering = {
            "name": ALL,
            "description": ALL,
        }

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<uuid>[\w\d_.-]+)/$" \
                % self._meta.resource_name, self.wrap_view('dispatch_detail'),
                name="api_dispatch_detail"),
        ]

    def apply_authorization_limits(self, request, object_list):
        if not request.user.is_superuser:
            object_list = object_list.filter(owner=request.user)
        return object_list

    # this is broken in tastypie 0.9.13
    # build custom resource_uri (instead of /resource/<pk>/)
    #def get_resource_uri(self, bundle_or_obj, url_name='api_dispatch_list'):
    #    kwargs = {
    #        'resource_name': self._meta.resource_name,
    #    }
    #    if isinstance(bundle_or_obj, Bundle):
    #        kwargs['pk'] = bundle_or_obj.obj.uuid
    #    else:
    #        kwargs['pk'] = bundle_or_obj.id
    #    if self._meta.api_name is not None:
    #        kwargs['api_name'] = self._meta.api_name
    #    return self._build_reverse_url('api_dispatch_detail', kwargs = kwargs)

    def obj_create(self, bundle, **kwargs):
        # set the owner
        kwargs['owner'] = bundle.request.user
        return super(CredentialGroupResource, self).obj_create(bundle, **kwargs)

class CredentialResource(ModelResource):
    groups = fields.ToManyField(CredentialGroupResource, 'groups', full=True)

    class Meta:
        queryset = Credential.objects.all()
        excludes = ('id', )
        #list_allowed_methods = ['get']
        authentication = AppAuthentication()
        authorization = CredentialAuthorization()
        resource_name = 'credentials'
        pass_request_user_to_django = True
        filtering = {
            "name": ALL,
            "description": ALL,
            "url": ALL,
        }

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<uuid>[\w\d_.-]+)/$" % self._meta.resource_name,
                self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
        ]

    # this is broken in tastypie 0.9.13
    # build custom resource_uri (instead of /resource/<pk>/)
    #def get_resource_uri(self, bundle_or_obj, url_name='api_dispatch_list'):
    #    kwargs = {
    #        'resource_name': self._meta.resource_name,
    #    }
    #    if isinstance(bundle_or_obj, Bundle):
    #        kwargs['pk'] = bundle_or_obj.obj.uuid
    #    else:
    #        kwargs['pk'] = bundle_or_obj.id
    #    if self._meta.api_name is not None:
    #        kwargs['api_name'] = self._meta.api_name
    #    return self._build_reverse_url('api_dispatch_detail', kwargs = kwargs)

    #def apply_authorization_limits(self, request, object_list):
    #    return object_list.filter(owner=request.user)

    def dehydrate(self, bundle):
        u = bundle.request.user
        key = get_user_encryption_key(u.username)
        try:
            bundle.data['password'] = decrypt(bundle.data['password'],
                key)
        except:
            bundle.data['password'] = None
        return bundle

########NEW FILE########
__FILENAME__ = context_processors
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf import settings
from django.core.cache import cache
from utils.encryption import get_user_encryption_key

def app_info(request):
    return {
        'APP_NAME': getattr(settings, 'APP_NAME'),
        'APP_REVISION': getattr(settings, 'APP_REVISION'),
    }

def google_analytics_code(request):
    return { 'GOOGLE_ANALYTICS_CODE': getattr(settings, 'GOOGLE_ANALYTICS_CODE')}

def stripe_info(request):
    return {
        'STRIPE_API_KEY': getattr(settings, 'STRIPE_API_KEY'),
        'STRIPE_PUBLISHABLE_KEY': getattr(settings, 'STRIPE_PUBLISHABLE_KEY'),
    }

def intercom_app_id(request):
    return { 'INTERCOM_APP_ID': getattr(settings, 'INTERCOM_APP_ID')}

def encryption_key(request):
    u = request.user
    key = get_user_encryption_key(u.username)
    return { 'ENCRYPTION_KEY': key }

def signup_enabled(request):
    return { 'SIGNUP_ENABLED': getattr(settings, 'SIGNUP_ENABLED')}

########NEW FILE########
__FILENAME__ = threadlocal
# coding: utf-8
# Copied from https://github.com/jedie/django-tools/blob/master/django_tools/middlewares/ThreadLocal.py
try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()

def get_current_request():
    """ returns the request object for this thead """
    return getattr(_thread_locals, "request", None)

def get_current_user():
    """ returns the current user, if exist, otherwise returns None """
    request = get_current_request()
    if request:
        return getattr(request, "user", None)

def get_current_session():
    """ returns the current user, if exist, otherwise returns None """
    request = get_current_request()
    if request:
        return getattr(request, "session", None)

class ThreadLocalMiddleware(object):
    """ Simple middleware that adds the request object in thread local storage."""
    def process_request(self, request):
        _thread_locals.request = request

########NEW FILE########
__FILENAME__ = settings
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Django settings for locksmith project.
import os
import subprocess
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '../')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

APP_NAME = 'locksmith'
# get latest git revision
process = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE)
out, err = process.communicate()

APP_REVISION = out[:6]
ADMINS = (
    ('Evan Hazlett', 'ejhazlett@gmail.com'),
)
ADMIN_EMAIL = 'support@vitasso.com'

AUTH_PROFILE_MODULE = 'accounts.UserProfile'
MANAGERS = ADMINS

BCRYPT_ENABLED = True
BCRYPT_ROUNDS = 12
BCRYPT_MIGRATE = True

SENTRY_DSN = ''
SIGNUP_ENABLED = True

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
AWS_STORAGE_BUCKET_NAME = 'locksmith'

CACHE_ENCRYPTION_KEY = '{0}:key'


# arcus cloud settings
if 'VCAP_SERVICES' in os.environ:
    import json
    vcap_services = json.loads(os.environ['VCAP_SERVICES'])
    mysql_srv = vcap_services['mysql-5.1'][0]
    redis_srv = vcap_services['redis-2.6'][0]
    memcached_srv = vcap_services['memcached-1.4'][0]
    elasticsearch_srv = vcap_services['elasticsearch-0.19'][0]
    mysql_creds = mysql_srv['credentials']
    redis_creds = redis_srv['credentials']
    memcached_creds = memcached_srv['credentials']
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': mysql_creds['name'],
            'USER': mysql_creds['user'],
            'PASSWORD': mysql_creds['password'],
            'HOST': mysql_creds['hostname'],
            'PORT': mysql_creds['port'],
        }
    }
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '{0}:{1}'.format(memcached_creds['host'],
                memcached_creds['port']),
        }
    }
    REDIS_HOST = redis_creds['host']
    REDIS_PORT = redis_creds['port']
    REDIS_DB = 0
    REDIS_PASSWORD = redis_creds['password']
    RQ_QUEUES = {
        'default': {
            'HOST': REDIS_HOST,
            'PORT': REDIS_PORT,
            'DB': REDIS_DB,
            'PASSWORD': REDIS_PASSWORD,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'locksmith.db',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }
    }
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6739
    REDIS_DB = 0
    REDIS_PASSWORD = None
    RQ_QUEUES = {
        'default': {
            'HOST': REDIS_HOST,
            'PORT': REDIS_PORT,
            'DB': REDIS_DB,
            'PASSWORD': REDIS_PASSWORD,
        }
    }

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

GOOGLE_ANALYTICS_CODE = ''
INTERCOM_APP_ID = ''
STRIPE_API_KEY = ''
STRIPE_PUBLISHABLE_KEY = ''
ACCOUNT_PLAN = 'locksmith-pro' # stripe plan

# auth backends
AUTHENTICATION_BACKENDS = (
    'social_auth.backends.twitter.TwitterBackend',
    'social_auth.backends.google.GoogleOAuth2Backend',
    'social_auth.backends.contrib.github.GithubBackend',
    'django.contrib.auth.backends.ModelBackend',
)
# these are placeholders ; set in local_settings.py to deploy
TWITTER_CONSUMER_KEY         = ''
TWITTER_CONSUMER_SECRET      = ''
FACEBOOK_APP_ID              = ''
FACEBOOK_API_SECRET          = ''
LINKEDIN_CONSUMER_KEY        = ''
LINKEDIN_CONSUMER_SECRET     = ''
ORKUT_CONSUMER_KEY           = ''
ORKUT_CONSUMER_SECRET        = ''
GOOGLE_CONSUMER_KEY          = ''
GOOGLE_CONSUMER_SECRET       = ''
GOOGLE_OAUTH2_CLIENT_ID      = ''
GOOGLE_OAUTH2_CLIENT_SECRET  = ''
FOURSQUARE_CONSUMER_KEY      = ''
FOURSQUARE_CONSUMER_SECRET   = ''
VK_APP_ID                    = ''
VK_API_SECRET                = ''
LIVE_CLIENT_ID               = ''
LIVE_CLIENT_SECRET           = ''
SKYROCK_CONSUMER_KEY         = ''
SKYROCK_CONSUMER_SECRET      = ''
YAHOO_CONSUMER_KEY           = ''
YAHOO_CONSUMER_SECRET        = ''
READABILITY_CONSUMER_SECRET  = ''
READABILITY_CONSUMER_SECRET  = ''
GITHUB_APP_ID                = ''
GITHUB_API_SECRET            = ''
GITHUB_EXTENDED_PERMISSIONS = ['user', 'user:email']

# more social auth settings
#LOGIN_URL = '/login-form/'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGIN_ERROR_URL = '/login-error/'
SOCIAL_AUTH_COMPLETE_URL_NAME = 'socialauth_complete'
SOCIAL_AUTH_ASSOCIATE_URL_NAME = 'socialauth_associate_complete'
# needed due to InnoDB storage restriction
# ideally we'd use Postgres, but it has issues in Arcus Cloud at the moment
# see https://github.com/omab/django-social-auth/issues/539 for details
SOCIAL_AUTH_UID_LENGTH = 222
SOCIAL_AUTH_NONCE_SERVER_URL_LENGTH = 200
SOCIAL_AUTH_ASSOCIATION_SERVER_URL_LENGTH = 135
SOCIAL_AUTH_ASSOCIATION_HANDLE_LENGTH = 125


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'z)h81*4eitd6k=8%&amp;i164h0fukf3p(fe8cpo*g&amp;vc2h@n8aba%'

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
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "locksmith.context_processors.app_info",
    "locksmith.context_processors.google_analytics_code",
    "locksmith.context_processors.encryption_key",
    "locksmith.context_processors.intercom_app_id",
    "locksmith.context_processors.signup_enabled",
    "locksmith.context_processors.stripe_info",
    'social_auth.context_processors.social_auth_by_name_backends',
    'social_auth.context_processors.social_auth_backends',
    'social_auth.context_processors.social_auth_login_redirect',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'locksmith.middleware.threadlocal.ThreadLocalMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'locksmith.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'locksmith.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'social_auth',
    'django_forms_bootstrap',
    'south',
    'tastypie',
    'django_bcrypt',
    'locksmith',
    'accounts',
    'vault',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'WARNING',
        'handlers': ['console', 'sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    }
}

try:
    from local_settings import *
except ImportError:
    pass

if AWS_ACCESS_KEY_ID:
    STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

# these must come after the above local_settings import in order to
# check for values in local_settings
if SENTRY_DSN:
    INSTALLED_APPS = INSTALLED_APPS + (
        'raven.contrib.django.raven_compat',
    )
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
        'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    )


########NEW FILE########
__FILENAME__ = locksmith
from django import template
from django.template.defaultfilters import stringfilter
from datetime import datetime
from django.utils.translation import ugettext as _
from utils.encryption import decrypt

register = template.Library()

@register.filter(takes_context=True)
@stringfilter
def decrypt(context, data=None):
    request = context['request']
    key = request.session.get('key')
    try:
        dec = decrypt(data, key)
    except:
        dec = _('access denied')
    return dec

@register.filter
def timestamp(value):
    try:
        return datetime.fromtimestamp(value)
    except AttributeError:
        return ''

########NEW FILE########
__FILENAME__ = urls
import os
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from tastypie.api import Api
from locksmith.api_v1 import (UserResource, CredentialGroupResource,
    CredentialResource)

admin.autodiscover()

# api
api_v1 = Api(api_name='v1')
api_v1.register(UserResource())
api_v1.register(CredentialGroupResource())
api_v1.register(CredentialResource())

urlpatterns = patterns('',
    url(r'^$', 'locksmith.views.index', name='index'),
    url(r'^about/$', 'locksmith.views.about', name='about'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include(api_v1.urls)),
    url(r'^api/login', 'locksmith.api_v1.api_login'),
    url(r'^auth/(?P<backend>[^/]+)/$',
        'locksmith.views.register_by_access_token'),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^vault/', include('vault.urls')),
    url(r'', include('social_auth.urls')),
)

########NEW FILE########
__FILENAME__ = views
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as login_user
from django.core.urlresolvers import reverse
from locksmith.api_v1 import UserResource
from social_auth.decorators import dsa_view
import datetime

def index(request):
    ctx = {}
    if request.user.is_authenticated():
        return redirect(reverse('vault.views.index'))
    else:
        return render_to_response('index.html', ctx,
            context_instance=RequestContext(request))

def about(request):
    ctx = {}
    return render_to_response('about.html', ctx,
        context_instance=RequestContext(request))

@dsa_view()
def register_by_access_token(request, backend, *args, **kwargs):
    access_token = request.GET.get('access_token')
    user = backend.do_auth(access_token)
    code = 200
    if user and user.is_active:
        login_user(request, user)
        ur = UserResource()
        user_data = ur.obj_get(request, username=user.username)
        bundle = ur.build_bundle(obj=user_data, request=request)
        data = ur.serialize(None, ur.full_dehydrate(bundle),
            'application/json')
    else:
        data = json.dumps({'error': 'Access denied'})
        code = 403
    return HttpResponse(data, status=code,
        content_type='application/json')


########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for locksmith project.

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
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "locksmith.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "locksmith.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = billing
#!/usr/bin/env python
# Copyright 2012 Evan Hazlett
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import stripe
from django.conf import settings
from django.utils.translation import ugettext as _

# set stripe api key
stripe.api_key = getattr(settings, 'STRIPE_API_KEY')

def create_customer(token=None, plan=None, email=None):
    customer = stripe.Customer.create(
        card=token,
        plan=plan,
        email=email
    )
    return customer

def charge(amount=None, currency='usd', card_number=None,
    card_exp_month=None, card_exp_year=None, card_cvc=None, card_name=None,
    description='Locksmith Payment'):
    """
    Charges specified credit card for account
    
    :param amount: Amount in dollars
    :param currency: Currency (default: usd)
    :param card_number: Credit card number
    :param card_exp_month: Credit card expiration month (two digit integer)
    :param card_exp_year: Credit card expiration year (two or four digit integer)
    :param card_cvc: Credit card CVC
    :param card_name: Credit cardholder name
    :param description: Charge description (default: Locksmith Payment)

    """
    # convert amount to cents
    amount = int(amount * 100)
    card_info = {
        'number': card_number.replace('-', ''),
        'exp_month': card_exp_month,
        'exp_year': card_exp_year,
        'cvc': card_cvc,
        'name': card_name,
    }
    data = {}
    try:
        charge = stripe.Charge.create(amount=amount, currency=currency, card=card_info,
            description=description)
        if charge.paid:
            data['status'] = True
            data['message'] = _('Thanks!')
        else:
            data['status'] = False
            data['message'] = charge.failure_message
        data['created'] = charge.created
    except Exception, e:
        data['status'] = False
        data['message'] = e
    return data

########NEW FILE########
__FILENAME__ = encryption
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import hashlib
from Crypto.Cipher import AES
from django.utils.translation import ugettext as _
import base64
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
import string
import random

def generate_password(length=16):
    """
    Generates a new random password
    
    :param length: Length of password

    """
    return ''.join(random.sample(string.letters+string.digits, length))

def set_user_encryption_key(username=None, key=None, ttl=None):
    """
    Sets the encryption key for the specified user

    """
    if not ttl:
        u = User.objects.get(username=username)
        ttl = u.get_profile().encryption_key_timeout
    cache.set(settings.CACHE_ENCRYPTION_KEY.format(username), key,
        timeout=ttl)

def get_user_encryption_key(username=None):
    """
    Gets the encryption key for the specified user

    """
    return cache.get(settings.CACHE_ENCRYPTION_KEY.format(username))

def clear_user_encryption_key(username=None):
    """
    Clears the encryption key for the specified user

    """
    cache.delete(settings.CACHE_ENCRYPTION_KEY.format(username))

def hash_text(text):
    """
    Hashes text with app key

    :param text: Text to encrypt

    """
    h = hashlib.sha256()
    h.update(getattr(settings, 'SECRET_KEY'))
    h.update(text)
    return h.hexdigest()

def _get_padded_key(key=None):
    if len(key) < 16:
        pad = 16 - len(key)
        k = key + ('^'*pad)
    else:
        k = key[:16]
    return k

def encrypt(data=None, key=None):
    """
    Encrypts data

    :param data: Data to encrypt
    :param key: Encryption key (salt)

    """
    k = _get_padded_key(key)
    e = AES.new(k, AES.MODE_CFB, k[::-1])
    enc = e.encrypt(data)
    return base64.b64encode(enc)

def decrypt(data=None, key=None):
    """
    Decrypts data

    :param data: Encrypted data to decrypt
    :param key: Encryption key (salt)

    """
    k = _get_padded_key(key)
    e = AES.new(k, AES.MODE_CFB, k[::-1])
    dec = e.decrypt(base64.b64decode(data))
    try:
        unicode(dec)
    except:
        dec = ''
    return dec

########NEW FILE########
__FILENAME__ = admin
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.contrib import admin
from vault.models import CredentialGroup, Credential

admin.site.register(CredentialGroup)

########NEW FILE########
__FILENAME__ = forms
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django import forms
from vault.models import CredentialGroup, Credential

class CredentialGroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CredentialGroupForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = True
    class Meta:
        model = CredentialGroup
        fields = ('name', 'description')

class CredentialForm(forms.ModelForm):
    class Meta:
        model = Credential

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Credential'
        db.create_table('vault_credential', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('key', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('vault', ['Credential'])


    def backwards(self, orm):
        # Deleting model 'Credential'
        db.delete_table('vault_credential')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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
        },
        'vault.credential': {
            'Meta': {'object_name': 'Credential'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['vault']
########NEW FILE########
__FILENAME__ = 0002_auto__add_credentialgroup__del_field_credential_owner__add_field_crede
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CredentialGroup'
        db.create_table('vault_credentialgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='credential_group_owner', null=True, to=orm['auth.User'])),
        ))
        db.send_create_signal('vault', ['CredentialGroup'])

        # Adding M2M table for field members on 'CredentialGroup'
        db.create_table('vault_credentialgroup_members', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('credentialgroup', models.ForeignKey(orm['vault.credentialgroup'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('vault_credentialgroup_members', ['credentialgroup_id', 'user_id'])

        # Deleting field 'Credential.owner'
        db.delete_column('vault_credential', 'owner_id')

        # Adding field 'Credential.group'
        db.add_column('vault_credential', 'group',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vault.CredentialGroup'], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'CredentialGroup'
        db.delete_table('vault_credentialgroup')

        # Removing M2M table for field members on 'CredentialGroup'
        db.delete_table('vault_credentialgroup_members')

        # Adding field 'Credential.owner'
        db.add_column('vault_credential', 'owner',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Credential.group'
        db.delete_column('vault_credential', 'group_id')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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
        },
        'vault.credential': {
            'Meta': {'object_name': 'Credential'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vault.CredentialGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'vault.credentialgroup': {
            'Meta': {'object_name': 'CredentialGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'credential_group_members'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'credential_group_owner'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['vault']
########NEW FILE########
__FILENAME__ = 0003_auto__del_field_credential_group
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Credential.group'
        db.delete_column('vault_credential', 'group_id')

        # Adding M2M table for field groups on 'Credential'
        db.create_table('vault_credential_groups', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('credential', models.ForeignKey(orm['vault.credential'], null=False)),
            ('credentialgroup', models.ForeignKey(orm['vault.credentialgroup'], null=False))
        ))
        db.create_unique('vault_credential_groups', ['credential_id', 'credentialgroup_id'])


    def backwards(self, orm):
        # Adding field 'Credential.group'
        db.add_column('vault_credential', 'group',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vault.CredentialGroup'], null=True, blank=True),
                      keep_default=False)

        # Removing M2M table for field groups on 'Credential'
        db.delete_table('vault_credential_groups')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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
        },
        'vault.credential': {
            'Meta': {'object_name': 'Credential'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['vault.CredentialGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'vault.credentialgroup': {
            'Meta': {'object_name': 'CredentialGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'credential_group_members'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'credential_group_owner'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['vault']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_credentialgroup_name__add_field_credentialgroup_descri
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'CredentialGroup.name'
        db.add_column('vault_credentialgroup', 'name',
                      self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True),
                      keep_default=False)

        # Adding field 'CredentialGroup.description'
        db.add_column('vault_credentialgroup', 'description',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'CredentialGroup.name'
        db.delete_column('vault_credentialgroup', 'name')

        # Deleting field 'CredentialGroup.description'
        db.delete_column('vault_credentialgroup', 'description')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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
        },
        'vault.credential': {
            'Meta': {'object_name': 'Credential'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['vault.CredentialGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'vault.credentialgroup': {
            'Meta': {'object_name': 'CredentialGroup'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'credential_group_members'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'credential_group_owner'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['vault']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_credential_uuid__add_field_credentialgroup_uuid
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Credential.uuid'
        db.add_column('vault_credential', 'uuid',
                      self.gf('django.db.models.fields.CharField')(default='6f2fae29-03f9-4daa-8e71-8bf965d43008', max_length=36, null=True, blank=True),
                      keep_default=False)

        # Adding field 'CredentialGroup.uuid'
        db.add_column('vault_credentialgroup', 'uuid',
                      self.gf('django.db.models.fields.CharField')(default='5045c41b-f9cb-4265-a4ff-a00fac0d5ae4', max_length=36, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Credential.uuid'
        db.delete_column('vault_credential', 'uuid')

        # Deleting field 'CredentialGroup.uuid'
        db.delete_column('vault_credentialgroup', 'uuid')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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
        },
        'vault.credential': {
            'Meta': {'object_name': 'Credential'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['vault.CredentialGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'e6a4765f-3704-4f55-ad0e-c6d6f3b9823b'", 'max_length': '36', 'null': 'True', 'blank': 'True'})
        },
        'vault.credentialgroup': {
            'Meta': {'object_name': 'CredentialGroup'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'credential_group_members'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'credential_group_owner'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'c7581278-b58b-479b-bb46-ab2389313cf0'", 'max_length': '36', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['vault']
########NEW FILE########
__FILENAME__ = 0006_auto__del_field_credential_key__add_field_credential_username__add_fie
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Credential.key'
        db.delete_column('vault_credential', 'key')

        # Adding field 'Credential.username'
        db.add_column('vault_credential', 'username',
                      self.gf('django.db.models.fields.CharField')(max_length=96, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Credential.password'
        db.add_column('vault_credential', 'password',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Credential.key'
        db.add_column('vault_credential', 'key',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Deleting field 'Credential.username'
        db.delete_column('vault_credential', 'username')

        # Deleting field 'Credential.password'
        db.delete_column('vault_credential', 'password')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
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
        },
        'vault.credential': {
            'Meta': {'object_name': 'Credential'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['vault.CredentialGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'fcfc33de-6751-43c2-8b2b-6720e62959d7'", 'max_length': '36', 'null': 'True', 'blank': 'True'})
        },
        'vault.credentialgroup': {
            'Meta': {'object_name': 'CredentialGroup'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'credential_group_members'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'credential_group_owner'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'90b3abf8-00fe-46c3-8a37-8c0e0331b4f1'", 'max_length': '36', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['vault']
########NEW FILE########
__FILENAME__ = models
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from uuid import uuid4
from utils.encryption import encrypt, get_user_encryption_key
from locksmith.middleware import threadlocal

def generate_uuid():
    return str(uuid4())

class CredentialGroup(models.Model):
    uuid = models.CharField(max_length=36, blank=True, null=True,
        default=generate_uuid)
    name = models.CharField(max_length=64, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, blank=True, null=True,
        related_name='credential_group_owner')
    members = models.ManyToManyField(User, blank=True, null=True,
        related_name='credential_group_members')

    def __unicode__(self):
        return '{0}: {1}'.format(self.owner.username, self.name)

    def get_credentials(self):
        return Credential.objects.filter(groups__in=[self])

class Credential(models.Model):
    uuid = models.CharField(max_length=36, blank=True, null=True,
        default=generate_uuid)
    name = models.CharField(max_length=64, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    username = models.CharField(max_length=96, blank=True, null=True)
    password = models.TextField(blank=True, null=True)
    groups = models.ManyToManyField(CredentialGroup, blank=True, null=True)

    def __unicode__(self):
        return '{0}: {1}'.format(','.join([x.name for x in self.groups.all()]),
            self.name)

    def save(self, *args, **kwargs):
        user = threadlocal.get_current_user()
        key = get_user_encryption_key(user.username) or kwargs.get('key')
        # if no key throw error
        if not key:
            raise StandardError("If calling save from outside of a request, " \
                "you must specify 'key' as a kwarg")
        self.password = encrypt(self.password, key)
        super(Credential, self).save(*args, **kwargs)

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
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.conf.urls import patterns, url

urlpatterns = patterns('vault.views',
    url(r'^$', 'index', name='vault.index'),
    url(r'^groups/(?P<uuid>\w{8}-\w{4}-\w{4}-\w{4}-\w{12})/$', 'group',
        name='vault.group'),
    url(r'^setkey/$', 'set_key', name='vault.set_key'),
    url(r'^lock/$', 'lock_session', name='vault.lock_session'),
    url(r'^genpass/$', 'random_password', name='vault.random_password'),
    url(r'^checksession/$', 'check_session', name='vault.check_session'),
)

########NEW FILE########
__FILENAME__ = views
# Copyright 2013 Evan Hazlett and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, Http404
from django.utils.translation import ugettext as _
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.conf import settings
from django.contrib import messages
from vault.models import CredentialGroup, Credential
from vault.forms import CredentialGroupForm
from utils.encryption import (set_user_encryption_key, clear_user_encryption_key,
    get_user_encryption_key, generate_password)
try:
    import simplejson as json
except ImportError:
    import json

@login_required
def index(request):
    ctx = {}
    try:
        groups = CredentialGroup.objects.filter(Q(owner=request.user) | \
            Q(members__in=[request.user])).order_by('name')
        ctx['credential_groups'] = groups
    except CredentialGroup.DoesNotExist:
        raise Http404()
    return render_to_response('vault/index.html', ctx,
        context_instance=RequestContext(request))

@login_required
def group(request, uuid=None):
    ctx = {}
    try:
        group = CredentialGroup.objects.get(Q(owner=request.user) | \
            Q(members__in=[request.user]), uuid=uuid)
        ctx['group'] = group
    except CredentialGroup.DoesNotExist:
        raise Http404()
    return render_to_response('vault/group.html', ctx,
        context_instance=RequestContext(request))

@login_required
@require_http_methods(["POST"])
def set_key(request):
    nxt = request.GET.get('next', reverse('index'))
    key = request.POST.get('key')
    u = request.user
    set_user_encryption_key(u.username, key)
    return redirect(nxt)

@login_required
def lock_session(request):
    nxt = request.GET.get('next', reverse('index'))
    clear_user_encryption_key(request.user.username)
    return redirect(nxt)

@login_required
def random_password(request):
    return HttpResponse(generate_password())

@login_required
def check_session(request):
    key = get_user_encryption_key(request.user.username)
    if key:
        key = True
    else:
        key = False
    data = {
        'status': key,
    }
    return HttpResponse(json.dumps(data), content_type='application/json')

########NEW FILE########
__FILENAME__ = wsgi
from locksmith import wsgi
#import newrelic.agent
application = wsgi.application

#newrelic.agent.initialize('newrelic.ini')
#app = newrelic.agent.wsgi_application()(app)

########NEW FILE########
