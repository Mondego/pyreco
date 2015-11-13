__FILENAME__ = admin
from datetime import datetime
from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib.admin.util import unquote
from django.contrib.auth.admin import csrf_protect_m
from django.db import transaction
from django.forms.formsets import all_valid
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.response import TemplateResponse
from django.utils.functional import update_wrapper
from django.utils.safestring import mark_safe
from nudge import client
from nudge import utils
from nudge.models import Batch, BatchPushItem, default_batch_start_date

try:
    import simplejson as json
except ImportError:
    import json


class BatchAdmin(admin.ModelAdmin):
    exclude = ['preflight', 'selected_items_packed', 'first_push_attempt']

    def render_change_form(self, *args, **kwargs):
        request, context = args[:2]
        batch = context.get('original')
        attached_versions = []
        if batch:
            context.update({
                'pushing': bool(batch.preflight),
                'object': batch,
            })
        else:
            context.update({'editable': True})

        if batch:
            available_changes = [item for item in utils.changed_items(
                batch.start_date, batch=batch)
                if item not in attached_versions]
        else:
            available_changes = [item for item in utils.changed_items(
                default_batch_start_date()) if item not in attached_versions]

        context.update({'available_changes': available_changes})

        return super(BatchAdmin, self).render_change_form(*args, **kwargs)

    def change_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if obj.preflight:
            return HttpResponseRedirect('push/')
        if '_save_and_push' not in request.POST:
            return super(BatchAdmin, self).change_view(
                request, object_id, extra_context=extra_context)
        else:
            ModelForm = self.get_form(request, obj)
            formsets = []
            form = ModelForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            prefixes = {}
            if hasattr(self, 'inline_instances'):
                inline_instances = self.inline_instances

            else:
                inline_instances = []

            zipped_formsets = zip(self.get_formsets(request, new_object),
                                  inline_instances)
            for FormSet, inline in zipped_formsets:
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object, prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)

            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=True)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=True)

                change_message = self.construct_change_message(
                    request, form, formsets)
                self.log_change(request, new_object, change_message)

                return HttpResponseRedirect('push/')

        context = {}.update(extra_context)
        return self.render_change_form(request, context, change=True, obj=obj)

    @csrf_protect_m
    @transaction.commit_on_success
    def pushing_view(self, request, object_id, form_url='', extra_context=None):
        batch_push_item_pk = request.POST.get('push-batch-item')
        if request.is_ajax() and batch_push_item_pk:
            batch_push_item = BatchPushItem.objects.get(pk=batch_push_item_pk)
            if not batch_push_item.batch.first_push_attempt:
                batch_push_item.batch.first_push_attempt = datetime.now()
                batch_push_item.batch.save()
            client.push_one(batch_push_item)
            return render_to_response('admin/nudge/batch/_batch_item_row.html',
                                      {'batch_item': batch_push_item})

        batch = self.model.objects.get(pk=object_id)

        if request.method == 'POST' and 'abort_preflight' in request.POST:
            BatchPushItem.objects.filter(batch=batch).delete()
            batch.preflight = None
            batch.save()

        if request.method == 'POST' and 'push_now' in request.POST:
            client.push_batch(batch)

        if not batch.preflight:
            return HttpResponseRedirect('../')

        batch_push_items = BatchPushItem.objects.filter(batch=batch)
        context = {'batch_push_items': batch_push_items,
                   'media': mark_safe(self.media)}

        opts = self.model._meta
        app_label = opts.app_label
        return TemplateResponse(request, [
            "admin/%s/%s/push.html" % (app_label, opts.object_name.lower()),
        ], context, current_app=self.admin_site.name)

    def get_urls(self):
        urlpatterns = super(BatchAdmin, self).get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        urlpatterns = patterns('', url(r'^(.+)/push/$',
                               wrap(self.pushing_view),
                               name='%s_%s_push' % info)) + urlpatterns
        return urlpatterns

    def save_model(self, request, obj, form, change):
        items_str = request.POST.getlist('changes_in_batch')

        obj.selected_items_packed = json.dumps(items_str)
        if '_save_and_push' in request.POST:
            obj.preflight = datetime.now()
            obj.save()
            for selected_item in obj.selected_items:
                bi = utils.inflate_batch_item(selected_item, obj)
                bi.save()
            request.POST['_continue'] = 1
        obj.save()


