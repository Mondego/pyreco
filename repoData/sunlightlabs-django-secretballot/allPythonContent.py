__FILENAME__ = middleware
from hashlib import md5


class SecretBallotMiddleware(object):
    def process_request(self, request):
        request.secretballot_token = self.generate_token(request)

    def generate_token(self, request):
        raise NotImplementedError


class SecretBallotIpMiddleware(SecretBallotMiddleware):
    def generate_token(self, request):
        return request.META['REMOTE_ADDR']


class SecretBallotIpUseragentMiddleware(SecretBallotMiddleware):
    def generate_token(self, request):
        s = ''.join((request.META['REMOTE_ADDR'], request.META.get('HTTP_USER_AGENT', '')))
        return md5(s).hexdigest()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Vote'
        db.create_table('secretballot_vote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('vote', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('secretballot', ['Vote'])

        # Adding unique constraint on 'Vote', fields ['token', 'content_type', 'object_id']
        db.create_unique('secretballot_vote', ['token', 'content_type_id', 'object_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Vote', fields ['token', 'content_type', 'object_id']
        db.delete_unique('secretballot_vote', ['token', 'content_type_id', 'object_id'])

        # Deleting model 'Vote'
        db.delete_table('secretballot_vote')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'secretballot.vote': {
            'Meta': {'unique_together': "(('token', 'content_type', 'object_id'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vote': ('django.db.models.fields.SmallIntegerField', [], {})
        }
    }

    complete_apps = ['secretballot']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_vote_created_at__add_field_vote_updated_at
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Vote.created_at'
        db.add_column('secretballot_vote', 'created_at',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, db_index=True, blank=True),
                      keep_default=False)

        # Adding field 'Vote.updated_at'
        db.add_column('secretballot_vote', 'updated_at',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, db_index=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Vote.created_at'
        db.delete_column('secretballot_vote', 'created_at')

        # Deleting field 'Vote.updated_at'
        db.delete_column('secretballot_vote', 'updated_at')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'secretballot.vote': {
            'Meta': {'unique_together': "(('token', 'content_type', 'object_id'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'vote': ('django.db.models.fields.SmallIntegerField', [], {})
        }
    }

    complete_apps = ['secretballot']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

VOTE_CHOICES = (
    (+1, '+1'),
    (-1, '-1'),
)


class Vote(models.Model):
    token = models.CharField(max_length=50)
    vote = models.SmallIntegerField(choices=VOTE_CHOICES)

    # generic foreign key to the model being voted upon
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True, null=True)

    class Meta:
        unique_together = (('token', 'content_type', 'object_id'),)

    def __unicode__(self):
        return '%s from %s on %s' % (self.get_vote_display(), self.token, self.content_object)

########NEW FILE########
__FILENAME__ = views
from django.template import loader, RequestContext
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseForbidden
from django.db.models.base import ModelBase
from django.contrib.contenttypes.models import ContentType
from secretballot.models import Vote


def vote(request, content_type, object_id, vote, can_vote_test=None,
         redirect_url=None, template_name=None, template_loader=loader,
         extra_context=None, context_processors=None, mimetype=None):

    # get the token from a SecretBallotMiddleware
    if not hasattr(request, 'secretballot_token'):
        raise ImproperlyConfigured('To use secretballot a SecretBallotMiddleware '
                                   'must be installed. (see secretballot/middleware.py)')
    token = request.secretballot_token

    if isinstance(content_type, ContentType):
        pass
    elif isinstance(content_type, ModelBase):
        content_type = ContentType.objects.get_for_model(content_type)
    elif isinstance(content_type, basestring) and '.' in content_type:
        app, modelname = content_type.split('.')
        content_type = ContentType.objects.get(app_label=app, model__iexact=modelname)
    else:
        raise ValueError('content_type must be an instance of ContentType, a model, '
                         'or "app.modelname" string')

    # do the action
    if vote:
        # 404 if object to be voted upon doesn't exist
        if content_type.model_class().objects.filter(pk=object_id).count() == 0:
            raise Http404

        # if there is a can_vote_test func specified, test then 403 if needed
        if can_vote_test:
            if not can_vote_test(request, content_type, object_id, vote):
                return HttpResponseForbidden("vote was forbidden")

        vobj, new = Vote.objects.get_or_create(content_type=content_type, object_id=object_id,
                                               token=token, defaults={'vote': vote})
        if not new:
            vobj.vote = vote
            vobj.save()
    else:
        Vote.objects.filter(content_type=content_type, object_id=object_id, token=token).delete()

    # build the response
    if redirect_url:
        return HttpResponseRedirect(redirect_url)
    elif template_name:
        content_obj = content_type.get_object_for_this_type(pk=object_id)
        c = RequestContext(request, {'content_obj': content_obj}, context_processors)

        # copy extra_context into context, calling any callables
        for k, v in extra_context.items():
            if callable(v):
                c[k] = v()
            else:
                c[k] = v

        t = template_loader.get_template(template_name)
        body = t.render(c)
    else:
        votes = Vote.objects.filter(content_type=content_type, object_id=object_id).count()
        body = '{"num_votes":%d}' % votes

    return HttpResponse(body, content_type=mimetype)

########NEW FILE########
