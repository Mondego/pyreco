__FILENAME__ = admin
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import reversion
from django.contrib.gis import admin
from models import EmailDomain, Organization, UserAuthorization, UserProfile


class ObjectAdmin(reversion.VersionAdmin,):
    pass


class EmailDomainInline(admin.TabularInline):
    model = EmailDomain
    extra = 5


class EmailDomainAdmin(ObjectAdmin):
    pass


class OrganizationAdmin(ObjectAdmin):
    inlines = [EmailDomainInline]
    pass


# Unregister userena's admin to add to it.
admin.site.unregister(UserProfile)
class UserProfileAdmin(ObjectAdmin):
    list_display = ('user', 'organization', 'score')
    readonly_fields = ('email',)

    def __unicode__(self):
        return self.user.organization


class UserAuthorizationAdmin(ObjectAdmin):
    list_display = ('user', 'Organization', 'Email', 'authorized')
    list_editable = ('authorized',)
    readonly_fields = ('permissions_granted_by',)

    list_filter = ('user_profile__organization',)
    raw_id_admin = ('user_profile',)

    def Organization(self, obj):
        return '%s' % (obj.user_profile.organization)

    def Email(self, obj):
        return '%s' % (obj.user.email)

# TODO:Accounts -- bring this back
#admin.site.register(EmailDomain, EmailDomainAdmin)
#admin.site.register(Organization, OrganizationAdmin)
#admin.site.register(UserProfile, UserProfileAdmin)
#admin.site.register(UserAuthorization, UserAuthorizationAdmin)

########NEW FILE########
__FILENAME__ = forms
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django import forms
from django.utils.translation import ugettext_lazy as _

from userena.forms import SignupForm


class SignupFormExtra(SignupForm):
    """
    A form to demonstrate how to add extra fields to the signup form, in this
    case adding the first and last name.
    """
    first_name = forms.CharField(label=_(u'First name'),
                                 max_length=30,
                                 required=False)

    last_name = forms.CharField(label=_(u'Last name'),
                                max_length=30,
                                required=False)

    def __init__(self, *args, **kw):
        """

        A bit of hackery to get the first name and last name at the top of the
        form instead at the end.

        """
        super(SignupFormExtra, self).__init__(*args, **kw)
        # Put the first and last name at the top
        new_order = self.fields.keyOrder[:-2]
        new_order.insert(0, 'first_name')
        new_order.insert(1, 'last_name')
        self.fields.keyOrder = new_order

    def save(self):
        """
        Override the save method to save the first and last name to the user
        field.

        """
        # First save the parent form and get the user.
        new_user = super(SignupFormExtra, self).save()

        new_user.first_name = self.cleaned_data['first_name']
        new_user.last_name = self.cleaned_data['last_name']
        new_user.save()

        # Userena expects to get the new user from this form, so return the new
        # user.
        return new_user
########NEW FILE########
__FILENAME__ = meta_badges
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import badges
from core.models import AOI

class AOICompleter(badges.MetaBadge):
    id = "AOICompleter"
    model = AOI
    one_time_only = False
    title = "AOI Completer"
    level = "1"
    def check_aoi(self,instance):
        if instance.analyst and instance.status == "Completed":
            newscore = AOI.objects.filter(analyst=instance.analyst,status="Completed").count() * 5 + 1
            instance.analyst.get_profile().score = newscore
            instance.analyst.get_profile().save()

            # TODO: not really using score at the moment, just giving the badge to them
            # do a check against badgesettings to see if they've really earned this

            return True
        return False
    def get_user(self,instance):
        return instance.analyst