admin.site.register(Batch, BatchAdmin)

########NEW FILE########
__FILENAME__ = client
"""
Commands to send to a nudge server
"""
import datetime
import hashlib
import os
import pickle
import urllib
import urllib2
import json
from Crypto.Cipher import AES

from django.conf import settings
from django.core import serializers
from django.db import models
from django.contrib.contenttypes.models import ContentType

from nudge.models import Batch, BatchPushItem
from itertools import chain
from reversion import get_for_object
from urlparse import urljoin

from .exceptions import CommandException

from django.conf import settings

IGNORE_RELATIONSHIPS = []

if hasattr(settings, 'NUDGE_IGNORE_RELATIONSHIPS'):
    for model_reference in settings.NUDGE_IGNORE_RELATIONSHIPS:
        app_label, model_label = model_reference.split('.')
        ct = ContentType.objects.get_by_natural_key(app_label, model_label)
        IGNORE_RELATIONSHIPS.append(ct.model_class())

def encrypt(key, plaintext):
    m = hashlib.md5(os.urandom(16))
    iv = m.digest()
    encobj = AES.new(key, AES.MODE_CBC, iv)
    pad = lambda s: s + (16 - len(s) % 16) * ' '
    return (encobj.encrypt(pad(plaintext)).encode('hex'), iv)


def encrypt_batch(key, b_plaintext):
    """Encrypts a pickled batch for sending to server"""
    encrypted, iv = encrypt(key, b_plaintext)
    return {'batch': encrypted, 'iv': iv.encode('hex')}


def serialize_objects(key, batch_push_items):
    """
    Returns an urlencoded pickled serialization of a batch ready to be sent
    to a nudge server.
    """
    batch_objects = []
    dependencies = [] 
    deletions = []

    for batch_item in batch_push_items:
        version = batch_item.version
        if version.type < 2 and version.object:
            updated_obj=version.object
            batch_objects.append(updated_obj)
            options = updated_obj._meta
            fk_fields = [f for f in options.fields if
                         isinstance(f, models.ForeignKey)]
            m2m_fields = [field.name for field in options.many_to_many]
            through_fields = [rel.get_accessor_name() for rel in
                              options.get_all_related_objects()]
            for related_obj in [getattr(updated_obj, f.name) for f in fk_fields]:
                if related_obj and related_obj not in dependencies and type(related_obj) not in IGNORE_RELATIONSHIPS:
                    dependencies.append(related_obj)

            for manager_name in chain(m2m_fields, through_fields):
                manager = getattr(updated_obj, manager_name)
                for related_obj in manager.all():
                    if related_obj and related_obj not in dependencies and type(related_obj) not in IGNORE_RELATIONSHIPS:
                        dependencies.append(related_obj)

        else:
            app_label = batch_item.version.content_type.app_label
            model_label = batch_item.version.content_type.model
            object_id = batch_item.version.object_id
            deletions.append((app_label, model_label, object_id))

    batch_items_serialized = serializers.serialize('json', batch_objects)
    dependencies_serialized = serializers.serialize('json', dependencies)
    b_plaintext = pickle.dumps({'update': batch_items_serialized,
                                'deletions' : json.dumps(deletions),
                                'dependencies': dependencies_serialized})

    return encrypt_batch(key, b_plaintext)


def send_command(target, data):
    """sends a nudge api command"""
    url = urljoin(settings.NUDGE_REMOTE_ADDRESS, target)
    req = urllib2.Request(url, urllib.urlencode(data))
    try:
        return urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        raise CommandException(
            'An exception occurred while contacting %s: %s' %
            (url, e), e)


