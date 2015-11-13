__FILENAME__ = index
from django.core.urlresolvers import reverse

from admin_tools.dashboard import modules, Dashboard
from admin_tools.utils import get_admin_site_name

from crate.web.dashboard.modules import StatusModule, RedisStatusModule


class CrateIndexDashboard(Dashboard):

    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        # append a link list module for "quick links"
        self.children.append(modules.LinkList(
            "Quick links",
            layout="inline",
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                ["Return to site", "/"],
                ["Change password",
                 reverse("%s:password_change" % site_name)],
                ["Log out", reverse("%s:logout" % site_name)],
            ]
        ))

        # append an app list module for "Administration"
        self.children.append(modules.AppList(
            "Administration",
            models=('django.contrib.*',),
        ))

        # append an app list module for "Applications"
        self.children.append(modules.AppList(
            "Applications",
            exclude=[
                "django.contrib.*",
                "pinax.apps.*",
                "djcelery.*",
                "emailconfirmation.*",
                "profiles.*",
            ],
        ))

        self.children.append(StatusModule("Status"))

        self.children.append(RedisStatusModule(
            "Redis Status",

        ))

        # append a recent actions module
        self.children.append(modules.RecentActions("Recent Actions", 5))

########NEW FILE########
__FILENAME__ = modules
import collections
import datetime

import redis

from django.conf import settings
from django.utils.timezone import utc

from admin_tools.dashboard.modules import DashboardModule


class StatusModule(DashboardModule):

    title = "Status"
    template = "admin_tools/dashboard/modules/status.html"

    def init_with_context(self, context):
        if hasattr(settings, "PYPI_DATASTORE"):
            datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))

            if datastore.get("crate:pypi:since") is not None:
                self.last_sync = datetime.datetime.fromtimestamp(float(datastore.get("crate:pypi:since")))
                self.last_sync.replace(tzinfo=utc)
            else:
                self.last_sync = None

            self.celery_queue_length = datastore.llen("celery")

    def is_empty(self):
        return False


class RedisStatusModule(DashboardModule):

    title = "Redis Status"
    template = "admin_tools/dashboard/modules/redis.html"

    def init_with_context(self, context):
        if hasattr(settings, "PYPI_DATASTORE"):
            datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))
            self.redis_info = collections.OrderedDict(sorted([(k, v) for k, v in datastore.info().iteritems()], key=lambda x: x[0]))

    def is_empty(self):
        return False

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from crate.web.history.models import Event


class EventAdmin(admin.ModelAdmin):
    list_display = ["package", "version", "action", "data", "created"]
    list_filter = ["action", "created"]
    search_fields = ["package", "version"]