class MultiJobCompleter(badges.MetaBadge):
    id = "MultiJobCompleter"
    model = AOI
    one_time_only = False
    title = "MultiJobCompleter"
    level = "2"

    def check_aoi(self, instance):
        if instance.analyst and instance.status == "Completed":
            # Score will get updated above
            jobs = set([aoi.job for aoi in AOI.objects.filter(analyst=instance.analyst,status="Completed")])
            return len(jobs) > 1
        return False
    def get_user(self,instance):
        return instance.analyst

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
        db.create_table(u'accounts_userprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mugshot', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('privacy', self.gf('django.db.models.fields.CharField')(default='registered', max_length=15)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='my_profile', unique=True, to=orm['auth.User'])),
        ))
        db.send_create_signal(u'accounts', ['UserProfile'])


    def backwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table(u'accounts_userprofile')


    models = {
        u'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'my_profile'", 'unique': 'True', 'to': u"orm['auth.User']"})
        },
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = 0002_auto__add_organization__add_unique_organization_name_primary_contact__
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Organization'
        db.create_table(u'accounts_organization', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('primary_contact', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal(u'accounts', ['Organization'])

        # Adding unique constraint on 'Organization', fields ['name', 'primary_contact']
        db.create_unique(u'accounts_organization', ['name', 'primary_contact_id'])

        # Adding field 'UserProfile.organization'
        db.add_column(u'accounts_userprofile', 'organization',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounts.Organization'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Removing unique constraint on 'Organization', fields ['name', 'primary_contact']
        db.delete_unique(u'accounts_organization', ['name', 'primary_contact_id'])

        # Deleting model 'Organization'
        db.delete_table(u'accounts_organization')

        # Deleting field 'UserProfile.organization'
        db.delete_column(u'accounts_userprofile', 'organization_id')


    models = {
        u'accounts.organization': {
            'Meta': {'unique_together': "(('name', 'primary_contact'),)", 'object_name': 'Organization'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'primary_contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.Organization']", 'null': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'my_profile'", 'unique': 'True', 'to': u"orm['auth.User']"})
        },
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_userprofile_score
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserProfile.score'
        db.add_column(u'accounts_userprofile', 'score',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserProfile.score'
        db.delete_column(u'accounts_userprofile', 'score')


    models = {
        u'accounts.organization': {
            'Meta': {'unique_together': "(('name', 'primary_contact'),)", 'object_name': 'Organization'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'primary_contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.Organization']", 'null': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = 0004_auto__add_userauthorization__add_emaildomain__add_field_userprofile_em
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserAuthorization'
        db.create_table(u'accounts_userauthorization', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('authorized', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('permissions_granted_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='permissions_granted_by', null=True, to=orm['auth.User'])),
            ('permission_granted_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2014, 1, 1, 0, 0), auto_now_add=True, blank=True)),
            ('user_profile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounts.UserProfile'])),
        ))
        db.send_create_signal(u'accounts', ['UserAuthorization'])

        # Adding model 'EmailDomain'
        db.create_table(u'accounts_emaildomain', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email_domain', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounts.Organization'])),
        ))
        db.send_create_signal(u'accounts', ['EmailDomain'])

        # Adding field 'UserProfile.email'
        db.add_column(u'accounts_userprofile', 'email',
                      self.gf('django.db.models.fields.CharField')(max_length=250, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'UserAuthorization'
        db.delete_table(u'accounts_userauthorization')

        # Deleting model 'EmailDomain'
        db.delete_table(u'accounts_emaildomain')

        # Deleting field 'UserProfile.email'
        db.delete_column(u'accounts_userprofile', 'email')


    models = {
        u'accounts.emaildomain': {
            'Meta': {'object_name': 'EmailDomain'},
            'email_domain': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.Organization']"})
        },
        u'accounts.organization': {
            'Meta': {'unique_together': "(('name', 'primary_contact'),)", 'object_name': 'Organization'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'primary_contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'accounts.userauthorization': {
            'Meta': {'object_name': 'UserAuthorization'},
            'authorized': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permission_granted_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2014, 1, 1, 0, 0)', 'auto_now_add': 'True', 'blank': 'True'}),
            'permissions_granted_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'permissions_granted_by'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'user_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.UserProfile']"})
        },
        u'accounts.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mugshot': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['accounts.Organization']", 'null': 'True', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'registered'", 'max_length': '15'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['accounts']
########NEW FILE########
__FILENAME__ = models
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from datetime import datetime
from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from django.template.defaultfilters import slugify

from userena.models import UserenaBaseProfile


class Organization(models.Model):
    name = models.CharField(max_length=250)
    primary_contact = models.ForeignKey(User, help_text="Contact for org.")

    class Meta:
        unique_together = ('name', 'primary_contact')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
            Adds a permissions group for the organization if one
            doesn't exist.
        """
        org_name = 'org-%s' % slugify(self.name)
        try:
            group_chk = Group.objects.get(name=org_name)
        except Group.DoesNotExist:
            Group.objects.create(name=org_name)

        super(Organization, self).save(*args, **kwargs)


class EmailDomain(models.Model):
    email_domain = models.CharField(max_length=50)
    organization = models.ForeignKey(Organization)

    def __str__(self):
        return self.email_domain


class UserProfile(UserenaBaseProfile):
    user = models.OneToOneField(User,
                                unique=True,
                                verbose_name=_('user'))
    email = models.CharField(max_length=250, null=True, blank=True)
    organization = models.ForeignKey(Organization, null=True, blank=True,
        help_text="If '------', no Organization records share the email domain.")

    # Badge scores
    defaultScore = 1
    score = models.IntegerField(default=defaultScore)

    def __str__(self):
        return "%s, %s, %s" % (self.user, self.organization, self.email)

    def save(self, *args, **kwargs):
        """ Creates a user auth record if one doesn't exist. """
        super(UserProfile, self).save()
        self.userauthorization, created = UserAuthorization.objects.get_or_create(
            user=self.user, user_profile=self)
        super(UserProfile, self).save()

    def clean(self):
        """
            Make sure that organization assigned matches the email and
            that the email matches the organization.
        """

        #TODO -- add styling to fields when error occurs.-- Right now
        # there is just an error at the top of the admin.

        # Make sure email matches email in user account
        if self.email != self.user.email:
            self.email = self.user.email

        domain = self.email.split('@')[1]
        if self.organization:
            accepted_domains = [x['email_domain'] for x in self.organization.emaildomain_set.values('email_domain')]
            if domain and domain not in accepted_domains:
                    raise ValidationError('User email domain must be in \
                        Organization domain options. Please add to the \
                        Organization record OR add a new Organization. Changes \
                        to this record were not saved. ')
        else:
            # If the user doesn't have an org, but they have an email
            # assign them an organization.
            try:
                email_domain = EmailDomain.objects.get(email_domain=domain)
                org = email_domain.org

                if org:
                    if self.organization != org:
                        self.organization = org

            except EmailDomain.DoesNotExist:
                raise ValidationError('There is no organization in the database \
                    with the email domain of %s. Please add one before continuing \
                    . Changes to this record were not saved.'
                    % domain)


class UserAuthorization(models.Model):
    user = models.OneToOneField(User)
    user_profile = models.OneToOneField(UserProfile)

    authorized = models.BooleanField(help_text='Check this to approve member access.')
    permissions_granted_by = models.ForeignKey(User, null=True, blank=True,
        related_name='permissions_granted_by')
    permission_granted_on = models.DateTimeField(auto_now_add=True, default=datetime.now())

    def __str__(self):
        return "%s, %s" % (self.user, self.user_profile)

    def save(self, *args, **kwargs):
        user_presave = User.objects.get(pk=self.user.id)

        # Grant default permissions to user if they are authorized.
        group_ids = [g.id for g in self.user.groups.all()]
        if self.authorized and 1 not in group_ids:
            # give them default auth permissions.
            self.user.groups.add(1)
            self.user.is_staff = True
            self.user.save()
        elif not self.authorized and 1 in group_ids:
            # if they are not staff and they have the permission, remove it.
            self.user.groups.remove(1)

        # TODO -- make this work!
        # *** If person is authorized and part of an organization, then they can add people from that org.

        #TODO
        # *** save permissions_granted_by as the user that is granting th permissions.
        # if self.authorized and not user_presave.authorized:
        #     permissions_granted_by
        #     and self.authorized != user_presave.authorized:

        super(UserAuthorization, self).save()

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from accounts.models import UserProfile


class Accounts(TestCase):
    def testUserProfile(self):
        """ Verify that creating a new user also creates a new profile """
        numberObjectsPre = UserProfile.objects.count()
        self.assertEqual(User.objects.count(),numberObjectsPre)
        newuser = User.objects.create_user(username="user",email="myemail@test.com",password="dummy")
        numberObjectsPost = UserProfile.objects.count()
        self.assertEqual(User.objects.count(),numberObjectsPost)

    def testBadges(self):
        """ Verify that a new user has no badges but can get them for being the analyst for one or more approved AOI's """
        newuser = User.objects.create_user(username="user",email="myemail@test.com",password="dummy")

        self.assertEqual(0,len(Badges.objects.filter(user=newuser)))
        # Check that score is set to default score
        self.assertEqual(UserProfile.defaultScore,newuser.get_profile().score)

        # TODO: make this into part of the fixture
        project = Project.objects.create(name="Project", description = "project", project_type="Exercise")
        project.save()

        jobs = [Job.objects.create(name="Job%d" % i, description = "blah", project=project) for i in range(3)]
        jobs.append(jobs[-1])
        for j in jobs:
            j.save()

        oldAOI = AOI.objects.all()[0]
        newAOIs = [AOI.objects.create(job=jobs[i],polygon=oldAOI.polygon) for i in range(4)]
        for n in newAOIs:
            n.save()

        # We've created 4 AOI's but none of them have analysts yet
        self.assertEqual(0,len(Badges.objects.filter(user=newuser)))
        self.assertEqual(UserProfile.defaultScore,newuser.get_profile().score)

        newAOIs[0].analyst = newuser
        newAOIs[0].save()

        # AOI hasn't been marked completed yet
        self.assertEqual(0,len(Badges.objects.filter(user=newuser)))
        self.assertEqual(UserProfile.defaultScore,newuser.get_profile().score)

        newAOIs[0].status = 'Completed'
        newAOIs[0].save()

        # Yay, we have a badge
        # TODO: why isn't badges getting updated here?
        #self.assertEqual(1,len(Badges.objects.filter(user=newuser)))
        # TODO: where/how to score the value
        self.assertEqual(UserProfile.defaultScore + 5,newuser.get_profile().score)
        # Change something other than status
        newAOIs[0].description = 'Completed'
        newAOIs[0].save()

        # Still only one badge
        #self.assertEqual(1,len(Badges.objects.filter(user=newuser)))
        # and same score
        self.assertEqual(UserProfile.defaultScore + 5,newuser.get_profile().score)
        #TODO: should a user lose points if someone else is set to be analyst

        for i in range(4):
            newAOIs[i].status = 'Completed'
            newAOIs[i].analyst = newuser
            newAOIs[i].save()

        # Two badges: 1 for supporting multiple efforts, 1 for first approved AOI
        #self.assertEqual(2,len(Badges.objects.filter(user=newuser)))
        # and score is now defaul + 5 * 4
        # TODO: should badges also be worth points?
        self.assertEqual(UserProfile.defaultScore + 5 * 4,newuser.get_profile().score)


        pass

########NEW FILE########
__FILENAME__ = urls

from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView
from django.conf import settings

from forms import SignupFormExtra

from userena import views as userena_views

from accounts.views import point_to_404

logout_page = getattr(settings, 'LOGOUT_URL', '/geoq')


urlpatterns = patterns('',

    # TODO:Accounts -- when you remove accounts, add this back in
    # # Signup
    # url(r'^(?P<username>[\.\w-]+)/signup/complete/$',
    #    userena_views.direct_to_user_template,
    #    {'template_name': 'userena/signup_complete.html',
    #     'extra_context': {'userena_activation_required': userena_settings.USERENA_ACTIVATION_REQUIRED,
    #                       'userena_activation_days': userena_settings.USERENA_ACTIVATION_DAYS}},
    #    name='userena_signup_complete'),

    # Signup, signin and signout
    url(r'^signup/$',
       point_to_404, name='userena_signup'),
    url(r'^signin/$',
        userena_views.signin,
        {'template_name': 'accounts/templates/accounts/signin_form.html'},
        name='userena_signin'),
    url(r'^signout/$',
       userena_views.signout,
       {'next_page': logout_page},
       name='userena_signout'),


    # Reset password
    url(r'^password/reset/$',
        point_to_404, name='userena_password_reset'),
    url(r'^password/reset/done/$',
        point_to_404, name='userena_password_reset_done'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        point_to_404, name='userena_password_reset_confirm'),
    url(r'^password/reset/confirm/complete/$', point_to_404),

    # Activate
    url(r'^activate/(?P<activation_key>\w+)/$',
        point_to_404, name='userena_activate'),

    # Retry activation
    url(r'^activate/retry/(?P<activation_key>\w+)/$',
        point_to_404, name='userena_activate_retry'),

    # Change email and confirm it
    url(r'^(?P<username>[\.\w-]+)/email/$',
       point_to_404, name='userena_email_change'),
    url(r'^(?P<username>[\.\w-]+)/email/complete/$',
       point_to_404, name='userena_email_change_complete'),
    url(r'^(?P<username>[\.\w-]+)/confirm-email/complete/$',
       point_to_404, name='userena_email_confirm_complete'),
    url(r'^confirm-email/(?P<confirmation_key>\w+)/$',
       point_to_404, name='userena_email_confirm'),

    # Disabled account
    url(r'^(?P<username>[\.\w-]+)/disabled/$',
       point_to_404, name='userena_disabled'),

    # Change password
    url(r'^(?P<username>[\.\w-]+)/password/$',
       point_to_404, name='userena_password_change'),
    url(r'^(?P<username>[\.\w-]+)/password/complete/$',
       point_to_404, name='userena_password_change_complete'),

    # Edit profile
    url(r'^(?P<username>[\.\w-]+)/edit/$',
       point_to_404, name='userena_profile_edit'),

    # View profiles
    url(r'^(?P<username>(?!signout|signup|signin)[\.\w-]+)/$',
       RedirectView.as_view(url='/geoq'),
       name='userena_profile_detail'),
    # url(r'^(?P<username>(?!signout|signup|signin)[\.\w-]+)/$',
    #    point_to_404, name='userena_profile_detail'),
    url(r'^page/(?P<page>[0-9]+)/$',
       point_to_404, name='userena_profile_list_paginated'),
    url(r'^$',
       point_to_404, name='userena_profile_list'),

    # If nothing overrides the urls, then load the default with userena.
    url(r'^', include('userena.urls')),
)
########NEW FILE########
__FILENAME__ = views
from django.http import Http404

# When restoring accounts, this view can be deleted.
def point_to_404(request):
    raise Http404
########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import reversion
from django.contrib.gis import admin
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django import forms
from models import Project, Job, AOI
from guardian.admin import GuardedModelAdmin


class ObjectAdmin(admin.OSMGeoAdmin, reversion.VersionAdmin,):
    list_display = ('name', 'created_at', 'updated_at')


class AOIAdmin(ObjectAdmin):
    filter_horizontal = ("reviewers",)
    save_on_top = True
    actions = ['rename_aois']
    search_fields = ['name', 'id']

    class NameInputForm(forms.Form):
        _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
        name_field = forms.CharField(max_length=200, required=True, label="AOI Name")

    def rename_aois(self, request, queryset):
        form = None

        if 'apply' in request.POST:
            form = self.NameInputForm(request.POST)

            if form.is_valid():
                namestring = form.cleaned_data['name_field']
                queryset.update(name=namestring)

                self.message_user(request, "Succesfully renamed selected AOIs")
                return HttpResponseRedirect(request.get_full_path())

        if not form:
            form = self.NameInputForm(initial={'_selected_action': request.POST.getlist('_selected_action')})

        return render(request, 'core/name_input.html', {'name_form': form})
    rename_aois.short_description = "Rename AOIs"


class JobAdmin(GuardedModelAdmin, ObjectAdmin):
    filter_horizontal = ("analysts", "reviewers", "feature_types")
    save_on_top = True


admin.site.register(Project, ObjectAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(AOI, AOIAdmin)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django import forms
from django.forms.widgets import (RadioInput, RadioSelect, CheckboxInput,
    CheckboxSelectMultiple)
from models import AOI, Job, Project

no_style = [RadioInput, RadioSelect, CheckboxInput, CheckboxSelectMultiple]


class StyledModelForm(forms.ModelForm):
    """
    Adds the span5 (in reference to the Twitter Bootstrap element)
    to form fields.
    """
    cls = 'span5'

    def __init__(self, *args, **kwargs):
        super(StyledModelForm, self).__init__(*args, **kwargs)

        for f in self.fields:
            if type(self.fields[f].widget) not in no_style:
                self.fields[f].widget.attrs['class'] = self.cls


class AOIForm(StyledModelForm):
    class Meta:
        fields = ('name', 'description', 'job', 'analyst',
                  'priority', 'status')
        model = AOI


class JobForm(StyledModelForm):
    class Meta:

        fields = ('name', 'description', 'project',
                  'analysts', 'reviewers', 'feature_types', 'map', 'grid')
        model = Job

    def __init__(self, project, *args, **kwargs):
        super(JobForm, self).__init__(*args, **kwargs)

        def remove_anonymous(field):
            """ Removes anonymous from choices in form. """
            field_var = self.fields[field].queryset.exclude(id=-1)
            self.fields[field].queryset = field_var
            return None
        remove_anonymous('reviewers')
        remove_anonymous('analysts')
        self.fields['project'].initial = project


class ProjectForm(StyledModelForm):
    class Meta:
        fields = ('name', 'description', 'project_type', 'active', 'private')
        model = Project

########NEW FILE########
__FILENAME__ = managers
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.contrib.gis.db import models


class AOIManager(models.GeoManager):

    def add_filters(self, **kwargs):
        """
        Returns the queryset with new filters
        """
        return super(AOIManager, self).get_query_set().filter(**kwargs)

    def unassigned(self):
        """
        Returns unassigned AOIs.
        """
        return self.add_filters(status='Unassigned')

    def assigned(self):
        """
        Returns assigned AOIs.
        """
        return self.add_filters(status='Assigned')

    def in_work(self):
        """
        Returns AOIs in work.
        """
        return self.add_filters(status='In Work')

    def submitted(self):
        """
        Returns submitted AOIs.
        """
        return self.add_filters(status='Submitted')

    def completed(self):
        """
        Returns completed AOIs.
        """
        return self.add_filters(status='Completed')

########NEW FILE########
__FILENAME__ = menu
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.core.urlresolvers import reverse_lazy
from django.utils.datastructures import SortedDict
import re


def menu(active=None, request_path=None, request_user=None):

    def order_dict(d, key):
        return SortedDict(sorted(d.items(), key=key))

    sort_key = lambda t: t[1].get('index', None)

    #help_dropdown = {
    #    'Submit Feedback':  {'index': 1, 'url':  reverse_lazy('home'), 'active': False},
    #    'FAQs':  {'index': 2, 'url': reverse_lazy('home'), 'active': False},
    #    }

    maps_dropdown = {
        'Maps': {'index': 1, 'url': reverse_lazy('map-list'), 'active': False},
        'Layers': {'index': 2, 'url': reverse_lazy('layer-list'), 'active': False},
        'Feature Types': {'index': 2, 'url': reverse_lazy('feature-type-list'), 'active': False}
    }
    menu_maps = {'Maps':  {'index': 4, 'url': '#', 'active': False, 'dropdown': order_dict(maps_dropdown, sort_key)}}
    menu_items = {
        'Projects': {'index': 2, 'url': reverse_lazy('project-list'), 'active': False},
        'Jobs': {'index': 3, 'url': reverse_lazy('job-list'), 'active': False}
        #'Help': {'index': 6, 'url': '#', 'active': False, 'dropdown': order_dict(help_dropdown, sort_key)},
    }

    if(request_user.groups.filter(name='admin_group') or request_user.is_superuser):
        menu_items.update(menu_maps)

    if request_path:
        for i in menu_items.keys():
            if menu_items[i].get('url', None):
                if re.search(str(menu_items[i].get('url')), request_path):
                    menu_items[i]['active'] = True

    return order_dict(menu_items, sort_key)

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)


class UserPermsMiddleware(object):

    def process_request(self, request):

        """
        Populates user permissions to use in the templates.
        """
        user = request.user
        perms = []

        perms = list(user.get_all_permissions()) + perms
        request.base_perms = set(perms)

        return None

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Project'
        db.create_table(u'core_project', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('project_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('private', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'core', ['Project'])

        # Adding model 'Job'
        db.create_table(u'core_job', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('progress', self.gf('django.db.models.fields.SmallIntegerField')(max_length=2, null=True, blank=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='project', to=orm['core.Project'])),
        ))
        db.send_create_signal(u'core', ['Job'])

        # Adding M2M table for field analysts on 'Job'
        m2m_table_name = db.shorten_name(u'core_job_analysts')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('job', models.ForeignKey(orm[u'core.job'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['job_id', 'user_id'])

        # Adding M2M table for field reviewers on 'Job'
        m2m_table_name = db.shorten_name(u'core_job_reviewers')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('job', models.ForeignKey(orm[u'core.job'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['job_id', 'user_id'])

        # Adding model 'AOI'
        db.create_table(u'core_aoi', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('analyst', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(related_name='aois', to=orm['core.Job'])),
            ('polygon', self.gf('django.contrib.gis.db.models.fields.MultiPolygonField')()),
            ('priority', self.gf('django.db.models.fields.SmallIntegerField')(default=5, max_length=1)),
            ('status', self.gf('django.db.models.fields.CharField')(default='Unassigned', max_length=15)),
        ))
        db.send_create_signal(u'core', ['AOI'])

        # Adding M2M table for field reviewers on 'AOI'
        m2m_table_name = db.shorten_name(u'core_aoi_reviewers')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('aoi', models.ForeignKey(orm[u'core.aoi'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['aoi_id', 'user_id'])


    def backwards(self, orm):
        # Deleting model 'Project'
        db.delete_table(u'core_project')

        # Deleting model 'Job'
        db.delete_table(u'core_job')

        # Removing M2M table for field analysts on 'Job'
        db.delete_table(db.shorten_name(u'core_job_analysts'))

        # Removing M2M table for field reviewers on 'Job'
        db.delete_table(db.shorten_name(u'core_job_reviewers'))

        # Deleting model 'AOI'
        db.delete_table(u'core_aoi')

        # Removing M2M table for field reviewers on 'AOI'
        db.delete_table(db.shorten_name(u'core_aoi_reviewers'))


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_job_map
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ("maps", "0002_auto__add_feature"),
        ("maps", "0003_auto__add_featuretype__del_field_feature_geometry__add_field_feature_t"),
    )

    def forwards(self, orm):
        # Adding field 'Job.map'
        db.add_column(u'core_job', 'map',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['maps.Map'], null=True, blank=True),
                      keep_default=False)

        # Adding M2M table for field feature_types on 'Job'
        m2m_table_name = db.shorten_name(u'core_job_feature_types')
        m2m_table_name = db.shorten_name(u'core_job_feature_types')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('job', models.ForeignKey(orm[u'core.job'], null=False)),
            ('featuretype', models.ForeignKey(orm[u'maps.featuretype'], null=False))
        ))
        db.create_unique(m2m_table_name, ['job_id', 'featuretype_id'])


    def backwards(self, orm):
        # Deleting field 'Job.map'
        db.delete_column(u'core_job', 'map_id')

        # Removing M2M table for field feature_types on 'Job'
        db.delete_table(db.shorten_name(u'core_job_feature_types'))


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'feature_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['maps.FeatureType']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {}),
            'style': ('jsonfield.fields.JSONField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0003_add_supervisors_to_proj
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding M2M table for field supervisors on 'Project'
        m2m_table_name = db.shorten_name(u'core_project_supervisors')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('project', models.ForeignKey(orm[u'core.project'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['project_id', 'user_id'])


    def backwards(self, orm):
        # Removing M2M table for field supervisors on 'Project'
        db.delete_table(db.shorten_name(u'core_project_supervisors'))


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'feature_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['maps.FeatureType']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'supervisors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'supervisors'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'style': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0004_auto__add_userprofile
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table(u'core_userprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('score', self.gf('django.db.models.fields.IntegerField')(default=1)),
        ))
        db.send_create_signal(u'core', ['UserProfile'])


    def backwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table(u'core_userprofile')


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'feature_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['maps.FeatureType']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'supervisors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'supervisors'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'style': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0005_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing M2M table for field supervisors on 'Project'
        db.delete_table(db.shorten_name(u'core_project_supervisors'))

        # Adding M2M table for field project_admins on 'Project'
        m2m_table_name = db.shorten_name(u'core_project_project_admins')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('project', models.ForeignKey(orm[u'core.project'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['project_id', 'user_id'])

        # Adding M2M table for field contributors on 'Project'
        m2m_table_name = db.shorten_name(u'core_project_contributors')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('project', models.ForeignKey(orm[u'core.project'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['project_id', 'user_id'])


    def backwards(self, orm):
        # Adding M2M table for field supervisors on 'Project'
        m2m_table_name = db.shorten_name(u'core_project_supervisors')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('project', models.ForeignKey(orm[u'core.project'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['project_id', 'user_id'])

        # Removing M2M table for field project_admins on 'Project'
        db.delete_table(db.shorten_name(u'core_project_project_admins'))

        # Removing M2M table for field contributors on 'Project'
        db.delete_table(db.shorten_name(u'core_project_contributors'))


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'feature_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['maps.FeatureType']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'contributors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'contributors'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_admins': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'project_admins'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'style': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '5'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0006_auto__del_userprofile
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table(u'core_userprofile')


    def backwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table(u'core_userprofile', (
            ('score', self.gf('django.db.models.fields.IntegerField')(default=1)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
        ))
        db.send_create_signal(u'core', ['UserProfile'])


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'feature_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['maps.FeatureType']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'contributors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'contributors'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_admins': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'project_admins'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'style': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '5'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0007_auto__add_field_job_grid
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Job.grid'
        db.add_column(u'core_job', 'grid',
                      self.gf('django.db.models.fields.CharField')(default='usng', max_length=5),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Job.grid'
        db.delete_column(u'core_job', 'grid')


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'feature_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['maps.FeatureType']", 'null': 'True', 'blank': 'True'}),
            'grid': ('django.db.models.fields.CharField', [], {'default': "'usng'", 'max_length': '5'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'contributors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'contributors'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_admins': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'project_admins'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'style': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '5'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import json

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.gis.geos import MultiPolygon
from django.core.urlresolvers import reverse
from django.utils.datastructures import SortedDict
from managers import AOIManager

TRUE_FALSE = [(0, 'False'), (1, 'True')]


class GeoQBase(models.Model):
    """
    A generic model for GeoQ objects.
    """

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ('-created_at',)


class Project(GeoQBase):
    """
    Top-level organizational object.
    """

    PROJECT_TYPES = [
        ("Hurricane/Cyclone", "Hurricane/Cyclone"),
        ("Tornado", "Tornado"),
        ("Earthquake", "Earthquake"),
        ("Extreme Weather", "Extreme Weather"),
        ("Fire", "Fire"),
        ("Flood", "Flood"),
        ("Tsunami", "Tsunami"),
        ("Volcano", "Volcano"),
        ("Pandemic", "Pandemic"),
        ("Exercise", "Exercise"),
        ]

    project_type = models.CharField(max_length=50, choices=PROJECT_TYPES)
    private = models.BooleanField(default=False, help_text='Make this project available to all users.')
    project_admins = models.ManyToManyField(
        User, blank=True, null=True,
        related_name="project_admins", help_text='User that has admin rights to project.')
    contributors = models.ManyToManyField(
        User, blank=True, null=True,
        related_name="contributors", help_text='User that will be able to take on jobs.')

    @property
    def jobs(self):
        return Job.objects.filter(project=self)

    @property
    def job_count(self):
        return self.jobs.count()

    @property
    def user_count(self):
        return User.objects.filter(analysts__project__id=self.id).distinct().count()

    @property
    def aois(self):
        return AOI.objects.filter(job__project__id=self.id)

    @property
    def aoi_count(self):
        return self.aois.count()

    @property
    def aois_envelope(self):
        return MultiPolygon([n.aois_envelope() for n in self.jobs if n.aois.count()])

    def get_absolute_url(self):
        return reverse('project-detail', args=[self.id])

    def get_update_url(self):
        return reverse('project-update', args=[self.id])


class Job(GeoQBase):
    """
    Mid-level organizational object.
    """

    GRID_SERVICE_VALUES = ['usng', 'mgrs']
    GRID_SERVICE_CHOICES = [(choice, choice) for choice in GRID_SERVICE_VALUES]

    analysts = models.ManyToManyField(User, blank=True, null=True, related_name="analysts")
    reviewers = models.ManyToManyField(User, blank=True, null=True, related_name="reviewers")
    progress = models.SmallIntegerField(max_length=2, blank=True, null=True)
    project = models.ForeignKey(Project, related_name="project")
    grid = models.CharField(max_length=5, choices=GRID_SERVICE_CHOICES, default=GRID_SERVICE_VALUES[0], help_text='Select usng for Jobs inside the US, otherwise use mgrs')

    map = models.ForeignKey('maps.Map', blank=True, null=True)
    feature_types = models.ManyToManyField('maps.FeatureType', blank=True, null=True)

    def get_absolute_url(self):
        return reverse('job-detail', args=[self.id])

    def get_update_url(self):
        return reverse('job-update', args=[self.id])

    def aois_geometry(self):
        return self.aois.all().collect()

    def aois_envelope(self):
        """
        Returns the envelope of related AOIs geometry.
        """
        return getattr(self.aois.all().collect(), 'envelope', None)

    def aoi_count(self):
        return self.aois.count()

    @property
    def user_count(self):
        return self.analysts.count()

    def unassigned_aois(self):
        """
        Returns the unassigned AOIs.
        """
        return self.aois.filter(status='Unassigned')

    def in_work_aois(self):
        """
        Returns the in work AOIs.
        """
        return self.aois.filter(status='In work')

    def complete(self):
        """
        Returns the completed AOIs.
        """
        return self.aois.filter(status='Completed')

    def in_work(self):
        """
        Returns the AOIs currently being worked
        """
        return self.aois.filter(status='In work')

    def geoJSON(self, as_json=True):
        """
        Returns geoJSON of the feature.
        """

        geojson = SortedDict()
        geojson["type"] = "FeatureCollection"
        geojson["features"] = [json.loads(aoi.geoJSON()) for aoi in self.aois.all()]

        return json.dumps(geojson) if as_json else geojson

    def features_geoJSON(self, as_json=True):

        geojson = SortedDict()
        geojson["type"] = "FeatureCollection"
        geojson["properties"] = dict(id=self.id)
        geojson["features"] = [n.geoJSON(as_json=False) for n in self.feature_set.all()]

        return json.dumps(geojson) if as_json else geojson


class AOI(GeoQBase):
    """
    Low-level organizational object.
    """

    STATUS_VALUES = ['Unassigned', 'In work', 'In review', 'Completed'] #'Assigned'
    STATUS_CHOICES = [(choice, choice) for choice in STATUS_VALUES]

    PRIORITIES = [(n, n) for n in range(1, 6)]

    analyst = models.ForeignKey(User, blank=True, null=True, help_text="User responsible for the AOI.")
    job = models.ForeignKey(Job, related_name="aois")
    reviewers = models.ManyToManyField(User, blank=True, null=True, related_name="aoi_reviewers",
                                       help_text='Users that actually reviewed this work.')
    objects = AOIManager()
    polygon = models.MultiPolygonField()
    priority = models.SmallIntegerField(choices=PRIORITIES, max_length=1, default=5)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Unassigned')

    def __unicode__(self):
        aoi_obj = '%s - AOI %s' % (self.name, self.id)
        return aoi_obj

    #def save(self):
    # if analyst or reviewer updated, then create policy to give them permission to edit this object.....
    # -- Afterwards -- check how this will work with the views.

    def get_absolute_url(self):
        return reverse('aoi-work', args=[self.id])

    def geoJSON(self):
        """
        Returns geoJSON of the feature.
        """

        if self.id is None:
            self.id = 1

        geojson = SortedDict()
        geojson["type"] = "Feature"
        geojson["properties"] = dict(
            id=self.id,
            status=self.status,
            analyst=(self.analyst.username if self.analyst is not None else 'Unassigned'),
            priority=self.priority,
            absolute_url=reverse('aoi-work', args=[self.id]),
            delete_url=reverse('aoi-deleter', args=[self.id]))
        geojson["geometry"] = json.loads(self.polygon.json)

        return json.dumps(geojson)

    def user_can_complete(self, user):
        """
        Returns whether the user can update the AOI as complete.
        """
        return user == self.analyst or user in self.job.reviewers.all()

    class Meta:
        verbose_name = 'Area of Interest'
        verbose_name_plural = 'Areas of Interest'


# if not 'syncdb' in sys.argv[1:2] and not 'migrate' in sys.argv[1:2]:
#     from accounts.meta_badges import *

########NEW FILE########
__FILENAME__ = proxies
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.http import HttpResponse
import json
import mimetypes
import urllib2

import logging

logger = logging.getLogger(__name__)


def proxy_to(request, path, target_url):
    url = '%s%s' % (target_url, path)

    url = url.replace('http:/', 'http://', 1)
    url = url.replace('http:///', 'http://')

    url = url.replace('https:/', 'https://', 1)
    url = url.replace('https:///', 'https://')

    testurl = False
    errorCode = ''
    status = {}

    if request.META.has_key('QUERY_STRING'):
        qs = request.META['QUERY_STRING']
        if len(qs) > 1:
            url = '%s?%s' % (url, qs)

    try:
        if testurl:
            content = url
            status_code = 200
            mimetype = 'text/plain'
        else:
            proxied_request = urllib2.urlopen(url, timeout=10)
            status_code = proxied_request.code
            mimetype = proxied_request.headers.typeheader or mimetypes.guess_type(url)
            content = proxied_request.read()
    except urllib2.HTTPError, e:
        status = {'status': 'error', 'details': 'Proxy HTTPError = ' + str(e.code)}
        errorCode = 'Proxy HTTPError = ' + str(e.code)
    except urllib2.URLError, e:
        status = {'status': 'error', 'details': 'Proxy URLError = ' + str(e.reason)}
        errorCode = 'Proxy URLError = ' + str(e.reason)
    except Exception:
        status = {'status': 'error', 'details': 'Proxy generic exception'}
        import traceback

        errorCode = 'Proxy generic exception: ' + traceback.format_exc()
    else:
        return HttpResponse(content, status=status_code, mimetype=mimetype)

    if errorCode and len(errorCode):
        logger.error(errorCode)
    output = json.dumps(status)
    return HttpResponse(output, content_type="application/json")
########NEW FILE########
__FILENAME__ = aoi_status
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django import template
register = template.Library()

@register.filter('aoi_status')
def aoi_status(objects,status):
    """
    Returns the status of the aoi
    """
    return objects.filter(status=status)

########NEW FILE########
__FILENAME__ = dynurl
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.template import Library,Node,Variable
from django.core.urlresolvers import reverse

register = Library()

class DynamicUrlNode(Node):
    def __init__(self, *args):
        self.name_var = Variable(args[0])
        try:
            self.args = [Variable(a) for a in args[1].split(',')]
        except IndexError:
            self.args = []

    def render(self,context):
        name = self.name_var.resolve(context)
        args = [a.resolve(context) for a in self.args]
        return reverse(name, args = args)

@register.tag
def DynamicUrl(parser,token):
    args = token.split_contents()
    return DynamicUrlNode(*args[1:])
########NEW FILE########
__FILENAME__ = gamification_tags
from django import template
from django.conf import settings

register = template.Library()


# gamification host
@register.simple_tag
def gamification_value(name):
    return getattr(settings, name, "")
########NEW FILE########
__FILENAME__ = menu
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django import template
from geoq.core.menu import menu

register = template.Library()

def get_menu(request=None, **kwargs):

    request_path = getattr(request, 'path', None)
    request_user = getattr(request, 'user', None)
    menu_dict = kwargs
    menu_dict['menu_items'] = menu(request_path=request_path, request_user=request_user)
    menu_dict['request'] = request

    return menu_dict

register.inclusion_tag('core/menu.html')(get_menu)

########NEW FILE########
__FILENAME__ = object_class
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django import template
register = template.Library()

@register.filter('object_class')
def field_class(ob):
    """
    Returns the class of the object
    """
    return ob.__class__.__name__

########NEW FILE########
__FILENAME__ = version
from django import template
import time
import os

register = template.Library()

@register.simple_tag
def version_date():
    try:
        timestamp = "Updated: " + time.strftime('%m/%d/%Y', time.gmtime(os.path.getmtime('.git')))
    except:
        timestamp = ""
    return timestamp

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from core.models import Job, AOI, Project
from badges.models import Badge as Badges

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client
from django.test import TestCase
from geoq.core.models import Project
from django.test import TestCase
from django.test import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

class CoreTest(TestCase):
    # TODO test requests to all views

    fixtures = ['core/initial_data.json']
    def setUp(self):

        self.get_views = [
                           'home',
                           'project-list',
                           'project-create',
                           'job-list',
                           'job-create',
                           'aoi-create',
                          ]

        self.admin, created = User.objects.get_or_create(username='admin', password='admin', is_superuser=True)

    def test_get_requests(self):
        """
        Makes a get request to views and ensures the view returns a 200.
        """
        c = Client()
        for view in self.get_views:
            response = c.get(reverse(view))
            self.assertEqual(200, response.status_code, "Problem with GET request to {0}".format(view))

    def test_usng_proxy(self):
        """
        Tests the USNG proxy.

        Given a comma seperated bbox (-77.6348876953125,37.81846319511331,-77.5360107421875,37.87051721701939) the
        service should USNG grids as GeoJSON.
        """

        pass


    def test_change_aoi_status(self):
        """
        Tests the ChangeAOIStatus View.

        Given an AOI id and a status, update the AOI's status attribute to the new status if user is allowed to update
        the AOI.  View should return JSON of the updated value.
        """

        pass

    def test_job_detailed_list_view(self):
        """
        Tests the JobDetailedList View.

        Given a job object return the job and related aois filtered by an optional status.  Error should return a
        human readable message with numeric response status both as JSON.

        Context data returned:
        object: The job, return a 404 if it does not exist.
        object_list: A list of aois related to the project.
        statuses: A list of all possible statuses (returned from the AOI model).
        active_status: The currently selected status, as received in a url parameter.
        """

        pass

    def test_detailed_list_view(self):
        """
        Tests the DetailedList View.

        Given a project object return the project and related jobs.  Errors should return a human readable message
        with numeric response status both as JSON.

        Context data returned:
        object: The project, return a 404 if it does not exist.
        object_list: A list of jobs related to the project.
        """

        pass

    def batch_create_views(self):
        """
        Tests the BatchCreateAOIS View.

        Given a job id received via the URL pattern return the job in the appropriate template on GET requests.  POST
        requests should contain the job (supplied via the URL route) and a GeoJSON representation of new AOIs.  The
        view will bulk create new AOIS from GeoJSON and relate them to the job.  Errors should return a human readable message
        with numeric response status both as JSON.

        Context data returned:

        GET:
        object: The job, return a 404 if it does not exist.
        """

        pass


    def dashboard(self):
        """
        Tests the Dashboard View.

        Returns the dashboard.

        Context data returned:

        GET:
        projects: List of projects.
        """

        pass

    def test_create_project_view(self):
        """
        Tests the create project view.
        """

        project = dict(name='Test project.', description="This is a test.", project_type='Fire')

        c = Client()
        c.login(username='admin', password='admin')
        response = c.post(reverse('project-create'), data=project)
        self.assertEqual(response.status_code, 201)

        # Make sure the user that creates the job becomes a supervisor
        proj = Project.objects.filter(name=project.get('name'))
        self.assertTrue(self.admin in proj.supervisors)



########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from django.views.generic import CreateView, TemplateView, ListView, UpdateView
from forms import AOIForm, JobForm, ProjectForm
from models import AOI, Project, Job
from proxies import proxy_to
from views import (BatchCreateAOIS, CreateFeaturesView, Dashboard, DetailedListView,
    JobDetailedListView, AOIDetailedListView, ChangeAOIStatus, JobDelete, AOIDelete, CreateJobView,
    UpdateJobView, CreateProjectView, redirect_to_unassigned_aoi, aoi_delete, display_help)
from geoq.maps.views import feature_delete

urlpatterns = patterns('',
    url(r'^$', Dashboard.as_view(), name='home'),

    # PROJECTS
    url(r'^projects/?$',
        ListView.as_view(queryset=Project.objects.all()),
        name='project-list'),

    url(r'^projects/(?P<pk>\d+)/?$',
        DetailedListView.as_view(template_name="core/project_detail.html"),
        name='project-detail'),

    url(r'^projects/create/?$', login_required(
        CreateProjectView.as_view(form_class=ProjectForm,
                           template_name="core/generic_form.html")),
        name='project-create'),
    url(r'^projects/update/(?P<pk>\d+)/?$', login_required(
        UpdateView.as_view(queryset=Project.objects.all(),
                           template_name='core/generic_form.html',
                           form_class=ProjectForm)),
        name='project-update'),

    # JOBS
    url(r'^jobs/?$', ListView.as_view(queryset=Job.objects.all()), name='job-list'),
    url(r'^jobs/(?P<pk>\d+)/(?P<status>[a-zA-Z_ ]+)?/?$',
        JobDetailedListView.as_view(template_name='core/job_detail.html'),
        name='job-detail'),
    url(r'^jobs/(?P<pk>\d+)/next-aoi', redirect_to_unassigned_aoi, name='job-next-aoi'),
    url(r'^jobs/create/?$',
        login_required(CreateJobView.as_view(queryset=Job.objects.all(),
                           template_name='core/generic_form.html',
                           form_class=JobForm)),
        name='job-create'),
    url(r'^jobs/update/(?P<pk>\d+)/?$',
        login_required(UpdateJobView.as_view(queryset=Job.objects.all(),
                           template_name='core/generic_form.html',
                           form_class=JobForm)),
        name='job-update'),
    url(r'^jobs/delete/(?P<pk>\d+)/?$',
        login_required(JobDelete.as_view()),
        name='job-delete'),
    url(r'^jobs/(?P<job_pk>\d+)/create-aois/?$',
        login_required(BatchCreateAOIS.as_view()),
        name='job-create-aois'),

    url(r'^jobs/(?P<job_pk>\d+)/batch-create-aois/?$',
        #login required set in views
        'core.views.batch_create_aois', name='job-batch-create-aois'),

    # AOIS
    url(r'^aois/(?P<status>[a-zA-Z_ ]+)?/?$', AOIDetailedListView.as_view(template_name='core/aoi_list.html'), name='aoi-list'),
    url(r'^aois/work/(?P<pk>\d+)/?$',
        login_required(CreateFeaturesView.as_view()), name='aoi-work'),
    url(r'^aois/update-status/(?P<pk>\d+)/(?P<status>Unassigned|Assigned|In work|In review|Completed)/?$', login_required(
        ChangeAOIStatus.as_view()),
        name="aoi-update-status"),
    url(r'^aois/create/?$', login_required(
        CreateView.as_view(queryset=AOI.objects.all(),
                           template_name='core/generic_form.html',
                           form_class=AOIForm)),
        name='aoi-create'),
    url(r'^aois/update/(?P<pk>\d+)/?$', login_required(
        UpdateView.as_view(queryset=AOI.objects.all(),
                           template_name='core/generic_form.html',
                           form_class=AOIForm)),
        name='aoi-update'),
    url(r'^aois/delete/(?P<pk>\d+)/?$', login_required(
        AOIDelete.as_view()),
        name='aoi-delete'),

    url(r'^aois/deleter/(?P<pk>\d+)/?$', login_required( aoi_delete ), name='aoi-deleter'),

    url(r'^features/delete/(?P<pk>\d+)/?$', login_required( feature_delete ), name='feature-delete'),

    # OTHER URLS
    url(r'^edit/?$', TemplateView.as_view(template_name='core/edit.html'), name='edit'),
    url(r'^help/?$', display_help, name='help_page'),
    url(r'^api/geo/usng/?$', 'core.views.usng', name='usng'),
    url(r'^api/geo/mgrs/?$', 'core.views.mgrs', name='mgrs'),
    url(r'^proxy/(?P<path>.*)$', proxy_to, {'target_url': ''}),
)
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.conf import settings
from datetime import datetime
import requests
import json


def send_aoi_create_event(user, aoi_id, aoi_feature_count):
    gamification_server = getattr(settings, 'GAMIFICATION_SERVER', '')
    gamification_project = getattr(settings, 'GAMIFICATION_PROJECT', '')

    if gamification_server and gamification_project:

        url = '%s/users/%s/projects/%s/event/' % (gamification_server, user.username, gamification_project)
        dtg = datetime.now().isoformat(' ')

        payload = {'event_dtg': dtg, 'details': {
            'event_type': 'aoi_complete',
            'aoi_id': aoi_id,
            'feature_count': aoi_feature_count
        }}
        headers = {'Content-type': 'application/json'}

        r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=5)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import json
import requests

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.forms.util import ValidationError
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, TemplateView, View, DeleteView, CreateView, UpdateView

from models import Project, Job, AOI
from geoq.maps.models import Layer, Map

from geoq.mgrs.utils import Grid, GridException
from geoq.core.utils import send_aoi_create_event
from geoq.mgrs.exceptions import ProgramException


class Dashboard(TemplateView):

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        cv = super(Dashboard, self).get_context_data(**kwargs)
        cv['projects'] = Project.objects.all()
        return cv


class BatchCreateAOIS(TemplateView):
    """
    Reads GeoJSON from post request and creates AOIS for each features.
    """
    template_name = 'core/job_batch_create_aois.html'

    def get_context_data(self, **kwargs):
        cv = super(BatchCreateAOIS, self).get_context_data(**kwargs)
        cv['object'] = get_object_or_404(Job, pk=self.kwargs.get('job_pk'))
        return cv

    def post(self, request, *args, **kwargs):
        aois = request.POST.get('aois')
        job = Job.objects.get(id=self.kwargs.get('job_pk'))

        try:
            aois = json.loads(aois)
        except ValueError:
            raise ValidationError(_("Enter valid JSON"))

        response = AOI.objects.bulk_create([AOI(name=job.name,
                                            job=job,
                                            description=job.description,
                                            polygon=GEOSGeometry(json.dumps(aoi.get('geometry')))) for aoi in aois])

        return HttpResponse()


#TODO: Abstract this
class DetailedListView(ListView):
    """
    A mixture between a list view and detailed view.
    """

    paginate_by = 15
    model = Project

    def get_queryset(self):
        return Job.objects.filter(project=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        cv = super(DetailedListView, self).get_context_data(**kwargs)
        cv['object'] = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        return cv


class CreateFeaturesView(DetailView):
    template_name = 'core/edit.html'
    queryset = AOI.objects.all()

    def get_context_data(self, **kwargs):
        cv = super(CreateFeaturesView, self).get_context_data(**kwargs)
        cv['reviewers'] = kwargs['object'].job.reviewers.all()

        cv['map'] = self.object.job.map
        cv['aoi'].analyst = self.request.user
        cv['aoi'].status = 'In work'
        cv['aoi'].save()
        return cv


def redirect_to_unassigned_aoi(request, pk):
    """
    Given a job, redirects the view to an unassigned AOI.  If there are no unassigned AOIs, the user will be redirected
     to the job's absolute url.
    """
    job = get_object_or_404(Job, id=pk)

    try:
        return HttpResponseRedirect(job.aois.filter(status='Unassigned')[0].get_absolute_url())
    except IndexError:
        return HttpResponseRedirect(job.get_absolute_url())


class JobDetailedListView(ListView):
    """
    A mixture between a list view and detailed view.
    """

    paginate_by = 15
    model = Job
    default_status = 'in work'
    request = None

    def get_queryset(self):
        status = getattr(self, 'status', None)
        q_set = AOI.objects.filter(job=self.kwargs.get('pk'))

        # # If there is a user logged in, we want to show their stuff
        # # at the top of the list
        if self.request.user.id is not None and status == 'in work':
            user = self.request.user
            clauses = 'WHEN analyst_id=%s THEN %s ELSE 1' % (user.id, 0)
            ordering = 'CASE %s END' % clauses
            self.queryset = q_set.extra(
               select={'ordering': ordering}, order_by=('ordering',))
        else:
            self.queryset = q_set

        if status and (status in [value.lower() for value in AOI.STATUS_VALUES]):
            return self.queryset.filter(status__iexact=status)
        else:
            return self.queryset

    def get(self, request, *args, **kwargs):
        self.status = self.kwargs.get('status')

        if self.status and hasattr(self.status, "lower"):
            self.status = self.status.lower()
        else:
            self.status = self.default_status.lower()

        self.request = request

        return super(JobDetailedListView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        cv = super(JobDetailedListView, self).get_context_data(**kwargs)
        cv['object'] = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
        cv['statuses'] = AOI.STATUS_VALUES
        cv['active_status'] = self.status
        if cv['object'].aoi_count() > 0:
            cv['completed'] = (cv['object'].complete().count() * 100) / cv['object'].aoi_count()
        else:
            cv['completed'] = 0
        return cv


class JobDelete(DeleteView):
    model = Job
    template_name = "core/generic_confirm_delete.html"

    def get_success_url(self):
        return reverse('project-detail', args=[self.object.project.pk])


class AOIDelete(DeleteView):
    model = AOI
    template_name = "core/generic_confirm_delete.html"

    def get_success_url(self):
        return reverse('job-detail', args=[self.object.job.pk])


class AOIDetailedListView(ListView):
    """
    A mixture between a list view and detailed view.
    """

    paginate_by = 25
    model = AOI
    default_status = 'unassigned'

    def get_queryset(self):
        status = getattr(self, 'status', None)
        self.queryset = AOI.objects.all()
        if status and (status in [value.lower() for value in AOI.STATUS_VALUES]):
            return self.queryset.filter(status__iexact=status)
        else:
            return self.queryset

    def get(self, request, *args, **kwargs):
        self.status = self.kwargs.get('status')

        if self.status and hasattr(self.status, "lower"):
            self.status = self.status.lower()
        else:
            self.status = self.default_status.lower()

        return super(AOIDetailedListView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        cv = super(AOIDetailedListView, self).get_context_data(**kwargs)
        cv['statuses'] = AOI.STATUS_VALUES
        cv['active_status'] = self.status
        return cv


class CreateProjectView(CreateView):
    """
    Create view that adds the user that created the job as a reviewer.
    """

    def form_valid(self, form):
        """
        If the form is valid, save the associated model and add the current user as a reviewer.
        """
        self.object = form.save()
        self.object.project_admins.add(self.request.user)
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

class CreateJobView(CreateView):
    """
    Create view that adds the user that created the job as a reviewer.
    """

    def get_form_kwargs(self):
        kwargs = super(CreateJobView, self).get_form_kwargs()
        kwargs['project'] = self.request.GET['project'] if 'project' in self.request.GET else 0
        return kwargs

    def form_valid(self, form):
        """
        If the form is valid, save the associated model and add the current user as a reviewer.
        """
        self.object = form.save()
        self.object.reviewers.add(self.request.user)
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class UpdateJobView(UpdateView):
    """
    Update Job
    """

    def get_form_kwargs(self):
        kwargs = super(UpdateJobView, self).get_form_kwargs()
        kwargs['project'] = kwargs['instance'].project_id if hasattr(kwargs['instance'],'project_id') else 0
        return kwargs


class ChangeAOIStatus(View):
    http_method_names = ['post','get']

    def _get_aoi_and_update(self, pk):
        aoi = get_object_or_404(AOI, pk=pk)
        status = self.kwargs.get('status')
        return status, aoi

    def _update_aoi(self, request, aoi, status):
        aoi.analyst = request.user
        aoi.status = status
        aoi.save()
        return aoi

    def get(self, request, **kwargs):
        # Used to unassign tasks on the job detail, 'in work' tab

        status, aoi = self._get_aoi_and_update(self.kwargs.get('pk'))

        if aoi.user_can_complete(request.user):
            aoi = self._update_aoi(request, aoi, status)

        try:
            url = request.META['HTTP_REFERER']
            return redirect(url)
        except KeyError:
            return redirect('/geoq/jobs/%s/' % aoi.job.id)

    def post(self, request, **kwargs):

        status, aoi = self._get_aoi_and_update(self.kwargs.get('pk'))

        if aoi.user_can_complete(request.user):
            aoi = self._update_aoi(request, aoi, status)

            # send aoi completion event for badging
            send_aoi_create_event(request.user, aoi.id, aoi.features.all().count())
            return HttpResponse(json.dumps({aoi.id: aoi.status}), mimetype="application/json")
        else:
            error = dict(error=403,
                         details="User not allowed to modify the status of this AOI.",)
            return HttpResponse(json.dumps(error), status=error.get('error'))


def usng(request):
    """
    Proxy to USNG service.
    """

    base_url = "http://app01.ozone.nga.mil/geoserver/wfs"

    bbox = request.GET.get('bbox')

    if not bbox:
        return HttpResponse()

    params = dict()
    params['service'] = 'wfs'
    params['version'] = '1.0.0'
    params['request'] = 'GetFeature'
    params['typeName'] = 'usng'
    params['bbox'] = bbox
    params['outputFormat'] = 'json'
    params['srsName'] = 'EPSG:4326'
    resp = requests.get(base_url, params=params)
    return HttpResponse(resp, mimetype="application/json")


def mgrs(request):
    """
    Create mgrs grid in manner similar to usng above
    """

    bbox = request.GET.get('bbox')

    if not bbox:
        return HttpResponse()

    bb = bbox.split(',')

    try:
        grid = Grid(bb[1], bb[0], bb[3], bb[2])
        fc = grid.build_grid_fc()
    except GridException:
        error = dict(error=500, details="Can't create grids across longitudinal boundaries. Try creating a smaller bounding box",)
        return HttpResponse(json.dumps(error), status=error.get('error'))
    except ProgramException:
        error = dict(error=500, details="Error executing external GeoConvert application. Make sure it is installed on the server",)
        return HttpResponse(json.dumps(error), status=error.get('error'))

    return HttpResponse(fc.__str__(), mimetype="application/json")

def geocode(request):
    """
    Proxy to geocode service
    """

    base_url = "http://geoservices.tamu.edu/Services/Geocode/WebService/GeocoderWebServiceHttpNonParsed_V04_01.aspx"
    params['apiKey'] = '57956afd728b4204bee23dbb17f00573'
    params['version'] = '4.01'

def aoi_delete(request, pk):
    try:
        aoi = AOI.objects.get(pk=pk)
        aoi.delete()
    except ObjectDoesNotExist:
        raise Http404

    return HttpResponse(status=200)

def display_help(request):
    return render(request, 'core/geoq_help.html')


@login_required
def batch_create_aois(request, *args, **kwargs):
    aois = request.POST.get('aois')
    job = Job.objects.get(id=kwargs.get('job_pk'))

    try:
        aois = json.loads(aois)
    except ValueError:
        raise ValidationError(_("Enter valid JSON"))

    response = AOI.objects.bulk_create([AOI(name=(aoi.get('name')),
                                        job=job,
                                        description=job.description,
                                        polygon=GEOSGeometry(json.dumps(aoi.get('geometry')))) for aoi in aois])

    return HttpResponse()

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import reversion
from django.contrib.gis import admin
from models import Layer, Map, MapLayer, Feature, FeatureType, GeoeventsSource


class MapLayerInline(admin.TabularInline):
    model = MapLayer
    extra = 1


class MapAdmin(reversion.VersionAdmin, admin.ModelAdmin):
    model = Map
    list_display = ['__unicode__', 'description',]
    inlines = [MapLayerInline]
    save_as = True
    ordering = ['title']
    search_fields = ['description', 'title', 'tags', ]

class LayerAdmin(reversion.VersionAdmin, admin.OSMGeoAdmin):
    model = Layer
    list_display = ['name', 'type', 'url']
    list_filter = ['type', 'image_format']
    save_as = True
    search_fields = ['name', 'url', 'type', ]
    normal_fields = ('name', 'type', 'url', 'layer', 'attribution', 'description', 'image_format')
    advanced_fields = (
     'styles', 'refreshrate', 'transparent', 'enable_identify',
    'token', 'additional_domains', 'constraints', 'extent', 'layer_parsing_function', 'info_format',
    'root_field', 'fields_to_show', 'downloadableLink', 'spatial_reference', 'layer_params' )

    desc = 'The settings below are advanced.  Please contact and admin if you have questions.'
    fieldsets = (
        (None, {'fields': normal_fields}),
        ('Advanced Settings', {'classes': ('collapse',),
                               'description': desc,
                               'fields': advanced_fields,
                               }))


class MapLayerAdmin(reversion.VersionAdmin, admin.ModelAdmin):
    model = MapLayer
    list_display = ['__unicode__', 'map', 'layer', 'stack_order', 'opacity', 'is_base_layer']
    list_filter = ['map', 'layer', 'stack_order',  'is_base_layer']


class FeatureAdmin(reversion.VersionAdmin, admin.OSMGeoAdmin):
    list_display = ['template', 'aoi', 'project', 'analyst', 'created_at']


class FeatureTypeAdmin(reversion.VersionAdmin, admin.ModelAdmin):
    save_as = True

class GeoeventsSourceAdmin(admin.ModelAdmin):
    model = GeoeventsSource
    list_display = ['name','url']

#admin.site.register(Point, FeatureAdmin)
#admin.site.register(Polygon, FeatureAdmin)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(FeatureType, FeatureTypeAdmin)
admin.site.register(Layer, LayerAdmin)
admin.site.register(Map, MapAdmin)
admin.site.register(GeoeventsSource, GeoeventsSourceAdmin)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from geoq.core.forms import StyledModelForm
from django.forms.models import inlineformset_factory
from models import Feature, FeatureType, Map, Layer, MapLayer


class FeatureForm(StyledModelForm):
    class Meta:
        model = Feature
        excluded_fields = ("aoi")


class FeatureTypeForm(StyledModelForm):
    class Meta:
        model = FeatureType


class MapForm(StyledModelForm):
    class Meta:
        model = Map


class LayerForm(StyledModelForm):
    class Meta:
        model = Layer


class MapLayerForm(StyledModelForm):
    class Meta:
        model = MapLayer

MapInlineFormset = inlineformset_factory(Map, MapLayer, extra=3)
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ("core", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'Layer'
        db.create_table(u'maps_layer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=75)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('layer', self.gf('django.db.models.fields.CharField')(max_length=800, null=True, blank=True)),
            ('image_format', self.gf('django.db.models.fields.CharField')(max_length=75, null=True, blank=True)),
            ('styles', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('transparent', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('refreshrate', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=800, null=True, blank=True)),
            ('attribution', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=400, null=True, blank=True)),
            ('extent', self.gf('django.contrib.gis.db.models.fields.PolygonField')(null=True, blank=True)),
            ('layer_parsing_function', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('enable_identify', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('info_format', self.gf('django.db.models.fields.CharField')(max_length=75, null=True, blank=True)),
            ('root_field', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('fields_to_show', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('downloadableLink', self.gf('django.db.models.fields.URLField')(max_length=300, null=True, blank=True)),
            ('layer_params', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('spatial_reference', self.gf('django.db.models.fields.CharField')(default='EPSG:4326', max_length=32, null=True, blank=True)),
            ('constraints', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('additional_domains', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'maps', ['Layer'])

        # Adding model 'Map'
        db.create_table(u'maps_map', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(unique=True, max_length=75)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=800, null=True, blank=True)),
            ('zoom', self.gf('django.db.models.fields.IntegerField')()),
            ('projection', self.gf('django.db.models.fields.CharField')(default='EPSG:4326', max_length=32, null=True, blank=True)),
            ('center_x', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('center_y', self.gf('django.db.models.fields.FloatField')(default=0.0)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'maps', ['Map'])

        # Adding model 'MapLayer'
        db.create_table(u'maps_maplayer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('map', self.gf('django.db.models.fields.related.ForeignKey')(related_name='map_set', to=orm['maps.Map'])),
            ('layer', self.gf('django.db.models.fields.related.ForeignKey')(related_name='map_layer_set', to=orm['maps.Layer'])),
            ('shown', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('stack_order', self.gf('django.db.models.fields.IntegerField')()),
            ('opacity', self.gf('django.db.models.fields.FloatField')(default=0.8)),
            ('is_base_layer', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('display_in_layer_switcher', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'maps', ['MapLayer'])


    def backwards(self, orm):
        # Deleting model 'Layer'
        db.delete_table(u'maps_layer')

        # Deleting model 'Map'
        db.delete_table(u'maps_map')

        # Deleting model 'MapLayer'
        db.delete_table(u'maps_maplayer')


    models = {
        u'maps.layer': {
            'Meta': {'ordering': "['name']", 'object_name': 'Layer'},
            'additional_domains': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'constraints': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'downloadableLink': ('django.db.models.fields.URLField', [], {'max_length': '300', 'null': 'True', 'blank': 'True'}),
            'enable_identify': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'extent': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            'fields_to_show': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'info_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'layer': ('django.db.models.fields.CharField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'layer_params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'layer_parsing_function': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'refreshrate': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'root_field': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'spatial_reference': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'styles': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'transparent': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {})
        },
        u'maps.maplayer': {
            'Meta': {'ordering': "['stack_order']", 'object_name': 'MapLayer'},
            'display_in_layer_switcher': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_base_layer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_layer_set'", 'to': u"orm['maps.Layer']"}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_set'", 'to': u"orm['maps.Map']"}),
            'opacity': ('django.db.models.fields.FloatField', [], {'default': '0.8'}),
            'shown': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'stack_order': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['maps']
########NEW FILE########
__FILENAME__ = 0002_auto__add_feature
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Feature'
        db.create_table(u'maps_feature', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('aoi', self.gf('django.db.models.fields.related.ForeignKey')(related_name='features', to=orm['core.AOI'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('analyst', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('feature_type', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Job'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Project'])),
            ('geometry', self.gf('django.contrib.gis.db.models.fields.GeometryField')()),
        ))
        db.send_create_signal(u'maps', ['Feature'])


    def backwards(self, orm):
        # Deleting model 'Feature'
        db.delete_table(u'maps_feature')


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.feature': {
            'Meta': {'object_name': 'Feature'},
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'aoi': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'features'", 'to': u"orm['core.AOI']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'feature_type': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'geometry': ('django.contrib.gis.db.models.fields.GeometryField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Job']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Project']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.layer': {
            'Meta': {'ordering': "['name']", 'object_name': 'Layer'},
            'additional_domains': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'constraints': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'downloadableLink': ('django.db.models.fields.URLField', [], {'max_length': '300', 'null': 'True', 'blank': 'True'}),
            'enable_identify': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'extent': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            'fields_to_show': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'info_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'layer': ('django.db.models.fields.CharField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'layer_params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'layer_parsing_function': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'refreshrate': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'root_field': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'spatial_reference': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'styles': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'transparent': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {})
        },
        u'maps.maplayer': {
            'Meta': {'ordering': "['stack_order']", 'object_name': 'MapLayer'},
            'display_in_layer_switcher': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_base_layer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_layer_set'", 'to': u"orm['maps.Layer']"}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_set'", 'to': u"orm['maps.Map']"}),
            'opacity': ('django.db.models.fields.FloatField', [], {'default': '0.8'}),
            'shown': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'stack_order': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['maps']
########NEW FILE########
__FILENAME__ = 0003_auto__add_featuretype__del_field_feature_geometry__add_field_feature_t
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'FeatureType'
        db.create_table(u'maps_featuretype', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('properties', self.gf('jsonfield.fields.JSONField')()),
            ('style', self.gf('jsonfield.fields.JSONField')()),
        ))
        db.send_create_signal(u'maps', ['FeatureType'])

        # Deleting field 'Feature.geometry'
        db.delete_column(u'maps_feature', 'geometry')

        # Adding field 'Feature.the_geom'
        db.add_column(u'maps_feature', 'the_geom',
                      self.gf('django.contrib.gis.db.models.fields.GeometryField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'FeatureType'
        db.delete_table(u'maps_featuretype')


        # User chose to not deal with backwards NULL issues for 'Feature.geometry'
        raise RuntimeError("Cannot reverse this migration. 'Feature.geometry' and its values cannot be restored.")
        # Deleting field 'Feature.the_geom'
        db.delete_column(u'maps_feature', 'the_geom')


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'features_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['maps.FeatureType']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progres': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.feature': {
            'Meta': {'ordering': "('-updated_at', 'aoi')", 'object_name': 'Feature'},
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'aoi': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'features'", 'to': u"orm['core.AOI']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'feature_type': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Job']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Project']"}),
            'the_geom': ('django.contrib.gis.db.models.fields.GeometryField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {}),
            'style': ('jsonfield.fields.JSONField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.layer': {
            'Meta': {'ordering': "['name']", 'object_name': 'Layer'},
            'additional_domains': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'constraints': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'downloadableLink': ('django.db.models.fields.URLField', [], {'max_length': '300', 'null': 'True', 'blank': 'True'}),
            'enable_identify': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'extent': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            'fields_to_show': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'info_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'layer': ('django.db.models.fields.CharField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'layer_params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'layer_parsing_function': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'refreshrate': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'root_field': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'spatial_reference': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'styles': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'transparent': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {})
        },
        u'maps.maplayer': {
            'Meta': {'ordering': "['stack_order']", 'object_name': 'MapLayer'},
            'display_in_layer_switcher': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_base_layer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_layer_set'", 'to': u"orm['maps.Layer']"}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_set'", 'to': u"orm['maps.Map']"}),
            'opacity': ('django.db.models.fields.FloatField', [], {'default': '0.8'}),
            'shown': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'stack_order': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['maps']
########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_featuretype_style__chg_field_featuretype_properties__d
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'FeatureType.style'
        db.alter_column(u'maps_featuretype', 'style', self.gf('jsonfield.fields.JSONField')(null=True))

        # Changing field 'FeatureType.properties'
        db.alter_column(u'maps_featuretype', 'properties', self.gf('jsonfield.fields.JSONField')(null=True))
        # Deleting field 'Feature.feature_type'
        db.delete_column(u'maps_feature', 'feature_type')

        # Adding field 'Feature.template'
        db.add_column(u'maps_feature', 'template',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['maps.FeatureType'], on_delete=models.PROTECT),
                      keep_default=False)

        # Adding field 'Feature.properties'
        db.add_column(u'maps_feature', 'properties',
                      self.gf('jsonfield.fields.JSONField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'FeatureType.style'
        raise RuntimeError("Cannot reverse this migration. 'FeatureType.style' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'FeatureType.properties'
        raise RuntimeError("Cannot reverse this migration. 'FeatureType.properties' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Feature.feature_type'
        raise RuntimeError("Cannot reverse this migration. 'Feature.feature_type' and its values cannot be restored.")
        # Deleting field 'Feature.template'
        db.delete_column(u'maps_feature', 'template_id')

        # Deleting field 'Feature.properties'
        db.delete_column(u'maps_feature', 'properties')


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'feature_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['maps.FeatureType']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.feature': {
            'Meta': {'ordering': "('-updated_at', 'aoi')", 'object_name': 'Feature'},
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'aoi': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'features'", 'to': u"orm['core.AOI']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Job']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Project']"}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.FeatureType']", 'on_delete': 'models.PROTECT'}),
            'the_geom': ('django.contrib.gis.db.models.fields.GeometryField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'style': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.layer': {
            'Meta': {'ordering': "['name']", 'object_name': 'Layer'},
            'additional_domains': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'constraints': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'downloadableLink': ('django.db.models.fields.URLField', [], {'max_length': '300', 'null': 'True', 'blank': 'True'}),
            'enable_identify': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'extent': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            'fields_to_show': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'info_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'layer': ('django.db.models.fields.CharField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'layer_params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'layer_parsing_function': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'refreshrate': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'root_field': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'spatial_reference': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'styles': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'transparent': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {})
        },
        u'maps.maplayer': {
            'Meta': {'ordering': "['stack_order']", 'object_name': 'MapLayer'},
            'display_in_layer_switcher': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_base_layer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_layer_set'", 'to': u"orm['maps.Layer']"}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_set'", 'to': u"orm['maps.Map']"}),
            'opacity': ('django.db.models.fields.FloatField', [], {'default': '0.8'}),
            'shown': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'stack_order': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['maps']
########NEW FILE########
__FILENAME__ = 0005_added_geoeventssource
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'GeoeventsSource'
        db.create_table(u'maps_geoeventssource', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal(u'maps', ['GeoeventsSource'])


    def backwards(self, orm):
        # Deleting model 'GeoeventsSource'
        db.delete_table(u'maps_geoeventssource')

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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.aoi': {
            'Meta': {'object_name': 'AOI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aois'", 'to': u"orm['core.Job']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'polygon': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'priority': ('django.db.models.fields.SmallIntegerField', [], {'default': '5', 'max_length': '1'}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'aoi_reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'Unassigned'", 'max_length': '15'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.job': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Job'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'analysts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'analysts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'feature_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['maps.FeatureType']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.Map']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'progress': ('django.db.models.fields.SmallIntegerField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project'", 'to': u"orm['core.Project']"}),
            'reviewers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reviewers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'core.project': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'contributors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'contributors'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project_admins': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'project_admins'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.feature': {
            'Meta': {'ordering': "('-updated_at', 'aoi')", 'object_name': 'Feature'},
            'analyst': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'aoi': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'features'", 'to': u"orm['core.AOI']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Job']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Project']"}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['maps.FeatureType']", 'on_delete': 'models.PROTECT'}),
            'the_geom': ('django.contrib.gis.db.models.fields.GeometryField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'maps.featuretype': {
            'Meta': {'object_name': 'FeatureType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'properties': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'style': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        u'maps.geoeventssource': {
            'Meta': {'object_name': 'GeoeventsSource'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'maps.layer': {
            'Meta': {'ordering': "['name']", 'object_name': 'Layer'},
            'additional_domains': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'attribution': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'constraints': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'downloadableLink': ('django.db.models.fields.URLField', [], {'max_length': '300', 'null': 'True', 'blank': 'True'}),
            'enable_identify': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'extent': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'blank': 'True'}),
            'fields_to_show': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'info_format': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'layer': ('django.db.models.fields.CharField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            'layer_params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'layer_parsing_function': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'refreshrate': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'root_field': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'spatial_reference': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'styles': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'transparent': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'maps.map': {
            'Meta': {'object_name': 'Map'},
            'center_x': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'center_y': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '800', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'projection': ('django.db.models.fields.CharField', [], {'default': "'EPSG:4326'", 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'zoom': ('django.db.models.fields.IntegerField', [], {'default': '5'})
        },
        u'maps.maplayer': {
            'Meta': {'ordering': "['stack_order']", 'object_name': 'MapLayer'},
            'display_in_layer_switcher': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_base_layer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'layer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_layer_set'", 'to': u"orm['maps.Layer']"}),
            'map': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'map_set'", 'to': u"orm['maps.Map']"}),
            'opacity': ('django.db.models.fields.FloatField', [], {'default': '0.80000000000000004'}),
            'shown': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'stack_order': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['maps']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import json
from geoq.core.models import AOI, Job, Project
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils.datastructures import SortedDict
from django.core.urlresolvers import reverse
from jsonfield import JSONField
from datetime import datetime

IMAGE_FORMATS = (
                ('image/png', 'image/png'),
                ('image/png8', 'image/png8'),
                ('image/png24', 'image/png24'),
                ('image/jpeg', 'image/jpeg'),
                ('image/gif', 'image/gif'),
                ('image/tiff', 'image/tiff'),
                ('image/tiff8', 'image/tiff8'),
                ('image/geotiff', 'image/geotiff'),
                ('image/geotiff8', 'image/geotiff8'),
                ('image/svg', 'image/svg'),
                ('rss', 'rss'),
                ('kml', 'kml'),
                ('kmz', 'kmz'),
                ('json', 'json'),
                ('png', 'png'),
                ('png8', 'png8'),
                ('png24', 'png24'),
                ('jpeg', 'jpeg'),
                ('jpg', 'jpg'),
                ('gif', 'gif'),
                ('tiff', 'tiff'),
                ('tiff8', 'tiff8'),
                ('geotiff', 'geotiff'),
                ('geotiff8', 'geotiff8'),
                ('svg', 'svg'),
)

SERVICE_TYPES = (
                ('WMS', 'WMS'),
                ('KML', 'KML'),
                ('GeoRSS', 'GeoRSS'),
                ('ESRI Tiled Map Service', 'ESRI Tiled Map Service'),
                ('ESRI Dynamic Map Layer', 'ESRI Dynamic Map Layer'),
                ('ESRI Feature Layer', 'ESRI Feature Layer'),
                ('GeoJSON', 'GeoJSON'),
                ('ESRI Clustered Feature Layer', 'ESRI Clustered Feature Layer'),
                #('ArcGIS93Rest', 'ArcGIS93Rest'),
                ('GPX', 'GPX'),
                #('GML','GML'),
                ('WMTS', 'WMTS'),
                ('Social Networking Link', 'Social Networking Link'),
                #('MapBox', 'MapBox'),
                #('TileServer','TileServer'),
                #('GetCapabilities', 'GetCapabilities'),
)

INFO_FORMATS = [(n, n) for n in sorted(['application/vnd.ogc.wms_xml',
                                       'application/xml', 'text/html', 'text/plain'])]


class Layer(models.Model):
    """
    A layer object that can be added to any map.
    """

    name = models.CharField(max_length=200, help_text='Name that will be displayed within GeoQ')
    type = models.CharField(choices=SERVICE_TYPES, max_length=75)
    """TODO: Make this url field a CharField"""
    url = models.URLField(help_text='URL of service. If WMS or ESRI, can be any valid URL. Otherwise, the URL will require a local proxy', max_length=500)
    layer = models.CharField(max_length=800, null=True, blank=True, help_text='Layer names can sometimes be comma-separated, and are not needed for data layers (KML, GeoRSS, GeoJSON...)')
    image_format = models.CharField(null=True, blank=True, choices=IMAGE_FORMATS, max_length=75, help_text='The MIME type of the image format to use for tiles on WMS layers (image/png, image/jpeg image/gif...). Double check that the server exposes this exactly - some servers push png instead of image/png.')
    styles = models.CharField(null=True, blank=True, max_length=200, help_text='The name of a style to use for this layer (only useful for WMS layers if the server exposes it.)')
    transparent = models.BooleanField(default=True, help_text='If WMS or overlay, should the tiles be transparent where possible?')
    refreshrate = models.PositiveIntegerField(blank=True, null=True, verbose_name="Layer Refresh Rate", help_text='Layer refresh rate in seconds for vector/data layers (will not refresh WMS layers)')
    description = models.TextField(max_length=800, null=True, blank=True, help_text='Text to show in layer chooser, please be descriptive - this will soon be searchable')
    attribution = models.CharField(max_length=200, null=True, blank=True, help_text="Attribution from layers to the map display (will show in bottom of map when layer is visible).")
    token = models.CharField(max_length=400, null=True, blank=True, help_text='Authentication token, if required (usually only for secure layer servers)')

    ## Advanced layer options
    objects = models.GeoManager()
    extent = models.PolygonField(null=True, blank=True, help_text='Extent of the layer.')
    layer_parsing_function = models.CharField(max_length=100, blank=True, null=True,  help_text='Advanced - The javascript function used to parse a data service (GeoJSON, GeoRSS, KML), needs to be an internally known parser. Contact an admin if you need data parsed in a new way.')
    enable_identify = models.BooleanField(default=False, help_text='Advanced - Allow user to click map to query layer for details. The map server must support queries for this layer.')
    info_format = models.CharField(max_length=75, null=True, blank=True, choices=INFO_FORMATS, help_text='Advanced - what format the server returns for an WMS-I query')
    root_field = models.CharField(max_length=100, null=True, blank=True, help_text='Advanced - For WMS-I (queryable) layers, the root field returned by server. Leave blank for default (will usually be "FIELDS" in returned XML).')
    fields_to_show = models.CharField(max_length=200, null=True, blank=True, help_text='Fields to show when someone uses the identify tool to click on the layer. Leave blank for all.')
    downloadableLink = models.URLField(max_length=400, null=True, blank=True, help_text='URL of link to supporting tool (such as a KML document that will be shown as a download button)')
    layer_params = JSONField(null=True, blank=True, help_text='JSON key/value pairs to be sent to the web service.  ex: {"crs":"urn:ogc:def:crs:EPSG::4326"}')
    spatial_reference = models.CharField(max_length=32, blank=True, null=True, default="EPSG:4326", help_text='The spatial reference of the service.  Should be in ESPG:XXXX format.')
    constraints = models.TextField(null=True, blank=True, help_text='Constrain layer data displayed to certain feature types')

    ## Primarily for http://trac.osgeo.org/openlayers/wiki/OpenLayersOptimization
    additional_domains = models.TextField(null=True, blank=True, help_text='Semicolon seperated list of additional domains for the layer.')

    def __unicode__(self):
        return '{0}'.format(self.name)

    def get_layer_urls(self):
        """
        Returns a list of urls for the layer.
        """
        urls = []

        if getattr(self, 'additional_domains'):
            map(urls.append, (domain for domain in self.additional_domains.split(";") if domain))

        return urls

    def get_absolute_url(self):
        return reverse('layer-update', args=[self.id])

    def get_layer_params(self):
        """
        Returns the layer_params attribute, which should be json
        """
        return self.layer_params

    def layer_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "format": self.image_format,
            "type": self.type,
            "url": self.url,
            "subdomains": self.get_layer_urls(),
            "layer": self.layer,
            "transparent": self.transparent,
            "layerParams": self.layer_params,
            "refreshrate": self.refreshrate,
            "token": self.token,
            "attribution": self.attribution,
            "spatialReference": self.spatial_reference,
            "layerParsingFunction": self.layer_parsing_function,
            "enableIdentify": self.enable_identify,
            "rootField": self.root_field,
            "infoFormat": self.info_format,
            "fieldsToShow": self.fields_to_show,
            "description": self.description,
            "downloadableLink": self.downloadableLink,
            "styles": self.styles,
        }


    class Meta:
        ordering = ["name"]


class Map(models.Model):
    """
    A Map aggregates several layers together.
    """

    title = models.CharField(max_length=75, unique=True)
    description = models.TextField(max_length=800, blank=True, null=True)
    zoom = models.IntegerField(help_text='Sets the default zoom level of the map.', default=5)
    projection = models.CharField(max_length=32, blank=True, null=True, default="EPSG:4326", help_text='Set the default projection for layers added to this map. Note that the projection of the map is usually determined by that of the current baseLayer')
    center_x = models.FloatField(default=0.0, help_text='Sets the center x coordinate of the map.  Maps on event pages default to the location of the event.')
    center_y = models.FloatField(default=0.0, help_text='Sets the center y coordinate of the map.  Maps on event pages default to the location of the event.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '{0}'.format(self.title)

    @property
    def name(self):
        return self.title

    @property
    def center(self):
        """
        A shortcut for the center_x and center_y properties as a tuple
        """
        return self.center_x, self.center_y

    @property
    def layers(self):
        layers = MapLayer.objects.filter(map=self.id)
        return [layer for layer in layers]

    def map_layers_json(self):

        def layer_json(map_layer):
            return {
                "id": map_layer.layer.id,
                "name": map_layer.layer.name,
                "format": map_layer.layer.image_format,
                "type": map_layer.layer.type,
                "url": map_layer.layer.url,
                "subdomains": map_layer.layer.get_layer_urls(),
                "layer": map_layer.layer.layer,
                "shown": map_layer.shown,
                "transparent": map_layer.layer.transparent,
                "opacity": map_layer.opacity,
                "layerParams": map_layer.layer.get_layer_params(),
                "isBaseLayer": map_layer.is_base_layer,
                "displayInLayerSwitcher": map_layer.display_in_layer_switcher,
                "refreshrate": map_layer.layer.refreshrate,
                "token": map_layer.layer.token,
                "attribution": map_layer.layer.attribution,
                "spatialReference": map_layer.layer.spatial_reference,
                "layerParsingFunction": map_layer.layer.layer_parsing_function,
                "enableIdentify": map_layer.layer.enable_identify,
                "rootField": map_layer.layer.root_field,
                "infoFormat": map_layer.layer.info_format,
                "fieldsToShow": map_layer.layer.fields_to_show,
                "description": map_layer.layer.description,
                "downloadableLink": map_layer.layer.downloadableLink,
                "styles": map_layer.layer.styles,
                "zIndex": map_layer.stack_order,
            }

        map_services = list()
        for map_layer in self.layers:
            map_services.append(layer_json(map_layer))

        return map_services

    def all_map_layers_json(self):
        map_services = list()
        for layer in Layer.objects.all():
            map_services.append(layer.layer_json())
        return json.dumps(map_services)

    def to_json(self):
        return json.dumps({
            "center_x": self.center_x,
            "center_y": self.center_y,
            "zoom": self.zoom,
            "projection": self.projection or "EPSG:4326",
            "layers": self.map_layers_json(),
            "all_layers": self.all_map_layers_json()
        })

    def get_absolute_url(self):
        return reverse('map-update', args=[self.id])


class MapLayer(models.Model):
    """
    The MapLayer is the mechanism that joins a Layer to a Map and allows for custom look and feel.
    """

    map = models.ForeignKey(Map, related_name='map_set')
    layer = models.ForeignKey(Layer, related_name='map_layer_set')
    shown = models.BooleanField(default=True)
    stack_order = models.IntegerField()
    opacity = models.FloatField(default=.80)
    is_base_layer = models.BooleanField(help_text="Base Layers are mutually exclusive layers, meaning only one can be enabled at any given time. The currently active base layer determines the available projection (coordinate system) and zoom levels available on the map.")
    display_in_layer_switcher = models.BooleanField()

    class Meta:
        ordering = ["stack_order"]

    def __unicode__(self):
        return 'Layer {0}: {1}'.format(self.stack_order, self.layer)


class Feature(models.Model):
    """
    Model to represent features created in the application.
    """
    aoi = models.ForeignKey(AOI, related_name='features', editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.GeoManager()
    analyst = models.ForeignKey(User, editable=False)
    template = models.ForeignKey("FeatureType", on_delete=models.PROTECT)

    # Allow the user to save their own properties
    properties = JSONField(load_kwargs={}, blank=True, null=True)

    # These help the user identify features when data is exposed outside of the application (Geoserver).
    job = models.ForeignKey(Job, editable=False)
    project = models.ForeignKey(Project, editable=False)

    #Try this vs having individual models
    the_geom = models.GeometryField(blank=True, null=True)

    def geoJSON(self, as_json=True):
        """
        Returns geoJSON of the feature.
        Try to conform to https://github.com/mapbox/simplestyle-spec/tree/master/1.0.0
        """
        
        geojson = SortedDict()
        geojson["type"] = "Feature"
        geojson["properties"] = dict(id=self.id,
                                     template=self.template.id if hasattr(self.template, "id") else None,
                                     analyst=self.analyst.username,
                                     created_at=datetime.strftime(self.created_at, '%Y-%m-%dT%H:%M:%S%Z'),
                                     updated_at=datetime.strftime(self.updated_at, '%Y-%m-%dT%H:%M:%S%Z')
                                     )
        geojson["geometry"] = json.loads(self.the_geom.json)

        return json.dumps(geojson) if as_json else geojson

    def __unicode__(self):
        return "Feature created for {0}".format(self.aoi.name)

    def clean(self):
        obj_geom_type = self.the_geom.geom_type.lower()
        template_geom_type = self.template.type.lower()
        if obj_geom_type != template_geom_type:
            error_text = "Feature type {0} does not match the template's feature type {1}."
            raise ValidationError(error_text.format(obj_geom_type, template_geom_type))

    class Meta:
        ordering = ('-updated_at', 'aoi',)


class FeatureType(models.Model):

    FEATURE_TYPES = (
        ('Point', 'Point'),
        ('Line', 'Line'),
        ('Polygon', 'Polygon'),
    )

    name = models.CharField(max_length=200)
    type = models.CharField(choices=FEATURE_TYPES, max_length=25)
    properties = JSONField(load_kwargs={}, blank=True, null=True)
    style = JSONField(load_kwargs={}, blank=True, null=True)

    def to_json(self):
        return json.dumps(dict(id=self.id,
                               properties=self.properties,
                               name=self.name,
                               type=self.type,
                               style=self.style))

    def featuretypes(self):
        return FeatureType.objects.all()

    def get_absolute_url(self):
        return reverse('feature-type-update', args=[self.id])

    def __unicode__(self):
        return self.name


class GeoeventsSource(models.Model):
    name = models.CharField(max_length=200)
    url = models.URLField(help_text='URL of service location. Requires JSONP support', max_length=500)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.test import Client
from django.test import TestCase


class MapsTest(TestCase):

    def test_create_features_view(self):
        """
        Tests the CreateFeatures View.

        Given an AOI id and geometry and properties as GeoJSON create a new feature.  Error should return a
        human readable message with numeric response status both as JSON.
        """

        pass

    def test_create_map_view(self):
        """
        Tests the CreateMap view.

        View renders both the Map form and an inline form for map layers.

        Context data returned:
        form: The Map ModelForm.
        custom_form: The inline map layer form.
        """

        pass

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, url
from django.views.generic import CreateView, UpdateView, ListView
from forms import FeatureTypeForm, MapForm, LayerForm, MapLayerForm
from views import CreateFeatures, EditFeatures, create_update_map, FeatureTypeListView, FeatureTypeDelete, MapListView, MapDelete, LayerListView, LayerDelete, LayerImport
from models import FeatureType, Map, Layer

urlpatterns = patterns('',

    url(r'^feature-types/?$',
        FeatureTypeListView.as_view(queryset=FeatureType.objects.all()),
                         name='feature-type-list'),

    url(r'^features/create/?$',
        login_required(CreateFeatures.as_view()),
        name='feature-create'),
                       
    url(r'^features/edit/?$',
        login_required(EditFeatures.as_view()),
        name='feature-edit'),

    url(r'^feature-types/create/?',
        login_required(CreateView.as_view(template_name='core/generic_form.html',
                           form_class=FeatureTypeForm)),
        name='feature-type-create'),

    url(r'^feature-types/update/(?P<pk>\d+)/?$',
        login_required(UpdateView.as_view(template_name='core/generic_form.html',
                           queryset=FeatureTypeForm.Meta.model.objects.all(),
                           form_class=FeatureTypeForm)),
        name='feature-type-update'),

    url(r'^feature-types/delete/(?P<pk>\d+)/?$',
        login_required(FeatureTypeDelete.as_view()),
        name='feature-type-delete'),

    # Map list
    url(r'^maps/?$', MapListView.as_view(queryset=Map.objects.all()),
                                              name='map-list'),

    url(r'^maps/delete/(?P<pk>\d+)/?$',
        login_required(MapDelete.as_view()),
        name='map-delete'),


    # Map CRUD Views
    url(r'^create/?$',
        login_required(create_update_map),
        name='map-create'),

    url(r'^update/(?P<pk>\d+)/?$',
        login_required(create_update_map),
        name='map-update'),

    # Layer CRUD Views
    url(r'^layers/?$',
        LayerListView.as_view(queryset=Layer.objects.all()),
                         name='layer-list'),

    url(r'^layers/create/?$',
        login_required(CreateView.as_view(template_name='core/generic_form.html', form_class=LayerForm)),
        name='layer-create'),

    url(r'^layers/update/(?P<pk>\d+)/?$',
        login_required(UpdateView.as_view(template_name='core/generic_form.html',
                           queryset=LayerForm.Meta.model.objects.all(),
                           form_class=LayerForm)),
        name='layer-update'),

    url(r'^layers/delete/(?P<pk>\d+)/?$',
        login_required(LayerDelete.as_view()),
        name='layer-delete'),

    url(r'^layers/import/?$',
        LayerImport.as_view(),
        name='layer-import'),

    # MapLayer CRUD Views

    url(r'^map-layers/create/?$',
        login_required(CreateView.as_view(template_name='core/generic_form.html',
                           form_class=MapLayerForm)),
        name='map-layer-create'),

    url(r'^map-layers/update/(?P<pk>\d+)/?$',
        login_required(UpdateView.as_view(template_name='core/generic_form.html',
                           queryset=MapLayerForm.Meta.model.objects.all(),
                           form_class=MapLayerForm)),
        name='map-layer-update'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from django.core import serializers
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic import ListView, View, DeleteView

from forms import MapForm, MapInlineFormset

from geoq.core.models import AOI
from models import Feature, FeatureType, Map, Layer, GeoeventsSource

import logging

logger = logging.getLogger(__name__)


class CreateFeatures(View):
    """
    Reads GeoJSON from post request and creates AOIS for each features.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        feature = None
        aoi = request.POST.get('aoi')
        geometry = request.POST.get('geometry')
        geojson = json.loads(geometry)
        properties = geojson.get('properties')

        aoi = AOI.objects.get(id=aoi)
        job = getattr(aoi, 'job')
        project = getattr(job, 'project')
        template = properties.get('template') if properties else None

        # TODO: handle exceptions
        if template:
            template = FeatureType.objects.get(id=template)

        attrs = dict(aoi=aoi,
                     job=job,
                     project=project,
                     analyst=request.user,
                     template=template)

        geometry = geojson.get('geometry')
        attrs['the_geom'] = GEOSGeometry(json.dumps(geometry))

        try:
            feature = Feature(**attrs)
            feature.full_clean()
            feature.save()
        except ValidationError as e:
            return HttpResponse(content=json.dumps(dict(errors=e.messages)), mimetype="application/json", status=400)

        # This feels a bit ugly but it does get the GeoJSON into the response
        feature_json = serializers.serialize('json', [feature,])
        feature_list = json.loads(feature_json)
        feature_list[0]['geojson'] = feature.geoJSON(True)
        
        return HttpResponse(json.dumps(feature_list), mimetype="application/json")

class EditFeatures(View):
    """
    Reads feature info from post request and updates associated feature object.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        
        geometry = request.POST.get('geometry')
        geojson = json.loads(geometry)
        properties = geojson.get('properties')
        
        try:
            feature = Feature.objects.get(pk=properties.get('id'))
        except ObjectDoesNotExist:
            raise Http404
    
        geometry = geojson.get('geometry')
        feature.the_geom = GEOSGeometry(json.dumps(geometry))
        
        template = properties.get('template') if properties else None
        
        # TODO: handle exceptions
        if template:
            feature.template = FeatureType.objects.get(id=template)
        
        try:
            feature.full_clean()
            feature.save()
        except ValidationError as e:
            return HttpResponse(content=json.dumps(dict(errors=e.messages)), mimetype="application/json", status=400)
        
        return HttpResponse("{}", mimetype="application/json")

def feature_delete(request,pk):
    try:
        feature = Feature.objects.get(pk=pk)
        feature.delete()
    except ObjectDoesNotExist:
        raise Http404

    return HttpResponse( content=pk, status=200 )

@login_required
def create_update_map(request, pk=None):

    if pk:
        map_obj = Map.objects.get(pk=pk)
    else:
        map_obj = None

    if request.method == 'POST':
        form = MapForm(request.POST, prefix='map', instance=map_obj)
        maplayers_formset = MapInlineFormset(request.POST, prefix='layers', instance=map_obj)

        if form.is_valid() and maplayers_formset.is_valid():
            form.save()
            maplayers_formset.save()
            return HttpResponseRedirect(reverse('job-list'))
    else:
        form = MapForm(prefix='map', instance=map_obj)
        maplayers_formset = MapInlineFormset(prefix='layers', instance=map_obj)
    return render_to_response('core/generic_form.html', {
        'form': form,
        'layer_formset': maplayers_formset,
        'custom_form': 'core/map_create.html',
        'object': map_obj,
        }, context_instance=RequestContext(request))


class MapListView(ListView):
    model = Map

    def get_context_data(self, **kwargs):
        context = super(MapListView, self).get_context_data(**kwargs)
        return context


class MapDelete(DeleteView):
    model = Map
    template_name = "core/generic_confirm_delete.html"

    def get_success_url(self):
        return reverse('map-list')


class FeatureTypeListView(ListView):

    model = FeatureType

    def get_context_data(self, **kwargs):
        context = super(FeatureTypeListView, self).get_context_data(**kwargs)
        return context


class FeatureTypeDelete(DeleteView):
    model = FeatureType
    template_name = "core/generic_confirm_delete.html"

    def get_success_url(self):
        return reverse('feature-type-update')


class LayerListView(ListView):

    model = Layer

    def get_context_data(self, **kwargs):
        context = super(LayerListView, self).get_context_data(**kwargs)
        return context


class LayerImport(ListView):

    model = Layer
    template_name = "maps/layer_import.html"

    def get_context_data(self, **kwargs):
        context = super(LayerImport, self).get_context_data(**kwargs)
        context['geoevents_sources'] = GeoeventsSource.objects.all()
        return context

    def post(self, request, *args, **kwargs):

        layers = request.POST.getlist('layer')

        for lay in layers:
            layer = json.loads(lay)
            # see if it's already in here. assume 'url' and 'layer' attributes make it unique
            l = Layer.objects.filter(url=layer['url'], layer=layer['layer'])
            if not l:
                # add the layer
                new_layer = Layer()
                for key, value in layer.iteritems():
                    if key == 'layer_params':
                        # TODO: need to pass json object here
                        pass
                    else:
                        setattr(new_layer, key, value)

                new_layer.save()

        return HttpResponseRedirect(reverse('layer-list'))


class LayerDelete(DeleteView):
    model = Layer
    template_name = "core/generic_confirm_delete.html"

    def get_success_url(self):
        return reverse('layer-list')
########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

class OutofGZDError(Exception):
    # Exception raised when the requested grid crosses over a GZD boundary. Will handle this at some point
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class GridTooLargeError(Exception):
    # Exception raised when the requested grid is too big.
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class ProgramException(Exception):
    # Exception raised when an internal error occurs
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value)
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import subprocess
# from django.contrib.gis.geos import *
from geojson import MultiPolygon, Feature, FeatureCollection
from exceptions import ProgramException

import logging
logger = logging.getLogger(__name__)

class Grid:

    LETTERS = ['A','B','C','D','E','F','G','H','J','K','L','M','N','P','Q','R','S','T','U','V','W','X','Y','Z','A','B','C']

    def __init__(self, sw_lat, sw_lon, ne_lat, ne_lon):
        self.sw_mgrs = self.get_mgrs(sw_lat,sw_lon)
        self.ne_mgrs = self.get_mgrs(ne_lat,ne_lon)

        if self.sw_mgrs[0:2] != self.ne_mgrs[0:2]:
            raise GridException("Can't create grids across longitudinal boundaries.")

        self.start_100k_easting_index = Grid.LETTERS.index(self.sw_mgrs[3:4])
        self.end_100k_easting_index = Grid.LETTERS.index(self.ne_mgrs[3:4])

        self.start_100k_northing_index = Grid.LETTERS.index(self.sw_mgrs[4:5])
        self.end_100k_northing_index = Grid.LETTERS.index(self.ne_mgrs[4:5])

        # need to check for a maximum size limit...


    # specify a grid point with a 1m designation (add zeros to easting and northing)
    def expand(self,original):
        return original[:7] + '000' + original[7:] + '000'

    # given a lat/lon combination, determine its 1km MGRS grid
    def get_mgrs(self,lat,lon):
        try:
            input = "%s,%s" % (lon, lat)
            process = subprocess.Popen(["GeoConvert","-w","-m","-p","-3","--input-string",input],stdout=subprocess.PIPE)
            return process.communicate()[0].rstrip()
        except Exception:
            import traceback
            errorCode = 'Program Error: ' + traceback.format_exc()
            if errorCode and len(errorCode):
                logger.error(errorCode)

            raise ProgramException('Unable to execute GeoConvert program')


    def get_polygon(self,mgrs_list):
        try:
            m_string = ';'.join(mgrs_list)
            process = subprocess.Popen(["GeoConvert","-w","-g","-p","0","--input-string",m_string],stdout=subprocess.PIPE)
            result = process.communicate()[0].rstrip().split('\n')
        except Exception:
            import traceback
            errorCode = 'Program Error: ' + traceback.format_exc()
            if errorCode and len(errorCode):
                logger.error(errorCode)

            raise ProgramException('Error executing GeoConvert program')

        for i,val in enumerate(result):
            result[i] = tuple(float(x) for x in val.split())

        return MultiPolygon([[result]])

    def create_geojson_polygon_fc(self,coords):
        feature = Feature(geometry=Polygon([coords]))
        return FeatureCollection([feature])

    def get_northing_list(self,count,northing):
        if count:
            return [northing+1,northing]
        else:
            return [northing,northing+1]

    def get_grid_coords(self,mgrs):
        easting = int(mgrs[5:7])
        northing = int(mgrs[7:9])
        heading = mgrs[0:3]
        e_index = Grid.LETTERS.index(mgrs[3:4])
        n_index = Grid.LETTERS.index(mgrs[4:5])
        coords = []


        for x_index in [easting,easting+1]:
            for y_index in self.get_northing_list(x_index-easting,northing):
                e = e_index
                n = n_index
                x = x_index
                y = y_index
                if x == 100:
                    x = 0
                    e = e_index+1
                if y == 100:
                    y = 0
                    n = n_index+1

                corner = "%s%s%s%02d%02d" % (heading, Grid.LETTERS[e], Grid.LETTERS[n], x, y)
                coords.append(self.expand(corner))

        coords.append(coords[0])
        return coords

    def get_array_for_block(self,northing_start,northing_end,easting_start,easting_end,prefix):
        m_array = []

        for n in range(northing_start,northing_end+1):
            for e in range(easting_start,easting_end+1):
                m_array.append("%s%02d%02d" % (prefix,e,n))

        return m_array


    def determine_mgrs_array(self):
        easting_start = int(self.sw_mgrs[5:7])
        easting_end = int(self.ne_mgrs[5:7])
        northing_start = int(self.sw_mgrs[7:9])
        northing_end = int(self.ne_mgrs[7:9])
        gzd_prefix = self.sw_mgrs[0:3]
        mgrs_array = []

        for e in range(self.start_100k_easting_index,self.end_100k_easting_index+1):
            for n in range(self.start_100k_northing_index,self.end_100k_northing_index+1):
                e_start = easting_start if (e == self.start_100k_easting_index) else 0
                e_end = easting_end if (e == self.end_100k_easting_index) else 99
                n_start = northing_start if (n == self.start_100k_northing_index) else 0
                n_end = northing_end if (n == self.end_100k_northing_index) else 99
                prefix = "%s%s%s" % (gzd_prefix,Grid.LETTERS[e],Grid.LETTERS[n])
                mgrs_array.extend(self.get_array_for_block(n_start,n_end,e_start,e_end,prefix))

        return mgrs_array


    def build_grid_fc(self):

        # can probably check for a maximum grid size...

        # and check that bounding box specified correctly

        # if we're not in the same 100,000km grid, will have to do something with this boundary condition
        # probably break each grid down into their components and get the relevant boxes within each

        m_array = self.determine_mgrs_array()

        for i,val in enumerate(m_array):
            gc = self.get_grid_coords(val)
            polygon = self.get_polygon(gc)
            m_array[i] = Feature(geometry=polygon,properties={"mgrs":val},id="mgrs."+val,geometry_name="the_geom")

        return FeatureCollection(m_array)


class GridException(Exception):
    pass



########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import os

#DJANGO_ROOT = os.path.dirname(os.path.realpath(django.__file__))
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))


DEBUG = True
TEMPLATE_DEBUG = True

ADMINS = (
    ('Admin User', 'admin@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'geoq',  # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'geoq',
        'PASSWORD': 'geoq',
        'HOST': 'localhost',  # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '5432',  # Set to empty string for default.
    }
}

AUTH_PROFILE_MODULE = 'accounts.UserProfile'

# Use this to change the base bootstrap library
#BOOTSTRAP_BASE_URL = None

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

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
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = '/opt/src/pyenv/geoq/nga-geoq'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/images/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_URL_FOLDER = ''  # Can be set to something like 'geoq-test/' if the app is not run at root level
STATIC_ROOT = '{0}{1}'.format('/var/www/static/', STATIC_URL_FOLDER)

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '{0}{1}'.format('/static/', STATIC_URL_FOLDER)


# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(SITE_ROOT, 'static'),
    # TODO: Should we add this static location back in?
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'compressor.finders.CompressorFinder',
)
COMPRESS_ENABLED = True
COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)


LEAFLET_CSS = [
    STATIC_URL + 'leaflet/leaflet-draw/leaflet.draw.css',
    os.path.join(STATIC_ROOT, '/static/leaflet/leaflet-draw/leaflet.draw.css')
    ]

LEAFLET_CONFIG = {
    'RESET_VIEW' : False,
    'PLUGINS': {
        'draw': {
            'css': LEAFLET_CSS,
            'js': STATIC_URL + 'leaflet/leaflet-draw/leaflet.draw.js',
            'repo': 'https://github.com/Leaflet/Leaflet.draw'
        },
        'esri': {
            'css': [],
            'js': [STATIC_URL + 'leaflet/esri-leaflet-src.js'],
            'repo': 'https://github.com/Esri/esri-leaflet'
        },
        'esriCluster': {
            'css': [STATIC_URL + 'leaflet/MarkerCluster.css'],
            'js': [STATIC_URL + 'leaflet/ClusteredFeatureLayer.js', STATIC_URL + 'leaflet/leaflet.markercluster.js'],
            'repo': 'https://github.com/Esri/esri-leaflet'
        },
    }
}


# Make this unique, and don't share it with anybody.
SECRET_KEY = '2t=^l2e$e5!du$0^c@3&qk4h_*stwwgp#1o$*n7#eisc)^2(wk'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages'
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    #'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'geoq.core.middleware.UserPermsMiddleware',             # works w/ guardian
)

# auth setup
AUTHENTICATION_BACKENDS = (
    'userena.backends.UserenaAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend', # default
)

ANONYMOUS_USER_ID = -1
AUTH_PROFILE_MODULE = 'accounts.UserProfile'

LOGIN_REDIRECT_URL = '/geoq/'   #'/accounts/%(username)s/'
LOGIN_URL = '/accounts/signin/'
LOGOUT_URL = '/geoq'
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
USERENA_ACTIVATION_DAYS = 3
# /auth setup

ROOT_URLCONF = 'geoq.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'geoq.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(SITE_ROOT, 'templates'),
    SITE_ROOT,
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.gis',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',

    'south',

    'compressor',
    'geoexplorer',
    'reversion',
    'guardian',
    'easy_thumbnails',
    'userena',
    'bootstrap_toolkit',
    'django_select2',
    'leaflet',
    'jsonfield',

    'geoq.accounts', # TODO:Accounts -- Figure out what we are doing
    'geoq.core',
    'geoq.maps',
    'geoq.mgrs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
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
    }
}

# Set default login location
#LOGIN_REDIRECT_URL = '/'


# Gamification variables
#GAMIFICATION_SERVER = 'http://localhost:6111'
#GAMIFICATION_PROJECT = 'django_geoq'

# Override production settings with local settings if they exist
try:
    from local_settings import *

except ImportError, e:
    # local_settings does not exist
    pass

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

from django.contrib import admin
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from geoq.core.views import Dashboard

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', Dashboard.as_view(), name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^geoq/', include('geoq.core.urls')),
    url(r'^maps/', include('geoq.maps.urls')),
    # url(r'^badges/', include('geoq.badges.urls')),
    url(r'^accounts/', include('geoq.accounts.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = wsgi
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

"""
WSGI config for geoq project.

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
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geoq.settings")
sys.path.append(os.path.dirname(__file__))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()


########NEW FILE########
__FILENAME__ = manage
# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geoq.settings")

    manage_dir = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(os.path.join(manage_dir, 'geoq'))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = pavement
# -*- coding: utf-8 -*-
# This technical data was produced for the U. S. Government under Contract No. W15P7T-13-C-F600, and
# is subject to the Rights in Technical Data-Noncommercial Items clause at DFARS 252.227-7013 (FEB 2012)

import os
import sys
import time

from paver.easy import *
from paver.setuputils import setup

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

setup(
    name="geoq",
    packages=['geoq'],
    version='0.0.0.2',
    url="",
    author="Site Admin",
    author_email="admin@localhost"
)


@task
def install_dependencies():
    """ Installs dependencies."""
    sh('pip install --upgrade -r geoq/requirements.txt')


@cmdopts([
    ('fixture=', 'f', 'Fixture to install"'),
])
@task
def install_fixture(options):
    """ Loads the supplied fixture """
    fixture = options.get('fixture')
    sh("python manage.py loaddata {fixture}".format(fixture=fixture))


def _perms_check():
    sh("python manage.py check_permissions")  # Check userena perms
    sh("python manage.py clean_expired")  # Clean our expired userena perms


@task
def install_dev_fixtures():
    """ Installs development fixtures in the correct order """
    fixtures = [
        'geoq/fixtures/initial_data.json',  # user permissions
        'geoq/accounts/fixture/initial_data.json',  # dummy users and groups
        'geoq/maps/fixtures/initial_data_types.json',  # Maps
        'geoq/core/fixture/initial_data.json',
        #'geoq/badges/fixtures/initial_data.json', # Removing badges for now, b/c not working
        ]

    for fixture in fixtures:
        sh("python manage.py loaddata {fixture}".format(fixture=fixture))

    sh("python manage.py migrate --all")
    _perms_check()


@task
def sync():
    """ Runs the syncdb process with migrations """
    sh("python manage.py syncdb --noinput")
    sh("python manage.py migrate --all --no-initial-data")

    fixture = 'geoq/fixtures/initial_data.json'
    sh("python manage.py loaddata {fixture}".format(fixture=fixture))
    _perms_check()


@task
def reset_dev_env():
    """ Resets your dev environment from scratch in the current branch you are in. """
    from geoq import settings
    database = settings.DATABASES.get('default').get('NAME')
    sh('dropdb {database}'.format(database=database))
    createdb()
    sync()
    install_dev_fixtures()


@cmdopts([
    ('bind=', 'b', 'Bind server to provided IP address and port number.'),
])
@task
def start_django(options):
    """ Starts the Django application. """
    bind = options.get('bind', '')
    sh('python manage.py runserver %s &' % bind)


@task
def delayed_fixtures():
    """Loads maps"""
    sh('python manage.py loaddata initial_data.json')


@task
def stop_django():
    """
    Stop the GeoNode Django application
    """
    kill('python', 'runserver')


@needs(['stop_django',
        'sync',
        'start_django'])
def start():
    """ Syncs the database and then starts the development server. """
    info("GeoQ is now available.")


@cmdopts([
    ('template=', 'T', 'Database template to use when creating new database, defaults to "template_postgis"'),
])
@task
def createdb(options):
    """ Creates the database in postgres. """
    from geoq import settings
    template = options.get('template', 'template_postgis')
    database = settings.DATABASES.get('default').get('NAME')
    sh('createdb {database}'.format(database=database, template=template))
    sh('echo "CREATE EXTENSION postgis;CREATE EXTENSION postgis_topology" | psql -d  {database}'.format(database=database))


@task
def create_db_user():
    """ Creates the database in postgres. """
    from geoq import settings
    database = settings.DATABASES.get('default').get('NAME')
    user = settings.DATABASES.get('default').get('USER')
    password = settings.DATABASES.get('default').get('PASSWORD')

    sh('psql -d {database} -c {sql}'.format(
        database=database,
        sql='"CREATE USER {user} WITH PASSWORD \'{password}\';"'.format(user=user, password=password)))
# Order matters for the list of apps, otherwise migrations reset may fail.
_APPS = ['maps', 'accounts', 'badges', 'core']


@task
def reset_migrations():
    """
        Takes an existing environment and updates it after a full migration reset.
    """
    for app in _APPS:
        sh('python manage.py migrate %s 0001 --fake  --delete-ghost-migrations' % app)


@task
def reset_migrations_full():
    """
        Resets south to start with a clean setup.
        This task will process a default list: accounts, core, maps, badges
        To run a full reset which removes all migraitons in repo -- run paver reset_south full

    """
    for app in _APPS:
        sh('rm -rf geoq/%s/migrations/' % app)
        sh('python manage.py schemamigration %s --initial' % app)

    # Finally, we execute the last setup.
    reset_migrations()


def kill(arg1, arg2):
    """Stops a proces that contains arg1 and is filtered by arg2
    """
    from subprocess import Popen, PIPE

    # Wait until ready
    t0 = time.time()
    # Wait no more than these many seconds
    time_out = 30
    running = True
    lines = []

    while running and time.time() - t0 < time_out:
        p = Popen('ps aux | grep %s' % arg1, shell=True,
                  stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)

        lines = p.stdout.readlines()

        running = False
        for line in lines:

            if '%s' % arg2 in line:
                running = True

                # Get pid
                fields = line.strip().split()

                info('Stopping %s (process number %s)' % (arg1, fields[1]))
                kill_cmd = 'kill -9 %s 2> /dev/null' % fields[1]
                os.system(kill_cmd)

        # Give it a little more time
        time.sleep(1)
    else:
        pass

    if running:
        raise Exception('Could not stop %s: '
                        'Running processes are\n%s'
                        % (arg1, '\n'.join([l.strip() for l in lines])))

########NEW FILE########