def push_one(batch_push_item):
    key = settings.NUDGE_KEY.decode('hex')
    if batch_push_item.last_tried and batch_push_item.success:
        return 200
    batch_push_item.last_tried = datetime.datetime.now()
    try:
        response = send_command(
          'batch/', serialize_objects(key, [batch_push_item]))
        if response.getcode() == 200:
            batch_push_item.success=True
    except CommandException, e:
        response = e.orig_exception
    batch_push_item.save()
    return response.getcode()


def push_batch(batch):
    """
    Pushes a batch to a server, logs push and timestamps on success
    """
    batch_push_items = BatchPushItem.objects.filter(batch=batch)
    if not batch.first_push_attempt:
        batch.first_push_attempt = datetime.datetime.now()
    for batch_push_item in batch_push_items:
        push_one(batch_push_item)
    batch.save()


def push_test_batch():
    """
    pushes empty batch to server to test settings and returns True on success
    """
    try:
        key = settings.NUDGE_KEY.decode('hex')
        response = send_command('batch/', serialize_batch(key, Batch()))
        return False if response.getcode() != 200 else True
    except:
        return False

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from models import Post


admin.site.register(Post)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=1000)


class Post(models.Model):
    title = models.CharField(max_length=1000)
    author = models.ForeignKey(Author)
    body = models.TextField()

    def __unicode__(self):
        return self.title

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
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = exceptions
class BaseNudgeException(Exception):
    """Base class for all Nudge exceptions. Should never be raised directly"""
    pass


class CommandException(BaseNudgeException):
    """An exception occurred while trying to perform a remote Nudge command"""

    def __init__(self, msg, orig_exception):
        self.orig_exception = orig_exception
        self.msg = msg


class BatchValidationError(BaseNudgeException):
    "This batch contains an error"
    
    def __init__(self, batch):
        self.batch = batch
        self.msg = "Batch Validation Failed"


class BatchPushFailure(BaseNudgeException):
    "Pushing this batch failed"

    def __init__(self, http_status=500):
        self.http_status=http_status