admin.site.register(Event, EventAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Event'
        db.create_table('history_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('package', self.gf('django.db.models.fields.SlugField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('action', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('data', self.gf('jsonfield.fields.JSONField')()),
        ))
        db.send_create_signal('history', ['Event'])

    def backwards(self, orm):
        # Deleting model 'Event'
        db.delete_table('history_event')

    models = {
        'history.event': {
            'Meta': {'object_name': 'Event'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.SlugField', [], {'max_length': '150'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        }
    }

    complete_apps = ['history']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_event_data
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Changing field 'Event.data'
        db.alter_column('history_event', 'data', self.gf('jsonfield.fields.JSONField')(null=True))

    def backwards(self, orm):
        # User chose to not deal with backwards NULL issues for 'Event.data'
        raise RuntimeError("Cannot reverse this migration. 'Event.data' and its values cannot be restored.")

    models = {
        'history.event': {
            'Meta': {'object_name': 'Event'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.SlugField', [], {'max_length': '150'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'})
        }
    }

    complete_apps = ['history']

########NEW FILE########
__FILENAME__ = 0003_convert_changelog_to_history
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    depends_on = (
        ("packages", "0019_auto__add_field_releasefile_hidden"),
    )

    def forwards(self, orm):
        for cl in orm["packages.ChangeLog"].objects.all().select_related("package", "version"):
            e = orm["history.Event"](created=cl.created, package=cl.package.name)

            if cl.type == "new":
                e.action = "package_create"
            else:
                e.action = "release_create"
                e.version = cl.release.version

            e.save()

    def backwards(self, orm):
        raise Exception("Cannot Go Backwards")

    models = {
        'history.event': {
            'Meta': {'object_name': 'Event'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.SlugField', [], {'max_length': '150'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'})
        },
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages', 'history']
    symmetrical = True

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from jsonfield import JSONField
from model_utils import Choices
from model_utils.models import TimeStampedModel

from crate.web.packages.models import Package, Release, ReleaseFile


class Event(TimeStampedModel):

    ACTIONS = Choices(
            ("package_create", _("Package Created")),
            ("package_delete", _("Package Deleted")),
            ("release_create", _("Release Created")),
            ("release_delete", _("Release Deleted")),
            ("file_add", _("File Added")),
            ("file_remove", _("File Removed")),
        )

    package = models.SlugField(max_length=150)
    version = models.CharField(max_length=512, blank=True)

    action = models.CharField(max_length=25, choices=ACTIONS)

    data = JSONField(null=True, blank=True)


@receiver(post_save, sender=Package)
def history_package_create(instance, created, **kwargs):
    if created:
        Event.objects.create(
            package=instance.name,
            action=Event.ACTIONS.package_create
        )


@receiver(post_delete, sender=Package)
def history_package_delete(instance, **kwargs):
    Event.objects.create(
        package=instance.name,
        action=Event.ACTIONS.package_delete
    )


@receiver(post_save, sender=Release)
def history_release_update(instance, created, **kwargs):
    if created:
        Event.objects.create(
            package=instance.package.name,
            version=instance.version,
            action=Event.ACTIONS.release_create
        )

    if instance.has_changed("hidden"):
        if instance.hidden:
            Event.objects.create(
                package=instance.package.name,
                version=instance.version,
                action=Event.ACTIONS.release_delete
            )
        else:
            Event.objects.create(
                package=instance.package.name,
                version=instance.version,
                action=Event.ACTIONS.release_create
            )


@receiver(post_save, sender=ReleaseFile)
def history_releasefile_update(instance, created, **kwargs):
    e = None

    if instance.has_changed("hidden"):
        if instance.hidden:
            e = Event.objects.create(
                package=instance.release.package.name,
                version=instance.release.version,
                action=Event.ACTIONS.file_remove
            )

    if e is not None:
        try:
            e.data = {
                "filename": instance.filename,
                "digest": instance.digest,
                "uri": instance.get_absolute_url(),
            }
        except ValueError:
            pass
        else:
            e.save()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from crate.web.lists.models import List


class PackageInline(admin.TabularInline):
    model = List.packages.through
    raw_id_fields = ["package"]
    extra = 0


class ListAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["name", "user__username", "packages__name"]
    raw_id_fields = ["user"]
    exclude = ["packages"]

    inlines = [
        PackageInline,
    ]

admin.site.register(List, ListAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms

from crate.web.lists.models import List


class CreateListForm(forms.ModelForm):

    class Meta:
        model = List
        fields = ["name", "description", "private"]

    def __init__(self, *args, **kwargs):
        super(CreateListForm, self).__init__(*args, **kwargs)

        self.fields["description"].widget = forms.Textarea()

########NEW FILE########
__FILENAME__ = helpers
from jingo import register

from crate.web.lists.forms import CreateListForm
from crate.web.lists.models import List


@register.function
def lists_for_user(user):
    if user.is_authenticated():
        return List.objects.filter(user=user).prefetch_related("packages")

    return []


@register.function
def new_list_with_package_form():
    return CreateListForm()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'List'
        db.create_table('lists_list', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('private', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('lists', ['List'])

        # Adding unique constraint on 'List', fields ['user', 'name']
        db.create_unique('lists_list', ['user_id', 'name'])

        # Adding M2M table for field packages on 'List'
        db.create_table('lists_list_packages', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('list', models.ForeignKey(orm['lists.list'], null=False)),
            ('package', models.ForeignKey(orm['packages.package'], null=False))
        ))
        db.create_unique('lists_list_packages', ['list_id', 'package_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'List', fields ['user', 'name']
        db.delete_unique('lists_list', ['user_id', 'name'])

        # Deleting model 'List'
        db.delete_table('lists_list')

        # Removing M2M table for field packages on 'List'
        db.delete_table('lists_list_packages')

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
        'lists.list': {
            'Meta': {'unique_together': "(('user', 'name'),)", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_list_slug__add_unique_list_user_slug
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'List.slug'
        db.add_column('lists_list', 'slug',
                      self.gf('django.db.models.fields.SlugField')(max_length=50, null=True),
                      keep_default=False)

        # Adding unique constraint on 'List', fields ['user', 'slug']
        db.create_unique('lists_list', ['user_id', 'slug'])

    def backwards(self, orm):
        # Removing unique constraint on 'List', fields ['user', 'slug']
        db.delete_unique('lists_list', ['user_id', 'slug'])

        # Deleting field 'List.slug'
        db.delete_column('lists_list', 'slug')

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
        'lists.list': {
            'Meta': {'unique_together': "[('user', 'name'), ('user', 'slug')]", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']

########NEW FILE########
__FILENAME__ = 0003_migrate_name_to_slug
# -*- coding: utf-8 -*-
from django.db.models import Q
from django.template.defaultfilters import slugify

from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        used = set()
        for l in orm["lists.List"].objects.filter(Q(slug=None) | Q(slug="")):
            slug = slugify(l.name)
            i = 1

            while (l.user, slug) in used:
                slug = slugify(u"%s %s" % (self.name, i))
                i += 1

            used.add((l.user, slug))

            l.slug = slug
            l.save()

    def backwards(self, orm):
        pass

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
        'lists.list': {
            'Meta': {'unique_together': "[('user', 'name'), ('user', 'slug')]", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_list_slug
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Changing field 'List.slug'
        db.alter_column('lists_list', 'slug', self.gf('django.db.models.fields.SlugField')(default='', max_length=50))

    def backwards(self, orm):
        # Changing field 'List.slug'
        db.alter_column('lists_list', 'slug', self.gf('django.db.models.fields.SlugField')(max_length=50, null=True))

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
        'lists.list': {
            'Meta': {'unique_together': "[('user', 'name'), ('user', 'slug')]", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_list_description
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'List.description'
        db.add_column('lists_list', 'description',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=250, blank=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'List.description'
        db.delete_column('lists_list', 'description')

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
        'lists.list': {
            'Meta': {'unique_together': "[('user', 'name'), ('user', 'slug')]", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models, IntegrityError
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel


class List(TimeStampedModel):
    user = models.ForeignKey("auth.User")
    # Translators: This is used to allow naming a specific list of packages.
    name = models.CharField(_("Name"), max_length=50, db_index=True)
    slug = models.SlugField(max_length=50)

    description = models.CharField(max_length=250, blank=True)

    private = models.BooleanField(_("Private List"), default=False, help_text=_("Private lists are visible only to you."))

    packages = models.ManyToManyField("packages.Package", verbose_name=_("Packages"))

    class Meta:
        unique_together = [
            ("user", "name"),
            ("user", "slug"),
        ]

    def save(self, *args, **kwargs):
        if not self.name:
            raise  IntegrityError("Name cannot be empty")

        if not self.slug:
            slug = slugify(self.name)
            i = 1

            while List.objects.filter(user=self.user, slug=slug).exists():
                slug = slugify(u"%s %s" % (self.name, i))
                i += 1

            self.slug = slug

        return super(List, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%(username)s / %(listname)s" % {"username": self.user.username, "listname": self.name}

    def get_absolute_url(self):
        return reverse("lists_detail", kwargs={"username": self.user.username, "slug": self.slug})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from crate.web.lists.views import AddToList, AddToNewList, RemoveFromList, ListsList, ListDetail

urlpatterns = patterns("",
    url(r"^(?P<username>[^/]+)/lists/$", ListsList.as_view(), name="lists_list"),
    url(r"^(?P<username>[^/]+)/lists/(?P<slug>[^/]+)/$", ListDetail.as_view(), name="lists_detail"),

    url(r"^(?P<list>[^/]+)/(?P<package>[^/]+)/add/$", AddToList.as_view(), name="add_package_to_list"),
    url(r"^_/(?P<package>[^/]+)/new/$", AddToNewList.as_view(), name="add_package_to_new_list"),
    url(r"^(?P<list>[^/]+)/(?P<package>[^/]+)/remove/$", RemoveFromList.as_view(), name="remove_package_from_list"),
)

########NEW FILE########
__FILENAME__ = views
import json

from django.db.models import Q
from django.http import HttpResponse
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from crate.web.lists.models import List
from crate.web.packages.models import Package


class AddToList(View):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AddToList, self).dispatch(*args, **kwargs)

    def render_json(self, **data):
        return HttpResponse(json.dumps(data), mimetype="application/json")

    def get_package(self, package):
        return next(iter(Package.objects.filter(name=package)[:1]), None)

    def get_list(self, list, user):
        return next(iter(List.objects.filter(name=list, user=user)[:1]), None)

    def get_message(self):
        return _("Successfully added %(package)s to %(list)s.") % self.kwargs

    def post(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

        package = self.get_package(self.kwargs.get("package"))

        if package is None:
            return self.render_json(
                        package=self.kwargs.get("package"),
                        list=self.kwargs.get("list"),
                        success=False,
                        message=_("Package does not exist")
                    )

        user_list = self.get_list(self.kwargs.get("list", None), user=request.user)

        if user_list is None:
            return self.render_json(
                        package=self.kwargs.get("package"),
                        list=self.kwargs.get("list"),
                        success=False,
                        message=_("List does not exist")
                    )

        user_list.packages.add(package)

        messages.success(request, self.get_message())

        return self.render_json(
                    package=self.kwargs.get("package"),
                    list=self.kwargs.get("list"),
                    success=True,
                    message=self.get_message()
                )


class AddToNewList(AddToList):

    def get_message(self):
        kw = self.kwargs.copy()
        kw.update({
            "list": self.request.POST.get("name"),
            })
        return _("Successfully added %(package)s to %(list)s.") % kw

    def get_list(self, list, user):
        if list is None:
            list = self.request.POST.get("name")

        defaults = {
            "private": self.request.POST.get("private", False),
            "description": self.request.POST.get("description", ""),
        }
        user_list, c = List.objects.get_or_create(user=user, name=list, defaults=defaults)

        if not c and user_list.private != self.request.POST.get("private", False):
            user_list.private = self.request.POST.get("private", False)
            user_list.save()

        if not c and user_list.description != self.request.POST.get("description", ""):
            user_list.description = self.request.POST.get("description", "")
            user_list.save()

        return user_list


class RemoveFromList(View):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RemoveFromList, self).dispatch(*args, **kwargs)

    def render_json(self, **data):
        return HttpResponse(json.dumps(data), mimetype="application/json")

    def get_message(self):
        return _("Successfully removed %(package)s from %(list)s.") % self.kwargs

    def post(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

        try:
            package = Package.objects.get(name=kwargs.get("package"))
            user_list = List.objects.get(name=kwargs.get("list"), user=request.user)
        except Package.DoesNotExist:
            return self.render_json(package=kwargs.get("package"), list=kwargs.get("list"), success=False, message=_("Package does not exist"))
        except List.DoesNotExist:
            return self.render_json(package=kwargs.get("package"), list=kwargs.get("list"), success=False, message=_("List does not exist"))

        user_list.packages.remove(package)

        messages.success(request, self.get_message())

        return self.render_json(package=kwargs.get("package"), list=kwargs.get("list"), success=True, message=self.get_message())


class ListsList(ListView):

    queryset = List.objects.all().order_by("name")

    def get_queryset(self):
        qs = super(ListsList, self).get_queryset()
        qs = qs.filter(user__username=self.kwargs.get("username"))

        if self.request.user.is_authenticated():
            qs = qs.filter(Q(private=False) | Q(private=True, user=self.request.user))
        else:
            qs = qs.filter(private=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super(ListsList, self).get_context_data(**kwargs)

        ctx.update({
            "username": self.kwargs.get("username"),
        })

        return ctx


class ListDetail(DetailView):

    queryset = List.objects.all().select_related("packages")

    def get_queryset(self):
        qs = super(ListDetail, self).get_queryset()
        qs = qs.filter(user__username=self.kwargs.get("username"))

        if self.request.user.is_authenticated():
            qs = qs.filter(Q(private=False) | Q(private=True, user=self.request.user))
        else:
            qs = qs.filter(private=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super(ListDetail, self).get_context_data(**kwargs)

        ctx.update({
            "packages": self.object.packages.all().extra(select={"lower_name": "lower(name)"}).order_by("lower_name"),
        })

        return ctx

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from crate.web.packages.models import Package, Release, ReleaseFile, TroveClassifier, PackageURI
from crate.web.packages.models import ReleaseRequire, ReleaseProvide, ReleaseObsolete, ReleaseURI, ChangeLog
from crate.web.packages.models import DownloadDelta, ReadTheDocsPackageSlug


class PackageURIAdmin(admin.TabularInline):
    model = PackageURI
    extra = 0


class PackageAdmin(admin.ModelAdmin):
    inlines = [PackageURIAdmin]
    list_display = ["name", "created", "modified", "downloads_synced_on"]
    list_filter = ["created", "modified", "downloads_synced_on"]
    search_fields = ["name"]


class ReleaseRequireInline(admin.TabularInline):
    model = ReleaseRequire
    extra = 0


class ReleaseProvideInline(admin.TabularInline):
    model = ReleaseProvide
    extra = 0


class ReleaseObsoleteInline(admin.TabularInline):
    model = ReleaseObsolete
    extra = 0


class ReleaseFileInline(admin.TabularInline):
    model = ReleaseFile
    extra = 0


class ReleaseURIInline(admin.TabularInline):
    model = ReleaseURI
    extra = 0


class ReleaseAdmin(admin.ModelAdmin):
    inlines = [ReleaseURIInline, ReleaseFileInline, ReleaseRequireInline, ReleaseProvideInline, ReleaseObsoleteInline]
    list_display = ["__unicode__", "package", "version", "summary", "author", "author_email", "maintainer", "maintainer_email", "created", "modified"]
    list_filter = ["created", "modified", "hidden"]
    search_fields = ["package__name", "version", "summary", "author", "author_email", "maintainer", "maintainer_email"]
    raw_id_fields = ["package"]


class TroveClassifierAdmin(admin.ModelAdmin):
    list_display = ["trove"]
    search_fields = ["trove"]


class ReleaseFileAdmin(admin.ModelAdmin):
    list_display = ["release", "type", "python_version", "downloads", "comment", "created", "modified"]
    list_filter = ["type", "created", "modified"]
    search_fields = ["release__package__name", "filename", "digest"]
    raw_id_fields = ["release"]


class DownloadDeltaAdmin(admin.ModelAdmin):
    list_display = ["file", "date", "delta"]
    list_filter = ["date"]
    search_fields = ["file__release__package__name", "file__filename"]
    raw_id_fields = ["file"]


class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ["package", "release", "type", "created", "modified"]
    list_filter = ["type", "created", "modified"]
    search_fields = ["package__name"]
    raw_id_fields = ["package", "release"]


class ReadTheDocsPackageSlugAdmin(admin.ModelAdmin):
    list_display = ["package", "slug"]
    search_fields = ["package__name", "slug"]
    raw_id_fields = ["package"]


admin.site.register(Package, PackageAdmin)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(ReleaseFile, ReleaseFileAdmin)
admin.site.register(TroveClassifier, TroveClassifierAdmin)
admin.site.register(DownloadDelta, DownloadDeltaAdmin)
admin.site.register(ChangeLog, ChangeLogAdmin)
admin.site.register(ReadTheDocsPackageSlug, ReadTheDocsPackageSlugAdmin)

########NEW FILE########
__FILENAME__ = api
from django.conf.urls import url

from tastypie import fields
from tastypie.bundle import Bundle
from tastypie.cache import SimpleCache
from tastypie.constants import ALL
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash

from crate.web.packages.models import Package, Release, ReleaseFile, ReleaseURI, TroveClassifier
from crate.web.packages.models import ReleaseRequire, ReleaseProvide, ReleaseObsolete


class InlineTroveClassifierResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["trove"]
        filtering = {
            "trove": ALL,
        }
        include_resource_uri = False
        ordering = ["trove"]
        queryset = TroveClassifier.objects.all()
        resource_name = "classifier"


class PackageResource(ModelResource):
    releases = fields.ToManyField("packages.api.ReleaseResource", "releases")
    downloads = fields.IntegerField("downloads")
    latest = fields.ToOneField("packages.api.InlineReleaseResource", "latest", full=True)

    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["created", "downloads_synced_on", "downloads", "name"]
        filtering = {
            "name": ALL,
            "created": ALL,
            "downloads_synced_on": ALL,
        }
        include_absolute_url = True
        ordering = ["created", "downloads_synced_on"]
        queryset = Package.objects.all()
        resource_name = "package"

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<name>[^/]+)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view("dispatch_detail"), name="api_dispatch_detail"),
        ]

    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            "resource_name": self._meta.resource_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs["name"] = bundle_or_obj.obj.name
        else:
            kwargs["name"] = bundle_or_obj.name

        if self._meta.api_name is not None:
            kwargs["api_name"] = self._meta.api_name

        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)


class InlineReleaseResource(ModelResource):
    files = fields.ToManyField("packages.api.ReleaseFileResource", "files", full=True)
    uris = fields.ToManyField("packages.api.ReleaseURIResource", "uris", full=True)
    classifiers = fields.ListField()
    requires = fields.ToManyField("packages.api.ReleaseRequireResource", "requires", full=True)
    provides = fields.ToManyField("packages.api.ReleaseProvideResource", "provides", full=True)
    obsoletes = fields.ToManyField("packages.api.ReleaseObsoleteResource", "obsoletes", full=True)
    downloads = fields.IntegerField("downloads")

    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = [
                    "author", "author_email", "created", "description", "download_uri", "downloads",
                    "license", "maintainer", "maintainer_email", "package", "platform", "classifiers",
                    "requires_python", "summary", "version"
                ]
        include_absolute_url = True
        include_resource_uri = False
        queryset = Release.objects.all()


class ReleaseResource(ModelResource):
    package = fields.ForeignKey(PackageResource, "package")
    files = fields.ToManyField("packages.api.ReleaseFileResource", "files", full=True)
    uris = fields.ToManyField("packages.api.ReleaseURIResource", "uris", full=True)
    classifiers = fields.ListField()
    requires = fields.ToManyField("packages.api.ReleaseRequireResource", "requires", full=True)
    provides = fields.ToManyField("packages.api.ReleaseProvideResource", "provides", full=True)
    obsoletes = fields.ToManyField("packages.api.ReleaseObsoleteResource", "obsoletes", full=True)
    downloads = fields.IntegerField("downloads")

    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = [
                    "author", "author_email", "created", "description", "download_uri", "downloads",
                    "license", "maintainer", "maintainer_email", "package", "platform", "classifiers",
                    "requires_python", "summary", "version"
                ]
        filtering = {
            "author": ALL,
            "author_email": ALL,
            "maintainer": ALL,
            "maintainer_email": ALL,
            "created": ALL,
            "license": ALL,
            "version": ALL,
        }
        include_absolute_url = True
        ordering = ["created", "license", "package", "version"]
        queryset = Release.objects.all()
        resource_name = "release"

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<package__name>[^/]+)-(?P<version>[^/]+)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view("dispatch_detail"), name="api_dispatch_detail"),
        ]

    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            "resource_name": self._meta.resource_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs["package__name"] = bundle_or_obj.obj.package.name
            kwargs["version"] = bundle_or_obj.obj.version
        else:
            kwargs["name"] = bundle_or_obj.package.name
            kwargs["version"] = bundle_or_obj.version

        if self._meta.api_name is not None:
            kwargs["api_name"] = self._meta.api_name

        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)

    def dehydrate_classifiers(self, bundle):
        return [c.trove for c in bundle.obj.classifiers.all()]


class ReleaseFileResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["comment", "created", "digest", "downloads", "file", "filename", "python_version", "type"]
        include_resource_uri = False
        queryset = ReleaseFile.objects.all()
        resource_name = "files"


class ReleaseURIResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["label", "uri"]
        include_resource_uri = False
        queryset = ReleaseURI.objects.all()
        resource_name = "uris"


class ReleaseRequireResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["kind", "name", "version", "environment"]
        include_resource_uri = False
        queryset = ReleaseRequire.objects.all()
        resource_name = "requires"


class ReleaseProvideResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["kind", "name", "version", "environment"]
        include_resource_uri = False
        queryset = ReleaseProvide.objects.all()
        resource_name = "provides"


class ReleaseObsoleteResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["kind", "name", "version", "environment"]
        include_resource_uri = False
        queryset = ReleaseObsolete.objects.all()
        resource_name = "obsoletes"

########NEW FILE########
__FILENAME__ = evaluators
import slumber

import jinja2

from slumber import exceptions

from django.core.cache import cache
from django.utils.translation import ugettext as _

from crate.web.packages.utils import verlib


class ReleaseEvaluator(object):
    def evaluate(self, types=None):
        if types is None:
            types = ["pep386", "hosting", "documentation"]

        return [getattr(self, "evaluate_%s" % t)() for t in types]

    def evaluate_pep386(self):
        if not hasattr(self, "_evaluate_pep386"):
            normalized = verlib.suggest_normalized_version(self.version)

            evaluator = {
                "title": _("PEP386 Compatibility"),
                "message": jinja2.Markup(_("PEP386 defines a specific allowed syntax for Python package versions."
                                           "<br /><br />"
                                           "Previously it was impossible to accurately determine across any Python package what "
                                           "order the versions should go in, but with PEP386 we can now intelligently sort by version..."
                                           "<br /><br />"
                                           "But only if the version numbers are compatible!"))
            }

            if self.version == normalized:
                self._evaluate_pep386 = {
                    "level": "success",
                    "message": jinja2.Markup(_('Compatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
            elif normalized is not None:
                self._evaluate_pep386 = {
                    "level": None,
                    "message": jinja2.Markup(_('Almost Compatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_pep386 = {
                    "level": "error",
                    "message": jinja2.Markup(_('Incompatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
        return self._evaluate_pep386

    def evaluate_hosting(self):
        if not hasattr(self, "_evaluate_hosting"):
            evaluator = {
                "title": _("Package Hosting"),
                "message": jinja2.Markup(
                    _("Did you know that packages listed on PyPI aren't required to host there?"
                      "<br /><br />"
                      "When your package manager tries to install a package from PyPI it looks in number "
                      "of locations, one such location is an author specified url of where the package can "
                      "be downloaded from."
                      "<br /><br />"
                      "Packages hosted by the author means that installing this package depends on the "
                      "authors server staying up, adding another link in the chain that can cause your "
                      "installation to fail")
                ),
            }

            if self.files.all().exists():
                self._evaluate_hosting = {
                    "level": "success",
                    "message": _("Package is hosted on PyPI"),
                    "evaluator": evaluator,
                }
            elif self.download_uri:
                self._evaluate_hosting = {
                    "level": "error",
                    "message": _("Package isn't hosted on PyPI"),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_hosting = {
                    "level": "error",
                    "message": _("No Package Hosting"),
                    "evaluator": evaluator,
                }
        return self._evaluate_hosting

    def evaluate_documentation(self):
        if not hasattr(self, "_evaluate_documentation"):
            evaluator = {
                "title": _("Documentation hosted on Read The Docs"),
                "message": jinja2.Markup(
                    _("Documentation can be one of the most important parts of any library. "
                      "Even more important than just having documentation, is making sure that people are "
                      "able to find it easily."
                      "<br /><br />"
                      "Read The Docs is an open source platform for hosting documentation generated by Sphinx."
                      "<br /><br />"
                      "Hosting your documentation on Read The Docs is easy (even if it's just an additional copy), and "
                      "it allows people who want to use your package the ability to locate your documentation in "
                      "what is quickly becoming a one stop shop for online open source documentation."
                      "<br /><br />"
                      "<small>If this says you aren't hosted on Read The Docs and you are please contact "
                      "<a href='mailto:support@crate.io'>support@crate.io</a></small>")
                ),
            }

            from crate.web.packages.models import ReadTheDocsPackageSlug

            qs = ReadTheDocsPackageSlug.objects.filter(package=self.package)
            slug = qs[0].slug if qs else self.package.name

            key = "evaluate:rtd:%s" % slug

            if cache.get(key, version=4) is not None:
                hosted_on_rtd, url = cache.get(key, version=4)
            else:
                try:
                    api = slumber.API(base_url="http://readthedocs.org/api/v1/")
                    results = api.project.get(slug__iexact=slug)
                except exceptions.SlumberHttpBaseException:
                    return {
                        "level": "unknown",
                        "message": jinja2.Markup(_('There was an error with the <a href="http://readthedocs.org/">Read The Docs</a> API.')),
                        "evaluator": evaluator,
                    }

                if results["objects"]:
                    hosted_on_rtd = True
                    url = results["objects"][0]["subdomain"]
                else:
                    hosted_on_rtd = False
                    url = None

                cache.set(key, (hosted_on_rtd, url), 60 * 30, version=4)  # Cache This for 30 Minutes

            if hosted_on_rtd:
                self._evaluate_documentation = {
                    "level": "success",
                    "message": jinja2.Markup(_('Available on <a href="%s">Read The Docs</a>') % url),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_documentation = {
                    "level": "unknown",
                    "message": jinja2.Markup(_('Unavailable on <a href="http://readthedocs.org/">Read The Docs</a>')),
                    "evaluator": evaluator,
                }
        return self._evaluate_documentation

########NEW FILE########
__FILENAME__ = helpers
from django.db.models import Sum

from jingo import register

from crate.web.packages.models import Package, ReleaseFile


@register.function
def package_information():
    return {
        "downloads": ReleaseFile.objects.all().aggregate(total_downloads=Sum("downloads")).get("total_downloads", 0),
        "packages": Package.objects.all().count(),
    }

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TroveClassifier'
        db.create_table('packages_troveclassifier', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trove', self.gf('django.db.models.fields.CharField')(unique=True, max_length=350)),
        ))
        db.send_create_signal('packages', ['TroveClassifier'])

        # Adding model 'Package'
        db.create_table('packages_package', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 227535))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 227680))),
            ('name', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=150)),
        ))
        db.send_create_signal('packages', ['Package'])

        # Adding model 'PackageURI'
        db.create_table('packages_packageuri', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(related_name='package_links', to=orm['packages.Package'])),
            ('uri', self.gf('django.db.models.fields.URLField')(max_length=400)),
        ))
        db.send_create_signal('packages', ['PackageURI'])

        # Adding unique constraint on 'PackageURI', fields ['package', 'uri']
        db.create_unique('packages_packageuri', ['package_id', 'uri'])

        # Adding model 'Release'
        db.create_table('packages_release', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 229663), db_index=True)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 229762))),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(related_name='releases', to=orm['packages.Package'])),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('platform', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('summary', self.gf('django.db.models.fields.TextField')()),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('keywords', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('license', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('author', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('author_email', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('maintainer', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('maintainer_email', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('requires_python', self.gf('django.db.models.fields.CharField')(max_length=25, blank=True)),
            ('download_uri', self.gf('django.db.models.fields.URLField')(max_length=1024, blank=True)),
            ('raw_data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('packages', ['Release'])

        # Adding unique constraint on 'Release', fields ['package', 'version']
        db.create_unique('packages_release', ['package_id', 'version'])

        # Adding M2M table for field classifiers on 'Release'
        db.create_table('packages_release_classifiers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('release', models.ForeignKey(orm['packages.release'], null=False)),
            ('troveclassifier', models.ForeignKey(orm['packages.troveclassifier'], null=False))
        ))
        db.create_unique('packages_release_classifiers', ['release_id', 'troveclassifier_id'])

        # Adding model 'ReleaseFile'
        db.create_table('packages_releasefile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 228759), db_index=True)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 228860))),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='files', to=orm['packages.Release'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=512)),
            ('filename', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
            ('digest', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('python_version', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('downloads', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('packages', ['ReleaseFile'])

        # Adding unique constraint on 'ReleaseFile', fields ['release', 'type', 'python_version', 'filename']
        db.create_unique('packages_releasefile', ['release_id', 'type', 'python_version', 'filename'])

        # Adding model 'ReleaseURI'
        db.create_table('packages_releaseuri', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='uris', to=orm['packages.Release'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('uri', self.gf('django.db.models.fields.URLField')(max_length=500)),
        ))
        db.send_create_signal('packages', ['ReleaseURI'])

        # Adding model 'ReleaseRequire'
        db.create_table('packages_releaserequire', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='requires', to=orm['packages.Release'])),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('environment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('packages', ['ReleaseRequire'])

        # Adding model 'ReleaseProvide'
        db.create_table('packages_releaseprovide', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='provides', to=orm['packages.Release'])),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('environment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('packages', ['ReleaseProvide'])

        # Adding model 'ReleaseObsolete'
        db.create_table('packages_releaseobsolete', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='obsoletes', to=orm['packages.Release'])),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('environment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('packages', ['ReleaseObsolete'])

    def backwards(self, orm):
        # Removing unique constraint on 'ReleaseFile', fields ['release', 'type', 'python_version', 'filename']
        db.delete_unique('packages_releasefile', ['release_id', 'type', 'python_version', 'filename'])

        # Removing unique constraint on 'Release', fields ['package', 'version']
        db.delete_unique('packages_release', ['package_id', 'version'])

        # Removing unique constraint on 'PackageURI', fields ['package', 'uri']
        db.delete_unique('packages_packageuri', ['package_id', 'uri'])

        # Deleting model 'TroveClassifier'
        db.delete_table('packages_troveclassifier')

        # Deleting model 'Package'
        db.delete_table('packages_package')

        # Deleting model 'PackageURI'
        db.delete_table('packages_packageuri')

        # Deleting model 'Release'
        db.delete_table('packages_release')

        # Removing M2M table for field classifiers on 'Release'
        db.delete_table('packages_release_classifiers')

        # Deleting model 'ReleaseFile'
        db.delete_table('packages_releasefile')

        # Deleting model 'ReleaseURI'
        db.delete_table('packages_releaseuri')

        # Deleting model 'ReleaseRequire'
        db.delete_table('packages_releaserequire')

        # Deleting model 'ReleaseProvide'
        db.delete_table('packages_releaseprovide')

        # Deleting model 'ReleaseObsolete'
        db.delete_table('packages_releaseobsolete')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 248043)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 248163)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 250204)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 250319)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 249244)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 249368)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_release_frequency
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.frequency'
        db.add_column('packages_release', 'frequency',
                      self.gf('django.db.models.fields.CharField')(default='hourly', max_length=25),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Release.frequency'
        db.delete_column('packages_release', 'frequency')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 359519)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 359624)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 354846)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'default': "'hourly'", 'max_length': '25'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 354960)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 356827)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 356937)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0004_auto__add_changelog
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ChangeLog'
        db.create_table('packages_changelog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 29, 4, 41, 10, 288146))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 29, 4, 41, 10, 288291))),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Package'])),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Release'], null=True, blank=True)),
        ))
        db.send_create_signal('packages', ['ChangeLog'])

    def backwards(self, orm):
        # Deleting model 'ChangeLog'
        db.delete_table('packages_changelog')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 329284)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 329489)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 331011)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 331123)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 332207)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'default': "'hourly'", 'max_length': '25'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 332320)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 335184)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 335321)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_package_featured
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.featured'
        db.add_column('packages_package', 'featured',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Package.featured'
        db.delete_column('packages_package', 'featured')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 90400)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 90509)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 94873)'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 94977)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 90976)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'default': "'hourly'", 'max_length': '25'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 91115)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 93155)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 93261)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0006_auto__del_field_release_frequency__del_field_package_featured
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Release.frequency'
        db.delete_column('packages_release', 'frequency')

        # Deleting field 'Package.featured'
        db.delete_column('packages_package', 'featured')

    def backwards(self, orm):
        # Adding field 'Release.frequency'
        db.add_column('packages_release', 'frequency',
                      self.gf('django.db.models.fields.CharField')(default='hourly', max_length=25),
                      keep_default=False)

        # Adding field 'Package.featured'
        db.add_column('packages_package', 'featured',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 976428)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 976528)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 971537)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 971657)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 974345)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 974459)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 972741)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 972865)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_package_downloads_synced_on
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.downloads_synced_on'
        db.add_column('packages_package', 'downloads_synced_on',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2012, 1, 30, 3, 47, 32, 799896)),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Package.downloads_synced_on'
        db.delete_column('packages_package', 'downloads_synced_on')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 843206)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 843306)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 842257)'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 842520)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 842360)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 839741)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 839867)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 844278)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 844378)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0008_auto__add_readthedocspackageslug
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ReadTheDocsPackageSlug'
        db.create_table('packages_readthedocspackageslug', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.OneToOneField')(related_name='readthedocs_slug', unique=True, to=orm['packages.Package'])),
            ('slug', self.gf('django.db.models.fields.CharField')(unique=True, max_length=150)),
        ))
        db.send_create_signal('packages', ['ReadTheDocsPackageSlug'])

    def backwards(self, orm):
        # Deleting model 'ReadTheDocsPackageSlug'
        db.delete_table('packages_readthedocspackageslug')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 479069)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 479188)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 483204)'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 483465)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 483306)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 481670)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 481776)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 480473)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 480579)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_release_deleted__add_field_package_deleted
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.deleted'
        db.add_column('packages_release', 'deleted',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Package.deleted'
        db.add_column('packages_package', 'deleted',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Release.deleted'
        db.delete_column('packages_release', 'deleted')

        # Deleting field 'Package.deleted'
        db.delete_column('packages_package', 'deleted')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 495558)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 495654)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 496243)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 496558)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 496340)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 493089)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 493188)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 491745)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 491859)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0010_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'ChangeLog', fields ['type']
        db.create_index('packages_changelog', ['type'])

    def backwards(self, orm):
        # Removing index on 'ChangeLog', fields ['type']
        db.delete_index('packages_changelog', ['type'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 723563)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 723670)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 722995)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 723333)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 723104)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 725821)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 725927)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 724937)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 725040)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0011_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'ChangeLog', fields ['created']
        db.create_index('packages_changelog', ['created'])

    def backwards(self, orm):
        # Removing index on 'ChangeLog', fields ['created']
        db.delete_index('packages_changelog', ['created'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 169328)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 169451)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 173859)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 174181)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 173957)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 171815)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 171918)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 170942)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 171053)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0012_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Release', fields ['order']
        db.create_index('packages_release', ['order'])

    def backwards(self, orm):
        # Removing index on 'Release', fields ['order']
        db.delete_index('packages_release', ['order'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 312737)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 312858)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 317211)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 317519)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 317305)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 315183)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 315281)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 314335)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 314433)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0013_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Release', fields ['deleted']
        db.create_index('packages_release', ['deleted'])

        # Adding index on 'Package', fields ['deleted']
        db.create_index('packages_package', ['deleted'])

    def backwards(self, orm):
        # Removing index on 'Package', fields ['deleted']
        db.delete_index('packages_package', ['deleted'])

        # Removing index on 'Release', fields ['deleted']
        db.delete_index('packages_release', ['deleted'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 533082)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 533182)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 531604)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 531942)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 531719)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 534759)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 534861)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 536366)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 536468)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0014_delete_deleted
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        for package in orm["packages.Package"].objects.filter(deleted=True):
            package.delete()

        for release in orm["packages.Release"].objects.filter(deleted=True):
            release.delete()

    def backwards(self, orm):
        pass

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'unique_together': "(('package', 'type'),)", 'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        }
    }

    complete_apps = ['packages']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0015_auto__del_field_release_deleted__del_field_package_deleted
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Release.deleted'
        db.delete_column('packages_release', 'deleted')

        # Deleting field 'Package.deleted'
        db.delete_column('packages_package', 'deleted')

    def backwards(self, orm):
        # Adding field 'Release.deleted'
        db.add_column('packages_release', 'deleted',
                      self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True),
                      keep_default=False)

        # Adding field 'Package.deleted'
        db.add_column('packages_package', 'deleted',
                      self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True),
                      keep_default=False)

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0016_auto__add_field_package_normalized_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.normalized_name'
        db.add_column('packages_package', 'normalized_name',
                      self.gf('django.db.models.fields.SlugField')(max_length=150, null=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Package.normalized_name'
        db.delete_column('packages_package', 'normalized_name')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'max_length': '150', 'null': 'True'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0017_normalize_names
# -*- coding: utf-8 -*-
import re
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        for package in orm["packages.Package"].objects.all():
            package.normalized_name = re.sub('[^A-Za-z0-9.]+', '-', package.name).lower()
            package.save()

    def backwards(self, orm):
        pass

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'max_length': '150', 'null': 'True'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0018_auto__chg_field_package_normalized_name__add_unique_package_normalized
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Package.normalized_name'
        db.alter_column('packages_package', 'normalized_name', self.gf('django.db.models.fields.SlugField')(default='', unique=True, max_length=150))

    def backwards(self, orm):
        # Changing field 'Package.normalized_name'
        db.alter_column('packages_package', 'normalized_name', self.gf('django.db.models.fields.SlugField')(max_length=150, null=True))

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0019_auto__add_field_releasefile_hidden
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ReleaseFile.hidden'
        db.add_column('packages_releasefile', 'hidden',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'ReleaseFile.hidden'
        db.delete_column('packages_releasefile', 'hidden')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0020_auto__add_field_release_show_install_command
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.show_install_command'
        db.add_column('packages_release', 'show_install_command',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Release.show_install_command'
        db.delete_column('packages_release', 'show_install_command')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0021_migrate_plone
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        orm["packages.Release"].objects.filter(classifiers__trove="Framework :: Plone").update(show_install_command=False)

    def backwards(self, orm):
        pass

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0022_auto__add_downloaddelta
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DownloadDelta'
        db.create_table('packages_downloaddelta', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('file', self.gf('django.db.models.fields.related.ForeignKey')(related_name='download_deltas', to=orm['packages.ReleaseFile'])),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('delta', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('packages', ['DownloadDelta'])

    def backwards(self, orm):
        # Deleting model 'DownloadDelta'
        db.delete_table('packages_downloaddelta')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0023_auto__add_unique_downloaddelta_date_file
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'DownloadDelta', fields ['date', 'file']
        db.create_unique('packages_downloaddelta', ['date', 'file_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'DownloadDelta', fields ['date', 'file']
        db.delete_unique('packages_downloaddelta', ['date', 'file_id'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0024_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'DownloadDelta', fields ['date']
        db.create_index('packages_downloaddelta', ['date'])

    def backwards(self, orm):
        # Removing index on 'DownloadDelta', fields ['date']
        db.delete_index('packages_downloaddelta', ['date'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'db_index': 'True'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0025_auto__add_downloadstatscache
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DownloadStatsCache'
        db.create_table('packages_downloadstatscache', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['packages.Package'], unique=True)),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('packages', ['DownloadStatsCache'])

    def backwards(self, orm):
        # Deleting model 'DownloadStatsCache'
        db.delete_table('packages_downloadstatscache')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'db_index': 'True'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.downloadstatscache': {
            'Meta': {'object_name': 'DownloadStatsCache'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['packages.Package']", 'unique': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0026_auto__del_downloadstatscache
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'DownloadStatsCache'
        db.delete_table('packages_downloadstatscache')

    def backwards(self, orm):
        # Adding model 'DownloadStatsCache'
        db.create_table('packages_downloadstatscache', (
            ('data', self.gf('django.db.models.fields.TextField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['packages.Package'], unique=True)),
        ))
        db.send_create_signal('packages', ['DownloadStatsCache'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'db_index': 'True'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0027_auto__del_field_release_raw_data
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Release.raw_data'
        db.delete_column('packages_release', 'raw_data')


    def backwards(self, orm):
        # Adding field 'Release.raw_data'
        db.add_column('packages_release', 'raw_data',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)


    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'db_index': 'True'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = models
import datetime
import os
import posixpath
import re
import urlparse
import uuid
import cStringIO
import sys

import bleach
import jinja2
import lxml.html

from docutils.core import publish_string, publish_parts
from docutils.utils import SystemMessage


from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.encoding import smart_str, force_unicode
from django.utils.importlib import import_module
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import TimeStampedModel

from crate.web.packages.evaluators import ReleaseEvaluator
from crate.web.packages.utils import verlib
from crate.web.packages.utils.datatools import track_data

ALLOWED_TAGS = bleach.ALLOWED_TAGS + [
                    "br", "img", "span", "div", "pre", "p",
                    "dl", "dd", "dt", "tt", "cite",
                    "h1", "h2", "h3", "h4", "h5", "h6",
                    "table", "col", "tr", "td", "th", "tbody", "thead",
                    "colgroup",
                ]

ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES.items())
ALLOWED_ATTRIBUTES.update({
    "img": ["src"],
    "span": ["class"],
})

# Get the Storage Engine for Packages
if getattr(settings, "PACKAGE_FILE_STORAGE", None):
    mod_name, engine_name = settings.PACKAGE_FILE_STORAGE.rsplit(".", 1)
    mod = import_module(mod_name)
    package_storage = getattr(mod, engine_name)(**getattr(settings, "PACKAGE_FILE_STORAGE_OPTIONS", {}))
else:
    package_storage = None


def release_file_upload_to(instance, filename):
    dsplit = instance.digest.split("$")
    if len(dsplit) == 2:
        directory = dsplit[1]
    else:
        directory = str(uuid.uuid4()).replace("-", "")

    if getattr(settings, "PACKAGE_FILE_STORAGE_BASE_DIR", None):
        path_items = [settings.PACKAGE_FILE_STORAGE_BASE_DIR]
    else:
        path_items = []

    for char in directory[:4]:
        path_items.append(char)

    path_items += [directory, filename]

    return posixpath.join(*path_items)


# @@@ These are by Nature Hierarchical. Would we benefit from a tree structure?
class TroveClassifier(models.Model):
    trove = models.CharField(max_length=350, unique=True)

    def __unicode__(self):
        return self.trove


class Package(TimeStampedModel):
    name = models.SlugField(max_length=150, unique=True)
    normalized_name = models.SlugField(max_length=150, unique=True)
    downloads_synced_on = models.DateTimeField(default=now)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.normalized_name = re.sub('[^A-Za-z0-9.]+', '-', self.name).lower()
        return super(Package, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("package_detail", kwargs={"package": self.name})

    def get_simple_url(self):
        return reverse("simple_package_detail", kwargs={"slug": self.name})

    @property
    def downloads(self):
        KEY = "crate:packages:package:%s:downloads" % self.pk

        total_downloads = cache.get(KEY)
        if total_downloads is None:
            total_downloads = ReleaseFile.objects.filter(release__package=self).aggregate(total_downloads=Sum("downloads"))["total_downloads"]
            if total_downloads is None:
                total_downloads = 0

            cache.set(KEY, total_downloads)
        return total_downloads

    @property
    def latest(self):
        if not hasattr(self, "_latest_release"):
            releases = self.releases.filter(hidden=False).order_by("-order")[:1]
            if releases:
                self._latest_release = releases[0]
            else:
                self._latest_release = None
        return self._latest_release

    @property
    def install_command(self):
        return "pip install %(package)s" % {"package": self.name}

    @property
    def requirement_line(self):
        if self.latest is not None:
            return "%(package)s==%(version)s" % {"package": self.name, "version": self.latest.version}

    @property
    def history(self):
        from history.models import Event

        return Event.objects.filter(package=self.package.name).order_by("-created")


class PackageURI(models.Model):
    package = models.ForeignKey(Package, related_name="package_links")
    uri = models.URLField(max_length=400)

    class Meta:
        unique_together = ["package", "uri"]

    def __unicode__(self):
        return self.uri


@track_data("hidden")
class Release(models.Model, ReleaseEvaluator):

    created = AutoCreatedField("created", db_index=True)
    modified = AutoLastModifiedField("modified")

    package = models.ForeignKey(Package, related_name="releases")
    version = models.CharField(max_length=512)

    hidden = models.BooleanField(default=False)
    show_install_command = models.BooleanField(default=True)

    order = models.IntegerField(default=0, db_index=True)

    platform = models.TextField(blank=True)

    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)

    keywords = models.TextField(blank=True)

    license = models.TextField(blank=True)

    author = models.TextField(blank=True)
    author_email = models.TextField(blank=True)

    maintainer = models.TextField(blank=True)
    maintainer_email = models.TextField(blank=True)

    requires_python = models.CharField(max_length=25, blank=True)

    download_uri = models.URLField(max_length=1024, blank=True)

    classifiers = models.ManyToManyField(TroveClassifier, related_name="releases", blank=True)

    class Meta:
        unique_together = ("package", "version")

    def __unicode__(self):
        return u"%(package)s %(version)s" % {"package": self.package.name, "version": self.version}

    def save(self, *args, **kwargs):
        # Update the Project's URIs
        docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})

        docutils_settings.update({"warning_stream": os.devnull})

        try:
            html_string = publish_string(source=smart_str(self.description), writer_name="html4css1", settings_overrides=docutils_settings)
            if html_string.strip():
                html = lxml.html.fromstring(html_string)

                for link in html.xpath("//a/@href"):
                    if len(link) > 400:
                        # @@@ ugly as sin, but fixes shit for now
                        continue

                    try:
                        if any(urlparse.urlparse(link)[:5]):
                            PackageURI.objects.get_or_create(package=self.package, uri=link)
                    except ValueError:
                        pass
        except Exception:
            # @@@ We Swallow Exceptions here, but it's the best way that I can think of atm.
            pass

        super(Release, self).save(*args, **kwargs)

        _current_show_install_command = self.show_install_command

        if self.classifiers.filter(trove="Framework :: Plone").exists():
            self.show_install_command = False
        else:
            self.show_install_command = True

        if _current_show_install_command != self.show_install_command:
            super(Release, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("package_detail", kwargs={"package": self.package.name, "version": self.version})

    @property
    def downloads(self):
        KEY = "crate:packages:release:%s:downloads" % self.pk

        total_downloads = cache.get(KEY)

        if total_downloads is None:
            total_downloads = self.files.aggregate(total_downloads=Sum("downloads"))["total_downloads"]
            if total_downloads is None:
                total_downloads = 0
            cache.set(KEY, total_downloads)

        return total_downloads

    @property
    def install_command(self):
        return "pip install %(package)s==%(version)s" % {"package": self.package.name, "version": self.version}

    @property
    def requirement_line(self):
        return "%(package)s==%(version)s" % {"package": self.package.name, "version": self.version}

    @property
    def description_html(self):
        if not hasattr(self, "_description_html"):
            # @@@ Consider Saving This to the DB
            docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})
            docutils_settings.update({
                            "raw_enabled": 0,  # no raw HTML code
                            "file_insertion_enabled": 0,  # no file/URL access
                            "halt_level": 2,  # at warnings or errors, raise an exception
                            "report_level": 5,  # never report problems with the reST code
                        })

            old_stderr = sys.stderr
            sys.stderr = s = cStringIO.StringIO()

            msg = ""

            try:
                bits = self.description.split(".. :changelog:", 1)
                description = bits[0]
                parts = publish_parts(source=smart_str(description), writer_name="html4css1", settings_overrides=docutils_settings)
            except SystemMessage:
                msg = None
            else:
                if parts is None or len(s.getvalue()) > 0:
                    msg = None
                else:
                    cnt = force_unicode(parts["fragment"])
                    cnt = bleach.clean(cnt, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
                    cnt = bleach.linkify(cnt, skip_pre=True, parse_email=True)

                    msg = jinja2.Markup(cnt)

            sys.stderr = old_stderr
            self._description_html = msg

        return self._description_html

    @property
    def changelog_html(self):
        if not hasattr(self, "_changelog_html"):
            docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})
            docutils_settings.update({
                            "raw_enabled": 0,  # no raw HTML code
                            "file_insertion_enabled": 0,  # no file/URL access
                            "halt_level": 2,  # at warnings or errors, raise an exception
                            "report_level": 5,  # never report problems with the reST code
                        })

            old_stderr = sys.stderr
            sys.stderr = s = cStringIO.StringIO()

            msg = ""

            try:
                bits = self.description.split(".. :changelog:", 1)

                if len(bits) > 1:
                    changelog = bits[1]
                else:
                    self._changelog_html = None
                    return

                parts = publish_parts(source=smart_str(changelog), writer_name="html4css1", settings_overrides=docutils_settings)
            except SystemMessage:
                msg = None
            else:
                if parts is None or len(s.getvalue()) > 0:
                    msg = None
                else:
                    cnt = force_unicode(parts["fragment"])
                    cnt = bleach.clean(cnt, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
                    cnt = bleach.linkify(cnt, skip_pre=True, parse_email=True)

                    msg = jinja2.Markup(cnt)

            sys.stderr = old_stderr
            self._changelog_html = msg

        return self._changelog_html


@track_data("hidden")
class ReleaseFile(models.Model):

    TYPES = Choices(
        ("sdist", _("Source")),
        ("bdist_egg", "Egg"),
        ("bdist_msi", "MSI"),
        ("bdist_dmg", "DMG"),
        ("bdist_rpm", "RPM"),
        ("bdist_dumb", _("Dumb Binary Distribution")),
        ("bdist_wininst", _("Windows Installer Binary Distribution")),
        ("bdist_wheel", _("Wheel")),
    )

    created = AutoCreatedField("created", db_index=True)
    modified = AutoLastModifiedField("modified")

    hidden = models.BooleanField(default=False)

    release = models.ForeignKey(Release, related_name="files")

    type = models.CharField(max_length=25, choices=TYPES)
    file = models.FileField(upload_to=release_file_upload_to, storage=package_storage, max_length=512, blank=True)
    filename = models.CharField(max_length=200, help_text="This is the file name given to us by PyPI", blank=True, null=True, default=None)
    digest = models.CharField(max_length=512, blank=True)

    python_version = models.CharField(max_length=25)

    downloads = models.PositiveIntegerField(default=0)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("release", "type", "python_version", "filename")

    def __unicode__(self):
        return os.path.basename(self.file.name)

    def get_absolute_url(self):
        return self.file.url

    def get_python_version_display(self):
        if self.python_version.lower() == "source":
            return ""
        return self.python_version


class ReleaseURI(models.Model):
    release = models.ForeignKey(Release, related_name="uris")
    label = models.CharField(max_length=64)
    uri = models.URLField(max_length=500)


class ReleaseRequire(models.Model):

    KIND = Choices(
        ("requires", "Requirement"),
        ("requires_dist", "Dist Requirement"),
        ("external", "External Requirement"),
    )

    release = models.ForeignKey(Release, related_name="requires")

    kind = models.CharField(max_length=50, choices=KIND)
    name = models.CharField(max_length=150)
    version = models.CharField(max_length=50, blank=True)

    environment = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class ReleaseProvide(models.Model):

    KIND = Choices(
        ("provides", "Provides"),
        ("provides_dist", "Dist Provides"),
    )

    release = models.ForeignKey(Release, related_name="provides")

    kind = models.CharField(max_length=50, choices=KIND)
    name = models.CharField(max_length=150)
    version = models.CharField(max_length=50, blank=True)

    environment = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class ReleaseObsolete(models.Model):

    KIND = Choices(
        ("obsoletes", "Obsoletes"),
        ("obsoletes_dist", "Dist Obsoletes"),
    )

    release = models.ForeignKey(Release, related_name="obsoletes")

    kind = models.CharField(max_length=50, choices=KIND)
    name = models.CharField(max_length=150)
    version = models.CharField(max_length=50, blank=True)

    environment = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class DownloadDelta(models.Model):

    file = models.ForeignKey(ReleaseFile, related_name="download_deltas")
    date = models.DateField(default=datetime.date.today, db_index=True)
    delta = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Download Delta"
        verbose_name_plural = "Download Deltas"

        unique_together = ("file", "date")


class ChangeLog(models.Model):

    TYPES = Choices(
        ("new", "New"),
        ("updated", "Updated"),
    )

    created = AutoCreatedField("created", db_index=True)
    modified = AutoLastModifiedField("modified")

    type = models.CharField(max_length=25, choices=TYPES, db_index=True)
    package = models.ForeignKey(Package)
    release = models.ForeignKey(Release, blank=True, null=True)


class ReadTheDocsPackageSlug(models.Model):
    package = models.OneToOneField(Package, related_name="readthedocs_slug")
    slug = models.CharField(max_length=150, unique=True)

    def __unicode__(self):
        return u"%s" % self.slug


@receiver(post_save, sender=Release)
def version_ordering(sender, **kwargs):
    instance = kwargs.get("instance")
    if instance is not None:
        releases = Release.objects.filter(package__pk=instance.package.pk)

        versions = []
        dated = []

        for release in releases:
            normalized = verlib.suggest_normalized_version(release.version)
            if normalized is not None:
                versions.append(release)
            else:
                dated.append(release)

        versions.sort(key=lambda x: verlib.NormalizedVersion(verlib.suggest_normalized_version(x.version)))
        dated.sort(key=lambda x: x.created)

        for i, release in enumerate(dated + versions):
            if release.order != i:
                Release.objects.filter(pk=release.pk).update(order=i)


@receiver(post_save, sender=Package)
def update_packages(sender, **kwargs):
    instance = kwargs.get("instance")
    if instance is not None:
        if kwargs.get("created", False):
            ChangeLog.objects.create(type=ChangeLog.TYPES.new, package=instance)


@receiver(post_save, sender=Release)
def release_changelog(sender, **kwargs):
    instance = kwargs.get("instance")
    if instance is not None:
        if kwargs.get("created", False):
            diff = instance.created - instance.package.created
            if diff.days != 0 or diff.seconds > 600:
                ChangeLog.objects.create(type=ChangeLog.TYPES.updated, package=instance.package, release=instance)


@receiver(post_save, sender=Package)
@receiver(post_delete, sender=Package)
def regenerate_simple_index(sender, **kwargs):
    from crate.web.packages.tasks import refresh_package_index_cache
    refresh_package_index_cache.delay()

########NEW FILE########
__FILENAME__ = search_indexes
from django.utils.translation import ugettext_noop as _

from haystack import indexes

from crate.web.packages.models import Package
from crate.web.search.indexes import PackageCelerySearchIndex

LICENSES = {
    "GNU General Public License (GPL)": "GPL",
    "GNU Library or Lesser General Public License (LGPL)": "LGPL",
    "GNU Affero General Public License v3": "Affero GPL",
    "Apache Software License": "Apache License",
    "ISC License (ISCL)": "ISC License",
    "Other/Proprietary License": _("Other/Proprietary"),
}


class PackageIndex(PackageCelerySearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr="name", boost=1.5)
    display_name = indexes.CharField(model_attr="name", indexed=False)
    summary = indexes.CharField(null=True)
    description = indexes.CharField(null=True)
    author = indexes.CharField(null=True)
    maintainer = indexes.CharField(null=True)
    downloads = indexes.IntegerField(model_attr="downloads", indexed=False)
    url = indexes.CharField(model_attr="get_absolute_url", indexed=False)
    operating_systems = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    licenses = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    implementations = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    python_versions = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    versions = indexes.MultiValueField(null=True)
    release_count = indexes.IntegerField(default=0)

    def get_model(self):
        return Package

    def prepare(self, obj):
        data = super(PackageIndex, self).prepare(obj)

        # For ES, because it doesn't tokenize on ``_``, which causes problems
        # on lots of searches.
        if '_' in data['name']:
            data['name'] += ' ' + data['name'].replace('_', '-')

        if obj.latest:
            data["summary"] = obj.latest.summary
            data["author"] = obj.latest.author if obj.latest.author else None
            data["maintainer"] = obj.latest.maintainer if obj.latest.maintainer else None
            data["description"] = obj.latest.description if obj.latest.description else None

            operating_systems = []
            licenses = []
            implementations = []
            python_versions = []

            for classifier in obj.latest.classifiers.all():
                if classifier.trove.startswith("License ::"):
                    # We Have a License for This Project
                    licenses.append(classifier.trove.rsplit("::", 1)[1].strip())
                elif classifier.trove.startswith("Operating System ::"):
                    operating_systems.append(classifier.trove.rsplit("::", 1)[1].strip())
                elif classifier.trove.startswith("Programming Language :: Python :: Implementation ::"):
                    implementations.append(classifier.trove.rsplit("::", 1)[1].strip())
                elif classifier.trove.startswith("Programming Language :: Python ::"):
                    if classifier.trove == "Programming Language :: Python :: 2 :: Only":
                        python_versions.append("2.x")
                    elif classifier.trove.startswith("Programming Language :: Python :: 2"):
                        python_versions.append("2.x")
                    elif classifier.trove.startswith("Programming Language :: Python :: 3"):
                        python_versions.append("3.x")
                    else:
                        python_versions.append(classifier.trove.rsplit("::", 1)[1].strip())

            if not licenses:
                licenses = [_("Unknown")]

            licenses = [x for x in licenses if x not in ["OSI Approved"]]
            licenses = [LICENSES.get(x, x) for x in licenses]

            data["licenses"] = licenses

            if not operating_systems:
                operating_systems = [_("Unknown")]
            data["operating_systems"] = operating_systems

            if not implementations:
                implementations = [_("Unknown")]
            data["implementations"] = implementations

            if not python_versions:
                python_versions = [_("Unknown")]
            data["python_versions"] = python_versions

        # Pack in all the versions in decending order.
        releases = obj.releases.all().order_by("-order")
        data["versions"] = [release.version for release in releases if release.version]
        data["release_count"] = releases.count()

        # We want to scale the boost for this document based on how many downloads have
        #   been recorded for this package.
        # @@@ Might want to actually tier these values instead of percentage them.
        # Cap out downloads at 100k
        capped_downloads = min(data["downloads"], 10000)
        boost = capped_downloads / 10000.0
        data["_boost"] = 1.0 + boost

        return data

########NEW FILE########
__FILENAME__ = restricted_urls
from django.conf.urls import patterns, url

from crate.web.packages.simple.views import PackageIndex, PackageDetail

handler404 = "crate.web.packages.simple.views.not_found"

urlpatterns = patterns("",
    url(r"^$", PackageIndex.as_view(restricted=True), name="simple_package_index"),
    url(r"^(?P<slug>[^/]+)/(?:(?P<version>[^/]+)/)?$", PackageDetail.as_view(restricted=True), name="simple_package_detail"),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from crate.web.packages.simple.views import PackageIndex, PackageDetail

handler404 = "crate.web.packages.simple.views.not_found"

urlpatterns = patterns("",
    url(r"^$", PackageIndex.as_view(), name="simple_package_index"),
    url(r"^(?P<slug>[^/]+)/(?:(?P<version>[^/]+)/)?$", PackageDetail.as_view(), name="simple_package_detail"),
)

########NEW FILE########
__FILENAME__ = views
import re

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound, HttpResponsePermanentRedirect, Http404
from django.views.decorators.cache import cache_page
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _

from crate.web.packages.models import Package


def not_found(request):
    return HttpResponseNotFound("Not Found")


class PackageIndex(ListView):

    restricted = False
    queryset = Package.objects.all().order_by("name")
    template_name = "packages/simple/package_list.html"

    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super(PackageIndex, self).dispatch(*args, **kwargs)

    def get_queryset(self, force_uncached=False):
        cached = cache.get("crate:packages:simple:PackageIndex:queryset")

        if cached and not force_uncached:
            return cached

        qs = super(PackageIndex, self).get_queryset()
        cache.set("crate:packages:simple:PackageIndex:queryset", list(qs), 60 * 60 * 24 * 365)
        return qs


class PackageDetail(DetailView):

    restricted = False
    queryset = Package.objects.all().prefetch_related("releases__uris", "releases__files", "package_links")
    slug_field = "name__iexact"
    template_name = "packages/simple/package_detail.html"

    def get_object(self, queryset=None):
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError(u"Generic detail view %s must be called with "
                                 u"either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            obj = queryset.get()
        except ObjectDoesNotExist:
            try:
                queryset = self.get_queryset()
                queryset = queryset.filter(normalized_name=re.sub('[^A-Za-z0-9.]+', '-', slug).lower())
                obj = queryset.get()
            except ObjectDoesNotExist:
                raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})

        return obj

    def get_context_data(self, **kwargs):
        ctx = super(PackageDetail, self).get_context_data(**kwargs)

        releases = self.object.releases.all()

        if self.kwargs.get("version"):
            releases = releases.filter(version=self.kwargs["version"])
        else:
            releases = releases.filter(hidden=False)

        ctx.update({
            "releases": releases,
            "restricted": self.restricted,
            "show_hidden": True if self.kwargs.get("version") else False,
        })

        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check that the case matches what it's supposed to be
        if self.object.name != self.kwargs.get(self.slug_url_kwarg, None):
            return HttpResponsePermanentRedirect(reverse("simple_package_detail", kwargs={"slug": self.object.name}))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns("",
    url(r"^(?P<slug>[^/]+)/delta\.json$", "crate.web.packages.stats.views.stats_delta", name="package_stats_delta"),
)

########NEW FILE########
__FILENAME__ = views
import collections
import json
import time

import isoweek

from django.http import HttpResponse
from django.views.decorators.cache import cache_page, cache_control
from django.shortcuts import get_object_or_404

from crate.web.packages.models import Package, Release, DownloadDelta


def fetch_stats(package):
    releases = list(Release.objects.filter(package=package).only("version", "order").order_by("order"))
    specific_releases = set([x.version for x in releases[-8:]])

    deltas = list(DownloadDelta.objects.filter(file__release__in=releases).only("date", "delta", "file__release__version").order_by("date").select_related("file", "file__release"))

    # @@@ Sanity Checks
    if not deltas:
        return [{}]

    data = [{"name": "Other", "data": []}] + [{"name": release.version, "data": []} for release in releases if release.version in specific_releases]

    # Get First Week
    start_week = isoweek.Week.withdate(deltas[0].date)
    end_week = isoweek.Week.thisweek()

    current = isoweek.Week(start_week.year, start_week.week)

    while current.year <= end_week.year and current.week < end_week.week:
        for x in data:
            x["data"].append({"x": int(time.mktime(current.day(0).timetuple()))})
        current = isoweek.Week(current.year, current.week + 1)

    _data = collections.defaultdict(dict)

    for d in deltas:
        target = int(time.mktime(isoweek.Week.withdate(d.date).day(0).timetuple()))
        _data[d.file.release.version if d.file.release.version in specific_releases else "Other"][target] = d.delta

    for i in xrange(0, len(data)):
        for j in xrange(0, len(data[i]["data"])):
            data[i]["data"][j]["y"] = _data[data[i]["name"] if data[i]["name"] in specific_releases else "Other"].get(data[i]["data"][j]["x"], 0)

    return data


@cache_page(86400)
@cache_control(public=True, max_age=86400)
def stats_delta(request, slug):
    package = get_object_or_404(Package, name=slug)

    data = fetch_stats(package)

    return HttpResponse(json.dumps(data), mimetype="application/json")

########NEW FILE########
__FILENAME__ = tasks
from celery.task import task

from crate.web.packages.simple.views import PackageIndex


@task
def refresh_package_index_cache():
    pi = PackageIndex()
    pi.get_queryset(force_uncached=True)

########NEW FILE########
__FILENAME__ = package_tags
from django import template
from django.core.cache import cache
from django.db.models import Sum

from crate.web.packages.models import Package, Release, ReleaseFile, ChangeLog

register = template.Library()


@register.assignment_tag
def package_download_count(package_name=None):
    if package_name is None:
        cached = cache.get("crate:stats:download_count")

        if cached:
            return cached

        count = ReleaseFile.objects.all().aggregate(total_downloads=Sum("downloads")).get("total_downloads", 0)
        cache.set("crate:stats:download_count", count, 60 * 60)
        return count
    else:
        cached = cache.get("crate:stats:download_count:%s" % package_name)

        if cached:
            return cached

        count = ReleaseFile.objects.filter(
                    release__package__name=package_name
                ).aggregate(total_downloads=Sum("downloads")).get("total_downloads", 0)
        cache.set("crate:stats:download_count:%s" % package_name, count, 60 * 60 * 24)
        return count


@register.assignment_tag
def package_count():
    cached = cache.get("crate:stats:package_count")

    if cached:
        return cached

    count = Package.objects.all().count()
    cache.set("crate:stats:package_count", count, 60 * 60)
    return count


@register.assignment_tag
def get_oldest_package():
    cached = cache.get("crate:stats:oldest_package")

    if cached:
        return cached

    pkgs = Package.objects.all().order_by("created")[:1]

    if pkgs:
        cache.set("crate:stats:oldest_package", pkgs[0], 60 * 60 * 24 * 7)
        return pkgs[0]
    else:
        return None


@register.assignment_tag
def new_packages(num):
    return [
        x for
        x in ChangeLog.objects.filter(type=ChangeLog.TYPES.new).select_related("package", "release").prefetch_related("package__releases").order_by("-created")[:num * 3]
        if len(x.package.releases.all())
    ][:num]


@register.assignment_tag
def updated_packages(num):
    return ChangeLog.objects.filter(type=ChangeLog.TYPES.updated).select_related("package", "release", "release__package").order_by("-created")[:num]


@register.assignment_tag
def featured_packages(num):
    return Package.objects.filter(featured=True).order_by("?")[:num]


@register.assignment_tag
def random_packages(num):
    return Package.objects.exclude(releases=None).order_by("?")[:num]


@register.assignment_tag
def package_versions(package_name, num=None):
    KEY = "crate:packages:package_versions:%s" % package_name

    qs = cache.get(KEY)

    if qs is None:
        qs = Release.objects.filter(package__name=package_name).select_related("package").order_by("-order")
        cache.set(KEY, list(qs))

    if num is not None:
        qs = qs[:num]
    return qs


@register.assignment_tag
def package_version_count(package_name):
    return Release.objects.filter(package__name=package_name).count()

########NEW FILE########
__FILENAME__ = package_utils
import os

from django import template

register = template.Library()


@register.filter
def filename(value):
    return os.path.basename(value)


@register.filter
def digest_type(digest):
    return digest.split("$")[0]


@register.filter
def digest_value(digest):
    return digest.split("$")[1]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from crate.web.packages.views import ReleaseDetail

urlpatterns = patterns("",
    url(r"^(?P<package>[^/]+)/(?:(?P<version>[^/]+)/)?$", ReleaseDetail.as_view(), name="package_detail"),
)

########NEW FILE########
__FILENAME__ = datatools
#
# Taken from http://justcramer.com/2010/12/06/tracking-changes-to-fields-in-django/
#

from django.db.models.signals import post_init

def track_data(*fields):
    """
    Tracks property changes on a model instance.

    The changed list of properties is refreshed on model initialization
    and save.

    >>> @track_data('name')
    >>> class Post(models.Model):
    >>>     name = models.CharField(...)
    >>>
    >>>     @classmethod
    >>>     def post_save(cls, sender, instance, created, **kwargs):
    >>>         if instance.has_changed('name'):
    >>>             print "Hooray!"
    """

    UNSAVED = dict()

    def _store(self):
        "Updates a local copy of attributes values"
        if self.id:
            self.__data = dict((f, getattr(self, f)) for f in fields)
        else:
            self.__data = UNSAVED

    def inner(cls):
        # contains a local copy of the previous values of attributes
        cls.__data = {}

        def has_changed(self, field):
            "Returns ``True`` if ``field`` has changed since initialization."
            if self.__data is UNSAVED:
                return False
            return self.__data.get(field) != getattr(self, field)
        cls.has_changed = has_changed

        def old_value(self, field):
            "Returns the previous value of ``field``"
            return self.__data.get(field)
        cls.old_value = old_value

        def whats_changed(self):
            "Returns a list of changed attributes."
            changed = {}
            if self.__data is UNSAVED:
                return changed
            for k, v in self.__data.iteritems():
                if v != getattr(self, k):
                    changed[k] = v
            return changed
        cls.whats_changed = whats_changed

        # Ensure we are updating local attributes on model init
        def _post_init(sender, instance, **kwargs):
            _store(instance)
        post_init.connect(_post_init, sender=cls, weak=False)

        # Ensure we are updating local attributes on model save
        def save(self, *args, **kwargs):
            save._original(self, *args, **kwargs)
            _store(self)
        save._original = cls.save
        cls.save = save
        return cls
    return inner

########NEW FILE########
__FILENAME__ = metadata
import collections
import email

from django.utils.encoding import force_unicode


def fix_encoding(s):
    return force_unicode(s, errors="ignore").encode("utf-8")


class ValidationError(Exception):
    """
        Raised When Meta Data doesn't validate
    """


class MetaData(object):
    """
        Takes a string representing a PKG-INFO file and validates it. The meta
        data is then available via the dict self.cleaned_data.
    """

    multiple_fields = set([
        "platform",
        "supported-platform",
        "classifier",
        "requires",
        "provides",
        "obsoletes",
        "requires-dist",
        "provides-dist",
        "obsoletes-dist",
        "requires-external",
        "project-url",
    ])

    def __init__(self, data):
        self.data = email.message_from_string(data.strip())
        self.errors = collections.defaultdict(set)

    def is_valid(self):
        if not hasattr(self, "_is_valid"):
            self.cleaned_data = {}

            for key in self.data.keys():
                try:
                    d = [getattr(self, "clean_%s" % key.lower(), lambda i: i)(x) for x in self.data.get_all(key)]
                    if len(d) > 1 and key.lower() not in self.multiple_fields:
                        raise ValidationError("%s has multiple values but that is not supported for this type." % key)

                    if key.lower() not in self.multiple_fields:
                        d = fix_encoding(d[0]) if len(d) else None
                    else:
                        d = [fix_encoding(x) for x in d]

                    self.cleaned_data[key.lower()] = d
                except ValidationError as e:
                    self.errors[key].add(e.message)

            if self.errors:
                self._is_valid = False
            else:
                self._is_valid = True

        return self._is_valid

########NEW FILE########
__FILENAME__ = verlib
"""
"Rational" version definition and parsing for DistutilsVersionFight
discussion at PyCon 2009.
"""

import re


class IrrationalVersionError(Exception):
    """This is an irrational version."""
    pass


class HugeMajorVersionNumError(IrrationalVersionError):
    """An irrational version because the major version number is huge
    (often because a year or date was used).

    See `error_on_huge_major_num` option in `NormalizedVersion` for details.
    This guard can be disabled by setting that option False.
    """
    pass

# A marker used in the second and third parts of the `parts` tuple, for
# versions that don't have those segments, to sort properly. An example
# of versions in sort order ('highest' last):
#   1.0b1                 ((1,0), ('b',1), ('f',))
#   1.0.dev345            ((1,0), ('f',),  ('dev', 345))
#   1.0                   ((1,0), ('f',),  ('f',))
#   1.0.post256.dev345    ((1,0), ('f',),  ('f', 'post', 256, 'dev', 345))
#   1.0.post345           ((1,0), ('f',),  ('f', 'post', 345, 'f'))
#                                   ^        ^                 ^
#   'b' < 'f' ---------------------/         |                 |
#                                            |                 |
#   'dev' < 'f' < 'post' -------------------/                  |
#                                                              |
#   'dev' < 'f' ----------------------------------------------/
# Other letters would do, but 'f' for 'final' is kind of nice.
FINAL_MARKER = ('f',)

VERSION_RE = re.compile(r'''
    ^
    (?P<version>\d+\.\d+)          # minimum 'N.N'
    (?P<extraversion>(?:\.\d+)*)   # any number of extra '.N' segments
    (?:
        (?P<prerel>[abc]|rc)       # 'a'=alpha, 'b'=beta, 'c'=release candidate
                                   # 'rc'= alias for release candidate
        (?P<prerelversion>\d+(?:\.\d+)*)
    )?
    (?P<postdev>(\.post(?P<post>\d+))?(\.dev(?P<dev>\d+))?)?
    $''', re.VERBOSE)


class NormalizedVersion(object):
    """A rational version.

    Good:
        1.2         # equivalent to "1.2.0"
        1.2.0
        1.2a1
        1.2.3a2
        1.2.3b1
        1.2.3c1
        1.2.3.4
        TODO: fill this out

    Bad:
        1           # mininum two numbers
        1.2a        # release level must have a release serial
        1.2.3b
    """
    def __init__(self, s, error_on_huge_major_num=True):
        """Create a NormalizedVersion instance from a version string.

        @param s {str} The version string.
        @param error_on_huge_major_num {bool} Whether to consider an
            apparent use of a year or full date as the major version number
            an error. Default True. One of the observed patterns on PyPI before
            the introduction of `NormalizedVersion` was version numbers like this:
                2009.01.03
                20040603
                2005.01
            This guard is here to strongly encourage the package author to
            use an alternate version, because a release deployed into PyPI
            and, e.g. downstream Linux package managers, will forever remove
            the possibility of using a version number like "1.0" (i.e.
            where the major number is less than that huge major number).
        """
        self._parse(s, error_on_huge_major_num)

    @classmethod
    def from_parts(cls, version, prerelease=FINAL_MARKER,
                   devpost=FINAL_MARKER):
        return cls(cls.parts_to_str((version, prerelease, devpost)))

    def _parse(self, s, error_on_huge_major_num=True):
        """Parses a string version into parts."""
        match = VERSION_RE.search(s)
        if not match:
            raise IrrationalVersionError(s)

        groups = match.groupdict()
        parts = []

        # main version
        block = self._parse_numdots(groups['version'], s, False, 2)
        extraversion = groups.get('extraversion')
        if extraversion not in ('', None):
            block += self._parse_numdots(extraversion[1:], s)
        parts.append(tuple(block))

        # prerelease
        prerel = groups.get('prerel')
        if prerel is not None:
            block = [prerel]
            block += self._parse_numdots(groups.get('prerelversion'), s,
                                         pad_zeros_length=1)
            parts.append(tuple(block))
        else:
            parts.append(FINAL_MARKER)

        # postdev
        if groups.get('postdev'):
            post = groups.get('post')
            dev = groups.get('dev')
            postdev = []
            if post is not None:
                postdev.extend([FINAL_MARKER[0], 'post', int(post)])
                if dev is None:
                    postdev.append(FINAL_MARKER[0])
            if dev is not None:
                postdev.extend(['dev', int(dev)])
            parts.append(tuple(postdev))
        else:
            parts.append(FINAL_MARKER)
        self.parts = tuple(parts)
        if error_on_huge_major_num and self.parts[0][0] > 1980:
            raise HugeMajorVersionNumError("huge major version number, %r, "
                "which might cause future problems: %r" % (self.parts[0][0], s))

    def _parse_numdots(self, s, full_ver_str, drop_trailing_zeros=True,
                       pad_zeros_length=0):
        """Parse 'N.N.N' sequences, return a list of ints.

        @param s {str} 'N.N.N..." sequence to be parsed
        @param full_ver_str {str} The full version string from which this
            comes. Used for error strings.
        @param drop_trailing_zeros {bool} Whether to drop trailing zeros
            from the returned list. Default True.
        @param pad_zeros_length {int} The length to which to pad the
            returned list with zeros, if necessary. Default 0.
        """
        nums = []
        for n in s.split("."):
            if len(n) > 1 and n[0] == '0':
                raise IrrationalVersionError("cannot have leading zero in "
                    "version number segment: '%s' in %r" % (n, full_ver_str))
            nums.append(int(n))
        if drop_trailing_zeros:
            while nums and nums[-1] == 0:
                nums.pop()
        while len(nums) < pad_zeros_length:
            nums.append(0)
        return nums

    def __str__(self):
        return self.parts_to_str(self.parts)

    @classmethod
    def parts_to_str(cls, parts):
        """Transforms a version expressed in tuple into its string
        representation."""
        # XXX This doesn't check for invalid tuples
        main, prerel, postdev = parts
        s = '.'.join(str(v) for v in main)
        if prerel is not FINAL_MARKER:
            s += prerel[0]
            s += '.'.join(str(v) for v in prerel[1:])
        if postdev and postdev is not FINAL_MARKER:
            if postdev[0] == 'f':
                postdev = postdev[1:]
            i = 0
            while i < len(postdev):
                if i % 2 == 0:
                    s += '.'
                s += str(postdev[i])
                i += 1
        return s

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)

    def _cannot_compare(self, other):
        raise TypeError("cannot compare %s and %s"
                % (type(self).__name__, type(other).__name__))

    def __eq__(self, other):
        if not isinstance(other, NormalizedVersion):
            self._cannot_compare(other)
        return self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, NormalizedVersion):
            self._cannot_compare(other)
        return self.parts < other.parts

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)


def suggest_normalized_version(s):
    """Suggest a normalized version close to the given version string.

    If you have a version string that isn't rational (i.e. NormalizedVersion
    doesn't like it) then you might be able to get an equivalent (or close)
    rational version from this function.

    This does a number of simple normalizations to the given string, based
    on observation of versions currently in use on PyPI. Given a dump of
    those version during PyCon 2009, 4287 of them:
    - 2312 (53.93%) match NormalizedVersion without change
    - with the automatic suggestion
    - 3474 (81.04%) match when using this suggestion method

    @param s {str} An irrational version string.
    @returns A rational version string, or None, if couldn't determine one.
    """
    try:
        NormalizedVersion(s)
        return s   # already rational
    except IrrationalVersionError:
        pass

    rs = s.lower()

    # part of this could use maketrans
    for orig, repl in (('-alpha', 'a'), ('-beta', 'b'), ('alpha', 'a'),
                       ('beta', 'b'), ('rc', 'c'), ('-final', ''),
                       ('-pre', 'c'),
                       ('-release', ''), ('.release', ''), ('-stable', ''),
                       ('+', '.'), ('_', '.'), (' ', ''), ('.final', ''),
                       ('final', '')):
        rs = rs.replace(orig, repl)

    # if something ends with dev or pre, we add a 0
    rs = re.sub(r"pre$", r"pre0", rs)
    rs = re.sub(r"dev$", r"dev0", rs)

    # if we have something like "b-2" or "a.2" at the end of the
    # version, that is pobably beta, alpha, etc
    # let's remove the dash or dot
    rs = re.sub(r"([abc|rc])[\-\.](\d+)$", r"\1\2", rs)

    # 1.0-dev-r371 -> 1.0.dev371
    # 0.1-dev-r79 -> 0.1.dev79
    rs = re.sub(r"[\-\.](dev)[\-\.]?r?(\d+)$", r".\1\2", rs)

    # Clean: 2.0.a.3, 2.0.b1, 0.9.0~c1
    rs = re.sub(r"[.~]?([abc])\.?", r"\1", rs)

    # Clean: v0.3, v1.0
    if rs.startswith('v'):
        rs = rs[1:]

    # Clean leading '0's on numbers.
    #TODO: unintended side-effect on, e.g., "2003.05.09"
    # PyPI stats: 77 (~2%) better
    rs = re.sub(r"\b0+(\d+)(?!\d)", r"\1", rs)

    # Clean a/b/c with no version. E.g. "1.0a" -> "1.0a0". Setuptools infers
    # zero.
    # PyPI stats: 245 (7.56%) better
    rs = re.sub(r"(\d+[abc])$", r"\g<1>0", rs)

    # the 'dev-rNNN' tag is a dev tag
    rs = re.sub(r"\.?(dev-r|dev\.r)\.?(\d+)$", r".dev\2", rs)

    # clean the - when used as a pre delimiter
    rs = re.sub(r"-(a|b|c)(\d+)$", r"\1\2", rs)

    # a terminal "dev" or "devel" can be changed into ".dev0"
    rs = re.sub(r"[\.\-](dev|devel)$", r".dev0", rs)

    # a terminal "dev" can be changed into ".dev0"
    rs = re.sub(r"(?![\.\-])dev$", r".dev0", rs)

    # a terminal "final" or "stable" can be removed
    rs = re.sub(r"(final|stable)$", "", rs)

    # The 'r' and the '-' tags are post release tags
    #   0.4a1.r10       ->  0.4a1.post10
    #   0.9.33-17222    ->  0.9.3.post17222
    #   0.9.33-r17222   ->  0.9.3.post17222
    rs = re.sub(r"\.?(r|-|-r)\.?(\d+)$", r".post\2", rs)

    # Clean 'r' instead of 'dev' usage:
    #   0.9.33+r17222   ->  0.9.3.dev17222
    #   1.0dev123       ->  1.0.dev123
    #   1.0.git123      ->  1.0.dev123
    #   1.0.bzr123      ->  1.0.dev123
    #   0.1a0dev.123    ->  0.1a0.dev123
    # PyPI stats:  ~150 (~4%) better
    rs = re.sub(r"\.?(dev|git|bzr)\.?(\d+)$", r".dev\2", rs)

    # Clean '.pre' (normalized from '-pre' above) instead of 'c' usage:
    #   0.2.pre1        ->  0.2c1
    #   0.2-c1         ->  0.2c1
    #   1.0preview123   ->  1.0c123
    # PyPI stats: ~21 (0.62%) better
    rs = re.sub(r"\.?(pre|preview|-c)(\d+)$", r"c\g<2>", rs)

    # Tcl/Tk uses "px" for their post release markers
    rs = re.sub(r"p(\d+)$", r".post\1", rs)

    try:
        NormalizedVersion(rs)
        return rs   # already rational
    except IrrationalVersionError:
        pass
    return None

########NEW FILE########
__FILENAME__ = views
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.detail import DetailView
from django.shortcuts import render

from crate.web.history.models import Event
from crate.web.packages.models import Release, Package


class ReleaseDetail(DetailView):

    model = Release
    queryset = Release.objects.all().prefetch_related(
                                        "uris",
                                        "files",
                                        "requires",
                                        "provides",
                                        "obsoletes",
                                        "classifiers",
                                    )

    def get_context_data(self, **kwargs):
        ctx = super(ReleaseDetail, self).get_context_data(**kwargs)
        ctx.update({
            "release_files": [x for x in self.object.files.all() if not x.hidden],
            "version_specific": self.kwargs.get("version", None),
            "versions": Release.objects.filter(package=self.object.package).select_related("package").order_by("-order"),
            "history": Event.objects.filter(package=self.object.package.name).order_by("-created"),
        })
        return ctx

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        package = self.kwargs["package"]
        version = self.kwargs.get("version", None)

        queryset = queryset.filter(package__name=package)

        if version:
            queryset = queryset.filter(version=version)
        else:
            queryset = queryset.filter(hidden=False).order_by("-order")[:1]

        try:
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj


def fuck_the_status_quo(request):
    blah = Package.objects.exclude(name__in=Release.objects.exclude(files=None).distinct("package").values_list("package__name", flat=True)).order_by("name")
    # blah = {}
    # for r in Release.objects.filter(files=None).select_related("package").prefetch_related("package"):
    #     blah.setdefault(r.package.name, []).append(r)
    return render(request, "status_quo.html", {"projects": blah})

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext as _

from haystack.forms import SearchForm as HaystackSearchForm
from haystack.inputs import AutoQuery
from haystack.query import SQ


class SearchForm(HaystackSearchForm):
    has_releases = forms.BooleanField(label=_("Has Releases"), required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

        self.fields["q"].widget.attrs.update({
            "class": "span10",
            "placeholder": _("Search"),
        })

    def search(self):
        if not self.is_valid():
            return self.no_query_found()

        if not self.cleaned_data.get("q"):
            return self.no_query_found()

        sqs = self.searchqueryset.filter(
                SQ(content=AutoQuery(self.cleaned_data["q"])) |
                SQ(name=AutoQuery(self.cleaned_data["q"]))
            )

        if self.cleaned_data.get("has_releases"):
            sqs = sqs.filter(release_count__gt=0)

        if self.load_all:
            sqs = sqs.load_all()

        return sqs

########NEW FILE########
__FILENAME__ = helpers
from jingo import register


@register.function
def facet2short(facet):
    FACETS = {
        "python_versions": "python",
        "operating_systems": "os",
        "licenses": "license",
        "implementations": "implementation",
    }
    return FACETS.get(facet)

########NEW FILE########
__FILENAME__ = indexes
from django.db.models import signals

from celery_haystack.indexes import CelerySearchIndex as BaseCelerySearchIndex

from crate.web.packages.models import Package, Release, ReleaseFile


class PackageCelerySearchIndex(BaseCelerySearchIndex):

    # We override the built-in _setup_* methods to connect the enqueuing
    # operation.
    def _setup_save(self, model=None):
        model = self.handle_model(model)
        signals.post_save.connect(self.enqueue_save, sender=model)
        signals.post_save.connect(self.enqueue_save_from_release, sender=Release)
        signals.post_save.connect(self.enqueue_save_from_releasefile, sender=ReleaseFile)

    def _setup_delete(self, model=None):
        model = self.handle_model(model)
        signals.post_delete.connect(self.enqueue_delete, sender=model)
        signals.post_delete.connect(self.enqueue_delete_from_release, sender=Release)
        signals.post_delete.connect(self.enqueue_delete_from_releasefile, sender=ReleaseFile)

    def _teardown_save(self, model=None):
        model = self.handle_model(model)
        signals.post_save.disconnect(self.enqueue_save, sender=model)
        signals.post_save.disconnect(self.enqueue_save_from_release, sender=Release)
        signals.post_save.disconnect(self.enqueue_save_from_releasefile, sender=ReleaseFile)

    def _teardown_delete(self, model=None):
        model = self.handle_model(model)
        signals.post_delete.disconnect(self.enqueue_delete, sender=model)
        signals.post_delete.disconnect(self.enqueue_delete_from_release, sender=Release)
        signals.post_delete.disconnect(self.enqueue_delete_from_releasefile, sender=ReleaseFile)

    def enqueue_save_from_release(self, instance, **kwargs):
        return self.enqueue('update', instance.package)

    def enqueue_delete_from_release(self, instance, **kwargs):
        try:
            return self.enqueue('update', instance.package)
        except Package.DoesNotExist:
            pass

    def enqueue_save_from_releasefile(self, instance, **kwargs):
        return self.enqueue('update', instance.release.package)

    def enqueue_delete_from_releasefile(self, instance, **kwargs):
        try:
            return self.enqueue('update', instance.release.package)
        except Release.DoesNotExist:
            pass

########NEW FILE########
__FILENAME__ = models
# Intentionally Left Blank

########NEW FILE########
__FILENAME__ = search_utils
from urllib import urlencode
from urlparse import urlparse, parse_qs, urlunparse

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


def re_qs(url, key, value):
    parsed = urlparse(url)
    data = parse_qs(parsed.query)
    if value is not None:
        data.update({
            key: [value],
        })
    else:
        if key in data:
            del data[key]

    _data = []
    for key, value in data.iteritems():
        for item in value:
            _data.append((key, item))

    return urlunparse([parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(_data), parsed.fragment])


@register.filter(name="repage")
@stringfilter
def repage(value, new_page):
    return re_qs(value, "page", new_page)


@register.filter(name="facet_python")
@stringfilter
def facet_python(value, new=None):
    return re_qs(value, "python", new)


@register.filter(name="facet_os")
@stringfilter
def facet_os(value, new=None):
    return re_qs(value, "os", new)


@register.filter(name="facet_license")
@stringfilter
def facet_license(value, new=None):
    return re_qs(value, "license", new)


@register.filter(name="facet_implementation")
@stringfilter
def facet_implementation(value, new=None):
    return re_qs(value, "implementation", new)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from crate.web.search.views import Search


urlpatterns = patterns("",
    url(r"^$", Search.as_view(), name="search"),
)

########NEW FILE########
__FILENAME__ = views
import urllib
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.utils.translation import ugettext as _

from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import FormMixin

from saved_searches.models import SavedSearch

from crate.web.search.forms import SearchForm


class Search(TemplateResponseMixin, FormMixin, View):

    searchqueryset = None
    load_all = False
    paginate_by = None
    allow_empty = True
    form_class = SearchForm
    paginator_class = Paginator
    search_key = 'general_search'

    def get_template_names(self):
        if "q" in self.request.GET:
            return ["search/results.html"]
        return ["homepage.html"]

    def get_searchqueryset(self):
        return self.searchqueryset

    def get_load_all(self):
        return self.load_all

    def get_allow_empty(self):
        """
        Returns ``True`` if the view should display empty lists, and ``False``
        if a 404 should be raised instead.
        """
        return self.allow_empty

    def get_paginate_by(self):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        if self.paginate_by is None:
            return getattr(settings, "HAYSTACK_SEARCH_RESULTS_PER_PAGE", 20)
        return self.paginate_by

    def get_paginator(self, results, per_page, orphans=0, allow_empty_first_page=True):
        """
        Return an instance of the paginator for this view.
        """
        return self.paginator_class(results, per_page, orphans=orphans, allow_empty_first_page=allow_empty_first_page)

    def paginate_results(self, results, page_size):
        """
        Paginate the results, if needed.
        """
        paginator = self.get_paginator(results, page_size, allow_empty_first_page=self.get_allow_empty())
        page = self.kwargs.get("page") or self.request.GET.get("page") or 1
        try:
            page_number = int(page)
        except ValueError:
            if page == "last":
                page_number = paginator.num_pages
            else:
                raise Http404(_(u"Page is not 'last', nor can it be converted to an int."))
        try:
            page = paginator.page(page_number)
            return (paginator, page, page.object_list, page.has_other_pages())
        except InvalidPage:
            raise Http404(_(u"Invalid page (%(page_number)s)") % {
                                "page_number": page_number
            })

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instanciating the form.
        """
        kwargs = {
            "initial": self.get_initial(),
            "searchqueryset": self.get_searchqueryset(),
            "load_all": self.get_load_all(),
        }
        if "q" in self.request.GET:
            kwargs.update({
                "data": self.request.GET,
            })
        return kwargs

    def form_valid(self, form):
        query = form.cleaned_data["q"]
        results = form.search()
        narrow = []

        faceted_by = {
            "python": None,
            "os": None,
            "license": None,
            "implementation": None,
        }

        # Check for facets.
        if self.request.GET.get("python"):
            faceted_by["python"] = self.request.GET["python"]
            narrow.append("python_versions:%s" % self.request.GET["python"])

        if self.request.GET.get("os"):
            faceted_by["os"] = self.request.GET["os"]
            narrow.append("operating_systems:%s" % self.request.GET["os"])

        if self.request.GET.get("license"):
            faceted_by["license"] = self.request.GET["license"]
            narrow.append("licenses:%s" % self.request.GET.get("license"))

        if self.request.GET.get("implementation"):
            faceted_by["implementation"] = self.request.GET["implementation"]
            narrow.append("implementations:%s" % self.request.GET.get("implementation"))

        if len(narrow):
            results = results.narrow(" AND ".join(narrow))

        page_size = self.get_paginate_by()

        if page_size:
            facets = results.facet("python_versions").facet("operating_systems").facet("licenses").facet("implementations").facet_counts()
            paginator, page, results, is_paginated = self.paginate_results(results, page_size)

            # Save it!
            self.save_search(page, query, results)

            # Grumble.
            duped = self.request.GET.copy()
            try:
                del duped["page"]
            except KeyError:
                pass
            query_params = urllib.urlencode(duped, doseq=True)
        else:
            facets = {}
            query_params = ""
            paginator, page, is_paginated = None, None, False

        print faceted_by

        ctx = {
            "form": form,
            "query": query,
            "results": results,
            "page": page,
            "paginator": paginator,
            "is_paginated": is_paginated,
            "facets": facets,
            "faceted_by": faceted_by,
            "query_params": query_params,
        }

        return self.render_to_response(self.get_context_data(**ctx))

    # Copy-pasta from saved_searches with light modification...
    def save_search(self, page, query, results):
        """
        Only save the search if we're on the first page.
        This will prevent an excessive number of duplicates for what is
        essentially the same search.
        """
        if query and page.number == 1:
            # Save the search.
            saved_search = SavedSearch(
                search_key=self.search_key,
                user_query=query,
                result_count=len(results)
            )

            if hasattr(results, 'query'):
                query_seen = results.query.build_query()

                if isinstance(query_seen, basestring):
                    saved_search.full_query = query_seen

            if self.request.user.is_authenticated():
                saved_search.user = self.request.user

            saved_search.save()

    def get(self, request, *args, **kwargs):
        self.request = request

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if "q" in self.request.GET:
            if form.is_valid():
                return self.form_valid(form)
            else:
                self.form_invalid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

########NEW FILE########
__FILENAME__ = associate
from django.core.exceptions import MultipleObjectsReturned

from account.models import EmailAddress

from social_auth.utils import setting
from social_auth.backends.pipeline import warn_setting
from social_auth.backends.exceptions import AuthException


def associate_by_email(details, *args, **kwargs):
    """Return user entry with same email address as one returned on details."""
    email = details.get('email')

    warn_setting('SOCIAL_AUTH_ASSOCIATE_BY_MAIL', 'associate_by_email')

    if email and setting('SOCIAL_AUTH_ASSOCIATE_BY_MAIL', True):
        # try to associate accounts registered with the same email address,
        # only if it's a single object. AuthException is raised if multiple
        # objects are returned
        try:
            address = EmailAddress.objects.filter(email=email, verified=True).select_related("user").get()
            return {"user": address.user}
        except MultipleObjectsReturned:
            raise AuthException(kwargs['backend'], 'Not unique email address.')
        except EmailAddress.DoesNotExist:
            pass

########NEW FILE########
__FILENAME__ = user
from account.models import Account, EmailAddress

from social_auth.models import User
from social_auth.backends.pipeline import warn_setting
from social_auth.utils import setting
from social_auth.signals import socialauth_not_registered


def create_user(backend, details, response, uid, username, user=None, *args, **kwargs):
    """Create user. Depends on get_username pipeline."""
    if user:
        return {'user': user}
    if not username:
        return None

    warn_setting('SOCIAL_AUTH_CREATE_USERS', 'create_user')

    if not setting('SOCIAL_AUTH_CREATE_USERS', True):
        # Send signal for cases where tracking failed registering is useful.
        socialauth_not_registered.send(sender=backend.__class__, uid=uid, response=response, details=details)
        return None

    email = details.get('email')
    request = kwargs["request"]

    user = User.objects.create_user(username=username, email=email)

    Account.create(request=request, user=user)
    EmailAddress.objects.add_email(user, user.email, primary=True)

    return {
        'user': user,
        'is_new': True
    }

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from crate.web.social_auth.views import SocialAuths

urlpatterns = patterns("",
    url(r"^social/$", SocialAuths.as_view(), name="social_auth_accounts"),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.views.generic.list import ListView
from django.utils.translation import ugettext as _

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required

from account.mixins import LoginRequiredMixin
from social_auth.decorators import dsa_view
from social_auth.models import UserSocialAuth
from social_auth.utils import backend_setting
from social_auth.views import DEFAULT_REDIRECT


class SocialAuths(LoginRequiredMixin, ListView):

    model = UserSocialAuth

    def get_queryset(self):
        qs = super(SocialAuths, self).get_queryset()
        qs = qs.filter(user=self.request.user)
        return qs


@login_required
@dsa_view()
def disconnect(request, backend, association_id=None):
    associated = request.user.social_auth.count()
    url = request.REQUEST.get(REDIRECT_FIELD_NAME, '') or backend_setting(backend, 'SOCIAL_AUTH_DISCONNECT_REDIRECT_URL') or DEFAULT_REDIRECT

    if not request.user.has_usable_password() and associated <= 1:
        messages.error(request, _("Cannot remove the only Social Account without first setting a Password or adding another Social Account."))
        return HttpResponseRedirect(url)

    usa = request.user.social_auth.get(pk=association_id)

    backend.disconnect(request.user, association_id)
    messages.success(request, _("Removed the %(provider)s account '%(uid)s'.") % {
        "provider": usa.provider,
        "uid": usa.extra_data.get("display", usa.uid) if usa.extra_data is not None else usa.uid,
    })

    return HttpResponseRedirect(url)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = helpers
import os

from urllib import urlencode
from urlparse import urlparse, parse_qs, urlunparse

from django.conf import settings
from django.utils import formats

import jinja2

from jingo import register
from account.utils import user_display as pinax_user_display
from staticfiles.storage import staticfiles_storage


@register.function
def ifelse(first, test, nelse):
    return first if test else nelse


@register.function
def pagination_numbers(numbers, current, max_num=13):
    step = (max_num - 1) / 2
    start = numbers.index(current) - step

    if start < 0:
        end = numbers.index(current) + step + abs(start)
        start = 0
    else:
        end = numbers.index(current) + step
    return numbers[start:end + 1]


@register.filter
def reqarg(url, name, value=None):
    parsed = urlparse(url)
    data = parse_qs(parsed.query)
    if value is not None:
        data.update({
            name: [value],
        })
    else:
        if name in data:
            del data[name]

    _data = []
    for key, value in data.iteritems():
        for item in value:
            _data.append((key, item))

    return jinja2.Markup(urlunparse([parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(_data), parsed.fragment]))


@register.filter
def filename(name):
    return os.path.basename(name)


@register.function
def char_split(value, names=None, char="$"):
    value_list = value.split(char)

    if names is not None:
        return dict(zip(names, value_list))

    return value_list


@register.filter
def date(value, arg=None):
    """Formats a date according to the given format."""
    if not value:
        return u''
    if arg is None:
        arg = settings.DATE_FORMAT
    try:
        return formats.date_format(value, arg)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''


@register.function
def static(path):
    """
    A template tag that returns the URL to a file
    using staticfiles' storage backend
    """
    return staticfiles_storage.url(path)


@register.filter
def is_checkbox(field):
    return field.field.widget.__class__.__name__.lower() == "checkboxinput"


@register.filter
def css_class(field):
    return field.field.widget.__class__.__name__.lower()


@register.function
def user_display(user):
    return pinax_user_display(user)


@register.function
def null_get(d, key, fallback=None):
    if d is None:
        return fallback
    return d.get(key, fallback)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