########NEW FILE########
__FILENAME__ = new_nudge_key
"""
(Re)generates a new local_key
"""
from django.core.management.base import NoArgsCommand
from nudge.utils import generate_key


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        new_key = generate_key()
        print "# add this to your settings.py"
        print "NUDGE_KEY = '%s'" % new_key

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    depends_on = (
        ('reversion', '0001_initial'),
    )

    def forwards(self, orm):
        # Adding model 'BatchPushItem'
        db.create_table('nudge_batchpushitem', (
            ('id',
             self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('batch', self.gf('django.db.models.fields.related.ForeignKey')(
                to=orm['nudge.Batch'])),
            ('version', self.gf('django.db.models.fields.related.ForeignKey')(
                to=orm['reversion.Version'])),
            ('last_tried',
             self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('success',
             self.gf('django.db.models.fields.BooleanField')(default=False)),
            ))
        db.send_create_signal('nudge', ['BatchPushItem'])

        # Adding model 'Batch'
        db.create_table('nudge_batch', (
            ('id',
             self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title',
             self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('description',
             self.gf('django.db.models.fields.TextField')(blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateField')(
                default=datetime.datetime(2012, 9, 13, 0, 0))),
            ('created',
             self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True,
                 blank=True)),
            ('updated',
             self.gf('django.db.models.fields.DateTimeField')(auto_now=True,
                 blank=True)),
            ('preflight',
             self.gf('django.db.models.fields.DateTimeField')(null=True,
                 blank=True)),
            ('first_push_attempt',
             self.gf('django.db.models.fields.DateTimeField')(null=True,
                 blank=True)),
            ('selected_items_packed',
             self.gf('django.db.models.fields.TextField')(default='[]')),
            ))
        db.send_create_signal('nudge', ['Batch'])

        # Adding model 'PushHistoryItem'
        db.create_table('nudge_pushhistoryitem', (
            ('id',
             self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('batch', self.gf('django.db.models.fields.related.ForeignKey')(
                to=orm['nudge.Batch'], on_delete=models.PROTECT)),
            ('created',
             self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True,
                 blank=True)),
            ('http_result',
             self.gf('django.db.models.fields.IntegerField')(null=True,
                 blank=True)),
            ))
        db.send_create_signal('nudge', ['PushHistoryItem'])

        # Adding model 'BatchItem'
        db.create_table('nudge_batchitem', (
            ('id',
             self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('object_id', self.gf('django.db.models.fields.IntegerField')()),
            ('version', self.gf('django.db.models.fields.related.ForeignKey')(
                to=orm['reversion.Version'])),
            ('batch', self.gf('django.db.models.fields.related.ForeignKey')(
                to=orm['nudge.Batch'])),
            ))
        db.send_create_signal('nudge', ['BatchItem'])


    def backwards(self, orm):
        # Deleting model 'BatchPushItem'
        db.delete_table('nudge_batchpushitem')

        # Deleting model 'Batch'
        db.delete_table('nudge_batch')

        # Deleting model 'PushHistoryItem'
        db.delete_table('nudge_pushhistoryitem')

        # Deleting model 'BatchItem'
        db.delete_table('nudge_batchitem')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [],
                     {'unique': 'True', 'max_length': '80'}),
            'permissions': (
            'django.db.models.fields.related.ManyToManyField', [],
            {'to': "orm['auth.Permission']", 'symmetrical': 'False',
             'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {
            'ordering': "('content_type__app_label', 'content_type__model', 'codename')",
            'unique_together': "(('content_type', 'codename'),)",
            'object_name': 'Permission'},
            'codename': (
            'django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [],
                             {'to': "orm['contenttypes.ContentType']"}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': (
            'django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [],
                            {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [],
                      {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [],
                           {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [],
                       {'to': "orm['auth.Group']", 'symmetrical': 'False',
                        'blank': 'True'}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': (
            'django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': (
            'django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': (
            'django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [],
                           {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [],
                          {'max_length': '30', 'blank': 'True'}),
            'password': (
            'django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': (
            'django.db.models.fields.related.ManyToManyField', [],
            {'to': "orm['auth.Permission']", 'symmetrical': 'False',
             'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [],
                         {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)",
                     'unique_together': "(('app_label', 'model'),)",
                     'object_name': 'ContentType',
                     'db_table': "'django_content_type'"},
            'app_label': (
            'django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': (
            'django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': (
            'django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'nudge.batch': {
            'Meta': {'object_name': 'Batch'},
            'created': ('django.db.models.fields.DateTimeField', [],
                        {'auto_now_add': 'True', 'blank': 'True'}),
            'description': (
            'django.db.models.fields.TextField', [], {'blank': 'True'}),
            'first_push_attempt': ('django.db.models.fields.DateTimeField', [],
                                   {'null': 'True', 'blank': 'True'}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'preflight': ('django.db.models.fields.DateTimeField', [],
                          {'null': 'True', 'blank': 'True'}),
            'selected_items_packed': (
            'django.db.models.fields.TextField', [], {'default': "'[]'"}),
            'start_date': ('django.db.models.fields.DateField', [],
                           {'default': 'datetime.datetime(2012, 9, 13, 0, 0)'}),
            'title': (
            'django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'updated': ('django.db.models.fields.DateTimeField', [],
                        {'auto_now': 'True', 'blank': 'True'})
        },
        'nudge.batchitem': {
            'Meta': {'object_name': 'BatchItem'},
            'batch': ('django.db.models.fields.related.ForeignKey', [],
                      {'to': "orm['nudge.Batch']"}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'version': ('django.db.models.fields.related.ForeignKey', [],
                        {'to': "orm['reversion.Version']"})
        },
        'nudge.batchpushitem': {
            'Meta': {'object_name': 'BatchPushItem'},
            'batch': ('django.db.models.fields.related.ForeignKey', [],
                      {'to': "orm['nudge.Batch']"}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_tried': (
            'django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'success': (
            'django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'version': ('django.db.models.fields.related.ForeignKey', [],
                        {'to': "orm['reversion.Version']"})
        },
        'nudge.pushhistoryitem': {
            'Meta': {'object_name': 'PushHistoryItem'},
            'batch': ('django.db.models.fields.related.ForeignKey', [],
                      {'to': "orm['nudge.Batch']",
                       'on_delete': 'models.PROTECT'}),
            'created': ('django.db.models.fields.DateTimeField', [],
                        {'auto_now_add': 'True', 'blank': 'True'}),
            'http_result': ('django.db.models.fields.IntegerField', [],
                            {'null': 'True', 'blank': 'True'}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'reversion.revision': {
            'Meta': {'object_name': 'Revision'},
            'comment': (
            'django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [],
                             {'auto_now_add': 'True', 'blank': 'True'}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manager_slug': ('django.db.models.fields.CharField', [],
                             {'default': "'default'", 'max_length': '200',
                              'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [],
                     {'to': "orm['auth.User']", 'null': 'True',
                      'blank': 'True'})
        },
        'reversion.version': {
            'Meta': {'object_name': 'Version'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [],
                             {'to': "orm['contenttypes.ContentType']"}),
            'format': (
            'django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': (
            'django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.TextField', [], {}),
            'object_id_int': ('django.db.models.fields.IntegerField', [],
                              {'db_index': 'True', 'null': 'True',
                               'blank': 'True'}),
            'object_repr': ('django.db.models.fields.TextField', [], {}),
            'revision': ('django.db.models.fields.related.ForeignKey', [],
                         {'to': "orm['reversion.Revision']"}),
            'serialized_data': ('django.db.models.fields.TextField', [], {}),
            'type': ('django.db.models.fields.PositiveSmallIntegerField', [],
                     {'db_index': 'True'})
        }
    }

    complete_apps = ['nudge']

########NEW FILE########
__FILENAME__ = models
from datetime import date
from django.db import models

try:
    import simplejson as json
except ImportError:
    import json


class BatchPushItem(models.Model):
    batch = models.ForeignKey('Batch')
    version = models.ForeignKey('reversion.Version')
    last_tried = models.DateTimeField(null=True)
    success = models.BooleanField(default=False)

    def __unicode__(self):
        return unicode(self.version)

    def version_type_string(self):
        return VERSION_TYPE_LOOKUP[self.version.type]


def default_batch_start_date():
    # date last completed batch pushed
    # or date of earliest revision
    # or today
    return date.today()


class Batch(models.Model):
    title = models.CharField(max_length=1000)
    description = models.TextField(blank=True)
    start_date = models.DateField(default=default_batch_start_date)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    preflight = models.DateTimeField(null=True, blank=True)
    first_push_attempt = models.DateTimeField(null=True, blank=True)
    selected_items_packed = models.TextField(default=json.dumps([]))

    def __unicode__(self):
        return u'%s' % self.title

    def is_valid(self, test_only=True):
        return True

    @property
    def selected_items(self):
        if not hasattr(self, '_selected_items'):
            self._selected_items = json.loads(self.selected_items_packed)
        return self._selected_items

    class Meta:
        verbose_name_plural = 'batches'
        permissions = (
            ('push_batch', 'Can push batches'),
        )


class PushHistoryItem(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    http_result = models.IntegerField(blank=True, null=True)


class BatchItem(models.Model):
    object_id = models.IntegerField()
    version = models.ForeignKey('reversion.Version')
    batch = models.ForeignKey(Batch)

    def __unicode__(self):
        return u'%s' % self.version.object_repr


from nudge.utils import VERSION_TYPE_LOOKUP

########NEW FILE########
__FILENAME__ = server
"""
Handles commands received from a Nudge client
"""
import binascii
import pickle
from Crypto.Cipher import AES
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
import reversion
from reversion.models import Version


try:
    import simplejson as json
except ImportError:
    import json




def decrypt(key, ciphertext, iv):
    """Decrypts message sent from client using shared symmetric key"""
    ciphertext = binascii.unhexlify(ciphertext)
    decobj = AES.new(key, AES.MODE_CBC, iv)
    plaintext = decobj.decrypt(ciphertext)
    return plaintext


def versions(keys):
    results = {}
    for key in keys:
        app, model, pk = key.split('~')
        content_type = ContentType.objects.get_by_natural_key(app, model)
        versions = Version.objects.all().filter(
            content_type=content_type
        ).filter(object_id=pk).order_by('-revision__date_created')
        if versions:
            latest = versions[0]
            results[key] = (latest.pk,
                            latest.type,
                            latest.revision
                            .date_created.strftime('%b %d, %Y, %I:%M %p'))
        else:
            results[key] = None
    return json.dumps(results)


def process_batch(key, batch_info, iv):
    """Loops through items in a batch and processes them."""
    batch_info = pickle.loads(decrypt(key, batch_info, iv.decode('hex')))
    success = True


    if 'dependencies' in batch_info:
        dependencies = serializers.deserialize('json', batch_info['dependencies'])
        for dep in dependencies:
            dep.save()

    if 'update' in batch_info:
        updates = serializers.deserialize('json', batch_info['update'])
        for item in updates:
            with reversion.create_revision():
                item.save()

    if 'deletions' in batch_info:
        deletions = json.loads(batch_info['deletions'])
        for deletion in deletions:
            app_label, model_label, object_id = deletion
            ct = ContentType.objects.get_by_natural_key(app_label, model_label)
            for result in ct.model_class().objects.filter(pk=object_id):
                with reversion.create_revision():
                    result.delete()
                    
    return success

########NEW FILE########
__FILENAME__ = nudge_admin_helpers
from django import template

register = template.Library()


@register.inclusion_tag(
    'admin/nudge/batch/submit_line.html', takes_context=True)
def submit_batch_row(context):
    """
    Displays the row of buttons for delete and save.
    """
    opts = context['opts']
    change = context['change']
    is_popup = context['is_popup']
    save_as = context['save_as']
    return {
        'onclick_attrib': (opts.get_ordered_objects() and change
                           and 'onclick="submitOrderForm();"' or ''),
        'show_delete_link': (not is_popup and context['has_delete_permission']
                             and (change)),
        'show_save_as_new': (not is_popup and change and save_as),
        'show_save_and_add_another': (context['has_add_permission']
                                      and not is_popup and (not save_as
                                      or context['add'])),
        'show_save_and_continue': (not is_popup
                                   and context['has_change_permission']),
        'is_popup': is_popup,
        'show_save': True
    }

########NEW FILE########
__FILENAME__ = version_display
from django import template
from nudge.utils import VERSION_TYPE_LOOKUP

register = template.Library()


@register.filter
def change_type(value):
    return VERSION_TYPE_LOOKUP[int(value)]

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.core.exceptions import ObjectDoesNotExist

import reversion
from django.test import TestCase
from nudge.client import encrypt, serialize_batch
from nudge.demo.models import Post, Author
from nudge.exceptions import BatchValidationError
from nudge.management.commands import nudgeinit
from nudge.models import Batch, BatchItem
from nudge.server import decrypt, process_batch
from nudge.utils import generate_key, add_versions_to_batch, changed_items

reversion.register(Post)
reversion.register(Author)

nudgeinit.Command().handle_noargs()


@reversion.create_revision()
def create_author():
    new_author = Author(name="Ross")
    new_author.save()
    return new_author


@reversion.create_revision()
def delete_with_reversion(object):
    object.delete()


class EncryptionTest(TestCase):
    def setUp(self):
        self.new_author = create_author()

    def tearDown(self):
        Author.objects.all().delete()

    def test_encryption(self):
        """
        Tests that encryption and decryption are sane
        """
        message = u"Hello, Nudge Encryption!"
        key = generate_key()
        encrypted, iv = encrypt(key.decode('hex'), message)
        decrypted = decrypt(key.decode('hex'), encrypted, iv)
        self.assertEqual(message, decrypted.strip())


class BatchTest(TestCase):
    def setUp(self):
        self.key = generate_key()
        self.batch = Batch(title="Best Batch Ever")
        self.new_author = create_author()
        self.batch.save()

    def tearDown(self):
        Author.objects.all().delete()
        BatchItem.objects.all().delete()

    def test_batch_serialization_and_processing(self):
        add_versions_to_batch(self.batch, changed_items())
        serialized = serialize_batch(self.key.decode('hex'), self.batch)
        process_batch(self.key.decode('hex'),
                      serialized['batch'],
                      serialized['iv'])

    def test_batch_with_deletion(self):
        delete_with_reversion(self.new_author)
        add_versions_to_batch(self.batch, changed_items())
        serialized = serialize_batch(self.key.decode('hex'), self.batch)
        with self.assertRaises(ObjectDoesNotExist):
            process_batch(self.key.decode('hex'),
                          serialized['batch'],
                          serialized['iv'])


class VersionTest(TestCase):
    def setUp(self):
        self.new_author = create_author()

    def tearDown(self):
        Author.objects.all().delete()

    def test_identify_changes(self):
        self.assertIn(self.new_author,
                      [version.object for version in changed_items()])

    def test_add_changes_to_batch(self):
        new_batch = Batch(title="Best Batch Ever")
        new_batch.save()
        add_versions_to_batch(new_batch, changed_items())
        self.assertIn(self.new_author,
                      [bi.version.object for bi
                       in new_batch.batchitem_set.all()])

    def test_add_deletion_to_batch(self):
        delete_with_reversion(self.new_author)

    def test_batch_validation(self):
        batch1 = Batch(title="Best Batch Ever")
        batch1.save()
        batch2 = Batch(title="2nd Best Batch Ever")
        batch2.save()
        add_versions_to_batch(batch1, changed_items())
        add_versions_to_batch(batch2, changed_items())
        with self.assertRaises(BatchValidationError):
            batch1.is_valid(test_only=False)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns('nudge.views',
                       url(r'^batch/$', 'batch'),
                       url(r'^check-versions/$', 'check_versions'),)

########NEW FILE########
__FILENAME__ = utils
import hashlib
import os

from datetime import datetime

from django.db.models.fields.related import (
    ReverseSingleRelatedObjectDescriptor, SingleRelatedObjectDescriptor,
    ForeignRelatedObjectsDescriptor)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from nudge.models import Batch, BatchPushItem
from nudge.exceptions import CommandException
from reversion.models import Version, Revision, VERSION_TYPE_CHOICES
from reversion import get_for_object

try:
    import simplejson as json
except ImportError:
    import json

VERSION_TYPE_LOOKUP = dict(VERSION_TYPE_CHOICES)


class PotentialBatchItem(object):
    def __init__(self, version, batch=None):
        self.content_type = version.content_type
        self.pk = version.object_id
        self.repr = version.object_repr
        self.version = version
        if batch:
            self.selected = (self.key() in batch.selected_items)

    def __eq__(self, other):
        return (self.content_type == other.content_type and
                self.pk == other.pk)

    def __unicode__(self):
        return self.repr

    def key(self):
        return '~'.join((self.content_type.app_label,
                         self.content_type.model,
                         self.pk))

    def version_type_string(self):
        return VERSION_TYPE_LOOKUP[self.version.type]


def inflate_batch_item(key, batch):
    app_label, model_label, pk = key.split('~')
    content_type = ContentType.objects.get_by_natural_key(app_label,
                                                          model_label)
    latest_version = Version.objects.filter(
        content_type=content_type
    ).filter(
        object_id=pk).order_by('-revision__date_created')[0]
    return BatchPushItem(batch=batch, version=latest_version)


def related_objects(obj):
    model = type(obj)
    relationship_names = []
    related_types = (ReverseSingleRelatedObjectDescriptor,
                     SingleRelatedObjectDescriptor,)
    for attr in dir(model):
        if isinstance(getattr(model, attr), related_types):
            relationship_names.append(attr)
    return [getattr(obj, relname) for relname in relationship_names
            if bool(getattr(obj, relname))]


def caster(fields, model):
    relationship_names = []
    related_types = (ReverseSingleRelatedObjectDescriptor,
                     SingleRelatedObjectDescriptor,
                     ForeignRelatedObjectsDescriptor,)
    for attr in dir(model):
        if isinstance(getattr(model, attr), related_types):
            relationship_names.append(attr)
    for rel_name in relationship_names:
        rel = getattr(model, rel_name)
        if rel_name in fields:
            fields[rel_name] = (rel.field.related.parent_model
                                .objects.get(pk=fields[rel_name]))
    return fields


def changed_items(for_date, batch=None):
    """Returns a list of objects that are new or changed and not pushed"""
    from nudge.client import send_command
    types = []
    for type_key in settings.NUDGE_SELECTIVE:
        app, model = type_key.lower().split('.')
        try:
            types.append(ContentType.objects.get_by_natural_key(app, model))
        except ContentType.DoesNotExist:
            raise ValueError(
                'Model listed in NUDGE_SELECTIVE does not exist: %s.%s' %
                  (app, model))

    eligible_versions = Version.objects.all().filter(
        revision__date_created__gte=for_date,
        content_type__in=types
      ).order_by('-revision__date_created')
    
    pot_batch_items = [PotentialBatchItem(version, batch=batch)
                        for version in eligible_versions]

    seen_pbis = []
    keys = [pbi.key() for pbi in pot_batch_items]
    response = send_command('check-versions/', {
        'keys': json.dumps(keys)}
      ).read()
    try:
        remote_versions = json.loads(response)
    except ValueError, e:
        raise CommandException(
          'Error decoding \'check-versions\' response: %s' % e, e)
   
    def seen(key):
        if key not in seen_pbis:
            seen_pbis.append(key)
            return True
        else:
            return False

    pot_batch_items = filter(seen, pot_batch_items)
    screened_pbis = []
    for pbi in pot_batch_items:
        remote_details = remote_versions[pbi.key()]
        if remote_details:
            version_pk, version_type, timestamp = remote_details
            remote_dt = datetime.strptime(timestamp,'%b %d, %Y, %I:%M %p')
            if remote_dt < pbi.version.revision.date_created.replace(second=0):
                pbi.remote_timestamp = timestamp
                pbi.remote_change_type = VERSION_TYPE_LOOKUP[version_type]
                screened_pbis.append(pbi)
        else:
            screened_pbis.append(pbi)

    return sorted(screened_pbis, key=lambda pbi: pbi.content_type)


def add_versions_to_batch(batch, versions):
    """Takes a list of Version objects, and adds them to the given Batch"""
    for v in versions:
        item = BatchItem(version=v, batch=batch)
        item.save()


def collect_eligibles(batch):
    """Collects all changed items and adds them to supplied batch"""
    for e in changed_items():
        e.batch = batch
        e.save()


def convert_keys_to_string(dictionary):
    """
    Recursively converts dictionary keys to strings.
    Found at http://stackoverflow.com/a/7027514/104365
    """
    if not isinstance(dictionary, dict):
        return dictionary
    return dict([(str(k), convert_keys_to_string(v))
                for k, v in dictionary.items()])


def generate_key():
    """Generate 32 byte key and return hex representation"""
    seed = os.urandom(32)
    key = hashlib.sha256(seed).digest().encode('hex')
    return key

########NEW FILE########
__FILENAME__ = views
import json
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from nudge import server

@csrf_exempt
@transaction.commit_on_success
def batch(request):
    key = settings.NUDGE_KEY.decode('hex')
    result = server.process_batch(key, request.POST['batch'], request.POST['iv'])
    return HttpResponse(result)


@csrf_exempt
def check_versions(request):
    keys = json.loads(request.POST['keys'])
    result = server.versions(keys)
    return HttpResponse(result)

########NEW FILE########
